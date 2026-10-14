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
# V2-061 Character
from .character import (
    ActionStatus,
    Character,
    CharacterLifecycle,
    Goal,
    GoalId,
    GoalStatus,
    Intent,
    IntentId,
    PlannedAction,
    PlannedActionId,
    create_character,
)
from .identity import (
    EntityId,
    EntityIdentity,
    EntityRegistry,
    ProjectId,
    ResolutionResult,
    ResolutionStatus,
    add_alias,
    create_identity,
    normalize_for_lookup,
    remove_alias,
    rename_identity,
    resolve_alias,
)

# V2-061 Character Knowledge
from .knowledge import (
    AcquisitionSource,
    CharacterKnowledge,
    KnowledgeLevel,
    Proposition,
    PropositionId,
    create_proposition,
    freeze_context,
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
