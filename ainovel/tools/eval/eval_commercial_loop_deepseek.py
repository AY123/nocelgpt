"""One-off: drive the full Commercial Loop v2 (DeepSeek) over the pilot claude
draft — simulate the commercial panel, rewrite toward the pay/retention plan,
re-simulate, and keep the rewrite ONLY if readers relatively improved AND no
persona newly lost pay intent. Manual eval harness (roadmap 4.4), not a test.

This exercises the GUARD on real prose: can a rewrite lift the mean-pay baseline
without tripping a newly_pay_lost rejection? The loop is comparison-only and
never gates. Replay-cached (sim + rewrite in separate buckets) so re-runs don't
re-bill.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.reader_sim import commercial_reader_simulator
from runtime.execution.commercial import optimize_commercial

PILOT = ROOT / "novel-pilot"
DRAFT = json.loads((PILOT / "registry" / "derived" / "drafts" / "TASK-00001.claude.json").read_text(encoding="utf-8"))
# rewrite_once only reads package.context (setting bindings) + package.task; the
# pilot draft carries its own body, so a minimal package is faithful enough.
PACKAGE = {"task": {"task_id": DRAFT.get("task_id", "TASK-00001")}, "context": {}}


def load_env(path: Path):
    if not path.is_file():
        return
    import os
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def _model(bucket: str, temperature: float):
    return LLMExecutionModel(
        provider="deepseek", model_id="deepseek-chat",
        temperature=temperature, max_tokens=3000, timeout_seconds=180,
        replay_dir=str(PILOT / "registry" / "derived" / f"commercial-loop-{bucket}-replay"))


def main():
    load_env(ROOT / ".env")
    simulator = commercial_reader_simulator(_model("sim", 0.4))
    rewrite_model = _model("rewrite", 0.7)

    print("=== commercial loop v2 over claude draft (DeepSeek, comparison-only) ===", flush=True)
    result = optimize_commercial(simulator, rewrite_model, DRAFT, PACKAGE, max_rounds=2)
    session = result.session.to_dict()

    print(f"\ngating={session['gating']} comparison_only={session['comparison_only']}")
    print(f"verdict={session['verdict']} terminate_reason={session['terminate_reason']}")
    print(f"initial draft: {DRAFT.get('content_hash','')[:24]}")
    print(f"selected     : {session['selected_draft_hash'][:24]}"
          f"  ({'REWRITE kept' if session['selected_draft_hash'] != DRAFT.get('content_hash') else 'original kept'})")

    for r in session["rounds"]:
        acc = "accepted" if r["accepted"] else "rejected"
        line = f"\nround {r['round']}: reader={r['reader_verdict']} [{acc}]"
        if not r.get("degraded"):
            line += f"  Δsatisfaction={r.get('mean_satisfaction_delta',0):+d}"
            line += f"  Δcontinue={r.get('continue_rate_delta',0):+d}"
            if "mean_pay_probability_delta" in r:
                line += f"  Δpay={r['mean_pay_probability_delta']:+d}"
            if r.get("newly_dropped"):
                line += f"  newly_dropped={r['newly_dropped']}"
            if r.get("newly_pay_lost"):
                line += f"  newly_pay_lost={r['newly_pay_lost']}"
        print(line)

    # final panel snapshot (comparison anchor, not an absolute score)
    agg = result.final_simulation.get("aggregate", {})
    print(f"\nfinal panel: mean_satisfaction={agg.get('mean_satisfaction')} "
          f"mean_pay_probability={agg.get('mean_pay_probability')} "
          f"pay_personas={agg.get('pay_personas')}")

    out = PILOT / "registry" / "derived" / "quality" / "TASK-00001.commercial-loop.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"session": session,
                               "final_simulation": result.final_simulation},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nsaved -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
