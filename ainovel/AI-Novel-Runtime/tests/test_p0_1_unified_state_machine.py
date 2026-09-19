"""
Tests for P0-1: Unified State Machine

Validates that the canonical ChapterDecision enforces all invariants
and prevents contradictory decision states.
"""
import pytest
from pathlib import Path
import json

from runtime.chapter.state_machine import (
    ChapterState,
    ChapterDecision,
    StateTransition,
    create_approved_decision,
    create_blocked_decision,
    create_held_decision,
)
from runtime.decision_engine import ProductionDecisionEngine


class TestChapterStateInvariants:
    """Test that ChapterDecision enforces invariants at construction"""

    def test_blocked_chapter_cannot_advance(self):
        """P0-1: BLOCKED chapters must not be able to advance"""
        with pytest.raises(ValueError, match="BLOCKED chapters cannot advance"):
            ChapterDecision(
                state=ChapterState.BLOCKED,
                advance_to_next=True,  # Contradiction!
                blocking_issues=["redline failed"],
                warnings=[],
                human_approval_required=False,
                decision_provenance={}
            )

    def test_finalized_chapter_cannot_have_blocking_issues(self):
        """P0-1: FINALIZED chapters cannot have blocking issues"""
        with pytest.raises(ValueError, match="FINALIZED chapters cannot have blocking issues"):
            ChapterDecision(
                state=ChapterState.FINALIZED,
                advance_to_next=True,
                blocking_issues=["some issue"],  # Contradiction!
                warnings=[],
                human_approval_required=False,
                decision_provenance={}
            )

    def test_held_chapter_must_require_approval(self):
        """P0-1: HELD chapters must require human approval"""
        with pytest.raises(ValueError, match="HELD chapters must require human approval"):
            ChapterDecision(
                state=ChapterState.HELD,
                advance_to_next=False,
                blocking_issues=[],
                warnings=["high deviations"],
                human_approval_required=False,  # Contradiction!
                decision_provenance={}
            )

    def test_only_approved_finalized_reviewed_can_advance(self):
        """P0-1: Only APPROVED/FINALIZED/REVIEWED chapters can advance"""
        # REVIEWED can advance if it only has advisory warnings
        decision = ChapterDecision(
            state=ChapterState.REVIEWED,
            advance_to_next=True,
            blocking_issues=[],
            warnings=[],
            human_approval_required=False,
            decision_provenance={}
        )
        assert decision.state == ChapterState.REVIEWED

        # But HELD cannot advance
        with pytest.raises(ValueError, match="Only APPROVED/FINALIZED/REVIEWED chapters can advance"):
            ChapterDecision(
                state=ChapterState.HELD,
                advance_to_next=True,  # Contradiction!
                blocking_issues=[],
                warnings=["warning"],
                human_approval_required=True,
                decision_provenance={}
            )


class TestChapterDecisionMethods:
    """Test ChapterDecision helper methods"""

    def test_approved_chapter_can_advance(self):
        """P0-1: APPROVED chapters with advance_to_next=True can advance"""
        decision = ChapterDecision(
            state=ChapterState.APPROVED,
            advance_to_next=True,
            blocking_issues=[],
            warnings=[],
            human_approval_required=False,
            decision_provenance={}
        )

        assert decision.can_advance()
        assert not decision.requires_human_review()
        assert not decision.is_terminal()

    def test_blocked_chapter_is_terminal(self):
        """P0-1: BLOCKED chapters are terminal"""
        decision = ChapterDecision(
            state=ChapterState.BLOCKED,
            advance_to_next=False,
            blocking_issues=["redline failed"],
            warnings=[],
            human_approval_required=False,
            decision_provenance={}
        )

        assert not decision.can_advance()
        assert decision.is_terminal()

    def test_held_chapter_requires_approval(self):
        """P0-1: HELD chapters require human approval"""
        decision = ChapterDecision(
            state=ChapterState.HELD,
            advance_to_next=False,
            blocking_issues=[],
            warnings=["high deviations"],
            human_approval_required=True,
            decision_provenance={}
        )

        assert decision.requires_human_review()
        assert not decision.can_advance()
        assert not decision.is_terminal()

    def test_finalized_chapter_is_terminal(self):
        """P0-1: FINALIZED chapters are terminal"""
        decision = ChapterDecision(
            state=ChapterState.FINALIZED,
            advance_to_next=True,
            blocking_issues=[],
            warnings=[],
            human_approval_required=False,
            decision_provenance={}
        )

        assert decision.can_advance()  # Can still advance cursor past it
        assert decision.is_terminal()


