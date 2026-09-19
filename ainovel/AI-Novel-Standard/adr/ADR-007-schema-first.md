# ADR-007: Schema First

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

The Registry, prompts, Agent APIs, and Task Packages all describe the same
entities (a Character, an Event, an Item). If each defines its own version of
those structures, the system has N incompatible truths about what a Character
is. Every contract drifts, and integration becomes endless reconciliation.

## Decision

**There is one Schema.** Every Registry entry, prompt, Agent API, and Task
Package references that single Schema and its single ID specification. Defining
a duplicate data structure for an entity already in the Schema is forbidden.

### Single hand-written source (Refinement A)

Only **one** artifact in the schema toolchain is hand-maintained. If the IDL,
the "YAML authority schema", and the JSON Schema were three independently edited
files, they would themselves be duplicate definitions — violating this ADR.

The chain is therefore:

```
IDL (written in YAML — the one authoritative, human/AI-edited source)
  └─[generator]→ JSON Schema   (pure output, read-only, carries DO-NOT-EDIT header)
  └─[generator]→ future targets (SQLite DDL / Neo4j / Vector schema)
```

- The IDL *is* the YAML authority source. There is no separate hand-written YAML
  schema and no separate hand-written JSON Schema.
- JSON Schema is a **generated, read-only** artifact. It is never hand-edited.
- A real generator produces it; a hand-copied file pretending to be "generated"
  is a violation.

Using an IDL (not raw JSON Schema) as the authority keeps the data contract
portable: future migration to SQLite / Neo4j / Vector stores regenerates targets
instead of rewriting the source.

## Consequences

- One entity = one definition = one ID rule, referenced everywhere.
- Adding/changing a field happens in the IDL; all targets regenerate; the
  Standard's semver (ADR-004) reflects whether the change is breaking.
- Generated artifacts are reproducible and diffable; drift is mechanically
  detectable (regenerate and compare).

## Relationships

- Provides Artifact shapes to [ADR-002](ADR-002-contract-layer.md).
- Defines the structures the Registry stores under [ADR-006](ADR-006-registry-facts-only.md).
- Distributed under the version contract of [ADR-004](ADR-004-four-repo-architecture.md).
