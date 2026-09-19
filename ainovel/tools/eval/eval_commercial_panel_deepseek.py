"""One-off: run the v2 COMMERCIAL reader panel (DeepSeek) over the pilot claude
draft and print each pay-behavior persona's continue/pay probability + the
aggregate付费信号. Manual eval harness (roadmap 4.4), not a test.

Like the v1 reader sim, these signals are COMPARISON-ONLY — a single run is
illustrative; the real use is compare_simulations(before, after) inside the
Commercial Loop. Replay-cached so re-runs don't re-bill.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.reader_sim import commercial_reader_simulator

PILOT = ROOT / "novel-pilot"
DRAFT = json.loads((PILOT / "registry" / "derived" / "drafts" / "TASK-00001.claude.json").read_text(encoding="utf-8"))


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


def main():
    load_env(ROOT / ".env")
    model = LLMExecutionModel(
        provider="deepseek", model_id="deepseek-chat",
        temperature=0.4, max_tokens=1500, timeout_seconds=180,
        replay_dir=str(PILOT / "registry" / "derived" / "commercial-panel-replay"))
    sim = commercial_reader_simulator(model)

    print("=== v2 commercial panel over claude draft (DeepSeek, comparison-only) ===", flush=True)
    report = sim.review(DRAFT)
    d = report.to_dict()

    print(f"\naxis={d['axis']} gating={d['gating']} comparison_only={d['comparison_only']}")
    print(f"\n{'persona':<10}{'satisf':>8}{'continue%':>11}{'pay%':>7}  drop_reason")
    for p in d["personas"]:
        cont_p = p.get("continue_probability", "-")
        pay_p = p.get("pay_probability", "-")
        reason = p.get("drop_reason", "")[:36]
        print(f"{p['name']:<10}{p['satisfaction']:>8}{cont_p:>11}{pay_p:>7}  {reason}")

    agg = d["aggregate"]
    print(f"\naggregate: mean_satisfaction={agg['mean_satisfaction']} "
          f"continue_rate={agg['continue_rate']}%")
    if "mean_pay_probability" in agg:
        print(f"mean_continue_probability={agg.get('mean_continue_probability')} "
              f"mean_pay_probability={agg['mean_pay_probability']}")
        print(f"likely to pay: {agg.get('pay_personas') or '(none)'}")
    print(f"would drop: {agg['drop_personas'] or '(none)'}")
    print(f"common expectations: {agg['common_expectations']}")

    out = PILOT / "registry" / "derived" / "quality" / "TASK-00001.commercial-panel.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nsaved -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
