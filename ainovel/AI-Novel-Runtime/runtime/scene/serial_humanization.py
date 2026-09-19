"""serial_humanization.py — cross-chapter opening-repetition check (ANES v2, ADR-003).

Where execution/humanization.py judges the AI-tells INSIDE one chapter, this
judges a tell that only shows ACROSS chapters: every chapter opening the same way.
A real DeepSeek baseline (genesis-pilot RUN-00018) opened three consecutive
chapters with "周洛铭睁开眼……" — a classic machine tic the single-chapter detector
structurally cannot see (each chapter has the opening only once, never a
within-chapter run). Readers feel the sameness immediately; this makes it
measurable.

It is the cross-chapter twin of execution/humanization.py, built on the model of
serial_pacing.py (which judges the SEQUENCE of per-chapter peaks). Same
discipline, one level up from the single chapter.

DISCIPLINE:
  - DETERMINISTIC: openings are strings, the analysis is counted — same bodies =>
    same findings. No LLM, no network.
  - EVALUATIVE, never gates (ADR-003): a deliberate structural echo (e.g. a diary
    序章) may repeat an opening on purpose, so this is ADVISORY. Reuses the
    ReviewReport shape (axis=evaluative, gating=False) so it rides the serial
    result like serial_pacing.
  - Degrades to a clean info note when there are too few chapters to see a pattern.
"""
from __future__ import annotations

import re
from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding
from ..execution.humanization import _sentences

# How many leading characters of the first sentence define "the opening". Long
# enough to capture a name + verb (周洛铭睁开眼) so it keys on the actual repeated
# clause, not just a recurring protagonist name; short enough to still match
# across small paraphrase (周洛铭睁开眼的时候 / 周洛铭睁开眼，看见 / 周洛铭睁开眼时).
OPENING_PREFIX_LEN = 6
# "3 = a pattern" — consistent with humanization.ANAPHORA_RUN_MAX and
# serial_pacing.DOLDRUMS_RUN. A run/cluster of this many shared openings warns.
REPEAT_RUN_MAX = 3
# 2 consecutive identical openings is a NUDGE, not an alarm: it may be a
# deliberate echo, but it is also the exact near-miss the real A/B exposed
# (v8 opened ch3+ch4 both "周洛铭睁开眼…" — 2 consecutive, so the run-of-3 warning
# never fired even though it read as the same AI tell). Reported at info so the
# detector's sensitivity matches the v9 prevention constraint, which fires on
# any recent repeat. See [[cross-chapter-opening-detector]].
REPEAT_RUN_NUDGE = 2

SERIAL_HUMANIZATION_REVIEWER_ID = "serial-opening-check-v1"


def _opening_prefix(body: str, prefix_len: int = OPENING_PREFIX_LEN) -> str:
    """The normalized opening of a chapter: the first real sentence's leading
    prefix_len characters, whitespace removed. Reuses humanization._sentences so
    the markdown chapter heading (# 第一章 …) is skipped and the first PROSE
    sentence is taken. Empty string for an empty/heading-only body."""
    sentences = _sentences(body or "")
    if not sentences:
        return ""
    first = re.sub(r"\s", "", sentences[0])
    return first[:prefix_len]


def _longest_repeat_run(prefixes: List[str]) -> tuple:
    """Longest run of CONSECUTIVE chapters sharing the same opening prefix, and
    that shared prefix. Empty prefixes never form a run."""
    best_len, best_pref = 1, ""
    run_len = 1
    for prev, cur in zip(prefixes, prefixes[1:]):
        if cur and prev == cur:
            run_len += 1
            if run_len > best_len:
                best_len, best_pref = run_len, cur
        else:
            run_len = 1
    return best_len, best_pref


def _largest_cluster(prefixes: List[str]) -> tuple:
    """The opening prefix shared by the MOST chapters anywhere in the run (not
    necessarily consecutive), and that count. Ties break on first-seen order."""
    counts: dict = {}
    for p in prefixes:
        if p:
            counts[p] = counts.get(p, 0) + 1
    if not counts:
        return 0, ""
    best_pref = max(counts, key=lambda k: counts[k])
    return counts[best_pref], best_pref