class TestStateTransitions:
    """Test state transition validation"""

    def test_valid_transitions(self):
        """P0-1: Valid transitions are allowed"""
        # DRAFTED → REVIEWED
        assert StateTransition.is_valid(ChapterState.DRAFTED, ChapterState.REVIEWED)

        # REVIEWED → APPROVED
        assert StateTransition.is_valid(ChapterState.REVIEWED, ChapterState.APPROVED)

        # APPROVED → FINALIZED
        assert StateTransition.is_valid(ChapterState.APPROVED, ChapterState.FINALIZED)

    def test_invalid_transitions(self):
        """P0-1: Invalid transitions are rejected"""
        # BLOCKED is terminal - cannot transition anywhere
        assert not StateTransition.is_valid(ChapterState.BLOCKED, ChapterState.APPROVED)

        # FINALIZED is terminal - cannot transition anywhere
        assert not StateTransition.is_valid(ChapterState.FINALIZED, ChapterState.REVIEWED)

        # Cannot skip states arbitrarily
        assert not StateTransition.is_valid(ChapterState.DRAFTED, ChapterState.FINALIZED)

    def test_validate_raises_on_invalid(self):
        """P0-1: validate() raises on invalid transitions"""
        with pytest.raises(ValueError, match="Illegal state transition"):
            StateTransition.validate(ChapterState.BLOCKED, ChapterState.APPROVED)


class TestFactoryFunctions:
    """Test convenience factory functions"""

    def test_create_approved_decision(self):
        """P0-1: create_approved_decision produces valid APPROVED decision"""
        decision = create_approved_decision()

        assert decision.state == ChapterState.APPROVED
        assert decision.can_advance()
        assert not decision.blocking_issues
        assert not decision.requires_human_review()

    def test_create_blocked_decision(self):
        """P0-1: create_blocked_decision produces valid BLOCKED decision"""
        decision = create_blocked_decision("redline failed")

        assert decision.state == ChapterState.BLOCKED
        assert not decision.can_advance()
        assert "redline failed" in decision.blocking_issues
        assert decision.is_terminal()

    def test_create_held_decision(self):
        """P0-1: create_held_decision produces valid HELD decision"""
        decision = create_held_decision(["warning 1", "warning 2"])

        assert decision.state == ChapterState.HELD
        assert not decision.can_advance()
        assert decision.requires_human_review()
        assert len(decision.warnings) == 2


class TestDecisionEngineIntegration:
    """Test ProductionDecisionEngine produces valid ChapterDecisions"""

    def test_engine_produces_approved_on_clean_input(self):
        """P0-1: Engine produces APPROVED for clean chapters"""
        engine = ProductionDecisionEngine()

        decision = engine.decide_chapter_state(
            critical_deviations=0,
            high_deviations=0,
            redline_passed=True,
            final_quality_scores={},
            calibration_status=None,
        )

        assert decision.state == ChapterState.APPROVED
        assert decision.can_advance()

    def test_engine_produces_blocked_on_redline_failure(self):
        """P0-1: Engine produces BLOCKED for redline failures"""
        engine = ProductionDecisionEngine()

        decision = engine.decide_chapter_state(
            redline_passed=False,
        )

        assert decision.state == ChapterState.BLOCKED
        assert not decision.can_advance()
        assert any("redline" in issue.lower() for issue in decision.blocking_issues)

    def test_engine_produces_blocked_on_critical_contract(self):
        """P0-1: Engine produces BLOCKED for critical contract violations"""
        engine = ProductionDecisionEngine()

        decision = engine.decide_chapter_state(
            critical_deviations=2,
        )

        assert decision.state == ChapterState.BLOCKED
        assert not decision.can_advance()
        assert any("Critical contract" in issue for issue in decision.blocking_issues)

    def test_engine_produces_held_on_high_deviations(self):
        """P0-1: Engine produces HELD for high severity issues"""
        engine = ProductionDecisionEngine()

        decision = engine.decide_chapter_state(
            high_deviations=3,
        )

        assert decision.state == ChapterState.HELD
        assert not decision.can_advance()
        assert decision.requires_human_review()

    def test_engine_respects_calibration_for_gating(self):
        """P0-2: Engine only gates on calibrated dimensions"""
        engine = ProductionDecisionEngine()

        # Uncalibrated dimension below threshold - should only warn, not gate
        decision = engine.decide_chapter_state(
            final_quality_scores={"hook": 50},  # Below threshold of 75
            calibration_status={
                "decision_dimensions": [],  # Not calibrated
            }
        )

        assert decision.state == ChapterState.APPROVED  # Not held!
        assert decision.can_advance()
        assert any("uncalibrated" in w for w in decision.warnings)

    def test_engine_gates_on_calibrated_dimension(self):
        """P0-2: Engine gates on calibrated dimensions below threshold"""
        engine = ProductionDecisionEngine()

        # Calibrated dimension below threshold - should gate
        decision = engine.decide_chapter_state(
            final_quality_scores={"hook": 50},  # Below threshold of 75
            calibration_status={
                "decision_dimensions": ["hook"],  # Calibrated!
            }
        )

        assert decision.state == ChapterState.HELD
        assert not decision.can_advance()
        assert decision.requires_human_review()


