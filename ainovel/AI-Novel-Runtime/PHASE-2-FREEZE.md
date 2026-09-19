# Phase 2 Freeze Manifest — ANES v2 Runtime

- **Runtime version:** `0.1.0`
- **Pins Standard:** `2.0.0`
- **Phase:** 2 — Executable (the spine)
- **Frozen:** 2026-06-30
- **Python:** 3.9+ · deps: pyyaml, jsonschema

## What Phase 2 delivers

Phase 1 was Foundation (a data contract). Phase 2 makes it **executable**: a
vertical spine that runs end-to-end on a real Project instance and emits a real,
reproducible build artifact. The repository is no longer documentation — it runs.

### The spine
```
RegistryLoader → Validator (deterministic gate) → Resolver → Normalizer
              → Compiler → Task Package + Build Manifest
```

### Components frozen
`refs`, `registry_loader`, `validator`, `resolver`, `normalizer`, `compiler`,
`manifest`, `pipeline`, `cli` — see [README](README.md).

## Verified at freeze (`python3 -m tests.test_spine`)

11/11 proofs pass:

1. clean fixture passes the deterministic gate
2. build succeeds and emits package + manifest
3. **rebuild is byte-reproducible** (identical content hash `sha256:cd2771…`)
4. provenance pins all 7 resolved entities at `@version`
5. dangling reference blocks the gate
6. tombstoned reference blocks the gate
7. entity `id` is not mistaken for an outbound reference (bug found & fixed)
8. causal cycle blocks the gate
9. failed gate blocks the build
10. blocked build emits no artifact
11. (schema invalidity blocks the gate — found a real fixture defect during bring-up)

## One real bug found and fixed during bring-up

The reference scanner initially treated each entity's own `id` field as an
outbound reference, producing a false "self-tombstone" finding. Fixed by
excluding `id` from outbound-ref scanning; proof #7 locks it in. Recorded here
because finding it is evidence the spine actually executes rather than merely
compiling.

## ADR conformance

| ADR | How Phase 2 honors it |
|-----|------------------------|
| 001 | Task Package is a compiled artifact; `build/` git-ignored; reproducible; never hand-edited |
| 003 | Only deterministic checks gate the build; no LLM-judge in the gate |
| 004 | Runtime pins Standard 2.0.0; fixture is a Project instance, not the Standard |
| 005 | Control flow (`pipeline`) separated from resource resolution (loader/resolver/normalizer/compiler) |
| 006 | Only `facts/**` loaded as truth; package carries pinned `derived_from` + `source_version` |
| 007 | Validation uses the Standard's *generated* JSON Schema, not a hand copy |

## Out of scope for Phase 2 (deferred)

PromptLoader, ContractLoader (Agent/Capability/Invocation contracts as code),
WorkflowScheduler (multi-task orchestration), the cache/embedding layer for
Derived artifacts, staleness re-computation, and any model/agent invocation.
These layer on top of the proven spine.

## Next

**Phase 3 — Contracts & Agents:** load Capability/Invocation/Artifact/Validation
contracts (ADR-002) as code, attach a PromptLoader, and let the Compiler target a
contract so a Task Package becomes directly invocable by an agent. Then the
WorkflowScheduler to chain tasks. All on top of this frozen, tested spine.
