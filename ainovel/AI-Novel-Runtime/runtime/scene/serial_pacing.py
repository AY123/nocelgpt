"""serial_pacing.py — cross-chapter pacing check (ANES v2, ADR-003).

Where pacing.py judges ONE chapter's emotion curve, this judges the RHYTHM OF
CLIMAXES ACROSS A SERIAL: the sequence of per-chapter PEAK valences. That
sequence is a web-novel's retention heartbeat — readers drop when the climaxes
stop coming (prolonged doldrums) or bunch up and leave a long flat stretch
(clustering), or when the gap between highs drifts past the cadence the author
promised (reward_loop.cadence_chapters).

DISCIPLINE:
  - DETERMINISTIC: peaks are numbers, the analysis is computed — same peaks (and
    same cadence) => same findings. No LLM, no network.
  - EVALUATIVE, never gates (ADR-003): serialization pacing is a judgment (a long
    quiet arc may be a deliberate build-up), so it is ADVISORY. Reuses the
    ReviewReport shape.
  - Degrades to a clean info note when there are too few chapters to see a
    rhythm.
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding

# What reads as a "low" climax and how long a run of them reads as doldrums.
LOW_PEAK = 60             # a chapter whose peak never clears this had no real high
DOLDRUMS_RUN = 3          # this many consecutive low-peak chapters = 断更风险
# Cadence tolerance: the real gap between climaxes may exceed the authored
# cadence by this factor before we warn (conservative — advisory, ADR-003).
CADENCE_SLACK = 2


SERIAL_PACING_REVIEWER_ID = "serial-pacing-check-v1"


def _climax_indices(peaks: List[int], threshold: int) -> List[int]:
    """Chapter indices (1-based) whose peak clears the climax threshold — the
    chapters that actually delivered a high."""
    return [i + 1 for i, p in enumerate(peaks) if p >= threshold]


def _longest_low_run(peaks: List[int], threshold: int) -> int:
    """Length of the longest run of consecutive chapters whose peak stayed below
    the climax threshold (the longest stretch with no real high)."""
    best = run = 0
    for p in peaks:
        run = run + 1 if p < threshold else 0
        best = max(best, run)
    return best


def _max_climax_gap(climaxes: List[int], total: int) -> int:
    """The largest gap (in chapters) between consecutive climaxes, also counting
    the lead-in from chapter 1 and the tail after the last climax — a long dry
    tail is as much a risk as a long dry middle."""
    if not climaxes:
        return total
    gaps = [climaxes[0]]                                    # lead-in from ch 1
    gaps += [b - a for a, b in zip(climaxes, climaxes[1:])]  # between climaxes
    gaps.append(total - climaxes[-1])                        # tail
    return max(gaps)



def check_serial_pacing(chapter_peaks: List[int], *, cadence: Optional[int] = None,
                        reviewer_id: str = SERIAL_PACING_REVIEWER_ID) -> ReviewReport:
    """Analyze the cross-chapter peak-valence sequence and return an ADVISORY
    report (ReviewReport: axis=evaluative, gating=False). Deterministic.

    `chapter_peaks` is the per-chapter climax height in chapter order. `cadence`
    is the authored `reward_loop.cadence_chapters` (how often a payoff was
    promised); when given, a climax gap exceeding cadence * CADENCE_SLACK is
    flagged. Fewer than 2 peaks => a clean info note (nothing to judge)."""
    peaks = [p for p in chapter_peaks if isinstance(p, int)]
    findings: List[ReviewFinding] = []
    total = len(peaks)

    if total < 2:
        findings.append(ReviewFinding(
            "serial-pacing", "info",
            "章节峰值数据不足，跳过连载节奏分析（未增强或章节过少）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    seq = "→".join(str(p) for p in peaks)
    climaxes = _climax_indices(peaks, LOW_PEAK)

    # 1. prolonged doldrums — a long run with no real climax.
    low_run = _longest_low_run(peaks, LOW_PEAK)
    if low_run >= DOLDRUMS_RUN:
        findings.append(ReviewFinding(
            "serial-pacing", "warning",
            f"连续 {low_run} 章无高潮（峰值均<{LOW_PEAK}），长期低迷易致弃书：{seq}"))

    # 2. no climax at all across the run.
    if not climaxes:
        findings.append(ReviewFinding(
            "serial-pacing", "warning",
            f"全程无一章达到高潮阈值（峰值<{LOW_PEAK}），缺乏爽点支撑追读：{seq}"))

    # 3. cadence violation — the largest climax gap drifts past the promised rhythm.
    if cadence and cadence >= 1:
        gap = _max_climax_gap(climaxes, total)
        if gap > cadence * CADENCE_SLACK:
            findings.append(ReviewFinding(
                "serial-pacing", "warning",
                f"高潮间隔最大 {gap} 章，超出声明节奏 {cadence} 章（reward_loop）"
                f"的 {CADENCE_SLACK} 倍容差，节律偏离：{seq}"))

    # 4. clustering — climaxes exist but bunch into a short span, leaving a long
    #    flat remainder (only meaningful with several climaxes).
    if len(climaxes) >= 2:
        span = climaxes[-1] - climaxes[0] + 1
        if span <= total / 2 and (total - span) >= DOLDRUMS_RUN:
            findings.append(ReviewFinding(
                "serial-pacing", "info",
                f"高潮集中在第 {climaxes[0]}–{climaxes[-1]} 章的 {span} 章内，"
                f"其余 {total - span} 章较平，注意高潮扎堆：{seq}"))

    if not findings:
        findings.append(ReviewFinding(
            "serial-pacing", "info",
            f"连载高潮节律健康（{len(climaxes)}/{total} 章达高潮）：{seq}"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
