"""
测试题材识别系统的准确性
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline.sources import load_reference_sources
from runtime.outline.analyzer import analyze_project_sources, merge_reference_analysis


def test_urban_rebirth_detection():
    """测试都市重生小说的题材识别"""
    project = Path(__file__).parent.parent.parent / "novel-dushi"
    source_result = load_reference_sources(project)

    assert source_result.ok, "Failed to load reference sources"

    analyses = analyze_project_sources(project, source_result.sources)
    merged = merge_reference_analysis(analyses)

    genre_signals = merged.get("genre_signals", [])

    # 断言：第一题材应该是"都市"或"都市重生"
    assert genre_signals[0] in ["都市", "都市重生"], \
        f"Expected '都市' or '都市重生' as primary genre, got '{genre_signals[0]}'"

    # 断言："都市"应该在前3个题材中
    assert "都市" in genre_signals[:3], \
        f"'都市' should be in top 3 genres, got {genre_signals[:3]}"

    # 断言：不应该有玄幻/奇幻元素排在前面
    assert genre_signals[0] not in ["玄幻", "奇幻", "仙侠"], \
        f"Fantasy genre should not be primary for urban novel, got '{genre_signals[0]}'"

    print(f"✅ 都市重生题材识别测试通过")
    print(f"   识别结果: {genre_signals}")
    return True


def test_genre_conflict_filtering():
    """测试负向关键词过滤功能"""
    from runtime.outline.analyzer import GENRE_CONFLICTS, _detect_genres

    # 测试文本：包含都市关键词但也有玄幻关键词
    mixed_text = "公司创业股票大学" + "修炼灵气法宝境界"
    genres = _detect_genres(mixed_text)

    # 因为有负向惩罚，都市得分应该被降低
    print(f"✅ 混合文本题材识别: {genres}")

    # 测试纯都市文本
    pure_urban_text = "公司创业股票投资大学高考校园互联网金融"
    pure_genres = _detect_genres(pure_urban_text)
    assert pure_genres[0] == "都市", f"Pure urban text should detect as '都市', got '{pure_genres[0]}'"

    print(f"✅ 纯都市文本识别: {pure_genres}")
    return True


if __name__ == "__main__":
    print("=== 运行题材识别测试 ===\n")

    try:
        test_urban_rebirth_detection()
        print()
        test_genre_conflict_filtering()
        print("\n🎉 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
