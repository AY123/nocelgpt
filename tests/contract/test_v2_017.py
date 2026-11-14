"""Finite contract compilation over explicit component-only author inputs.

Synthetic APPROVED labels test structural behavior, not a human review event.
The separately provided project Story Fixtures require actual Owner review.
No fake read value here is claimed as real PostgreSQL or production permission.
"""

import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import pytest

from anovel.canon.chapter import CandidateEvidence, ChapterCandidate, StoredChapter
from anovel.canon.identity import canonical_bytes
from anovel.canon.models import CommitReceipt, RootSeed, StoredRoot
from anovel.contracts.compiler import compile_contract, contract_is_current
from anovel.contracts.models import CanonView, CompiledContract, ContinuationEvidence
from anovel.domain.character import Character
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactState,
    MarkUnknown,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    SetFact,
    preview_delta,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import (
    Belief,
    Goal,
    Intent,
    KnowledgeLevel,
    KnowledgeState,
    Observation,
    Proposition,
    WorldFact,
)
from anovel.genre.registry import GenreRegistry, PackRef
from anovel.planning.models import (
    ArcPlan,
    ChapterPlan,
    ForbiddenTransition,
    KnowledgeBoundary,
    RequiredTransition,
    RevealBoundary,
    ScenePlan,
    SeriesVision,
    StoryFixture,
    TransitionKind,
)
from anovel.planning.replanning import assess_changes, propose_revision
from anovel.planning.versions import (
    PlanHistory,
    PlanVersion,
    adopt_revision,
    freeze_chapters,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "contract-component"
BRANCH = "main"
PARENT = "sha256:" + "a" * 64
REVIEW = "component-test-only/not-real-human-evidence"


def eid(name, project=PROJECT):
    return EntityId(project, name)


def pack(anchor="urban.business.realistic", version="1.0.0", project=PROJECT):
    source = ROOT / "specs/genres"
    row = next(
        r
        for r in json.loads((source / "registry.yaml").read_text())["packs"]
        if r["id"] == anchor and r["version"] == version
    )
    return GenreRegistry.from_directory(source).bind(
        project, PackRef(row["id"], row["version"], row["content_hash"])
    )


def make_case(
    *,
    anchor="urban.business.realistic",
    required=(),
    forbidden=(),
    protected=(),
    boundaries=(),
    reveals=(),
    reader_boundaries=(),
    review="APPROVED",
    with_intent=False,
):
    alice, bob = Character(eid("alice"), "甲"), Character(eid("bob"), "乙")
    facts = (
        WorldFact(
            eid("balance"), Proposition(alice.id, "balance", 10), "supplied-root"
        ),
        WorldFact(
            eid("secret"), Proposition(bob.id, "conceals-defect", True), "supplied-root"
        ),
    )
    knowledge = KnowledgeState(PROJECT, (alice, bob))
    for f in facts:
        knowledge.add_fact(f)
    for name, fact, holder in [
        ("observation-balance", facts[0], alice.id),
        ("observation-secret", facts[1], bob.id),
    ]:
        obs = Observation(
            eid(name), fact.id, frozenset({holder}), "supplied-observation"
        )
        knowledge.add_observation(obs)
        knowledge.learn(holder, fact.id, obs.id)
    false_belief = Belief(
        eid("false-belief"),
        alice.id,
        Proposition(bob.id, "conceals-defect", False),
        "supplied-rumor",
    )
    knowledge.add_belief(false_belief)
    knowledge.add_goal(Goal(eid("goal"), alice.id, "在不伪造记录的前提下保住作坊。"))
    knowledge.add_intent(
        Intent(
            eid("intent"),
            alice.id,
            eid("goal"),
            "根据自己的错误判断与对方谈判。",
            (false_belief.id,),
            "可能失去信任。",
        )
    )
    scene = ScenePlan(
        eid("scene-1"),
        1,
        "安静谈话或有限事实变化。",
        required=required,
        forbidden=forbidden,
        protected_fact_ids=protected,
        intent_ids=(eid("intent"),) if with_intent else (),
        knowledge_boundaries=boundaries,
        reveal_fact_ids=reveals,
    )
    first = ChapterPlan(
        eid("chapter-1"),
        1,
        "从给定初始事实开始。",
        (scene,),
        start_intent="甲走进作坊，处理眼前的选择。",
    )
    second = ChapterPlan(
        eid("chapter-2"),
        2,
        "承接上一章实际落点。",
        (ScenePlan(eid("scene-2"), 1, "核对旧账并改变判断。"),),
        start_intent="承接门外停住的脚步，而非重新开始。",
    )
    vision = SeriesVision(
        eid("vision"),
        "资源有限的主角用选择与代价推进冲突。",
        "取得能够公开检验的证据。",
        (ArcPlan(eid("arc"), "成功引出新的利益冲突。", (first, second)),),
    )
    seed = RootSeed(
        tuple(Entity(c.id, c.display_name) for c in (alice, bob)), (), facts
    )
    fixture = StoryFixture(
        eid("fixture"),
        "development",
        pack(anchor),
        seed,
        canonical_bytes(knowledge.to_dict()),
        reader_boundaries,
        vision,
        review_status=review,
        review_ref=REVIEW if review == "APPROVED" else None,
        world_boundaries=("遵守显式冻结题材机制。",),
        conflict_engine="证据、利益与信任冲突相互影响。",
        choice_costs=("公开事实可能失去订单。",),
        opponent_adaptation=("对手看见行动后调整合作条件。",),
        reader_promises=("主角会为错误判断付出代价。",),
    )
    version = PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash)
    history = PlanHistory((version,))
    receipt = CommitReceipt(
        PROJECT,
        BRANCH,
        "synthetic-root",
        PARENT,
        "b" * 64,
        "2026-11-14T00:00:00.000000Z",
    )
    root = StoredRoot(
        receipt,
        seed,
        "组件根输入，不是真实数据库来源。".encode(),
        b"synthetic-authority",
    )
    baseline = FactBaseline.from_world_facts(PROJECT, BRANCH, PARENT, facts)
    return fixture, history, CanonView(root, baseline, None, 1)


