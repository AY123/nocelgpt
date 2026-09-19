from __future__ import annotations

from pathlib import Path

from .w9_calibration_summary import build_w9_summary

REPORT_FILENAME = "w9-calibration-summary.md"


def render_w9_summary_markdown(project_root: str) -> str:
    summary = build_w9_summary(project_root)
    lines = []
    lines.append("# W9 Reviewer Calibration Summary")
    lines.append("")
    lines.append(f"- Status: `{summary.get('status')}`")
    lines.append(f"- Sample count: `{summary.get('sample_count')}`")
    lines.append(f"- Real sample count: `{summary.get('real_sample_count')}`")
    lines.append(f"- Skeleton seed count: `{summary.get('skeleton_seed_count')}`")
    lines.append(f"- Skipped sample count: `{summary.get('skipped_sample_count')}`")
    lines.append(f"- Summary hash: `{summary.get('content_hash')}`")
    lines.append("")
    lines.append("## Boundary")
    boundary = summary.get("boundary") or {}
    lines.append(f"- Boundary sample count: `{boundary.get('boundary_sample_count')}`")
    lines.append(f"- Boundary mean continue probability: `{boundary.get('boundary_mean_continue_probability')}`")
    trust = boundary.get("boundary_trust_flags") or {}
    lines.append(f"- Evidence spans present: `{trust.get('has_evidence_spans')}`")
    lines.append(f"- Uncertainty present: `{trust.get('has_uncertainty')}`")
    lines.append("")
    lines.append("## Dimension Stats")
    lines.append("| Dimension | Level | N | r | MAE | CI95 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for dim, stat in (summary.get("dimension_stats") or {}).items():
        lines.append(
            f"| {dim} | {stat.get('level')} | {stat.get('sample_count')} | {stat.get('correlation')} | "
            f"{stat.get('mean_abs_error')} | {stat.get('ci95_half_width')} |"
        )
    lines.append("")
    lines.append("## Trusted Dimensions")
    trusted = summary.get("trusted_dimensions") or []
    if trusted:
        for dim in trusted:
            lines.append(f"- {dim}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append(f"Metadata root: `{summary.get('metadata_root')}`")
    return "\n".join(lines) + "\n"


def write_w9_summary_markdown(project_root: str) -> Path:
    out = Path(project_root) / "AI-Novel-Runtime" / "quality-golden-set" / "metadata" / REPORT_FILENAME
    out.write_text(render_w9_summary_markdown(project_root), encoding="utf-8")
    return out
