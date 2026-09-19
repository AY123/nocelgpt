# ADR-001: Task Package is a Build Artifact

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

A Task Package is the self-contained bundle handed to a model to execute one
unit of work (e.g. "write chapter 18"). It carries the goal, the relevant
Registry facts, the outline slice, character states, timeline, and style
constraints — pre-resolved so the model reads one bundle instead of the whole
Registry.

The tempting failure mode is to let a human or an AI hand-author this bundle.
The moment that happens, the bundle and the Registry (the SSOT) diverge: the
package says one thing about a character's state, the Registry says another,
and within weeks no one knows which is authoritative.

## Decision

A Task Package is **always a build artifact**, never a source. It is the output
of a deterministic compile step:

```
TaskPackage = compile(
    Registry,        # facts (SSOT)
    Outline,         # the slice being executed
    Characters,      # resolved states
    Timeline,        # relevant events
    Style,           # style constraints
    TaskDefinition   # what to do
)
```

It is therefore **read-only and disposable**. It can always be regenerated from
its sources. It must never be edited by hand.

The compile path is staged (per the Execution Layer design):

```
Registry → Resolver → Normalizer → Compiler → TaskPackage
```

- **Resolver** — expands references transitively (Hero → Equipment → Weapon → Magic).
- **Normalizer** — unifies formats so downstream sees one canonical shape.
- **Compiler** — prunes to a token-budgeted, self-contained bundle.

"Token efficiency" is therefore a *derived property* of compilation, not a
*manual obligation*.

## Consequences

- If a generated chapter implies a fact must change, the change is written to
  the **Registry**, then the Task Package is **recompiled** — never patched in place.
- Task Packages live in a build/ output location, are `.gitignore`-able, and
  are reproducible from `(Registry version, sources)`.
- Any tool that emits a Task Package must stamp it with the source versions it
  was compiled from, so a stale package is detectable.
- Editing a Task Package by hand is a process violation, not a shortcut.

## Relationships

- Depends on [ADR-006](ADR-006-registry-facts-only.md) (Registry is the clean source).
- Depends on [ADR-005](ADR-005-execution-layer-split.md) (compile is resource resolution, not control flow).
- Constrained by [ADR-007](ADR-007-schema-first.md) (package shape references the one Schema).
