"""baseline_comparison.py — compare baseline freeze artifacts.

This module provides a small, read-side comparison helper for baseline freeze
records so the fixed 2–3 chapter baselines can be compared deterministically.
"""
from __future__ import annotations

from typing import Optional

from .baseline_freeze import load_baseline_freeze_record

COMPARISON_KIND = "baseline_freeze_comparison"
COMPARISON_VERSION = "1.0"


def compare_baseline_freeze_records(left: dict, right: dict) -> dict:
    left_chapters = left.get("chapter_ids", []) or []
    right_chapters = right.get("chapter_ids", []) or []
    left_ids = set(left_chapters)
    right_ids = set(right_chapters)
    overlap = sorted(left_ids & right_ids)
    left_hash = left.get("content_hash")
    right_hash = right.get("content_hash")
    same_content = (left_hash == right_hash) if (left_hash is not None or right_hash is not None) else (
        left_chapters == right_chapters
    )
    return {
        "kind": COMPARISON_KIND,
        "version": COMPARISON_VERSION,
        "left": {
            "baseline_id": left.get("baseline_id"),
            "chapter_count": len(left_chapters),
            "content_hash": left_hash,
            "run_manifest_ref": left.get("run_manifest_ref"),
            "live_baseline_report_ref": left.get("live_baseline_report_ref"),
        },
        "right": {
            "baseline_id": right.get("baseline_id"),
            "chapter_count": len(right_chapters),
            "content_hash": right_hash,
            "run_manifest_ref": right.get("run_manifest_ref"),
            "live_baseline_report_ref": right.get("live_baseline_report_ref"),
        },
        "delta_chapter_count": len(right_chapters) - len(left_chapters),
        "shared_chapter_ids": overlap,
        "same_content_hash": same_content,
        "same_run_manifest_ref": left.get("run_manifest_ref") == right.get("run_manifest_ref"),
        "same_report_ref": left.get("live_baseline_report_ref") == right.get("live_baseline_report_ref"),
    }


def compare_baseline_freeze_paths(project_path, left_id: str, right_id: str) -> Optional[dict]:
    left = load_baseline_freeze_record(project_path, left_id)
    right = load_baseline_freeze_record(project_path, right_id)
    if left is None or right is None:
        return None
    return compare_baseline_freeze_records(left, right)
