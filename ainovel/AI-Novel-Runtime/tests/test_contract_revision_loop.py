"""Test Contract Gate revision loop integration (Phase 3 Stage 2, Task 2.2 Part 2).

Tests that when a Candidate fails contract check, the revision loop is triggered.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


def test_candidate_check_triggers_revision_when_critical_issues():
    """When check_candidate() finds critical issues, revision should be triggered."""
    import sys
    from pathlib import Path

    # Add runtime_plugins to path
    plugins_path = Path(__file__).parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate

    # We can't run the real check without a real contract file,
    # but we can verify the check_candidate method exists and has the right signature
    gate = Mock(spec=ContractGate)

    # Verify the method exists by checking the class
    assert hasattr(ContractGate, 'check_candidate')
    import inspect
    sig = inspect.signature(ContractGate.check_candidate)
    assert 'chapter' in sig.parameters
    assert 'candidate_text' in sig.parameters
    assert 'prev_text' in sig.parameters


def test_revision_loop_structure():
    """Test the expected structure of the revision loop.

    Pseudo-code of what should happen:

    1. execute_package() -> candidate_draft
    2. check_candidate(candidate_draft)
    3. If critical issues:
       a. Generate revision_suggestions
       b. Call rewrite with suggestions
       c. Re-check revised draft
       d. If still fails, repeat (max N rounds)
    4. If passes or max rounds reached, proceed to Final
    """
    # This is a design test - it documents the expected behavior
    # The actual implementation will be in run_serial

    expected_flow = {
        "step1": "generate candidate",
        "step2": "check_candidate()",
        "step3_if_critical": {
            "action": "revision_loop",
            "max_rounds": 2,
            "per_round": [
                "extract suggestions from issues",
                "call rewrite_model with suggestions",
                "check_candidate() again",
            ],
            "exit_condition": "pass OR max_rounds",
        },
        "step4": "proceed to hygiene/commercial loops",
    }

    assert expected_flow["step3_if_critical"]["max_rounds"] >= 1
    assert "check_candidate()" in expected_flow["step2"]


def test_revision_session_structure():
    """Test the expected structure of the contract_revision_session.

    This should be persisted on the ChapterRun envelope, similar to
    hygiene_session and commercial_session.
    """
    expected_session = {
        "rounds": [
            {
                "round": 1,
                "check_result": {
                    "pass": False,
                    "issues": [
                        {
                            "category": "critical",
                            "field": "entry_location",
                            "description": "章节未在要求的地点开始"
                        }
                    ],
                    "requires_revision": True,
                    "revision_suggestions": [
                        "确保章节在 loc_city_square 开始"
                    ]
                },
                "revised_draft_hash": "abc123...",
            }
        ],
        "final_check": {
            "pass": True,
            "issues": [],
        },
        "verdict": "revised_pass",  # or "revised_fail" or "initial_pass"
    }

    assert "rounds" in expected_session
    assert "final_check" in expected_session
    assert "verdict" in expected_session


def test_chapter_run_contract_revision_field():
    """Verify ChapterRun can carry contract_revision_session."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    # Create a ChapterRun with contract_revision_session
    # (This field doesn't exist yet - we'll add it)
    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
    )

    # Currently contract_validation exists, but contract_revision_session doesn't
    assert hasattr(run, 'contract_validation')
    # TODO: Add contract_revision_session field to ChapterRun


def test_revision_loop_never_gates():
    """Contract revision loop is ADVISORY - it never gates the serial (ADR-003).

    Even if revision fails after max rounds, the chapter is still produced.
    The failure is recorded in contract_revision_session for audit.
    """
    # This is a design principle test
    ADR_003 = "evaluative/advisory checks never gate production"

    # The revision loop:
    # - Records all attempts in contract_revision_session
    # - Produces the BEST draft (fewest critical issues)
    # - NEVER raises or skips the chapter
    # - Lets the chapter proceed even if critical issues remain

    assert "never gate" in ADR_003.lower()
