"""
V2-005 Step 4 Contract Tests: Entity Registry.

Tests for:
- EntityRegistry.__init__
- EntityRegistry.add_entity
- EntityRegistry.get_entity
- EntityRegistry.get_entities

Contract: V2-005 Implementation Contract v1.1.0 §4
Baseline: 0b091b229dc010e0e87a4be1eada4be5d3ba422c
"""

import pytest

from anovel.domain.identity import (
    EntityId,
    EntityIdentity,
    EntityRegistry,
    ProjectId,
)


# --- Fixtures ---


@pytest.fixture
def registry():
    """Fresh EntityRegistry for each test."""
    return EntityRegistry()


@pytest.fixture
def sample_entity():
    """Sample entity for testing."""
    return EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
        entity_type="CHARACTER",
    )


@pytest.fixture
def another_entity():
    """Another sample entity for testing."""
    return EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440001"),
        project_id=ProjectId("proj_01"),
        canonical_name="李四",
        aliases=frozenset(["老李"]),
        entity_type="CHARACTER",
    )


@pytest.fixture
def different_project_entity():
    """Entity in different project."""
    return EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440002"),
        project_id=ProjectId("proj_02"),
        canonical_name="王五",
        aliases=frozenset(),
        entity_type="CHARACTER",
    )


# --- EntityRegistry.__init__ Tests ---


def test_registry_init_creates_empty_registry():
    """New registry is empty."""
    registry = EntityRegistry()
    assert registry.get_entity(EntityId("nonexistent")) is None
    assert registry.get_entities(ProjectId("nonexistent")) == []


def test_registry_init_independent_instances():
    """Multiple registry instances are independent."""
    registry1 = EntityRegistry()
    registry2 = EntityRegistry()

    entity = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
    )

    registry1.add_entity(entity)

    # Registry 2 should not have the entity
    assert registry2.get_entity(entity.entity_id) is None


# --- EntityRegistry.add_entity Tests ---


def test_add_entity_stores_entity(registry, sample_entity):
    """Adding entity makes it retrievable."""
    registry.add_entity(sample_entity)
    retrieved = registry.get_entity(sample_entity.entity_id)
    assert retrieved == sample_entity


def test_add_entity_same_id_same_value_is_noop(registry):
    """Adding same entity (by value) is idempotent no-op."""
    entity = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
    )

    registry.add_entity(entity)
    registry.add_entity(entity)  # Should not raise

    # Verify it's only in there once
    entities = registry.get_entities(entity.project_id)
    assert entities.count(entity) == 1


def test_add_entity_same_id_same_value_different_object(registry):
    """Adding entity with same ID and same content (different object) is no-op."""
    entity1 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张"]),
    )

    # Create a new object with identical content (value equality, not object identity)
    entity2 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张"]),
    )

    assert entity1 is not entity2  # Different objects
    assert entity1 == entity2  # Same value

    registry.add_entity(entity1)
    registry.add_entity(entity2)  # Should not raise

    entities = registry.get_entities(entity1.project_id)
    assert len(entities) == 1


def test_add_entity_same_id_different_value_raises(registry):
    """Adding entity with same ID but different content raises ValueError."""
    entity1 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
    )

    entity2 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="李四",  # Different name
        aliases=frozenset(),
    )

    registry.add_entity(entity1)

    with pytest.raises(ValueError, match="already registered with different content"):
        registry.add_entity(entity2)


def test_add_entity_duplicate_name_allowed(registry):
    """Multiple entities with same canonical_name are allowed."""
    entity1 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
    )

    entity2 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440001"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",  # Same name, different ID
        aliases=frozenset(),
    )

    registry.add_entity(entity1)
    registry.add_entity(entity2)  # Should not raise

    entities = registry.get_entities(ProjectId("proj_01"))
    assert len(entities) == 2


def test_add_entity_updates_project_index(registry, sample_entity):
    """Adding entity updates project index."""
    registry.add_entity(sample_entity)
    entities = registry.get_entities(sample_entity.project_id)
    assert sample_entity in entities


def test_add_entity_multiple_entities_same_project(registry, sample_entity, another_entity):
    """Adding multiple entities to same project works."""
    registry.add_entity(sample_entity)
    registry.add_entity(another_entity)

    entities = registry.get_entities(ProjectId("proj_01"))
    assert len(entities) == 2
    assert sample_entity in entities
    assert another_entity in entities


