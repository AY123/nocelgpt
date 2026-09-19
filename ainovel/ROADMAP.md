# ANES v2 — Architecture Roadmap & Deferral Register

Records what is built, and what was **consciously deferred** with rationale, so
deferral is a decision on record rather than an omission. Driven by the audit of
2026-06-30.

## Built (boundaries now physical, not just documented)

| Layer | State | Proven by |
|-------|-------|-----------|
| Standard — specs, ADRs, IDL→schema | frozen `2.0.0` | schema drift gate (7 files) |
| Standard — **Catalog** (generated) | done | conformance: catalog is single source; misfiled record rejected |
| Standard — **Contract layer** (capabilities + Task Package envelope) | done | conformance: capability gate + envelope validation |
| Runtime — build spine | frozen `0.1.0` | spine suite (11) |
| Runtime — catalog consumer (no hardcoded maps) | done | `TYPE_DIR`/`TYPE_TO_ENTITY` deleted; hash unchanged |
| **Template** — init from catalog | done | conformance: generated Project passes gate |
| Project — example via Template | reproducible | `init_project.py` |

## Deferral register — built only when a consumer exists

The guiding rule (learned in Phase 2): **a module with no consumer is a stub.**
Each item below is deferred *because nothing consumes it yet*, with the trigger
that should unblock it.

| Deferred module | Why deferred | Build trigger | Acceptance proof when built |
|-----------------|--------------|---------------|------------------------------|
| Runtime subdomain split (`resource/ control/ qa/ artifacts/`) | Split STARTED in Phase 3 (`runtime/execution/`); rest follows when more modules land | When Runtime exceeds ~15 modules | All existing suites pass unchanged after move; import graph has no cross-subdomain cycles |
| **Real LLM adapter** (Claude/GPT behind `Model` protocol) | `Model` seam + deterministic adapter exist; real adapter is a drop-in needing secrets/network, out of CI scope | When live drafts are wanted | A real adapter returns `model_kind="llm"`; output flows through the same QA + artifact contract |
| **WorkflowScheduler** (retry/parallel/rollback orchestration) | Nothing to orchestrate beyond one linear build + one execution | When a 2nd capability + multi-task chains exist | A multi-task chain runs; a mid-chain failure rolls back without partial artifacts |
| **PromptLoader** (versioned prompt templates) | Phase 3 uses a minimal inline prompt renderer; sufficient for one capability | When prompts need versioning or 2nd capability | Prompt templates are versioned artifacts; same package + template version => same prompt |
| **Tool / Memory** resolution | No agent needs tools/memory yet (single-shot draft) | When an agent needs external tools or cross-call memory | Resolved as ADR-005 resources behind protocols, like `Model` |
| **Derived-artifact recompute** (auto-rebuild on staleness) | Location, index, and staleness DETECTION now built (`derived.py`); auto-rebuild has no consumer yet | When a stale derived artifact must be regenerated automatically | A stale artifact is detected and re-derived to a fresh pin without manual steps |
| **ID mint module** (serial mint, ledger validation) | Fixtures hand-authored with stable IDs; no concurrent minting | When entities are created programmatically / by agents | Concurrent mints produce no duplicate IDs; a tombstoned ID is never reissued |
| **Migrations** (Standard upgrade, Project pin bump, compat matrix) | Only one Standard version (`2.0.0`) exists | When Standard `2.1`/`3.0` ships | A Project pinned to vN upgrades to vN+1 and re-passes the full gate |
| **Evaluative-QA** (trend, sampling, dashboard, review queue) | Generative output now exists (drafts), but stub model output isn't worth scoring; activates with the real LLM adapter | When the real LLM adapter emits prose to score | An evaluative finding is recorded as trend and provably never blocks a build (ADR-003) |
| **Release/distribution** (version registry, schema discovery) | Runtime resolves schema by path + pin; sufficient for one Standard | When multiple Standard versions coexist | Two Projects pinned to different Standard versions each resolve the correct schema set |

## Phase 4 — Commercial Narrative Intelligence (planned, 2026-07-03)

The engineering kernel (ADR-001..009, dual-axis QA, schema-first, replay, real-model
validation) is strong enough. Phase 4 shifts the main battlefield from *compiler /
runtime infrastructure* to the **novel brain + commercial serial operations**: the
system must continuously answer *why is this chapter worth reading, why must the next
one be opened, why does this character retain readers, why will this book earn long-term*.

**Freeze boundary for Phase 4** (what may evolve, what may not):

| Layer | Modules | May Phase 4 touch? | Rationale |
|-------|---------|--------------------|-----------|
| Engineering kernel | ADR-001 Task Package, ADR-003 dual-axis QA, ADR-006 facts-only registry, ADR-007 schema-first, ADR-008 state=projection, Replay | **No** | Long-term maintenance lifeline; breaking it is a rewrite |
| Novel-brain layer | quality-report / reader-simulation / scene-plan / novel-brain / prompt-manifest schemas | **Yes, rigorously** | Directly drives quality / commercial / retention; must not be frozen dead |
| Evolution method | — | **MAJOR-version coexistence only** (v1 frozen, v2 added) | Matches existing v2/v3/v4 prompt keying and frozen-schema-envelope convention; never break v1 in place |

**Architectural increment that unblocks everything: `Build Gate ≠ Publish Readiness`.**
This does NOT violate ADR-003. It adds a layer *beside* the deterministic build gate:
build is still never blocked by an evaluative judgment (`gating=false` holds), but
*publish* may be advised against by a quality policy — a production decision, staged
for human authority per ADR-009, never auto-executed.

**Three invariants that constrain every sub-phase (learned from the plan review):**

1. **v2 read-side compatibility, not just v2 schema.** MAJOR-version coexistence
   solves the *file* (v1 frozen, v2 added) but not the *readers*. `quality_center.py`
   `SCORE_DIMENSIONS`, RevisionController, Review-Panel synthesis, and the Dashboard
   all hard-read `scores`. So v2 **keeps every v1 dimension** (`commercial` stays as a
   roll-up; new dims decompose it) and every consumer must tolerate a v1-only chapter
   beside a v2 one. No `KeyError` on the first mixed serial.
2. **`safety` splits across BOTH axes — it is NOT purely evaluative.** A subjective
   "edginess risk" score is evaluative (never gates). But deterministic red-line
   checks (banned terms, political/explicit hard-lines) are a **deterministic gate that
   MAY block a build** — this is the correct application of ADR-003, not a violation.
   Never let a platform-ban-triggering chapter through on a `gating=false` report.
3. **16 dimensions map onto the existing Review Panel (P10), not one mega-judge.** One
   LLM emitting 16 stable scores in a single JSON degrades fast. Retention/subscription
   → commercial panelist; character_growth → character panelist; etc. This reuses the
   panel architecture instead of overloading a single judge.

The same discipline that produced P1–P24 governs each sub-phase: **schema-first →
consumer wired → real-DeepSeek validation → regression tests → ROADMAP + memory
updated**. No sub-phase fans out all its schemas at once; a module with no consumer
is still a stub.

