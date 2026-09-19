from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from .routing import RoutingDecision


@dataclass(frozen=True)
class RoutingEvaluationReport:
    model_id: str
    provider: Optional[str]
    task_type: Optional[str]
    target_style: Optional[str]
    known_failure_mode: Optional[str]
    baseline_pack_id: Optional[str]
    routed_pack_id: Optional[str]
    prompt_version: str
    outcome: str
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_routing(
    *,
    baseline: RoutingDecision,
    routed: RoutingDecision,
    task_type: str | None = None,
    target_style: str | None = None,
    known_failure_mode: str | None = None,
) -> RoutingEvaluationReport:
    if baseline.model_id != routed.model_id:
        raise ValueError("baseline and routed decisions must target the same model")
    if baseline.provider != routed.provider:
        raise ValueError("baseline and routed decisions must target the same provider")

    if baseline.constraint_pack_id == routed.constraint_pack_id:
        outcome = "no_change"
    elif baseline.constraint_pack_id is None and routed.constraint_pack_id is not None:
        outcome = "specialized"
    else:
        outcome = "routed"

    rationale = "; ".join(filter(None, [
        f"baseline={baseline.constraint_pack_id or 'none'}",
        f"routed={routed.constraint_pack_id or 'none'}",
        routed.rationale,
    ]))
    return RoutingEvaluationReport(
        model_id=routed.model_id,
        provider=routed.provider,
        task_type=task_type,
        target_style=target_style,
        known_failure_mode=known_failure_mode,
        baseline_pack_id=baseline.constraint_pack_id,
        routed_pack_id=routed.constraint_pack_id,
        prompt_version=routed.prompt_version,
        outcome=outcome,
        rationale=rationale,
    )
