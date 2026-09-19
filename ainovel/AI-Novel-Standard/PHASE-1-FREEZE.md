# Phase 1 Freeze Manifest — ANES v2

- **Standard version:** `2.0.0` (first frozen public contract)
- **Phase:** 1 — Foundation (data contract)
- **Frozen:** 2026-06-30
- **IDL format:** 1.0
- **JSON Schema dialect:** draft 2020-12

## What is frozen

This manifest pins the Phase 1 foundation. Downstream repos (Template, Runtime,
Project) pin Standard `2.0.0` per [ADR-004](adr/ADR-004-four-repo-architecture.md).
Breaking any item below is a MAJOR Standard bump.

### Frozen ADRs
- [ADR-001](adr/ADR-001-task-package-is-build-artifact.md) — Task Package is a build artifact
- [ADR-002](adr/ADR-002-contract-layer.md) — Unified Contract Layer
- [ADR-003](adr/ADR-003-qa-dual-axis.md) — QA dual-axis (only deterministic gates)
- [ADR-004](adr/ADR-004-four-repo-architecture.md) — Four-repo + version pin
- [ADR-005](adr/ADR-005-execution-layer-split.md) — Execution layer split
- [ADR-006](adr/ADR-006-registry-facts-only.md) — Registry is facts only (+ staleness)
- [ADR-007](adr/ADR-007-schema-first.md) — Schema first (single hand-written source)

### Frozen specs (Phase 1 deliverables, in dependency order)
1. [ID Naming Specification](phase-1/spec/01-id-naming-specification.md)
2. [Reference Grammar](phase-1/spec/02-reference-grammar.md)
3. [Core IDL](phase-1/spec/03-core-idl.md)
4. [Registry Directory Specification](phase-1/spec/04-registry-directory-specification.md)

### Frozen authoritative IDL source
- [`phase-1/idl/`](phase-1/idl/) — 6 core entities + shared `_types`:
  Character (CHR), Relationship (REL), Timeline (TML), Event (EVT),
  WorldRule (MAG/TEC), Item (ITM).

### Generated artifacts (read-only, reproducible)
- [`phase-1/generated/json-schema/`](phase-1/generated/json-schema/) — 6 schemas.
- Generator: [`tools/idl_to_jsonschema.py`](tools/idl_to_jsonschema.py).

## Reproducibility / drift gate

Regenerate and verify no drift (deterministic; ADR-007):

```sh
python3 tools/idl_to_jsonschema.py \
  --idl-dir phase-1/idl \
  --out-dir phase-1/generated/json-schema --check
```

Exit 0 = generated schemas match the IDL. Exit 1 = drift (someone hand-edited a
generated file or forgot to regenerate). This is a Phase-4 deterministic QA gate.

## Verified at freeze

- Generation: 6/6 schemas generated from IDL.
- Drift check: passes clean (exit 0); catches tampering (exit 1). Both directions
  tested.

## Out of scope for Phase 1 (deferred)

Per the agreed order, the following come later and are NOT frozen here: the
remaining entity types (LOC/FAC/ARC/PLT/THM/VOL/CHP/SCN/BEAT/FOR/INV/TASK/PKG/
AGT/CON), the Derived-wrapper schema, Execution Layer docs, Contract Layer docs,
QA test definitions, and the Template/Runtime repos.

## Next phase

**Phase 2 — Knowledge Base:** Registry validation rules (the deterministic
checks Phase 4 QA will invoke), the SSOT mechanics, and the remaining
worldbuilding entity IDLs, all building on this frozen contract.
