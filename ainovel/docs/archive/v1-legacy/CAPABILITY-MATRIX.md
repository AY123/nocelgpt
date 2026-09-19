# ANES v2 — Capability Matrix (built / live / gap)

Purpose: this file is the **anti-duplicate-work ledger**. External strategic
reviews (see `任务清单.txt`) recurringly propose "new" modules that already
exist and are wired. Before building anything a review calls "missing", check
here first. This complements `ROADMAP.md` (deferral register) with a
report-claim ↔ code cross-reference.

Legend:
- **live** — built AND on a real production path (serial run / CLI), with tests.
- **built** — module exists and tested, but not yet on the default production path.
- **gap** — genuinely absent or a placeholder that never fires in practice.

Audit basis: 2026-07-13, verified against `runtime/` HEAD.

## Report-claim cross-reference

| Report claim ("missing / mock") | Actual | Evidence |
|---|---|---|
| Long-Arc Planner (卷级/百章/升级曲线) | **live** (v10 prompt path) | `runtime/arc/projection.py`; injected `serialize/loop.py:293,581` |
| Narrative Director control loop | **live** (v6+) | `runtime/director/`; objective/brief folded into prompt |
| Reference Intelligence | **live** (deterministic anchor; opt LM judge arm) | `runtime/reference/`; writes `REFPROFILE-001.json` |
| Auto Project Genesis (one command) | **live** (preview/confirm split) | `runtime/genesis/orchestrate.py`; CLI `genesis` (`cli.py:2257`) |
| Approval Queue | **live** (real queue + audit ledger + CLI) | `runtime/approval/queue.py`; CLI `approval list/show/approve/reject/stats` |
| WorkflowScheduler (checkpoint/resume/retry/budget stop) | **live** | `serialize/workflow_scheduler.py`; CLI `workflow`; run-level budget halt `loop.py:313` |
| Platform redline deterministic gate (architecture) | **live** | `runtime/execution/redline.py`; hard-hit blocks build `run.py:184` |
| Originality / similarity check | **live but opt-in** | `runtime/execution/m7.py` (L0–L3; L3 blocks) — only runs when `originality_references` supplied |
| Quality diagnosis + revision + regression loop | **live** | `quality_center.py` (18-dim + revision_plan), `revision.py:214`, `prose_hygiene.py` |
| Cost / budget circuit-breaker | **partial** | run-level halt `loop.py:313`; no per-chapter budget / tier routing / serial-wired fallback |
| Narrative State (unified projection) | **partial (fragmented)** | IR / mandate / arc each project a slice; no single `narrative-state` read-side fold |
| Multi-version generation + director selection | **built, not live in serial** | `chapter/reviser.py:generate_candidates`, `director/compare.py`; not called from `serialize/loop.py` |

## Genuine gaps (the real backlog)

These are what the milestone plan (see memory `task-list-audit-2026-07`) targets.
Each is a real absence or a placeholder that never fires, NOT a "build it again".

| # | Gap | Why it matters | Milestone |
|---|---|---|---|
| B1 | Redline default ruleset is placeholder patterns (`露骨性描写占位符` etc. — never match real prose) | Commercialization red line; gate architecture is inert without real rules | M1 |
| B2 | Originality m7 gate is opt-in, not default-wired into serial | Real reference-driven books need similarity checking on every chapter | M1 |
| B3 | ~~Genesis does not generate market-position / run admission~~ **DONE (M2)** — `positioning/generate.py` folds a Position, genesis runs admission → pins verdict + surfaces in approval context | Open-book chain now closes (参考→开书→市场准入) | ✅ M2 |
| B4 | ~~Cost control incomplete~~ **DONE (M4)** — `run_serial(per_chapter_budget=...)` caps single-chapter spend (skips commercial/hygiene loops past cap); provider fallback confirmed live (comma `--model-provider`). Tier routing / daily budget deferred (no consumer = stub) | Multi-version generation now bounded | ✅ M4 |
| B5 | ~~No unified read-side `narrative-state` projection~~ **DONE (M3)** — `runtime/narrative/state.py` folds StoryState + persisted mandate/ir/run into one projection; live on dashboard + `narrative` CLI | Long-serial payoff-debt / reader-question / emotion-curve read surface | ✅ M3 |
| C6 | ~~Multi-version + selection not on serial path~~ **DONE (M4)** — `run_serial(candidate_models=[...])` generates N real drafts (write=False for losers), reuses `build_version_comparison`/`build_version_selection`, persists only winner; CLI `--candidates N`. Honest (real LLM regen, NOT the string-mangling reviser stub); default 1 = byte-identical | Per-chapter quality lever, budget-gated | ✅ M4 |
| C7 | ~~Reference LM abstraction arm rarely used~~ **DONE (M5)** — standalone `reference_lm_abstraction` artifact (`reference/abstract.py`) + frozen schema + `abstract/show/validate` CLI; fed to IR/arc/prompt-binding. **Verify caught + fixed a Schema-First violation**: it had injected the field INTO the frozen outline (additionalProperties:false → contract red); moved to a runtime sibling merged onto the in-memory outline in serial CLI (disk stays clean), reconnecting the real consumer path (was built≠live) | Report's "abstract sell-points/pacing/hooks" layer | ✅ M5 |

## Standing rule

Do not "new-build" a **live** or **built** row above. For a **built** row, the
work is *wiring + budget*, not re-implementation. For **gap** rows, respect
CLAUDE.md §1 (Schema-First) and §2 (envelope sibling, never gate on evaluative
signals). Every gap that touches an LLM path needs a real-model smoke command
(project history: only real models expose adapter/enum/wiring bugs).
