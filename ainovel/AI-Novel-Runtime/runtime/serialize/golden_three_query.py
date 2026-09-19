"""golden_three_query.py — read-side query for golden three review records."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "golden-three-review-records"


def list_golden_three_review_records(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_golden_three_review_record(project_path, record_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, record_id)
