"""reference/ — the Reference Quality Anchor subdomain (M9).

The input 1-5 reference novels are HUMAN-SELECTED, market-validated commercial
successes. This subdomain treats them as the quality GROUND TRUTH: it measures
each reference chapter with the SAME deterministic instruments the runtime runs
on generated chapters (density / ai_taste / hook / length), aggregates them into
a pinned ReferenceQualityProfile (per-feature median + IQR band), so a generated
chapter's own measurements can later be compared against "what a market-validated
chapter looks like".

DISCIPLINE:
  - COMPARISON-ONLY, never gates (ADR-003): the profile and any gap read against
    it are advisory; they inform a human, never block a build.
  - READS only; the profile is a DERIVED artifact under registry/derived/, never
    a fact (ADR-006) and never the published log (ADR-009).
  - The deterministic measurement arm imports NO model (guard-enforced). A judge
    arm exists for the double-measure but is opt-in and only runs with a model.
  - Same corpus => same profile (deterministic aggregation), pinned like the
    market snapshot (P0).
"""
from .segment import segment_reference_novel, ReferenceChapter
from .measure import measure_reference_chapter, DETERMINISTIC_FEATURES
from .profile import (build_reference_profile, load_reference_profile,
                      write_reference_profile, ReferenceQualityProfile,
                      PROFILE_ID)
from .writer import build_reference_intelligence, ReferenceProfileResult
from .abstract import (build_reference_abstraction, write_reference_abstraction,
                       load_reference_abstraction, ReferenceAbstractionResult,
                       ABSTRACT_ID)
from .gap import compare_to_profile

__all__ = [
    "segment_reference_novel", "ReferenceChapter",
    "measure_reference_chapter", "DETERMINISTIC_FEATURES",
    "build_reference_profile", "load_reference_profile",
    "write_reference_profile", "ReferenceQualityProfile", "PROFILE_ID",
    "build_reference_intelligence", "ReferenceProfileResult",
    "build_reference_abstraction", "write_reference_abstraction",
    "load_reference_abstraction", "ReferenceAbstractionResult", "ABSTRACT_ID",
    "compare_to_profile",
]
