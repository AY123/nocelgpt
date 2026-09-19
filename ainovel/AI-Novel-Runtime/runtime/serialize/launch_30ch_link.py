"""launch_30ch_link.py — link launch reports to run manifests."""
from __future__ import annotations

from .serialization_utils import content_hash


def build_30ch_launch_link(*, launch_report_id: str, run_manifest_ref: str, notes: str = "") -> dict:
    link = {
        "kind": "30ch_launch_link",
        "version": "1.0",
        "launch_report_id": launch_report_id,
        "run_manifest_ref": run_manifest_ref,
        "notes": notes,
    }
    link["content_hash"] = content_hash(link)
    return link
