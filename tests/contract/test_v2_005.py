"""V2-005: Core entity IDs and alias resolution contract tests."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import jsonschema
import pytest

from anovel.domain.identity import (
    AliasResolutionResult,
    Entity,
    EntityId,
    EntityRegistry,
)

ROOT = Path(__file__).resolve().parents[2]
ENTITY_SCHEMA = json.loads((ROOT / "specs/schemas/entity.schema.json").read_text())


def test_entity_id_stable_across_renames():
    """Entity ID remains unchanged when display name changes."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity = Entity(id=eid, display_name="张三", aliases=set())

    registry = EntityRegistry()
    registry.register(entity)

    # Rename entity
    registry.rename(eid, "张三丰", keep_old_as_alias=True)

    # ID unchanged
    assert registry.get(eid) is not None
    assert registry.get(eid).id == eid
    assert registry.get(eid).display_name == "张三丰"


def test_same_name_different_projects_no_confusion():
    """Entities with same name in different projects are distinct."""
    eid1 = EntityId(project="novel_a", local_id="char_001")
    eid2 = EntityId(project="novel_b", local_id="char_001")

    entity1 = Entity(id=eid1, display_name="李四", aliases=set())
    entity2 = Entity(id=eid2, display_name="李四", aliases=set())

    registry = EntityRegistry()
    registry.register(entity1)
    registry.register(entity2)

    # Resolve in different projects
    result1, resolved1 = registry.resolve("novel_a", "李四")
    result2, resolved2 = registry.resolve("novel_b", "李四")

    assert result1 == AliasResolutionResult.UNIQUE_MATCH
    assert result2 == AliasResolutionResult.UNIQUE_MATCH
    assert resolved1.id == eid1
    assert resolved2.id == eid2


def test_ambiguous_alias_returns_conflict():
    """Distinct identities may share names; resolution must not pick one."""
    registry = EntityRegistry()
    first = Entity(EntityId("novel_a", "first"), "同名", {"同别名"})
    second = Entity(EntityId("novel_a", "second"), "同名", {"同别名"})
    registry.register(first)
    registry.register(second)
    for name in ("同名", "同别名"):
        assert registry.resolve("novel_a", name) == (
            AliasResolutionResult.AMBIGUOUS,
            None,
        )
    assert registry.get(first.id) == first
    assert registry.get(second.id) == second
    assert len(list(registry.list_in_project("novel_a"))) == 2


def test_unknown_alias_returns_not_found():
    """Resolution returns NOT_FOUND for unknown aliases."""
    registry = EntityRegistry()

    result, entity = registry.resolve("novel_a", "不存在的角色")

    assert result == AliasResolutionResult.NOT_FOUND
    assert entity is None


def test_multiple_aliases_resolve_to_same_entity():
    """Multiple aliases all resolve to the same entity."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity = Entity(id=eid, display_name="王五", aliases={"老王", "王老板", "五哥"})

    registry = EntityRegistry()
    registry.register(entity)

    # All aliases resolve to same entity
    for name in ["王五", "老王", "王老板", "五哥"]:
        result, resolved = registry.resolve("novel_a", name)
        assert result == AliasResolutionResult.UNIQUE_MATCH
        assert resolved.id == eid


def test_rename_preserves_old_name_as_alias():
    """Rename with keep_old_as_alias=True adds old name to aliases."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity = Entity(id=eid, display_name="赵六", aliases=set())

    registry = EntityRegistry()
    registry.register(entity)

    registry.rename(eid, "赵大侠", keep_old_as_alias=True)

    # Old name now resolves as alias
    result, resolved = registry.resolve("novel_a", "赵六")
    assert result == AliasResolutionResult.UNIQUE_MATCH
    assert resolved.id == eid
    assert resolved.display_name == "赵大侠"


def test_rename_without_alias_makes_old_name_unavailable():
    """Rename with keep_old_as_alias=False removes old name."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity = Entity(id=eid, display_name="孙七", aliases=set())

    registry = EntityRegistry()
    registry.register(entity)

    registry.rename(eid, "孙掌门", keep_old_as_alias=False)

    # Old name no longer resolves
    result, _ = registry.resolve("novel_a", "孙七")
    assert result == AliasResolutionResult.NOT_FOUND


def test_cross_project_reference_rejected():
    """Cannot resolve entity from different project."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity = Entity(id=eid, display_name="周八", aliases=set())

    registry = EntityRegistry()
    registry.register(entity)

    # Try to resolve in wrong project
    result, _ = registry.resolve("novel_b", "周八")
    assert result == AliasResolutionResult.NOT_FOUND


def test_missing_project_scope_rejected():
    """Resolution requires explicit project scope."""
    registry = EntityRegistry()

    with pytest.raises(ValueError, match="project cannot be empty"):
        registry.resolve("", "角色名")


