"""W9 reviewer-calibration summary and dimension-grading policy.

This module holds the W9 pipeline that was introduced by ``b49fc62`` and later
lost when ``b866525`` reused the ``reviewer_calibration_summary`` filename for
the unrelated D90-02 ``build_reviewer_calibration`` report. Two different
modules had collided on one filename; the W9 half lives here so both survive.

Dimension grading is advisory (ADR-003): ``decision`` dimensions may sort or
choose, ``diagnostic`` dimensions may be inspected but never gate alone, and
``unreliable`` dimensions are disabled for selection.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean

from .reviewer_calibration import (
    build_calibration_summary,
    calibration_metadata_dir,
    load_calibration_results,
    _content_hash,
)

DECISION_MODE = "decision"
DIAGNOSTIC_MODE = "diagnostic"
UNRELIABLE_MODE = "unreliable"

SUMMARY_KIND = "w9_reviewer_calibration_summary"
SUMMARY_VERSION = "1.1"
SUMMARY_FILENAME = "w9-calibration-summary.json"
REPORT_FILENAME = "w9-calibration-report.md"

# A calibration row only counts as EVIDENCE when its sample has a real prose
# body. The W9 set on disk failed this badly: of 50 sample dirs, 7 have no
# body.txt at all and 40 hold a 54-58 char DEFECT LABEL ("同义反复拖慢节奏") rather
# than a chapter fragment — yet all 43 carried editor scores, so the summary
# reported real_sample_count=43 and r=0.85-0.92. Scoring a defect label is not
# scoring prose, so those correlations are not evidence that the reviewer agrees
# with humans about NOVELS.
#
# 200 chars is the floor for "this is a prose fragment, not a label". The three
# genuine samples are 253-339 chars; every stub is under 60.
MIN_REAL_BODY_CHARS = 200

# A dimension needs at least this many REAL samples before its correlation may
# promote it to `decision` (mirrors the existing trusted_dimensions floor of 5).
MIN_REAL_SAMPLES_FOR_DECISION = 5


def load_w9_dimension_policy(project_root: str) -> dict:
    """Grade each dimension from the W9 calibration summary.

    Degrades to an empty grading when the project has no calibration results
    on disk: an uncalibrated signal must not drive a strong decision
    (``docs/README.md`` §4), so no dimension is decision-eligible until the
    calibration exists. Never raises, never gates (ADR-003).
    """
    try:
        summary = build_w9_summary(project_root)
    except FileNotFoundError:
        return {"decision": set(), "diagnostic": set(), "unreliable": set()}
    grading = summary.get("dimension_grading") or {}
    policy = {
        "decision": set(grading.get("decision") or []),
        "diagnostic": set(grading.get("diagnostic") or []),
        "unreliable": set(grading.get("unreliable") or []),
    }
    return policy


def classify_w9_dimension(project_root: str, dimension: str) -> str:
    policy = load_w9_dimension_policy(project_root)
    if dimension in policy["decision"]:
        return DECISION_MODE
    if dimension in policy["diagnostic"]:
        return DIAGNOSTIC_MODE
    return UNRELIABLE_MODE


def can_use_w9_dimension_for_decision(project_root: str, dimension: str) -> bool:
    return classify_w9_dimension(project_root, dimension) == DECISION_MODE


def filter_w9_decision_scores(project_root: str, scores: dict) -> dict:
    policy = load_w9_dimension_policy(project_root)
    allowed = policy["decision"]
    return {dim: value for dim, value in (scores or {}).items() if dim in allowed}


def build_w9_selection_policy(project_root: str) -> dict:
    try:
        summary = build_w9_summary(project_root)
        grading = summary.get("dimension_grading") or {}
        status = summary.get("status")
        trusted = sorted(summary.get("trusted_dimensions") or [])
    except FileNotFoundError:
        grading = {"decision": [], "diagnostic": [], "unreliable": []}
        status = "unavailable"
        trusted = []
    policy = {
        "kind": "w9_selection_policy",
        "version": "1.0",
        "status": status,
        "decision_dimensions": sorted(grading.get("decision") or []),
        "diagnostic_dimensions": sorted(grading.get("diagnostic") or []),
        "unreliable_dimensions": sorted(grading.get("unreliable") or []),
        "blocked_dimensions": sorted(
            set(grading.get("diagnostic") or [])
            | set(grading.get("unreliable") or [])
        ),
        "trusted_dimensions": trusted,
    }
    return policy


def build_boundary_summary(results: dict) -> dict:
    rows = results.get("results") or []
    boundary_rows = [r for r in rows if r.get("sample_category") == "boundary"]
    dimension_grading = (results.get("report") or {}).get("dimension_grading") or {}
    summary = {
        "boundary_sample_count": len(boundary_rows),
        "boundary_status_counts": dict(Counter(r.get("decision_mode") for r in boundary_rows)),
        "boundary_trust_flags": {
            "has_evidence_spans": all(bool(r.get("evidence_spans")) for r in boundary_rows),
            "has_uncertainty": all(r.get("uncertainty") is not None for r in boundary_rows),
        },
        "boundary_mean_continue_probability": mean(
            [r.get("continue_probability") for r in boundary_rows if r.get("continue_probability") is not None]
        ) if any(r.get("continue_probability") is not None for r in boundary_rows) else None,
        "dimension_grading": dimension_grading,
    }
    return summary


def _row_has_real_body(row: dict) -> bool:
    """True when the row's sample points at an actual prose body on disk.

    A missing file, an unreadable one, or a body shorter than
    MIN_REAL_BODY_CHARS all count as NOT real: the calibration cannot claim a
    human scored prose when what sits on disk is a one-line defect label.
    """
    ref = row.get("body_ref")
    if not ref:
        return False
    try:
        body = Path(ref).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return False
    return len(body) >= MIN_REAL_BODY_CHARS


def _downgrade_grading_without_evidence(summary: dict, real_sample_count: int) -> dict:
    """Demote `decision` dimensions that no real-sample evidence supports.

    `dimension_grading` as computed upstream is a HARDCODED tuple
    (reviewer_calibration.DECISION_DIMENSIONS) — the label was authored a priori
    and the r-values printed beside it never actually gated the promotion. So a
    set of stub samples yields four `decision` dimensions that read as calibrated
    when nothing was calibrated.

    Demotion target is `diagnostic`, not `unreliable`: the dimension may still be
    inspected and compared, it just may not drive an automatic choice. That keeps
    this a trust downgrade, never a new gate (ADR-003). Restoring `decision`
    requires real samples, not a code change.
    """
    grading = dict(summary.get("dimension_grading") or {})
    decision = list(grading.get("decision") or [])
    if not decision or real_sample_count >= MIN_REAL_SAMPLES_FOR_DECISION:
        return summary

    stats = dict(summary.get("dimension_stats") or {})
    for dim in decision:
        stat = dict(stats.get(dim) or {})
        stat["level"] = DIAGNOSTIC_MODE
        stat["rationale"] = (
            f"降级：仅 {real_sample_count} 个真实样本（正文 ≥{MIN_REAL_BODY_CHARS} 字），"
            f"低于 {MIN_REAL_SAMPLES_FOR_DECISION} 的下限；相关性由标签样本得出，不足以驱动自动决策"
        )
        stat["real_sample_count"] = real_sample_count
        stats[dim] = stat

    grading["decision"] = []
    grading["diagnostic"] = sorted(set(grading.get("diagnostic") or []) | set(decision))
    summary["dimension_grading"] = grading
    summary["dimension_stats"] = stats
    summary["trusted_dimensions"] = []
    summary["grading_downgraded"] = {
        "reason": "insufficient_real_samples",
        "demoted_from_decision": sorted(decision),
        "real_sample_count": real_sample_count,
        "min_real_body_chars": MIN_REAL_BODY_CHARS,
        "min_real_samples_for_decision": MIN_REAL_SAMPLES_FOR_DECISION,
    }
    return summary


def build_w9_summary(project_root: str) -> dict:
    results = load_calibration_results(project_root)
    rows = results.get("results") or []
    summary = build_calibration_summary(rows)
    skipped = results.get("skipped") or []
    skeleton_seeds = results.get("skeleton_seeds") or [
        item for item in skipped if "skeleton" in (item.get("reason") or "").lower()
    ]
    # real_sample_count used to be len(rows) — it counted ROWS, never checking
    # whether a row's sample had a body. That is how 40 stub labels became
    # "43 real samples". It is now an evidence count.
    real_sample_count = sum(1 for row in rows if _row_has_real_body(row))
    label_only_sample_count = len(rows) - real_sample_count
    summary.update({
        "row_count": len(rows),
        "label_only_sample_count": label_only_sample_count,
        "status": results.get("status"),
        "sample_count": results.get("sample_count", 0),
        "real_sample_count": real_sample_count,
        "skeleton_seed_count": len(skeleton_seeds),
        "skipped_sample_count": len(skipped),
        "boundary": build_boundary_summary(results),
        "content_hash": results.get("content_hash") or summary.get("content_hash"),
    })
    summary["kind"] = SUMMARY_KIND
    summary["version"] = SUMMARY_VERSION
    summary["metadata_root"] = str(calibration_metadata_dir(project_root))
    # Demote `decision` dimensions the evidence does not support, and say so in
    # the status: a reader (or dashboard) that only looks at `status` must not
    # come away believing this calibration is complete.
    summary = _downgrade_grading_without_evidence(summary, real_sample_count)
    if summary.get("grading_downgraded"):
        summary["status"] = "uncalibrated_insufficient_real_samples"
        # The boundary block carries its OWN copy of dimension_grading (folded
        # from results["report"]), so leaving it untouched would keep publishing
        # the four demoted dimensions as `decision` one level down.
        boundary = dict(summary.get("boundary") or {})
        if boundary.get("dimension_grading"):
            boundary["dimension_grading"] = summary["dimension_grading"]
            summary["boundary"] = boundary
    summary["content_hash"] = _content_hash(summary)
    return summary


def render_w9_report(project_root: str) -> str:
    summary = build_w9_summary(project_root)
    dims = summary.get("dimension_stats") or {}
    lines = [
        "# W9 Reviewer Calibration Report",
        "",
        f"- Status: `{summary['status']}`",
        f"- Real samples (正文 ≥{MIN_REAL_BODY_CHARS} 字): `{summary['real_sample_count']}`",
        f"- Label-only samples (no prose body): `{summary.get('label_only_sample_count', 0)}`",
        f"- Scored rows: `{summary.get('row_count', 0)}`",
        f"- Skeleton seeds: `{summary['skeleton_seed_count']}`",
        f"- Skipped samples: `{summary['skipped_sample_count']}`",
        f"- Boundary samples: `{summary['boundary']['boundary_sample_count']}`",
    ]
    downgraded = summary.get("grading_downgraded")
    if downgraded:
        lines.extend([
            "",
            "> **降级**：以下维度原标为 `decision`，但支撑它们的样本多为缺陷标签而非正文，"
            "已降为 `diagnostic`（可诊断、不可驱动自动选择）：",
            f"> `{'`, `'.join(downgraded['demoted_from_decision'])}`",
            f"> 真实样本 {downgraded['real_sample_count']} 个，低于下限 "
            f"{downgraded['min_real_samples_for_decision']}。",
        ])
    lines.extend(["", "## Dimension Stats"])
    for dim, stat in dims.items():
        # `n` is the SCORED-ROW count, which is not the same as the real-sample
        # count when rows point at label stubs. Naming it explicitly is what
        # stops "n=43" from being read as "43 real chapters were calibrated".
        lines.append(
            f"- `{dim}`: level={stat.get('level')}, scored_rows={stat['sample_count']}, "
            f"real_samples={summary['real_sample_count']}, r={stat['correlation']}, "
            f"mae={stat['mean_abs_error']}, ci95={stat['ci95_half_width']}"
        )
    lines.extend([
        "",
        "## Boundary Summary",
        f"- Mean continue probability: `{summary['boundary']['boundary_mean_continue_probability']}`",
        f"- Has evidence spans: `{summary['boundary']['boundary_trust_flags']['has_evidence_spans']}`",
        f"- Has uncertainty: `{summary['boundary']['boundary_trust_flags']['has_uncertainty']}`",
        "",
        f"- Content hash: `{summary['content_hash']}`",
    ])
    return "\n".join(lines) + "\n"


def write_w9_summary(project_root: str) -> Path:
    summary = build_w9_summary(project_root)
    path = Path(project_root) / "AI-Novel-Runtime" / "quality-golden-set" / "metadata" / SUMMARY_FILENAME
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_w9_report(project_root: str) -> Path:
    path = Path(project_root) / "AI-Novel-Runtime" / "quality-golden-set" / "metadata" / REPORT_FILENAME
    path.write_text(render_w9_report(project_root), encoding="utf-8")
    return path
