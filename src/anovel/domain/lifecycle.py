"""
Character lifecycle semantics and goal transition validation.

Implements behavioral constraints per frozen V2-061 Contract:
- DECEASED characters cannot form new goals/intents by default
- PLANNED characters cannot acquire story-event knowledge
- Goal status transitions with validity rules
- Lifecycle transition validation

These are default rules; genre extensions may override per Contract lines 949-950.

Contract: Frozen V2-061 §Lifecycle Semantics + §Goal Lifecycle
"""

from __future__ import annotations

from .character import CharacterLifecycle, Goal, GoalStatus


def validate_goal_formation(
    lifecycle: CharacterLifecycle,
    allow_deceased: bool = False,
) -> None:
    """
    Validate whether character can form new goals given lifecycle state.

    Default rules (Contract line 929):
    - DECEASED: cannot form goals by default
    - Other states: allowed

    Args:
        lifecycle: Character lifecycle state
        allow_deceased: Override to allow DECEASED goal formation (genre extension)

    Raises:
        ValueError: If lifecycle state prevents goal formation

    Contract: Frozen V2-061 §Lifecycle Semantics line 929
    """
    if lifecycle == CharacterLifecycle.DECEASED and not allow_deceased:
        raise ValueError(
            "DECEASED character cannot form new goals by default. "
            "Genre extensions may override with allow_deceased=True."
        )


def validate_intent_formation(
    lifecycle: CharacterLifecycle,
    allow_deceased: bool = False,
) -> None:
    """
    Validate whether character can form new intents given lifecycle state.

    Default rules (Contract line 929):
    - DECEASED: cannot form intents by default
    - Other states: allowed

    Args:
        lifecycle: Character lifecycle state
        allow_deceased: Override to allow DECEASED intent formation (genre extension)

    Raises:
        ValueError: If lifecycle state prevents intent formation

    Contract: Frozen V2-061 §Lifecycle Semantics line 929
    """
    if lifecycle == CharacterLifecycle.DECEASED and not allow_deceased:
        raise ValueError(
            "DECEASED character cannot form new intents by default. "
            "Genre extensions may override with allow_deceased=True."
        )


def validate_knowledge_acquisition(
    lifecycle: CharacterLifecycle,
    is_story_event: bool,
    allow_planned: bool = False,
) -> None:
    """
    Validate whether character can acquire knowledge given lifecycle state.

    Default rules (Contract line 930):
    - PLANNED: cannot have knowledge of story events (not yet in story)
    - Other states: allowed

    Args:
        lifecycle: Character lifecycle state
        is_story_event: Whether knowledge is about story events (vs background/setup)
        allow_planned: Override to allow PLANNED story knowledge (genre extension)

    Raises:
        ValueError: If lifecycle state prevents knowledge acquisition

    Contract: Frozen V2-061 §Lifecycle Semantics line 930
    """
    if lifecycle == CharacterLifecycle.PLANNED and is_story_event and not allow_planned:
        raise ValueError(
            "PLANNED character cannot have knowledge of story events by default. "
            "Background/setup knowledge allowed. "
            "Genre extensions may override with allow_planned=True."
        )


def validate_lifecycle_transition(
    from_state: CharacterLifecycle,
    to_state: CharacterLifecycle,
    allow_resurrection: bool = False,
) -> None:
    """
    Validate lifecycle state transition.

    Default valid transitions (Contract lines 943-947):
    - PLANNED → ACTIVE (character enters story)
    - ACTIVE → INACTIVE
    - ACTIVE → DECEASED (character dies)
    - INACTIVE → ACTIVE
    - DECEASED → ACTIVE (NOT allowed by default, requires allow_resurrection)

    Args:
        from_state: Current lifecycle state
        to_state: Target lifecycle state
        allow_resurrection: Override to allow DECEASED→ACTIVE (genre extension)

    Raises:
        ValueError: If transition is invalid

    Contract: Frozen V2-061 §Lifecycle Semantics lines 943-947
    """
    # Same state is always valid (no-op)
    if from_state == to_state:
        return

    # DECEASED → ACTIVE requires explicit genre override
    if (
        from_state == CharacterLifecycle.DECEASED
        and to_state == CharacterLifecycle.ACTIVE
    ):
        if not allow_resurrection:
            raise ValueError(
                "DECEASED → ACTIVE transition not allowed by default. "
                "Genre extensions may override with allow_resurrection=True."
            )
        return

    # All other transitions are valid by default
    # Genre may add additional constraints


def validate_goal_transition(
    from_status: GoalStatus,
    to_status: GoalStatus,
) -> None:
    """
    Validate goal status transition.

    Valid transitions per frozen Contract:
    - ACTIVE → ACHIEVED (goal accomplished)
    - ACTIVE → FAILED (goal cannot be achieved)
    - ACTIVE → ABANDONED (character gives up)
    - ACTIVE → BLOCKED (obstacle encountered)
    - BLOCKED → ACTIVE (obstacle removed)
    - BLOCKED → FAILED (obstacle insurmountable)
    - BLOCKED → ABANDONED (character gives up while blocked)

    Invalid transitions:
    - ACHIEVED → ACTIVE (cannot reactivate achieved goal)
    - FAILED → ACTIVE (cannot reactivate failed goal)
    - ABANDONED → ACTIVE (cannot reactivate abandoned goal)
    - SUPERSEDED → * (terminal state, goal replaced by another)

    Args:
        from_status: Current goal status
        to_status: Target goal status

    Raises:
        ValueError: If transition is invalid

    Contract: Frozen V2-061 §Goal Lifecycle + ADR-002
    """
    # Same status is always valid (no-op)
    if from_status == to_status:
        return

    # Define invalid transitions (terminal states cannot reactivate)
    terminal_states = {
        GoalStatus.ACHIEVED,
        GoalStatus.FAILED,
        GoalStatus.ABANDONED,
        GoalStatus.SUPERSEDED,
    }

    if from_status in terminal_states and to_status == GoalStatus.ACTIVE:
        raise ValueError(
            f"Goal status transition {from_status.value} → {to_status.value} is INVALID. "
            f"Terminal goal states cannot reactivate."
        )

    if from_status in terminal_states and to_status == GoalStatus.BLOCKED:
        raise ValueError(
            f"Goal status transition {from_status.value} → {to_status.value} is INVALID. "
            f"Terminal goal states cannot be blocked."
        )

    if from_status == GoalStatus.SUPERSEDED:
        raise ValueError(
            "Goal status transition from SUPERSEDED is INVALID. "
            "SUPERSEDED is terminal state (goal replaced by another)."
        )

    # All other transitions are valid


def transition_goal(goal: Goal, new_status: GoalStatus) -> Goal:
    """
    Create new Goal with transitioned status after validation.

    Args:
        goal: Current goal
        new_status: Target status

    Returns:
        New Goal with updated status

    Raises:
        ValueError: If transition is invalid

    Contract: Frozen V2-061 §Goal Lifecycle
    """
    validate_goal_transition(goal.status, new_status)

    from dataclasses import replace
    from datetime import datetime

    # Update resolved_at for terminal states
    if new_status in {
        GoalStatus.ACHIEVED,
        GoalStatus.FAILED,
        GoalStatus.ABANDONED,
        GoalStatus.SUPERSEDED,
    }:
        if goal.resolved_at is None:
            return replace(goal, status=new_status, resolved_at=datetime.utcnow())

    return replace(goal, status=new_status)
