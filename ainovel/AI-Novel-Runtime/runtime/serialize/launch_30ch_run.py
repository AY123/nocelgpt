"""launch_30ch_run.py — helper to attach launch link to a run manifest."""
from __future__ import annotations

from .launch_30ch_link import build_30ch_launch_link


def build_30ch_run_attachment(*, launch_report_id: str, run_manifest_ref: str, notes: str = "") -> dict:
    return build_30ch_launch_link(
        launch_report_id=launch_report_id,
        run_manifest_ref=run_manifest_ref,
        notes=notes,
    )
