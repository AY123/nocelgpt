"""baseline_query.py — read-side query for baseline reports."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "baseline-reports"


def list_baseline_reports(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_baseline_report(project_path, report_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, report_id)
