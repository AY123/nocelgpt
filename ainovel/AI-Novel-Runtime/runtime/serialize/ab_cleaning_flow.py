"""ab_cleaning_flow.py — simple A/B sample flow for dialogue cleaning."""
from __future__ import annotations

from typing import Iterable

from .ab_cleaning_report import build_ab_cleaning_report


def build_ab_cleaning_flow(*, samples: Iterable[tuple[str, str]], profiles: Iterable[object]) -> dict:
    samples = list(samples)
    reports = []
    for before, after in samples:
        reports.append(build_ab_cleaning_report(before=before, after=after, profiles=profiles))
    return {
        "kind": "ab_cleaning_flow",
        "sample_count": len(samples),
        "reports": reports,
        "all_stable": all(r["speaker_stability"] for r in reports) if reports else True,
        "avg_delta_confidence": round(sum(r["delta_confidence"] for r in reports) / len(reports), 3) if reports else 0.0,
    }
