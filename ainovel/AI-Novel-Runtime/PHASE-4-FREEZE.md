# Phase 4 Freeze Manifest — ANES v2 Runtime

- **Runtime version:** `0.4.0` (see *Version honesty* below — this number is
  doc-only; there is no `__version__` constant in code yet)
- **Pins Standard:** `2.0.0`
- **Phase:** 4 — Commercial Narrative Intelligence (novel brain + serial ops)
- **Frozen:** 2026-07-04
- **Python:** 3.9+ · deps: pyyaml, jsonschema (+ optional live LLM providers)

## What Phase 4 delivers

Phase 3 closed the execution loop (Task Package → ChapterDraft) with a
deterministic stub, then a real LLM adapter dropped in behind the `Model` seam.
Phase 4 moves the battlefield **off compiler/runtime infrastructure and onto the
novel itself**: quality that a commercial serial actually needs, a narrative IR
the draft is grounded on, per-lead character continuity, reader/pay-intent
simulation, market positioning, and a publishing operations layer.

Every Phase 4 sub-phase held the engineering kernel established in Phases 1–3:

- **No ADR broke.** ADR-001…009 boundaries are intact (see *ADR boundaries* below).
- **Evaluative/predictive signals never gate.** Only deterministic checks and the
  safety red-line can block; quality scores, reader verdicts, pay probabilities,
  pacing analyses, and positioning verdicts are advisory (ADR-003).
- **No artifact writes `registry/facts/`.** Every new artifact class is either a
  *derived* read-side fold or an *authored source* — never fact mutation (ADR-006).
  Eight fitness guards now enforce this per subdomain.
- **Human authority holds every outward transition.** publish, market admission,
  and positioning revision are staged *recommendations*, never auto-executions
  (ADR-009).
- **Every new artifact shipped with a real consumer**, MAJOR-version coexistence
  for prompt/schema changes, and either real-DeepSeek or fixture validation.

The end-to-end pipeline now runs:

```
market snapshot → market-position admission (admit/revise/hold)
  → outline → per-chapter draft (chapter-IR + character-runtime + Brain style)
  → quality v2 + reader simulation + commercial simulation
  → publish-readiness → production card → volume/direction review
  → positioning revision proposal (production → positioning loop)
```

## Sub-phases delivered (4.1 – 4.6)

| # | Capability | Module(s) | Key artifact / schema | Axis |
|---|---|---|---|---|
| 4.1 | **Quality Model v2 + Publish Readiness** | `runtime/publishing/` | `quality-report.v2.schema.json`, `publish-readiness.schema.json` | 18-dim evaluative + deterministic red-line gate; Build-Gate ≠ Publish-Readiness |
| 4.2 | **Narrative IR** | `runtime/scene/`, `runtime/execution/` | `chapter-ir.schema.json`, scene-plan v2, draft prompt v4 | grounds `promise_delivery` on the IR payoff target |
| 4.3 | **Character Runtime** | `runtime/execution/`, `runtime/memory/` | `character-runtime.schema.json`, draft prompt v5 | per-lead goal/pressure/growth as a fold (ADR-008) |
| 4.4 | **Commercial Loop v2** | `runtime/market/`, `runtime/serialize/` | `commercial-session.schema.json` 1.1 (6 pay personas) | pay/continue probability; rejects pay-loss rewrites; comparison-only |
| 4.5 | **Market Positioning** | `runtime/positioning/` | `market-position.schema.json`, `market-admission.schema.json` | pre-book admit/revise/hold; deterministic, never gates; authority=human |
| 4.6 | **Publishing OS** | `runtime/publishing/`, `runtime/dashboard/` | `production-card.schema.json`, `review-report.schema.json` | book-health board + Production Card + Volume/Direction review + positioning revision proposal |

Supporting layers carried in from late Phase 3 / early Phase 4 that Phase 4
depends on and freezes alongside: `runtime/market/` (market snapshot P0),
`runtime/memory/` (long-novel temporal-causal + state projection P13/P14),
`runtime/brain/` (authored Novel Brain constitution P15), `runtime/serialize/`
(serial production chain), `runtime/schedule/` (serial schedule projection),
`runtime/inventory/` (production stock funnel), `runtime/export/` (manuscript +
IP-bible exporters), `runtime/prompt/` (prompt manifest/replay/diff/audit),
`runtime/llm/` + `runtime/llm_adapter/` (live provider seam + boundary contract).

