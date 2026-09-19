"""plan.py — stage reconciled candidates as a FactCandidatePlan derived artifact.

Assembles the plan in the shape of contracts/fact-candidate-plan.schema.json and
writes it under registry/derived/fact-candidates/ via derived.write_artifact —
NEVER to registry/facts/ (ADR-006). The plan is inert: review_status is
needs_human_review and policy.writes_registry_facts is false. Minting and the
recompute it triggers are separate, human-authorized workflows (ADR-009),
described in next_workflow but not performed here.

The plan's provenance is DOUBLE-PINNED so it inherits staleness for free
(runtime/derived.py):
  - `source.content_hash` pins the exact draft prose the candidates came from.
  - `reconciled_against` (mirrored into provenance.derived_from) pins each fact
    the reconciliation was computed against. If any of those facts advances
    before the plan is minted, the plan is STALE and must be re-run — you must
    not mint from a reconciliation computed against superseded facts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml

from .. import derived
from ..approval import ApprovalDecision, ApprovalQueue, create_approval_request, record_approval_decision
from ..execution.draft_review import unanchored_entity_reviewer
from ..llm.types import sha256_obj
from ..registry_loader import load as load_registry
from ..serialize.serialization_utils import dump_pretty_json
from .extract import (DeterministicExtractor, LLMExtractor, declared_fields_by_type,
                      entity_roster)
from .reconcile import Reconciliation, reconcile

PLAN_VERSION = "1.0"
CATEGORY = "fact-candidates"
APPROVAL_CATEGORY = "w12-fact-approval"
MINT_CATEGORY = "w12-fact-mint"


def _rationale(recon: Reconciliation) -> str:
    counts = recon.counts()
    parts = [f"{c}={counts[c]}" for c in ("new", "additive", "consistent",
                                          "conflicting", "unverifiable")]
    note = ""
    if counts["conflicting"]:
        note = " — CONFLICTS require human judgement (prose typo? retcon? new fact?)"
    return "候选事实：" + ", ".join(parts) + note


def _unwrap_draft(payload: dict) -> dict:
    """A persisted draft artifact is an ENVELOPE ({draft:{body,...}, director,
    qa_review, ...}); the extractor reads draft.get('body') and expects the INNER
    draft. Unwrap it (carrying the inner provenance/task_id) so the prose actually
    reaches the extractor. Flat payloads (body already at top level) pass through.

    Without this the W12 --chapter-draft-id path fed the envelope to the extractor,
    which found no 'body' and emitted 0 candidates — a built≠live gap the real
    DeepSeek run exposed (envelope body lives one level down)."""
    if isinstance(payload.get("draft"), dict) and "body" in payload["draft"]:
        inner = dict(payload["draft"])
        # carry envelope-level ids the extractor/plan rely on
        for k in ("task_id", "draft_artifact_id", "draft_artifact_path"):
            if k in payload and k not in inner:
                inner[k] = payload[k]
        return inner
    return payload


def _load_draft_from_index(project_path: Path, draft_id: str) -> dict:
    idx = project_path / "registry" / "derived" / "_index.yaml"
    if not idx.exists():
        return {}
    try:
        data = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
        for entry in reversed(data.get("artifacts", []) or []):
            if entry.get("category") == "drafts" and entry.get("id") == draft_id:
                rel = entry.get("path")
                if rel:
                    p = project_path / rel
                    if p.exists():
                        payload = json.loads(p.read_text(encoding="utf-8"))
                        payload.setdefault("task_id", entry.get("id", draft_id))
                        payload.setdefault("draft_artifact_id", entry.get("id", draft_id))
                        payload.setdefault("draft_artifact_path", rel)
                        return _unwrap_draft(payload)
    except Exception:
        return {}
    return {}


def _default_draft(project_path: Path) -> dict:
    idx = project_path / "registry" / "derived" / "_index.yaml"
    if idx.exists():
        try:
            data = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
            drafts = [e for e in data.get("artifacts", []) if e.get("category") == "drafts"]
            if drafts:
                entry = drafts[-1]
                rel = entry.get("draft_artifact_path") or entry.get("path")
                if rel:
                    p = project_path / rel
                    if p.exists():
                        payload = json.loads(p.read_text(encoding="utf-8"))
                        payload.setdefault("task_id", entry.get("id", payload.get("task_id", "chapter-final")))
                        payload.setdefault("draft_artifact_id", entry.get("draft_artifact_id", entry.get("id", "chapter-final")))
                        payload.setdefault("draft_artifact_path", rel)
                        return _unwrap_draft(payload)
        except Exception:
            pass
    for rel in (
        "chapter-final.json",
        "latest/chapter-final.json",
        "build-ch1/chapter-final.json",
    ):
        p = project_path / rel
        if p.exists():
            payload = json.loads(p.read_text(encoding="utf-8"))
            payload.setdefault("task_id", "chapter-final")
            payload.setdefault("draft_artifact_id", "chapter-final")
            payload.setdefault("draft_artifact_path", rel)
            return _unwrap_draft(payload)
    return {}


def _default_known_entities(project_path: Path) -> list[dict]:
    reg = load_registry(project_path)
    return entity_roster(reg, reg.all_ids())


def _resolve_schema_dir(project_path: Path, schema_dir=None):
    """Locate the frozen JSON-schema dir for shape normalization. Prefer the
    caller-supplied path (the serial loop passes its own); otherwise fall back
    to the sibling AI-Novel-Standard convention (same default the CLI uses).
    Returns None if nothing resolves — normalize_candidates then no-ops."""
    if schema_dir is not None:
        return schema_dir
    candidate = Path(project_path).resolve().parent / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"
    return candidate if candidate.is_dir() else None


def _resolve_w12_draft(project_path: Path, draft: Optional[dict], chapter_draft_id: Optional[str]) -> tuple[dict, str]:
    if draft is not None:
        return draft, "direct-draft"
    if chapter_draft_id:
        resolved = _load_draft_from_index(project_path, chapter_draft_id)
        if not resolved:
            raise FileNotFoundError(
                f"chapter draft '{chapter_draft_id}' not found in registry/derived/_index.yaml"
            )
        return resolved, f"derived-index:{chapter_draft_id}"
    return _default_draft(project_path), "default-resolver"


def run_w12_fact_reflow(*, project_path, plan_id: str, draft: Optional[dict] = None,
                        chapter_draft_id: Optional[str] = None,
                        known_entities: Optional[list[dict]] = None,
                        model=None, accepted: Optional[list[str]] = None,
                        approver: str = "human", schema_dir=None) -> dict:
    project_path = Path(project_path)
    draft, draft_source = _resolve_w12_draft(project_path, draft, chapter_draft_id)
    reg = load_registry(project_path) if (project_path / "registry" / "_meta" / "registry-version").exists() else None
    roster = known_entities or _default_known_entities(project_path)
    resolved_schema_dir = _resolve_schema_dir(project_path, schema_dir)
    # constrain the extractor to real schema slots so it stops inventing near-miss
    # field names (possession/summary→description/…), the dominant un-mintable
    # cause CLOSE-15 found. Degrades to None (example-only prompt) if unavailable.
    declared = None
    if resolved_schema_dir is not None:
        try:
            declared = declared_fields_by_type(resolved_schema_dir)
        except Exception:
            declared = None
    extractor = (LLMExtractor(model) if model is not None else DeterministicExtractor())
    candidates = extractor.extract(draft, known_entities=roster, declared_fields=declared)
    if reg is None:
        from .reconcile import Reconciliation
        recon = Reconciliation()
    else:
        # SHAPE-only normalization between extract and reconcile: wrap scalars
        # into arrays, coerce scalar leaves to strings, resolve entity-ref names
        # to live ids — so schema-shape mismatches stop masquerading as
        # un-mintable. Never invents facts; total (failure leaves values as-is).
        from .normalize import normalize_candidates
        candidates = normalize_candidates(
            candidates, reg=reg, schema_dir=resolved_schema_dir)
        recon = reconcile(reg, candidates)
    reviewer = unanchored_entity_reviewer()
    review_report = reviewer.review(draft, {"context": {"entities": roster}})
    review_findings = [
        {"check": f.check, "severity": f.severity, "message": f.message}
        for f in review_report.findings
    ]
    plan, rel = stage_plan(project_path=project_path, plan_id=plan_id, draft=draft,
                           recon=recon, extractor_id=extractor.model_id)

    queue = ApprovalQueue(project_path=project_path)
    request = create_approval_request(
        request_id=f"APR-W12-{plan_id}",
        target_type="mint",
        target_id=plan_id,
        action="confirm_mint",
        reason="W12 fact reflow requires human approval",
        requested_by={"module": "runtime.candidates.plan", "plan_id": plan_id},
        context={"plan_id": plan_id, "source_plan": rel},
    )
    queue.enqueue(request)
    decision = ApprovalDecision.APPROVED if accepted is not None else ApprovalDecision.DEFERRED
    if accepted is not None:
        record_approval_decision(queue, request_id=request.id, decision=decision,
                                 decided_by=approver, notes="W12 mint approved")
    return {
        "plan": plan,
        "derived_path": rel,
        "draft_id": draft.get("task_id", "chapter-final"),
        "draft_source": draft_source,
        "approval_request_id": request.id,
        "approval_status": queue.get_request(request.id).status,
        "candidate_count": len(candidates),
        "reconciled_counts": recon.counts(),
        "review_findings": review_findings,
        "accepted_candidates": accepted or [],
        "extractor_error": getattr(extractor, "last_error", None),
    }


def build_plan(
    *,
    plan_id: str,
    draft: dict,
    recon: Reconciliation,
    extractor_id: str,
) -> dict:
    """Build the FactCandidatePlan artifact dict (schema-shaped). Pure; no I/O.

    NOTE: draft_source (which resolver produced the draft) is deliberately NOT
    placed in the `source` block — fact-candidate-plan.schema.json declares
    source as additionalProperties:false. That runtime-provenance value rides the
    run_w12_fact_reflow RETURN dict (envelope sibling), never the frozen plan."""
    source = {
        "chapter_draft_id": draft.get("task_id", ""),
        "content_hash": draft.get("content_hash", ""),
        "extractor": extractor_id,
    }
    plan = {
        "id": plan_id,
        "kind": "fact_candidate_plan",
        "version": PLAN_VERSION,
        "authority": "human",
        "gating": False,
        "review_status": "needs_human_review",
        "policy": {
            "writes_registry_facts": False,
            "requires_human_approval": True,
            "requires_id_mint_review": True,
        },
        "source": source,
        "reconciled_against": list(recon.reconciled_against),
        "items": [i.to_dict() for i in recon.items],
        "next_workflow": {
            "mint": ("Accepted new/additive candidates are written to "
                     "registry/facts/ and fact_version is bumped — a separate, "
                     "human-authorized workflow paired with the ID Mint Ledger."),
            "recompute": ("After a mint, derived artifacts pinned to the changed "
                          "facts go stale and must be recomputed — a separate "
                          "workflow (Derived Recompute Engine)."),
        },
        "rationale": _rationale(recon),
    }
    return plan


def stage_plan(
    *,
    project_path,
    plan_id: str,
    draft: dict,
    recon: Reconciliation,
    extractor_id: str,
) -> tuple[dict, str]:
    """Build and WRITE the plan as a derived artifact. Returns (plan, rel_path).

    The write goes only to registry/derived/fact-candidates/ and updates the
    provenance index — never registry/facts/. A fitness guard enforces that this
    module imports no facts-writing path."""
    plan = build_plan(plan_id=plan_id, draft=draft, recon=recon,
                       extractor_id=extractor_id)

    # content_hash over the semantic core (everything but the hash itself) so the
    # plan is byte-reproducible from the same draft + registry.
    plan["content_hash"] = sha256_obj({k: v for k, v in plan.items()
                                       if k != "content_hash"})

    # Provenance the derived index/staleness check reads: the reconciled fact
    # pins ARE the plan's derived_from, so the plan goes stale if any advances.
    plan["provenance"] = {
        "derived_from": list(recon.reconciled_against),
        "source_version": None,
    }

    serialized = _canonical(plan)
    rel = derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=plan_id,
        artifact=plan,
        serialized=serialized,
    )
    return plan, rel


def _canonical(plan: dict) -> str:
    return dump_pretty_json(plan)


def next_plan_id(existing_ids: List[str]) -> str:
    """Next FCP-##### id given the ids already present. Deterministic."""
    nums = [int(i.split("-", 1)[1]) for i in existing_ids
            if i.startswith("FCP-") and i.split("-", 1)[1].isdigit()]
    return f"FCP-{(max(nums) + 1) if nums else 1:05d}"
