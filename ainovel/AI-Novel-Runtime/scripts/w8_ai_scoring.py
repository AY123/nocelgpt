"""w8_ai_scoring.py — walk the W8-03 double-review + adjudication flow with AI.

Simulates the human scoring step (W8-03): two AI "editors" independently score a
golden-set sample across the 12 calibration dimensions (1–5), disagreements are
adjudicated, and a consensus is formed — mirroring the shape of human_scores.json.

DISCIPLINE (hard):
  - Writes ONLY ai_scores.json in each sample dir. NEVER touches human_scores.json
    — that file is the real ground-truth slot these AI scores stand in FOR while
    real human review is pending. This proves the pipeline end-to-end, it is NOT a
    substitute for real human calibration.
  - LLM calls are replay-cached (serial-replay-w8score-gen) → re-runs are free.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/w8_ai_scoring.py [N]   # N samples, default 3
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
GSET = RT / "quality-golden-set" / "samples"
REPLAY = RT.parent / "genesis-pilot" / "registry" / "derived" / "serial-replay-w8score-gen"

DIMS = (
    "opening_hook", "chapter_goal", "conflict_progression", "character_motivation",
    "emotion_flow", "information_density", "payoff_delivery", "ending_hook",
    "continuity", "ai_voice_risk", "paying_intent", "continue_intent",
)
DIM_CN = {
    "opening_hook": "开篇钩子", "chapter_goal": "章节目标", "conflict_progression": "冲突推进",
    "character_motivation": "角色动机", "emotion_flow": "情绪流动", "information_density": "信息密度",
    "payoff_delivery": "兑现交付", "ending_hook": "结尾钩子", "continuity": "连贯性",
    "ai_voice_risk": "AI腔风险(越高越像AI)", "paying_intent": "付费意愿", "continue_intent": "追读意愿",
}
ADJUDICATE_DELTA = 2  # |a-b| >= this on a dimension → needs adjudication


def _load_env() -> None:
    for f in (RT.parent / "genesis-pilot" / ".env", RT.parent / ".env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _editor_prompt(body: str, persona: str) -> str:
    dim_lines = "\n".join(f"  - {d} ({DIM_CN[d]})" for d in DIMS)
    return (
        f"你是一名{persona}。请对下面这段中文小说章节正文，就 12 个维度各打一个 1–5 的整数分"
        f"（1=很差，5=很好；注意 ai_voice_risk 是「越高越像 AI 腔、越差」）。\n"
        f"维度：\n{dim_lines}\n\n"
        f"只输出一个 JSON 对象，键是上面的英文维度名，值是 1–5 整数，外加一个 "
        f"\"note\" 字段（一句话中文点评）。不要输出别的。\n\n"
        f"正文：\n{body}\n"
    )


def _parse_scores(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in model output")
    obj = json.loads(m.group(0))
    out = {}
    for d in DIMS:
        v = obj.get(d)
        if not isinstance(v, (int, float)):
            raise ValueError(f"missing/invalid dimension {d}: {v!r}")
        out[d] = max(1, min(5, int(round(v))))
    out["_note"] = str(obj.get("note", ""))[:200]
    return out


def _score_as(model, body: str, persona: str) -> dict:
    out = model.generate(_editor_prompt(body, persona))
    return _parse_scores(out.text)


def _adjudicate(a: dict, b: dict) -> tuple[dict, list[str]]:
    """Form consensus. Agreeing dims → mean (rounded). Dims differing by >=
    ADJUDICATE_DELTA are flagged and resolved to the rounded mean (a stand-in for
    a third-reviewer arbitration)."""
    consensus, disputed = {}, []
    for d in DIMS:
        va, vb = a[d], b[d]
        if abs(va - vb) >= ADJUDICATE_DELTA:
            disputed.append(d)
        consensus[d] = int(round((va + vb) / 2))
    return consensus, disputed


def main() -> None:
    _load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY not set — cannot run AI scoring")
    from runtime.execution.llm_model import LLMExecutionModel

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                              temperature=0.0, replay_dir=str(REPLAY))

    # only samples that actually have a body (empty seed dirs QGS-004..010 skipped)
    dirs = [d for d in sorted(GSET.glob("QGS-*")) if (d / "body.txt").is_file()][:n]
    print(f"AI-scoring {len(dirs)} samples (persona A=严格市场编辑, B=资深文学编辑)\n")

    written = 0
    for sd in dirs:
        body = (sd / "body.txt").read_text(encoding="utf-8")
        ed_a = _score_as(model, body, "严格的商业网文主编，看重钩子/付费/追读")
        ed_b = _score_as(model, body, "资深文学编辑，看重人物动机/情绪/连贯")
        consensus, disputed = _adjudicate(ed_a, ed_b)
        # decision on how the sample may be used (mirror human_scores.final_judgement)
        deltas = [abs(ed_a[d] - ed_b[d]) for d in DIMS]
        agreement = sum(1 for x in deltas if x <= 1) / len(DIMS)
        payload = {
            "_source": "AI-simulated (deepseek-chat, temp=0) — NOT human ground truth",
            "editor_a": {d: ed_a[d] for d in DIMS},
            "editor_b": {d: ed_b[d] for d in DIMS},
            "editor_a_note": ed_a.get("_note", ""),
            "editor_b_note": ed_b.get("_note", ""),
            "consensus_scores": consensus,
            "disputed_dimensions": disputed,
            "agreement_rate": round(agreement, 3),
            "final_judgement": "use_for_pipeline_validation_only",
        }
        (sd / "ai_scores.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
        print(f"  {sd.name}: agreement={agreement:.0%}  disputed={disputed or '—'}")

    print(f"\nwrote ai_scores.json to {written} samples "
          f"(human_scores.json untouched)")


if __name__ == "__main__":
    main()
