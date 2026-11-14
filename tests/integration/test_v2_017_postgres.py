"""Contract compilation from actual retained PostgreSQL Canon read inputs.

All story writes below use the existing CanonCommitService and isolated TEST
issuer. No production quality/Permit, Writer, or independent human review is
invented; actual adopted fixture sources are separately checked by the suite.
"""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from test_v2_010 import (
    ACTOR,
    AUTHORIZATION,
    BRANCH,
    ISSUER,
    admin_engine,
    counts,
    database,
    engine,
)

from anovel.canon.chapter import CandidateEvidence, ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes
from anovel.canon.models import CanonError
from anovel.canon.repository import Repository
from anovel.contracts.compiler import compile_contract, contract_is_current
from anovel.contracts.models import CanonView, ContinuationEvidence
from anovel.domain.delta import (
    FactPath,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.planning.models import StoryFixture
from anovel.planning.versions import PlanHistory, PlanVersion

__all__ = ["admin_engine", "database", "engine"]
DIRECTORY = Path(__file__).resolve().parents[2] / "specs/fixtures/stories"
PROSE = "\ufeff她记下这一次选择的代价。\r\n门外脚步停住，她没有立刻开门。 \n".encode()


def fixture_data(name, *, quiet=False):
    fixture = StoryFixture.from_dict(
        json.loads((DIRECTORY / (name + ".json")).read_text())
    )
    if quiet:
        # A clearly labeled component derivative, not a new human story approval.
        arc = fixture.vision.arcs[0]
        first = arc.chapters[0]
        scenes = tuple(replace(s, required=()) for s in first.scenes)
        changed = replace(first, scenes=scenes)
        vision = replace(
            fixture.vision,
            arcs=(
                replace(arc, chapters=(changed, *arc.chapters[1:])),
                *fixture.vision.arcs[1:],
            ),
        )
        fixture = replace(
            fixture,
            vision=vision,
            review_ref="component-only/quiet-derivative-not-human-evidence",
        )
    return fixture


def history_for(fixture):
    return PlanHistory(
        (
            PlanVersion(
                EntityId(fixture.project, "pg-plan"),
                1,
                None,
                fixture.vision,
                fixture.content_hash,
            ),
        )
    )


def ready_story(engine, fixture):
    project = fixture.project
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(project, BRANCH, ACTOR)
    ticket = service.begin_root(project, BRANCH, ACTOR, "v2017-root")
    root = service.initialize_root(
        ticket, fixture.root_seed, "给定故事的初始事实；尚未生成正式小说。".encode()
    )
    service.configure_chapter_authority(project, BRANCH, ACTOR, ISSUER, "TEST-POLICY-1")
    issuer = ProtectedPermitIssuer(
        engine, test_database=engine.url.database, issuer_id=ISSUER
    )
    return service, issuer, root


def assert_unchanged(engine, project, before, head):
    assert counts(engine) == before
    assert Repository(engine).head(project, BRANCH) == head


def compile_at(service, fixture, history, parent, *, chapter=1, continuity=None):
    view = CanonView.from_service(service, fixture.project, BRANCH, parent)
    chapter_id = fixture.vision.chapters[chapter - 1].id
    return compile_contract(history, chapter_id, fixture, view, continuity), view


def commit_compiled(
    service, issuer, fixture, view, contract, *, name="accepted-1", prose=PROSE
):
    source = EntityId(fixture.project, name)
    evidence = ProseEvidence(
        source, NarrativePosition(contract.chapter_number, 1), "test-supplied/prose"
    )
    operations = []
    for i, bound in enumerate(contract.required):
        meta = OperationMeta(
            EntityId(fixture.project, name + "-op-" + str(i)),
            bound.spec.target_id,
            FactPath.VALUE,
            bound.expected,
            evidence,
            AUTHORIZATION,
        )
        operations.append(bound.materialize(meta))
    if not operations:
        snapshot = view.baseline.facts[0]
        operations.append(
            NoChange(
                OperationMeta(
                    EntityId(fixture.project, name + "-quiet-op"),
                    snapshot.seed_fact.id,
                    FactPath.VALUE,
                    Precondition.from_snapshot(snapshot),
                    evidence,
                    AUTHORIZATION,
                )
            )
        )
    delta = NarrativeDelta(
        EntityId(fixture.project, name + "-delta"),
        BRANCH,
        view.parent_ref,
        source,
        tuple(operations),
    )
    dependencies = tuple(
        CandidateEvidence(
            kind,
            canonical_bytes(contract.to_dict())
            if kind == "CONTRACT"
            else canonical_bytes(fixture.pack_binding.to_dict())
            if kind == "PACK"
            else ("isolated test " + kind).encode(),
            "test/" + kind.lower(),
            "1.0",
            "v2017-isolated-test",
            "1.0",
        )
        for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
    )
    candidate = ChapterCandidate(
        source, BRANCH, view.parent_ref, 1, prose, delta, dependencies
    )
    ticket = service.begin_chapter(
        fixture.project, BRANCH, ACTOR, name, view.parent_ref
    )
    permit = issuer.issue(ticket, candidate)
    return service.commit(ticket, candidate, permit)


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_actual_adopted_fixture_compiles_from_real_root_and_only_explicit_delta_commits(
    engine, name
):
    fixture = fixture_data(name)
    service, issuer, root = ready_story(engine, fixture)
    history = history_for(fixture)
    before = counts(engine)
    result, view = compile_at(service, fixture, history, root.commit_id)
    assert result.ok and result.contract is not None
    assert view.next_chapter == 1 and view.previous is None
    assert result.contract.parent_ref == root.commit_id
    assert result.contract.fixture_hash == fixture.content_hash
    assert_unchanged(engine, fixture.project, before, root.commit_id)
    receipt = commit_compiled(service, issuer, fixture, view, result.contract)
    assert receipt.commit_id != root.commit_id
    stored = service.load_commit(fixture.project, BRANCH, receipt.commit_id)
    rebuilt = service.rebuild_snapshot(fixture.project, BRANCH, receipt.commit_id)
    assert canonical_bytes(result.contract.to_dict()) == next(
        a.content for a in stored.candidate.dependencies if a.kind == "CONTRACT"
    )
    assert rebuilt.baseline == service.load_baseline(
        fixture.project, BRANCH, receipt.commit_id
    )
    assert stored.candidate.prose == PROSE
    assert counts(engine)["commits"] == 2


@pytest.mark.parametrize("name", ["urban", "fantasy"])
def test_real_predecessor_ending_and_unknown_semantics_bind_second_quiet_contract(
    engine, name
):
    fixture = fixture_data(name, quiet=True)
    service, issuer, root = ready_story(engine, fixture)
    history = history_for(fixture)
    first, root_view = compile_at(service, fixture, history, root.commit_id)
    assert first.ok
    receipt = commit_compiled(service, issuer, fixture, root_view, first.contract)
    previous = service.load_commit(fixture.project, BRANCH, receipt.commit_id)
    text = previous.candidate.prose.decode()
    continuation = ContinuationEvidence.from_previous(
        previous, text.index("门外"), evidence_ref="real-stored-prose/ending"
    )
    before = counts(engine)
    result, view = compile_at(
        service, fixture, history, receipt.commit_id, chapter=2, continuity=continuation
    )
    assert result.ok and result.contract.required == ()
    assert view.next_chapter == 2
    assert view.previous.receipt == previous.receipt
    assert view.previous.candidate_id == previous.candidate.id
    assert view.previous.prose == previous.candidate.prose
    assert view.previous.state == previous.state
    assert (
        continuation.end == len(text)
        and continuation.quote == text[text.index("门外") :]
    )
    assert continuation.prose_hash == sha256(PROSE).hexdigest()
    assert (
        continuation.end_time
        == continuation.end_location
        == continuation.pov
        == "UNKNOWN"
    )
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)
    second = commit_compiled(
        service, issuer, fixture, view, result.contract, name="accepted-2"
    )
    new_view = CanonView.from_service(
        service, fixture.project, BRANCH, second.commit_id
    )
    assert not contract_is_current(
        result.contract,
        history,
        fixture.vision.chapters[1].id,
        fixture,
        new_view,
        continuation,
    )
    assert (
        service.rebuild_snapshot(fixture.project, BRANCH, second.commit_id).baseline
        == new_view.baseline
    )


