#!/usr/bin/env python3
"""Run the V2-005 domain behavior directly, without mocks or external services."""

from anovel.domain.identity import (
    AliasResolutionResult,
    Entity,
    EntityId,
    EntityRegistry,
)


def main() -> None:
    registry = EntityRegistry()
    first = Entity(EntityId("novel_a", "char_001"), "李四", {"小李", "李公子"})
    other_project = Entity(EntityId("novel_b", "char_001"), "李四", {"老李"})
    registry.register(first)
    registry.register(other_project)

    for project, expected in (("novel_a", first), ("novel_b", other_project)):
        status, entity = registry.resolve(project, "李四")
        assert status is AliasResolutionResult.UNIQUE_MATCH and entity == expected
        print(f"项目隔离: {project} / 李四 -> {entity.id}")

    registry.rename(first.id, "李大侠")
    renamed = registry.get(first.id)
    assert renamed is not None and renamed.id == first.id
    assert renamed.display_name == "李大侠"
    for name in ("李大侠", "李四", "小李", "李公子"):
        status, entity = registry.resolve("novel_a", name)
        assert status is AliasResolutionResult.UNIQUE_MATCH and entity == renamed
        print(f"改名与别名: {name} -> {entity.id} ({entity.display_name})")

    for project, name in (("novel_b", "李大侠"), ("novel_a", "不存在的角色")):
        status, entity = registry.resolve(project, name)
        assert status is AliasResolutionResult.NOT_FOUND and entity is None
        print(f"未找到: {project} / {name} -> {status.value}")

    second = Entity(EntityId("novel_a", "char_002"), "王五", {"小李"})
    registry.register(second)
    status, entity = registry.resolve("novel_a", "小李")
    assert status is AliasResolutionResult.AMBIGUOUS and entity is None
    assert registry.get(first.id) == renamed and registry.get(second.id) == second
    print(f"真实歧义: novel_a / 小李 -> {status.value}; 两个稳定ID均保留")

    payload = renamed.to_dict()
    assert Entity.from_dict(payload) == renamed
    print(f"数据往返: {payload}")

    try:
        registry.resolve("", "李四")
    except ValueError:
        print("缺失项目作用域: 明确拒绝")
    else:
        raise AssertionError("missing project scope was accepted")

    print("V2-005 业务演示通过（内存领域能力，不代表持久化或产品闭环）。")


if __name__ == "__main__":
    main()
