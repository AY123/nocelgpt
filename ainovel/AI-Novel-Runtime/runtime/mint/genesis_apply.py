"""genesis_apply.py — structured book-genesis landing writer (ANES v2, Minimal Genesis / M2).

The mint executor (executor.py) lands PROSE-EXTRACTION candidates: single
entities established by NAME, minimal synthesized records. It structurally
refuses an Event (needs `timeline`, beyond the name-synthesizable set) and never
rewrites the intra-plan references a batch carries. So it cannot land an outline's
event LOG — the exact gap that left projects unable to run a long serial (§14.4).

This module is the OTHER authorized fact-writer for that job. It lives in
runtime/mint/ on purpose: fitness guard #16 says only registry_loader (reads) and
mint/ (writes) may name the facts path, so the ADR-009 boundary stays crossable in
one auditable subdomain. It differs from executor.py in exactly what an outline
import plan needs:

  - lands FULL STRUCTURED records (Event with timeline/sequence_index/participants),
    carried verbatim from build_import_plan — not synthesized from a name;
  - allocates a real ledger id for EVERY accepted candidate up front, then REWRITES
    every cross-candidate reference (participants/causes/effects/timeline/…) from
    the candidate id to its minted id, so nothing dangles after the batch lands;
  - reuses executor's landing discipline WHOLESALE: idmint allocation, the
    validate-then-write gate (_revalidate), and the atomic _commit. It adds the
    remap; it does not fork the write path.

DISCIPLINE (inherited): human-authorized only (confirmed=True); validate-then-
write (a dangling ref / causality cycle / schema break is caught in memory and
writes nothing); idmint is the sole id allocator; a preview writes nothing.
"""
from __future__ import annotations

import copy
import json
from typing import Dict, List, Optional

from .. import derived
from .. import idmint
from ..catalog import Catalog
from ..registry_loader import load as load_registry
from .executor import (MintRefused, _registry_floor, _revalidate, _commit,
                       validator)

GENESIS_RECEIPT_CATEGORY = "genesis-receipts"
GENESIS_RECEIPT_VERSION = "1.0"


def _accepted_items(plan: dict, accepted: Optional[List[str]]) -> List[dict]:
    """The plan items to land. `accepted=None` means every item (genesis opens a
    whole book — the common case); an explicit list restricts + validates."""
    if plan.get("review_status") != "needs_human_review":
        raise MintRefused("plan_not_reviewable",
                          f"review_status={plan.get('review_status')!r}")
    items = plan.get("items", [])
    if accepted is None:
        return list(items)
    acc = list(dict.fromkeys(accepted))
    by_id = {it["candidate_id"] for it in items}
    missing = [c for c in acc if c not in by_id]
    if missing:
        raise MintRefused("unknown_candidate", f"{missing} not in plan {plan.get('id')}")
    return [it for it in items if it["candidate_id"] in set(acc)]


def _allocate_ids(project_path, reg, items: List[dict], *, allocate: bool) -> Dict[str, str]:
    """Build {candidate_id -> id}. With allocate=True each id is a real ledger
    append (idmint.mint_id); with allocate=False (preview) it is a provisional
    monotone id per type code, read-only — mirroring executor._assign_ids. Every
    id is strictly above BOTH the ledger max and the registry floor for its type,
    so a batch open can never clobber an existing entity."""
    id_map: Dict[str, str] = {}
    floors: Dict[str, int] = {}
    next_ord: Dict[str, int] = {}
    led = None if allocate else idmint.load_ledger(project_path)
    for it in items:
        cid = it["candidate_id"]
        type_code = cid.split("-", 1)[0]
        if type_code not in floors:
            floors[type_code] = _registry_floor(reg, type_code)
        if allocate:
            id_map[cid] = idmint.mint_id(
                project_path, type_code,
                minter="runtime:genesis-apply", floor=floors[type_code])
        else:
            base = next_ord.get(
                type_code,
                max(idmint.max_ordinal(led, type_code), floors[type_code]))
            ordinal = base + 1
            next_ord[type_code] = ordinal
            id_map[cid] = idmint.format_id(type_code, ordinal)
    return id_map


