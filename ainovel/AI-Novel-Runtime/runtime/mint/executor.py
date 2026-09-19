"""executor.py — the mint executor (ANES v2, roadmap Phase 5.2).

The ONLY fact-writer in the system. Promotes human-accepted `additive` candidates
from a FactCandidatePlan into registry/facts/, bumping fact_version and the
monotone registry version, and emits an auditable MintReceipt. Validate-then-write:
nothing touches disk unless the post-mint registry passes the full gate.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import yaml

from .. import derived
from .. import idmint
from ..catalog import Catalog
from ..registry_loader import Registry, load as load_registry
from .. import validator
from ..approval import (
    ApprovalDecision,
    ApprovalQueue,
    create_approval_request,
    record_approval_decision,
)
from ..serialize.serialization_utils import dump_pretty_json

# A `new` entity is minted only when its whole required-field set can be
# synthesized from a name-establishing candidate. These are the fields the
# executor supplies for a minimal record; any type needing more (Event.timeline,
# Timeline.kind, WorldRule.rule_kind/statement, Relationship.from/to/kind) is
# refused, not guessed — establish it by name here, add structure via later
# additive mints or a structured authoring workflow.
_SYNTHESIZABLE_REQUIRED = {"id", "name", "fact_version", "status"}

RECEIPT_CATEGORY = "mint-receipts"
RECEIPT_VERSION = "1.0"
_RUNTIME_FIELDS = ("_source_path",)


class MintRefused(Exception):
    """Raised when a mint cannot proceed. Carries a machine-usable reason so the
    CLI can report exactly why the boundary was NOT crossed. Refusal writes
    nothing — the SSOT is untouched."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass
class MintItem:
    """One application resolved from an accepted candidate.

    `classification` is 'additive' (fill an empty field on an existing entity) or
    'new' (establish a brand-new entity by name). For an additive item `entity_id`
    is the existing entity and `type_code` is None; for a new item `entity_id` is
    filled in at execution time with the ledger-minted id and `type_code` is the
    resolved frozen type code."""
    candidate_id: str
    entity_id: str
    field: str
    value: Any
    classification: str = "additive"
    type_code: Optional[str] = None


@dataclass
class MintPlan:
    """The resolved, refusal-checked set of additive writes a confirmed mint will
    apply. Pure data — building it touches no disk."""
    plan_id: str
    plan_content_hash: str
    chapter_draft_id: str
    items: List[MintItem] = field(default_factory=list)


def _dotted_set(record: dict, dotted: str, value: Any) -> None:
    """Set a possibly-dotted field path, creating intermediate dicts. Mutates the
    given record (always a deep copy in this module, never the live registry)."""
    parts = dotted.split(".")
    cur = record
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _dotted_get(record: dict, dotted: str):
    cur: Any = record
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple)) and len(value) == 0:
        return True
    return False


def _resolve_new_type_code(target_type: str, catalog: Catalog) -> str:
    """Map a candidate's target_type (an entity NAME, e.g. 'Character') to its
    frozen type code (CHR). Refuses when the name is unknown or maps to more than
    one code (WorldRule → MAG|TEC): a `new` mint must not guess magic-vs-tech."""
    codes = sorted(tc for tc in catalog.type_codes()
                   if catalog.entity_name(tc) == target_type)
    if not codes:
        raise MintRefused("unknown_target_type",
                          f"target_type {target_type!r} is not a catalog entity")
    if len(codes) > 1:
        raise MintRefused(
            "ambiguous_type_code",
            f"target_type {target_type!r} maps to multiple type codes {codes}; "
            f"a human must disambiguate before a new entity can be minted")
    return codes[0]


def _required_fields(schema_dir, catalog: Catalog, type_code: str) -> set:
    """The required-field set of a type's frozen entity schema. Used to decide
    whether a minimal name-establishing record satisfies the type — i.e. whether
    a `new` candidate is mintable this phase or must be refused for structure."""
    schema_path = Path(schema_dir) / catalog.schema_file(type_code)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return set(schema.get("required", []))


