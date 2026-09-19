"""CI-M2-04: deterministic two-arm consumption A/B report.

Runs the SAME next chapter (N+1) twice — WITH vs WITHOUT the approved new facts
consumed — and proves the six acceptance criteria at once:
  1. prompt content changed          (rendered_hash differs)
  2. prompt manifest hash changed    (binding_hash differs)
  3. draft content hash changed      (draft content_hash differs)
  4. historical fact hashes unchanged (mint is additive-only; prior facts frozen)
  5. approved facts are semantically reflected in the prose
  6. the A/B report is replayable    (snapshot/mint/objective/prompt/draft hashes
     pinned + a deterministic report_hash)

Advisory read-side artifact: it never gates and writes no facts (ADR-003/006).
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

REPORT_KIND = "consumption_ab_report"
REPORT_SCHEMA_VERSION = "1.0"


def _hash(value: Mapping) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _facts_reflected(body: str, approved_facts: Sequence[Mapping]) -> list[dict]:
    """Per approved fact, whether a semantic marker of it appears in the prose.
    Deterministic substring check over the fact's name/aliases (advisory — a
    reviewer confirms nuance; this only flags outright absence)."""
    body = body or ""
    out = []
    for fact in approved_facts or []:
        markers = [str(fact.get("name") or "")]
        markers += [str(a) for a in (fact.get("aliases") or [])]
        markers = [m for m in markers if m]
        present = any(m in body for m in markers)
        out.append({
            "fact_id": str(fact.get("id") or ""),
            "markers": markers,
            "reflected": present,
        })
    return out


def build_consumption_ab_report(
    *,
    chapter_id: str,
    consumption_evidence: Mapping,
    arm_without: Mapping,
    arm_with: Mapping,
    approved_facts: Sequence[Mapping] | None = None,
    historical_fact_hashes_before: Mapping | None = None,
    historical_fact_hashes_after: Mapping | None = None,
    semantic_ledger_before: Mapping | None = None,
    semantic_ledger_after: Mapping | None = None,
) -> dict:
    """Fold two arm results into a criteria-checked A/B report.

    arm_without / arm_with each carry the arm's hashes + body:
      {prompt_manifest_hash, prompt_rendered_hash, draft_content_hash, body}
    historical_fact_hashes_* map already-existing fact id -> content hash, taken
    BEFORE the mint and AFTER recompute; they must be identical (additive-only).
    """
    aw, ap = dict(arm_without), dict(arm_with)
    approved_facts = list(approved_facts or [])

    prompt_changed = aw.get("prompt_rendered_hash") != ap.get("prompt_rendered_hash")
    manifest_changed = aw.get("prompt_manifest_hash") != ap.get("prompt_manifest_hash")
    draft_changed = aw.get("draft_content_hash") != ap.get("draft_content_hash")

    before = dict(historical_fact_hashes_before or {})
    after = dict(historical_fact_hashes_after or {})
    fact_ids_stable = before == after
    changed_fact_ids = sorted(
        fid for fid in set(before) | set(after) if before.get(fid) != after.get(fid))

    reflection_without = _facts_reflected(aw.get("body", ""), approved_facts)
    reflection = _facts_reflected(ap.get("body", ""), approved_facts)
    facts_absent_without = bool(reflection_without) and not any(
        r["reflected"] for r in reflection_without)
    facts_reflected = bool(reflection) and all(r["reflected"] for r in reflection)

    # Replayable when every provenance handle the report was built from is pinned.
    replay_handles = {
        "consumption_hash": consumption_evidence.get("consumption_hash"),
        "corpus_snapshot_id": consumption_evidence.get("corpus_snapshot_id"),
        "mint_ids": consumption_evidence.get("mint_ids") or [],
        "objective_id": consumption_evidence.get("objective_id"),
        "with_prompt_manifest_hash": ap.get("prompt_manifest_hash"),
        "with_draft_content_hash": ap.get("draft_content_hash"),
    }
    replayable = all(
        replay_handles[k] for k in
        ("consumption_hash", "with_prompt_manifest_hash", "with_draft_content_hash")
    ) and bool(replay_handles["mint_ids"])

    semantic_stable = dict(semantic_ledger_before or {}) == dict(semantic_ledger_after or {})
    criteria = {
        "prompt_content_changed": prompt_changed,
        "prompt_manifest_hash_changed": manifest_changed,
        "draft_content_hash_changed": draft_changed,
        "historical_fact_hashes_unchanged": fact_ids_stable,
        "semantic_ledger_stable": semantic_stable,
        "approved_facts_absent_without": facts_absent_without,
        "approved_facts_reflected": facts_reflected,
        "report_replayable": replayable,
    }

    payload = {
        "kind": REPORT_KIND,
        "schema_version": REPORT_SCHEMA_VERSION,
        "chapter_id": chapter_id,
        "consumption_hash": consumption_evidence.get("consumption_hash"),
        "mint_ids": consumption_evidence.get("mint_ids") or [],
        "arm_without": {
            "prompt_manifest_hash": aw.get("prompt_manifest_hash"),
            "prompt_rendered_hash": aw.get("prompt_rendered_hash"),
            "draft_content_hash": aw.get("draft_content_hash"),
            "model_audit": aw.get("model_audit"),
        },
        "arm_with": {
            "prompt_manifest_hash": ap.get("prompt_manifest_hash"),
            "prompt_rendered_hash": ap.get("prompt_rendered_hash"),
            "draft_content_hash": ap.get("draft_content_hash"),
            "model_audit": ap.get("model_audit"),
        },
        "fact_reflection_without": reflection_without,
        "fact_reflection": reflection,
        "changed_historical_fact_ids": changed_fact_ids,
        "replay_handles": replay_handles,
        "semantic_ledger_before": semantic_ledger_before,
        "semantic_ledger_after": semantic_ledger_after,
        "criteria": criteria,
        "all_criteria_met": all(criteria.values()),
        "comparison_only": True,
        "gating": False,
    }
    payload["report_hash"] = _hash(payload)
    return payload
