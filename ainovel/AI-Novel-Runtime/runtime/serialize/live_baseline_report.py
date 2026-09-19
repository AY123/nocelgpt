"""live_baseline_report.py — live-baseline failure/passthrough report artifacts.

A baseline report is the unified audit record for a real multi-chapter live run.
It is generated regardless of outcome (passed / failed / budget_held / interrupted)
and records the environment, chapter outcomes, replay counts, costs, and resume
status. It never stores secrets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .. import derived

CATEGORY = "live-baseline-reports"
REPORT_VERSION = "1.0"


def next_report_id(existing_ids: list[str]) -> str:
    nums = [int(i.split("-", 1)[1]) for i in existing_ids
            if i.startswith("LBR-") and i.split("-", 1)[1].isdigit()]
    return f"LBR-{(max(nums) + 1) if nums else 1:05d}"


def _existing_report_ids(project_path) -> list[str]:
    return [e["id"] for e in derived._load_index(project_path).get("artifacts", [])
            if e.get("category") == CATEGORY]


def _summarize_chapters(chapters: list[dict]) -> dict:
    stages = {}
    selection_count = 0
    ok_count = 0
    failed_count = 0
    for chapter in chapters:
        stage = chapter.get("stage", "unknown")
        stages[stage] = stages.get(stage, 0) + 1
        length = chapter.get("length") or {}
        if length.get("selected_version"):
            selection_count += 1
        if chapter.get("ok"):
            ok_count += 1
        else:
            failed_count += 1
    return {
        "count": len(chapters),
        "ok": ok_count,
        "failed": failed_count,
        "by_stage": stages,
        "selected_versions": selection_count,
    }


# Per-chapter advisory detectors that ride the ChapterRun as ReviewReport-shaped
# dicts (findings[].severity ∈ info|warning|error). A real live run fills these;
# a deterministic run leaves them null. Rolled up so a baseline report reads as a
# quality result, not just a stage tally. ADR-003: advisory, never gates.
_ADVISORY_DETECTORS = ("pacing", "density", "ai_taste", "end_hook", "mandate", "length",
                       "meta_reference")


def _count_flags(report: dict) -> int:
    """Warning+error findings in one ReviewReport-shaped detector dict."""
    if not isinstance(report, dict):
        return 0
    return sum(1 for f in report.get("findings", [])
               if isinstance(f, dict) and f.get("severity") in ("warning", "error"))


def _summarize_quality(chapters: list[dict]) -> dict:
    """Fold the per-chapter quality signals into aggregate counts. The text-
    integrity gate is the only hard gate (ADR-003); everything else is advisory
    and reported as flagged-chapter counts, never as a gate outcome."""
    integrity = {"pass": 0, "fail": 0, "review_required": 0, "not_assessed": 0}
    advisory = {name: {"checked": 0, "flagged": 0} for name in _ADVISORY_DETECTORS}
    verdicts: dict = {}
    reference_gap_measured = 0
    for chapter in chapters:
        gate = chapter.get("integrity") or {}
        status = gate.get("status", "not_assessed")
        integrity[status] = integrity.get(status, 0) + 1
        for name in _ADVISORY_DETECTORS:
            report = chapter.get(name)
            if report is None:
                continue
            advisory[name]["checked"] += 1
            if _count_flags(report):
                advisory[name]["flagged"] += 1
        verdict = chapter.get("verdict")
        if verdict is not None:
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
        if chapter.get("reference_gap") is not None:
            reference_gap_measured += 1
    return {
        "integrity_gate": integrity,
        "advisory_flags": advisory,
        "verdicts": verdicts,
        "reference_gap_measured": reference_gap_measured,
    }


def build_live_baseline_report(
    *,
    project_path,
    baseline_id: str,
    status: str,
    environment: dict,
    chapters: list[dict],
    failures: list[dict],
    replay: dict,
    cost: dict,
    resume: dict,
    run_manifest: Optional[dict] = None,
    run_manifest_ref: Optional[str] = None,
) -> dict:
    chapter_summary = _summarize_chapters(chapters)
    quality_summary = _summarize_quality(chapters)
    integrity_gate = quality_summary["integrity_gate"]
    run_summary = {
        "baseline_id": baseline_id,
        "status": status,
        "prompt_version": environment.get("prompt_version"),
        "model_provider": environment.get("provider"),
        "model_id": environment.get("model"),
        "chapter_count": chapter_summary["count"],
        "selected_versions": chapter_summary["selected_versions"],
        "live_calls": replay.get("live_calls"),
        "actual_cost": cost.get("actual_cost"),
        "currency": cost.get("currency"),
        "resumed": resume.get("resumed"),
        "integrity_failures": integrity_gate["fail"] + integrity_gate["review_required"],
    }
    return {
        "id": next_report_id(_existing_report_ids(project_path)),
        "kind": "live_baseline_report",
        "version": REPORT_VERSION,
        "baseline_id": baseline_id,
        "status": status,
        "environment": environment,
        "run_summary": run_summary,
        "chapter_summary": chapter_summary,
        "quality_summary": quality_summary,
        "chapters": chapters,
        "failures": failures,
        "replay": replay,
        "cost": cost,
        "resume": resume,
        "run_manifest": run_manifest,
        "run_manifest_ref": run_manifest_ref,
        "gating": False,
    }


def write_live_baseline_report(*, project_path, report: dict) -> str:
    rel = derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=report["id"],
        artifact=report,
        serialized=json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return rel
