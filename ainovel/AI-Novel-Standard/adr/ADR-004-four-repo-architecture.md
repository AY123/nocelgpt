# ADR-004: Four-Repository Architecture

- **Status:** Accepted (Frozen, ANES v2 Phase 1)
- **Date:** 2026-06-30
- **Supersedes:** —
- **Superseded by:** —

## Context

A single repo conflates four concerns that evolve at different rates and have
different audiences: the rules, the project mold, the execution engine, and the
actual book. Conflating them means a change to "how we write" and a change to
"what happens in chapter 18" land in the same history, and there is no clean way
to start a second novel.

A very common mistake is to treat the actual novel as if it *were* the Standard.
It is not. The novel is an **instance**.

## Decision

Four repositories, with a strict dependency direction and explicit version
contracts:

```
AI-Novel-Standard/   "how it should be done"   — the rules; publishes a semver'd contract
AI-Novel-Template/   "what a new project looks like" — the mold; pins one Standard version
AI-Novel-Runtime/    "how AI executes daily"   — the engine; targets a Standard + Template version
my-novel-XX/  (Project, an instance) "this book's real data" — derived from Template; holds real Registry + prose
```

**Project is never the Standard.** It is an instance produced from Template.

### Version contract (the part that makes it hold together)

- **Standard** publishes its interface under **semantic versioning**. Breaking
  changes to ID rules, Reference Grammar, Schema, or contracts bump MAJOR.
- **Template, Runtime, and every Project pin** the Standard version they depend
  on. No floating dependency.
- A Project upgrades its pinned Standard version deliberately, as a migration,
  not implicitly.

### ID scope (Refinement C)

- IDs are **minted within a single Project** and are monotonic there. The
  Project is the unit of the Registry SSOT.
- Minting is a **serial `mint` operation** (owned by Runtime later), so parallel
  agents / worktrees cannot collide on the counter.
- Cross-work / series namespacing lives at the **reference layer** via a project
  prefix; it does not pollute the per-Project ID.

## Consequences

- Each repo has one clear responsibility and one audience.
- Starting a second novel = new Project from Template; the Standard is untouched.
- Without the pins, the four repos drift apart within a month; the pins are
  load-bearing, not optional.

## Relationships

- Version contract governs [ADR-007](ADR-007-schema-first.md) distribution.
- ID scope is detailed by the ID Naming Specification.
