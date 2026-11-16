"""Role context from real PostgreSQL history, without context-side Canon writes.

The old isolated TEST issuer is used only to create an accepted predecessor.
Context compilation is offline and read-only, not Writer or production Permit.
"""

import json
from dataclasses import replace
from hashlib import sha256

import pytest
from test_v2_017_postgres import (
    BRANCH,
    admin_engine,
    assert_unchanged,
    commit_compiled,
    compile_at,
    counts,
    database,
    engine,
    fixture_data,
    history_for,
    ready_story,
)

from anovel.canon.chapter import CandidateEvidence
from anovel.canon.identity import canonical_bytes
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
from anovel.contracts.models import CanonView, ContinuationEvidence
from anovel.domain.events import NarrativePosition
from anovel.planning.models import RequiredTransition, TransitionKind

__all__ = ["admin_engine", "database", "engine"]


def frozen_inputs(
    contract, *, role=ContextRole.WRITER, actor_id=None, max_units=100000, sources=()
):
    request = ContextRequest(
        contract.project,
        contract.branch,
        contract.parent_ref,
        contract.content_hash,
        role,
        ContextBudget(max_units),
        actor_id=actor_id,
    )
    return FrozenContextInputs.from_contract(contract, request, sources=sources)


def accepted_predecessor(engine, name="urban"):
    fixture = fixture_data(name, quiet=True)
    # Explicit component derivative, preserving the actual approved root facts.
    # The old fact is made mandatory even though optional text is more recent.
    hidden = {v.fact_id for v in fixture.reader_boundaries}
    fact = next(
        f
        for f in fixture.root_seed.facts
        if f.id not in hidden and type(f.proposition.value) is int
    )
    arc = fixture.vision.arcs[0]
    chapter = arc.chapters[1]
    scene = replace(
        chapter.scenes[0],
        required=(RequiredTransition(fact.id, TransitionKind.NO_CHANGE),),
    )
    chapter = replace(chapter, scenes=(scene, *chapter.scenes[1:]))
    vision = replace(
        fixture.vision,
        arcs=(
            replace(arc, chapters=(arc.chapters[0], chapter, *arc.chapters[2:])),
            *fixture.vision.arcs[1:],
        ),
    )
    fixture = replace(
        fixture, vision=vision, review_ref="component-only/context-old-fact-scenario"
    )
    service, issuer, root = ready_story(engine, fixture)
    history = history_for(fixture)
    first, view = compile_at(service, fixture, history, root.commit_id)
    assert first.ok
    prose = "\ufeff这是上一章实际接受的正文。\r\n门外脚步停住，她把账册翻回旧页。 \n".encode()
    receipt = commit_compiled(
        service, issuer, fixture, view, first.contract, prose=prose
    )
    previous = service.load_commit(fixture.project, BRANCH, receipt.commit_id)
    text = prose.decode()
    ending = ContinuationEvidence.from_previous(
        previous, text.index("门外"), evidence_ref="actual-accepted-prose/ending"
    )
    current = CanonView.from_service(
        service, fixture.project, BRANCH, receipt.commit_id
    )
    result = compile_contract(history, chapter.id, fixture, current, ending)
    assert result.ok, result.diagnostics
    return fixture, service, root, receipt, result.contract, ending, fact


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_real_adopted_root_context_is_safe_and_compatible_with_existing_candidate_evidence(
    engine, name
):
    fixture = fixture_data(name)
    service, _issuer, root = ready_story(engine, fixture)
    compiled, view = compile_at(service, fixture, history_for(fixture), root.commit_id)
    assert compiled.ok
    before = counts(engine)
    writer = compile_context(frozen_inputs(compiled.contract))
    reviewer = compile_context(
        frozen_inputs(compiled.contract, role=ContextRole.REVIEWER)
    )
    assert writer.ok and reviewer.ok
    fact_id = fixture.reader_boundaries[0].fact_id
    private = next(f for f in fixture.root_seed.facts if f.id == fact_id)
    truth = str(private.proposition.value).encode()
    assert (
        truth not in writer.artifact.model_bytes
        and truth not in writer.artifact.to_bytes()
    )
    assert truth in reviewer.artifact.model_bytes
    evidence = CandidateEvidence(
        "CONTEXT",
        writer.artifact.to_bytes(),
        "test/context-byte-estimate",
        "1.0",
        "v2018-component-integration",
        "1.0",
    )
    assert evidence.content_hash == sha256(writer.artifact.to_bytes()).hexdigest()
    assert CandidateEvidence.from_dict(evidence.to_dict()) == evidence
    assert ContextArtifact.from_dict(json.loads(evidence.content)) == writer.artifact
    assert_unchanged(engine, fixture.project, before, root.commit_id)
    assert (
        service.load_root(fixture.project, BRANCH, root.commit_id).seed.to_dict()
        == view.root.seed.to_dict()
    )


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_real_old_required_fact_and_complete_ending_survive_new_optional_retrieval(
    engine, name
):
    fixture, service, _root, receipt, contract, ending, fact = accepted_predecessor(
        engine, name
    )
    before = counts(engine)
    plain = compile_context(frozen_inputs(contract))
    assert plain.ok
    optional = ContextSource(
        "recent-optional",
        fixture.project,
        BRANCH,
        receipt.commit_id,
        "test/recent-retrieval",
        "1.0",
        ("MORE_RECENT_OPTIONAL_63 " * (plain.artifact.estimated_units + 1)).encode(),
        (ContextRole.WRITER,),
        NarrativePosition(2, 1),
        priority=99999,
    )
    result = compile_context(
        frozen_inputs(
            contract, max_units=plain.artifact.estimated_units + 30, sources=(optional,)
        )
    )
    assert result.ok
    selected = next(
        i for i in result.artifact.items if i.kind == "ACTUAL_PREDECESSOR_ENDING"
    )
    assert selected.required and selected.data == ending.to_dict()
    assert selected.data["quote"] == ending.quote and selected.data["quote"].endswith(
        " \n"
    )
    assert (
        selected.data["prose_hash"]
        == sha256(
            service.load_commit(
                fixture.project, BRANCH, receipt.commit_id
            ).candidate.prose
        ).hexdigest()
    )
    assert any(
        i.required and i.kind == "FACT" and fact.id.local_id.encode() in i.content
        for i in result.artifact.items
    )
    assert b"MORE_RECENT_OPTIONAL_63" not in result.artifact.model_bytes
    assert any(
        not s.included and "BUDGET" in s.reason for s in result.artifact.selections
    )
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)


