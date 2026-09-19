"""baseline_artifacts.py — derived artifact writer for baseline reports."""
from __future__ import annotations

from .. import derived
from .baseline_report import build_baseline_report
from .serialization_utils import dump_pretty_json

CATEGORY = "baseline-reports"


def write_baseline_report(*, project_path, report_id: str, chapters, reviewers, winner_scored_hash: str = "",
                          winner_written_hash: str = "", winner_scored_id: str = "", winner_written_id: str = "",
                          notes: str = "") -> str:
    report = build_baseline_report(
        chapters=chapters,
        reviewers=reviewers,
        winner_scored_hash=winner_scored_hash,
        winner_written_hash=winner_written_hash,
        winner_scored_id=winner_scored_id,
        winner_written_id=winner_written_id,
        notes=notes,
    )
    return derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report_id,
        artifact=report,
        serialized=dump_pretty_json(report),
    )
