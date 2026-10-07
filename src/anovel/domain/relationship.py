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
    Data Structures:
        RelationshipRegistry (in-memory, for tests)

Relationship Semantics:
    - Directed (no automatic inverse)
    - Immutable (no updates)
    - Project-scoped (isolation)
    - Idempotent (create/delete)

Contract: V2-006 Implementation Contract v1.0.0
"""

from dataclasses import dataclass
from typing import NewType

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
