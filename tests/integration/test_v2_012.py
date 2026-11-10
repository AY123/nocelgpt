"""Read-only story recovery from actual committed PostgreSQL history.

Every normal story is written by the existing sole Canon service. Direct SQL
below is limited to explicit corruption probes in disposable test databases;
it is never a second initialization or chapter-writing path.
"""

from hashlib import sha256

import pytest
from sqlalchemy import create_engine, text
from test_v2_010 import (
    ACTOR,
    AUTHORIZATION,
    BRANCH,
    ISSUER,
    PROJECT,
    PROSE,
    admin_engine,
    candidate,
    counts,
    database,
    engine,
    initialize,
    prepared,
    ready,
    unchanged,
)

from anovel.canon import projection
from anovel.canon.chapter import ChapterCandidate
from anovel.canon.commit_service import CanonCommitService
from anovel.canon.identity import CANONICAL_ENCODING, canonical_bytes
from anovel.canon.models import CanonIntegrityError
from anovel.canon.projection import ProjectionError
from anovel.canon.repository import Repository
from anovel.domain.delta import (
    FactPath,
    FactState,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    SetFact,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId

# Explicitly expose shared pytest fixtures, without importing old test functions.
__all__ = ["admin_engine", "database", "engine"]


def history_chain(engine):
    service, issuer, _root_ticket, root = ready(engine)
    receipts = [root]
    originals = []
    for index, (operation, value) in enumerate(
        [("set", 20), ("unknown", 20), ("set", 30), ("retract", 30), ("no_change", 30)],
        start=1,
    ):
        proposal = candidate(
            service,
            receipts[-1].commit_id,
            name="chapter-" + str(index),
            operation=operation,
            value=value,
        )
        ticket = service.begin_chapter(
            PROJECT, BRANCH, ACTOR, "request-" + str(index), receipts[-1].commit_id
        )
        permit = issuer.issue(ticket, proposal)
        receipt = service.commit(ticket, proposal, permit)
        receipts.append(receipt)
        originals.append((ticket, proposal, permit))
    return service, issuer, receipts, originals


def test_rebuild_replays_finite_history_and_matches_every_historical_snapshot(engine):
    service, _issuer, receipts, _originals = history_chain(engine)
    before = counts(engine)
    expected_states = [
        FactState.known(10),
        FactState.known(20),
        FactState.unknown(),
        FactState.known(30),
        FactState.retracted(),
        FactState.retracted(),
    ]
    for index, (receipt, expected_state) in enumerate(zip(receipts, expected_states)):
        result = service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
        assert result.receipt == receipt
        assert result.baseline.parent_ref == receipt.commit_id
        assert result.baseline.facts[0].state == expected_state
        assert result.baseline.facts[0].revision == min(index, 4)
        assert len(result.checkpoints) == index + 1
        assert (
            result.baseline_sha256
            == sha256(canonical_bytes(result.baseline.to_dict())).hexdigest()
        )
        for number, step in enumerate(result.checkpoints):
            assert step.commit_id == receipts[number].commit_id
            assert step.sequence == number
            assert step.schema_version == "1.0"
            assert step.encoding == CANONICAL_ENCODING
            if number == 0:
                assert step.event_type == "ROOT_INITIALIZED"
                assert step.reducer_version == "ROOT-1"
                assert step.expected_snapshot_sha256 is None
            else:
                assert step.event_type == "CHAPTER_COMMITTED"
                assert step.reducer_version == "FACT_DELTA-1"
                historical = service.load_commit(PROJECT, BRANCH, step.commit_id)
                # Original snapshot binds the candidate parent. Compare before
                # final output re-anchors the baseline to the accepted commit.
                digest = sha256(canonical_bytes(historical.state.to_dict())).hexdigest()
                assert step.snapshot_sha256 == step.expected_snapshot_sha256 == digest
    assert (
        service.load_root(PROJECT, BRANCH, receipts[0].commit_id).prose
        == b"initial root"
    )
    assert (
        service.load_commit(PROJECT, BRANCH, receipts[-1].commit_id).candidate.prose
        == PROSE
    )
    unchanged(engine, before, receipts[-1].commit_id)


def test_rebuild_does_not_use_stored_baseline_as_reducer_input(engine, monkeypatch):
    service, _issuer, receipts, _originals = history_chain(engine)
    before = counts(engine)

    def forbidden(*_args, **_kwargs):
        pytest.fail("Rebuild must replay root and Delta, never load_baseline")

    monkeypatch.setattr(Repository, "load_baseline", forbidden)
    result = service.rebuild_snapshot(PROJECT, BRANCH, receipts[-1].commit_id)
    assert result.baseline.facts[0].state == FactState.retracted()
    assert result.baseline.facts[0].revision == 4
    assert result.receipt == receipts[-1]
    unchanged(engine, before, receipts[-1].commit_id)


def test_new_connection_rebuilds_old_target_without_future_facts(engine):
    service, _issuer, receipts, _originals = history_chain(engine)
    expected = service.rebuild_snapshot(PROJECT, BRANCH, receipts[1].commit_id)
    before = counts(engine)
    fresh = create_engine(engine.url)
    try:
        reader = CanonCommitService(fresh)
        first = reader.rebuild_snapshot(PROJECT, BRANCH, receipts[1].commit_id)
        second = reader.rebuild_snapshot(PROJECT, BRANCH, receipts[1].commit_id)
        assert first == second == expected
        assert first.baseline.facts[0].state == FactState.known(20)
        assert first.baseline.facts[0].revision == 1
        assert first.receipt == receipts[1]
        assert len(first.checkpoints) == 2
    finally:
        fresh.dispose()
    unchanged(engine, before, receipts[-1].commit_id)


def scoped_candidate(service, project, parent, dependencies, value):
    baseline = service.load_baseline(project, BRANCH, parent)
    snapshot = baseline.facts[0]
    source = EntityId(project, "scoped-chapter")
    operation = SetFact(
        OperationMeta(
            EntityId(project, "scoped-operation"),
            snapshot.seed_fact.id,
            FactPath.VALUE,
            Precondition.from_snapshot(snapshot),
            ProseEvidence(source, NarrativePosition(1, 1), "prose:1"),
            AUTHORIZATION,
        ),
        value,
    )
    return ChapterCandidate(
        source,
        BRANCH,
        parent,
        1,
        PROSE,
        NarrativeDelta(
            EntityId(project, "scoped-delta"), BRANCH, parent, source, (operation,)
        ),
        dependencies,
    )


def test_two_books_named_main_rebuild_only_their_own_interleaved_history(engine):
    service, issuer, _root_ticket, root = ready(engine)
    other = "other-book"
    other_service, _other_ticket, other_root = initialize(engine, project=other)
    other_service.configure_chapter_authority(other, BRANCH, ACTOR, ISSUER)
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "first", root.commit_id)
    first = candidate(service, root.commit_id)
    accepted = service.commit(ticket, first, issuer.issue(ticket, first))
    other_proposal = scoped_candidate(
        other_service, other, other_root.commit_id, first.dependencies, 80
    )
    other_ticket = other_service.begin_chapter(
        other, BRANCH, ACTOR, "first", other_root.commit_id
    )
    other_receipt = other_service.commit(
        other_ticket, other_proposal, issuer.issue(other_ticket, other_proposal)
    )
    following = candidate(service, accepted.commit_id, name="following", value=30)
    following_ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "following", accepted.commit_id
    )
    final = service.commit(
        following_ticket, following, issuer.issue(following_ticket, following)
    )
    before = counts(engine)
    own = service.rebuild_snapshot(PROJECT, BRANCH, final.commit_id)
    foreign = other_service.rebuild_snapshot(other, BRANCH, other_receipt.commit_id)
    assert own.baseline.project == PROJECT
    assert own.baseline.facts[0].seed_fact.id.project == PROJECT
    assert own.baseline.facts[0].state == FactState.known(30)
    assert len(own.checkpoints) == 3
    assert foreign.baseline.project == other
    assert foreign.baseline.facts[0].seed_fact.id.project == other
    assert foreign.baseline.facts[0].state == FactState.known(80)
    assert len(foreign.checkpoints) == 2
    for wrong_project, wrong_commit in [
        (PROJECT, other_receipt.commit_id),
        (other, final.commit_id),
    ]:
        with pytest.raises(CanonIntegrityError):
            service.rebuild_snapshot(wrong_project, BRANCH, wrong_commit)
    assert counts(engine) == before
    assert Repository(engine).head(PROJECT, BRANCH) == final.commit_id
    assert Repository(engine).head(other, BRANCH) == other_receipt.commit_id


