"""winner_drift.py — report helpers for winner drift checks."""
from __future__ import annotations

from typing import Optional

from .serialization_utils import content_hash


def _content_hash(report: dict) -> str:
    return content_hash(report)


def build_winner_drift_report(*, scored_hash: str, written_hash: str, scored_id: str, written_id: str,
                              evidence_ref: str = "", notes: str = "") -> dict:
    report = {
        "kind": "winner_drift_report",
        "version": "1.0",
        "scored_id": scored_id,
        "written_id": written_id,
        "scored_hash": scored_hash,
        "written_hash": written_hash,
        "matches": scored_hash == written_hash,
        "evidence_ref": evidence_ref,
        "notes": notes,
    }
    report["content_hash"] = _content_hash(report)
    return report