| Sub-phase | Deliverable | Consumer (built first) | Acceptance proof |
|-----------|-------------|------------------------|------------------|
| **4.1 Novel Quality Model v2** (P0, in progress) | `quality-report` → **v2** (v1 dims kept; `commercial` becomes a roll-up decomposed into retention/subscription/payoff/curiosity/promise_delivery/pacing/character_growth/serial_sustainability/reader_drop_risk); new `publish-readiness` schema; `safety` split: deterministic red-line check (gate) + subjective edginess score (evaluative) | DraftReviewer maps dims onto the P10 Review Panel (not one mega-judge); **Dashboard aggregates a quality TREND** tolerant of mixed v1/v2 chapters | One real DeepSeek chapter emits explicit retention/subscription/drop/payoff judgments + a `publish_recommendation`; a red-line hit gates the build; a v1 chapter beside a v2 one produces no `KeyError` |
| **4.2 Narrative IR** (P1, ✅ DONE 2026-07-03) | new `chapter-ir` schema; `scene-plan` → **v2** (per-scene information_gain/reader_question added; turning_point→`turn`, emotion_shift→`emotion` reuse v1 fields; `ir_ref` links the plan to its IR); scene-plan demoted to an IR **lowering** (one scene per beat) | `chapter.draft` prompt → **v4**, bound to the Chapter IR (intent + payoff_target + per-beat narrative ops) not the coarse outline | Prose generation consumes an executable narrative IR (v4 draft carries the IR + differs from v3); 4.1 `promise_delivery` grounded on IR `payoff_target` via a widened DraftReviewer seam (`review(..., grounding=)`); v4 serial never gates, v3 byte-identical. 242 pytest + conformance |
| **4.3 Character Runtime** (P2, ✅ DONE 2026-07-03) | new `character-runtime` schema (projection, ADR-008): per-lead goal/pressure/secret/fear/desire/relationship_tension/growth_stage/next_likely_action, folded from facts+outline up to the chapter's cursor event (`runtime/memory/character_runtime.py`) | draft prompt → **v5** (= v4 + a `character_runtime` variable) constrains each lead's next plausible action; growth_stage buckets by folded appearance count, next_likely_action synthesized deterministically from goal+pressure | Character behavior continuous (leads act from a standing goal+pressure), growth traceable (a fold consequence, not a written-back counter), relationship change causal (tension appears/ends because a REL fact did); v5 serial never gates, v4 byte-identical. 254 pytest + conformance |
| **4.4 Commercial Loop v2** (P3, ✅ DONE 2026-07-04) | `reader-simulation` → **v2**: 6 fixed commercial personas (首订党/追订党/白嫖党/打赏党/月票党/养肥党) **extend** the P11 appetite set (do not replace it); add per-persona continue_probability/pay_probability (drop_point/drop_reason already existed). Additive schema 1.0→1.1 (all new fields optional; v1 reports still validate). P11 comparison-only, never-gates contract preserved | Commercial loop rejects a rewrite that keeps readers but loses pay intent (`newly_pay_lost`), not just satisfaction; Dashboard surfaces the pay signal as comparison-only MOVEMENT (never an absolute per-chapter pay score) | Real DeepSeek: the panel splits by pay behavior (打赏党 satisfaction 85/pay 15 — a leak the v1 satisfaction-only panel misses); the full loop REJECTED a real rewrite that lifted retention (+17 continue) but crossed 打赏党 below the pay bar, keeping the original. Comparison-only, never gates. 265 pytest + 12 fitness |
| **4.5 Market Positioning** (P4, ✅ DONE 2026-07-04) | ONE authored `market-position` schema whose `reader_segment`/`trope_map`/`commercial_promise` sub-blocks ARE the roadmap's reader-segment/trope-map/commercial-promise (each populated + read — no stub schemas); new derived `market-admission` verdict schema (authority const human ADR-009, gating const false ADR-003) | `runtime/positioning/` admission check — a DETERMINISTIC fold of Position + Novel Brain + Market Snapshot into admit/revise/hold (completeness + internal Brain-agreement + external Snapshot-alignment); CLI `positioning admit` | Before opening a book the system judges target reader / pay trigger / differentiation / first-30-chapter hook / 100-chapter sustainability; same inputs → same verdict; degrades when Brain/snapshot absent (no fabricated conflict); stale snapshot surfaced never gates. 283 pytest + 13 fitness *(read-side; fixture-validated, no live model needed)* |
| **4.6 Publishing OS** (P5, ✅ DONE 2026-07-04) | Dashboard grows a `book_health` verdict (healthy/watch/at_risk) from signals it ALREADY folds (no new schema); new `production-card` schema (per-chapter, CITES publish-readiness) + ONE `review-report` schema (scope=volume ~10ch / direction ~30ch — not two stubs). Both authority const human (ADR-009), gating const false (ADR-003) | `runtime/publishing/` card.py + review.py — deterministic read-side folds; direction review carries `market_position_revision`, a concrete PROPOSAL to revise the 4.5 Market Position where production diverged from the thesis (never auto-written); CLI `publishing card|review` | A publish decision cites its Production Card (card lifts + cites publish-readiness); a Direction Review produces a concrete market-position revision (sagging retention→sustainability edit, high drop-risk→drop_triggers edit, holds→pay_trigger edit); review/dashboard health thresholds asserted in sync. 295 pytest + 14 fitness *(read-side; fixture-validated)* |

**Phase 4 COMPLETE (4.1–4.6).** The battlefield moved from compiler/runtime infrastructure to the novel brain + commercial serial operations, and every sub-phase held the engineering kernel: no ADR broke, evaluative/predictive signals never gate (only deterministic checks + the safety red-line do), and every new artifact class (quality v2, IR, character runtime, commercial personas, market position, production card, review) shipped with a real consumer, MAJOR-version coexistence, and real-DeepSeek or fixture validation. The pipeline now runs end to end: market snapshot → market-position admission → outline → per-chapter draft (IR + character runtime + Brain style) → quality v2 + reader/commercial simulation → publish-readiness → production card → volume/direction review → positioning revision. The human authority boundary (ADR-009) holds every outward transition (publish, admit, positioning revision) as a staged recommendation, never an auto-execution.

> **Frozen 2026-07-04 — see [PHASE-4-FREEZE.md](AI-Novel-Runtime/PHASE-4-FREEZE.md).** Verified totals at freeze: **300 pytest + 77 custom-runner proofs** (spine 11 / execution 33 / conformance 19 / fitness 14 — a bare `pytest` does not collect the four runners). The per-sub-phase counts above (e.g. "295 pytest + 14 fitness" at 4.6) are as-landed snapshots; 300 is the current total. The freeze manifest is the authoritative record of the frozen capability boundary, artifact taxonomy, ADR status, honest limitations, and Phase 5 entry conditions.

