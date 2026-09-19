"""test_promise_core.py — Promise Ledger core tests (Stage B.1).

Tests the unified promise tracking system (runtime/promise/).
"""
import pytest
from unittest.mock import Mock

from runtime.promise.ledger import (
    PromiseEntry,
    PromiseLedger,
    project_promise_ledger,
    ledger_artifact,
    _next_promise_id,
)


def test_promise_entry_basic():
    """Test basic PromiseEntry creation."""
    entry = PromiseEntry(
        id="PROMISE-00001",
        type="packaging",
        statement="主角将获得特殊能力",
        created_at_chapter=1,
        evidence_terms=["梦晶", "精神力"],
        must_deliver_by=3,
        status="open",
        level="critical",
    )

    assert entry.id == "PROMISE-00001"
    assert entry.type == "packaging"
    assert entry.status == "open"
    assert len(entry.evidence_terms) == 2

    d = entry.to_dict()
    assert d["id"] == "PROMISE-00001"
    assert d["created_at_chapter"] == 1


def test_promise_ledger_empty():
    """Test empty promise ledger."""
    ledger = PromiseLedger(reviewer="test-v1", promises=[])

    assert len(ledger.promises) == 0
    assert ledger.gating is False
    assert ledger.ledger_hash  # Should have a hash even when empty

    d = ledger.to_dict()
    assert d["summary"]["total"] == 0
    assert d["summary"]["open"] == 0


def test_promise_ledger_with_entries():
    """Test promise ledger with multiple entries."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001",
            type="packaging",
            statement="金手指能力",
            created_at_chapter=1,
            must_deliver_by=3,
            status="open",
            level="critical",
        ),
        PromiseEntry(
            id="PROMISE-00002",
            type="narrative",
            statement="复仇伏笔",
            created_at_chapter=2,
            status="open",
            level="important",
        ),
        PromiseEntry(
            id="PROMISE-00003",
            type="packaging",
            statement="建立势力",
            created_at_chapter=1,
            must_deliver_by=3,
            status="delivered",
            delivered_at_chapter=2,
            level="critical",
        ),
    ]

    ledger = PromiseLedger(reviewer="test-v1", promises=promises)

    assert len(ledger.promises) == 3

    d = ledger.to_dict()
    assert d["summary"]["total"] == 3
    assert d["summary"]["open"] == 2
    assert d["summary"]["delivered"] == 1
    assert d["summary"]["by_type"]["packaging"] == 2
    assert d["summary"]["by_type"]["narrative"] == 1


def test_promise_ledger_pending_for_chapter():
    """Test querying pending promises for a chapter."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001",
            type="packaging",
            statement="Must deliver by chapter 3",
            created_at_chapter=1,
            must_deliver_by=3,
            status="open",
        ),
        PromiseEntry(
            id="PROMISE-00002",
            type="packaging",
            statement="Must deliver by chapter 5",
            created_at_chapter=1,
            must_deliver_by=5,
            status="open",
        ),
        PromiseEntry(
            id="PROMISE-00003",
            type="narrative",
            statement="No deadline",
            created_at_chapter=2,
            must_deliver_by=None,
            status="open",
        ),
    ]

    ledger = PromiseLedger(reviewer="test-v1", promises=promises)

    # Chapter 2: no promises due this chapter
    pending_ch2 = ledger.pending_for_chapter(2)
    assert len(pending_ch2) == 0

    # Chapter 3: promise 1 is due this chapter
    pending_ch3 = ledger.pending_for_chapter(3)
    assert len(pending_ch3) == 1
    assert pending_ch3[0].id == "PROMISE-00001"

    # Chapter 5: promise 2 is due this chapter
    pending_ch5 = ledger.pending_for_chapter(5)
    assert len(pending_ch5) == 1
    assert pending_ch5[0].id == "PROMISE-00002"

    # Chapter 6: no promises due (all passed)
    pending_ch6 = ledger.pending_for_chapter(6)
    assert len(pending_ch6) == 0


def test_promise_ledger_open_promises():
    """Test querying all open promises."""
    promises = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="A",
                    created_at_chapter=1, status="open"),
        PromiseEntry(id="PROMISE-00002", type="narrative", statement="B",
                    created_at_chapter=2, status="delivered"),
        PromiseEntry(id="PROMISE-00003", type="thread", statement="C",
                    created_at_chapter=3, status="open"),
    ]

    ledger = PromiseLedger(reviewer="test-v1", promises=promises)
    open_p = ledger.open_promises()

    assert len(open_p) == 2
    assert open_p[0].id == "PROMISE-00001"
    assert open_p[1].id == "PROMISE-00003"


