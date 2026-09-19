"""length_check.py — single-chapter length-vs-target check (ANES v2, ADR-003).

The §14 real-baseline finding, made into a guard: the DeepSeek 12-chapter run
swung 1773 → 5766 chars/chapter with NO length constraint anywhere (the outline
declared target_wordcount_per_chapter but no code read it, and no prompt carried
a length instruction). For a web-serial charged per chapter, a chapter that is
half or double the promised length is a real reader-experience + revenue problem
— it shows up chapter-to-chapter, before any cross-chapter planning could help.

It is the fourth twin of density / ai_taste / hook_check: same discipline,
different signal. It reads the DRAFT BODY directly, so it works on ANY draft (no
enrichment) and for any prompt version.

Signal: char count vs the chapter's target band. A chapter far below target reads
as thin/rushed; far above reads as padded (注水) or a runaway. The target is the
outline's target_wordcount_per_chapter; absent one, the check emits a neutral
info note (measured, not judged) so "no target authored" is distinguishable from
"on target".

DISCIPLINE:
  - DETERMINISTIC: a char count vs a band — same body + same target => same
    finding.
  - EVALUATIVE, never gates (ADR-003): a deliberately short punch-chapter or a
    long climax may be a real choice, so this is ADVISORY. It reuses the
    ReviewReport shape (axis=evaluative, gating=False) so it rides the envelope
    like check_density / check_pacing. It is NOT the draft_qa word floor (that is
    a deterministic GATE that skips a chapter) — a length miss never skips.
  - Reads only the body string + an int target. No package, no state, no model.
"""
from __future__ import annotations

from typing import List, Optional

from .draft_review import ReviewReport, ReviewFinding
from ..chapter_length import DEFAULT_BAND_LOW, DEFAULT_BAND_HIGH, role_length

LENGTH_REVIEWER_ID = "length-check-v1"

# The ROLE-LESS default band around target, as a fraction. A chapter role
# (清单 item 2: 长度区间按功能绑定) supplies its own band via
# chapter_length.ROLE_LENGTH; absent a role these historical global values
# apply, so a role-less call stays byte-identical to before this wiring.
# Conservative — warn on the clearly-off (half / 1.5x+), not the merely uneven
# (ADR-003: advisory must not cry wolf).
BAND_LOW = DEFAULT_BAND_LOW      # < 60% of target reads as thin/rushed
BAND_HIGH = DEFAULT_BAND_HIGH    # > 150% of target reads as padded / runaway


def _band_for(role: Optional[str]) -> tuple[float, float]:
    """The (low, high) band ratios for a chapter role. None → the global band,
    preserving the role-less behavior exactly."""
    if role is None:
        return BAND_LOW, BAND_HIGH
    rl = role_length(role)
    return rl["band_low"], rl["band_high"]


def length_summary(body: str, target: Optional[int] = None,
                   *, role: Optional[str] = None) -> Optional[dict]:
    """Reduce a draft body to its numeric length shape vs target. Returns None
    for an empty body (nothing to measure). Deterministic — mirrors
    density_summary. `ratio` is None when no target is authored. `role` selects
    the function-bound band; absent role uses the global band."""
    text = (body or "").strip()
    if not text:
        return None
    total = len(text)
    ratio = round(total / target, 3) if target else None
    band_low, band_high = _band_for(role)
    return {
        "total_chars": total,
        "target_chars": target,
        "ratio": ratio,
        "role": role,
        "band_low": band_low,
        "band_high": band_high,
    }


def check_length(artifact: dict, *, target: Optional[int] = None,
                 role: Optional[str] = None,
                 reviewer_id: str = LENGTH_REVIEWER_ID) -> ReviewReport:
    """Analyze a draft body's length against the chapter target and return an
    ADVISORY report (ReviewReport: axis=evaluative, gating=False). Deterministic.
    Emits a clean info note when on-target or when no target is authored, so
    'checked, on target' / 'no target' / 'off target' are all distinguishable.
    `role` selects the function-bound band (开篇/推进/反转/钩子); absent role uses
    the global band, so a role-less call is unchanged from before this wiring."""
    body = artifact.get("body", "")
    summary = length_summary(body, target, role=role)
    findings: List[ReviewFinding] = []

    if summary is None:
        findings.append(ReviewFinding("length", "info", "正文为空，跳过篇幅分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    total = summary["total_chars"]
    if not target:
        findings.append(ReviewFinding(
            "length", "info",
            f"篇幅 {total} 字；大纲未声明目标篇幅，跳过达标判断（advisory）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    band_low, band_high = summary["band_low"], summary["band_high"]
    role_note = f"，{role}章带宽" if role else ""
    ratio = summary["ratio"]
    low, high = int(target * band_low), int(target * band_high)
    if total < low:
        findings.append(ReviewFinding(
            "length", "warning",
            f"篇幅偏短（{total} 字 < 目标 {target} 的 {band_low:.0%}={low} 字，"
            f"当前 {ratio:.0%}{role_note}），单章内容单薄/仓促，付费连载易读作凑更"))
    elif total > high:
        findings.append(ReviewFinding(
            "length", "warning",
            f"篇幅偏长（{total} 字 > 目标 {target} 的 {band_high:.0%}={high} 字，"
            f"当前 {ratio:.0%}{role_note}），单章过载，警惕注水或节奏拖沓"))
    else:
        findings.append(ReviewFinding(
            "length", "info",
            f"篇幅达标（{total} 字，目标 {target}，{ratio:.0%}，在 "
            f"{band_low:.0%}–{band_high:.0%} 带宽内{role_note}）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
