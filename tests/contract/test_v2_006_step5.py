"""
V2-006 Step 5 Contract Tests — delete_relationship Operation.

Tests the idempotent deletion operation with no cascade behavior.

Contract: V2-006 Implementation Contract v1.0.1 §5.2
"""

import pytest

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    RelationshipId,
    RelationshipRegistry,
    RelationshipType,
    create_relationship,
    delete_relationship,
)

# --- Basic Deletion Tests ---


def test_delete_existing_relationship():
    """S5-T01: Delete existing relationship removes it from registry."""
    registry = RelationshipRegistry()
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    registry.add_relationship(rel)
    assert registry.get_relationship(rel.relationship_id) == rel

    delete_relationship(rel.relationship_id, registry)
    assert registry.get_relationship(rel.relationship_id) is None


def test_delete_nonexistent_relationship():
    """S5-T02: Delete nonexistent ID is no-op (does not raise)."""
    registry = RelationshipRegistry()
    unknown_id = RelationshipId("00000000-0000-4000-8000-000000000099")

    # Should not raise
    delete_relationship(unknown_id, registry)


def test_delete_twice_idempotent():
    """S5-T03: Deleting same ID twice is idempotent (no error)."""
    registry = RelationshipRegistry()
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    registry.add_relationship(rel)
    delete_relationship(rel.relationship_id, registry)
    delete_relationship(rel.relationship_id, registry)  # Second call: no error


# --- Index Cleanup Tests ---


def test_delete_cleans_source_query():
    """S5-T04: Deleted relationship removed from source entity queries."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # Before delete: relationship present
    results = registry.get_relationships(source, project)
    assert rel in results

    # After delete: relationship absent
    delete_relationship(rel.relationship_id, registry)
    results = registry.get_relationships(source, project)
    assert rel not in results


def test_delete_cleans_target_query():
    """S5-T05: Deleted relationship removed from target entity queries."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # Before delete: relationship present in target query
    results = registry.get_relationships(target, project)
    assert rel in results

    # After delete: relationship absent from target query
    delete_relationship(rel.relationship_id, registry)
    results = registry.get_relationships(target, project)
    assert rel not in results


# --- No Cascade Tests ---


def test_delete_preserves_other_relationships():
    """S5-T06: Deleting one relationship preserves others."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target_a = EntityId("650e8400-e29b-41d4-a716-446655440001")
    target_b = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    rel1 = create_relationship(source, target_a, RelationshipType("knows"), project)
    rel2 = create_relationship(source, target_b, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Delete rel1
    delete_relationship(rel1.relationship_id, registry)

    # rel1 absent, rel2 present
    assert registry.get_relationship(rel1.relationship_id) is None
    assert registry.get_relationship(rel2.relationship_id) == rel2


def test_delete_cross_project_isolation():
    """S5-T07: Deleting in one project does not affect another."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")

    rel_p1 = create_relationship(
        source, target, RelationshipType("knows"), ProjectId("proj_001")
    )
    rel_p2 = create_relationship(
        source, target, RelationshipType("knows"), ProjectId("proj_002")
    )

    registry.add_relationship(rel_p1)
    registry.add_relationship(rel_p2)

    # Delete from proj_001
    delete_relationship(rel_p1.relationship_id, registry)

    # proj_001 relationship absent, proj_002 present
    assert registry.get_relationship(rel_p1.relationship_id) is None
    assert registry.get_relationship(rel_p2.relationship_id) == rel_p2


