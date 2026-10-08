"""
V2-006 Step 7 Integration Tests — Cross-Operation Integration Coverage.

Tests integration of Steps 1-6 together, verifying that the complete
relationship domain behaves correctly as a unified system.

Contract: V2-006 Implementation Contract v1.0.1 Step 7
"""

import pytest

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    RelationshipRegistry,
    RelationshipType,
    create_relationship,
    delete_relationship,
    get_relationships,
)

# --- Full Lifecycle Integration ---


def test_full_lifecycle_create_add_query_delete():
    """
    I7-T01: Complete lifecycle integration.

    create → add → query → delete → query
    Verifies source and target queries throughout lifecycle.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create
    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Add
    registry.add_relationship(rel)

    # Query (source side)
    results_a = get_relationships(entity_a, project, registry)
    assert rel in results_a

    # Query (target side)
    results_b = get_relationships(entity_b, project, registry)
    assert rel in results_b

    # Delete
    delete_relationship(rel.relationship_id, registry)

    # Query after delete (source side)
    results_a_after = get_relationships(entity_a, project, registry)
    assert rel not in results_a_after

    # Query after delete (target side)
    results_b_after = get_relationships(entity_b, project, registry)
    assert rel not in results_b_after


def test_self_relationship_integration():
    """
    I7-T02: Self-relationship through full lifecycle.

    A→A created via create_relationship, added, queried (once), deleted.
    """
    registry = RelationshipRegistry()
    entity = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project = ProjectId("proj_001")

    # Create self-relationship via public API
    rel = create_relationship(entity, entity, RelationshipType("reflects_on"), project)
    assert rel.source_entity_id == entity
    assert rel.target_entity_id == entity

    # Add
    registry.add_relationship(rel)

    # Query: returned exactly once
    results = get_relationships(entity, project, registry)
    assert results.count(rel) == 1
    assert len(results) == 1

    # Delete
    delete_relationship(rel.relationship_id, registry)

    # Query after delete
    results_after = get_relationships(entity, project, registry)
    assert len(results_after) == 0


# --- Step 3 H1 v1.0.1 Integration (CRITICAL) ---


def test_duplicate_prevention_v1_0_1():
    """
    I7-T03: Duplicate prevention with Step 3 H1 v1.0.1 semantics.

    Two create calls with same tuple generate different IDs.
    Registry enforces tuple uniqueness (ValueError, not silent no-op).
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create twice with same semantic tuple
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Different IDs (Step 4 behavior)
    assert rel1.relationship_id != rel2.relationship_id

    # Add first: success
    registry.add_relationship(rel1)
    assert registry.get_relationship(rel1.relationship_id) == rel1

    # Add second while first is live: ValueError (H1 v1.0.1)
    with pytest.raises(ValueError, match="already exists with RelationshipId"):
        registry.add_relationship(rel2)

    # Final state before deletion
    assert registry.get_relationship(rel1.relationship_id) == rel1
    assert registry.get_relationship(rel2.relationship_id) is None


def test_tuple_release_after_delete():
    """
    I7-T04: Tuple uniqueness release after deletion.

    After deleting original, same semantic tuple can be added with new ID.
    Proves: live-state based uniqueness, no tombstone.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create two with same tuple
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    assert rel1.relationship_id != rel2.relationship_id

    # Add first
    registry.add_relationship(rel1)

    # Attempt add second: blocked
    with pytest.raises(ValueError):
        registry.add_relationship(rel2)

    # Delete original
    delete_relationship(rel1.relationship_id, registry)

    # Now add second: succeeds (tuple released)
    registry.add_relationship(rel2)

    # Final state
    assert registry.get_relationship(rel1.relationship_id) is None
    assert registry.get_relationship(rel2.relationship_id) == rel2


def test_same_id_idempotency():
    """
    I7-T05: Same relationship object added twice is idempotent.

    Second add is no-op. Query returns it once.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Add twice
    registry.add_relationship(rel)
    registry.add_relationship(rel)  # No-op

    # Query: returned once
    results = get_relationships(entity_a, project, registry)
    assert results.count(rel) == 1


