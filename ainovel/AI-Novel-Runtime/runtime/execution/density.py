"""density.py — single-chapter information-density check (ANES v2, ADR-003).

The §14 real-baseline finding, made into a guard: the DeepSeek chapter opened
with ~1/3 of its words as zero-information atmosphere ("暮色如铁锈 / 寒风如刀"),
where Claude conveyed the same setup in two concrete details. That reads as 注水
to a web-novel audience and it shows up in the FIRST chapter — before any
cross-chapter planning could help. This checker quantifies it DETERMINISTICALLY.

It is the twin of scene/pacing.py: same discipline, different signal. Pacing
analyzes the LLM-enriched emotion CURVE; density analyzes the DRAFT BODY TEXT
directly, so it works on ANY draft (no enrichment needed) and for any prompt
version.

Three deterministic signals:
  1. dialogue_ratio     — quoted chars / total chars. Too low reads as narration
                          pile-up with no scene (a 注水 signature).
  2. simile_per_1000    — simile/atmosphere markers per 1000 chars. Too high is
                          the "暮色如铁锈" adjective-stacking problem.
  3. frontload_skew     — concreteness (dialogue + proper-noun chars) of the
                          first third vs the rest. A first third far less
                          concrete than the body is the §14 front-loaded-mood
                          opening.

DISCIPLINE:
  - DETERMINISTIC: every signal is counted from the text, not judged — same body
    => same findings.
  - EVALUATIVE, never gates (ADR-003): a quiet atmospheric passage may be a
    deliberate choice, so this is ADVISORY. It reuses the ReviewReport shape
    (axis=evaluative, gating=False) so it rides the envelope like check_pacing.
  - Reads only the body string. No package, no state, no model, no I/O.
"""
from __future__ import annotations

import re
from typing import List, Optional

from .draft_review import ReviewReport, ReviewFinding

# Quoted-speech spans, across the quote styles web-novel prose actually uses:
# straight ASCII, CJK corner brackets, and curly doubles. Non-greedy, capped so a
# single unmatched quote can't swallow the whole chapter.
_DIALOGUE_RE = re.compile(
    r'"[^"\n]{1,400}"'          # ASCII straight
    r'|“[^”\n]{1,400}”'          # curly double
    r'|「[^」\n]{1,400}」'        # CJK corner
    r'|『[^』\n]{1,400}』'        # CJK white corner
)

# Simile / atmosphere markers. CJK comparatives + the common English ones. These
# are the words that carry "X 如/像 Y" atmosphere sentences.
_SIMILE_TOKENS_CJK = ("如同", "仿佛", "宛如", "犹如", "好似", "似的", "像是")
# bare 如 / 像 are counted too but only as standalone comparative use — see below.
_SIMILE_RE_CJK = re.compile("|".join(_SIMILE_TOKENS_CJK) + r"|(?<![一-龥])[如像](?=[一-龥])")
_SIMILE_RE_EN = re.compile(r"\b(?:like|as if|as though)\b", re.IGNORECASE)

# Conservative thresholds — warn on the clearly-bad, not the merely quiet
# (ADR-003: advisory must not cry wolf). Initial values; tune against real data.
DIALOGUE_FLOOR = 0.05        # < 5% of chars in dialogue reads as narration-only
SIMILE_PER_1000 = 8.0        # more than this per 1000 chars is atmosphere-stacking
# Front-loaded mood: the OPENING third stacks atmosphere (simile/比喻) far denser
# than the rest — the §14 "暮色如铁锈 / 寒风如刀" opening that delays the story.
# Signal is the opening's simile CONCENTRATION vs the rest's, which is
# language-robust (counts the same markers CJK+EN) — unlike a "concreteness"
# proxy, which cannot measure CJK narration (no case/token cues) and false-fired
# on every Chinese chapter (real-run finding 2026-07-06).
FRONTLOAD_OPENING_SIMILE = 8.0   # opening simile/1000 must itself be high to flag
FRONTLOAD_RATIO = 2.0            # AND be >=2x the rest's concentration
FRONTLOAD_MIN_CHARS = 800        # below this the thirds are too small to compare

DENSITY_REVIEWER_ID = "density-check-v1"


def _dialogue_chars(text: str) -> int:
    return sum(len(m) for m in _DIALOGUE_RE.findall(text))