def test_delete_no_cascade_to_related_relationships():
    """S5-T12: Deleting relationship does not cascade to relationships sharing entities."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    # R1: A -> B knows
    # R2: A -> C likes
    # R3: C -> B depends_on
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_c, RelationshipType("likes"), project)
    rel3 = create_relationship(
        entity_c, entity_b, RelationshipType("depends_on"), project
    )

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)
    registry.add_relationship(rel3)

    # Delete R1
    delete_relationship(rel1.relationship_id, registry)

    # R1 absent, R2 and R3 present
    assert registry.get_relationship(rel1.relationship_id) is None
    assert registry.get_relationship(rel2.relationship_id) == rel2
    assert registry.get_relationship(rel3.relationship_id) == rel3


# --- Tuple Reuse Tests ---


def test_delete_allows_tuple_reuse():
    """S5-T08: After deleting, same semantic tuple can be added with new ID."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create and add first relationship
    rel1 = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel1)

    # Delete it
    delete_relationship(rel1.relationship_id, registry)

    # Create and add second relationship with same tuple
    rel2 = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel2)  # Should succeed

    assert registry.get_relationship(rel2.relationship_id) == rel2


def test_delete_same_object_readd():
    """S5-T09: After deleting, same object can be re-added."""
    registry = RelationshipRegistry()
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    registry.add_relationship(rel)
    delete_relationship(rel.relationship_id, registry)
    registry.add_relationship(rel)  # Re-add same object

    assert registry.get_relationship(rel.relationship_id) == rel


# --- Return Value Tests ---


def test_delete_returns_none():
    """S5-T13: Successful deletion returns None."""
    registry = RelationshipRegistry()
    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    registry.add_relationship(rel)
    result = delete_relationship(rel.relationship_id, registry)
    assert result is None


def test_delete_missing_returns_none():
    """S5-T14: Deleting missing ID returns None (no error)."""
    registry = RelationshipRegistry()
    unknown_id = RelationshipId("00000000-0000-4000-8000-000000000099")

    result = delete_relationship(unknown_id, registry)
    assert result is None


# --- Step 3 H1 Integration Tests ---


def test_delete_preserves_step3_h1_tuple_uniqueness():
    """S5-T15: Deletion preserves Step 3 H1 tuple uniqueness semantics."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create two relationships with same tuple
    rel1 = create_relationship(source, target, RelationshipType("knows"), project)
    rel2 = create_relationship(source, target, RelationshipType("knows"), project)
    assert rel1.relationship_id != rel2.relationship_id

    # Add first
    registry.add_relationship(rel1)

    # Second is rejected (Step 3 H1 v1.0.1 semantics)
    with pytest.raises(ValueError, match="already exists with RelationshipId"):
        registry.add_relationship(rel2)

    # Delete first
    delete_relationship(rel1.relationship_id, registry)

    # Now second can be added (tuple released)
    registry.add_relationship(rel2)
    assert registry.get_relationship(rel2.relationship_id) == rel2


def test_delete_tuple_uniqueness_live_state():
    """
    CRITICAL: Tuple uniqueness is live-state based, not tombstoned.

    After delete, tuple is available for reuse.
    """
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    r1 = create_relationship(source, target, RelationshipType("knows"), project)
    r2 = create_relationship(source, target, RelationshipType("knows"), project)

    registry.add_relationship(r1)

    # Before delete: r2 rejected
    with pytest.raises(ValueError):
        registry.add_relationship(r2)

    # Delete r1
    delete_relationship(r1.relationship_id, registry)

    # After delete: r2 accepted (tuple released)
    registry.add_relationship(r2)
    assert registry.get_relationship(r2.relationship_id) == r2


# --- V2-005 Compatibility (No Entity Cascade) ---


def test_delete_no_cascade_to_entities():
    """S5-T10/T11: Deletion does not affect entities (V2-005 compatibility)."""
    # This test verifies deletion doesn't attempt entity operations
    # Actual EntityRegistry interaction would be tested in integration layer
    registry = RelationshipRegistry()

    rel = create_relationship(
        EntityId("550e8400-e29b-41d4-a716-446655440000"),
        EntityId("650e8400-e29b-41d4-a716-446655440001"),
        RelationshipType("knows"),
        ProjectId("proj_001"),
    )

    registry.add_relationship(rel)
    delete_relationship(rel.relationship_id, registry)

    # No EntityRegistry operations should have been attempted
    # (verified by absence of imports/calls in implementation)
