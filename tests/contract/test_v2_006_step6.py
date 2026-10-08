"""
V2-006 Step 6 Contract Tests — get_relationships Query Operation.

Tests the query operation for retrieving relationships by entity and project.

Contract: V2-006 Implementation Contract v1.0.1 §5.3
"""

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    RelationshipRegistry,
    RelationshipType,
    create_relationship,
    delete_relationship,
    get_relationships,
)

# --- Basic Query Tests ---


def test_get_relationships_source_match():
    """S6-T01: Relationship where entity is source is returned."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    results = get_relationships(source, project, registry)
    assert rel in results


def test_get_relationships_target_match():
    """S6-T02: Relationship where entity is target is returned."""
    registry = RelationshipRegistry()
    source = EntityId("550e8400-e29b-41d4-a716-446655440000")
    target = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(source, target, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    results = get_relationships(target, project, registry)
    assert rel in results


def test_get_relationships_both_sides():
    """S6-T03: Both source and target matches returned."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    # A -> B, B -> C
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_b, entity_c, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Query B: should return both (target in rel1, source in rel2)
    results = get_relationships(entity_b, project, registry)
    assert rel1 in results
    assert rel2 in results
    assert len(results) == 2


def test_get_relationships_non_matching_excluded():
    """S6-T04: Non-matching relationship excluded."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    # A -> B, C -> B (C unrelated to A)
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_c, entity_b, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Query A: should return only rel1
    results = get_relationships(entity_a, project, registry)
    assert rel1 in results
    assert rel2 not in results


def test_get_relationships_wrong_project_excluded():
    """S6-T05: Wrong-project relationship excluded."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")

    rel_p1 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_001")
    )
    rel_p2 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_002")
    )

    registry.add_relationship(rel_p1)
    registry.add_relationship(rel_p2)

    # Query proj_001: should return only rel_p1
    results = get_relationships(entity_a, ProjectId("proj_001"), registry)
    assert rel_p1 in results
    assert rel_p2 not in results


def test_get_relationships_cross_project_isolation():
    """S6-T06: Same tuple across two projects isolated."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")

    rel_p1 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_001")
    )
    rel_p2 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_002")
    )

    registry.add_relationship(rel_p1)
    registry.add_relationship(rel_p2)

    results_p1 = get_relationships(entity_a, ProjectId("proj_001"), registry)
    results_p2 = get_relationships(entity_a, ProjectId("proj_002"), registry)

    assert rel_p1 in results_p1
    assert rel_p2 not in results_p1

    assert rel_p2 in results_p2
    assert rel_p1 not in results_p2


# --- Empty Result Tests ---


def test_get_relationships_empty_registry():
    """S6-T07: Empty registry returns empty list."""
    registry = RelationshipRegistry()
    entity = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project = ProjectId("proj_001")

    results = get_relationships(entity, project, registry)
    assert results == []


def test_get_relationships_unknown_entity():
    """S6-T08: Unknown entity returns empty list."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    unknown = EntityId("00000000-0000-4000-8000-000000000099")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    results = get_relationships(unknown, project, registry)
    assert results == []


def test_get_relationships_unknown_project():
    """S6-T09: Unknown project returns empty list."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")

    rel = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_001")
    )
    registry.add_relationship(rel)

    results = get_relationships(entity_a, ProjectId("proj_unknown"), registry)
    assert results == []


# --- Self-Relationship Tests ---


def test_get_relationships_self_relationship_once():
    """S6-T10: Self-relationship returned exactly once."""
    registry = RelationshipRegistry()
    entity = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project = ProjectId("proj_001")

    rel = create_relationship(entity, entity, RelationshipType("reflects_on"), project)
    registry.add_relationship(rel)

    results = get_relationships(entity, project, registry)
    assert results.count(rel) == 1
    assert len(results) == 1


# --- Multiple Relationship Tests ---


def test_get_relationships_multiple_types():
    """S6-T11: Multiple relationship types returned."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("likes"), project)
    rel3 = create_relationship(
        entity_a, entity_b, RelationshipType("trusts"), project
    )

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)
    registry.add_relationship(rel3)

    results = get_relationships(entity_a, project, registry)
    assert rel1 in results
    assert rel2 in results
    assert rel3 in results
    assert len(results) == 3


def test_get_relationships_multiple_matches():
    """S6-T12: Multiple matching relationships returned."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    entity_d = EntityId("650e8400-e29b-41d4-a716-446655440003")
    project = ProjectId("proj_001")

    # A involved in multiple relationships
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_c, entity_a, RelationshipType("likes"), project)
    rel3 = create_relationship(entity_a, entity_d, RelationshipType("trusts"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)
    registry.add_relationship(rel3)

    results = get_relationships(entity_a, project, registry)
    assert len(results) == 3
    assert rel1 in results
    assert rel2 in results
    assert rel3 in results


# --- Return Type Tests ---


def test_get_relationships_returns_list():
    """S6-T13: Return type is list."""
    registry = RelationshipRegistry()
    entity = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project = ProjectId("proj_001")

    results = get_relationships(entity, project, registry)
    assert isinstance(results, list)


def test_get_relationships_preserves_objects():
    """S6-T14: Relationship objects preserved (not cloned)."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    results = get_relationships(entity_a, project, registry)
    assert len(results) == 1
    assert results[0] is rel  # Same object, not cloned


# --- Determinism Tests ---


def test_get_relationships_deterministic_order():
    """S6-T15: Repeated query returns same order."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_c, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Query multiple times
    results1 = get_relationships(entity_a, project, registry)
    results2 = get_relationships(entity_a, project, registry)
    results3 = get_relationships(entity_a, project, registry)

    # Same order
    assert results1 == results2 == results3


# --- Read-Only Tests ---


def test_get_relationships_does_not_mutate_registry():
    """S6-T16: Query does not mutate registry."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # Query
    get_relationships(entity_a, project, registry)

    # Relationship still present
    assert registry.get_relationship(rel.relationship_id) == rel


# --- Live-State Integration Tests ---


def test_get_relationships_after_add():
    """S6-T17: Added relationship immediately visible."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Before add
    results_before = get_relationships(entity_a, project, registry)
    assert len(results_before) == 0

    # Add
    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # After add: immediately visible
    results_after = get_relationships(entity_a, project, registry)
    assert rel in results_after


def test_get_relationships_after_delete():
    """S6-T18: Deleted relationship immediately absent."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # Before delete
    results_before = get_relationships(entity_a, project, registry)
    assert rel in results_before

    # Delete
    delete_relationship(rel.relationship_id, registry)

    # After delete: immediately absent
    results_after = get_relationships(entity_a, project, registry)
    assert rel not in results_after


def test_get_relationships_delete_readd():
    """S6-T19: Delete then re-add immediately visible again."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Add
    registry.add_relationship(rel)
    assert rel in get_relationships(entity_a, project, registry)

    # Delete
    delete_relationship(rel.relationship_id, registry)
    assert rel not in get_relationships(entity_a, project, registry)

    # Re-add
    registry.add_relationship(rel)
    assert rel in get_relationships(entity_a, project, registry)


# --- V2-005 Compatibility Tests ---


def test_get_relationships_v2_005_compatibility():
    """S6-T20: V2-005 EntityId/ProjectId types work correctly."""
    registry = RelationshipRegistry()

    # V2-005 types (NewType of str)
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    results = get_relationships(entity_a, project, registry)
    assert len(results) == 1
    assert results[0] == rel
