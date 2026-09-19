"""test_promise_matcher.py — Tests for Promise Evidence Matcher.

Tests the evidence matching logic that detects promise delivery.
"""
import pytest
from runtime.promise.ledger import PromiseEntry, PromiseLedger
from runtime.promise.matcher import (
    match_evidence,
    check_delivery,
    get_delivered_promises,
    get_pending_promises,
    calculate_ledger_summary,
)


def test_match_evidence_full_match():
    """Test evidence matching with 100% coverage."""
    promise = PromiseEntry(
        id="TEST-001",
        type="packaging",
        statement="Test promise",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核", "曜能"],
        must_deliver_by=1,
        status="open",
    )

    draft = "段奕尘使用吞噬能力，吸收了晶核的曜能。"

    coverage = match_evidence(promise, draft)
    assert coverage == 1.0  # All 3 terms found


def test_match_evidence_partial_match():
    """Test evidence matching with partial coverage."""
    promise = PromiseEntry(
        id="TEST-002",
        type="packaging",
        statement="Test promise",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核", "曜能", "转化"],
        must_deliver_by=1,
        status="open",
    )

    draft = "段奕尘使用吞噬能力，感受到曜能在体内流转。"

    coverage = match_evidence(promise, draft)
    assert coverage == 0.5  # 2 out of 4 terms found


def test_match_evidence_no_match():
    """Test evidence matching with no terms found."""
    promise = PromiseEntry(
        id="TEST-003",
        type="packaging",
        statement="Test promise",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核", "曜能"],
        must_deliver_by=1,
        status="open",
    )

    draft = "段奕尘在矿道中奔跑。"

    coverage = match_evidence(promise, draft)
    assert coverage == 0.0


def test_match_evidence_no_terms():
    """Test evidence matching when promise has no terms."""
    promise = PromiseEntry(
        id="TEST-004",
        type="narrative",
        statement="Test promise",
        created_at_chapter=1,
        evidence_terms=[],
        must_deliver_by=None,
        status="open",
    )

    draft = "Some content"

    coverage = match_evidence(promise, draft)
    assert coverage == 0.0


def test_match_evidence_empty_draft():
    """Test evidence matching with empty draft."""
    promise = PromiseEntry(
        id="TEST-005",
        type="packaging",
        statement="Test promise",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核"],
        must_deliver_by=1,
        status="open",
    )

    coverage = match_evidence(promise, "")
    assert coverage == 0.0

    coverage = match_evidence(promise, "")
    assert coverage == 0.0


def test_check_delivery_delivers_promise():
    """Test that check_delivery marks promises as delivered."""
    promise1 = PromiseEntry(
        id="PROMISE-00001",
        type="packaging",
        statement="吞噬能力",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核", "曜能"],
        must_deliver_by=1,
        status="open",
    )

    promise2 = PromiseEntry(
        id="PROMISE-00002",
        type="packaging",
        statement="矿工崛起",
        created_at_chapter=1,
        evidence_terms=["矿工", "逆袭"],
        must_deliver_by=2,
        status="open",
    )

    ledger = PromiseLedger(
        reviewer="test",
        promises=[promise1, promise2],
    )

    # Draft contains evidence for promise1 (100% coverage)
    draft = "段奕尘的吞噬能力可以吸收晶核中的曜能。"

    updated_ledger = check_delivery(
        ledger,
        draft,
        chapter=1,
        event_id="EVT-00001",
        threshold=0.5
    )

    # Promise1 should be delivered
    p1 = [p for p in updated_ledger.promises if p.id == "PROMISE-00001"][0]
    assert p1.status == "delivered"
    assert p1.delivered_at_chapter == 1
    assert p1.delivered_in_event == "EVT-00001"

    # Promise2 should still be open (no evidence)
    p2 = [p for p in updated_ledger.promises if p.id == "PROMISE-00002"][0]
    assert p2.status == "open"


