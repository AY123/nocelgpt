"""validator.py — deterministic QA gate aggregator (ANES v2, ADR-003).

A check REGISTRY, not a monolith. Each check self-registers with a name and a QA
axis; `validate()` iterates the registry. Adding a check (mint, derived
staleness, cross-project) is a decorated function — the aggregator never changes.

Axes (ADR-003):
  - deterministic (AXIS_GATE)  : pass/fail, may BLOCK a build
  - evaluative   (AXIS_TREND)  : reported only, downgraded to warnings, never gates

Checks currently registered (all deterministic):
  schema · dangling · tombstone · causality · temporal · pin
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from jsonschema import Draft202012Validator

from . import refs
from .catalog import Catalog
from .registry_loader import Registry

SEVERITY_ERROR = "error"
SEVERITY_WARN = "warning"

# Fields injected by the runtime that are not part of the schema.
_RUNTIME_FIELDS = {"_source_path"}


@dataclass
class Finding:
    check: str
    severity: str
    entity: str
    message: str

    def __str__(self):
        return f"[{self.severity}] {self.check} @ {self.entity}: {self.message}"


@dataclass
class ValidationReport:
    findings: List[Finding]

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == SEVERITY_ERROR]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        e = len(self.errors)
        w = len(self.findings) - e
        return f"{'PASS' if self.ok else 'FAIL'} ({e} error(s), {w} warning(s))"


class SchemaSet:
    """Loads the Standard's generated JSON Schemas, one per entity.

    Uses the generated catalog to map type_code -> schema file, so there is no
    hardcoded type->entity table in the Runtime (single source of truth, ADR-007).
    """

    def __init__(self, schema_dir: str | Path, catalog: Catalog | None = None):
        self.schema_dir = Path(schema_dir)
        self.catalog = catalog or Catalog.load(schema_dir)
        self._validators = {}

    def validator_for(self, type_code: str) -> Draft202012Validator:
        schema_file = self.catalog.schema_file(type_code)  # raises if unknown
        if schema_file not in self._validators:
            path = self.schema_dir / schema_file
            schema = json.loads(path.read_text(encoding="utf-8"))
            self._validators[schema_file] = Draft202012Validator(schema)
        return self._validators[schema_file]


def _strip_runtime_fields(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in _RUNTIME_FIELDS}


def _iter_refs(value):
    """Yield every reference string anywhere in a record value (recursive)."""
    if refs.is_reference(value):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from _iter_refs(v)


def _outbound_refs(record: dict):
    """Refs a record points AT — excludes its own `id` (identity, not a ref)."""
    for key, value in record.items():
        if key == "id":
            continue
        yield from _iter_refs(value)


def _check_schema(reg: Registry, schemas: SchemaSet) -> List[Finding]:
    out = []
    for rid, record in reg.facts.items():
        tc = rid.split("-", 1)[0]
        try:
            validator = schemas.validator_for(tc)
        except ValueError as e:
            out.append(Finding("schema", SEVERITY_ERROR, rid, str(e)))
            continue
        payload = _strip_runtime_fields(record)
        for err in sorted(validator.iter_errors(payload), key=lambda e: e.path):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            out.append(Finding("schema", SEVERITY_ERROR, rid,
                               f"{loc}: {err.message}"))
    return out


def _check_dangling(reg: Registry) -> List[Finding]:
    out = []
    for rid, record in reg.facts.items():
        for raw in _outbound_refs(_strip_runtime_fields(record)):
            ref = refs.parse(raw)
            if not ref.is_local:
                continue  # cross-project refs resolved elsewhere
            if not reg.exists(ref.id):
                out.append(Finding("dangling", SEVERITY_ERROR, rid,
                                   f"reference to missing entity {ref.id}"))
    return out


def _check_tombstone(reg: Registry) -> List[Finding]:
    out = []
    for rid, record in reg.facts.items():
        for raw in _outbound_refs(_strip_runtime_fields(record)):
            ref = refs.parse(raw)
            if not ref.is_local:
                continue
            target = reg.get(ref.id)
            if target and target.get("status") in ("deprecated", "tombstoned"):
                out.append(Finding("tombstone", SEVERITY_ERROR, rid,
                                   f"reference to {target['status']} entity "
                                   f"{ref.id}"))
    return out


def _check_causality_dag(reg: Registry) -> List[Finding]:
    """Event.causes/effects must form a DAG (no cycles)."""
    # Build directed edges cause -> event (and event -> effect).
    adj = {}
    for rid, record in reg.facts.items():
        if not rid.startswith("EVT-"):
            continue
        adj.setdefault(rid, set())
        for raw in record.get("causes", []) or []:
            cid = refs.parse(raw).id
            adj.setdefault(cid, set()).add(rid)      # cause -> this
        for raw in record.get("effects", []) or []:
            eid = refs.parse(raw).id
            adj.setdefault(rid, set()).add(eid)       # this -> effect

    # DFS cycle detection.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}
    out: List[Finding] = []

    def dfs(node, stack):
        color[node] = GRAY
        for nxt in sorted(adj.get(node, ())):
            if color.get(nxt, WHITE) == GRAY:
                cycle = " -> ".join(stack + [nxt])
                out.append(Finding("causality", SEVERITY_ERROR, node,
                                   f"causal cycle: {cycle}"))
                return
            if color.get(nxt, WHITE) == WHITE:
                dfs(nxt, stack + [nxt])
        color[node] = BLACK

    for node in sorted(adj):
        if color[node] == WHITE:
            dfs(node, [node])
    return out


def _check_temporal_causal(reg: Registry) -> List[Finding]:
    """A cause must occur BEFORE its effect. If EVT-A lists EVT-B in `causes`
    (B caused A), then B must be earlier on the timeline than A — i.e.
    B.sequence_index < A.sequence_index. A cause landing at or after its effect
    is a timeline break (the classic long-novel continuity bug: a payoff whose
    setup happens later). Deterministic and gating.

    Only judged when BOTH events carry a sequence_index and share a timeline;
    a missing index is not an error here (that is a separate completeness
    concern), so sparsely-indexed fixtures are never falsely flagged.
    """
    out: List[Finding] = []
    for rid, record in reg.facts.items():
        if not rid.startswith("EVT-"):
            continue
        a_idx = record.get("sequence_index")
        a_tl = record.get("timeline")
        if a_idx is None:
            continue
        for raw in record.get("causes", []) or []:
            cid = refs.parse(raw).id
            cause = reg.get(cid)
            if not cause or not cid.startswith("EVT-"):
                continue
            c_idx = cause.get("sequence_index")
            if c_idx is None:
                continue
            # Only compare within the same timeline (cross-timeline ordering is
            # not defined by a single integer index).
            if a_tl is not None and cause.get("timeline") not in (None, a_tl):
                continue
            if c_idx >= a_idx:
                out.append(Finding(
                    "temporal", SEVERITY_ERROR, rid,
                    f"cause {cid} (sequence_index={c_idx}) does not precede its "
                    f"effect {rid} (sequence_index={a_idx}): timeline break"))
    return out


def _check_pin(reg: Registry, standard_version: str) -> List[Finding]:
    """MAJOR must match between Project pin and Standard (ADR-004 semver)."""
    pin_major = reg.standard_pin.split(".", 1)[0]
    std_major = standard_version.split(".", 1)[0]
    if pin_major != std_major:
        return [Finding("pin", SEVERITY_ERROR, "_meta",
                        f"Project pins Standard {reg.standard_pin} but runtime "
                        f"targets {standard_version} (MAJOR mismatch)")]
    return []


# --- Check registry (ADR-003) -------------------------------------------------
# Each deterministic check self-registers here with its name and QA axis. Adding
# a new check (mint, derived-staleness, cross-project) means writing a function
# and decorating it — the validate() aggregator never changes. Only AXIS_GATE
# checks can block a build; AXIS_TREND results are reported but never gate
# (the place evaluative/LLM-judge checks attach in future, ADR-003).
AXIS_GATE = "deterministic"      # may block the build
AXIS_TREND = "evaluative"        # reported only, never blocks


@dataclass
class Check:
    name: str
    axis: str
    fn: "callable"


_REGISTRY: "list[Check]" = []


def register(name: str, axis: str = AXIS_GATE):
    def deco(fn):
        _REGISTRY.append(Check(name=name, axis=axis, fn=fn))
        return fn
    return deco


# Adapt the existing _check_* functions into the registry. They keep their
# original signatures; the registry passes a context object and each picks what
# it needs. This is behavior-preserving: same checks, same order, same findings.
@register("pin")
def _r_pin(ctx) -> List[Finding]:
    return _check_pin(ctx["reg"], ctx["standard_version"])


@register("schema")
def _r_schema(ctx) -> List[Finding]:
    return _check_schema(ctx["reg"], ctx["schemas"])


@register("dangling")
def _r_dangling(ctx) -> List[Finding]:
    return _check_dangling(ctx["reg"])


@register("tombstone")
def _r_tombstone(ctx) -> List[Finding]:
    return _check_tombstone(ctx["reg"])


@register("causality")
def _r_causality(ctx) -> List[Finding]:
    return _check_causality_dag(ctx["reg"])


@register("temporal")
def _r_temporal(ctx) -> List[Finding]:
    return _check_temporal_causal(ctx["reg"])


def registered_checks() -> "list[tuple[str, str]]":
    """(name, axis) for every registered check — for introspection/tests."""
    return [(c.name, c.axis) for c in _REGISTRY]


def validate(reg: Registry, schema_dir: str | Path,
             standard_version: str = "2.0.0") -> ValidationReport:
    """Run every registered check. Gate axis findings can fail the build;
    trend axis findings are collected but downgraded to warnings so they never
    block (ADR-003). The set of checks is the registry, not a hand list."""
    ctx = {
        "reg": reg,
        "schemas": SchemaSet(schema_dir),
        "standard_version": standard_version,
    }
    findings: List[Finding] = []
    for check in _REGISTRY:
        results = check.fn(ctx)
        if check.axis == AXIS_TREND:
            # evaluative results are never gating; force non-error severity
            results = [Finding(f.check, SEVERITY_WARN, f.entity, f.message)
                       for f in results]
        findings += results
    return ValidationReport(findings=findings)
