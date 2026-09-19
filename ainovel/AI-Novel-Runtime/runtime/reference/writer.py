"""writer.py — build + persist the Reference Quality Profile (M9).

Loads the project's 1-5 reference novels (sources/reference-novels/, via
outline.sources), folds them into a ReferenceQualityProfile with the SAME
deterministic detectors the runtime runs on generated chapters, validates the
result against the frozen contract, and pins it under registry/derived/reference/
(a DERIVED artifact, ADR-006 — never a fact, never the published log).

DISCIPLINE:
  - COMPARISON-ONLY, never gates (ADR-003).
  - The deterministic arm imports NO model. The optional judge arm is opt-in:
    a reviewer is injected by the caller (build_reference_profile's `reviewer`),
    so THIS module never imports the LM stack directly either.
  - Same corpus => same profile; validated against the frozen schema before write.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ..outline.sources import load_reference_sources, iter_source_texts
from .profile import (build_reference_profile, derived_reference_dir,
                      write_reference_profile, load_reference_profile,
                      PROFILE_ID, ReferenceQualityProfile)


@dataclass(frozen=True)
class ReferenceProfileResult:
    ok: bool
    stage: str
    message: str
    profile_json: str | None = None
    chapters_measured: int | None = None
    sources: int | None = None
    has_judge_bands: bool | None = None
    errors: list[str] | None = None


def _load_source_texts(project_path: str | Path) -> Tuple[bool, List[tuple], list]:
    """Load reference novels into [(source_id, text), ...] for the profile builder.
    Returns (ok, sources, errors)."""
    check = load_reference_sources(project_path)
    if not check.ok:
        return False, [], list(check.errors)
    pairs = [(src.id, text) for src, text in iter_source_texts(project_path, check.sources)]
    return True, pairs, []


def build_reference_intelligence(project_path: str | Path, *,
                                 reviewer=None) -> ReferenceProfileResult:
    """Segment + measure the reference novels into a pinned ReferenceQualityProfile.

    The deterministic arm always runs. When a `reviewer` (a DraftReviewer, e.g.
    the LMQualityJudge) is supplied, the opt-in judge arm adds judge.<dim> bands
    (the double-measure). Validates against the frozen contract before writing —
    Schema-First: a profile that would not conform is never persisted.
    """
    project = Path(project_path)
    ok, sources, errors = _load_source_texts(project)
    if not ok:
        return ReferenceProfileResult(
            ok=False, stage="sources",
            message="reference source validation failed", errors=errors)

    profile = build_reference_profile(sources, reviewer=reviewer)
    if profile.chapters_measured == 0:
        return ReferenceProfileResult(
            ok=False, stage="measure",
            message="no measurable reference chapters found "
                    "(sources present but empty/too short after segmentation)",
            errors=["0 chapters measured"])

    _validate_profile(profile)  # Schema-First guard before write.

    rel = write_reference_profile(project, profile)
    return ReferenceProfileResult(
        ok=True, stage="done",
        message="reference quality profile produced",
        profile_json=rel,
        chapters_measured=profile.chapters_measured,
        sources=len(profile.source_ids),
        has_judge_bands=bool(profile.judge_bands))


_SCHEMA_REL = ("AI-Novel-Standard", "contracts",
               "reference-quality-profile.schema.json")


def _standard_contracts_path() -> Path:
    """The frozen contract lives in the sibling AI-Novel-Standard repo."""
    # runtime/reference/writer.py -> AI-Novel-Runtime -> repo root -> sibling
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root.joinpath(*_SCHEMA_REL)


def _validate_profile(profile: ReferenceQualityProfile) -> None:
    """Validate the profile dict against the frozen contract. Raises on drift so
    a non-conforming profile is never pinned (Schema-First). A missing jsonschema
    or contract file degrades to a no-op — the caller still gets a profile, but
    conformance is asserted wherever the contract is reachable (tests + CI)."""
    schema_path = _standard_contracts_path()
    if not schema_path.exists():
        return
    try:
        import jsonschema  # optional at runtime; always present in tests/CI
    except ImportError:
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(profile.to_dict(), schema)
