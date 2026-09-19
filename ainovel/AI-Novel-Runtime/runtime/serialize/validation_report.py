"""validation_report.py — short-run validation summary.

This helper turns a small set of chapter quality snapshots into a read-side
summary so the 2–3 chapter short-run can be described as a coherent validation
artifact.
"""
from __future__ import annotations

from typing import Iterable

from .quality_snapshot import compare_quality_snapshots, build_quality_snapshot
from .serialization_utils import content_hash

VALIDATION_REPORT_KIND = "short_run_validation_report"
VALIDATION_REPORT_VERSION = "1.0"


def _content_hash(report: dict) -> str:
    return content_hash(report)


def build_short_run_validation_report(snapshots: Iterable[dict]) -> dict:
    snapshots = list(snapshots)
    comparisons = []
    for left, right in zip(snapshots, snapshots[1:]):
        comparisons.append(compare_quality_snapshots(left, right))
    report = {
        "kind": VALIDATION_REPORT_KIND,
        "version": VALIDATION_REPORT_VERSION,
        "snapshot_count": len(snapshots),
        "chapter_ids": [s.get("chapter_id") for s in snapshots],
        "comparisons": comparisons,
        "warning_counts": [s.get("warning_count", 0) for s in snapshots],
        "lengths": [s.get("length", {}) for s in snapshots],
        "languages": [s.get("language", {}) for s in snapshots],
        "verdict": (
            "improved" if comparisons and all(c.get("verdict") == "improved" for c in comparisons)
            else "mixed" if comparisons else "single"
        ),
    }
    report["content_hash"] = _content_hash(report)
    return report


def build_short_run_validation_report_from_bodies(chapters: Iterable[tuple[str, str]]) -> dict:
    snapshots = [build_quality_snapshot(chapter_id=chapter_id, body=body) for chapter_id, body in chapters]
    return build_short_run_validation_report(snapshots)
