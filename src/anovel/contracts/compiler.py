"""Pure finite compilation of explicit plans, never generation or Canon mutation.

The supplied KnowledgeState remains an author input. Only declared knowledge /
reveal constraints are checked; this is not a full semantic or Q3 checker.
Hypothetical reducer metadata never becomes evidence for an accepted chapter.
"""

from __future__ import annotations

from hashlib import sha256

from anovel.canon.identity import canonical_bytes
from anovel.contracts.models import (
    BoundTransition,
    CanonView,
    CompilationResult,
    CompiledContract,
    CompiledScene,
    ContinuationEvidence,
    Diagnostic,
    KnowledgeSnapshot,
    ReplanRequest,
    RetainedInput,
)
from anovel.domain.delta import (
    FactPath,
    FactState,
    FactStatus,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    preview_delta,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import IntentStatus, KnowledgeState
from anovel.genre.extensions.registration import registered_extensions
from anovel.genre.policy import GenrePolicy
from anovel.planning.models import ChapterPlan, ScenePlan, StoryFixture, TransitionKind
from anovel.planning.versions import PlanHistory


def _failure(
    code: str,
    message: str,
    history: PlanHistory | None,
    chapter_id: EntityId | None,
    scene_id: EntityId | None = None,
) -> CompilationResult:
    diagnosis = Diagnostic(code, message, scene_id)
    replan = None
    if (
        history is not None
        and chapter_id is not None
        and chapter_id.project == history.active.project
    ):
        replan = ReplanRequest(history.active.content_hash, (chapter_id,), (code,))
    return CompilationResult(None, (diagnosis,), replan)


def _ending_error(
    view: CanonView, continuity: ContinuationEvidence | None
) -> str | None:
    if view.previous is None:
        return (
            None
            if continuity is None
            else "The first chapter explicitly has no preceding prose."
        )
    if type(continuity) is not ContinuationEvidence:
        return (
            "The next chapter requires source-bound actual predecessor ending evidence."
        )
    previous = view.previous
    prose = previous.prose
    text = prose.decode("utf-8")
    if (
        continuity.previous_commit_id != view.parent_ref
        or continuity.previous_commit_id != previous.receipt.commit_id
        or continuity.candidate_id != previous.candidate_id
        or continuity.prose_hash != sha256(prose).hexdigest()
        or continuity.start >= len(text)
        or continuity.end != len(text)
        or text[continuity.start : continuity.end] != continuity.quote
    ):
        return "Predecessor commit, raw prose hash, candidate or exact ending span changed."
    return None


def _known_current(
    knowledge: KnowledgeState, view: CanonView, actor: EntityId, fact_id: EntityId
) -> bool:
    snapshot = view.baseline.get(fact_id)
    if snapshot is None or snapshot.state.status is not FactStatus.KNOWN:
        return False
    try:
        acquired = knowledge.require_known(actor, fact_id)
    except ValueError:
        return False
    return (
        acquired.proposition.subject == snapshot.seed_fact.proposition.subject
        and acquired.proposition.predicate == snapshot.seed_fact.proposition.predicate
        and FactState.known(acquired.proposition.value) == snapshot.state
    )


def _scene_diagnostics(
    scene: ScenePlan,
    chapter: ChapterPlan,
    fixture: StoryFixture,
    view: CanonView,
    knowledge: KnowledgeState,
) -> tuple[Diagnostic, ...]:
    issues: list[Diagnostic] = []
    entity_ids = {v.id for v in view.root.seed.entities}
    known_actors = {v.id for v in knowledge.characters}
    for fact_id in (*scene.protected_fact_ids, *(v.target_id for v in scene.forbidden)):
        if view.baseline.get(fact_id) is None:
            issues.append(
                Diagnostic(
                    "UNREGISTERED_CONSTRAINT_TARGET",
                    "A protected or forbidden target is absent from actual Canon.",
                    scene.id,
                )
            )
    for boundary in scene.knowledge_boundaries:
        if boundary.actor_id not in known_actors or boundary.actor_id not in entity_ids:
            issues.append(
                Diagnostic(
                    "UNREGISTERED_KNOWLEDGE_ACTOR",
                    "Knowledge boundary actor is not a registered character.",
                    scene.id,
                )
            )
            continue
        for fact_id in boundary.must_know:
            if not _known_current(knowledge, view, boundary.actor_id, fact_id):
                issues.append(
                    Diagnostic(
                        "REQUIRED_KNOWLEDGE_UNAVAILABLE",
                        "World truth or belief alone does not establish current acquired knowledge.",
                        scene.id,
                    )
                )
        for fact_id in boundary.must_not_know:
            if view.baseline.get(fact_id) is None:
                issues.append(
                    Diagnostic(
                        "UNREGISTERED_CONSTRAINT_TARGET",
                        "Forbidden knowledge target is absent from Canon.",
                        scene.id,
                    )
                )
            elif any(
                holder == boundary.actor_id and target == fact_id
                for holder, target, _source in knowledge.knowledge
            ):
                issues.append(
                    Diagnostic(
                        "FORBIDDEN_KNOWLEDGE_ACQUIRED",
                        "The supplied character has already acquired this protected information.",
                        scene.id,
                    )
                )
    intents = {v.id: v for v in knowledge.intents}
    beliefs = {v.id: v for v in knowledge.beliefs}
    for intent_id in scene.intent_ids:
        intent = intents.get(intent_id)
        if intent is None or intent.status is not IntentStatus.PLANNED:
            issues.append(
                Diagnostic(
                    "INTENT_UNAVAILABLE",
                    "Scene intention is absent or cancelled.",
                    scene.id,
                )
            )
            continue
        # Incorrect beliefs remain legitimate intentions. Acquired facts must
        # still agree with actual Canon when used as a declared factual basis.
        for basis in intent.based_on:
            if basis not in beliefs and not _known_current(
                knowledge, view, intent.owner, basis
            ):
                issues.append(
                    Diagnostic(
                        "INTENT_KNOWLEDGE_STALE",
                        "Intention uses an unacquired or outdated factual basis.",
                        scene.id,
                    )
                )
    reveals = {v.fact_id: v.not_before for v in fixture.reader_boundaries}
    position = NarrativePosition(chapter.number, scene.order)
    for fact_id in scene.reveal_fact_ids:
        if view.baseline.get(fact_id) is None:
            issues.append(
                Diagnostic(
                    "REVEAL_TARGET_UNAVAILABLE",
                    "Revealed fact is absent from actual Canon.",
                    scene.id,
                )
            )
        elif fact_id in reveals and position < reveals[fact_id]:
            issues.append(
                Diagnostic(
                    "EARLY_REVEAL",
                    "Explicit reveal intent precedes its frozen reader boundary.",
                    scene.id,
                )
            )
    return tuple(issues)


def compile_contract(
    history: PlanHistory,
    chapter_id: EntityId,
    fixture: StoryFixture,
    canon_view: CanonView,
    continuity: ContinuationEvidence | None = None,
    *,
    knowledge_snapshot: KnowledgeSnapshot | None = None,
) -> CompilationResult:
    """Compile one next chapter deterministically, without model or DB writes.

    A structural APPROVED/ref pair is a supplied attestation, not an independent
    verification of human identity. Real fixture acceptance is separately bound
    to the actual Owner input by the task evidence / trusted caller.
    """
    if (
        type(history) is not PlanHistory
        or type(chapter_id) is not EntityId
        or type(fixture) is not StoryFixture
        or type(canon_view) is not CanonView
    ):
        return _failure(
            "INVALID_INPUT_TYPE",
            "Exact immutable planning/fixture/Canon values are required.",
            None,
            None,
        )
    active = history.active
    if fixture.review_status != "APPROVED" or fixture.review_ref is None:
        return _failure(
            "FIXTURE_REVIEW_REQUIRED",
            "Actual human story review remains required; DRAFT is not an approved author input.",
            history,
            chapter_id,
        )
    if {chapter_id.project, fixture.project, active.id.project, canon_view.project} != {
        fixture.project
    }:
        return _failure(
            "SCOPE_MISMATCH",
            "Planning, fixture and actual Canon belong to different projects.",
            history,
            chapter_id,
        )
    if active.fixture_hash != fixture.content_hash:
        return _failure(
            "STALE_FIXTURE_BINDING",
            "The adopted plan binds different story/knowledge/Pack input bytes.",
            history,
            chapter_id,
        )
    if (
        history.versions[0].fixture_hash == fixture.content_hash
        and history.versions[0].vision != fixture.vision
    ):
        return _failure(
            "INITIAL_VISION_MISMATCH",
            "Initial plan must preserve the actual reviewed fixture vision.",
            history,
            chapter_id,
        )
    if canonical_bytes(fixture.root_seed.to_dict()) != canonical_bytes(
        canon_view.root.seed.to_dict()
    ):
        return _failure(
            "CANON_ROOT_MISMATCH",
            "Manual initial facts differ from the actual retained Canon root.",
            history,
            chapter_id,
        )
    try:
        chapter = active.vision.chapter(chapter_id)
    except ValueError as error:
        return _failure("CHAPTER_NOT_REGISTERED", str(error), history, chapter_id)
    if chapter.number != canon_view.next_chapter:
        return _failure(
            "CHAPTER_NOT_NEXT",
            "Only the chapter following this accepted historical target can be compiled.",
            history,
            chapter_id,
        )
    ending_error = _ending_error(canon_view, continuity)
    if ending_error is not None:
        return _failure("CONTINUATION_MISMATCH", ending_error, history, chapter_id)
    registry = registered_extensions()
    try:
        registry.validate_baseline(canon_view.baseline)
        policy = GenrePolicy(fixture.pack_binding).check_strategy(
            fixture.pack_binding.select_strategy()
        )
        if any(
            v.pack_bytes != canonical_bytes(fixture.pack_binding.to_dict())
            for v in canon_view.baseline.extensions
        ):
            return _failure(
                "PACK_BINDING_MISMATCH",
                "Canon root and author input retain different exact GenrePacks.",
                history,
                chapter_id,
            )
    except ValueError as error:
        return _failure("GENRE_BINDING_INVALID", str(error), history, chapter_id)
    try:
        if knowledge_snapshot is None:
            knowledge_snapshot = KnowledgeSnapshot(
                fixture.project,
                canon_view.parent_ref,
                "initial-fixture:" + fixture.content_hash,
                fixture.knowledge_bytes,
            )
        if type(knowledge_snapshot) is not KnowledgeSnapshot:
            raise ValueError("an exact immutable knowledge snapshot is required")
        knowledge_snapshot.validate_against(canon_view)
        knowledge = knowledge_snapshot.knowledge
    except ValueError as error:
        return _failure("KNOWLEDGE_SNAPSHOT_INVALID", str(error), history, chapter_id)
    scenes: list[CompiledScene] = []
    seen: set[EntityId] = set()
    all_bound: list[tuple[int, BoundTransition]] = []
    for scene in chapter.scenes:
        protected = set(scene.protected_fact_ids)
        forbidden = scene.forbidden
        diagnoses = _scene_diagnostics(scene, chapter, fixture, canon_view, knowledge)
        if diagnoses:
            return CompilationResult(
                None,
                diagnoses,
                ReplanRequest(
                    active.content_hash, (chapter_id,), tuple(v.code for v in diagnoses)
                ),
            )
        bound: list[BoundTransition] = []
        for spec in scene.required:
            if spec.target_id in seen:
                return _failure(
                    "DUPLICATE_REQUIRED_TARGET",
                    "A chapter cannot silently merge repeated target changes across scenes.",
                    history,
                    chapter_id,
                    scene.id,
                )
            seen.add(spec.target_id)
            if (
                spec.target_id in protected
                and spec.operation is not TransitionKind.NO_CHANGE
            ):
                return _failure(
                    "PROTECTED_FACT_CONFLICT",
                    "Required transition changes an explicitly protected fact.",
                    history,
                    chapter_id,
                    scene.id,
                )
            if any(
                v.target_id == spec.target_id
                and v.operation is spec.operation
                and (
                    spec.operation is not TransitionKind.SET_FACT
                    or (
                        v.value is not None
                        and spec.value is not None
                        and FactState.known(v.value) == FactState.known(spec.value)
                    )
                )
                for v in forbidden
            ):
                return _failure(
                    "FORBIDDEN_TRANSITION_CONFLICT",
                    "Required transition matches an explicit forbidden operation/value.",
                    history,
                    chapter_id,
                    scene.id,
                )
            snapshot = canon_view.baseline.get(spec.target_id)
            if snapshot is None:
                return _failure(
                    "REQUIRED_TARGET_UNAVAILABLE",
                    "Required target is absent from the actual Canon baseline.",
                    history,
                    chapter_id,
                    scene.id,
                )
            try:
                item = BoundTransition(spec, Precondition.from_snapshot(snapshot))
            except ValueError as error:
                return _failure(
                    "STALE_REQUIRED_STATE", str(error), history, chapter_id, scene.id
                )
            bound.append(item)
            all_bound.append((scene.order, item))
        scenes.append(CompiledScene(scene, tuple(bound)))
    if all_bound:
        # Explicitly hypothetical: metadata does not become retained prose
        # evidence, an Observation, a Permit, or a Canon operation receipt.
        source = EntityId(
            fixture.project, "hypothetical-plan-only:" + active.content_hash
        )
        auth = "HYPOTHETICAL_PLAN_ONLY"
        operations = tuple(
            item.materialize(
                OperationMeta(
                    EntityId(fixture.project, "hypothetical-op:" + str(index)),
                    item.target_id,
                    FactPath.VALUE,
                    item.expected,
                    ProseEvidence(
                        source,
                        NarrativePosition(chapter.number, order),
                        "HYPOTHETICAL_PLAN_ONLY/not-prose-evidence",
                    ),
                    auth,
                )
            )
            for index, (order, item) in enumerate(all_bound)
        )
        try:
            delta = NarrativeDelta(
                EntityId(fixture.project, "hypothetical-delta:" + chapter.content_hash),
                canon_view.branch,
                canon_view.parent_ref,
                source,
                operations,
            )
            preview_delta(
                canon_view.baseline,
                delta,
                source_id=source,
                authorization_refs=frozenset({auth}),
                extension_registry=registry,
            )
        except ValueError as error:
            return _failure(
                "REQUIRED_TRANSITIONS_INAPPLICABLE", str(error), history, chapter_id
            )
    inputs = (
        RetainedInput("fixture", canonical_bytes(fixture.to_dict())),
        RetainedInput("plan", canonical_bytes(active.to_dict())),
        RetainedInput("plan_history", canonical_bytes(history.to_dict())),
        RetainedInput("canon", canonical_bytes(canon_view.to_dict())),
        RetainedInput("pack", canonical_bytes(fixture.pack_binding.to_dict())),
        RetainedInput("knowledge", canonical_bytes(knowledge_snapshot.to_dict())),
        RetainedInput(
            "continuity",
            canonical_bytes(None if continuity is None else continuity.to_dict()),
        ),
    )
    contract = CompiledContract(
        canon_view.project,
        canon_view.branch,
        canon_view.parent_ref,
        chapter.id,
        chapter.number,
        active.id,
        active.revision,
        active.content_hash,
        fixture.content_hash,
        canon_view.content_hash,
        fixture.pack_binding.ref.content_hash,
        inputs[-2].content_hash,
        inputs[-1].content_hash,
        policy.policy_version,
        policy.policy_hash,
        tuple(scenes),
        inputs,
    )
    return CompilationResult(contract, ())


def contract_is_current(
    contract: CompiledContract,
    history: PlanHistory,
    chapter_id: EntityId,
    fixture: StoryFixture,
    canon_view: CanonView,
    continuity: ContinuationEvidence | None = None,
    *,
    knowledge_snapshot: KnowledgeSnapshot | None = None,
) -> bool:
    """Recompile against explicit current inputs; hashes alone never self-renew."""
    if type(contract) is not CompiledContract:
        return False
    result = compile_contract(
        history,
        chapter_id,
        fixture,
        canon_view,
        continuity,
        knowledge_snapshot=knowledge_snapshot,
    )
    return (
        result.contract is not None
        and contract.content_hash == result.contract.content_hash
    )