def plan_mint(plan: dict, accepted: List[str], *,
              catalog: Optional[Catalog] = None, schema_dir=None) -> MintPlan:
    """Resolve a MintPlan from a FactCandidatePlan + the candidate ids a human
    accepted. PURE (no I/O for the additive path; reads schema files to validate
    the `new` path). Refuses before any write is contemplated:
      - a plan not in needs_human_review status;
      - an accepted id absent from the plan;
      - an `additive` candidate with no matched entity;
      - a `new` candidate outside the mintable subset (not name-establishing, an
        ambiguous type, or a type needing structured fields) — refused, not
        guessed;
      - any other class (conflicting/consistent/unverifiable) — refused, not
        silently skipped (a conflicting retcon is a separate human workflow)."""
    if plan.get("review_status") != "needs_human_review":
        raise MintRefused("plan_not_reviewable",
                          f"review_status={plan.get('review_status')!r}")
    by_id = {it["candidate_id"]: it for it in plan.get("items", [])}
    accepted_set = list(dict.fromkeys(accepted))  # dedupe, keep order
    if not accepted_set:
        raise MintRefused("nothing_accepted",
                          "no candidate ids were accepted for minting")

    items: List[MintItem] = []
    for cid in accepted_set:
        it = by_id.get(cid)
        if it is None:
            raise MintRefused("unknown_candidate",
                              f"{cid} is not in plan {plan.get('id')}")
        cls = it.get("classification")
        if cls == "additive":
            items.append(_resolve_additive(cid, it))
        elif cls == "new":
            items.append(_resolve_new(cid, it, catalog, schema_dir))
        else:
            raise MintRefused(
                "non_mintable_class",
                f"{cid} is {cls!r}; mint applies only 'additive' or 'new' "
                f"(conflicting is a retcon — a separate human-authorized workflow; "
                f"consistent/unverifiable need no write)")

    return MintPlan(
        plan_id=plan.get("id", ""),
        plan_content_hash=plan.get("content_hash", ""),
        chapter_draft_id=plan.get("source", {}).get("chapter_draft_id", ""),
        items=items,
    )


def _resolve_additive(cid: str, it: dict) -> MintItem:
    entity_id = it.get("matched_entity_id")
    if not entity_id:
        raise MintRefused("additive_without_entity",
                          f"{cid} is additive but has no matched_entity_id")
    return MintItem(
        candidate_id=cid,
        entity_id=entity_id,
        field=it["field"],
        value=it.get("extracted_value"),
        classification="additive",
    )


def _resolve_new(cid: str, it: dict, catalog: Optional[Catalog], schema_dir) -> MintItem:
    """Resolve a `new` candidate into a mintable item, or refuse. entity_id is
    left empty here — the real id is allocated from the ledger at execution time
    (plan_mint is pure); preview fills a provisional id separately."""
    if catalog is None or schema_dir is None:
        # Defensive: only execute/preview call with a `new` item, and both supply
        # these. A caller reaching the new path without them is a programming bug.
        raise MintRefused("new_needs_catalog",
                          f"{cid} is new but no catalog/schema_dir was supplied")
    if it.get("field") != "name":
        raise MintRefused(
            "new_needs_name",
            f"{cid} is new but establishes {it.get('field')!r}, not 'name'; a new "
            f"entity is minted by name first, then extended by additive mints")
    type_code = _resolve_new_type_code(it.get("target_type", ""), catalog)
    required = _required_fields(schema_dir, catalog, type_code)
    unmet = required - _SYNTHESIZABLE_REQUIRED
    if unmet:
        raise MintRefused(
            "new_requires_structured_fields",
            f"{cid} ({type_code}) needs structured field(s) {sorted(unmet)} that "
            f"cannot be synthesized from a name; author it explicitly instead")
    return MintItem(
        candidate_id=cid,
        entity_id="",  # filled with the minted id at execution time
        field="name",
        value=it.get("extracted_value"),
        classification="new",
        type_code=type_code,
    )


def _check_not_stale(reg: Registry, plan: dict) -> None:
    """Refuse a plan whose reconciliation is stale (ADR-006): any fact it was
    reconciled against has advanced since. Minting from a superseded
    reconciliation could write a value that no longer fits the current fact."""
    reasons = derived.check_staleness(reg, plan.get("reconciled_against", []))
    if reasons:
        raise MintRefused("plan_stale", "; ".join(reasons))


