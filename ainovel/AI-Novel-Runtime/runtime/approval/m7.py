from __future__ import annotations

from typing import Any, Optional

from ..execution.m7 import M7Result
from .queue import ApprovalQueue, ApprovalRequest, create_approval_request

M7_REQUEST_KIND = "m7_review_request"


def build_m7_request(
    *,
    request_id: str,
    chapter_id: str,
    reason: str,
    risk_level: str,
    requested_by: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
) -> ApprovalRequest:
    payload = dict(context or {})
    payload.setdefault("chapter_id", chapter_id)
    payload.setdefault("risk_level", risk_level)
    return create_approval_request(
        request_id=request_id,
        target_type="publish",
        target_id=chapter_id,
        action="review_m7_risk",
        reason=reason,
        requested_by=requested_by or {},
        context=payload,
        risk_level=risk_level,
    )


def enqueue_m7_request(
    queue: ApprovalQueue,
    *,
    request_id: str,
    chapter_id: str,
    reason: str,
    risk_level: str,
    requested_by: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
) -> ApprovalRequest:
    request = build_m7_request(
        request_id=request_id,
        chapter_id=chapter_id,
        reason=reason,
        risk_level=risk_level,
        requested_by=requested_by,
        context=context,
    )
    return queue.enqueue(request)


def m7_result_to_request(
    result: M7Result,
    *,
    request_id: str,
    requested_by: Optional[dict[str, Any]] = None,
) -> ApprovalRequest:
    context = {
        "recommendation": result.recommendation,
        "redline_passed": result.redline_passed,
        "redline_hits": result.redline_hits,
        "similarity": result.similarity,
        "rationale": result.rationale,
    }
    return build_m7_request(
        request_id=request_id,
        chapter_id=result.chapter_id,
        reason=result.rationale,
        risk_level=result.risk_level,
        requested_by=requested_by,
        context=context,
    )
