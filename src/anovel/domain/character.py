"""
ANovelOS V2 Character Domain Model.

This module implements the Character aggregate with knowledge, goals, intents,
and planned actions. Follows BASE/DERIVED/CACHE semantics per ADR-002.

Public API:
    Types:
        Character, Goal, Intent, PlannedAction
        GoalStatus, ActionStatus, CharacterLifecycle

    Operations:
        create_character

Invariants:
    - Character uses EntityId from V2-005 for entity_id field
    - knowledge is dict[PropositionId, CharacterKnowledge]
    - CACHE fields (aligns_with_fact) not persisted
    - DERIVED fields (active_goals, knowledge_count) computed from BASE
    - PlannedAction.occurred_event_ref is reference, not occurrence authority

Contract: V2-061 Implementation Contract + ADR-002
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Mapping, Optional

from .identity import EntityId, ProjectId
from .knowledge import CharacterKnowledge, PropositionId

# --- Enums ---


class CharacterLifecycle(Enum):
    """Character lifecycle state."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DECEASED = "deceased"


class GoalStatus(Enum):
    """Goal pursuit status."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"


class ActionStatus(Enum):
    """Planned action status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --- Domain Models ---


@dataclass(frozen=True)
class Goal:
    """
    Character goal representation.

    BASE fields (all persisted):
        goal_id: Unique identifier
        character: Character who holds this goal
        description: Natural language goal description
        target_state: Desired outcome representation
        status: Goal pursuit status
        priority: Relative priority (higher = more important)
        formed_at: When goal was formed
        resolved_at: When goal was achieved/abandoned

    Contract: ADR-002 Goal BASE fields
    """

    goal_id: str
    character: EntityId
    description: str
    target_state: Optional[Mapping[str, str]]
    status: GoalStatus
    priority: int
    formed_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass(frozen=True)
class Intent:
    """
    Character intent representation.

    BASE fields (all persisted):
        intent_id: Unique identifier
        character: Character who holds this intent
        goal_ref: Reference to related goal
        description: Natural language intent description
        formed_at: When intent was formed
        abandoned_at: When intent was abandoned

    Contract: ADR-002 Intent BASE fields
    """

    intent_id: str
    character: EntityId
    goal_ref: Optional[str]
    description: str
    formed_at: datetime
    abandoned_at: Optional[datetime] = None


@dataclass(frozen=True)
class PlannedAction:
    """
    Planned action representation.

    BASE fields (all persisted):
        action_id: Unique identifier
        character: Character planning this action
        action_description: Natural language action description
        intent_ref: Reference to related intent
        planned_for: When action is planned to occur
        status: Action execution status
        occurred_event_ref: Reference to event if action occurred
        created_at: When action was planned
        cancelled_at: When action was cancelled

    Invariants:
        - occurred_event_ref is a reference/link, NOT occurrence authority
        - V2-007 owns occurrence truth, not PlannedAction

    Contract: ADR-002 PlannedAction BASE fields
    """

    action_id: str
    character: EntityId
    action_description: str
    intent_ref: Optional[str]
    planned_for: Optional[str]
    status: ActionStatus
    occurred_event_ref: Optional[str]
    created_at: datetime
    cancelled_at: Optional[datetime] = None


@dataclass(frozen=True)
class Character:
    """
    Character aggregate with knowledge, goals, intents, and planned actions.

    BASE fields (persisted):
        entity_id: Stable identifier from V2-005
        project_id: Project scope
        lifecycle: Character lifecycle state
        knowledge: Map of PropositionId to CharacterKnowledge
        goals: List of character goals
        intents: List of character intents
        planned_actions: List of planned actions
        created_at: Creation timestamp
        updated_at: Last update timestamp
        authority: Authority source for this character state
        provenance: Provenance information

    DERIVED fields (not persisted, computed from BASE):
        active_goals: Filtered list of goals with status=ACTIVE
        knowledge_count: Count of knowledge entries

    Invariants:
        - entity_id from V2-005 (reused, not redesigned)
        - knowledge values contain CACHE field aligns_with_fact (not persisted)
        - DERIVED fields recomputed after deserialization

    Contract: ADR-002 Character BASE/DERIVED classification
    """

    # BASE fields
    entity_id: EntityId
    project_id: ProjectId
    lifecycle: CharacterLifecycle
    knowledge: Dict[PropositionId, CharacterKnowledge]
    goals: List[Goal]
    intents: List[Intent]
    planned_actions: List[PlannedAction]
    created_at: datetime
    updated_at: datetime
    authority: str
    provenance: Optional[str] = None

    @property
    def active_goals(self) -> List[Goal]:
        """
        DERIVED: Filter goals with status=ACTIVE.

        Not persisted. Recomputed from BASE goals field.

        Returns:
            List of goals with status=ACTIVE
        """
        return [g for g in self.goals if g.status == GoalStatus.ACTIVE]

    @property
    def knowledge_count(self) -> int:
        """
        DERIVED: Count of knowledge entries.

        Not persisted. Recomputed from BASE knowledge field.

        Returns:
            Number of knowledge entries
        """
        return len(self.knowledge)


def create_character(
    project_id: ProjectId,
    canonical_name: str,
    entity_type: str = "CHARACTER",
    authority: str = "initial_state",
) -> Character:
    """
    Create a new character with stable identity.

    Generates entity identity via V2-005 and creates Character with empty
    knowledge, goals, intents, and planned actions.

    Args:
        project_id: Project scope
        canonical_name: Character canonical name
        entity_type: Entity type (defaults to "CHARACTER")
        authority: Authority source for this character

    Returns:
        Character with fresh entity_id and empty collections

    Raises:
        ValueError: If project_id or canonical_name invalid

    Example:
        >>> char = create_character(
        ...     ProjectId("proj_01"),
        ...     "张三",
        ...     authority="initial_state"
        ... )
        >>> char.lifecycle
        <CharacterLifecycle.ACTIVE: 'active'>

    Contract: V2-061 + ADR-002
    """
    from .identity import create_identity

    # Create stable entity identity via V2-005
    identity = create_identity(
        project_id=project_id,
        canonical_name=canonical_name,
        entity_type=entity_type,
    )

    now = datetime.utcnow()

    return Character(
        entity_id=identity.entity_id,
        project_id=project_id,
        lifecycle=CharacterLifecycle.ACTIVE,
        knowledge={},
        goals=[],
        intents=[],
        planned_actions=[],
        created_at=now,
        updated_at=now,
        authority=authority,
        provenance=None,
    )
