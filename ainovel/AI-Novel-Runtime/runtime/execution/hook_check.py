"""hook_check.py — single-chapter end-hook detection (ANES v2, ADR-003).

The §14 finding-3 remedy, made into an advisory guard: the chapter-end hook was
left entirely to the model's discretion — Claude/GPT closed on emotion with no
追读 pull; DeepSeek had one but templated. The director objective already DECLARES
a cliffhanger_type and renders it into the v6/v7 prompt, but nothing CHECKED
whether the finished draft actually left a hook. This module does — deterministically.

It is the FOURTH twin of scene/pacing.py, execution/density.py, and
execution/humanization.py: same discipline, different signal. density measures
WHAT the prose carries, humanization HOW sentences are built; this measures the
ENDING's FUNCTION — does the last beat leave the reader needing the next chapter?

Signals over the ENDING segment (last ~3 sentences / ~200 chars), bilingual:
  1. has_question   — the ending poses an open question (？/? or a question word)
  2. has_suspension — it breaks off mid-beat (em-dash / ellipsis close)
  3. has_turn       — a reversal / threat / intrusion word cluster (突然/身后/门外
                      /推开/危险/血 · suddenly/behind/door/too late/blood)
  4. has_closure    — a settling/resolution signal (松了口气/睡着/终于安全/沉沉睡去
                      · asleep/safe/at last/breathed) — the §14 "closed on emotion" tell

Warning only when the ending has NO hook signal AND shows closure (the clearly-bad
"emotional close, no pull"), or when the objective declared a hook the ending
doesn't deliver. No-hook-no-closure is a neutral info (don't cry wolf).

DISCIPLINE:
  - DETERMINISTIC: signals are matched from the ending text — same body => same findings.
  - EVALUATIVE, never gates (ADR-003): reuses ReviewReport (axis=evaluative,
    gating=False) so it rides the envelope like check_pacing.
  - Reads only the body (+ an optional objective for the declared/delivered cross-
    check). No package, state, model, or I/O.
"""
from __future__ import annotations

import re
from typing import List, Optional

from .draft_review import ReviewReport, ReviewFinding

HOOK_REVIEWER_ID = "hook-check-v1"

# The ending segment: the last few sentences OR the last N chars, whichever is
# longer, so a run of short punchy closing lines and one long closing paragraph
# both get a fair window.
ENDING_SENTENCES = 3
ENDING_CHARS = 200
MIN_BODY_CHARS = 200         # below this the "ending" is the whole thing — skip

# Sentence terminators, both scripts (mirrors humanization._sentences).
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?\.]+[\s”」』\"']*|\n+")

# ① open question at the end
_QUESTION_RE = re.compile(
    r"[？?]"
    r"|什么|为什么|怎么|难道|是谁|会不会|能不能|究竟|到底|还是"
    r"|\b(?:what|why|who|how|where|when|whether|could|would)\b", re.IGNORECASE)

# ② suspension: the ending breaks off mid-beat
_SUSPENSION_RE = re.compile(r"(?:——|—|\.\.\.|…|……)\s*$")

# ③ reversal / threat / intrusion cluster — the shape of a real cliffhanger
_TURN_RE = re.compile(
    r"突然|忽然|竟|却在|没想到|来不及|身后|门外|背后|推开(?:了)?门|出现|逼近|扑"
    r"|危险|杀|死|血|尖叫|惨叫|警告|敌|追兵|黑影|抓住|抓向|响起|炸开"
    r"|\bsudden(?:ly)?\b|\bbehind\b|\bdoor\b|\btoo late\b|\bblood\b|\bscream",
    re.IGNORECASE)

# ④ closure / settling — the §14 "closed on emotion, no pull" tell
_CLOSURE_RE = re.compile(
    r"松了(?:一)?口气|舒了(?:一)?口气|睡着|睡去|沉沉(?:地)?睡|安心|平静下来|终于安全"
    r"|放下心|安然|终于结束|一切都会好|渐渐(?:睡|平)|合上眼|闭上(?:了)?眼|安稳"
    r"|\bat last\b|\bfell asleep\b|\bsafe (?:now|at last)\b|\bbreathed\b"
    r"|\bat peace\b|\bfinally (?:rest|safe|calm)", re.IGNORECASE)


