"""
V2-005 Step 5 Contract Tests: create_identity and rename_identity.

Tests for:
- create_identity operation
- rename_identity operation

Contract: V2-005 Implementation Contract v1.1.0 §3.1, §3.2
Baseline: 637ab05eb4e1bc19815a6e5c766a529a6ae7d2eb
"""

from uuid import UUID

import pytest

from anovel.domain.identity import (
    EntityId,
    EntityIdentity,
    ProjectId,
    create_identity,
    rename_identity,
)


# --- create_identity Tests ---


def test_create_identity_valid_creation():
    """create_identity creates valid EntityIdentity."""
    entity = create_identity(
        ProjectId("proj_01"),
        "张三",
        entity_type="CHARACTER",
    )

    assert isinstance(entity, EntityIdentity)
    assert entity.project_id == ProjectId("proj_01")
    assert entity.canonical_name == "张三"
    assert entity.aliases == frozenset()
    assert entity.entity_type == "CHARACTER"


def test_create_identity_generates_fresh_uuid_v4():
    """create_identity generates fresh UUID v4 for entity_id."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    # Verify it's a valid UUID
    parsed = UUID(entity.entity_id)
    assert parsed.version == 4


def test_create_identity_repeated_same_input_gets_different_ids():
    """Repeated create_identity with same input produces different IDs."""
    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "张三")

    assert entity1.entity_id != entity2.entity_id


def test_create_identity_aliases_initially_empty():
    """create_identity sets aliases to empty frozenset."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    assert entity.aliases == frozenset()
    assert len(entity.aliases) == 0


def test_create_identity_canonical_name_outer_trim():
    """create_identity trims outer whitespace from canonical_name."""
    entity = create_identity(ProjectId("proj_01"), "  张三  ")
    assert entity.canonical_name == "张三"


def test_create_identity_empty_name_raises():
    """create_identity raises ValueError for empty canonical_name."""
    with pytest.raises(ValueError, match="canonical_name cannot be empty"):
        create_identity(ProjectId("proj_01"), "")


def test_create_identity_whitespace_only_name_raises():
    """create_identity raises ValueError for whitespace-only canonical_name."""
    with pytest.raises(ValueError, match="canonical_name cannot be empty"):
        create_identity(ProjectId("proj_01"), "   ")


def test_create_identity_empty_project_id_raises():
    """create_identity raises ValueError for empty project_id."""
    with pytest.raises(ValueError, match="project_id cannot be empty"):
        create_identity(ProjectId(""), "张三")


def test_create_identity_whitespace_only_project_id_raises():
    """create_identity raises ValueError for whitespace-only project_id."""
    with pytest.raises(ValueError, match="project_id cannot be empty"):
        create_identity(ProjectId("   "), "张三")


def test_create_identity_invalid_entity_type_empty_raises():
    """create_identity raises ValueError for empty entity_type."""
    with pytest.raises(ValueError, match="entity_type cannot be empty"):
        create_identity(ProjectId("proj_01"), "张三", entity_type="")


def test_create_identity_invalid_entity_type_whitespace_raises():
    """create_identity raises ValueError for whitespace-only entity_type."""
    with pytest.raises(ValueError, match="entity_type cannot be empty"):
        create_identity(ProjectId("proj_01"), "张三", entity_type="   ")


def test_create_identity_entity_type_none_allowed():
    """create_identity allows entity_type=None."""
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type=None)
    assert entity.entity_type is None


def test_create_identity_without_entity_type():
    """create_identity works without entity_type argument."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    assert entity.entity_type is None


def test_create_identity_preserves_project_id():
    """create_identity preserves exact project_id."""
    pid = ProjectId("my_project_123")
    entity = create_identity(pid, "张三")
    assert entity.project_id == pid


def test_create_identity_preserves_entity_type():
    """create_identity preserves exact entity_type."""
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="LOCATION")
    assert entity.entity_type == "LOCATION"


def test_create_identity_is_pure_function():
    """create_identity has no side effects (pure function)."""
    # Calling create_identity should not affect global state
    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "李四")

    # Both entities should exist independently
    assert entity1.canonical_name == "张三"
    assert entity2.canonical_name == "李四"


# --- rename_identity Tests ---


def test_rename_identity_preserves_entity_id():
    """rename_identity preserves entity_id."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三丰")

    assert renamed.entity_id == original.entity_id