class TestSerializationRoundTrip:
    """Test ChapterDecision serialization"""

    def test_to_dict_from_dict_roundtrip(self):
        """P0-1: ChapterDecision survives serialization roundtrip"""
        original = ChapterDecision(
            state=ChapterState.HELD,
            advance_to_next=False,
            blocking_issues=[],
            warnings=["warning 1", "warning 2"],
            human_approval_required=True,
            decision_provenance={"engine": "test", "version": "1.0"}
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ChapterDecision.from_dict(data)

        assert restored.state == original.state
        assert restored.advance_to_next == original.advance_to_next
        assert restored.warnings == original.warnings
        assert restored.can_advance() == original.can_advance()


class TestChapter100Artifact:
    """Test that chapter 100 artifact would pass P0-1 validation"""

    def test_chapter_100_decision_consistency(self):
        """P0-1: Real chapter 100 artifact structure (simulated)

        The actual artifact had contradictions. After P0-1, this pattern
        should be impossible to construct.
        """
        # The old contradictory state from the audit
        # overall_verdict: pass, publish_readiness: ready
        # BUT action: revise, advance: false, hold: true

        # The key contradiction was: ready + pass BUT also hold + revise
        # In our model: APPROVED state means ready, but advance_to_next=False means held
        # This is actually NOT contradictory if we interpret it as:
        # "Chapter quality is APPROVED, but we're holding it for human review"

        # The real contradiction is: action="revise" with verdict="pass"
        # If action is revise, state should be REVISION_REQUIRED, not APPROVED

        # So the actual contradiction to prevent is:
        # HELD state (action=hold) claiming to be APPROVED
        with pytest.raises(ValueError, match="Only APPROVED/FINALIZED/REVIEWED"):
            ChapterDecision(
                state=ChapterState.HELD,  # action=hold/revise
                advance_to_next=True,  # But claiming it can advance!
                blocking_issues=[],
                warnings=["some warning"],
                human_approval_required=True,
                decision_provenance={}
            )

    def test_correct_held_state_for_chapter_100(self):
        """P0-1: Chapter 100 should have been HELD, not APPROVED"""
        # Based on the audit: action=revise, hold=true, advance=false
        # This is correctly represented as HELD

        decision = ChapterDecision(
            state=ChapterState.HELD,
            advance_to_next=False,
            blocking_issues=[],
            warnings=["requires revision", "hold for review"],
            human_approval_required=True,
            decision_provenance={"source": "comparison_report"}
        )

        assert not decision.can_advance()
        assert decision.requires_human_review()
        assert decision.state == ChapterState.HELD


class TestLegacyCompatibility:
    """Test backward compatibility with old decide() method"""

    def test_legacy_decide_method_works(self):
        """P0-1: Legacy decide() method still works for backward compat"""
        engine = ProductionDecisionEngine()

        action, blocking, warnings = engine.decide(
            critical_deviations=0,
            redline_passed=True,
        )

        assert action == "publish"
        assert len(blocking) == 0

    def test_legacy_decide_maps_states_correctly(self):
        """P0-1: Legacy decide() maps new states to old actions"""
        engine = ProductionDecisionEngine()

        # BLOCKED → "block"
        action, _, _ = engine.decide(redline_passed=False)
        assert action == "block"

        # HELD → "hold"
        action, _, _ = engine.decide(high_deviations=1)
        assert action == "hold"

        # APPROVED → "publish"
        action, _, _ = engine.decide()
        assert action == "publish"
