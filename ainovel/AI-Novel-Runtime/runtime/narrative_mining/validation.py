"""Structure validation for consensus-ready book narrative profiles."""
from __future__ import annotations

from typing import Mapping

from .book_profile import BookProfileError


class BookProfileValidationError(BookProfileError):
    pass


def validate_profile_structure(profile: Mapping, *, snapshot: Mapping, passes: Mapping | None = None) -> list[str]:
    errors: list[str] = []
    if profile.get("corpus_snapshot_id") != snapshot.get("id"):
        errors.append("profile snapshot binding mismatch")
    if profile.get("corpus_manifest_hash") != snapshot.get("manifest_hash"):
        errors.append("profile manifest hash mismatch")

    if _has_raw_prose(profile):
        errors.append("profile contains raw prose or excerpt fields")

    positioning = profile.get("positioning") or {}
    protagonist = profile.get("protagonist") or {}
    progression = profile.get("progression") or {}
    commercial = profile.get("commercial") or {}
    sustainability = profile.get("sustainability") or {}
    confidence = profile.get("confidence") or {}

    if not positioning.get("core_fantasy"):
        errors.append("missing core fantasy")
    if not positioning.get("target_reader"):
        errors.append("missing target reader")
    if not protagonist.get("initial_deficit"):
        errors.append("missing protagonist deficit")
    if protagonist.get("agency_level") not in {"high", "medium", "low", "unknown"}:
        errors.append("invalid protagonist agency level")
    if len(progression.get("growth_axes") or []) == 0:
        errors.append("missing growth axes")
    if len(progression.get("limitations") or []) == 0 and len(progression.get("growth_axes") or []) == 1:
        errors.append("single growth axis without explicit limitation")
    if commercial.get("first_visible_payoff_chapter") is not None and commercial.get("first_visible_payoff_chapter") < 1:
        errors.append("invalid first visible payoff chapter")
    if not commercial.get("first_volume_promise"):
        errors.append("missing first volume promise")
    if not sustainability.get("sources_30_100"):
        errors.append("missing sustainability sources")
    if confidence.get("level") not in {"low", "medium", "high"}:
        errors.append("invalid confidence level")
    if confidence.get("score") is None:
        errors.append("missing confidence score")

    if passes:
        completed = [name for name, result in passes.items() if isinstance(result, Mapping) and result.get("status") == "completed"]
        if not completed:
            errors.append("no completed analysis pass available")
        if len(completed) < 2 and profile.get("analysis", {}).get("method") == "consensus":
            errors.append("consensus profile requires at least two completed passes")

    if profile.get("analysis", {}).get("method") == "consensus" and profile.get("confidence", {}).get("level") == "low":
        errors.append("consensus profile confidence too low")

    if profile.get("commercial", {}).get("first_visible_payoff_chapter") is None and "first_visible_payoff_chapter" in _evidence_fields(profile):
        errors.append("evidence contradicts missing payoff chapter")

    return errors


def _has_raw_prose(profile: Mapping) -> bool:
    text = repr(profile)
    for forbidden in ("excerpt", "source_prose", "original_text", "全文", "原文"):
        if forbidden in text:
            return True
    return False


def _evidence_fields(profile: Mapping) -> set[str]:
    fields = set()
    for item in profile.get("evidence") or []:
        if isinstance(item, Mapping) and item.get("field"):
            fields.add(str(item["field"]))
    return fields
