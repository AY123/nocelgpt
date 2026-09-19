"""Y365-03: multi-proposal opening book comparison and selection.

Generates multiple opening-book proposals from the same input and compares them
on a set of deterministic dimensions so a human can pick the best one. Advisory
(ADR-003); never gates — selection authority is human.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ProposalScore:
    proposal_id: str
    logline: str
    originality_risk: str
    market_fit: float | None
    opening_hook_strength: float | None
    long_arc_clarity: float | None
    total_score: float | None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultiProposalComparison:
    kind: str
    version: str
    project_id: str
    proposals: list[ProposalScore]
    winner_id: str | None
    publish_authority: str = "human"
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "proposals": [p.to_dict() for p in self.proposals],
            "winner_id": self.winner_id,
            "publish_authority": self.publish_authority,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def compare_multi_proposals(
    *,
    project_id: str,
    proposals: Sequence[Mapping[str, Any]],
) -> MultiProposalComparison:
    scored: list[ProposalScore] = []
    for p in proposals:
        pid = str(p.get("proposal_id") or p.get("id") or "")
        logline = str(p.get("logline") or "")
        risk = str(p.get("originality_risk") or p.get("risk_level") or "unknown")
        market = p.get("market_fit")
        hook = p.get("opening_hook_strength")
        arc = p.get("long_arc_clarity")

        vals = [float(v) for v in [market, hook, arc] if isinstance(v, (int, float))]
        total = round(sum(vals) / len(vals), 2) if vals else None

        scored.append(ProposalScore(
            proposal_id=pid,
            logline=logline,
            originality_risk=risk,
            market_fit=float(market) if isinstance(market, (int, float)) else None,
            opening_hook_strength=float(hook) if isinstance(hook, (int, float)) else None,
            long_arc_clarity=float(arc) if isinstance(arc, (int, float)) else None,
            total_score=total,
        ))

    winner = None
    with_scores = [s for s in scored if s.total_score is not None]
    if with_scores:
        winner = max(with_scores, key=lambda s: s.total_score or 0).proposal_id

    return MultiProposalComparison(
        kind="multi_proposal_comparison",
        version="1.0",
        project_id=project_id,
        proposals=scored,
        winner_id=winner,
        metadata={"proposal_count": len(scored)},
    )
