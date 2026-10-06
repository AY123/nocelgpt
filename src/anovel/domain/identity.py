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


# --- Entity Registry (Step 4) ---


class EntityRegistry:
    """
    In-memory registry for entity identity management.

    This is a simple in-memory storage for V2-005 contract tests.
    NOT persistent (persistence is V2-009).
    NOT thread-safe (concurrency is V2-009).

    Contract: V2-005 §4
    """

    def __init__(self) -> None:
        """Initialize empty entity registry."""
        self._entities: dict[EntityId, EntityIdentity] = {}
        self._by_project: dict[ProjectId, set[EntityId]] = {}

    def add_entity(self, entity: EntityIdentity) -> None:
        """
        Add entity to registry with uniqueness enforcement.

        Uniqueness Constraint:
        - entity_id MUST be unique across registry
        - Duplicate entity_id with different content → ValueError

        Idempotency:
        - Same entity_id + same content (by value equality) → no-op
        - Same entity_id + different content → ValueError

        NOT Constrained:
        - canonical_name MAY be duplicate (across entities)
        - Aliases MAY be duplicate (across entities) → AMBIGUOUS at resolution

        Args:
            entity: EntityIdentity to add

        Raises:
            ValueError: If entity_id already registered with different content

        Contract: V2-005 §4.1
        """
        if entity.entity_id in self._entities:
            existing = self._entities[entity.entity_id]
            if existing != entity:  # Value equality (frozen dataclass)
                raise ValueError(
                    f"Entity ID {entity.entity_id} already registered "
                    f"with different content"
                )
            # Same content → idempotent, no-op
            return

        # Normal registration
        self._entities[entity.entity_id] = entity
        # Add to project index (set ensures no duplicates)
        self._by_project.setdefault(entity.project_id, set()).add(entity.entity_id)

    def get_entity(self, entity_id: EntityId) -> EntityIdentity | None:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Entity identifier to look up

        Returns:
            EntityIdentity if found, None otherwise

        Contract: V2-005 §4
        """
        return self._entities.get(entity_id)

    def get_entities(self, project_id: ProjectId) -> list[EntityIdentity]:
        """
        Retrieve all entities in project.

        Args:
            project_id: Project scope to query

        Returns:
            List of EntityIdentity objects in project (empty if project unknown)

        Contract: V2-005 §4
        """
        entity_ids = self._by_project.get(project_id, set())
        return [self._entities[eid] for eid in entity_ids]


# --- Entity Operations (Step 5) ---


def create_identity(
    project_id: ProjectId,
    canonical_name: str,
    entity_type: str | None = None,
) -> EntityIdentity:
    """
    Create a new entity identity with stable ID.

    Generates a fresh UUID v4 entity ID and creates an immutable EntityIdentity
    with empty aliases. This is a pure function with no side effects.

    Args:
        project_id: Project scope for entity (non-empty)
        canonical_name: Primary display name (non-empty, outer whitespace trimmed)
        entity_type: Optional entity type tag (if provided, must be non-empty)

    Returns:
        EntityIdentity with fresh entity_id and empty aliases

    Raises:
        ValueError: If project_id is empty
        ValueError: If canonical_name is empty or whitespace-only
        ValueError: If entity_type is non-None but empty or whitespace-only

    Example:
        >>> entity = create_identity(
        ...     ProjectId("proj_01"),
        ...     "张三",
        ...     entity_type="CHARACTER"
        ... )
        >>> entity.canonical_name
        '张三'
        >>> entity.aliases
        frozenset()

    Contract: V2-005 §3.1
    """
    # Validate project_id
    if not project_id or not project_id.strip():
        raise ValueError("project_id cannot be empty or whitespace-only")

    # Validate and trim canonical_name
    if not canonical_name or not canonical_name.strip():
        raise ValueError("canonical_name cannot be empty or whitespace-only")
    trimmed_name = canonical_name.strip()

    # Validate entity_type (if provided)
    if entity_type is not None and (not entity_type or not entity_type.strip()):
        raise ValueError("entity_type cannot be empty or whitespace-only")

    # Generate fresh entity ID
    entity_id = _generate_entity_id()

    return EntityIdentity(
        entity_id=entity_id,
        project_id=project_id,
        canonical_name=trimmed_name,
        aliases=frozenset(),
        entity_type=entity_type,
    )


def rename_identity(
    identity: EntityIdentity,
    new_canonical_name: str,
) -> EntityIdentity:
    """
    Rename entity to new canonical name.

    Returns a new EntityIdentity with the new canonical name. The old canonical
    name is automatically preserved as an alias. The entity_id, project_id, and
    entity_type remain unchanged. This is a pure function - the original identity
    object is not modified.

    Args:
        identity: Existing entity identity to rename
        new_canonical_name: New primary display name (non-empty, outer whitespace trimmed)

    Returns:
        New EntityIdentity with updated canonical_name and old name added to aliases

    Raises:
        ValueError: If new_canonical_name is empty or whitespace-only

    Example:
        >>> original = create_identity(ProjectId("proj_01"), "张三")
        >>> renamed = rename_identity(original, "张三丰")
        >>> renamed.entity_id == original.entity_id
        True
        >>> renamed.canonical_name
        '张三丰'
        >>> "张三" in renamed.aliases
        True

    Contract: V2-005 §3.2
    """
    # Validate and trim new canonical name
    if not new_canonical_name or not new_canonical_name.strip():
        raise ValueError("new_canonical_name cannot be empty or whitespace-only")
    trimmed_new_name = new_canonical_name.strip()

    # Return new EntityIdentity with old canonical name added to aliases
    # frozenset union automatically handles duplicates
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=trimmed_new_name,
        aliases=identity.aliases | {identity.canonical_name},
        entity_type=identity.entity_type,
    )


def add_alias(
    identity: EntityIdentity,
    alias: str,
) -> EntityIdentity:
    """
    Add alias to entity identity.

    Returns a new EntityIdentity with the alias added to the aliases set.
    The alias is trimmed of outer whitespace before storage. If the alias
    already exists (compared via normalized lookup), this is a no-op and
    returns a new EntityIdentity with the same aliases.

    Duplicate detection uses normalize_for_lookup() for comparison, ensuring
    case-insensitive matching for ASCII and whitespace normalization.

    Args:
        identity: Existing entity identity
        alias: Alternative name to add (non-empty, outer whitespace trimmed)

    Returns:
        New EntityIdentity with alias added (or unchanged if duplicate)

    Raises:
        ValueError: If alias is empty or whitespace-only

    Example:
        >>> entity = create_identity(ProjectId("proj_01"), "张三")
        >>> with_alias = add_alias(entity, "老张")
        >>> "老张" in with_alias.aliases
        True

    Contract: V2-005 §3.3
    """
    # Validate and trim alias
    if not alias or not alias.strip():
        raise ValueError("alias cannot be empty or whitespace-only")
    trimmed_alias = alias.strip()

    # Check if alias already exists using normalized comparison
    normalized_new = normalize_for_lookup(trimmed_alias)

    # Check against canonical name and existing aliases
    if normalized_new == normalize_for_lookup(identity.canonical_name):
        # Alias matches canonical name - still add to aliases (idempotent)
        pass

    for existing_alias in identity.aliases:
        if normalized_new == normalize_for_lookup(existing_alias):
            # Alias already exists (after normalization) - idempotent no-op
            return EntityIdentity(
                entity_id=identity.entity_id,
                project_id=identity.project_id,
                canonical_name=identity.canonical_name,
                aliases=identity.aliases,
                entity_type=identity.entity_type,
            )

    # Add new alias
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=identity.canonical_name,
        aliases=identity.aliases | {trimmed_alias},
        entity_type=identity.entity_type,
    )


def remove_alias(
    identity: EntityIdentity,
    alias: str,
) -> EntityIdentity:
    """
    Remove alias from entity identity.

    Returns a new EntityIdentity with the specified alias removed from the
    aliases set. The alias is compared using normalize_for_lookup() for
    matching. If the alias does not exist, this is a no-op.

    Cannot remove the canonical name - attempting to do so raises ValueError.
    The canonical name protection uses exact string equality, not normalized
    comparison.

    Args:
        identity: Existing entity identity
        alias: Alias to remove (compared via normalized lookup)

    Returns:
        New EntityIdentity with alias removed (or unchanged if not found)

    Raises:
        ValueError: If alias exactly matches canonical_name (cannot remove canonical name)

    Example:
        >>> entity = create_identity(ProjectId("proj_01"), "张三")
        >>> with_alias = add_alias(entity, "老张")
        >>> without = remove_alias(with_alias, "老张")
        >>> "老张" in without.aliases
        False

    Contract: V2-005 §3.4
    """
    # Trim alias for comparison
    trimmed_alias = alias.strip()

    # Check if trying to remove canonical name (exact equality)
    if trimmed_alias == identity.canonical_name:
        raise ValueError("Cannot remove canonical name as alias")

    # Find and remove matching alias using normalized comparison
    normalized_target = normalize_for_lookup(trimmed_alias)
    aliases_to_keep = set()
    for existing_alias in identity.aliases:
        if normalize_for_lookup(existing_alias) != normalized_target:
            aliases_to_keep.add(existing_alias)

    # Return new EntityIdentity with updated aliases
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=identity.canonical_name,
        aliases=frozenset(aliases_to_keep),
        entity_type=identity.entity_type,
    )


# Functions for Step 7+ operations (to be implemented)
