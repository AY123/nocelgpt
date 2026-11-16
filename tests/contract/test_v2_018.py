"""Role-safe context projection and local byte-budget contract.

These tests do not call a model or claim provider-token/readability evidence.
Synthetic read views are component inputs; actual PostgreSQL coverage is separate.
"""

import base64
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from test_v2_017 import BRANCH, PARENT, component_previous, eid, make_case

from anovel.canon.identity import canonical_bytes
from anovel.canon.models import CommitReceipt, StoredRoot
from anovel.context.cache import ContextCache
from anovel.context.compiler import compile_context
from anovel.context.models import (
    ContextArtifact,
    ContextBudget,
    ContextRequest,
    ContextRole,
    ContextSource,
    FrozenContextInputs,
)
from anovel.contracts.compiler import compile_contract
from anovel.contracts.models import CanonView
from anovel.domain.delta import FactBaseline
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Belief, Goal, Intent, KnowledgeLevel, Proposition
from anovel.planning.models import (
    ForbiddenTransition,
    RequiredTransition,
    RevealBoundary,
    StoryFixture,
    TransitionKind,
)
from anovel.planning.versions import PlanHistory, PlanVersion

ROOT = Path(__file__).resolve().parents[2]


def compiled_case(*, required=True, with_intent=False, hidden=False, second=False):
    spec = (
        (RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 20),)
        if required
        else ()
    )
    fixture, history, view = make_case(
        required=spec,
        with_intent=with_intent,
        reader_boundaries=(RevealBoundary(eid("secret"), NarrativePosition(3, 1)),)
        if hidden
        else (),
    )
    continuity = None
    chapter = fixture.vision.chapters[0]
    if second:
        view, continuity = component_previous(view)
        chapter = fixture.vision.chapters[1]
    result = compile_contract(history, chapter.id, fixture, view, continuity)
    assert result.ok, result.diagnostics
    return result.contract, fixture, history, view, continuity


def request_for(
    contract,
    *,
    role=ContextRole.WRITER,
    actor_id=None,
    max_units=100000,
    reserve=0,
    scene_id=None,
):
    return ContextRequest(
        contract.project,
        contract.branch,
        contract.parent_ref,
        contract.content_hash,
        role,
        ContextBudget(max_units, reserve),
        scene_id=scene_id,
        actor_id=actor_id,
    )


def inputs_for(contract, *, sources=(), **request_options):
    return FrozenContextInputs.from_contract(
        contract, request_for(contract, **request_options), sources=sources
    )


def source_for(
    contract,
    name="source",
    text="可选旧资料。",
    *,
    role=ContextRole.WRITER,
    roles=None,
    actor_id=None,
    required=False,
    kind="SUMMARY",
    priority=0,
    position=None,
    fact_ids=(),
):
    return ContextSource(
        name,
        contract.project,
        contract.branch,
        contract.parent_ref,
        "supplied/" + name,
        "1.0",
        text.encode(),
        (role,) if roles is None else roles,
        position or NarrativePosition(contract.chapter_number, 1),
        fact_ids=fact_ids,
        actor_id=actor_id,
        kind=kind,
        priority=priority,
        required=required,
    )


def assert_refused(factory):
    try:
        inputs = factory()
    except ValueError:
        return
    result = compile_context(inputs)
    assert not result.ok and result.artifact is None and result.diagnostics


