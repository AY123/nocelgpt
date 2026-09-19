"""
测试从真实 Story Bible 加载契约
"""

from runtime.contract.chapter_contract import load_story_bible_contracts
from pathlib import Path


def test_load_contracts_from_real_bible():
    """测试从真实的 Story Bible 加载30个契约"""

    # 找到 Story Bible 路径
    bible_path = Path(__file__).parent.parent.parent / "novel-dushi" / "registry" / "story-bible" / "BIBLE-00001.yaml"

    if not bible_path.exists():
        print(f"⚠️  Story Bible 不存在: {bible_path}")
        print(f"   跳过测试")
        return

    print(f"📖 加载 Story Bible: {bible_path}")

    # 加载契约
    contracts = load_story_bible_contracts(str(bible_path))

    print(f"✓ 成功加载 {len(contracts)} 个契约")

    # 验证数量
    assert len(contracts) == 30, f"期望30个契约，实际 {len(contracts)}"

    # 验证每个契约
    for i, contract in enumerate(contracts):
        chapter_num = i + 1

        # 基本信息
        assert contract.chapter_number == chapter_num, f"第{chapter_num}章编号错误"
        assert contract.chapter_id == f"TASK-{chapter_num:05d}", f"第{chapter_num}章ID错误"

        # 主角名字
        assert contract.protagonist_name == "陈默", f"第{chapter_num}章主角名字错误"

        # 日期
        assert contract.date, f"第{chapter_num}章缺少日期"

        # Story Bible 版本
        assert contract.story_bible_version == "1.2", f"第{chapter_num}章 Story Bible 版本错误"

        print(f"  ✓ 第{chapter_num}章契约验证通过")
        print(f"     - 目标: {contract.objective[:50]}...")
        print(f"     - 对手: {contract.antagonist}")
        print(f"     - 日期: {contract.date}")
        print(f"     - 地点: {contract.allowed_locations}")

    # 打印一些统计信息
    print()
    print("📊 契约统计:")
    print(f"   - 总契约数: {len(contracts)}")
    print(f"   - 第一章日期: {contracts[0].date}")
    print(f"   - 最后一章日期: {contracts[-1].date}")
    print(f"   - Story Bible Hash: {contracts[0].story_bible_hash[:16]}...")

    # 验证时间线连续性
    print()
    print("🕐 时间线检查:")
    for i in range(len(contracts) - 1):
        curr_date = contracts[i].date
        next_date = contracts[i + 1].date

        if curr_date > next_date:
            print(f"   ❌ 时间倒流: 第{i+1}章 ({curr_date}) → 第{i+2}章 ({next_date})")
        else:
            print(f"   ✓ 第{i+1}章 ({curr_date}) → 第{i+2}章 ({next_date})")

    print()
    print("✅ 所有契约加载和验证完成！")


if __name__ == "__main__":
    test_load_contracts_from_real_bible()
