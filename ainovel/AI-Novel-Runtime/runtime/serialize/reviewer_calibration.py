"""reviewer_calibration.py — reviewer calibration backfill and summary helpers."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

from .serialization_utils import content_hash

CATEGORY = "reviewer-calibration-reports"
RESULT_KIND = "w9_reviewer_calibration_results"
REPORT_KIND = "w9_reviewer_calibration_report"
REPORT_VERSION = "1.0"

DIMENSIONS = (
    "opening_hook",
    "chapter_goal",
    "conflict_progression",
    "character_motivation",
    "emotion_flow",
    "information_density",
    "payoff_delivery",
    "ending_hook",
    "continuity",
    "ai_voice_risk",
    "paying_intent",
    "continue_intent",
)

DECISION_DIMENSIONS = (
    "opening_hook",
    "conflict_progression",
    "paying_intent",
    "continue_intent",
)

DIAGNOSTIC_DIMENSIONS = (
    "chapter_goal",
    "character_motivation",
    "emotion_flow",
    "information_density",
    "payoff_delivery",
    "ending_hook",
    "continuity",
    "ai_voice_risk",
)

UNRELIABLE_DIMENSIONS = ()

DIMENSION_LEVELS = {
    **{dim: "decision" for dim in DECISION_DIMENSIONS},
    **{dim: "diagnostic" for dim in DIAGNOSTIC_DIMENSIONS},
    **{dim: "unreliable" for dim in UNRELIABLE_DIMENSIONS},
}


def _content_hash(data: dict) -> str:
    return content_hash(data)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_sample_human_scores(sample_path: str | Path) -> dict:
    return load_json(Path(sample_path) / "human_scores.json")


def load_sample_body(sample_path: str | Path) -> str:
    return Path(sample_path, "body.txt").read_text(encoding="utf-8")


def _mean_scores(*score_maps: dict[str, int]) -> dict[str, float]:
    out: dict[str, float] = {}
    for dim in DIMENSIONS:
        vals = [m[dim] for m in score_maps if dim in m and m[dim] is not None]
        out[dim] = mean(vals) if vals else 0.0
    return out


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2 or len(xs) != len(ys):
        return None
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not denx or not deny:
        return None
    return num / (denx * deny)


def _confidence_interval_half_width(values: list[float]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    avg = mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (n - 1)
    stddev = math.sqrt(variance)
    # Approximate 95% CI using normal approximation; enough for calibration dashboards.
    return 1.96 * (stddev / math.sqrt(n))


def build_calibration_row(*, sample_id: str, sample_category: str, reviewer_output: dict,
                          human_scores: dict, body_path: str | Path, notes_ref: str,
                          human_score_ref: str) -> dict:
    reviewer_scores = reviewer_output.get("dimension_scores") or {}
    human_a = human_scores.get("editor_a") or {}
    human_b = human_scores.get("editor_b") or {}
    human_mean = _mean_scores(human_a, human_b)
    deltas = {dim: reviewer_scores.get(dim, 0) - human_mean.get(dim, 0) for dim in DIMENSIONS}
    row = {
        "kind": RESULT_KIND,
        "version": "1.0",
        "sample_id": sample_id,
        "sample_category": sample_category,
        "body_ref": str(body_path),
        "human_score_ref": str(human_score_ref),
        "notes_ref": str(notes_ref),
        "decision_mode": reviewer_output.get("decision_mode", "calibration"),
        "dimension_scores": {dim: reviewer_scores.get(dim) for dim in DIMENSIONS},
        "severity_labels": reviewer_output.get("severity_labels", []),
        "continue_probability": reviewer_output.get("continue_probability"),
        "pay_probability": reviewer_output.get("pay_probability"),
        "risk_flags": reviewer_output.get("risk_flags", []),
        "evidence_spans": reviewer_output.get("evidence_spans", []),
        "recommendation": reviewer_output.get("recommendation"),
        "uncertainty": reviewer_output.get("uncertainty", "high"),
        "comparison": {
            "human_score_ref": str(human_score_ref),
            "golden_reference": None,
            "human_mean": human_mean,
            "delta_summary": deltas,
        },
        "body_hash": _content_hash({"body": load_sample_body(Path(body_path).parent)}),
        "human_scores_hash": _content_hash(human_scores),
        "reviewer_output_hash": _content_hash(reviewer_output),
    }
    row["content_hash"] = _content_hash(row)
    return row


def _dimension_level(dim: str) -> str:
    return DIMENSION_LEVELS.get(dim, "unreliable")


def _dimension_rationale(dim: str, stat: dict) -> str:
    level = _dimension_level(dim)
    if level == "decision":
        return "信号稳定，适合驱动自动选择或硬门控"
    if level == "diagnostic":
        return "相关性足够高，但更适合用于诊断/复盘，不直接单独决定选择"
    return "校准证据不足或不稳定，禁止进入自动决策"


def build_calibration_summary(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    dimension_stats = {}
    for dim in DIMENSIONS:
        human_vals: list[float] = []
        reviewer_vals: list[float] = []
        abs_errors: list[float] = []
        for row in rows:
            comp = row.get("comparison", {})
            human = comp.get("human_mean", {}).get(dim)
            reviewer = (row.get("dimension_scores") or {}).get(dim)
            if human is None or reviewer is None:
                continue
            human_vals.append(float(human))
            reviewer_vals.append(float(reviewer))
            abs_errors.append(abs(float(reviewer) - float(human)))
        stat = {
            "sample_count": len(abs_errors),
            "correlation": _pearson(reviewer_vals, human_vals),
            "mean_abs_error": mean(abs_errors) if abs_errors else None,
            "ci95_half_width": _confidence_interval_half_width(abs_errors),
        }
        stat["level"] = _dimension_level(dim)
        stat["rationale"] = _dimension_rationale(dim, stat)
        dimension_stats[dim] = stat
    summary = {
        "kind": REPORT_KIND,
        "version": REPORT_VERSION,
        "sample_count": len(rows),
        "dimension_stats": dimension_stats,
        "dimension_grading": {
            "decision": list(DECISION_DIMENSIONS),
            "diagnostic": list(DIAGNOSTIC_DIMENSIONS),
            "unreliable": list(UNRELIABLE_DIMENSIONS),
        },
        "trusted_dimensions": [dim for dim, stat in dimension_stats.items()
                               if stat["sample_count"] >= 5 and (stat["correlation"] or 0) >= 0.6],
        "notes": "calibration summary from real reviewer backfill",
    }
    summary["content_hash"] = _content_hash(summary)
    return summary


def build_real_calibration_report(*, rows: Iterable[dict], subset: Iterable[dict]) -> dict:
    rows = list(rows)
    sample_ids = {r["sample_id"] for r in rows}
    subset_ids = [s["sample_id"] for s in subset]
    missing = [sid for sid in subset_ids if sid not in sample_ids]
    report = build_calibration_summary(rows)
    report.update({
        "subset_ids": subset_ids,
        "missing_subset_ids": missing,
        "status": "complete" if not missing and len(rows) >= len(subset_ids) else "incomplete",
    })
    report["content_hash"] = _content_hash(report)
    return report


def calibration_metadata_dir(project_root: str | Path) -> Path:
    return Path(project_root) / "AI-Novel-Runtime" / "quality-golden-set" / "metadata"


def load_calibration_subset(project_root: str | Path) -> dict:
    return load_json(calibration_metadata_dir(project_root) / "w9-calibration-subset.json")


def load_calibration_results(project_root: str | Path) -> dict:
    return load_json(calibration_metadata_dir(project_root) / "w9-calibration-results.json")


def write_calibration_results(project_root: str | Path, results: dict) -> Path:
    path = calibration_metadata_dir(project_root) / "w9-calibration-results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
