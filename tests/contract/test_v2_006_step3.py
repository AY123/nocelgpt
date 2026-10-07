"""
V2-006 Step 3 Tests: Relationship Registry.

Tests RelationshipRegistry CRUD operations, project isolation, idempotency, and conflict detection.

Contract: V2-006 Implementation Contract v1.0.0 §9 Step 3
"""

import pytest

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    EntityRelationship,
    RelationshipId,
    RelationshipRegistry,
    RelationshipType,
)


# --- Registry Initialization Tests ---


def test_registry_initialization():
    """RelationshipRegistry initializes empty."""
    registry = RelationshipRegistry()
    assert registry is not None


def test_registry_empty_get_returns_none():
    """Getting non-existent relationship returns None."""
    registry = RelationshipRegistry()
    rel_id = RelationshipId("00000000-0000-4000-8000-000000000000")
    assert registry.get_relationship(rel_id) is None


def test_registry_empty_project_returns_empty_list():
    """Querying empty project returns empty list."""
    registry = RelationshipRegistry()
    results = registry.get_relationships(
        EntityId("550e8400-e29b-41d4-a716-446655440000"), ProjectId("proj_001")
    )
    assert results == []


# --- Add/Get Tests ---


def test_registry_add_then_get():
    """Added relationship can be retrieved by ID."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    retrieved = registry.get_relationship(rel.relationship_id)

    assert retrieved == rel


def test_registry_add_then_project_query():
    """Added relationship appears in project query."""
    registry = RelationshipRegistry()
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=project_id,
        source_entity_id=entity_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    results = registry.get_relationships(entity_id, project_id)

    assert len(results) == 1
    assert results[0] == rel


# --- Project Isolation Tests ---


def test_registry_project_isolation():
    """Relationships in different projects are isolated."""
    registry = RelationshipRegistry()
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")

    rel_proj1 = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000001"),
        project_id=ProjectId("proj_001"),
        source_entity_id=entity_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel_proj2 = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000002"),
        project_id=ProjectId("proj_002"),
        source_entity_id=entity_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel_proj1)
    registry.add_relationship(rel_proj2)

    # Project 1 only sees its own relationships
    results_p1 = registry.get_relationships(entity_id, ProjectId("proj_001"))
    assert len(results_p1) == 1
    assert results_p1[0].relationship_id == rel_proj1.relationship_id

    # Project 2 only sees its own relationships
    results_p2 = registry.get_relationships(entity_id, ProjectId("proj_002"))
    assert len(results_p2) == 1
    assert results_p2[0].relationship_id == rel_proj2.relationship_id


def test_registry_cross_project_query_returns_empty():
    """Querying wrong project returns empty list."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)

    # Query different project
    results = registry.get_relationships(
        rel.source_entity_id, ProjectId("proj_002")
    )
    assert results == []


# --- Idempotency Tests ---


def test_registry_add_same_relationship_twice_is_noop():
    """Adding same relationship twice is idempotent (no-op)."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    registry.add_relationship(rel)  # Second add is no-op

    # Only one relationship in registry
    results = registry.get_relationships(rel.source_entity_id, rel.project_id)
    assert len(results) == 1


# --- Conflict Detection Tests ---


def test_registry_same_id_different_content_raises():
    """Adding relationship with same ID but different content raises ValueError."""
    registry = RelationshipRegistry()
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")

    rel1 = EntityRelationship(
        relationship_id=rel_id,
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=rel_id,  # Same ID
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("DIFFERENT-TARGET-0000-0000-000000000000"),  # Different content
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel1)

    with pytest.raises(ValueError, match="already exists with different content"):
        registry.add_relationship(rel2)


# --- Uniqueness Constraint Tests ---


def test_registry_same_tuple_different_id_is_noop():
    """Adding relationship with same (source, target, type, project) tuple but different ID is no-op."""
    registry = RelationshipRegistry()

    rel1 = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000001"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000002"),  # Different ID
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)  # no-op (tuple already exists)

    # Only first relationship added
    results = registry.get_relationships(rel1.source_entity_id, rel1.project_id)
    assert len(results) == 1
    assert results[0].relationship_id == rel1.relationship_id


# --- Remove Tests ---


def test_registry_remove_existing():
    """Removing existing relationship removes it."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    registry.remove_relationship(rel.relationship_id)

    assert registry.get_relationship(rel.relationship_id) is None


def test_registry_remove_nonexistent_is_noop():
    """Removing non-existent relationship is idempotent (no error)."""
    registry = RelationshipRegistry()
    rel_id = RelationshipId("00000000-0000-4000-8000-000000000000")

    # Remove non-existent (should not raise)
    registry.remove_relationship(rel_id)


def test_registry_remove_twice_is_noop():
    """Removing same relationship twice is idempotent."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    registry.remove_relationship(rel.relationship_id)
    registry.remove_relationship(rel.relationship_id)  # Second remove is no-op


# --- Query by Entity Tests ---


def test_registry_query_returns_source_relationships():
    """Query returns relationships where entity is source."""
    registry = RelationshipRegistry()
    source_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=project_id,
        source_entity_id=source_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    results = registry.get_relationships(source_id, project_id)

    assert len(results) == 1
    assert results[0] == rel


def test_registry_query_returns_target_relationships():
    """Query returns relationships where entity is target."""
    registry = RelationshipRegistry()
    target_id = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project_id = ProjectId("proj_001")

    rel = EntityRelationship(
        relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
        project_id=project_id,
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=target_id,
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    results = registry.get_relationships(target_id, project_id)

    assert len(results) == 1
    assert results[0] == rel


def test_registry_query_returns_both_source_and_target():
    """Query returns relationships where entity is source OR target."""
    registry = RelationshipRegistry()
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    rel_as_source = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000001"),
        project_id=project_id,
        source_entity_id=entity_id,
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel_as_target = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000002"),
        project_id=project_id,
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440002"),
        target_entity_id=entity_id,
        relationship_type=RelationshipType("likes"),
    )

    registry.add_relationship(rel_as_source)
    registry.add_relationship(rel_as_target)

    results = registry.get_relationships(entity_id, project_id)
    assert len(results) == 2


# --- Multiple Relationships Tests ---


def test_registry_multiple_relationships_different_types():
    """Registry supports multiple relationships with different types."""
    registry = RelationshipRegistry()
    source_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target_id = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project_id = ProjectId("proj_001")

    rel_knows = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000001"),
        project_id=project_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=RelationshipType("knows"),
    )

    rel_likes = EntityRelationship(
        relationship_id=RelationshipId("00000000-0000-4000-8000-000000000002"),
        project_id=project_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=RelationshipType("likes"),
    )

    registry.add_relationship(rel_knows)
    registry.add_relationship(rel_likes)

    results = registry.get_relationships(source_id, project_id)
    assert len(results) == 2


# --- V2-005 Preservation ---


def test_v2_005_entity_registry_still_works():
    """V2-005 EntityRegistry is unaffected by V2-006 Step 3."""
    from anovel.domain.identity import EntityRegistry, create_identity

    # V2-005 registry still works
    entity_registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_001"), "Test Entity")
    entity_registry.add_entity(entity)

    retrieved = entity_registry.get_entity(entity.entity_id)
    assert retrieved == entity
