"""Source-bound offline scene candidates, not extraction or Canon acceptance.

The real Contract/Context compilers, ModelGateway and SQLite Workflow store are
used with a finite synthetic adapter. Explicit Delta mappings are supplied test
data, not automatic prose understanding or real human review evidence.
"""

import json
import socket
from base64 import b64encode
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from test_v2_015 import pack as business_pack
from test_v2_017 import BRANCH, PARENT, PROJECT, eid, make_case
from test_v2_020 import RUN, CountingLocalAdapter, harness, policy_for, start

from anovel.canon.identity import canonical_bytes
from anovel.canon.models import RootSeed
from anovel.context.cache import ContextCache
from anovel.context.compiler import compile_context
from anovel.context.models import (
    ContextBudget,
    ContextError,
    ContextRequest,
    ContextRole,
    ContextSource,
    FrozenContextInputs,
)
from anovel.context.scene import (
    CandidateSceneProjection,
    OperationQuote,
    SceneDeltaBinding,
    SceneSpan,
    evidence_ref,
)
from anovel.contracts.models import CanonView
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactState,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
    SetFact,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import Entity
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.genre.extensions.business import (
    BusinessState,
    ResourceHolding,
    create_business_binding,
    transfer_resource,
)
from anovel.planning.models import (
    ForbiddenTransition,
    KnowledgeBoundary,
    RequiredTransition,
    RevealBoundary,
    ScenePlan,
    TransitionKind,
)
from anovel.planning.versions import PlanHistory, PlanVersion
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.scene import SceneProjection
from anovel.workflow.store import WorkflowStore

REVIEW = "synthetic-explicit-delta-mapping/not-human-review"
CHANGE_TEXT = "显式映射数据：余额从10记为20。"
ENDING_TEXT = "实际末段：甲停在记录桌前。"
OUTSIDE = "未投影片段：UNSELECTED_DRAFT_BODY_SENTINEL"
SCENE_TEXT = CHANGE_TEXT + "\n" + ENDING_TEXT
PROSE = (SCENE_TEXT + "\n" + OUTSIDE).encode()
UNCHANGED_PROSE = (
    "显式映射数据：余额仍为10。\n" + ENDING_TEXT + "\n" + OUTSIDE
).encode()


@pytest.fixture(autouse=True)
def no_network_or_provider_construction(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Scene projection tests must remain entirely offline")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)


def scene_case(
    *,
    anchor="urban.business.realistic",
    target_required=False,
    target_knowledge=False,
    target_intent=False,
    hidden=False,
    source_required=False,
    source_forbidden=False,
    source_protected=False,
    sources=(),
):
    fixture, _history, view = make_case(
        anchor=anchor,
        reader_boundaries=(RevealBoundary(eid("secret"), NarrativePosition(3, 1)),)
        if hidden
        else (),
    )
    first = fixture.vision.chapters[0]
    source = replace(
        first.scenes[0],
        required=(RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 20),)
        if source_required
        else (),
        forbidden=(ForbiddenTransition(eid("balance"), TransitionKind.SET_FACT, 20),)
        if source_forbidden
        else (),
        protected_fact_ids=(eid("balance"),) if source_protected else (),
    )
    target = ScenePlan(
        eid("scene-1-next"),
        2,
        "在同章第二场核对前场留下的显式事实。",
        required=(RequiredTransition(eid("balance"), TransitionKind.SET_FACT, 30),)
        if target_required
        else (),
        protected_fact_ids=() if target_required else (eid("balance"),),
        knowledge_boundaries=(
            KnowledgeBoundary(eid("alice"), must_know=(eid("balance"),)),
        )
        if target_knowledge
        else (),
        intent_ids=(eid("intent"),) if target_intent else (),
    )
    arc = fixture.vision.arcs[0]
    vision = replace(
        fixture.vision,
        arcs=(
            replace(
                arc,
                chapters=(
                    replace(first, scenes=(source, target)),
                    *arc.chapters[1:],
                ),
            ),
        ),
    )
    if target_intent:
        knowledge = json.loads(fixture.knowledge_bytes)
        knowledge["intents"][0]["based_on"] = [eid("balance").to_dict()]
        fixture = replace(fixture, knowledge_bytes=canonical_bytes(knowledge))
    fixture = replace(fixture, vision=vision)
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    budget, policies = ContextBudget(100000), (policy_for(),)
    frozen = FrozenChapterInput.freeze(
        history=history,
        chapter_id=first.id,
        fixture=fixture,
        view=view,
        budget=budget,
        policies=policies,
        instructions="只返回显式合成测试text，不调用网络。",
        template_version="offline-two-scene-contract-v1",
        sources=sources,
    )
    return SimpleNamespace(
        fixture=fixture,
        history=history,
        view=view,
        frozen=frozen,
        budget=budget,
        policies=policies,
    )


