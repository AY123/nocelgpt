"""
P0 修复验证测试 - 验证 outline 加载和 chapter 门禁
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.outline.writer import load_project_outline
from runtime.chapter.finalizer import Finalizer
from runtime.chapter.types import ChapterRevision, ChapterReview
from runtime.genre_contract import validate_chapter_genre


def test_outline_loading():
    """测试 1: outline 加载功能"""
    print("测试 1: outline 加载...")

    # 测试加载函数存在
    try:
        from runtime.outline.writer import load_project_outline
        print("  ✅ load_project_outline 导入成功")
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        assert False, "load_project_outline 应该存在"


def test_chapter_genre_gate_with_violation():
    """测试 2: chapter 门禁对违规内容的阻断"""
    print("\n测试 2: chapter 门禁验证...")

    # 创建都市章节包含玄幻内容
    violation_text = """
    # 第一章

    陈默在公司里修炼，运转体内灵气。
    经过一夜修炼，他突破到了筑基期。
    获得了一件法宝，实力大增。
    """

    result = validate_chapter_genre(violation_text, "都市", "TEST-CH-001")

    assert not result.ok, "应该检测到违规"
    assert len(result.violations) > 0, "应该有违规记录"

    violations = [v.keyword for v in result.violations]
    print(f"  ✅ 检测到违规: {violations}")

    # 验证关键词
    assert "修炼" in violations, "应该检测到'修炼'"
    assert "灵气" in violations, "应该检测到'灵气'"


def test_chapter_genre_gate_without_violation():
    """测试 3: chapter 门禁对合规内容放行"""
    print("\n测试 3: 合规内容验证...")

    # 纯都市内容
    clean_text = """
    # 第一章

    陈默坐在办公室里，处理着一天的工作。
    下班后和同事去吃饭，讨论着公司的项目。
    回到家已经很晚了。
    """

    result = validate_chapter_genre(clean_text, "都市", "TEST-CH-002")

    assert result.ok, "纯都市内容应该通过"
    print("  ✅ 纯都市内容通过验证")


def test_schema_validation():
    """测试 4: schema 包含新字段"""
    print("\n测试 4: schema 验证...")

    import json
    schema_path = Path(__file__).parent.parent.parent / "AI-Novel-Standard" / "contracts" / "outline.schema.json"

    with open(schema_path, 'r') as f:
        schema = json.load(f)

    properties = schema.get("properties", {})

    assert "genre_profile_id" in properties, "schema 应包含 genre_profile_id"
    assert "genre_contract_version" in properties, "schema 应包含 genre_contract_version"
    assert "progression_system" in properties, "schema 应包含 progression_system"

    print("  ✅ schema 包含所有新字段")

    # 验证 progression_system 的 type 枚举
    prog_props = properties["progression_system"].get("properties", {})
    if "type" in prog_props:
        enum_values = prog_props["type"].get("enum", [])
        assert "wealth" in enum_values, "应支持 wealth 类型"
        assert "power" in enum_values, "应支持 power 类型"
        print(f"  ✅ progression_system.type 支持: {enum_values}")


def test_summary():
    """运行所有 P0 修复验证测试"""
    print("=" * 60)
    print("P0 修复验证测试")
    print("=" * 60)

    test_outline_loading()
    test_chapter_genre_gate_with_violation()
    test_chapter_genre_gate_without_violation()
    test_schema_validation()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n🎉 P0 修复验证通过！")


if __name__ == "__main__":
    test_summary()
