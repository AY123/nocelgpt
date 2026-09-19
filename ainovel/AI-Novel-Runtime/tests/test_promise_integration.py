"""test_promise_integration.py — Promise Ledger integration tests (Stage B.4).

Tests that Promise Ledger is properly integrated into the serial run pipeline.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


def test_promise_ledger_loads_in_serial_run():
    """Test that Promise Ledger loads during serial run initialization."""
    # This is a simplified test - we verify the integration points exist
    # Full integration testing requires a real project setup
    from runtime.promise import project_promise_ledger
    from unittest.mock import Mock

    # Create mock registry and packaging
    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "[伏笔] Test setup",
            "sequence_index": 0,
        }
    }

    mock_packaging = {
        "promises": [
            {
                "promise_id": "P1",
                "statement": "Test promise",
                "evidence_terms": ["test"],
                "must_appear_by": 3,
            }
        ]
    }

    # Verify ledger can be created
    ledger = project_promise_ledger(mock_reg, mock_packaging)

    assert ledger is not None
    assert len(ledger.promises) >= 1  # At least the packaging promise


def test_promise_injection_into_objective():
    """Test that promises are injected into chapter objectives."""
    from runtime.promise import (
        PromiseEntry,
        PromiseLedger,
        inject_promises_into_objective,
    )

    # Create a test ledger with promises
    promises = [
        PromiseEntry(
            id="PROMISE-00001",
            type="packaging",
            statement="Test promise",
            created_at_chapter=1,
            must_deliver_by=3,
            status="open",
            level="critical",
        ),
    ]
    ledger = PromiseLedger(reviewer="test", promises=promises)

    # Create a mock objective
    objective = {
        "id": "OBJ-00001",
        "primary_goal": "Test goal",
        "constraints": [],
    }

    # Inject promises
    result = inject_promises_into_objective(objective, ledger, chapter=3)

    # Verify injection
    assert "promise_to_deliver" in result
    assert len(result["promise_to_deliver"]) > 0
    assert "promise_refs" in result
    assert len(result["promise_refs"]) > 0


def test_promise_ledger_graceful_degradation():
    """Test that Promise Ledger handles errors gracefully."""
    from runtime.promise import project_promise_ledger
    from unittest.mock import Mock

    # Test with invalid packaging
    mock_reg = Mock()
    mock_reg.facts = {}

    # Invalid packaging should not crash
    try:
        ledger = project_promise_ledger(mock_reg, None)
        assert ledger is not None
        assert len(ledger.promises) == 0
    except Exception as e:
        pytest.fail(f"Should handle None packaging gracefully: {e}")


def test_promise_ledger_result_summary():
    """Test that Promise Ledger summary appears in serial result."""
    from runtime.serialize.loop import SerialResult, ChapterRun, ChapterSpec

    result = SerialResult(
        produced=0,
        skipped=0,
        final_state_hash="test",
        gating=False,
        chapters=[],
        llm_cost={},
        llm_usage={},
        reviewer="test-reviewer",
        promise_ledger={
            "summary": {
                "total": 5,
                "open": 3,
                "delivered": 2,
                "by_type": {"packaging": 2, "narrative": 3},
            },
            "gating": False,
            "reviewer": "promise-ledger-v1",
        }
    )

    result_dict = result.to_dict()

    assert "promise_ledger" in result_dict
    assert result_dict["promise_ledger"]["summary"]["total"] == 5
    assert result_dict["promise_ledger"]["gating"] is False


def test_promise_ledger_none_when_absent():
    """Test that promise_ledger is None when no packaging exists."""
    from runtime.serialize.loop import SerialResult

    result = SerialResult(
        produced=0,
        skipped=0,
        final_state_hash="test",
        gating=False,
        chapters=[],
        llm_cost={},
        llm_usage={},
        reviewer="test-reviewer",
        promise_ledger=None,  # No packaging = no ledger
    )

    result_dict = result.to_dict()

    # Should be None, not an empty dict
    assert result_dict["promise_ledger"] is None


def test_integration_adrs_compliance():
    """Test that Promise integration follows ADRs."""
    from runtime.promise import PromiseLedger

    # ADR-003: Advisory, never gates
    ledger = PromiseLedger(reviewer="test", promises=[])
    assert ledger.gating is False

    # ADR-006: Derived artifact, never a fact
    # (Verified by where it's stored in serialize/loop.py)

    # ADR-008: Deterministic
    # (Verified by ledger_hash test in core tests)

    # ADR-009: Human authority
    # (Verified by authority field in ledger_artifact)

    # Integration should not break existing behavior
    # (Verified by graceful degradation test above)
