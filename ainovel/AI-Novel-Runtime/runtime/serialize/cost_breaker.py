"""D180-05: layered cost budget and circuit breaker.

Provides project / volume / batch / chapter / stage / provider layered budget
checking. When a budget is exceeded, the circuit breaker trips and prevents
new paid calls — it does NOT destroy in-progress work. Advisory enforcement
(ADR-003) at report level; the breaker itself is a hard stop on billing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class BudgetLayer:
    layer: str
    limit: float | None
    spent: float
    remaining: float | None
    tripped: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CircuitBreakerReport:
    kind: str
    version: str
    layers: list[BudgetLayer]
    any_tripped: bool
    comparison_only: bool = False  # the breaker is a real hard stop on billing
    gating: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "layers": [l.to_dict() for l in self.layers],
            "any_tripped": self.any_tripped,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def check_budget(
    *,
    project_limit: float | None = None,
    project_spent: float = 0.0,
    volume_limit: float | None = None,
    volume_spent: float = 0.0,
    batch_limit: float | None = None,
    batch_spent: float = 0.0,
    chapter_limit: float | None = None,
    chapter_spent: float = 0.0,
    stage_limit: float | None = None,
    stage_spent: float = 0.0,
    provider_limit: float | None = None,
    provider_spent: float = 0.0,
) -> CircuitBreakerReport:
    layers: list[BudgetLayer] = []

    def _check(layer: str, limit: float | None, spent: float) -> BudgetLayer:
        if limit is None:
            return BudgetLayer(layer=layer, limit=None, spent=spent, remaining=None, tripped=False, notes="no limit set")
        remaining = round(limit - spent, 6)
        tripped = spent >= limit
        return BudgetLayer(
            layer=layer, limit=limit, spent=spent,
            remaining=remaining, tripped=tripped,
            notes="tripped" if tripped else "ok",
        )

    layers.append(_check("project", project_limit, project_spent))
    layers.append(_check("volume", volume_limit, volume_spent))
    layers.append(_check("batch", batch_limit, batch_spent))
    layers.append(_check("chapter", chapter_limit, chapter_spent))
    layers.append(_check("stage", stage_limit, stage_spent))
    layers.append(_check("provider", provider_limit, provider_spent))

    any_tripped = any(l.tripped for l in layers)

    return CircuitBreakerReport(
        kind="circuit_breaker_report",
        version="1.0",
        layers=layers,
        any_tripped=any_tripped,
        metadata={"layer_count": len(layers)},
    )
