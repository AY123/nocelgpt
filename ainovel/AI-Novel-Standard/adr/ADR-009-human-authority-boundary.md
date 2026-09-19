# ADR-009: Human Authority Boundary

- **Status:** Accepted (added 2026-07-03, after the Phase 1 freeze)
- **Date:** 2026-07-03
- **Supersedes:** —
- **Superseded by:** —

## Context

The prior ADRs each constrain a *mechanism*. ADR-003 says probabilistic
judgments may not gate. ADR-006 says a Derived artifact may not write back into
Facts. ADR-008 says State is recomputed, never mutated. None of them answer a
different question: **who is allowed to pull the trigger on an irreversible or
outward-facing transition?**

Two such transitions exist in the system, and both are one-way:

1. **Mint** — promoting a reviewed candidate (from an import plan) into
   `registry/facts/**`. Once a fact is minted it becomes SSOT that every
   downstream Task Package, projection, and draft trusts. Un-minting is not a
   clean operation.
2. **Publish** — emitting a chapter outward (to a platform, an export, a reader).
   Once published it is public; retraction does not undo distribution.

Today the code already behaves correctly by habit, but only by habit:

- `runtime/outline/import_plan.py` produces a plan marked
  `review_status="needs_human_review"`, `requires_human_approval=True`,
  `requires_id_mint_review=True`, and its docstring states that applying the
  plan and minting IDs is "a separate workflow." No automatic mint executor
  exists anywhere in `runtime/`.
- `runtime/serialize/loop.py`, `runtime/schedule/`, and `runtime/dashboard/` are
  read-only; they write drafts as Derived artifacts and never publish.

The problem is that this is an *unwritten* invariant. Nothing stops a future
refactor of `import_plan`, or a newly written mint/publish executor, from wiring
an AI decision straight through to Facts or to a platform. The principle lives
in scattered comments and mission prose, not in a binding record. That is
exactly the gap the ADR set is meant to close.

## Decision

There is a **human authority boundary** around every irreversible or
outward-facing transition. The system may do everything up to that boundary
autonomously; it may not cross it without an explicit human authorization step.

The boundary is drawn around two transitions:

- **Mint into `registry/facts/**`** (promoting reviewed candidates to SSOT).
- **Publish** (emitting a chapter outward to any external destination).

The hard rule:

- AI may **prepare, propose, and stage** these transitions — produce the import
  plan, compute the candidate facts, format the export, queue the chapter.
- AI may **not execute** them. Crossing the boundary requires a distinct,
  explicit human authorization action that is separate from the preparation
  step.
- Preparation and execution are **separate workflows**. A staged artifact
  (import plan, ready-to-publish export) is inert until a human authorizes it;
  its mere existence is never consent.

What this boundary is *not*:

- It is not a quality gate. ADR-003 already governs what may block a build. A
  candidate can pass every deterministic gate and still sit un-minted, because
  passing checks is not the same as being authorized.
- It is not the facts/derived rule. ADR-006 forbids automatic write-back of
  Derived into Facts. ADR-009 is orthogonal: even a legitimately human-reviewed
  *fact* still requires an explicit mint action to enter the SSOT. 006 governs
  the machinery; 009 governs the authority.

This axis — **authority**, distinct from *mechanism* (003) and *provenance*
(006) — is the contribution of this ADR.

## Consequences

- Any command or module that would mint facts or publish outward must expose the
  human authorization as a separate, explicit step — never a silent side effect
  of preparation, and never a default-on flag.
- The existing `needs_human_review` / `requires_human_approval` markers in
  `import_plan.py` are now backed by a binding record, not just convention. A
  future refactor that removed them would be violating an ADR, not just a habit.
- A future publish/export stage (roadmap-level, not yet built) inherits this
  constraint by construction: it may format and stage an export, but the act of
  publishing is a human-authorized step.
- Autonomy stays maximal *below* the boundary: generation, review, revision,
  commercial comparison, scheduling, and dashboards all run without asking,
  because none of them crosses an irreversible or outward-facing line.

## Relationships

- Complements [ADR-003](ADR-003-qa-dual-axis.md): gates decide *whether work is
  defect-free*; this ADR decides *who authorizes an irreversible transition*.
  A green build does not imply authorization.
- Complements [ADR-006](ADR-006-registry-facts-only.md): 006 forbids automatic
  Derived→Facts write-back; 009 adds that even reviewed facts need an explicit
  human mint action to enter the SSOT.
- Constrains the mint workflow seeded by
  [ADR-001](ADR-001-task-package-is-build-artifact.md) inputs and the
  import-plan producer under `runtime/outline/import_plan.py`.