def _apply_in_memory(reg: Registry, mint_plan: MintPlan) -> dict:
    """Return {entity_id: (before_version, after_record)} for the writes, computed
    on DEEP COPIES. The live registry is never mutated. For a `new` item the
    entity_id must already be assigned (a minted or provisional id) and a minimal
    record is synthesized. For an `additive` item the existing entity is copied and
    refused if the target field is no longer empty (the reconciliation said
    additive, but the fact changed underneath — belt-and-suspenders alongside the
    staleness check)."""
    staged: dict = {}
    for item in mint_plan.items:
        if item.classification == "new":
            if not item.entity_id:
                raise MintRefused("new_id_unassigned",
                                  f"{item.candidate_id} is new but no id was allocated")
            record = staged.get(item.entity_id, (None, None))[1]
            if record is None:
                # A minimal name-establishing record. Required fields beyond these
                # were refused in plan_mint, so this is always schema-complete for
                # the scoped subset (Character/Item).
                record = {"id": item.entity_id, "name": item.value,
                          "status": "active", "fact_version": 0}
                before_version = 0
            else:
                before_version = staged[item.entity_id][0]
            staged[item.entity_id] = (before_version, record)
            continue

        entity = reg.get(item.entity_id)
        if entity is None:
            raise MintRefused("entity_gone",
                              f"{item.entity_id} no longer exists in the registry")
        record = staged.get(item.entity_id, (None, None))[1]
        if record is None:
            record = copy.deepcopy(entity)
            record.pop("_source_path", None)
            before_version = int(record.get("fact_version", 0))
        else:
            before_version = staged[item.entity_id][0]

        found, existing = _dotted_get(record, item.field)
        if found and not _is_empty(existing):
            raise MintRefused(
                "field_no_longer_empty",
                f"{item.entity_id}.{item.field} is no longer empty "
                f"(={existing!r}); additive mint would overwrite it")
        _dotted_set(record, item.field, item.value)
        staged[item.entity_id] = (before_version, record)
    return staged


def _registry_floor(reg: Registry, type_code: str) -> int:
    """Highest ordinal for `type_code` among the ids ALREADY in the registry. The
    ledger is normally the sole allocator, but a Project seeded before the ledger
    existed (header drift) can hold facts the ledger has no entry for. Allocating
    strictly above this floor means a divergent ledger can never mint an id that
    already exists on disk — closing the silent-clobber hole where minting
    CHR-00001 would overwrite an existing CHR-00001."""
    hi = 0
    for entity_id in reg.facts:
        code, _, tail = entity_id.partition("-")
        if code == type_code and tail.isdigit():
            hi = max(hi, int(tail))
    return hi


def _assign_ids(project_path, reg: Registry, catalog: Catalog, mint_plan: MintPlan,
                *, allocate: bool) -> None:
    """Fill each `new` item's entity_id, always strictly above BOTH the ledger max
    and the highest existing registry ordinal for that type code (the floor). With
    allocate=True the id comes from the append-only ledger (idmint.mint_id — a
    real, serialized append). With allocate=False (preview) it is computed
    READ-ONLY, so a preview writes no ledger entry yet shows the id that would be
    minted. Additive items are untouched. Refuses (collision guard) if an
    allocated id somehow already exists — a mint must never overwrite an entity."""
    floors = {}
    for item in mint_plan.items:
        if item.classification == "new":
            floors.setdefault(item.type_code, _registry_floor(reg, item.type_code))

    if allocate:
        for item in mint_plan.items:
            if item.classification == "new":
                item.entity_id = idmint.mint_id(
                    project_path, item.type_code,
                    minter="runtime:mint-executor",
                    floor=floors[item.type_code])
                if reg.get(item.entity_id) is not None:
                    raise MintRefused(
                        "id_collision",
                        f"minted {item.entity_id} but it already exists — refusing "
                        f"to overwrite an entity")
        return
    # preview: provisional ids, monotone per type code, no ledger write
    led = idmint.load_ledger(project_path)
    next_by_code: dict = {}
    for item in mint_plan.items:
        if item.classification != "new":
            continue
        base = next_by_code.get(
            item.type_code,
            max(idmint.max_ordinal(led, item.type_code), floors[item.type_code]))
        ordinal = base + 1
        next_by_code[item.type_code] = ordinal
        item.entity_id = idmint.format_id(item.type_code, ordinal)


