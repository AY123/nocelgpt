"""pacing.py — intra-chapter pacing check over the emotion curve (ANES v2, ADR-003).

The LLM scene planner (llm_planner) enriches each scene with an `emotion.valence`
(0-100). The sequence of valences across a chapter's scenes is its emotion curve.
`check_pacing` analyzes that curve DETERMINISTICALLY and reports pacing risks:
a flat curve (no rise/fall), a monotone curve (only climbing or only sinking),
weak amplitude (too small a swing to feel like anything happened), or no real
peak. These are the shapes that read as 平淡/注水 to a web-novel audience.

DISCIPLINE:
  - DETERMINISTIC: valence is numeric and the curve's shape (variance, peak,
    monotonicity) is computed, not judged — same curve => same findings.
  - EVALUATIVE, never gates (ADR-003): a flat chapter may be a deliberate
    breather, so pacing is ADVISORY. It emits findings; it never blocks. Reuses
    the ReviewReport shape so it rides the envelope like any evaluative report.
  - Degrades to an empty report when the plan carries no emotion data (a bare
    deterministic skeleton, or enrichment that degraded) — nothing to analyze.
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding

# Tunable thresholds for what reads as "flat" / "weak" to a web-novel audience.
# Deliberately conservative so the check warns on the clearly-bad, not the merely
# quiet (ADR-003: advisory, must not cry wolf).
FLAT_STDEV = 8.0          # a valence spread tighter than this reads as flat
WEAK_AMPLITUDE = 20       # max-min below this is too small a swing to register


def _valences(scene_plan: dict) -> List[int]:
    """The valence sequence across scenes, in scene order. Scenes without an
    emotion are skipped — a partially-enriched plan still yields a curve from the
    scenes that have one."""
    out = []
    for s in scene_plan.get("scenes", []):
        emo = s.get("emotion")
        if isinstance(emo, dict) and isinstance(emo.get("valence"), int):
            out.append(emo["valence"])
    return out


def _stdev(xs: List[int]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    return (sum((x - mean) ** 2 for x in xs) / n) ** 0.5


def _is_monotone(xs: List[int]) -> bool:
    """True if the curve only rises (or only falls) across the whole chapter —
    no internal turn. Equal-adjacent steps are allowed within one direction."""
    if len(xs) < 3:
        return False
    non_decreasing = all(b >= a for a, b in zip(xs, xs[1:]))
    non_increasing = all(b <= a for a, b in zip(xs, xs[1:]))
    return non_decreasing or non_increasing


def _peak_index(xs: List[int]) -> int:
    return max(range(len(xs)), key=lambda i: xs[i])


def curve_summary(scene_plan: dict) -> Optional[dict]:
    """Reduce a chapter's emotion curve to its numeric shape: peak / mean /
    amplitude / the raw valence sequence. Returns None when the plan carries no
    emotion data (a bare skeleton). This is what the cross-chapter pacing layer
    reads per chapter — a chapter's PEAK valence is its climax height — so it need
    not re-open the scene plan. Deterministic."""
    valences = _valences(scene_plan)
    if not valences:
        return None
    return {
        "peak": max(valences),
        "mean": round(sum(valences) / len(valences), 1),
        "amplitude": max(valences) - min(valences),
        "valences": valences,
    }


PACING_REVIEWER_ID = "pacing-check-v1"


def check_pacing(scene_plan: dict, *, reviewer_id: str = PACING_REVIEWER_ID) -> ReviewReport:
    """Analyze a scene plan's emotion curve and return an ADVISORY pacing report
    (ReviewReport: axis=evaluative, gating=False). Deterministic. Emits no
    findings — an empty clean report — when there is no emotion curve to judge
    (bare skeleton), so 'checked, nothing flagged' is distinguishable from
    'never checked'."""
    valences = _valences(scene_plan)
    findings: List[ReviewFinding] = []

    if len(valences) < 2:
        # Not enough of a curve to say anything — no emotion data or a single
        # scene. Report clean rather than warn (ADR-003: don't cry wolf).
        findings.append(ReviewFinding(
            "pacing", "info",
            "情绪曲线数据不足，跳过节奏分析（未增强或场景过少）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    stdev = _stdev(valences)
    amplitude = max(valences) - min(valences)
    curve_str = "→".join(str(v) for v in valences)

    if stdev < FLAT_STDEV:
        findings.append(ReviewFinding(
            "pacing", "warning",
            f"情绪曲线过平（标准差 {stdev:.1f}<{FLAT_STDEV:.0f}），全章缺乏起伏，"
            f"读来易显平淡/注水：{curve_str}"))
    elif amplitude < WEAK_AMPLITUDE:
        findings.append(ReviewFinding(
            "pacing", "warning",
            f"情绪振幅偏弱（{amplitude}<{WEAK_AMPLITUDE}），高低落差不足以形成爽点："
            f"{curve_str}"))

    if _is_monotone(valences):
        findings.append(ReviewFinding(
            "pacing", "warning",
            f"情绪曲线单调（全程只升或只降），章内缺少转折/张弛：{curve_str}"))

    # A healthy web-novel chapter usually crests near the climax, then lands the
    # exit hook — a peak stuck at the very first scene often means the chapter
    # front-loads and fizzles.
    peak = _peak_index(valences)
    if len(valences) >= 3 and peak == 0:
        findings.append(ReviewFinding(
            "pacing", "info",
            f"情绪峰值在开篇场景，后续走低，注意是否虎头蛇尾：{curve_str}"))

    if not findings:
        findings.append(ReviewFinding(
            "pacing", "info",
            f"情绪曲线起伏健康（振幅 {amplitude}，标准差 {stdev:.1f}）：{curve_str}"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
