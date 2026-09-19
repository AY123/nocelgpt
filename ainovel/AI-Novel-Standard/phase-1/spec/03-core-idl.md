# Core IDL — Interface Definition Language (ANES v2, Phase 1)

- **Status:** Frozen (format v1.0)
- **Governed by:** [ADR-007](../adr/ADR-007-schema-first.md)
- **Depends on:** ID Naming Specification, Reference Grammar
- **Authoritative source files:** [`../idl/`](../idl/)
- **Generated outputs:** [`../generated/json-schema/`](../generated/json-schema/) (read-only)

## 1. Purpose

The IDL is the **single hand-written source** of the data contract (ADR-007,
Refinement A). It is written in YAML. From it, a generator produces JSON Schema
(now) and other targets (SQLite/Neo4j/Vector, later). The IDL is never bypassed;
JSON Schema is never hand-edited.

## 2. File layout

```
idl/
  _types.idl.yaml        # primitive + reference type system (shared)
  character.idl.yaml     # CHR
  relationship.idl.yaml  # REL
  timeline.idl.yaml      # TML
  event.idl.yaml         # EVT
  world_rule.idl.yaml    # MAG / TEC (rule-system element)
  item.idl.yaml          # ITM
```

Each entity file is one `entity` definition. `_types.idl.yaml` is shared
vocabulary, not an entity.

## 3. Entity definition format

```yaml
idl_version: "1.0"          # IDL format version (this spec)
entity: <PascalCaseName>    # logical entity name
type_code: <CODE>           # from the frozen ID registry
description: <one line>
fields:                     # ordered map of field-name -> field-def
  <field-name>:
    type: <type-expr>       # see §4
    required: <bool>        # default false
    immutable: <bool>       # default false; true => never changes after mint
    default: <value>        # optional
    doc: <one line>         # human/AI documentation
    # type-specific keys (values, ref_types, of, fields) per §4
```

## 4. Type system (`type-expr`)

| Type | Meaning | Extra keys | JSON Schema mapping |
|------|---------|-----------|---------------------|
| `id` | this entity's own identifier | `code` (type-code) | `string`, `pattern` for that code |
| `string` | short single-line text | — | `string` |
| `text` | long multi-line prose/notes | — | `string` |
| `int` | integer | `min`,`max` | `integer` |
| `float` | real number | `min`,`max` | `number` |
| `bool` | boolean | — | `boolean` |
| `date` | story-world or real date token | `format` | `string` (format/pattern) |
| `enum` | closed value set | `values: [...]` | `string` + `enum` |
| `ref` | single typed reference | `ref_types: [CODES]` | `string` + ref pattern |
| `ref[]` | list of references | `ref_types: [CODES]` | `array` of ref strings |
| `list` | list of a primitive/struct | `of: <type-expr>` | `array` |
| `map` | string-keyed map | `of: <type-expr>` | `object` + `additionalProperties` |
| `struct` | inline nested object | `fields: {...}` | nested `object` |

### 4.1 Reference typing

`ref` and `ref[]` may constrain allowed targets via `ref_types`, e.g.
`ref_types: [CHR, FAC]` means the reference must point at a Character or Faction.
The generator emits a `pattern` enforcing `^(<code1>|<code2>|...)-\d{5,}$`,
optionally allowing a `<project-id>:` prefix and `#fragment`/`@version` suffix
per the Reference Grammar.

### 4.2 Universal fields (injected into every entity)

The generator injects these into every entity unless already present, so all
entities share identity + lifecycle + provenance shape:

```yaml
id:        { type: id, code: <entity code>, required: true, immutable: true }
name:      { type: string, required: true, doc: "mutable human label" }
status:    { type: enum, values: [active, deprecated, tombstoned], default: active }
fact_version: { type: int, min: 1, required: true, doc: "Registry version of this record" }
```

> `fact_version` is what the Reference Grammar `@version` and ADR-006 staleness
> compare against. It lives on the Fact record itself.

## 5. Facts vs Derived (ADR-006)

Entity IDL files define **Facts** only. Derived artifacts (summaries, analyses)
are *not* entities and are not defined here; they reuse the provenance shape
(`derived_from`, `source_version`) defined in the Reference Grammar and will get
their own generated wrapper schema in a later phase. No inference field is
permitted in an entity IDL.

## 6. Generation contract

- Generator: [`../../tools/idl_to_jsonschema.py`](../../tools/idl_to_jsonschema.py)
- Input: every `*.idl.yaml` in `idl/` (+ `_types.idl.yaml`).
- Output: one JSON Schema (draft 2020-12) per entity in
  `generated/json-schema/`, each stamped with a `DO NOT EDIT` header and the
  source IDL file + format version.
- Determinism: same IDL ⇒ byte-identical JSON Schema. Drift is detected by
  regenerating and diffing.

## 7. Conformance checklist

- [ ] Exactly one IDL file per entity; no entity defined twice (ADR-007).
- [ ] Every `type_code` is in the frozen ID registry.
- [ ] Every `ref`/`ref[]` declares `ref_types` from the frozen registry.
- [ ] No inference/summary/analysis field in any entity IDL (ADR-006).
- [ ] JSON Schema present for every entity and byte-identical to a fresh
      generation.
