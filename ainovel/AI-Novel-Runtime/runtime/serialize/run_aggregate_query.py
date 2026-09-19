"""run_aggregate_query.py — read-side query for run aggregates."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "run-aggregates"


def list_run_aggregates(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_run_aggregate(project_path, aggregate_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, aggregate_id)
