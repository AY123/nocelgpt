"""
V2-005 Final Contract Tests: Consolidated integration and acceptance tests.

This file provides the final contract verification layer for V2-005,
complementing the detailed Step 3-7 tests. Tests here focus on:
- Cross-step integration (full operation chains)
- Type contract completeness
- ResolutionResult union behavior
- Serialization and schema validation
- Negative scenarios per contract §11.3

Contract: V2-005 Implementation Contract v1.1.0 §11
Baseline: 48eb836bcb44abce88453c0f07a45d0c31eb96d5
"""

import json
from pathlib import Path

import pytest

from anovel.domain.identity import (
    AmbiguousResult,
    EntityId,
    EntityIdentity,
    EntityRegistry,
    InvalidInputResult,
    NotFoundResult,
    ProjectId,
    ResolvedResult,
    ResolutionResult,
    ResolutionStatus,
    add_alias,
    create_identity,
    remove_alias,
    rename_identity,
    resolve_alias,
)


# --- Type Contract Tests ---


def test_resolution_result_union_completeness():
    """ResolutionResult union includes all four result types."""
    # Test that all result types are part of the union
    resolved = ResolvedResult(
        status=ResolutionStatus.RESOLVED,
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
    )
    not_found = NotFoundResult(status=ResolutionStatus.NOT_FOUND)
    ambiguous = AmbiguousResult(
        status=ResolutionStatus.AMBIGUOUS,
        candidates=frozenset([EntityId("550e8400-e29b-41d4-a716-446655440000")]),
    )
    invalid = InvalidInputResult(
        status=ResolutionStatus.INVALID_INPUT, reason="test"
    )

    results: list[ResolutionResult] = [resolved, not_found, ambiguous, invalid]

    assert len(results) == 4
    assert all(hasattr(r, "status") for r in results)


def test_resolution_status_literal_narrowing():
    """ResolutionStatus discriminates result types via literal status."""
    resolved = ResolvedResult(
        status=ResolutionStatus.RESOLVED,
        entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
    )

    # Type narrowing via status check
    if resolved.status == ResolutionStatus.RESOLVED:
        # Should have entity_id attribute
        assert hasattr(resolved, "entity_id")

    ambiguous = AmbiguousResult(
        status=ResolutionStatus.AMBIGUOUS,
        candidates=frozenset([EntityId("550e8400-e29b-41d4-a716-446655440000")]),
    )

    if ambiguous.status == ResolutionStatus.AMBIGUOUS:
        # Should have candidates attribute
        assert hasattr(ambiguous, "candidates")


# --- Cross-Step Integration Tests ---


def test_full_chain_create_add_resolve():
    """Integration: create → add_alias → register → resolve."""
    registry = EntityRegistry()

    # Step 1: Create identity
    entity = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
    assert entity.canonical_name == "张三"
    assert len(entity.aliases) == 0

    # Step 2: Add alias
    entity_with_alias = add_alias(entity, "老张")
    assert "老张" in entity_with_alias.aliases

    # Step 3: Register
    registry.add_entity(entity_with_alias)

    # Step 4: Resolve canonical
    result_canonical = resolve_alias(ProjectId("proj_01"), "张三", registry)
    assert result_canonical.status == ResolutionStatus.RESOLVED
    assert result_canonical.entity_id == entity.entity_id

    # Step 5: Resolve alias
    result_alias = resolve_alias(ProjectId("proj_01"), "老张", registry)
    assert result_alias.status == ResolutionStatus.RESOLVED
    assert result_alias.entity_id == entity.entity_id


def test_full_chain_create_rename_resolve():
    """Integration: create → rename → register → resolve both names."""
    registry = EntityRegistry()

    # Create with original name
    entity = create_identity(ProjectId("proj_01"), "李四")

    # Rename (old name becomes alias)
    renamed = rename_identity(entity, "李老板")
    assert renamed.canonical_name == "李老板"
    assert "李四" in renamed.aliases

    # Register
    registry.add_entity(renamed)

    # Resolve new canonical
    result_new = resolve_alias(ProjectId("proj_01"), "李老板", registry)
    assert result_new.status == ResolutionStatus.RESOLVED
    assert result_new.entity_id == entity.entity_id

    # Resolve old name (now alias)
    result_old = resolve_alias(ProjectId("proj_01"), "李四", registry)
    assert result_old.status == ResolutionStatus.RESOLVED
    assert result_old.entity_id == entity.entity_id