def saved_scene(tmp_path, *, prose=PROSE, **case_options):
    case = scene_case(**case_options)
    env = harness(
        tmp_path, adapter=CountingLocalAdapter(output={"text": prose.decode()})
    )
    saved = start(env, case)
    assert saved.state == "DRAFT_SAVED" and saved.prose == prose
    return case, env, saved


def spans(prose=PROSE):
    text = prose.decode()
    end = text.index("\n" + OUTSIDE)
    ending_start = text.index(ENDING_TEXT)
    first_end = text.index("\n")
    return (
        SceneSpan(0, end, text[:end]),
        SceneSpan(ending_start, end, text[ending_start:end]),
        SceneSpan(0, first_end, text[:first_end]),
    )


def binding_for(
    saved, case, *, change=True, target="balance", value=20, ending_fact_ids=()
):
    if not change:
        return SceneDeltaBinding(None, REVIEW, ending_fact_ids=ending_fact_ids)
    _source, _ending, quote = spans(saved.prose)
    source_id = saved.contract.scenes[0].id
    before = case.view.baseline.get(eid(target))
    meta = OperationMeta(
        eid("explicit-change"),
        eid(target),
        FactPath.VALUE,
        Precondition.from_snapshot(before),
        ProseEvidence(
            source_id,
            NarrativePosition(1, 1),
            evidence_ref(RUN, saved.revision, saved.prose_hash, quote),
        ),
        REVIEW,
    )
    delta = NarrativeDelta(
        eid("explicit-delta"),
        BRANCH,
        saved.contract.parent_ref,
        source_id,
        (SetFact(meta, value),),
    )
    return SceneDeltaBinding(
        delta, REVIEW, (OperationQuote(meta.id, quote),), ending_fact_ids
    )


def project(env, case, saved, *, binding=None, **changes):
    source_span, ending_span, _quote = spans(saved.prose)
    args = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "expected_record_hash": saved.record_hash,
        "source_scene_id": saved.contract.scenes[0].id,
        "target_scene_id": saved.contract.scenes[1].id,
        "source_span": source_span,
        "ending_span": ending_span,
        "delta_binding": binding if binding is not None else binding_for(saved, case),
    }
    args.update(changes)
    return env.workflow.project_scene(case.frozen, **args)


def candidate(saved, binding, **changes):
    source_span, ending_span, _quote = spans(saved.prose)
    args = {
        "source_run_id": RUN,
        "source_revision": saved.revision,
        "source_record_hash": saved.record_hash,
        "source_input_hash": saved.input_hash,
        "source_prose": saved.prose,
        "source_scene_id": saved.contract.scenes[0].id,
        "target_scene_id": saved.contract.scenes[1].id,
        "source_span": source_span,
        "ending_span": ending_span,
        "binding": binding,
    }
    args.update(changes)
    return CandidateSceneProjection.create(saved.contract, **args)


class ObservedCache(ContextCache):
    def __init__(self):
        super().__init__()
        self.reads = 0

    def get(self, inputs):
        self.reads += 1
        return super().get(inputs)


@pytest.mark.parametrize(
    "anchor", ["urban.business.realistic", "fantasy.eastern.progression"]
)
def test_changed_fact_reaches_real_second_scene_without_canon_or_draft_publication(
    tmp_path, anchor
):
    case, env, saved = saved_scene(tmp_path, anchor=anchor)
    canon_before = canonical_bytes(case.view.to_dict())
    result = project(env, case, saved)
    after = result.candidate.replay(saved.contract)
    assert after.get(eid("balance")).state == FactState.known(20)
    assert after.get(eid("balance")).revision == 1
    assert result.candidate.changed_ids(saved.contract) == frozenset({eid("balance")})
    assert result.candidate.before_hash != result.candidate.after_hash
    assert (
        after.parent_ref == case.view.baseline.parent_ref == saved.contract.parent_ref
    )
    assert canonical_bytes(case.view.to_dict()) == canon_before
    assert case.view.baseline.get(eid("balance")).state == FactState.known(10)
    fact = next(v for v in result.context.items if v.id == "fact:balance")
    assert fact.kind == "DRAFT_CANDIDATE_FACT" and fact.required
    assert fact.data["state"]["value"] == 20
    assert fact.data["epistemic_kind"] == "DRAFT_CANDIDATE_NOT_ACTOR_KNOWLEDGE"
    assert result.context.scene_id == saved.contract.scenes[1].id
    assert result.context.role is ContextRole.WRITER
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )
    assert not saved.accepted and saved.revision == 1 and env.adapter.calls == 1


def test_explicit_no_fact_change_keeps_baseline_but_binds_actual_scene_ending(tmp_path):
    case, env, saved = saved_scene(tmp_path, prose=UNCHANGED_PROSE)
    result = project(env, case, saved, binding=binding_for(saved, case, change=False))
    assert result.candidate.binding.delta is None
    assert result.candidate.before_hash == result.candidate.after_hash
    assert result.candidate.changed_ids(saved.contract) == frozenset()
    assert result.candidate.replay(saved.contract) == case.view.baseline
    ending = next(
        v for v in result.context.items if v.kind == "ACTUAL_PRECEDING_SCENE_ENDING"
    )
    provenance = next(
        v for v in result.context.items if v.kind == "DRAFT_CANDIDATE_PROVENANCE"
    )
    assert ending.required and ending.data["text"] == ENDING_TEXT
    assert (
        provenance.required
        and provenance.data["meaning"] == "UNCOMMITTED_SCENE_CANDIDATE"
    )
    assert not any(v.kind == "DRAFT_CANDIDATE_FACT" for v in result.context.items)


