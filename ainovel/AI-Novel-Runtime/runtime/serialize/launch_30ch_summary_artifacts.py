"""launch_30ch_summary_artifacts.py — derived artifact writer for 30 chapter launch summaries."""
from __future__ import annotations

import json

from .. import derived
from .launch_30ch_summary import build_30ch_launch_summary

CATEGORY = "30ch-launch-summaries"


def write_30ch_launch_summary(*, project_path, summary_id: str, **kwargs) -> str:
    summary = build_30ch_launch_summary(project_path=str(project_path), **kwargs)
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=summary_id,
        artifact=summary,
        serialized=json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
    )