def test_full_chain_ambiguous_detection():
    """Integration: multiple entities with same name → ambiguous."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "王五")
    entity2 = create_identity(ProjectId("proj_01"), "王五")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "王五", registry)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert len(result.candidates) == 2
    assert entity1.entity_id in result.candidates
    assert entity2.entity_id in result.candidates


def test_full_chain_project_isolation():
    """Integration: entities in different projects don't interfere."""
    registry = EntityRegistry()

    entity_p1 = create_identity(ProjectId("proj_01"), "赵六")
    entity_p2 = create_identity(ProjectId("proj_02"), "赵六")

    registry.add_entity(entity_p1)
    registry.add_entity(entity_p2)

    # Resolve in proj_01
    result_p1 = resolve_alias(ProjectId("proj_01"), "赵六", registry)
    assert result_p1.status == ResolutionStatus.RESOLVED
    assert result_p1.entity_id == entity_p1.entity_id

    # Resolve in proj_02
    result_p2 = resolve_alias(ProjectId("proj_02"), "赵六", registry)
    assert result_p2.status == ResolutionStatus.RESOLVED
    assert result_p2.entity_id == entity_p2.entity_id


# --- Serialization and Schema Tests ---


def test_serialization_round_trip():
    """EntityIdentity serializes to dict and validates."""
    entity = create_identity(ProjectId("proj_01"), "测试")
    entity_with_alias = add_alias(entity, "test")

    # Serialize
    serialized = {
        "entity_id": entity_with_alias.entity_id,
        "project_id": entity_with_alias.project_id,
        "canonical_name": entity_with_alias.canonical_name,
        "aliases": list(entity_with_alias.aliases),
        "entity_type": entity_with_alias.entity_type,
    }

    # Deserialize
    deserialized = EntityIdentity(
        entity_id=EntityId(serialized["entity_id"]),
        project_id=ProjectId(serialized["project_id"]),
        canonical_name=serialized["canonical_name"],
        aliases=frozenset(serialized["aliases"]),
        entity_type=serialized["entity_type"],
    )

    assert deserialized == entity_with_alias


