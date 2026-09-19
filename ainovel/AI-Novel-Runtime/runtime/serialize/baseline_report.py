"""baseline_report.py — first-pass baseline report for week 4."""
from __future__ import annotations

from typing import Iterable

from .golden_three import build_golden_three_review_pack
from .serialization_utils import content_hash
from .winner_drift import build_winner_drift_report

BASELINE_REPORT_KIND = "baseline_report"
BASELINE_REPORT_VERSION = "1.0"


def build_baseline_report(*, chapters: Iterable[tuple[str, str]], reviewers: Iterable[str],
                          winner_scored_hash: str = "", winner_written_hash: str = "",
                          winner_scored_id: str = "", winner_written_id: str = "",
                          notes: str = "") -> dict:
    chapters = list(chapters)
    pack = build_golden_three_review_pack(chapters=chapters[:3])
    winner = None
    if winner_scored_id or winner_written_id:
        winner = build_winner_drift_report(
            scored_hash=winner_scored_hash,
            written_hash=winner_written_hash,
            scored_id=winner_scored_id,
            written_id=winner_written_id,
            notes=notes,
        )
    report = {
        "kind": BASELINE_REPORT_KIND,
        "version": BASELINE_REPORT_VERSION,
        "chapter_count": len(chapters),
        "chapter_ids": [cid for cid, _ in chapters],
        "pack": pack,
        "winner_drift": winner,
        "reviewers": list(reviewers),
        "notes": notes,
    }
    report["content_hash"] = content_hash(report)
    return report
