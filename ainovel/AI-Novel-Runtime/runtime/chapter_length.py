"""chapter_length.py — the single source of truth for chapter-role length bands.

接下来两周执行清单 Week-1 item 2 (长度区间设计): a chapter's length is no longer
one number but a FUNCTION-BOUND interval. An 开篇章 establishes a world and runs
longer; a 推进章 holds a steady middle; a 反转章 needs room to turn; a 钩子章 lands
a punch and tolerates being shorter. Each role therefore gets its own band.

Two length definitions used to live apart and could drift:
  - runtime/chapter/reviewer.py  — per-role `min_chars` (verdict floor)
  - runtime/execution/length_check.py — one target + a GLOBAL band (0.6–1.5)
Both `chapter/` and `execution/` import THIS leaf module (they do not import
each other), so the role→length contract has exactly one home.

DISCIPLINE:
  - `min_chars` is the reviewer's verdict floor (evaluative, advisory). It is
    NOT a build/publish hard gate — those remain draft_qa's `min_words` and the
    text-integrity gate, which this module never touches (清单 item 2: 不破坏硬门).
  - The (band_low, band_high) ratios are the advisory length band around the
    outline's per-chapter target, consumed by length_check. Advisory, never
    gates (ADR-003).
  - Deterministic: same text → same role → same band.
"""
from __future__ import annotations

from typing import Optional

CHAPTER_ROLES = ("opening", "advance", "turn", "hook")

# Function-bound length contract per role. `min_chars` preserves the reviewer's
# historical verdict floors EXACTLY (opening 900 / advance 700 / turn 800 /
# hook 600 / default 700) so verdicts do not shift. The band ratios widen or
# shift by function; `advance`/`default` keep the historical global 0.6–1.5 so
# a chapter with no role resolves byte-identically to the old global band.
ROLE_LENGTH = {
    "opening": {"min_chars": 900, "band_low": 0.8, "band_high": 1.6},
    "advance": {"min_chars": 700, "band_low": 0.6, "band_high": 1.5},
    "turn":    {"min_chars": 800, "band_low": 0.7, "band_high": 1.5},
    "hook":    {"min_chars": 600, "band_low": 0.45, "band_high": 1.3},
    "default": {"min_chars": 700, "band_low": 0.6, "band_high": 1.5},
}

# The global band used when NO role is supplied — identical to length_check's
# historical BAND_LOW / BAND_HIGH, so the role-less path is unchanged.
DEFAULT_BAND_LOW = ROLE_LENGTH["default"]["band_low"]
DEFAULT_BAND_HIGH = ROLE_LENGTH["default"]["band_high"]


def role_length(role: Optional[str]) -> dict:
    """The length contract for a role. Unknown/None → the default band."""
    return ROLE_LENGTH.get(role or "default", ROLE_LENGTH["default"])


# Chapter POSITION -> function, for the chapters whose commercial function is fixed
# by WHERE THEY SIT rather than by what they happen to contain (规范 §7 黄金三章):
#   ch1 开篇 — establish 异常/欲望/危机/选择; runs longest
#   ch2 推进 — verify the mechanism, expose its cost
#   ch3 反转 — the first ACTIVE victory; a turn
# Only ch1/ch3 differ from the historical default: ch2 maps to `advance`, which IS
# the old default, so a chapter-2 render stays byte-identical.
POSITION_ROLES = {1: "opening", 2: "advance", 3: "turn"}

# Director pacing_role -> our role vocabulary. Lifted out of loop.py (where it was
# an inline literal) so generation and measurement cannot disagree on what a
# pacing_role means.
PACING_ROLE_MAP = {
    "rising_action": "advance", "climax": "turn", "turn": "turn",
    "opening": "opening", "hook": "hook", "cliffhanger": "hook",
    "setup": "opening",
}


def role_for_chapter(chapter_no: Optional[int] = None, *,
                     pacing_role: Optional[str] = None,
                     body: Optional[str] = None) -> str:
    """The ONE way to resolve a chapter's function, in falling authority:

      1. POSITION, for the first three chapters. §7 黄金三章 is a FROZEN commercial
         contract — ch1 must establish, ch2 must verify the mechanism, ch3 must land
         the first active victory — so their function is decided before a word
         exists and outranks any runtime opinion about them.
      2. the director's `pacing_role`, for every chapter after the third.
      3. the produced body's heading (`infer_chapter_role`) — a post-hoc guess,
         and only usable once the text exists.

    Position outranks the heading guess because generation needs the role BEFORE
    the text exists, and the heading token ("第一章") only helps if the model
    happened to write it. Deterministic; never raises.
    """
    if (isinstance(chapter_no, int) and not isinstance(chapter_no, bool)
            and chapter_no in POSITION_ROLES):
        return POSITION_ROLES[chapter_no]
    mapped = PACING_ROLE_MAP.get((pacing_role or "").strip())
    if mapped:
        return mapped
    if body:
        return infer_chapter_role(body)
    return "advance"


