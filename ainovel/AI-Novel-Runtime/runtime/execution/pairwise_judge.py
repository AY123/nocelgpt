"""pairwise_judge.py — RELATIVE character comparison of two chapter drafts.

WHY THIS EXISTS (§12.1 ② effect-measurement follow-up): the absolute Novel
Quality judge (quality_center.LLMQualityJudge) saturates on character_consistency
(~91 mean, stdev ~3 at baseline) and quantizes to ~5-point steps. A fine change
in character rendering — e.g. the +18% interiority the psych-deepening put into
the prose — lives BELOW that instrument's resolution, so a real before/after
delta reads as noise. This module measures the DIFFERENCE directly instead of
differencing two coarse absolute numbers.

It follows the codebase's established comparison-only pattern (reader_sim's
compare_simulations, director/compare.py): the numbers are meaningful ONLY as a
relative A-vs-B judgment, never as an absolute score. Structural invariants:
comparison_only=True, gating=False, never calibrates. A pairwise judge is a
SIBLING of the reader simulator, not a variant of the absolute quality judge —
it produces per-dimension winners, not a scored report, so it touches none of
the 10 absolute-score consumers (dashboard/redline/publish_readiness/revision/…)
and stays independent of their absolute thresholds.

POSITION-BIAS CONTROL (load-bearing): an LLM asked "which is better, A or B?"
has a well-known order bias. Every pair is judged TWICE with the drafts swapped;
a dimension counts as a win for a draft only when BOTH orderings agree. A
disagreement is recorded as a tie (the bias cancelled the signal). This is what
makes a pairwise verdict trustworthy — without it the win-rate is contaminated
by whichever draft was shown first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .quality_center import _extract_json

# The character dimensions this judge compares. Named to mirror the absolute
# judge's dims so a reader can line the two instruments up, but here they are
# compared, never scored.
CHARACTER_DIMS: Tuple[str, ...] = ("character_consistency", "character_growth")

_VERDICTS = ("a", "b", "tie")


@dataclass(frozen=True)
class PairwiseComparison:
    """A relative A-vs-B character judgment over one chapter's two drafts.

    `dimensions` maps each character dim -> a verdict dict with the bias-controlled
    outcome ('a'|'b'|'tie'), the two raw single-order calls, and evidence. `winner`
    is the label that won more dimensions ('a'|'b'|'tie'). Advisory + comparison-
    only: none of these numbers is an absolute score."""
    reviewer: str
    label_a: str
    label_b: str
    dimensions: dict                      # dim -> {verdict, order_ab, order_ba, evidence}
    winner: str                           # 'a' | 'b' | 'tie'
    judge_provenance: Optional[dict] = None
    axis: str = "evaluative"              # structural invariant
    gating: bool = False                  # structural invariant — never blocks
    comparison_only: bool = True          # structural invariant — relative use only
    calibrates: bool = False              # structural invariant — never calibrates signals

    def to_dict(self) -> dict:
        out = {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "comparison_only": self.comparison_only,
            "calibrates": self.calibrates,
            "label_a": self.label_a,
            "label_b": self.label_b,
            "dimensions": self.dimensions,
            "winner": self.winner,
        }
        if self.judge_provenance is not None:
            out["judge_provenance"] = self.judge_provenance
        return out


# --------------------------------------------------------------------------- #
# Prompt (contracted). Asks the model to pick, per dimension, which draft is    #
# stronger — NOT to score either one. Kept deliberately narrow to the character #
# dims so the judgment is about people, not overall quality.                    #
# --------------------------------------------------------------------------- #
_PAIRWISE_TEMPLATE = """# Role
你是一名拥有百万字网文经验的商业小说总编，只做人物塑造的对比评审。
你不打绝对分，只判断两稿中哪一稿在每个人物维度上更强。

# 任务
下面是同一章的两个版本（稿件甲 / 稿件乙），情节相同，只在人物刻画上可能有差异。
就每个维度，判断哪一稿更强，并引用正文具体句子作为依据。

# 对比维度
- character_consistency: 人物言行是否更贴合设定、更少 OOC、性格更立得住
- character_growth: 本章人物的内在变化/成长是否更清晰、可追踪、有说服力

# 稿件甲
<<<A>>>
{body_a}
<<<END A>>>

# 稿件乙
<<<B>>>
{body_b}
<<<END B>>>

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown 代码块。winner 取值 "A"/"B"/"tie"：
{{
  "character_consistency": {{"winner":"A|B|tie","evidence":"引用甲或乙的具体句子说明"}},
  "character_growth": {{"winner":"A|B|tie","evidence":"引用甲或乙的具体句子说明"}}
}}

# 失败兜底
无法评估时也必须输出上述结构，每个维度 winner 给 "tie"，evidence 留空。"""


def build_pairwise_prompt(body_a: str, body_b: str) -> str:
    return _PAIRWISE_TEMPLATE.format(body_a=body_a or "", body_b=body_b or "")


def _parse_single(text: str) -> Optional[dict]:
    """Parse one single-order call into {dim: 'a'|'b'|'tie', evidence}. Returns
    None on any parse failure (the caller degrades to tie). Never raises. The
    'A'/'B' in the model's output are FIRST/SECOND slot — mapping back to the
    real drafts is the caller's job (it knows which draft it put first)."""
    obj = _extract_json(text)
    if obj is None:
        return None
    out = {}
    for dim in CHARACTER_DIMS:
        cell = obj.get(dim)
        w = (cell.get("winner") if isinstance(cell, dict) else "") or ""
        w = str(w).strip().lower()
        slot = w if w in ("a", "b", "tie") else "tie"
        ev = cell.get("evidence", "") if isinstance(cell, dict) else ""
        out[dim] = {"slot": slot, "evidence": str(ev)}
    return out