def _revalidate(project_path, staged: dict, schema_dir) -> "validator.ValidationReport":
    """Build a candidate registry = current facts with staged records replacing
    their originals (fact_version bumped), and run the FULL deterministic gate on
    it in memory. This is the validate-then-write guard: a mint that would break
    the registry (dangling/tombstone ref, causality cycle, schema) is caught here
    before anything touches disk."""
    reg = load_registry(project_path, schema_dir=schema_dir)
    for entity_id, (before_version, record) in staged.items():
        bumped = copy.deepcopy(record)
        bumped["fact_version"] = before_version + 1
        bumped["_source_path"] = reg.facts.get(entity_id, {}).get("_source_path", "")
        reg.facts[entity_id] = bumped
    return validator.validate(reg, schema_dir)


def _commit(project_path, reg: Registry, catalog: Catalog, staged: dict) -> dict:
    """Write the staged records to disk with bumped fact_version, bump the
    monotone registry version, and return {entity_id: (before, after)} versions.
    Called ONLY after revalidation passed."""
    project_path = Path(project_path)
    versions: dict = {}
    for entity_id, (before_version, record) in staged.items():
        after_version = before_version + 1
        out = dict(record)
        out.pop("_source_path", None)
        out["fact_version"] = after_version
        type_code = entity_id.split("-", 1)[0]
        facts_dir = catalog.facts_dir(type_code)
        path = project_path / "registry" / "facts" / facts_dir / f"{entity_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True),
                        encoding="utf-8")
        versions[entity_id] = (before_version, after_version)

    meta = project_path / "registry" / "_meta" / "registry-version"
    rv_before = int(meta.read_text(encoding="utf-8").strip())
    rv_after = rv_before + 1
    meta.write_text(f"{rv_after}\n", encoding="utf-8")
    return {"versions": versions, "rv_before": rv_before, "rv_after": rv_after}


def _next_receipt_id(project_path) -> str:
    ids = []
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == RECEIPT_CATEGORY and e.get("id", "").startswith("MINT-"):
            tail = e["id"].split("-", 1)[1]
            if tail.isdigit():
                ids.append(int(tail))
    return f"MINT-{(max(ids) + 1) if ids else 1:05d}"


def _build_receipt(*, receipt_id, mint_plan, commit_result, report, actor) -> dict:
    versions = commit_result["versions"]
    minted = []
    # per-item view (field/value) alongside the per-entity version bump
    for item in mint_plan.items:
        before, after = versions[item.entity_id]
        entry = {
            "candidate_id": item.candidate_id,
            "entity_id": item.entity_id,
            "classification": item.classification,
            "field": item.field,
            "value": item.value,
            "fact_version": {"before": before, "after": after},
        }
        if item.classification == "new":
            entry["type_code"] = item.type_code
        minted.append(entry)
    n_new = sum(1 for i in mint_plan.items if i.classification == "new")
    n_add = len(mint_plan.items) - n_new
    receipt = {
        "id": receipt_id,
        "kind": "mint_receipt",
        "version": RECEIPT_VERSION,
        "authority": "human",
        "gating": False,
        "authorized": {
            "confirmed": True,
            "accepted_candidates": [i.candidate_id for i in mint_plan.items],
        },
        "source_plan": {
            "plan_id": mint_plan.plan_id,
            "plan_content_hash": mint_plan.plan_content_hash,
            "chapter_draft_id": mint_plan.chapter_draft_id,
        },
        "registry_version": {
            "before": commit_result["rv_before"],
            "after": commit_result["rv_after"],
        },
        "minted": minted,
        "revalidation": {
            "passed": report.ok,
            "checks": sorted({f.check for f in report.findings}) or ["(no findings)"],
        },
        "rationale": (f"minted {n_new} new + {n_add} additive fact(s) from plan "
                      f"{mint_plan.plan_id}; registry v{commit_result['rv_before']}"
                      f"→v{commit_result['rv_after']}"),
    }
    if actor:
        receipt["authorized"]["actor"] = actor
    return receipt


