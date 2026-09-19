"""normalizer.py — canonicalize resolved entities (ANES v2).

Resource-resolution path (ADR-005), stage after Resolver, before Compiler.

The Normalizer produces ONE canonical shape downstream consumers can rely on,
independent of how a record happened to be authored:
  - drops null / empty-collection fields (they carry no fact)
  - sorts reference lists deterministically
  - groups each entity under its type
  - leaves prose/notes untouched (human content, not a resolution source)

It never invents or infers data (ADR-006) — normalization is shape only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import refs
from .resolver import Resolution


@dataclass
class NormalizedBundle:
    registry_version: int
    seeds: List[str]
    pins: List[str]
    by_type: Dict[str, List[dict]] = field(default_factory=dict)

    def entity_count(self) -> int:
        return sum(len(v) for v in self.by_type.values())


def _is_empty(value) -> bool:
    return value is None or value == [] or value == {} or value == ""


def _clean(record: dict) -> dict:
    """Drop empty fields; sort lists of references for determinism."""
    out = {}
    for key, value in record.items():
        if _is_empty(value):
            continue
        if isinstance(value, list) and value and all(
                refs.is_reference(v) for v in value):
            value = sorted(value)
        out[key] = value
    return out


def normalize(resolution: Resolution,
              emit_order: Optional[Dict[str, int]] = None) -> NormalizedBundle:
    """Canonicalize a resolution into a stable bundle.

    `emit_order` (type_code -> rank) comes from the Standard catalog and decides
    the order entity types appear in. If omitted, types are ordered
    alphabetically. There is no hardcoded type order in the Runtime any more
    (single source of truth lives in the Standard's IDL).
    """
    emit_order = emit_order or {}
    bundle = NormalizedBundle(
        registry_version=resolution.registry_version,
        seeds=list(resolution.seeds),
        pins=list(resolution.pins),
    )
    for ent in resolution.ordered():
        cleaned = _clean(ent.record)
        bundle.by_type.setdefault(ent.type_code, []).append(cleaned)

    # Stable ordering: by declared rank from the catalog, then type code as a
    # deterministic tiebreaker for any type the catalog didn't rank.
    ranked = sorted(bundle.by_type, key=lambda tc: (emit_order.get(tc, 999), tc))
    bundle.by_type = {
        tc: sorted(bundle.by_type[tc], key=lambda r: r["id"]) for tc in ranked
    }
    return bundle
