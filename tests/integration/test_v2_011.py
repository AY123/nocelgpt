"""Real PostgreSQL retry/CAS acceptance through the existing Canon service.

The disposable database, seed and finite candidate helpers are the V2-010
fixtures. No alternate writer or production Permit is introduced. Fault
injection is confined to these tests: one DBAPI commit completes before its
acknowledgement is hidden from SQLAlchemy/the caller.
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from test_v2_010 import (
    ACTOR,
    BRANCH,
    ISSUER,
    PROJECT,
    PROSE,
    admin_engine,
    candidate,
    counts,
    database,
    engine,
    prepared,
    ready,
    unchanged,
)

from anovel.canon.chapter import ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.models import (
    CanonConflict,
    CanonError,
    CanonPermissionError,
    CommitReceipt,
)
from anovel.canon.repository import Repository
from anovel.domain.identity import EntityId

# pytest discovers these imported fixtures; they are intentional public exports.
__all__ = ["admin_engine", "database", "engine"]


def _contending_commits(engine, attempts):
    """Prove both independent backends wait on the actual branch row lock."""
    start = threading.Barrier(3)
    names = ["v2011_" + uuid.uuid4().hex for _ in range(2)]
    workers = [
        create_engine(
            engine.url,
            pool_size=1,
            max_overflow=0,
            connect_args={
                "application_name": name,
                "connect_timeout": 10,
                "options": "-c statement_timeout=20000 -c lock_timeout=15000",
            },
        )
        for name in names
    ]

    def commit(index):
        worker = workers[index]
        service = CanonCommitService(worker, test_database=worker.url.database)
        with worker.connect() as connection:
            pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
        start.wait(timeout=10)
        try:
            result = service.commit(*attempts[index])
        except CanonConflict as error:
            result = error
        return pid, result

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            with engine.begin() as blocker:
                blocker.execute(
                    text(
                        "SELECT 1 FROM anovel_canon.branches "
                        "WHERE project_id=:project AND branch_id=:branch FOR UPDATE"
                    ),
                    {"project": PROJECT, "branch": BRANCH},
                )
                futures = [pool.submit(commit, index) for index in range(2)]
                start.wait(timeout=10)
                deadline = time.monotonic() + 10
                waiting = 0
                while time.monotonic() < deadline:
                    with engine.connect() as observer:
                        waiting = observer.execute(
                            text(
                                "SELECT count(*) FROM pg_stat_activity "
                                "WHERE application_name IN (:one,:two) "
                                "AND wait_event_type='Lock'"
                            ),
                            {"one": names[0], "two": names[1]},
                        ).scalar_one()
                    if waiting == 2:
                        break
                    time.sleep(0.02)
                assert waiting == 2, "Both PostgreSQL transactions must contend"
            results = [future.result(timeout=25) for future in futures]
        assert len({pid for pid, _result in results}) == 2
        return [result for _pid, result in results]
    finally:
        for worker in workers:
            worker.dispose()


def _assert_one_chapter(engine, before, root, receipt, proposal):
    after = counts(engine)
    expected = dict(before)
    for table in ("commits", "events", "receipts"):
        expected[table] += 1
    expected["artifacts"] += 6
    expected["commit_artifacts"] += 6
    assert after == expected, "No losing/duplicate proposal may leave story rows"
    repository = Repository(engine)
    assert repository.head(PROJECT, BRANCH) == receipt.commit_id
    assert repository.receipt(PROJECT, BRANCH, receipt.request_id) == receipt
    stored = repository.load_commit(PROJECT, BRANCH, receipt.commit_id)
    assert stored.receipt == receipt
    assert stored.candidate == proposal
    assert stored.candidate.prose == proposal.prose
    assert repository.load_root(PROJECT, BRANCH, root.commit_id).receipt == root
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT parent_id,sequence FROM anovel_canon.commits "
                "WHERE project_id=:project AND branch_id=:branch AND sequence>0"
            ),
            {"project": PROJECT, "branch": BRANCH},
        ).all() == [(root.commit_id, 1)]


@pytest.mark.parametrize("mode", ["same-payload", "changed-payload", "other-key"])
def test_real_concurrent_chapter_requests_have_one_durable_winner(engine, mode):
    service, issuer, _root_ticket, root = ready(engine)
    first_ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "request-1", root.commit_id
    )
    first = replace(
        candidate(service, root.commit_id, name="first"),
        prose=b"first contender's exact prose",
    )
    first_permit = issuer.issue(first_ticket, first)
    second_ticket = (
        service.begin_chapter(PROJECT, BRANCH, ACTOR, "request-2", root.commit_id)
        if mode == "other-key"
        else service.begin_chapter(
            PROJECT, BRANCH, ACTOR, first_ticket.request_id, root.commit_id
        )
    )
    second = (
        first
        if mode == "same-payload"
        else replace(
            candidate(service, root.commit_id, name="second", value=25),
            prose=b"second contender's distinct prose",
        )
    )
    second_permit = issuer.issue(second_ticket, second)
    assert first_permit != second_permit
    before = counts(engine)
    results = _contending_commits(
        engine,
        [
            (first_ticket, first, first_permit),
            (second_ticket, second, second_permit),
        ],
    )
    if mode == "same-payload":
        assert all(isinstance(result, CommitReceipt) for result in results)
        assert results[0] == results[1]
        receipt = results[0]
        winner = first
    else:
        assert sum(isinstance(result, CommitReceipt) for result in results) == 1
        assert sum(isinstance(result, CanonConflict) for result in results) == 1
        winner_index = next(
            index
            for index, result in enumerate(results)
            if isinstance(result, CommitReceipt)
        )
        receipt = results[winner_index]
        winner = [first, second][winner_index]
        loser = [first, second][1 - winner_index]
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM anovel_canon.artifacts "
                        "WHERE artifact_type='RAW_PROSE' AND content=:prose"
                    ),
                    {"prose": loser.prose},
                ).scalar_one()
                == 0
            )
    _assert_one_chapter(engine, before, root, receipt, winner)


@pytest.mark.parametrize(
    "change", ["prose", "delta", "version", "dependency-bytes", "dependency-version"]
)
def test_committed_request_rejects_different_payload_without_touching_history(
    engine, change
):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    original = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    if change == "prose":
        changed = replace(proposal, prose=PROSE + b"different bytes")
    elif change == "delta":
        operation = proposal.delta.operations[0]
        changed = replace(
            proposal,
            delta=replace(proposal.delta, operations=(replace(operation, value=21),)),
        )
    elif change == "version":
        changed = replace(proposal, version=proposal.version + 1)
    else:
        dependency = proposal.dependencies[0]
        altered = (
            replace(dependency, content=b"changed retained dependency")
            if change == "dependency-bytes"
            else replace(dependency, producer_version="2.0")
        )
        changed = replace(proposal, dependencies=(altered,) + proposal.dependencies[1:])
    assert changed.payload_hash != proposal.payload_hash
    before = counts(engine)
    with pytest.raises(CanonConflict, match="already accepted a different candidate"):
        service.commit(ticket, changed, permit)
    unchanged(engine, before, receipt.commit_id)
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id) == original
    assert service.commit(ticket, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_committed_but_lost_dbapi_ack_recovers_on_new_connection_and_continues(
    engine,
):
    _service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    fault = {"armed": False, "injections": 0, "committed_backend": None}

    class LostCommitAcknowledgement(psycopg.Connection):
        def commit(self):
            super().commit()
            if fault["armed"]:
                fault["armed"] = False
                fault["injections"] += 1
                fault["committed_backend"] = self.info.backend_pid
                raise psycopg.OperationalError("injected lost commit acknowledgement")

    arguments, keywords = engine.dialect.create_connect_args(engine.url)
    keywords["connect_timeout"] = 10
    lost_connection_engine = create_engine(
        engine.url,
        creator=lambda: LostCommitAcknowledgement.connect(*arguments, **keywords),
        pool_size=1,
        max_overflow=0,
    )
    try:
        lost_service = CanonCommitService(
            lost_connection_engine, test_database=engine.url.database
        )
        fault["armed"] = True
        with pytest.raises(
            OperationalError, match="injected lost commit acknowledgement"
        ):
            lost_service.commit(ticket, proposal, permit)
        assert fault["injections"] == 1
        assert not fault["armed"]
        assert fault["committed_backend"] is not None
    finally:
        lost_connection_engine.dispose()

    # The caller obtained no receipt. An independent DB read proves COMMIT won.
    committed = Repository(engine).receipt(PROJECT, BRANCH, ticket.request_id)
    assert isinstance(committed, CommitReceipt)
    assert Repository(engine).head(PROJECT, BRANCH) == committed.commit_id
    after_unknown_result = counts(engine)
    assert after_unknown_result["commits"] == 2
    assert after_unknown_result["events"] == after_unknown_result["receipts"] == 2
    fresh = create_engine(
        engine.url, pool_size=1, max_overflow=0, connect_args={"connect_timeout": 10}
    )
    try:
        with fresh.connect() as connection:
            assert (
                connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
                != (fault["committed_backend"])
            )
        service = CanonCommitService(fresh, test_database=fresh.url.database)
        recovered_ticket = service.begin_chapter(
            PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
        )
        assert recovered_ticket == ticket
        restored_candidate = ChapterCandidate.from_dict(proposal.to_dict())
        recovered = service.commit(recovered_ticket, restored_candidate, permit)
        assert recovered == committed
        assert service.load_commit(PROJECT, BRANCH, recovered.commit_id).candidate == (
            proposal
        )
        unchanged(engine, after_unknown_result, committed.commit_id)

        following = candidate(service, recovered.commit_id, name="following", value=30)
        next_ticket = service.begin_chapter(
            PROJECT, BRANCH, ACTOR, "request-2", recovered.commit_id
        )
        # Issuance is a separate trusted capability, still disposable TEST only.
        next_issuer = ProtectedPermitIssuer(
            fresh, test_database=fresh.url.database, issuer_id=ISSUER
        )
        following_receipt = service.commit(
            next_ticket, following, next_issuer.issue(next_ticket, following)
        )
        assert (
            service.load_commit(PROJECT, BRANCH, following_receipt.commit_id).candidate
            == following
        )
        following_state = service.load_baseline(
            PROJECT, BRANCH, following_receipt.commit_id
        ).get(EntityId(PROJECT, "balance"))
        assert following_state is not None
        assert following_state.state.value == 30
        assert following_state.revision == 2
        with fresh.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT parent_id,sequence FROM anovel_canon.commits "
                    "WHERE commit_id=:commit"
                ),
                {"commit": following_receipt.commit_id},
            ).one() == (committed.commit_id, 2)
        after_following = counts(engine)
        assert after_following["commits"] == 3
        assert after_following["events"] == after_following["receipts"] == 3
        # A delayed retry must not rewind HEAD after the following chapter.
        assert service.commit(recovered_ticket, restored_candidate, permit) == committed
        unchanged(engine, after_following, following_receipt.commit_id)
    finally:
        fresh.dispose()


@pytest.mark.parametrize("mismatch", ["actor", "project", "branch", "parent"])
def test_receipt_recovery_does_not_cross_actor_scope_or_frozen_parent(engine, mismatch):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    before = counts(engine)
    if mismatch == "parent":
        with pytest.raises(CanonConflict, match="frozen parent mismatch"):
            service.begin_chapter(
                PROJECT, BRANCH, ACTOR, ticket.request_id, receipt.commit_id
            )
        changed = candidate(service, receipt.commit_id, name="wrong-parent", value=30)
        with pytest.raises(CanonConflict, match="frozen parent mismatch"):
            service.commit(ticket, changed, permit)
    else:
        altered = replace(ticket, **{mismatch: "different-" + mismatch})
        with pytest.raises(CanonPermissionError):
            service.begin_chapter(
                altered.project,
                altered.branch,
                altered.actor,
                altered.request_id,
                root.commit_id,
            )
        with pytest.raises(CanonError):
            service.commit(altered, proposal, permit)
    unchanged(engine, before, receipt.commit_id)
    recovered = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
    )
    assert recovered == ticket
    assert service.commit(recovered, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_rolled_back_commit_can_retry_same_key_without_partial_story(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION anovel_canon.reject_v2011_event() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN "
            "IF NEW.event_type='CHAPTER_COMMITTED' THEN "
            "RAISE EXCEPTION 'injected retryable event failure' USING ERRCODE='23514'; "
            "END IF; RETURN NEW; END $$"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER injected_v2011_failure BEFORE INSERT "
            "ON anovel_canon.events FOR EACH ROW "
            "EXECUTE FUNCTION anovel_canon.reject_v2011_event()"
        )
    try:
        with pytest.raises(DBAPIError) as failure:
            service.commit(ticket, proposal, permit)
        assert failure.value.orig.sqlstate == "23514"
        assert Repository(engine).receipt(PROJECT, BRANCH, ticket.request_id) is None
        unchanged(engine, before, root.commit_id)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER injected_v2011_failure ON anovel_canon.events"
            )
    recovered = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
    )
    assert recovered == ticket
    receipt = service.commit(recovered, proposal, permit)
    _assert_one_chapter(engine, before, root, receipt, proposal)
    after_success = counts(engine)
    assert service.commit(recovered, proposal, permit) == receipt
    unchanged(engine, after_success, receipt.commit_id)
