"""N100-063: calibration protocol for predicted vs real platform data.

Defines the protocol for comparing AI-predicted signals (retention, drop-risk,
pay probability) against real platform data (N100-062). Until real data exists,
all predictions stay labeled predicted/diagnostic; no calibration is claimed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class CalibrationMetric:
    metric_name: str
    predicted_values: list[float] = field(default_factory=list)
    real_values: list[float] = field(default_factory=list)
    mae: float | None = None
    correlation: float | None = None
    sample_size: int = 0
    confidence_interval: tuple[float, float] | None = None
    is_calibrated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "predicted_values": list(self.predicted_values),
            "real_values": list(self.real_values),
            "mae": self.mae,
            "correlation": self.correlation,
            "sample_size": self.sample_size,
            "confidence_interval": list(self.confidence_interval) if self.confidence_interval else None,
            "is_calibrated": self.is_calibrated,
        }


@dataclass(frozen=True)
class CalibrationProtocolReport:
    protocol_id: str
    kind: str = "calibration_protocol"
    version: str = "1.0"
    metrics: list[CalibrationMetric] = field(default_factory=list)
    has_real_data: bool = False
    calibrates: bool = False
    all_predictions_labeled: bool = True
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "kind": self.kind,
            "version": self.version,
            "metrics": [m.to_dict() for m in self.metrics],
            "has_real_data": self.has_real_data,
            "calibrates": self.calibrates,
            "all_predictions_labeled": self.all_predictions_labeled,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_calibration_protocol(
    *,
    protocol_id: str,
    predicted: Mapping[str, list[float]] | None = None,
    real: Mapping[str, list[float]] | None = None,
    min_sample: int = 30,
) -> CalibrationProtocolReport:
    metrics: list[CalibrationMetric] = []
    has_real = bool(real)
    all_calibrated = True

    metric_names = set((predicted or {}).keys()) | set((real or {}).keys())
    for name in sorted(metric_names):
        pv = list((predicted or {}).get(name, []))
        rv = list((real or {}).get(name, []))
        sample = min(len(pv), len(rv))
        mae_val = None
        corr = None
        calibrated = False
        if sample >= min_sample and rv:
            diffs = [abs(p - r) for p, r in zip(pv[:sample], rv[:sample])]
            mae_val = round(sum(diffs) / len(diffs), 4)
            if len(diffs) > 1:
                mean_p = sum(pv[:sample]) / sample
                mean_r = sum(rv[:sample]) / sample
                num = sum((p - mean_p) * (r - mean_r) for p, r in zip(pv[:sample], rv[:sample]))
                den_p = (sum((p - mean_p) ** 2 for p in pv[:sample]) ** 0.5)
                den_r = (sum((r - mean_r) ** 2 for r in rv[:sample]) ** 0.5)
                if den_p > 0 and den_r > 0:
                    corr = round(num / (den_p * den_r), 4)
            calibrated = True
        if not calibrated:
            all_calibrated = False
        metrics.append(CalibrationMetric(
            metric_name=name,
            predicted_values=pv,
            real_values=rv,
            mae=mae_val,
            correlation=corr,
            sample_size=sample,
            is_calibrated=calibrated,
        ))

    return CalibrationProtocolReport(
        protocol_id=protocol_id,
        metrics=metrics,
        has_real_data=has_real,
        calibrates=all_calibrated and has_real,
        all_predictions_labeled=not has_real,
        metadata={"min_sample": min_sample, "metric_count": len(metrics)},
    )
