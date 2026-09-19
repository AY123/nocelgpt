from __future__ import annotations

import pytest

from runtime.approval import (
    ApprovalDecision,
    ApprovalNotFound,
    ApprovalQueue,
    ApprovalStateError,
    ApprovalStatus,
    create_approval_request,
    load_approval_queue,
    record_approval_decision,
)


def _req(request_id, target_type="mint", action="confirm_mint", module="mint_executor"):
    return create_approval_request(
        request_id=request_id,
        target_type=target_type,
        target_id="X-1",
        action=action,
        reason="needs approval",
        requested_by={"module": module},
    )


def test_approval_queue_enqueues_and_records_decision(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = create_approval_request(
        request_id="APR-00001",
        target_type="mint",
        target_id="CAND-00001",
        action="confirm_mint",
        reason="fact write requires human approval",
        requested_by={"module": "mint_executor", "run_id": "RUN-1"},
        context={"project_id": "PROJ-1"},
    )
    queue.enqueue(request)
    assert queue.list_pending()[0].status == ApprovalStatus.PENDING.value
    record = record_approval_decision(
        queue,
        request_id=request.id,
        decision=ApprovalDecision.APPROVED,
        decided_by="human",
        notes="ok",
    )
    assert record.decision == "approved"
    assert record.snapshot["id"] == request.id
    assert queue.list_records()[0].id == record.id


def test_approval_queue_round_trips_from_disk(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = create_approval_request(
        request_id="APR-00002",
        target_type="genesis",
        target_id="OUTLINE-00001",
        action="confirm_genesis",
        reason="book opening requires human approval",
    )
    queue.enqueue(request)
    record_approval_decision(
        queue,
        request_id=request.id,
        decision=ApprovalDecision.APPROVED,
        decided_by="human",
        notes="approved",
    )
    reloaded = load_approval_queue(tmp_path)
    assert reloaded.requests[0].id == request.id
    assert reloaded.records[0].request_id == request.id


# --- task 1: status machine ------------------------------------------------

def test_decision_bumps_request_status_and_survives_reload(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = queue.enqueue(_req("APR-MINT-00001"))
    assert queue.list_pending()  # pending before the decision

    record_approval_decision(
        queue, request_id=request.id,
        decision=ApprovalDecision.APPROVED, decided_by="human")

    # in-memory: no longer pending, status projected from the decision
    assert queue.get_request(request.id).status == ApprovalStatus.APPROVED.value
    assert queue.list_pending() == []

    # on reload: the decided request must NOT come back as pending
    reloaded = load_approval_queue(tmp_path)
    assert reloaded.get_request(request.id).status == ApprovalStatus.APPROVED.value
    assert reloaded.list_pending() == []
    # and the record survives under its own REC- namespace
    assert reloaded.records_for(request.id)[0].decision == "approved"


def test_reject_projects_rejected_status(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = queue.enqueue(_req("APR-MINT-00002"))
    record_approval_decision(
        queue, request_id=request.id,
        decision=ApprovalDecision.REJECTED, decided_by="human", notes="no")
    assert queue.get_request(request.id).status == ApprovalStatus.REJECTED.value


def test_deferred_request_can_be_decided_again(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = queue.enqueue(_req("APR-MINT-00003"))
    record_approval_decision(
        queue, request_id=request.id,
        decision=ApprovalDecision.DEFERRED, decided_by="human")
    assert queue.get_request(request.id).status == ApprovalStatus.DEFERRED.value
    # deferred is an open state: a follow-up decision is allowed
    record_approval_decision(
        queue, request_id=request.id,
        decision=ApprovalDecision.APPROVED, decided_by="human")
    assert queue.get_request(request.id).status == ApprovalStatus.APPROVED.value


def test_re_deciding_terminal_request_is_refused(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = queue.enqueue(_req("APR-MINT-00004"))
    record_approval_decision(
        queue, request_id=request.id,
        decision=ApprovalDecision.APPROVED, decided_by="human")
    with pytest.raises(ApprovalStateError):
        record_approval_decision(
            queue, request_id=request.id,
            decision=ApprovalDecision.REJECTED, decided_by="human")


def test_deciding_unknown_request_raises_not_found(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    with pytest.raises(ApprovalNotFound):
        record_approval_decision(
            queue, request_id="APR-NOPE",
            decision=ApprovalDecision.APPROVED, decided_by="human")


# --- task 2: query surface -------------------------------------------------

def test_list_requests_filters_each_dimension(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    queue.enqueue(_req("APR-MINT-00010", target_type="mint", action="confirm_mint", module="mint_executor"))
    queue.enqueue(_req("APR-PUB-00010", target_type="publish", action="confirm_publish", module="publishing.card"))
    queue.enqueue(_req("APR-MINT-00011", target_type="mint", action="confirm_mint", module="mint_executor"))

    assert {r.id for r in queue.list_by_target("mint")} == {"APR-MINT-00010", "APR-MINT-00011"}
    assert [r.id for r in queue.list_by_target("publish")] == ["APR-PUB-00010"]
    assert [r.id for r in queue.list_requests(action="confirm_publish")] == ["APR-PUB-00010"]
    assert {r.id for r in queue.list_requests(source_module="mint_executor")} == {"APR-MINT-00010", "APR-MINT-00011"}
    # combined filter
    assert [r.id for r in queue.list_requests(target_type="mint", action="confirm_publish")] == []


def test_list_by_status_reflects_decisions(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    queue.enqueue(_req("APR-MINT-00020"))
    decided = queue.enqueue(_req("APR-MINT-00021"))
    record_approval_decision(
        queue, request_id=decided.id,
        decision=ApprovalDecision.APPROVED, decided_by="human")
    assert [r.id for r in queue.list_by_status(ApprovalStatus.PENDING.value)] == ["APR-MINT-00020"]
    assert [r.id for r in queue.list_by_status(ApprovalStatus.APPROVED.value)] == ["APR-MINT-00021"]


def test_stats_aggregates_by_status_and_target(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    queue.enqueue(_req("APR-MINT-00030", target_type="mint"))
    queue.enqueue(_req("APR-PUB-00030", target_type="publish"))
    decided = queue.enqueue(_req("APR-MINT-00031", target_type="mint"))
    record_approval_decision(
        queue, request_id=decided.id,
        decision=ApprovalDecision.APPROVED, decided_by="human")

    stats = queue.stats()
    assert stats["total_requests"] == 3
    assert stats["total_records"] == 1
    assert stats["by_status"] == {"approved": 1, "pending": 2}
    assert stats["by_target_type"] == {"mint": 2, "publish": 1}


def test_get_request_returns_none_when_absent(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    assert queue.get_request("APR-MISSING") is None


# --- task 5: audit fields (stored now, consumed next round) ----------------

def test_source_module_auto_derives_from_requested_by(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = queue.enqueue(_req("APR-MINT-00040", module="mint.executor"))
    assert request.source_module == "mint.executor"
    # survives a round-trip through disk
    assert load_approval_queue(tmp_path).get_request(request.id).source_module == "mint.executor"


def test_audit_fields_round_trip(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = create_approval_request(
        request_id="APR-MINT-00041", target_type="mint", target_id="X-1",
        action="confirm_mint", reason="needs approval",
        requested_by={"module": "mint.executor"},
        risk_level="high", priority=5, expires_at="2026-07-20T00:00:00+00:00")
    queue.enqueue(request)
    reloaded = load_approval_queue(tmp_path).get_request(request.id)
    assert reloaded.risk_level == "high"
    assert reloaded.priority == 5
    assert reloaded.expires_at == "2026-07-20T00:00:00+00:00"
    assert reloaded.source_module == "mint.executor"


def test_old_artifact_without_audit_fields_reloads(tmp_path):
    """A request persisted before task 5 (no risk_level/priority/... keys on disk)
    must reload without error, defaulting the new fields."""
    from runtime import derived
    legacy = {
        "kind": "approval_request", "id": "APR-LEGACY-1", "target_type": "mint",
        "target_id": "X-1", "action": "confirm_mint", "reason": "old",
        "authority": "system", "status": "pending",
        "created_at": "2026-07-01T00:00:00+00:00",
        "requested_by": {}, "context": {},
    }
    derived.write_artifact(
        project_path=tmp_path, category="approval-requests",
        artifact_id=legacy["id"], artifact=legacy,
        serialized=__import__("json").dumps(legacy))
    reloaded = load_approval_queue(tmp_path).get_request("APR-LEGACY-1")
    assert reloaded is not None
    assert reloaded.risk_level == ""
    assert reloaded.priority == 0
    assert reloaded.source_module == ""
    assert reloaded.expires_at == ""