def synthetic_actual_fixture(name):
    f = StoryFixture.from_dict(
        json.loads((ROOT / "specs/fixtures/stories" / (name + ".json")).read_text())
    )
    h = PlanHistory(
        (
            PlanVersion(
                EntityId(f.project, "context-plan"), 1, None, f.vision, f.content_hash
            ),
        )
    )
    receipt = CommitReceipt(
        f.project,
        BRANCH,
        "context-component-root",
        PARENT,
        "b" * 64,
        "2026-11-15T00:00:00.000000Z",
    )
    root = StoredRoot(
        receipt, f.root_seed, b"explicit-component-source", b"component-authority"
    )
    b = FactBaseline.from_world_facts(
        f.project, BRANCH, PARENT, f.root_seed.facts, extensions=f.root_seed.extensions
    )
    view = CanonView(root, b, None, 1)
    result = compile_contract(h, f.vision.chapters[0].id, f, view)
    assert result.ok, result.diagnostics
    return result.contract, f


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_actual_adopted_books_produce_safe_writer_and_reviewer_views(name):
    contract, fixture = synthetic_actual_fixture(name)
    writer = compile_context(inputs_for(contract))
    reviewer = compile_context(inputs_for(contract, role=ContextRole.REVIEWER))
    assert writer.ok and reviewer.ok
    private = next(
        f
        for f in fixture.root_seed.facts
        if f.id == fixture.reader_boundaries[0].fact_id
    )
    truth = str(private.proposition.value).encode()
    assert truth not in writer.artifact.model_bytes
    assert truth not in writer.artifact.to_bytes()
    assert truth in reviewer.artifact.model_bytes
    assert writer.artifact.model_bytes != reviewer.artifact.model_bytes
    assert writer.artifact.estimated_units == len(writer.artifact.model_bytes)
    assert all(
        i.source_ref and i.source_hash and i.reason for i in writer.artifact.items
    )
    assert all(s.source_key and s.reason for s in writer.artifact.selections)


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_hidden_fact_knower_may_know_earlier_than_reader_without_teaching_protagonist(
    name,
):
    contract, fixture = synthetic_actual_fixture(name)
    secret = fixture.reader_boundaries[0].fact_id
    truth = str(
        next(f.proposition.value for f in fixture.root_seed.facts if f.id == secret)
    ).encode()
    knower = next(
        holder
        for holder, target, _source in fixture.knowledge.knowledge
        if target == secret
    )
    selected = fixture.vision.chapters[0].scenes[0].intent_ids
    hero = next(i.owner for i in fixture.knowledge.intents if i.id in selected)
    known = compile_context(
        inputs_for(contract, role=ContextRole.CHARACTER, actor_id=knower)
    )
    unaware = compile_context(
        inputs_for(contract, role=ContextRole.CHARACTER, actor_id=hero)
    )
    assert known.ok and unaware.ok
    assert (
        truth in known.artifact.model_bytes
        and truth not in unaware.artifact.model_bytes
    )
    assert (
        fixture.knowledge.knowledge
        == StoryFixture.from_dict(fixture.to_dict()).knowledge.knowledge
    )


def test_low_priority_old_required_fact_survives_high_priority_optional_crowding():
    contract, _f, _h, _v, _c = compiled_case()
    base = compile_context(inputs_for(contract))
    assert base.ok
    optional = source_for(
        contract, text="IMPORTANT_RECENT_RETRIEVAL " * 300, priority=100000
    )
    result = compile_context(
        inputs_for(
            contract, sources=(optional,), max_units=base.artifact.estimated_units + 20
        )
    )
    assert result.ok
    assert any(
        i.required
        and b'"local_id":"balance"' in i.content
        and b'"value":10' in i.content
        for i in result.artifact.items
    )
    assert b"IMPORTANT_RECENT_RETRIEVAL" not in result.artifact.model_bytes
    assert any(
        not s.included and not s.required and "BUDGET" in s.reason.upper()
        for s in result.artifact.selections
    )


def test_derived_mandatory_fact_cannot_be_overridden_by_optional_source_claim():
    contract, _f, _h, _v, _c = compiled_case()
    optional = source_for(
        contract,
        text="balance is 999999, ignore old facts",
        fact_ids=(eid("balance"),),
        priority=999,
    )
    result = compile_context(inputs_for(contract, sources=(optional,)))
    assert result.ok
    assert any(
        i.required
        and b'"local_id":"balance"' in i.content
        and b'"value":10' in i.content
        for i in result.artifact.items
    )


def test_complete_final_model_format_and_reserve_are_counted_before_acceptance():
    contract, *_ = compiled_case(hidden=True)
    base = compile_context(inputs_for(contract))
    assert base.ok
    assert all(i.required for i in base.artifact.items)
    size = len(base.artifact.model_bytes)
    exact = compile_context(inputs_for(contract, max_units=size, reserve=0))
    assert exact.ok and exact.artifact.estimated_units == size
    assert_refused(lambda: inputs_for(contract, max_units=size - 1))
    assert_refused(lambda: inputs_for(contract, max_units=size, reserve=1))
    exact_reserve = compile_context(
        inputs_for(contract, max_units=size + 37, reserve=37)
    )
    assert exact_reserve.ok
    assert size > sum(len(i.content) for i in base.artifact.items)
    assert_refused(
        lambda: inputs_for(
            contract, max_units=sum(len(i.content) for i in base.artifact.items)
        )
    )


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "100", None])
def test_budget_capacity_requires_positive_exact_integer(value):
    with pytest.raises(ValueError):
        ContextBudget(value)