## Runtime subdomains at freeze (16)

```
runtime/
  # build spine + core (Phases 1–3, unchanged)
  catalog.py compiler.py contracts.py derived.py manifest.py
  normalizer.py pipeline.py refs.py registry_loader.py resolver.py validator.py
  # subdomains
  execution/   # loop: agent, model, draft_qa, run
  llm/  llm_adapter/   # live provider seam + boundary contract
  prompt/      # manifest / replay / diff / audit
  scene/       # scene DSL + narrative IR lowering
  memory/      # temporal-causal check, state projection, character runtime fold
  brain/       # authored Novel Brain constitution (source class)
  outline/     # outline DSL bootstrap
  market/      # market snapshot + commercial simulation
  positioning/ # pre-book market-position admission
  publishing/  # quality v2, publish readiness, production card, review
  dashboard/   # read-side panorama aggregation
  serialize/   # per-chapter serial production chain
  schedule/    # serial schedule projection
  inventory/   # production stock funnel
  export/      # manuscript + IP bible exporters
```

> **Known debt (see report §15):** these 16 subdomains are flat under
> `runtime/`. Phase 5 should introduce ownership grouping
> (control/resource/execution/evaluation/production/operations/integration)
> **before** adding more, or Runtime drifts toward a big ball of mud. This is
> recorded, not yet done.

## CLI surface at freeze (17 top-level commands)

Build/execution spine (Phases 1–3): `validate`, `build`, `execute`, `refine`.
Prompt runtime: `prompt-replay`, `prompt-diff`, `prompt-audit`.
Phase 4 novel/serial ops: `outline`, `market`, `positioning`, `commercial`,
`publishing`, `dashboard`, `state`, `schedule`, `serial`, `export`.

Each Phase 4 command is a `<group> <subcommand>` pair (e.g.
`positioning admit`, `publishing card`, `publishing review`, `serial run`,
`brain check`, `export book|ip`, `schedule check`). Full arg reference lives in
`runtime/cli.py`; this manifest freezes the *set*, not the flags.

## Verified at freeze (300 pytest + 77 across 4 custom runners)

Phase 4 uses **two independent test mechanisms**. This matters: a bare `pytest`
run does **not** collect the four custom runners, and the four runners are not
pytest tests. Both must pass for the freeze to hold.

| Mechanism | Suites | Proofs | How to run |
|---|---|---|---|
| pytest | 30 suites (`test_reader_sim` … `test_dashboard_pacing`) | **300 passed** | `python3 -m pytest -q` |
| custom runner | `test_spine` | 11 passed | `PYTHONPATH=. python3 tests/test_spine.py` |
| custom runner | `test_execution` | 33 passed | `PYTHONPATH=. python3 tests/test_execution.py` |
| custom runner | `test_conformance` | 19 passed | `PYTHONPATH=. python3 tests/test_conformance.py` |
| custom runner | `test_fitness` | **14 passed** | `PYTHONPATH=. python3 tests/test_fitness.py` |

All five re-run and passed at freeze time (2026-07-04). Totals: **300 pytest +
77 runner proofs = 377**. The README's "300 + 14" undercounted the spine /
execution / conformance runners — this manifest is the corrected record.

### Architecture Fitness functions (14 standing guards)

The 6 Phase-3 guards (catalog SSOT, no Standard-internal imports, build ⊥
execution layering, gate checks deterministic, no facts-dir literals, output
schema from capability contract) **plus 8 Phase-4 guards** — one per resource
subdomain proving it does **not** write registry facts directly:

```
outline · market intelligence · novel brain · serial production
· serialization schedule · novel dashboard · market positioning · publishing OS
```

These fail the fitness runner on architectural drift. The ADR-006 boundary
("prose/derived never becomes a fact without human authority") is now executable
per subdomain, not just documented.

## ADR boundaries reaffirmed at freeze

