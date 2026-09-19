"""rewrite.py — Director rewrite-decision generation.

Turns critique signals into an explicit rewrite strategy. This module is
advisory and read-side: it never writes facts, never publishes, and never
calibrates real reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "rewrite-decision.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _next_id(prefix: str, seed: Optional[str] = None) -> str:
    if seed:
        return seed
    return f"{prefix}-00001"


def build_rewrite_decision(*, chapter_id: str, round: int = 1,
                           critique: Optional[dict] = None,
                           quality: Optional[dict] = None,
                           commercial: Optional[dict] = None,
                           objective: Optional[dict] = None,
                           decision_id: Optional[str] = None) -> dict[str, Any]:
    critique = critique or {}
    quality = quality or {}
    commercial = commercial or {}
    dims = critique.get("problem_dimensions") or quality.get("problem_dimensions") or []
    decision = critique.get("decision") or "rewrite"
    strategy_mode = "targeted_rewrite" if decision == "rewrite" else "keep"
    return {
        "id": _next_id("RWD", decision_id),
        "kind": "rewrite_decision",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "decision_id": _next_id("RWD", decision_id),
        "chapter_id": chapter_id,
        "round": round,
        "decision": decision,
        "trigger_sources": critique.get("trigger_sources") or ["director_critique"],
        "problem_dimensions": dims,
        "rewrite_strategy": {
            "mode": strategy_mode,
            "scope": critique.get("scope") or ["middle_section", "ending"],
            "actions": critique.get("actions") or [
                "压缩说明性段落",
                "强化冲突推进",
                "增强结尾钩子",
            ],
        },
        "priority": critique.get("priority") or "high",
        "expected_improvement": critique.get("expected_improvement") or [
            "提升 next_chapter_pull",
            "降低 drop_risk",
        ],
        "acceptance_threshold": critique.get("acceptance_threshold") or {
            "quality_min": quality.get("quality_min", 80),
            "commercial_min": commercial.get("commercial_min", 75),
        },
        "human_notes": critique.get("human_notes") or "",
        "notes": objective.get("notes") if objective else "",
    }


def validate_rewrite_decision(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs
