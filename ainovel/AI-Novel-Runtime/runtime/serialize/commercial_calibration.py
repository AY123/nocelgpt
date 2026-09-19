"""Y365-04: commercial signal real calibration reconciler.

Reconciles simulated/diagnostic commercial signals (reader_sim, commercial_verdict)
against real platform signals. Until real data exists, all signals remain
predicted/diagnostic. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CalibrationMetric:
    signal_name: str
    simulated_mean: float | None
    real_mean: float | None
    mae: float | None
    correlation: float | None
    is_calibrated: bool
    label: str  # "calibrated" | "predicted" | "diagnostic" | "no-data"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommercialCalibrationReport:
    kind: str
    version: str
    project_id: str
    metrics: list[CalibrationMetric]
    any_calibrated: bool
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "metrics": [m.to_dict() for m in self.metrics],
            "any_calibrated": self.any_calibrated,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)


def build_commercial_calibration(
    *,
    project_id: str,
    simulated_signals: Mapping[str, list[float]],
    real_signals: Mapping[str, list[float]] | None = None,
    min_sample: int = 10,
) -> CommercialCalibrationReport:
    real = real_signals or {}
    metrics: list[CalibrationMetric] = []
    any_cal = False

    for name in sorted(set(list(simulated_signals.keys()) + list(real.keys()))):
        sim_vals = [float(v) for v in (simulated_signals.get(name) or [])]
        real_vals = [float(v) for v in (real.get(name) or [])]
        n = min(len(sim_vals), len(real_vals))

        sim_mean = round(sum(sim_vals) / len(sim_vals), 4) if sim_vals else None
        real_mean = round(sum(real_vals) / len(real_vals), 4) if real_vals else None

        if n == 0:
            label = "no-data" if not real_vals else "predicted"
            if sim_vals:
                label = "predicted"
            metrics.append(CalibrationMetric(
                signal_name=name,
                simulated_mean=sim_mean,
                real_mean=real_mean,
                mae=None,
                correlation=None,
                is_calibrated=False,
                label=label,
            ))
            continue

        paired_s = sim_vals[:n]
        paired_r = real_vals[:n]
        mae = round(sum(abs(a - b) for a, b in zip(paired_s, paired_r)) / n, 4)
        corr = _pearson(paired_s, paired_r)

        is_cal = n >= min_sample and corr is not None and corr >= 0.6 and mae <= 0.2
        if is_cal:
            any_cal = True
            label = "calibrated"
        elif n >= min_sample:
            label = "diagnostic"
        else:
            label = "predicted"

        metrics.append(CalibrationMetric(
            signal_name=name,
            simulated_mean=sim_mean,
            real_mean=real_mean,
            mae=mae,
            correlation=corr,
            is_calibrated=is_cal,
            label=label,
        ))

    return CommercialCalibrationReport(
        kind="commercial_calibration_report",
        version="1.0",
        project_id=project_id,
        metrics=metrics,
        any_calibrated=any_cal,
        metadata={
            "metric_count": len(metrics),
            "min_sample": min_sample,
            "calibrated_count": sum(1 for m in metrics if m.is_calibrated),
        },
    )
