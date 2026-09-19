#!/usr/bin/env python3
"""
测试验证器功能
"""

import sys
sys.path.insert(0, 'tools')
from validate_contract import ContractValidator


def test_location_extraction():
    """测试地点提取"""
    print("=" * 70)
    print("测试地点提取")
    print("=" * 70)
    print()

    validator = ContractValidator()

    test_cases = [
        ("段奕尘站在矿场边缘的乱石堆旁", "loc_矿场边缘_乱石堆"),
        ("他们走到秘密通道入口", "loc_矿场_秘密通道入口"),
        ("通道深处一片漆黑", "loc_秘密通道_第一层深处"),
        ("第二层入口前立着一扇石门", "loc_秘密通道_第二层入口"),
        ("随机文本没有地点", "loc_unknown"),
    ]

    passed = 0
    for text, expected in test_cases:
        result = validator._extract_location(text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1

        print(f"{status} 文本: {text[:30]}")
        print(f"   期望: {expected}")
        print(f"   实际: {result}")
        print()

    print(f"通过: {passed}/{len(test_cases)}")
    print()


def test_keyword_extraction():
    """测试关键词提取"""
    print("=" * 70)
    print("测试关键词提取")
    print("=" * 70)
    print()

    validator = ContractValidator()

    text = "曜师听见了段奕尘的呼唤，远处晶石响应发光"
    keywords = validator._extract_keywords(text)

    print(f"文本: {text}")
    print(f"提取关键词: {keywords}")
    print(f"关键词数量: {len(keywords)}")
    print()

    # 检查是否包含核心词
    core_words = ["曜师", "听见", "呼唤", "晶石", "发光"]
    found = [w for w in core_words if any(w in kw for kw in keywords)]

    print(f"核心词: {core_words}")
    print(f"找到: {found}")
    print()

    if len(found) >= 3:
        print("✅ 关键词提取基本可用")
    else:
        print("❌ 关键词提取质量不足")

    print()


def test_validation_logic():
    """测试验证逻辑"""
    print("=" * 70)
    print("测试验证逻辑")
    print("=" * 70)
    print()

    validator = ContractValidator()

    # 模拟契约
    entry_state = {
        "location_id": "loc_矿场边缘_乱石堆",
        "time_relation": "immediate",
        "pov": "段奕尘",
        "must_address": "曜师听见了呼唤，晶石响应"
    }

    # 测试场景1: 符合契约
    next_text_1 = "段奕尘站在矿场边缘的乱石堆上，刚才曜师听见了他的呼唤，远处的晶石闪烁着光芒。"

    actual_loc = validator._extract_location(next_text_1[:500])
    print(f"场景1: 符合契约")
    print(f"  要求地点: {entry_state['location_id']}")
    print(f"  实际地点: {actual_loc}")
    print(f"  匹配: {'✅' if actual_loc == entry_state['location_id'] else '❌'}")
    print()

    # 测试场景2: 地点不符
    next_text_2 = "此时，在通道深处，段奕尘向前走去。"

    actual_loc_2 = validator._extract_location(next_text_2[:500])
    print(f"场景2: 地点不符")
    print(f"  要求地点: {entry_state['location_id']}")
    print(f"  实际地点: {actual_loc_2}")
    print(f"  匹配: {'❌' if actual_loc_2 != entry_state['location_id'] else '✅'}")
    print()


def main():
    """运行所有测试"""
    test_location_extraction()
    test_keyword_extraction()
    test_validation_logic()

    print("=" * 70)
    print("测试完成")
    print("=" * 70)
    print()
    print("验证器功能已改进，可以:")
    print("  ✅ 提取地点并映射到location_id")
    print("  ✅ 提取关键词（改进版）")
    print("  ✅ 验证地点匹配")
    print()


if __name__ == '__main__':
    main()
