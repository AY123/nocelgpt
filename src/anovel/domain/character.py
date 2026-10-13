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

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NewType

from .identity import EntityId, EntityRegistry, ProjectId
from .knowledge import CharacterKnowledge, PropositionId

# --- Type Aliases ---

GoalId = NewType("GoalId", str)
"""Stable identifier for character goals (UUID v4 format)."""

IntentId = NewType("IntentId", str)
"""Stable identifier for character intents (UUID v4 format)."""

PlannedActionId = NewType("PlannedActionId", str)
"""Stable identifier for planned actions (UUID v4 format)."""

# --- Enums ---


class CharacterLifecycle(Enum):
    """Character lifecycle state.

    Contract: Frozen V2-061 §Lifecycle

    PLANNED: Defined but not yet active in story
    ACTIVE: Currently part of story
    INACTIVE: Temporarily not appearing (still alive/existing)
    DECEASED: Character has died in story
    SUPERSEDED: Character concept replaced/merged
    """

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECEASED = "DECEASED"
    SUPERSEDED = "SUPERSEDED"


class GoalStatus(Enum):
    """Goal pursuit status.

    Contract: Frozen V2-061 §Goal Lifecycle (AC-4)
    """

    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    ACHIEVED = "ACHIEVED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    SUPERSEDED = "SUPERSEDED"


class ActionStatus(Enum):
    """Planned action status.

    Contract: Frozen V2-061 §PlannedAction Occurrence Invariant (AC-3)

    V2-061 owns PLANNED/CANCELLED only.
    V2-007 owns objective occurrence authority.
    """

    PLANNED = "PLANNED"
    CANCELLED = "CANCELLED"


# --- Domain Models ---


@dataclass(frozen=True)
class Goal:
    """
    Character goal representation.

    BASE fields (all persisted):
        goal_id: Unique stable identifier (UUID v4)
        character: Character who holds this goal
        description: Natural language goal description
        target_state: Desired outcome representation
        status: Goal pursuit status
        priority: Relative priority (higher = more important)
        formed_at: When goal was formed
        resolved_at: When goal was achieved/abandoned

    Invariants:
        - goal_id must be valid UUID v4 format

    Contract: ADR-002 Goal BASE fields + Frozen V2-061 §Goal Lifecycle (AC-4)
    """

    goal_id: GoalId
    character: EntityId
    description: str
    target_state: Mapping[str, str] | None
    status: GoalStatus
    priority: int | None
    formed_at: datetime | None
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate Goal invariants.

        Contract: Frozen V2-061 §GoalId UUID v4 format
        """
        from .knowledge import validate_uuid_v4_format

        validate_uuid_v4_format(self.goal_id, "goal_id")


@dataclass(frozen=True)
class Intent:
    """
    Character intent representation.

    BASE fields (all persisted):
        intent_id: Unique stable identifier (UUID v4)
        character: Character who holds this intent
        goal_ref: Reference to related goal
        description: Natural language intent description
        formed_at: When intent was formed
        abandoned_at: When intent was abandoned

    Invariants:
        - intent_id must be valid UUID v4 format

    Contract: ADR-002 Intent BASE fields + Frozen V2-061 §Intent
    """

    intent_id: IntentId
    character: EntityId
    goal_ref: GoalId | None
    description: str
    formed_at: datetime | None
    abandoned_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate Intent invariants.

        Contract: Frozen V2-061 §IntentId UUID v4 format
        """
        from .knowledge import validate_uuid_v4_format

        validate_uuid_v4_format(self.intent_id, "intent_id")


@dataclass(frozen=True)
class PlannedAction:
    """
    Planned action representation.

    BASE fields (all persisted):
        action_id: Unique stable identifier (UUID v4)
        character: Character planning this action
        action_description: Natural language action description
        intent_ref: Reference to related intent
        planned_for: When action is planned to occur
        status: Action status (PLANNED or CANCELLED only - V2-061 authority)
        occurred_event_ref: Reference to event if action occurred
        created_at: When action was planned
        cancelled_at: When action was cancelled

    Invariants:
        - action_id must be valid UUID v4 format
        - occurred_event_ref is a reference/link, NOT occurrence authority
        - V2-007 owns occurrence truth, not PlannedAction
        - status can only be PLANNED or CANCELLED (no IN_PROGRESS/COMPLETED)
        - status=CANCELLED + occurred_event_ref != None is INVALID

    Contract: ADR-002 PlannedAction BASE fields + Frozen V2-061 §PlannedAction Occurrence Invariant (AC-3)
    """

    action_id: PlannedActionId
    character: EntityId
    action_description: str
    intent_ref: IntentId | None
    planned_for: str | None
    status: ActionStatus
    occurred_event_ref: str | None
    created_at: datetime
    cancelled_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate PlannedAction invariants.

        Contract: Frozen V2-061 §PlannedAction Occurrence Invariant + §PlannedActionId UUID v4 format
        """
        # Validate UUID v4 format
        from .knowledge import validate_uuid_v4_format

        validate_uuid_v4_format(self.action_id, "action_id")

        # CANCELLED + occurred_event_ref != None is invalid
        if (
            self.status == ActionStatus.CANCELLED
            and self.occurred_event_ref is not None
        ):
            raise ValueError(
                "PlannedAction with status=CANCELLED cannot have occurred_event_ref. "
                "Cancelled plans should not link to occurrence events."
            )


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
        provenance: Structured provenance metadata (dict)

    DERIVED fields (not persisted, computed from BASE):
        active_goals: Filtered list of goals with status=ACTIVE
        knowledge_count: Count of knowledge entries

    Invariants:
        - entity_id from V2-005 (reused, not redesigned)
        - knowledge values contain CACHE field aligns_with_fact (not persisted)
        - DERIVED fields recomputed after deserialization
        - provenance is dict[str, str] per frozen Contract line 206

    Contract: ADR-002 Character BASE/DERIVED classification + Frozen V2-061 §Character
    """

    # BASE fields
    entity_id: EntityId
    project_id: ProjectId
    lifecycle: CharacterLifecycle
    knowledge: dict[PropositionId, CharacterKnowledge]
    goals: list[Goal]
    intents: list[Intent]
    planned_actions: list[PlannedAction]
    created_at: datetime
    updated_at: datetime
    authority: str
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def active_goals(self) -> list[Goal]:
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


