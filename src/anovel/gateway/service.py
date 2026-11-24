"""Stable logical submissions with durable admission before network I/O."""

from __future__ import annotations

from .ledger import BudgetLedger
from .models import (
    EstimateFeeBound,
    GatewayError,
    GatewayRequest,
    GatewayResult,
    ProviderReply,
    RetryDecision,
)
from .provider import ProviderAdapter


class ModelGateway:
    def __init__(self, ledger: BudgetLedger, adapter: ProviderAdapter) -> None:
        self.ledger = ledger
        self.adapter = adapter

    def submit(
        self,
        request: GatewayRequest,
        policy_id: str,
        attempt_id: str,
        decision: RetryDecision | None = None,
        *,
        estimate_fee: EstimateFeeBound | None = None,
    ) -> GatewayResult:
        policy = next((p for p in request.policies if p.id == policy_id), None)
        if policy is None:
            raise GatewayError("Model policy not frozen in request")
        replay = self.ledger.reserve(
            request, policy, attempt_id, decision, estimate_fee=estimate_fee
        )
        if replay is not None:
            return replay
        permit = self.ledger.mark_dispatch(request.run_id, attempt_id)
        try:
            reply = self.adapter.send(request, policy, attempt_id, permit)
        except Exception:
            # A dispatched adapter failure does not prove non-execution. Never
            # release liability or retry here; credentials/errors are not logged.
            reply = ProviderReply("UNKNOWN", error_code="ADAPTER_INTERRUPTED")
        return self.ledger.finish(request, policy, attempt_id, reply)

    def recover(self, run_id: str, attempt_id: str) -> GatewayResult | None:
        return self.ledger.recover(run_id, attempt_id)
