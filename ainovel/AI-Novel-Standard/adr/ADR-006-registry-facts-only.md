# ADR-006: Registry Is Declarative Facts Only

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

If the Registry is allowed to hold inferences, it rots. Example: the Registry
states `Hero.age = 18`. A model infers "Hero is an adult" and writes it back.
Later another model reads that and infers "Hero may drink alcohol" and writes
*that* back. Inferences pile on inferences; the SSOT fills with unverifiable
derived claims and nobody can tell a fact from a guess.

## Decision

The Registry stores **facts only** — declarative, asserted ground truth. It
**must not** store inferences, summaries, evaluations, psychological analyses,
or style analyses. All such products are **Derived Artifacts** and live in a
separate space; they are never written back into the SSOT.

```
Registry/
  Facts/        # SSOT — declarative facts only
  Derived/      # inferences, analyses — generated, never authoritative
  Summary/      # rolling summaries — generated
  Snapshot/     # point-in-time captures — generated
```

### Staleness rule (Refinement B) — necessary companion to "no write-back"

Forbidding write-back is necessary but not sufficient: you can still *read a
stale Derived artifact and treat it as current*. Therefore every Derived
artifact must carry provenance:

```yaml
derived_from: [<fact references it was computed from>]
source_version: <Registry version those facts were at>
```

When any source fact's version changes, the Derived artifact is automatically
**stale** and must be recomputed before trust. A consumer that finds a stale
Derived artifact treats it as absent, not as truth.

## Consequences

- `Facts/` stays clean and auditable indefinitely; its size grows only with real
  facts, not with accumulated speculation.
- Any analysis/summary is reproducible from Facts + the generator that made it.
- Task Package compilation (ADR-001) reads Facts as authoritative and may attach
  Derived context only when it is non-stale.
- The version contract (ADR-004) provides the version identifiers staleness
  compares against.

## Relationships

- Source of truth consumed by [ADR-001](ADR-001-task-package-is-build-artifact.md).
- Staleness uses versions from [ADR-004](ADR-004-four-repo-architecture.md).
- Invariants asserted against Facts are tested under [ADR-003](ADR-003-qa-dual-axis.md).
