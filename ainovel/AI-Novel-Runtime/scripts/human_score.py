"""human_score.py — interactive REAL-human scoring of golden-set samples (CLOSE-05).

One reviewer scores one sample's 12 calibration dimensions (1–5, per
metadata/editor-guide.md), writing into human_scores.json's editor_a OR editor_b
slot WITH reviewer identity + timestamp so the calibration ground truth is
auditable (身份/时间/独立性可审计 — the CLOSE-05 acceptance criterion).

DISCIPLINE (hard):
  - This is for REAL humans. Do NOT drive it with an AI to fill editor_a/editor_b
    — that reintroduces the self-referential / same-source inflation W9 just fixed.
    AI stand-in scoring has its own separate tool (scripts/w8_ai_scoring.py →
    ai_scores.json) and never lands here.
  - Two DISTINCT reviewers must fill editor_a and editor_b independently. The tool
    refuses to let one reviewer id fill both slots of the same sample.
  - Scale is 1–5 (matches the AI-judge reviewer side, so MAE is meaningful).

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/human_score.py --reviewer <name> --slot editor_a QGS-00001
  PYTHONPATH=. python3 scripts/human_score.py --reviewer <name> --slot editor_b --all
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
SAMPLES = RT / "quality-golden-set" / "samples"

DIMENSIONS = (
    "opening_hook", "chapter_goal", "conflict_progression", "character_motivation",
    "emotion_flow", "information_density", "payoff_delivery", "ending_hook",
    "continuity", "ai_voice_risk", "paying_intent", "continue_intent",
)

DIM_HINT = {
    "opening_hook": "开篇钩子强度",
    "chapter_goal": "本章目标是否清晰",
    "conflict_progression": "冲突是否真实推进",
    "character_motivation": "角色动机是否可信",
    "emotion_flow": "情绪流动是否自然",
    "information_density": "信息密度（过低=水，过高=堵）",
    "payoff_delivery": "回报/爽点是否兑现",
    "ending_hook": "章末钩子拉力",
    "continuity": "连续性/前后一致",
    "ai_voice_risk": "AI 腔风险（5=几乎无 AI 味，1=严重）",
    "paying_intent": "付费意愿",
    "continue_intent": "追读意愿",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _prompt_score(dim: str) -> int:
    while True:
        raw = input(f"  {dim} — {DIM_HINT[dim]} [1-5]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("    请输入 1-5 的整数。")


def _sample_dirs(args) -> list[Path]:
    if args.all:
        return sorted(d for d in SAMPLES.glob("QGS-*")
                      if (d / "body.txt").is_file())
    out = []
    for sid in args.samples:
        d = SAMPLES / sid
        if not (d / "body.txt").is_file():
            print(f"跳过 {sid}: 无 body.txt（可能是 skeleton seed）")
            continue
        out.append(d)
    return out


def score_sample(sample_dir: Path, reviewer: str, slot: str, *, force: bool) -> bool:
    """Interactively score one sample into the given editor slot. Returns True if
    written, False if skipped. Never fills both slots with the same reviewer id."""
    hs_path = sample_dir / "human_scores.json"
    hs = _load(hs_path)
    other = "editor_b" if slot == "editor_a" else "editor_a"
    other_block = hs.get(other) or {}
    if isinstance(other_block, dict) and other_block.get("_reviewer") == reviewer:
        print(f"[{sample_dir.name}] 拒绝：评审者 '{reviewer}' 已填了 {other} 槽，"
              f"两槽必须由两个不同的人独立评分。")
        return False
    existing = hs.get(slot)
    if isinstance(existing, dict) and existing.get("_reviewer") and not force:
        print(f"[{sample_dir.name}] {slot} 已由 '{existing.get('_reviewer')}' 于 "
              f"{existing.get('_scored_at')} 填写。用 --force 覆盖，否则跳过。")
        return False

    body = (sample_dir / "body.txt").read_text(encoding="utf-8")
    notes = sample_dir / "notes.md"
    print("\n" + "=" * 72)
    print(f"样本 {sample_dir.name}  →  评审者 '{reviewer}'  槽 {slot}")
    print("=" * 72)
    print(body.strip()[:4000])
    if notes.is_file():
        print("\n--- 评审说明 (notes.md) ---")
        print(notes.read_text(encoding="utf-8").strip()[:1500])
    print("\n--- 打分 (1-5, 见 metadata/editor-guide.md) ---")

    scores = {dim: _prompt_score(dim) for dim in DIMENSIONS}
    scores["_reviewer"] = reviewer
    scores["_scored_at"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

    hs[slot] = scores
    hs_path.write_text(json.dumps(hs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[{sample_dir.name}] 已写入 {slot}（评审者 {reviewer}）。")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="真人金样集打分（CLOSE-05）")
    ap.add_argument("--reviewer", required=True, help="评审者标识（真人姓名/工号，进入审计）")
    ap.add_argument("--slot", required=True, choices=["editor_a", "editor_b"],
                    help="写入哪个编辑槽；两槽须由两个不同的人各填一次")
    ap.add_argument("--all", action="store_true", help="对全部有正文的样本依次打分")
    ap.add_argument("--force", action="store_true", help="覆盖该槽已有评分")
    ap.add_argument("samples", nargs="*", help="样本 id，如 QGS-00001（未加 --all 时必填）")
    args = ap.parse_args()

    if not args.all and not args.samples:
        ap.error("提供样本 id 或使用 --all")

    dirs = _sample_dirs(args)
    if not dirs:
        print("没有可打分的样本。")
        return 1
    written = 0
    for d in dirs:
        try:
            if score_sample(d, args.reviewer, args.slot, force=args.force):
                written += 1
        except (KeyboardInterrupt, EOFError):
            print("\n中断，已保存之前的样本。")
            break
    print(f"\n完成：写入 {written}/{len(dirs)} 个样本的 {args.slot}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
