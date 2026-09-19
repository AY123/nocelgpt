"""gap.py — place a generated chapter's measurement against the reference anchor.

Given a generated chapter's own feature vector (from measure_reference_chapter,
the SAME instruments) and a pinned ReferenceQualityProfile's bands, produce a
per-feature GAP read: is the generated value inside the market-validated IQR
band [q1,q3], and if not, how far from the band edge (in band-widths) does it sit.

DISCIPLINE: pure/deterministic; COMPARISON-ONLY, never gates (ADR-003). A gap is
a signal for a human, never a build blocker. Absent/empty bands degrade to a
null gap for that feature — the anchor simply has nothing to say there.
"""
from __future__ import annotations

from typing import Optional


def _feature_gap(value, band: dict) -> Optional[dict]:
    """One feature's gap against its band. Returns None when there is nothing to
    compare (no value, or an empty band with n==0)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not band or band.get("n", 0) == 0:
        return None
    q1, q3, median = band.get("q1"), band.get("q3"), band.get("median")
    if q1 is None or q3 is None:
        return None
    value = float(value)
    in_band = q1 <= value <= q3
    # Distance from the nearest band edge, normalized by band width so features
    # on different scales are comparable. Width 0 (all reference chapters equal)
    # falls back to an absolute edge distance.
    width = q3 - q1
    if value < q1:
        edge_gap = q1 - value
        direction = "below"
    elif value > q3:
        edge_gap = value - q3
        direction = "above"
    else:
        edge_gap = 0.0
        direction = "in_band"
    band_widths = round(edge_gap / width, 3) if width > 0 else None
    return {
        "value": round(value, 4),
        "median": median,
        "band": [q1, q3],
        "in_band": in_band,
        "direction": direction,
        "edge_gap": round(edge_gap, 4),
        "band_widths_out": band_widths,
    }


def compare_to_profile(measurement: dict, profile: dict) -> dict:
    """Fold a generated chapter's feature vector against the reference profile's
    bands into a gap read. `measurement` is a flat feature dict (density.* /
    ai_taste.* / hook.*); `profile` is a loaded ReferenceQualityProfile dict.

    Returns {features: {feature: gap|...}, in_band, out_of_band, features_compared,
    comparison_only, gating}. Deterministic; never gates (ADR-003)."""
    bands = (profile or {}).get("bands") or {}
    gaps: dict = {}
    in_band = out_of_band = 0
    for feature, band in bands.items():
        gap = _feature_gap((measurement or {}).get(feature), band)
        if gap is None:
            continue
        gaps[feature] = gap
        if gap["in_band"]:
            in_band += 1
        else:
            out_of_band += 1
    return {
        "features": gaps,
        "features_compared": len(gaps),
        "in_band": in_band,
        "out_of_band": out_of_band,
        "comparison_only": True,
        "gating": False,
    }
