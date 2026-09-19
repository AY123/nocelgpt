#!/usr/bin/env python3
"""
测试脚本：使用契约生成Ch101并验证
"""

import json
import sys
sys.path.insert(0, 'prompts')
sys.path.insert(0, 'tools')

from chapter_prompt_v15 import generate_chapter_prompt_v15
from validate_contract import ContractValidator


def test_ch101_generation():
    """
    测试Ch101生成流程

    步骤：
    1. 加载契约
    2. 生成prompt
    3. 调用LLM生成正文（需要手动或API）
    4. 验证契约遵守
    5. 输出报告
    """

    print("=" * 70)
    print("Ch101生成与验证测试")
    print("=" * 70)
    print()

    # Step 1: 加载契约
    print("Step 1: 加载契约...")
    with open('contracts/chapter_101_contract.json', 'r') as f:
        contract = json.load(f)

    if not contract.get('approved'):
        print("❌ 错误：契约未批准")
        return

    print("✅ 契约已批准")
    print()

    # Step 2: 生成prompt
    print("Step 2: 生成prompt...")
    prompt = generate_chapter_prompt_v15(101, contract)

    with open('prompts/ch101_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"✅ Prompt已生成（{len(prompt)}字）")
    print()

    # Step 3: 提示手动生成
    print("Step 3: 生成正文")
    print("-" * 70)
    print("请使用以下prompt通过LLM生成Ch101正文：")
    print()
    print("  文件：prompts/ch101_prompt.txt")
    print()
    print("  或直接复制以下内容到LLM：")
    print()
    print(prompt)
    print()
    print("-" * 70)
    print()
    print("生成后，将正文保存到：generated/chapter_101.md")
    print()

    # Step 4-5: 验证（需要生成后的正文）
    print("Step 4-5: 验证（需要正文）")
    print()
    print("生成正文后，运行验证：")
    print("  python3 test_validate_ch101.py")
    print()


def validate_ch101():
    """
    验证Ch101正文

    前提：generated/chapter_101.md已存在
    """

    import os

    print("=" * 70)
    print("Ch101契约验证")
    print("=" * 70)
    print()

    # 检查文件
    if not os.path.exists('generated/chapter_101.md'):
        print("❌ 错误：未找到生成的正文")
        print("   请先生成：generated/chapter_101.md")
        return

    # 读取正文
    with open('generated/chapter_101.md', 'r', encoding='utf-8') as f:
        ch101_text = f.read()

    print(f"✅ 已加载Ch101正文（{len(ch101_text)}字）")
    print()

    # 读取Ch100作为对比
    with open('novel-lingse-complete-100-chapters.md', 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    match = re.search(r'# 第一百章.*?(?=# 第|\Z)', content, re.DOTALL)

    if not match:
        print("❌ 错误：未找到Ch100")
        return

    ch100_text = match.group(0)

    # 验证
    validator = ContractValidator('contracts')
    result = validator.validate_transition(100, 101, ch100_text, ch101_text)

    print("验证结果：")
    print("-" * 70)

    if result['valid']:
        print("✅ 验证通过！无硬错误")
    else:
        print("❌ 验证失败")
        print()
        print("硬错误：")
        for error in result['hard_errors']:
            print(f"  - {error}")

    if result['soft_issues']:
        print()
        print("软问题（提醒）：")
        for issue in result['soft_issues']:
            print(f"  - {issue}")

    print()
    print("=" * 70)

    # 保存报告
    report = {
        "chapter": 101,
        "text_length": len(ch101_text),
        "validation": result
    }

    with open('reports/ch101_validation.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("📁 验证报告已保存：reports/ch101_validation.json")
    print()


if __name__ == '__main__':
    # 运行生成测试
    test_ch101_generation()

    print()
    print("=" * 70)
    print("下一步")
    print("=" * 70)
    print()
    print("1. 使用上述prompt通过LLM生成Ch101")
    print("2. 保存到 generated/chapter_101.md")
    print("3. 运行验证：python3 test_ch101.py --validate")
    print()