def test_author_fact_selection_requires_a_unique_compatible_quote(tmp_path):
    literal = "balance变为20。"
    rumor = "听说secret变为false。"
    prose = f"{literal}\n{rumor}\n重复。重复。\n{CHANGE_TEXT}\n\n{ENDING_TEXT}"
    case, env, saved = saved_scene(tmp_path, prose=prose.encode())

    def submit(edit):
        return env.workflow.project_scene(
            case.frozen,
            project=PROJECT,
            branch=BRANCH,
            run_id=RUN,
            expected_record_hash=saved.record_hash,
            fact_edits=[edit],
        )

    invalid = (
        ({"quote": "缺失。", "value": 20}, "SCENE_FACT_QUOTE_NOT_FOUND"),
        ({"quote": "重复。", "value": 20}, "SCENE_FACT_QUOTE_AMBIGUOUS"),
        ({"quote": literal, "value": 21}, "SCENE_FACT_SELECTION_CONFLICT"),
        ({"quote": "变为20。", "value": 20}, "SCENE_FACT_SELECTION_CONFLICT"),
        (
            {"quote": "secret变为false。", "value": False},
            "SCENE_FACT_SELECTION_CONFLICT",
        ),
        ({"quote": literal, "value": []}, "INVALID_SCENE_FACT_VALUE"),
        ({"quote": CHANGE_TEXT, "value": 20}, "SCENE_FACT_ID_REQUIRED"),
        (
            {"quote": CHANGE_TEXT, "value": "20", "fact_id": "balance"},
            "INVALID_SCENE_FACT_VALUE",
        ),
    )
    for edit, code in invalid:
        with pytest.raises(WorkflowError, match=f"^{code}$"):
            submit(edit)

    automatic = submit({"quote": literal, "value": 20})
    explicit = submit({"quote": CHANGE_TEXT, "value": 20, "fact_id": "balance"})
    assert automatic.candidate.after_hash == explicit.candidate.after_hash
    assert automatic.candidate.binding.operation_quotes[0].span.quote == literal
    assert explicit.candidate.binding.operation_quotes[0].span.quote == CHANGE_TEXT
    for projection in (automatic, explicit):
        fact = next(
            item for item in projection.context.items if item.id == "fact:balance"
        )
        assert fact.data["state"]["value"] == 20
    assert env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN) == saved
    assert env.adapter.calls == 1


def test_replace_with_fact_edits_preserves_draft_on_rejection_and_recovers_export(
    tmp_path, monkeypatch
):
    case, env, saved = saved_scene(tmp_path)
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    quote = "balance变为20。"
    prose = f"{quote}\n\n{ENDING_TEXT}"
    edits = [{"quote": quote, "value": 20}]
    path = tmp_path / "scene-projection.json"
    request = {
        "operation": "REPLACE_DRAFT_AND_PROJECT_SCENE",
        "current_input": case.frozen.to_dict(),
        **scope,
        "expected_revision": saved.revision,
        "expected_prose_hash": saved.prose_hash,
        "text": prose,
        "fact_edits": edits,
        "output": str(path),
    }
    task = WorkflowTaskAdapter(env.workflow)
    before = env.store_path.read_bytes()
    with pytest.raises(WorkflowError, match="^SCENE_FACT_SELECTION_CONFLICT$"):
        task.execute(request | {"fact_edits": [{"quote": quote, "value": 21}]})
    with pytest.raises(WorkflowError, match="^DRAFT_REVISION_CONFLICT$"):
        task.execute(request | {"expected_prose_hash": "0" * 64})
    assert not path.exists()
    path.write_bytes(b"existing export")
    with pytest.raises(WorkflowError, match="^SCENE_PROJECTION_EXPORT_FAILED$"):
        task.execute(request)
    assert env.store_path.read_bytes() == before
    assert path.read_bytes() == b"existing export"
    path.unlink()

    def fail_export(*_args, **_kwargs):
        raise WorkflowError("SCENE_PROJECTION_EXPORT_FAILED")

    with monkeypatch.context() as patch:
        patch.setattr(env.workflow, "export_scene_projection", fail_export)
        with pytest.raises(
            WorkflowError, match="^DRAFT_SAVED_SCENE_PROJECTION_EXPORT_FAILED$"
        ):
            task.execute(request)
    edited = env.workflow.inspect(**scope)
    assert edited.revision == saved.revision + 1 and edited.prose == prose.encode()
    assert edited.versions[:-1] == saved.versions
    with pytest.raises(WorkflowError, match="^DRAFT_REVISION_CONFLICT$"):
        task.execute(request)
    projection = env.workflow.project_scene(
        case.frozen, **scope, expected_record_hash=edited.record_hash, fact_edits=edits
    )
    env.workflow.export_scene_projection(projection, output=path)
    assert SceneProjection.from_dict(json.loads(path.read_bytes())) == projection
    assert projection.candidate.source_record_hash == edited.record_hash
    assert projection.candidate.ending_span.quote == ENDING_TEXT
    assert env.adapter.calls == 1


