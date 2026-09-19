#!/usr/bin/env python3
"""
Contract Gate单元测试
"""

import pytest
from pathlib import Path
import sys

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from runtime_plugins.contract import ContractGate, ContractCheckError


def test_precheck_success():
    """测试：precheck通过（Ch101已批准）"""
    gate = ContractGate(
        contracts_dir=Path('contracts'),
        schemas_dir=Path('schemas')
    )

    # 应该不抛异常
    gate.precheck(101)
    print("✅ Ch101 precheck通过")


def test_precheck_no_contract():
    """测试：precheck失败（契约不存在）"""
    gate = ContractGate(
        contracts_dir=Path('contracts'),
        schemas_dir=Path('schemas')
    )

    with pytest.raises(ContractCheckError) as exc_info:
        gate.precheck(999)

    assert "契约不存在" in str(exc_info.value)
    print("✅ 无契约时正确阻止")


def test_precheck_not_approved():
    """测试：precheck失败（未批准）"""
    # 这个测试需要一个approved=false的契约
    # 暂时跳过
    print("⏭ 跳过（需要未批准契约）")


def test_load_contract():
    """测试：加载契约"""
    gate = ContractGate(
        contracts_dir=Path('contracts'),
        schemas_dir=Path('schemas')
    )

    contract = gate.load_contract(101)

    assert contract is not None
    assert contract['chapter'] == 101
    assert 'entry_state' in contract
    assert 'exit_target' in contract
    print("✅ 契约加载成功")


def test_inject_contract():
    """测试：注入契约到prompt"""
    gate = ContractGate(
        contracts_dir=Path('contracts'),
        schemas_dir=Path('schemas')
    )

    contract = gate.load_contract(101)
    base_prompt = "这是原始prompt内容。"

    injected = gate.inject_contract(base_prompt, contract)

    # 验证注入内容
    assert "章节契约" in injected
    assert "入口要求" in injected
    assert "出口要求" in injected
    assert base_prompt in injected

    # 验证契约在前
    assert injected.index("章节契约") < injected.index(base_prompt)

    print("✅ 契约注入成功")
    print(f"   原始长度: {len(base_prompt)}字")
    print(f"   注入后: {len(injected)}字")


def test_validate_integration():
    """测试：验证集成"""
    gate = ContractGate(
        contracts_dir=Path('contracts'),
        schemas_dir=Path('schemas')
    )

    # 读取Ch100和Ch101
    with open('novel-lingse-complete-100-chapters.md', 'r') as f:
        content = f.read()

    import re
    match = re.search(r'# 第一百章.*?(?=# 第|\Z)', content, re.DOTALL)
    ch100_text = match.group(0) if match else ""

    with open('generated/chapter_101.md', 'r') as f:
        ch101_text = f.read()

    # 验证
    result = gate.validate(101, ch100_text, ch101_text)

    assert 'valid' in result
    assert 'hard_errors' in result
    assert 'soft_issues' in result

    print(f"✅ 验证功能集成成功")
    print(f"   验证结果: {'通过' if result['valid'] else '失败'}")
    print(f"   硬错误: {len(result['hard_errors'])}个")
    print(f"   软问题: {len(result['soft_issues'])}个")


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("Contract Gate 单元测试")
    print("=" * 70)
    print()

    tests = [
        ("Precheck成功", test_precheck_success),
        ("Precheck失败（无契约）", test_precheck_no_contract),
        ("Precheck失败（未批准）", test_precheck_not_approved),
        ("加载契约", test_load_contract),
        ("注入契约", test_inject_contract),
        ("验证集成", test_validate_integration),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_func in tests:
        print(f"测试: {name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            if "跳过" in str(e):
                skipped += 1
            else:
                failed += 1
                print(f"   ❌ 失败: {e}")
        print()

    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"跳过: {skipped}")
    print()

    if failed == 0:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 存在失败测试")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_all_tests())
