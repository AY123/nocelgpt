"""launch_30ch_summary_query.py — read-side query for 30 chapter launch summaries."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "30ch-launch-summaries"


def list_30ch_launch_summaries(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_30ch_launch_summary(project_path, summary_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, summary_id)