def test_json_schema_validation():
    """EntityIdentity JSON validates against schema."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")

    # Load schema
    schema_path = Path("specs/schemas/entity-identity.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    # Create entity
    entity = create_identity(ProjectId("proj_01"), "张三")
    entity_with_alias = add_alias(entity, "老张")

    # Serialize
    instance = {
        "entity_id": entity_with_alias.entity_id,
        "project_id": entity_with_alias.project_id,
        "canonical_name": entity_with_alias.canonical_name,
        "aliases": list(entity_with_alias.aliases),
        "entity_type": entity_with_alias.entity_type,
    }

    # Validate
    jsonschema.validate(instance=instance, schema=schema)


# --- Negative Scenario Tests (§11.3) ---


def test_ns1_cross_project_leakage():
    """NS-1: Entities do not leak across project boundaries."""
    registry = EntityRegistry()

    entity_p1 = create_identity(ProjectId("proj_01"), "secret")
    registry.add_entity(entity_p1)

    # Attempt to resolve in different project
    result = resolve_alias(ProjectId("proj_02"), "secret", registry)

    assert result.status == ResolutionStatus.NOT_FOUND


def test_ns2_no_random_selection_on_ambiguity():
    """NS-2: Ambiguous resolution never selects randomly."""
    registry = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "张三")
    entity2 = create_identity(ProjectId("proj_01"), "张三")

    registry.add_entity(entity1)
    registry.add_entity(entity2)

    # Multiple resolutions should be consistent
    results = [resolve_alias(ProjectId("proj_01"), "张三", registry) for _ in range(10)]

    # All should be ambiguous
    assert all(r.status == ResolutionStatus.AMBIGUOUS for r in results)

    # All should have same candidates
    first_candidates = results[0].candidates
    assert all(r.candidates == first_candidates for r in results)


def test_ns3_no_database_row_order_dependency():
    """NS-3: Resolution is independent of registration order."""
    registry1 = EntityRegistry()
    registry2 = EntityRegistry()

    entity1 = create_identity(ProjectId("proj_01"), "A")
    entity2 = create_identity(ProjectId("proj_01"), "B")

    # Register in different orders
    registry1.add_entity(entity1)
    registry1.add_entity(entity2)

    registry2.add_entity(entity2)
    registry2.add_entity(entity1)

    # Resolve same name from both registries
    result1 = resolve_alias(ProjectId("proj_01"), "A", registry1)
    result2 = resolve_alias(ProjectId("proj_01"), "A", registry2)

    assert result1.status == result2.status
    assert result1.entity_id == result2.entity_id


def test_ns4_no_implicit_rename_creates_new_entity():
    """NS-4: Rename does not create a new entity."""
    entity = create_identity(ProjectId("proj_01"), "原名")
    original_id = entity.entity_id

    renamed = rename_identity(entity, "新名")

    # Same entity ID
    assert renamed.entity_id == original_id


def test_ns5_no_silent_alias_overwrite():
    """NS-5: Adding duplicate alias (normalized) is idempotent, not overwrite."""
    entity = create_identity(ProjectId("proj_01"), "张三")

    step1 = add_alias(entity, "zhang")
    step2 = add_alias(step1, "ZHANG")  # Normalized duplicate

    # Should be idempotent (same set)
    assert len(step2.aliases) == 1
    assert "zhang" in step2.aliases


def test_ns6_name_is_not_identity():
    """NS-6: Name changes do not change entity identity."""
    entity = create_identity(ProjectId("proj_01"), "original")
    original_id = entity.entity_id

    # Rename multiple times
    renamed1 = rename_identity(entity, "name1")
    renamed2 = rename_identity(renamed1, "name2")
    renamed3 = rename_identity(renamed2, "name3")

    # Entity ID never changes
    assert renamed1.entity_id == original_id
    assert renamed2.entity_id == original_id
    assert renamed3.entity_id == original_id


# --- Required Named Tests (§11.1) ---


def test_create_identity_generates_stable_id():
    """create_identity generates stable EntityId."""
    entity = create_identity(ProjectId("proj_01"), "test")
    assert entity.entity_id is not None
    assert len(entity.entity_id) == 36  # UUID format


def test_create_identity_empty_name_raises():
    """create_identity raises ValueError for empty name."""
    with pytest.raises(ValueError):
        create_identity(ProjectId("proj_01"), "")


def test_rename_preserves_entity_id():
    """rename_identity preserves entity_id."""
    entity = create_identity(ProjectId("proj_01"), "old")
    renamed = rename_identity(entity, "new")
    assert renamed.entity_id == entity.entity_id


def test_rename_old_name_becomes_alias():
    """rename_identity adds old name as alias."""
    entity = create_identity(ProjectId("proj_01"), "old")
    renamed = rename_identity(entity, "new")
    assert "old" in renamed.aliases


def test_rename_empty_name_raises():
    """rename_identity raises ValueError for empty name."""
    entity = create_identity(ProjectId("proj_01"), "test")
    with pytest.raises(ValueError):
        rename_identity(entity, "")


def test_add_alias_adds_to_set():
    """add_alias adds alias to aliases set."""
    entity = create_identity(ProjectId("proj_01"), "test")
    with_alias = add_alias(entity, "alias1")
    assert "alias1" in with_alias.aliases


def test_add_alias_idempotent():
    """add_alias is idempotent for duplicate aliases."""
    entity = create_identity(ProjectId("proj_01"), "test")
    step1 = add_alias(entity, "alias1")
    step2 = add_alias(step1, "alias1")
    assert len(step2.aliases) == 1


def test_add_alias_empty_raises():
    """add_alias raises ValueError for empty alias."""
    entity = create_identity(ProjectId("proj_01"), "test")
    with pytest.raises(ValueError):
        add_alias(entity, "")


def test_remove_alias_removes_from_set():
    """remove_alias removes alias from set."""
    entity = create_identity(ProjectId("proj_01"), "test")
    with_alias = add_alias(entity, "alias1")
    without = remove_alias(with_alias, "alias1")
    assert "alias1" not in without.aliases


def test_remove_alias_idempotent():
    """remove_alias is idempotent when alias not found."""
    entity = create_identity(ProjectId("proj_01"), "test")
    result = remove_alias(entity, "nonexistent")
    assert result.aliases == entity.aliases


def test_remove_alias_canonical_name_raises():
    """remove_alias raises ValueError when removing canonical name."""
    entity = create_identity(ProjectId("proj_01"), "test")
    with pytest.raises(ValueError):
        remove_alias(entity, "test")


def test_resolve_unique_alias_returns_resolved():
    """resolve_alias returns RESOLVED for unique match."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "test")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "test", registry)
    assert result.status == ResolutionStatus.RESOLVED


