"""winner_drift_artifacts.py — derived artifact writer for winner drift reports."""
from __future__ import annotations

import json

from .. import derived
from .winner_drift import build_winner_drift_report

CATEGORY = "winner-drift-reports"


def write_winner_drift_report(*, project_path, report_id: str, scored_hash: str, written_hash: str,
                              scored_id: str, written_id: str, evidence_ref: str = "", notes: str = "") -> str:
    report = build_winner_drift_report(
        scored_hash=scored_hash,
        written_hash=written_hash,
        scored_id=scored_id,
        written_id=written_id,
        evidence_ref=evidence_ref,
        notes=notes,
    )
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