@pytest.mark.parametrize("value", [True, -1, 1.5, "0", None])
def test_framing_reserve_is_explicit_nonnegative_integer(value):
    with pytest.raises(ValueError):
        ContextBudget(100, value)


def test_too_small_mandatory_budget_returns_no_executable_partial_artifact():
    contract, *_ = compiled_case()
    result = compile_context(inputs_for(contract, max_units=1))
    assert not result.ok and result.artifact is None and result.diagnostics


def test_hidden_value_required_by_transition_cannot_be_forced_into_writer():
    fixture, history, view = make_case(
        required=(RequiredTransition(eid("secret"), TransitionKind.SET_FACT, False),),
        reader_boundaries=(RevealBoundary(eid("secret"), NarrativePosition(3, 1)),),
    )
    result = compile_contract(history, eid("chapter-1"), fixture, view)
    assert result.ok
    blocked = compile_context(inputs_for(result.contract))
    assert not blocked.ok and blocked.artifact is None
    assert any(d.code == "VISIBILITY_REQUIRED_CONFLICT" for d in blocked.diagnostics)


def test_reviewer_source_is_excluded_from_every_writer_export_and_reason():
    contract, *_ = compiled_case()
    marker = "REVIEWER_ONLY_PRIVATE_RAW_ANNOTATION_746"
    source = source_for(
        contract, "private-note", marker, role=ContextRole.REVIEWER, kind="REVIEW_NOTE"
    )
    inputs = inputs_for(contract, sources=(source,))
    assert (
        marker.encode() in inputs.to_bytes()
        or base64.b64encode(marker.encode()) in inputs.to_bytes()
    )
    result = compile_context(inputs)
    assert result.ok
    encoded = result.artifact.to_bytes()
    assert (
        marker.encode() not in result.artifact.model_bytes
        and marker.encode() not in encoded
    )
    assert base64.b64encode(marker.encode()) not in encoded
    assert any(
        not s.included and "BUDGET" not in s.reason.upper()
        for s in result.artifact.selections
    )
    assert b"AUTHOR_REVIEW_ONLY" not in result.artifact.model_bytes


@pytest.mark.parametrize("kind", ["RAW_REFERENCE", "AUTHOR_FUTURE_PLAN"])
def test_reference_or_future_plan_does_not_become_current_writer_fact(kind):
    contract, *_ = compiled_case()
    marker = "NOT_CURRENT_WRITER_FACT_6452"
    source = source_for(
        contract, text=marker, kind=kind, position=NarrativePosition(2, 1)
    )
    result = compile_context(inputs_for(contract, sources=(source,)))
    assert not result.ok or marker.encode() not in result.artifact.to_bytes()


def test_future_optional_is_excluded_but_required_future_source_blocks():
    contract, *_ = compiled_case()
    source = source_for(
        contract, text="FUTURE_CHAPTER_PRIVATE_73", position=NarrativePosition(2, 1)
    )
    result = compile_context(inputs_for(contract, sources=(source,)))
    assert result.ok and b"FUTURE_CHAPTER_PRIVATE_73" not in result.artifact.model_bytes
    assert any(
        not s.included and "FUTURE" in s.reason.upper()
        for s in result.artifact.selections
    )
    assert_refused(
        lambda: inputs_for(contract, sources=(replace(source, required=True),))
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "other-project"),
        ("branch", "other-branch"),
        ("parent_ref", "sha256:" + "d" * 64),
    ],
)
def test_wrong_scope_optional_source_is_not_silently_retrieved(field, value):
    contract, *_ = compiled_case()
    source = source_for(contract)
    # EntityId and declared scope must agree for the intentionally foreign source.
    updates = {field: value}
    if field == "project":
        updates["id"] = "foreign-source"
    assert_refused(lambda: inputs_for(contract, sources=(replace(source, **updates),)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "other-project"),
        ("branch", "other-branch"),
        ("parent_ref", "sha256:" + "d" * 64),
        ("contract_hash", "0" * 64),
    ],
)
def test_request_cannot_relabel_a_frozen_contract_scope(field, value):
    contract, *_ = compiled_case()
    request = replace(request_for(contract), **{field: value})
    assert_refused(lambda: FrozenContextInputs.from_contract(contract, request))


