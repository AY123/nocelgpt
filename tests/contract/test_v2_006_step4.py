"""
V2-006 Step 4 Contract Tests — create_relationship Operation.

Tests the pure domain factory operation for creating EntityRelationship instances.

Contract: V2-006 Implementation Contract v1.0.1 §5.1
"""

import uuid

import pytest

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    EntityRelationship,
    RelationshipRegistry,
    RelationshipType,
    create_relationship,
)

# --- Valid Creation Tests ---


def test_create_relationship_valid():
    """S4-T01: Valid inputs create EntityRelationship with all fields assigned."""
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    rel_type = RelationshipType("knows")
    project = ProjectId("proj_001")

    rel = create_relationship(source, target, rel_type, project)

    assert isinstance(rel, EntityRelationship)
    assert rel.source_entity_id == source
    assert rel.target_entity_id == target
    assert rel.relationship_type == rel_type
    assert rel.project_id == project
    assert rel.relationship_id  # Not empty


def test_create_relationship_uuid_v4():
    """S4-T02: Generated RelationshipId is valid UUID v4."""
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    # Parse as UUID
    parsed = uuid.UUID(rel.relationship_id)
    assert parsed.version == 4


def test_create_relationship_new_identity_each_call():
    """S4-T03: Each call generates a different RelationshipId, even with same inputs."""
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    rel_type = RelationshipType("knows")
    project = ProjectId("proj_001")

    rel1 = create_relationship(source, target, rel_type, project)
    rel2 = create_relationship(source, target, rel_type, project)

    # Different IDs
    assert rel1.relationship_id != rel2.relationship_id

    # Same other fields
    assert rel1.source_entity_id == rel2.source_entity_id
    assert rel1.target_entity_id == rel2.target_entity_id
    assert rel1.relationship_type == rel2.relationship_type
    assert rel1.project_id == rel2.project_id


# --- Validation Tests ---


def test_create_relationship_empty_type_raises():
    """S4-T04: Empty relationship_type raises ValueError."""
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        create_relationship(
            EntityId("550e8400-e29b-41d4-a716-446655440000"),
            EntityId("650e8400-e29b-41d4-a716-446655440001"),
            RelationshipType(""),
            ProjectId("proj_001"),
        )


def test_create_relationship_whitespace_type_raises():
    """S4-T05: Whitespace-only relationship_type raises ValueError."""
    whitespace_cases = ["   ", "\t\n", " \t ", "\n"]

    for whitespace in whitespace_cases:
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            create_relationship(
                EntityId("550e8400-e29b-41d4-a716-446655440000"),
                EntityId("650e8400-e29b-41d4-a716-446655440001"),
                RelationshipType(whitespace),
                ProjectId("proj_001"),
            )


def test_create_relationship_trim_behavior():
    """S4-T06: Relationship type is trimmed (whitespace removed)."""
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("  knows  "),
        ProjectId("proj_001"),
    )

    assert rel.relationship_type == RelationshipType("knows")


# --- Field Assignment Tests ---


def test_create_relationship_field_assignment():
    """S4-T07: All fields assigned exactly as provided."""
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    rel_type = RelationshipType("depends_on")
    project = ProjectId("proj_xyz")

    rel = create_relationship(source, target, rel_type, project)

    assert rel.source_entity_id == source
    assert rel.target_entity_id == target
    assert rel.relationship_type == rel_type
    assert rel.project_id == project


def test_create_relationship_self_relationship():
    """S4-T08: Self-relationships (source == target) are allowed."""
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")

    rel = create_relationship(
        entity_id, entity_id, RelationshipType("reflects_on"), ProjectId("proj_001")
    )

    assert rel.source_entity_id == entity_id
    assert rel.target_entity_id == entity_id
    assert rel.source_entity_id == rel.target_entity_id


# --- No Referential Integrity Tests ---


def test_create_relationship_no_referential_integrity():
    """S4-T09: Creation succeeds without EntityRegistry or entity existence checks."""
    # Arbitrary UUIDs that likely don't exist in any registry
    unknown_source = EntityId("00000000-0000-4000-8000-000000000001")
    unknown_target = EntityId("00000000-0000-4000-8000-000000000002")

    # Should succeed without checking entity existence
    rel = create_relationship(
        unknown_source,
        unknown_target,
        RelationshipType("knows"),
        ProjectId("proj_unknown"),
    )

    assert rel.source_entity_id == unknown_source
    assert rel.target_entity_id == unknown_target


# --- Immutability Tests ---


def test_create_relationship_immutability():
    """S4-T10: Returned EntityRelationship is frozen (immutable)."""
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    # Attempt to modify should fail (frozen dataclass)
    with pytest.raises(AttributeError):
        rel.relationship_type = RelationshipType("different")  # type: ignore


# --- Step 3 H1 Integration Tests ---


def test_create_relationship_integration_with_step3_h1():
    """
    Integration: create_relationship generates fresh IDs, registry enforces tuple uniqueness.

    Step 3 H1 semantics: different ID + same tuple → ValueError
    """
    registry = RelationshipRegistry()

    # Create two relationships with same semantic tuple
    rel1 = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    rel2 = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    # Different IDs generated
    assert rel1.relationship_id != rel2.relationship_id

    # First add succeeds
    registry.add_relationship(rel1)
    assert registry.get_relationship(rel1.relationship_id) == rel1

    # Second add raises ValueError (Step 3 H1 tuple uniqueness)
    with pytest.raises(ValueError, match="already exists with RelationshipId"):
        registry.add_relationship(rel2)

    # Verify registry state unchanged by failed add
    assert registry.get_relationship(rel1.relationship_id) == rel1
    assert registry.get_relationship(rel2.relationship_id) is None


def test_create_relationship_different_projects_allowed():
    """Different projects with same tuple are allowed in registry."""
    registry = RelationshipRegistry()

    rel1 = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    rel2 = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_002"),  # Different project
    )

    # Both adds succeed (project isolation)
    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    assert registry.get_relationship(rel1.relationship_id) == rel1
    assert registry.get_relationship(rel2.relationship_id) == rel2


# --- V2-005 Compatibility Tests ---


def test_v2_005_entity_id_still_works():
    """Step 4 does not break V2-005 EntityId usage."""
    # Create relationship using V2-005 types
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    rel = create_relationship(
        entity_id,
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        project_id,
    )

    # V2-005 types remain unchanged
    assert isinstance(rel.source_entity_id, str)  # EntityId is NewType of str
    assert isinstance(rel.project_id, str)  # ProjectId is NewType of str
