"""launch_30ch_artifacts.py — derived artifact writer for 30 chapter launch plans."""
from __future__ import annotations

import json

from .. import derived
from .launch_30ch import build_30ch_launch_plan
from .launch_30ch_report import build_30ch_launch_report

CATEGORY = "30ch-launch-plans"
REPORT_CATEGORY = "30ch-launch-reports"


def write_30ch_launch_plan(*, project_path, report_id: str, plan: dict) -> str:
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=plan,
        serialized=json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2),
    )


def write_30ch_launch_report(*, project_path, report_id: str, **kwargs) -> str:
    report = build_30ch_launch_report(**kwargs)
    return derived.write_artifact(
        project_path=project_path,
        category=REPORT_CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