def test_same_id_conflict():
    """
    I7-T06: Same RelationshipId with different content raises ValueError.

    Registry remains consistent after rejection.
    """
    registry = RelationshipRegistry()
    rel_id = "550e8400-e29b-41d4-a716-446655440099"

    # Create two relationships with same ID but different content
    # (bypassing create_relationship to simulate conflict)
    from anovel.domain.relationship import EntityRelationship, RelationshipId

    rel1 = EntityRelationship(
        relationship_id=RelationshipId(rel_id),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=RelationshipId(rel_id),  # Same ID
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440002"),  # Different
        target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440003"),  # Different
        relationship_type=RelationshipType("likes"),  # Different
    )

    # Add first
    registry.add_relationship(rel1)

    # Add conflicting: ValueError
    with pytest.raises(ValueError, match="already exists with different content"):
        registry.add_relationship(rel2)

    # Original remains
    assert registry.get_relationship(RelationshipId(rel_id)) == rel1


# --- Multiple Relationship Types ---


def test_multiple_relationship_types_same_entities():
    """
    I7-T07: Multiple relationship types between same entities allowed.

    Relationship type is part of uniqueness tuple.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create multiple types
    rel_knows = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel_likes = create_relationship(entity_a, entity_b, RelationshipType("likes"), project)
    rel_depends = create_relationship(
        entity_a, entity_b, RelationshipType("depends_on"), project
    )

    # All have distinct IDs
    assert len({rel_knows.relationship_id, rel_likes.relationship_id, rel_depends.relationship_id}) == 3

    # All accepted
    registry.add_relationship(rel_knows)
    registry.add_relationship(rel_likes)
    registry.add_relationship(rel_depends)

    # All queryable
    results = get_relationships(entity_a, project, registry)
    assert rel_knows in results
    assert rel_likes in results
    assert rel_depends in results
    assert len(results) == 3


def test_directionality():
    """
    I7-T08: Relationships are directed; A→B does not imply B→A.

    Both directions can coexist as distinct relationships.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create A→B
    rel_forward = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel_forward)

    # Query B: only target-side match
    results_b_before = get_relationships(entity_b, project, registry)
    assert rel_forward in results_b_before
    assert len(results_b_before) == 1

    # B→A does NOT automatically exist
    # Now explicitly create B→A
    rel_backward = create_relationship(entity_b, entity_a, RelationshipType("knows"), project)
    registry.add_relationship(rel_backward)  # Allowed (different tuple)

    # Both coexist
    assert registry.get_relationship(rel_forward.relationship_id) == rel_forward
    assert registry.get_relationship(rel_backward.relationship_id) == rel_backward

    # Query B now returns both (as source in backward, as target in forward)
    results_b_after = get_relationships(entity_b, project, registry)
    assert rel_forward in results_b_after
    assert rel_backward in results_b_after
    assert len(results_b_after) == 2


# --- Project Isolation ---


def test_project_isolation_integration():
    """
    I7-T09: Project isolation through full lifecycle.

    Equivalent relationships in different projects remain independent.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")

    # Create equivalent relationships in two projects
    rel_p1 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_001")
    )
    rel_p2 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_002")
    )

    # Both allowed
    registry.add_relationship(rel_p1)
    registry.add_relationship(rel_p2)

    # Query P1: only P1 relationship
    results_p1 = get_relationships(entity_a, ProjectId("proj_001"), registry)
    assert rel_p1 in results_p1
    assert rel_p2 not in results_p1

    # Query P2: only P2 relationship
    results_p2 = get_relationships(entity_a, ProjectId("proj_002"), registry)
    assert rel_p2 in results_p2
    assert rel_p1 not in results_p2

    # Delete P1 relationship
    delete_relationship(rel_p1.relationship_id, registry)

    # P2 unaffected
    assert registry.get_relationship(rel_p2.relationship_id) == rel_p2
    results_p2_after = get_relationships(entity_a, ProjectId("proj_002"), registry)
    assert rel_p2 in results_p2_after


def test_no_referential_integrity():
    """
    I7-T10: Relationships work with unknown EntityIds (no EntityRegistry dependency).

    Full lifecycle succeeds with typed but unknown entities.
    """
    registry = RelationshipRegistry()
    unknown_a = EntityId("00000000-0000-4000-8000-000000000001")
    unknown_b = EntityId("00000000-0000-4000-8000-000000000002")
    project = ProjectId("unknown_project")

    # Create with unknown entities
    rel = create_relationship(unknown_a, unknown_b, RelationshipType("knows"), project)

    # Add
    registry.add_relationship(rel)

    # Query
    results = get_relationships(unknown_a, project, registry)
    assert rel in results

    # Delete
    delete_relationship(rel.relationship_id, registry)

    # Query after delete
    results_after = get_relationships(unknown_a, project, registry)
    assert len(results_after) == 0


# --- Multiple Connected Relationships ---


def test_multiple_connected_relationships():
    """
    I7-T11: Multiple connected relationships query correctly.

    A→B, B→C, C→D, D→A: each entity's query returns only direct relationships.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    entity_d = EntityId("650e8400-e29b-41d4-a716-446655440003")
    project = ProjectId("proj_001")

    # Create chain
    rel_ab = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel_bc = create_relationship(entity_b, entity_c, RelationshipType("likes"), project)
    rel_cd = create_relationship(entity_c, entity_d, RelationshipType("depends"), project)
    rel_da = create_relationship(entity_d, entity_a, RelationshipType("rivals"), project)

    registry.add_relationship(rel_ab)
    registry.add_relationship(rel_bc)
    registry.add_relationship(rel_cd)
    registry.add_relationship(rel_da)

    # Query A: only relationships where A is source or target
    results_a = get_relationships(entity_a, project, registry)
    assert rel_ab in results_a  # A is source
    assert rel_da in results_a  # A is target
    assert rel_bc not in results_a  # A is neither
    assert rel_cd not in results_a  # A is neither
    assert len(results_a) == 2

    # Query B: its direct relationships only
    results_b = get_relationships(entity_b, project, registry)
    assert rel_ab in results_b  # B is target
    assert rel_bc in results_b  # B is source
    assert len(results_b) == 2


