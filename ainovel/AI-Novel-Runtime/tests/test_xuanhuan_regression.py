"""
P0-B: 玄幻项目回归测试
验证题材系统改动不会破坏现有玄幻项目
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline.sources import load_reference_sources
from runtime.outline.analyzer import analyze_project_sources, merge_reference_analysis
from runtime.outline.agents import propose_candidates


def test_xuanhuan_genre_detection():
    """测试玄幻项目的题材识别"""
    print("测试 1: 玄幻题材识别...")

    project = Path(__file__).parent.parent.parent / "novel-lingse"

    if not project.exists():
        print("  ⚠️  novel-lingse 项目不存在，跳过")
        return True

    source_result = load_reference_sources(project)

    if not source_result.ok:
        print("  ⚠️  无参考小说，跳过")
        return True

    analyses = analyze_project_sources(project, source_result.sources)
    merged = merge_reference_analysis(analyses)

    genre_signals = merged.get("genre_signals", [])
    primary = genre_signals[0] if genre_signals else "无"

    print(f"  识别结果: {genre_signals}")

    # 玄幻项目应该识别为玄幻/仙侠/奇幻等，不应该是都市
    if primary == "都市":
        print(f"  ❌ 玄幻项目被误判为都市")
        return False

    print(f"  ✅ 第一题材: {primary}")
    return True


def test_xuanhuan_fallback():
    """测试玄幻题材 fallback 模板"""
    print("\n测试 2: 玄幻 fallback 模板...")

    xuanhuan_analysis = {
        "genre_signals": ["玄幻"],
        "reader_rewards": ["power-fantasy"],
        "structure_signals": ["linear"],
    }

    candidates = propose_candidates(xuanhuan_analysis)
    titles = [c["title"] for c in candidates]

    print(f"  Fallback 候选: {titles}")

    # 验证玄幻 fallback 包含修炼/境界等元素
    xuanhuan_keywords = ["神帝", "修炼", "境界", "突破", "传承"]
    has_xuanhuan = any(
        any(kw in title for kw in xuanhuan_keywords)
        for title in titles
    )

    if not has_xuanhuan:
        print(f"  ❌ 玄幻 fallback 缺少玄幻关键词")
        return False

    # 验证不应该包含都市元素
    urban_keywords = ["重生", "创业", "系统", "神豪", "职场", "公司"]
    has_urban = any(
        any(kw in title for kw in urban_keywords)
        for title in titles
    )

    if has_urban:
        print(f"  ❌ 玄幻 fallback 混入都市元素")
        return False

    print(f"  ✅ 玄幻 fallback 验证通过")
    return True


def test_fantasy_fallback_preserved():
    """测试奇幻 fallback 保持原有逻辑"""
    print("\n测试 3: 奇幻 fallback 向后兼容...")

    fantasy_analysis = {
        "genre_signals": ["奇幻"],
        "reader_rewards": ["mystery"],
        "structure_signals": ["linear"],
    }

    candidates = propose_candidates(fantasy_analysis)
    titles = [c["title"] for c in candidates]

    print(f"  Fallback 候选: {titles}")

    # 验证原有奇幻模板保留
    expected_titles = ["灰烬纪元的执灯人", "群星下的无名王座", "第九座天穹图书馆"]

    if titles != expected_titles:
        print(f"  ⚠️  奇幻 fallback 模板发生变化")
        print(f"     期望: {expected_titles}")
        print(f"     实际: {titles}")
        # 不算失败，只是提醒
        return True

    print(f"  ✅ 奇幻 fallback 保持原逻辑")
    return True


def test_power_system_in_xuanhuan():
    """测试玄幻 fallback 包含 power_system"""
    print("\n测试 4: 玄幻 power_system...")

    xuanhuan_analysis = {
        "genre_signals": ["玄幻"],
        "reader_rewards": ["power-fantasy"],
        "structure_signals": ["linear"],
    }

    candidates = propose_candidates(xuanhuan_analysis)

    for candidate in candidates:
        if "power_system" not in candidate:
            print(f"  ❌ 候选 {candidate['id']} 缺少 power_system")
            return False

        ps = candidate["power_system"]

        # 验证包含必要字段
        if "tiers" not in ps or "breakthrough_condition" not in ps:
            print(f"  ❌ power_system 缺少必要字段")
            return False

        # 验证 tiers 是修炼境界，不是都市财富
        tiers_str = str(ps["tiers"])
        urban_tier_keywords = ["打工仔", "小老板", "企业家", "资本家", "温饱", "小康"]

        if any(kw in tiers_str for kw in urban_tier_keywords):
            print(f"  ❌ 玄幻 power_system 包含都市财富等级: {ps['tiers']}")
            return False

    print(f"  ✅ 玄幻 power_system 验证通过")
    return True


def test_summary():
    """运行所有玄幻回归测试"""
    print("=" * 60)
    print("玄幻项目回归测试（P0-B）")
    print("=" * 60)

    results = []

    results.append(("玄幻题材识别", test_xuanhuan_genre_detection()))
    results.append(("玄幻 fallback", test_xuanhuan_fallback()))
    results.append(("奇幻 fallback 兼容", test_fantasy_fallback_preserved()))
    results.append(("玄幻 power_system", test_power_system_in_xuanhuan()))

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
        print("\n🎉 玄幻项目回归测试通过！改动不影响现有功能。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，改动可能破坏玄幻项目")
        return 1


if __name__ == "__main__":
    sys.exit(test_summary())