def compile_case(fixture, history, view, chapter="chapter-1", continuity=None):
    return compile_contract(history, eid(chapter), fixture, view, continuity)


def change_future(vision, *, first=False):
    arc = vision.arcs[0]
    chapters = list(arc.chapters)
    index = 0 if first else 1
    chapters[index] = replace(chapters[index], purpose="新的、明确记录理由的未来意图。")
    return replace(vision, arcs=(replace(arc, chapters=tuple(chapters)),))


def component_previous(view, change_value=None):
    text = "\ufeff第一句保留原始换行。\r\n门外脚步停住，她没有立刻开门。"
    prose = text.encode()
    snapshot = view.baseline.get(eid("balance"))
    source = eid("accepted-component-chapter")
    evidence = ProseEvidence(source, NarrativePosition(1, 1), "component-only/prose")
    meta = OperationMeta(
        eid("prior-op"),
        snapshot.seed_fact.id,
        FactPath.VALUE,
        Precondition.from_snapshot(snapshot),
        evidence,
        "component-only",
    )
    op = NoChange(meta) if change_value is None else SetFact(meta, change_value)
    delta = NarrativeDelta(eid("prior-delta"), BRANCH, PARENT, source, (op,))
    dependencies = tuple(
        CandidateEvidence(
            kind,
            ("component " + kind).encode(),
            "test/" + kind.lower(),
            "1.0",
            "component-test",
            "1.0",
        )
        for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
    )
    candidate = ChapterCandidate(source, BRANCH, PARENT, 1, prose, delta, dependencies)
    receipt = CommitReceipt(
        PROJECT,
        BRANCH,
        "synthetic-chapter",
        "sha256:" + "c" * 64,
        candidate.payload_hash,
        "2026-11-14T00:00:01.000000Z",
    )
    state = preview_delta(
        view.baseline,
        delta,
        source_id=source,
        authorization_refs=frozenset({"component-only"}),
    ).candidate
    previous = StoredChapter(receipt, candidate, state, b"component-only-not-a-permit")
    current = replace(state, parent_ref=receipt.commit_id)
    later = CanonView(view.root, current, previous, 2)
    start = text.index("门外")
    continuity = ContinuationEvidence(
        receipt.commit_id,
        source,
        sha256(prose).hexdigest(),
        start,
        len(text),
        text[start:],
        evidence_ref="component-only/actual-ending",
    )
    return later, continuity


@pytest.mark.parametrize(
    "anchor", ["urban.business.realistic", "fantasy.eastern.progression"]
)
def test_two_anchors_compile_without_genesis_and_retain_exact_inputs(anchor):
    fixture, history, view = make_case(anchor=anchor)
    before = canonical_bytes(view.to_dict())
    result = compile_case(fixture, history, view)
    assert result.ok and result.contract is not None and result.diagnostics == ()
    contract = result.contract
    assert contract.parent_ref == PARENT and contract.chapter_number == 1
    assert contract.required == ()
    assert compile_case(fixture, history, view).contract == contract
    assert CompiledContract.from_dict(contract.to_dict()) == contract
    assert len(contract.retained_inputs) > 0
    assert canonical_bytes(view.to_dict()) == before
    assert not hasattr(contract, "permit")