def test_replace_with_fact_edits_validates_scene_contract_before_saving(tmp_path):
    case, env, saved = saved_scene(tmp_path, source_protected=True)
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    quote = "balance变为20。"
    path = tmp_path / "protected-projection.json"
    before = env.store_path.read_bytes()
    with pytest.raises(ContextError, match="^INVALID_CANDIDATE_SCENE_PROJECTION$"):
        env.workflow.replace_draft_and_project_scene(
            case.frozen,
            **scope,
            expected_revision=saved.revision,
            expected_prose_hash=saved.prose_hash,
            prose=f"{quote}\n\n{ENDING_TEXT}".encode(),
            fact_edits=[{"quote": quote, "value": 20}],
            output=path,
        )
    assert not path.exists() and env.store_path.read_bytes() == before
    assert env.adapter.calls == 1


def test_audit_roundtrip_replays_candidate_without_forwarding_full_source_or_baseline(
    tmp_path,
):
    case, env, saved = saved_scene(tmp_path, hidden=True)
    result = project(env, case, saved)
    restored = SceneProjection.from_dict(result.to_dict())
    assert restored == result
    assert restored.inputs == FrozenContextInputs.from_dict(result.inputs.to_dict())
    assert restored.candidate == CandidateSceneProjection.from_dict(
        result.candidate.to_dict()
    )
    assert (
        env.workflow.consume_scene_projection(case.frozen, restored).model_bytes
        == result.context.model_bytes
    )
    assert b"UNSELECTED_DRAFT_BODY_SENTINEL" not in result.context.model_bytes
    assert b"conceals-defect" not in result.context.model_bytes
    assert b"FACT_BASELINE" not in result.context.model_bytes
    assert result.inputs.to_dict()["visibility"] == "AUDIT_ONLY"
    assert result.to_dict()["visibility"] == "AUDIT_ONLY"
    assert b"UNSELECTED_DRAFT_BODY_SENTINEL" in result.candidate.source_prose


def test_reopened_workflow_can_consume_retained_projection_without_gateway(tmp_path):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    reopened = ChapterWorkflow(WorkflowStore(env.store_path))
    assert reopened.consume_scene_projection(case.frozen, result) == result.context
    assert env.adapter.calls == 1


def test_valid_cache_hit_keeps_distinct_explicit_mapping_identities_separate(tmp_path):
    case, env, saved = saved_scene(tmp_path)
    cache = ObservedCache()
    changed = project(env, case, saved, cache=cache)
    assert compile_context(changed.inputs, cache).cache_hit
    another = binding_for(saved, case)
    operation = another.delta.operations[0]
    review = REVIEW + "/second-mapping"
    another = replace(
        another,
        review_ref=review,
        delta=replace(
            another.delta,
            operations=(
                replace(
                    operation, meta=replace(operation.meta, authorization_ref=review)
                ),
            ),
        ),
    )
    remapped = project(env, case, saved, binding=another, cache=cache)
    assert changed.context.cache_key != remapped.context.cache_key
    assert changed.inputs.content_hash != remapped.inputs.content_hash
    assert (
        env.workflow.consume_scene_projection(case.frozen, changed, cache=cache)
        == changed.context
    )
    assert cache.reads >= 4


@pytest.mark.parametrize("operation", ["project", "consume"])
def test_durable_edit_rejects_old_projection_before_cache_lookup(tmp_path, operation):
    case, env, saved = saved_scene(tmp_path)
    cache = ObservedCache()
    old = project(env, case, saved, cache=cache)
    edited = env.workflow.replace_draft(
        case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        expected_revision=saved.revision,
        expected_prose_hash=saved.prose_hash,
        prose=PROSE.replace(b"10", b"11"),
    )
    reads = cache.reads
    with pytest.raises(WorkflowError, match="SCENE_SOURCE_CHANGED"):
        if operation == "project":
            project(env, case, saved, cache=cache)
        else:
            env.workflow.consume_scene_projection(case.frozen, old, cache=cache)
    assert cache.reads == reads and edited.revision == 2
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == edited.record_hash
    )
    assert env.adapter.calls == 1


