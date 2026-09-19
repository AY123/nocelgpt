from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ..execution.tournament import TournamentResult, run_tournament


def _sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def choose_tournament_winner(result: TournamentResult) -> str | None:
    winner = result.summary.get("winner")
    return str(winner) if winner in result.candidates else None


def run_outline_tournament(
    candidates: Sequence[Mapping[str, Any]],
    model=None,
    *,
    judge_models: Sequence[tuple[str, Any]] | None = None,
    reviewer_id: str = "genesis-pairwise-judge-v1",
) -> dict:
    """Run one or more judges over exactly one frozen candidate snapshot.

    ``model`` remains as the backward-compatible single-judge argument.  New
    callers pass named ``judge_models`` so independent provider results can be
    archived and disagreements reported without regenerating candidates.
    """
    if judge_models is None:
        judge_models = [(
            f"{getattr(model, 'primary_provider', getattr(model, 'provider', 'unknown'))}:"
            f"{getattr(model, 'model_id', 'unknown')}",
            model,
        )] if model is not None else []

    frozen = [dict(candidate) for candidate in candidates]
    candidate_hash = _sha256(frozen)
    results = []
    for judge_key, judge_model in judge_models:
        result = run_tournament(
            frozen,
            judge_model,
            reviewer_id=f"{reviewer_id}:{judge_key}",
        )
        provider = str(
            getattr(judge_model, "primary_provider", None)
            or getattr(judge_model, "provider", None)
            or judge_key.split(":", 1)[0]
        )
        model_id = str(getattr(judge_model, "model_id", None) or judge_key)
        summary = result.summary
        call_count = sum(
            len((match.comparison.get("judge_provenance") or {}).get("calls") or {})
            for match in result.matches
        )
        acceptance = {
            "expected_pairs": len(frozen) * (len(frozen) - 1) // 2,
            "completed_pairs": summary["n_pairs"],
            "expected_calls": len(frozen) * (len(frozen) - 1),
            "completed_calls": call_count,
            "n_degraded": summary["n_degraded"],
            "call_error_count": len(summary["call_errors"]),
            "position_consistency_rate": summary["position_consistency_rate"],
        }
        acceptance["passed"] = (
            acceptance["completed_pairs"] == acceptance["expected_pairs"]
            and acceptance["completed_calls"] == acceptance["expected_calls"]
            and acceptance["n_degraded"] == 0
            and acceptance["call_error_count"] == 0
            and acceptance["position_consistency_rate"] is not None
            and acceptance["position_consistency_rate"] >= 0.75
        )
        results.append({
            "judge": judge_key,
            "provider": provider,
            "model": model_id,
            "candidate_hash": candidate_hash,
            "winner": choose_tournament_winner(result),
            "acceptance": acceptance,
            "result": result.to_dict(),
        })

    all_complete = bool(results) and all(
        item["result"]["summary"]["n_degraded"] == 0
        and not item["result"]["summary"]["call_errors"]
        for item in results
    )
    all_accepted = bool(results) and all(
        item["acceptance"]["passed"] for item in results)
    provider_winners = {item["judge"]: item["winner"] for item in results}
    non_null_winners = set(provider_winners.values())
    consensus = (
        next(iter(non_null_winners))
        if all_accepted and len(non_null_winners) == 1 and None not in non_null_winners
        else None
    )
    disagreements = []
    if len(set(provider_winners.values())) > 1:
        disagreements.append({
            "kind": "winner_disagreement",
            "provider_winners": provider_winners,
            "resolution": "human_review_required",
        })
    for item in results:
        summary = item["result"]["summary"]
        if summary["n_degraded"]:
            disagreements.append({
                "kind": "judge_degraded",
                "judge": item["judge"],
                "n_degraded": summary["n_degraded"],
            })

    return {
        "kind": "outline_tournament",
        "reviewer": reviewer_id,
        "candidate_hash": candidate_hash,
        "candidate_ids": [str(candidate.get("id") or "") for candidate in frozen],
        "judges": results,
        "summary": {
            "judge_count": len(results),
            "all_complete": all_complete,
            "all_judges_passed_acceptance": all_accepted,
            "provider_winners": provider_winners,
            "provider_disagreements": disagreements,
            "winner": consensus,
            "winner_authority": "advisory_only",
        },
        "winner": consensus,
        "gating": False,
        "comparison_only": True,
        "calibrates": False,
        "human_authority": True,
        "outline_qa": {
            "status": "not_model_integrated",
            "note": "Outline QA is a separate unfinished capability; tournament success does not complete it.",
        },
    }
