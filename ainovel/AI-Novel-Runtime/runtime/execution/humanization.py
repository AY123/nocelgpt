"""humanization.py — single-chapter "AI 味" (AI-tell) detection (ANES v2, ADR-003).

The §14 real-baseline finding, made into an advisory guard: the DeepSeek chapter
read as visibly machine-written — parallel-structure stacking ("He had not eaten
in four days. He had not slept in five."), nested em-dash asides ("the wound in
his side—the one he'd bound...—throbbed"), and a monotone sentence rhythm. These
are the tells a human editor spots instantly; this module makes them measurable.

It is the THIRD twin of scene/pacing.py and execution/density.py: same
discipline, different signal. density measures WHAT the prose carries (dialogue /
simile / front-loaded mood); this measures HOW the sentences are BUILT (syntactic
tells), so the two never overlap.

This file is the home of the whole Humanization Engine. v1 is DETECTION only; the
later halves — targeted de-AI rewrite (feeds revise_until) and generation-time
prevention (a prompt constraint) — will land here, both consuming this detector's
output as their input.

Three deterministic signals (bilingual — CJK and English both):
  1. anaphora_run       — the longest run of consecutive sentences that START the
                          same way. The strongest, most language-robust LLM tell.
  2. dash_aside_per_1000 — density of em-dash parenthetical asides ("—...—").
  3. sentence_length_cv — coefficient of variation of sentence length. Too low =
                          monotone rhythm, the machine lack of human burstiness.

DISCIPLINE:
  - DETERMINISTIC: every signal is counted/computed from the text — same body =>
    same findings.
  - EVALUATIVE, never gates (ADR-003): a deliberately incantatory passage may use
    anaphora on purpose, so this is ADVISORY. Reuses the ReviewReport shape
    (axis=evaluative, gating=False) so it rides the envelope like check_pacing.
  - Reads only the body string. No package, state, model, or I/O.
"""
from __future__ import annotations

import re
from typing import List, Optional

from .draft_review import ReviewReport, ReviewFinding

# Conservative thresholds — warn on the clearly-machine, not the merely rhythmic
# (ADR-003: advisory must not cry wolf). Initial values; tune against real data.
ANAPHORA_RUN_MAX = 3          # >=3 consecutive same-opening sentences reads as stacking
DASH_ASIDE_PER_1000 = 5.0     # em-dash asides per 1000 chars above this = nested-aside tic
SENTENCE_CV_FLOOR = 0.35      # length CV below this = monotone, non-human rhythm
CV_MIN_SENTENCES = 8          # below this the CV is too noisy to judge

AI_TASTE_REVIEWER_ID = "ai-taste-check-v1"

# Sentence terminators, both scripts. A run of terminators counts once.
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?\.]+[\s”」』\"']*|\n+")

# An em-dash aside: a span opened and closed by a dash run (CJK 破折号 —— or the
# ASCII/unicode em dash —), non-greedy, capped so one stray dash can't span the
# whole chapter.
_DASH_ASIDE_RE = re.compile(r"(?:——|—|--)[^—\n]{1,120}(?:——|—|--)")


def _sentences(text: str) -> List[str]:
    """Split bilingual prose into sentences. Drops markdown headings/blank lines
    and whitespace-only fragments. Deterministic."""
    out: List[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):   # skip headings/blank lines
            continue
        for frag in _SENTENCE_SPLIT_RE.split(s):
            # Strip quote/emphasis wrappers AND bracket-panel delimiters (【】〔〕):
            # a run of system-panel lines (【扫描启动】【匹配度:0%】…), a common
            # 玄幻/系统流 device, otherwise all key on 「【」 and register as a false
            # anaphora run — the detector targets prose heads (他…他…他), not UI.
            f = frag.strip().strip("*_>—-「」『』【】〔〕\"'“” ")
            if f:
                out.append(f)
    return out