def test_real_predecessor_cannot_be_replaced_by_hook_or_partial_budget_artifact(engine):
    fixture, service, _root, receipt, contract, ending, _fact = accepted_predecessor(
        engine
    )
    before = counts(engine)
    blocked = compile_context(frozen_inputs(contract, max_units=1))
    assert not blocked.ok and blocked.artifact is None
    full = compile_context(frozen_inputs(contract))
    assert full.ok
    ending_item = next(
        i for i in full.artifact.items if i.kind == "ACTUAL_PREDECESSOR_ENDING"
    )
    assert ending_item.data == ending.to_dict()
    assert ending_item.data["quote"] != "这个大纲的高潮将引出下一章。"
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)


def test_real_context_frozen_replay_and_role_cache_do_not_write_or_teach_characters(
    engine, monkeypatch
):
    fixture = fixture_data("fantasy")
    service, _issuer, root = ready_story(engine, fixture)
    compiled, _view = compile_at(service, fixture, history_for(fixture), root.commit_id)
    contract = compiled.contract
    before = counts(engine)
    knowledge_before = canonical_bytes(fixture.knowledge.to_dict())
    cache = ContextCache()
    reviewer = compile_context(
        frozen_inputs(contract, role=ContextRole.REVIEWER), cache
    )
    writer_inputs = frozen_inputs(contract)
    writer = compile_context(writer_inputs, cache)
    assert reviewer.ok and writer.ok and not writer.cache_hit
    assert reviewer.artifact.cache_key != writer.artifact.cache_key
    frozen = writer_inputs.to_bytes()

    def forbidden(*_args, **_kwargs):
        pytest.fail("Frozen context replay must use no database or network")

    monkeypatch.setattr(service, "rebuild_snapshot", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    replay = compile_context(FrozenContextInputs.from_dict(json.loads(frozen)))
    assert replay.ok and replay.artifact.to_bytes() == writer.artifact.to_bytes()
    assert canonical_bytes(fixture.knowledge.to_dict()) == knowledge_before
    assert_unchanged(engine, fixture.project, before, root.commit_id)
