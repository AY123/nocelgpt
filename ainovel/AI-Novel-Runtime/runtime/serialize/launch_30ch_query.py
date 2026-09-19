"""launch_30ch_query.py — read-side query for 30 chapter launch reports."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "30ch-launch-reports"


def list_30ch_launch_reports(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_30ch_launch_report(project_path, report_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, report_id)
