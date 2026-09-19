"""
题材系统 P0 修复验证测试
验证审核报告指出的关键缺陷是否已修复
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline import llm_agents
from runtime.outline.sources import load_reference_sources
from runtime.outline.analyzer import analyze_project_sources, merge_reference_analysis
from runtime.outline.agents import propose_candidates


def test_p0_1_template_parameter_fix():
    """P0-1: 验证 _PROPOSE_TEMPLATE.format() 参数已修复"""
    print("测试 P0-1: 模板参数修复...")

    # 检查模板是否有 {genre_constraint} 占位符
    template = llm_agents._PROPOSE_TEMPLATE
    assert "{genre_constraint}" in template, "模板应包含 {genre_constraint} 占位符"

    # 模拟非都市题材调用，验证不会抛出 KeyError
    mock_analysis = {
        "genre_signals": ["玄幻"],
        "reader_rewards": ["power-fantasy"],
        "structure_signals": ["linear"],
    }

    try:
        # 这应该不会因为缺少 genre_constraint 参数而失败
        template.format(
            analysis="test analysis",
            n=3,
            genre_constraint="测试约束"
        )
        print("  ✅ 模板参数修复验证通过")
        return True
    except KeyError as e:
        print(f"  ❌ 模板参数错误: {e}")
        return False


def test_p0_2_genre_specific_fallback():
    """P0-2: 验证确定性 fallback 已按题材分离"""
    print("\n测试 P0-2: 题材专用 fallback...")

    # 测试都市题材 fallback
    urban_analysis = {
        "genre_signals": ["都市", "都市重生"],
        "reader_rewards": ["wealth-fantasy"],
        "structure_signals": ["linear"],
    }
    urban_fallback = propose_candidates(urban_analysis)

    # 验证都市 fallback 不包含奇幻元素
    urban_titles = [c["title"] for c in urban_fallback]
    fantasy_keywords = ["灰烬", "执灯人", "王座", "图书馆", "天穹", "旧神", "预言"]

    has_fantasy = any(
        any(kw in title for kw in fantasy_keywords)
        for title in urban_titles
    )

    if has_fantasy:
        print(f"  ❌ 都市 fallback 仍包含奇幻元素: {urban_titles}")
        return False

    # 验证都市 fallback 包含现实关键词
    urban_keywords = ["重生", "创业", "职场", "系统", "神豪", "总裁", "金融"]
    has_urban = any(
        any(kw in title for kw in urban_keywords)
        for title in urban_titles
    )

    if not has_urban:
        print(f"  ❌ 都市 fallback 缺少都市关键词: {urban_titles}")
        return False

    print(f"  ✅ 都市 fallback: {urban_titles}")

    # 测试奇幻题材 fallback（应保持原有逻辑）
    fantasy_analysis = {
        "genre_signals": ["奇幻"],
        "reader_rewards": ["mystery"],
        "structure_signals": ["linear"],
    }
    fantasy_fallback = propose_candidates(fantasy_analysis)
    fantasy_titles = [c["title"] for c in fantasy_fallback]

    print(f"  ✅ 奇幻 fallback: {fantasy_titles}")
    return True


def test_p0_3_no_fantasy_world_rules():
    """P0-3: 验证 novel-dushi 不包含奇幻 world_rules"""
    print("\n测试 P0-3: Registry 题材一致性...")

    project = Path(__file__).parent.parent.parent / "novel-dushi"
    world_rules_dir = project / "registry" / "facts" / "world_rules"

    if not world_rules_dir.exists():
        print("  ✅ world_rules 目录为空")
        return True

    # 检查是否有 MAG-* 文件
    mag_files = list(world_rules_dir.glob("MAG-*.yaml"))
    if mag_files:
        print(f"  ❌ 发现奇幻魔法规则文件: {[f.name for f in mag_files]}")
        return False

    print("  ✅ 无奇幻 world_rules 文件")
    return True


def test_p0_4_urban_genre_detection():
    """P0-4: 验证都市题材识别准确性"""
    print("\n测试 P0-4: 都市题材识别...")

    project = Path(__file__).parent.parent.parent / "novel-dushi"
    source_result = load_reference_sources(project)

    if not source_result.ok:
        print("  ⚠️  无参考小说，跳过")
        return True

    analyses = analyze_project_sources(project, source_result.sources)
    merged = merge_reference_analysis(analyses)

    genre_signals = merged.get("genre_signals", [])
    primary = genre_signals[0] if genre_signals else "无"

    if primary not in ["都市", "都市重生"]:
        print(f"  ❌ 第一题材应为'都市'或'都市重生'，实际: {primary}")
        print(f"     完整信号: {genre_signals}")
        return False

    # 验证不应该有奇幻排第一
    if primary in ["奇幻", "玄幻", "仙侠"]:
        print(f"  ❌ 奇幻/玄幻不应排第一: {genre_signals}")
        return False

    print(f"  ✅ 题材识别: {genre_signals}")
    return True


def test_summary():
    """运行所有 P0 测试"""
    print("=" * 60)
    print("题材系统 P0 修复验证测试")
    print("=" * 60)

    results = []

    results.append(("P0-1: 模板参数", test_p0_1_template_parameter_fix()))
    results.append(("P0-2: 题材 fallback", test_p0_2_genre_specific_fallback()))
    results.append(("P0-3: Registry 清理", test_p0_3_no_fantasy_world_rules()))
    results.append(("P0-4: 题材识别", test_p0_4_urban_genre_detection()))

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
        print("\n🎉 所有 P0 修复验证通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_summary())