@pytest.mark.parametrize("operation", ["project", "consume"])
def test_changed_frozen_input_rejected_before_cache(tmp_path, operation):
    case, env, saved = saved_scene(tmp_path)
    cache = ObservedCache()
    old = project(env, case, saved, cache=cache)
    row = case.frozen.to_dict()
    row["instructions"] = "不同的显式输入，不得复用旧缓存。"
    changed = FrozenChapterInput.from_dict(row)
    reads = cache.reads
    with pytest.raises(WorkflowError, match="WORKFLOW_INPUT_CHANGED"):
        if operation == "project":
            project(env, replace_namespace(case, frozen=changed), saved, cache=cache)
        else:
            env.workflow.consume_scene_projection(changed, old, cache=cache)
    assert cache.reads == reads


def replace_namespace(value, **changes):
    return SimpleNamespace(**(vars(value) | changes))


@pytest.mark.parametrize(
    "scope",
    [
        {"project": "other-project"},
        {"branch": "other-branch"},
        {"run_id": "missing-run"},
    ],
)
def test_wrong_scope_cannot_obtain_candidate_context(tmp_path, scope):
    case, env, saved = saved_scene(tmp_path)
    with pytest.raises(WorkflowError):
        project(env, case, saved, **scope)
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


@pytest.mark.parametrize(
    "dependency,code",
    [
        ("target_required", "SCENE_PRECONDITION_STALE"),
        ("target_knowledge", "SCENE_KNOWLEDGE_OR_INTENT_STALE"),
        ("target_intent", "SCENE_KNOWLEDGE_OR_INTENT_STALE"),
    ],
)
def test_changed_fact_does_not_silently_rewrite_frozen_target_dependencies(
    tmp_path, dependency, code
):
    case, env, saved = saved_scene(tmp_path, **{dependency: True})
    contract_before = saved.contract_bytes
    with pytest.raises(WorkflowError, match=code):
        project(env, case, saved)
    assert saved.contract_bytes == contract_before
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


@pytest.mark.parametrize("mode", ["changed-hidden-fact", "hidden-ending-fact"])
def test_hidden_fact_cannot_enter_second_scene_through_candidate_or_ending(
    tmp_path, mode
):
    case, env, saved = saved_scene(tmp_path, hidden=True)
    binding = (
        binding_for(saved, case, target="secret", value=False)
        if mode == "changed-hidden-fact"
        else binding_for(saved, case, change=False, ending_fact_ids=(eid("secret"),))
    )
    with pytest.raises(WorkflowError, match="SCENE_CANDIDATE_VISIBILITY_CONFLICT"):
        project(env, case, saved, binding=binding)
    assert env.adapter.calls == 1


def test_explicit_hidden_nochange_operation_is_not_a_visibility_bypass(tmp_path):
    case, env, saved = saved_scene(tmp_path, hidden=True)
    mapping = binding_for(saved, case, target="secret", value=False)
    operation = NoChange(mapping.delta.operations[0].meta)
    mapping = replace(mapping, delta=replace(mapping.delta, operations=(operation,)))
    assert not candidate(saved, mapping).changed_ids(saved.contract)
    assert mapping.ending_fact_ids == ()
    with pytest.raises(WorkflowError, match="SCENE_CANDIDATE_VISIBILITY_CONFLICT"):
        project(env, case, saved, binding=mapping)


@pytest.mark.parametrize("role", [ContextRole.CHARACTER, ContextRole.REVIEWER])
def test_candidate_is_not_character_knowledge_or_reviewer_context(tmp_path, role):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    request = replace(
        result.inputs.request,
        role=role,
        actor_id=eid("alice") if role is ContextRole.CHARACTER else None,
    )
    blocked = compile_context(replace(result.inputs, request=request))
    assert blocked.artifact is None
    assert blocked.diagnostics[0].code == "SCENE_CANDIDATE_ROLE_OR_TARGET_MISMATCH"


def test_candidate_target_cannot_be_swapped_at_context_compile(tmp_path):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    inputs = replace(
        result.inputs,
        request=replace(result.inputs.request, scene_id=saved.contract.scenes[0].id),
    )
    blocked = compile_context(inputs)
    assert blocked.artifact is None
    assert blocked.diagnostics[0].code == "SCENE_CANDIDATE_ROLE_OR_TARGET_MISMATCH"


def test_mandatory_candidate_and_actual_ending_cannot_be_truncated_to_fit_budget(
    tmp_path,
):
    case, env, saved = saved_scene(tmp_path)
    cache = ObservedCache()
    full = project(env, case, saved, cache=cache)
    floor = replace(
        full.context,
        items=tuple(v for v in full.context.items if v.required),
        selections=(),
    ).estimated_units
    fitting = project(env, case, saved, budget=ContextBudget(floor), cache=cache)
    assert fitting.context.estimated_units == floor
    assert {v.kind for v in fitting.context.items} >= {
        "DRAFT_CANDIDATE_PROVENANCE",
        "DRAFT_CANDIDATE_FACT",
        "ACTUAL_PRECEDING_SCENE_ENDING",
    }
    with pytest.raises(WorkflowError, match="MANDATORY_BUDGET_OVERFLOW"):
        project(env, case, saved, budget=ContextBudget(floor - 1), cache=cache)
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


