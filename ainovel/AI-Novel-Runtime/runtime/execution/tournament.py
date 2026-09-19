"""All-pairs Genesis tournament over complete, frozen book proposals."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any, Mapping, Sequence

from .genesis_pairwise_judge import (
    GENESIS_DIMS,
    GenesisPairwiseComparison,
    compare_genesis_candidates,
)


@dataclass(frozen=True)
class TournamentMatch:
    label_a: str
    label_b: str
    comparison: dict[str, Any]


@dataclass(frozen=True)
class TournamentResult:
    reviewer: str
    candidates: list[str]
    matches: list[TournamentMatch]
    summary: dict[str, Any]
    comparison_only: bool = True
    gating: bool = False
    calibrates: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "candidates": list(self.candidates),
            "matches": [asdict(match) for match in self.matches],
            "summary": self.summary,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "calibrates": self.calibrates,
            "metadata": self.metadata,
        }


def aggregate_tournament(
    candidate_ids: Sequence[str],
    comparisons: Sequence[GenesisPairwiseComparison],
    *,
    reviewer_id: str,
) -> dict[str, Any]:
    candidates = {
        candidate_id: {
            "match_wins": 0,
            "match_losses": 0,
            "match_ties": 0,
            "dimension_wins": {dim: 0 for dim in GENESIS_DIMS},
            "total_dimension_wins": 0,
            "total_wins": 0,
        }
        for candidate_id in candidate_ids
    }
    n_degraded = 0
    consistent_dimensions = 0
    measured_dimensions = 0
    call_errors = []

    for comparison in comparisons:
        provenance = comparison.judge_provenance or {}
        degraded = bool(provenance.get("degraded"))
        if degraded:
            n_degraded += 1
            for order, error in (provenance.get("call_errors") or {}).items():
                call_errors.append({
                    "label_a": comparison.label_a,
                    "label_b": comparison.label_b,
                    "order": order,
                    "error": error,
                })
            candidates[comparison.label_a]["match_ties"] += 1
            candidates[comparison.label_b]["match_ties"] += 1
            continue

        consistent_dimensions += int(provenance.get("position_consistent_dimensions") or 0)
        measured_dimensions += int(provenance.get("position_total_dimensions") or 0)
        if comparison.winner == "a":
            candidates[comparison.label_a]["match_wins"] += 1
            candidates[comparison.label_b]["match_losses"] += 1
        elif comparison.winner == "b":
            candidates[comparison.label_b]["match_wins"] += 1
            candidates[comparison.label_a]["match_losses"] += 1
        else:
            candidates[comparison.label_a]["match_ties"] += 1
            candidates[comparison.label_b]["match_ties"] += 1

        for dim, result in comparison.dimensions.items():
            winner_id = None
            if result["verdict"] == "a":
                winner_id = comparison.label_a
            elif result["verdict"] == "b":
                winner_id = comparison.label_b
            if winner_id is not None:
                candidates[winner_id]["dimension_wins"][dim] += 1
                candidates[winner_id]["total_dimension_wins"] += 1
                candidates[winner_id]["total_wins"] += 1

    max_wins = max((item["total_wins"] for item in candidates.values()), default=0)
    leaders = [candidate_id for candidate_id, item in candidates.items()
               if item["total_wins"] == max_wins]
    winner = leaders[0] if len(leaders) == 1 else None
    return {
        "reviewer": reviewer_id,
        "gating": False,
        "comparison_only": True,
        "calibrates": False,
        "n_pairs": len(comparisons),
        "n_degraded": n_degraded,
        "call_errors": call_errors,
        "per_candidate": candidates,
        "position_consistent_dimensions": consistent_dimensions,
        "position_total_dimensions": measured_dimensions,
        "position_consistency_rate": (
            round(consistent_dimensions / measured_dimensions, 4)
            if measured_dimensions else None
        ),
        "winner": winner,
        "winner_basis": "unique_highest_dimension_wins",
    }


def run_tournament(
    candidates: Sequence[Mapping[str, Any]],
    model,
    *,
    reviewer_id: str = "genesis-pairwise-judge-v1",
) -> TournamentResult:
    """Compare every pair twice while preserving real candidate identities."""
    normalized = []
    seen = set()
    for item in candidates:
        candidate_id = str(item.get("id") or "")
        if not candidate_id or candidate_id in seen:
            continue
        proposal = item.get("proposal")
        if not isinstance(proposal, Mapping):
            proposal = {key: value for key, value in item.items() if key != "id"}
        if proposal:
            normalized.append({"id": candidate_id, "proposal": proposal})
            seen.add(candidate_id)

    matches: list[TournamentMatch] = []
    comparisons: list[GenesisPairwiseComparison] = []
    for a, b in combinations(normalized, 2):
        comparison = compare_genesis_candidates(
            a["proposal"],
            b["proposal"],
            model,
            label_a=a["id"],
            label_b=b["id"],
            reviewer_id=reviewer_id,
        )
        comparisons.append(comparison)
        matches.append(TournamentMatch(
            label_a=a["id"],
            label_b=b["id"],
            comparison=comparison.to_dict(),
        ))

    candidate_ids = [item["id"] for item in normalized]
    summary = aggregate_tournament(candidate_ids, comparisons, reviewer_id=reviewer_id)
    return TournamentResult(
        reviewer=reviewer_id,
        candidates=candidate_ids,
        matches=matches,
        summary=summary,
        metadata={"match_count": len(matches), "calls_per_match": 2},
    )
