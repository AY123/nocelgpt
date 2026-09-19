"""w12_run00025_aggregate.py — fold W12 fact-reflow over all 33 RUN-00025 chapters.

Runs a W12 extractor over every immutable archived chapter draft from RUN-00025,
using the real registry only for a read-only roster + reconcile. Nothing is staged
(no plan/approval writes) — an aggregate must not mutate the live registry. Emits
per-chapter candidate / reconciliation stats and a whole-run aggregate.

Two modes:
  det  (default) — DeterministicExtractor, no LLM, no API cost. Floor baseline;
                   yields only status=active → all consistent (0% actionable).
  llm            — LLMExtractor via deepseek (replay-cached in
                   serial-replay-w12probe-gen, so a re-run is free). Produces the
                   real semantic reflow (new abilities/injuries/memory/possessions).

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/w12_run00025_aggregate.py [det|llm]
"""
from __future__ import annotations

import json
import glob
import os
import sys
from collections import Counter
from pathlib import Path

from runtime.candidates.extract import entity_roster, DeterministicExtractor, LLMExtractor
from runtime.candidates.reconcile import reconcile
from runtime.registry_loader import load as load_registry

PILOT = Path(__file__).resolve().parents[1].parent / "genesis-pilot"
DRAFTS = PILOT / "analysis" / "run-00025-snapshot" / "derived" / "drafts"
REPLAY = PILOT / "registry" / "derived" / "serial-replay-w12probe-gen"


def _load_env() -> None:
    for f in (PILOT / ".env", PILOT.parent / ".env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _build_extractor(mode: str):
    if mode == "det":
        return DeterministicExtractor(), "deterministic extractor (no LLM)"
    if mode == "llm":
        _load_env()
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise SystemExit("DEEPSEEK_API_KEY not set — cannot run llm mode")
        from runtime.execution.llm_model import LLMExecutionModel
        model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                                  temperature=0.0, replay_dir=str(REPLAY))
        return LLMExtractor(model), "LLM extractor (deepseek-chat, replay-cached)"
    raise SystemExit(f"unknown mode {mode!r} (use det|llm)")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "det"
    reg = load_registry(PILOT)
    roster = entity_roster(reg, reg.all_ids())
    extractor, source = _build_extractor(mode)

    # READ-ONLY: extract → reconcile directly against the real registry. We do NOT
    # call run_w12_fact_reflow (it STAGES a plan + approval into the ADR-009 queue).
    rows = []
    for f in sorted(glob.glob(str(DRAFTS / "*.json"))):
        env = json.load(open(f))
        draft = env.get("draft") or env
        tid = draft.get("task_id") or os.path.basename(f)[:-5]
        candidates = extractor.extract(draft, known_entities=roster)
        recon = reconcile(reg, candidates)
        rows.append({
            "task_id": tid,
            "body_chars": len(draft.get("body", "") or ""),
            "candidate_count": len(candidates),
            "reconciled_counts": recon.counts(),
        })

    totals = Counter()
    for r in rows:
        for k, v in r["reconciled_counts"].items():
            totals[k] += v
    total_cand = sum(r["candidate_count"] for r in rows)
    # "有效率": candidates that are actionable (new/additive), i.e. would evolve
    # facts, vs merely consistent/unverifiable. "冲突率": conflicting share.
    actionable = totals["new"] + totals["additive"]
    conflict = totals["conflicting"]
    eff = (actionable / total_cand) if total_cand else 0.0
    conflict_rate = (conflict / total_cand) if total_cand else 0.0

    print(f"chapters processed : {len(rows)}")
    print(f"total candidates   : {total_cand}")
    print(f"reconciled totals  : {dict(totals)}")
    print(f"actionable(new+add): {actionable}  有效率={eff:.1%}")
    print(f"conflicting        : {conflict}  冲突率={conflict_rate:.1%}")
    print("\nper-chapter:")
    for r in rows:
        print(f"  {r['task_id']}  body={r['body_chars']:>5}  "
              f"cand={r['candidate_count']}  "
              f"counts={r['reconciled_counts']}")

    # write a machine-readable aggregate next to the other analysis artifacts
    out = {
        "kind": "w12_run_aggregate",
        "run": "RUN-00025",
        "mode": mode,
        "source": source,
        "chapters": len(rows),
        "total_candidates": total_cand,
        "reconciled_totals": dict(totals),
        "actionable_count": actionable,
        "effective_rate": round(eff, 4),
        "conflict_count": conflict,
        "conflict_rate": round(conflict_rate, 4),
        "per_chapter": rows,
    }
    dest = PILOT / "analysis" / f"w12-run00025-aggregate-{mode}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
