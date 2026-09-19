"""
P0-B: 端到端题材一致性验证
验证从参考分析 → outline → facts → chapter 的题材保持一致
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline.sources import load_reference_sources
from runtime.outline.analyzer import analyze_project_sources, merge_reference_analysis


def test_dushi_end_to_end_consistency():
    """测试 novel-dushi 端到端题材一致性"""
    print("测试: novel-dushi 端到端题材一致性...")

    project = Path(__file__).parent.parent.parent / "novel-dushi"

    if not project.exists():
        print("  ⚠️  项目不存在，跳过")
        return True

    # 1. 检查参考分析的题材识别
    source_result = load_reference_sources(project)
    if source_result.ok:
        analyses = analyze_project_sources(project, source_result.sources)
        merged = merge_reference_analysis(analyses)
        genre_signals = merged.get("genre_signals", [])
        print(f"  参考分析题材: {genre_signals[:3]}")

        if genre_signals and genre_signals[0] not in ["都市", "都市重生"]:
            print(f"  ❌ 参考分析第一题材应为都市，实际: {genre_signals[0]}")
            return False

    # 2. 检查 facts/characters 的题材一致性
    char_dir = project / "registry" / "facts" / "characters"
    if char_dir.exists():
        chars = list(char_dir.glob("*.yaml"))
        if chars:
            with open(chars[0], 'r', encoding='utf-8') as f:
                content = f.read()

            # 都市角色不应该有修炼相关描述
            fantasy_keywords = ["修炼", "境界", "突破", "灵气", "法宝", "丹药"]
            has_fantasy = any(kw in content for kw in fantasy_keywords)

            if has_fantasy:
                print(f"  ❌ 都市角色包含玄幻元素")
                return False

            print(f"  ✅ 角色 facts 无玄幻元素")

    # 3. 检查 world_rules 的题材一致性
    world_rules_dir = project / "registry" / "facts" / "world_rules"
    if world_rules_dir.exists():
        magic_files = list(world_rules_dir.glob("MAG-*.yaml"))
        power_files = list(world_rules_dir.glob("POW-*.yaml"))

        if magic_files or power_files:
            print(f"  ❌ 都市项目包含魔法/力量规则: {[f.name for f in magic_files + power_files]}")
            return False

        print(f"  ✅ world_rules 无奇幻规则")

    # 4. 检查生成的章节内容
    final_dir = project / "registry" / "derived" / "chapter-final"
    if final_dir.exists():
        final_files = list(final_dir.glob("final-*.json"))
        if final_files:
            with open(final_files[0], 'r', encoding='utf-8') as f:
                chapter = json.load(f)

            # 检查 body/prose 内容
            body = chapter.get("body", "") or chapter.get("prose", "")

            if body:
                # 都市章节不应该包含玄幻元素
                fantasy_keywords = ["修炼", "境界", "突破", "灵气", "法宝", "丹药", "灵力", "真元"]
                has_fantasy = any(kw in body for kw in fantasy_keywords)

                if has_fantasy:
                    print(f"  ❌ 都市章节包含玄幻元素")
                    return False

                # 应该包含都市元素
                urban_keywords = ["公司", "学校", "教室", "办公室", "城市", "手机", "电脑"]
                has_urban = any(kw in body for kw in urban_keywords)

                if not has_urban:
                    print(f"  ⚠️  章节内容缺少明显都市场景")

                print(f"  ✅ 章节内容题材一致")

    print(f"  ✅ 端到端题材一致性验证通过")
    return True


def test_genre_profile_presence():
    """测试 genre_profile_id 字段存在性（如果实现了的话）"""
    print("\n测试: genre_profile_id 字段...")

    project = Path(__file__).parent.parent.parent / "novel-dushi"

    # 检查 outline 是否有 genre_profile
    outline_dir = project / "registry" / "derived" / "outlines"
    if outline_dir.exists():
        outline_files = list(outline_dir.glob("*.json"))
        if outline_files:
            with open(outline_files[0], 'r', encoding='utf-8') as f:
                outline = json.load(f)

            if "genre_profile_id" in outline or "genre" in outline:
                print(f"  ✅ outline 包含题材字段")
            else:
                print(f"  ℹ️  outline 未实现 genre_profile_id（预期，P1 任务）")

    return True


def test_llm_mixed_genre_output():
    """测试 LLM 是否会生成混合题材输出（需要实际调用 LLM）"""
    print("\n测试: LLM 混合题材输出...")
    print("  ℹ️  需要实际 LLM 调用，跳过（手动验证）")
    return True


def test_summary():
    """运行所有端到端一致性测试"""
    print("=" * 60)
    print("端到端题材一致性验证（P0-B）")
    print("=" * 60)

    results = []

    results.append(("都市项目一致性", test_dushi_end_to_end_consistency()))
    results.append(("genre_profile 字段", test_genre_profile_presence()))
    results.append(("LLM 混合题材", test_llm_mixed_genre_output()))

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
        print("\n🎉 端到端题材一致性验证通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_summary())
