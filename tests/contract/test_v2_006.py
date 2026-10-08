"""
V2-006 Consolidated Contract Tests — Final EntityRelationship Contract.

These tests verify the complete V2-006 contract as a unified whole, providing
consolidated coverage beyond the granular step-specific tests.

Contract: V2-006 Implementation Contract v1.0.1
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from anovel.domain.identity import EntityId, ProjectId
from anovel.domain.relationship import (
    EntityRelationship,
    RelationshipId,
    RelationshipRegistry,
    RelationshipType,
    create_relationship,
    delete_relationship,
    get_relationships,
    validate_relationship_type,
)

# --- Group A: Types / Model ---


def test_relationship_id_contract():
    """C-T01: RelationshipId is NewType of string (UUID v4)."""
    rel_id = RelationshipId("550e8400-e29b-41d4-a716-446655440000")
    assert isinstance(rel_id, str)
    # RelationshipId is NewType, runtime is string


def test_relationship_type_extensibility():
    """C-T02: RelationshipType accepts arbitrary strings (not enum)."""
    # Common relationship types
    assert RelationshipType("knows") == "knows"
    assert RelationshipType("parent_of") == "parent_of"

    # Arbitrary custom types allowed
    assert RelationshipType("custom_relationship_123") == "custom_relationship_123"
    assert RelationshipType("asdf") == "asdf"


def test_relationship_type_normalization_and_rejection():
    """C-T03: RelationshipType normalized (whitespace trimmed) but rejects empty."""
    # Normalization
    assert validate_relationship_type("  knows  ") == "knows"
    assert validate_relationship_type("\tparent\n") == "parent"

    # Rejection
    with pytest.raises(ValueError, match="empty"):
        validate_relationship_type("")

    with pytest.raises(ValueError, match="empty"):
        validate_relationship_type("   ")


def test_entity_relationship_five_field_contract():
    """C-T04: EntityRelationship has exactly 5 required fields."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    # Exactly 5 fields
    assert rel.relationship_id == RelationshipId("550e8400-e29b-41d4-a716-446655440000")
    assert rel.project_id == ProjectId("proj_001")
    assert rel.source_entity_id == EntityId("650e8400-e29b-41d4-a716-446655440001")
    assert rel.target_entity_id == EntityId("750e8400-e29b-41d4-a716-446655440002")
    assert rel.relationship_type == RelationshipType("knows")


def test_entity_relationship_immutability():
    """C-T05: EntityRelationship is immutable (frozen dataclass)."""
    rel = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    with pytest.raises(AttributeError):
        rel.relationship_type = RelationshipType("different")  # type: ignore


def test_self_relationship_allowed():
    """C-T06: Self-relationships (A→A) are allowed."""
    entity = EntityId("550e8400-e29b-41d4-a716-446655440000")
    rel = EntityRelationship(
        relationship_id=RelationshipId("650e8400-e29b-41d4-a716-446655440001"),
        project_id=ProjectId("proj_001"),
        source_entity_id=entity,
        target_entity_id=entity,
        relationship_type=RelationshipType("reflects_on"),
    )

    assert rel.source_entity_id == rel.target_entity_id


# --- Group B: Schema ---


def test_schema_meta_validation():
    """C-T07: entity-relationship.schema.json is valid Draft 2020-12."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())

    # Meta-schema validation
    Draft202012Validator.check_schema(schema)


def test_valid_relationship_payload_validates():
    """C-T08: Valid EntityRelationship payload passes schema validation."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    payload = {
        "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
        "project_id": "proj_001",
        "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
        "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
        "relationship_type": "knows",
    }

    validator.validate(payload)  # Should not raise


def test_all_five_fields_required():
    """C-T09: Schema requires all 5 fields (no optional fields)."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    # Missing relationship_id
    with pytest.raises(ValidationError):
        validator.validate({
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "knows",
        })

    # Missing relationship_type
    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
        })


def test_additional_properties_rejected():
    """C-T10: Schema rejects additional properties (no metadata/timestamps)."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    payload_with_extra = {
        "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
        "project_id": "proj_001",
        "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
        "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
        "relationship_type": "knows",
        "metadata": {"extra": "data"},  # Not allowed
    }

    with pytest.raises(ValidationError):
        validator.validate(payload_with_extra)


def test_invalid_relationship_id_rejected():
    """C-T11: Schema rejects invalid relationship_id (non-UUID v4)."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    # Not a UUID
    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "not-a-uuid",
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "knows",
        })

    # UUID v1 (not v4)
    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-11d4-a716-446655440000",  # v1
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "knows",
        })


def test_invalid_source_entity_id_rejected():
    """C-T12: Schema rejects invalid source_entity_id."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
            "project_id": "proj_001",
            "source_entity_id": "invalid",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "knows",
        })


