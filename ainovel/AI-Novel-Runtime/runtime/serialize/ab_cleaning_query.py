"""ab_cleaning_query.py — read-side query for A/B cleaning reports."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "ab-cleaning-reports"


def list_ab_cleaning_reports(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_ab_cleaning_report(project_path, report_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, report_id)