| ADR | Boundary | Phase 4 status |
|---|---|---|
| 001 | Task Package is a build artifact | intact — Phase 4 added no build-spine mutation |
| 002 | Contract layer (schemas are the contract) | intact — 23 contract schemas, all Standard-owned |
| 003 | QA dual-axis: only deterministic gates block | intact — all evaluative/predictive signals advisory |
| 004 | Four-repo architecture (Standard/Runtime/Template/Project) | intact |
| 005 | Execution layer split from build spine | intact — fitness guard enforces layering |
| 006 | Registry holds facts only; prose/derived never auto-writes facts | intact — 8 new fitness guards |
| 007 | Schema-first | intact — every new artifact is schema-defined |
| 008 | State is a projection (`fold(facts, events)`), never mutable | intact — character runtime, story state, schedule all folds |
| 009 | Human authority boundary on irreversible/outward transitions | intact — publish/admit/positioning-revision all staged recommendations |

## Artifact taxonomy at freeze (three classes — do not conflate)

1. **Facts** (`registry/facts/`) — the SSOT. Hand-authored or human-approved.
   Phase 4 wrote **zero** new fact-writers (enforced by fitness).
2. **Derived** (`registry/derived/`) — read-side folds over facts + events +
   sources. Provenance-pinned, staleness-checked. ChapterDraft, character
   runtime, story state, dashboard, production card, schedule, inventory,
   review — all derived. **Never consumed as truth when STALE.**
3. **Authored sources** (`sources/`) — Novel Brain constitution, outline,
   market position, market snapshot. Human-authored inputs to generation; not
   facts (not the story's truth), not derived (not folded from facts).

## Honest boundaries (what Phase 4 deliberately does NOT do)

- **No fact evolution from prose.** prose → fact candidates → human approval →
  registry write is *not* built. Facts stay frozen while the serial grows —
  Character Runtime / State / Timeline will drift behind the prose over a long
  serial. This is the #1 Phase-5 architectural gap (report P0 §3).
- **No derived recompute.** Staleness is *detected* (Phase 3); auto-rebuild on
  fact change is not. Impacted derived artifacts must be regenerated by hand.
- **No ID mint ledger.** IDs are hand-authored in fixtures. No serial mint,
  namespace policy, tombstone ledger, or concurrent-mint proof.
- **No WorkflowScheduler.** The system is a set of composable CLI capabilities,
  not an orchestration layer — no task graph, retry/rollback, partial-artifact
  cleanup, or human-approval checkpoint runtime.
- **No Operator UI.** Operator surface is CLI + artifacts only.
- **Single Project.** No multi-book / portfolio / IP-matrix runtime.
- **No Standard migration.** Only Standard 2.0.0 exists; no upgrade/compat path.
- **Reader/market signals are model-driven, not calibrated** against real
  publish/retention/conversion data (no such data exists yet).
- **`__version__` is doc-only.** There is no version constant in code; the
  `0.4.0` above lives only in this manifest. Recording as debt.

## Phase 5 entry conditions (green light)

Phase 5 may begin once this manifest is committed. It **must not** break any
Phase 4 invariant above. Recommended Phase 5 theme — *Production Orchestration
& Fact Evolution* — with the following ordering (per audit + review):

1. **Fact Candidate Pipeline** — prose → candidates → conflict detection →
   human approval → fact write → recompute trigger. (Closes the #1 gap.)
2. **Derived Recompute Engine** — dependency graph, stale detection, recompute
   plan, deterministic rebuild, impacted-artifact report.
3. **ID Mint Ledger** — serial mint, namespace policy, tombstone ledger,
   collision + concurrent-mint proofs.
4. **Production Run Manifest** — one serial run's artifacts / model calls /
   costs / approvals / failures / outputs, reproducible. (Preferred over a
   heavyweight WorkflowScheduler until real production volume justifies one.)
5. **Reader Signal Store** — schema + confidence fields only; wire the seam for
   future real-publish calibration. Do **not** "calibrate" against model output.

Deferred until fact-evolution loop closes + real production volume exists:
heavyweight WorkflowScheduler, Operator Web UI, multi-book portfolio, market
platform depth, Standard migration, multi-agent协作协议.

Before adding subdomains, introduce Runtime ownership grouping (report §15).