def test_historical_rebuild_does_not_require_current_chapter_authority(engine):
    service, issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    expected = service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    issuer.revoke(PROJECT, BRANCH, permit)
    service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
    before = counts(engine)
    assert service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id) == expected
    assert service.commit(ticket, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_projection_failure_keeps_committed_receipt_head_and_original_bytes(
    engine, monkeypatch
):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    stored = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    before = counts(engine)

    def failed_reducer(*_args, **_kwargs):
        raise RuntimeError("injected read-only projection failure")

    with monkeypatch.context() as patch:
        patch.setattr(projection, "preview_delta", failed_reducer)
        with pytest.raises(ProjectionError) as failure:
            service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
        assert failure.value.receipt == receipt
        assert failure.value.canon_committed is True
        assert Repository(engine).receipt(PROJECT, BRANCH, ticket.request_id) == receipt
        assert service.load_commit(PROJECT, BRANCH, receipt.commit_id) == stored
        assert service.commit(ticket, proposal, permit) == receipt
        unchanged(engine, before, receipt.commit_id)
    recovered = service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    assert recovered.receipt == receipt
    assert recovered.baseline.facts[0].state == FactState.known(20)
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id) == stored
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize("scope", ["project", "branch", "unknown-commit"])
def test_rebuild_rejects_unknown_or_wrong_scope_target(engine, scope):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    before = counts(engine)
    project, branch, target = PROJECT, BRANCH, receipt.commit_id
    if scope == "project":
        project = "other-book"
    elif scope == "branch":
        branch = "other-branch"
    else:
        target = "sha256:" + "f" * 64
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(project, branch, target)
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize("location", ["root", "middle", "target"])
def test_rebuild_refuses_missing_ancestor_event(engine, location):
    service, _issuer, receipts, _originals = history_chain(engine)
    selected = receipts[{"root": 0, "middle": 2, "target": -1}[location]]
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.events DISABLE TRIGGER immutable_events"
        )
        connection.execute(
            text("DELETE FROM anovel_canon.events WHERE commit_id=:commit"),
            {"commit": selected.commit_id},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.events ENABLE TRIGGER immutable_events"
        )
    before = counts(engine)
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(PROJECT, BRANCH, receipts[-1].commit_id)
    unchanged(engine, before, receipts[-1].commit_id)


