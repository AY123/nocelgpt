"""Exercise both orders of the actual Canon cancellation and commit race."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from queue import Queue

import pytest
from sqlalchemy import create_engine, text
from test_v2_010 import (
    ACTOR,
    BRANCH,
    PROJECT,
    admin_engine,
    counts,
    database,
    engine,
    prepared,
    unchanged,
)
from test_v2_011 import _assert_one_chapter
from test_v2_019 import context_for, ledger_for, request_for, success_reply

from anovel.canon import repository as canon_repository
from anovel.canon.chapter import ChapterCandidate
from anovel.canon.commit_service import CanonCommitService
from anovel.canon.identity import canonical_bytes
from anovel.canon.models import (
    CanonConflict,
    CanonError,
    CanonPermissionError,
    CommitReceipt,
)
from anovel.context.models import ContextRequest

__all__ = ["admin_engine", "database", "engine"]


def _race(engine, monkeypatch, first, ticket, proposal, permit):
    """Pause the first operation after its real branch lock is acquired."""
    engines = {
        operation: create_engine(
            engine.url,
            pool_size=1,
            max_overflow=0,
            connect_args={
                "connect_timeout": 10,
                "options": "-c statement_timeout=20000 -c lock_timeout=15000",
            },
        )
        for operation in ("cancel", "commit")
    }
    worker = threading.local()
    locked = threading.Event()
    release = threading.Event()
    pids = Queue()
    branch = canon_repository._branch
    second = "commit" if first == "cancel" else "cancel"

    def observe_branch(connection, params):
        operation = worker.operation
        pids.put(
            (
                operation,
                connection.execute(text("SELECT pg_backend_pid()")).scalar_one(),
            )
        )
        row = branch(connection, params)
        if operation == first:
            locked.set()
            assert release.wait(timeout=12), "First branch lock was not released"
        return row

    def run(operation):
        worker.operation = operation
        service = CanonCommitService(
            engines[operation], test_database=engine.url.database
        )
        if operation == "cancel":
            return service.cancel(ticket)
        try:
            return service.commit(ticket, proposal, permit)
        except CanonPermissionError as error:
            return error

    try:
        with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
            patch.setattr(canon_repository, "_branch", observe_branch)
            leading = pool.submit(run, first)
            try:
                assert locked.wait(timeout=10), (
                    "First operation did not lock the branch"
                )
                waiting = pool.submit(run, second)
                backends = dict(pids.get(timeout=10) for _ in range(2))
                with engine.connect() as observer:
                    observer_pid = observer.execute(
                        text("SELECT pg_backend_pid()")
                    ).scalar_one()
                    assert len({observer_pid, *backends.values()}) == 3
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline:
                        blockers = observer.execute(
                            text("SELECT pg_blocking_pids(:waiter)"),
                            {"waiter": backends[second]},
                        ).scalar_one()
                        if backends[first] in blockers:
                            break
                        time.sleep(0.02)
                    else:
                        pytest.fail(
                            "PostgreSQL did not observe the expected branch lock contention"
                        )
            finally:
                release.set()
            outcomes = {
                first: leading.result(timeout=20),
                second: waiting.result(timeout=20),
            }
        return outcomes, set(backends.values())
    finally:
        for worker_engine in engines.values():
            worker_engine.dispose()


@pytest.mark.parametrize("first", ["cancel", "commit"])
def test_canon_cancel_commit_race_and_restart_with_issued_permit(
    engine, monkeypatch, tmp_path, first
):
    _service, issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    observer = CanonCommitService(
        engine.execution_options(postgresql_readonly=True),
        test_database=engine.url.database,
    )
    pending = observer.inspect_chapter_submission(ticket, proposal)
    assert pending.state == "UNKNOWN" and pending.receipt is None
    unchanged(engine, before, root.commit_id)
    if first == "cancel":
        # This finite local Gateway request belongs to the same old request and
        # frozen parent. Keep its liability pending until cancellation wins.
        source_context = context_for(project=PROJECT)
        binding = ContextRequest(
            PROJECT,
            BRANCH,
            root.commit_id,
            source_context.contract_hash,
            source_context.role,
            source_context.budget,
        )
        context = replace(
            source_context, parent_ref=root.commit_id, request_hash=binding.content_hash
        )
        request = request_for(
            run=ticket.request_id, logical=proposal.id.local_id, context=context
        )
        ledger = ledger_for(tmp_path, request)
        policy = request.policies[0]
        attempt = f"old-execution-{ticket.execution_version}"
        assert ledger.reserve(request, policy, attempt) is None
        ledger.mark_dispatch(request.run_id, attempt).consume(request, policy, attempt)
        unknown = ledger.recover(request.run_id, attempt)
        assert unknown.status == "UNKNOWN" and unknown.charge_status == "PENDING"
        assert unknown.charge_microusd is None

    outcomes, old_backends = _race(engine, monkeypatch, first, ticket, proposal, permit)
    fresh = create_engine(engine.url, pool_size=1, max_overflow=0)
    try:
        service = CanonCommitService(fresh, test_database=fresh.url.database)
        readback = CanonCommitService(
            fresh.execution_options(postgresql_readonly=True),
            test_database=fresh.url.database,
        )
        with fresh.connect() as connection:
            assert (
                connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
                not in old_backends
            )
            flags = connection.execute(
                text(
                    "SELECT cancelled, execution_version FROM anovel_canon.requests "
                    "WHERE project_id=:project AND branch_id=:branch AND request_id=:request"
                ),
                {"project": PROJECT, "branch": BRANCH, "request": ticket.request_id},
            ).one()
        restored = ChapterCandidate.from_dict(proposal.to_dict())
        with pytest.raises(CanonError, match="candidate crosses ticket scope"):
            readback.inspect_chapter_submission(
                replace(ticket, branch="another-branch"), restored
            )
        for forged in (
            replace(ticket, actor="another-editor"),
            replace(ticket, authorization_version=ticket.authorization_version + 1),
            replace(ticket, execution_version=ticket.execution_version + 1),
        ):
            with pytest.raises(CanonPermissionError):
                readback.inspect_chapter_submission(forged, restored)
        wrong_parent = "sha256:" + "f" * 64
        rebound = replace(
            restored,
            parent_ref=wrong_parent,
            delta=replace(restored.delta, parent_ref=wrong_parent),
        )
        with pytest.raises(CanonConflict, match="frozen parent mismatch"):
            readback.inspect_chapter_submission(ticket, rebound)

        if first == "cancel":
            assert outcomes["cancel"] is None
            assert isinstance(outcomes["commit"], CanonPermissionError)
            assert "cancelled or stale" in str(outcomes["commit"])
            assert flags == (True, ticket.execution_version + 1)
            cancelled = readback.inspect_chapter_submission(ticket, restored)
            assert cancelled.state == "CANCELLED" and cancelled.receipt is None
            late_result = ledger.finish(
                request,
                policy,
                attempt,
                replace(
                    success_reply(policy, marker="late-cancelled-chapter"),
                    output_bytes=canonical_bytes({"text": restored.prose.decode()}),
                ),
            )
            assert late_result.status == "SUCCESS" and late_result.attempt_id == attempt
            assert ledger.summary(request.run_id)["attempts"] == 1
            late_candidate = replace(
                restored,
                dependencies=tuple(
                    replace(item, content=late_result.to_bytes())
                    if item.kind == "MODEL"
                    else item
                    for item in restored.dependencies
                ),
            )
            with pytest.raises(CanonPermissionError, match="cancelled or stale"):
                service.begin_chapter(
                    PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
                )
            with pytest.raises(CanonPermissionError, match="cancelled or stale"):
                service.commit(ticket, restored, permit)
            with pytest.raises(CanonPermissionError, match="cancelled or stale"):
                service.commit(ticket, late_candidate, permit)
            assert readback.inspect_chapter_submission(ticket, restored) == cancelled
            assert service.cancel(ticket) is None
            assert (
                canon_repository.Repository(fresh).receipt(
                    PROJECT, BRANCH, ticket.request_id
                )
                is None
            )
            unchanged(fresh, before, root.commit_id)
            return

        receipt = outcomes["commit"]
        assert isinstance(receipt, CommitReceipt)
        assert outcomes["cancel"] == receipt
        assert flags == (False, ticket.execution_version)
        _assert_one_chapter(fresh, before, root, receipt, proposal)
        accepted = counts(fresh)

        issuer.revoke(PROJECT, BRANCH, permit)
        confirmed = readback.inspect_chapter_submission(ticket, restored)
        assert confirmed.state == "COMMITTED" and confirmed.receipt == receipt
        with pytest.raises(
            CanonConflict, match="already accepted a different candidate"
        ):
            readback.inspect_chapter_submission(
                ticket, replace(restored, version=restored.version + 1)
            )
        recovered_ticket = service.begin_chapter(
            PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
        )
        assert recovered_ticket == ticket
        recovered = service.commit(recovered_ticket, restored, permit)
        assert canonical_bytes(recovered.to_dict()) == canonical_bytes(
            receipt.to_dict()
        )
        assert service.cancel(recovered_ticket) == receipt
        with pytest.raises(
            CanonConflict, match="already accepted a different candidate"
        ):
            service.commit(
                recovered_ticket,
                replace(restored, version=restored.version + 1),
                permit,
            )
        unchanged(fresh, accepted, receipt.commit_id)
    finally:
        fresh.dispose()
