"""baseline_compare_report.py — derived report for baseline comparisons.

This module turns a deterministic comparison between two frozen baselines into a
written derived artifact so the comparison itself becomes auditable.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional

from .. import derived
from .baseline_comparison import compare_baseline_freeze_records
from .baseline_freeze import load_baseline_freeze_record

CATEGORY = "baseline-compare-reports"
REPORT_VERSION = "1.0"
REPORT_KIND = "baseline_compare_report"


def _content_hash(report: dict) -> str:
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_baseline_compare_report(*, left: dict, right: dict, left_path: str, right_path: str) -> dict:
    comparison = compare_baseline_freeze_records(left, right)
    report = {
        "kind": REPORT_KIND,
        "version": REPORT_VERSION,
        "left_path": left_path,
        "right_path": right_path,
        "comparison": comparison,
    }
    report["content_hash"] = _content_hash(report)
    return report


def write_baseline_compare_report(*, project_path, report: dict, report_id: str) -> str:
    rel = derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return rel


def compare_and_write_baseline_report(*, project_path, left_id: str, right_id: str, report_id: str) -> Optional[tuple[dict, str]]:
    left = load_baseline_freeze_record(project_path, left_id)
    right = load_baseline_freeze_record(project_path, right_id)
    if left is None or right is None:
        return None
    left_path = str(Path(project_path) / "registry" / "derived" / "baseline-freezes" / f"{left_id}.json")
    right_path = str(Path(project_path) / "registry" / "derived" / "baseline-freezes" / f"{right_id}.json")
    report = build_baseline_compare_report(left=left, right=right, left_path=left_path, right_path=right_path)
    rel = write_baseline_compare_report(project_path=project_path, report=report, report_id=report_id)
    return report, rel