def test_resolve_not_found_returns_not_found():
    """resolve_alias returns NOT_FOUND when no match."""
    registry = EntityRegistry()
    result = resolve_alias(ProjectId("proj_01"), "nonexistent", registry)
    assert result.status == ResolutionStatus.NOT_FOUND


def test_resolve_ambiguous_returns_ambiguous():
    """resolve_alias returns AMBIGUOUS for multiple matches."""
    registry = EntityRegistry()
    entity1 = create_identity(ProjectId("proj_01"), "test")
    entity2 = create_identity(ProjectId("proj_01"), "test")
    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "test", registry)
    assert result.status == ResolutionStatus.AMBIGUOUS


def test_resolve_empty_string_returns_invalid():
    """resolve_alias returns INVALID_INPUT for empty string."""
    registry = EntityRegistry()
    result = resolve_alias(ProjectId("proj_01"), "", registry)
    assert result.status == ResolutionStatus.INVALID_INPUT


def test_resolve_whitespace_only_returns_invalid():
    """resolve_alias returns INVALID_INPUT for whitespace-only."""
    registry = EntityRegistry()
    result = resolve_alias(ProjectId("proj_01"), "   ", registry)
    assert result.status == ResolutionStatus.INVALID_INPUT


def test_project_isolation():
    """Entities in different projects are isolated."""
    registry = EntityRegistry()
    entity1 = create_identity(ProjectId("proj_01"), "test")
    entity2 = create_identity(ProjectId("proj_02"), "test")
    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "test", registry)
    assert result.entity_id == entity1.entity_id


def test_same_name_different_projects():
    """Same name in different projects resolves correctly."""
    registry = EntityRegistry()
    entity1 = create_identity(ProjectId("proj_01"), "test")
    entity2 = create_identity(ProjectId("proj_02"), "test")
    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result1 = resolve_alias(ProjectId("proj_01"), "test", registry)
    result2 = resolve_alias(ProjectId("proj_02"), "test", registry)

    assert result1.entity_id == entity1.entity_id
    assert result2.entity_id == entity2.entity_id


def test_normalization_whitespace():
    """normalize_for_lookup handles whitespace correctly."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "Zhang  San")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "Zhang San", registry)
    assert result.status == ResolutionStatus.RESOLVED


def test_normalization_ascii_case_insensitive():
    """normalize_for_lookup is case-insensitive for ASCII."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "Smith")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "SMITH", registry)
    assert result.status == ResolutionStatus.RESOLVED


def test_normalization_chinese_case_sensitive():
    """normalize_for_lookup preserves Chinese case."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "张三")
    registry.add_entity(entity)

    result = resolve_alias(ProjectId("proj_01"), "张三", registry)
    assert result.status == ResolutionStatus.RESOLVED


def test_deterministic_resolution():
    """Resolution is deterministic across multiple calls."""
    registry = EntityRegistry()
    entity = create_identity(ProjectId("proj_01"), "test")
    registry.add_entity(entity)

    results = [resolve_alias(ProjectId("proj_01"), "test", registry) for _ in range(5)]

    assert all(r.status == results[0].status for r in results)
    assert all(r.entity_id == results[0].entity_id for r in results)


def test_ambiguous_result_unordered():
    """AmbiguousResult candidates are unordered (frozenset)."""
    registry = EntityRegistry()
    entity1 = create_identity(ProjectId("proj_01"), "test")
    entity2 = create_identity(ProjectId("proj_01"), "test")
    registry.add_entity(entity1)
    registry.add_entity(entity2)

    result = resolve_alias(ProjectId("proj_01"), "test", registry)

    assert isinstance(result.candidates, frozenset)
    assert len(result.candidates) == 2