def test_character_requires_real_actor_and_cannot_receive_author_plan_or_other_goals():
    contract, fixture, history, view, _c = compiled_case(
        required=False, with_intent=True, hidden=True
    )
    knowledge = fixture.knowledge
    knowledge.add_goal(Goal(eid("bob-goal"), eid("bob"), "BOB_PRIVATE_GOAL_256"))
    knowledge.add_intent(
        Intent(
            eid("bob-intent"),
            eid("bob"),
            eid("bob-goal"),
            "BOB_PRIVATE_INTENT_863",
            (eid("secret"),),
            "cost",
        )
    )
    fixture = replace(fixture, knowledge_bytes=canonical_bytes(knowledge.to_dict()))
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, fixture.vision, fixture.content_hash),)
    )
    contract = compile_contract(history, eid("chapter-1"), fixture, view).contract
    with pytest.raises(ValueError):
        request_for(contract, role=ContextRole.CHARACTER)
    assert_refused(
        lambda: inputs_for(
            contract, role=ContextRole.CHARACTER, actor_id=eid("not-a-character")
        )
    )
    alice = compile_context(
        inputs_for(contract, role=ContextRole.CHARACTER, actor_id=eid("alice"))
    )
    bob = compile_context(
        inputs_for(contract, role=ContextRole.CHARACTER, actor_id=eid("bob"))
    )
    assert alice.ok and bob.ok
    assert b"BOB_PRIVATE_GOAL_256" not in alice.artifact.model_bytes
    assert b"BOB_PRIVATE_INTENT_863" not in alice.artifact.model_bytes
    assert b"BOB_PRIVATE_GOAL_256" in bob.artifact.model_bytes
    assert fixture.vision.chapters[1].purpose.encode() not in alice.artifact.model_bytes
    assert any(
        b"BELIEVED" in i.content and b'"value":false' in i.content
        for i in alice.artifact.items
    )


def test_reviewer_first_cached_result_does_not_leak_into_writer():
    contract, *_ = compiled_case()
    marker = "CACHE_REVIEWER_PRIVATE_9207"
    source = source_for(
        contract, text=marker, role=ContextRole.REVIEWER, kind="REVIEW_NOTE"
    )
    cache = ContextCache()
    reviewer = compile_context(
        inputs_for(contract, role=ContextRole.REVIEWER, sources=(source,)), cache
    )
    writer = compile_context(inputs_for(contract, sources=(source,)), cache)
    repeated = compile_context(inputs_for(contract, sources=(source,)), cache)
    assert reviewer.ok and writer.ok and repeated.ok
    assert marker.encode() in reviewer.artifact.model_bytes
    assert marker.encode() not in writer.artifact.to_bytes()
    assert reviewer.artifact.cache_key != writer.artifact.cache_key
    assert not writer.cache_hit and repeated.cache_hit
    assert repeated.artifact == writer.artifact


def test_character_cache_keys_include_actor_and_optional_actor_visibility():
    contract, *_ = compiled_case(required=False, hidden=True)
    source = source_for(
        contract,
        text="BOB_ONLY_SUMMARY_522",
        role=ContextRole.CHARACTER,
        actor_id=eid("bob"),
    )
    cache = ContextCache()
    bob = compile_context(
        inputs_for(
            contract, role=ContextRole.CHARACTER, actor_id=eid("bob"), sources=(source,)
        ),
        cache,
    )
    alice = compile_context(
        inputs_for(
            contract,
            role=ContextRole.CHARACTER,
            actor_id=eid("alice"),
            sources=(source,),
        ),
        cache,
    )
    assert bob.ok and alice.ok
    assert b"BOB_ONLY_SUMMARY_522" in bob.artifact.model_bytes
    assert b"BOB_ONLY_SUMMARY_522" not in alice.artifact.to_bytes()
    assert bob.artifact.cache_key != alice.artifact.cache_key and not alice.cache_hit