def validate_knowledge_key_invariant(character: Character) -> None:
    """
    Validate that Character.knowledge dict keys match proposition IDs.

    Frozen Contract §CharacterKnowledge requires:
    dict key == CharacterKnowledge.proposition.proposition_id

    Args:
        character: Character to validate

    Raises:
        ValueError: If key doesn't match embedded proposition_id

    Contract: Frozen V2-061 §Proposition Resolution
    """
    for key, ck in character.knowledge.items():
        if key != ck.proposition.proposition_id:
            raise ValueError(
                f"Character.knowledge key ({key}) must match "
                f"CharacterKnowledge.proposition.proposition_id "
                f"({ck.proposition.proposition_id})"
            )


def validate_project_isolation(
    character: Character,
    entity_registry: EntityRegistry,
) -> None:
    """
    Validate that Character respects project isolation boundaries.

    Frozen Contract §Project Isolation requires:
    - Character.project_id matches EntityIdentity.project_id
    - Entity exists in registry
    - Entity entity_type == "CHARACTER"
    - All knowledge provenance respects project boundaries

    Args:
        character: Character to validate
        entity_registry: V2-005 EntityRegistry for identity lookup

    Raises:
        ValueError: If project isolation violated

    Contract: Frozen V2-061 §Project Isolation
    """

    # Validate character entity exists
    identity = entity_registry.get_entity(character.entity_id)
    if identity is None:
        raise ValueError(
            f"Character entity_id {character.entity_id} not found in EntityRegistry"
        )

    # Validate project_id matches
    if identity.project_id != character.project_id:
        raise ValueError(
            f"Character.project_id ({character.project_id}) must match "
            f"EntityIdentity.project_id ({identity.project_id})"
        )

    # Validate entity_type is CHARACTER
    if identity.entity_type != "CHARACTER":
        raise ValueError(
            f"Character entity must have entity_type='CHARACTER', "
            f"got '{identity.entity_type}' for {character.entity_id}"
        )

    # Validate all knowledge provenance respects project boundaries
    for _prop_id, ck in character.knowledge.items():
        # Knower must be same character (implicitly same project)
        if ck.knower != character.entity_id:
            raise ValueError(
                f"CharacterKnowledge.knower ({ck.knower}) must match "
                f"Character.entity_id ({character.entity_id})"
            )

        # Source character must be same project if present
        if ck.source_character is not None:
            source_identity = entity_registry.get_entity(ck.source_character)
            if source_identity is None:
                raise ValueError(
                    f"source_character {ck.source_character} not found in EntityRegistry"
                )
            if source_identity.project_id != character.project_id:
                raise ValueError(
                    f"source_character {ck.source_character} belongs to project "
                    f"{source_identity.project_id}, but character belongs to "
                    f"{character.project_id}. Cross-project provenance invalid."
                )

        # Proposition subject/object must be same project if EntityId
        prop = ck.proposition
        if prop.project_id != character.project_id:
            raise ValueError(
                f"Proposition.project_id ({prop.project_id}) must match "
                f"Character.project_id ({character.project_id})"
            )

        # Validate subject if it's a registered EntityId reference
        # Note: EntityId is NewType, not runtime class - use registry lookup instead
        subj_identity = entity_registry.get_entity(prop.subject)
        if subj_identity is not None:  # If found in registry, must be same project
            if subj_identity.project_id != character.project_id:
                raise ValueError(
                    f"Proposition subject {prop.subject} belongs to project "
                    f"{subj_identity.project_id}, but character belongs to "
                    f"{character.project_id}. Cross-project references invalid."
                )

        # Validate object if it's a registered EntityId reference
        if isinstance(prop.object, str):
            try:
                obj_id = EntityId(prop.object)
                obj_identity = entity_registry.get_entity(obj_id)
            except (ValueError, TypeError):
                obj_identity = None
        elif prop.object is not None:
            obj_identity = entity_registry.get_entity(prop.object)
        else:
            obj_identity = None
        if obj_identity is not None:  # If found in registry, must be same project
            if obj_identity.project_id != character.project_id:
                raise ValueError(
                    f"Proposition object {prop.object} belongs to project "
                    f"{obj_identity.project_id}, but character belongs to "
                    f"{character.project_id}. Cross-project references invalid."
                )


def create_character(
    project_id: ProjectId,
    canonical_name: str,
    authority: str = "initial_state",
) -> Character:
    """
    Create a new character with stable identity.

    Generates entity identity via V2-005 and creates Character with empty
    knowledge, goals, intents, and planned actions.

    Args:
        project_id: Project scope
        canonical_name: Character canonical name
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
        <CharacterLifecycle.ACTIVE: 'ACTIVE'>

    Contract: V2-061 + ADR-002 + Frozen V2-061 §Entity Type Validation

    Note: entity_type is hardcoded to "CHARACTER" per contract requirement.
    V2-061 only handles CHARACTER entity_type. Other types must be rejected.
    """
    from .identity import create_identity

    # Create stable entity identity via V2-005
    # entity_type must be "CHARACTER" per frozen contract
    identity = create_identity(
        project_id=project_id,
        canonical_name=canonical_name,
        entity_type="CHARACTER",
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
        provenance={},
    )
