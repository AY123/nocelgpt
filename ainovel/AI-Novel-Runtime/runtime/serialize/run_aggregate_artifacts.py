"""run_aggregate_artifacts.py — derived artifact writer for run aggregates."""
from __future__ import annotations

from .. import derived
from .run_aggregate import build_run_aggregate
from .serialization_utils import dump_pretty_json

CATEGORY = "run-aggregates"


def write_run_aggregate(*, project_path, aggregate_id: str, **kwargs) -> str:
    aggregate = build_run_aggregate(project_path=project_path, **kwargs)
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=aggregate_id,
        artifact=aggregate,
        serialized=dump_pretty_json(aggregate),
    )