@pytest.mark.parametrize(
    "kind,value,operation",
    [
        (TransitionKind.SET_FACT, 20, SetFact),
        (TransitionKind.MARK_UNKNOWN, None, MarkUnknown),
        (TransitionKind.RETRACT_FACT, None, RetractFact),
        (TransitionKind.NO_CHANGE, None, NoChange),
    ],
)
def test_required_transition_materializes_existing_delta_with_full_precondition(
    kind, value, operation
):
    spec = RequiredTransition(eid("balance"), kind, value)
    fixture, history, view = make_case(required=(spec,))
    result = compile_case(fixture, history, view)
    assert result.ok
    bound = result.contract.required[0]
    snapshot = view.baseline.get(eid("balance"))
    assert bound.expected == Precondition.from_snapshot(snapshot)
    prose = ProseEvidence(
        eid("real-future-prose"), NarrativePosition(1, 1), "supplied-source"
    )
    meta = OperationMeta(
        eid("actual-op"),
        eid("balance"),
        FactPath.VALUE,
        bound.expected,
        prose,
        "actual-authorization-reference",
    )
    actual = bound.materialize(meta)
    assert type(actual) is operation
    delta = NarrativeDelta(
        eid("actual-delta"), BRANCH, PARENT, prose.source_id, (actual,)
    )
    preview = preview_delta(
        view.baseline,
        delta,
        source_id=prose.source_id,
        authorization_refs=frozenset({meta.authorization_ref}),
    )
    assert view.baseline.get(eid("balance")).state == FactState.known(10)
    if kind is TransitionKind.NO_CHANGE:
        assert preview.candidate == view.baseline
    else:
        assert preview.candidate.get(eid("balance")).revision == snapshot.revision + 1


@pytest.mark.parametrize("fault", ["wrong-target", "wrong-state", "wrong-revision"])
def test_bound_transition_cannot_use_unrelated_future_operation_metadata(fault):
    fixture, history, view = make_case(
        required=(RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 20),)
    )
    bound = compile_case(fixture, history, view).contract.required[0]
    meta = OperationMeta(
        eid("op"),
        eid("balance"),
        FactPath.VALUE,
        bound.expected,
        ProseEvidence(eid("prose"), NarrativePosition(1, 1), "actual-prose"),
        "authorization",
    )
    if fault == "wrong-target":
        meta = replace(meta, target_id=eid("secret"))
    elif fault == "wrong-state":
        meta = replace(
            meta, expected=replace(bound.expected, state=FactState.known(999))
        )
    else:
        meta = replace(meta, expected=replace(bound.expected, revision=4))
    with pytest.raises(ValueError):
        bound.materialize(meta)


@pytest.mark.parametrize("value", [None, [], {}, float("inf"), float("nan")])
def test_required_set_requires_a_nonnull_finite_scalar(value):
    with pytest.raises(ValueError):
        RequiredTransition(eid("balance"), TransitionKind.SET_FACT, value)


@pytest.mark.parametrize(
    "kind",
    [
        TransitionKind.MARK_UNKNOWN,
        TransitionKind.RETRACT_FACT,
        TransitionKind.NO_CHANGE,
    ],
)
def test_non_set_transitions_reject_hidden_value_payload(kind):
    with pytest.raises(ValueError):
        RequiredTransition(eid("balance"), kind, 5)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "protected",
        "forbidden",
        "wrong-type",
        "stale-state",
        "missing-target",
    ],
)
def test_conflicting_or_inapplicable_requirements_return_diagnostics_without_changing_canon(
    fault,
):
    spec = RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 20)
    opts = {"required": (spec,)}
    if fault == "duplicate":
        opts["required"] = (spec, spec)
    elif fault == "protected":
        opts["protected"] = (eid("balance"),)
    elif fault == "forbidden":
        opts["forbidden"] = (
            ForbiddenTransition(eid("balance"), TransitionKind.SET_FACT, 20),
        )
    elif fault == "wrong-type":
        opts["required"] = (replace(spec, value=True),)
    elif fault == "stale-state":
        opts["required"] = (replace(spec, expected_state=FactState.known(999)),)
    else:
        opts["required"] = (replace(spec, target_id=eid("not-registered")),)
    fixture, history, view = make_case(**opts)
    before = canonical_bytes(view.to_dict())
    result = compile_case(fixture, history, view)
    assert not result.ok and result.contract is None and result.diagnostics
    assert canonical_bytes(view.to_dict()) == before


def test_known_constraint_uses_actual_acquisition_not_just_world_truth_or_belief():
    boundary = KnowledgeBoundary(
        eid("alice"), must_know=(eid("balance"),), must_not_know=(eid("secret"),)
    )
    fixture, history, view = make_case(boundaries=(boundary,), with_intent=True)
    state = KnowledgeState.from_dict(json.loads(fixture.knowledge_bytes))
    assert (
        state.query(eid("alice"), Proposition(eid("bob"), "conceals-defect", False))
        is KnowledgeLevel.BELIEVED
    )
    assert compile_case(fixture, history, view).ok
    bad_boundary = KnowledgeBoundary(eid("alice"), must_know=(eid("secret"),))
    bad_fixture, bad_history, bad_view = make_case(boundaries=(bad_boundary,))
    rejected = compile_case(bad_fixture, bad_history, bad_view)
    assert not rejected.ok and rejected.contract is None


