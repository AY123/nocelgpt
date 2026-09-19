"""select.py — Director version selection.

Turns a comparison report into a selection record. This module is advisory and
read-side: it never writes facts, never publishes, and never calibrates real
reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Optional

from jsonschema import Draft202012Validator

# Lazy-imported at the call site below: a top-level import of serialize.w9_policy
# pulls in serialize/__init__ -> loop -> chapter -> director, a circular import
# (regression from b49fc62). Same fix as director/compare.py.

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "version-selection.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def build_version_selection(*, chapter_id: str, comparison: dict,
                            selected_version: Optional[str] = None,
                            reason: Optional[str] = None,
                            long_arc_plan: Optional[dict] = None,
                            objective: Optional[dict] = None,
                            project_path: Optional[str] = None) -> dict[str, Any]:
    winner = selected_version or comparison.get("winner")
    notes = ["Selection is advisory and recorded for auditability."]
    if objective and objective.get("primary_goal"):
        notes.append(f"objective={objective['primary_goal']}")
    long_arc_band = (comparison.get("summary") or {}).get("long_arc_band")
    if long_arc_band and long_arc_band.get("goal"):
        notes.append(f"long_arc={long_arc_band['goal']}")
    versions = comparison.get("versions") or []
    winner_row = next((row for row in versions if row.get("version_id") == winner), {})
    decision_scores = winner_row.get("decision_scores") or {}
    if project_path:
        from ..serialize.w9_policy import filter_w9_decision_scores
        decision_scores = filter_w9_decision_scores(project_path, decision_scores)
    selection_policy = comparison.get("selection_policy") or {}
    normalized_policy = {
        "primary_metric": selection_policy.get("primary_metric", "reader_pull"),
        "secondary_metric": selection_policy.get("secondary_metric", "quality_consistency"),
        "tie_break": selection_policy.get("tie_break", "earlier_input_order"),
        "decision_dimensions": sorted((comparison.get("selection_policy") or {}).get("decision_dimensions") or []),
        "diagnostic_dimensions": sorted((comparison.get("selection_policy") or {}).get("diagnostic_dimensions") or []),
        "unreliable_dimensions": sorted((comparison.get("selection_policy") or {}).get("unreliable_dimensions") or []),
        "decision_scores": decision_scores,
        "decision_score_mean": mean(list(decision_scores.values())) if decision_scores else None,
    }
    return {
        "id": f"SEL-{chapter_id[-5:] if chapter_id else '00001'}",
        "kind": "version_selection",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "chapter_id": chapter_id,
        "comparison_ref": comparison.get("id"),
        "selected_version": winner,
        "reason": reason or "best aligned with chapter objective and reader pull",
        "selection_policy": normalized_policy,
        "notes": "\n".join(notes),
    }


def validate_version_selection(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs
