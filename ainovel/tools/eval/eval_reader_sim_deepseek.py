"""One-off: run the Reader Simulator (DeepSeek) over the pilot claude draft and
print each persona's verdict + the aggregate. Manual eval harness, not a test.
Reader signals are COMPARISON-ONLY — this single run is illustrative; the real
use is compare_simulations(before, after). Replay-cached so re-runs don't re-bill.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.reader_sim import llm_reader_simulator

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
        replay_dir=str(PILOT / "registry" / "derived" / "reader-sim-replay"))
    sim = llm_reader_simulator(model)

    print("=== reader simulation over claude draft (DeepSeek, comparison-only) ===", flush=True)
    report = sim.review(DRAFT)
    d = report.to_dict()

    print(f"\naxis={d['axis']} gating={d['gating']} comparison_only={d['comparison_only']}")
    print(f"\n{'persona':<10}{'satisf':>8}{'continue':>10}  drop_reason")
    for p in d["personas"]:
        cont = "yes" if p["would_continue"] else "NO"
        reason = p.get("drop_reason", "")[:40]
        print(f"{p['name']:<10}{p['satisfaction']:>8}{cont:>10}  {reason}")

    agg = d["aggregate"]
    print(f"\naggregate: mean_satisfaction={agg['mean_satisfaction']} "
          f"continue_rate={agg['continue_rate']}%")
    print(f"would drop: {agg['drop_personas'] or '(none)'}")
    print(f"common expectations: {agg['common_expectations']}")

    out = PILOT / "registry" / "derived" / "quality" / "TASK-00001.reader-sim.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nsaved -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
