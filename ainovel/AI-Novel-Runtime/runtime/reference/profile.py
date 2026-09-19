"""profile.py — aggregate per-chapter reference measurements into a pinned profile.

The ReferenceQualityProfile is the quality ANCHOR: for each comparable feature it
records the market-validated distribution (median + IQR band [q1,q3] + n) folded
across every measured reference chapter, so a generated chapter's measurement can
later be placed against the band (M9.1) WITHOUT the saturating LLM judge.

DISCIPLINE: pinned DERIVED artifact under registry/derived/reference/ (never a
fact, ADR-006); deterministic aggregation; comparison-only, never gates (ADR-003);
imports NO model (pure statistics, guard-enforced).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .measure import DETERMINISTIC_FEATURES, measure_reference_chapter
from .segment import segment_reference_novel

SCHEMA_VERSION = "1.0"
PROFILE_ID = "REFPROFILE-001"


def derived_reference_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "registry" / "derived" / "reference"


def _percentile(sorted_xs: List[float], q: float) -> float:
    if not sorted_xs:
        return 0.0
    if len(sorted_xs) == 1:
        return float(sorted_xs[0])
    pos = q * (len(sorted_xs) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 >= len(sorted_xs):
        return float(sorted_xs[lo])
    return float(sorted_xs[lo] + (sorted_xs[lo + 1] - sorted_xs[lo]) * frac)
def _band(values: List[float]) -> dict:
    """Fold a feature's per-chapter values into a distribution band: median, the
    IQR [q1,q3], min/max, and n. Deterministic; empty => a null band."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return {"n": 0, "median": None, "q1": None, "q3": None, "min": None, "max": None}
    return {
        "n": n,
        "median": round(_percentile(xs, 0.5), 4),
        "q1": round(_percentile(xs, 0.25), 4),
        "q3": round(_percentile(xs, 0.75), 4),
        "min": round(xs[0], 4),
        "max": round(xs[-1], 4),
    }


@dataclass(frozen=True)
class ReferenceQualityProfile:
    """The pinned quality anchor: per-feature market-validated distribution bands
    folded across all measured reference chapters. Advisory, never gates."""
    id: str
    source_ids: List[str]
    chapters_measured: int
    bands: dict = field(default_factory=dict)   # feature -> band dict
    judge_bands: dict = field(default_factory=dict)  # judge.<dim> -> band (opt-in)
    gating: bool = False                         # ADR-003: never gates

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schema_version": SCHEMA_VERSION,
            "kind": "reference_quality_profile",
            "source_ids": self.source_ids,
            "chapters_measured": self.chapters_measured,
            "bands": self.bands,
            "judge_bands": self.judge_bands,
            "gating": self.gating,
        }
def build_reference_profile(sources: List[tuple], *, reviewer=None) -> ReferenceQualityProfile:
    """Segment + measure every reference novel and fold the per-chapter feature
    vectors into a ReferenceQualityProfile.

    `sources` is [(source_id, full_text), ...] (from outline.sources loading).
    The deterministic arm always runs; the optional `reviewer` adds judge.<dim>
    bands (the double-measure). Deterministic given (sources, reviewer)."""
    per_feature: dict = {}
    judge_feature: dict = {}
    source_ids: List[str] = []
    chapters_measured = 0
    for source_id, text in sources:
        source_ids.append(source_id)
        for chapter in segment_reference_novel(source_id, text):
            feats = measure_reference_chapter(chapter.body, reviewer=reviewer)
            if not feats:
                continue
            chapters_measured += 1
            for key, val in feats.items():
                bucket = judge_feature if key.startswith("judge.") else per_feature
                bucket.setdefault(key, []).append(val)
    # Band only the declared comparable deterministic features (identity/size
    # features are measured but excluded — they are not quality signals alone).
    bands = {f: _band(per_feature[f]) for f in DETERMINISTIC_FEATURES if f in per_feature}
    judge_bands = {f: _band(vals) for f, vals in sorted(judge_feature.items())}
    return ReferenceQualityProfile(
        id=PROFILE_ID,
        source_ids=source_ids,
        chapters_measured=chapters_measured,
        bands=bands,
        judge_bands=judge_bands,
    )
def write_reference_profile(project_path: str | Path,
                            profile: ReferenceQualityProfile) -> str:
    """Persist the profile under registry/derived/reference/ (pinned, like the
    market snapshot). A DERIVED artifact, never a fact. Returns the rel path."""
    out_dir = derived_reference_dir(project_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{profile.id}.json"
    path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path.relative_to(Path(project_path)))


def load_reference_profile(project_path: str | Path) -> Optional[dict]:
    """Return the pinned ReferenceQualityProfile dict if built, else None.
    Consumers treat absence as 'no reference anchor yet' and fall back."""
    path = derived_reference_dir(project_path) / f"{PROFILE_ID}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
