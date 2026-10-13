"""
V2-061 Lifecycle and Goal Transition Tests.

Tests lifecycle semantics and goal status transitions per frozen Contract:
- DECEASED cannot form goals/intents by default
- PLANNED cannot acquire story-event knowledge
- Lifecycle transitions (DECEASED→ACTIVE invalid by default)
- Goal status transitions (terminal states cannot reactivate)

Contract Authority: Frozen V2-061 §Lifecycle Semantics + §Goal Lifecycle
"""

import uuid
from datetime import datetime

import pytest

from src.anovel.domain import (
    Character,
    CharacterKnowledge,
    CharacterLifecycle,
    Goal,
    GoalId,
    GoalStatus,
    Intent,
    IntentId,
    KnowledgeLevel,
    AcquisitionSource,
    create_character,
    create_proposition,
)
from src.anovel.domain.identity import EntityId, ProjectId
from src.anovel.domain.lifecycle import (
    validate_goal_formation,
    validate_intent_formation,
    validate_knowledge_acquisition,
    validate_lifecycle_transition,
    validate_goal_transition,
    transition_goal,
)


class TestLifecycleConstraints:
    """Character lifecycle behavioral constraints."""

    def test_deceased_cannot_form_goal_by_default(self):
        """DECEASED character cannot form new goals by default."""
        with pytest.raises(ValueError, match="DECEASED character cannot form new goals"):
            validate_goal_formation(CharacterLifecycle.DECEASED)

    def test_deceased_can_form_goal_with_override(self):
        """DECEASED character can form goals with genre override."""
        # Should not raise
        validate_goal_formation(CharacterLifecycle.DECEASED, allow_deceased=True)

    def test_active_can_form_goal(self):
        """ACTIVE character can form goals."""
        # Should not raise
        validate_goal_formation(CharacterLifecycle.ACTIVE)

    def test_deceased_cannot_form_intent_by_default(self):
        """DECEASED character cannot form new intents by default."""
        with pytest.raises(ValueError, match="DECEASED character cannot form new intents"):
            validate_intent_formation(CharacterLifecycle.DECEASED)

    def test_deceased_can_form_intent_with_override(self):
        """DECEASED character can form intents with genre override."""
        # Should not raise
        validate_intent_formation(CharacterLifecycle.DECEASED, allow_deceased=True)

    def test_planned_cannot_acquire_story_knowledge_by_default(self):
        """PLANNED character cannot have knowledge of story events by default."""
        with pytest.raises(ValueError, match="PLANNED character cannot have knowledge of story events"):
            validate_knowledge_acquisition(
                CharacterLifecycle.PLANNED,
                is_story_event=True,
            )

    def test_planned_can_acquire_background_knowledge(self):
        """PLANNED character can have background/setup knowledge."""
        # Should not raise
        validate_knowledge_acquisition(
            CharacterLifecycle.PLANNED,
            is_story_event=False,
        )

    def test_planned_can_acquire_story_knowledge_with_override(self):
        """PLANNED character can have story knowledge with genre override."""
        # Should not raise
        validate_knowledge_acquisition(
            CharacterLifecycle.PLANNED,
            is_story_event=True,
            allow_planned=True,
        )

    def test_active_can_acquire_story_knowledge(self):
        """ACTIVE character can acquire story-event knowledge."""
        # Should not raise
        validate_knowledge_acquisition(
            CharacterLifecycle.ACTIVE,
            is_story_event=True,
        )