def test_certain_knowledge_must_not_be_leaked_across_explicit_boundary():
    fixture, history, view = make_case(
        boundaries=(KnowledgeBoundary(eid("bob"), must_not_know=(eid("secret"),)),)
    )
    result = compile_case(fixture, history, view)
    assert not result.ok and result.diagnostics


def test_reader_reveal_must_respect_frozen_narrative_position():
    fixture, history, view = make_case(
        reveals=(eid("secret"),),
        reader_boundaries=(RevealBoundary(eid("secret"), NarrativePosition(2, 1)),),
    )
    assert not compile_case(fixture, history, view).ok
    allowed, allowed_history, allowed_view = make_case(
        reveals=(eid("secret"),),
        reader_boundaries=(RevealBoundary(eid("secret"), NarrativePosition(1, 1)),),
    )
    assert compile_case(allowed, allowed_history, allowed_view).ok


def test_actual_owner_review_is_not_inferred_from_component_approval_label():
    fixture, history, view = make_case(review="DRAFT")
    result = compile_case(fixture, history, view)
    assert not result.ok and result.contract is None
    assert any(d.code == "FIXTURE_REVIEW_REQUIRED" for d in result.diagnostics)
    assert fixture.review_status == "DRAFT" and fixture.review_ref is None


def test_first_chapter_explicitly_has_no_previous_prose():
    fixture, history, view = make_case()
    later, continuation = component_previous(view)
    assert compile_case(fixture, history, view).ok
    assert not compile_case(fixture, history, view, continuity=continuation).ok
    assert not compile_case(fixture, history, later).ok


def test_continuation_uses_actual_previous_utf8_ending_and_keeps_unknown_semantics():
    fixture, history, view = make_case()
    later, continuity = component_previous(view)
    result = compile_case(
        fixture, history, later, chapter="chapter-2", continuity=continuity
    )
    assert result.ok and result.contract.chapter_number == 2
    assert continuity.end_time == continuity.end_location == continuity.pov == "UNKNOWN"
    assert CompiledContract.from_dict(result.contract.to_dict()) == result.contract
    assert not contract_is_current(
        result.contract,
        history,
        eid("chapter-2"),
        fixture,
        later,
        replace(continuity, unfinished_action="different explicit unknown follow-up"),
    )


@pytest.mark.parametrize(
    "fault", ["commit", "candidate", "hash", "quote", "not-ending"]
)
def test_previous_prose_identity_or_ending_mismatch_blocks_contract(fault):
    fixture, history, view = make_case()
    later, continuity = component_previous(view)
    if fault == "commit":
        continuity = replace(continuity, previous_commit_id=PARENT)
    elif fault == "candidate":
        continuity = replace(continuity, candidate_id=eid("different-source"))
    elif fault == "hash":
        continuity = replace(continuity, prose_hash="0" * 64)
    elif fault == "quote":
        continuity = replace(continuity, quote="捏造的章纲钩子。")
    else:
        text = later.previous.prose.decode()
        continuity = replace(
            continuity, end=len(text) - 1, quote=text[continuity.start : -1]
        )
    result = compile_case(
        fixture, history, later, chapter="chapter-2", continuity=continuity
    )
    assert not result.ok and result.contract is None


def test_future_revision_preserves_frozen_bytes_and_retires_old_active_version():
    fixture, history, view = make_case()
    frozen = freeze_chapters(history, (eid("chapter-1"),))
    original = canonical_bytes(frozen.active.to_dict())
    version = PlanVersion(
        eid("plan"),
        2,
        frozen.active.content_hash,
        change_future(fixture.vision),
        fixture.content_hash,
    )
    changed = adopt_revision(
        frozen,
        version,
        reason="后续阻力发生变化，保留已冻结章节。",
        authority_ref="component-test-authority",
    )
    assert changed.active == version and history.active.revision == 1
    assert canonical_bytes(changed.versions[0].to_dict()) == original
    old_contract = compile_case(fixture, frozen, view).contract
    new_contract = compile_case(fixture, changed, view).contract
    assert (
        new_contract is not None
        and new_contract.content_hash != old_contract.content_hash
    )
    assert not contract_is_current(
        old_contract, changed, eid("chapter-1"), fixture, view
    )
    assert PlanHistory.from_dict(changed.to_dict()) == changed


