"""
V2-006 Step 2 Tests: Relationship Identity Model.

Tests EntityRelationship dataclass construction, immutability, and field validation.

Contract: V2-006 Implementation Contract v1.0.0 §9 Step 2
"""

import pytest

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    EntityRelationship,
    RelationshipId,
    RelationshipType,
)


# --- EntityRelationship Construction Tests ---


def test_entity_relationship_construction():
    """EntityRelationship can be constructed with all required fields."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    assert rel.relationship_id == RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    assert rel.project_id == ProjectId("proj_001")
    assert rel.source_entity_id == EntityId("550e8400-e29b-41d4-a716-446655440000")
    assert rel.target_entity_id == EntityId("650e8400-e29b-41d4-a716-446655440001")
    assert rel.relationship_type == RelationshipType("knows")


def test_entity_relationship_field_preservation():
    """EntityRelationship preserves all field values."""
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    proj_id = ProjectId("proj_001")
    source_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target_id = EntityId("650e8400-e29b-41d4-a716-446655440001")
    rel_type = RelationshipType("parent_of")

    rel = EntityRelationship(
        relationship_id=rel_id,
        project_id=proj_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=rel_type,
    )

    # All fields accessible
    assert rel.relationship_id == rel_id
    assert rel.project_id == proj_id
    assert rel.source_entity_id == source_id
    assert rel.target_entity_id == target_id
    assert rel.relationship_type == rel_type


# --- Immutability Tests ---


def test_entity_relationship_is_frozen():
    """EntityRelationship is immutable (frozen dataclass)."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    # Attempting to modify raises FrozenInstanceError
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        rel.relationship_type = RelationshipType("likes")  # type: ignore


def test_entity_relationship_immutability_all_fields():
    """All EntityRelationship fields are immutable."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    # Cannot modify any field
    with pytest.raises(Exception):
        rel.relationship_id = RelationshipId("new-id")  # type: ignore

    with pytest.raises(Exception):
        rel.project_id = ProjectId("proj_002")  # type: ignore

    with pytest.raises(Exception):
        rel.source_entity_id = EntityId("new-source")  # type: ignore

    with pytest.raises(Exception):
        rel.target_entity_id = EntityId("new-target")  # type: ignore


# --- Self-Relationship Tests ---


def test_entity_relationship_self_relationship():
    """EntityRelationship allows source == target (self-relationships)."""
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")

    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=entity_id,
        target_entity_id=entity_id,  # Same entity
        relationship_type=RelationshipType("reflects_on"),
    )

    assert rel.source_entity_id == rel.target_entity_id


# --- Equality Tests ---


def test_entity_relationship_equality():
    """EntityRelationship supports equality comparison."""
    rel1 = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    assert rel1 == rel2


def test_entity_relationship_inequality():
    """EntityRelationship detects differences in fields."""
    rel1 = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=RelationshipId("different-id-0000-0000-0000-000000000000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    assert rel1 != rel2


# --- Type Integration Tests ---


def test_entity_relationship_uses_v2_005_types():
    """EntityRelationship correctly integrates V2-005 types."""
    # V2-005 types (EntityId, ProjectId) can be used directly
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=project_id,
        source_entity_id=entity_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    assert isinstance(rel.source_entity_id, str)  # NewType is transparent at runtime
    assert isinstance(rel.project_id, str)


def test_entity_relationship_uses_step1_types():
    """EntityRelationship correctly integrates Step 1 types."""
    # Step 1 types (RelationshipId, RelationshipType) can be used
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    rel_type = RelationshipType("depends_on")

    rel = EntityRelationship(
        relationship_id=rel_id,
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=rel_type,
    )

    assert isinstance(rel.relationship_id, str)
    assert isinstance(rel.relationship_type, str)


# --- Multiple Relationship Types Tests ---


def test_entity_relationship_different_types():
    """EntityRelationship supports different relationship types."""
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel_knows = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000001"),
        project_id=project,
        source_entity_id=entity_a,
        target_entity_id=entity_b,
        relationship_type=RelationshipType("knows"),
    )

    rel_likes = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000002"),
        project_id=project,
        source_entity_id=entity_a,
        target_entity_id=entity_b,
        relationship_type=RelationshipType("likes"),
    )

    # Same entities, different types, different IDs
    assert rel_knows.source_entity_id == rel_likes.source_entity_id
    assert rel_knows.target_entity_id == rel_likes.target_entity_id
    assert rel_knows.relationship_type != rel_likes.relationship_type
    assert rel_knows.relationship_id != rel_likes.relationship_id


# --- Dataclass Behavior Tests ---


def test_entity_relationship_repr():
    """EntityRelationship has a useful repr."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    repr_str = repr(rel)
    assert "EntityRelationship" in repr_str
    assert "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8" in repr_str


def test_entity_relationship_is_hashable():
    """EntityRelationship is hashable (frozen dataclass)."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    # Can be used in sets and as dict keys
    rel_set = {rel}
    assert rel in rel_set

    rel_dict = {rel: "metadata"}
    assert rel_dict[rel] == "metadata"


# --- V2-005 Preservation ---


def test_v2_005_entity_identity_still_works():
    """V2-005 EntityIdentity is unaffected by V2-006 Step 2."""
    from anovel.domain.identity import create_identity

    # V2-005 operations still work
    entity = create_identity(ProjectId("proj_001"), "Test Entity")
    assert entity.canonical_name == "Test Entity"