def test_add_entity_no_duplicate_in_project_index(registry):
    """Repeated add of same entity doesn't pollute project index."""
    entity = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(),
    )

    registry.add_entity(entity)
    registry.add_entity(entity)
    registry.add_entity(entity)  # Add 3 times

    # Should only appear once in project entities
    entities = registry.get_entities(entity.project_id)
    assert entities.count(entity) == 1
    assert len(entities) == 1


# --- EntityRegistry.get_entity Tests ---


def test_get_entity_returns_entity(registry, sample_entity):
    """get_entity returns stored entity."""
    registry.add_entity(sample_entity)
    retrieved = registry.get_entity(sample_entity.entity_id)
    assert retrieved == sample_entity


def test_get_entity_not_found_returns_none(registry):
    """get_entity returns None for unknown entity_id."""
    result = registry.get_entity(EntityId("nonexistent-id"))
    assert result is None


def test_get_entity_empty_registry_returns_none(registry):
    """get_entity on empty registry returns None."""
    result = registry.get_entity(EntityId("550e8400-e29b-41d4-a716-446655440000"))
    assert result is None


# --- EntityRegistry.get_entities Tests ---


def test_get_entities_returns_project_entities(
    registry, sample_entity, another_entity, different_project_entity
):
    """get_entities returns only entities in specified project."""
    registry.add_entity(sample_entity)
    registry.add_entity(another_entity)
    registry.add_entity(different_project_entity)

    proj_01_entities = registry.get_entities(ProjectId("proj_01"))
    assert len(proj_01_entities) == 2
    assert sample_entity in proj_01_entities
    assert another_entity in proj_01_entities
    assert different_project_entity not in proj_01_entities


def test_get_entities_unknown_project_returns_empty(registry):
    """get_entities for unknown project returns empty list."""
    result = registry.get_entities(ProjectId("nonexistent_project"))
    assert result == []
    assert isinstance(result, list)


def test_get_entities_empty_registry_returns_empty(registry):
    """get_entities on empty registry returns empty list."""
    result = registry.get_entities(ProjectId("proj_01"))
    assert result == []


def test_get_entities_project_isolation(
    registry, sample_entity, different_project_entity
):
    """Entities in different projects are isolated."""
    registry.add_entity(sample_entity)
    registry.add_entity(different_project_entity)

    proj_01_entities = registry.get_entities(ProjectId("proj_01"))
    proj_02_entities = registry.get_entities(ProjectId("proj_02"))

    assert len(proj_01_entities) == 1
    assert len(proj_02_entities) == 1
    assert sample_entity in proj_01_entities
    assert different_project_entity in proj_02_entities


def test_get_entities_returns_list(registry, sample_entity):
    """get_entities returns a list (iterable)."""
    registry.add_entity(sample_entity)
    result = registry.get_entities(sample_entity.project_id)
    assert isinstance(result, list)


# --- Value Equality Tests ---


def test_add_entity_uses_value_equality_not_identity(registry):
    """add_entity compares by value (==), not object identity (is)."""
    entity1 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张", "张总"]),
        entity_type="CHARACTER",
    )

    # Create identical entity (different object)
    entity2 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["老张", "张总"]),  # Same aliases, different order OK
        entity_type="CHARACTER",
    )

    assert entity1 is not entity2  # Different objects
    assert entity1 == entity2  # Same value

    registry.add_entity(entity1)
    registry.add_entity(entity2)  # Should be no-op, not raise

    # Should only have one entity
    entities = registry.get_entities(entity1.project_id)
    assert len(entities) == 1


def test_frozen_dataclass_equality(registry):
    """Verify frozen dataclass value equality works as expected."""
    entity1 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["a", "b"]),
    )

    entity2 = EntityIdentity(
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
        project_id=ProjectId("proj_01"),
        canonical_name="张三",
        aliases=frozenset(["b", "a"]),  # Different order, same set
    )

    # frozenset equality is order-independent
    assert entity1 == entity2

    registry.add_entity(entity1)
    registry.add_entity(entity2)  # Should be no-op

    entities = registry.get_entities(entity1.project_id)
    assert len(entities) == 1
