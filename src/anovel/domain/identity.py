"""
ANovelOS V2 Entity Identity and Alias Resolution.

This module provides the foundational identity layer for narrative entities.
Entity identity is stable and independent from display names. Alias resolution
is project-scoped and fails explicitly on ambiguity.

Public API:
    Types:
        EntityId, ProjectId, EntityIdentity, ResolutionResult
    Operations:
        create_identity, rename_identity, add_alias, remove_alias, resolve_alias

Invariants:
    - Entity ID never changes (stable across rename)
    - Project isolation (no cross-project resolution)
    - Explicit ambiguity (no random selection)
    - Deterministic resolution

Contract: V2-005 Implementation Contract v1.1.0
Authority: docs/V2-005_IMPLEMENTATION_CONTRACT.md
Baseline: 4248258339fa1c90df1c9e34572df24abe13330d
"""

from dataclasses import dataclass
from enum import Enum
from typing import NewType, Union

# --- Type Aliases (Step 2) ---

EntityId = NewType("EntityId", str)
"""Opaque stable identifier for narrative entities (UUID v4 format)."""

ProjectId = NewType("ProjectId", str)
"""Project scope boundary for entity resolution."""


# --- Enums (Step 2) ---


class ResolutionStatus(Enum):
    """Status of alias resolution attempt."""

    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    INVALID_INPUT = "invalid_input"


# --- Domain Models (Step 2) ---


@dataclass(frozen=True)
class EntityIdentity:
    """
    Immutable identity aggregate for narrative entities.

    Attributes:
        entity_id: Stable unique identifier (never changes)
        project_id: Project scope for this entity
        canonical_name: Primary display name
        aliases: Additional names for lookup (immutable set)
        entity_type: Optional entity classification (e.g., 'CHARACTER', 'LOCATION')
    """

    entity_id: EntityId
    project_id: ProjectId
    canonical_name: str
    aliases: frozenset[str]
    entity_type: str | None = None


@dataclass(frozen=True)
class ResolvedResult:
    """
    Successful alias resolution result.

    Attributes:
        status: Always ResolutionStatus.RESOLVED
        identity: The resolved entity identity
    """

    status: ResolutionStatus
    identity: EntityIdentity


@dataclass(frozen=True)
class NotFoundResult:
    """
    Alias not found result.

    Attributes:
        status: Always ResolutionStatus.NOT_FOUND
        alias: The alias that was not found
    """

    status: ResolutionStatus
    alias: str


@dataclass(frozen=True)
class AmbiguousResult:
    """
    Ambiguous alias resolution result (multiple matches).

    Attributes:
        status: Always ResolutionStatus.AMBIGUOUS
        alias: The ambiguous alias
        candidates: Entity IDs of all matching entities
    """

    status: ResolutionStatus
    alias: str
    candidates: frozenset[EntityId]


@dataclass(frozen=True)
class InvalidInputResult:
    """
    Invalid input result (e.g., empty alias after normalization).

    Attributes:
        status: Always ResolutionStatus.INVALID_INPUT
        reason: Human-readable explanation of why input is invalid
    """

    status: ResolutionStatus
    reason: str


# --- Resolution Result Union (Step 2) ---

ResolutionResult = (
    ResolvedResult | NotFoundResult | AmbiguousResult | InvalidInputResult
)
"""
Union of all possible resolution results.

Discriminated by the 'status' field.
"""

# Functions will be defined in Step 3+
