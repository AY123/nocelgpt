# ID Naming Specification (ANES v2, Phase 1)

- **Status:** Frozen
- **Governed by:** [ADR-004](../adr/ADR-004-four-repo-architecture.md), [ADR-007](../adr/ADR-007-schema-first.md)
- **Consumed by:** Reference Grammar, Core IDL, Registry Directory Specification

## 1. Purpose

Define the one and only identifier scheme for every entity in a Project. An ID
is the **permanent, immutable handle** for an entity. Names, titles, and labels
are mutable; IDs are not. Every cross-reference in the system targets an ID,
never a name.

## 2. Core invariants (frozen)

1. **An ID is immutable for the life of the Project.** Renaming an entity
   changes its `name` field; the ID never changes.
2. **An ID is never reused.** Once minted, an ID is permanently bound to one
   entity, even if that entity is later deprecated or deleted (it becomes a
   tombstone, see §7).
3. **IDs are minted within a single Project** and are monotonic there. The
   Project is the unit of the Registry SSOT (ADR-004).
4. **Minting is a serial operation.** Concurrency is resolved by serializing the
   `mint` step, never by relying on a distributed counter.
5. **An ID carries no semantics beyond type + ordinal.** It does not encode
   volume, status, author, or date. Those are fields, not ID substructure.

## 3. ID grammar

```
<id>        ::= <type-code> "-" <ordinal>
<type-code> ::= 3–4 uppercase ASCII letters, from the frozen registry below
<ordinal>   ::= zero-padded decimal, width 5, e.g. 00001 .. 99999
```

- Separator is a single hyphen `-`.
- Width is **5** by default (supports 99,999 entities per type per Project).
  Overflow promotes to width 6 (`100000`); existing width-5 IDs are never
  repadded. Parsers MUST accept width ≥ 5.
- Regex (single ID): `^[A-Z]{3,4}-\d{5,}$`

Examples: `CHR-00018`, `EVT-00102`, `LOC-00008`, `CH-00081` → note `CH` is
2 letters and is therefore **not** valid; chapter uses `CHP` (see registry).

## 4. Frozen type-code registry

Type codes are part of the Standard's public contract. Adding a code is a MINOR
Standard bump; changing or removing a code is a MAJOR bump (ADR-004).

| Code | Entity | Layer | Notes |
|------|--------|-------|-------|
| `CHR` | Character | Detailed Design | persons/agents in-world |
| `LOC` | Location | Worldbuilding | places |
| `ITM` | Item | Worldbuilding | objects, artifacts |
| `MAG` | Magic / Rule-System element | Worldbuilding | a magic or tech rule unit |
| `TEC` | Technology element | Worldbuilding | parallel to MAG for tech settings |
| `FAC` | Faction / Organization | Worldbuilding | groups, nations, guilds |
| `TML` | Timeline | Narrative Architecture | a named time axis (main / flashback / parallel line) |
| `EVT` | Event | Timeline | a dated story-world occurrence, positioned on a `TML` |
| `REL` | Relationship | Detailed Design | a typed edge between two entities |
| `ARC` | Arc (character or plot) | Narrative Architecture | a tension/development arc |
| `PLT` | Plotline | Detailed Design | a thread woven through chapters |
| `THM` | Theme | Requirements | a thematic requirement |
| `VOL` | Volume | Narrative Architecture | top structural module |
| `CHP` | Chapter | Build unit | a chapter (NOT `CH`) |
| `SCN` | Scene | Build unit | smallest authored unit |
| `BEAT`| Beat | Detailed Design | a beat within a scene/chapter |
| `FOR` | Foreshadow (setup/payoff) | Detailed Design | an entry in the setup/payoff ledger |
| `INV` | Invariant | Detailed Design | a canon assertion |
| `TASK`| Task | Execution | a unit of work |
| `PKG` | Task Package | Execution (build artifact) | output of compile (ADR-001) |
| `AGT` | Agent | Contracts | an agent capability instance |
| `CON` | Contract | Contracts | a contract definition |
| `ADR` | Decision Record | Governance | architecture decision (special, see §6) |

> All codes are 3–4 letters to keep the regex uniform and avoid 1–2 letter
> collisions with prose abbreviations.

## 5. Cross-Project / series namespacing (Refinement C)

IDs themselves stay Project-local and clean. When a reference must cross
Projects (a series sharing canon), the **project prefix lives at the reference
layer**, not inside the ID:

```
<project-id>:<id>      e.g.   nova-saga:CHR-00018
```

- Within a Project, the bare form `CHR-00018` is used everywhere.
- The `project-id` prefix is added only by the reference layer when resolving
  across Project boundaries. The Reference Grammar specifies this form.
- This keeps per-Project IDs short, sortable, and collision-free under parallel
  minting.

## 6. ADR IDs (special case)

`ADR-###` predates entity minting and uses width-3 ordinals in the Standard repo
itself (e.g. `ADR-001`). ADR IDs are **Standard-scoped**, not Project-scoped,
because they govern the Standard. They are exempt from Project minting but obey
the same immutability rule.

## 7. Lifecycle: deprecation and tombstones

- An entity is never hard-deleted from the ID space. To remove it, mark its
  Registry record `status: deprecated` (or `tombstoned`).
- A tombstoned ID remains reserved forever and must not be reminted.
- References to a tombstoned ID are a Validation Contract concern (dangling
  reference check), resolved at QA time (ADR-003), not by reusing the ID.

## 8. Minting procedure (normative)

1. Acquire the Project's serial mint lock.
2. Read the current max ordinal for the requested type-code from the mint ledger.
3. Allocate `max + 1`; if it would exceed current width, promote width.
4. Record the new ID in the mint ledger with timestamp and minter identity.
5. Release the lock.

The mint ledger is a Project-scoped, append-only Fact (it records what was
minted; it is ground truth, not inference). Its location is fixed by the
Registry Directory Specification. Implementation of the lock belongs to Runtime
(ADR-004); this spec only mandates serialization.

## 9. Conformance checklist

- [ ] Every entity has exactly one ID matching `^[A-Z]{3,4}-\d{5,}$`.
- [ ] No ID is reused or repurposed across entities.
- [ ] No reference targets a name where an ID exists.
- [ ] Type code is drawn from the frozen registry (§4).
- [ ] Cross-Project references use `<project-id>:<id>`, never an embedded prefix.
- [ ] Tombstoned IDs remain reserved.
