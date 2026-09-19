# Registry Directory Specification (ANES v2, Phase 1)

- **Status:** Frozen
- **Governed by:** [ADR-006](../adr/ADR-006-registry-facts-only.md), [ADR-004](../adr/ADR-004-four-repo-architecture.md), [ADR-007](../adr/ADR-007-schema-first.md)
- **Depends on:** ID Naming Specification, Reference Grammar, Core IDL
- **Scope:** the on-disk layout of a **Project** instance's Registry. The
  Standard defines the *shape*; a Project *fills* it.

## 1. Purpose

Define where facts, derived artifacts, and the mint ledger live on disk, and the
rules that keep the Facts space clean and the SSOT authoritative. This is the
contract every tool (Resolver, Compiler, QA, Runtime) reads against.

## 2. Top-level layout (within a Project)

```
registry/
  facts/                 # SSOT — declarative facts only (ADR-006)
    characters/          # one file per CHR entity
    relationships/       # one file per REL entity
    timelines/           # one file per TML entity
    events/              # one file per EVT entity
    world_rules/         # one file per MAG/TEC entity
    items/               # one file per ITM entity
    ...                  # one dir per entity type as later phases add them
  derived/               # generated, never authoritative (ADR-006)
    summary/             # rolling summaries
    snapshot/            # point-in-time captures
    analysis/            # inferences, style/psych analysis
  _meta/
    mint-ledger.yaml     # append-only ID mint record (ID spec §8)
    registry-version     # integer: current Registry version (monotone)
    standard.pin         # pinned Standard semver this Project targets (ADR-004)
```

- One entity = one file. Filename = `<id>.yaml`, e.g. `facts/characters/CHR-00018.yaml`.
- Directory name is fixed per entity type (see §2 tree). Tools locate an entity
  by `type_code → directory` mapping, never by scanning.

## 3. Fact file rules

1. **Facts only.** A file under `facts/` contains exactly one entity record
   conforming to that entity's generated JSON Schema. No summaries, inferences,
   evaluations, or analyses (ADR-006).
2. **Schema-validated.** Every fact file MUST validate against
   `generated/json-schema/<Entity>.schema.json`. This is a deterministic QA gate
   (ADR-003).
3. **References, not names.** Every pointer to another entity uses the Reference
   Grammar. No natural-language references in any field except `notes`/`text`
   prose (which are non-resolution fields).
4. **`fact_version`** on each record equals the Registry version at which the
   record last changed. Bumping a fact increments the record's `fact_version`
   and the Project `registry-version`.

## 4. Derived artifact rules

1. Everything under `derived/` is **generated and disposable**; it can be
   deleted and recomputed.
2. Every derived file MUST carry provenance (Reference Grammar §5):
   ```yaml
   derived_from: [CHR-00018@v12, EVT-00102@v7]
   source_version: 12
   ```
3. **Staleness** (ADR-006): if any `derived_from` target's current
   `fact_version` exceeds its pin, the artifact is stale. Consumers treat a
   stale artifact as absent. A deterministic check flags stale derived files.
4. Nothing under `derived/` may be cited as a source by a fact file. Derived →
   Facts write-back is forbidden.

## 5. The mint ledger (`_meta/mint-ledger.yaml`)

- Append-only record of every minted ID: `{id, type_code, minted_at, minter}`.
- It is itself a **Fact** (it records what happened), so it lives under `_meta/`
  and is ground truth for the serial `mint` operation (ID spec §8).
- Tombstoned IDs remain in the ledger forever and are never reminted.

## 6. Versioning & the Standard pin

- `_meta/registry-version` is a single monotonically increasing integer. Any
  fact mutation increments it. This integer is what Reference Grammar `@vN`
  pins target.
- `_meta/standard.pin` records the exact Standard semver this Project conforms
  to (ADR-004). Tools refuse to operate if their Standard version is
  incompatible with the pin.

## 7. What the Standard ships vs. what the Project fills

| Standard (this repo) ships | Project instance fills |
|----------------------------|------------------------|
| this directory contract | actual `facts/**` files |
| generated JSON Schema | actual `derived/**` artifacts |
| ID + reference + IDL specs | `_meta/mint-ledger.yaml` entries |
| validation rules | `_meta/registry-version`, `standard.pin` |

The Template repo (ADR-004) materializes an **empty** version of this tree so a
new Project starts conformant. The Standard never contains a Project's facts.

## 8. Conformance checklist

- [ ] Every fact file validates against its generated JSON Schema.
- [ ] No file under `facts/` contains a summary/inference/analysis (ADR-006).
- [ ] Every reference uses the Reference Grammar; no dangling/tombstoned targets.
- [ ] Every derived file carries `derived_from` + `source_version`.
- [ ] No stale derived artifact is consumed as truth.
- [ ] `mint-ledger.yaml` is append-only; no ID reused.
- [ ] `registry-version` is monotone; `standard.pin` present and compatible.
