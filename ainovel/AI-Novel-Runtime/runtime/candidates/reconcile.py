"""reconcile.py — DETERMINISTIC reconciliation of prose candidates vs facts.

This is the anti-rot core of the Fact Candidate Pipeline. Extraction (a model
reading prose) is evaluative and never gates; reconciliation is a PURE,
DETERMINISTIC classification of each candidate against the declared Registry:

    new          no entity of this type/name exists              -> mint creates it
    additive     entity exists, the asserted field is EMPTY      -> mint extends it
    consistent   entity exists, asserted value EQUALS the fact    -> confirmation only
    conflicting  entity exists, asserted value CONTRADICTS fact   -> HUMAN decides
    unverifiable  cannot be deterministically compared            -> HUMAN decides

DISCIPLINE:
  - PURE + DETERMINISTIC (no model, no I/O, no randomness): same candidates +
    same Registry => same classifications. This is what makes the plan
    reproducible and lets a fitness/regression test pin every branch.
  - NEVER auto-resolves a `conflicting` item. A contradiction between prose and
    a declared fact is surfaced, never overwritten — auto-overwriting the SSOT
    from inference is exactly the rot ADR-006 forbids. The pipeline's job is to
    hand the human a clean prose-vs-fact diff, not to guess.
  - Writes nothing. Classification is a fold; staging is plan.py's job.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..registry_loader import Registry


def build_field_constraints(schema_dir, catalog) -> Dict[str, Dict[str, list]]:
    """Read each entity schema's ENUM-constrained fields into
    {target_type: {field: [allowed values]}}. I/O helper (kept OUT of the pure
    fold — the caller builds this once and passes it into reconcile).

    Why this exists: a real DeepSeek run mapped narrative situation (受伤/被追捕)
    onto Character.status, whose schema enum is a LIFECYCLE (active/deprecated/
    tombstoned). Without this, such an assertion looks like a retcon `conflicting`
    and pollutes the human review queue with false alarms. With it, an
    out-of-enum value on a constrained field is reclassified `unverifiable` — the
    honest label: 'the prose asserts something this field cannot hold'."""
    from ..catalog import Catalog
    cat = catalog if isinstance(catalog, Catalog) else Catalog.load(schema_dir)
    out: Dict[str, Dict[str, list]] = {}
    for type_code in cat.type_codes():
        entity = cat.entity_name(type_code)
        if entity in out:
            continue
        schema_path = Path(schema_dir) / cat.schema_file(type_code)
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        fields: Dict[str, list] = {}
        for fname, fspec in (schema.get("properties") or {}).items():
            if isinstance(fspec, dict) and isinstance(fspec.get("enum"), list):
                fields[fname] = list(fspec["enum"])
        if fields:
            out[entity] = fields
    return out


# --- input shape (produced by extract.py) -----------------------------------

@dataclass(frozen=True)
class RawCandidate:
    """One fact asserted by prose, before reconciliation.

    `matched_entity_id` is the entity the extractor believes this is about (by
    id or name resolution); None means the extractor found no referent. The
    reconciler re-checks it against the live Registry — it never trusts the
    extractor's match blindly, because the extractor is evaluative."""
    target_type: str
    field: str
    value: Any
    evidence: str
    matched_entity_id: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


# --- output shape ------------------------------------------------------------

CLASSIFICATIONS = ("new", "additive", "consistent", "conflicting", "unverifiable")


@dataclass(frozen=True)
class ReconciledItem:
    candidate_id: str
    classification: str
    target_type: str
    field: str
    extracted_value: Any
    evidence: str
    matched_entity_id: Optional[str] = None
    existing_value: Any = None
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "candidate_id": self.candidate_id,
            "classification": self.classification,
            "target_type": self.target_type,
            "field": self.field,
            "extracted_value": self.extracted_value,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "reason": self.reason,
        }
        if self.matched_entity_id is not None:
            d["matched_entity_id"] = self.matched_entity_id
        if self.existing_value is not None:
            d["existing_value"] = self.existing_value
        return d


