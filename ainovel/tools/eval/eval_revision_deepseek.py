"""One-off: run the full Revision Controller loop over a real pilot draft with
DeepSeek — judge -> targeted rewrite -> re-judge -> verify improvement. Manual
eval harness, not a test. Uses replay_dir so re-runs don't re-bill.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file: tools/eval/)
sys.path.insert(0, str(ROOT / "AI-Novel-Runtime"))

from runtime.execution.llm_model import LLMExecutionModel
from runtime.execution.quality_center import llm_quality_judge
from runtime.execution.revision import revise_until

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


def main():
    load_env(ROOT / ".env")
    replay = str(PILOT / "registry" / "derived" / "quality-replay")
    judge_model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                                    temperature=0.3, max_tokens=2000,
                                    timeout_seconds=180, replay_dir=replay)
    rewrite_model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                                      temperature=0.6, max_tokens=3000,
                                      timeout_seconds=240, replay_dir=replay)
    judge = llm_quality_judge(judge_model)

    print("=== running revision loop over claude draft (DeepSeek) ===", flush=True)
    result = revise_until(judge, rewrite_model, DRAFT, PACKAGE, max_rounds=2)
    session = result.session

    print(f"\nterminate_reason: {session.terminate_reason}")
    print(f"verdict         : {session.verdict}")
    print(f"gating          : {session.gating}")
    print(f"rounds          : {len(session.rounds)}")
    for rnd in session.rounds:
        print(f"\n--- round {rnd['round']} ---")
        print(f"  targeted: {rnd['targeted_dimensions']}")
        print(f"  hash: {rnd['draft_hash_before'][:20]} -> {rnd['draft_hash_after'][:20]}")
        for d in sorted(set(rnd['scores_before']) | set(rnd['scores_after'])):
            b, a = rnd['scores_before'].get(d), rnd['scores_after'].get(d)
            mark = ""
            if d in rnd.get('improved', []): mark = " IMPROVED"
            elif d in rnd.get('regressed', []): mark = " REGRESSED"
            if b != a:
                print(f"    {d:<24} {b:>3} -> {a:>3}{mark}")

    out = PILOT / "registry" / "derived" / "quality" / "TASK-00001.revision-session.json"
    out.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fin = PILOT / "registry" / "derived" / "quality" / "TASK-00001.revised-draft.json"
    fin.write_text(json.dumps(result.final_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nsession  -> {out.relative_to(ROOT)}")
    print(f"final    -> {fin.relative_to(ROOT)} ({result.final_artifact.get('word_count')} words)")
    print(f"selected  : {session.selected_draft_hash[:24]}")


if __name__ == "__main__":
    main()
