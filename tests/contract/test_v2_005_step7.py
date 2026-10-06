"""
V2-005 Step 7 Contract Tests: resolve_alias.

Tests for:
- resolve_alias operation
- Project isolation
- Ambiguity detection
- Input validation

Contract: V2-005 Implementation Contract v1.1.0 §3.5
Baseline: b1cd7153a155bae4a29a15e4744c1002c1082eaf
"""

import pytest

from anovel.domain.identity import (
    EntityRegistry,
    ProjectId,
    ResolutionStatus,
    add_alias,
    create_identity,
    resolve_alias,
)


# --- Basic Resolution Tests ---


def test_resolve_alias_unique_canonical_resolved():
    """resolve_alias resolves unique canonical name to entity."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_unique_alias_resolved():
    """resolve_alias resolves unique alias to entity."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "张三")
    entity_with_alias = add_alias(entity, "老张")
    registry.add_entity(entity_with_alias)

    result = resolve_alias(ProjectId("proj_01"), "老张", registry)

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_no_match_not_found():
    """resolve_alias returns NOT_FOUND when no match."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "不存在", registry)

    assert result.status == ResolutionStatus.NOT_FOUND


def test_resolve_alias_empty_registry_not_found():
    """resolve_alias returns NOT_FOUND in empty registry."""
    registry = EntityRegistry()

    result = resolve_alias(ProjectId("proj_01"), "任何名字", registry)

    assert result.status == ResolutionStatus.NOT_FOUND


# --- Input Validation Tests ---


def test_resolve_alias_empty_string_invalid():
    """resolve_alias returns INVALID_INPUT for empty string."""
    registry = EntityRegistry()

    result = resolve_alias(ProjectId("proj_01"), "", registry)

    assert result.status == ResolutionStatus.INVALID_INPUT
    assert "empty" in result.reason.lower() or "whitespace" in result.reason.lower()


def test_resolve_alias_whitespace_only_invalid():
    """resolve_alias returns INVALID_INPUT for whitespace-only string."""
    registry = EntityRegistry()

    result = resolve_alias(ProjectId("proj_01"), "   ", registry)

    assert result.status == ResolutionStatus.INVALID_INPUT


def test_resolve_alias_none_invalid():
    """resolve_alias returns INVALID_INPUT for None (runtime robustness)."""
    registry = EntityRegistry()

    # Type ignore for intentional runtime robustness test
    result = resolve_alias(ProjectId("proj_01"), None, registry)  # type: ignore

    assert result.status == ResolutionStatus.INVALID_INPUT


def test_resolve_alias_normalizes_to_empty_invalid():
    """resolve_alias returns INVALID_INPUT when lookup normalizes to empty."""
    registry = EntityRegistry()

    # U+3000 (ideographic space) normalizes to regular space, then strips to empty
    result = resolve_alias(ProjectId("proj_01"), "　", registry)

    assert result.status == ResolutionStatus.INVALID_INPUT


# --- Project Isolation Tests ---


def test_resolve_alias_project_isolation():
    """resolve_alias only searches within specified project."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_02"), "张三")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    # Resolve in proj_01
    result1 = resolve_alias(ProjectId("proj_01"), "张三", registry)
    assert result1.status == ResolutionStatus.RESOLVED
    assert result1.entity_id == entity1.entity_id

    # Resolve in proj_02
    result2 = resolve_alias(ProjectId("proj_02"), "张三", registry)
    assert result2.status == ResolutionStatus.RESOLVED
    assert result2.entity_id == entity2.entity_id


def test_resolve_alias_cross_project_not_found():
    """resolve_alias does not match entities from other projects."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    # Search in different project
    result = resolve_alias(ProjectId("proj_02"), "张三", registry)

    assert result.status == ResolutionStatus.NOT_FOUND


# --- Ambiguity Detection Tests ---


def test_resolve_alias_two_canonical_collisions_ambiguous():
    """resolve_alias returns AMBIGUOUS for two entities with same canonical name."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "张三")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.candidates) == 2
    assert entity1.entity_id in result.candidates
    assert entity2.entity_id in result.candidates


