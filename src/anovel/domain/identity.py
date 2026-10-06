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
from typing import Literal, NewType

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
        entity_id: The resolved entity identifier
    """

    status: Literal[ResolutionStatus.RESOLVED]
    entity_id: EntityId


@dataclass(frozen=True)
class NotFoundResult:
    """
    Alias not found result.

    Attributes:
        status: Always ResolutionStatus.NOT_FOUND
    """

    status: Literal[ResolutionStatus.NOT_FOUND]


@dataclass(frozen=True)
class AmbiguousResult:
    """
    Ambiguous alias resolution result (multiple matches).

    Attributes:
        status: Always ResolutionStatus.AMBIGUOUS
        candidates: Entity IDs of all matching entities (unordered, ≥2)
    """

    status: Literal[ResolutionStatus.AMBIGUOUS]
    candidates: frozenset[EntityId]


@dataclass(frozen=True)
class InvalidInputResult:
    """
    Invalid input result (e.g., empty alias after normalization).

    Attributes:
        status: Always ResolutionStatus.INVALID_INPUT
        reason: Human-readable explanation of why input is invalid
    """

    status: Literal[ResolutionStatus.INVALID_INPUT]
    reason: str


# --- Resolution Result Union (Step 2) ---

ResolutionResult = (
    ResolvedResult | NotFoundResult | AmbiguousResult | InvalidInputResult
)
"""
Union of all possible resolution results.

Discriminated by the 'status' field.
"""

# --- ID Generation (Step 3) ---

import uuid


def _generate_entity_id() -> EntityId:
    """
    Generate a new unique entity ID.

    Uses UUID v4 (random) for entity identity.

    Returns:
        EntityId: Fresh entity ID (never previously issued)

    Contract: V2-005 §3.1
    """
    return EntityId(str(uuid.uuid4()))


# --- Name Normalization (Step 3) ---


def normalize_for_lookup(s: str) -> str:
    """
    Normalize string for case-insensitive lookup.

    Normalization steps:
    1. Strip leading/trailing whitespace
    2. Remove all U+3000 (full-width space)
    3. Collapse consecutive ASCII U+0020 spaces to single space
    4. Lowercase only if result is pure ASCII

    Args:
        s: Input string to normalize

    Returns:
        Normalized string for lookup comparison

    Examples:
        >>> normalize_for_lookup("  张三  ")
        '张三'
        >>> normalize_for_lookup("Zhang  San")
        'zhang san'
        >>> normalize_for_lookup("SMITH")
        'smith'
        >>> normalize_for_lookup("李　明")
        '李明'

    Contract: V2-005 §3.6
    """
    # Step 1: Strip leading/trailing whitespace
    result = s.strip()

    # Step 2: Remove all U+3000 (full-width space)
    result = result.replace("　", "")

    # Step 3: Collapse consecutive ASCII spaces (U+0020) to single space
    # Only collapse U+0020, not other whitespace characters
    while "  " in result:  # consecutive ASCII spaces
        result = result.replace("  ", " ")

    # Step 4: Lowercase only if pure ASCII
    if result.isascii():
        result = result.lower()

    return result


# Functions for Step 3+ operations (to be implemented)