def _remap(value, id_map: Dict[str, str]):
    """Deep-rewrite every candidate id anywhere in a record to its minted id.
    Generic (walks strings/lists/dicts) so it catches EVERY reference field —
    id, participants, causes, effects, timeline, abilities, from/to — without
    enumerating them. A string that isn't a candidate id passes through."""
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, list):
        return [_remap(v, id_map) for v in value]
    if isinstance(value, dict):
        return {k: _remap(v, id_map) for k, v in value.items()}
    return value


def _stage_records(items: List[dict], id_map: Dict[str, str]) -> dict:
    """{minted_id: (before_version=0, remapped_record)} for the new entities.
    The record is carried verbatim from the plan (structured, schema-complete),
    with all candidate ids rewritten to minted ids. _commit bumps 0 -> 1."""
    staged: dict = {}
    for it in items:
        record = _remap(copy.deepcopy(it["record"]), id_map)
        record["fact_version"] = 0
        staged[record["id"]] = (0, record)
    return staged


def _next_receipt_id(project_path) -> str:
    ids = []
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == GENESIS_RECEIPT_CATEGORY and e.get("id", "").startswith("GEN-"):
            tail = e["id"].split("-", 1)[1]
            if tail.isdigit():
                ids.append(int(tail))
    return f"GEN-{(max(ids) + 1) if ids else 1:05d}"


def preview_genesis(*, project_path, plan: dict, accepted: Optional[List[str]] = None,
                    schema_dir):
    """Resolve + remap + revalidate WITHOUT writing. Returns (id_map, staged,
    report). Refuses exactly as execute would, so a preview truthfully shows
    whether opening the book would pass the deterministic gate."""
    reg = load_registry(project_path, schema_dir=schema_dir)
    items = _accepted_items(plan, accepted)
    if not items:
        raise MintRefused("nothing_accepted", "no candidates to land")
    id_map = _allocate_ids(project_path, reg, items, allocate=False)
    staged = _stage_records(items, id_map)
    report = _revalidate(project_path, staged, schema_dir)
    return id_map, staged, report


def execute_genesis(*, project_path, plan: dict, accepted: Optional[List[str]] = None,
                    schema_dir, confirmed: bool, actor: Optional[str] = None) -> dict:
    """Cross the ADR-009 boundary: land an outline import plan's candidates as
    structured facts, remapping intra-plan references to minted ids. Requires
    confirmed=True. Validate-then-write: allocate ids, remap, run the full gate in
    memory, and _commit ONLY if it passes — otherwise refuse and write nothing.
    Emits + returns a genesis receipt carrying the id_map (audit trail)."""
    if not confirmed:
        raise MintRefused("not_confirmed",
                          "genesis landing requires explicit human authorization (--confirm)")

    reg = load_registry(project_path, schema_dir=schema_dir)
    catalog = Catalog.load(schema_dir)
    items = _accepted_items(plan, accepted)
    if not items:
        raise MintRefused("nothing_accepted", "no candidates to land")

    id_map = _allocate_ids(project_path, reg, items, allocate=True)
    staged = _stage_records(items, id_map)

    report = _revalidate(project_path, staged, schema_dir)
    if not report.ok:
        raise MintRefused(
            "post_genesis_gate_failed",
            "; ".join(str(f) for f in report.findings
                      if f.severity == validator.SEVERITY_ERROR)
            or "the post-genesis registry did not pass the deterministic gate")

    commit_result = _commit(project_path, reg, catalog, staged)

    receipt_id = _next_receipt_id(project_path)
    receipt = {
        "id": receipt_id,
        "kind": "genesis_receipt",
        "version": GENESIS_RECEIPT_VERSION,
        "authority": "human",
        "gating": False,
        "authorized": {"confirmed": True,
                       "accepted_candidates": [it["candidate_id"] for it in items]},
        "source_plan": {
            "plan_id": plan.get("id", ""),
            "source_outline_id": plan.get("source_outline_id", ""),
        },
        "id_map": id_map,
        "registry_version": {"before": commit_result["rv_before"],
                             "after": commit_result["rv_after"]},
        "landed": [
            {"candidate_id": cid, "entity_id": eid,
             "fact_version": {"before": commit_result["versions"][eid][0],
                              "after": commit_result["versions"][eid][1]}}
            for cid, eid in id_map.items()
        ],
        "actor": actor or "unknown",
    }
    derived.write_artifact(
        project_path=project_path,
        category=GENESIS_RECEIPT_CATEGORY,
        artifact_id=receipt_id,
        artifact=receipt,
        serialized=json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return receipt