def test_resolve_alias_canonical_vs_alias_collision_ambiguous():
    """resolve_alias returns AMBIGUOUS for canonical vs alias collision (no priority)."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "李四")
    entity2_with_alias = add_alias(entity2, "张三")  # Alias matches entity1's canonical

    registry.add_entity(entity1)
    registry.add_entity(entity2_with_alias)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.candidates) == 2
    assert entity1.entity_id in result.candidates
    assert entity2.entity_id in result.candidates


def test_resolve_alias_same_entity_canonical_and_alias_resolved():
    """resolve_alias resolves when same entity matches via both canonical and alias."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    entity_with_alias = add_alias(entity, "张三")  # Add canonical as alias

    registry.add_entity(entity_with_alias)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    # Should resolve (not ambiguous) since it's the same entity
    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_ambiguous_candidates_frozenset():
    """resolve_alias returns candidates as frozenset."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "张三")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert isinstance(result.candidates, frozenset)


def test_resolve_alias_many_collisions_all_reported():
    """resolve_alias reports all candidates in ambiguous result."""
    registry = EntityRegistry()

    entities = [create_identity(ProjectId("proj_01"), "张三") for _ in range(5)]
    for entity in entities:
        registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.candidates) == 5
    for entity in entities:
        assert entity.entity_id in result.candidates


# --- Normalized Matching Tests ---


def test_resolve_alias_normalized_ascii_case_match():
    """resolve_alias matches ASCII names case-insensitively."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "Smith")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "SMITH", registry)

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_normalized_whitespace_match():
    """resolve_alias normalizes whitespace for matching."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "Zhang  San")  # Double space
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "Zhang San", registry)  # Single space

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_u3000_normalization():
    """resolve_alias normalizes U+3000 (ideographic space) by removing it."""
    registry = EntityRegistry()

    # U+3000 is removed during normalization
    entity = create_identity(ProjectId("proj_01"), "张　三")  # Ideographic space
    registry.add_entity(entity)

    # Both normalize to "张三" (U+3000 removed)
    result = resolve_alias(ProjectId("proj_01"), "张三", registry)  # No space

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


def test_resolve_alias_chinese_case_sensitive():
    """resolve_alias treats Chinese as case-preserving (no lowercase)."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    # Same characters should match
    result = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result.status == ResolutionStatus.RESOLVED
    assert result.entity_id == entity.entity_id


# --- Determinism and Idempotency Tests ---


def test_resolve_alias_registration_order_independent():
    """resolve_alias result does not depend on registration order."""
    registry1 = EntityRegistry()
    registry2 = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "李四")

    # Register in different orders
    registry1.add_entity(entity1)
    registry1.add_entity(entity2)

    registry2.add_entity(entity2)
    registry2.add_entity(entity1)

    result1 = resolve_alias(ProjectId("proj_01"), "张三", registry1)
    result2 = resolve_alias(ProjectId("proj_01"), "张三", registry2)

    assert result1.status == result2.status
    assert result1.entity_id == result2.entity_id


def test_resolve_alias_repeated_calls_identical():
    """resolve_alias returns value-equal results on repeated calls."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    result1 = resolve_alias(ProjectId("proj_01"), "张三", registry)
    result2 = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result1 == result2


def test_resolve_alias_ambiguous_repeated_calls_identical():
    """resolve_alias returns consistent ambiguous results."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "张三")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result1 = resolve_alias(ProjectId("proj_01"), "张三", registry)
    result2 = resolve_alias(ProjectId("proj_01"), "张三", registry)

    assert result1 == result2
    assert result1.candidates == result2.candidates


# --- Registry Immutability Tests ---


def test_resolve_alias_does_not_modify_registry():
    """resolve_alias does not modify registry state."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    # Get initial state
    initial_entities = registry.get_entities(ProjectId("proj_01"))
    initial_count = len(initial_entities)

    # Resolve
    resolve_alias(ProjectId("proj_01"), "张三", registry)

    # Verify no modification
    final_entities = registry.get_entities(ProjectId("proj_01"))
    final_count = len(final_entities)

    assert final_count == initial_count


def test_resolve_alias_not_found_does_not_modify_registry():
    """resolve_alias does not modify registry even on NOT_FOUND."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    initial_count = len(registry.get_entities(ProjectId("proj_01")))

    # Resolve non-existent
    resolve_alias(ProjectId("proj_01"), "不存在", registry)

    final_count = len(registry.get_entities(ProjectId("proj_01")))

    assert final_count == initial_count


# --- Integration Tests ---


def test_resolve_alias_integration_create_add_resolve():
    """Integration: create entity, add alias, resolve both."""
    registry = EntityRegistry()

    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    entity_with_alias = add_alias(entity, "老张")
    registry.add_entity(entity_with_alias)

    # Resolve canonical
    result_canonical = resolve_alias(ProjectId("proj_01"), "张三", registry)
    assert result_canonical.status == ResolutionStatus.RESOLVED
    assert result_canonical.entity_id == entity.entity_id

    # Resolve alias
    result_alias = resolve_alias(ProjectId("proj_01"), "老张", registry)
    assert result_alias.status == ResolutionStatus.RESOLVED
    assert result_alias.entity_id == entity.entity_id


def test_resolve_alias_integration_multiple_entities():
    """Integration: resolve in registry with multiple entities."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "李四")
    entity3 = create_identity(ProjectId("proj_01"), "王五")

    registry.add_entity(entity1)
    registry.add_entity(entity2)
    registry.add_entity(entity3)

    # Resolve each
    assert resolve_alias(ProjectId("proj_01"), "张三", registry).entity_id == entity1.entity_id
    assert resolve_alias(ProjectId("proj_01"), "李四", registry).entity_id == entity2.entity_id
    assert resolve_alias(ProjectId("proj_01"), "王五", registry).entity_id == entity3.entity_id
