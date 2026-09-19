from __future__ import annotations

import json
from pathlib import Path

from .reviewer_calibration import (
    build_calibration_row,
    build_real_calibration_report,
    calibration_metadata_dir,
    load_calibration_subset,
    load_calibration_results,
    load_json,
    load_sample_human_scores,
    write_calibration_results,
)


def build_real_reviewer_output(sample_id: str, sample_dir: Path) -> dict:
    """Build the reviewer (simulator) side of a calibration row.

    The reviewer side MUST be independent of the human ground truth, otherwise
    the calibration correlation is self-referential (r≈1.0 by construction).
    The authoritative human scores stay on the comparison side only.

    Source: the AI reviewer's ``consensus_scores`` in ``ai_scores.json`` — an
    LLM judge scored the body without seeing human_scores (ADR: simulator is
    never authoritative; human_editor_is_authoritative). This measures how well
    the automated reviewer aligns with real human ground truth, which is what
    W9 calibration is for. Falls back to skipping the sample if no independent
    reviewer output exists (never copies human scores into the reviewer side).
    """
    sample_labels = json.loads((sample_dir / "labels.json").read_text(encoding="utf-8"))
    ai_scores = json.loads((sample_dir / "ai_scores.json").read_text(encoding="utf-8"))
    dimension_scores = dict(ai_scores.get("consensus_scores") or {})
    return {
        "decision_mode": "calibration",
        "reviewer_source": "ai_scores.consensus_scores",
        "dimension_scores": dimension_scores,
        "severity_labels": sample_labels.get("severity_labels", []),
        "continue_probability": sample_labels.get("continue_probability", 0.5),
        "pay_probability": sample_labels.get("pay_probability", 0.5),
        "risk_flags": sample_labels.get("risk_flags", []),
        "evidence_spans": sample_labels.get("evidence_spans", []),
        "recommendation": sample_labels.get("recommendation", "review_only"),
        "uncertainty": sample_labels.get("uncertainty", "high"),
    }


def _sample_readme_is_skeleton(sample_dir: Path) -> bool:
    readme = sample_dir / "README.txt"
    if not readme.exists():
        return False
    text = readme.read_text(encoding="utf-8")
    return "仅提供结构，不包含正文内容" in text or "sample skeleton" in text.lower()


def _backfill_rows(project_root: str | Path, queue: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    project_root = Path(project_root)
    rows = []
    skipped = []
    skeleton_seeds = []
    samples_root = project_root / "AI-Novel-Runtime" / "quality-golden-set" / "samples"
    for item in queue:
        sample_dir = samples_root / item["sample_id"]
        human_scores_path = sample_dir / "human_scores.json"
        body_path = sample_dir / "body.txt"
        notes_path = sample_dir / "notes.md"
        ai_scores_path = sample_dir / "ai_scores.json"
        if (not human_scores_path.exists() or not body_path.exists()
                or not notes_path.exists() or not ai_scores_path.exists()):
            if _sample_readme_is_skeleton(sample_dir):
                skeleton_seeds.append({"sample_id": item["sample_id"], "category": item.get("category"), "reason": "seed skeleton only; intentionally no正文/human_scores"})
            else:
                skipped.append({"sample_id": item["sample_id"], "category": item.get("category"), "reason": "missing required sample files"})
            continue
        human_scores = load_sample_human_scores(sample_dir)
        reviewer_output = build_real_reviewer_output(item["sample_id"], sample_dir)
        row = build_calibration_row(
            sample_id=item["sample_id"],
            sample_category=item["category"],
            reviewer_output=reviewer_output,
            human_scores=human_scores,
            body_path=body_path,
            notes_ref=notes_path,
            human_score_ref=human_scores_path,
        )
        rows.append(row)
    return rows, skipped, skeleton_seeds


def backfill_subset(project_root: str | Path) -> dict:
    project_root = Path(project_root)
    subset = load_calibration_subset(project_root)["subset"]
    rows, skipped, skeleton_seeds = _backfill_rows(project_root, subset)

    results = {
        "kind": "w9_reviewer_calibration_results",
        "version": "1.0",
        "decision_mode": "calibration",
        "sample_count": len(rows),
        "status": "complete" if not skipped and not skeleton_seeds else "complete_with_skeleton_seeds" if skeleton_seeds and not skipped else "partial",
        "results": rows,
        "skipped": skipped,
        "skeleton_seeds": skeleton_seeds,
        "report": build_real_calibration_report(rows=rows, subset=subset),
    }
    results["content_hash"] = results["report"]["content_hash"]
    write_calibration_results(project_root, results)
    return results


def backfill_all(project_root: str | Path) -> dict:
    project_root = Path(project_root)
    queue = load_json(calibration_metadata_dir(project_root) / "w9-calibration-queue.json")["queue"]
    rows, skipped, skeleton_seeds = _backfill_rows(project_root, queue)
    subset = load_calibration_subset(project_root)["subset"]
    results = {
        "kind": "w9_reviewer_calibration_results",
        "version": "1.0",
        "decision_mode": "calibration",
        "sample_count": len(rows),
        "status": "complete" if not skipped and not skeleton_seeds else "complete_with_skeleton_seeds" if skeleton_seeds and not skipped else "partial",
        "results": rows,
        "skipped": skipped,
        "skeleton_seeds": skeleton_seeds,
        "report": build_real_calibration_report(rows=rows, subset=subset),
    }
    results["content_hash"] = results["report"]["content_hash"]
    write_calibration_results(project_root, results)
    return results


def show_results(project_root: str | Path) -> dict:
    return load_calibration_results(project_root)
