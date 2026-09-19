# ADR-008: Story State Is a Projection, Not Mutable State

- **Status:** Accepted (Frozen, ANES v2 Phase 14)
- **Date:** 2026-07-02
- **Supersedes:** —
- **Superseded by:** —

## Context

A long serial needs cross-chapter continuity state: which foreshadowing is still
open, where each character currently stands, what a faction holds, how far the
timeline has advanced. The obvious design is a `StoryState` object that each
chapter **mutates** in place — chapter 71 resolves foreshadow #18 by flipping a
flag, updates a character's location, decrements a faction's strength.

That design is how most AI-writing systems rot past ~50 chapters. In-place
mutation destroys two things this project treats as load-bearing:

1. **Reproducibility.** The whole Runtime is byte-reproducible: same input ⇒ same
   `content_hash` (ADR-001, ADR-005). A mutable state object read and written by
   non-deterministic model calls is not reproducible — you can never re-derive
   the state at chapter N from first principles, only replay a mutation log and
   hope no write was lost or reordered.
2. **The facts/derived boundary (ADR-006).** A mutable `CharacterState.location`
   that a chapter writes back is exactly the "inference written back into the
   SSOT" that ADR-006 forbids. It fills the source of truth with unverifiable
   derived claims and nobody can tell a fact from a guess.

## Decision

**Story State is a pure projection — a fold over facts, never a mutable object.**

```
StoryState@N = fold(facts, events[1..N])
```

- Every state view (`ForeshadowState`, `TimelineState`, `CharacterState`,
  `ItemState`, faction/world/… as they land) is **computed** from the Registry's
  declarative facts plus the ordered event log. It is a **Derived Artifact**
  (ADR-006): it lives under `registry/derived/`, never in `facts/`.
- The fold is a **pure, deterministic function**. Same facts ⇒ same
  `state_hash`, computed with the same canonical `sha256(sorted-key JSON)` the
  rest of the Runtime uses. No model call, no randomness, no I/O inside the fold.
- Advancing the story does **not** mutate state. It appends a **fact** (a new
  event, an edited entity with a bumped `fact_version`). Chapter 71 "resolving"
  foreshadow #18 is authored as a new Event that picks up the setup event; the
  projection is then **recomputed** and #18 drops out of the open set on its own.
- The projection **writes nothing back into facts** and can **never gate a
  build** (ADR-003 evaluative axis). It is advisory context that prompts and
  reviewers read; the only gating continuity rule stays the deterministic
  cause-precedes-effect check in `validator.py`.

### Ordering (necessary companion to "fold")

A fold requires a total order. The projection orders events by the same
`sequence_index` the temporal-causal gate already uses (per timeline). Events
without a `sequence_index` are folded in a stable id order after the indexed
ones — a sparse index is not an error (consistent with ADR-006's staleness rule
and the temporal check's "missing index is not a break" stance).

### Staleness (inherited, not reinvented)

Because the projection is a Derived Artifact pinned to `derived_from: ID@vN`, it
inherits ADR-006 staleness for free: when any source fact's `fact_version`
advances, the stored projection is stale and must be recomputed before trust.
Recompute is cheap and total — it is the whole point of a fold.

## Consequences

- The state at any chapter is **reconstructible from facts alone** — no mutation
  log to replay, no lost writes. Auditability of ADR-006 extends to state.
- **Novel Brain** (the static "constitution": mission, genre, promise, forbidden
  style, emotional curve) is explicitly **not** this. Brain is authored,
  near-static configuration; StoryState is recomputed per chapter. Conflating
  them yields an object that is neither a good config nor a good projection. They
  are separate artifacts with separate lifecycles.
- Serialization/scheduler/dashboard layers become **views over the projection**,
  not owners of state. They read; they never hold the truth.
- The existing advisory thread tracker (`memory/threads.py`, P13) is the first,
  ad-hoc slice of this projection; it is subsumed as one view among several,
  keeping its `gating=false` discipline.

## Relationships

- Refines the facts/derived boundary of [ADR-006](ADR-006-registry-facts-only.md);
  state is Derived, never a fact.
- Reproducibility contract from [ADR-001](ADR-001-task-package-is-build-artifact.md)
  and [ADR-005](ADR-005-execution-layer-split.md) is why the fold must be pure.
- Advisory, never-gates discipline is the evaluative axis of
  [ADR-003](ADR-003-qa-dual-axis.md); ordering reuses the deterministic
  temporal-causal gate.