@pytest.mark.parametrize("pair", ["reverse", "same", "other-chapter"])
def test_only_explicit_first_to_adjacent_second_scene_pair_is_supported(tmp_path, pair):
    case, env, saved = saved_scene(tmp_path)
    source_id, target_id = saved.contract.scenes[0].id, saved.contract.scenes[1].id
    if pair == "reverse":
        source_id, target_id = target_id, source_id
    elif pair == "same":
        target_id = source_id
    else:
        target_id = case.fixture.vision.chapters[1].scenes[0].id
    with pytest.raises(ContextError):
        project(env, case, saved, source_scene_id=source_id, target_scene_id=target_id)


@pytest.mark.parametrize(
    "fault", ["source-quote", "ending-quote", "ending-not-at-end", "byte-offset"]
)
def test_actual_unicode_fragment_and_ending_are_checked_against_saved_prose(
    tmp_path, fault
):
    case, env, saved = saved_scene(tmp_path)
    source, ending, _quote = spans()
    with pytest.raises(ContextError):
        if fault == "source-quote":
            source = replace(source, quote=source.quote + "伪造")
        elif fault == "ending-quote":
            ending = replace(ending, quote="并非真实末段")
        elif fault == "ending-not-at-end":
            ending = SceneSpan(0, len(CHANGE_TEXT), CHANGE_TEXT)
        else:
            ending = SceneSpan(
                len(SCENE_TEXT[: ending.start].encode()),
                len(SCENE_TEXT.encode()),
                ending.quote,
            )
        project(env, case, saved, source_span=source, ending_span=ending)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-quote",
        "unknown-operation",
        "evidence-ref",
        "review-ref",
        "position",
        "parent",
        "branch",
        "precondition",
    ],
)
def test_explicit_delta_must_bind_each_operation_to_same_draft_fragment(
    tmp_path, fault
):
    case, env, saved = saved_scene(tmp_path)
    binding = binding_for(saved, case)
    delta, operation = binding.delta, binding.delta.operations[0]
    with pytest.raises(ContextError):
        if fault == "missing-quote":
            binding = replace(binding, operation_quotes=())
        elif fault == "unknown-operation":
            binding = replace(
                binding,
                operation_quotes=(
                    replace(binding.operation_quotes[0], operation_id=eid("unmapped")),
                ),
            )
        elif fault == "review-ref":
            binding = replace(binding, review_ref="different-explicit-review")
        else:
            meta = operation.meta
            if fault == "evidence-ref":
                meta = replace(
                    meta,
                    evidence=replace(
                        meta.evidence, evidence_ref="unbound-prose-reference"
                    ),
                )
            elif fault == "position":
                meta = replace(
                    meta,
                    evidence=replace(meta.evidence, position=NarrativePosition(1, 2)),
                )
            elif fault == "precondition":
                meta = replace(meta, expected=Precondition(0, FactState.known(11)))
            delta = replace(delta, operations=(replace(operation, meta=meta),))
            if fault == "parent":
                delta = replace(delta, parent_ref="sha256:" + "c" * 64)
            elif fault == "branch":
                delta = replace(delta, branch="other-branch")
            binding = replace(binding, delta=delta)
        project(env, case, saved, binding=binding)
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


def test_nochange_cannot_smuggle_operation_quotes_or_unknown_ending_fact(tmp_path):
    case, _env, saved = saved_scene(tmp_path)
    original = binding_for(saved, case)
    with pytest.raises(ContextError):
        candidate(saved, SceneDeltaBinding(None, REVIEW, original.operation_quotes))
    with pytest.raises(ContextError):
        candidate(
            saved,
            SceneDeltaBinding(None, REVIEW, ending_fact_ids=(eid("unknown-fact"),)),
        )


def test_candidate_derived_after_hash_is_replayed_instead_of_trusting_serialized_claim(
    tmp_path,
):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    row = result.candidate.to_dict()
    row["after_hash"] = "f" * 64
    with pytest.raises(ContextError):
        CandidateSceneProjection.from_dict(row)
    assert (
        result.candidate.after_hash
        == sha256(
            canonical_bytes(result.candidate.replay(saved.contract).to_dict())
        ).hexdigest()
    )


def test_legacy_no_candidate_frozen_input_keeps_exact_serialization_bytes(tmp_path):
    _case, _env, saved = saved_scene(tmp_path)
    inputs = FrozenContextInputs.from_contract(
        saved.contract,
        ContextRequest(
            PROJECT,
            BRANCH,
            saved.contract.parent_ref,
            saved.contract.content_hash,
            ContextRole.WRITER,
            saved.context.budget,
        ),
    )
    legacy = {
        "kind": "FROZEN_CONTEXT_INPUTS",
        "schema_version": "1.0",
        "visibility": "AUDIT_ONLY",
        "contract_base64": b64encode(saved.contract_bytes).decode(),
        "contract_hash": saved.contract.content_hash,
        "request": inputs.request.to_dict(),
        "sources": [],
    }
    assert inputs.candidate is None
    assert "candidate" not in inputs.to_dict()
    assert canonical_bytes(inputs.to_dict()) == canonical_bytes(legacy)
    assert inputs.content_hash == sha256(canonical_bytes(legacy)).hexdigest()
    assert FrozenContextInputs.from_dict(legacy) == inputs