class TestLifecycleTransitions:
    """Lifecycle state transition validation."""

    def test_planned_to_active_valid(self):
        """PLANNED → ACTIVE transition is valid."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.PLANNED,
            CharacterLifecycle.ACTIVE,
        )

    def test_active_to_deceased_valid(self):
        """ACTIVE → DECEASED transition is valid."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.ACTIVE,
            CharacterLifecycle.DECEASED,
        )

    def test_active_to_inactive_valid(self):
        """ACTIVE → INACTIVE transition is valid."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.ACTIVE,
            CharacterLifecycle.INACTIVE,
        )

    def test_inactive_to_active_valid(self):
        """INACTIVE → ACTIVE transition is valid."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.INACTIVE,
            CharacterLifecycle.ACTIVE,
        )

    def test_deceased_to_active_invalid_by_default(self):
        """DECEASED → ACTIVE transition invalid by default (no resurrection)."""
        with pytest.raises(ValueError, match="DECEASED → ACTIVE transition not allowed"):
            validate_lifecycle_transition(
                CharacterLifecycle.DECEASED,
                CharacterLifecycle.ACTIVE,
            )

    def test_deceased_to_active_valid_with_override(self):
        """DECEASED → ACTIVE transition valid with genre override."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.DECEASED,
            CharacterLifecycle.ACTIVE,
            allow_resurrection=True,
        )

    def test_same_state_transition_valid(self):
        """Same state transition is valid (no-op)."""
        # Should not raise
        validate_lifecycle_transition(
            CharacterLifecycle.ACTIVE,
            CharacterLifecycle.ACTIVE,
        )


class TestGoalTransitions:
    """Goal status transition validation."""

    def test_active_to_achieved_valid(self):
        """ACTIVE → ACHIEVED transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.ACTIVE, GoalStatus.ACHIEVED)

    def test_active_to_failed_valid(self):
        """ACTIVE → FAILED transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.ACTIVE, GoalStatus.FAILED)

    def test_active_to_abandoned_valid(self):
        """ACTIVE → ABANDONED transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.ACTIVE, GoalStatus.ABANDONED)

    def test_active_to_blocked_valid(self):
        """ACTIVE → BLOCKED transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.ACTIVE, GoalStatus.BLOCKED)

    def test_blocked_to_active_valid(self):
        """BLOCKED → ACTIVE transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.BLOCKED, GoalStatus.ACTIVE)

    def test_blocked_to_failed_valid(self):
        """BLOCKED → FAILED transition is valid."""
        # Should not raise
        validate_goal_transition(GoalStatus.BLOCKED, GoalStatus.FAILED)

    def test_achieved_to_active_invalid(self):
        """ACHIEVED → ACTIVE transition is invalid (terminal state)."""
        with pytest.raises(ValueError, match="Terminal goal states cannot reactivate"):
            validate_goal_transition(GoalStatus.ACHIEVED, GoalStatus.ACTIVE)

    def test_failed_to_active_invalid(self):
        """FAILED → ACTIVE transition is invalid (terminal state)."""
        with pytest.raises(ValueError, match="Terminal goal states cannot reactivate"):
            validate_goal_transition(GoalStatus.FAILED, GoalStatus.ACTIVE)

    def test_abandoned_to_active_invalid(self):
        """ABANDONED → ACTIVE transition is invalid (terminal state)."""
        with pytest.raises(ValueError, match="Terminal goal states cannot reactivate"):
            validate_goal_transition(GoalStatus.ABANDONED, GoalStatus.ACTIVE)

    def test_superseded_to_any_invalid(self):
        """SUPERSEDED → * transition is invalid (terminal state)."""
        with pytest.raises(ValueError, match="Terminal goal states cannot reactivate"):
            validate_goal_transition(GoalStatus.SUPERSEDED, GoalStatus.ACTIVE)

        with pytest.raises(ValueError, match="SUPERSEDED is terminal state"):
            validate_goal_transition(GoalStatus.SUPERSEDED, GoalStatus.FAILED)

    def test_same_status_transition_valid(self):
        """Same status transition is valid (no-op)."""
        # Should not raise
        validate_goal_transition(GoalStatus.ACTIVE, GoalStatus.ACTIVE)

    def test_transition_goal_sets_resolved_at(self):
        """transition_goal sets resolved_at for terminal states."""
        goal = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=EntityId("char-123"),
            description="Find artifact",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
            resolved_at=None,
        )

        goal2 = transition_goal(goal, GoalStatus.ACHIEVED)

        assert goal2.status == GoalStatus.ACHIEVED
        assert goal2.resolved_at is not None
        assert goal2.goal_id == goal.goal_id

    def test_transition_goal_validates(self):
        """transition_goal validates transition before applying."""
        goal = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=EntityId("char-123"),
            description="Find artifact",
            target_state=None,
            status=GoalStatus.ACHIEVED,
            priority=10,
            formed_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="Terminal goal states cannot reactivate"):
            transition_goal(goal, GoalStatus.ACTIVE)
