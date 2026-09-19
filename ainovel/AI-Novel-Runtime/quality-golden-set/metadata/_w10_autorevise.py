#!/usr/bin/env python3
"""W10-02 automatic-revision arm generator.

For each selected baseline chapter, run the market-anchored prose-hygiene loop
(REFPROFILE-001 anchor) to produce an automatic_revision draft. The plain loop
no-ops on the 16 zero-warning chapters; the market anchor treats out-of-band
reference features as warnings, so every chapter gets a real rewrite attempt.

Writes one JSON per chapter to quality-golden-set/w10-auto-revision/ and a
run-summary with REAL accumulated API cost (captured by wrapping the client).

Usage: python3 _w10_autorevise.py [--limit N] [--dry-run]
Spends real DeepSeek API unless --dry-run.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# runtime import root = AI-Novel-Runtime (metadata -> quality-golden-set -> AI-Novel-Runtime)
RT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RT))

PROJECT = Path(os.path.expanduser("~/Documents/xiaoshuo/AINovel/genesis-pilot"))
DERIVED = PROJECT / "registry" / "derived"
BUILD = PROJECT / "build-serial"
OUT = RT / "quality-golden-set" / "w10-auto-revision"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _w10_select as sel  # noqa: E402


def load_dotenv():
    for env in (PROJECT / ".env", RT.parent / ".env"):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class CostCapturingClient:
    """Wrap an LLMClient; tally real cost/tokens from each LLMResponse. The plain
    generate() path discards these, so we intercept at the client boundary without
    touching production code."""

    def __init__(self, inner):
        from runtime.llm.cost import CostCalculator
        from runtime.llm.factory import DEFAULT_PRICING
        self._inner = inner
        self._calc = CostCalculator(DEFAULT_PRICING)
        self.total_cost = 0.0
        self.currency = None
        self.calls = 0
        self.in_tokens = 0
        self.out_tokens = 0

    def generate(self, request):
        resp = self._inner.generate(request)
        self.calls += 1
        usage = getattr(resp, "token_usage", None)
        # The raw adapter returns cost=None (priced separately in production). We
        # price the captured usage with the same table so the run cost is real.
        cost = getattr(resp, "cost", None)
        if cost is None and usage is not None:
            # Pin provider/model to the known run identity — the raw adapter's
            # provider attr may be an enum/"unknown" that misses the pricing key.
            model_id = os.environ.get("W10_MODEL_ID", "deepseek-chat")
            cost = self._calc.calculate("deepseek", model_id, usage)
        if cost is not None:
            self.total_cost += float(getattr(cost, "total_cost", 0.0) or 0.0)
            self.currency = getattr(cost, "currency", self.currency)
        if usage is not None:
            self.in_tokens += getattr(usage, "input_tokens", 0) or 0
            self.out_tokens += getattr(usage, "output_tokens", 0) or 0
        return resp

    def generate_stream(self, request):
        return self._inner.generate_stream(request)


def build_rewrite_model():
    from runtime.execution.llm_model import LLMExecutionModel
    model = LLMExecutionModel(
        provider="deepseek",
        model_id=os.environ.get("W10_MODEL_ID", "deepseek-chat"),
        temperature=0.7,
        top_p=0.95,
        max_tokens=8000,
        timeout_seconds=180,
        replay_dir=None,
        stream=False,
    )
    cap = CostCapturingClient(model.client)
    model.client = cap
    return model, cap


def load_inner_draft(chapter_id):
    """Return the inner ChapterDraft artifact (with body) for a chapter."""
    path = DERIVED / "drafts" / f"draft-{chapter_id}.json"
    if not path.exists():
        # some layouts name by index; fall back to a scan
        for p in (DERIVED / "drafts").glob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            inner = d.get("draft", d)
            if inner.get("task_id") == chapter_id:
                return inner
        raise FileNotFoundError(f"no draft for {chapter_id}")
    env = json.loads(path.read_text(encoding="utf-8"))
    return env.get("draft", env)


def load_package(chapter_id):
    path = BUILD / f"{chapter_id}.package.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_objective(chapter_id):
    path = DERIVED / "chapter-objective" / f"objective-{chapter_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    for p in (DERIVED / "chapter-objective").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("task_id") == chapter_id or d.get("chapter_id") == chapter_id:
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="process only the first N selected chapters")
    ap.add_argument("--dry-run", action="store_true",
                    help="no API; report plan and per-chapter warning counts only")
    ap.add_argument("--max-rounds", type=int, default=2)
    args = ap.parse_args()

    load_dotenv()
    OUT.mkdir(parents=True, exist_ok=True)

    from runtime.execution.prose_hygiene import improve_prose_hygiene, _warning_count
    from runtime.reference.profile import load_reference_profile

    profile = load_reference_profile(PROJECT)
    if profile is None:
        print("FATAL: REFPROFILE-001 not found; cannot run market-anchored path")
        return 1

    rows = sel.rank()
    selected = rows[:30]
    if args.limit:
        selected = selected[:args.limit]

    model = cap = None
    if not args.dry_run:
        model, cap = build_rewrite_model()

    summary = {"kind": "w10_auto_revision_run", "chapters": [], "started": time.time()}
    for i, row in enumerate(selected, 1):
        cid = row["chapter_id"]
        draft = load_inner_draft(cid)
        pkg = load_package(cid)
        obj = load_objective(cid)
        wbefore = _warning_count(draft, objective=obj, reference_profile=profile)

        if args.dry_run:
            print(f"[{i:>2}/{len(selected)}] {cid}  market_warnings={wbefore}")
            summary["chapters"].append(
                {"chapter_id": cid, "market_warnings_before": wbefore})
            continue

        t0 = time.time()
        result = improve_prose_hygiene(
            model, draft, pkg,
            max_rounds=args.max_rounds, objective=obj, reference_profile=profile)
        sess = result.session
        final = result.final_artifact
        changed = final.get("content_hash") != draft.get("content_hash")
        rec = {
            "chapter_id": cid,
            "verdict": sess.verdict,
            "terminate_reason": sess.terminate_reason,
            "rounds": len(sess.rounds),
            "changed": changed,
            "orig_hash": draft.get("content_hash"),
            "final_hash": final.get("content_hash"),
            "orig_len": len(draft.get("body", "")),
            "final_len": len(final.get("body", "")),
            "elapsed_s": round(time.time() - t0, 1),
        }
        (OUT / f"auto-{cid}.json").write_text(
            json.dumps({"session": sess.to_dict(), "artifact": final},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        summary["chapters"].append(rec)
        print(f"[{i:>2}/{len(selected)}] {cid}  {sess.verdict:>9}  "
              f"rounds={len(sess.rounds)} changed={changed} "
              f"len {rec['orig_len']}->{rec['final_len']}  "
              f"cost={cap.total_cost:.4f} {cap.currency or ''}")

    summary["ended"] = time.time()
    if cap:
        summary["total_cost"] = round(cap.total_cost, 4)
        summary["currency"] = cap.currency
        summary["api_calls"] = cap.calls
        summary["input_tokens"] = cap.in_tokens
        summary["output_tokens"] = cap.out_tokens
    (OUT / "_run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if cap:
        print(f"\nTOTAL: {cap.calls} calls, {cap.total_cost:.4f} {cap.currency}, "
              f"in={cap.in_tokens} out={cap.out_tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