def test_frozen_or_accepted_planning_content_cannot_be_rewritten_by_revision():
    fixture, history, _view = make_case()
    frozen = freeze_chapters(history, (eid("chapter-1"),))
    illegal = PlanVersion(
        eid("plan"),
        2,
        frozen.active.content_hash,
        change_future(fixture.vision, first=True),
        fixture.content_hash,
    )
    with pytest.raises(ValueError):
        adopt_revision(
            frozen,
            illegal,
            reason="不能改变冻结章节。",
            authority_ref="component-test-authority",
        )


@pytest.mark.parametrize("fault", ["revision-gap", "parent", "identity"])
def test_adoption_requires_exact_next_revision_and_parent(fault):
    fixture, history, _view = make_case()
    revision, parent, identity = 2, history.active.content_hash, eid("plan")
    if fault == "revision-gap":
        revision = 3
    elif fault == "parent":
        parent = "0" * 64
    else:
        identity = eid("other-plan")
    proposed = PlanVersion(
        identity, revision, parent, change_future(fixture.vision), fixture.content_hash
    )
    with pytest.raises(ValueError):
        adopt_revision(
            history,
            proposed,
            reason="修改未来。",
            authority_ref="component-test-authority",
        )


def test_planning_and_fixture_values_are_immutable_and_parsers_are_closed():
    fixture, history, _view = make_case()
    assert StoryFixture.from_dict(fixture.to_dict()) == fixture
    assert PlanVersion.from_dict(history.active.to_dict()) == history.active
    for value in (fixture, history.active, history.active.vision):
        document = value.to_dict()
        document["unregistered_field"] = True
        with pytest.raises(ValueError):
            type(value).from_dict(document)
    with pytest.raises(FrozenInstanceError):
        history.active.revision = 99
    exported = fixture.to_dict()
    exported["world_boundaries"] = ["external mutation"]
    assert fixture.world_boundaries != ("external mutation",)


def test_dependency_change_marks_contracts_for_rebinding_without_canon_rewrite():
    fixture, history, view = make_case()
    contract = compile_case(fixture, history, view).contract
    identity = contract.input_identity
    for field in (
        "parent_ref",
        "canon_hash",
        "pack_hash",
        "knowledge_hash",
        "continuity_hash",
    ):
        changed = replace(
            identity, **{field: ("sha256:" if field == "parent_ref" else "") + "d" * 64}
        )
        impact = assess_changes(
            identity, changed, chapter_ids=(eid("chapter-1"), eid("chapter-2"))
        )
        assert set(impact.affected_chapter_ids) == {eid("chapter-1"), eid("chapter-2")}
        assert impact.changed_inputs
    unchanged = assess_changes(
        identity, identity, chapter_ids=(eid("chapter-1"), eid("chapter-2"))
    )
    assert unchanged.affected_chapter_ids == ()


def test_future_replan_proposal_is_not_automatic_adoption_or_contract_reuse():
    fixture, history, view = make_case()
    before = canonical_bytes(history.to_dict())
    proposal = propose_revision(
        history, change_future(fixture.vision), reason="未来对手策略变化。"
    )
    assert canonical_bytes(history.to_dict()) == before
    assert proposal.base_hash == history.active.content_hash
    changed = adopt_revision(
        history,
        proposal.version,
        reason=proposal.reason,
        authority_ref="component-authority",
    )
    first = compile_case(fixture, history, view).contract
    second = compile_case(fixture, changed, view).contract
    impact = assess_changes(
        first.input_identity,
        second.input_identity,
        chapter_ids=(eid("chapter-1"), eid("chapter-2")),
        before_plan=history.active,
        after_plan=changed.active,
    )
    assert eid("chapter-2") in impact.affected_chapter_ids
    assert eid("chapter-1") in impact.reusable_chapter_ids
    assert first.content_hash != second.content_hash


