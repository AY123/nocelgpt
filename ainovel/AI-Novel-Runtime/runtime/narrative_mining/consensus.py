"""Consensus assembly for book narrative profiles."""
from __future__ import annotations

from typing import Mapping

from .book_profile import BookProfileError
from .validation import validate_profile_structure


class BookProfileConsensusError(BookProfileError):
    pass


_REQUIRED_FIELDS = (
    "positioning",
    "protagonist",
    "progression",
    "commercial",
    "sustainability",
)


def build_consensus_profile(*, deterministic: Mapping, top_down: Mapping, bottom_up: Mapping, snapshot: Mapping) -> dict:
    for part in (deterministic, top_down, bottom_up):
        if part.get("corpus_snapshot_id") != snapshot["id"]:
            raise BookProfileConsensusError("analysis pass snapshot binding is invalid")
    if top_down.get("status") != "completed" and bottom_up.get("status") != "completed":
        raise BookProfileConsensusError("no completed analysis pass available for consensus")

    findings = dict(deterministic)
    findings.update(_merge_pass_findings(top_down, bottom_up))
    evidence = list(deterministic.get("evidence", [])) + list(top_down.get("evidence", [])) + list(bottom_up.get("evidence", []))
    confidence = _consensus_confidence(deterministic, top_down, bottom_up)
    profile = {
        "id": deterministic["id"],
        "kind": deterministic["kind"],
        "schema_version": deterministic["schema_version"],
        "book_id": deterministic["book_id"],
        "corpus_snapshot_id": deterministic["corpus_snapshot_id"],
        "corpus_manifest_hash": deterministic["corpus_manifest_hash"],
        "analysis": {
            "method": "consensus",
            "analyzer_version": deterministic["analysis"]["analyzer_version"],
            "prompt_version": deterministic["analysis"]["prompt_version"],
            "model_policy_version": deterministic["analysis"]["model_policy_version"],
        },
        "positioning": _merge_positioning(deterministic, top_down, bottom_up),
        "protagonist": findings.get("protagonist", deterministic["protagonist"]),
        "progression": findings.get("progression", deterministic["progression"]),
        "commercial": findings.get("commercial", deterministic["commercial"]),
        "sustainability": findings.get("sustainability", deterministic["sustainability"]),
        "evidence": evidence,
        "confidence": confidence,
    }
    errors = validate_profile_structure(profile, snapshot=snapshot, passes={"deterministic": deterministic, "top_down": top_down, "bottom_up": bottom_up})
    if errors:
        raise BookProfileConsensusError("; ".join(errors))
    return profile


def _merge_pass_findings(top_down: Mapping, bottom_up: Mapping) -> dict:
    merged = {}
    if top_down.get("status") == "completed":
        merged.update(_from_analysis_pass(top_down))
    if bottom_up.get("status") == "completed":
        merged.update(_from_analysis_pass(bottom_up))
    return merged


def _merge_positioning(deterministic: Mapping, top_down: Mapping, bottom_up: Mapping) -> dict:
    base = dict(deterministic.get("positioning", {}))
    if top_down.get("status") == "completed":
        base.update({k: v for k, v in _from_analysis_pass(top_down)["positioning"].items() if v not in (None, "", [])})
    if bottom_up.get("status") == "completed":
        base.update({k: v for k, v in _from_analysis_pass(bottom_up)["positioning"].items() if v not in (None, "", [])})
    return base


def _from_analysis_pass(pass_result: Mapping) -> dict:
    findings = pass_result.get("findings") or {}
    return {
        "positioning": {
            "genre": pass_result.get("analysis", {}).get("genre", ""),
            "subgenres": [],
            "core_fantasy": findings.get("core_fantasy", ""),
            "target_reader": findings.get("target_reader", []),
            "one_line_selling_point": findings.get("selling_point", ""),
        },
        "protagonist": {
            "initial_deficit": findings.get("protagonist_deficit", ""),
            "long_term_desire": findings.get("long_term_desire", ""),
            "agency_level": "high" if findings.get("protagonist_deficit") else "low",
        },
        "progression": {
            "core_ability": findings.get("core_ability", ""),
            "limitations": findings.get("limitations", []),
            "growth_axes": findings.get("growth_axes", []),
        },
        "commercial": {
            "first_visible_payoff_chapter": findings.get("first_visible_payoff_chapter"),
            "first_volume_promise": findings.get("first_volume_promise", ""),
        },
        "sustainability": {
            "sources_30_100": findings.get("sustainability_sources", []),
            "mid_stage_risks": findings.get("mid_stage_risks", []),
        },
    }


def _consensus_confidence(deterministic: Mapping, top_down: Mapping, bottom_up: Mapping) -> dict:
    scored = [deterministic.get("confidence", {}).get("score", 0.0)]
    scored.extend(pass_result.get("confidence", {}).get("score", 0.0) for pass_result in (top_down, bottom_up) if pass_result.get("status") == "completed")
    score = round(sum(scored) / len(scored), 3)
    level = "low" if score < 0.4 else "medium" if score < 0.7 else "high"
    limitations = []
    if top_down.get("status") != "completed":
        limitations.append("top_down_analysis_degraded")
    if bottom_up.get("status") != "completed":
        limitations.append("bottom_up_analysis_degraded")
    limitations.extend(deterministic.get("confidence", {}).get("limitations", []))
    return {"level": level, "score": score, "limitations": sorted(set(limitations))}
