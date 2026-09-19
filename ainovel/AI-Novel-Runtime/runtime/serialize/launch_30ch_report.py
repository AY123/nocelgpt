"""launch_30ch_report.py — first-pass report for 30 chapter launch."""
from __future__ import annotations

from .launch_30ch import build_30ch_launch_plan
from .serialization_utils import content_hash

LAUNCH_30CH_REPORT_KIND = "30ch_launch_report"
LAUNCH_30CH_REPORT_VERSION = "1.0"


def build_30ch_launch_report(*, project_path: str, standard_root: str, prompt_version: str,
                             model_provider: str, model_id: str, budget_limit: float,
                             notes: str = "") -> dict:
    plan = build_30ch_launch_plan(
        project_path=str(project_path),
        standard_root=str(standard_root),
        prompt_version=prompt_version,
        model_provider=model_provider,
        model_id=model_id,
        budget_limit=budget_limit,
    )
    report = {
        "kind": LAUNCH_30CH_REPORT_KIND,
        "version": LAUNCH_30CH_REPORT_VERSION,
        "plan": plan,
        "notes": notes,
    }
    report["content_hash"] = content_hash(report)
    return report
