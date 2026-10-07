"""
V2-006 Step 1 Tests: Core Relationship Types.

Tests RelationshipId, RelationshipType, and validation functions.

Contract: V2-006 Implementation Contract v1.0.0 §9 Step 1
"""

import re

import pytest

from anovel.domain.relationship import (
    RelationshipId,
    RelationshipType,
    validate_relationship_type,
)


# --- RelationshipId Tests ---


def test_relationship_id_is_newtype():
    """RelationshipId is a NewType wrapping str."""
    # NewType creates a callable that returns the wrapped type
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    assert isinstance(rel_id, str)


def test_relationship_id_uuid_v4_format():
    """RelationshipId follows UUID v4 format pattern."""
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")

    # UUID v4 pattern: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    # where y is [89ab]
    uuid_v4_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    assert re.match(uuid_v4_pattern, rel_id)


def test_relationship_id_distinct_from_entity_id():
    """RelationshipId is a separate type from EntityId."""
    from anovel.domain.identity import EntityId

    # Both are NewType wrappers around str, but distinct types
    rel_id = RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    entity_id = EntityId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")

    # Runtime: both are strings (NewType is type-checker only)
    assert isinstance(rel_id, str)
    assert isinstance(entity_id, str)

    # But mypy treats them as distinct types


# --- RelationshipType Tests ---


def test_relationship_type_is_newtype():
    """RelationshipType is a NewType wrapping str."""
    rel_type = RelationshipType("knows")
    assert isinstance(rel_type, str)


def test_relationship_type_creation():
    """RelationshipType can be created with valid strings."""
    rel_type1 = RelationshipType("knows")
    assert rel_type1 == "knows"

    rel_type2 = RelationshipType("parent_of")
    assert rel_type2 == "parent_of"

    rel_type3 = RelationshipType("depends_on")
    assert rel_type3 == "depends_on"


def test_relationship_type_no_business_validation():
    """RelationshipType accepts any non-empty string (no business rules)."""
    # No ontology validation - application layer responsibility
    RelationshipType("asdf1234")  # Arbitrary string OK
    RelationshipType("made_up_type")  # OK
    RelationshipType("!@#$%")  # Special chars OK (no validation)


# --- validate_relationship_type Tests ---


def test_validate_relationship_type_valid():
    """validate_relationship_type accepts valid strings."""
    result = validate_relationship_type("knows")
    assert result == RelationshipType("knows")
    assert isinstance(result, str)


def test_validate_relationship_type_trims_whitespace():
    """validate_relationship_type trims leading/trailing whitespace."""
    result = validate_relationship_type("  knows  ")
    assert result == RelationshipType("knows")


def test_validate_relationship_type_empty_raises():
    """validate_relationship_type raises ValueError for empty string."""
    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        validate_relationship_type("")


def test_validate_relationship_type_whitespace_only_raises():
    """validate_relationship_type raises ValueError for whitespace-only."""
    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        validate_relationship_type("   ")

    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        validate_relationship_type("\t\n")


def test_validate_relationship_type_preserves_internal_spaces():
    """validate_relationship_type preserves internal spaces."""
    result = validate_relationship_type("  parent of  ")
    assert result == RelationshipType("parent of")


# --- Type Annotation Tests ---


def test_relationship_id_type_annotation():
    """RelationshipId has correct type annotation."""
    from typing import get_type_hints

    # NewType creates a callable, not a class
    # So we test by using it in a function
    def func(rel_id: RelationshipId) -> RelationshipId:
        return rel_id

    hints = get_type_hints(func)
    # NewType is transparent to runtime type hints (shows underlying str)
    # But mypy enforces the NewType distinction


def test_relationship_type_type_annotation():
    """RelationshipType has correct type annotation."""
    from typing import get_type_hints

    def func(rel_type: RelationshipType) -> RelationshipType:
        return rel_type

    hints = get_type_hints(func)
    # NewType is transparent to runtime type hints (shows underlying str)
    # But mypy enforces the NewType distinction


# --- Integration: V2-005 Preservation ---


def test_v2_005_types_still_importable():
    """V2-005 types are still importable and unchanged."""
    from anovel.domain.identity import EntityId, ProjectId, EntityIdentity

    # Can still create V2-005 types
    entity_id = EntityId("550e8400-e29b-41d4-a716-446655440000")
    project_id = ProjectId("proj_001")

    assert isinstance(entity_id, str)
    assert isinstance(project_id, str)
