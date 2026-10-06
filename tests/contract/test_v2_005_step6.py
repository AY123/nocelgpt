"""
V2-005 Step 6 Contract Tests: add_alias and remove_alias.

Tests for:
- add_alias operation
- remove_alias operation

Contract: V2-005 Implementation Contract v1.1.0 §3.3, §3.4
Baseline: e87477b9fd0e71609322f336de5793ca9d9f1fbb
"""

import pytest

from anovel.domain.identity import (
    EntityId,
    EntityIdentity,
    ProjectId,
    add_alias,
    create_identity,
    remove_alias,
)


# --- add_alias Tests ---


def test_add_alias_adds_to_set():
    """add_alias adds alias to aliases set."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    assert "老张" in with_alias.aliases


def test_add_alias_preserves_entity_id():
    """add_alias preserves entity_id."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    assert with_alias.entity_id == entity.entity_id


def test_add_alias_preserves_project_id():
    """add_alias preserves project_id."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    assert with_alias.project_id == entity.project_id


def test_add_alias_preserves_canonical_name():
    """add_alias preserves canonical_name."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    assert with_alias.canonical_name == entity.canonical_name


def test_add_alias_preserves_entity_type():
    """add_alias preserves entity_type."""
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    with_alias = add_alias(entity, "老张")

    assert with_alias.entity_type == entity.entity_type


def test_add_alias_preserves_existing_aliases():
    """add_alias preserves existing aliases."""
    entity = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张", "张总"]),
    )

    with_new_alias = add_alias(entity, "三哥")

    assert "老张" in with_new_alias.aliases
    assert "张总" in with_new_alias.aliases
    assert "三哥" in with_new_alias.aliases


def test_add_alias_trims_outer_whitespace():
    """add_alias trims outer whitespace from alias."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "  老张  ")

    assert "老张" in with_alias.aliases
    assert "  老张  " not in with_alias.aliases


def test_add_alias_empty_raises():
    """add_alias raises ValueError for empty alias."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    with pytest.raises(ValueError, match="alias cannot be empty"):
        add_alias(entity, "")


def test_add_alias_whitespace_only_raises():
    """add_alias raises ValueError for whitespace-only alias."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    with pytest.raises(ValueError, match="alias cannot be empty"):
        add_alias(entity, "   ")


def test_add_alias_idempotent_exact_match():
    """add_alias is idempotent for exact duplicate."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias1 = add_alias(entity, "老张")
    with_alias2 = add_alias(with_alias1, "老张")

    # Should have same aliases
    assert with_alias1.aliases == with_alias2.aliases
    assert list(with_alias2.aliases).count("老张") == 1


def test_add_alias_idempotent_normalized_duplicate():
    """add_alias is idempotent for normalized duplicate (case/whitespace)."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias1 = add_alias(entity, "zhang")
    with_alias2 = add_alias(with_alias1, "ZHANG")  # Different case

    # Should be idempotent (normalized to same)
    assert len(with_alias2.aliases) == 1
    # Original form preserved
    assert "zhang" in with_alias2.aliases


def test_add_alias_normalized_comparison_ascii():
    """add_alias uses normalize_for_lookup for ASCII comparison."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias1 = add_alias(entity, "Smith")
    with_alias2 = add_alias(with_alias1, "smith")  # Lowercase

    # Should detect as duplicate
    assert len(with_alias2.aliases) == 1
    assert "Smith" in with_alias2.aliases  # Original form kept


def test_add_alias_normalized_comparison_whitespace():
    """add_alias detects whitespace-normalized duplicates."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias1 = add_alias(entity, "Zhang  San")  # Double space
    with_alias2 = add_alias(with_alias1, "Zhang San")  # Single space

    # After normalization, these are equivalent
    assert len(with_alias2.aliases) == 1


def test_add_alias_chinese_case_sensitive():
    """add_alias treats Chinese as case-sensitive (no lowercase)."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias1 = add_alias(entity, "张三")
    with_alias2 = add_alias(with_alias1, "张三")  # Identical

    # Should be idempotent
    assert len(with_alias2.aliases) == 1


def test_add_alias_returns_new_object():
    """add_alias returns new EntityIdentity object."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    assert with_alias is not entity
    assert with_alias != entity


def test_add_alias_original_unchanged():
    """add_alias does not modify original EntityIdentity."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    original_aliases = entity.aliases

    with_alias = add_alias(entity, "老张")

    assert entity.aliases == original_aliases
    assert len(entity.aliases) == 0


