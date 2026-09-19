"""normalize.py — shape-only normalization of extracted fact-candidate values.

Sits between extract() and reconcile() in the W12 reflow. The LLM extractor
emits a value in whatever shape the prose suggested (a bare string, a number, a
list); the frozen entity schemas require specific shapes (abilities is an array
of MAG/TEC entity-ref strings, physical_facts values are strings, ...). Without
this layer a large fraction of semantically-valid candidates are un-mintable
purely because of SHAPE — the memory records 87.7% valid vs ~10% mintable.

DISCIPLINE (hard — this layer is SHAPE ONLY, like runtime/normalizer.py):
  - NEVER invents a fact, splits prose into fields, or maps narrative onto an
    enum. Those are semantic inferences and belong to a human (ADR-009), or are
    left for reconcile to mark `unverifiable`/`conflicting`.
  - NEVER mints or writes anything (ADR-006). Entity-ref resolution is a
    read-only lookup against the live registry's name index; an unresolved name
    is left untouched, not invented.
  - Deterministic: same candidates + same registry ⇒ same output.
  - Total: any per-field failure leaves that candidate's value unchanged, so a
    normalization bug can never break the W12 reflow (ADR-003 never-gates).

Transforms applied (all pure shape):
  1. scalar → [scalar]        when the field is an array of PLAIN strings
                              (e.g. aliases) — wrapping a lone value is shape.
  2. name → [entity-id]       when the field is an array of ENTITY-REF strings
                              (items carry a `pattern`, e.g. abilities) AND the
                              scalar resolves to a live entity by name. Unresolved
                              names are left as-is (reconcile → unverifiable).
  3. non-string scalar → str  when the field (or an object's values) is typed
                              string (e.g. physical_facts.*).
Anything else is left unchanged.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from .reconcile import RawCandidate, _build_name_index, _norm_name

# spec kinds returned by _field_shapes
ARRAY_PLAIN = "array_plain"     # array of plain strings (no item pattern)
ARRAY_REF = "array_ref"         # array of entity-ref strings (items have pattern)
STRING = "string"               # a string-typed scalar field
OBJECT_STR_VALUES = "obj_str"   # object whose additionalProperties are strings
OTHER = "other"


def _field_shapes(schema_dir, catalog) -> Dict[str, Dict[str, str]]:
    """Read each entity schema's property shapes into {entity_name: {field: kind}}.

    I/O helper kept OUT of the pure normalize fold — the caller builds it once
    and passes it in, mirroring reconcile.build_field_constraints. Only the
    top-level property shape is recorded; dotted leaf fields (physical_facts.
    eye_color) are resolved against their parent object at normalize time.
    """
    from ..catalog import Catalog
    cat = catalog if isinstance(catalog, Catalog) else Catalog.load(schema_dir)
    out: Dict[str, Dict[str, str]] = {}
    for type_code in cat.type_codes():
        entity = cat.entity_name(type_code)
        if entity in out:
            continue
        schema_path = Path(schema_dir) / cat.schema_file(type_code)
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        fields: Dict[str, str] = {}
        for fname, fspec in (schema.get("properties") or {}).items():
            fields[fname] = _classify_shape(fspec)
        if fields:
            out[entity] = fields
    return out


def _classify_shape(fspec: Any) -> str:
    if not isinstance(fspec, dict):
        return OTHER
    ftype = fspec.get("type")
    if ftype == "array":
        items = fspec.get("items")
        if isinstance(items, dict) and items.get("type") == "string":
            return ARRAY_REF if items.get("pattern") else ARRAY_PLAIN
        return OTHER
    if ftype == "string":
        return STRING
    if ftype == "object":
        addl = fspec.get("additionalProperties")
        if isinstance(addl, dict) and addl.get("type") == "string":
            return OBJECT_STR_VALUES
        return OTHER
    return OTHER


def _top_field(field: str) -> str:
    """The top-level property a (possibly dotted) field path targets:
    'physical_facts.eye_color' → 'physical_facts', 'abilities' → 'abilities'."""
    return field.split(".", 1)[0] if field else field


def _normalize_value(value: Any, kind: str, field: str,
                     name_index: Dict[str, str]) -> Any:
    """Return the shape-normalized value, or the original value if no total,
    non-inventive transform applies. Never raises for a normalizable input."""
    dotted = "." in (field or "")

    if kind == OBJECT_STR_VALUES:
        # a whole-object assignment is left alone (splitting prose into keys is
        # semantic); a dotted leaf (physical_facts.eye_color) is a string slot.
        if dotted and not isinstance(value, (dict, list)) and value is not None:
            return value if isinstance(value, str) else _scalar_to_str(value)
        return value

    if kind == STRING:
        if isinstance(value, str) or value is None:
            return value
        if isinstance(value, (dict, list)):
            return value  # structured → string is not shape, leave for reconcile
        return _scalar_to_str(value)

    if kind == ARRAY_PLAIN:
        if isinstance(value, list) or value is None:
            return value
        scalar = value if isinstance(value, str) else _scalar_to_str(value)
        return [scalar]

    if kind == ARRAY_REF:
        # entity-ref array: wrap a lone value into a list and resolve names to
        # live entity ids (read-only). Unresolved names are left verbatim so
        # reconcile surfaces them honestly rather than inventing a ref.
        if value is None:
            return value
        items = value if isinstance(value, list) else [value]
        resolved: List[Any] = []
        for it in items:
            resolved.append(_resolve_ref(it, name_index))
        return resolved

    return value


def _scalar_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _resolve_ref(item: Any, name_index: Dict[str, str]) -> Any:
    """Resolve one entity-ref array item. If it is already an id-shaped token or
    is not a plain string, leave it. If it is a name that resolves to a live
    entity, return that id; otherwise return the original (never invent)."""
    if not isinstance(item, str):
        return item
    resolved = name_index.get(_norm_name(item))
    return resolved if resolved else item


def normalize_candidates(candidates: List[RawCandidate], *, reg=None,
                         schema_dir=None, catalog=None) -> List[RawCandidate]:
    """Shape-normalize each candidate's value against the frozen entity schemas.

    Pure fold over candidates. `reg` (a live Registry) enables name→entity-id
    resolution for entity-ref array fields; without it, only shape wrapping is
    applied. `schema_dir`/`catalog` locate the schemas that drive the shape
    rules; if neither is available the candidates are returned unchanged.

    Total by construction: a per-candidate failure leaves that candidate as-is,
    so this layer can never break the W12 reflow (ADR-003).
    """
    if not candidates:
        return list(candidates)
    try:
        shapes = _field_shapes(schema_dir, catalog) if (schema_dir or catalog) else {}
    except Exception:
        shapes = {}
    if not shapes:
        return list(candidates)
    name_index = _build_name_index(reg) if reg is not None else {}

    out: List[RawCandidate] = []
    for cand in candidates:
        try:
            kind = (shapes.get(cand.target_type) or {}).get(_top_field(cand.field), OTHER)
            new_value = _normalize_value(cand.value, kind, cand.field, name_index)
            if new_value is not cand.value and new_value != cand.value:
                cand = replace(cand, value=new_value)
        except Exception:
            pass  # never let a normalization bug drop or corrupt a candidate
        out.append(cand)
    return out
