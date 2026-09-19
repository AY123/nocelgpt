# Reference Grammar (ANES v2, Phase 1)

- **Status:** Frozen
- **Governed by:** [ADR-007](../adr/ADR-007-schema-first.md), [ADR-006](../adr/ADR-006-registry-facts-only.md)
- **Depends on:** ID Naming Specification
- **Consumed by:** Core IDL, Registry, Prompts, Task Package compiler

## 1. Purpose

Define the single, machine-parseable syntax for pointing at an entity (or part
of one) from anywhere: Registry fields, prompts, outlines, Task Packages. Natural
language references ("the protagonist", "that city in chapter 1", "yesterday's
event") are **forbidden** in any machine-consumed field because they cannot be
resolved deterministically. Every such reference is a typed pointer to an ID.

## 2. Reference forms

```
<ref>            ::= <local-ref> | <qualified-ref>
<local-ref>      ::= <id> [ "#" <fragment> ] [ "@" <version> ]
<qualified-ref>  ::= <project-id> ":" <local-ref>
<id>             ::= as defined in the ID Naming Specification
<project-id>     ::= 1–32 chars, lowercase ASCII letters/digits/hyphen
<fragment>       ::= <field-path>           ; addresses a part of the entity
<field-path>     ::= <segment> { "." <segment> }
<segment>        ::= <field-name> | <field-name> "[" <key> "]"
<version>        ::= "v" <integer> | "latest"   ; Registry version pin
```

### 2.1 Examples

| Reference | Means |
|-----------|-------|
| `CHR-00018` | the Character entity, current version |
| `CHR-00018#name` | that character's `name` field |
| `CHR-00018#relationships[REL-00004]` | a keyed sub-element |
| `EVT-00102@v7` | the Event as it was at Registry version 7 (pinned) |
| `CHR-00018@latest` | explicit "follow head" (default if `@` omitted) |
| `nova-saga:CHR-00018` | character 18 in another Project (series) |
| `nova-saga:CHR-00018#arc@v3` | fully qualified, fragment + version |

## 3. Resolution semantics (normative)

1. **A bare `<id>` resolves to `@latest`** of the entity within the current
   Project. Resolution is performed on the resource-resolution path (ADR-005),
   never by the model guessing.
2. **`@version` pins** the reference to a specific Registry version. Pinned
   references are how Task Packages (ADR-001) and Derived artifacts (ADR-006)
   record exactly what they were built from.
3. **A fragment `#field-path`** addresses into the entity per the Schema. An
   unknown field path is a resolution error (caught by a Validation Contract).
4. **A `<qualified-ref>`** crosses Project boundaries; resolution requires the
   named Project to be a declared dependency. Cross-Project refs are read-only
   from the referrer's side.
5. **Dangling references** (target ID not minted, or tombstoned) are a
   deterministic QA failure (ADR-003), not a runtime guess.

## 4. Where references are mandatory vs. allowed

- **Mandatory (machine-consumed):** any Registry field that points at another
  entity; any structured input to an Agent/Prompt/Task Package. These MUST use
  this grammar.
- **Allowed (human prose only):** narrative prose (the actual novel text) and
  free-text notes may use names, because they are build artifacts / human-facing,
  not resolution sources. Tools that *extract* facts from prose must convert
  names to refs before writing to the Registry.

## 5. Provenance references (ties to ADR-006)

The `derived_from` field required on every Derived artifact is a **list of
pinned references**:

```yaml
derived_from:
  - CHR-00018@v12
  - EVT-00102@v7
source_version: 12      # the Registry version this artifact was computed at
```

Staleness check: if `latest` version of any `derived_from` target exceeds the
pin, the Derived artifact is stale (ADR-006 §staleness). This is purely
mechanical because references are typed and versioned.

## 6. Canonical serialization

- In YAML/JSON, a reference is a **string scalar** in one of the forms above.
- A field that holds a reference is typed in the IDL as `ref` (single) or
  `ref[]` (list), optionally constrained to a type-code set, e.g.
  `ref<CHR|FAC>`. The IDL section defines this type.
- No alternate encodings (objects with `{id: ...}` wrappers) — one string form
  only, to keep parsing trivial and uniform.

## 7. Conformance checklist

- [ ] Every machine-consumed pointer matches the `<ref>` grammar.
- [ ] No natural-language entity reference appears in a machine-consumed field.
- [ ] Cross-Project refs name a declared dependency Project.
- [ ] Derived artifacts carry pinned `derived_from` + `source_version`.
- [ ] Fragments address fields that exist in the Schema.
- [ ] References serialize as plain string scalars.