def test_promise_ledger_overdue_promises():
    """Test querying overdue promises."""
    promises = [
        PromiseEntry(
            id="PROMISE-00001",
            type="packaging",
            statement="Due ch 3",
            created_at_chapter=1,
            must_deliver_by=3,
            status="open",
        ),
        PromiseEntry(
            id="PROMISE-00002",
            type="packaging",
            statement="Due ch 5",
            created_at_chapter=1,
            must_deliver_by=5,
            status="open",
        ),
        PromiseEntry(
            id="PROMISE-00003",
            type="narrative",
            statement="No deadline",
            created_at_chapter=2,
            must_deliver_by=None,
            status="open",
        ),
    ]

    ledger = PromiseLedger(reviewer="test-v1", promises=promises)

    # At chapter 4: promise 1 is overdue
    overdue_ch4 = ledger.overdue_promises(4)
    assert len(overdue_ch4) == 1
    assert overdue_ch4[0].id == "PROMISE-00001"

    # At chapter 6: both promise 1 and 2 are overdue
    overdue_ch6 = ledger.overdue_promises(6)
    assert len(overdue_ch6) == 2


def test_next_promise_id():
    """Test promise ID generation."""
    assert _next_promise_id([]) == "PROMISE-00001"
    assert _next_promise_id(["PROMISE-00001"]) == "PROMISE-00002"
    assert _next_promise_id(["PROMISE-00001", "PROMISE-00005"]) == "PROMISE-00006"
    assert _next_promise_id(["PROMISE-00099"]) == "PROMISE-00100"


def test_ledger_deterministic_hash():
    """Test that same promises produce same hash."""
    promises1 = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="A",
                    created_at_chapter=1, status="open"),
    ]
    promises2 = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="A",
                    created_at_chapter=1, status="open"),
    ]

    ledger1 = PromiseLedger(reviewer="test-v1", promises=promises1)
    ledger2 = PromiseLedger(reviewer="test-v1", promises=promises2)

    assert ledger1.ledger_hash == ledger2.ledger_hash


def test_ledger_different_hash():
    """Test that different promises produce different hash."""
    promises1 = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="A",
                    created_at_chapter=1, status="open"),
    ]
    promises2 = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="B",  # Different statement
                    created_at_chapter=1, status="open"),
    ]

    ledger1 = PromiseLedger(reviewer="test-v1", promises=promises1)
    ledger2 = PromiseLedger(reviewer="test-v1", promises=promises2)

    assert ledger1.ledger_hash != ledger2.ledger_hash


def test_ledger_artifact():
    """Test creating a derived artifact from ledger."""
    promises = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="Test",
                    created_at_chapter=1, status="open"),
    ]
    ledger = PromiseLedger(reviewer="test-v1", promises=promises)

    artifact = ledger_artifact(ledger, "/tmp/test-project")

    assert artifact["kind"] == "promise_ledger"
    assert artifact["version"] == "1.0"
    assert artifact["authority"] == "human"
    assert artifact["gating"] is False
    assert "promises" in artifact
    assert "summary" in artifact
    assert artifact["summary"]["total"] == 1


def test_project_promise_ledger_empty():
    """Test projecting ledger with no data."""
    # Mock empty registry
    mock_reg = Mock()
    mock_reg.facts = {}

    ledger = project_promise_ledger(mock_reg, packaging=None)

    assert len(ledger.promises) == 0
    assert ledger.gating is False
    assert ledger.reviewer == "promise-ledger-v1"


def test_adrs_compliance():
    """Test that Promise Ledger follows all ADRs."""
    promises = [
        PromiseEntry(id="PROMISE-00001", type="packaging", statement="Test",
                    created_at_chapter=1, status="open"),
    ]
    ledger = PromiseLedger(reviewer="test-v1", promises=promises)

    # ADR-003: Advisory, never gates
    assert ledger.gating is False

    artifact = ledger_artifact(ledger, "/tmp/test")

    # ADR-009: Human authority
    assert artifact["authority"] == "human"

    # ADR-008: Deterministic (same input => same hash)
    ledger2 = PromiseLedger(reviewer="test-v1", promises=promises)
    assert ledger.ledger_hash == ledger2.ledger_hash
