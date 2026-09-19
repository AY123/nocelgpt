"""Y365-01: platform feedback closed-loop collector and reconciler.

Collects real platform signals (clicks, retention, subscriptions, tips, votes,
abandonment) and reconciles them against predicted/diagnostic signals. Does NOT
rewrite facts or text from platform data. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PlatformSignalBatch:
    batch_id: str
    platform: str
    window_start: str
    window_end: str
    sample_size: int
    signals: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciledSignal:
    signal_name: str
    predicted: float | None
    actual: float | None
    delta: float | None
    direction: str  # "over-predicted" | "under-predicted" | "matched" | "no-data"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlatformFeedbackReconciliation:
    kind: str
    version: str
    project_id: str
    batches: list[PlatformSignalBatch]
    reconciled: list[ReconciledSignal]
    has_real_data: bool
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "batches": [b.to_dict() for b in self.batches],
            "reconciled": [r.to_dict() for r in self.reconciled],
            "has_real_data": self.has_real_data,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def reconcile_platform_feedback(
    *,
    project_id: str,
    batches: Sequence[Mapping[str, Any]],
    predicted_signals: Mapping[str, float] | None = None,
) -> PlatformFeedbackReconciliation:
    parsed_batches: list[PlatformSignalBatch] = []
    has_real = False
    all_actual: dict[str, list[float]] = {}

    for b in batches:
        signals = dict(b.get("signals") or {})
        sample = int(b.get("sample_size") or 0)
        if sample > 0:
            has_real = True
        for k, v in signals.items():
            if isinstance(v, (int, float)):
                all_actual.setdefault(k, []).append(float(v))
        parsed_batches.append(PlatformSignalBatch(
            batch_id=str(b.get("batch_id") or ""),
            platform=str(b.get("platform") or ""),
            window_start=str(b.get("window_start") or ""),
            window_end=str(b.get("window_end") or ""),
            sample_size=sample,
            signals=signals,
            confidence=b.get("confidence"),
        ))

    predicted = predicted_signals or {}
    reconciled: list[ReconciledSignal] = []
    all_keys = sorted(set(list(predicted.keys()) + list(all_actual.keys())))
    for key in all_keys:
        p_val = predicted.get(key)
        a_vals = all_actual.get(key) or []
        a_val = round(sum(a_vals) / len(a_vals), 4) if a_vals else None
        delta = None
        direction = "no-data"
        if p_val is not None and a_val is not None:
            delta = round(a_val - p_val, 4)
            if abs(delta) < 0.01:
                direction = "matched"
            elif delta > 0:
                direction = "under-predicted"
            else:
                direction = "over-predicted"
        elif p_val is not None and a_val is None:
            direction = "predicted-only"
        reconciled.append(ReconciledSignal(
            signal_name=key,
            predicted=p_val,
            actual=a_val,
            delta=delta,
            direction=direction,
        ))

    return PlatformFeedbackReconciliation(
        kind="platform_feedback_reconciliation",
        version="1.0",
        project_id=project_id,
        batches=parsed_batches,
        reconciled=reconciled,
        has_real_data=has_real,
        metadata={"batch_count": len(parsed_batches), "signal_count": len(reconciled)},
    )
