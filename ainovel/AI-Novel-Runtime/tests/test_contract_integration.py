"""
Contract Integration 集成测试
"""

import pytest
from pathlib import Path
from runtime.serialize.contract_integration import ContractIntegration, create_integration
from runtime.contract import ProductionState


class TestContractIntegration:
    """ContractIntegration 测试"""

    @pytest.fixture
    def novel_dushi_path(self):
        """返回 novel-dushi 项目路径"""
        # novel-dushi 在 AINovel 目录下
        tests_dir = Path(__file__).parent
        runtime_dir = tests_dir.parent  # AI-Novel-Runtime
        ai_novel_dir = runtime_dir.parent  # AINovel
        novel_dushi = ai_novel_dir / "novel-dushi"
        return novel_dushi

    def test_create_integration_with_real_project(self, novel_dushi_path):
        """测试使用真实项目创建集成"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)

        assert integration.is_enabled()
        assert len(integration.contracts) == 30
        print(f"\n{integration.summary()}")

    def test_get_contract(self, novel_dushi_path):
        """测试获取契约"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)

        # 获取第1章契约
        contract = integration.get_contract(1)
        assert contract is not None
        assert contract.chapter_number == 1
        assert contract.protagonist_name == "陈默"

        # 获取不存在的契约
        contract = integration.get_contract(999)
        assert contract is None

    def test_initialize_state(self, novel_dushi_path):
        """测试初始化状态"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)
        state = integration.initialize_state()

        assert state is not None
        assert state.chapter_number == 0
        assert state.protagonist.name == "陈默"
        assert state.current_date == "2013-01-15"

        print(f"\n{state.summary()}")

    def test_validate_chapter_entry_first_chapter(self, novel_dushi_path):
        """测试验证第1章入口条件"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)
        integration.initialize_state()

        # 第1章不需要上一章状态
        can_proceed, errors = integration.validate_chapter_entry(1)
        assert can_proceed
        assert len(errors) == 0

    def test_validate_chapter_entry_requires_previous_approved(self, novel_dushi_path):
        """测试验证第2章需要第1章通过"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)
        integration.initialize_state()

        # 第2章需要第1章状态
        can_proceed, errors = integration.validate_chapter_entry(
            2,
            previous_state=None
        )
        assert not can_proceed
        assert len(errors) > 0
        assert "缺少上一章状态" in errors[0]

    def test_validate_chapter_entry_blocked_state(self, novel_dushi_path):
        """测试验证被阻塞状态无法继续"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)
        integration.initialize_state()

        # 第1章被阻塞，第2章无法继续
        can_proceed, errors = integration.validate_chapter_entry(
            2,
            previous_state=ProductionState.BLOCKED
        )
        assert not can_proceed
        assert len(errors) > 0
        assert "无法继续" in errors[0]

    def test_validate_chapter_entry_approved_state(self, novel_dushi_path):
        """测试验证通过状态可以继续"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)
        state = integration.initialize_state()

        # 手动更新到第1章状态
        state.chapter_number = 1
        integration.current_state = state

        # 第1章通过，第2章可以继续
        can_proceed, errors = integration.validate_chapter_entry(
            2,
            previous_state=ProductionState.HUMAN_APPROVED
        )
        assert can_proceed
        assert len(errors) == 0

    def test_validate_chapter_draft(self, novel_dushi_path):
        """测试验证章节草稿"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)

        # 正确的草稿
        draft_text = "陈默" * 100 + "恒远投资公司" * 10 + "测试内容" * 100
        extracted_data = {
            'protagonist_name': '陈默',
            'date': '2013-01-15',
            'locations': ['恒远投资公司'],
            'characters': ['陈默'],
        }

        passed, result = integration.validate_chapter_draft(1, draft_text, extracted_data)
        assert passed
        assert result['passed']
        print(f"\n验证结果: {result}")

    def test_validate_chapter_draft_wrong_protagonist(self, novel_dushi_path):
        """测试验证错误主角名的草稿"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        integration = ContractIntegration(novel_dushi_path)

        # 错误的主角名
        draft_text = "林远" * 100
        extracted_data = {
            'protagonist_name': '林远',  # 错误
        }

        passed, result = integration.validate_chapter_draft(1, draft_text, extracted_data)
        assert not passed
        assert not result['passed']
        assert len(result['errors']) > 0
        print(f"\n验证失败: {result['errors']}")

    def test_create_integration_helper(self, novel_dushi_path):
        """测试 create_integration 辅助函数"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        # 启用集成
        integration = create_integration(novel_dushi_path, enable_contract_integration=True)
        assert integration is not None
        assert integration.is_enabled()

        # 禁用集成
        integration = create_integration(novel_dushi_path, enable_contract_integration=False)
        assert integration is None


if __name__ == "__main__":
    # 手动运行测试
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # 运行测试
    pytest.main([__file__, "-v", "-s"])
