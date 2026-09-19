from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .queue import (
    ApprovalDecision,
    ApprovalQueue,
    ApprovalRequest,
    create_approval_request,
    load_approval_queue,
    record_approval_decision,
)
from ..execution.m7 import M7Result

PUBLISH_REQUEST_KIND = "publish_request"


def build_publish_request(*, request_id: str, chapter_id: str, reason: str, requested_by: Optional[dict[str, Any]] = None, context: Optional[dict[str, Any]] = None) -> ApprovalRequest:
    payload = dict(context or {})
    payload.setdefault("chapter_id", chapter_id)
    return create_approval_request(
        request_id=request_id,
        target_type="publish",
        target_id=chapter_id,
        action="confirm_publish",
        reason=reason,
        requested_by=requested_by or {},
        context=payload,
    )


def enqueue_publish_request(queue: ApprovalQueue, *, request_id: str, chapter_id: str, reason: str, requested_by: Optional[dict[str, Any]] = None, context: Optional[dict[str, Any]] = None) -> ApprovalRequest:
    request = build_publish_request(
        request_id=request_id,
        chapter_id=chapter_id,
        reason=reason,
        requested_by=requested_by,
        context=context,
    )
    return queue.enqueue(request)


def approve_publish(project_path: str | Path, *, request_id: str, decided_by: str, notes: str = "") -> dict[str, Any]:
    """Record a human APPROVED decision on a publish request.

    Audit only: this records who authorized the publish, it does NOT write the
    published log. Publishing is an irreversible outward transition, so per
    ADR-009 the human still authors the published log to actually publish — the
    approval never crosses that boundary on its own."""
    queue = load_approval_queue(project_path)
    record = record_approval_decision(
        queue,
        request_id=request_id,
        decision=ApprovalDecision.APPROVED,
        decided_by=decided_by,
        notes=notes,
    )
    return record.to_dict()


def reject_publish(project_path: str | Path, *, request_id: str, decided_by: str, notes: str = "") -> dict[str, Any]:
    """Record a human REJECTED decision on a publish request. Symmetric to
    approve_publish; audit only, writes no published log (ADR-009)."""
    queue = load_approval_queue(project_path)
    record = record_approval_decision(
        queue,
        request_id=request_id,
        decision=ApprovalDecision.REJECTED,
        decided_by=decided_by,
        notes=notes,
    )
    return record.to_dict()