def test_check_delivery_threshold():
    """Test that threshold controls delivery detection."""
    promise = PromiseEntry(
        id="PROMISE-00001",
        type="packaging",
        statement="Test",
        created_at_chapter=1,
        evidence_terms=["吞噬", "晶核", "曜能", "转化"],
        must_deliver_by=1,
        status="open",
    )

    ledger = PromiseLedger(reviewer="test", promises=[promise])

    # Draft contains 2/4 terms = 50% coverage
    draft = "段奕尘使用吞噬能力，感受到曜能流转。"

    # With threshold=0.5, should deliver
    updated = check_delivery(ledger, draft, 1, "EVT-001", threshold=0.5)
    assert updated.promises[0].status == "delivered"

    # With threshold=0.6, should NOT deliver
    updated = check_delivery(ledger, draft, 1, "EVT-001", threshold=0.6)
    assert updated.promises[0].status == "open"


def test_check_delivery_keeps_already_delivered():
    """Test that already delivered promises stay delivered."""
    promise = PromiseEntry(
        id="PROMISE-00001",
        type="packaging",
        statement="Test",
        created_at_chapter=1,
        evidence_terms=["吞噬"],
        must_deliver_by=1,
        status="delivered",
        delivered_at_chapter=1,
        delivered_in_event="EVT-00001",
    )

    ledger = PromiseLedger(reviewer="test", promises=[promise])

    # Check again in chapter 2
    updated = check_delivery(ledger, "Some content", 2, "EVT-00002")

    # Should still be delivered in chapter 1 (not updated)
    assert updated.promises[0].status == "delivered"
    assert updated.promises[0].delivered_at_chapter == 1
    assert updated.promises[0].delivered_in_event == "EVT-00001"


def test_get_delivered_promises():
    """Test getting delivered promises for a chapter."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="P1",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=1, status="delivered",
            delivered_at_chapter=1, delivered_in_event="EVT-001"
        ),
        PromiseEntry(
            id="PROMISE-00002", type="packaging", statement="P2",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=2, status="delivered",
            delivered_at_chapter=2, delivered_in_event="EVT-002"
        ),
        PromiseEntry(
            id="PROMISE-00003", type="packaging", statement="P3",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=1, status="open"
        ),
    ]

    ledger = PromiseLedger(reviewer="test", promises=promises)

    # Chapter 1 should have PROMISE-00001
    ch1_delivered = get_delivered_promises(ledger, 1)
    assert ch1_delivered == ["PROMISE-00001"]

    # Chapter 2 should have PROMISE-00002
    ch2_delivered = get_delivered_promises(ledger, 2)
    assert ch2_delivered == ["PROMISE-00002"]


def test_get_pending_promises():
    """Test getting overdue promises."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001", type="packaging", statement="P1",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=1, status="open"
        ),
        PromiseEntry(
            id="PROMISE-00002", type="packaging", statement="P2",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=3, status="open"
        ),
        PromiseEntry(
            id="PROMISE-00003", type="packaging", statement="P3",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=2, status="delivered",
            delivered_at_chapter=2
        ),
        PromiseEntry(
            id="PROMISE-00004", type="narrative", statement="P4",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=None, status="open"
        ),
    ]

    ledger = PromiseLedger(reviewer="test", promises=promises)

    # At chapter 2: PROMISE-00001 (due ch1) and PROMISE-00002 (no due) are overdue
    pending = get_pending_promises(ledger, 2)
    assert set(pending) == {"PROMISE-00001"}

    # At chapter 3: PROMISE-00001 and PROMISE-00002 are overdue
    pending = get_pending_promises(ledger, 3)
    assert set(pending) == {"PROMISE-00001", "PROMISE-00002"}


def test_calculate_ledger_summary():
    """Test ledger summary calculation."""
    promises = [
        PromiseEntry(
            id="P1", type="packaging", statement="P1",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=1, status="open"
        ),
        PromiseEntry(
            id="P2", type="packaging", statement="P2",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=2, status="delivered",
            delivered_at_chapter=2
        ),
        PromiseEntry(
            id="P3", type="thread", statement="P3",
            created_at_chapter=1, evidence_terms=[], must_deliver_by=None, status="open"
        ),
    ]

    ledger = PromiseLedger(reviewer="test", promises=promises)

    summary = calculate_ledger_summary(ledger)

    assert summary["total"] == 3
    assert summary["by_status"] == {"open": 2, "delivered": 1}
    assert summary["by_type"] == {"packaging": 2, "thread": 1}