@pytest.mark.parametrize(
    "kind",
    [
        "ROOT_INPUT",
        "RAW_PROSE",
        "NARRATIVE_DELTA",
        "STATE_SNAPSHOT",
        "COMMIT_PERMIT",
        "DEPENDENCY_BUNDLE",
    ],
)
def test_rebuild_refuses_corrupted_retained_bytes(engine, kind):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts DISABLE TRIGGER immutable_artifacts"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.artifacts SET content=:bad WHERE artifact_type=:kind"
            ),
            {"bad": b"intentionally corrupted retained bytes", "kind": kind},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts ENABLE TRIGGER immutable_artifacts"
        )
    before = counts(engine)
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    assert Repository(engine).receipt(PROJECT, BRANCH, ticket.request_id) == receipt
    unchanged(engine, before, receipt.commit_id)
    assert root.commit_id != receipt.commit_id


@pytest.mark.parametrize("location", ["root", "chapter"])
def test_rebuild_refuses_unknown_reducer_without_latest_fallback(engine, location):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    selected = root if location == "root" else receipt
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.events DROP CONSTRAINT event_reducer_pair"
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.events DISABLE TRIGGER immutable_events"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.events SET reducer_version='UNSUPPORTED-999' WHERE commit_id=:commit"
            ),
            {"commit": selected.commit_id},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.events ENABLE TRIGGER immutable_events"
        )
    before = counts(engine)
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize("location", ["root", "chapter"])
def test_rebuild_refuses_wrong_artifact_encoding(engine, location):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    kind = "ROOT_INPUT" if location == "root" else "NARRATIVE_DELTA"
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts DISABLE TRIGGER immutable_artifacts"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.artifacts SET encoding='RAW-UTF8' WHERE artifact_type=:kind"
            ),
            {"kind": kind},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts ENABLE TRIGGER immutable_artifacts"
        )
    before = counts(engine)
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    unchanged(engine, before, receipt.commit_id)


def test_rebuild_refuses_missing_delta_link_instead_of_trusting_snapshot(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commit_artifacts DISABLE TRIGGER immutable_links"
        )
        connection.execute(
            text(
                "DELETE FROM anovel_canon.commit_artifacts WHERE commit_id=:commit AND artifact_type='NARRATIVE_DELTA'"
            ),
            {"commit": receipt.commit_id},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commit_artifacts ENABLE TRIGGER immutable_links"
        )
    before = counts(engine)
    with pytest.raises(CanonIntegrityError):
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize("damage", ["self-cycle", "skip-parent", "sequence-gap"])
def test_rebuild_rejects_corrupt_persistent_ancestry_before_content_loading(
    engine, damage
):
    service, _issuer, receipts, _originals = history_chain(engine)
    target = receipts[-1]
    params = {
        "project": PROJECT,
        "branch": BRANCH,
        "commit": target.commit_id,
        "parent": target.commit_id if damage == "self-cycle" else receipts[0].commit_id,
    }
    # Explicit isolated corruption probe: row identities, receipts and HEAD
    # remain unchanged. Discovery must reject the broken ancestry before a
    # stale canonical-envelope/hash mismatch can incidentally hide the defect.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commits DISABLE TRIGGER immutable_commits"
        )
        if damage == "sequence-gap":
            connection.execute(
                text(
                    "UPDATE anovel_canon.commits SET sequence=6 "
                    "WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit"
                ),
                params,
            )
        else:
            connection.execute(
                text(
                    "UPDATE anovel_canon.commits SET parent_id=:parent "
                    "WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit"
                ),
                params,
            )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commits ENABLE TRIGGER immutable_commits"
        )
    before = counts(engine)
    assert Repository(engine).receipt(PROJECT, BRANCH, target.request_id) == target
    with pytest.raises(CanonIntegrityError, match="cycle|continuous"):
        service.rebuild_snapshot(PROJECT, BRANCH, target.commit_id)
    assert Repository(engine).receipt(PROJECT, BRANCH, target.request_id) == target
    unchanged(engine, before, target.commit_id)
