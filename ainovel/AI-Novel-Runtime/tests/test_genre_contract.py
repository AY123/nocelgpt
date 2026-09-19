"""
P0-B: 题材契约门禁测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.genre_contract import (
    validate_genre_contract,
    validate_outline_genre,
    validate_chapter_genre,
    GenreContractResult,
)


def test_urban_contract_forbids_xuanhuan():
    """测试都市契约禁止玄幻元素"""
    print("测试 1: 都市契约禁止玄幻元素...")

    # 包含修炼的都市文本
    bad_content = "陈默在公司上班，晚上回家修炼，突破到了筑基期。"

    result = validate_genre_contract("都市", bad_content, strict=True)

    if result.ok:
        print(f"  ❌ 应该检测到违规，但验证通过")
        return False

    if len(result.violations) == 0:
        print(f"  ❌ 没有记录违规")
        return False

    # 验证检测到"修炼"和"筑基"
    keywords = [v.keyword for v in result.violations]
    if "修炼" not in keywords:
        print(f"  ❌ 未检测到'修炼'关键词")
        return False

    print(f"  ✅ 检测到违规: {keywords}")
    return True


def test_urban_contract_allows_urban():
    """测试都市契约允许都市内容"""
    print("\n测试 2: 都市契约允许都市内容...")

    # 纯都市内容
    good_content = "陈默在公司上班，处理了一天的报表，晚上和同事去吃饭。"

    result = validate_genre_contract("都市", good_content, strict=True)

    if not result.ok:
        print(f"  ❌ 纯都市内容不应该被拒绝")
        print(f"     违规: {[v.keyword for v in result.violations]}")
        return False

    print(f"  ✅ 纯都市内容验证通过")
    return True


def test_xuanhuan_contract_forbids_modern():
    """测试玄幻契约禁止现代元素"""
    print("\n测试 3: 玄幻契约禁止现代元素...")

    # 包含股票的玄幻文本
    bad_content = "少年修炼到元婴期后，回到凡间炒股票，成为股市大佬。"

    result = validate_genre_contract("玄幻", bad_content, strict=True)

    if result.ok:
        print(f"  ❌ 应该检测到违规，但验证通过")
        return False

    keywords = [v.keyword for v in result.violations]
    if "股票" not in keywords:
        print(f"  ❌ 未检测到'股票'关键词")
        return False

    print(f"  ✅ 检测到违规: {keywords}")
    return True


def test_xuanhuan_contract_allows_cultivation():
    """测试玄幻契约允许修炼元素"""
    print("\n测试 4: 玄幻契约允许修炼元素...")

    # 纯玄幻内容
    good_content = "少年修炼三年，终于突破到筑基期，获得了一件法宝。"

    result = validate_genre_contract("玄幻", good_content, strict=True)

    if not result.ok:
        print(f"  ❌ 纯玄幻内容不应该被拒绝")
        print(f"     违规: {[v.keyword for v in result.violations]}")
        return False

    print(f"  ✅ 纯玄幻内容验证通过")
    return True


def test_outline_validation():
    """测试 outline 验证"""
    print("\n测试 5: outline 题材契约验证...")

    # 都市 outline 包含玄幻元素
    bad_outline = {
        "genre": ["都市"],
        "logline": "主角在公司修炼，突破到金丹期成为总裁",
        "world": {
            "summary": "现代都市，但存在灵气复苏"
        },
        "characters": [
            {
                "arc": "从打工仔修炼成仙",
                "motivation": "获得法宝"
            }
        ]
    }

    result = validate_outline_genre(bad_outline)

    if result.ok:
        print(f"  ❌ 应该检测到违规")
        return False

    keywords = [v.keyword for v in result.violations]
    print(f"  ✅ 检测到违规: {keywords}")
    return True


def test_chapter_validation():
    """测试 chapter 验证"""
    print("\n测试 6: chapter 题材契约验证...")

    # 都市章节包含修炼
    bad_chapter = """
    陈默坐在办公室里，表面上在处理文件，实际上在运转体内的灵气。
    经过一夜的修炼，他终于突破到了筑基期。
    """

    result = validate_chapter_genre(bad_chapter, "都市", "TASK-00001")

    if result.ok:
        print(f"  ❌ 应该检测到违规")
        return False

    print(f"  ✅ 检测到违规: {[v.keyword for v in result.violations]}")
    return True


def test_urban_rebirth_subgenre():
    """测试都市重生子类型"""
    print("\n测试 7: 都市重生子类型处理...")

    # 都市重生允许"重生"但不允许"修炼"
    content = "35岁的陈默重生回到18岁，开始修炼成仙。"

    result = validate_genre_contract("都市重生", content, strict=True)

    if result.ok:
        print(f"  ❌ 应该检测到'修炼'违规")
        return False

    # "重生"不应该被标记为违规
    keywords = [v.keyword for v in result.violations]
    if "重生" in keywords:
        print(f"  ❌ '重生'不应该是违规关键词")
        return False

    print(f"  ✅ 正确处理都市重生子类型")
    return True


def test_summary():
    """运行所有题材契约门禁测试"""
    print("=" * 60)
    print("题材契约门禁测试（P0-B）")
    print("=" * 60)

    results = []

    results.append(("都市禁止玄幻", test_urban_contract_forbids_xuanhuan()))
    results.append(("都市允许都市", test_urban_contract_allows_urban()))
    results.append(("玄幻禁止现代", test_xuanhuan_contract_forbids_modern()))
    results.append(("玄幻允许修炼", test_xuanhuan_contract_allows_cultivation()))
    results.append(("outline 验证", test_outline_validation()))
    results.append(("chapter 验证", test_chapter_validation()))
    results.append(("都市重生处理", test_urban_rebirth_subgenre()))

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
        print("\n🎉 题材契约门禁测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_summary())