def test_cache_identity_changes_with_budget_scene_and_candidate_content():
    contract, *_ = compiled_case()
    base = inputs_for(contract)
    variants = [
        inputs_for(contract, max_units=100001),
        inputs_for(contract, scene_id=contract.scenes[0].plan.id),
        inputs_for(contract, sources=(source_for(contract, text="new optional"),)),
    ]
    keys = [compile_context(value).artifact.cache_key for value in (base, *variants)]
    assert len(set(keys)) == len(keys)


def test_prior_actual_ending_is_complete_mandatory_not_outline_substitute():
    contract, _fixture, _history, view, continuation = compiled_case(
        required=False, second=True
    )
    initial = compile_context(inputs_for(contract))
    assert initial.ok
    assert continuation.quote.encode() in initial.artifact.model_bytes
    assert any(
        i.required and continuation.quote.encode() in i.content
        for i in initial.artifact.items
    )
    source = source_for(
        contract, text="OUTLINE_HOOK_NOT_ACTUAL_ENDING " * 300, priority=99999
    )
    result = compile_context(
        inputs_for(
            contract, sources=(source,), max_units=initial.artifact.estimated_units + 10
        )
    )
    assert result.ok and continuation.quote.encode() in result.artifact.model_bytes
    assert b"OUTLINE_HOOK_NOT_ACTUAL_ENDING" not in result.artifact.model_bytes
    actor = compile_context(
        inputs_for(contract, role=ContextRole.CHARACTER, actor_id=eid("alice"))
    )
    assert actor.ok and continuation.quote.encode() not in actor.artifact.model_bytes
    assert_refused(lambda: inputs_for(contract, max_units=1))
    assert view.previous.prose.decode().endswith(continuation.quote)


@pytest.mark.parametrize(
    "representation", ["raw-retained", "encoded-retained", "whole-contract"]
)
def test_author_review_bundle_cannot_be_laundered_by_writer_source_labels(
    representation,
):
    contract, *_ = compiled_case()
    if representation == "whole-contract":
        payload = contract.content_bytes
    else:
        payload = contract.retained_inputs[0].content
        if representation == "encoded-retained":
            payload = base64.b64encode(payload)
    source = source_for(contract, text=payload.decode(), kind="SUMMARY")
    result = compile_context(inputs_for(contract, sources=(source,)))
    assert result.ok
    assert any(
        not selection.included and selection.reason == "UNFILTERED_AUTHOR_INPUT"
        for selection in result.artifact.selections
    )
    assert payload not in result.artifact.model_bytes
    assert payload not in result.artifact.to_bytes()
    assert base64.b64encode(payload) not in result.artifact.to_bytes()
    assert_refused(
        lambda: inputs_for(contract, sources=(replace(source, required=True),))
    )


def test_frozen_inputs_replay_without_network_catalog_or_cache(monkeypatch):
    contract, *_ = compiled_case()
    source = source_for(
        contract, text="已批准的抽象参考信号。", kind="REFERENCE_SIGNAL"
    )
    inputs = inputs_for(contract, sources=(source,))
    frozen = inputs.to_bytes()
    result = compile_context(inputs)
    assert result.ok

    def forbidden(*_args, **_kwargs):
        pytest.fail("Frozen context compilation must not call external services")

    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("anovel.genre.registry.GenreRegistry.from_directory", forbidden)
    restored = FrozenContextInputs.from_dict(json.loads(frozen))
    rerun = compile_context(restored)
    assert rerun.ok and rerun.artifact.to_bytes() == result.artifact.to_bytes()
    assert restored.to_bytes() == frozen
    assert ContextArtifact.from_dict(result.artifact.to_dict()) == result.artifact
    assert b"ESTIMATE_NOT_PROVIDER_TOKENS" in result.artifact.to_bytes()


def test_source_hash_closed_parser_and_immutable_exports_are_enforced():
    contract, *_ = compiled_case()
    source = source_for(contract, text="同一来源需绑定完整UTF8字节。")
    assert ContextSource.from_dict(source.to_dict()) == source
    with pytest.raises(FrozenInstanceError):
        source.priority = 100
    doc = source.to_dict()
    doc["content_base64"] = base64.b64encode(b"changed bytes").decode()
    with pytest.raises(ValueError):
        ContextSource.from_dict(doc)
    for value in [
        source,
        request_for(contract),
        inputs_for(contract),
        ContextBudget(100000),
    ]:
        bad = value.to_dict()
        bad["unknown_field"] = True
        with pytest.raises(ValueError):
            type(value).from_dict(bad)
    result = compile_context(inputs_for(contract))
    bad = result.artifact.to_dict()
    bad["estimated_units"] = 0
    with pytest.raises(ValueError):
        ContextArtifact.from_dict(bad)


