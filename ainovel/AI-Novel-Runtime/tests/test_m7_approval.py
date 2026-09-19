from __future__ import annotations

from runtime.approval import ApprovalQueue, enqueue_m7_request, m7_result_to_request
from runtime.execution.m7 import assess_m7


def test_m7_result_can_enqueue_review_request(tmp_path):
    queue = ApprovalQueue(project_path=tmp_path)
    result = assess_m7(
        {"body": "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。"},
        chapter_id="CH-9",
        references=[{
            "source_id": "REF-1",
            "source_type": "reference_novel",
            "text": "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。",
        }],
    )
    request = enqueue_m7_request(
        queue,
        request_id="APR-M7-00001",
        chapter_id=result.chapter_id,
        reason=result.rationale,
        risk_level=result.risk_level,
        requested_by={"module": "runtime.execution.m7"},
        context={"recommendation": result.recommendation},
    )
    assert request.target_type == "publish"
    assert request.context["risk_level"] == "L3"
    assert queue.list_pending()[0].id == "APR-M7-00001"


def test_m7_result_to_request_carries_context():
    result = assess_m7({"body": "他在城门外停下脚步。"}, chapter_id="CH-10", references=[])
    request = m7_result_to_request(result, request_id="APR-M7-00002", requested_by={"module": "m7"})
    assert request.id == "APR-M7-00002"
    assert request.context["recommendation"] == result.recommendation
    assert request.context["redline_passed"] is True