def test_duplicate_entity_id_rejected():
    """Cannot register two entities with same ID."""
    eid = EntityId(project="novel_a", local_id="char_001")
    entity1 = Entity(id=eid, display_name="吴九", aliases=set())
    entity2 = Entity(id=eid, display_name="郑十", aliases=set())

    registry = EntityRegistry()
    registry.register(entity1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(entity2)


def test_alias_conflict_within_project_is_explicitly_ambiguous():
    registry = EntityRegistry()
    first = Entity(EntityId("novel_a", "first"), "冯十一", {"老冯"})
    second = Entity(EntityId("novel_a", "second"), "陈十二", {"老冯"})
    registry.register(first)
    registry.register(second)
    assert registry.resolve("novel_a", "老冯") == (
        AliasResolutionResult.AMBIGUOUS,
        None,
    )
    assert registry.resolve("novel_a", "冯十一")[1] == first
    assert registry.resolve("novel_a", "陈十二")[1] == second


def test_rename_to_existing_name_is_ambiguous_without_merging():
    registry = EntityRegistry()
    first = Entity(EntityId("novel_a", "first"), "褚十三", set())
    second = Entity(EntityId("novel_a", "second"), "卫十四", set())
    registry.register(first)
    registry.register(second)
    registry.rename(first.id, "卫十四")
    assert registry.resolve("novel_a", "卫十四") == (
        AliasResolutionResult.AMBIGUOUS,
        None,
    )
    assert registry.get(first.id).id == first.id
    assert registry.get(second.id) == second
    registry.rename(first.id, "新名", keep_old_as_alias=False)
    assert registry.resolve("novel_a", "卫十四")[1] == second
    assert registry.resolve("novel_a", "新名")[1].id == first.id


def test_entity_id_rejects_empty_fields():
    """EntityId requires non-empty project and local_id."""
    with pytest.raises(ValueError, match="project cannot be empty"):
        EntityId(project="", local_id="char_001")

    with pytest.raises(ValueError, match="local_id cannot be empty"):
        EntityId(project="novel_a", local_id="")


def test_entity_id_rejects_slash_in_fields():
    """EntityId rejects slash in project or local_id."""
    with pytest.raises(ValueError, match="cannot contain '/'"):
        EntityId(project="novel/a", local_id="char_001")

    with pytest.raises(ValueError, match="cannot contain '/'"):
        EntityId(project="novel_a", local_id="char/001")


def test_entity_requires_non_empty_display_name():
    """Entity requires non-empty display_name."""
    eid = EntityId(project="novel_a", local_id="char_001")

    with pytest.raises(ValueError, match="display_name cannot be empty"):
        Entity(id=eid, display_name="", aliases=set())


def test_entity_schema_validates_valid_entity():
    """Valid entity passes JSON schema validation."""
    valid_entity = {
        "id": {"project": "novel_a", "local_id": "char_001"},
        "display_name": "Test Character",
        "aliases": ["Alias1", "Alias2"],
    }

    jsonschema.validate(instance=valid_entity, schema=ENTITY_SCHEMA)


def test_entity_schema_rejects_missing_required_fields():
    """Schema rejects entity missing required fields."""
    invalid_entity = {
        "id": {"project": "novel_a", "local_id": "char_001"}
        # Missing display_name
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_entity, schema=ENTITY_SCHEMA)


def test_entity_schema_rejects_empty_strings():
    """Schema rejects empty project, local_id, or display_name."""
    invalid_entity = {
        "id": {"project": "", "local_id": "char_001"},
        "display_name": "Test",
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_entity, schema=ENTITY_SCHEMA)


def test_entity_schema_rejects_slash_in_id_fields():
    """Schema rejects slash in project or local_id."""
    invalid_entity = {
        "id": {"project": "novel/a", "local_id": "char_001"},
        "display_name": "Test",
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_entity, schema=ENTITY_SCHEMA)


def test_list_entities_in_project():
    """Can list all entities within a project."""
    eid1 = EntityId(project="novel_a", local_id="char_001")
    eid2 = EntityId(project="novel_a", local_id="char_002")
    eid3 = EntityId(project="novel_b", local_id="char_001")

    registry = EntityRegistry()
    registry.register(Entity(id=eid1, display_name="角色1", aliases=set()))
    registry.register(Entity(id=eid2, display_name="角色2", aliases=set()))
    registry.register(Entity(id=eid3, display_name="角色3", aliases=set()))

    entities_a = list(registry.list_in_project("novel_a"))
    assert len(entities_a) == 2
    assert all(e.id.project == "novel_a" for e in entities_a)


def test_entity_str_representation():
    """EntityId has readable string representation."""
    eid = EntityId(project="novel_a", local_id="char_001")
    assert str(eid) == "novel_a/char_001"


@pytest.mark.parametrize("keep_old", [True, False])
def test_rename_handles_old_display_name_already_in_aliases(keep_old):
    registry = EntityRegistry()
    entity = Entity(EntityId("book", "one"), "旧名", {"旧名", "其他别名"})
    registry.register(entity)
    registry.rename(entity.id, "新名", keep_old_as_alias=keep_old)
    updated = registry.get(entity.id)
    assert updated.id == entity.id
    assert updated.display_name == "新名"
    assert registry.resolve("book", "其他别名")[1] == updated
    if keep_old:
        assert "旧名" in updated.aliases
        assert registry.resolve("book", "旧名")[1] == updated
    else:
        assert "旧名" not in updated.aliases
        assert registry.resolve("book", "旧名") == (
            AliasResolutionResult.NOT_FOUND,
            None,
        )


@pytest.mark.parametrize("keep_old", [True, False])
def test_repeated_rename_to_same_name_is_safe_noop(keep_old):
    registry = EntityRegistry()
    entity = Entity(EntityId("book", "one"), "名字", {"名字", "别名"})
    registry.register(entity)
    registry.rename(entity.id, "名字", keep_old_as_alias=keep_old)
    registry.rename(entity.id, "名字", keep_old_as_alias=keep_old)
    assert registry.get(entity.id) == entity
    assert registry.resolve("book", "名字")[1] == entity
    assert registry.resolve("book", "别名")[1] == entity


def test_rename_to_own_alias_preserves_all_lookup_paths():
    registry = EntityRegistry()
    entity = Entity(EntityId("book", "one"), "旧名", {"新名", "又一名"})
    registry.register(entity)
    registry.rename(entity.id, "新名")
    for name in ("旧名", "新名", "又一名"):
        assert registry.resolve("book", name)[1].id == entity.id


def test_rename_removes_only_renamed_identity_from_ambiguous_index():
    registry = EntityRegistry()
    first = Entity(EntityId("book", "one"), "同名", {"保留"})
    second = Entity(EntityId("book", "two"), "同名", set())
    registry.register(first)
    registry.register(second)
    registry.rename(first.id, "新名", keep_old_as_alias=False)
    assert registry.resolve("book", "同名")[1] == second
    assert registry.resolve("book", "新名")[1].id == first.id
    assert registry.resolve("book", "保留")[1].id == first.id


def test_alias_input_is_defensively_copied():
    aliases = {"原别名"}
    entity = Entity(EntityId("book", "one"), "原名", aliases)
    aliases.clear()
    aliases.add("污染别名")
    registry = EntityRegistry()
    registry.register(entity)
    aliases.add("注册后污染")
    assert entity.aliases == frozenset({"原别名"})
    assert registry.resolve("book", "原别名")[1] == entity
    assert registry.resolve("book", "污染别名")[0] == AliasResolutionResult.NOT_FOUND
    assert registry.resolve("book", "注册后污染")[0] == AliasResolutionResult.NOT_FOUND


def test_all_public_entity_snapshots_are_immutable_and_project_safe():
    registry = EntityRegistry()
    entity = Entity(EntityId("book_a", "one"), "名字", {"别名"})
    registry.register(entity)
    snapshots = (
        entity,
        registry.get(entity.id),
        registry.resolve("book_a", "名字")[1],
        next(iter(registry.list_in_project("book_a"))),
    )
    for snapshot in snapshots:
        with pytest.raises(FrozenInstanceError):
            snapshot.id = EntityId("book_b", "one")
        with pytest.raises(FrozenInstanceError):
            snapshot.display_name = "污染"
        with pytest.raises(FrozenInstanceError):
            snapshot.aliases = frozenset({"污染"})
        with pytest.raises(FrozenInstanceError):
            snapshot.id.project = "book_b"
        with pytest.raises(AttributeError):
            snapshot.aliases.add("污染")
        assert not hasattr(snapshot, "__dict__")
    assert registry.resolve("book_a", "名字")[1] == entity
    assert registry.resolve("book_b", "名字")[0] == AliasResolutionResult.NOT_FOUND
    registry.rename(entity.id, "改名")
    assert entity.display_name == "名字"
    assert registry.get(entity.id).display_name == "改名"


def test_json_serialization_does_not_expose_internal_state():
    payload = {
        "id": {"project": "book", "local_id": "one"},
        "display_name": "名字",
        "aliases": ["乙", "甲"],
    }
    entity = Entity.from_dict(payload)
    payload["id"]["project"] = "wrong"
    payload["aliases"].append("污染")
    first = entity.to_dict()
    assert first["aliases"] == sorted(["乙", "甲"])
    first["id"]["project"] = "wrong_again"
    first["aliases"].append("污染")
    assert entity.id.project == "book"
    assert entity.aliases == frozenset({"乙", "甲"})
    assert Entity.from_dict(entity.to_dict()) == entity


VALID_PAYLOADS = [
    {"id": {"project": "book", "local_id": "one"}, "display_name": "名字"},
    {
        "id": {"project": "项目甲", "local_id": "人物-01"},
        "display_name": "同名",
        "aliases": [],
    },
    {
        "id": {"project": "book", "local_id": "one"},
        "display_name": "名字/一",
        "aliases": ["名字/一", "别名", "另一个别名"],
    },
]
INVALID_PAYLOADS = [
    None,
    [],
    "entity",
    42,
    {},
    {"id": {"project": "book", "local_id": "one"}},
    {"display_name": "名字"},
    {"id": None, "display_name": "名字"},
    {"id": [], "display_name": "名字"},
    {"id": {}, "display_name": "名字"},
    {"id": {"project": "book"}, "display_name": "名字"},
    {"id": {"local_id": "one"}, "display_name": "名字"},
    {
        "id": {"project": "book", "local_id": "one", "extra": True},
        "display_name": "名字",
    },
    {
        "id": {"project": "book", "local_id": "one"},
        "display_name": "名字",
        "extra": True,
    },
]
for field in ("project", "local_id"):
    for bad in ("", "a/b", None, False, 1, [], {}):
        INVALID_PAYLOADS.append(
            {
                "id": {"project": "book", "local_id": "one", field: bad},
                "display_name": "名字",
            }
        )
for bad in ("", None, False, 1, [], {}):
    INVALID_PAYLOADS.append(
        {"id": {"project": "book", "local_id": "one"}, "display_name": bad}
    )
for bad in (None, "别名", {}, 1, [""], [1], [False], [{}], ["重复", "重复"]):
    INVALID_PAYLOADS.append(
        {
            "id": {"project": "book", "local_id": "one"},
            "display_name": "名字",
            "aliases": bad,
        }
    )


@pytest.mark.parametrize("payload", VALID_PAYLOADS)
def test_same_valid_payloads_pass_code_and_schema(payload):
    jsonschema.Draft202012Validator(ENTITY_SCHEMA).validate(payload)
    entity = Entity.from_dict(payload)
    jsonschema.Draft202012Validator(ENTITY_SCHEMA).validate(entity.to_dict())
    assert Entity.from_dict(entity.to_dict()) == entity


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_same_invalid_payloads_fail_code_and_schema(payload):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(ENTITY_SCHEMA).validate(payload)
    with pytest.raises(ValueError):
        Entity.from_dict(payload)


@pytest.mark.parametrize("bad", [None, False, 1, [], {}])
def test_direct_entity_id_rejects_non_string_fields(bad):
    with pytest.raises(ValueError):
        EntityId(bad, "one")
    with pytest.raises(ValueError):
        EntityId("book", bad)


@pytest.mark.parametrize("bad", [None, False, 123, ""])
def test_direct_entity_rejects_invalid_display_names(bad):
    with pytest.raises(ValueError):
        Entity(EntityId("book", "one"), bad, set())


@pytest.mark.parametrize("bad", [None, "alias", ["alias"], {""}, {1}])
def test_direct_entity_rejects_invalid_aliases(bad):
    with pytest.raises(ValueError):
        Entity(EntityId("book", "one"), "名字", bad)


def test_direct_entity_requires_typed_identity():
    with pytest.raises(ValueError):
        Entity({"project": "book", "local_id": "one"}, "名字", set())


@pytest.mark.parametrize("bad", [None, False, 1, "", "a/b"])
def test_all_project_lookup_boundaries_require_valid_scope(bad):
    registry = EntityRegistry()
    with pytest.raises(ValueError):
        registry.resolve(bad, "名字")
    with pytest.raises(ValueError):
        registry.list_in_project(bad)


def test_invalid_rename_leaves_identity_and_indexes_unchanged():
    registry = EntityRegistry()
    entity = Entity(EntityId("book", "one"), "名字", {"别名"})
    registry.register(entity)
    for bad in (None, False, 123, ""):
        with pytest.raises(ValueError):
            registry.rename(entity.id, bad)
    with pytest.raises(ValueError):
        registry.rename(entity.id, "新名", keep_old_as_alias="true")
    with pytest.raises(ValueError, match="not found"):
        registry.rename(EntityId("other_book", "one"), "新名")
    assert registry.get(entity.id) == entity
    for name in ("名字", "别名"):
        assert registry.resolve("book", name)[1] == entity
    assert registry.resolve("book", "新名")[0] == AliasResolutionResult.NOT_FOUND
