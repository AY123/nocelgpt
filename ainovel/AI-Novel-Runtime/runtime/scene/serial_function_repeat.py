"""serial_function_repeat.py — cross-chapter FUNCTION repetition (W11-03, ADR-003).

Where mandate_check judges whether the conflict keeps RISING and serial_pacing
judges the rhythm of climaxes, this judges whether chapters keep doing the SAME
STRUCTURAL JOB. A book where every chapter is "rising_action / reveal /
partial_payoff / flat escalation" reads as 原地打转 — the plot signature never
changes even as names and events do. The real genesis-pilot 33-ch baseline
(RUN-00025) had 25 consecutive chapters with an identical function signature; the
single-chapter detectors structurally cannot see it (each chapter has its
signature exactly once, never a within-chapter run).

It is the cross-chapter twin of mandate_check.check_mandate_series, built on the
model of serial_pacing.py / serial_humanization.py (fold over the produced
sequence). Three patterns, from the W11-03 scaffold:

  1. continuous_repeat — the SAME signature for >= CONTINUOUS_RUN consecutive
     chapters: the plot job stopped changing.
  2. cyclical_repeat — a signature recurs at a FIXED period (A B A B / A B C A B C)
     for >= CYCLE_REPEATS cycles: a rotating template, not real variety.
  3. renamed_same_function — chapters whose STRUCTURAL signature is identical but
     whose surface intent (plot_threads / character_focus) differs: 换名同功能,
     new dressing on the same beat.

DISCIPLINE (mirrors mandate_check.py / serial_pacing.py):
  - DETERMINISTIC: reads only the objective+mandate fields — same inputs => same
    findings. No LLM, no network, no I/O.
  - EVALUATIVE, never gates (ADR-003): a deliberately steady arc can repeat a
    function on purpose, so this is ADVISORY. Reuses the ReviewReport shape.
  - Degrades to a clean info note when there are too few chapters to see a run.
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding

FUNCTION_REPEAT_REVIEWER_ID = "function-repeat-check-v1"

# The same function signature this many chapters running reads as a stalled job.
# 3 = a pattern, consistent with mandate_check.FLAT_RUN family and the §14 "3 =
# a pattern" convention.
CONTINUOUS_RUN = 3
# A period-P cycle must repeat this many full cycles before it reads as a template.
CYCLE_REPEATS = 3
# Longest cycle period worth testing (a period longer than this over a short book
# is not distinguishable from noise).
MAX_CYCLE_PERIOD = 4


def _signature(objective: Optional[dict], mandate: Optional[dict]) -> tuple:
    """The structural function signature of one chapter: what JOB it does. Keyed on
    stable enum-like fields the generation chain already produces. Surface fields
    (plot_threads / character_focus) are deliberately EXCLUDED — they are what
    'renamed_same_function' varies while this stays fixed."""
    o = objective or {}
    m = mandate or {}
    commercial = o.get("commercial_intent") or {}
    return (
        o.get("pacing_role"),
        o.get("cliffhanger_type"),
        commercial.get("payoff_type"),
        (m.get("escalation") or {}).get("kind"),
    )


def _surface(objective: Optional[dict]) -> tuple:
    """The surface intent that SHOULD vary chapter to chapter even when the
    structural job is the same. Used to distinguish 'renamed_same_function' (same
    signature, different dressing) from a true duplicate."""
    o = objective or {}
    threads = o.get("plot_threads") or []
    focus = o.get("character_focus") or []
    norm = lambda xs: tuple(sorted(str(x) for x in xs)) if isinstance(xs, list) else (str(xs),)
    return (norm(threads), norm(focus))


def _longest_run(sigs: List[tuple]) -> tuple:
    """(length, start_index, signature) of the longest run of identical signatures."""
    best_len = best_start = 0
    best_sig = None
    i = 0
    n = len(sigs)
    while i < n:
        j = i
        while j + 1 < n and sigs[j + 1] == sigs[i]:
            j += 1
        if (j - i + 1) > best_len:
            best_len, best_start, best_sig = j - i + 1, i, sigs[i]
        i = j + 1
    return best_len, best_start, best_sig


def _detect_cycle(sigs: List[tuple]) -> Optional[tuple]:
    """Smallest period P (2..MAX_CYCLE_PERIOD) whose pattern repeats for >=
    CYCLE_REPEATS full cycles AND is not a single constant (that is continuous_
    repeat, reported separately). Returns (period, repeats) or None."""
    n = len(sigs)
    for period in range(2, MAX_CYCLE_PERIOD + 1):
        if n < period * CYCLE_REPEATS:
            continue
        block = sigs[:period]
        if len(set(block)) == 1:
            continue  # constant block is continuous, not cyclic
        full = period * CYCLE_REPEATS
        if all(sigs[k] == sigs[k % period] for k in range(full)):
            return period, CYCLE_REPEATS
    return None


def check_serial_function_repeat(
    chapters: List[dict], *,
    reviewer_id: str = FUNCTION_REPEAT_REVIEWER_ID,
) -> ReviewReport:
    """Fold the produced chapter sequence into a function-repetition read.

    `chapters` is an ordered list of {"objective": <dict|None>, "mandate":
    <dict|None>, "chapter_id": <str>} — chapter order is the list order. Warns on
    continuous_repeat / cyclical_repeat / renamed_same_function. Deterministic,
    advisory, never gates (ADR-003). Fewer than CONTINUOUS_RUN chapters => a clean
    info note."""
    seq = [c for c in chapters if isinstance(c, dict)]
    findings: List[ReviewFinding] = []
    total = len(seq)

    if total < CONTINUOUS_RUN:
        findings.append(ReviewFinding(
            "function-repeat", "info",
            "章节数量不足，跳过跨章功能重复分析（章节过少或未启用 objective/mandate）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    ids = [c.get("chapter_id") or f"#{i+1}" for i, c in enumerate(seq)]
    sigs = [_signature(c.get("objective"), c.get("mandate")) for c in seq]
    surfaces = [_surface(c.get("objective")) for c in seq]

    # 1. continuous_repeat — a run of identical signatures.
    run_len, run_start, run_sig = _longest_run(sigs)
    if run_len >= CONTINUOUS_RUN:
        span = f"{ids[run_start]}..{ids[run_start + run_len - 1]}"
        findings.append(ReviewFinding(
            "function-repeat", "warning",
            f"连续 {run_len} 章功能签名完全相同（{span}），章节在做同一件事，"
            f"疑似原地打转。签名(pacing/钩子/回报/升级)={run_sig}——"
            f"建议在其中插入功能变化（换钩子类型/推进不可逆回报/切换节奏角色）"))

    # 2. cyclical_repeat — a rotating template.
    cycle = _detect_cycle(sigs)
    if cycle:
        period, repeats = cycle
        findings.append(ReviewFinding(
            "function-repeat", "warning",
            f"功能签名以周期 {period} 循环出现（>= {repeats} 个周期），像是套模板轮转"
            f"而非真实变化——建议打破固定轮转节奏"))

    # 3. renamed_same_function — same signature, different surface dressing.
    # Count chapters sharing a signature with an earlier chapter but carrying a
    # DIFFERENT surface (plot_threads/character_focus): new names, same job.
    seen: dict = {}
    renamed = []
    for i, sig in enumerate(sigs):
        if sig in seen and surfaces[i] != seen[sig][1]:
            renamed.append((ids[seen[sig][0]], ids[i]))
        seen.setdefault(sig, (i, surfaces[i]))
    if renamed:
        sample = "; ".join(f"{a}≈{b}" for a, b in renamed[:3])
        more = f"（等 {len(renamed)} 处）" if len(renamed) > 3 else ""
        findings.append(ReviewFinding(
            "function-repeat", "warning",
            f"发现换名同功能：结构签名相同但线索/人物表面不同的章节 {sample}{more}——"
            f"表面换了包装，实际承担同一叙事功能"))

    if not findings:
        distinct = len(set(sigs))
        findings.append(ReviewFinding(
            "function-repeat", "info",
            f"跨章功能多样性健康（{total} 章，{distinct} 种不同功能签名，无长期重复）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