def test_invalid_target_entity_id_rejected():
    """C-T13: Schema rejects invalid target_entity_id."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "invalid",
            "relationship_type": "knows",
        })


def test_project_id_schema_semantics():
    """C-T14: Schema enforces project_id as non-empty string."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    # Empty project_id
    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
            "project_id": "",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "knows",
        })


def test_relationship_type_schema_semantics():
    """C-T15: Schema enforces relationship_type as non-empty string (not enum)."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    # Arbitrary types allowed
    validator.validate({
        "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
        "project_id": "proj_001",
        "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
        "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
        "relationship_type": "custom_type_999",
    })

    # Empty not allowed
    with pytest.raises(ValidationError):
        validator.validate({
            "relationship_id": "550e8400-e29b-41d4-a716-446655440000",
            "project_id": "proj_001",
            "source_entity_id": "650e8400-e29b-41d4-a716-446655440001",
            "target_entity_id": "750e8400-e29b-41d4-a716-446655440002",
            "relationship_type": "",
        })


def test_serialization_round_trip():
    """C-T16: EntityRelationship serialization round-trip preserves all fields."""
    schema_path = Path("specs/schemas/entity-relationship.schema.json")
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)

    # Original
    rel = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    # Serialize
    payload = {
        "relationship_id": rel.relationship_id,
        "project_id": rel.project_id,
        "source_entity_id": rel.source_entity_id,
        "target_entity_id": rel.target_entity_id,
        "relationship_type": rel.relationship_type,
    }

    # Validate
    validator.validate(payload)

    # Reconstruct
    rel_reconstructed = EntityRelationship(
        relationship_id=RelationshipId(payload["relationship_id"]),
        project_id=ProjectId(payload["project_id"]),
        source_entity_id=EntityId(payload["source_entity_id"]),
        target_entity_id=EntityId(payload["target_entity_id"]),
        relationship_type=RelationshipType(payload["relationship_type"]),
    )

    # Verify equality
    assert rel_reconstructed == rel


# --- Group C: Registry ---


def test_same_id_same_content_is_noop():
    """C-T17: Registry add with same ID and same content is no-op."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    registry.add_relationship(rel)  # No-op

    # Query returns once
    results = get_relationships(rel.source_entity_id, rel.project_id, registry)
    assert results.count(rel) == 1


def test_same_id_different_content_raises_valueerror():
    """C-T18: Registry add with same ID but different content raises ValueError."""
    registry = RelationshipRegistry()

    rel1 = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    rel2 = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),  # Same ID
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("850e8400-e29b-41d4-a716-446655440003"),  # Different
        target_entity_id=EntityId("950e8400-e29b-41d4-a716-446655440004"),  # Different
        relationship_type=RelationshipType("likes"),  # Different
    )

    registry.add_relationship(rel1)

    with pytest.raises(ValueError, match="already exists with different content"):
        registry.add_relationship(rel2)


def test_different_id_same_live_tuple_raises_valueerror():
    """
    C-T19: Different ID + same LIVE tuple raises ValueError (H1 v1.0.1).

    CRITICAL: This is the corrected H1 semantic.
    Historical v1.0.0 silent no-op is prohibited.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    # Create twice: different IDs
    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    assert rel1.relationship_id != rel2.relationship_id

    # Add first
    registry.add_relationship(rel1)

    # Add second while first is live: ValueError (NOT silent no-op)
    with pytest.raises(ValueError, match="already exists with RelationshipId"):
        registry.add_relationship(rel2)


def test_same_tuple_different_project_allowed():
    """C-T20: Same semantic tuple in different projects is allowed."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")

    rel_p1 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_001")
    )
    rel_p2 = create_relationship(
        entity_a, entity_b, RelationshipType("knows"), ProjectId("proj_002")
    )

    # Both allowed
    registry.add_relationship(rel_p1)
    registry.add_relationship(rel_p2)

    assert registry.get_relationship(rel_p1.relationship_id) == rel_p1
    assert registry.get_relationship(rel_p2.relationship_id) == rel_p2


def test_remove_existing_relationship():
    """C-T21: Registry can remove existing relationship."""
    registry = RelationshipRegistry()
    rel = EntityRelationship(
        relationship_id=RelationshipId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_001"),
        source_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
        target_entity_id=EntityId("750e8400-e29b-41d4-a716-446655440002"),
        relationship_type=RelationshipType("knows"),
    )

    registry.add_relationship(rel)
    registry.remove_relationship(rel.relationship_id)

    assert registry.get_relationship(rel.relationship_id) is None