def _simile_count(text: str) -> int:
    return len(_SIMILE_RE_CJK.findall(text)) + len(_SIMILE_RE_EN.findall(text))


def _simile_per_1000(text: str) -> float:
    """Simile/atmosphere-marker concentration per 1000 chars. Language-robust: it
    counts the same CJK+EN markers everywhere, so it measures the SHAPE of the
    prose (how atmosphere-heavy it is), not its language. This is the frontload
    signal — the opening's concentration vs the rest's."""
    n = len(text)
    if n == 0:
        return 0.0
    return _simile_count(text) / n * 1000


def _thirds(text: str) -> List[str]:
    """Split into three roughly equal char-length slices, on paragraph-ish
    boundaries where possible so a slice doesn't cut mid-sentence. Deterministic."""
    n = len(text)
    if n < 3:
        return [text, "", ""]
    return [text[: n // 3], text[n // 3: 2 * n // 3], text[2 * n // 3:]]


def density_summary(body: str) -> Optional[dict]:
    """Reduce a draft body to its numeric density shape. Returns None for an empty
    body (nothing to measure). Deterministic — mirrors curve_summary."""
    text = (body or "").strip()
    if not text:
        return None
    total = len(text)
    dialogue = _dialogue_chars(text)
    similes = _simile_count(text)
    first, second, third = _thirds(text)
    rest = second + third
    return {
        "total_chars": total,
        "dialogue_ratio": round(dialogue / total, 4),
        "simile_per_1000": round(similes / total * 1000, 2),
        "opening_simile_per_1000": round(_simile_per_1000(first), 2),
        "rest_simile_per_1000": round(_simile_per_1000(rest), 2),
    }


def check_density(artifact: dict, *, reviewer_id: str = DENSITY_REVIEWER_ID) -> ReviewReport:
    """Analyze a draft body's information density and return an ADVISORY report
    (ReviewReport: axis=evaluative, gating=False). Deterministic. Emits a clean
    info note when there's nothing to flag, so 'checked, nothing flagged' is
    distinguishable from 'never checked'."""
    body = artifact.get("body", "")
    summary = density_summary(body)
    findings: List[ReviewFinding] = []

    if summary is None:
        findings.append(ReviewFinding(
            "density", "info", "正文为空，跳过信息密度分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    if summary["dialogue_ratio"] < DIALOGUE_FLOOR:
        findings.append(ReviewFinding(
            "density", "warning",
            f"对白占比过低（{summary['dialogue_ratio']:.1%}<{DIALOGUE_FLOOR:.0%}），"
            f"全章以叙述堆积为主、缺少场景与人物交锋，易读作注水"))

    if summary["simile_per_1000"] > SIMILE_PER_1000:
        findings.append(ReviewFinding(
            "density", "warning",
            f"比喻/氛围句密度偏高（每千字 {summary['simile_per_1000']:.1f}>"
            f"{SIMILE_PER_1000:.0f}），警惕「暮色如铁锈」式形容词堆砌、信息增量低"))

    # Front-loaded mood: the opening third stacks atmosphere (simile/比喻) both
    # in ABSOLUTE terms and RELATIVE to the rest. Both conditions guard against a
    # false positive — a uniformly atmospheric book won't trip on the ratio, and
    # a lightly-figurative opening won't trip on the absolute floor. Language-
    # robust (simile markers are counted identically CJK+EN).
    oc, rc = summary["opening_simile_per_1000"], summary["rest_simile_per_1000"]
    if (summary["total_chars"] >= FRONTLOAD_MIN_CHARS
            and oc >= FRONTLOAD_OPENING_SIMILE
            and oc >= max(rc, 0.1) * FRONTLOAD_RATIO):
        findings.append(ReviewFinding(
            "density", "warning",
            f"开篇氛围/比喻堆砌（前1/3每千字 {oc:.1f} 比喻，为后段 {rc:.1f} 的"
            f"{oc / rc if rc else 99:.1f} 倍），黄金开篇迟迟不进入正题、信息增量低"))

    if not findings:
        findings.append(ReviewFinding(
            "density", "info",
            f"信息密度健康（对白占比 {summary['dialogue_ratio']:.1%}，"
            f"每千字比喻 {summary['simile_per_1000']:.1f}）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