def test_explicit_delta_satisfies_finite_source_required_transition(tmp_path):
    case, env, saved = saved_scene(tmp_path, source_required=True)
    result = project(env, case, saved)
    assert result.candidate.replay(saved.contract).get(
        eid("balance")
    ).state == FactState.known(20)
    assert env.adapter.calls == 1


@pytest.mark.parametrize(
    "fault", ["missing-required", "wrong-required-value", "forbidden", "protected"]
)
def test_source_finite_contract_is_checked_before_next_scene_projection(
    tmp_path, fault
):
    options = (
        {"source_required": True}
        if fault in {"missing-required", "wrong-required-value"}
        else {"source_forbidden" if fault == "forbidden" else "source_protected": True}
    )
    case, env, saved = saved_scene(tmp_path, **options)
    binding = binding_for(
        saved,
        case,
        change=fault != "missing-required",
        value=21 if fault == "wrong-required-value" else 20,
    )
    with pytest.raises(ContextError):
        project(env, case, saved, binding=binding)
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )
    assert case.view.baseline.get(eid("balance")).state == FactState.known(10)


def supplied_source(name, *, fact_ids=(), required=True, content=None):
    return ContextSource(
        name,
        PROJECT,
        BRANCH,
        PARENT,
        "synthetic-supplied/" + name,
        "v1",
        content if content is not None else ("离线来源：" + name).encode(),
        (ContextRole.WRITER,),
        NarrativePosition(1, 1),
        fact_ids=fact_ids,
        required=required,
    )


def test_legitimate_reverse_order_sources_are_canonicalized_and_consumed(tmp_path):
    sources = (supplied_source("z-source"), supplied_source("a-source"))
    case, env, saved = saved_scene(tmp_path, sources=sources)
    assert [v["id"] for v in case.frozen.to_dict()["sources"]] == [
        "z-source",
        "a-source",
    ]
    result = project(env, case, saved)
    assert [v.id for v in result.inputs.sources] == ["a-source", "z-source"]
    consumed = env.workflow.consume_scene_projection(case.frozen, result)
    assert consumed == result.context
    assert {v.id for v in consumed.items} >= {"source:a-source", "source:z-source"}


def test_changed_supplied_source_content_invalidates_old_projection_before_cache(
    tmp_path,
):
    sources = (supplied_source("z-source"), supplied_source("a-source"))
    case, env, saved = saved_scene(tmp_path, sources=sources)
    cache = ObservedCache()
    result = project(env, case, saved, cache=cache)
    current = case.frozen.to_dict()
    current["sources"][0] = replace(
        sources[0], content=b"changed-source-content"
    ).to_dict()
    changed = FrozenChapterInput.from_dict(current)
    reads = cache.reads
    with pytest.raises(WorkflowError, match="WORKFLOW_INPUT_CHANGED"):
        env.workflow.consume_scene_projection(changed, result, cache=cache)
    assert cache.reads == reads


def test_internally_consistent_projection_with_extra_source_is_rejected_before_cache(
    tmp_path,
):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    inputs = replace(result.inputs, sources=(supplied_source("extra"),))
    rebuilt = compile_context(inputs)
    assert rebuilt.artifact is not None
    forgery = SceneProjection(result.candidate, inputs, rebuilt.artifact)
    cache = ObservedCache()
    cache.put(forgery.context)
    with pytest.raises(WorkflowError, match="SCENE_SOURCES_CHANGED"):
        env.workflow.consume_scene_projection(case.frozen, forgery, cache=cache)
    assert cache.reads == 0


@pytest.mark.parametrize("required", [False, True])
def test_parent_source_depending_on_changed_fact_is_excluded_or_blocks(
    tmp_path, required
):
    source = supplied_source(
        "old-balance",
        fact_ids=(eid("balance"),),
        required=required,
        content=b"old-balance=10",
    )
    case, env, saved = saved_scene(tmp_path, sources=(source,))
    if required:
        with pytest.raises(WorkflowError, match="VISIBILITY_REQUIRED_CONFLICT"):
            project(env, case, saved)
    else:
        result = project(env, case, saved)
        assert b"old-balance=10" not in result.context.model_bytes
        assert any(
            v.reason == "SCENE_SOURCE_FACT_DEPENDENCY_STALE" and not v.included
            for v in result.context.selections
        )


