"""D90-02: reviewer calibration summary.

Compares model (LLM judge) scores against human gold-sample scores per
dimension. Reports sample size, mean absolute error (MAE), Pearson correlation,
and a calibration status per dimension. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DimensionCalibration:
    dimension: str
    sample_size: int
    mae: float | None
    correlation: float | None
    confidence: str  # "high" | "medium" | "low" | "insufficient"
    is_calibrated: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewerCalibrationReport:
    kind: str
    version: str
    reviewer_id: str
    dimensions: list[DimensionCalibration]
    overall_mae: float | None
    overall_correlation: float | None
    min_sample: int
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "reviewer_id": self.reviewer_id,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "overall_mae": self.overall_mae,
            "overall_correlation": self.overall_correlation,
            "min_sample": self.min_sample,
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


def build_reviewer_calibration(
    *,
    reviewer_id: str,
    model_scores: Mapping[str, list[float]],
    human_scores: Mapping[str, list[float]],
    min_sample: int = 10,
) -> ReviewerCalibrationReport:
    dims: list[DimensionCalibration] = []
    all_maes: list[float] = []
    all_corr: list[float] = []

    for dim in sorted(set(list(model_scores.keys()) + list(human_scores.keys()))):
        m_vals = model_scores.get(dim) or []
        h_vals = human_scores.get(dim) or []
        n = min(len(m_vals), len(h_vals))
        if n == 0:
            dims.append(DimensionCalibration(
                dimension=dim, sample_size=0, mae=None, correlation=None,
                confidence="insufficient", is_calibrated=False,
                notes="no paired samples",
            ))
            continue
        paired_m = [float(v) for v in m_vals[:n]]
        paired_h = [float(v) for v in h_vals[:n]]
        mae = round(sum(abs(a - b) for a, b in zip(paired_m, paired_h)) / n, 4)
        corr = _pearson(paired_m, paired_h)
        all_maes.append(mae)
        if corr is not None:
            all_corr.append(corr)
        confidence = "insufficient"
        is_calibrated = False
        if n >= min_sample:
            if corr is not None and corr >= 0.6 and mae <= 2.0:
                confidence = "high"
                is_calibrated = True
            elif n >= min_sample and corr is not None and corr >= 0.3:
                confidence = "medium"
            elif n >= min_sample:
                confidence = "low"
        dims.append(DimensionCalibration(
            dimension=dim, sample_size=n, mae=mae, correlation=corr,
            confidence=confidence, is_calibrated=is_calibrated,
        ))

    overall_mae = round(sum(all_maes) / len(all_maes), 4) if all_maes else None
    overall_corr = round(sum(all_corr) / len(all_corr), 4) if all_corr else None

    return ReviewerCalibrationReport(
        kind="reviewer_calibration_report",
        version="1.0",
        reviewer_id=reviewer_id,
        dimensions=dims,
        overall_mae=overall_mae,
        overall_correlation=overall_corr,
        min_sample=min_sample,
        metadata={
            "dimension_count": len(dims),
            "calibrated_count": sum(1 for d in dims if d.is_calibrated),
        },
    )