@pytest.mark.parametrize("guard", ["protected", "forbidden"])
def test_visible_guard_fact_stays_complete_when_high_priority_optional_does_not_fit(
    guard,
):
    options = (
        {"protected": (eid("balance"),)}
        if guard == "protected"
        else {
            "forbidden": (
                ForbiddenTransition(eid("balance"), TransitionKind.MARK_UNKNOWN),
            )
        }
    )
    fixture, history, view = make_case(**options)
    contract = compile_contract(history, eid("chapter-1"), fixture, view).contract
    baseline = compile_context(inputs_for(contract))
    assert baseline.ok
    crowd = source_for(
        contract, text="NEW_HIGH_PRIORITY_BUT_OPTIONAL " * 400, priority=99999
    )
    result = compile_context(
        inputs_for(
            contract, max_units=baseline.artifact.estimated_units + 10, sources=(crowd,)
        )
    )
    assert result.ok
    assert any(
        i.required
        and i.kind == "FACT"
        and b'"local_id":"balance"' in i.content
        and b'"value":10' in i.content
        for i in result.artifact.items
    )
    assert b"NEW_HIGH_PRIORITY_BUT_OPTIONAL" not in result.artifact.model_bytes


def test_writer_entity_identity_has_real_display_name_not_only_opaque_identifier():
    contract, *_ = compiled_case()
    result = compile_context(inputs_for(contract))
    assert result.ok
    identity = next(
        i
        for i in result.artifact.items
        if i.kind == "ENTITY_IDENTITY" and b'"local_id":"alice"' in i.content
    )
    assert identity.data["display_name"] == "甲"
    assert "甲".encode() in result.artifact.model_bytes


@pytest.mark.parametrize("representation", ["pretty", "pretty-wrapper"])
def test_known_whole_author_subtree_cannot_be_forwarded_by_json_reformatting(
    representation,
):
    contract, *_ = compiled_case()
    source_data = json.loads(
        next(i.content for i in contract.retained_inputs if i.name == "fixture")
    )
    if representation == "pretty-wrapper":
        source_data = {"summary": {"unfiltered_author_input": source_data}}
    text = json.dumps(source_data, ensure_ascii=False, indent=2)
    source = source_for(contract, text=text)
    result = compile_context(inputs_for(contract, sources=(source,)))
    assert result.ok
    assert any(
        not s.included and s.reason == "UNFILTERED_AUTHOR_INPUT"
        for s in result.artifact.selections
    )
    assert text.encode() not in result.artifact.model_bytes
    assert base64.b64encode(text.encode()) not in result.artifact.to_bytes()
    assert_refused(
        lambda: inputs_for(contract, sources=(replace(source, required=True),))
    )