@pytest.mark.parametrize(
    "fault",
    ["hash", "candidate", "commit", "quote", "trimmed-ending", "missing-ending"],
)
def test_actual_previous_source_mismatch_cannot_compile_or_change_real_canon(
    engine, fault
):
    fixture = fixture_data("urban", quiet=True)
    service, issuer, root = ready_story(engine, fixture)
    history = history_for(fixture)
    first, view = compile_at(service, fixture, history, root.commit_id)
    assert first.ok
    receipt = commit_compiled(service, issuer, fixture, view, first.contract)
    previous = service.load_commit(fixture.project, BRANCH, receipt.commit_id)
    evidence = ContinuationEvidence.from_previous(previous)
    if fault == "hash":
        evidence = replace(
            evidence, prose_hash=sha256(PROSE.replace(b"\r\n", b"\n")).hexdigest()
        )
    elif fault == "candidate":
        evidence = replace(
            evidence, candidate_id=EntityId(fixture.project, "nonexistent-source")
        )
    elif fault == "commit":
        evidence = replace(evidence, previous_commit_id=root.commit_id)
    elif fault == "quote":
        evidence = replace(evidence, quote="只存在于计划而未存在于正文的钩子。")
    elif fault == "trimmed-ending":
        text = PROSE.decode()
        evidence = replace(evidence, end=len(text) - 1, quote=text[:-1])
    else:
        evidence = None
    before = counts(engine)
    result, _view = compile_at(
        service, fixture, history, receipt.commit_id, chapter=2, continuity=evidence
    )
    assert not result.ok and result.contract is None and result.diagnostics
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)


