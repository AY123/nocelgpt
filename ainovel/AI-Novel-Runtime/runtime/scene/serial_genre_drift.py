"""serial_genre_drift.py — cross-chapter genre-drift check (ANES v2, ADR-003).

The fourth cross-chapter twin, after serial_pacing (sequence of peaks),
serial_humanization (sequence of openings) and serial_function_repeat (sequence
of chapter functions). This one judges the sequence of GENRE-MARKER DENSITY.

WHY IT EXISTS:
QIDIAN_SUBGENRE_DEEP_DIVE.md §4.3 documents a degradation gradient —
异世大陆/武侠/仙侠/高武世界 all slide toward generic 东方玄幻, which slides toward
undifferentiated 升级爽文. The mechanism belongs to the model, not the author:
玄幻 is the most-represented genre in the training prior, so with no active
constraint the prose drifts there. The observable consequence is that chapter 30
reads LESS like its declared subgenre than chapter 3 did.

No existing detector can see this. The single-chapter family (density, ai_taste,
pacing, hook) is blind by construction — each measures ONE chapter, and a
uniformly drifted book looks locally fine in every chapter. serial_humanization
folds across chapters but keys on openings only. Genre drift is a TREND in a
book-level signal, so it needs a book-level fold.

WHAT IT MEASURES:
Per chapter, the density of that genre's discriminant markers (per 1000 chars,
see genre_taxonomy._GENRE_MARKERS). Then three reads over the sequence:
  1. TREND — first third vs last third. A large drop = the drift signature.
  2. FLOOR — chapters with (near-)zero markers = locally genre-less chapters.
  3. LEVEL — a whole book below the floor = it never established the genre
     (a different defect from drifting away, so it is reported differently).

HONEST LIMITATION (do not oversell a finding):
Marker density is a PROXY for genre fidelity, not a measure of it. Prose can keep
a genre's substance in different words, or stuff markers while delivering nothing.
So this is a smoke alarm that points a human at a chapter range — never a verdict,
never a gate.

DISCIPLINE:
  - DETERMINISTIC: counting substrings in bodies. Same bodies + same genre =>
    same findings. No LLM, no network.
  - EVALUATIVE, never gates (ADR-003). Reuses the ReviewReport shape
    (axis=evaluative, gating=False) so it rides the serial result like its twins.
  - Degrades to a clean info note on: unknown genre (no marker table), too few
    chapters to see a trend, or empty bodies. Never raises, never blocks.
  - Reads only the draft body — no draft bytes are modified, so content_hash is
    untouched.
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.draft_review import ReviewReport, ReviewFinding
from ..genre_taxonomy import markers_for_genre

# Minimum chapters before a TREND is meaningful. Three thirds of >=2 chapters
# each: below this, one atypical chapter dominates a third and the "trend" is
# noise. Consistent with the family's "don't judge what you can't see" habit
# (humanization.CV_MIN_SENTENCES, density.FRONTLOAD_MIN_CHARS).
TREND_MIN_CHAPTERS = 6

# Chapters shorter than this are excluded from the density series: a 200-char
# stub's density swings wildly on one word and would forge a fake trend.
MIN_CHAPTER_CHARS = 500

# Relative drop (last third vs first third) that reads as drift. 0.4 = the last
# third carries under 60% of the opening third's marker density. Deliberately
# coarse — this is a proxy, so a tight threshold would imply false precision.
DRIFT_DROP_RATIO = 0.4

# Median density below which the book never established ANY genre vocabulary.
# Absolute on purpose: this asks "is there a vocabulary at all", and at ~0.5/千字
# a 3000-char chapter carries ~1 marker total, which no genre commitment survives.
GENRELESS_FLOOR = 0.5

# Per-chapter outliers are judged RELATIVE to the book's own median, not against
# an absolute number. Measured reason: with book-specific markers the absolute
# scale is meaningless — the real baseline's coinages run 1.6–9.6/千字 while stock
# genre words on the same prose run 0.0–1.1, so one fixed floor either flags
# everything in the second case (it flagged 31/33) or nothing in the first. 0.25 =
# a chapter carrying under a quarter of the book's typical genre vocabulary.
GENRELESS_RELATIVE = 0.25

# How many outlier chapters to name in a finding before summarizing.
MAX_LISTED_CHAPTERS = 5

SERIAL_GENRE_DRIFT_REVIEWER_ID = "serial-genre-drift-check-v1"


def marker_density(body: str, markers: List[str]) -> float:
    """Genre markers per 1000 chars of body. Counts every occurrence (a chapter
    leaning hard on one marker is still engaging the genre's vocabulary).
    Returns 0.0 for an empty body — callers filter short bodies out first."""
    text = body or ""
    if not text:
        return 0.0
    hits = sum(text.count(m) for m in markers)
    return round(hits * 1000.0 / len(text), 3)


def _median(values: List[float]) -> float:
    """Median of a non-empty series. Median rather than mean because the density
    distribution is right-skewed — the real baseline had chapters at 9.6/千字
    against a typical 3, and a mean lets those few pull the 'normal' level up,
    which would then flag healthy chapters as outliers."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _thirds(values: List[float]) -> tuple:
    """Split a series into (first_third, last_third) means. The middle third is
    intentionally discarded: the comparison of interest is start vs end, and
    including the middle in either side blurs exactly the signal we want."""
    n = len(values)
    cut = max(1, n // 3)
    first = values[:cut]
    last = values[-cut:]
    return (sum(first) / len(first), sum(last) / len(last))


def check_serial_genre_drift(chapter_bodies: List[str], genre: Optional[str], *,
                             authored_markers: Optional[List[str]] = None,
                             reviewer_id: str = SERIAL_GENRE_DRIFT_REVIEWER_ID
                             ) -> ReviewReport:
    """Analyze the cross-chapter genre-marker density series and return an
    ADVISORY report (ReviewReport: axis=evaluative, gating=False). Deterministic.

    `chapter_bodies` is the prose body of each chapter in chapter order; `genre`
    is the declared genre (brain.genre.primary / outline.genre[0]).

    `authored_markers` are the book's OWN coined terms
    (genre_taxonomy.extract_authored_markers). When present they take priority
    over the stock genre table, because a book's genre identity lives in its own
    vocabulary — measured on the real 33-chapter baseline, the stock 都市 table
    scored 20 hits across ~177k chars and called 31/33 chapters genre-less, while
    the book's coinages (梦墟/核心执念/梦晶) appeared ~1400 times with a stable
    rising density. The stock table is the fallback for books that coined nothing.

    No markers at all, or too few analyzable chapters, degrades to a clean info note.
    """
    findings: List[ReviewFinding] = []
    # .strip() matters: a whitespace-only entry is truthy, and letting it through
    # would count str.count(" ") on every body — a huge fake density.
    authored = [m for m in (authored_markers or []) if m and m.strip()]
    markers = authored or markers_for_genre(genre)
    shown_genre = (genre or "未声明").strip() or "未声明"
    # Findings must say WHICH vocabulary was measured — a reader can only judge a
    # density number if they know what was counted.
    label = "作品自有术语" if authored else f"{shown_genre}通用词"

    if not markers:
        findings.append(ReviewFinding(
            "serial-genre-drift", "info",
            f"题材「{shown_genre}」无判别式词表，且作品未声明自有术语，"
            f"跳过跨章题材漂移分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    # Index-preserving so findings can name real chapter numbers (1-based).
    series = [(i, marker_density(b, markers))
              for i, b in enumerate(chapter_bodies or [], start=1)
              if b and len(b) >= MIN_CHAPTER_CHARS]

    if len(series) < TREND_MIN_CHAPTERS:
        findings.append(ReviewFinding(
            "serial-genre-drift", "info",
            f"可分析章节不足 {TREND_MIN_CHAPTERS} 章（当前 {len(series)} 章），"
            f"跳过跨章题材漂移分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    densities = [d for _, d in series]
    total = len(series)
    overall = round(sum(densities) / total, 3)
    first_mean, last_mean = _thirds(densities)

    median = _median(densities)

    # 1. LEVEL — the book never established a genre vocabulary at all. Checked
    #    FIRST because when it holds, the trend and per-chapter reads below are
    #    noise on top of near-zero and would just repeat the same defect.
    #
    #    It requires the OPENING THIRD to be weak too, not just the median. A book
    #    that opens strong and fades has a low median once the faded majority
    #    outnumbers the strong opening (3 dense + 6 empty chapters => median 0),
    #    but that is DRIFT — the more specific and more actionable finding — and
    #    reporting it as "never established" both mislabels it and suppresses the
    #    trend message. "Never established" means it was never there, including at
    #    the start; on the real baseline's stock-word path both were ~0 (first
    #    third 0.08, median 0.00), which is the case this branch is for.
    if median < GENRELESS_FLOOR and first_mean < GENRELESS_FLOOR:
        findings.append(ReviewFinding(
            "serial-genre-drift", "warning",
            f"全书{label}密度偏低（中位 {median:.2f}/千字，均值 {overall:.2f}），"
            f"题材特征自始未确立，而非中途漂移"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    # 2. TREND — the drift signature this module exists to catch.
    if first_mean > 0:
        drop = (first_mean - last_mean) / first_mean
        if drop >= DRIFT_DROP_RATIO:
            findings.append(ReviewFinding(
                "serial-genre-drift", "warning",
                f"题材特征衰减：{label}密度从前三分之一的 "
                f"{first_mean:.2f}/千字 降到后三分之一的 {last_mean:.2f}/千字"
                f"（降幅 {drop:.0%}）。后段正文正在脱离「{shown_genre}」的题材承诺，"
                f"向通用升级流漂移，建议回看后段章节是否仍在兑现本题材的判别式要素"))

    # 3. OUTLIERS — chapters that fell off the BOOK'S OWN norm. Relative to the
    #    book's median, not an absolute number: with book-specific markers an
    #    absolute floor is meaningless (a book coining one heavily-used term sits
    #    an order of magnitude above one coining five rare ones). Same
    #    comparison-only discipline the retention curve and reference bands use.
    cutoff = median * GENRELESS_RELATIVE
    genreless = [i for i, d in series if d < cutoff]
    if genreless:
        shown = "、".join(f"第{i}章" for i in genreless[:MAX_LISTED_CHAPTERS])
        more = f" 等 {len(genreless)} 章" if len(genreless) > MAX_LISTED_CHAPTERS else ""
        findings.append(ReviewFinding(
            "serial-genre-drift", "warning",
            f"{shown}{more}的{label}密度低于全书中位的 {GENRELESS_RELATIVE:.0%}"
            f"（<{cutoff:.2f}/千字，中位 {median:.2f}），"
            f"这些章节读起来与题材关联薄弱，"
            f"建议确认它们是否仍在推进本题材的核心机制"))

    if not findings:
        findings.append(ReviewFinding(
            "serial-genre-drift", "info",
            f"题材特征稳定（{label}密度中位 {median:.2f}/千字，"
            f"前段 {first_mean:.2f} → 后段 {last_mean:.2f}，{total} 章）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
