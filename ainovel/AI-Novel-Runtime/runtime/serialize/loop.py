"""Serial production subdomain (ANES v2, roadmap P14+P15 consumer, P17 seed).

The FIRST real consumer of the full production chain: it runs many chapters in
sequence and carries state between them, which is what proves P14 (StoryState
fold) and P15 (Novel Brain) actually connect end-to-end. Per chapter:

    build Task Package -> execute (reads the Novel Brain for style)
                       -> project StoryState up to this chapter's event (cursor)

State rides between chapters as a fold CURSOR (ADR-008): chapter N's state is
`project_state(reg, up_to_event=<this chapter's event>)`, recomputed from facts —
never a mutated object. The whole run is reproducible: same project => same
per-chapter draft hash AND state_hash.

DISCIPLINE:
  - The ORCHESTRATION never gates (ADR-003 evaluative axis): a chapter that fails
    its own deterministic draft QA is recorded and SKIPPED, and the serial keeps
    going (the seed of break/resume + 断更恢复). The per-chapter deterministic
    gate inside execute_package still blocks that ONE chapter — the loop just
    doesn't abort the serial on it.
  - READS only; writes drafts as derived artifacts (via execute_package), never
    facts (ADR-006).
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..llm.types import CostMetrics, TokenUsage

from .. import compiler, registry_loader, derived
from ..pipeline import build_task_package
from ..execution.run import execute_package
from ..memory.state import project_state
from ..chapter import (
    BeatPlanner,
    ChapterProductionOrchestrator,
    ChapterReviewer,
    DraftWriter,
    Finalizer,
    RevisionEngine,
)
from .quality_snapshot import build_quality_snapshot
from .checkpoints import build_checkpoint, CHECKPOINT_INDICES
from .cost_breaker import check_budget
from ..llm.cost_fold import CostFold


def _breaker_tripped(**layers) -> bool:
    """True when any budget layer has tripped the D180-05 circuit breaker.

    Both budget decisions in this loop (run-level before starting a chapter,
    chapter-level before the optional enhancer loops) route through
    `cost_breaker.check_budget` so the layered breaker is the ONE thing that
    decides whether the run may keep paying a provider. Before this it was two
    inline `spent >= limit` compares and the breaker module — which the docstring
    calls "a hard stop on billing" — had no caller at all.

    A layer with `limit=None` never trips, so a run that passes no budget flags
    behaves exactly as it did before this wiring.
    """
    return check_budget(**layers).any_tripped


def _at_least(major: str, floor: int) -> bool:
    """True when the prompt MAJOR version is >= floor.

    The prompt-capability checks below used to be hand-maintained CLOSED
    enumerations (`major in ("3","4",...,"11")`). Every one of them was in fact a
    contiguous range topping out at the newest version, so each new prompt version
    had to be appended to TEN separate tuples — and a version missed from a tuple
    silently skips that variable-binding block, rendering a template whose required
    variables were never bound. That is exactly how v12 shipped broken: the CLI
    resolved --craft-texture to 12.0.0 while every ladder here still stopped at 11.

    Expressing the same predicate ORDINALLY makes a new version work by default and
    removes the whole class of defect. Non-numeric majors (never produced by the
    resolver) degrade to False, preserving the old behavior for unknown values."""
    try:
        return int(major) >= floor
    except (TypeError, ValueError):
        return False


def _scene_beats(scene_plan: Optional[dict]) -> Optional[int]:
    """How many scenes the plan carries — the divisor for the per-beat length
    budget (P0-3). None when there is no plan, which makes length_directive fall
    back to the whole-chapter form, keeping the no-plan path byte-identical.

    Measured rationale: 4-beat chapters ran 5128 chars vs 5-beat 5305 (only 176
    apart) against a 3287 market p75 — the overshoot is per-beat verbosity, not
    beat count, so the model needs a PER-BEAT number it can hold while writing."""
    scenes = (scene_plan or {}).get("scenes") if isinstance(scene_plan, dict) else None
    return len(scenes) if scenes else None


@dataclass(frozen=True)
class ChapterSpec:
    """One planned chapter: the event it dramatizes + the seeds to build from."""
    index: int
    task_id: str
    event_id: str
    seeds: List[str]
    goal: str
    planning_source: Optional[dict] = None


@dataclass
class ChapterRun:
    spec: ChapterSpec
    ok: bool
    stage: str
    message: str = ""
    draft_hash: Optional[str] = None
    state_hash: Optional[str] = None
    open_setups: int = 0
    events_so_far: int = 0
    verdict: Optional[str] = None
    qa_scores: Optional[dict] = None    # judge's raw 18-dim scores (advisory);
                                        # None unless a scoring reviewer ran
    commercial_verdict: Optional[str] = None
    pacing: Optional[dict] = None       # intra-chapter emotion-curve check (advisory)
    pacing_peak: Optional[int] = None   # this chapter's climax height (peak valence)
    density: Optional[dict] = None      # single-chapter info-density check (advisory)
    ai_taste: Optional[dict] = None     # single-chapter AI-tell check (advisory)
    hygiene: Optional[dict] = None      # prose-hygiene correction session (advisory)
    end_hook: Optional[dict] = None     # single-chapter end-hook check (advisory)
    meta_reference: Optional[dict] = None  # narrative-layer leak check (advisory)
    integrity: Optional[dict] = None    # text-integrity gate result (hard gate)
    length: Optional[dict] = None       # single-chapter length-vs-target check (advisory)
    mandate: Optional[dict] = None      # single-chapter 温水章 check (advisory, Phase 9.3)
    m7: Optional[dict] = None            # M7 originality + red-line gate result (advisory)
    m7_approval_id: Optional[str] = None # approval request id when M7 held/blocked (ADR-009)
    llm_cost: Optional[dict] = None      # chapter-level real LLM cost fold
    llm_usage: Optional[dict] = None     # chapter-level real LLM token usage fold
    m5_final: Optional[dict] = None      # M5.1 chapter-production final artifact
    reference_gap: Optional[dict] = None # gap vs the M9 reference quality anchor (advisory)
    budget_note: Optional[str] = None    # M4-B4: per-chapter budget cap skipped an enhancer
    quality_snapshot: Optional[dict] = None
    w12: Optional[dict] = None           # W12 fact-candidate reflow summary (opt-in);
                                         # stages candidates + approval, never mints (ADR-009)
    contract_validation: Optional[dict] = None  # Phase 3.3: Contract Gate post-generation
                                                # validation result (advisory, v15 only)
    contract_revision_session: Optional[dict] = None  # Phase 3 Stage 2, Task 2.2: Candidate
                                                      # contract check + revision loop (advisory, v15 only)
    final_contract_validation: Optional[dict] = None  # P0-2: Final contract check after ALL
                                                      # modifications (revision+commercial+hygiene)
    production_card: Optional[dict] = None  # Stage A: Unified final-draft quality card
                                            # (contract, quality, reader, originality)
    quality_gate: Optional[dict] = None     # A.2: final-draft quality gate result (advisory,
                                            # ADR-003 — recorded, never blocks the serial)

    def to_dict(self) -> dict:
        return {
            "index": self.spec.index, "task_id": self.spec.task_id,
            "event": self.spec.event_id, "ok": self.ok, "stage": self.stage,
            "draft_hash": self.draft_hash, "state_hash": self.state_hash,
            "open_setups": self.open_setups, "events_so_far": self.events_so_far,
            "verdict": self.verdict, "qa_scores": self.qa_scores,
            "commercial_verdict": self.commercial_verdict,
            "pacing": self.pacing, "pacing_peak": self.pacing_peak,
            "density": self.density,
            "ai_taste": self.ai_taste,
            "hygiene": self.hygiene,
            "end_hook": self.end_hook,
            "meta_reference": self.meta_reference,
            "integrity": self.integrity,
            "length": self.length,
            "mandate": self.mandate,
            "m7": self.m7,
            "m7_approval_id": self.m7_approval_id,
            "llm_cost": self.llm_cost,
            "llm_usage": self.llm_usage,
            "m5_final": self.m5_final,
            "reference_gap": self.reference_gap,
            "budget_note": self.budget_note,
            "w12": self.w12,
            "contract_validation": self.contract_validation,
            "contract_revision_session": self.contract_revision_session,
            "final_contract_validation": self.final_contract_validation,
            "production_card": self.production_card,
            "quality_gate": self.quality_gate,
            "message": self.message,
        }


@dataclass
class SerialResult:
    reviewer: str
    gating: bool = False    # ADR-003 evaluative axis — the serial never gates
    chapters: List[ChapterRun] = field(default_factory=list)
    produced: int = 0
    skipped: int = 0
    final_state_hash: Optional[str] = None
    serial_pacing: Optional[dict] = None   # cross-chapter climax-rhythm check (advisory)
    serial_openings: Optional[dict] = None # cross-chapter 开篇雷同 check (advisory, §14 anti-AI)
    mandate_series: Optional[dict] = None  # cross-chapter 张力停滞/原地打转 check (advisory, Phase 9.3)
    function_repeat: Optional[dict] = None # cross-chapter 功能重复 check (advisory, W11-03)
    genre_drift: Optional[dict] = None     # cross-chapter 题材漂移 check (advisory, §4.3 退化梯度)
    packaging_delivery: Optional[dict] = None  # §3.3 包装承诺兑现 check (advisory)
    promise_ledger: Optional[dict] = None  # Stage B: Promise Ledger摘要 (advisory)
    llm_cost: Optional[dict] = None        # total real LLM cost fold
    llm_usage: Optional[dict] = None       # total real LLM token usage fold
    #: 有真实 LLM 调用却缺少定价时的告警文案(否则 None)。真花了钱但折不出
    #: 金额意味着预算熔断在那些调用上无效 —— 必须说出来,不能静默当成免费。
    cost_warning: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "produced": self.produced,
            "skipped": self.skipped,
            "final_state_hash": self.final_state_hash,
            "serial_pacing": self.serial_pacing,
            "serial_openings": self.serial_openings,
            "mandate_series": self.mandate_series,
            "function_repeat": self.function_repeat,
            "genre_drift": self.genre_drift,
            "packaging_delivery": self.packaging_delivery,
            "promise_ledger": self.promise_ledger,
            "llm_cost": self.llm_cost,
            "llm_usage": self.llm_usage,
            "cost_warning": self.cost_warning,
            "chapters": [c.to_dict() for c in self.chapters],
        }


def plan_chapters(reg) -> List[ChapterSpec]:
    """Derive a chapter plan from the fold-ordered event log (ADR-008): one
    chapter per event, in story order. Each chapter seeds from its event plus the
    characters participating in it, so the Task Package carries the right facts.
    Deterministic: same facts => same plan."""
    from ..memory.state import _ordered_event_ids
    specs: List[ChapterSpec] = []
    for i, eid in enumerate(_ordered_event_ids(reg.facts), start=1):
        rec = reg.get(eid) or {}
        participants = [p for p in (rec.get("participants") or [])
                        if isinstance(p, str) and p.startswith("CHR-")]
        seeds = [eid] + participants
        goal = f"draft chapter {i}: {rec.get('summary') or rec.get('name') or eid}"
        specs.append(ChapterSpec(index=i, task_id=f"TASK-{i:05d}",
                                 event_id=eid, seeds=seeds, goal=goal))
    return specs


def plan_continuation_from_rolling_plan(
    *, project_path: str | Path, reg, start_chapter: int,
) -> List[ChapterSpec]:
    """Build one 10-chapter continuation window from a rolling plan.

    The last minted event remains the Fact/state anchor. Rolling goals only
    supply task intent and provenance; this path never creates or mutates Facts.
    """
    if start_chapter <= 1 or (start_chapter - 1) % 10:
        raise ValueError(
            "rolling-plan continuation must start after a 10-chapter checkpoint")

    from ..memory.state import _ordered_event_ids
    from .rolling_plan import rolling_plan_source

    checkpoint_index = start_chapter - 1
    source = rolling_plan_source(project_path, checkpoint_index)
    if source is None:
        raise ValueError(
            f"missing rolling plan rolling-{checkpoint_index:03d}.json")

    event_ids = _ordered_event_ids(reg.facts)
    if not event_ids:
        raise ValueError(
            "rolling-plan continuation requires at least one minted Fact event")
    anchor_event = event_ids[-1]
    anchor = reg.get(anchor_event) or {}
    participants = [
        value for value in (anchor.get("participants") or [])
        if isinstance(value, str) and value.startswith("CHR-")
    ]
    seeds = [anchor_event] + participants
    goals = source["plan"].get("active_goals") or []
    by_chapter = {
        int(goal.get("chapter_no")): goal
        for goal in goals
        if isinstance(goal, dict) and str(goal.get("chapter_no", "")).isdigit()
    }
    expected = list(range(start_chapter, start_chapter + 10))
    missing = [index for index in expected if index not in by_chapter]
    if missing:
        raise ValueError(
            f"rolling plan {source['ref']} misses active chapters {missing}")

    source_public = {key: value for key, value in source.items() if key != "plan"}
    return [
        ChapterSpec(
            index=index,
            task_id=f"TASK-{index:05d}",
            event_id=anchor_event,
            seeds=list(seeds),
            goal=(f"draft chapter {index}: "
                  f"{str(by_chapter[index].get('active_goal') or '').strip()}"),
            planning_source={
                **source_public,
                "fact_state_anchor": anchor_event,
                "chapter_goal": by_chapter[index],
            },
        )
        for index in expected
    ]


def _load_continuation_context(project_path: Path, start_chapter: int) -> dict:
    """Load the persisted chapter context immediately preceding a resume."""
    bodies_by_chapter: dict[int, str] = {}
    for index in range(1, start_chapter):
        path = (project_path / "registry" / "derived" / "drafts"
                / f"TASK-{index:05d}.json")
        try:
            envelope = _json.loads(path.read_text(encoding="utf-8"))
            body = str((envelope.get("draft") or {}).get("body") or "")
        except (OSError, ValueError, AttributeError):
            continue
        if body:
            bodies_by_chapter[index] = body

    previous = start_chapter - 1
    mandate = None
    mandate_path = (
        project_path / "registry" / "derived" / "narrative-mandate"
        / f"mnd-TASK-{previous:05d}.json")
    try:
        mandate = _json.loads(mandate_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    quality_scores = None
    run_path = (project_path / "registry" / "derived" / "chapter-run"
                / f"run-TASK-{previous:05d}.json")
    try:
        run = _json.loads(run_path.read_text(encoding="utf-8"))
        scores = run.get("qa_scores")
        if isinstance(scores, dict) and scores:
            quality_scores = scores
    except (OSError, ValueError, AttributeError):
        pass
    return {
        "bodies_by_chapter": bodies_by_chapter,
        "recent_bodies": [bodies_by_chapter[i]
                          for i in sorted(bodies_by_chapter)[-3:]],
        "prev_mandate": mandate,
        "prev_quality_scores": quality_scores,
    }


def _candidate_score(ex) -> float:
    """Score a candidate ExecutionResult for director selection. Prefers the
    evaluative reviewer's overall (a scoring reviewer produces qa_review.scores);
    falls back to word_count when no scores exist (a deterministic reviewer), so
    a candidate set is always rankable. Higher is better; risk dims are not used
    here (the reviewer already folds them into its scores)."""
    scores = (ex.qa_review or {}).get("scores")
    if isinstance(scores, dict) and scores:
        nums = [v for v in scores.values() if isinstance(v, (int, float))]
        if nums:
            return sum(nums) / len(nums)
    return float((ex.artifact or {}).get("word_count", 0) or 0)


def _select_best_candidate(*, cand_models, package, standard_root, project_path,
                           prompt_runtime, prompt_version, reviewer, extra_vars,
                           chapter_ir_grounding, director_objective, director_brief,
                           target_wordcount, spec, project_derived,
                           scene_beats=None):
    """C6: generate one draft per candidate model (write=False so losers never
    clobber the draft artifact), score each, and use the REAL director
    compare/select machinery to pick the winner. Returns (winner_ExecutionResult,
    version_selection_dict, version_comparison_dict). The winner is re-executed
    with write=True so the persisted draft + envelope are exactly the single-draft
    path's output.

    A candidate that fails execution is dropped (never crashes the set). If every
    candidate fails, the first result is returned so the caller records the skip
    exactly as the single-draft path would. Never gates (ADR-003)."""
    from ..director import build_version_comparison, build_version_selection

    results = []
    for i, cm in enumerate(cand_models):
        ex_i = execute_package(
            package=package, standard_root=standard_root,
            project_path=project_path, model=cm, prompt_runtime=prompt_runtime,
            prompt_version=prompt_version, reviewer=reviewer,
            extra_prompt_variables=extra_vars, review_grounding=chapter_ir_grounding,
            director_objective=director_objective, director_brief=director_brief,
            target_wordcount=target_wordcount, scene_beats=scene_beats,
            chapter_no=spec.index,
            write=False)
        results.append((f"cand-{i}", ex_i))

    ok_results = [(vid, ex) for vid, ex in results if ex.ok and ex.artifact]
    if not ok_results:
        return results[0][1], None, None

    scores = {vid: _candidate_score(ex) for vid, ex in ok_results}
    versions = [{
        "version_id": vid,
        "text": (ex.artifact or {}).get("body", ""),
        "after_review": ex.qa_review or {},
        "director_score": scores[vid],
    } for vid, ex in ok_results]
    comparison = build_version_comparison(
        chapter_id=spec.task_id, versions=versions,
        objective=director_objective, brief=director_brief)
    winner_id = comparison.get("winner") or ok_results[0][0]
    winner_ex = next((ex for vid, ex in ok_results if vid == winner_id),
                     ok_results[0][1])
    # cite the actual per-candidate scores so the selection is auditable without
    # re-deriving them (the comparison is persisted alongside, but the reason is
    # self-contained). Stable order: candidate index.
    score_str = ", ".join(f"{vid}={scores[vid]:.2f}"
                          for vid, _ in ok_results)
    selection = build_version_selection(
        chapter_id=spec.task_id, comparison=comparison,
        selected_version=winner_id,
        reason=(f"highest reviewer score among {len(ok_results)} candidates "
                f"({score_str}); winner={winner_id}"))

    # Return the already-generated winner artifact instead of executing the
    # winner again. A second live pass can drift from the selected candidate
    # even when the prompt is semantically identical, so persisting the first
    # winner keeps selection and output aligned.
    return winner_ex, selection, comparison


def run_serial(
    *,
    project_path: str | Path,
    standard_root: str | Path,
    schema_dir: str | Path,
    out_dir: str | Path,
    model=None,
    reviewer=None,
    prompt_runtime=None,
    simulator=None,
    rewrite_model=None,
    commercial_rounds: int = 2,
    prompt_version: str = "1.0.0",
    max_chapters: Optional[int] = None,
    start_chapter: int = 1,
    rolling_plan_continuation: bool = False,
    max_depth: int = 2,
    reviewer_id: str = "serial-v1",
    outline: Optional[dict] = None,
    scene_planner_model=None,
    psych_beats: bool = False,
    hygiene_model=None,
    hygiene_rounds: int = 2,
    redline_ruleset=None,
    originality_references: Optional[List[dict]] = None,
    approval_queue=None,
    budget_limit: Optional[float] = None,
    per_chapter_budget: Optional[float] = None,
    candidate_models: Optional[List] = None,
    w12_extract: bool = False,
    w12_model=None,
    consumption_by_chapter: Optional[dict] = None,
    contracts_dir: Optional[str | Path] = None,
    enable_contract_gate: bool = False,
    strict_contract_mode: bool = False,
    contract_revision_rounds: int = 2,
    enable_final_quality_review: bool = False,
    final_review_threshold: str = "always",
    final_review_model=None,
    enable_final_reader_simulation: bool = False,
    final_reader_threshold: str = "always",
    final_reader_sim_model=None,
) -> SerialResult:
    """Run the production chain over a planned chapter sequence, carrying state
    (as a fold cursor) between chapters. Never gates the serial (ADR-003).

    If both `simulator` and `rewrite_model` are given, each chapter additionally
    runs the Commercial Optimization Loop (P16): the reader-preferred draft is
    re-gated deterministically and, if it passes, written back over the initial
    draft with its commercial_session on the envelope. This is COMPARISON-ONLY
    and never gates the serial; when the pair is absent the loop is skipped and
    the per-chapter draft is byte-identical to the non-commercial run.

    `prompt_version` selects the chapter-draft template. With the v2 template
    ("2.0.0") the Prompt Orchestrator feeds each chapter a compact "story so far"
    recap (state_digest of the fold up to the PREVIOUS chapter's event), so the
    model sees the accumulated state a long serial can't fit whole. v1 ("1.0.0",
    the default) takes no story_state and is byte-identical to before this wiring.

    With the v3 template ("3.0.0") the Scene DSL layer additionally feeds each
    chapter a rendered beat skeleton: `plan_scenes` folds the chapter's outline
    intent (`outline["first_30_chapters"][chapter_no]`, passed via `outline`) and
    its event participants into an ordered scene plan. When `outline` is absent or
    has no entry for a chapter, the plan degrades to the chapter goal — advisory,
    never a gate (ADR-003). v1/v2 ignore `outline` entirely and stay byte-identical.

    With the v4 template ("4.0.0", Phase 4.2 Narrative IR) the compiler gains an
    executable middle layer: each chapter is folded into a Chapter IR
    (chapter-ir.schema.json) — chapter intent + payoff_target + per-beat narrative
    operations (turning_point/emotion_shift/information_gain/reader_question/
    exit_hook) — and the scene plan is LOWERED from that IR rather than folded
    directly from the outline, so the two artifacts can never disagree. The IR is
    persisted (registry/derived/chapter-ir/) and rendered into the prompt beside
    the scene plan; its payoff_target grounds the reviewer's promise_delivery
    score. v4 degrades to the chapter goal without an outline and never gates.

    With the v5 template ("5.0.0", Phase 4.3 Character Runtime) each chapter
    additionally gets a per-LEAD CHARACTER RUNTIME projected from the facts up to
    the PREVIOUS chapter's event (the leads' standing as they enter the chapter):
    goal / pressure / secret / fear / desire / relationship_tension / growth_stage
    / next_likely_action. It is a projection (ADR-008), never mutable state; it is
    persisted (registry/derived/character-runtime/) and rendered into the prompt so
    each lead's behavior stays continuous across chapters. v5 does everything v4
    does plus this; it degrades to empty leads without facts and never gates.

    With the v15 template ("15.0.0", Phase 3 Contract Gate) each chapter is
    verified against an AUTHORED CONTRACT before generation begins. When
    `enable_contract_gate` is True and prompt_version is "15.0.0", the precheck
    verifies the chapter has a valid, approved contract file (chapter_N_contract.json)
    before building the task package. Chapters without valid contracts are SKIPPED
    (ADR-003: orchestration never kills the serial). In strict_contract_mode, a
    contract failure raises; in non-strict (default), it skips and continues.
    When contracts_dir is absent, defaults to project_path/contracts.

    Additionally, with Contract Gate enabled and `rewrite_model` provided, the
    generated Candidate is checked against the contract BEFORE finalization. If
    critical issues are found (location mismatch, missing hook consumption, missing
    required characters), a revision loop is triggered (max `contract_revision_rounds`
    rounds, default 2). The revision loop uses the contract check's suggestions to
    guide targeted rewrites. This is ADVISORY and never gates (ADR-003): even if
    revision fails after max rounds, the best draft (fewest critical issues) is kept
    and the chapter proceeds. The revision session is recorded in
    `contract_revision_session` on the ChapterRun for audit.

    `scene_planner_model` (v3/v4/v5, optional) is an LLM that ENRICHES each scene
    plan with pov / emotion / within-scene micro-beats, inside the deterministic
    skeleton (it may add detail, never change structure). On any failure it
    degrades to the bare skeleton; absent, the skeleton is used as-is.
    """
    project_path = Path(project_path)
    reg = registry_loader.load(project_path)
    if rolling_plan_continuation:
        specs = plan_continuation_from_rolling_plan(
            project_path=project_path, reg=reg, start_chapter=start_chapter)
    else:
        specs = plan_chapters(reg)
        if start_chapter > 1:
            specs = [spec for spec in specs if spec.index >= start_chapter]
    if max_chapters is not None:
        specs = specs[:max_chapters]

    result = SerialResult(reviewer=reviewer_id)
    last_state_hash: Optional[str] = None
    prev_event_id: Optional[str] = (
        specs[0].event_id if rolling_plan_continuation and specs else None)
    total_llm_cost = 0.0
    # 跨全程累计"有真实调用却没有定价"的次数。此前所有折叠点都写
    # `float(cst.get("total_cost", 0) or 0)`,把 None 静默折成 0 —— 于是未定价
    # 模型的真实花费被当成免费,total_llm_cost 永远是 0,--budget-limit 永不触发。
    # 已发生两次(deepseek-chat、92code:gpt-5.6-sol),后者在零预算保护下跑掉 18 元。
    # 这里只让它**可见**:确定性 stub 跑仍然 cost=null(不伪造),但真实调用缺价
    # 会被数出来并在收尾告警。
    cost_fold = CostFold()
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_cost_currency = None
    total_cost_pricing_version = None

    # The M5 orchestrator operates on ChapterDraft objects via
    # ChapterReviewer.review(draft), a DIFFERENT seam from the DraftReviewer
    # protocol (review(artifact, package)) that execute_package uses below.
    # Forcing the passed DraftReviewer into the orchestrator broke the default
    # path with `TypeError: review() takes 2 positional arguments but 3 were
    # given` (ChapterReviewer.review takes only (self, draft)). The evaluative
    # reviewer must flow ONLY into execute_package/reviewer, never here.
    chapter_pipeline = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
    # Narrative Mandate (Phase 9): the previous chapter's mandate, folded into
    # the next (escalation.from_level = prev to_level, inner_shift.from = prev to).
    # None on the opening chapter => the mandate degrades to base tension levels.
    continuation_context = (
        _load_continuation_context(project_path, start_chapter)
        if rolling_plan_continuation else {})
    prev_mandate: Optional[dict] = continuation_context.get("prev_mandate")
    mandates: List[dict] = []   # produced mandates, folded for the cross-chapter series check
    chapter_bodies: List[str] = list(continuation_context.get("recent_bodies") or [])
    # Same bodies keyed by REAL chapter number (spec.index), for checks that must
    # know which chapter a body is — the packaging promise-delivery window is
    # "by chapter N". A flat list index cannot answer that: --start-chapter skips
    # chapters, so bodies[0] is not necessarily chapter 1.
    bodies_by_chapter: dict = dict(continuation_context.get("bodies_by_chapter") or {})
    function_sigs: List[dict] = []  # per-chapter {objective,mandate,chapter_id}, folded for W11-03 function-repeat check
    # Previous chapter's quality scores, carried to derive THIS chapter's verdict
    # (regressed/degraded) — the cross-chapter fold the director feedback reads.
    # None until a scoring reviewer (llm-quality/panel) first produces scores.
    prev_quality_scores: Optional[dict] = continuation_context.get("prev_quality_scores")

    # M7 approval sequence: when a chapter's M7 assessment recommends hold/block
    # (L2/L3 originality risk or a hard red-line), we enqueue a review request on
    # the supplied ApprovalQueue (ADR-009: a human executes the publish transition;
    # the serial itself NEVER gates — ADR-003). Counter is run-local; the request
    # id embeds the chapter task_id so it is stable and idempotent per chapter.
    m7_approval_seq = 0

    # Character Speech Profiles (roadmap §15): authored per-character voice spec,
    # loaded ONCE and indexed by character_id. Absent/pristine => empty index =>
    # no language block injected => v7 degrades to v6 behavior. READ only; the
    # speech subdomain never writes facts and imports no model (guard #22).
    from ..speech import (load_speech, speech_profiles_by_id,
                          render_speech_profiles)
    speech_by_id = speech_profiles_by_id(load_speech(project_path))

    # Target chapter length (A.3): the outline's market_position declares
    # target_wordcount_per_chapter; read it ONCE and thread it into generation so
    # the model writes to a consistent length (the real run swung 1773→5766 with
    # no constraint). Absent outline / field => None => no length directive, so
    # generation is byte-identical to before this wiring.
    target_wordcount = None
    if outline:
        twc = (outline.get("market_position") or {}).get("target_wordcount_per_chapter")
        if isinstance(twc, int) and twc > 0:
            target_wordcount = twc

    # Long-Arc Plan (M3): project the outline's volume/power/conflict skeleton
    # into per-chapter long-arc coordinates ONCE for the whole run (it is constant
    # given the outline). v10 renders each chapter's coordinate into the prompt so
    # long-range rhythm (volume climax / power progression / paywall) holds. Built
    # only on the v10 path; a pure deterministic fold, never gates (ADR-003).
    long_arc_plan = None
    if _at_least(prompt_version.split(".", 1)[0], 10):
        from ..arc import project_long_arc
        long_arc_plan = project_long_arc(outline)

    # Novel Brain, loaded ONCE for the two consumers that read the AUTHORED
    # coinages out of it: the per-chapter genre contract (v14) and the end-of-run
    # genre-drift fold. Loaded unconditionally rather than behind the v14 gate —
    # the drift fold runs on EVERY version, so gating this would silently weaken
    # the detector on a v13 run. One small yaml read per run; the Brain is constant
    # for the run, so a per-chapter load would be pure waste. Absent => None =>
    # both paths degrade to the outline alone.
    from ..brain import load_brain as _load_brain_for_genre
    genre_brain = _load_brain_for_genre(project_path)

    # Promise Ledger (Stage B): unified承诺追踪 across packaging + narrative setups +
    # plot threads. Loaded ONCE for the run; the ledger is projected from packaging +
    # registry facts. When present, promises are injected into chapter objectives to
    # guide generation. Advisory only (ADR-003): never gates, only informs. Absent
    # packaging or no promises => empty ledger => no injection, so behavior degrades
    # cleanly to pre-Promise runs. Read-only projection (ADR-006/008).
    promise_ledger = None
    try:
        from ..packaging import load_packaging
        from ..promise import project_promise_ledger
        packaging = load_packaging(project_path)
        if packaging:
            promise_ledger = project_promise_ledger(reg, packaging)
            import logging
            logging.info(f"Promise Ledger loaded: {len(promise_ledger.promises)} promises")
    except Exception as e:
        # Graceful degradation: if Promise Ledger fails, continue without it
        import logging
        logging.warning(f"Promise Ledger loading failed: {type(e).__name__}: {e}")
        pass

    # Reference Quality Anchor (M9): the pinned per-feature market-validated band
    # profile, loaded ONCE (it is a static derived artifact). Each chapter's body
    # is later measured against it into a gap read persisted on the ChapterRun,
    # so per-chapter distance from a market winner is auditable after the run
    # (not only recomputed on-the-fly by the dashboard). Absent => None => no gap,
    # a clean skip. Deterministic; comparison-only, never gates (ADR-003).
    from ..reference import load_reference_profile
    reference_profile = load_reference_profile(project_path)

    # P0-3: Track consumed events and state hashes to detect anomalies.
    # These are advisory checks: detection does not gate the run (ADR-003),
    # but warnings help diagnose incomplete checkpoints or projection failures.
    consumed_events = set()
    prev_state_hash: Optional[str] = None

    for spec in specs:
        # D180-05: the layered breaker (cost_breaker.check_budget) is the single
        # decision point for "may this run keep paying a provider". It replaces a
        # hand-rolled `spent >= limit` compare here; the semantics are identical
        # (limit None => never tripped), so a run without --budget-limit is
        # byte-identical to before. The breaker is a hard stop on BILLING, which is
        # not an ADR-003 quality gate: it bounds spend, it never judges the prose.
        if _breaker_tripped(project_limit=budget_limit, project_spent=total_llm_cost):
            result.chapters.append(ChapterRun(
                spec=spec, ok=False, stage="budget-held",
                message=(f"live LLM budget {budget_limit:.2f} reached; "
                         "remaining chapters were not started"),
            ))
            result.skipped += 1
            continue

        # --- Contract Gate precheck (Phase 3, v15 only) --------------------------
        # When enable_contract_gate is True and using prompt v15, verify the chapter
        # has an approved contract BEFORE building the task package. This is the
        # precheck gate: no contract => skip this chapter (ADR-003: orchestration
        # never kills the serial, but MAY skip individual chapters). In strict mode
        # a contract failure raises; in non-strict it skips and continues.
        # After precheck succeeds, load the contract and prepare it for injection
        # into the chapter prompt (the actual injection happens in extra_vars below).
        loaded_contract = None
        if enable_contract_gate and prompt_version == "15.0.0":
            from pathlib import Path as _ContractPath
            # Lazy import to avoid loading Contract Gate when not needed
            import sys
            contract_plugin_path = _ContractPath(__file__).parent.parent.parent.parent / 'runtime_plugins'
            if str(contract_plugin_path) not in sys.path:
                sys.path.insert(0, str(contract_plugin_path))

            try:
                from runtime_plugins.contract import ContractGate, ContractCheckError

                _contracts_dir = _ContractPath(contracts_dir) if contracts_dir else project_path / "contracts"
                _schemas_dir = _ContractPath(schema_dir)
                gate = ContractGate(
                    contracts_dir=_contracts_dir,
                    schemas_dir=_schemas_dir,
                    strict_mode=strict_contract_mode,
                )

                # Precheck: verify contract exists, is valid, and approved
                gate.precheck(spec.index)

                # Chain validation: verify continuity with previous contract
                # (only for chapter 2+, since chapter 1 has no predecessor)
                if spec.index > 1:
                    try:
                        chain_result = gate.validate_chain(spec.index - 1, spec.index)
                        if not chain_result["valid"]:
                            issues = chain_result.get("issues", [])
                            issue_summary = "; ".join(
                                f"{issue['field']}: {issue['description']}"
                                for issue in issues[:3]  # Show first 3 issues
                            )
                            if strict_contract_mode:
                                raise ContractCheckError(
                                    f"Ch{spec.index} contract chain validation failed: {issue_summary}"
                                )
                            else:
                                # Non-strict: log warning but continue
                                import logging
                                logging.warning(
                                    f"Ch{spec.index} contract chain validation failed "
                                    f"({len(issues)} issues): {issue_summary}"
                                )
                                print(f"  [warn] ch {spec.index:>2} contract chain: "
                                      f"{len(issues)} issues")
                    except FileNotFoundError:
                        # Previous contract missing - already handled by its own precheck
                        pass

                # Load the contract for injection into the prompt
                contract_dict = gate.load_contract(spec.index)

                # Render contract into a formatted string that will be injected into the prompt
                # This uses the same inject_contract logic but extracts just the contract section
                loaded_contract = gate.inject_contract("", contract_dict).strip()

            except Exception as e:
                # Import succeeded, check if it's a ContractCheckError
                from runtime_plugins.contract import ContractCheckError as _CCE
                if isinstance(e, _CCE):
                    # Contract check failed
                    if strict_contract_mode:
                        raise
                    else:
                        result.chapters.append(ChapterRun(
                            spec=spec, ok=False, stage="contract-check-failed",
                            message=f"Contract Gate precheck failed: {e}",
                        ))
                        result.skipped += 1
                        print(f"  [skip] ch {spec.index:>2} {spec.event_id} "
                              f"stage=contract-check-failed  {e}")
                        continue
                else:
                    # Unexpected error in Contract Gate setup
                    if strict_contract_mode:
                        raise
                    else:
                        result.chapters.append(ChapterRun(
                            spec=spec, ok=False, stage="contract-gate-error",
                            message=f"Contract Gate error: {type(e).__name__}: {e}",
                        ))
                        result.skipped += 1
                        print(f"  [skip] ch {spec.index:>2} {spec.event_id} "
                              f"stage=contract-gate-error  {type(e).__name__}")
                        continue
        # --- build the Task Package for this chapter -------------------------
        from ..pipeline import build_task_package
        build = build_task_package(
            project_path=project_path, schema_dir=schema_dir,
            task=compiler.TaskDefinition(
                spec.task_id, spec.goal, "ChapterDraft", list(spec.seeds),
                extra=({"planning_source": getattr(spec, "planning_source", None)}
                       if getattr(spec, "planning_source", None) else {})),
            out_dir=out_dir, standard_root=standard_root, max_depth=max_depth)
        if not build.ok:
            result.skipped += 1
            result.chapters.append(ChapterRun(
                spec=spec, ok=False, stage=f"build:{build.stage}",
                message=build.message))
            continue

        # --- Prompt Orchestrator: feed "story so far" when using the v2 prompt.
        # The recap is the fold up to the PREVIOUS chapter's event (state at the
        # start of THIS chapter), digested into a compact string. v1 gets nothing,
        # so its render is byte-identical to before this wiring.
        extra_vars = None
        scene_plan_obj = None
        cr = None                     # v5+: per-lead character runtime (computed before enrich)
        chapter_ir_grounding = None   # v4: IR payoff_target grounds promise_delivery
        director_objective = None     # v6: fed to the DirectorSession (Phase 7.2)
        director_brief = None
        mandate = None                # v8: the narrative mandate (Phase 9)
        major = prompt_version.split(".", 1)[0]
        if major != "1":
            from ..memory.state import state_digest
            if prev_event_id is None:
                # first chapter — no prior events have happened yet (开篇)
                digest = "（暂无前情，本章为开篇）"
            else:
                prior = project_state(reg, up_to_event=prev_event_id)
                digest = state_digest(prior)
            extra_vars = {"story_state": digest}

            # --- Contract Gate injection (v15 only, Phase 3) ---------------------
            # If a contract was loaded during precheck, inject it into extra_vars
            # so it reaches the chapter-draft v15.0.0 prompt template. The contract
            # contains the authored entry/exit requirements and chapter intent that
            # the model MUST honor. v15 template declares chapter_contract as a
            # required variable, so this must be bound for v15 runs. For non-v15 or
            # when Contract Gate is disabled, this variable is not bound (v1-v14
            # templates don't declare it, so they stay byte-identical).
            if _at_least(major, 15) and loaded_contract is not None:
                extra_vars["chapter_contract"] = loaded_contract

            # --- P0-3: Load actual exit state from previous chapter --------------
            # The actual exit state (extracted from the FINAL text of chapter N-1)
            # is the REAL entry point for chapter N, not the planned entry from the
            # contract. This closes the state-driven feedback loop: planned → actual
            # → next chapter uses actual. When no actual exit exists (chapter 1, or
            # a resumed run without prior extraction), degrades to the contract's
            # planned entry, so v15 behavior stays consistent.
            if _at_least(major, 15) and enable_contract_gate and spec.index > 1:
                from pathlib import Path as _ActualExitPath
                try:
                    # Load the actual exit state from the previous chapter
                    prev_task_id = f"TASK-{(spec.index - 1):05d}"
                    exit_path = (
                        project_path / "registry" / "derived" / "chapter-exit-state"
                        / f"exit-{prev_task_id}.json"
                    )
                    if exit_path.exists():
                        import json as _exit_json
                        actual_exit = _exit_json.loads(exit_path.read_text(encoding="utf-8"))
                        # Render the actual exit into a prompt-friendly format
                        # This tells the model: "The previous chapter ACTUALLY ended with..."
                        # rather than "The contract PLANNED for it to end with..."
                        exit_summary = []
                        confidence_notes = []

                        # Confidence threshold for using extracted values
                        CONFIDENCE_THRESHOLD = 0.5

                        # Prefer the canonical fields emitted by
                        # ContractGate.extract_actual_exit_state; accept the
                        # earlier aliases so persisted P0 prototype artifacts
                        # remain resumable.
                        location = (actual_exit.get("location_id") or
                                    actual_exit.get("location"))
                        location_conf = actual_exit.get("location_confidence", 0.6)

                        characters = (actual_exit.get("characters_present") or
                                      actual_exit.get("present_characters") or [])
                        characters_conf = actual_exit.get("characters_confidence", 0.6)

                        hook = (actual_exit.get("hook_promise") or
                                actual_exit.get("active_hooks") or [])
                        hook_conf = actual_exit.get("hook_confidence", 0.6)

                        unfinished = (actual_exit.get("unfinished_action") or
                                      actual_exit.get("plot_threads") or [])
                        unfinished_conf = actual_exit.get("unfinished_action_confidence", 0.6)

                        emotional_state = actual_exit.get("emotional_state")
                        emotional_conf = actual_exit.get("emotional_confidence", 0.6)

                        # Only high-confidence fields may override the planned
                        # entry. Low-confidence guesses remain auditable in the
                        # artifact, but must not become generation instructions.
                        if location:
                            if location_conf < CONFIDENCE_THRESHOLD:
                                confidence_notes.append(
                                    f"地点提取置信度较低 ({location_conf:.2f})，沿用契约计划")
                            else:
                                exit_summary.append(f"地点：{location}")

                        if characters:
                            chars = ", ".join(map(str, characters))
                            if characters_conf < CONFIDENCE_THRESHOLD:
                                confidence_notes.append(
                                    f"人物提取置信度较低 ({characters_conf:.2f})，沿用契约计划")
                            else:
                                exit_summary.append(f"在场人物：{chars}")

                        if hook:
                            hooks = ", ".join(map(str, hook)) if isinstance(hook, list) else str(hook)
                            if hook_conf < CONFIDENCE_THRESHOLD:
                                confidence_notes.append(
                                    f"钩子提取置信度较低 ({hook_conf:.2f})，沿用契约计划")
                            else:
                                exit_summary.append(f"悬念钩子：{hooks}")

                        if emotional_state:
                            if emotional_conf < CONFIDENCE_THRESHOLD:
                                confidence_notes.append(
                                    f"情绪提取置信度较低 ({emotional_conf:.2f})，沿用契约计划")
                            else:
                                exit_summary.append(f"情绪基调：{emotional_state}")

                        if unfinished:
                            threads = (", ".join(map(str, unfinished))
                                       if isinstance(unfinished, list) else str(unfinished))
                            if unfinished_conf < CONFIDENCE_THRESHOLD:
                                confidence_notes.append(
                                    f"未完成动作提取置信度较低 ({unfinished_conf:.2f})，沿用契约计划")
                            else:
                                exit_summary.append(f"未完成动作：{threads}")

                        overall_conf = actual_exit.get("overall_confidence")
                        if overall_conf is not None and overall_conf < CONFIDENCE_THRESHOLD:
                            confidence_notes.append(
                                f"整体提取置信度较低 ({overall_conf:.2f})，未确认字段不得覆盖契约"
                            )

                        actual_entry_context = ""
                        if exit_summary or confidence_notes:
                            actual_entry_context = "【上一章实际结局状态】"
                            if exit_summary:
                                actual_entry_context += "\n" + "\n".join(exit_summary)
                            if confidence_notes:
                                actual_entry_context += (
                                    "\n\n【低置信度字段处理】\n" +
                                    "\n".join(f"- {note}" for note in confidence_notes)
                                )
                            if exit_summary:
                                actual_entry_context += (
                                    "\n\n仅对以上已确认字段，本章应该从这个实际状态开始并优先于契约计划；"
                                    "未确认字段继续遵循契约。"
                                )
                            else:
                                actual_entry_context += "\n\n本章入口完全遵循契约计划。"

                        extra_vars["actual_entry_state"] = actual_entry_context
                    else:
                        # No actual exit found - degrade to empty (contract takes precedence)
                        extra_vars["actual_entry_state"] = ""
                except Exception as exc:
                    # Loading actual exit is advisory - log but don't break
                    import logging
                    logging.warning(f"Ch{spec.index} Failed to load actual exit state: "
                                    f"{type(exc).__name__}: {exc}")
                    extra_vars["actual_entry_state"] = ""
            elif _at_least(major, 15):
                # v15 but not using contract gate, or chapter 1 - bind empty so template doesn't break
                extra_vars["actual_entry_state"] = ""

            # --- Scene DSL layer (v3) / Narrative IR (v4): give the drafter a
            # paced structure instead of a single goal line. Both degrade to the
            # chapter goal when no outline entry exists and NEVER gate (ADR-003);
            # provenance pins are inherited from the package the chapter was built
            # from (staleness for free). The production compiler layers are:
            #   v3:  outline -> scene-plan            -> prompt
            #   v4:  outline -> chapter-ir -> scene-plan (lowered) -> prompt
            #   v5:  v4 + a per-lead character runtime (goal/pressure/next action)
            if _at_least(major, 3):
                from ..scene import render_scene_plan
                participants = [s for s in spec.seeds if s.startswith("CHR-")]
                prov = build.package.get("provenance", {})
                derived_from = list(prov.get("derived_from", []))
                source_version = prov.get("source_version", reg.version)

                if _at_least(major, 4):
                    # v4/v5/v6/v7: build the Chapter IR, then LOWER it into the scene plan
                    # (one scene per beat). The scene plan is downstream of the IR,
                    # so the two can never disagree on the chapter's beats. The IR
                    # also declares the payoff_target that grounds promise_delivery.
                    from ..scene import build_chapter_ir, lower_to_scene_plan, render_chapter_ir
                    # long-arc coordinate (when projected, v10 path) shifts the IR
                    # beat valences by the chapter's position in the authored arc so
                    # the cross-chapter peak tracks the arc, not a flat 75-75-85 loop
                    # (N100-072). None on non-v10 => byte-identical fold.
                    long_arc_coord = (long_arc_plan.chapter(spec.index)
                                      if long_arc_plan is not None else None)
                    ir = build_chapter_ir(
                        task_id=spec.task_id, chapter_no=spec.index, goal=spec.goal,
                        participants=participants, derived_from=derived_from,
                        source_version=source_version, outline=outline,
                        long_arc_coord=long_arc_coord)
                    plan = lower_to_scene_plan(ir)
                    # The IR's payoff_target grounds the reviewer's promise_delivery
                    # score (Phase 4.2): promise is STATED, not guessed. Absent for
                    # a pure setup chapter => ungrounded fallback.
                    chapter_ir_grounding = ir.get("payoff_target")
                    extra_vars["chapter_ir"] = render_chapter_ir(ir)
                    # Persist the IR as a Derived artifact — its declared home is
                    # registry/derived/chapter-ir/. "ir-" prefixed id so it does
                    # not clobber the draft (task_id) or scene plan ("scene-").
                    derived.write_artifact(
                        project_path=project_path, category="chapter-ir",
                        artifact_id=f"ir-{spec.task_id}", artifact=ir,
                        serialized=_json.dumps(ir, ensure_ascii=False, indent=2) + "\n")
                else:
                    # v3: fold the outline intent straight into a beat skeleton.
                    from ..scene import plan_scenes
                    plan = plan_scenes(
                        task_id=spec.task_id, chapter_no=spec.index, goal=spec.goal,
                        participants=participants, derived_from=derived_from,
                        source_version=source_version, outline=outline)

                # Optional LLM enrichment: fills pov/emotion/beats_within INSIDE
                # the deterministic skeleton. On failure it degrades to the
                # skeleton (advisory, never gates). Absent model => bare skeleton,
                # byte-identical to before this wiring.
                #
                # psych_beats (the §12.1 ② follow-up experiment): when on, project
                # the character runtime NOW (it's a pure deterministic fold, cheap)
                # and hand its rendered psych block to enrich, so the model lands
                # each lead's standing inner state as concrete in-scene ACTIONS
                # inside beats_within — testing whether a beat (instructing the
                # action a state causes) moves character quality where a static
                # prompt block did not. cr is reused by the block below (not
                # recomputed). Off => generic enrich, byte-identical.
                if scene_planner_model is not None:
                    from ..scene.llm_planner import LLMScenePlanner
                    psych_render = ""
                    if psych_beats and _at_least(major, 5):
                        from ..memory import (project_character_runtime,
                                              render_character_runtime)
                        cr = project_character_runtime(
                            reg, chapter_no=spec.index, task_id=spec.task_id,
                            up_to_event=prev_event_id, outline=outline,
                            derived_from=derived_from, source_version=source_version)
                        psych_render = render_character_runtime(cr)
                    plan = LLMScenePlanner(scene_planner_model).enrich(
                        plan, psych=psych_render)
                scene_plan_obj = plan
                extra_vars["scene_plan"] = render_scene_plan(plan)

                # Persist the scene plan as a Derived artifact (its declared home
                # registry/derived/scene-plan/), so read-side consumers (the
                # dashboard's pacing view) can fold it. "scene-" prefixed id.
                derived.write_artifact(
                    project_path=project_path, category="scene-plan",
                    artifact_id=f"scene-{spec.task_id}", artifact=plan,
                    serialized=_json.dumps(plan, ensure_ascii=False, indent=2) + "\n")

                # --- Character Runtime (v5 only, Phase 4.3): project each LEAD's
                # standing as they ENTER this chapter — folded from facts up to the
                # PREVIOUS chapter's event (prev_event_id), same cursor as the
                # "story so far" recap. This is a projection (ADR-008), never mutable
                # state; it keeps each lead's behavior CONTINUOUS (they act from a
                # standing goal + pressure). Persisted (cr- prefix) and rendered into
                # the prompt. Degrades cleanly (empty leads) and never gates (ADR-003).
                if _at_least(major, 5):
                    from ..memory import (project_character_runtime,
                                          render_character_runtime)
                    # Reuse cr if the psych-beats path already projected it above
                    # (same inputs => same deterministic fold); else project now.
                    if cr is None:
                        cr = project_character_runtime(
                            reg, chapter_no=spec.index, task_id=spec.task_id,
                            up_to_event=prev_event_id, outline=outline,
                            derived_from=derived_from, source_version=source_version)
                    extra_vars["character_runtime"] = render_character_runtime(cr)
                    derived.write_artifact(
                        project_path=project_path, category="character-runtime",
                        artifact_id=f"cr-{spec.task_id}", artifact=cr,
                        serialized=_json.dumps(cr, ensure_ascii=False, indent=2) + "\n")

                # --- Narrative Mandate (v8 only, Phase 9): fold the cross-chapter
                # mandate ABOVE the director objective — why THIS chapter must
                # happen now, how far the conflict escalates vs the previous
                # chapter, how the protagonist changes inside, what irreversible
                # advance it commits. A projection (ADR-008), not mutable state:
                # escalation.from_level folds from the PREVIOUS mandate's to_level,
                # inner_shift.from from its `to`. Persisted (mnd- prefix) and
                # rendered into the prompt; it CONSTRAINS the objective built
                # below (mandate= param). Degrades cleanly on the opening chapter
                # (no prev mandate => base levels) and never gates (ADR-003).
                if _at_least(major, 8):
                    from ..director import (project_narrative_mandate,
                                            render_narrative_mandate)
                    mandate = project_narrative_mandate(
                        chapter_no=spec.index, task_id=spec.task_id,
                        outline=outline, prev_mandate=prev_mandate,
                        derived_from=derived_from, source_version=source_version)
                    extra_vars["narrative_mandate"] = render_narrative_mandate(mandate)
                    derived.write_artifact(
                        project_path=project_path, category="narrative-mandate",
                        artifact_id=f"mnd-{spec.task_id}", artifact=mandate,
                        serialized=_json.dumps(mandate, ensure_ascii=False, indent=2) + "\n")
                    prev_mandate = mandate

                # --- Narrative Director (v6 only, Phase 7.1): fold a ChapterObjective
                # + DirectorBrief and render them into the prompt. The director sits
                # ABOVE the IR: the objective is the chapter's top-level intent (what
                # it must accomplish for story + retention + commercial pull), the IR
                # is HOW to execute it. Both are folded from what the loop already has
                # (the IR, the outline entry, the fold cursor) — the director invents
                # no new model here; generation stays behind the Model seam. Persisted
                # (obj-/dbr- prefixes) as derived artifacts. The objective/brief NEVER
                # gate (ADR-003, gating=false) and are advisory production intent;
                # absent an outline the IR degrades and the objective degrades with it.
                if _at_least(major, 6):
                    from ..director import (build_chapter_objective, render_chapter_objective,
                                            build_director_brief, render_director_brief,
                                            build_director_feedback, prev_run_signals)
                    # `ir` exists here because major in ("4","5","6") built it above.
                    ir_ctx = {
                        "id": ir.get("id"),
                        "primary_goal": ir.get("intent"),
                        "reader_question": ir.get("dramatic_question"),
                        "payoff_target": [ir["payoff_target"]["promise"]]
                            if isinstance(ir.get("payoff_target"), dict)
                            and ir["payoff_target"].get("promise") else [],
                        "notes": "",
                    }
                    # --- Cross-chapter feedback (Phase 7.3): shape THIS chapter's
                    # commercial intent from the PREVIOUS chapter's realized signals
                    # (quality verdict / commercial verdict / pacing curve / setup
                    # backlog). A pure deterministic fold: with NO adverse signal it
                    # returns the SAME defaults build_chapter_objective already uses,
                    # so a plain deterministic serial is byte-identical with or
                    # without feedback. It only diverges the objective when a REAL
                    # adverse signal appeared. Advisory, never gates (ADR-003); it
                    # touches prose intent only, so the state fold is unaffected.
                    feedback = build_director_feedback(
                        prev_run_signals(result.chapters[-1]) if result.chapters else None)
                    director_objective = build_chapter_objective(
                        chapter_id=spec.task_id, narrative_ir=ir_ctx,
                        state={"state_hash": last_state_hash} if last_state_hash else None,
                        commercial=feedback, mandate=mandate,
                        objective_id=f"OBJ-{spec.index:05d}")

                    # --- Promise Ledger injection (Stage B.3): inject承诺 into objective
                    # When Promise Ledger is available, inject relevant promises (pending +
                    # overdue) into the objective. This guides generation toward delivering
                    # promises. Advisory only (ADR-003): adds fields but never gates. If
                    # ledger is absent or has no relevant promises, the objective is unchanged.
                    if promise_ledger:
                        try:
                            from ..promise import inject_promises_into_objective
                            director_objective = inject_promises_into_objective(
                                director_objective, promise_ledger, chapter=spec.index)
                        except Exception:
                            # Graceful degradation: if injection fails, continue without it
                            pass

                    director_brief = build_director_brief(
                        chapter_id=spec.task_id, objective=director_objective,
                        narrative_ir={"hash": ir.get("id")},
                        brief_id=f"DBR-{spec.index:05d}")
                    extra_vars["chapter_objective"] = render_chapter_objective(director_objective)
                    extra_vars["director_brief"] = render_director_brief(director_brief)
                    derived.write_artifact(
                        project_path=project_path, category="chapter-objective",
                        artifact_id=f"obj-{spec.task_id}", artifact=director_objective,
                        serialized=_json.dumps(director_objective, ensure_ascii=False, indent=2) + "\n")
                    derived.write_artifact(
                        project_path=project_path, category="director-brief",
                        artifact_id=f"dbr-{spec.task_id}", artifact=director_brief,
                        serialized=_json.dumps(director_brief, ensure_ascii=False, indent=2) + "\n")

                # --- Character Speech Profiles (v7 only, roadmap §15): inject the
                # authored language block for the profiled characters that APPEAR
                # in THIS chapter (matched by character_id against the chapter's
                # participants, in stable participant order). This is the direct
                # §14 remedy — it tells the model how these specific characters
                # sound different so dialogue stops being one uniform voice. The
                # profiles are an AUTHORED source (not fact, not projection), read
                # ONCE before the loop; nothing is persisted here (the source
                # already lives under sources/). Degradation is clean: a chapter
                # whose characters have no profile binds nothing, so v7 renders
                # byte-identically to v6. Advisory, never gates (ADR-003).
                if _at_least(major, 7):
                    appearing = [speech_by_id[c] for c in participants
                                 if c in speech_by_id]
                    # Always bind for v7 (the template requires it), same discipline
                    # as v5/v6's character_runtime/director vars. No appearing profile
                    # => a neutral-voice sentinel, so a v7 run with no profiles is a
                    # stable degradation rather than a render failure.
                    extra_vars["speech_profiles"] = render_speech_profiles(appearing)

                # --- opening-diversity constraint (v9+, §14 anti-AI prevention):
                # render the last K PRIOR chapters' openings into a "vary the
                # entrance away from these" block. chapter_bodies is appended AFTER
                # execute_package below, so at this point it holds only prior
                # chapters — a fold cursor, no current-chapter leak (mirrors the
                # story_state digest discipline). This is the prevention half of the
                # check_serial_openings detector. Always binds for v9/v10 (template
                # requires it); no prior bodies => a stable sentinel, so an opening
                # chapter degrades cleanly rather than failing to render.
                if _at_least(major, 9):
                    from ..scene import render_recent_openings
                    extra_vars["recent_openings"] = render_recent_openings(chapter_bodies)

                # --- long-arc coordinate (v10 only, Long-Arc Planner M3): render
                # THIS chapter's projected long-arc position (volume / distance to
                # the volume climax / expected power tier / conflict pressure /
                # paywall+milestone) into the prompt so long-range rhythm holds.
                # long_arc_plan was projected once before the loop; a chapter past
                # the plan's horizon renders a stable sentinel, never a failure.
                if _at_least(major, 10) and long_arc_plan is not None:
                    from ..arc import render_long_arc
                    extra_vars["long_arc"] = render_long_arc(long_arc_plan, spec.index)

                # --- chapter role (章位角色, v3+): resolve THIS chapter's function
                # BEFORE generating it. This was never set, so every chapter —
                # including chapter 1 — generated with the binding's default
                # "advance" (binding.py always binds chapter_role), and run.py fed
                # that role to length_directive: the opening chapter was therefore
                # held to the 推进章 band (min 700 / 0.6-1.5) instead of the 开篇章
                # band (min 900 / 0.8-1.6). The role-bound length contract in
                # chapter_length.py existed but never reached generation for ch1/ch3.
                # Position decides for the first three (§7 黄金三章 is a frozen
                # commercial contract); the director's pacing_role decides after.
                # Scope: v3+ only, because this block sits under the v3 gate — v1/v2
                # never receive extra_vars here and stay byte-identical. Within v3+,
                # ch2 resolves to "advance" == the old default, so only ch1 (opening)
                # and ch3 (turn) change, which is exactly the defect being fixed.
                from ..chapter_length import role_for_chapter
                extra_vars["chapter_role"] = role_for_chapter(
                    spec.index,
                    pacing_role=(director_objective or {}).get("pacing_role"))

                # --- genre contract (v14 only, genre-drift prevention §4.3):
                # render the declared genre's discriminant requirement + its
                # degradation symptoms + the book's OWN coined terms into a
                # per-chapter constraint. The model's prior leans generic 玄幻, and
                # the slide is invisible chapter-by-chapter (each chapter reads fine
                # locally while the book stops delivering its genre promise), so the
                # constraint has to be restated EVERY chapter rather than once at
                # the outline. Prevention half of check_serial_genre_drift; naming
                # the same coined terms the detector counts closes the loop on one
                # signal. Unknown genre => a stable sentinel, never a failure.
                if _at_least(major, 14):
                    from ..genre_taxonomy import (extract_authored_markers,
                                                  render_genre_contract)
                    gc_genre = None
                    if outline:
                        _g = outline.get("genre") or []
                        gc_genre = _g[0] if isinstance(_g, list) and _g else None
                        if not gc_genre:
                            gc_genre = ((outline.get("market_position") or {})
                                        .get("sub_genre") or None)
                    gc_sources = [s for s in (outline, genre_brain)
                                  if isinstance(s, dict)]
                    extra_vars["genre_contract"] = render_genre_contract(
                        gc_genre,
                        authored_markers=extract_authored_markers(*gc_sources))

        # --- execute (reads the Novel Brain internally for style) ------------
        # C6 multi-version: when candidate_models holds >1 model, generate ONE
        # draft per model (each with write=False so losers never touch the derived
        # index), score each by its qa_review, then reuse the REAL director
        # compare/select machinery to pick the winner and persist ONLY it. With a
        # single model (the default) this is exactly the prior single-draft path —
        # one execute_package call with write=True — so a deterministic/mock run is
        # byte-identical. Genuine variation needs a live model at temp>0 with
        # per-candidate replay isolation (identical requests otherwise hit the
        # replay cache); the CLI builds candidate_models that way. Advisory: the
        # base draft is still what gets produced, selection never gates (ADR-003).
        version_selection = None
        cand_models = candidate_models or [model]
        # Approved-fact consumption for THIS chapter (CI-M2 next-chapter loop):
        # when the caller supplies consumption evidence keyed by chapter index,
        # feed it to execute_package so the approved_state reaches the prompt. None
        # => byte-identical to before (the whole existing serial path).
        _cons = (consumption_by_chapter or {}).get(spec.index) or {}
        _cons_ev = _cons.get("evidence")
        _cons_state = _cons.get("recomputed_state")
        # A generation failure must SKIP the chapter, not kill the serial — the
        # module docstring's "断更恢复" promise. Before this boundary only
        # `not ex.ok` (a QA/contract failure) was handled; a TRANSPORT failure
        # raised straight out of the loop. Real cost of that gap, measured on the
        # 3-arm run: one curl timeout killed the DeepSeek arm at ch19 (18/30
        # produced) and a Connection error killed the GPT-v11 arm at ch23 (22/30) —
        # after the retry policy's 3 attempts were already exhausted. Both runs lost
        # their run-manifest AND every chapter-run detector reading, because those
        # are persisted after the loop.
        #
        # Caught broadly on purpose: ANY per-chapter generation failure is a skip.
        # The serial is the recovery unit (ADR-003 — orchestration never gates), and
        # narrowing this to LLMError would leave the same hole open for the next
        # unexpected exception class.
        try:
            if len(cand_models) <= 1:
                ex = execute_package(
                    package=build.package, standard_root=standard_root,
                    project_path=project_path, model=model, prompt_runtime=prompt_runtime,
                    prompt_version=prompt_version, reviewer=reviewer,
                    extra_prompt_variables=extra_vars, review_grounding=chapter_ir_grounding,
                    director_objective=director_objective, director_brief=director_brief,
                    consumption_evidence=_cons_ev, recomputed_state=_cons_state,
                    target_wordcount=target_wordcount,
                    scene_beats=_scene_beats(scene_plan_obj),
                    chapter_no=spec.index)
            else:
                ex, version_selection, version_comparison = _select_best_candidate(
                    cand_models=cand_models, package=build.package,
                    standard_root=standard_root, project_path=project_path,
                    prompt_runtime=prompt_runtime, prompt_version=prompt_version,
                    reviewer=reviewer, extra_vars=extra_vars,
                    chapter_ir_grounding=chapter_ir_grounding,
                    director_objective=director_objective, director_brief=director_brief,
                    target_wordcount=target_wordcount, spec=spec,
                    project_derived=derived,
                    scene_beats=_scene_beats(scene_plan_obj))
                # Persist the SELECTED winner's draft. Every candidate ran with
                # write=False (so losers never clobber the derived index), which means
                # the winner was never written to disk either. Rather than re-execute
                # the winner (a second live pass can DRIFT from the selected candidate),
                # write the envelope execute_package already built around it — the same
                # bytes the single-draft write=True path would have produced. Skipped
                # when the winner failed execution (no envelope) so the caller records
                # the skip exactly as the single-draft path does.
                if ex.ok and ex.envelope is not None:
                    from ..execution.agent import serialize as _serialize
                    from ..execution.run import DERIVED_CATEGORY as _DRAFTS
                    ex.artifact_path = derived.write_artifact(
                        project_path=project_path, category=_DRAFTS,
                        artifact_id=ex.artifact["task_id"], artifact=ex.artifact,
                        serialized=_serialize(ex.envelope))
                # Persist BOTH the comparison (per-candidate scores + diffs — the
                # evidence) and the selection (the decision that cites it). Previously
                # only the selection was written, so its comparison_ref pointed at
                # nothing on disk and the per-candidate scores were unrecoverable.
                if version_comparison is not None:
                    derived.write_artifact(
                        project_path=project_path, category="version-comparison",
                        artifact_id=f"cmp-{spec.task_id}", artifact=version_comparison,
                        serialized=_json.dumps(version_comparison, ensure_ascii=False, indent=2) + "\n")
                if version_selection is not None:
                    derived.write_artifact(
                        project_path=project_path, category="version-selection",
                        artifact_id=f"sel-{spec.task_id}", artifact=version_selection,
                        serialized=_json.dumps(version_selection, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:                      # noqa: BLE001 — see above
            # Record the skip in the SAME shape the `not ex.ok` path uses, so a
            # transport failure and a QA failure are indistinguishable downstream
            # (report/dashboard/manifest all already handle ok=False).
            result.skipped += 1
            result.chapters.append(ChapterRun(
                spec=spec, ok=False, stage="execute:generation-error",
                message=f"{type(exc).__name__}: {exc}"))
            print(f"  [skip] ch {spec.index:>2} {spec.event_id} "
                  f"stage=generation-error  {type(exc).__name__}: {str(exc)[:90]}")
            continue

        # --- optional Contract Revision Loop (Phase 3 Stage 2, Task 2.2), advisory --
        # When Contract Gate is enabled with a rewrite_model, check the Candidate
        # against the contract BEFORE finalizing. If critical issues are found
        # (location mismatch, missing hook, missing required characters), trigger
        # a targeted revision loop (max contract_revision_rounds, default 2). The
        # loop extracts suggestions from the contract check and feeds them to the
        # rewrite model. After each revision, re-check the contract. Keep the BEST
        # draft (fewest critical issues). This is ADVISORY and never gates (ADR-003):
        # even if all revisions fail, the best attempt is kept and the chapter
        # proceeds. The revision session is recorded in contract_revision_session
        # for audit. Runs BEFORE commercial/hygiene loops so those work on the
        # contract-compliant draft.
        contract_revision_session = None
        if (enable_contract_gate and prompt_version == "15.0.0" and
            rewrite_model is not None and ex.ok and ex.artifact is not None):
            from pathlib import Path as _ContractPath
            try:
                import sys
                contract_plugin_path = _ContractPath(__file__).parent.parent.parent.parent / 'runtime_plugins'
                if str(contract_plugin_path) not in sys.path:
                    sys.path.insert(0, str(contract_plugin_path))
                from contract.gate import ContractGate

                _contracts_dir = _ContractPath(contracts_dir) if contracts_dir else project_path / "contracts"
                _schemas_dir = _ContractPath(schema_dir)
                gate = ContractGate(
                    contracts_dir=_contracts_dir,
                    schemas_dir=_schemas_dir,
                    strict_mode=strict_contract_mode,
                )

                # Load previous chapter text for continuity (Chapter 2+)
                prev_text = ""
                if spec.index > 1:
                    prev_chapter_index = spec.index - 1
                    prev_text = bodies_by_chapter.get(prev_chapter_index, "")

                # Initial check on the Candidate
                candidate_draft = ex.artifact
                candidate_text = (candidate_draft or {}).get("body", "")
                original_check = gate.check_candidate(
                    chapter=spec.index,
                    candidate_text=candidate_text,
                    prev_text=prev_text
                )

                revision_rounds = []
                current_draft = candidate_draft
                best_draft = candidate_draft
                best_check = original_check

                # Count critical issues as the optimization target
                def _count_critical_issues(check_result):
                    return len([iss for iss in check_result.get("issues", [])
                               if iss.get("category") == "critical"])

                original_critical_count = _count_critical_issues(original_check)
                best_critical_count = original_critical_count

                # If critical issues found and rewrite_model available, trigger revision
                if original_check.get("requires_revision") and contract_revision_rounds > 0:
                    from ..execution.revision import rewrite_once
                    from ..execution.draft_qa import check_draft

                    for round_num in range(1, contract_revision_rounds + 1):
                        # Extract revision guidance from the current best check
                        # (use original_check for round 1, then best_check for subsequent rounds)
                        current_check = original_check if round_num == 1 else best_check
                        suggestions = current_check.get("revision_suggestions", [])
                        if not suggestions:
                            break  # No actionable guidance

                        # Format suggestions as revision instruction
                        revision_instruction = (
                            "修订以下契约问题：\n" +
                            "\n".join(f"• {s}" for s in suggestions[:3])  # Top 3 suggestions
                        )

                        # Rewrite with contract guidance
                        revised = rewrite_once(
                            rewrite_model, current_draft, build.package,
                            reason=revision_instruction,
                            objective=director_objective
                        )

                        # Re-check the revised draft
                        revised_text = (revised or {}).get("body", "")
                        revised_check = gate.check_candidate(
                            chapter=spec.index,
                            candidate_text=revised_text,
                            prev_text=prev_text
                        )

                        revised_critical_count = _count_critical_issues(revised_check)

                        # Record this round
                        revision_rounds.append({
                            "round": round_num,
                            "check_result": revised_check,
                            "revised_draft_hash": (revised or {}).get("content_hash"),
                            "critical_issues_before": best_critical_count,
                            "critical_issues_after": revised_critical_count,
                        })

                        # Keep the best draft (fewest critical issues)
                        if revised_critical_count < best_critical_count:
                            best_draft = revised
                            best_check = revised_check
                            best_critical_count = revised_critical_count
                            current_draft = revised

                        # Exit early if perfect (no critical issues)
                        if revised_critical_count == 0:
                            break

                # Determine verdict
                if not original_check.get("requires_revision"):
                    verdict = "initial_pass"
                elif best_critical_count == 0:
                    verdict = "revised_pass"
                elif best_critical_count < original_critical_count:
                    verdict = "revised_improved"
                else:
                    verdict = "revised_partial"  # Still has issues but did our best

                # Pin the checked text explicitly. check_candidate only returns
                # findings, so trying to read a hash from final_check made the
                # later post-enhancer validation unable to tell whether the prose
                # had changed after this check.
                validated_draft_hash = (best_draft or {}).get("content_hash")
                # Build session record
                contract_revision_session = {
                    "initial_check": original_check,
                    "rounds": revision_rounds,
                    "final_check": best_check,
                    "validated_draft_hash": validated_draft_hash,
                    "verdict": verdict,
                    "initial_critical_count": original_critical_count,
                    "final_critical_count": best_critical_count,
                    "improved": best_critical_count < original_critical_count,
                }

                # Use the best draft going forward
                if best_draft["content_hash"] != ex.artifact["content_hash"]:
                    # The revision improved the draft - update the artifact
                    # Write the revised draft back (same as hygiene/commercial loops do)
                    from ..execution.envelope import wrap
                    from ..execution.agent import serialize
                    from ..execution.run import DERIVED_CATEGORY
                    envelope = wrap(best_draft, None,
                                    contract_revision_session=contract_revision_session)
                    derived.write_artifact(
                        project_path=project_path, category=DERIVED_CATEGORY,
                        artifact_id=best_draft["task_id"], artifact=best_draft,
                        serialized=serialize(envelope))
                    ex.artifact = best_draft
                    chapter_draft = best_draft

                # Log result
                if revision_rounds:
                    print(f"  [contract] ch {spec.index:>2} revised "
                          f"{len(revision_rounds)} rounds, "
                          f"critical: {_count_critical_issues(initial_check)}→{best_critical_count}")

            except Exception as exc:  # advisory — contract revision never breaks the serial
                import logging
                logging.warning(f"Ch{spec.index} Contract revision error: {type(exc).__name__}: {exc}")
                contract_revision_session = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "verdict": "error",
                }

        # --- optional Commercial Optimization Loop (P16), comparison-only ----
        # Improves the draft by simulated reader reaction, re-gates it, and (only
        # if it still passes) writes it back over the initial draft. Never gates
        # the serial; skipped entirely when no simulator+rewriter is supplied.
        chapter_draft = ex.artifact

        # --- Phase 1 Task 1.3.1: Length Enforcement (post-generation) --------
        # Apply hard truncation if the draft exceeds the target length ceiling.
        # This is a DETERMINISTIC post-processing step that runs AFTER generation
        # but BEFORE commercial/hygiene loops, so those work on length-compliant
        # drafts. Truncation is at complete sentence boundaries, preserving text
        # integrity. Only applies when target_wordcount is specified.
        if ex.ok and chapter_draft is not None and target_wordcount is not None:
            from ..chapter.length_enforcer import enforce_length_hard_limit
            # enforce_length_hard_limit returns the draft (modified or original)
            chapter_draft = enforce_length_hard_limit(
                chapter_draft, target=target_wordcount, tolerance=0.2)

        if not ex.ok:
            result.skipped += 1
            result.chapters.append(ChapterRun(
                spec=spec, ok=False, stage=f"execute:{ex.stage}",
                message=ex.message,
                draft_hash=(chapter_draft or {}).get("content_hash")))
            continue
        chapter_cost = 0.0
        chapter_usage = {"input": 0, "output": 0, "total": 0}
        chapter_budget_note = None
        if ex.artifact is not None:
            llm = ((ex.artifact.get("produced_by") or {}).get("llm") or {})
            cst = llm.get("cost") or {}
            tu = llm.get("token_usage") or {}
            # 走 cost_fold 而不是 `or 0`:金额照加,但"有 token 用量却没成本"
            # 会被数进 cost_fold.unpriced_calls,收尾时告警(见 §cost 折叠注释)。
            chapter_cost += cost_fold.add(llm)
            chapter_usage["input"] += int(tu.get("input_tokens", tu.get("input", 0)) or 0)
            chapter_usage["output"] += int(tu.get("output_tokens", tu.get("output", 0)) or 0)
            chapter_usage["total"] += int(tu.get("total_tokens", tu.get("total", 0)) or 0)
            if cst.get("currency"):
                total_cost_currency = cst.get("currency")
            if cst.get("pricing_version"):
                total_cost_pricing_version = cst.get("pricing_version")
        # M4-B4 per-chapter budget cap: the optional enhancement loops (commercial,
        # hygiene) each add LLM calls ON TOP of generation. The run-level budget_limit
        # only checks at a chapter's START, so a single chapter's loops can overshoot
        # it (and C6 multi-version would multiply that). When the generation cost of
        # THIS chapter has already reached per_chapter_budget, skip the optional
        # enhancers for this chapter and record why. The base draft is untouched, so
        # the serial never gates (ADR-003) — it degrades to the cheaper path.
        def _chapter_over_budget() -> bool:
            # Same breaker, chapter layer. Keeping both layers behind one
            # check_budget call means there is exactly ONE place that decides
            # whether a paid call may proceed (D180-05).
            return _breaker_tripped(chapter_limit=per_chapter_budget,
                                    chapter_spent=chapter_cost)

        commercial_verdict = None
        if simulator is not None and rewrite_model is not None and _chapter_over_budget():
            chapter_budget_note = (
                f"per-chapter budget {per_chapter_budget:.4f} reached at "
                f"{chapter_cost:.4f} after generation; commercial loop skipped")
        elif simulator is not None and rewrite_model is not None:
            from ..execution.commercial import optimize_commercial
            from ..execution.draft_qa import check_draft
            from ..execution.envelope import wrap
            from ..execution.agent import serialize
            from ..execution.run import DERIVED_CATEGORY
            cres = optimize_commercial(
                simulator, rewrite_model, ex.artifact, build.package,
                max_rounds=commercial_rounds)
            commercial_verdict = cres.session.verdict
            selected = cres.final_artifact
            if selected["content_hash"] != ex.artifact["content_hash"] \
                    and not check_draft(selected):
                envelope = wrap(selected, None,
                                commercial_session=cres.session.to_dict())
                derived.write_artifact(
                    project_path=project_path, category=DERIVED_CATEGORY,
                    artifact_id=selected["task_id"], artifact=selected,
                    serialized=serialize(envelope))
                chapter_draft = selected
            for rr in getattr(cres.session, "rounds", []) or []:
                for key in ("initial", "final"):
                    art = rr.get(key)
                    if isinstance(art, dict):
                        llm = ((art.get("produced_by") or {}).get("llm") or {})
                        cst = llm.get("cost") or {}
                        tu = llm.get("token_usage") or {}
                        # 同上:商业环的每轮改写也是真实付费调用,未定价同样要被数出来。
                        chapter_cost += cost_fold.add(llm)
                        chapter_usage["input"] += int(tu.get("input_tokens", tu.get("input", 0)) or 0)
                        chapter_usage["output"] += int(tu.get("output_tokens", tu.get("output", 0)) or 0)
                        chapter_usage["total"] += int(tu.get("total_tokens", tu.get("total", 0)) or 0)
                        if cst.get("currency"):
                            total_cost_currency = cst.get("currency")
                        if cst.get("pricing_version"):
                            total_cost_pricing_version = cst.get("pricing_version")

        total_llm_cost += chapter_cost
        total_input_tokens += chapter_usage["input"]
        total_output_tokens += chapter_usage["output"]
        total_tokens += chapter_usage["total"]

        # --- optional Prose Hygiene correction loop (§14.5), opt-in ----------
        # Turns the deterministic density + ai_taste WARNINGS into a targeted
        # rewrite, re-checks deterministically, and keeps the fewest-warning draft.
        # It reuses rewrite_once (no second rewrite engine) and, like the
        # commercial loop, only writes the corrected draft back when it STILL
        # passes the deterministic gate (check_draft). Runs on the post-commercial
        # draft. Off unless hygiene_model is supplied → byte-identical when absent.
        # Never gates the serial (ADR-003); the rewrite is prose-only so state is
        # unaffected (state_hash unchanged).
        hygiene = None
        integrity = None
        from ..execution.text_integrity import assess_text_integrity
        integrity = assess_text_integrity(chapter_draft)
        if integrity.status == "fail":
            result.skipped += 1
            result.chapters.append(ChapterRun(
                spec=spec, ok=False, stage="integrity-failed",
                message=", ".join(integrity.reason_codes) or "text integrity failed",
                draft_hash=chapter_draft.get("content_hash"),
                integrity=integrity.to_dict(),
            ))
            continue
        if hygiene_model is not None and _chapter_over_budget():
            # Re-checked AFTER the commercial loop: its cost may have pushed this
            # chapter over the cap even if generation alone did not. Skip hygiene,
            # keep the (possibly commercial-improved) draft. Preserve any earlier note.
            note = (f"per-chapter budget {per_chapter_budget:.4f} reached at "
                    f"{chapter_cost:.4f}; hygiene loop skipped")
            chapter_budget_note = (chapter_budget_note + "; " + note
                                   if chapter_budget_note else note)
        elif hygiene_model is not None:
            from ..execution.prose_hygiene import improve_prose_hygiene
            from ..execution.draft_qa import check_draft
            from ..execution.envelope import wrap
            from ..execution.agent import serialize
            from ..execution.run import DERIVED_CATEGORY
            hres = improve_prose_hygiene(
                hygiene_model, chapter_draft, build.package,
                max_rounds=hygiene_rounds, objective=director_objective,
                reference_profile=reference_profile)
            hygiene = hres.session.to_dict()
            corrected = hres.final_artifact
            if corrected["content_hash"] != chapter_draft["content_hash"] \
                    and check_draft(corrected):
                envelope = wrap(corrected, None,
                                hygiene_session=hres.session.to_dict())
                derived.write_artifact(
                    project_path=project_path, category=DERIVED_CATEGORY,
                    artifact_id=corrected["task_id"], artifact=corrected,
                    serialized=serialize(envelope))
                chapter_draft = corrected

        # --- P0-2: Final Contract Validation after all modifications ---------
        # After contract revision + commercial + hygiene loops complete, verify
        # the FINAL draft still honors the contract. If commercial/hygiene modified
        # the text after contract revision, the final text might violate the contract.
        # This is the closed-loop check: ALL modifications → final validation.
        # Advisory (ADR-003): validation failures are recorded but never gate the
        # serial. When validation fails, a warning is logged and the chapter proceeds
        # with the best available draft.
        final_contract_validation = None
        if (enable_contract_gate and prompt_version == "15.0.0" and
            chapter_draft is not None and spec.index >= 1):
            # Only skip when the revision session proves this exact final hash was
            # already checked. Without a revision session there is no candidate
            # validation at all (rewrite_model is optional), so the final draft
            # must always be checked.
            current_hash = chapter_draft.get("content_hash")
            revision_final_hash = (
                contract_revision_session.get("validated_draft_hash")
                if isinstance(contract_revision_session, dict) else None)
            draft_changed_after_revision = (
                revision_final_hash is None or current_hash != revision_final_hash)

            if draft_changed_after_revision:
                from pathlib import Path as _ContractPath
                try:
                    import sys
                    contract_plugin_path = _ContractPath(__file__).parent.parent.parent.parent / 'runtime_plugins'
                    if str(contract_plugin_path) not in sys.path:
                        sys.path.insert(0, str(contract_plugin_path))
                    from runtime_plugins.contract import ContractGate, ContractViolationError

                    _contracts_dir = _ContractPath(contracts_dir) if contracts_dir else project_path / "contracts"
                    _schemas_dir = _ContractPath(schema_dir)
                    gate = ContractGate(
                        contracts_dir=_contracts_dir,
                        schemas_dir=_schemas_dir,
                        strict_mode=strict_contract_mode,
                    )

                    # Load previous chapter text for continuity (Chapter 2+)
                    prev_text = ""
                    if spec.index > 1:
                        prev_chapter_index = spec.index - 1
                        prev_text = bodies_by_chapter.get(prev_chapter_index, "")

                    # Check the FINAL draft against the contract
                    final_text = chapter_draft.get("body", "")
                    final_hash = chapter_draft.get("content_hash", "unknown")
                    final_check = gate.check_candidate(
                        chapter=spec.index,
                        candidate_text=final_text,
                        prev_text=prev_text
                    )

                    final_contract_validation = {
                        "stage": "final_after_all_modifications",
                        "validated_draft_hash": final_hash,
                        "check_result": final_check,
                        "requires_revision": final_check.get("requires_revision", False),
                        "critical_issues": len([iss for iss in final_check.get("issues", [])
                                               if iss.get("category") == "critical"]),
                    }

                    # Log warning if the final draft has new contract violations
                    if final_check.get("requires_revision"):
                        import logging
                        critical_count = final_contract_validation["critical_issues"]
                        logging.warning(
                            f"Ch{spec.index} Final contract validation failed after "
                            f"commercial/hygiene modifications: {critical_count} critical issues"
                        )
                        print(f"  [warn] ch {spec.index:>2} FINAL contract check: "
                              f"{critical_count} critical issues after modifications")

                except Exception as exc:
                    # Final validation is advisory — log error but don't break the serial
                    import logging
                    logging.warning(f"Ch{spec.index} Final contract validation error: "
                                    f"{type(exc).__name__}: {exc}")
                    final_contract_validation = {
                        "stage": "final_after_all_modifications",
                        "error": f"{type(exc).__name__}: {exc}",
                    }

        # --- project state as of this chapter's event (fold cursor) ----------
        # State is a fold of FACTS, so the commercial rewrite (prose only) does
        # not affect it — the state_hash is the same with or without P16.
        state = project_state(reg, up_to_event=spec.event_id)
        last_state_hash = state.state_hash
        # Derive the quality verdict as a CROSS-CHAPTER fold: a scoring reviewer
        # (llm-quality / panel) produces per-dimension scores on ex.qa_review;
        # chapter_quality_verdict compares this chapter's overall mean to the
        # previous chapter's to yield regressed/degraded/None. A deterministic
        # reviewer (the default) produces no scores => verdict None => the serial
        # is byte-identical to before this wiring. Advisory, never gates (ADR-003).
        from ..execution.quality_center import chapter_quality_verdict
        verdict = chapter_quality_verdict(ex.qa_review, prev_quality_scores)
        _scores = (ex.qa_review or {}).get("scores")
        if isinstance(_scores, dict) and _scores:
            prev_quality_scores = _scores

        # --- M7 originality + red-line gate over the FINAL draft (advisory) ---
        # The M7 gate (execution/m7.py) was built but never LIVE on the serial
        # production path — it only ran downstream in the Production Card. Here it
        # runs on the settled draft (post-hygiene, post-commercial), so the
        # originality + red-line assessment is folded into the ChapterRun and the
        # per-chapter audit trail. The red-line half is cheap and deterministic, so
        # it runs on EVERY chapter; the originality window-match is O(body·refs) and
        # opt-in — absent references => risk L0 (no match), so behaviour is
        # unchanged for runs without a reference corpus. NEVER gates (ADR-003): a
        # hold/block recommendation is recorded and, if an ApprovalQueue was
        # supplied, enqueued for a human decision (ADR-009) — the serial goes on.
        from ..execution.m7 import assess_m7
        m7_result = assess_m7(
            chapter_draft, chapter_id=spec.task_id,
            references=originality_references or (),
            redline_ruleset=redline_ruleset)
        m7_dict = m7_result.to_dict()
        m7_approval_id = None
        if approval_queue is not None and m7_result.recommendation in ("hold", "block"):
            from ..approval import enqueue_m7_request
            m7_approval_seq += 1
            m7_approval_id = f"APR-M7-{spec.task_id}"
            enqueue_m7_request(
                approval_queue,
                request_id=m7_approval_id,
                chapter_id=spec.task_id,
                reason=m7_result.rationale,
                risk_level=m7_result.risk_level,
                requested_by={"module": "runtime.serialize.loop"},
                context={
                    "recommendation": m7_result.recommendation,
                    "redline_passed": m7_result.redline_passed,
                    "similarity": m7_result.similarity,
                })

        # --- intra-chapter pacing check over the emotion curve (advisory) ----
        # Runs only when the scene plan carried emotion data (i.e. it was
        # LLM-enriched). Deterministic; NEVER gates (ADR-003) — it records
        # findings for the audit trail and degrades to a clean info note when
        # there is no curve to judge.
        pacing = None
        pacing_peak = None
        if scene_plan_obj is not None:
            from ..scene import check_pacing, curve_summary
            pacing = check_pacing(scene_plan_obj).to_dict()
            summary = curve_summary(scene_plan_obj)
            if summary is not None:
                pacing_peak = summary["peak"]

        # --- single-chapter information-density check (advisory) -------------
        # The §14 anti-注水 signal: quantifies dialogue ratio / simile density /
        # front-loaded mood over the DRAFT BODY directly. Unlike pacing it needs
        # no emotion enrichment, so it runs for EVERY prompt version and every
        # chapter. Deterministic; NEVER gates (ADR-003) — reads only the body, so
        # it touches neither draft_hash nor state_hash.
        from ..execution.density import check_density
        density = check_density(chapter_draft).to_dict()

        # --- single-chapter AI-tell check (advisory) -------------------------
        # The §14 anti-AI-味 signal: quantifies anaphora stacking / em-dash
        # asides / monotone sentence rhythm over the DRAFT BODY. Twin of the
        # density check: same discipline, syntactic signals instead of content.
        # Deterministic; NEVER gates (ADR-003) — reads only the body, so it
        # touches neither draft_hash nor state_hash.
        from ..execution.humanization import check_ai_taste
        ai_taste = check_ai_taste(chapter_draft).to_dict()
        from ..serialize.quality_snapshot import build_quality_snapshot
        quality_snapshot = build_quality_snapshot(
            chapter_id=spec.task_id,
            body=(chapter_draft or {}).get("body", ""),
            objective=director_objective,
            reference_profile=reference_profile,
        )

        # --- single-chapter end-hook check (advisory) ------------------------
        # The §14 finding-3 remedy: verifies the chapter END actually leaves a
        # 追读 hook, instead of trusting the model to. Cross-checks against the
        # director objective's declared cliffhanger_type when present (v6/v7).
        # Deterministic; NEVER gates (ADR-003) — reads only the body, so it
        # touches neither draft_hash nor state_hash.
        from ..execution.hook_check import check_end_hook
        end_hook = check_end_hook(
            chapter_draft, objective=director_objective).to_dict()

        # --- narrative-layer leak check (advisory) ---------------------------
        # Fifth twin of density/ai_taste/hook/length: detects 叙事外的章节指代
        # ("上一章"/"第5章"/"前文") leaking into the prose — the reader is reading a
        # novel, not a chaptered document. Found by spot-checking real A/B prose
        # (v11 12 hits/4ch, v12 3/1) after confirming NO existing detector covered
        # it (text_integrity passes, hygiene only flags dialogue ratio). Validated
        # negative on 4 real bestsellers (0/120 chapters) before wiring, because
        # substring false positives have bitten this repo 4 times.
        # Deterministic; NEVER gates (ADR-003) — reads only the body, so it
        # touches neither draft_hash nor state_hash.
        from ..execution.meta_reference import check_meta_reference
        meta_reference = check_meta_reference(chapter_draft).to_dict()

        # --- single-chapter length-vs-target check (advisory) ----------------
        # The §14 anti-抖动 signal: the real run swung 1773→5766 chars/chapter.
        # Measures the body char count against the outline's target_wordcount.
        # Fourth twin of density/ai_taste/hook: deterministic, reads only the
        # body, NEVER gates (ADR-003) — a length miss is advised, not skipped
        # (that would be the draft_qa word floor, a different, gating check).
        # 清单 item 2 (长度区间按功能绑定): resolve the chapter's function so the
        # band is role-aware (开篇 runs longer, 钩子 tolerates shorter). Resolved
        # through the SAME role_for_chapter the generation side above uses — the
        # pacing_role→role mapping used to be an inline literal here, i.e. a second
        # copy of the table that could drift from generation's copy (the same
        # duplication defect as the old _MALE_LEAN pair). Measuring a chapter
        # against a band the generator was never told about is exactly the
        # disagreement worth preventing structurally.
        from ..execution.length_check import check_length
        from ..chapter_length import role_for_chapter
        chapter_role = role_for_chapter(
            spec.index,
            pacing_role=(director_objective or {}).get("pacing_role"),
            body=(chapter_draft or {}).get("body", ""))
        length = check_length(
            chapter_draft, target=target_wordcount, role=chapter_role).to_dict()

        # --- single-chapter reference-anchor gap (advisory, M9.1) ------------
        # Measures the DRAFT BODY with the SAME instruments used on the reference
        # novels, then places each feature against the market-validated band: how
        # far this chapter sits from what a market winner looks like. Fifth twin
        # of density/ai_taste/hook/length: deterministic, reads only the body,
        # NEVER gates (ADR-003) — the gap informs, it does not skip or block. When
        # no profile is pinned it degrades to None (a clean skip), so a project
        # without a reference anchor is byte-identical to before this wiring.
        reference_gap = None
        if reference_profile is not None:
            from ..reference import measure_reference_chapter, compare_to_profile
            measurement = measure_reference_chapter(
                (chapter_draft or {}).get("body", ""), target_wordcount=target_wordcount)
            reference_gap = compare_to_profile(measurement, reference_profile)

        # --- single-chapter 温水章 check (advisory, Phase 9.3) ------------------
        # Keys the narrative mandate's why_now.cost_of_delay: a chapter with no
        # time pressure reads as a lukewarm/filler chapter. Deterministic; NEVER
        # gates (ADR-003). A run without the mandate layer (v1-v7 => mandate None)
        # degrades to a clean skip info, so it touches no draft/state hash.
        from ..director import check_mandate_chapter
        mandate_check = check_mandate_chapter(mandate).to_dict()
        if mandate:
            mandates.append(mandate)

        # Fold this chapter's body for the cross-chapter opening-repetition check
        # (single-chapter ai_taste cannot see openings repeating ACROSS chapters).
        chapter_bodies.append((chapter_draft or {}).get("body", ""))
        # Same body keyed by real chapter number, for window-based checks (§3.3
        # packaging promises are due "by chapter N", which a flat index cannot say).
        bodies_by_chapter[spec.index] = (chapter_draft or {}).get("body", "")

        # Fold this chapter's structural function signature (objective + mandate)
        # for the cross-chapter function-repetition check (W11-03): whether chapters
        # keep doing the SAME structural job (原地打转). Deterministic, never gates.
        function_sigs.append({
            "chapter_id": spec.task_id,
            "objective": director_objective,
            "mandate": mandate,
        })

        chapter_body = (chapter_draft or {}).get("body", "")
        quality_snapshot = build_quality_snapshot(
            chapter_id=spec.task_id,
            body=chapter_body,
            objective=chapter_ir_grounding,
        )
        m5_final = chapter_pipeline.produce(
            chapter_no=spec.index,
            chapter_id=spec.task_id,
            goal=spec.goal,
            text=chapter_body,
            constraints=list(spec.seeds),
            required_facts=list(spec.seeds),
            character_focus=[s for s in spec.seeds if s.startswith("CHR-")],
            state_cursor=state.state_hash,
            story_state=extra_vars.get("story_state") if extra_vars else None,
            chapter_ir=chapter_ir_grounding,
            character_runtime=cr,
            director_objective=director_objective,
            source_refs=[ex.artifact_path] if getattr(ex, "artifact_path", None) else [],
            produced_by=(chapter_draft or {}).get("produced_by"),
            project_path=str(project_path),
        )

        # --- W12 fact-candidate reflow (opt-in, --w12-extract) -------------------
        # First LIVE consumer of run_w12_fact_reflow inside the serial loop (it was
        # CLI-only — built≠live). After a chapter is produced, extract fact
        # candidates from its prose, reconcile against the registry, stage a plan
        # and an approval request. It STAGES only — never mints (ADR-009: the mint
        # is a separate human-confirmed step) and never gates the serial (ADR-003).
        # The in-memory chapter_draft is passed directly, so we read the exact draft
        # just produced — not a drafts/<id> file a later run could clobber.
        w12_summary = None
        if w12_extract:
            try:
                from ..candidates.plan import run_w12_fact_reflow
                w12_result = run_w12_fact_reflow(
                    project_path=project_path,
                    plan_id=f"W12-{spec.task_id}",
                    draft=chapter_draft,
                    model=w12_model,
                    schema_dir=schema_dir,
                )
                w12_summary = {
                    "plan_id": w12_result["plan"]["id"],
                    "derived_path": w12_result["derived_path"],
                    "candidate_count": w12_result["candidate_count"],
                    "reconciled_counts": w12_result["reconciled_counts"],
                    "approval_request_id": w12_result["approval_request_id"],
                    "approval_status": w12_result["approval_status"],
                    "review_findings": len(w12_result.get("review_findings", [])),
                }
            except Exception as exc:  # advisory — a W12 failure never breaks the serial
                w12_summary = {"error": f"{type(exc).__name__}: {exc}"}

        # --- Contract Gate post-generation validation (Phase 3.3, v15 only) ------
        # When Contract Gate is enabled, validate the generated chapter against its
        # contract and the previous chapter (continuity check). This is ADVISORY
        # only — validation failures are recorded but NEVER gate the serial
        # (ADR-003). The validation report is persisted as a derived artifact so
        # it's auditable after the run. Validation runs from chapter 1+ (P0 fix:
        # chapter 1 should also extract exit state for chapter 2 to consume).
        # When validation fails, a warning is logged but the chapter is still
        # marked as produced.
        contract_validation = None
        if enable_contract_gate and prompt_version == "15.0.0" and spec.index >= 1:
            from pathlib import Path as _ContractPath
            try:
                import sys
                contract_plugin_path = _ContractPath(__file__).parent.parent.parent.parent / 'runtime_plugins'
                if str(contract_plugin_path) not in sys.path:
                    sys.path.insert(0, str(contract_plugin_path))
                from runtime_plugins.contract import ContractGate, ContractViolationError

                _contracts_dir = _ContractPath(contracts_dir) if contracts_dir else project_path / "contracts"
                _schemas_dir = _ContractPath(schema_dir)
                gate = ContractGate(
                    contracts_dir=_contracts_dir,
                    schemas_dir=_schemas_dir,
                    strict_mode=strict_contract_mode,
                )

                # Continuity validation (only for chapter 2+, needs previous chapter)
                if spec.index > 1:
                    # Load previous chapter text for continuity validation
                    prev_chapter_index = spec.index - 1
                    prev_text = bodies_by_chapter.get(prev_chapter_index, "")
                    curr_text = (chapter_draft or {}).get("body", "")

                    # Validate: checks contract compliance + continuity
                    validation_result = gate.validate(spec.index, prev_text, curr_text)

                    # Task 2.3: Record the hash of the draft being validated
                    # This ensures we can verify the validation corresponds to the final draft
                    validated_hash = chapter_draft.get("content_hash", "unknown")
                    validation_result["validated_draft_hash"] = validated_hash
                    validation_result["validated_at"] = spec.index

                    contract_validation = validation_result  # dict with 'valid', 'issues', etc.

                    # Persist validation report as derived artifact
                    derived.write_artifact(
                        project_path=project_path,
                        category="contract-validation",
                        artifact_id=f"val-{spec.task_id}",
                        artifact=validation_result,
                        serialized=_json.dumps(validation_result, ensure_ascii=False, indent=2) + "\n")

                    # Log warning if validation failed (advisory, never gates)
                    if not validation_result.get("valid", True):
                        import logging
                        logging.warning(f"Ch{spec.index} Contract validation failed: "
                                        f"{len(validation_result.get('issues', []))} issues found")
                        print(f"  [warn] ch {spec.index:>2} contract validation failed "
                              f"({len(validation_result.get('issues', []))} issues)")

                # --- Extract actual exit state (Phase 3 Stage 2) -----------------
                # Extract the actual exit state from the final text and compare
                # it with the planned exit_target. This forms the state-driven
                # feedback loop: planned → actual → deviation → next chapter uses actual.
                # The actual_exit_state is persisted as an independent artifact for
                # audit and for the next chapter's contract authoring to reference.
                try:
                    curr_text = (chapter_draft or {}).get("body", "")
                    curr_hash = chapter_draft.get("content_hash", "unknown")

                    # Extract actual exit state from final text
                    actual_exit = gate.extract_actual_exit_state(
                        chapter=spec.index,
                        final_text=curr_text,
                        final_text_hash=curr_hash
                    )

                    # Compare planned vs actual
                    comparison = gate.compare_planned_vs_actual(
                        chapter=spec.index,
                        actual_exit=actual_exit
                    )

                    # Persist actual exit state as derived artifact
                    derived.write_artifact(
                        project_path=project_path,
                        category="chapter-exit-state",
                        artifact_id=f"exit-{spec.task_id}",
                        artifact=actual_exit,
                        serialized=_json.dumps(actual_exit, ensure_ascii=False, indent=2) + "\n")

                    # Persist deviation report
                    deviation_report = {
                        "chapter": spec.index,
                        "task_id": spec.task_id,
                        "actual_exit": actual_exit,
                        "comparison": comparison
                    }
                    derived.write_artifact(
                        project_path=project_path,
                        category="contract-deviation",
                        artifact_id=f"dev-{spec.task_id}",
                        artifact=deviation_report,
                        serialized=_json.dumps(deviation_report, ensure_ascii=False, indent=2) + "\n")

                    # Log deviations if any
                    if comparison.get("deviations"):
                        import logging
                        logging.info(f"Ch{spec.index} Exit state deviations: "
                                     f"{len(comparison['deviations'])} found, "
                                     f"match score: {comparison['match_score']:.2f}")
                        print(f"  [info] ch {spec.index:>2} exit deviations: "
                              f"{len(comparison['deviations'])}, "
                              f"score={comparison['match_score']:.2f}")

                    strict_result = comparison.get("strict_mode", {})
                    if strict_contract_mode and strict_result.get("blocked"):
                        raise ContractViolationError(
                            f"Ch{spec.index} strict contract check blocked: "
                            f"{strict_result.get('status')}: {strict_result.get('reason')}"
                        )

                except ContractViolationError:
                    raise
                except Exception as exit_exc:
                    # Exit state extraction is advisory unless strict mode made a
                    # deliberate blocking decision above.
                    import logging
                    logging.warning(f"Ch{spec.index} Exit state extraction error: "
                                    f"{type(exit_exc).__name__}: {exit_exc}")

            except ContractViolationError:
                raise
            except Exception as exc:
                # Validation errors remain advisory; explicit strict-mode
                # violations are re-raised above and cannot be swallowed here.
                import logging
                logging.warning(f"Ch{spec.index} Contract validation error: {type(exc).__name__}: {exc}")
                contract_validation = {
                    "valid": None,
                    "error": f"{type(exc).__name__}: {exc}"
                }

        # --- Phase 2: Final Draft Quality Re-review (optional) ------------------
        # After all modifications (revision + commercial + hygiene), optionally
        # re-run Quality Center on the FINAL draft to track quality changes.
        # This is advisory and configurable; when disabled (default for now),
        # Production Card reuses initial scores. When enabled, it adds LLM cost
        # but provides true quality delta tracking.

        # FIXED (P0-3): Save initial scores BEFORE any modification
        initial_quality_scores = _scores.copy() if isinstance(_scores, dict) and _scores else {}
        final_quality_scores = _scores if isinstance(_scores, dict) and _scores else {}
        quality_delta = {}

        # Stage A: Allow final quality review even if no initial scores exist
        # If _scores is empty, we'll generate both initial and final scores
        if enable_final_quality_review and final_review_model:
            try:
                # Check if we should review this chapter (threshold logic)
                should_review = False

                if final_review_threshold == "always":
                    should_review = True
                elif final_review_threshold == "contract-warning":
                    should_review = final_contract_validation and final_contract_validation.get("requires_revision", False)
                elif final_review_threshold == "quality-drop":
                    initial_avg = sum(_scores.values()) / len(_scores) if _scores else 0
                    should_review = initial_avg < 75
                elif final_review_threshold == "critical-only":
                    should_review = spec.index in [1, 10, 20, 30, 50, 100]

                if should_review:
                    import logging
                    logging.info(f"Ch{spec.index} Running final draft quality re-review")

                    # Construct final artifact for review
                    final_artifact = {
                        "chapter_index": spec.index,
                        "body": chapter_draft.get("body", ""),
                        "content_hash": chapter_draft.get("content_hash"),
                        "word_count": len(chapter_draft.get("body", "").split()),
                    }

                    # Use the passed-in final_review_model (already a LLMQualityJudge from CLI)
                    # Run review
                    final_report = final_review_model.review(
                        artifact=final_artifact,
                        package=build.package,
                        grounding=grounding if 'grounding' in locals() else None
                    )

                    # Extract final scores
                    if final_report.scores:
                        final_quality_scores = final_report.scores

                        # Compute quality delta
                        # If no initial scores exist, treat this as the first evaluation
                        if initial_quality_scores:
                            for dim in final_quality_scores:
                                if dim in initial_quality_scores:
                                    initial_val = initial_quality_scores[dim]
                                    final_val = final_quality_scores[dim]
                                    delta = final_val - initial_val
                                    quality_delta[dim] = {
                                        "initial": initial_val,
                                        "final": final_val,
                                        "delta": delta
                                    }
                        else:
                            # No initial scores - this IS the initial evaluation
                            logging.info(f"Ch{spec.index} First-time quality evaluation (no initial scores)")
                            # Set initial_quality_scores to final_quality_scores for Production Card
                            initial_quality_scores = final_quality_scores.copy()

                        logging.info(f"Ch{spec.index} Final review complete"
                                   + (f", {len([d for d in quality_delta.values() if d['delta'] < -5])} dimensions degraded" if quality_delta else ""))

            except Exception as final_review_exc:
                import logging
                logging.warning(f"Ch{spec.index} Final quality review error: "
                              f"{type(final_review_exc).__name__}: {final_review_exc}")

        # --- Phase 3: Final Draft Reader Simulation (optional) ------------------
        # After commercial optimization, optionally re-run reader simulation on
        # the FINAL draft to detect new dropout risks introduced by modifications.
        # Stage A: Allow final reader simulation even without commercial mode
        final_reader_simulation = None
        final_dropout_risk = None
        final_continuation_rate = None

        if enable_final_reader_simulation and final_reader_sim_model:
            try:
                # Check if we should simulate (threshold logic)
                should_simulate = False

                if final_reader_threshold == "always":
                    should_simulate = True
                elif final_reader_threshold == "commercial-revised":
                    # Only if the commercial optimization loop ran (it may end
                    # "unchanged" if no rewrite gained; that still ran). The
                    # previous line referenced `commercial_revision_session`,
                    # a variable that never exists in this scope — a NameError
                    # swallowed by the except below, so reader simulation was
                    # always empty even when enabled. The loop sets
                    # `commercial_verdict` when it runs; None when absent.
                    should_simulate = commercial_verdict is not None
                elif final_reader_threshold == "dropout-risk":
                    # Only if initial simulation showed dropout risk
                    initial_sim = ex.reader_simulation if hasattr(ex, 'reader_simulation') else None
                    if initial_sim:
                        initial_dropout = initial_sim.get("dropout_risk", 0)
                        should_simulate = initial_dropout > 0.2

                if should_simulate:
                    import logging
                    logging.info(f"Ch{spec.index} Running final draft reader simulation")

                    # Construct final artifact for simulation
                    final_sim_artifact = {
                        "chapter_index": spec.index,
                        "body": chapter_draft.get("body", ""),
                        "content_hash": chapter_draft.get("content_hash"),
                    }

                    # Run simulation using final_reader_sim_model
                    final_sim_result = final_reader_sim_model.review(final_sim_artifact, build.package)

                    if final_sim_result and not final_sim_result.to_dict().get("judge_provenance", {}).get("degraded"):
                        final_reader_simulation = final_sim_result.to_dict()

                        # Extract dropout metrics (fixed: use 'personas' and 'would_continue')
                        personas = final_reader_simulation.get("personas", [])
                        if personas:
                            dropouts = [p for p in personas if not p.get("would_continue", True)]
                            final_dropout_risk = len(dropouts) / len(personas)
                            final_continuation_rate = 1.0 - final_dropout_risk

                            # Check for new dropouts
                            initial_sim = ex.reader_simulation if hasattr(ex, 'reader_simulation') else None
                            if initial_sim:
                                initial_personas = initial_sim.get("personas", [])
                                initial_dropouts = [p for p in initial_personas if not p.get("would_continue", True)]
                                initial_dropout_risk = len(initial_dropouts) / len(initial_personas) if initial_personas else 0

                                if final_dropout_risk > initial_dropout_risk:
                                    logging.warning(
                                        f"Ch{spec.index} Final draft introduced new dropout risks: "
                                        f"{initial_dropout_risk:.1%} → {final_dropout_risk:.1%}"
                                    )

                            logging.info(f"Ch{spec.index} Final reader simulation complete, "
                                       f"dropout risk: {final_dropout_risk:.1%}")
                        else:
                            logging.info(f"Ch{spec.index} Final reader simulation complete (no personas)")

            except Exception as final_sim_exc:
                import logging
                logging.warning(f"Ch{spec.index} Final reader simulation error: "
                              f"{type(final_sim_exc).__name__}: {final_sim_exc}")

        # --- Promise Delivery Check (Stage B.3) ------------------------------
        # Check if this draft delivers any open promises and update the ledger.
        # Uses evidence matching to detect delivery based on term coverage.
        promises_delivered = []
        promises_pending = []

        if promise_ledger:
            try:
                from ..promise.matcher import check_delivery, get_delivered_promises, get_pending_promises

                # Get draft body for evidence matching
                draft_body = chapter_draft.get("body", "")

                # Check delivery and update ledger (threshold=0.5 means 50% evidence coverage)
                promise_ledger = check_delivery(
                    promise_ledger,
                    draft_body,
                    chapter=spec.index,
                    event_id=spec.event_id,
                    threshold=0.5
                )

                # Get promises delivered in this chapter
                promises_delivered = get_delivered_promises(promise_ledger, spec.index)

                # Get promises that are overdue (should have been delivered by now)
                promises_pending = get_pending_promises(promise_ledger, spec.index)

                if promises_delivered:
                    import logging
                    logging.info(f"Ch{spec.index} Delivered {len(promises_delivered)} promises: {promises_delivered}")

                if promises_pending:
                    import logging
                    logging.warning(f"Ch{spec.index} {len(promises_pending)} promises overdue: {promises_pending}")

            except Exception as promise_exc:
                import logging
                logging.warning(f"Ch{spec.index} Promise delivery check error: "
                              f"{type(promise_exc).__name__}: {promise_exc}")

        # --- P0-3: Governance Module Checks (Stage B.4) -----------------------
        # Wire in the three governance modules: PromiseDebtTracker,
        # CharacterArcValidator, and WorldConsistencyChecker.
        # These provide advisory signals (ADR-003: never gate) but their findings
        # are recorded in the Production Card for human review.
        governance_reports = {
            "promise_debt": None,
            "character_arc": None,
            "world_consistency": None,
        }

        # P0-3.1: Promise Debt Tracker
        if promise_ledger:
            try:
                from ..promise_debt_tracker import PromiseDebtTracker
                tracker = PromiseDebtTracker()
                debt_report = tracker.analyze_debt(
                    current_chapter=spec.index,
                    promise_ledger=promise_ledger.to_dict()
                )
                governance_reports["promise_debt"] = {
                    "total_pending": debt_report.total_pending_promises,
                    "critical_count": len(debt_report.critical_debts),
                    "high_urgency_count": len(debt_report.high_urgency_debts),
                    "recommendations": debt_report.recommendations,
                    "next_chapter_suggestions": debt_report.next_chapter_suggestions,
                }

                # Log critical debt
                if debt_report.critical_debts:
                    import logging
                    logging.warning(
                        f"Ch{spec.index} CRITICAL promise debt: "
                        f"{len(debt_report.critical_debts)} promises overdue >20 chapters"
                    )
            except Exception as debt_exc:
                import logging
                logging.warning(f"Ch{spec.index} Promise debt tracking error: {debt_exc}")

        # P0-3.2: Character Arc Validator
        # Only run if character growth data is available
        try:
            from ..character_arc_validator import CharacterArcValidator
            from ..character_growth import CharacterGrowth

            # Check if we have character growth data in state
            if state and hasattr(state, 'character_growth'):
                validator = CharacterArcValidator()
                arc_reports = []

                # Validate each character's arc
                for char_id, growth_data in state.character_growth.items():
                    if isinstance(growth_data, CharacterGrowth):
                        arc_report = validator.validate_arc(
                            character_growth=growth_data,
                            current_chapter=spec.index
                        )
                        if arc_report.issues:
                            arc_reports.append({
                                "character_id": char_id,
                                "character_name": arc_report.character_name,
                                "issue_count": len(arc_report.issues),
                                "arc_health_score": arc_report.arc_health_score,
                                "critical_issues": [
                                    issue.description for issue in arc_report.issues
                                    if issue.severity == "critical"
                                ],
                            })

                if arc_reports:
                    governance_reports["character_arc"] = {
                        "validated_characters": len(arc_reports),
                        "characters_with_issues": len(arc_reports),
                        "reports": arc_reports,
                    }

                    # Log critical arc issues
                    critical_count = sum(
                        len(r["critical_issues"]) for r in arc_reports
                    )
                    if critical_count > 0:
                        import logging
                        logging.warning(
                            f"Ch{spec.index} Character arc issues: "
                            f"{critical_count} critical across {len(arc_reports)} characters"
                        )
        except Exception as arc_exc:
            import logging
            logging.warning(f"Ch{spec.index} Character arc validation error: {arc_exc}")

        # P0-3.3: World Consistency Checker
        try:
            from ..world_consistency_checker import WorldConsistencyChecker

            checker = WorldConsistencyChecker()
            consistency_report = checker.check_consistency(
                current_chapter=spec.index,
                chapter_content=chapter_draft.get("body", ""),
                story_state=state.to_dict() if state else {}
            )

            governance_reports["world_consistency"] = {
                "total_rules": consistency_report.total_rules,
                "total_inconsistencies": consistency_report.total_inconsistencies,
                "critical_count": len(consistency_report.critical_inconsistencies),
                "high_count": len(consistency_report.high_inconsistencies),
                "consistency_score": consistency_report.consistency_score,
                "recommendations": consistency_report.recommendations,
            }

            # Log critical inconsistencies
            if consistency_report.critical_inconsistencies:
                import logging
                logging.warning(
                    f"Ch{spec.index} CRITICAL world inconsistencies: "
                    f"{len(consistency_report.critical_inconsistencies)} detected"
                )
        except Exception as consistency_exc:
            import logging
            logging.warning(f"Ch{spec.index} World consistency check error: {consistency_exc}")

        # --- Production Card: unified final-draft quality card (Stage A) --------
        # Aggregate all final checks (contract, quality, prose, originality) into
        # a single production card that provides publish recommendation and human
        # approval interface. Stage A Phase 1 (data structure) + Phase 2-6
        # (simplified: reuse existing results, TODO: add true final re-review).
        # P0-1: Now uses canonical ChapterDecision from decision engine.
        production_card_dict = None
        canonical_decision = None  # P0-1: The one true decision
        try:
            from ..production_card import ProductionCard
            from ..decision_engine import ProductionDecisionEngine, load_calibration_status

            # Extract final contract validation results
            final_contract_status = "pass"
            critical_count = 0
            high_count = 0
            if final_contract_validation:
                if final_contract_validation.get("requires_revision"):
                    critical_count = final_contract_validation.get("critical_issues", 0)
                    final_contract_status = "invalid" if critical_count > 0 else "warning"
                high_count = final_contract_validation.get("high_count", 0)

            # P0-1: Use decision engine to compute THE canonical decision
            engine = ProductionDecisionEngine()
            calibration_status = load_calibration_status(project_path)

            # Check if reader simulation was degraded
            reader_sim_degraded = False
            if final_reader_simulation:
                judge_prov = final_reader_simulation.get("judge_provenance", {})
                reader_sim_degraded = judge_prov.get("degraded", False) if isinstance(judge_prov, dict) else False

            canonical_decision = engine.decide_chapter_state(
                critical_deviations=critical_count,
                high_deviations=high_count,
                redline_passed=m7_dict.get("redline_passed", True) if m7_dict else True,
                final_quality_scores=final_quality_scores,
                quality_delta=quality_delta,
                calibration_status=calibration_status,
                dropout_risk=final_dropout_risk,
                reader_simulation_degraded=reader_sim_degraded,
                promises_overdue=promises_pending or [],
                strict_mode=False,  # gate is only defined when enable_contract_gate=True
            )

            # Build Production Card with canonical decision
            production_card = ProductionCard(
                chapter=spec.index,
                draft_hash=chapter_draft["content_hash"],
                draft_timestamp=datetime.now(timezone.utc).isoformat(),

                # Contract status
                contract_status=final_contract_status,
                contract_deviations=len(final_contract_validation.get("deviations", [])) if final_contract_validation else 0,
                critical_deviations=critical_count,
                high_deviations=high_count,
                medium_deviations=final_contract_validation.get("medium_count", 0) if final_contract_validation else 0,
                minor_deviations=final_contract_validation.get("minor_count", 0) if final_contract_validation else 0,

                # Quality scores (TODO Phase 2: add true final re-review)
                # Currently reusing initial qa_review scores
                initial_quality_scores=initial_quality_scores,
                final_quality_scores=final_quality_scores,
                quality_delta=quality_delta,

                # Reader simulation (TODO Phase 3: add final reader simulation)
                reader_simulation=final_reader_simulation,
                dropout_risk=final_dropout_risk,
                continuation_rate=final_continuation_rate,

                # Promise delivery (Stage B.3)
                promises_delivered=promises_delivered,
                promises_pending=promises_pending,

                # P0-3: Governance reports (Stage B.4)
                governance_reports=governance_reports,

                # Prose checks
                prose_checks={
                    "hygiene": hygiene if hygiene else {},
                    "density": density if density else {},
                    "ai_taste": ai_taste if ai_taste else {},
                    "integrity": integrity.to_dict() if integrity else {},
                    "end_hook": end_hook if end_hook else {},
                    "meta_reference": meta_reference if meta_reference else {},
                    "length": length if length else {},
                },

                # M7 originality
                m7_originality=m7_dict if m7_dict else None,
                redline_passed=m7_dict.get("redline_passed", True) if m7_dict else True,

                # Review model
                review_model=str(final_review_model) if final_review_model else None,
                strict_mode=False,

                # P0-1: Canonical decision
                canonical_decision=canonical_decision.to_dict(),
            )

            # P0-1: Derive publish recommendation from canonical decision
            production_card.publish_recommendation = production_card.compute_recommendation()
            production_card.blocking_issues = canonical_decision.blocking_issues
            production_card.warnings = canonical_decision.warnings

            production_card_dict = production_card.to_dict()

            # P0-1: Log decision for visibility (use logging, not print to avoid stdout pollution)
            import logging
            logging.info(f"[decision] ch {spec.index:>2} {canonical_decision}")

        except Exception as pc_exc:
            import logging
            logging.error(f"Ch{spec.index} Production Card/Decision error: {type(pc_exc).__name__}: {pc_exc}")
            # P0-1: Decision failure is a BLOCK
            from ..chapter.state_machine import create_blocked_decision
            canonical_decision = create_blocked_decision(
                reason=f"Decision engine error: {pc_exc}",
                provenance={"error": str(pc_exc)}
            )

        # P0-1: Enforce the canonical decision
        # ADR-003: The serial orchestration never gates. Even BLOCKED chapters are
        # produced and recorded. However, chapters that cannot advance (HELD/BLOCKED)
        # are marked as ok=False and the issue is logged.
        chapter_ok = True
        if canonical_decision and not canonical_decision.can_advance():
            # Chapter is blocked/held - mark as not OK
            chapter_ok = False
            import logging
            logging.warning(f"[held] ch {spec.index:>2} {canonical_decision.state.value} - not advancing")

        # Count as produced regardless (ADR-003: never gates)
        result.produced += 1

        result.chapters.append(ChapterRun(
            spec=spec, ok=chapter_ok, stage="done", message=ex.message,
            draft_hash=chapter_draft["content_hash"],
            state_hash=state.state_hash,
            open_setups=len(state.open_setups),
            events_so_far=len(state.event_order),
            verdict=verdict,
            qa_scores=(_scores if isinstance(_scores, dict) and _scores else None),
            commercial_verdict=commercial_verdict,
            pacing=pacing, pacing_peak=pacing_peak,
            density=density, ai_taste=ai_taste, hygiene=hygiene,
            end_hook=end_hook, meta_reference=meta_reference,
            integrity=(integrity.to_dict() if integrity else None),
            length=length, mandate=mandate_check,
            m7=m7_dict, m7_approval_id=m7_approval_id,
            llm_cost={"total_cost": round(chapter_cost, 8), "currency": total_cost_currency, "pricing_version": total_cost_pricing_version},
            llm_usage=chapter_usage,
            m5_final=m5_final.to_dict(),
            reference_gap=reference_gap,
            budget_note=chapter_budget_note,
            w12=w12_summary,
            contract_validation=contract_validation,
            contract_revision_session=contract_revision_session,
            final_contract_validation=final_contract_validation,
            production_card=production_card_dict,
        ))
        result.chapters[-1].quality_snapshot = quality_snapshot

        # --- A.2 Quality Gate over the FINAL draft (advisory, ADR-003) ---------
        # Wire the Final Quality Gate that was implemented but never called on the
        # production path (Built≠Live). It aggregates the already-computed
        # deterministic signals (integrity / promise debt / cross-chapter length
        # continuity / length vs target / AI-taste) into a single
        # proceed/hold/block recommendation recorded on the ChapterRun. It NEVER
        # gates the serial — the same signals already ride the production card —
        # but centralizes them into the A.2 contract so a human reviewing the
        # run sees one combined final-draft verdict that says when the book may
        # advance versus when it needs a look.
        try:
            from ..chapter.quality_gate import assess_final_quality_gate
            qg_promise_ledger = None
            if promise_ledger is not None:
                # quality_gate expects {id: {created_chapter,status,description}}
                qg_promise_ledger = {
                    p.to_dict()["id"]: {
                        "created_chapter": p.created_at_chapter,
                        "status": "pending" if p.status == "open" else p.status,
                        "description": p.statement,
                    }
                    for p in promise_ledger.promises
                    if p.status == "open"
                }
            qg = assess_final_quality_gate(
                chapter_index=spec.index,
                chapter_draft=chapter_draft,
                chapter_run=result.chapters[-1],
                story_state=state,
                promise_ledger=qg_promise_ledger,
                previous_chapters=[
                    {"body": b} for b in bodies_by_chapter.values()
                ] if bodies_by_chapter else None,
            )
            result.chapters[-1].quality_gate = qg.to_dict()
        except Exception as qg_exc:  # advisory — a gate failure never breaks the serial
            import logging
            logging.warning(f"Ch{spec.index} Quality gate error: "
                            f"{type(qg_exc).__name__}: {qg_exc}")

        # P0-3: Detect event_id reuse (advisory, never gates).
        if spec.event_id in consumed_events:
            print(f"  ⚠️  ch{spec.index:>3} reusing event {spec.event_id} "
                  "(possible event queue exhaustion or indexing error)")
        consumed_events.add(spec.event_id)

        # P0-3: Detect unchanged state_hash (advisory, never gates).
        if prev_state_hash and state.state_hash == prev_state_hash:
            print(f"  ⚠️  ch{spec.index:>3} state_hash unchanged "
                  "(possible state projection failure)")
        prev_state_hash = state.state_hash

        # advance the "story so far" cursor for the NEXT chapter's recap
        prev_event_id = spec.event_id

    result.final_state_hash = last_state_hash
    result.llm_cost = {
        "total_cost": round(total_llm_cost, 8),
        "currency": total_cost_currency,
        "pricing_version": total_cost_pricing_version,
        # 让"真花了钱但没定价"这件事可见。确定性 stub 跑这两个字段是 0/False
        # (没有调用 => 没有低估),所以不改变原有的 cost=null 语义。
        "unpriced_calls": cost_fold.unpriced_calls,
        "understated": cost_fold.is_understated,
    }
    result.cost_warning = cost_fold.warning()
    result.llm_usage = {
        "input": total_input_tokens,
        "output": total_output_tokens,
        "total": total_tokens,
    }

    # --- cross-chapter pacing: the rhythm of climaxes across the whole run ----
    # Folds each produced chapter's peak valence into a climax-rhythm check,
    # measured against the authored cadence (outline.reward_loop.cadence_chapters)
    # when present. Advisory, never gates (ADR-003); runs only when chapters were
    # enriched (peaks exist), else stays None and behavior is unchanged.
    peaks = [c.pacing_peak for c in result.chapters if c.pacing_peak is not None]
    if len(peaks) >= 2:
        from ..scene import check_serial_pacing
        cadence = None
        if outline:
            rl = outline.get("reward_loop") or {}
            c = rl.get("cadence_chapters")
            cadence = c if isinstance(c, int) and c >= 1 else None
        result.serial_pacing = check_serial_pacing(peaks, cadence=cadence).to_dict()

    # --- cross-chapter mandate: tension-stall + spinning-in-place over the run --
    # Folds the produced NarrativeMandate sequence into the 张力停滞/原地打转 check
    # (escalation flat run / reversible net-advance run). Advisory, never gates
    # (ADR-003); runs only when mandates exist (v8), else stays None so a v1-v7
    # run's result is byte-identical.
    if len(mandates) >= 2:
        from ..director import check_mandate_series
        result.mandate_series = check_mandate_series(mandates).to_dict()

    # --- cross-chapter openings: 开篇雷同 across the run (§14 anti-AI) ----------
    # Folds each produced chapter's opening into a repetition check the
    # single-chapter ai_taste structurally cannot see (each chapter opens once).
    # Advisory, never gates (ADR-003); runs only with >=2 produced bodies, else
    # stays None so a short/empty run's result is byte-identical.
    if len([b for b in chapter_bodies if b]) >= 2:
        from ..scene import check_serial_openings
        result.serial_openings = check_serial_openings(chapter_bodies).to_dict()

    # --- cross-chapter function repetition: 功能重复/原地打转 (W11-03) -----------
    # Folds each produced chapter's structural function signature (objective +
    # mandate) into a repetition check the single-chapter detectors cannot see
    # (each chapter carries its signature exactly once). Warns on continuous /
    # cyclical / renamed-same-function repetition. Advisory, never gates
    # (ADR-003); runs only with >=2 signatures, else stays None so a short run's
    # result is byte-identical. objectives exist on v6+; a run without them still
    # folds (None signatures) and degrades cleanly.
    if len(function_sigs) >= 2:
        from ..scene import check_serial_function_repeat
        result.function_repeat = check_serial_function_repeat(function_sigs).to_dict()

    # --- cross-chapter genre drift: 题材漂移 across the run (§4.3 退化梯度) -------
    # Folds each produced body's genre-discriminant-marker density into a trend
    # check. The model's prior leans 玄幻, so an unconstrained run drifts toward
    # generic 升级流 — chapter 30 reads less like its declared subgenre than
    # chapter 3. No single-chapter detector can see this (a uniformly drifted book
    # looks locally fine everywhere); it is a book-level trend, so it needs a
    # book-level fold. Marker density is a PROXY, so this is advisory and never
    # gates (ADR-003). Runs only with enough bodies AND a known genre, else stays
    # None so a short run / unknown-genre run is byte-identical.
    if len([b for b in chapter_bodies if b]) >= 2:
        from ..scene import check_serial_genre_drift
        from ..genre_taxonomy import extract_authored_markers
        drift_genre = None
        if outline:
            genres = outline.get("genre") or []
            drift_genre = genres[0] if isinstance(genres, list) and genres else None
            if not drift_genre:
                drift_genre = ((outline.get("market_position") or {})
                               .get("sub_genre") or None)
        # The book's OWN coined terms are the primary instrument — the stock genre
        # table is only the fallback. Measured on the real 33ch baseline: stock 都市
        # words scored 20 hits in ~177k chars and called 31/33 chapters genre-less,
        # while this book's coinages (梦墟/核心执念/梦晶) appeared ~1400 times. Reading
        # the coinages out of the AUTHORED outline (plus Brain when present) keeps
        # the yardstick independent of whatever the model drifted into.
        authored_markers = extract_authored_markers(
            *(s for s in (outline, genre_brain) if isinstance(s, dict)))
        result.genre_drift = check_serial_genre_drift(
            chapter_bodies, drift_genre,
            authored_markers=authored_markers).to_dict()

    # --- packaging promise delivery (§3.3 承诺一致性, all versions) --------------
    # The packaging (书名/一句话卖点/简介/标签) decides 点击 — whether a reader opens
    # the book at all — and its promises decide whether the opening chapters read as
    # honored or as bait. Those are the two funnel terms with the most reader loss
    # and, until now, no tooling at all. Folds the AUTHORED promises against the
    # produced bodies: was each promise's evidence visible by the chapter the author
    # promised it? Keyed by REAL chapter number, because the window is "by chapter
    # N" and --start-chapter makes a flat index lie. Absent packaging => a clean
    # info note, so every existing project is unaffected. Advisory, never gates
    # (ADR-003); authority stays human (ADR-009).
    if bodies_by_chapter:
        from ..packaging import check_promise_delivery, load_packaging
        result.packaging_delivery = check_promise_delivery(
            load_packaging(project_path), bodies_by_chapter).to_dict()

    # --- Promise Ledger summary (Stage B, all versions) --------------------------
    # Include Promise Ledger summary in the result for visibility. This shows the
    # overall promise tracking state: total promises, by type, by status, etc.
    # Advisory only (ADR-003), never gates. When ledger is absent (no packaging or
    # no promises), this field stays None so runs without promises are byte-identical.
    if promise_ledger:
        result.promise_ledger = {
            "summary": promise_ledger.to_dict()["summary"],
            "gating": False,
            "reviewer": promise_ledger.reviewer,
        }

    # --- persist the per-chapter run (the four §14 detectors) -----------------
    # Until now the ChapterRun — pacing / density / ai_taste / end_hook — lived
    # only in the in-memory result and the printed log; nothing on disk carried
    # the detector readings, so per-chapter quality history could not be folded
    # by the dashboard or audited after the run. Write each ChapterRun as its own
    # derived artifact (category "chapter-run", keyed run-<task_id> like the
    # cr-/scene-/ir- per-chapter artifacts), idempotent on re-run. Advisory read-
    # side data only — writes no facts (ADR-006), never gates (ADR-003).
    for c in result.chapters:
        cr_dict = c.to_dict()
        derived.write_artifact(
            project_path=project_path, category="chapter-run",
            artifact_id=f"run-{c.spec.task_id}", artifact=cr_dict,
            serialized=_json.dumps(cr_dict, ensure_ascii=False, indent=2) + "\n")
        if c.index if hasattr(c, 'index') else False:
            pass
        if c.m5_final:
            derived.write_artifact(
                project_path=project_path, category="chapter-final",
                artifact_id=f"final-{c.spec.task_id}", artifact=c.m5_final,
                serialized=_json.dumps(c.m5_final, ensure_ascii=False, indent=2) + "\n")
        if c.spec.index in CHECKPOINT_INDICES:
            # P0-3: Validate checkpoint completeness before writing.
            # Missing fields are still written (for audit), but flagged so incomplete
            # checkpoints don't silently pollute 复盘/baseline reports.
            incomplete_fields = []
            if not c.ok:
                incomplete_fields.append("chapter_failed")
            if not c.draft_hash:
                incomplete_fields.append("draft_hash")
            if not c.m5_final or not c.m5_final.get("final_hash"):
                incomplete_fields.append("final_hash")
            if not c.m7:
                incomplete_fields.append("m7")
            if not c.quality_snapshot:
                incomplete_fields.append("quality_snapshot")

            if incomplete_fields:
                print(f"  ⚠️  checkpoint cp-{c.spec.index:03d} incomplete: "
                      f"missing {', '.join(incomplete_fields)}")

            # Shared builder (checkpoints.py) is the single source of truth for the
            # checkpoint shape, so a checkpoint written live here is byte-identical
            # to one the backfill projection folds from the persisted chapter-run.
            checkpoint = build_checkpoint(
                chapter_index=c.spec.index,
                chapter_id=c.spec.task_id,
                event_id=c.spec.event_id,
                draft_hash=c.draft_hash,
                state_hash=c.state_hash,
                final_hash=(c.m5_final or {}).get("final_hash"),
                verdict=c.verdict,
                commercial_verdict=c.commercial_verdict,
                quality_snapshot=c.quality_snapshot,
                m7=c.m7,
            )

            # P0-3: Mark incomplete checkpoints for filtering in复盘 queries.
            if incomplete_fields:
                checkpoint["_incomplete_fields"] = incomplete_fields

            derived.write_artifact(
                project_path=project_path, category="serial-checkpoints",
                artifact_id=f"cp-{c.spec.index:03d}", artifact=checkpoint,
                serialized=_json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n")

            # N100-074: at each checkpoint, project the next 10-20 chapter window
            # from the work's long-arc into a rolling plan and persist it. Pure
            # deterministic fold (ADR-008); forward-only (never rewrites completed
            # chapters); advisory (ADR-003) — a projection failure degrades to no
            # rolling plan and never breaks the run. Closes the built≠live gap:
            # rolling_plan.py had no producer on the real path.
            if outline:
                try:
                    from ..long_arc.plan import build_long_arc_plan
                    from .rolling_plan import build_rolling_plan
                    long_arc = build_long_arc_plan(outline).to_dict()
                    rolling = build_rolling_plan(
                        long_arc, checkpoint=f"cp-{c.spec.index:03d}",
                        current_chapter=c.spec.index)
                    derived.write_artifact(
                        project_path=project_path, category="rolling-plans",
                        artifact_id=f"rolling-{c.spec.index:03d}", artifact=rolling,
                        serialized=_json.dumps(rolling, ensure_ascii=False, indent=2) + "\n")
                except Exception:
                    pass  # advisory: rolling plan is a projection, never gates

    return result