def extension_case(anchor, *, pay=True):
    fixture, _history, view = make_case(anchor=anchor)
    ids = {v.id for v in fixture.root_seed.entities}
    if anchor == "fantasy.eastern.progression":
        from anovel.genre.extensions.progression import (
            Cultivator,
            ProgressionResource,
            ProgressionState,
            RealmDefinition,
            create_progression_binding,
        )

        state = ProgressionState(
            (
                RealmDefinition(eid("realm-0"), 0, "灵石", "颗", 0),
                RealmDefinition(eid("realm-1"), 1, "灵石", "颗", 5),
            ),
            (Cultivator(eid("alice"), eid("realm-0")),),
            (),
            (),
            (ProgressionResource(eid("pool"), eid("alice"), "灵石", "颗", 20, 0),),
        )
        ids |= state.referenced_ids
        bind = create_progression_binding(
            pack(anchor, "1.1.0"), tuple(sorted(ids, key=str))
        )
        updates = [("alice", "cultivator.realm", "realm-1")]
        if pay:
            updates += [
                ("pool", "resource.quantity", 15),
                ("pool", "resource.spent", 5),
            ]
    else:
        from anovel.genre.extensions.business import (
            BusinessState,
            CashAccount,
            create_business_binding,
        )

        state = BusinessState(
            (),
            (
                CashAccount(eid("account-a"), eid("alice"), "CNY", 1000),
                CashAccount(eid("account-b"), eid("bob"), "CNY", 0),
            ),
            (),
            (),
        )
        ids |= state.referenced_ids
        bind = create_business_binding(
            pack(anchor, "1.1.0"), tuple(sorted(ids, key=str))
        )
        updates = [("account-a", "account.balance_minor", 900)]
        if pay:
            updates += [("account-b", "account.balance_minor", 100)]
    facts = fixture.root_seed.facts + state.to_facts("component-root")
    required = tuple(
        RequiredTransition(
            next(
                f.id
                for f in facts
                if f.proposition.subject == eid(subject)
                and f.proposition.predicate.endswith(":" + field)
            ),
            TransitionKind.SET_FACT,
            value,
        )
        for subject, field, value in updates
    )
    seed = RootSeed(
        tuple(Entity(i, i.local_id) for i in sorted(ids, key=str)),
        (),
        facts,
        extensions=(bind,),
    )
    first = fixture.vision.arcs[0].chapters[0]
    first = replace(first, scenes=(replace(first.scenes[0], required=required),))
    arc = fixture.vision.arcs[0]
    vision = replace(
        fixture.vision, arcs=(replace(arc, chapters=(first, arc.chapters[1])),)
    )
    fixture = replace(
        fixture, pack_binding=pack(anchor, "1.1.0"), root_seed=seed, vision=vision
    )
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    view = CanonView(
        replace(view.root, seed=seed),
        FactBaseline.from_world_facts(
            PROJECT, BRANCH, PARENT, facts, extensions=(bind,)
        ),
        None,
        1,
    )
    return fixture, history, view


@pytest.mark.parametrize(
    "anchor", ["urban.business.realistic", "fantasy.eastern.progression"]
)
def test_compiler_reuses_registered_extension_conservation_and_cost_rules(anchor):
    fixture, history, view = extension_case(anchor)
    accepted = compile_case(fixture, history, view)
    assert accepted.ok and accepted.contract.required
    bad, bad_history, bad_view = extension_case(anchor, pay=False)
    before = canonical_bytes(bad_view.to_dict())
    rejected = compile_case(bad, bad_history, bad_view)
    assert not rejected.ok and rejected.contract is None and rejected.diagnostics
    assert canonical_bytes(bad_view.to_dict()) == before


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_actual_adopted_development_fixture_and_owner_source_are_bound(name):
    directory = ROOT / "specs/fixtures/stories"
    receipt = json.loads((directory / "OWNER_DECISION.json").read_text())
    text = (directory / "OWNER_REVIEW.md").read_bytes()
    assert receipt["review_target"] == {
        "ref": "specs/fixtures/stories/OWNER_REVIEW.md",
        "sha256": sha256(text).hexdigest(),
    }
    assert receipt["decision"] == "APPROVED_FOR_DEVELOPMENT_INPUT"
    assert receipt["response"] == "采用当前两份作为开发输入"
    fixture = StoryFixture.from_dict(
        json.loads((directory / (name + ".json")).read_text())
    )
    assert fixture.review_status == "APPROVED"
    inventory = json.loads((directory / "INPUT_MANIFEST.json").read_text())
    entry = next(v for v in inventory["fixtures"] if v["path"].endswith(name + ".json"))
    assert (
        entry["file_sha256"]
        == sha256((directory / (name + ".json")).read_bytes()).hexdigest()
    )
    assert entry["content_hash"] == fixture.content_hash
    assert "OWNER_DECISION.json" in fixture.review_ref
    assert fixture.partition == "development"
    assert (
        fixture.world_boundaries
        and fixture.choice_costs
        and fixture.opponent_adaptation
        and fixture.reader_promises
    )
    assert (
        fixture.reader_boundaries
        and fixture.knowledge.beliefs
        and fixture.knowledge.intents
    )
    history = PlanHistory(
        (
            PlanVersion(
                EntityId(fixture.project, "adopted-plan"),
                1,
                None,
                fixture.vision,
                fixture.content_hash,
            ),
        )
    )
    receipt = CommitReceipt(
        fixture.project,
        BRANCH,
        "component-owner-input",
        PARENT,
        "b" * 64,
        "2026-11-14T00:00:00.000000Z",
    )
    root = StoredRoot(
        receipt, fixture.root_seed, b"component-only-root", b"component-only-authority"
    )
    baseline = FactBaseline.from_world_facts(
        fixture.project,
        BRANCH,
        PARENT,
        fixture.root_seed.facts,
        extensions=fixture.root_seed.extensions,
    )
    compiled = compile_contract(
        history,
        fixture.vision.chapters[0].id,
        fixture,
        CanonView(root, baseline, None, 1),
    )
    assert compiled.ok and compiled.contract is not None
    assert compiled.contract.fixture_hash == fixture.content_hash


