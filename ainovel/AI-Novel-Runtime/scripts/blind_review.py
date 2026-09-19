"""blind_review.py — REAL-human blind A/B review of W10 packets (CLOSE-08~11).

Shows a reviewer version_A and version_B of a chapter (provenance hidden: one is
the original, one is the automatic revision) and records winner (A / B / tie),
confidence, reason codes, and notes into each packet's human_result. The unblind
key stays sealed until aggregation (scripts/blind_unblind.py).

DISCIPLINE (hard):
  - REAL humans only. AI must not pick winners here (same-source bias, the W9
    lesson). No AI stand-in writes human_result.
  - The tool never reveals which arm is which; it only shows A/B text.
  - Two-arm review (original vs automatic_revision), per the accepted plan
    deviation — human_revision arm does not exist and is not faked.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/blind_review.py --reviewer <name> --batch W10-B01
  PYTHONPATH=. python3 scripts/blind_review.py --reviewer <name> --all
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
PKG = RT / "quality-golden-set" / "w10-blind-package"

VALID_REASONS = (
    "improves_hook", "improves_continuity", "fixes_padding", "fixes_ai_voice",
    "fixes_conflict", "introduces_regression", "no_net_gain",
)
WINNER_MAP = {"a": "A", "b": "B", "t": "tie", "tie": "tie", "A": "A", "B": "B"}
CONFIDENCE = {"l": "low", "m": "medium", "h": "high",
              "low": "low", "medium": "medium", "high": "high"}


def _packets(args) -> list[Path]:
    allp = sorted(PKG.glob("packet-QGS-*.json"))
    if args.all:
        return allp
    if args.batch:
        return [p for p in allp
                if json.loads(p.read_text(encoding="utf-8")).get("batch_id") == args.batch]
    out = []
    for cid in args.candidates:
        p = PKG / f"packet-{cid}.json"
        if p.is_file():
            out.append(p)
        else:
            print(f"跳过 {cid}: 无 packet 文件")
    return out


def _prompt_winner() -> str:
    while True:
        raw = input("  哪个更像好的商业网文章节？ [A / B / tie]: ").strip().lower()
        if raw in WINNER_MAP:
            return WINNER_MAP[raw]
        print("    请输入 A、B 或 tie。")


def _prompt_confidence() -> str:
    while True:
        raw = input("  置信度 [low / medium / high]: ").strip().lower()
        if raw in CONFIDENCE:
            return CONFIDENCE[raw]
        print("    请输入 low / medium / high。")


def _prompt_reasons() -> list[str]:
    print("  理由码（逗号分隔，可留空）:")
    for i, r in enumerate(VALID_REASONS, 1):
        print(f"    {i}. {r}")
    while True:
        raw = input("  选择（编号或名称，逗号分隔）: ").strip()
        if not raw:
            return []
        picks = [x.strip() for x in raw.split(",") if x.strip()]
        out = []
        ok = True
        for p in picks:
            if p.isdigit() and 1 <= int(p) <= len(VALID_REASONS):
                out.append(VALID_REASONS[int(p) - 1])
            elif p in VALID_REASONS:
                out.append(p)
            else:
                print(f"    无效理由码: {p}")
                ok = False
                break
        if ok:
            return out


def review_packet(packet_path: Path, reviewer: str, *, force: bool) -> bool:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    result = packet.get("human_result") or {}
    if result.get("winner") and not force:
        print(f"[{packet['candidate_id']}] 已评（winner={result['winner']}，"
              f"by {result.get('_reviewer')}）。用 --force 覆盖，否则跳过。")
        return False

    print("\n" + "=" * 72)
    print(f"{packet['candidate_id']}  批次 {packet['batch_id']}  评审者 '{reviewer}'")
    print("=" * 72)
    print(packet.get("instruction", ""))
    print("\n" + "-" * 30 + " VERSION A " + "-" * 30)
    print((packet.get("version_A") or {}).get("text", "").strip()[:4500])
    print("\n" + "-" * 30 + " VERSION B " + "-" * 30)
    print((packet.get("version_B") or {}).get("text", "").strip()[:4500])
    print("\n" + "-" * 72)

    winner = _prompt_winner()
    confidence = _prompt_confidence()
    reasons = _prompt_reasons()
    notes = input("  备注（可留空）: ").strip()

    packet["human_result"] = {
        "winner": winner,
        "confidence": confidence,
        "reason_codes": reasons,
        "notes": notes,
        "_reviewer": reviewer,
        "_reviewed_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"[{packet['candidate_id']}] 已记录 winner={winner} ({confidence})。")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="真人双臂盲评（CLOSE-08~11）")
    ap.add_argument("--reviewer", required=True, help="评审者标识（进入审计）")
    ap.add_argument("--batch", help="只评某批次，如 W10-B01")
    ap.add_argument("--all", action="store_true", help="评全部 packet")
    ap.add_argument("--force", action="store_true", help="覆盖已评结果")
    ap.add_argument("candidates", nargs="*", help="候选 id，如 QGS-00001")
    args = ap.parse_args()

    if not args.all and not args.batch and not args.candidates:
        ap.error("提供候选 id、--batch，或 --all")

    packets = _packets(args)
    if not packets:
        print("没有可评的 packet。")
        return 1
    done = 0
    for p in packets:
        try:
            if review_packet(p, args.reviewer, force=args.force):
                done += 1
        except (KeyboardInterrupt, EOFError):
            print("\n中断，已保存之前的评审。")
            break
    print(f"\n完成：评审 {done}/{len(packets)} 个 packet。揭盲聚合用 scripts/blind_unblind.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