def test_rename_identity_preserves_project_id():
    """rename_identity preserves project_id."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三丰")

    assert renamed.project_id == original.project_id


def test_rename_identity_preserves_entity_type():
    """rename_identity preserves entity_type."""
    original = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    renamed = rename_identity(original, "张三丰")

    assert renamed.entity_type == original.entity_type


def test_rename_identity_preserves_existing_aliases():
    """rename_identity preserves existing aliases."""
    # Create entity with existing aliases (via frozen constructor for test)
    original = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张", "张总"]),
    )

    renamed = rename_identity(original, "张三丰")

    assert "老张" in renamed.aliases
    assert "张总" in renamed.aliases


def test_rename_identity_old_canonical_becomes_alias():
    """rename_identity adds old canonical_name to aliases."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三丰")

    assert "张三" in renamed.aliases


def test_rename_identity_old_canonical_already_alias_no_duplicate():
    """rename_identity handles old canonical already in aliases (no duplicate)."""
    # Create entity with canonical name already in aliases
    original = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["张三", "老张"]),  # "张三" already there
    )

    renamed = rename_identity(original, "张三丰")

    # "张三" should still be in aliases, no duplicate
    assert "张三" in renamed.aliases
    # frozenset naturally deduplicates
    assert list(renamed.aliases).count("张三") == 1


def test_rename_identity_trims_new_canonical_outer_whitespace():
    """rename_identity trims outer whitespace from new_canonical_name."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "  张三丰  ")

    assert renamed.canonical_name == "张三丰"


def test_rename_identity_empty_new_name_raises():
    """rename_identity raises ValueError for empty new_canonical_name."""
    original = create_identity(ProjectId("proj_01"), "张三")

    with pytest.raises(ValueError, match="new_canonical_name cannot be empty"):
        rename_identity(original, "")


def test_rename_identity_whitespace_only_new_name_raises():
    """rename_identity raises ValueError for whitespace-only new_canonical_name."""
    original = create_identity(ProjectId("proj_01"), "张三")

    with pytest.raises(ValueError, match="new_canonical_name cannot be empty"):
        rename_identity(original, "   ")


def test_rename_identity_original_object_remains_unchanged():
    """rename_identity does not mutate original EntityIdentity."""
    original = create_identity(ProjectId("proj_01"), "张三")
    original_id = original.entity_id
    original_name = original.canonical_name
    original_aliases = original.aliases

    renamed = rename_identity(original, "张三丰")

    # Original should be completely unchanged
    assert original.entity_id == original_id
    assert original.canonical_name == original_name
    assert original.aliases == original_aliases
    assert original.canonical_name == "张三"  # Still old name


def test_rename_identity_original_unchanged_after_value_error():
    """rename_identity does not affect original if ValueError raised."""
    original = create_identity(ProjectId("proj_01"), "张三")
    original_canonical = original.canonical_name

    try:
        rename_identity(original, "")  # Should raise
    except ValueError:
        pass

    # Original should be unchanged
    assert original.canonical_name == original_canonical


def test_rename_identity_returns_new_object():
    """rename_identity returns a new EntityIdentity object."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三丰")

    assert renamed is not original  # Different objects
    assert renamed != original  # Different values


def test_rename_identity_updates_canonical_name():
    """rename_identity updates canonical_name to new value."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三丰")

    assert renamed.canonical_name == "张三丰"


def test_rename_identity_chain():
    """rename_identity can be chained multiple times."""
    entity1 = create_identity(ProjectId("proj_01"), "A")
    entity2 = rename_identity(entity1, "B")
    entity3 = rename_identity(entity2, "C")

    # All should have same entity_id
    assert entity1.entity_id == entity2.entity_id == entity3.entity_id

    # Final entity should have all previous names as aliases
    assert entity3.canonical_name == "C"
    assert "A" in entity3.aliases
    assert "B" in entity3.aliases


def test_rename_identity_to_same_name():
    """rename_identity to same name still adds old name to aliases (contract behavior)."""
    original = create_identity(ProjectId("proj_01"), "张三")
    renamed = rename_identity(original, "张三")

    # Per contract: always returns new object, always adds old canonical to aliases
    assert renamed is not original
    assert renamed.canonical_name == "张三"
    assert "张三" in renamed.aliases  # Old canonical added even if same


# --- Integration Tests ---


def test_create_and_rename_integration():
    """Integration: create_identity followed by rename_identity."""
    entity = create_identity(
        ProjectId("proj_01"),
        "Original Name",
        entity_type="CHARACTER",
    )

    renamed = rename_identity(entity, "New Name")

    assert renamed.entity_id == entity.entity_id
    assert renamed.canonical_name == "New Name"
    assert "Original Name" in renamed.aliases
    assert renamed.entity_type == "CHARACTER"
