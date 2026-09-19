# Phase 3 Freeze Manifest — ANES v2 Runtime

- **Runtime version:** `0.3.0`
- **Pins Standard:** `2.0.0`
- **Phase:** 3 — Execution loop closed + derived-artifact lifecycle
- **Frozen:** 2026-06-30
- **Python:** 3.9+ · deps: pyyaml, jsonschema

## What Phase 3 delivers

Phase 2 made the repository *run* (build a Task Package). Phase 3 makes the Task
Package an **execution artifact**, not just a build artifact: a real
`ChapterDraftAgent` consumes it and produces output. This is the loop the audit
identified as the ★★★★★ gap.

### The execution loop (control flow, distinct from the build spine, ADR-005)
```
Task Package → render prompt → Model → ChapterDraft
            → deterministic draft QA gate (ADR-003)
            → output Artifact Contract (ADR-002)
            → derived artifact + provenance (ADR-006)
```

### New (under `runtime/execution/` — the subdomain split begins here)
- `model.py` — `Model` protocol + `DeterministicModel` (CI-runnable, no network).
  Real Claude/GPT adapters are drop-ins behind the same `generate()`.
- `agent.py` — `ChapterDraftAgent`: renders a prompt, calls the model, emits a
  ChapterDraft artifact with provenance.
- `draft_qa.py` — deterministic structural QA on the draft (gate axis only).
- `run.py` — orchestrates the loop; writes the draft as a **derived** artifact.

### New in the Standard
- `contracts/chapter-draft.schema.json` — the OUTPUT Artifact Contract (the 4th
  ADR-002 contract kind, now materialized for an output).
- `contracts/capabilities/chapter-draft.capability.yaml` — gained
  `input.constraints` (seed types/count, required extra), enforced by the Runtime.

## Verified at freeze (48 proofs across 4 suites + drift gate)

| Suite | Proofs | Asserts |
|-------|--------|---------|
| schema drift | gate | IDL → 7 generated schemas, no drift |
| `test_spine` | 11 | build pipeline + reproducibility + gating |
| `test_conformance` | 19 | catalog SSOT, contracts, input constraints, validator registry, Template→Project |
| `test_execution` | 12 | loop closes, draft reproducible, provenance pinned, derived index, staleness guard, output schema from capability contract, QA gates, package not mutated |
| `test_fitness` | 6 | **Architecture Fitness** (audit §7) — see below |

### Architecture Fitness functions (standing guards, audit §7)
1. No hardcoded entity-type maps in Runtime (catalog is SSOT).
2. Runtime never imports Standard-internal modules.
3. Build pipeline does not depend on the execution subdomain (layering).
4. All registered gate checks are deterministic (ADR-003).
5. No hardcoded facts-dir literals in resource modules.
6. Execution does not hardcode an output-contract filename (it comes from the
   capability contract's `output.schema`).

These fail CI on architectural drift — the rules fixed by hand across prior
audits are now executable.

## Derived-artifact lifecycle (audit's #1 priority, now built)

Phase 3 produces derived artifacts (ChapterDraft). `runtime/derived.py` gives
them the lifecycle ADR-006 always required:
- **Anchored location** — written under the Project's `registry/derived/<category>/`,
  never an arbitrary path, never `facts/`.
- **Provenance index** — `registry/derived/_index.yaml` records each artifact's
  id, path, content hash, and pinned sources.
- **Staleness check** — a derived artifact whose `derived_from: ID@vN` pin is
  behind the entity's current `fact_version` (or whose source is gone) is STALE
  and must not be consumed as truth. Enforced as a deterministic execution-stage
  gate, not just documented.

## Output schema binding (audit §3/§4, now fixed)

The output Artifact Contract is declared by the capability contract
(`output.schema: chapter-draft.schema.json`) and loaded from it at execution
time. It is no longer a constant in execution code — a new capability cannot
silently reuse or drift from the wrong output schema. A fitness guard enforces
this.

## Honest boundary: the loop does NOT write facts (ADR-006)

The audit's loop diagram ended `Output → Registry Update`. The freeze
**deliberately stops short of writing `registry/facts/`**: prose is a derived
artifact, not a fact (ADR-006). The draft is written under the derived path with
provenance. Extracting facts *from* prose is a separate generative capability
(`FactExtraction`) and is deferred until it has a consumer. Auto-writing facts
from generated prose would corrupt the SSOT — so it is not done.

## Model adapter honesty

The loop is proven with a **deterministic stub model** so it runs in CI without
secrets and is byte-reproducible. A real Claude/GPT adapter is a drop-in behind
the `Model` protocol (`model_kind="llm"`); it is not implemented here because the
stub is sufficient to prove the loop closes and the contracts bind. Real-model
output is, by nature, evaluative (trend axis), never a deterministic gate.

## Out of scope (still deferred, now with acceptance proofs — see ROADMAP)

Real LLM adapter, PromptLoader (versioned templates), WorkflowScheduler,
multi-capability routing, derived **recompute** (staleness detection now exists;
auto-rebuild does not), ID mint, migrations, evaluative-QA trend store,
cross-project resolver.

## Next

The loop is closed for one capability with a stub model, and derived artifacts
now have a lifecycle. The next consumer-driven step is a **real LLM adapter**
behind the existing `Model` seam (drop-in), which turns the deterministic proof
into live drafts and activates the evaluative-QA trend axis — without touching
the build spine or contracts.
