"""
P0-B: Progression 系统测试
验证多种进阶体系的抽象和兼容性
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.progression import (
    ProgressionSystem,
    PowerSystem,
    WealthSystem,
    TechSystem,
    InfluenceSystem,
    infer_progression_type,
    create_default_progression,
    normalize_progression_dict,
)


def test_power_system():
    """测试 PowerSystem"""
    print("测试 1: PowerSystem...")

    ps = PowerSystem(
        tiers=["炼气", "筑基", "金丹"],
        breakthrough_condition="突破境界瓶颈",
        hard_limits=["资源稀缺", "天赋限制"]
    )

    assert ps.type == "power"
    assert len(ps.tiers) == 3
    assert ps.tiers[0] == "炼气"

    # 序列化
    data = ps.to_dict()
    assert data["type"] == "power"

    # 反序列化
    ps2 = PowerSystem.from_dict(data)
    assert ps2.type == "power"
    assert ps2.tiers == ps.tiers

    print("  ✅ PowerSystem 测试通过")
    return True


def test_wealth_system():
    """测试 WealthSystem"""
    print("\n测试 2: WealthSystem...")

    ws = WealthSystem(
        tiers=["贫困", "温饱", "小康", "富裕", "富豪"],
        breakthrough_condition="完成重大商业项目",
        hard_limits=["不能违反法律", "财富需要合理来源"]
    )

    assert ws.type == "wealth"
    assert len(ws.tiers) == 5
    assert "富豪" in ws.tiers

    # 序列化
    data = ws.to_dict()
    assert data["type"] == "wealth"

    # 反序列化
    ws2 = WealthSystem.from_dict(data)
    assert ws2.type == "wealth"

    print("  ✅ WealthSystem 测试通过")
    return True


def test_infer_progression_type():
    """测试题材推断"""
    print("\n测试 3: 题材推断...")

    assert infer_progression_type("都市") == "wealth"
    assert infer_progression_type("都市重生") == "wealth"
    assert infer_progression_type("科幻") == "tech"
    assert infer_progression_type("玄幻") == "power"
    assert infer_progression_type("仙侠") == "power"

    print("  ✅ 题材推断测试通过")
    return True


def test_create_default_progression():
    """测试默认进阶系统创建"""
    print("\n测试 4: 默认进阶系统...")

    # 都市题材
    urban = create_default_progression("都市")
    assert urban.type == "wealth"
    assert "富豪" in urban.tiers

    # 玄幻题材
    xuanhuan = create_default_progression("玄幻")
    assert xuanhuan.type == "power"
    assert any("金丹" in tier or "元婴" in tier for tier in xuanhuan.tiers)

    # 科幻题材
    scifi = create_default_progression("科幻")
    assert scifi.type == "tech"
    assert "文明" in str(scifi.tiers)

    print("  ✅ 默认进阶系统测试通过")
    return True


def test_normalize_old_format():
    """测试旧格式兼容性"""
    print("\n测试 5: 旧格式兼容...")

    # 旧格式（无 type 字段）
    old_data = {
        "tiers": ["炼气", "筑基", "金丹"],
        "breakthrough_condition": "突破境界",
        "hard_limits": ["资源稀缺"]
    }

    # 规范化
    normalized = normalize_progression_dict(old_data, genre="玄幻")
    assert "type" in normalized
    assert normalized["type"] == "power"

    # 都市旧格式
    old_urban = {
        "tiers": ["打工仔", "小老板", "企业家"],
        "breakthrough_condition": "完成项目",
        "hard_limits": ["法律限制"]
    }

    normalized_urban = normalize_progression_dict(old_urban, genre="都市")
    assert normalized_urban["type"] == "wealth"

    print("  ✅ 旧格式兼容测试通过")
    return True


def test_polymorphic_deserialization():
    """测试多态反序列化"""
    print("\n测试 6: 多态反序列化...")

    # WealthSystem
    wealth_data = {
        "type": "wealth",
        "tiers": ["贫困", "富豪"],
        "breakthrough_condition": "商业成功",
        "hard_limits": ["法律"]
    }

    prog = ProgressionSystem.from_dict(wealth_data)
    assert isinstance(prog, WealthSystem)
    assert prog.type == "wealth"

    # PowerSystem
    power_data = {
        "type": "power",
        "tiers": ["炼气", "金丹"],
        "breakthrough_condition": "突破",
        "hard_limits": ["资源"]
    }

    prog2 = ProgressionSystem.from_dict(power_data)
    assert isinstance(prog2, PowerSystem)
    assert prog2.type == "power"

    print("  ✅ 多态反序列化测试通过")
    return True


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n测试 7: 向后兼容性...")

    # 模拟旧代码只使用 tiers 字段
    old_outline = {
        "power_system": {
            "tiers": ["炼气", "筑基"],
            "breakthrough_condition": "突破",
            "hard_limits": ["资源"]
        }
    }

    # 旧代码可以继续访问
    ps_data = old_outline["power_system"]
    assert "tiers" in ps_data
    assert ps_data["tiers"][0] == "炼气"

    # 新代码可以规范化
    normalized = normalize_progression_dict(ps_data, genre="玄幻")
    assert normalized["type"] == "power"

    print("  ✅ 向后兼容性测试通过")
    return True


def test_summary():
    """运行所有 progression 系统测试"""
    print("=" * 60)
    print("Progression 系统测试（P0-B）")
    print("=" * 60)

    results = []

    results.append(("PowerSystem", test_power_system()))
    results.append(("WealthSystem", test_wealth_system()))
    results.append(("题材推断", test_infer_progression_type()))
    results.append(("默认进阶系统", test_create_default_progression()))
    results.append(("旧格式兼容", test_normalize_old_format()))
    results.append(("多态反序列化", test_polymorphic_deserialization()))
    results.append(("向后兼容性", test_backward_compatibility()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 Progression 系统测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_summary())