def _opening(sentence: str) -> str:
    """The sentence's 'head unit' for anaphora detection: the first word for
    latin script, the first CJK character otherwise (a pro-drop subject like 他
    is one char — two-char keying would miss 他…他…他). Lowercased so 'He'/'he'
    match. Empty string when there's nothing to key on."""
    s = sentence.strip()
    if not s:
        return ""
    m = re.match(r"[A-Za-z]+", s)
    if m:
        return m.group(0).lower()
    # CJK (or mixed): the first non-space character — the script's "first token",
    # symmetric with taking the first WORD for latin script. In a pro-drop
    # language, 3+ consecutive sentences with the same explicit-subject head
    # (他…他…他) reads as the same monotone tell as English anaphora.
    cjk = re.sub(r"\s", "", s)
    # Enumeration ordinals (第一…第二…第三…) are a LIST device, not the monotone
    # subject-drop tell — keying on the bare 第 collided all list items into a
    # false run (RUN-00001 ch8 "第一道/第二道/第三道", ch14 "第一个/第二个/第三个").
    # Key on 第+ordinal so the items self-distinguish; a genuine 第X…第X…第X repeat
    # (same ordinal) still keys the same and is correctly caught.
    m2 = re.match(r"第[一二三四五六七八九十百千两0-9]+", cjk)
    if m2:
        return m2.group(0)
    return cjk[:1]


def _longest_anaphora_run(sentences: List[str]) -> tuple:
    """Longest run of consecutive sentences sharing an opening, and how many
    sentences that run spans. Runs of trivial/empty openings are ignored."""
    best_len = 1
    best_open = ""
    run_len = 1
    for prev, cur in zip(sentences, sentences[1:]):
        po, co = _opening(prev), _opening(cur)
        if po and po == co:
            run_len += 1
            if run_len > best_len:
                best_len, best_open = run_len, co
        else:
            run_len = 1
    return best_len, best_open


def locate_anaphora_run(body: str, *, max_sentences: int = 4) -> List[str]:
    """The actual sentences composing the longest same-opening run — the LOCATION
    behind the anaphora_run COUNT. A rewrite instruction that only states the metric
    ("最长 3 句同头") makes the model hunt for the offenders and, on a borderline
    (3-sentence) run, it often skips them (observed in the tighten0716 A/B: ch3's
    3-run survived an instruction byte-identical to ch1's 5-run that was fixed).
    Quoting the specific sentences back removes the "can't find them" failure mode.
    Deterministic; empty list when no run reaches ANAPHORA_RUN_MAX. Reuses the same
    _sentences / _opening primitives as the detector, so the located run is exactly
    the one that was counted (no drift)."""
    sentences = _sentences(body or "")
    if len(sentences) < ANAPHORA_RUN_MAX:
        return []
    best_start, best_len = 0, 1
    run_start, run_len = 0, 1
    for i in range(1, len(sentences)):
        po, co = _opening(sentences[i - 1]), _opening(sentences[i])
        if po and po == co:
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_start, run_len = i, 1
    if best_len < ANAPHORA_RUN_MAX:
        return []
    return sentences[best_start:best_start + min(best_len, max_sentences)]


def locate_anaphora_spans(body: str, *, max_sentences: int = 4) -> List[dict]:
    """Phase 1 Task 1.2.1: Enhanced anaphora locator with char offsets.

    Returns detailed span information for the longest anaphora run, including:
    - sentence_index: index in the sentence list
    - text: the actual sentence text
    - char_offset: character position in the original body
    - pattern: the opening pattern (e.g., "他", "he")

    This enables quantified rewrite instructions that cite exact locations:
    "第5-7句出现同头排比（他...），位于第500-800字，请改写至少2句的开头。"

    Returns empty list when no run reaches ANAPHORA_RUN_MAX.
    """
    text = (body or "").strip()
    if not text:
        return []

    # Get sentences and find the longest anaphora run
    sentences = _sentences(text)
    if len(sentences) < ANAPHORA_RUN_MAX:
        return []

    # Find the longest anaphora run (same logic as locate_anaphora_run)
    best_start, best_len = 0, 1
    run_start, run_len = 0, 1
    best_pattern = ""

    for i in range(1, len(sentences)):
        po, co = _opening(sentences[i - 1]), _opening(sentences[i])
        if po and po == co:
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
                best_pattern = co
        else:
            run_start, run_len = i, 1

    if best_len < ANAPHORA_RUN_MAX:
        return []

    # Calculate character offsets for each sentence in the run
    spans = []
    run_sentences = sentences[best_start:best_start + min(best_len, max_sentences)]

    for rel_idx, sentence in enumerate(run_sentences):
        abs_idx = best_start + rel_idx

        # Find this sentence's position in the original body
        # Strategy: search for the sentence text in body, accounting for previous sentences
        char_offset = _find_sentence_offset(text, sentences, abs_idx)

        spans.append({
            "sentence_index": abs_idx,
            "text": sentence,
            "char_offset": char_offset,
            "pattern": best_pattern,
            "length": len(sentence)
        })

    return spans


