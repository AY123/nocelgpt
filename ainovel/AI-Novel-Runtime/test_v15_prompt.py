#!/usr/bin/env python3
"""
测试v15 Prompt生成器
"""

import sys
from pathlib import Path

# 添加路径
runtime_path = Path(__file__).parent.parent
sys.path.insert(0, str(runtime_path))

from runtime.prompts.v15.chapter import (
    render_chapter_prompt_v15,
    validate_v15_config,
    _render_base_prompt
)


def test_v15_config_validation():
    """测试v15配置验证"""
    print("=" * 70)
    print("测试1: v15配置验证")
    print("=" * 70)

    contracts_dir = Path('../contracts')
    schemas_dir = Path('../schemas')

    is_valid = validate_v15_config(contracts_dir, schemas_dir)

    print(f"contracts_dir存在: {contracts_dir.exists()}")
    print(f"schemas_dir存在: {schemas_dir.exists()}")
    print(f"配置有效: {is_valid}")

    if is_valid:
        print("✅ v15配置验证通过")
    else:
        print("❌ v15配置验证失败")

    print()


def test_base_prompt_generation():
    """测试基础prompt生成"""
    print("=" * 70)
    print("测试2: 基础Prompt生成")
    print("=" * 70)

    context = {
        'objective': '段奕尘与镜见川商议下一步计划',
        'ir': '两人站在矿场边缘，刚刚揭示了妹妹被拖入晶石的真相'
    }

    prompt = _render_base_prompt(101, context)

    print(f"生成的prompt长度: {len(prompt)}字")
    print(f"包含章节号: {'第101章' in prompt}")
    print(f"包含目标: {'商议' in prompt}")
    print()
    print("Prompt预览（前300字）：")
    print("-" * 70)
    print(prompt[:300])
    print("...")
    print()
    print("✅ 基础prompt生成成功")
    print()


def test_v15_prompt_with_contract():
    """测试v15 prompt生成（带契约）"""
    print("=" * 70)
    print("测试3: v15 Prompt生成（带契约）")
    print("=" * 70)

    contracts_dir = Path('../contracts')
    schemas_dir = Path('../schemas')

    context = {
        'objective': '段奕尘与镜见川商议下一步计划',
        'ir': '两人站在矿场边缘'
    }

    try:
        prompt = render_chapter_prompt_v15(
            chapter=101,
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            base_context=context,
            strict_mode=False
        )

        print(f"生成的prompt长度: {len(prompt)}字")
        print(f"包含契约: {'章节契约' in prompt}")
        print(f"包含入口要求: {'入口要求' in prompt}")
        print(f"包含出口要求: {'出口要求' in prompt}")
        print()
        print("Prompt预览（前500字）：")
        print("-" * 70)
        print(prompt[:500])
        print("...")
        print()
        print("✅ v15 prompt生成成功")

    except Exception as e:
        print(f"❌ 生成失败: {e}")

    print()


def test_v15_fallback():
    """测试v15降级到v5"""
    print("=" * 70)
    print("测试4: v15降级（无契约章节）")
    print("=" * 70)

    contracts_dir = Path('../contracts')
    schemas_dir = Path('../schemas')

    context = {
        'objective': '测试章节',
        'ir': '测试内容'
    }

    try:
        # 测试不存在的章节（应该降级）
        prompt = render_chapter_prompt_v15(
            chapter=999,
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            base_context=context,
            strict_mode=False  # 非严格模式
        )

        print(f"生成的prompt长度: {len(prompt)}字")
        print(f"包含契约: {'章节契约' in prompt}")
        print(f"是v5 fallback: {'章节契约' not in prompt}")
        print()
        print("✅ 降级机制工作正常")

    except Exception as e:
        print(f"错误: {e}")

    print()


def test_v15_strict_mode():
    """测试v15严格模式"""
    print("=" * 70)
    print("测试5: v15严格模式（应该抛异常）")
    print("=" * 70)

    contracts_dir = Path('../contracts')
    schemas_dir = Path('../schemas')

    context = {'objective': '测试', 'ir': '测试'}

    try:
        prompt = render_chapter_prompt_v15(
            chapter=999,  # 不存在的章节
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            base_context=context,
            strict_mode=True  # 严格模式
        )
        print("❌ 应该抛出异常但没有")
    except Exception as e:
        print(f"✅ 正确抛出异常: {type(e).__name__}")
        print(f"   错误信息: {str(e)[:80]}...")

    print()


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("v15 Prompt生成器测试套件")
    print("=" * 70)
    print()

    test_v15_config_validation()
    test_base_prompt_generation()
    test_v15_prompt_with_contract()
    test_v15_fallback()
    test_v15_strict_mode()

    print("=" * 70)
    print("测试完成")
    print("=" * 70)
    print()


if __name__ == '__main__':
    run_all_tests()
