"""resolver.py — transitive reference closure (ANES v2).

Resource-resolution path (ADR-005). Given seed entity IDs, walk references to
build the closed set of entities needed to compile a Task Package (ADR-001).

The Resolver only EXPANDS and PINS; it does not reshape or prune (that is the
Normalizer's and Compiler's job). Output records are pinned to the Registry
version they were read at, so the resulting bundle is reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from . import refs
from .registry_loader import Registry

_RUNTIME_FIELDS = {"_source_path"}


@dataclass
class ResolvedEntity:
    id: str
    type_code: str
    fact_version: int
    record: dict
    depth: int  # distance from the nearest seed


@dataclass
class Resolution:
    seeds: List[str]
    registry_version: int
    entities: Dict[str, ResolvedEntity] = field(default_factory=dict)
    # pinned reference list, e.g. ["CHR-00001@v5", ...] — feeds provenance.
    pins: List[str] = field(default_factory=list)

    def ordered(self) -> List[ResolvedEntity]:
        # deterministic order: by depth, then id
        return sorted(self.entities.values(), key=lambda e: (e.depth, e.id))


def _refs_in(value):
    if refs.is_reference(value):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _refs_in(v)
    elif isinstance(value, list):
        for v in value:
            yield from _refs_in(v)


def resolve(reg: Registry, seeds: List[str], max_depth: int = 2) -> Resolution:
    """BFS closure from seeds up to max_depth hops.

    max_depth bounds the bundle so a Task Package stays token-bounded (ADR-001).
    Depth 0 = the seeds themselves; depth 1 = their direct references; etc.
    """
    res = Resolution(seeds=list(seeds), registry_version=reg.version)
    visited: Set[str] = set()
    frontier = [(s, 0) for s in seeds]

    while frontier:
        entity_id, depth = frontier.pop(0)
        if entity_id in visited:
            continue
        visited.add(entity_id)

        record = reg.get(entity_id)
        if record is None:
            # Dangling refs are a Validator concern; Resolver skips silently
            # (the gate already ran before resolve in the pipeline).
            continue

        fv = int(record.get("fact_version", 0))
        res.entities[entity_id] = ResolvedEntity(
            id=entity_id,
            type_code=entity_id.split("-", 1)[0],
            fact_version=fv,
            record={k: v for k, v in record.items() if k not in _RUNTIME_FIELDS},
            depth=depth,
        )

        if depth < max_depth:
            for raw in _refs_in(record):
                ref = refs.parse(raw)
                if ref.is_local and ref.id not in visited:
                    frontier.append((ref.id, depth + 1))

    # Build deterministic, pinned provenance list.
    res.pins = [f"{e.id}@v{e.fact_version}" for e in res.ordered()]
    return res
