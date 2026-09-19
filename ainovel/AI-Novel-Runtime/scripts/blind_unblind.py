"""blind_unblind.py — unblind W10 human A/B results and decide the auto-revision
policy (CLOSE-10).

Reads each packet's human_result (winner A/B/tie) + the sealed _UNBLIND_KEY.json
(which of A/B is original vs automatic_revision), translates each blind pick into
an ARM winner, then computes the automatic-revision net win rate and regression
rate and emits a retain / restrict / disable decision record into
metadata/w10-blind-review-comparison-results.json.

DISCIPLINE:
  - Deterministic tally; never invents a verdict for an unreviewed packet.
  - Advisory instrument deltas in the key are NOT used to pick winners (the human
    A/B call is authoritative); they are carried through for context only.
  - Two-arm review (original vs automatic_revision); the human_revision arm is
    absent by accepted plan deviation.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/blind_unblind.py            # aggregate + write
  PYTHONPATH=. python3 scripts/blind_unblind.py --dry-run  # print, do not write
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
PKG = RT / "quality-golden-set" / "w10-blind-package"
META = RT / "quality-golden-set" / "metadata"
RESULTS = META / "w10-blind-review-comparison-results.json"

# policy thresholds (advisory; documented so the decision is explainable)
RETAIN_MIN_NET = 0.15      # auto wins − auto losses, as a fraction of reviewed
RESTRICT_MIN_NET = 0.0     # non-negative but weak → restrict to safe cases
MAX_REGRESSION = 0.20      # fraction of packets where auto introduced a regression


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _arm_winner(blind_winner: str, entry: dict) -> str:
    """Translate a blind A/B/tie pick into an arm winner using the unblind map.
    entry has version_A / version_B in {'original','automatic_revision'}."""
    if blind_winner == "tie":
        return "tie"
    side = "version_A" if blind_winner == "A" else "version_B"
    return entry.get(side, "unknown")


def aggregate() -> dict:
    key = _load(PKG / "_UNBLIND_KEY.json")
    kmap = key.get("map") or {}
    rows = []
    for pkt_path in sorted(PKG.glob("packet-QGS-*.json")):
        pkt = _load(pkt_path)
        cid = pkt.get("candidate_id")
        res = pkt.get("human_result") or {}
        winner = res.get("winner")
        if not winner:
            continue  # not reviewed yet — never invent a verdict
        entry = kmap.get(cid) or {}
        arm = _arm_winner(winner, entry)
        rows.append({
            "candidate_id": cid,
            "batch_id": pkt.get("batch_id"),
            "blind_winner": winner,
            "arm_winner": arm,
            "confidence": res.get("confidence"),
            "reason_codes": res.get("reason_codes") or [],
            "reviewer": res.get("_reviewer"),
            "reviewed_at": res.get("_reviewed_at"),
        })

    reviewed = len(rows)
    auto_wins = sum(1 for r in rows if r["arm_winner"] == "automatic_revision")
    orig_wins = sum(1 for r in rows if r["arm_winner"] == "original")
    ties = sum(1 for r in rows if r["arm_winner"] == "tie")
    regressions = sum(1 for r in rows if "introduces_regression" in r["reason_codes"])

    net = (auto_wins - orig_wins) / reviewed if reviewed else 0.0
    regression_rate = regressions / reviewed if reviewed else 0.0

    if reviewed == 0:
        decision, rationale = "insufficient_data", "无已评 packet，无法给出结论。"
    elif regression_rate > MAX_REGRESSION:
        decision = "restrict"
        rationale = (f"回归率 {regression_rate:.0%} 超过阈值 {MAX_REGRESSION:.0%}，"
                     f"自动修订仅在无回归风险的场景启用。")
    elif net >= RETAIN_MIN_NET:
        decision = "retain"
        rationale = (f"自动修订净胜率 {net:+.0%}（auto {auto_wins} / orig {orig_wins} / "
                     f"tie {ties}），回归率 {regression_rate:.0%}，达到保留阈值。")
    elif net >= RESTRICT_MIN_NET:
        decision = "restrict"
        rationale = (f"净胜率 {net:+.0%} 非负但弱，限制在可获益场景使用。")
    else:
        decision = "disable"
        rationale = (f"净胜率 {net:+.0%} 为负（auto {auto_wins} / orig {orig_wins}），"
                     f"自动修订无净收益，默认链路禁用。")

    return {
        "reviewed_count": reviewed,
        "total_packets": len(list(PKG.glob("packet-QGS-*.json"))),
        "auto_wins": auto_wins,
        "original_wins": orig_wins,
        "ties": ties,
        "regression_count": regressions,
        "net_win_rate": round(net, 4),
        "regression_rate": round(regression_rate, 4),
        "decision": decision,
        "rationale": rationale,
        "per_candidate": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="W10 揭盲聚合与策略结论（CLOSE-10）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写结果文件")
    args = ap.parse_args()

    agg = aggregate()
    print(json.dumps({k: v for k, v in agg.items() if k != "per_candidate"},
                     ensure_ascii=False, indent=2))
    if agg["reviewed_count"] < agg["total_packets"]:
        print(f"\n注意：仅 {agg['reviewed_count']}/{agg['total_packets']} 个 packet 已评，"
              f"结论为阶段性。")

    if args.dry_run:
        print("\n[dry-run] 未写入结果文件。")
        return 0

    existing = _load(RESULTS)
    existing.update({
        "status": "aggregated" if agg["reviewed_count"] else "awaiting_human_review",
        "review_type": "two_way_original_vs_automatic",
        "aggregate": {k: v for k, v in agg.items() if k != "per_candidate"},
        "per_candidate": agg["per_candidate"],
        "decision_record": {
            "decision": agg["decision"],
            "rationale": agg["rationale"],
            "aggregated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    })
    RESULTS.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"\n已写入 {RESULTS.name}：decision={agg['decision']}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