@pytest.mark.parametrize("change", ["premise", "goal", "arc"])
def test_frozen_chapter_cannot_be_changed_through_outer_context(change):
    fixture, history, _view = make_case()
    history = freeze_chapters(history, (eid("chapter-1"),))
    before = history.content_bytes
    vision = history.active.vision
    if change == "premise":
        vision = replace(vision, premise="不同的全局前提")
    elif change == "goal":
        vision = replace(vision, protagonist_goal="不同的全局目标")
    else:
        vision = replace(
            vision, arcs=(replace(vision.arcs[0], purpose="不同的冻结上层意图"),)
        )
    version = PlanVersion(
        history.active.id, 2, history.active.content_hash, vision, fixture.content_hash
    )
    with pytest.raises(ValueError):
        adopt_revision(
            history, version, reason="component attempt", authority_ref=REVIEW
        )
    assert history.content_bytes == before


def test_compiled_contract_retains_complete_adoption_and_freeze_history():
    fixture, history, view = make_case()
    history = freeze_chapters(history, (eid("chapter-1"),))
    version = PlanVersion(
        history.active.id,
        2,
        history.active.content_hash,
        change_future(history.active.vision),
        fixture.content_hash,
    )
    history = adopt_revision(
        history, version, reason="future only", authority_ref=REVIEW
    )
    contract = compile_case(fixture, history, view).contract
    retained = next(v for v in contract.retained_inputs if v.name == "plan_history")
    restored = PlanHistory.from_dict(json.loads(retained.content))
    assert restored == history and restored.supersessions and restored.frozen_chapters
    assert CompiledContract.from_dict(contract.to_dict()) == contract


def current_knowledge_case():
    """Component historical values only; not actual prose acquisition evidence."""
    from anovel.contracts.models import KnowledgeSnapshot

    fixture, history, view = make_case()
    later, ending = component_previous(view, change_value=20)
    state = fixture.knowledge.to_dict()
    next(f for f in state["facts"] if f["id"]["local_id"] == "balance")["proposition"][
        "value"
    ] = 20
    knowledge = KnowledgeState.from_dict(state)
    snapshot = KnowledgeSnapshot(
        PROJECT,
        later.parent_ref,
        "component-only/current-author-input",
        canonical_bytes(knowledge.to_dict()),
    )
    return fixture, history, later, ending, snapshot


def test_current_knowledge_can_advance_without_rewriting_initial_fixture_or_canon():
    from anovel.contracts.models import KnowledgeSnapshot

    fixture, history, view, ending, snapshot = current_knowledge_case()
    initial = fixture.content_bytes
    original = canonical_bytes(view.to_dict())
    stale = compile_case(fixture, history, view, chapter="chapter-2", continuity=ending)
    assert not stale.ok and stale.diagnostics[0].code == "KNOWLEDGE_SNAPSHOT_INVALID"
    result = compile_contract(
        history, eid("chapter-2"), fixture, view, ending, knowledge_snapshot=snapshot
    )
    assert result.ok and result.contract is not None
    assert (
        fixture.content_bytes == initial and canonical_bytes(view.to_dict()) == original
    )
    retained = next(v for v in result.contract.retained_inputs if v.name == "knowledge")
    assert KnowledgeSnapshot.from_dict(json.loads(retained.content)) == snapshot
    assert CompiledContract.from_dict(result.contract.to_dict()) == result.contract
    assert contract_is_current(
        result.contract,
        history,
        eid("chapter-2"),
        fixture,
        view,
        ending,
        knowledge_snapshot=snapshot,
    )
    revised = replace(snapshot, source_ref="component-only/new-record")
    assert not contract_is_current(
        result.contract,
        history,
        eid("chapter-2"),
        fixture,
        view,
        ending,
        knowledge_snapshot=revised,
    )


@pytest.mark.parametrize(
    "fault", ["parent", "project", "world-value", "unregistered-character"]
)
def test_current_knowledge_snapshot_cannot_claim_wrong_scope_or_world(fault):
    from anovel.contracts.models import KnowledgeSnapshot

    fixture, history, view, ending, snapshot = current_knowledge_case()
    if fault == "parent":
        snapshot = replace(snapshot, parent_ref=PARENT)
    elif fault == "project":
        with pytest.raises(ValueError):
            replace(snapshot, project="another-project")
        return
    else:
        state = snapshot.knowledge.to_dict()
        if fault == "world-value":
            next(f for f in state["facts"] if f["id"]["local_id"] == "balance")[
                "proposition"
            ]["value"] = 999
        else:
            person = Character(eid("unregistered"), "未登记人物").to_dict()
            state["characters"].append(person)
        snapshot = KnowledgeSnapshot(
            PROJECT,
            view.parent_ref,
            "component-only/invalid",
            canonical_bytes(KnowledgeState.from_dict(state).to_dict()),
        )
    result = compile_contract(
        history, eid("chapter-2"), fixture, view, ending, knowledge_snapshot=snapshot
    )
    assert not result.ok and result.contract is None
    assert result.diagnostics[0].code == "KNOWLEDGE_SNAPSHOT_INVALID"


