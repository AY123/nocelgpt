"""publish_readiness.py — the 'Build Gate ≠ Publish Readiness' layer (Phase 4.1).

This is a PRODUCTION DECISION artifact that sits BESIDE the deterministic build
gate. It does NOT violate ADR-003:

  - Build is never blocked by an evaluative judgment (quality-report gating=false).
  - Separately, this artifact advises whether a chapter should be PUBLISHED.
  - It is ADVISORY toward a HUMAN (ADR-009): the system may recommend block/hold,
    but only a human executes the irreversible, outward publish transition.

Two inputs, on two different axes (Phase 4 invariant #3 — the safety split):

  1. DETERMINISTIC red-line result (redline.py). A HARD hit is objective and
     forces recommendation='block'. This is the axis of safety that legitimately
     gates the build AND blocks publish.
  2. EVALUATIVE quality-report v2 signals (retention / subscription / payoff /
     reader_drop_risk). These are advisory: they can lower a recommendation to
     'hold', but NEVER to 'block' on their own — only a hard red-line blocks.

The derivation is PURE and DETERMINISTIC given (hits, quality report, policy):
same inputs => same recommendation, so it is replay-stable like every other
derived artifact. The recorded `policy` block makes the decision auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .m7 import M7Result
from .redline import RedlineHit, has_hard_hit, hits_to_dicts

SCHEMA_VERSION = "1.0"

# Default publish policy. A commercial signal below HOLD_THRESHOLD, or a
# reader_drop_risk at/above DROP_RISK_HOLD_AT, advises a 'hold' (soft: fix before
# publish). Only a hard red-line advises 'block'. Advisory dims considered for the
# hold decision — the operable commercial signals from quality-report v2.
HOLD_THRESHOLD = 60
DROP_RISK_HOLD_AT = 60
_HOLD_DIMS = ("retention", "subscription", "payoff")


@dataclass(frozen=True)
class PublishReadiness:
    chapter_id: str
    recommendation: str                       # recommend | hold | block
    redline_passed: bool
    redline_hits: List[dict] = field(default_factory=list)
    quality: dict = field(default_factory=dict)
    below_threshold: List[str] = field(default_factory=list)
    draft_content_hash: Optional[str] = None
    quality_report_ref: Optional[str] = None
    rationale: str = ""
    hold_threshold: int = HOLD_THRESHOLD
    drop_risk_hold_at: int = DROP_RISK_HOLD_AT

    # Structural invariants (mirrored by publish-readiness.schema.json):
    authority: str = "human"                  # ADR-009: human executes publish
    gates_build: bool = False                 # never blocks a build

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "subject": _subject(self.chapter_id, self.draft_content_hash,
                                self.quality_report_ref),
            "authority": self.authority,
            "gates_build": self.gates_build,
            "recommendation": self.recommendation,
            "basis": {
                "redline": {
                    "passed": self.redline_passed,
                    "hits": self.redline_hits,
                },
                "quality": {
                    **self.quality,
                    "below_threshold": self.below_threshold,
                },
            },
            "policy": {
                "hold_threshold": self.hold_threshold,
                "drop_risk_hold_at": self.drop_risk_hold_at,
            },
            "rationale": self.rationale,
        }


def _subject(chapter_id: str, content_hash: Optional[str],
             quality_ref: Optional[str]) -> dict:
    out = {"chapter_id": chapter_id}
    if content_hash:
        out["draft_content_hash"] = content_hash
    if quality_ref:
        out["quality_report_ref"] = quality_ref
    return out


def assess_publish_readiness(
    *,
    chapter_id: str,
    redline_hits: Optional[Sequence[RedlineHit]] = None,
    m7_result: Optional[M7Result] = None,
    quality_report: Optional[dict] = None,
    draft_content_hash: Optional[str] = None,
    quality_report_ref: Optional[str] = None,
    hold_threshold: int = HOLD_THRESHOLD,
    drop_risk_hold_at: int = DROP_RISK_HOLD_AT,
) -> PublishReadiness:
    """Derive a publish recommendation. Pure/deterministic; never raises.

    If an M7 result is supplied, it is the upstream gate: its red-line and
    originality assessment are folded into publish readiness. Hard red-lines or
    L3 originality risk both force 'block'.

    Precedence:
      1. any HARD red-line hit or M7 L3/block  -> 'block'
      2. else any commercial signal below threshold / drop-risk too high -> 'hold'
      3. else -> 'recommend'
    """
    redline_hits = list(redline_hits or [])
    if m7_result is not None:
        redline_hits = [RedlineHit(rule=h.get("rule", ""), severity=h.get("severity", "soft"), evidence=h.get("evidence", "")) for h in m7_result.redline_hits]
    hard = has_hard_hit(redline_hits) or (m7_result is not None and m7_result.recommendation == "block")
    scores = ((quality_report or {}).get("scores") or {}) if isinstance(quality_report, dict) else {}

    quality = {}
    for dim in ("retention", "subscription", "payoff", "reader_drop_risk"):
        if dim in scores:
            quality[dim] = scores[dim]

    below = [dim for dim in _HOLD_DIMS
             if dim in scores and scores[dim] < hold_threshold]
    drop_high = ("reader_drop_risk" in scores
                 and scores["reader_drop_risk"] >= drop_risk_hold_at)

    if hard:
        rec = "block"
        rationale = ("上游 M7/硬性红线命中，禁止发布(确定性检查，ADR-003)；"
                     "该判定同时也应阻断构建。")
    elif below or drop_high:
        rec = "hold"
        reasons = []
        if below:
            reasons.append("商业维度不达标: " + ", ".join(below))
        if drop_high:
            reasons.append(f"弃书风险过高(reader_drop_risk>={drop_risk_hold_at})")
        rationale = "建议修订后再发布 — " + "; ".join(reasons) + "。"
    else:
        rec = "recommend"
        rationale = "未命中红线，商业信号达标，可发布(仍需人工授权，ADR-009)。"

    # A soft red-line hit is surfaced in below_threshold-style rationale but does
    # not by itself force hold; record it so the human sees it.
    soft_hits = [h.rule for h in redline_hits if h.severity == "soft"]
    if soft_hits and rec == "recommend":
        rationale += " 注意软性敏感项(仅提示，不阻断): " + ", ".join(soft_hits) + "。"

    return PublishReadiness(
        chapter_id=chapter_id,
        recommendation=rec,
        redline_passed=not hard,
        redline_hits=hits_to_dicts(redline_hits),
        quality=quality,
        below_threshold=below,
        draft_content_hash=draft_content_hash,
        quality_report_ref=quality_report_ref,
        rationale=rationale,
        hold_threshold=hold_threshold,
        drop_risk_hold_at=drop_risk_hold_at,
    )