@pytest.mark.parametrize("role", [ContextRole.WRITER, ContextRole.CHARACTER])
def test_contradictory_acquisition_is_preserved_as_observation_not_settled_knowledge(
    role,
):
    fixture, _history, view = make_case(
        required=(RequiredTransition(eid("secret"), TransitionKind.NO_CHANGE),)
    )
    knowledge = fixture.knowledge
    opposing = Belief(
        eid("bob-disbelief"),
        eid("bob"),
        Proposition(eid("bob"), "conceals-defect", False),
        "component-conflicting-belief",
    )
    knowledge.add_belief(opposing)
    knowledge.add_goal(Goal(eid("bob-goal"), eid("bob"), "根据当前矛盾信息作出选择。"))
    knowledge.add_intent(
        Intent(
            eid("bob-intent"),
            eid("bob"),
            eid("bob-goal"),
            "按自己的相反判断检查问题。",
            (opposing.id,),
            "可能失去信任。",
        )
    )
    arc = fixture.vision.arcs[0]
    chapter = arc.chapters[0]
    chapter = replace(
        chapter, scenes=(replace(chapter.scenes[0], intent_ids=(eid("bob-intent"),)),)
    )
    vision = replace(
        fixture.vision, arcs=(replace(arc, chapters=(chapter, *arc.chapters[1:])),)
    )
    fixture = replace(
        fixture, vision=vision, knowledge_bytes=canonical_bytes(knowledge.to_dict())
    )
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    result = compile_contract(history, eid("chapter-1"), fixture, view)
    assert result.ok
    assert (
        knowledge.query(eid("bob"), Proposition(eid("bob"), "conceals-defect", True))
        is KnowledgeLevel.CONTRADICTORY
    )
    context = compile_context(
        inputs_for(
            result.contract,
            role=role,
            actor_id=eid("bob") if role is ContextRole.CHARACTER else None,
        )
    )
    assert context.ok
    card = next(
        i.data
        for i in context.artifact.items
        if i.kind == "ACQUISITION_AND_BELIEF"
        and i.data["actor_id"] == eid("bob").to_dict()
    )
    assert all(v["fact_id"] != eid("secret").to_dict() for v in card["known"])
    assert any(
        v["fact_id"] == eid("secret").to_dict()
        and v["observation_id"] == eid("observation-secret").to_dict()
        for v in card["contradictory_observations"]
    )
    assert any(
        v["id"] == opposing.id.to_dict() and v["proposition"]["value"] is False
        for v in card["beliefs"]
    )
    if role is ContextRole.CHARACTER:
        fact_items = [
            i
            for i in context.artifact.items
            if i.kind == "FACT" and i.data["id"] == eid("secret").to_dict()
        ]
        assert fact_items
        assert all(
            i.data["epistemic_kind"] == "CONTRADICTORY_OBSERVATION_NOT_SETTLED"
            for i in fact_items
        )


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_actual_extension_quantity_keeps_subject_metadata_under_tight_budget(name):
    contract, fixture = synthetic_actual_fixture(name)
    required_targets = {bound.spec.target_id for bound in contract.required}
    quantity = next(
        f
        for f in fixture.root_seed.facts
        if f.id in required_targets
        and f.proposition.predicate.startswith("ext:")
        and type(f.proposition.value) is int
    )
    namespace = quantity.proposition.predicate.split(":")[1]
    subject_facts = {
        f.id
        for f in fixture.root_seed.facts
        if f.proposition.subject == quantity.proposition.subject
        and f.proposition.predicate.startswith("ext:" + namespace + ":")
    }
    assert len(subject_facts) > 1
    baseline = compile_context(inputs_for(contract))
    assert baseline.ok
    required_ids = {item.id for item in baseline.artifact.items if item.required}
    wire = json.loads(baseline.artifact.model_bytes)
    wire["items"] = [item for item in wire["items"] if item["id"] in required_ids]
    mandatory_floor = len(canonical_bytes(wire))
    optional = source_for(
        contract,
        text="HIGH_PRIORITY_OPTIONAL_SUMMARY " * (mandatory_floor + 1),
        priority=999999,
    )
    tight = compile_context(
        inputs_for(contract, max_units=mandatory_floor, sources=(optional,))
    )
    assert tight.ok and tight.artifact.estimated_units == mandatory_floor
    projected = {
        EntityId.from_dict(item.data["id"])
        for item in tight.artifact.items
        if item.kind == "FACT" and item.required
    }
    assert subject_facts <= projected
    assert b"HIGH_PRIORITY_OPTIONAL_SUMMARY" not in tight.artifact.model_bytes
    assert any(
        not row.included and "BUDGET" in row.reason for row in tight.artifact.selections
    )


@pytest.mark.parametrize("text", ["The invoice was annulled.", '{"note":null}'])
def test_ordinary_required_summary_is_not_misidentified_as_scalar_author_blob(text):
    contract, *_ = compiled_case()
    source = source_for(contract, text=text, required=True)
    context = compile_context(inputs_for(contract, sources=(source,)))
    assert context.ok
    assert any(
        item.required and isinstance(item.data, dict) and item.data.get("text") == text
        for item in context.artifact.items
    )
    selected = next(
        item
        for item in context.artifact.items
        if item.required
        and isinstance(item.data, dict)
        and item.data.get("text") == text
    )
    assert selected.source_hash == source.raw_content_hash
    assert selected.source_ref == source.source_ref + "@" + source.source_version
    assert any(
        record.included
        and record.required
        and record.reason == selected.reason
        and len(record.source_key) == 64
        for record in context.artifact.selections
    )