def test_add_alias_matching_canonical_name():
    """add_alias allows adding alias that matches canonical name."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "张三")  # Same as canonical

    # Should still add (contract allows this)
    assert "张三" in with_alias.aliases


# --- remove_alias Tests ---


def test_remove_alias_removes_from_set():
    """remove_alias removes alias from aliases set."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert "老张" not in without_alias.aliases


def test_remove_alias_preserves_entity_id():
    """remove_alias preserves entity_id."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert without_alias.entity_id == entity.entity_id


def test_remove_alias_preserves_project_id():
    """remove_alias preserves project_id."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert without_alias.project_id == entity.project_id


def test_remove_alias_preserves_canonical_name():
    """remove_alias preserves canonical_name."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert without_alias.canonical_name == entity.canonical_name


def test_remove_alias_preserves_entity_type():
    """remove_alias preserves entity_type."""
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert without_alias.entity_type == entity.entity_type


def test_remove_alias_preserves_other_aliases():
    """remove_alias preserves other aliases."""
    entity = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张", "张总", "三哥"]),
    )

    without_one = remove_alias(entity, "张总")

    assert "老张" in without_one.aliases
    assert "三哥" in without_one.aliases
    assert "张总" not in without_one.aliases


def test_remove_alias_idempotent_not_found():
    """remove_alias is idempotent when alias not found."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    without1 = remove_alias(entity, "不存在")
    without2 = remove_alias(without1, "不存在")

    assert without1.aliases == without2.aliases


def test_remove_alias_canonical_name_raises():
    """remove_alias raises ValueError when trying to remove canonical name."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    with pytest.raises(ValueError, match="Cannot remove canonical name"):
        remove_alias(entity, "张三")


def test_remove_alias_normalized_canonical_name_raises():
    """remove_alias raises ValueError for normalized match to canonical name."""
    entity = create_identity(ProjectId("proj_01"), "Zhang")

    # Try to remove with different case
    with pytest.raises(ValueError, match="Cannot remove canonical name"):
        remove_alias(entity, "ZHANG")


def test_remove_alias_normalized_comparison():
    """remove_alias uses normalize_for_lookup for matching."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "Smith")

    # Remove with different case
    without_alias = remove_alias(with_alias, "smith")

    assert "Smith" not in without_alias.aliases


def test_remove_alias_normalized_whitespace():
    """remove_alias matches with normalized whitespace."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "Zhang  San")  # Double space

    # Remove with single space
    without_alias = remove_alias(with_alias, "Zhang San")

    # Should be removed (normalized match)
    assert len(without_alias.aliases) == 0


def test_remove_alias_returns_new_object():
    """remove_alias returns new EntityIdentity object."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    without_alias = remove_alias(with_alias, "老张")

    assert without_alias is not with_alias
    assert without_alias != with_alias


def test_remove_alias_original_unchanged():
    """remove_alias does not modify original EntityIdentity."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")
    original_aliases = with_alias.aliases

    without_alias = remove_alias(with_alias, "老张")

    assert with_alias.aliases == original_aliases
    assert "老张" in with_alias.aliases


def test_remove_alias_empty_string_idempotent():
    """remove_alias with empty string is idempotent (no match)."""
    entity = create_identity(ProjectId("proj_01"), "张三")
    with_alias = add_alias(entity, "老张")

    # Empty string won't match anything
    result = remove_alias(with_alias, "")

    # Should be no-op
    assert result.aliases == with_alias.aliases


# --- Integration Tests ---


def test_add_and_remove_alias_integration():
    """Integration: add_alias followed by remove_alias."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    with_alias = add_alias(entity, "老张")
    assert "老张" in with_alias.aliases

    without_alias = remove_alias(with_alias, "老张")
    assert "老张" not in without_alias.aliases
    assert len(without_alias.aliases) == 0


def test_multiple_alias_operations():
    """Integration: multiple add and remove operations."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    step1 = add_alias(entity, "老张")
    step2 = add_alias(step1, "张总")
    step3 = add_alias(step2, "三哥")

    assert len(step3.aliases) == 3

    step4 = remove_alias(step3, "张总")
    assert len(step4.aliases) == 2
    assert "老张" in step4.aliases
    assert "三哥" in step4.aliases
    assert "张总" not in step4.aliases


def test_alias_operations_preserve_identity():
    """Integration: alias operations preserve entity identity."""
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    original_id = entity.entity_id

    step1 = add_alias(entity, "老张")
    step2 = add_alias(step1, "张总")
    step3 = remove_alias(step2, "老张")

    assert step3.entity_id == original_id
    assert step3.canonical_name == "张三"
    assert step3.entity_type == "CHARACTER"