Cross-cutting: **PromptLoader v2** activates at 4.2 (the deferred trigger "2nd
capability / prompts need versioning" is met by draft v4 + quality.review v2) — prompts
become auditable production assets (id/version/role/output_schema/model_preference/
failure_policy), not inline templates.

## Phase 5 — Production Orchestration & Fact Evolution (complete, 2026-07-04)

Phase 4 built the *judgement* system; Phase 5 closes the *evolution* loop so a
long serial's facts grow with its prose instead of drifting behind it. Ordering
(per the audit + review): **fact-candidate → derived recompute → ID mint → run
manifest → reader-signal-store schema**. Heavy WorkflowScheduler and Operator UI
stay deferred until the fact-evolution loop closes and real production volume
justifies them (an audit gap ≠ a build trigger).

| # | Sub-phase | State | What it delivers | Structural invariants |
|---|-----------|-------|------------------|-----------------------|
| 5.1 | **Fact Candidate Pipeline** (PREPARATION half) | ✅ DONE 2026-07-04 | `runtime/candidates/` (extract seam: deterministic stub + LLM drop-in · **deterministic** 5-class reconcile new/additive/consistent/conflicting/unverifiable · stage plan). New `fact-candidate-plan` schema. CLI `candidates extract\|review`. Extracts candidate facts from a produced ChapterDraft, reconciles vs registry, stages a plan for human review | Writes ONLY `registry/derived/fact-candidates/`, never facts (ADR-006, fitness guard #15); never mints (ADR-009, `authority` const human); never gates (ADR-003, `gating` const false). A `conflicting` item is NEVER auto-resolved — surfaced for a human (prose typo? retcon? new fact?). Plan double-pinned (draft content_hash + reconciled fact pins) so it inherits staleness — you cannot mint from a superseded reconciliation. 314 pytest + 15 fitness *(deterministic core; fixture-validated, LLM extractor drop-in unactivated)* |
| 5.2 | **Mint executor** (crosses ADR-009 boundary) | ✅ DONE 2026-07-04 | New subdomain `runtime/mint/` — the system's ONLY fact-writer. New `mint-receipt` schema. CLI `candidates mint --accept CAND-… --confirm` (omit `--confirm` = preview, writes nothing). Writes human-accepted **additive** candidates into facts + `fact_version++` + registry-version++, emits an auditable receipt | ADDITIVE ONLY this phase — a `conflicting` (retcon) or `new` (needs ID Ledger) accepted candidate is REFUSED, not skipped. VALIDATE-THEN-WRITE: post-mint registry is re-gated in memory; a mint that would introduce a dangling/tombstone ref or causality cycle is refused and writes NOTHING (SSOT never left invalid). Stale plan refused (ADR-006). `--confirm` is the distinct human authorization (ADR-009); receipt `authority` const human, `gating` const false. Fitness guard #16 asserts mint is the ONLY fact-writer (only the loader + `mint/` name the facts path). 324 pytest + 16 fitness |
| 5.3 | **Derived Recompute Engine** | ✅ DONE 2026-07-04 | New subdomain `runtime/recompute/` + new `recompute-report` schema. CLI `recompute plan\|apply` (plan previews, writes nothing). After a mint, analyzes which indexed derived artifacts went stale and responds with a DETERMINISTIC/GENERATIVE PARTITION | A pure fact-fold (StoryState — reproducible, no model) is AUTO-REBUILT + written back with a fresh pin (no longer stale); a GENERATIVE artifact (prose draft, quality, sim) is STAGED with the exact human regeneration command, NEVER auto-authored — re-authoring reviewed prose is a silent clobber that crosses ADR-009. The partition is a rebuilder registry (registered rebuilder ⇒ deterministic; else generative). Not a fact-writer (only `mint/` is). Fitness guard #17: recompute imports no model, so it cannot regenerate — enforcing the partition. Report `authority` const human, `gating` const false. 332 pytest + 17 fitness |
| 5.4 | **ID Mint Ledger** | ✅ DONE 2026-07-05 | `runtime/idmint/` — serial, append-only ID allocation (max+1 fold per type-code under an OS flock) into `registry/_meta/mint-ledger.yaml`; new `mint-ledger` schema. Then **5.4b** wired it into the mint executor so `new` candidates finally mint: an id is allocated through the ledger, a minimal name-establishing fact is written, fact_version 0→1 (`mint-receipt` → 1.1, `classification` enum additive\|new) | The ledger is a FACT under `_meta/` but NOT a `registry/facts/**` write, so it sits outside guard 16 and gets its own guard 18 (idmint writes no facts, imports no model — allocation is a pure fold, never generative). The `new` path is deliberately narrow: mints only a name-establishing candidate whose target_type resolves to exactly ONE type_code and whose required fields ⊆ {id,name,fact_version,status} (Character/Item); an ambiguous type (WorldRule→MAG\|TEC), a structured-required type (Event/Timeline/Relationship), or a non-name field is REFUSED with a specific reason, never guessed. Ids allocate strictly above BOTH the ledger max AND the highest existing registry ordinal (a `floor`), so a divergent/empty ledger can never clobber a hand-seeded fact — the collision + tombstone-reservation proofs the roadmap named. Guard 19: `mint_id` is called only from `mint/`, keeping id allocation coupled to the one authorized fact-writer (ADR-009). 352 pytest + 19 fitness |
| 5.5 | **Production Run Manifest** | ✅ DONE 2026-07-05 | `runtime/serialize/run_manifest.py` + new `production-run-manifest` schema. `serial run` now persists an audit record of the run under `registry/derived/run-manifests/` (default-on, `--no-manifest` opts out): per-chapter artifacts/output-paths/draft+state hashes, failures (skipped chapters + reason), model-calls + token usage + costs, approvals (publish_readiness), cross-chapter pacing — enough pins to reproduce the run | A READ-SIDE FOLD: `run_serial` is untouched, so the 10 existing serial tests still pass byte-for-byte. Cost/model-call data is folded from each produced chapter's persisted `draft.produced_by.llm` (no plumbing) — and exists ONLY for live-model chapters; a deterministic-stub run records `cost: null`, `live_calls: 0`, zero tokens (never fabricated). NOT byte-reproducible by design (embeds timestamps + live cost) — exactly the build-manifest stance, one level up: the DRAFTS are reproducible, this record is the audit trail. `gating` const false (ADR-003); writes only to derived/, never facts (ADR-006, guard #10 already fences serialize/). No new fitness guard — introduces no new architectural boundary; `gating:false` is asserted by a test. 359 pytest + 19 fitness + 19 conformance + 33 execution |
| 5.6 | **Reader Signal Store** | ✅ DONE 2026-07-05 | new `reader-signal` schema (real platform 订阅/首订/追读率/掉粉/打赏/月票 + confidence: level/sample_size/is_estimated) imported under `sources/reader-signals/`; `runtime/signals/` loader + a DETERMINISTIC reconcile that places a real signal beside its predicted reader-sim; CLI `signals check\|compare`; Template scaffolds the slot | Resolved the "schema only vs no-consumer-is-a-stub" tension: ONE new schema + a minimal REAL consumer that stays COMPARISON-ONLY and NEVER calibrates. A reader signal is external ground-truth (like the Market Snapshot — imported not crawled, dated, staleness/confidence-aware), never a fact (ADR-006) and never a projection (ADR-008). The reconcile is the seam a future real-publish calibration will consume, WIRED NOT FIRED: `comparison_only`/`gating: false`/`calibrates: false` are all structural; only continue_rate↔retention_rate is a real gap (other metrics reported side-by-side with no fabricated prediction — personas ≠ real readers); low confidence is flagged so a noisy number is never over-read. Guard #20: signals/ writes no facts and imports no model (mirrors #17 — it cannot feed reality back into generation). 372 pytest + 20 fitness + 19 conformance + 33 execution |

**5.1 landed — the preparation half of prose→fact evolution.** The pipeline is
deliberately split at the ADR-009 boundary: it prepares and stages, a human
authorizes the mint (5.2). Extraction is the one evaluative step (a model reading
prose, never gates); reconciliation is a pure deterministic fold — same prose +
same registry ⇒ same classification, which is what makes the plan reproducible
and the conflict-handling auditable. The stub extractor proves the
extract→reconcile→stage loop closes in CI without secrets; the LLM extractor
drops in behind the same `extract(draft) → [RawCandidate]` shape (same seam as
`scene/llm_planner.py`), unactivated until live extraction is wanted.

**5.2 landed — the execution half; the loop's write side now closes.** The mint
executor is the system's first and only fact-writer, and it lives in its own
subdomain (`runtime/mint/`) precisely so the ADR-009 preparation/execution split
is PHYSICAL: `candidates/` literally cannot write facts (guard #15), `mint/` is
the only thing that can (guard #16). Three disciplines make crossing the boundary
safe. **Human-authorized:** no write without `--confirm`; a preview is inert.
**Additive-only (this phase):** it fills empty fields and bumps `fact_version`,
never overwrites a declared fact — a `conflicting` (retcon) or `new` (needs the
ID Ledger, 5.4) accepted candidate is refused, not silently skipped, keeping the
first fact-writer's risk surface minimal. **Validate-then-write:** the post-mint
registry is re-gated in memory and committed only if it passes, so a mint that
would introduce a dangling ref or causality cycle writes nothing — the SSOT is
never left invalid. Staleness falls out for free: the plan's double-pin (5.1)
means once a fact advances, its plan can no longer mint, caught before any write.

**5.3 landed — the loop closes; derived artifacts no longer silently rot.** After
a mint advances a fact, staleness cascades to every derived artifact pinned to
it. Detection already existed (`derived.py`); 5.3 is the response, and its shape
was forced by what the exploration found: most derived artifacts are GENERATIVE
(prose, quality, sims — produced by a model), and only a few are pure fact-folds.
So the engine partitions them. A deterministic fold (StoryState) is auto-rebuilt
and re-pinned — cheap, reproducible, no model, no outward act — so it is fresh
again. A generative artifact is STAGED with the exact human command, never
re-authored: regenerating reviewed prose behind the author's back is a silent
clobber and crosses the ADR-009 boundary. This makes recompute to derived
artifacts what mint is to facts — it does the safe deterministic work and stages
the rest for a human. Fitness guard #17 (recompute imports no model) makes the
partition un-bypassable: the engine *cannot* regenerate, only rebuild or stage.
The prose→fact→recompute loop is now closed end to end for the additive path —
the audit's #1 architectural gap ("facts drift behind prose over a long serial")
is structurally addressed.

**5.4 + 5.4b landed — the `new` path closes; the loop can now BIRTH entities.**
5.4 built the ID Mint Ledger (`runtime/idmint/`): serial, append-only ID
allocation as a pure `max(ordinal)+1` fold per type-code under an `fcntl.flock`,
so concurrent mints never collide (a real multi-process test proves contiguous
1..N, no duplicates). But by the project's own rule — "a module with no consumer
is a stub" — the ledger was inert until 5.4b gave it one: the mint executor now
accepts `new` candidates. When a human confirms a `new` candidate, an id is
allocated through the ledger, a minimal name-establishing fact record is written,
and fact_version goes 0→1 — the same validate-then-write, human-authorized,
append-only discipline as the additive path. Two safety decisions shaped it.
**Narrow by refusal, not by guessing:** `new` mints only a name-establishing
candidate whose target_type resolves to exactly one type_code and whose required
fields are synthesizable from a name (Character/Item); an ambiguous WorldRule
(MAG vs TEC), a structured-required Event/Timeline/Relationship, or a non-name
field is refused with a specific reason — the executor is the boundary that says
"a human must author this", not a heuristic that fabricates structure. **A new id
never clobbers an existing fact:** allocation is floored strictly above BOTH the
ledger max and the highest existing registry ordinal, so a Project seeded before
the ledger existed (empty ledger, facts already on disk — the documented
header-drift case) cannot re-allocate CHR-00001 over a living entity. This closed
a real silent-clobber hole caught by the first end-to-end smoke run — exactly the
class of bug the collision proofs exist to prevent. Guard 19 fences id allocation
(`mint_id`) to `mint/` alone, so birthing an entity stays inside the one
auditable ADR-009 crossing. The prose→fact loop is now closed for BOTH mintable
classes (additive extends, new establishes); `conflicting` retcons remain the one
deliberately-unclosed door, the highest-risk SSOT operation.

**5.5 landed — a serial run now leaves an auditable trail instead of a printout.**
`run_serial` always produced a rich in-memory result (per-chapter outcomes, draft
+ state hashes, verdicts, skips, pacing) that the CLI printed and threw away.
5.5 persists it as a `production-run-manifest` under
`registry/derived/run-manifests/`: artifacts + output paths, failures (skipped
chapters with their stage + reason), model-calls + token usage + money cost,
approvals (publish_readiness), and enough pins (draft_hash + state_hash +
prompt_version + model params + replay_ref) to reproduce the run. The design
decision that kept it cheap and honest: the manifest is a READ-SIDE FOLD.
`run_serial` is untouched — its 10 tests pass byte-for-byte — because every
produced draft envelope ALREADY carries `produced_by.llm` (token_usage, cost,
model, latency, replay_ref) and `publish_readiness`; the manifest folds what is
already on disk rather than plumbing new state through the loop. Two honesty
constraints: cost/token data exists only for LIVE-model chapters, so a
deterministic-stub run records `cost: null` / `live_calls: 0` / zero tokens — it
never fabricates a cost it did not incur; and the manifest is deliberately NOT
byte-reproducible (it embeds timestamps and live cost), the same stance the build
manifest takes — the DRAFTS are reproducible, this is the audit trail over them.
It never gates (ADR-003) and writes only to derived/ (ADR-006, guard #10 already
fences serialize/ as a non-fact-writer). This is the roadmap's chosen alternative
to a heavy WorkflowScheduler: record every run faithfully now; orchestration waits
until real production volume justifies it. Remaining in Phase 5: 5.6 Reader Signal
Store (schema-only seam).

**5.6 landed — Phase 5 COMPLETE.** The Reader Signal Store closes Phase 5 by
wiring the seam between what the model PREDICTS and what really happens when a
chapter ships. `reader-simulation` is a model guessing reader reaction; a
`reader-signal` is real platform data (订阅/首订/追读率/掉粉/打赏/月票), imported
by an operator under `sources/reader-signals/` — external ground-truth, like the
Market Snapshot (pinned not crawled, dated, confidence-aware), never a fact
(ADR-006) or a projection (ADR-008). The design resolved a real tension: the
roadmap said "schema only, NOT calibrated against model output," but this
project's founding rule is "a module with no consumer is a stub." The resolution:
ONE new schema plus a minimal REAL consumer (`runtime/signals/` loader + a
deterministic reconcile) that honors both — the reconcile places a real signal
beside its prediction as a COMPARISON-ONLY, never-gating diagnostic, and
`calibrates: false` is structural: nothing here adjusts the simulator, the prompt,
or generation. The seam is wired, not fired. Honest correspondence: only the
simulator's continue_rate ↔ the platform's retention_rate is a clean pair (both
mean "% who kept reading"); other real metrics are reported side-by-side with no
fabricated predicted counterpart, because simulated personas are not real readers
and forcing a 打赏/月票 gap would over-claim. Low-confidence signals are flagged so
a noisy number is never over-read. Fitness guard #20 makes the discipline physical:
`signals/` writes no facts and imports no model — mirroring guard #17 for
recompute, it structurally *cannot* feed reality back into generation. CLI `signals
check|compare`; Template scaffolds `sources/reader-signals/` with a commented
example. **Phase 5 (5.1–5.6) is complete:** the prose→fact evolution loop closed
end to end (candidates → mint additive+new → recompute → ID ledger), every serial
run leaves an auditable manifest, and the real-signal seam stands ready for a
future calibration phase — with no evaluative/predictive signal ever gating a
build and every outward/irreversible transition (mint, publish, calibration)
staged behind the human-authority boundary (ADR-009).
## Phase 6 — Narrative Director (control-layer skeleton, 2026-07-06)

Phase 6 introduced `runtime/director/` — the objective/brief/critique/rewrite/
comparison/selection artifacts and an execution-time audit block. It landed the
SHAPE of a director but not a working one: no consumer wired generation to the
objective, the artifacts held hardcoded defaults, three of them had no schema, and
none carried the `gating`/`authority` structural consts every peer advisory
artifact has. **Phase 7 (below) is what made the director actually direct.**

## Phase 7 — Director Control Loop (2026-07-06)

Phase 7 promoted the Narrative Director from a CLI stub to the per-chapter control
brain of the serial: objective-driven generation → produce → judge → feed the
realized signals back into the next chapter's objective, all auditable, with every
outward/irreversible transition still human (ADR-009). The compare/select artifacts
were deliberately kept as a THIN ADAPTER over the existing Commercial Loop +
Revision Controller — the director ARBITRATES existing signals, it is not a third
rewrite engine.

| # | Sub-phase | State | What it delivers | Structural invariants |
|---|-----------|-------|------------------|-----------------------|
| 7.0 | **Pay Phase 6 debt** | ✅ DONE 2026-07-06 | 3 missing schemas (director-critique/version-comparison/version-selection); `gating:const false` + `authority:const human` on all 6 director artifacts; compare/select reduced to a thin adapter (fabricated score scale removed); `_director_audit` moved OFF the sealed inner draft ONTO the envelope | Director never gates (ADR-003); `acceptance_threshold` reframed as a REWRITE BUDGET not a gate; new fitness guard #21 (director/ writes no facts, imports no model); fixed 2 director tests that were RED on clean main; a v6 draft's inner ChapterDraft stays additionalProperties:false-valid. 394 pytest + 21 fitness |
| 7.1 | **Director drives generation (prompt v6)** | ✅ DONE 2026-07-06 | `chapter-draft.v6` = v5 + `chapter_objective` + `director_brief` slots; the serial loop folds a ChapterObjective (above the IR) + DirectorBrief and renders them into generation; `render_chapter_objective`/`render_director_brief` | v5 byte-identical (no objective → v5 path unchanged); v6 draft differs (objective injected); state_hash identical across v5/v6 (director changes prose, not facts, ADR-008); never gates. Caught the allowlist-binding wire bug (a prompt var = template slot + loop fold + binding allowlist, three places). 397 pytest |
| 7.2 | **DirectorSession** | ✅ DONE 2026-07-06 | New `director-session` schema (per-chapter decision record: objective/brief/critique/rewrite/comparison/selection refs + pins + rationale); `runtime/director/session.py`; `execute_package` threads the real objective/brief so the session references real OBJ-/DBR- ids (Phase 6's dict stuffed task_id/content_hash as fake ids) | Rides the envelope like commercial-session/revision-session, never the sealed draft; degrades to null refs on a v1-v5 run so every chapter has an audit record; `gating:false`/`authority:human` structural. Surfaced a dead-code finding: `runtime/serialize.py` is shadowed by the `serialize/` package. 399 pytest |
| 7.3 | **Cross-chapter feedback** | ✅ DONE 2026-07-06 | `runtime/director/feedback.py` — chapter N+1's objective is a pure deterministic fold of chapter N's realized signals (quality/commercial verdict, pacing curve, open-setup backlog) into the next objective's commercial intent | Neutral baseline matches build_chapter_objective's defaults, so a no-adverse-signal run is byte-identical with/without feedback; a real adverse signal (backlog > 3) diverges the objective to `clear_payoff`; touches prose intent only, so state_hash is unchanged (ADR-008); advisory, never gates. 401 pytest |
| 7.4 | **Director dashboard view** | ✅ DONE 2026-07-06 | Dashboard `_director_section` folds persisted DirectorSessions + objectives into a direction-health readout (objective coverage, retention/payoff distribution, feedback-divergence count); CLI text + JSON | Pure read-side fold, recomputes nothing authoritative; degrades to None on a project the director never ran; never gates (ADR-003); writes no facts. 403 pytest |

**Phase 7 COMPLETE (7.0–7.4).** The director now closes its own loop: it sets a
per-chapter objective, that objective drives generation (v6), the decision is
recorded as an auditable DirectorSession on the envelope, the realized signals feed
the next chapter's objective, and the whole arc surfaces in the dashboard — with no
evaluative/predictive signal ever gating a build, no fact written by the director
(guard #21), internal draft selection automatic but every outward transition
(publish, mint) still human (ADR-009), and the v5 generation path byte-identical.
Verified totals at close: **405 pytest + 21 fitness + 19 conformance + 33 execution**,
all green. **Follow-up cleanup done in the same pass:** deleted the dead
`runtime/serialize.py` (shadowed by the `serialize/` package, so it never ran);
fixed the 2 Phase-6-era outline-source test failures — a real code bug
(`outline_markdown` used hard subscripts `outline['title']`/`['logline']` where every
other field degrades via `.get`, so a minimal outline crashed) and a stale test
fixture (the outline schema had been tightened to require `collaboration` + an
`^OUTLINE-\d{5,}$` id, which the pre-existing test predated).

## Strategic reorientation (2026-07-06): Novel → Architecture

With the engineering kernel and the P4–P7 production loop complete, the project
crosses a threshold: **the remaining value is almost entirely in novel quality,
not infrastructure.** The standing directive is now ~70% of effort on the novel-
quality systems (Narrative Intelligence, Character Intelligence, Novel Quality
Engine, Reader/Commercial Intelligence, Author Persona, Humanization), ~20% on
automated production, ~10% on engineering — and every design must answer *"does
this make the novel better?"* or it is not built.

The full quality-first reorder — corrected against real code (only the cross-
chapter Narrative Planner is greenfield; character runtime, reader-sim, and the
18-dim quality model already exist and need activation/deepening, not rebuilding)
— lives in [`docs/PRODUCTION_ROADMAP_v2.md`](docs/PRODUCTION_ROADMAP_v2.md) §12
(v2.1). The next greenfield increment (Phase 9, cross-chapter Narrative Planner /
`chapter-mandate`) is designed there. This ROADMAP remains the authoritative
as-built ledger; PRODUCTION_ROADMAP_v2 is the forward plan.

## Decisions made during this pass (stated, not asked)

1. **Catalog is generated from the IDL**, not hand-written — adding a second
   hand-source would violate ADR-007. Entity deployment metadata (`facts_dir`,
   `scope`) now lives in each IDL.
2. **Contracts live in `Standard/contracts/`**, physically separate from
   `phase-1/generated/`. The Task Package envelope is an *authored* artifact
   contract; it validates envelope shape only and never redefines entities
   (so ADR-007 holds).
3. **Template scaffolds from the catalog**, so Project layout cannot drift from
   the Standard. The Runtime fixture stays a *test fixture*; Template output is
   the *Project* path — resolving the "fixture-as-stealth-template" overlap (§2).

## Overlaps acknowledged, not yet split

- `compiler.py` holds `TaskDefinition` + compile logic. `TaskDefinition` is a
  control-flow input; it moves to a contracts module when the Runtime gains a
  proper control/ subdomain (above).
- `manifest.py` sits on the control/resource boundary. Stays with control
  (it records a build event) until the subdomain split forces an explicit home.

## Resolved since the 2026-06-30 audit

- **Real-model finding (fact extraction): id-only prompting made every candidate a phantom `new`.**
  The first real DeepSeek run of `candidates extract` over the 3728-word pilot
  chapter (about the existing lead 埃德里克·万斯 = CHR-00001) returned **33
  candidates, ALL `new`, 0 matched** — a chapter about a known character produced
  zero additive/consistent/conflicting and would have MINTED A DUPLICATE lead
  (CHR-00003 "埃德里克·万斯"), exactly the entity-drift the pipeline exists to
  prevent. Two layers of root cause, both invisible to the deterministic-stub CI
  (the stub reads provenance pins, never prose): (1) `build_extract_prompt` fed
  the model only entity IDs (`CHR-00001`), never names — so a model reading
  "埃德里克·万斯" had no way to know it was CHR-00001 (registry name `Edric Vance`,
  a cross-language gap too); it honestly labeled everything `new`. (2)
  `reconcile.py` trusted only an exact `matched_entity_id` and never did the
  name resolution its own docstring claimed. Fix, mirroring the 5.4b "give the
  model eyes" discipline: an `entity_roster` (id + name + **aliases**, deliberately
  NOT declared field values — value comparison stays the deterministic
  reconciler's job, and leaking values would let the model prejudge consistent/
  conflicting and destroy reproducibility) is rendered into the prompt; and
  `reconcile` gained a deterministic name-resolution safety net (id → name-in-id-
  slot → name-field-value, id-first). Re-run with Chinese aliases added to the
  pilot leads: **0 new, 19 additive, 4 conflicting**, reconciled against
  CHR-00001/002/EVT-00001 — and the conflicts are REAL (CHR-00002 declared eye
  color grey, but the generator wrote 玛伦's eyes as 琥珀色/amber in the prose — a
  genuine continuity drift the pipeline caught and, per ADR-006, never
  auto-resolved). This is the payoff of a real-provider pass: pure-logic tests
  prove the wiring is consistent; only real prose proves the prompt actually
  communicates.

- **Second real-model finding (same run): narrative situation stuffed into a lifecycle enum.**
  The fixed extraction (above) still produced 3 false `conflicting` items: the
  model mapped narrative situation (受伤/被追捕/被治安官搜寻) onto `Character.status`,
  whose schema enum is a LIFECYCLE (active/deprecated/tombstoned). Not a corruption
  path (mint refuses all `conflicting`, and the post-mint gate would reject a
  non-enum status anyway) — but a precision/UX bug: a review queue where 3 of 4
  "conflicts" are false alarms erodes trust in the flag. Fix, deterministic and in
  reconcile (the guarantee, not the advisory model): `build_field_constraints`
  reads each entity schema's enum-constrained fields; `reconcile(field_constraints=)`
  reclassifies an out-of-enum value on a constrained field as `unverifiable` (with
  the reason "status only accepts [...]; prose asserts '受伤'") instead of a false
  retcon. Valid-enum values still conflict normally (a real `deprecated` vs `active`
  retcon is preserved); absent constraints, behavior is unchanged (backward-compat).
  Re-run (cached extraction, fresh reconcile): **conflicting 4→1, unverifiable 0→3**
  — the 3 status items correctly reclassified, and the ONE surviving conflict is the
  real eye-color drift. 382 pytest + 20 fitness + 19 conformance + 33 execution.
  Both findings were invisible to the deterministic-stub CI (the stub never reads
  prose) — the recurring lesson: only a real-provider pass exercises the
  prompt/model seam.

- **Phase 4.6 Publishing OS landed — Phase 4 COMPLETE.** The dashboard's panorama
  became OPERATIONS, all read-side folds over products that already exist — no new
  state, never gates. Three deliverables mapped to the roadmap's acceptance
  criteria: (1) the Dashboard grew a `book_health` verdict (healthy/watch/at_risk)
  synthesized from signals it ALREADY folds — quality-trend retention/drop-risk,
  publish-readiness, commercial pay movement, schedule break-risk, thin stock,
  pacing — with NO new schema (consistent with the dashboard having none); this is
  the "Book Health / trends / drop risk" operations board. (2) `production-card`
  schema + `runtime/publishing/card.py`: a per-chapter fold that CITES the
  publish-readiness verdict (does not recompute it) alongside quality/commercial/
  pacing/status, with deterministic triage flags — satisfies "a publish decision
  cites its Production Card". (3) `review-report` schema + `review.py`: ONE schema
  for both cadences (scope=volume ~10ch 卷末复盘 / direction ~30ch 大方向复盘),
  avoiding two near-identical stub schemas; the DIRECTION scope carries
  `market_position_revision`, a concrete PROPOSAL to revise the authored Market
  Position (4.5) where 30 chapters of production reality diverged from the pre-book
  thesis (sagging retention → sustainability_100 edit; elevated drop-risk →
  drop_triggers edit; publish-holds → pay_trigger edit). This closes the Phase-4
  feedback loop: production reality → revised positioning. Both artifacts:
  `authority` const human (ADR-009 — publish/positioning-revision are outward
  decisions, the review only proposes, never auto-writes sources/market-position.
  yaml), `gating` const false (ADR-003), deterministic (same inputs → same
  output), written to registry/derived/ never facts/. The review's health
  synthesis SHARES thresholds with the dashboard book_health, asserted in sync by
  a test so they never disagree on "at risk". CLI `publishing card|review
  [--json][--write]`; fitness guard #14. **Design fix caught by the pilot smoke
  test** (why a real run matters, not just unit tests): the card's 'not-reviewed'
  flag directly contradicted status='reviewed' — they sit on different axes
  (qa_review lifecycle vs publish-readiness presence), so the flag was renamed
  'publish-unknown'. Commit 43a1db7. Full suite green (295) + 14 fitness. **This
  completes Phase 4 (4.1–4.6)** — the pipeline now runs end to end: market snapshot
  → positioning admission → outline → per-chapter draft (IR + character runtime +
  Brain) → quality v2 + reader/commercial sim → publish-readiness → production card
  → volume/direction review → positioning revision, with no evaluative signal ever
  gating a build and every outward transition staged for human authority.


- **Phase 4.5 Market Positioning landed — the pre-book admission check.**
  The pipeline can now answer the commercial questions BEFORE a book is opened:
  who is the target reader, is there a real pay trigger, is it differentiated,
  does it have a first-30-chapter hook and 100-chapter sustainability. Two
  artifacts, each with a real consumer (the roadmap named four schemas but the
  section forbids fanning out stubs, so the reader-segment / trope-map /
  commercial-promise concepts became the three POPULATED sub-blocks of ONE
  authored `market-position` — each read by the consumer, none a stub):
  `market-position.schema.json` is the AUTHORED commercial thesis under sources/
  (a third artifact class beside the Brain — not a fact, not a projection); and
  `market-admission.schema.json` is a DERIVED read-side verdict. The consumer,
  `runtime/positioning/`, ships on day one: `project_admission` is a DETERMINISTIC
  fold of Position + Novel Brain + Market Snapshot into admit/revise/hold —
  completeness (are the pre-book answers present?), internal (Brain agreement:
  channel match, a leaned-on trope the Brain forbids), external (Market Snapshot
  alignment: channel present, leaned-on genres trending, drop_triggers informed
  by market drop points). No new judgment model — every check is a deterministic
  read, so the same inputs always yield the same verdict (fixture-validated, no
  live model). Two structural invariants: `gating` const false — admission NEVER
  blocks a build (ADR-003); `authority` const human — opening/committing to a
  book is an outward, hard-to-reverse decision (ADR-009), so the system
  recommends but a human commits. Each source degrades gracefully: a missing
  Brain or snapshot never fabricates a conflict, and a STALE snapshot is
  surfaced but never gates. CLI `positioning admit [--json] [--write]`; fitness
  guard #13 (positioning never writes facts, ADR-006 — it writes the verdict to
  registry/derived/market-admission/, never registry/facts/); Template scaffolds
  sources/market-position.yaml. Commit 7a93152. Full suite green (283) + 13
  fitness. **This is the pipeline's commercial FRONT DOOR** — market snapshot
  (P0) informs it, and it now stands beside the Novel Brain as the second
  authored input a strategist writes before production begins.


- **Phase 4.4 Commercial Loop v2 landed — the pay axis, proven to catch a real trade-off.**
  `reader-simulation` gained a second FIXED panel of six commercial personas
  (首订党/追订党/白嫖党/打赏党/月票党/养肥党) that read by PAY BEHAVIOR, extending
  (not replacing) the P11 appetite panel; each persona now reports
  `continue_probability` + `pay_probability`. The Commercial Loop rejects a
  rewrite that keeps readers but loses pay intent (`newly_pay_lost`) — mirroring
  the `newly_dropped` guard — so it optimizes toward pay-conversion, not vague
  satisfaction. Additive schema bumps (reader-simulation + commercial-session
  1.0→1.1, every new field optional; a v1 report/session still validates and a
  mixed v1/v2 serial never `KeyError`s — invariant #1). The Dashboard surfaces
  the pay signal as comparison-only MOVEMENT (`pay_probability_delta` +
  `pay_leak_personas`), NEVER an absolute per-chapter pay score — the sharp
  discipline call: unlike QA scores (absolute), reader/commercial signals are
  structurally comparison-only. Both invariants held (`gating` const false,
  `comparison_only` const true). **Real-DeepSeek proof, two runs:** (1) the panel
  splits by pay behavior — 打赏党 reported satisfaction 85 / continue 90 but pay
  15, a monetization leak the v1 satisfaction-only panel scores as a clean win;
  (2) the full loop REJECTED a real rewrite that improved retention (continue
  +17, 养肥党 newly_retained) with flat satisfaction, because it crossed 打赏党
  below the pay bar (`newly_pay_lost`) — verdict regressed, original kept. That
  is the thesis end-to-end: a rewrite can broaden reach while bleeding revenue,
  and only a pay-aware guard catches it. CLI `commercial --panel
  {appetite,commercial,both}` + `serial run --panel`; eval harnesses
  `tools/eval/eval_commercial_{panel,loop}_deepseek.py` (replay-cached). Commits
  9ce376a (core) / 237eb65 (dashboard) / d9511b1 (loop eval). Full suite green
  (265) + 12 fitness.


- **Commercial loop proven end-to-end under a real model + a third real-model bug.**
  Once DeepSeek recovered from overload, the full Commercial Optimization Loop ran
  against it and reached `verdict: improved` (round 1 accepted, Δsatisfaction +13,
  Δcontinue +33, no persona dropped): all 14 live calls succeeded (replay buckets
  confirmed 6 baseline + 6 re-sim personas + 1 rewrite + 1 gen), every persona's
  real JSON parsed, `compare_simulations` produced a sound relative verdict, and
  the reader-preferred rewrite replaced the initial draft with its
  commercial_session on the envelope. **Third real-model bug caught:** a rerun
  with a different `--timeout` re-billed every call because the replay key hashed
  `timeout_seconds` — an OPERATIONAL field ("how long we'll wait"), not part of
  the semantic request. (The earlier `execute` replay hit only by luck: identical
  `--timeout` both runs.) Fixed: `_stable_request_payload` now strips
  `timeout_seconds` alongside `request_id`/`rendered_at`, so reruns differing only
  in timeout share a cache entry; semantic fields (prompt, max_output_tokens)
  still change the key. Locked by `test_replay_key_stability` (4 proofs). Full
  suite green (163). **Three real-model findings total (serial gen-model, 5xx
  retry, replay timeout-key) — all invisible to the fake-model CI, all in the
  provider/operational seam that only a real run exercises.**


- **Second real-model finding: 5xx server errors were misclassified as permanent.**
  A real DeepSeek commercial-loop run degraded on round 1 with "rewrite model
  produced no usable prose". Root cause (found via replay buckets + a reproduction
  that returned HTTP 503 "Service is too busy"): the OpenAI-compatible adapter
  classified an SDK error as Transient ONLY if its class name was
  APIConnection/APITimeout/RateLimit — so a **503 InternalServerError fell through
  to PermanentLLMError and was never retried**, even though the RetryPolicy would
  have retried it 3×. Provider overload therefore silently degraded the advisory
  loop instead of riding out a transient blip. Fixed: `_classify_openai_error`
  now keys on HTTP `status_code` first (5xx + 408/409/429 ⇒ Transient) with a
  class-name fallback; 4xx client errors stay Permanent. Locked by
  `test_openai_error_classification` (5 proofs). Full suite green (159). The
  advisory loops' swallow-and-degrade behavior (`rewrite_once` returns None on
  error) is left as-is — it is correct by design (an advisory loop must never
  crash the pipeline); the bug was upstream in retry classification, not the
  swallow. **Both real-model findings (this + the serial gen-model bug) were
  invisible to the fake-model CI suite — the payoff of a real-provider pass.**


- **First real-model end-to-end validation (DeepSeek) — and the bug it caught.**
  Ran the whole chain against a live provider (DeepSeek v4-flash), which the CI
  suite's deterministic/fake models could not exercise. Confirmed working under a
  real LLM: single-chapter `execute` produces genuine Chinese prose; the replay
  store is a true cache (identical request → identical `content_hash`, ~0.7s, no
  re-bill — an earlier "mismatch" was a test passing different `--max-tokens`,
  not a bug); the v2 Prompt Orchestrator recap keeps continuity across chapters
  (ch2 correctly picked up ch1's "逐出家族"/"古玉"); the Novel Brain voice and
  cast are honored. **Caught a real bug invisible to fake-model tests:**
  `serial run` built a live model only for `--commercial` (sim/rewrite), never
  for chapter GENERATION — so `--model-provider` was silently ignored and every
  serial chapter came out as deterministic-stub prose. Fixed: the CLI now builds
  a `gen` model for any live provider and passes it as `run_serial(model=...)`.
  Locked by a regression test (`test_serial_cli_builds_gen_model_for_live_provider`)
  that asserts a live provider yields a generation model and deterministic yields
  None. Full suite green (154). **This is why B mattered: pure-logic tests prove
  the wiring is consistent, but only a real run proves the wiring is connected.**


- **Prompt Orchestrator: story-so-far recap flows into chapter generation (C).**
  The deferred "prompts dynamically read the StoryState projection" data line —
  flagged in the very first audit — is now built. At chapter N a long serial
  can't fit the whole book in the model's context, but it CAN fit "the story so
  far": `memory.state_digest` compresses the StoryState projection (active
  characters, still-open foreshadows, active relationships, latest event) into a
  compact deterministic recap. A NEW `chapter-draft.v2` prompt template adds a
  `story_state` slot; the serial chain (`run_serial(prompt_version="2.0.0")`)
  feeds each chapter the digest of the fold up to the PREVIOUS chapter's event.
  Non-breaking by construction: templates are keyed by MAJOR version so v1 is
  untouched, and the binder adds `story_state` ONLY when supplied — so the v1
  path's binding_hash and draft content_hash are byte-identical to before (the
  existing execute suite still passes unchanged). Proven: v2 serial drafts differ
  (recap injected) while per-chapter state_hash stays IDENTICAL to a v1 run
  (state is a fold of facts, not prose); the recap accumulates across chapters;
  never gates (ADR-003). Exposed as `serial run --prompt-version 2.0.0`. 6 proofs
  in `test_prompt_orchestrator`; full suite green (153).


- **Novel Dashboard landed (P18) — the final read-side view.** `runtime/dashboard/`
  aggregates the products the pipeline already produces into one project-wide
  panorama: the Story State projection (P14 — events/characters/relationships/
  foreshadow open+resolved), the Novel Brain (P15 — authored? valid? mission/
  genre/promise), the serialization schedule (P17 — backlog/break-risk/calendar),
  the production tally (drafts in the derived index), and the QA/commercial
  signals riding the latest draft's envelope (P16). It introduces NO new state
  and computes nothing authoritative — every number is read from an existing
  artifact or recomputed by an existing projection. ADVISORY, `gating=false`
  (ADR-003); reads only, never writes facts (fitness guard #12). Every source
  degrades gracefully, so even an empty project yields a dashboard rather than an
  error. Exposed as `runtime.cli dashboard [--today] [--days] [--json]`. 5 proofs
  in `test_dashboard`; full suite green (147). **This completes the North Star
  pipeline skeleton (P14–P18): produce continuously → carry reproducible state →
  read the Brain → optionally optimize commercially → track the schedule →
  surface it all in one view, with no evaluative signal ever gating a build.**


- **Serialization schedule landed as a projection (P17).** `runtime/schedule/`
  gives the backlog / break-risk / update-calendar (库存/断更预警/更新日历) the
  North Star's "持续连载" needs — but, following ADR-008, NOT as mutable
  operational state a daily job edits. It is a PROJECTION:
  `schedule@today = fold(authored SerialPlan, count of produced drafts)`.
  produced = drafts in the derived index; due = daily_target over active days
  since start_date (skipping rest_days); backlog(库存) = produced − due; a backlog
  below the plan's backlog_target is a break risk (断更预警). The SerialPlan is an
  AUTHORED input under `sources/serial-plan.yaml` (like the Novel Brain) — never a
  fact (ADR-006) or a derived artifact. The projection is PURE + DETERMINISTIC
  (same inputs + same `today` → same report) and ADVISORY: `gating=false`, a thin
  backlog WARNS, never blocks (ADR-003). Reads only; never writes facts (fitness
  guard #11). Schema `serial-plan.schema.json`; loader mirrors the Brain (absent /
  all-commented scaffold → treated as absent, no false failure). Exposed as
  `runtime.cli schedule check [--today] [--days]`; Template scaffolds the slot.
  12 proofs in `test_schedule`; full suite green (142). **This completes the
  "持续生产" last mile** — the pipeline can now produce continuously (serial
  chain) AND report whether it is keeping pace with a publishing plan.


- **Commercial loop wired into the serial chain, per chapter (P16→serial).**
  `run_serial` gained optional `simulator` + `rewrite_model` + `commercial_rounds`.
  When both are supplied, each chapter additionally runs the Commercial
  Optimization Loop (P16): the reader-preferred draft is re-gated deterministically
  and, only if it still passes, written back over the initial draft with its
  commercial_session on the envelope; `ChapterRun.commercial_verdict` records the
  outcome. Purely ADDITIVE — with no simulator the per-chapter draft is
  byte-identical to a plain serial run (proven). Comparison-only, never gates the
  serial (ADR-003). Proven in `test_serial`: with an improving simulator every
  chapter's draft hash changes to the rewrite while the `state_hash` stays
  IDENTICAL to the plain run — commercial optimization changes prose, never state
  (ADR-008), because state is a fold of facts. The written-back drafts still pass
  the deterministic gate. Exposed as `runtime.cli serial run --commercial`. 3 new
  proofs (10 in `test_serial`); full suite green (130).


- **Commercial Optimization Loop closed (P16).** `runtime/execution/commercial.py`
  ties SIMULATED reader reaction to a rewrite decision: draft → simulate readers
  → targeted rewrite → re-simulate → keep the rewrite ONLY when readers relatively
  improved (retention/satisfaction up, no persona newly dropped). It is
  deliberately DISTINCT from the Revision Controller: revise_until optimizes 8
  craft dimensions toward an ABSOLUTE threshold; this loop is driven by reader
  deltas and is strictly COMPARISON-ONLY (the North Star discipline). Two
  structural invariants, enforced in code AND by commercial-session.schema.json:
  `gating` const false and `comparison_only` const true — it can NEVER block a
  build (ADR-003), and the deterministic gate still runs on the selected draft.
  It reuses existing seams (reader_sim.compare_simulations + revision.rewrite_once)
  so it adds no new scorer. Always returns the best draft by reader reaction,
  never worse than the input; a persona newly dropping → rewrite rejected, the
  ORIGINAL kept; a degraded simulation bails safely. Session rides the envelope
  (envelope.wrap gained commercial_session). Exposed as `runtime.cli commercial`.
  7 proofs in `test_commercial`; full suite green (127). **Deferred:** wiring the
  loop into the serial chain per chapter (its own increment, once a real serial
  run wants automatic commercial optimization).


- **Serial production chain proven end-to-end (P14+P15 consumer, P17 seed).**
  `runtime/serialize/` is the FIRST real consumer of the whole production chain,
  which is what proves P14 (StoryState fold) and P15 (Novel Brain) actually
  connect. Per chapter: build Task Package → execute (reads the Brain for style)
  → project StoryState up to that chapter's event. State rides between chapters
  as a fold CURSOR (ADR-008), recomputed from facts — never a mutated object.
  `plan_chapters` derives one chapter per event in fold order; `run_serial`
  produces the sequence. Proven: N chapters run end-to-end; state accumulates
  monotonically (events_so_far 1..N, distinct per-chapter state_hash); the whole
  run is reproducible (same project → same per-chapter draft AND state hashes);
  the Brain flows into every chapter (with/without Brain → different drafts, same
  state); a chapter that fails its own deterministic gate is SKIPPED and the
  serial keeps producing (break/resume + 断更恢复 seed); the ORCHESTRATION never
  gates (ADR-003), while each chapter's deterministic gate still blocks that one
  chapter. Reads only; writes drafts as derived artifacts, never facts (fitness
  guard #10). Exposed as `runtime.cli serial run`. 7 proofs in `test_serial`;
  full suite green (120). **This closed the "no real multi-chapter run" gap** —
  P17 (scheduler/库存/断更预警/update-calendar) now has a real consumer to build
  on, and is deferred until that scheduling layer is actually wanted.


- **Novel Brain landed as an authored constitution (P15).** The Brain is the
  authored, near-static intent of a novel — mission, genre, target reader,
  promise, writing/forbidden style, commercial position, emotional curve. It is
  a THIRD artifact class: neither a story fact (ADR-006) nor a recomputed
  projection (ADR-008: StoryState is a fold; the Brain is not). It lives under
  `sources/novel-brain.yaml` (authored input), NEVER under `registry/`. Schema:
  `Standard/contracts/novel-brain.schema.json` (`kind: novel_brain`,
  `additionalProperties: false`). Loader `runtime/brain/` READS only, never
  writes facts (fitness guard #9). Its real consumer ships on day one: the
  `writing_style` + `forbidden_style` render into the chapter-draft prompt's
  `style` variable, so it clears the "no consumer = stub" rule. ADDITIVE and
  non-breaking — a project with NO Brain produces a byte-identical deterministic
  draft (proven in `test_brain`); an authored Brain provably changes the draft.
  A pristine (all-commented) scaffold parses as absent, so `brain check` never
  false-fails a fresh project. Exposed as `runtime.cli brain check`; advisory,
  never gates (ADR-003). Template scaffolds the slot. 9 proofs in `test_brain`;
  full suite green (113). **Deferred:** wiring Brain into outline positioning /
  reviewers / reader-sim (each its own increment, once that consumer is real).


- **Story State landed as a projection, not mutable state (P14, ADR-008).**
  `runtime/memory/state.py` folds the Registry's facts + ordered event log into a
  `StoryState` — `StoryState@N = fold(facts, events[1..N])`. It is PURE and
  DETERMINISTIC (same facts ⇒ same `state_hash`, via the same canonical
  `sha256(sorted-key JSON)` as `execution.agent`), so it never breaks
  reproducibility (ADR-001/005). Advancing the story does not mutate state — it
  appends a fact (a new event / a bumped `fact_version`) and the projection is
  recomputed; a mentorship's `until_event` folding in flips it to ended, a
  foreshadow's payoff event moves it from `open` to `resolved`, with no flag
  flipped anywhere. The projection is a Derived Artifact (ADR-006): written under
  `registry/derived/story-state/`, pinned to `derived_from: ID@vN`, so it
  inherits staleness for free (a bumped source marks it stale, recompute is a
  total fold). Advisory, `gating=false` (ADR-003) — the P13 thread tracker is now
  one view of this projection. Exposed as `runtime.cli state [--up-to-event]
  [--json] [--write]`. 10 proofs in `test_state`; full suite green (104).
  **Deferred, guarded by ADR-008:** Novel Brain (static "constitution" — a
  separate authored artifact, explicitly NOT this projection); serialization /
  scheduler / dashboard (views over the projection, built when a real multi-chapter
  run is the consumer).


- **Derived-artifact lifecycle built (audit's #1 priority).** `runtime/derived.py`
  anchors every derived artifact under the Project's `registry/derived/<category>/`,
  registers it in a provenance index (`_index.yaml`), and enforces an ADR-006
  **staleness check**: a draft whose `derived_from: ID@vN` pin is behind the
  entity's current `fact_version` (or whose source is gone) is rejected at a
  `staleness` execution stage. Detection is built; auto-recompute is deferred.
- **Capability declares its own output schema (audit §3/§4).** The output
  Artifact Contract is read from the capability contract's `output.schema`, not a
  constant in execution code. A fitness guard forbids hardcoded contract
  filenames in `execution/`, so a new capability cannot drift from its output shape.
- **Execution loop closed (Phase 3).** A `ChapterDraftAgent` consumes a Task
  Package and produces a ChapterDraft via a swappable `Model` seam: render prompt
  → model → draft → deterministic draft-QA gate → output Artifact Contract →
  staleness guard → derived artifact written into the Project with provenance.
  The Task Package is now an *execution* artifact, not just a build artifact —
  making the capability's input AND output contracts binding. Byte-reproducible
  with a deterministic stub model (CI-runnable, no secrets); real LLM adapter is
  a drop-in. Loop stops short of writing facts (ADR-006: prose is derived, not a
  fact). 12 proofs in `test_execution`.
- **Architecture Fitness suite added (audit §7).** 6 executable guards fail CI on
  drift: no hardcoded type maps, no Standard-internal imports, build pipeline
  independent of execution subdomain, gate checks deterministic only, no
  hardcoded facts-dir literals, no hardcoded output-contract filename in
  execution. The rules fixed by hand across prior audits are now standing tests
  (`test_fitness`).
- **Capability contracts now constrain inputs, not just name.** Each capability
  declares `input.constraints` (`seed_types`, `min_seeds`, `max_seeds`,
  `required_extra`); the pipeline enforces them at a new `capability-input`
  stage before compile. A task with a disallowed seed type or too few seeds is
  rejected as semantically invalid, not merely name-valid. Behavior-preserving
  for valid tasks (hash `cd2771…`); locked by conformance proofs.
- **`validator.py` converted to a check registry.** Checks self-register with a
  name and a QA axis (`deterministic` gate vs `evaluative` trend, ADR-003);
  `validate()` iterates the registry instead of a hand-wired list. Adding mint /
  derived-staleness / cross-project checks is now a decorated function — the
  aggregator never changes. Evaluative-axis findings are downgraded to warnings
  and can never gate a build, giving evaluative QA a home without violating
  ADR-003. Behavior-preserving (build hash unchanged `cd2771…`); locked by
  conformance proofs.
- **`TYPE_ORDER` hardcode removed.** Bundle emit-order now comes from each IDL's
  `registry.order`, flows through `catalog.json`, and is consumed by the
  normalizer. The Runtime holds no hardcoded type map of any kind
  (`TYPE_DIR`/`TYPE_TO_ENTITY`/`TYPE_ORDER` all gone). Build hash unchanged
  (`cd2771…`), proving behavior-preserving. Locked by conformance proofs.
- **Manifest reproducibility semantics documented.** The package is
  byte-reproducible (content_hash); the manifest is a time-stamped audit record
  and intentionally is not. Stated in `manifest.py` and tests assert only the
  package hash, never the manifest.

