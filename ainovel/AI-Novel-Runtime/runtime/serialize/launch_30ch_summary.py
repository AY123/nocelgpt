"""launch_30ch_summary.py — consolidated summary for 30 chapter launch artifacts."""
from __future__ import annotations

from .launch_30ch import build_30ch_launch_plan
from .launch_30ch_report import build_30ch_launch_report
from .launch_30ch_link import build_30ch_launch_link
from .launch_30ch_run import build_30ch_run_attachment
from .launch_30ch_bundle import list_30ch_launch_bundle
from .serialization_utils import content_hash


def build_30ch_launch_summary(*, project_path: str, standard_root: str, prompt_version: str,
                              model_provider: str, model_id: str, budget_limit: float,
                              launch_report_id: str, run_manifest_ref: str,
                              notes: str = "") -> dict:
    summary = {
        "kind": "30ch_launch_summary",
        "version": "1.0",
        "bundle": list_30ch_launch_bundle(project_path),
        "plan": build_30ch_launch_plan(
            project_path=str(project_path),
            standard_root=standard_root,
            prompt_version=prompt_version,
            model_provider=model_provider,
            model_id=model_id,
            budget_limit=budget_limit,
        ),
        "report": build_30ch_launch_report(
            project_path=project_path,
            standard_root=standard_root,
            prompt_version=prompt_version,
            model_provider=model_provider,
            model_id=model_id,
            budget_limit=budget_limit,
            notes=notes,
        ),
        "link": build_30ch_launch_link(
            launch_report_id=launch_report_id,
            run_manifest_ref=run_manifest_ref,
            notes=notes,
        ),
        "run": build_30ch_run_attachment(
            launch_report_id=launch_report_id,
            run_manifest_ref=run_manifest_ref,
            notes=notes,
        ),
        "notes": notes,
    }
    summary["content_hash"] = content_hash(summary)
    return summary
