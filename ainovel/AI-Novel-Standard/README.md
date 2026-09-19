# AI-Novel-Standard

The **Standard** repository of the AI Novel Operating System (ANES v2). It
answers one question only: *how it should be done*. It contains rules, ADRs,
the data contract (IDL → generated schema), and specifications. It contains **no
novel content and no Project data** (ADR-004).

> Sibling repos (later): `AI-Novel-Template` (what a new project looks like),
> `AI-Novel-Runtime` (how AI executes daily), and `my-novel-XX` Projects
> (a book's real data). Each pins a Standard version.

## Current state

- **Version:** `2.0.0` — see [PHASE-1-FREEZE.md](PHASE-1-FREEZE.md).
- **Phase 1 (Foundation): frozen.** Data contract is established and the
  generator is verified.

## Layout

```
adr/                         # 7 frozen architecture decision records
phase-1/
  spec/                      # 4 frozen specs (ID, reference, IDL, registry dir)
  idl/                       # authoritative hand-written IDL (6 entities + _types)
  generated/json-schema/     # READ-ONLY generated JSON Schema (do not edit)
tools/
  idl_to_jsonschema.py       # the generator (single source -> schema; ADR-007)
PHASE-1-FREEZE.md            # freeze manifest + version pin
```

## Start here

1. [ADR index](adr/README.md) — the immutable core decisions.
2. [ID Naming Specification](phase-1/spec/01-id-naming-specification.md)
3. [Reference Grammar](phase-1/spec/02-reference-grammar.md)
4. [Core IDL](phase-1/spec/03-core-idl.md)
5. [Registry Directory Specification](phase-1/spec/04-registry-directory-specification.md)

## Regenerate / verify schemas

```sh
# regenerate
python3 tools/idl_to_jsonschema.py --idl-dir phase-1/idl --out-dir phase-1/generated/json-schema
# verify no drift (deterministic gate)
python3 tools/idl_to_jsonschema.py --idl-dir phase-1/idl --out-dir phase-1/generated/json-schema --check
```

Requires Python 3 + `pyyaml`.
