"""ab_cleaning_artifacts.py — derived artifact writer for A/B cleaning."""
from __future__ import annotations

import json

from .. import derived
from .ab_cleaning_flow import build_ab_cleaning_flow

CATEGORY = "ab-cleaning-reports"


def write_ab_cleaning_flow(*, project_path, report_id: str, samples, profiles) -> str:
    report = build_ab_cleaning_flow(samples=samples, profiles=profiles)
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
