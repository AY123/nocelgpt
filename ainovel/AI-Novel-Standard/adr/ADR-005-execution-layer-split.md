# ADR-005: Execution Layer Split

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

The naive call stack `Task → Workflow → Agent → Registry → Prompt → Model`
mixes two different concerns. "Do step A then step B, retry on failure, run
these in parallel" is orchestration. "Fetch this fact, load this template,
choose this model" is resource acquisition. If they are treated as one path,
then "retry a failed task" and "re-resolve a stale piece of context" get the
same handling — and their correct policies are completely different.

## Decision

The Execution Layer (L5.5) splits into **two independent paths**:

### Control flow (orchestration)

```
Task → Workflow → Agent
```

Concerns: sequencing, parallelism, retry, rollback, gating. Operates on units of
work. A retry here re-runs a step.

### Resource resolution (acquisition)

```
Agent → { Registry, Prompt, Model, Tool, Memory }
```

Concerns: resolving references, loading templates, selecting models, reading
memory. A "retry" here re-resolves data; it may invalidate a cache and recompute
a Derived artifact, which is a different operation from re-running a Task.

These two paths are documented, versioned, and reasoned about separately.

## Consequences

- Retry, cache, and rollback policies are defined per path and do not bleed into
  each other.
- Task Package compilation (ADR-001) lives on the **resource resolution** path
  (Resolver → Normalizer → Compiler); workflow retry lives on the **control
  flow** path.
- Determinism/Idempotency metadata from contracts (ADR-002) is consumed on the
  control-flow path to decide replay safety, and on the resolution path to
  decide cache validity.

## Relationships

- Carries out compilation defined in [ADR-001](ADR-001-task-package-is-build-artifact.md).
- Consumes retry/cache metadata from [ADR-002](ADR-002-contract-layer.md).
- Resolution path honors the staleness rules of [ADR-006](ADR-006-registry-facts-only.md).
