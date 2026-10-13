"""
ANovelOS V2 Entity Relationship Tracking.

This module extends the V2-005 identity foundation by adding directed
relationships between entities. Relationships are project-scoped, immutable,
and stored in-memory for tests/prototyping.

Public API:
    Types:
        RelationshipId, RelationshipType, EntityRelationship
    Operations:
        create_relationship, delete_relationship, get_relationships
        validate_relationship_type
    Data Structures:
        RelationshipRegistry (in-memory, for tests)

Relationship Semantics:
    - Directed (no automatic inverse)
    - Immutable (no updates after creation)
    - Project-scoped (cross-project isolation)
    - Fresh identity (create_relationship generates new UUID v4 each call)
    - Idempotent deletion (delete_relationship is idempotent)
    - Registry replay (adding same ID + same content is no-op)
    - No referential integrity (entities need not exist)
    - No graph inference (no transitive traversal)
    - No cascade (deleting relationship does not affect entities or other relationships)

Contract: V2-006 Implementation Contract v1.0.1
"""

import uuid
from dataclasses import dataclass
from typing import NewType, Optional

from anovel.domain.identity import EntityId, ProjectId

# --- Type Aliases (Step 1) ---

RelationshipId = NewType("RelationshipId", str)
"""
Opaque stable identifier for relationships.

Format: UUID v4 (lowercase, with hyphens, 36 characters)
Example: "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"

Contract: V2-006 §3.1
"""

RelationshipType = NewType("RelationshipType", str)
"""
Extensible relationship type identifier.

Application-defined semantics (not constrained by V2-006).
Examples: "parent_of", "knows", "depends_on", "belongs_to"

NOT an enum (allows future extension without contract changes).
Semantic validation is application layer responsibility.

Contract: V2-006 §3.2
"""


# --- Validation Functions (Step 1) ---


def validate_relationship_type(s: str) -> RelationshipType:
    """
    Validate and construct RelationshipType.

    Args:
        s: Raw relationship type string

    Returns:
        RelationshipType if valid

    Raises:
        ValueError: If empty or whitespace-only

    Example:
        >>> validate_relationship_type("knows")
        RelationshipType("knows")
        >>> validate_relationship_type("  ")
        Traceback (most recent call last):
        ValueError: RelationshipType cannot be empty or whitespace-only

    Contract: V2-006 §3.2
    """
    trimmed = s.strip()
    if not trimmed:
        raise ValueError("RelationshipType cannot be empty or whitespace-only")
    return RelationshipType(trimmed)


# --- Domain Model (Step 2) ---


@dataclass(frozen=True)
class EntityRelationship:
    """
    Directed relationship between two entities.

    Immutable after creation. Identity is relationship_id.
    Uniqueness constraint: (source_entity_id, target_entity_id, relationship_type, project_id).

    Attributes:
        relationship_id: Stable unique identifier (UUID v4)
        project_id: Project scope (from V2-005)
        source_entity_id: Source entity (from V2-005)
        target_entity_id: Target entity (from V2-005)
        relationship_type: Type of relationship (extensible string)

    Invariants:
        - Immutable (frozen dataclass)
        - All fields required (no None values)
        - Source and target may be equal (self-relationships allowed)

    Example:
        >>> rel = EntityRelationship(
        ...     relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        ...     project_id=ProjectId("proj_001"),
        ...     source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        ...     target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        ...     relationship_type=RelationshipType("knows")
        ... )

    Contract: V2-006 §3.3
    """

    relationship_id: RelationshipId
    project_id: ProjectId
    source_entity_id: EntityId
    target_entity_id: EntityId
    relationship_type: RelationshipType


# --- Public Operations (Step 4) ---


def create_relationship(
    source_entity_id: EntityId,
    target_entity_id: EntityId,
    relationship_type: RelationshipType,
    project_id: ProjectId,
) -> EntityRelationship:
    """
    Create a directed relationship between two entities.

    Generates a new RelationshipId (UUID v4).
    Does NOT validate that source/target entities exist (no referential integrity).

    Args:
        source_entity_id: Source entity
        target_entity_id: Target entity
        relationship_type: Type of relationship
        project_id: Project scope

    Returns:
        New EntityRelationship instance

    Raises:
        ValueError: If relationship_type is empty or whitespace-only

    Example:
        >>> rel = create_relationship(
        ...     EntityId("550e8400-e29b-41d4-a716-446655440000"),
        ...     EntityId("650e8400-e29b-41d4-a716-446655440001"),
        ...     RelationshipType("knows"),
        ...     ProjectId("proj_001")
        ... )
        >>> rel.relationship_id  # UUID v4 generated
        RelationshipId("a1b2c3d4...")

    Contract: V2-006 §5.1 (v1.0.1)
    """
    # Validate relationship type (reuses Step 1 validator)
    validated_type = validate_relationship_type(relationship_type)

    # Generate new UUID v4
    relationship_id = RelationshipId(str(uuid.uuid4()))

    # Return immutable relationship
    return EntityRelationship(
        relationship_id=relationship_id,
        project_id=project_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relationship_type=validated_type,
    )


def delete_relationship(
    relationship_id: RelationshipId, registry: "RelationshipRegistry"
) -> None:
    """
    Delete a relationship by ID.

    Idempotent: no-op if relationship_id not found (does not raise).
    Does NOT cascade or affect inverse relationships.

    Args:
        relationship_id: ID of relationship to delete
        registry: RelationshipRegistry to delete from

    Example:
        >>> delete_relationship(rel_id, registry)
        >>> # Second call is no-op:
        >>> delete_relationship(rel_id, registry)  # No error

    Contract: V2-006 §5.2 (v1.0.1)
    """
    registry.remove_relationship(relationship_id)


