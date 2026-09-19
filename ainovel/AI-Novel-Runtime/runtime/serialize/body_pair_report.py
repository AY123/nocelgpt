"""body_pair_report.py — pairwise body comparison for prose revisions."""
from __future__ import annotations

from typing import Iterable

from .serialization_utils import content_hash
from .validation_report import build_short_run_validation_report_from_bodies

BODY_PAIR_REPORT_KIND = "body_pair_validation_report"
BODY_PAIR_REPORT_VERSION = "1.0"


def _content_hash(report: dict) -> str:
    return content_hash(report)


def build_body_pair_validation_report(*, before: Iterable[tuple[str, str]], after: Iterable[tuple[str, str]]) -> dict:
    before_report = build_short_run_validation_report_from_bodies(before)
    after_report = build_short_run_validation_report_from_bodies(after)
    report = {
        "kind": BODY_PAIR_REPORT_KIND,
        "version": BODY_PAIR_REPORT_VERSION,
        "before": before_report,
        "after": after_report,
        "before_verdict": before_report.get("verdict"),
        "after_verdict": after_report.get("verdict"),
        "before_snapshot_count": before_report.get("snapshot_count", 0),
        "after_snapshot_count": after_report.get("snapshot_count", 0),
    }
    report["content_hash"] = _content_hash(report)
    return report
