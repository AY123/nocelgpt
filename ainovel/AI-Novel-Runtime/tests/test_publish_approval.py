from __future__ import annotations

from runtime.approval import (
    ApprovalQueue,
    approve_publish,
    build_publish_request,
    enqueue_publish_request,
    load_approval_queue,
    reject_publish,
)


def test_publish_request_builds_and_records_approval(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = enqueue_publish_request(
        queue,
        request_id="APR-PUB-00001",
        chapter_id="TASK-00001",
        reason="chapter ready for release",
        requested_by={"module": "publishing.card"},
        context={"chapter_id": "TASK-00001"},
    )
    assert request.target_type == "publish"
    record = approve_publish(tmp_path, request_id=request.id, decided_by="human", notes="ok")
    assert record["decision"] == "approved"
    # audit only: approving records the go/no-go, it does not publish (ADR-009)
    assert load_approval_queue(tmp_path).get_request(request.id).status == "approved"


def test_reject_publish_records_rejection(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    request = enqueue_publish_request(
        queue,
        request_id="APR-PUB-00002",
        chapter_id="TASK-00002",
        reason="not ready",
    )
    record = reject_publish(tmp_path, request_id=request.id, decided_by="human", notes="fix hook")
    assert record["decision"] == "rejected"
    assert load_approval_queue(tmp_path).get_request(request.id).status == "rejected"