def test_actual_read_adapter_has_only_three_read_methods_and_retains_no_service(engine):
    fixture = fixture_data("fantasy")
    service, _issuer, root = ready_story(engine, fixture)
    calls = []

    class ReadOnlyPort:
        def rebuild_snapshot(self, *args):
            calls.append("rebuild")
            return service.rebuild_snapshot(*args)

        def load_root(self, *args):
            calls.append("root")
            return service.load_root(*args)

        def load_commit(self, *args):
            calls.append("chapter")
            return service.load_commit(*args)

    before = counts(engine)
    view = CanonView.from_service(
        ReadOnlyPort(), fixture.project, BRANCH, root.commit_id
    )
    assert calls == ["rebuild", "root"]
    assert not hasattr(view, "service") and not hasattr(view, "engine")
    assert compile_contract(
        history_for(fixture), fixture.vision.chapters[0].id, fixture, view
    ).ok
    assert_unchanged(engine, fixture.project, before, root.commit_id)


def test_cross_project_plan_fixture_and_real_view_are_not_interchangeable(engine):
    urban = fixture_data("urban")
    fantasy = fixture_data("fantasy")
    service, _issuer, root = ready_story(engine, fantasy)
    before = counts(engine)
    view = CanonView.from_service(service, fantasy.project, BRANCH, root.commit_id)
    result = compile_contract(
        history_for(urban), urban.vision.chapters[0].id, urban, view
    )
    assert not result.ok and result.contract is None
    assert_unchanged(engine, fantasy.project, before, root.commit_id)


def test_nonexistent_historical_parent_is_not_accepted_as_a_real_read_view(engine):
    fixture = fixture_data("urban")
    service, _issuer, root = ready_story(engine, fixture)
    before = counts(engine)
    with pytest.raises(CanonError):
        CanonView.from_service(service, fixture.project, BRANCH, "sha256:" + "0" * 64)
    assert_unchanged(engine, fixture.project, before, root.commit_id)


def test_historical_read_target_is_explicit_and_does_not_claim_latest_head(engine):
    fixture = fixture_data("urban", quiet=True)
    service, issuer, root = ready_story(engine, fixture)
    history = history_for(fixture)
    initial, view = compile_at(service, fixture, history, root.commit_id)
    receipt = commit_compiled(service, issuer, fixture, view, initial.contract)
    before = counts(engine)
    historical = CanonView.from_service(
        service, fixture.project, BRANCH, root.commit_id
    )
    current = CanonView.from_service(
        service, fixture.project, BRANCH, receipt.commit_id
    )
    assert historical.parent_ref == root.commit_id and historical.next_chapter == 1
    assert current.parent_ref == receipt.commit_id and current.next_chapter == 2
    assert not contract_is_current(
        initial.contract, history, fixture.vision.chapters[0].id, fixture, current
    )
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)


def test_explicit_current_knowledge_snapshot_rebinds_without_new_canon_write(engine):
    from anovel.contracts.models import KnowledgeSnapshot
    from anovel.domain.knowledge import Observation

    fixture = fixture_data("urban", quiet=True)
    history = history_for(fixture)
    service, issuer, root = ready_story(engine, fixture)
    first, view = compile_at(service, fixture, history, root.commit_id)
    receipt = commit_compiled(service, issuer, fixture, view, first.contract)
    view = CanonView.from_service(service, fixture.project, BRANCH, receipt.commit_id)
    ending = ContinuationEvidence.from_previous(
        view.previous, evidence_ref="actual-stored-prose/test-ending"
    )
    default = compile_contract(
        history, fixture.vision.chapters[1].id, fixture, view, ending
    )
    assert default.ok
    state = fixture.knowledge
    truth = EntityId(fixture.project, "truth")
    keeper = EntityId(fixture.project, "zhao-chuan")
    observation = Observation(
        EntityId(fixture.project, "manual-confirmation"),
        truth,
        frozenset({keeper}),
        "explicit-test-author-input/not-prose-extraction",
    )
    state.add_observation(observation)
    state.learn(keeper, truth, observation.id)
    snapshot = KnowledgeSnapshot(
        fixture.project,
        receipt.commit_id,
        "explicit-test-author-input/not-Canon-knowledge-store",
        canonical_bytes(state.to_dict()),
    )
    before = counts(engine)
    updated = compile_contract(
        history,
        fixture.vision.chapters[1].id,
        fixture,
        view,
        ending,
        knowledge_snapshot=snapshot,
    )
    assert (
        updated.ok
        and updated.contract.knowledge_hash != default.contract.knowledge_hash
    )
    assert not contract_is_current(
        default.contract,
        history,
        fixture.vision.chapters[1].id,
        fixture,
        view,
        ending,
        knowledge_snapshot=snapshot,
    )
    invalid = replace(snapshot, parent_ref=root.commit_id)
    refused = compile_contract(
        history,
        fixture.vision.chapters[1].id,
        fixture,
        view,
        ending,
        knowledge_snapshot=invalid,
    )
    assert (
        not refused.ok and refused.diagnostics[0].code == "KNOWLEDGE_SNAPSHOT_INVALID"
    )
    assert_unchanged(engine, fixture.project, before, receipt.commit_id)