def _sentences(text: str) -> List[str]:
    out: List[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        for frag in _SENTENCE_SPLIT_RE.split(s):
            f = frag.strip()
            if f:
                out.append(f)
    return out


def _ending_segment(text: str) -> str:
    """The ending window: the last ENDING_SENTENCES sentences OR the last
    ENDING_CHARS characters, whichever is longer. Deterministic. Note the segment
    is rebuilt from raw tail chars for suspension detection (which needs the true
    final punctuation), joined with the last sentences for the word signals."""
    tail_chars = text[-ENDING_CHARS:]
    sents = _sentences(text)
    tail_sents = "。".join(sents[-ENDING_SENTENCES:]) if sents else ""
    return tail_sents if len(tail_sents) >= len(tail_chars) else tail_chars


def hook_summary(body: str) -> Optional[dict]:
    """Reduce a draft's ending to its hook-signal shape. Returns None for an empty
    body. Deterministic — mirrors density_summary / ai_taste_summary. Suspension
    is checked on the RAW text tail (the true final punctuation), the rest on the
    ending segment."""
    text = (body or "").strip()
    if not text:
        return None
    ending = _ending_segment(text)
    return {
        "ending_len": len(ending),
        "has_question": bool(_QUESTION_RE.search(ending)),
        "has_suspension": bool(_SUSPENSION_RE.search(text)),
        "has_turn": bool(_TURN_RE.search(ending)),
        "has_closure": bool(_CLOSURE_RE.search(ending)),
    }


def _has_hook(summary: dict) -> bool:
    return (summary["has_question"] or summary["has_suspension"]
            or summary["has_turn"])


def check_end_hook(artifact: dict, *, objective: Optional[dict] = None,
                   reviewer_id: str = HOOK_REVIEWER_ID) -> ReviewReport:
    """Analyze a draft's ending for a 追读 hook and return an ADVISORY report
    (ReviewReport: axis=evaluative, gating=False). Deterministic. Warns only on
    the clearly-bad (a settling close with no hook, or an objective-declared hook
    the ending doesn't deliver); otherwise a clean/neutral info. `objective` is an
    optional ChapterObjective whose cliffhanger_type is cross-checked."""
    body = artifact.get("body", "")
    summary = hook_summary(body)
    findings: List[ReviewFinding] = []

    if summary is None:
        findings.append(ReviewFinding("end-hook", "info", "正文为空，跳过章末钩子分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    if summary["ending_len"] < 1 or len(body.strip()) < MIN_BODY_CHARS:
        findings.append(ReviewFinding("end-hook", "info", "正文过短，跳过章末钩子分析"))
        return ReviewReport(reviewer=reviewer_id, findings=findings)

    has_hook = _has_hook(summary)
    declared = (objective or {}).get("cliffhanger_type")

    if not has_hook and summary["has_closure"]:
        findings.append(ReviewFinding(
            "end-hook", "warning",
            "章末收于平息/情绪落地（无悬念、无未决、无转折），缺乏追读钩子，"
            "掉读风险高——建议以疑问/悬置/转折收尾"))
    elif declared and declared != "none" and not has_hook:
        findings.append(ReviewFinding(
            "end-hook", "warning",
            f"导演目标声明章末钩子（{declared}），但正文结尾未见钩子特征"
            f"（疑问/悬置/转折），声明与兑现不符"))

    if not findings:
        if has_hook:
            kinds = [k for k, on in (("疑问", summary["has_question"]),
                                     ("悬置", summary["has_suspension"]),
                                     ("转折/威胁", summary["has_turn"])) if on]
            findings.append(ReviewFinding(
                "end-hook", "info", f"章末留有钩子（{'、'.join(kinds)}）"))
        else:
            findings.append(ReviewFinding(
                "end-hook", "info", "章末未见明显钩子，但也未落于平息（中性收束）"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
