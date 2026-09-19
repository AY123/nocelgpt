# AI-Novel-Runtime

The **Runtime** of the AI Novel Operating System (ANES v2). It answers one
question: *how an AI novel production system executes every day*. It contains
programs, production folds, gates, evaluators, replay, and operator-facing CLI
commands. The specifications and schemas live in `AI-Novel-Standard`.

> This repo pins **Standard `2.0.0`**. Per ADR-004, Runtime targets a Standard
> version; it does not redefine contracts.

## What Runs Today

**Phases 4, 5, 6, and 7 are complete.** Runtime is no longer only a build spine
plus one draft executor; it is an end-to-end read-side production system for
commercial serial fiction, with a fact-evolution loop and a per-chapter narrative
director:

```text
market snapshot
  -> market-position admission
  -> outline
  -> Task Package
  -> director objective + brief (Phase 7)
  -> chapter draft with Narrative IR + Character Runtime + Novel Brain
  -> quality v2 + reader/commercial simulation
  -> publish-readiness
  -> DirectorSession (per-chapter decision record, Phase 7)
  -> production card
  -> volume/direction review
  -> proposed positioning revision
  -> serial run + run-manifest (audit record, Phase 5)
  -> fact candidates -> mint -> recompute -> ID ledger (fact evolution, Phase 5)
```

The core boundary is unchanged: **deterministic checks may gate builds;
evaluative/commercial/predictive signals never gate builds**. They produce
advice, trends, production cards, director sessions, and human-authority
recommendations. Every outward/irreversible transition (mint a fact, publish,
calibrate against real signals) is staged for human authority (ADR-009).

> **Roadmap status is a snapshot that rots.** For the authoritative,
> up-to-date milestone list see [`../ROADMAP.md`](../ROADMAP.md) and the project
> memory index — not this README. If they disagree, the code and ROADMAP win.

## Production Capabilities

