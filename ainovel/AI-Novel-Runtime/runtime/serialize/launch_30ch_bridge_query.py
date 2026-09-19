"""launch_30ch_bridge_query.py — read-side query for 30 chapter launch bridges."""
from __future__ import annotations

from typing import Optional

from .query_utils import list_artifacts, load_artifact

CATEGORY = "30ch-launch-bridges"


def list_30ch_launch_bridges(project_path) -> list[dict]:
    return list_artifacts(project_path, CATEGORY)


def load_30ch_launch_bridge(project_path, bridge_id: str) -> Optional[dict]:
    return load_artifact(project_path, CATEGORY, bridge_id)