def _combine(order_ab: Optional[dict], order_ba: Optional[dict]) -> dict:
    """Fold the two single-order calls into a bias-controlled per-dim verdict.

    order_ab judged (real_A as slot A, real_B as slot B): slot 'a' => real A wins.
    order_ba judged (real_B as slot A, real_A as slot B): slot 'a' => real B wins,
    so it must be FLIPPED back to the real-draft frame before comparing.

    A dimension counts for a draft only when BOTH orderings agree in the real
    frame; disagreement (order bias) => tie. A missing/failed call => tie."""
    dims = {}
    for dim in CHARACTER_DIMS:
        ab = (order_ab or {}).get(dim, {}).get("slot", "tie")
        ba_raw = (order_ba or {}).get(dim, {}).get("slot", "tie")
        # flip the swapped call back to the real-draft frame
        ba = {"a": "b", "b": "a", "tie": "tie"}[ba_raw]
        if ab == ba and ab in ("a", "b"):
            verdict = ab
        else:
            verdict = "tie"
        evidence = ((order_ab or {}).get(dim, {}).get("evidence", "")
                    or (order_ba or {}).get(dim, {}).get("evidence", ""))
        dims[dim] = {"verdict": verdict, "order_ab": ab, "order_ba": ba,
                     "evidence": evidence}
    return dims


def _winner(dims: dict) -> str:
    """The label that won more character dimensions ('a'|'b'|'tie')."""
    a = sum(1 for d in dims.values() if d["verdict"] == "a")
    b = sum(1 for d in dims.values() if d["verdict"] == "b")
    if a > b:
        return "a"
    if b > a:
        return "b"
    return "tie"


def compare_character(body_a: str, body_b: str, model, *,
                      label_a: str = "A", label_b: str = "B",
                      reviewer_id: str = "pairwise-character-judge-v1"
                      ) -> PairwiseComparison:
    """RELATIVE character comparison of two drafts, bias-controlled by judging
    both orderings and keeping only agreeing verdicts. Advisory, comparison-only,
    never gates. A model failure degrades to an all-tie verdict — never raises,
    so a batch of comparisons can't be broken by one bad call."""
    model_id = getattr(model, "model_id", "")

    def _call(x: str, y: str) -> Tuple[Optional[dict], Optional[str]]:
        try:
            output = model.generate(build_pairwise_prompt(x, y))
            text = getattr(output, "text", "")
        except Exception as exc:
            return None, f"{exc.__class__.__name__}: {exc}"
        parsed = _parse_single(text)
        if parsed is None:
            return None, f"unparseable response ({len(text)} chars): {text[:240]!r}"
        return parsed, None

    # order 1: real A first. order 2: real B first (swapped).
    ab, ab_error = _call(body_a, body_b)
    ba, ba_error = _call(body_b, body_a)

    dims = _combine(ab, ba)
    provenance = None
    if ab_error or ba_error:
        provenance = {
            "degraded": True,
            "reason": "one or both pairwise calls failed",
            "model_id": model_id,
            "call_errors": {
                "order_ab": ab_error,
                "order_ba": ba_error,
            },
        }
    return PairwiseComparison(
        reviewer=reviewer_id, label_a=label_a, label_b=label_b,
        dimensions=dims, winner=_winner(dims), judge_provenance=provenance)


def aggregate_comparisons(comparisons: List[PairwiseComparison]) -> dict:
    """Fold a batch of per-chapter comparisons into a win-rate summary. This is
    the answer the effect-measurement asks: across chapters, does draft A win the
    character dims more than draft B? Ties and degraded pairs are reported so the
    win-rate denominator is honest. Comparison-only — never an absolute score."""
    per_dim = {dim: {"a": 0, "b": 0, "tie": 0} for dim in CHARACTER_DIMS}
    overall = {"a": 0, "b": 0, "tie": 0}
    degraded = 0
    for c in comparisons:
        if c.judge_provenance and c.judge_provenance.get("degraded"):
            degraded += 1
        for dim in CHARACTER_DIMS:
            per_dim[dim][c.dimensions[dim]["verdict"]] += 1
        overall[c.winner] += 1
    n = len(comparisons)
    return {
        "reviewer": comparisons[0].reviewer if comparisons else "",
        "gating": False, "comparison_only": True, "calibrates": False,
        "n_pairs": n, "n_degraded": degraded,
        "per_dimension": per_dim,
        "overall": overall,
        # decisive_win_rate_a: of pairs with a NON-tie overall winner, the share A won.
        "decisive_win_rate_a": (
            round(overall["a"] / (overall["a"] + overall["b"]), 3)
            if (overall["a"] + overall["b"]) else None),
    }