| Area | What Runtime does | Boundary |
|------|-------------------|----------|
| Build spine | Loads facts, validates deterministic gates, resolves refs, normalizes sources, compiles Task Packages and manifests | Deterministic; build-gating |
| Execution | Turns a Task Package into a ChapterDraft derived artifact through deterministic, pasted, or LLM-backed models | Draft is derived, never fact truth |
| Prompt runtime | Loads versioned prompt assets, renders manifests, audits and diffs prompt records | Prompt assets are reproducible production inputs |
| Narrative IR | Lowers outline intent into executable per-beat narrative operations used by draft prompts | Read-side plan, never a source of fact truth |
| Character Runtime | Projects goals, pressure, tension, secrets, fears, desires, growth stage, and next likely action from facts and outline | ADR-008 projection; no counters written back |
| Novel Brain | Loads authored style/market/narrative strategy and checks production alignment | Authored strategic source, not a generated verdict |
| Quality Center | Produces quality v2 judgments, revision plans, red-line checks, and publish-readiness | Red-line is deterministic gate; quality scores are advisory |
| Reader Simulation | Runs appetite and commercial persona panels with continue/pay probabilities and drop reasons | Comparison-only; never absolute sales truth |
| Commercial Loop | Compares drafts/revisions for retention and pay-intent movement, rejecting pay-leaking rewrites | Advisory optimization; never build gate |
| Market Intelligence | Builds market snapshots and deterministic admission verdicts from position, brain, and snapshot alignment | Human-authority recommendation |
| Dashboard | Folds quality, retention, pay movement, pacing, schedule, inventory, and readiness into book health | Operations board; no new fact state |
| Publishing OS | Creates Production Cards and volume/direction Review Reports, including proposed market-position revisions | Human-authority recommendation; never auto-publishes |
| Export | Exports book/IP bible style outputs from existing project artifacts | Read/export only |
| Serial production | Runs the build→execute→state chain over a planned chapter sequence, carrying StoryState as a fold cursor; persists a per-run audit manifest | Orchestration never gates; writes derived, never facts |
| Fact evolution (Phase 5) | Extracts fact candidates from prose, reconciles them, mints human-confirmed additive/new facts, recomputes stale derived artifacts, allocates IDs through an append-only ledger | Mint is the ONLY fact-writer; `--confirm` is the human-authority crossing (ADR-009) |
| Narrative Director (Phase 6/7) | Sets each chapter's objective + brief, drives generation (prompt v6), records a DirectorSession, and feeds realized signals into the next chapter's objective | Advisory planner; writes no facts, imports no model (fitness guard #21); never gates |
| Reader Signal Store (Phase 5.6) | Places real platform signals (订阅/首订/追读/掉粉/打赏/月票) beside predicted reader-sim | Comparison-only; never calibrates generation (seam wired, not fired) |

## CLI Surface

Run commands from `AI-Novel-Runtime/` with `PYTHONPATH` pointing at the runtime
package when needed:

```sh
export PYTHONPATH=.
STD=../AI-Novel-Standard
SCHEMA=$STD/phase-1/generated/json-schema
PROJ=tests/fixtures/proj-demo
```

Core build and execution:

```sh
python3 -m runtime.cli validate --project $PROJ --schema-dir $SCHEMA

python3 -m runtime.cli build --project $PROJ --schema-dir $SCHEMA \
  --task TASK-00018 --goal "draft chapter 18" --capability ChapterDraft \
  --seed CHR-00001 --seed EVT-00002 --out build

python3 -m runtime.cli execute --package build/TASK-00018.package.json \
  --standard-root $STD --project $PROJ
```

Production operations:

```sh
python3 -m runtime.cli market snapshot --project $PROJ
python3 -m runtime.cli positioning admit --project $PROJ --standard-root $STD
python3 -m runtime.cli dashboard --project $PROJ --standard-root $STD
python3 -m runtime.cli publishing card --project $PROJ --chapter TASK-00001
python3 -m runtime.cli publishing review --project $PROJ --standard-root $STD --scope direction
```

Other command groups include:

- `outline sources-check|bootstrap`
- `prompt-replay`, `prompt-diff`, `prompt-audit`
- `refine`
- `commercial`
- `serial run` (add `--prompt-version 6.0.0` for the director-driven chapter loop)
- `schedule check`
- `brain check`
- `state`
- `export book|ipbible`
- `director plan|brief|critique|rewrite|compare|select` (Phase 6/7 narrative director)
- `candidates extract|review|mint` (Phase 5 fact evolution; `mint --confirm` is the human-authorized fact write)
- `recompute plan|apply` (Phase 5.3 derived-artifact recompute)
- `signals check|compare` (Phase 5.6 real reader-signal reconcile)

Use `python3 -m runtime.cli <command> --help` for exact flags. Some live-model
paths require provider credentials in `.env`; replay-backed and deterministic
paths run without network.

## Components

| Path | Role |
|------|------|
| `catalog.py`, `contracts.py`, `registry_loader.py`, `validator.py`, `resolver.py`, `normalizer.py`, `compiler.py`, `pipeline.py` | Deterministic build spine and contract-bound Task Package compiler |
| `derived.py`, `manifest.py` | Derived artifact lifecycle, provenance index, build manifests, staleness checks |
| `execution/` | Draft execution, LLM/paste/deterministic model seams, quality review, red lines, revision, refinement, reader simulation, commercial loop, publish-readiness |
| `prompt/` | Versioned prompt loading, rendering, cache, manifest audit/diff/replay |
| `scene/` | Scene plans, Narrative IR, pacing and serial pacing projections |
| `memory/` | State and Character Runtime projections |
| `brain/` | Novel Brain loading and checks |
| `market/` | Market source ingestion, snapshot writing, market analysis |
| `positioning/` | Market-position admission verdicts |
| `dashboard/` | Book health and operations report folds |
| `publishing/` | Production Card and volume/direction Review Report folds |
| `outline/` | Reference-source checks, outline bootstrap, outline QA and writers |
| `schedule/`, `inventory/`, `serialize/` | Production schedule, inventory, and serial production (build→execute→state chain + run manifest) |
| `director/` | Narrative Director (Phase 6/7): chapter objective, brief, critique, rewrite decision, version comparison/selection, DirectorSession, cross-chapter feedback |
| `candidates/` | Fact Candidate Pipeline (Phase 5.1): extract prose→candidates, deterministic reconcile, stage a review plan (never writes facts) |
| `mint/` | Mint executor (Phase 5.2): the system's ONLY fact-writer; additive/new, validate-then-write, human-confirmed (ADR-009) |
| `recompute/` | Derived Recompute Engine (Phase 5.3): auto-rebuilds pure folds, stages generative artifacts for a human |
| `idmint/` | ID Mint Ledger (Phase 5.4): serial, append-only ID allocation under an OS flock |
| `signals/` | Reader Signal Store (Phase 5.6): real platform signals beside predictions; comparison-only, never calibrates |
| `export/` | Book and IP bible exports |
| `llm/`, `llm_adapter/` | Provider adapters, retry/error classification, replay, cost/usage accounting, boundary dataclasses |
| `cli.py` | Operator entrypoint |

## Proofs

Current local verification uses **two independent mechanisms** — a bare
`pytest` run does *not* collect the four custom runners, so both must be run:

```sh
python3 -m pytest AI-Novel-Runtime/tests
# 405 passed

cd AI-Novel-Runtime
PYTHONPATH=. python3 -m tests.test_spine        # 11 passed, 0 failed
PYTHONPATH=. python3 -m tests.test_execution    # 33 passed, 0 failed
PYTHONPATH=. python3 -m tests.test_conformance  # 19 passed, 0 failed
PYTHONPATH=. python3 -m tests.test_fitness      # 21 passed, 0 failed
```

Totals (verified 2026-07-06): **405 pytest + 84 runner proofs** (spine 11 /
execution 33 / conformance 19 / fitness 21). The Phase 4 frozen capability
boundary is recorded in [PHASE-4-FREEZE.md](PHASE-4-FREEZE.md); the full
milestone history through Phase 7 is in [`../ROADMAP.md`](../ROADMAP.md).
Test counts are a snapshot — re-run the suites above rather than trusting this
number if the tree has moved.

The test suite covers the build spine, contract conformance, execution loop,
prompt runtime, LLM boundary schemas, replay stability, real-provider error
classification, Narrative IR, Character Runtime, quality center, reader
simulation, commercial loop, market positioning, dashboard, publishing OS,
schedule, inventory, serial production, export, and architectural fitness.

The architecture fitness checks are standing guards against drift:

- no hardcoded entity-type maps in Runtime
- Runtime does not import Standard-internal modules
- build pipeline does not depend on the execution subdomain
- all registered gate checks are deterministic
- resource modules do not hardcode facts-directory literals
- execution does not hardcode an output-contract filename
- outline, market, brain, serial, dashboard, positioning, and publishing do not
  write registry facts directly
- mint is the ONLY fact-writer (only the loader and `mint/` name the facts path)
- recompute, idmint, signals, and director write no facts and import no model
  (they cannot regenerate prose or feed reality back into generation)

## Invariants

- **ADR-001** — Task Packages are build artifacts, reproducible from pinned
  inputs, never hand-edited source truth.
- **ADR-003** — deterministic checks may gate; evaluative quality, reader,
  market, pay, and publishing signals are advisory unless they are deterministic
  red-line checks.
- **ADR-004** — Runtime targets Standard `2.0.0`; Standard owns schemas and
  contracts.
- **ADR-005** — control flow, resource resolution, execution, and read-side
  production folds stay physically separate.
- **ADR-006** — only `registry/facts/**` is source truth. Drafts, quality
  reports, simulations, cards, reviews, snapshots, and admission verdicts are
  derived/read-side artifacts.
- **ADR-007** — validation uses generated Standard schemas and authored
  contracts, not Runtime copies.
- **ADR-008** — state, character runtime, inventory, schedule, dashboard health,
  and publishing reviews are projections/folds, not mutable truth.
- **ADR-009** — publish, admit, and market-position revision decisions are staged
  for human authority; Runtime recommends and records, but does not auto-execute
  outward commitments.

## Current Limits

The Runtime has the Phase 4–7 production loop plus a Phase 5 fact-evolution loop,
but it is not yet a complete autonomous publishing factory. Real remaining gaps
(see [`../docs/PRODUCTION_ROADMAP_v2.md`](../docs/PRODUCTION_ROADMAP_v2.md) for the
plan that closes them):

- **no WorkflowScheduler** for multi-task rollback, parallel orchestration,
  resumable batch production, and retry at the production-chain level
- **no Auto Project Genesis**: reference-novel ingestion, analysis, and the
  8-role outline agents exist under `outline/` but are deterministic mocks — they
  are not wired to a real LLM and do not yet generate a Novel Brain or open a
  production-ready book from references alone
- **no unified Human Approval Queue**: `requires_human_approval` flags exist on
  candidate/import plans, but there is no single approval-record store organizing
  every irreversible action for batch human sign-off
- **no post-generation originality/similarity check** against the reference
  novels (the pre-book OriginalityGuard role is a mock)
- **no long-arc planner** for volume structure, 100-chapter direction, or a
  power/progression system consistency check
- **no cost budget / circuit breaker**; run cost is recorded but not capped
- **no Standard migration framework** beyond the current `2.0.0` pin
- **no UI layer**; the operator surface is CLI plus artifacts

Already delivered (do NOT list these as gaps — Phase 5 shipped them):
automatic derived-artifact recompute (`recompute/`), the ID mint ledger
(`idmint/`), and prose→fact write-back via the candidate→mint pipeline
(`candidates/` + `mint/`, human-confirmed).

## Project Fixture

`tests/fixtures/proj-demo/` is a Project instance, not part of the Standard. It
contains real CHR/EVT/REL/TML/MAG/ITM records plus authored and derived
production artifacts used to prove the Runtime against project-shaped data.
