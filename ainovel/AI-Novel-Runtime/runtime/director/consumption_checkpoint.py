"""N100-043: cross-chapter consumption checkpoint.

Folds consumption evidence + promise ledger + semantic ledger into a single
deterministic checkpoint artifact so the next chapter's prompt binding can
consume ALL prior state in one read. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .consumption import build_consumption_evidence, approved_state_constraints
from .semantic_ledger import render_semantic_ledger


def build_consumption_checkpoint(
    *,
    chapter_id: str,
    approved_candidates: list[Mapping] | None = None,
    mint_records: list[Mapping] | None = None,
    recompute: Mapping | None = None,
    state_before: Mapping | None = None,
    state_after: Mapping | None = None,
    objective_id: str | None = None,
    prompt_manifest_id: str | None = None,
    draft_ref: str | None = None,
    promise_ledger: Mapping | None = None,
    semantic_ledger: Mapping | None = None,
) -> dict[str, Any]:
    evidence = build_consumption_evidence(
        chapter_id=chapter_id,
        approved_candidates=approved_candidates,
        mint_records=mint_records,
        recompute=recompute,
        state_before=state_before,
        state_after=state_after,
        objective_id=objective_id,
        prompt_manifest_id=prompt_manifest_id,
        draft_ref=draft_ref,
    )
    constraints = approved_state_constraints(evidence, state_after)
    promise_summary: dict[str, Any] = {}
    if promise_ledger:
        promise_summary = {
            "overdue": list(promise_ledger.get("overdue") or []),
            "resolved": list(promise_ledger.get("resolved") or []),
            "pending": list(promise_ledger.get("pending") or []),
            "metadata": promise_ledger.get("metadata") or {},
        }
    semantic_text = render_semantic_ledger(semantic_ledger or {})
    payload = {
        "kind": "consumption_checkpoint",
        "version": "1.0",
        "chapter_id": chapter_id,
        "consumption_hash": evidence.get("consumption_hash"),
        "approved_state": evidence,
        "approved_state_constraints": constraints,
        "approved_facts": evidence.get("approved_facts") or [],
        "promise_summary": promise_summary,
        "semantic_ledger_text": semantic_text,
        "gating": False,
        "comparison_only": True,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["checkpoint_hash"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    return payload


def checkpoint_to_prompt_variables(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a consumption checkpoint into the extra variables that
    bind_chapter_draft expects."""
    return {
        "approved_state": checkpoint.get("approved_state"),
        "approved_state_constraints": checkpoint.get("approved_state_constraints") or [],
        "semantic_ledger": checkpoint.get("semantic_ledger_text") or "",
    }
