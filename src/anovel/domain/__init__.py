"""
ANovelOS V2 Domain Layer.

This package contains the core domain models and business logic for narrative
generation and management.

Public submodules:
    identity: Entity identity and alias resolution
    knowledge: Character knowledge and propositions
    character: Character aggregate with knowledge, goals, and intents
"""

# V2-005 Entity Identity
from .identity import (
    EntityId,
    ProjectId,
    EntityIdentity,
    ResolutionResult,
    ResolutionStatus,
    create_identity,
    rename_identity,
    add_alias,
    remove_alias,
    resolve_alias,
    normalize_for_lookup,
    EntityRegistry,
)

# V2-061 Character Knowledge
from .knowledge import (
    PropositionId,
    Proposition,
    CharacterKnowledge,
    KnowledgeLevel,
    AcquisitionSource,
    create_proposition,
    freeze_context,
)

# V2-061 Character
from .character import (
    Character,
    Goal,
    Intent,
    PlannedAction,
    CharacterLifecycle,
    GoalStatus,
    ActionStatus,
    GoalId,
    IntentId,
    PlannedActionId,
    create_character,
)

__all__ = [
    # V2-005
    "EntityId",
    "ProjectId",
    "EntityIdentity",
    "ResolutionResult",
    "ResolutionStatus",
    "create_identity",
    "rename_identity",
    "add_alias",
    "remove_alias",
    "resolve_alias",
    "normalize_for_lookup",
    "EntityRegistry",
    # V2-061 Knowledge
    "PropositionId",
    "Proposition",
    "CharacterKnowledge",
    "KnowledgeLevel",
    "AcquisitionSource",
    "create_proposition",
    "freeze_context",
    # V2-061 Character
    "Character",
    "Goal",
    "Intent",
    "PlannedAction",
    "CharacterLifecycle",
    "GoalStatus",
    "ActionStatus",
    "GoalId",
    "IntentId",
    "PlannedActionId",
    "create_character",
]
