"""session.py — Director session (per-chapter decision record).

Assembles the director's per-chapter chain of control (objective / brief /
critique / rewrite / comparison / selection + the selected draft and rationale)
into one schema-backed, auditable artifact. It replaces the ad-hoc `director`
dict Phase 6 attached to the draft. Like commercial-session/revision-session, it
RIDES THE ENVELOPE beside the draft, never inside the frozen ChapterDraft.

This module is advisory and read-side: it never writes facts, never publishes,
and never calibrates real reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "director-session.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def build_director_session(*, chapter_id: str,
                           objective: Optional[dict] = None,
                           brief: Optional[dict] = None,
                           critique: Optional[dict] = None,
                           rewrite_decision: Optional[dict] = None,
                           comparison: Optional[dict] = None,
                           selection: Optional[dict] = None,
                           selected_draft_hash: Optional[str] = None,
                           state_hash: Optional[str] = None,
                           prompt_version: Optional[str] = None,
                           rationale: Optional[list] = None) -> dict[str, Any]:
    """Fold the director's per-chapter decisions into a DirectorSession. Every
    input is optional so the session degrades gracefully — a deterministic serial
    with only an objective+brief still records a valid session (the loop's common
    case); the critique/rewrite/comparison/selection are present only when a
    rewrite/selection actually ran."""
    def _id(d):
        return (d or {}).get("id") if d else None

    return {
        "kind": "director_session",
        "schema_version": "1.0",
        "authority": "human",
        "gating": False,
        "chapter_id": chapter_id,
        "objective_id": _id(objective),
        "brief_id": _id(brief),
        "critique_id": _id(critique),
        "rewrite_decision_id": _id(rewrite_decision),
        "comparison_id": _id(comparison),
        "selection_id": _id(selection),
        "selected_draft_hash": selected_draft_hash,
        "pins": {
            "draft_content_hash": selected_draft_hash,
            "state_hash": state_hash,
            "prompt_version": prompt_version,
        },
        "rationale": rationale or [
            "draft generated from the chapter objective and director brief",
            "quality and publish-readiness signals attached to the envelope",
        ],
    }


def validate_director_session(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs
