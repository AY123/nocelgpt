# Architecture Decision Records (ADR)

These records are **frozen** as of ANES v2 Phase 1. They are the immutable
core of the AI Novel Operating System. An ADR is never edited in place; it is
either `Accepted` (and frozen) or later `Superseded` by a new ADR that
references it. Changing a frozen ADR requires a new ADR, never a silent edit.

| ID | Title | Status |
|----|-------|--------|
| [ADR-001](ADR-001-task-package-is-build-artifact.md) | Task Package is a Build Artifact | Accepted (Frozen) |
| [ADR-002](ADR-002-contract-layer.md) | Unified Contract Layer | Accepted (Frozen) |
| [ADR-003](ADR-003-qa-dual-axis.md) | QA Dual-Axis Model | Accepted (Frozen) |
| [ADR-004](ADR-004-four-repo-architecture.md) | Four-Repository Architecture | Accepted (Frozen) |
| [ADR-005](ADR-005-execution-layer-split.md) | Execution Layer Split | Accepted (Frozen) |
| [ADR-006](ADR-006-registry-facts-only.md) | Registry Is Declarative Facts Only | Accepted (Frozen) |
| [ADR-007](ADR-007-schema-first.md) | Schema First | Accepted (Frozen) |
| [ADR-008](ADR-008-state-is-projection.md) | Story State Is a Projection, Not Mutable State | Accepted (Frozen) |
| [ADR-009](ADR-009-human-authority-boundary.md) | Human Authority Boundary | Accepted (post-freeze, 2026-07-03) |

ADR-001 through ADR-008 are the original Phase 1 frozen core. ADR-009 was added
after the freeze under the same rules (never edited in place; superseded only by
a new ADR) — it does not modify any frozen ADR, it adds an orthogonal invariant
(authority, distinct from mechanism) that the frozen set left unstated.

## Refinements folded into the frozen set

Three refinements (A/B/C) raised before freeze are not separate ADRs; each is
absorbed into the ADR it constrains:

- **Refinement A** (single hand-written schema source) → ADR-007.
- **Refinement B** (Derived staleness via provenance) → ADR-006.
- **Refinement C** (Project-scoped serial ID minting) → ADR-004 + the ID Naming
  Specification.