@dataclass
class Reconciliation:
    items: List[ReconciledItem] = field(default_factory=list)
    reconciled_against: List[str] = field(default_factory=list)  # ID@vN pins

    def counts(self) -> dict:
        return {c: sum(1 for i in self.items if i.classification == c)
                for c in CLASSIFICATIONS}


# --- field access ------------------------------------------------------------

def _dotted_get(record: dict, dotted: str):
    """Read a possibly-dotted field path (physical_facts.eye_color) from a fact
    record. Returns (found, value). `found` distinguishes an absent field from a
    field explicitly set to a falsy value — the additive/conflicting split hinges
    on it."""
    cur: Any = record
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _is_empty(value: Any) -> bool:
    """Whether a declared field counts as 'not yet asserted' (=> additive)."""
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple)) and len(value) == 0:
        return True
    return False


def _values_equal(a: Any, b: Any) -> bool:
    """Deterministic equality for consistent-vs-conflicting. Strings compared
    case-insensitively and whitespace-trimmed (prose casing is not a fact
    change); everything else by structural equality."""
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    return a == b


def _in_enum(value: Any, enum_vals: list) -> bool:
    """Whether an asserted value is one of a constrained field's allowed enum
    values, using the same case-insensitive string comparison as _values_equal
    (so a valid value differing only in casing is still in-enum)."""
    return any(_values_equal(value, ev) for ev in enum_vals)


# --- the fold ----------------------------------------------------------------

def _pin(record: dict, entity_id: str) -> str:
    return f"{entity_id}@v{int(record.get('fact_version', 0))}"


def _norm_name(s: Any) -> str:
    """Normalize a name for matching: trimmed, lowercased, inner spaces removed
    (so 'Edric Vance' and 'edric  vance' match). Deterministic."""
    if not isinstance(s, str):
        return ""
    return "".join(s.split()).strip().lower()


def _build_name_index(reg: Registry) -> dict:
    """Map every entity's name + aliases (normalized) → its id, for resolving a
    candidate the extractor named but did not id. Deterministic; on a name
    collision the LOWEST id wins (stable), so the fold stays reproducible."""
    index: dict[str, str] = {}
    for eid in sorted(reg.all_ids()):
        rec = reg.get(eid) or {}
        names = [rec.get("name")] + list(rec.get("aliases") or [])
        for nm in names:
            key = _norm_name(nm)
            if key and key not in index:
                index[key] = eid
    return index


def _resolve_subject(reg: Registry, name_index: dict, cand: RawCandidate):
    """Resolve the entity a candidate is about, returning (matched_id, entity) or
    (None, None). Three deterministic tiers, id-first (the extractor's explicit
    intent wins; name resolution is the safety net for when it didn't/couldn't):
      1. an explicit, live matched_entity_id  → trust it;
      2. a matched_entity_id that is actually a NAME (some models put the name in
         the id slot) → resolve via the name index;
      3. no usable id, but the extracted value of a `name` field matches a known
         entity → resolve (catches '正文写了埃德里克·万斯' with a blank id)."""
    mid = cand.matched_entity_id
    if mid and reg.exists(mid):
        return mid, reg.get(mid)
    if mid:
        by_name = name_index.get(_norm_name(mid))
        if by_name:
            return by_name, reg.get(by_name)
    if cand.field == "name":
        by_val = name_index.get(_norm_name(cand.value))
        if by_val:
            return by_val, reg.get(by_val)
    return None, None


