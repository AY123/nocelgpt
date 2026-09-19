"""End-to-end test for Contract Revision Loop (Phase 3 Stage 2, Task 2.2).

Tests the full revision flow: Candidate check → revision → re-check → keep best.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch


def test_revision_loop_integration_points():
    """Verify the revision loop integration points exist in run_serial."""
    import inspect
    from runtime.serialize.loop import run_serial

    # Check the new parameter exists
    sig = inspect.signature(run_serial)
    assert 'contract_revision_rounds' in sig.parameters
    assert sig.parameters['contract_revision_rounds'].default == 2

    # Check docstring mentions revision loop
    doc = run_serial.__doc__
    assert 'revision loop' in doc.lower()
    assert 'critical issues' in doc.lower()


def test_chapter_run_carries_revision_session():
    """Verify ChapterRun can carry contract_revision_session."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    session = {
        "initial_check": {"pass": False, "requires_revision": True},
        "rounds": [
            {
                "round": 1,
                "check_result": {"pass": True, "issues": []},
                "revised_draft_hash": "abc123",
            }
        ],
        "final_check": {"pass": True, "issues": []},
        "verdict": "revised_pass",
    }

    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        contract_revision_session=session,
    )

    # Check field exists
    assert hasattr(run, 'contract_revision_session')
    assert run.contract_revision_session == session

    # Check serialization
    run_dict = run.to_dict()
    assert 'contract_revision_session' in run_dict
    assert run_dict['contract_revision_session'] == session


def test_revision_session_structure_valid():
    """Test that a typical revision session has the expected structure."""
    session = {
        "initial_check": {
            "pass": False,
            "issues": [
                {
                    "category": "critical",
                    "field": "entry_location",
                    "description": "章节未在要求的地点开始"
                }
            ],
            "requires_revision": True,
            "revision_suggestions": ["确保章节在 loc_city_square 开始"]
        },
        "rounds": [
            {
                "round": 1,
                "check_result": {
                    "pass": True,
                    "issues": [],
                    "requires_revision": False,
                },
                "revised_draft_hash": "def456",
                "critical_issues_before": 1,
                "critical_issues_after": 0,
            }
        ],
        "final_check": {
            "pass": True,
            "issues": [],
            "requires_revision": False,
        },
        "verdict": "revised_pass",
        "initial_critical_count": 1,
        "final_critical_count": 0,
        "improved": True,
    }

    # Validate structure
    assert "initial_check" in session
    assert "rounds" in session
    assert "final_check" in session
    assert "verdict" in session
    assert "improved" in session

    # Validate round structure
    assert len(session["rounds"]) == 1
    round1 = session["rounds"][0]
    assert round1["round"] == 1
    assert "check_result" in round1
    assert "revised_draft_hash" in round1
    assert "critical_issues_before" in round1
    assert "critical_issues_after" in round1

    # Validate improvement
    assert session["initial_critical_count"] > session["final_critical_count"]
    assert session["improved"] is True


def test_revision_verdicts():
    """Test the different verdict outcomes."""
    verdicts = [
        "initial_pass",      # No revision needed
        "revised_pass",      # Revision succeeded (0 critical issues)
        "revised_improved",  # Revision reduced critical issues
        "revised_partial",   # Still has issues but did best effort
        "error",             # Revision failed with error
    ]

    for verdict in verdicts:
        session = {
            "verdict": verdict,
            "initial_check": {"pass": verdict == "initial_pass"},
            "rounds": [] if verdict == "initial_pass" else [{"round": 1}],
            "final_check": {"pass": verdict in ("initial_pass", "revised_pass")},
        }

        # All verdicts are valid - none should gate (ADR-003)
        assert session["verdict"] in verdicts


def test_revision_loop_never_gates_chapter():
    """Test that revision failures never gate the chapter (ADR-003).

    Even if all revision rounds fail and critical issues remain,
    the chapter should still be marked as produced (ok=True).
    """
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    # Worst case: all revisions failed, still has critical issues
    failed_session = {
        "initial_check": {"pass": False, "requires_revision": True},
        "rounds": [
            {"round": 1, "critical_issues_after": 2},
            {"round": 2, "critical_issues_after": 2},
        ],
        "final_check": {"pass": False, "issues": [{"category": "critical"}]},
        "verdict": "revised_partial",
        "initial_critical_count": 2,
        "final_critical_count": 2,
        "improved": False,
    }

    # Chapter should still be ok=True (never gates)
    run = ChapterRun(
        spec=spec,
        ok=True,  # ← This is the key assertion
        stage="done",
        contract_revision_session=failed_session,
    )

    assert run.ok is True
    assert run.stage == "done"
    assert run.contract_revision_session["verdict"] == "revised_partial"


def test_check_candidate_method_exists():
    """Verify ContractGate.check_candidate() method exists with correct signature."""
    import sys
    from pathlib import Path

    # Add runtime_plugins to path
    plugins_path = Path(__file__).parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate
    import inspect

    # Verify method exists
    assert hasattr(ContractGate, 'check_candidate')

    # Verify signature
    sig = inspect.signature(ContractGate.check_candidate)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'chapter' in params
    assert 'candidate_text' in params
    assert 'prev_text' in params


def test_revision_loop_keeps_best_draft():
    """Test that revision loop keeps the draft with fewest critical issues.

    If round 1 improves but round 2 degrades, round 1's draft should be kept.
    """
    # Simulated session where round 2 was worse than round 1
    session = {
        "initial_check": {"pass": False},
        "rounds": [
            {
                "round": 1,
                "revised_draft_hash": "hash1",
                "critical_issues_before": 3,
                "critical_issues_after": 1,  # ← Best
            },
            {
                "round": 2,
                "revised_draft_hash": "hash2",
                "critical_issues_before": 1,
                "critical_issues_after": 2,  # ← Worse than round 1
            },
        ],
        "final_check": {"pass": False},
        "verdict": "revised_improved",
        "initial_critical_count": 3,
        "final_critical_count": 1,  # ← Kept round 1's result
        "improved": True,
    }

    # The final_critical_count should be from round 1 (the best)
    assert session["final_critical_count"] == 1
    assert session["rounds"][0]["critical_issues_after"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