def preview_mint(*, project_path, plan: dict, accepted: List[str], schema_dir):
    """Resolve + revalidate a mint WITHOUT writing anything. Returns
    (mint_plan, report). Refuses (raises MintRefused) exactly as execute would,
    so a preview truthfully shows whether the boundary crossing would succeed.

    A `new` item gets a PROVISIONAL id (max_ordinal+1, read-only) so the preview
    shows the id that would be minted without touching the ledger."""
    reg = load_registry(project_path, schema_dir=schema_dir)
    _check_not_stale(reg, plan)
    catalog = Catalog.load(schema_dir)
    mint_plan = plan_mint(plan, accepted, catalog=catalog, schema_dir=schema_dir)
    _assign_ids(project_path, reg, catalog, mint_plan, allocate=False)
    staged = _apply_in_memory(reg, mint_plan)
    report = _revalidate(project_path, staged, schema_dir)
    return mint_plan, report


def execute_mint(*, project_path, plan: dict, accepted: List[str], schema_dir,
                 confirmed: bool, actor: Optional[str] = None) -> dict:
    """Cross the ADR-009 boundary: write accepted additive/new candidates into facts.

    Requires `confirmed=True` (the distinct human authorization). Validate-then-
    write: applies in memory, runs the full gate, and commits ONLY if it passes —
    otherwise refuses and writes nothing. A `new` item allocates an id from the
    append-only ID Mint Ledger (idmint) before the gate; if the gate then fails,
    that ordinal stays reserved (ID spec §7 — reserved ordinals are never reused,
    like a tombstone), which is consistent, not corruption. Emits + returns a
    MintReceipt."""
    queue = ApprovalQueue(project_path=Path(project_path))
    approval_request = create_approval_request(
        request_id=f"APR-MINT-{plan.get('id', '00001')}",
        target_type="mint",
        target_id=plan.get("id", "FACT-PLAN-00001"),
        action="confirm_mint",
        reason="fact write requires human approval",
        requested_by={"module": "mint.executor", "plan_id": plan.get("id", "")},
        context={"plan_id": plan.get("id", ""), "chapter_draft_id": plan.get("source", {}).get("chapter_draft_id", "")},
    )
    queue.enqueue(approval_request)
    if not confirmed:
        raise MintRefused("not_confirmed",
                          "mint requires explicit human authorization (--confirm)")

    reg = load_registry(project_path, schema_dir=schema_dir)
    _check_not_stale(reg, plan)
    catalog = Catalog.load(schema_dir)
    mint_plan = plan_mint(plan, accepted, catalog=catalog, schema_dir=schema_dir)
    _assign_ids(project_path, reg, catalog, mint_plan, allocate=True)
    staged = _apply_in_memory(reg, mint_plan)

    report = _revalidate(project_path, staged, schema_dir)
    if not report.ok:
        raise MintRefused(
            "post_mint_gate_failed",
            "; ".join(str(f) for f in report.findings
                      if f.severity == validator.SEVERITY_ERROR)
            or "the post-mint registry did not pass the deterministic gate")

    commit_result = _commit(project_path, reg, catalog, staged)

    receipt_id = _next_receipt_id(project_path)
    record_approval_decision(
        queue,
        request_id=approval_request.id,
        decision=ApprovalDecision.APPROVED,
        decided_by=actor or "human",
        notes="mint confirmed",
    )
    receipt = _build_receipt(receipt_id=receipt_id, mint_plan=mint_plan,
                             commit_result=commit_result, report=report, actor=actor)
    derived.write_artifact(
        project_path=project_path,
        category=RECEIPT_CATEGORY,
        artifact_id=receipt_id,
        artifact=receipt,
        serialized=dump_pretty_json(receipt),
    )
    return receipt
