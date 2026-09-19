"""winner_drift_query.py — read-side query for winner drift reports."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "winner-drift-reports"


def list_winner_drift_reports(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_winner_drift_report(project_path, report_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, report_id)