def _find_sentence_offset(body: str, sentences: List[str], target_index: int) -> int:
    """Find the character offset of a sentence in the original body.

    This is approximate because _sentences() strips punctuation and whitespace,
    so we search for the sentence content and return the first match after
    accumulating lengths of previous sentences.
    """
    # Approximate offset: sum of lengths of all previous sentences plus separators
    approx_offset = 0
    for i in range(target_index):
        # Each sentence is separated by punctuation (~1-2 chars) and possibly newlines
        approx_offset += len(sentences[i]) + 2  # +2 for punctuation and space

    # Search for the target sentence in the body starting from approximate offset
    target = sentences[target_index]
    # Strip the sentence to match how it appears in body (may have surrounding punctuation)
    search_start = max(0, approx_offset - 50)  # Search a bit before in case of drift

    # Find the first occurrence of the sentence content
    idx = body.find(target, search_start)
    if idx == -1:
        # Fallback: return approximate offset
        return approx_offset

    return idx


def _stdev(xs: List[int]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    return (sum((x - mean) ** 2 for x in xs) / n) ** 0.5


def ai_taste_summary(body: str) -> Optional[dict]:
    """Reduce a draft body to its numeric AI-tell shape. Returns None for an empty
    body. Deterministic — mirrors density_summary / curve_summary."""
    text = (body or "").strip()
    if not text:
        return None
    sentences = _sentences(text)
    if not sentences:
        return None
    lengths = [len(s) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    run_len, run_open = _longest_anaphora_run(sentences)
    dash_asides = len(_DASH_ASIDE_RE.findall(text))
    cv = round(_stdev(lengths) / mean_len, 3) if mean_len else 0.0
    return {
        "total_chars": len(text),
        "sentence_count": len(sentences),
        "anaphora_run": run_len,
        "anaphora_open": run_open,
        "dash_aside_per_1000": round(dash_asides / len(text) * 1000, 2),
        "sentence_length_cv": cv,
    }


def check_ai_taste(artifact: dict, *, reviewer_id: str = AI_TASTE_REVIEWER_ID) -> ReviewReport:
    """Analyze a draft body's AI-tell signals and return an ADVISORY report
    (ReviewReport: axis=evaluative, gating=False). Deterministic. Emits a clean
    info note when nothing is flagged, so 'checked, nothing flagged' is
    distinguishable from 'never checked'."""
    body = artifact.get("body", "")
    summary = ai_taste_summary(body)
    findings: List[ReviewFinding] = []

    if summary is None:
        findings.append(ReviewFinding(
            "ai-taste", "info", "正文为空，跳过 AI 味分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    if summary["anaphora_run"] >= ANAPHORA_RUN_MAX:
        head = summary["anaphora_open"]
        msg = (f"连续 {summary['anaphora_run']} 句同头排比"
               f"（以“{head}”开头），机器味重的对偶/排比堆砌，建议打散句式")
        # Quote the offending sentences (量化→定位). The count-only instruction let
        # borderline 3-runs survive (tighten0716 ch3); naming the exact sentences
        # removes the "can't find them" skip. This mirrors the market-anchored path
        # (_market_findings) so BOTH hygiene routes carry the location. Location only
        # — the 同头排比 substring (asserted by tests) is unchanged, and a run we
        # can't re-locate degrades to the plain message.
        run = locate_anaphora_run(body)
        if run:
            quoted = "；".join(f"「{s}」" for s in run)
            msg += f"。具体需改写这几句同头：{quoted}"
        findings.append(ReviewFinding("ai-taste", "warning", msg))

    if summary["dash_aside_per_1000"] > DASH_ASIDE_PER_1000:
        findings.append(ReviewFinding(
            "ai-taste", "warning",
            f"破折号插入语密度偏高（每千字 {summary['dash_aside_per_1000']:.1f}>"
            f"{DASH_ASIDE_PER_1000:.0f}），套嵌同位语是典型 AI 腔，建议改为独立短句"))

    if (summary["sentence_count"] >= CV_MIN_SENTENCES
            and summary["sentence_length_cv"] < SENTENCE_CV_FLOOR):
        findings.append(ReviewFinding(
            "ai-taste", "warning",
            f"句长变异过低（CV {summary['sentence_length_cv']:.2f}<"
            f"{SENTENCE_CV_FLOOR:.2f}），全章句子长短均匀、节奏单调，缺乏人类行文的长短交错"))

    if not findings:
        findings.append(ReviewFinding(
            "ai-taste", "info",
            f"未见明显 AI 味信号（最长同头 {summary['anaphora_run']} 句，"
            f"句长 CV {summary['sentence_length_cv']:.2f}）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)

