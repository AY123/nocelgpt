"""run_aggregate.py — derived run-level aggregate from chapter artifacts."""
from __future__ import annotations

from .launch_30ch_summary import build_30ch_launch_summary
from .checkpoints import load_serial_checkpoints
from .serialization_utils import content_hash

CATEGORY = "run-aggregates"


def build_run_aggregate(*, project_path, standard_root, prompt_version, model_provider, model_id,
                        budget_limit, launch_report_id, run_manifest_ref, notes: str = "") -> dict:
    run_summary = build_30ch_launch_summary(
        project_path=str(project_path),
        standard_root=str(standard_root),
        prompt_version=prompt_version,
        model_provider=model_provider,
        model_id=model_id,
        budget_limit=budget_limit,
        launch_report_id=launch_report_id,
        run_manifest_ref=run_manifest_ref,
        notes=notes,
    )
    # Fold the staged review checkpoints (chapters 10/20/30) the run persisted,
    # so 复盘 / 阶段对比 / 基线报告汇总 can cite them off one aggregate. Read-side
    # only; empty list for a run that never reached chapter 10. This is the
    # reference end that closes the checkpoint loop (writer→reader→aggregate).
    checkpoints = load_serial_checkpoints(project_path)
    aggregate = {
        "kind": "run_aggregate",
        "version": "1.0",
        "run_summary": run_summary,
        "checkpoints": checkpoints,
        "project_path": str(project_path),
        "notes": notes,
    }
    aggregate["content_hash"] = content_hash(aggregate)
    return aggregate