def reconcile(reg: Registry, candidates: List[RawCandidate], *,
              field_constraints: Optional[Dict[str, Dict[str, list]]] = None) -> Reconciliation:
    """Classify each raw candidate against the current Registry. Pure fold.

    Subject resolution is id-first with a NAME-RESOLUTION safety net (_resolve_
    subject): the extractor may name an entity it couldn't id (cross-language name,
    blank id slot), and the reconciler resolves it against the registry's name +
    alias index rather than misfiling it as `new` — closing the phantom-duplicate
    hole a real model exposed. Still deterministic: same candidates + same
    registry ⇒ same classification.

    `field_constraints` ({target_type: {field: [enum values]}}, from
    build_field_constraints) is optional; when supplied, an assertion whose value
    is OUTSIDE a constrained field's enum is classified `unverifiable` (with a
    clear reason) instead of `conflicting`. This is the second real-model fix: a
    model that writes narrative situation (受伤) into a lifecycle enum (status)
    should not pollute the review queue with a false retcon. Absent constraints,
    behavior is unchanged (backward-compatible)."""
    out = Reconciliation()
    pins: dict[str, str] = {}  # entity_id -> ID@vN, deduped, stable order
    name_index = _build_name_index(reg)
    field_constraints = field_constraints or {}

    for idx, cand in enumerate(candidates, start=1):
        cid = f"CAND-{idx:05d}"
        matched_id, entity = _resolve_subject(reg, name_index, cand)

        if entity is None:
            # No live referent. If the extractor named an entity that does not
            # exist, that's still a `new` proposal for that entity; otherwise a
            # brand-new fact. Either way there is nothing to contradict.
            out.items.append(ReconciledItem(
                candidate_id=cid,
                classification="new",
                target_type=cand.target_type,
                field=cand.field,
                extracted_value=cand.value,
                evidence=cand.evidence,
                confidence=cand.confidence,
                reason=cand.reason or "no matching entity in registry",
            ))
            continue

        pins[matched_id] = _pin(entity, matched_id)
        found, existing = _dotted_get(entity, cand.field)

        enum_vals = field_constraints.get(cand.target_type, {}).get(cand.field)
        out_of_enum = (enum_vals is not None
                       and not _in_enum(cand.value, enum_vals))

        if not found or _is_empty(existing):
            if out_of_enum:
                # the field is empty, but the asserted value can never be written
                # to a constrained field — not an additive fill, an unverifiable
                # mismatch (e.g. status="受伤" into a lifecycle enum).
                classification = "unverifiable"
                reason = (f"{cand.field} only accepts {enum_vals}; prose asserts "
                          f"{cand.value!r}, which is not a valid value for this field")
            else:
                classification = "additive"
                reason = cand.reason or f"{matched_id}.{cand.field} is currently empty"
        elif out_of_enum:
            # a value outside the field's enum is NOT a retcon `conflicting` — the
            # field structurally cannot hold it. Surface it as unverifiable so the
            # review queue is not polluted with false conflicts (a model mapping
            # narrative situation onto a lifecycle enum is the real-model case).
            classification = "unverifiable"
            reason = (f"{cand.field} only accepts {enum_vals}; prose asserts "
                      f"{cand.value!r} (declared {existing!r}) — not a value this "
                      f"field can hold, so not a resolvable conflict")
        elif _unverifiable(cand.value, existing):
            classification = "unverifiable"
            reason = cand.reason or "values not deterministically comparable"
        elif _values_equal(cand.value, existing):
            classification = "consistent"
            reason = cand.reason or "prose agrees with declared fact"
        else:
            classification = "conflicting"
            reason = (cand.reason
                      or f"prose asserts {cand.value!r}, fact declares {existing!r}")

        out.items.append(ReconciledItem(
            candidate_id=cid,
            classification=classification,
            target_type=cand.target_type,
            field=cand.field,
            extracted_value=cand.value,
            existing_value=existing if found else None,
            evidence=cand.evidence,
            matched_entity_id=matched_id,
            confidence=cand.confidence,
            reason=reason,
        ))

    out.reconciled_against = [pins[k] for k in sorted(pins)]
    return out


def _unverifiable(extracted: Any, existing: Any) -> bool:
    """A comparison is unverifiable when the two sides are not of comparable
    shape — e.g. prose free-text vs a structured list — so neither 'equal' nor
    'contradicts' can be asserted deterministically. Kept narrow on purpose:
    same-typed scalars and lists ARE comparable (consistent/conflicting)."""
    if type(extracted) is type(existing):
        return False
    # str-vs-str handled above; a str asserted against a structured value cannot
    # be deterministically judged equal or contradictory.
    if isinstance(existing, (dict, list)) and not isinstance(extracted, (dict, list)):
        return True
    if isinstance(extracted, (dict, list)) and not isinstance(existing, (dict, list)):
        return True
    return False