@pytest.mark.parametrize(
    "form", ["raw-candidate", "base64-prose", "structured-candidate"]
)
@pytest.mark.parametrize("required", [False, True])
def test_audit_candidate_or_full_prose_cannot_be_laundered_as_context_source(
    tmp_path, form, required
):
    case, env, saved = saved_scene(tmp_path)
    result = project(env, case, saved)
    if form == "raw-candidate":
        content = result.candidate.payload
    elif form == "base64-prose":
        content = b64encode(result.candidate.source_prose)
    else:
        content = json.dumps({"wrapped": result.candidate.to_dict()}, indent=2).encode()
    source = supplied_source("laundered", required=required, content=content)
    compiled = compile_context(replace(result.inputs, sources=(source,)))
    if required:
        assert compiled.artifact is None
        assert compiled.diagnostics[0].code == "VISIBILITY_REQUIRED_CONFLICT"
    else:
        assert compiled.artifact is not None
        assert not any(v.id == "source:laundered" for v in compiled.artifact.items)
        assert b"UNSELECTED_DRAFT_BODY_SENTINEL" not in compiled.artifact.model_bytes
        assert any(
            v.reason == "UNFILTERED_AUTHOR_INPUT" and not v.included
            for v in compiled.artifact.selections
        )


def test_registered_extension_sibling_dependency_blocks_without_direct_target_change(
    tmp_path,
):
    case = scene_case()
    genre = business_pack(project=PROJECT)
    business = BusinessState(
        (),
        (),
        (),
        (
            ResourceHolding(eid("stock-a"), eid("alice"), "widget", "piece", 8),
            ResourceHolding(eid("stock-b"), eid("bob"), "widget", "piece", 2),
        ),
    )
    extension = create_business_binding(
        genre, tuple(sorted(business.referenced_ids, key=str))
    )
    facts = business.to_facts("explicit-synthetic-business-root")
    seed = RootSeed(
        (
            *case.fixture.root_seed.entities,
            Entity(eid("stock-a"), "甲的物资"),
            Entity(eid("stock-b"), "乙的物资"),
        ),
        (),
        (*case.fixture.root_seed.facts, *facts),
        (extension,),
    )
    owner_fact = next(
        f
        for f in facts
        if f.proposition.subject == eid("stock-a")
        and f.proposition.predicate.endswith("resource.owner")
    )
    quantity_fact = next(
        f
        for f in facts
        if f.proposition.subject == eid("stock-a")
        and f.proposition.predicate.endswith("resource.quantity")
    )
    knowledge = case.fixture.knowledge
    for fact in facts:
        knowledge.add_fact(fact)
    arc = case.fixture.vision.arcs[0]
    first = arc.chapters[0]
    target = replace(
        first.scenes[1],
        protected_fact_ids=(),
        required=(RequiredTransition(owner_fact.id, TransitionKind.NO_CHANGE),),
    )
    vision = replace(
        case.fixture.vision,
        arcs=(
            replace(
                arc,
                chapters=(
                    replace(first, scenes=(first.scenes[0], target)),
                    *arc.chapters[1:],
                ),
            ),
        ),
    )
    fixture = replace(
        case.fixture,
        pack_binding=genre,
        root_seed=seed,
        vision=vision,
        knowledge_bytes=canonical_bytes(knowledge.to_dict()),
    )
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    baseline = FactBaseline.from_world_facts(
        PROJECT, BRANCH, PARENT, seed.facts, extensions=seed.extensions
    )
    view = CanonView(replace(case.view.root, seed=seed), baseline, None, 1)
    row = case.frozen.to_dict()
    row.update(
        fixture=fixture.to_dict(), history=history.to_dict(), view=view.to_dict()
    )
    case = replace_namespace(
        case,
        frozen=FrozenChapterInput.from_dict(row),
        fixture=fixture,
        history=history,
        view=view,
    )
    prose = (
        "显式映射数据：甲交给乙一件物资。\n" + ENDING_TEXT + "\n" + OUTSIDE
    ).encode()
    env = harness(
        tmp_path, adapter=CountingLocalAdapter(output={"text": prose.decode()})
    )
    saved = start(env, case)
    _source, _ending, quote = spans(saved.prose)
    delta = transfer_resource(
        baseline,
        eid("stock-a"),
        eid("stock-b"),
        1,
        delta_id=eid("resource-transfer"),
        evidence=ProseEvidence(
            saved.contract.scenes[0].id,
            NarrativePosition(1, 1),
            evidence_ref(RUN, saved.revision, saved.prose_hash, quote),
        ),
        authorization_ref=REVIEW,
    )
    mapping = SceneDeltaBinding(
        delta,
        REVIEW,
        tuple(OperationQuote(op.meta.id, quote) for op in delta.operations),
    )
    preview = candidate(saved, mapping)
    assert owner_fact.id not in preview.changed_ids(saved.contract)
    assert quantity_fact.id in preview.changed_ids(saved.contract)
    assert preview.replay(saved.contract).get(
        quantity_fact.id
    ).state == FactState.known(7)
    before = canonical_bytes(view.to_dict())
    with pytest.raises(WorkflowError, match="SCENE_EXTENSION_DEPENDENCY_STALE"):
        project(env, case, saved, binding=mapping)
    assert canonical_bytes(view.to_dict()) == before
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )
    assert env.adapter.calls == 1