def test_no_transitive_traversal():
    """
    I7-T12: Query does not return transitive relationships.

    A→B, B→C: query A returns only A→B, not B→C.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    rel_ab = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel_bc = create_relationship(entity_b, entity_c, RelationshipType("knows"), project)

    registry.add_relationship(rel_ab)
    registry.add_relationship(rel_bc)

    # Query A: only A→B (not transitive B→C)
    results_a = get_relationships(entity_a, project, registry)
    assert rel_ab in results_a
    assert rel_bc not in results_a
    assert len(results_a) == 1


# --- Delete No Cascade ---


def test_delete_no_cascade():
    """
    I7-T13: Deleting one relationship does not cascade to related relationships.

    R1=A→B, R2=A→C, R3=D→B: delete R1 leaves R2, R3 intact.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    entity_d = EntityId("650e8400-e29b-41d4-a716-446655440003")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_c, RelationshipType("likes"), project)
    rel3 = create_relationship(entity_d, entity_b, RelationshipType("depends"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)
    registry.add_relationship(rel3)

    # Delete R1
    delete_relationship(rel1.relationship_id, registry)

    # R1 absent
    assert registry.get_relationship(rel1.relationship_id) is None

    # R2, R3 present
    assert registry.get_relationship(rel2.relationship_id) == rel2
    assert registry.get_relationship(rel3.relationship_id) == rel3

    # Queries consistent
    results_a = get_relationships(entity_a, project, registry)
    assert rel1 not in results_a
    assert rel2 in results_a

    results_b = get_relationships(entity_b, project, registry)
    assert rel1 not in results_b
    assert rel3 in results_b


# --- Live-State Integration ---


def test_live_state_integration():
    """
    I7-T14: Complete live-state integration: create→add→query→delete→query→re-add→query.

    No cache lag, no tombstone visibility.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Create: not yet in registry
    results_0 = get_relationships(entity_a, project, registry)
    assert len(results_0) == 0

    # Add: visible
    registry.add_relationship(rel)
    results_1 = get_relationships(entity_a, project, registry)
    assert rel in results_1

    # Delete: absent
    delete_relationship(rel.relationship_id, registry)
    results_2 = get_relationships(entity_a, project, registry)
    assert rel not in results_2

    # Re-add: visible
    registry.add_relationship(rel)
    results_3 = get_relationships(entity_a, project, registry)
    assert rel in results_3


def test_determinism_integration():
    """
    I7-T15: Deterministic ordering across multiple queries without registry changes.

    Same query returns same order.
    """
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
    results_1 = get_relationships(entity_a, project, registry)
    results_2 = get_relationships(entity_a, project, registry)
    results_3 = get_relationships(entity_a, project, registry)

    # Same order
    assert results_1 == results_2 == results_3


# --- Large Relationship Set ---


def test_large_relationship_set():
    """
    I7-T16: Large relationship set (100 relationships) with correct filtering.

    Verifies project filtering, source/target filtering, no duplicates, expected count.
    """
    registry = RelationshipRegistry()
    project_1 = ProjectId("proj_001")
    project_2 = ProjectId("proj_002")

    # Target entity for queries
    target_entity = EntityId("550e8400-e29b-41d4-a716-446655440000")

    # Create 50 relationships in P1 involving target_entity
    p1_relationships = []
    for i in range(50):
        source = EntityId(f"550e8400-e29b-41d4-a716-4466554400{i:02d}")
        rel = create_relationship(source, target_entity, RelationshipType(f"type_{i}"), project_1)
        registry.add_relationship(rel)
        p1_relationships.append(rel)

    # Create 50 relationships in P2 involving target_entity
    p2_relationships = []
    for i in range(50):
        source = EntityId(f"650e8400-e29b-41d4-a716-4466554400{i:02d}")
        rel = create_relationship(source, target_entity, RelationshipType(f"type_{i}"), project_2)
        registry.add_relationship(rel)
        p2_relationships.append(rel)

    # Query P1: exactly 50 from P1
    results_p1 = get_relationships(target_entity, project_1, registry)
    assert len(results_p1) == 50
    assert all(r in p1_relationships for r in results_p1)
    assert all(r.project_id == project_1 for r in results_p1)

    # Query P2: exactly 50 from P2
    results_p2 = get_relationships(target_entity, project_2, registry)
    assert len(results_p2) == 50
    assert all(r in p2_relationships for r in results_p2)
    assert all(r.project_id == project_2 for r in results_p2)

    # No duplicates
    assert len(set(results_p1)) == 50
    assert len(set(results_p2)) == 50


def test_mixed_project_large_set():
    """
    I7-T17: Mixed-project large set verifies no cross-project leakage.

    Explicit expected sets verification.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_1 = ProjectId("proj_001")
    project_2 = ProjectId("proj_002")

    # Create relationships in both projects
    p1_rels = []
    for i in range(30):
        target = EntityId(f"550e8400-e29b-41d4-a716-4466554400{i:02d}")
        rel = create_relationship(entity_a, target, RelationshipType(f"p1_type_{i}"), project_1)
        registry.add_relationship(rel)
        p1_rels.append(rel)

    p2_rels = []
    for i in range(20):
        target = EntityId(f"650e8400-e29b-41d4-a716-4466554400{i:02d}")
        rel = create_relationship(entity_a, target, RelationshipType(f"p2_type_{i}"), project_2)
        registry.add_relationship(rel)
        p2_rels.append(rel)

    # Query P1
    results_p1 = get_relationships(entity_a, project_1, registry)
    assert len(results_p1) == 30
    assert set(results_p1) == set(p1_rels)
    # Verify no P2 leakage
    assert all(r not in p2_rels for r in results_p1)

    # Query P2
    results_p2 = get_relationships(entity_a, project_2, registry)
    assert len(results_p2) == 20
    assert set(results_p2) == set(p2_rels)
    # Verify no P1 leakage
    assert all(r not in p1_rels for r in results_p2)


# --- Additional Integration Scenarios ---


def test_immutability_through_lifecycle():
    """
    I7-T18: Immutability preserved through full lifecycle.

    Created and queried relationships remain immutable.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    registry.add_relationship(rel)

    # Query
    results = get_relationships(entity_a, project, registry)
    queried_rel = results[0]

    # Attempt mutation
    with pytest.raises(AttributeError):
        queried_rel.relationship_type = RelationshipType("different")  # type: ignore


def test_relationship_type_normalization():
    """
    I7-T19: Relationship type normalization through Steps 1→4→Registry→6.

    Whitespace trimmed by Step 1 validation, preserved through lifecycle.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create with whitespace
    rel = create_relationship(entity_a, entity_b, RelationshipType("  knows  "), project)

    # Stored type is normalized
    assert rel.relationship_type == RelationshipType("knows")

    # Add and query
    registry.add_relationship(rel)
    results = get_relationships(entity_a, project, registry)

    # Queried relationship has normalized type
    assert results[0].relationship_type == RelationshipType("knows")


def test_delete_idempotency_integration():
    """
    I7-T20: Delete idempotency through public API with existing relationships.

    Multiple deletes of same ID with other relationships present.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("650e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    # Create multiple relationships
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_c, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Delete rel1 multiple times
    delete_relationship(rel1.relationship_id, registry)
    delete_relationship(rel1.relationship_id, registry)  # Idempotent
    delete_relationship(rel1.relationship_id, registry)  # Idempotent

    # rel2 unchanged
    assert registry.get_relationship(rel2.relationship_id) == rel2

    # Queries correct
    results = get_relationships(entity_a, project, registry)
    assert rel1 not in results
    assert rel2 in results