def check_serial_openings(chapter_bodies: List[str], *,
                          reviewer_id: str = SERIAL_HUMANIZATION_REVIEWER_ID) -> ReviewReport:
    """Analyze the cross-chapter sequence of chapter openings and return an
    ADVISORY report (ReviewReport: axis=evaluative, gating=False). Deterministic.

    `chapter_bodies` is the prose body of each chapter in chapter order. Fewer
    than 2 non-empty openings => a clean info note (nothing to compare)."""
    prefixes = [_opening_prefix(b) for b in chapter_bodies]
    non_empty = [p for p in prefixes if p]
    findings: List[ReviewFinding] = []

    if len(non_empty) < 2:
        findings.append(ReviewFinding(
            "serial-opening", "info",
            "章节数不足，跳过跨章开篇雷同分析（正文过少或为空）"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    total = len(non_empty)

    # 1. consecutive same-opening run — the strongest tell (the 睁开眼×3 case).
    #    >=3 consecutive = warning (a clear AI tell); exactly 2 = info nudge (may
    #    be a deliberate echo, but it is the near-miss the real A/B exposed).
    run_len, run_pref = _longest_repeat_run(prefixes)
    if run_len >= REPEAT_RUN_MAX:
        findings.append(ReviewFinding(
            "serial-opening", "warning",
            f"连续 {run_len} 章以相同开篇“{run_pref}…”起笔，"
            f"跨章开篇雷同是典型 AI 腔，建议换用动作/对话/场景等不同入场方式"))
    elif run_len == REPEAT_RUN_NUDGE:
        findings.append(ReviewFinding(
            "serial-opening", "info",
            f"连续 {run_len} 章以相同开篇“{run_pref}…”起笔，"
            f"尚不构成明显雷同，但注意下一章换一种入场方式"))

    # 2. largest scattered cluster — many chapters keying on one opening even if
    #    not consecutive still reads as a template. Skip it only when finding 1
    #    already reported that exact prefix (a consecutive run of the same opening).
    cluster_n, cluster_pref = _largest_cluster(prefixes)
    already_reported = run_len >= REPEAT_RUN_MAX and cluster_pref == run_pref
    if cluster_n >= REPEAT_RUN_MAX and not already_reported:
        findings.append(ReviewFinding(
            "serial-opening", "warning",
            f"{cluster_n}/{total} 章以“{cluster_pref}…”开篇，开篇模板化，"
            f"建议丰富入场方式"))

    if not findings:
        findings.append(ReviewFinding(
            "serial-opening", "info",
            f"跨章开篇多样（{total} 章开篇无明显雷同）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)


# --- prevention side (detection→prevention lower half) ----------------------
# How many chapters back the generation-time constraint looks, and how much of
# each opening to show the model (a full-ish first sentence reads better than a
# 6-char prefix when the goal is "don't write like THIS", not "did it repeat").
RECENT_OPENINGS_WINDOW = 3
OPENING_SNIPPET_CHARS = 40


def _opening_snippet(body: str, max_chars: int = OPENING_SNIPPET_CHARS) -> str:
    """The chapter's first prose sentence, capped — shown to the model as an
    example to vary AWAY from. Skips the markdown heading via _sentences."""
    sentences = _sentences(body or "")
    if not sentences:
        return ""
    first = sentences[0].strip()
    return first[:max_chars]


def render_recent_openings(chapter_bodies: List[str], *,
                           window: int = RECENT_OPENINGS_WINDOW) -> str:
    """Render the openings of the last `window` produced chapters into a
    generation-time diversity constraint block. Deterministic. The caller passes
    ONLY prior chapters (fold cursor), so the current chapter never leaks in.

    Returns a stable sentinel when there are no prior openings (the opening
    chapter), so the v9 prompt slot always binds to a non-empty string."""
    snippets = [s for s in (_opening_snippet(b) for b in chapter_bodies[-window:]) if s]
    if not snippets:
        return "（本章为开篇或暂无前章，开篇方式不受约束）"
    lines = [f"- 第 {i} 近章开篇：「{s}…」" for i, s in enumerate(reversed(snippets), 1)]
    return ("最近 {n} 章的开篇如下，本章开头必须与它们明显不同——"
            "换一种入场方式（动作/对话/场景/悬念/时间跳切等），"
            "不要重复相同的主语起手或句式：\n{lines}").format(
                n=len(snippets), lines="\n".join(lines))
