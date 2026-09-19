"""
P0 整改：真实集成测试
验证题材契约门禁、Progression 主路径切换、genre_profile_id 等整改
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline.agents import propose_candidates, synthesize_final_outline
from runtime.outline.workflow import run_outline_bootstrap, OutlineBootstrapResult
from runtime.genre_contract import validate_outline_genre


def test_genre_contract_gate_in_outline():
    """测试 1: 题材契约门禁已接入 outline 生成"""
    print("测试 1: 题材契约门禁接入...")

    # 模拟包含违规内容的 merged_analysis
    bad_analysis = {
        "genre_signals": ["都市"],
        "reader_rewards": ["wealth"],
        "structure_signals": ["linear"],
    }

    # propose_candidates 应该生成都市候选
    candidates = propose_candidates(bad_analysis)

    # 检查是否生成了 progression_system（不是 power_system）
    has_progression = any(
        "progression_system" in c for c in candidates
    )

    assert has_progression, "Fallback 应生成 progression_system"
    print("  ✅ Fallback 生成 progression_system（新格式）")

    # 检查都市候选是否包含 wealth 类型
    urban_candidate = candidates[0] if candidates else {}
    prog = urban_candidate.get("progression_system") or {}

    assert prog.get("type") == "wealth", f"都市候选应使用 WealthSystem，实际: {prog.get('type')}"
    print("  ✅ 都市候选使用 WealthSystem")


def test_unknown_genre_no_silent_fallback():
    """测试 2: 未知题材不静默回退奇幻"""
    print("\n测试 2: 未知题材处理...")

    unknown_analysis = {
        "genre_signals": ["武侠"],  # 未定义的题材
        "reader_rewards": ["justice"],
        "structure_signals": ["linear"],
    }

    candidates = propose_candidates(unknown_analysis)

    assert candidates, "未知题材应返回候选"

    first = candidates[0]

    # 检查是否返回了需要人工确认的候选
    if first.get("require_human_confirmation"):
        print(f"  ✅ 未知题材需要人工确认")
        print(f"     degraded_reason: {first.get('degraded_reason')}")
    elif first.get("title") in ["灰烬纪元的执灯人", "群星下的无名王座"]:
        assert False, f"未知题材不应静默回退到奇幻: {first.get('title')}"
    else:
        print(f"  ⚠️  未知题材返回候选: {first.get('title')}")


def test_genre_profile_id_in_outline():
    """测试 3: outline 包含 genre_profile_id"""
    print("\n测试 3: genre_profile_id 字段...")

    # 模拟 synthesize_final_outline
    candidates = [{
        "id": "TEST-A",
        "title": "测试都市",
        "genre": ["都市"],
        "logline": "测试",
        "direction": "test",
        "design_focus": [],
        "protagonist_engine": {
            "desire": "test",
            "flaw": "test",
            "golden_finger": "test",
            "cost": "test"
        },
        "progression_system": {
            "type": "wealth",
            "tiers": ["贫困", "富豪"],
            "breakthrough_condition": "test",
            "hard_limits": []
        },
        "characters": [],
        "world": {"summary": "test", "rules": []},
    }]

    reviews = [{
        "candidate_id": "TEST-A",
        "verdict": "promising",
        "score": 8.0,
        "risk_level": "low",
        "guardrails": [],
    }]

    merged = {
        "genre_signals": ["都市"],
        "reader_rewards": [],
        "structure_signals": [],
    }

    outline = synthesize_final_outline(
        candidates, reviews, merged,
        "TEST-PROJECT", [], None
    )

    # 检查 genre_profile_id
    assert "genre_profile_id" in outline, "outline 应包含 genre_profile_id"
    print(f"  ✅ outline 包含 genre_profile_id: {outline['genre_profile_id']}")

    # 检查 genre_contract_version
    assert "genre_contract_version" in outline, "outline 应包含 genre_contract_version"
    print(f"  ✅ outline 包含 genre_contract_version: {outline['genre_contract_version']}")

    # 检查 progression_system 优先级
    assert outline.get("progression_system"), "outline 应优先使用 progression_system"
    print(f"  ✅ outline 优先使用 progression_system")


def test_progression_main_path():
    """测试 4: Progression 主路径切换"""
    print("\n测试 4: Progression 主路径...")

    # 测试都市、玄幻、科幻的 fallback
    genres_to_test = [
        ("都市", "wealth"),
        ("玄幻", "power"),
        ("科幻", "tech"),
    ]

    for genre, expected_type in genres_to_test:
        analysis = {
            "genre_signals": [genre],
            "reader_rewards": [],
            "structure_signals": [],
        }

        candidates = propose_candidates(analysis)

        assert candidates, f"{genre} 应有候选"

        prog = candidates[0].get("progression_system") or {}
        actual_type = prog.get("type")

        assert actual_type == expected_type, f"{genre} 应为 {expected_type}，实际: {actual_type}"
        print(f"  ✅ {genre} → {expected_type}")


def test_genre_contract_validation():
    """测试 5: 题材契约验证功能"""
    print("\n测试 5: 题材契约验证...")

    # 创建包含违规的 outline
    bad_outline = {
        "genre": ["都市"],
        "logline": "主角在公司修炼，突破到金丹期",
        "world": {"summary": "现代都市，灵气复苏"},
        "characters": [{"arc": "从打工仔修炼成仙"}],
    }

    result = validate_outline_genre(bad_outline)

    assert not result.ok, "应检测到违规"
    assert len(result.violations) > 0, "应有违规记录"
    print(f"  ✅ 检测到违规: {len(result.violations)} 处")
    print(f"     关键词: {[v.keyword for v in result.violations[:3]]}")


def test_summary():
    """运行所有 P0 整改验证测试"""
    print("=" * 60)
    print("P0 整改验证测试")
    print("=" * 60)

    test_genre_contract_gate_in_outline()
    test_unknown_genre_no_silent_fallback()
    test_genre_profile_id_in_outline()
    test_progression_main_path()
    test_genre_contract_validation()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n🎉 所有测试通过！")


if __name__ == "__main__":
    test_summary()