@pytest.mark.parametrize("constraint", ["protected", "forbidden"])
def test_scene_constraints_do_not_silently_become_whole_chapter_bans(constraint):
    fixture, _history, view = make_case()
    chapter = fixture.vision.chapters[0]
    first = chapter.scenes[0]
    required = (RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 20),)
    if constraint == "protected":
        first = replace(first, required=required)
        second = ScenePlan(
            eid("additional-scene"),
            2,
            "变化后安静讨论，不再改账",
            protected_fact_ids=(eid("balance"),),
        )
    else:
        first = replace(
            first,
            forbidden=(
                ForbiddenTransition(eid("balance"), TransitionKind.SET_FACT, 20),
            ),
        )
        second = ScenePlan(
            eid("additional-scene"), 2, "在明确后续场景作出选择", required=required
        )
    chapter = replace(chapter, scenes=(first, second))
    arc = fixture.vision.arcs[0]
    vision = replace(
        fixture.vision, arcs=(replace(arc, chapters=(chapter, arc.chapters[1])),)
    )
    fixture = replace(fixture, vision=vision)
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    result = compile_case(fixture, history, view)
    assert result.ok and len(result.contract.required) == 1
    assert (
        len(result.contract.scenes[0 if constraint == "protected" else 1].required) == 1
    )


def test_thirty_compiled_chapters_do_not_recursively_embed_predecessor_contracts():
    """Component storage-shape control, not generated prose or 30ch certification."""
    fixture, _history, view = make_case()
    chapters = tuple(
        ChapterPlan(
            eid("bounded-chapter-" + str(i)),
            i,
            "安静核对当前事实",
            (ScenePlan(eid("bounded-scene-" + str(i)), 1, "观察与选择"),),
        )
        for i in range(1, 31)
    )
    vision = replace(
        fixture.vision, arcs=(replace(fixture.vision.arcs[0], chapters=chapters),)
    )
    fixture = replace(fixture, vision=vision)
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    sizes = []
    for number, chapter in enumerate(chapters, 1):
        ending = (
            None
            if view.previous is None
            else ContinuationEvidence.from_previous(
                view.previous, evidence_ref="component-only/bounded-prose"
            )
        )
        result = compile_contract(history, chapter.id, fixture, view, ending)
        assert (
            result.ok
            and CompiledContract.from_dict(result.contract.to_dict()) == result.contract
        )
        sizes.append(len(result.contract.content_bytes))
        snapshot = view.baseline.get(eid("balance"))
        source = eid("bounded-source-" + str(number))
        meta = OperationMeta(
            eid("bounded-op-" + str(number)),
            snapshot.seed_fact.id,
            FactPath.VALUE,
            Precondition.from_snapshot(snapshot),
            ProseEvidence(source, NarrativePosition(number, 1), "component-only"),
            "component-only",
        )
        delta = NarrativeDelta(
            eid("bounded-delta-" + str(number)),
            BRANCH,
            view.parent_ref,
            source,
            (NoChange(meta),),
        )
        dependencies = tuple(
            CandidateEvidence(
                kind,
                result.contract.content_bytes
                if kind == "CONTRACT"
                else b"component-only-dependency",
                "test/" + kind.lower(),
                "1.0",
                "component-test",
                "1.0",
            )
            for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
        )
        candidate = ChapterCandidate(
            source,
            BRANCH,
            view.parent_ref,
            1,
            b"component-only predecessor prose",
            delta,
            dependencies,
        )
        receipt = CommitReceipt(
            PROJECT,
            BRANCH,
            "bounded-" + str(number),
            "sha256:" + sha256(str(number).encode()).hexdigest(),
            candidate.payload_hash,
            "2026-11-14T00:00:00.000000Z",
        )
        state = preview_delta(
            view.baseline,
            delta,
            source_id=source,
            authorization_refs=frozenset({"component-only"}),
        ).candidate
        previous = StoredChapter(receipt, candidate, state, b"component-only-permit")
        view = CanonView(
            view.root,
            replace(state, parent_ref=receipt.commit_id),
            previous,
            number + 1,
        )
        projection = view.to_dict()["previous"]
        assert "candidate" not in projection and "permit_base64" not in projection
        assert projection["receipt"]["payload_hash"] == candidate.payload_hash
    assert max(sizes) < sizes[0] * 2
    assert max(sizes[1:]) - min(sizes[1:]) < 1000
