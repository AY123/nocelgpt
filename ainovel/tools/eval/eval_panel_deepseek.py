"""One-off: run the multi-model review PANEL over a real pilot draft.

You only have a live DeepSeek key (OpenAI/Anthropic/Gemini are placeholders), so
this uses DeepSeek for every seat but with DIFFERENT role_focus prompts — enough
to prove independent scoring + weighted synthesis + disagreement surfacing. When
real Claude/GPT/Gemini keys exist, swap the per-role model and nothing else
changes. Replay-cached; not a test.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.review_panel import build_review_panel

PILOT = ROOT / "novel-pilot"
PACKAGE = json.loads((PILOT / "build" / "TASK-00001.package.json").read_text(encoding="utf-8"))
DRAFT = json.loads((PILOT / "registry" / "derived" / "drafts" / "TASK-00001.claude.json").read_text(encoding="utf-8"))


def load_env(path):
    if not path.is_file():
        return
    import os
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def mk(role):
    # distinct replay bucket per role so each seat caches independently
    return LLMExecutionModel(
        provider="deepseek", model_id="deepseek-chat",
        temperature=0.3, max_tokens=2000, timeout_seconds=180,
        replay_dir=str(PILOT / "registry" / "derived" / f"panel-replay-{role}"),
    )


def main():
    load_env(ROOT / ".env")
    panel = build_review_panel({
        "literary": mk("literary"),
        "structural": mk("structural"),
        "commercial": mk("commercial"),
        "logic": mk("logic"),
    })
    print("=== running 4-seat review panel (DeepSeek multi-role) ===", flush=True)
    report = panel.review(DRAFT, PACKAGE)
    d = report.to_dict()

    print("\n--- per-panelist scores ---")
    dims = list(report.scores.keys())
    header = f"{'dimension':<24}" + "".join(f"{p['role'][:8]:>10}" for p in d["panel"]["panelists"]) + f"{'CONSENSUS':>11}"
    print(header)
    for dim in dims:
        row = f"{dim:<24}"
        for p in d["panel"]["panelists"]:
            row += f"{p['scores'].get(dim,''):>10}"
        row += f"{report.scores[dim]:>11}"
        print(row)

    print("\n--- disagreement (spread across seats) ---")
    for dim, spread in sorted(d["panel"]["disagreement"].items(), key=lambda x: -x[1]):
        flag = "  <-- high" if spread >= 25 else ""
        print(f"  {dim:<24}{spread:>4}{flag}")

    print("\n--- consensus revision_plan (union) ---")
    for item in report.revision_plan:
        print(f"  [{item.get('priority','-')}] {item.get('dimension')}: {item.get('action')}")

    out = PILOT / "registry" / "derived" / "quality" / "TASK-00001.panel.json"
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nconsensus -> {out.relative_to(ROOT)}")
    print(f"degraded  : {report.judge_provenance['degraded']} | gating: {report.gating}")


if __name__ == "__main__":
    main()
