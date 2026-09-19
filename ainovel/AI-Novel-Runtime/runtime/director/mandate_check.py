"""mandate_check.py — the three anti-流水账 detectors (Phase 9.3, ADR-003).

These turn "the story is treading water" into COMPUTABLE, advisory signals over
the NarrativeMandate sequence (ROADMAP §13.3.2). Three checks, each keyed to one
of the mandate's four fields:

  1. 温水章 (lukewarm chapter) — why_now.cost_of_delay == "none": no time
     pressure, the protagonist could have waited. Warned PER chapter.
  2. 张力停滞 (tension stall)  — escalation.kind == "flat" for >= FLAT_RUN
     consecutive chapters: the conflict stopped rising.
  3. 原地打转 (spinning in place) — net_advance.irreversible == False for
     >= REVERSIBLE_RUN consecutive chapters: nothing irreversible advanced.

DISCIPLINE (mirrors serial_pacing.py / hook_check.py):
  - DETERMINISTIC: reads only the mandate fields — same mandates => same findings.
    No LLM, no network, no I/O.
  - EVALUATIVE, never gates (ADR-003): treading water is a judgment (a deliberate
    quiet arc exists), so ADVISORY. Reuses the ReviewReport shape.
  - Degrades to a clean info note when there are too few mandates to see a run.

The single-chapter twin (per-chapter cost_of_delay) rides the ChapterRun beside
pacing/density/ai_taste/hook/length; the cross-chapter runs (flat/reversible) are
folded over the whole produced sequence like check_serial_pacing.
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding

MANDATE_REVIEWER_ID = "mandate-check-v1"

# A flat escalation this many chapters running reads as a tension stall.
FLAT_RUN = 2
# A reversible net-advance this many chapters running reads as spinning in place.
REVERSIBLE_RUN = 3


def _longest_run(flags: List[bool]) -> int:
    """Length of the longest run of consecutive True flags."""
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def check_mandate_chapter(mandate: Optional[dict], *,
                          reviewer_id: str = MANDATE_REVIEWER_ID) -> ReviewReport:
    """Single-chapter 温水章 check: warn when this chapter's mandate carries no
    time pressure (why_now.cost_of_delay == 'none'). Advisory, deterministic,
    never gates. Rides the ChapterRun beside the other single-chapter detectors.
    A None mandate (a run without the mandate layer) => a clean skip info."""
    findings: List[ReviewFinding] = []
    if not mandate:
        findings.append(ReviewFinding(
            "mandate", "info", "本章无叙事强制令，跳过温水章分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    wn = mandate.get("why_now") or {}
    cod = wn.get("cost_of_delay")
    if cod == "none":
        findings.append(ReviewFinding(
            "mandate", "warning",
            "本章无时间压力（cost_of_delay=none），主角本可不必现在行动，疑似温水章——"
            "建议补一个「不能等」的触发（威胁/期限/代价）"))
    else:
        findings.append(ReviewFinding(
            "mandate", "info",
            f"本章存在行动紧迫性（cost_of_delay={cod}）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)


def check_mandate_series(mandates: List[dict], *,
                         reviewer_id: str = MANDATE_REVIEWER_ID) -> ReviewReport:
    """Cross-chapter 张力停滞 + 原地打转 check over the produced mandate sequence
    (chapter order). Warns when the conflict stops rising (escalation.kind flat
    for >= FLAT_RUN running) or nothing irreversible advances (net_advance.
    irreversible False for >= REVERSIBLE_RUN running). Deterministic, advisory,
    never gates. Fewer than 2 mandates => a clean info note."""
    seq = [m for m in mandates if isinstance(m, dict)]
    findings: List[ReviewFinding] = []
    total = len(seq)

    if total < 2:
        findings.append(ReviewFinding(
            "mandate-series", "info",
            "叙事强制令数量不足，跳过跨章张力/推进分析（未启用 mandate 或章节过少）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    flat_flags = [(m.get("escalation") or {}).get("kind") == "flat" for m in seq]
    rev_flags = [not (m.get("net_advance") or {}).get("irreversible", False)
                 for m in seq]
    ladder = "→".join(str((m.get("escalation") or {}).get("to_level")) for m in seq)

    # 1. tension stall — a run of flat escalations.
    flat_run = _longest_run(flat_flags)
    if flat_run >= FLAT_RUN:
        findings.append(ReviewFinding(
            "mandate-series", "warning",
            f"连续 {flat_run} 章冲突无升级（escalation=flat），张力停滞易致读者流失。"
            f"冲突阶梯：{ladder}"))

    # 2. spinning in place — a run of reversible net-advances.
    rev_run = _longest_run(rev_flags)
    if rev_run >= REVERSIBLE_RUN:
        findings.append(ReviewFinding(
            "mandate-series", "warning",
            f"连续 {rev_run} 章无不可逆推进（net_advance.irreversible=false），"
            f"主线原地打转，缺乏实质进展"))

    if not findings:
        climbs = sum(1 for a, b in zip(seq, seq[1:])
                     if (b.get("escalation") or {}).get("to_level", 0)
                     > (a.get("escalation") or {}).get("from_level", 0))
        findings.append(ReviewFinding(
            "mandate-series", "info",
            f"跨章张力健康（{climbs}/{total-1} 处升级，无长期停滞）。冲突阶梯：{ladder}"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)

