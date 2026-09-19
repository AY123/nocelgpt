# ADR-002: Unified Contract Layer

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

Agents, prompts, and pipelines all have inputs and outputs. If each defines its
own I/O ad hoc, the system drifts into incompatible conventions: one prompt
emits `character_name`, another emits `hero_name`, a pipeline expects `name`.
Nothing composes, and every integration becomes a translation chore.

Prompt Interface and Agent API are not two separate disciplines — they are two
*granularities* of the same thing: a contract.

## Decision

There is **one Contract Layer**. Every agent, prompt, and pipeline references
contracts from it rather than inventing I/O shapes. The layer has four contract
kinds:

| Contract | Answers | Granularity | Example |
|----------|---------|-------------|---------|
| **Capability Contract** | what an agent can do | coarse | `OutlineAgent: Goal → OutlineDraft` |
| **Invocation Contract** | how a specific call is shaped | fine | this prompt's input/output schema |
| **Artifact Contract** | what a produced artifact looks like | data | `ChapterDraft`, `OutlineDraft` shapes |
| **Validation Contract** | what "valid" means for an artifact | check | assertions an artifact must pass |

Every Capability/Invocation contract must additionally declare:

- **Determinism** — deterministic (schema/validation work) or generative (writing work).
- **Idempotency / Retry policy** — whether re-running is safe and whether the result is cacheable.

These two fields are what make retry, caching, and rollback engineerable rather
than guessed at.

## Consequences

- Artifact Contracts reference the single Schema (ADR-007); they never redefine
  field shapes.
- A pipeline is type-checkable: stage N's output Artifact Contract must satisfy
  stage N+1's input Invocation Contract.
- Determinism + retry metadata let the Execution Layer (ADR-005) decide what is
  safe to cache and replay.

## Relationships

- Depends on [ADR-007](ADR-007-schema-first.md) (Artifact shapes come from the Schema).
- Feeds [ADR-005](ADR-005-execution-layer-split.md) (retry/cache use Determinism + Idempotency).
- Validation Contracts are consumed by [ADR-003](ADR-003-qa-dual-axis.md).