def infer_chapter_role(text: str) -> str:
    """Infer a chapter's function from its heading line. Deterministic; mirrors
    the tokens the reviewer historically keyed on so both agree on one role."""
    lines = text.splitlines() if text else []
    head = lines[0].strip() if lines else ""
    if any(t in head for t in ("楔子", "序章", "开篇", "第一章", "Chapter 1", "CHAPTER 1")):
        return "opening"
    if any(t in head for t in ("转折", "反转", "逆转", "第二章", "Chapter 2", "CHAPTER 2")):
        return "turn"
    if any(t in head for t in ("钩子", "悬念", "尾声", "第五章", "Chapter 5", "CHAPTER 5")):
        return "hook"
    return "advance"


# --------------------------------------------------------------------------- #
# Length DIRECTIVE (the generation-side half of the length contract)          #
# --------------------------------------------------------------------------- #
# P0-3 篇幅失控. Measured on RUN-00001 (30ch) and the v11/v12 A/B:
#   market median 3166 / p75 3287 chars  ·  our median 5238 (1.56x), v12 5427 (1.65x)
#
# Two remedies were RULED OUT by evidence before landing this one:
#   1. hygiene rewrite — the required shrink (0.64x) is BELOW the deletion-cheat
#      floor (0.8x), so every round would be rejected as gutting. Pinned by
#      test_length_cannot_be_hygiene_fixed.
#   2. stronger prompt wording alone — tried twice ("严禁超过3900" still produced
#      231-242%). Words without a NUMBER the model can divide are ignored.
#
# So the fix is upstream, in what the plan HANDS to generation, and it changes two
# things about the old directive ("目标篇幅：约 N 字（可上下浮动…）"):
#   a) it had NO UPPER BOUND — "可上下浮动" invites overshoot. Now an explicit ceiling.
#   b) it gave ONE WHOLE-CHAPTER number while the model writes beat by beat. Measured:
#      4-beat chapters ran 5128 chars, 5-beat 5305 — only 176 apart, so the overshoot
#      is per-beat verbosity, NOT beat count. Giving a PER-BEAT budget converts an
#      un-actionable total into a number the model can hold while writing each scene.
# Advisory in the ADR-003 sense: this is prompt input, not a gate. The hard floor
# stays draft_qa's min_words; the advisory band stays length_check.

# The ceiling as a multiple of target. 1.25 sits just above the market p75/median
# ratio (3287/3166 = 1.04) with headroom for a legitimately eventful chapter, while
# cutting hard into the measured 1.56-1.65x. Deliberately NOT 1.0: an exact quota
# invites padding to hit it.
LENGTH_CEILING_RATIO = 1.25


def length_directive(target: Optional[int], *, role: Optional[str] = None,
                     beats: Optional[int] = None) -> str:
    """The generation-side length instruction for `target` chars.

    Returns "" for a falsy target, so a project with no target renders a
    byte-identical draft (the load-bearing non-breaking invariant).

    `beats` (optional): when the scene plan is known, the total is divided into a
    per-beat budget — the lever the measurement says matters. `role` widens the
    ceiling for an 开篇 chapter, which legitimately runs longer.
    Deterministic: same (target, role, beats) => same string."""
    if not target:
        return ""
    band_high = role_length(role)["band_high"]
    # The ceiling is the TIGHTER of the role band and the global ratio. In practice
    # every role band (1.3-1.6) exceeds 1.25, so today all roles land on 1.25 —
    # and the measurement says that is right: the market's 开篇 window is only 1.6%
    # wider than the whole-book window (golden3 p75 3409 vs first30 p75 3354), so
    # there is no evidence for widening the ceiling by role. The min() is kept so a
    # role band TIGHTER than 1.25 (e.g. a future 钩子 band) would still win.
    ceiling = int(target * min(band_high, LENGTH_CEILING_RATIO))
    parts = [f"目标篇幅：{target} 字，上限 {ceiling} 字（**不得超过上限**）。"]
    if beats and beats > 0:
        per = int(target / beats)
        parts.append(
            f"本章分 {beats} 个分镜，平均每个分镜约 {per} 字——"
            f"写每一个分镜时都按这个额度收，不要在单个分镜里铺陈到超额。")
    parts.append("宁可写紧，也不要为凑字数注水；但不要草草收尾、砍掉应有的情节。")
    return "".join(parts)
