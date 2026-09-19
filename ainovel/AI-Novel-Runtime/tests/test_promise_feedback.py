"""test_promise_feedback.py — Promise feedback tests (Stage B.3).

Tests the promise-to-generation feedback layer.
"""
import pytest

from runtime.promise.ledger import PromiseEntry, PromiseLedger
from runtime.promise.feedback import (
    pending_promises_for_chapter,
    overdue_promises_for_chapter,
    render_promise_brief,
    inject_promises_into_objective,
    render_promise_brief_for_prompt,
    verify_promise_delivery,
    promise_delivery_report,
)


def test_pending_promises_for_chapter():
    """Test querying pending promises for a chapter."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="Promise 1",
            created_at_chapter=1, must_deliver_by=3, status="open",
        ),
        PromiseEntry(
            id="PROMISE-00002", type="packaging", statement="Promise 2",
            created_at_chapter=1, must_deliver_by=5, status="open",
        ),
        PromiseEntry(
            id="PROMISE-00003", type="narrative", statement="Promise 3",
            created_at_chapter=2, must_deliver_by=None, status="open",
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    # Chapter 3: exact deadline
    pending = pending_promises_for_chapter(ledger, 3)
    assert len(pending) == 1
    assert pending[0].id == "PROMISE-00001"

    # Chapter 3 with lookahead: includes promise due at ch 5
    pending = pending_promises_for_chapter(ledger, 3, lookahead=2)
    assert len(pending) == 2
    assert pending[0].id == "PROMISE-00001"
    assert pending[1].id == "PROMISE-00002"


def test_overdue_promises_for_chapter():
    """Test querying overdue promises."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="Overdue",
            created_at_chapter=1, must_deliver_by=3, status="open",
        ),
        PromiseEntry(
            id="PROMISE-00002", type="packaging", statement="Not yet",
            created_at_chapter=1, must_deliver_by=10, status="open",
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    # Chapter 5: first promise is overdue
    overdue = overdue_promises_for_chapter(ledger, 5)
    assert len(overdue) == 1
    assert overdue[0].id == "PROMISE-00001"


def test_render_promise_brief_empty():
    """Test rendering empty promise list."""
    brief = render_promise_brief([], context="delivery")
    assert brief == ""


def test_render_promise_brief_delivery():
    """Test rendering promises for delivery context."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="金手指能力",
            created_at_chapter=1, must_deliver_by=3, status="open",
            level="critical", evidence_terms=["梦晶", "精神力"],
        ),
        PromiseEntry(
            id="PROMISE-00002", type="narrative", statement="复仇伏笔",
            created_at_chapter=2, status="open", level="important",
        ),
    ]

    brief = render_promise_brief(promises, context="delivery")

    assert "必须兑现的承诺" in brief
    assert "金手指能力" in brief
    assert "梦晶" in brief
    assert "应兑现的伏笔" in brief
    assert "复仇伏笔" in brief


def test_inject_promises_into_objective():
    """Test injecting promises into chapter objective."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="Test promise",
            created_at_chapter=1, must_deliver_by=3, status="open",
            level="critical",
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    objective = {
        "id": "OBJ-00001",
        "constraints": ["原有约束"],
    }

    result = inject_promises_into_objective(objective, ledger, chapter=3)

    # Check promise_to_deliver field
    assert "promise_to_deliver" in result
    assert len(result["promise_to_deliver"]) == 1
    assert result["promise_to_deliver"][0] == "Test promise"

    # Check promise_refs field
    assert "promise_refs" in result
    assert len(result["promise_refs"]) == 1
    assert result["promise_refs"][0]["id"] == "PROMISE-00001"
    assert result["promise_refs"][0]["level"] == "critical"

    # Check constraints updated
    assert len(result["constraints"]) == 2
    assert any("包装承诺" in c for c in result["constraints"])


def test_inject_promises_no_relevant():
    """Test injecting when no promises are relevant."""
    ledger = PromiseLedger(reviewer="test", promises=[])

    objective = {"id": "OBJ-00001"}
    result = inject_promises_into_objective(objective, ledger, chapter=5)

    assert result["promise_to_deliver"] == []
    assert result["promise_refs"] == []


def test_render_promise_brief_for_prompt():
    """Test rendering promise brief for prompts."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="关键承诺",
            created_at_chapter=1, must_deliver_by=3, status="open",
            level="critical", evidence_terms=["关键词"],
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    brief = render_promise_brief_for_prompt(ledger, chapter=3)

    assert brief != ""
    assert "本章应兑现的承诺" in brief or "逾期未兑的承诺" in brief
    assert "关键承诺" in brief


def test_render_promise_brief_for_prompt_empty():
    """Test rendering when no promises are relevant."""
    ledger = PromiseLedger(reviewer="test", promises=[])
    brief = render_promise_brief_for_prompt(ledger, chapter=5)
    assert brief == ""


def test_verify_promise_delivery_with_evidence():
    """Test verifying promise delivery with evidence terms."""
    promise = PromiseEntry(
        id="PROMISE-00001", type="packaging", statement="金手指",
        created_at_chapter=1, evidence_terms=["梦晶", "精神力", "天赋"],
        status="open",
    )

    draft = "主角激活了梦晶，发现自己拥有强大的精神力。"

    result = verify_promise_delivery(draft, promise)

    assert result["delivered"] is True
    assert "梦晶" in result["evidence_found"]
    assert "精神力" in result["evidence_found"]
    assert result["confidence"] in ["medium", "high"]


def test_verify_promise_delivery_no_evidence():
    """Test verifying when evidence terms are not found."""
    promise = PromiseEntry(
        id="PROMISE-00001", type="packaging", statement="Test",
        created_at_chapter=1, evidence_terms=["关键词A", "关键词B"],
        status="open",
    )

    draft = "这是一段普通的文本，没有包含关键词。"

    result = verify_promise_delivery(draft, promise)

    assert result["delivered"] is False
    assert len(result["evidence_found"]) == 0
    assert result["confidence"] == "low"


def test_verify_promise_delivery_no_terms():
    """Test verifying promise without evidence terms."""
    promise = PromiseEntry(
        id="PROMISE-00001", type="narrative", statement="叙事伏笔",
        created_at_chapter=2, evidence_terms=[], status="open",
    )

    draft = "任意文本"

    result = verify_promise_delivery(draft, promise)

    assert result["delivered"] is None
    assert result["confidence"] == "unknown"


def test_promise_delivery_report():
    """Test generating a delivery report."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="Promise 1",
            created_at_chapter=1, must_deliver_by=3, status="open",
            evidence_terms=["关键词A"],
        ),
        PromiseEntry(
            id="PROMISE-00002", type="packaging", statement="Promise 2",
            created_at_chapter=1, must_deliver_by=3, status="open",
            evidence_terms=["关键词B"],
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    draft = "本章包含关键词A，实现了第一个承诺。"

    report = promise_delivery_report(ledger, chapter=3, draft_body=draft)

    assert report["chapter"] == 3
    assert report["total_relevant"] == 2
    assert report["delivered"] == 1  # Only one delivered
    assert len(report["results"]) == 2
    assert "承诺已兑现" in report["summary"]


def test_promise_delivery_report_no_relevant():
    """Test delivery report when no promises are relevant."""
    ledger = PromiseLedger(reviewer="test", promises=[])
    draft = "任意文本"

    report = promise_delivery_report(ledger, chapter=5, draft_body=draft)

    assert report["total_relevant"] == 0
    assert report["delivered"] == 0
    assert "无待兑承诺" in report["summary"]


def test_feedback_adrs_compliance():
    """Test that feedback layer follows ADRs."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="Test",
            created_at_chapter=1, must_deliver_by=3, status="open",
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    # ADR-003: Advisory only, never gates
    # The feedback functions return data but don't block execution
    pending = pending_promises_for_chapter(ledger, 3)
    assert isinstance(pending, list)  # Returns data, doesn't raise

    objective = {"id": "OBJ-00001"}
    result = inject_promises_into_objective(objective, ledger, 3)
    # Injection adds fields but doesn't reject the objective
    assert "promise_to_deliver" in result