def get_relationships(
    entity_id: EntityId,
    project_id: ProjectId,
    registry: "RelationshipRegistry",
) -> list[EntityRelationship]:
    """
    Get all relationships for an entity (source or target).

    Returns relationships where entity_id appears as source OR target,
    within the specified project.

    Args:
        entity_id: Entity to find relationships for
        project_id: Project scope
        registry: RelationshipRegistry to query

    Returns:
        List of EntityRelationship (empty list if none found)
        Order is deterministic but unspecified

    Example:
        >>> rel1 = create_relationship(A, B, "knows", proj)
        >>> rel2 = create_relationship(B, C, "likes", proj)
        >>> registry.add_relationship(rel1)
        >>> registry.add_relationship(rel2)
        >>> get_relationships(B, proj, registry)
        [rel1, rel2]  # B appears as target in rel1, source in rel2

    Contract: V2-006 §5.3 (v1.0.1)
    """
    return registry.get_relationships(entity_id, project_id)


# --- Relationship Registry (Step 3) ---


class RelationshipRegistry:
    """
    In-memory relationship store for tests and prototyping.

    NOT for production persistence (see V2-007).

    Identity: relationship_id (primary key)
    Uniqueness: (source_entity_id, target_entity_id, relationship_type, project_id) tuple

    Contract: V2-006 §4
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._relationships: dict[RelationshipId, EntityRelationship] = {}
        self._by_project: dict[ProjectId, set[RelationshipId]] = {}

    def add_relationship(self, relationship: EntityRelationship) -> None:
        """
        Add relationship to registry.

        Idempotent based on relationship_id:
        - If relationship_id exists with same content → no-op
        - If relationship_id exists with different content → ValueError

        Uniqueness constraint:
        - If (source, target, type, project) tuple exists with different ID → ValueError

        Args:
            relationship: EntityRelationship to add

        Raises:
            ValueError: If relationship_id exists with different content
            ValueError: If semantic tuple exists with different relationship_id

        Example:
            >>> registry = RelationshipRegistry()
            >>> rel = EntityRelationship(...)
            >>> registry.add_relationship(rel)
            >>> registry.add_relationship(rel)  # no-op (same content)

        Contract: V2-006 §4.2 (v1.0.1)
        """
        rel_id = relationship.relationship_id

        # Check if relationship_id already exists
        if rel_id in self._relationships:
            existing = self._relationships[rel_id]
            if existing != relationship:
                raise ValueError(
                    f"RelationshipId {rel_id} already exists with different content"
                )
            # Same content → no-op
            return

        # Check uniqueness constraint: (source, target, type, project) tuple
        for existing_rel in self._relationships.values():
            if (
                existing_rel.source_entity_id == relationship.source_entity_id
                and existing_rel.target_entity_id == relationship.target_entity_id
                and existing_rel.relationship_type == relationship.relationship_type
                and existing_rel.project_id == relationship.project_id
            ):
                # Tuple collision with different ID → reject
                raise ValueError(
                    f"Relationship with tuple (source={relationship.source_entity_id}, "
                    f"target={relationship.target_entity_id}, "
                    f"type={relationship.relationship_type}, "
                    f"project={relationship.project_id}) already exists with "
                    f"RelationshipId {existing_rel.relationship_id}"
                )

        # Add relationship
        self._relationships[rel_id] = relationship

        # Add to project index
        if relationship.project_id not in self._by_project:
            self._by_project[relationship.project_id] = set()
        self._by_project[relationship.project_id].add(rel_id)

    def remove_relationship(self, relationship_id: RelationshipId) -> None:
        """
        Remove relationship by ID.

        Idempotent: no-op if relationship_id not found (does not raise).

        Args:
            relationship_id: ID of relationship to remove

        Example:
            >>> registry.remove_relationship(rel_id)
            >>> registry.remove_relationship(rel_id)  # no-op (not found)

        Contract: V2-006 §4.2
        """
        if relationship_id not in self._relationships:
            return  # no-op

        relationship = self._relationships[relationship_id]
        project_id = relationship.project_id

        # Remove from main storage
        del self._relationships[relationship_id]

        # Remove from project index
        if project_id in self._by_project:
            self._by_project[project_id].discard(relationship_id)
            # Clean up empty project sets
            if not self._by_project[project_id]:
                del self._by_project[project_id]

    def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Optional[EntityRelationship]:
        """
        Get relationship by ID.

        Args:
            relationship_id: ID to lookup

        Returns:
            EntityRelationship if found, None otherwise

        Example:
            >>> rel = registry.get_relationship(rel_id)
            >>> if rel is not None:
            ...     print(rel.relationship_type)

        Contract: V2-006 §4.2
        """
        return self._relationships.get(relationship_id)

    def get_relationships(
        self, entity_id: EntityId, project_id: ProjectId
    ) -> list[EntityRelationship]:
        """
        Get all relationships for an entity (source or target).

        Returns relationships where entity_id appears as source OR target,
        within the specified project.

        Args:
            entity_id: Entity to find relationships for
            project_id: Project scope

        Returns:
            List of EntityRelationship (empty list if none found)
            Order is deterministic but unspecified (implementation-defined)

        Example:
            >>> rels = registry.get_relationships(entity_id, project_id)
            >>> for rel in rels:
            ...     print(rel.relationship_type)

        Contract: V2-006 §4.2
        """
        if project_id not in self._by_project:
            return []

        results = []
        for rel_id in self._by_project[project_id]:
            rel = self._relationships[rel_id]
            if rel.source_entity_id == entity_id or rel.target_entity_id == entity_id:
                results.append(rel)

        return results
