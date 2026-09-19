"""One-off: run the Novel Quality Center LLM judge (DeepSeek) over the two
existing pilot drafts and print a side-by-side comparison. Not a test — a
manual eval harness. Uses replay_dir so re-runs don't re-bill.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
RUNTIME = ROOT / "AI-Novel-Runtime"
sys.path.insert(0, str(RUNTIME))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.quality_center import llm_quality_judge

PILOT = ROOT / "novel-pilot"
PACKAGE = json.loads((PILOT / "build" / "TASK-00001.package.json").read_text(encoding="utf-8"))
DRAFTS = {
    "claude": PILOT / "registry" / "derived" / "drafts" / "TASK-00001.claude.json",
    "gpt": PILOT / "registry" / "derived" / "drafts" / "TASK-00001.gpt.json",
}


def load_env(path: Path):
    if not path.is_file():
        return
    import os
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip("'\"")
        os.environ.setdefault(k.strip(), v)


def main():
    load_env(ROOT / ".env")
    model = LLMExecutionModel(
        provider="deepseek",
        model_id="deepseek-chat",
        temperature=0.3,
        max_tokens=2000,
        timeout_seconds=180,
        replay_dir=str(PILOT / "registry" / "derived" / "quality-replay"),
    )
    judge = llm_quality_judge(model)

    reports = {}
    for name, path in DRAFTS.items():
        draft = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n=== judging {name} draft ({draft.get('word_count','?')} words) ===",
              flush=True)
        report = judge.review(draft, PACKAGE)
        reports[name] = report.to_dict()
        out = PILOT / "registry" / "derived" / "quality" / f"TASK-00001.{name}.quality.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        prov = report.judge_provenance or {}
        print(f"parse_ok={prov.get('parse_ok')} degraded={prov.get('degraded')}", flush=True)
        print("scores:", json.dumps(report.scores, ensure_ascii=False), flush=True)

    # side-by-side
    print("\n=== SIDE BY SIDE ===")
    dims = list(next(iter(reports.values()))["scores"].keys())
    header = f"{'dimension':<24}" + "".join(f"{n:>10}" for n in reports)
    print(header)
    for d in dims:
        row = f"{d:<24}" + "".join(f"{reports[n]['scores'].get(d,''):>10}" for n in reports)
        print(row)
    for name, rep in reports.items():
        print(f"\n--- {name} revision_plan ---")
        for item in rep.get("revision_plan", []):
            print(f"  [{item.get('priority','-')}] {item.get('dimension')}: {item.get('action')}")
        preds = rep.get("predictions") or {}
        if preds:
            print(f"  predictions (comparison-only, non-gating): "
                  f"sub={preds.get('subscription')} ret={preds.get('retention')} "
                  f"sat={preds.get('reader_satisfaction')}")


if __name__ == "__main__":
    main()
