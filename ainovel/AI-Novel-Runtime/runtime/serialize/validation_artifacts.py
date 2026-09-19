"""validation_artifacts.py — derived artifact writer for short-run validation."""
from __future__ import annotations

import json

from .. import derived
from .validation_report import build_short_run_validation_report

CATEGORY = "short-run-validation-reports"


def write_short_run_validation_report(*, project_path, report_id: str, snapshots: list[dict]) -> str:
    report = build_short_run_validation_report(snapshots)
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