def test_remove_missing_is_noop():
    """C-T22: Registry remove of missing relationship is no-op."""
    registry = RelationshipRegistry()
    unknown_id = RelationshipId("00000000-0000-4000-8000-000000000099")

    # Should not raise
    registry.remove_relationship(unknown_id)


def test_tuple_released_after_deletion():
    """
    C-T23: Tuple released after deletion (H1 v1.0.1).

    CRITICAL: After deleting original, same tuple can be added with new ID.
    Proves live-state uniqueness, no tombstone.
    """
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    registry.add_relationship(rel1)

    # Blocked while rel1 is live
    with pytest.raises(ValueError):
        registry.add_relationship(rel2)

    # Delete rel1
    delete_relationship(rel1.relationship_id, registry)

    # Now rel2 can be added (tuple released)
    registry.add_relationship(rel2)

    assert registry.get_relationship(rel1.relationship_id) is None
    assert registry.get_relationship(rel2.relationship_id) == rel2


# --- Group D: Public Operations ---


def test_create_generates_uuid_v4():
    """C-T24: create_relationship generates fresh UUID v4 every time."""
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)

    # Different IDs
    assert rel1.relationship_id != rel2.relationship_id

    # UUID v4 format (version nibble = 4)
    assert rel1.relationship_id[14] == "4"
    assert rel2.relationship_id[14] == "4"


def test_create_normalizes_relationship_type():
    """C-T25: create_relationship normalizes relationship_type."""
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    project = ProjectId("proj_001")

    rel = create_relationship(entity_a, entity_b, RelationshipType("  knows  "), project)

    assert rel.relationship_type == "knows"


def test_create_no_referential_integrity():
    """C-T26: create_relationship works with unknown EntityIds."""
    unknown_a = EntityId("00000000-0000-4000-8000-000000000001")
    unknown_b = EntityId("00000000-0000-4000-8000-000000000002")
    project = ProjectId("unknown_project")

    # Should not require entity existence
    rel = create_relationship(unknown_a, unknown_b, RelationshipType("knows"), project)

    assert rel.source_entity_id == unknown_a
    assert rel.target_entity_id == unknown_b


def test_delete_is_idempotent_and_no_cascade():
    """C-T27: delete_relationship is idempotent and does not cascade."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("750e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    rel1 = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel2 = create_relationship(entity_a, entity_c, RelationshipType("likes"), project)

    registry.add_relationship(rel1)
    registry.add_relationship(rel2)

    # Delete rel1 multiple times (idempotent)
    delete_relationship(rel1.relationship_id, registry)
    delete_relationship(rel1.relationship_id, registry)
    delete_relationship(rel1.relationship_id, registry)

    # rel2 unaffected (no cascade)
    assert registry.get_relationship(rel2.relationship_id) == rel2


def test_query_returns_source_or_target():
    """C-T28: get_relationships returns relationships where entity is source OR target."""
    registry = RelationshipRegistry()
    entity_a = EntityId("550e8400-e29b-41d4-a716-446655440000")
    entity_b = EntityId("650e8400-e29b-41d4-a716-446655440001")
    entity_c = EntityId("750e8400-e29b-41d4-a716-446655440002")
    project = ProjectId("proj_001")

    # A→B, B→C
    rel_ab = create_relationship(entity_a, entity_b, RelationshipType("knows"), project)
    rel_bc = create_relationship(entity_b, entity_c, RelationshipType("likes"), project)

    registry.add_relationship(rel_ab)
    registry.add_relationship(rel_bc)

    # Query B: returns both (target in rel_ab, source in rel_bc)
    results_b = get_relationships(entity_b, project, registry)
    assert rel_ab in results_b
    assert rel_bc in results_b
    assert len(results_b) == 2


def test_query_project_isolation():
    """C-T29: get_relationships enforces project isolation."""
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

    # Query P1: only P1
    results_p1 = get_relationships(entity_a, ProjectId("proj_001"), registry)
    assert rel_p1 in results_p1
    assert rel_p2 not in results_p1


def test_query_returns_empty_list_when_none():
    """C-T30: get_relationships returns [] when no matches."""
    registry = RelationshipRegistry()
    unknown = EntityId("00000000-0000-4000-8000-000000000099")
    project = ProjectId("proj_001")

    results = get_relationships(unknown, project, registry)
    assert results == []
    assert isinstance(results, list)
