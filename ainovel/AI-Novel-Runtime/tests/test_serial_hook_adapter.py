"""
Serial Hook Adapter 测试
"""

import pytest
from pathlib import Path
from runtime.serialize.serial_hook_adapter import SerialHookAdapter, create_adapter
from runtime.contract import ProductionState


class TestSerialHookAdapter:
    """SerialHookAdapter 测试"""

    @pytest.fixture
    def novel_dushi_path(self):
        """返回 novel-dushi 项目路径"""
        tests_dir = Path(__file__).parent
        runtime_dir = tests_dir.parent
        ai_novel_dir = runtime_dir.parent
        novel_dushi = ai_novel_dir / "novel-dushi"
        return novel_dushi

    def test_create_adapter_disabled(self, novel_dushi_path):
        """测试创建禁用的适配器"""
        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=False
        )

        assert adapter is not None
        assert not adapter.enabled
        print("\n✓ 禁用的适配器创建成功")

    def test_create_adapter_enabled(self, novel_dushi_path):
        """测试创建启用的适配器"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        assert adapter is not None
        assert adapter.enabled
        print("\n✓ 启用的适配器创建成功")

    def test_can_generate_first_chapter(self, novel_dushi_path):
        """测试第1章总是可以生成"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        can_proceed, errors = adapter.can_generate_chapter(1)
        assert can_proceed
        assert len(errors) == 0
        print("\n✓ 第1章可以生成")

    def test_cannot_generate_second_without_approval(self, novel_dushi_path):
        """测试第2章需要第1章审核通过"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        # 模拟第1章只是 GENERATED 状态
        adapter.chapter_states[1] = ProductionState.GENERATED

        can_proceed, errors = adapter.can_generate_chapter(2)
        assert not can_proceed
        assert len(errors) > 0
        print(f"\n✓ 第2章被正确阻塞: {errors}")

    def test_can_generate_second_with_approval(self, novel_dushi_path):
        """测试第2章在第1章审核通过后可以生成"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        # 模拟第1章是 HUMAN_APPROVED 状态
        adapter.chapter_states[1] = ProductionState.HUMAN_APPROVED

        # 更新故事状态到第1章（避免连续性检查失败）
        adapter.hook.integration.current_state.chapter_number = 1

        can_proceed, errors = adapter.can_generate_chapter(2)
        assert can_proceed
        assert len(errors) == 0
        print("\n✓ 第2章可以生成（第1章已审核通过）")

    def test_force_generation(self, novel_dushi_path):
        """测试强制生成可以跳过阻塞"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        # 模拟第1章是 BLOCKED 状态
        adapter.chapter_states[1] = ProductionState.BLOCKED

        # 正常情况下无法生成
        can_proceed, _ = adapter.can_generate_chapter(2, force=False)
        assert not can_proceed

        # 强制生成可以跳过
        can_proceed, _ = adapter.can_generate_chapter(2, force=True)
        assert can_proceed
        print("\n✓ 强制生成可以跳过阻塞")

    def test_validate_and_save_chapter(self, novel_dushi_path):
        """测试验证并保存章节"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        # 模拟章节内容
        draft = "陈默" * 100 + "测试内容" * 100

        # 记录保存状态
        saved_state = None

        def save_callback(state: ProductionState):
            nonlocal saved_state
            saved_state = state

        # 验证并保存
        passed, state = adapter.validate_and_save_chapter(
            chapter_number=1,
            draft_text=draft,
            save_callback=save_callback
        )

        assert passed
        assert state == ProductionState.GENERATED
        assert saved_state == ProductionState.GENERATED
        print(f"\n✓ 章节验证并保存成功，状态: {state}")

    def test_statistics(self, novel_dushi_path):
        """测试统计信息"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        adapter = create_adapter(
            project_path=novel_dushi_path,
            enable_contract_integration=True
        )

        # 验证一些章节
        draft = "陈默" * 100
        adapter.validate_and_save_chapter(1, draft)
        adapter.validate_and_save_chapter(2, draft)

        # 获取统计
        stats = adapter.get_statistics()
        assert stats['total_chapters'] >= 2
        print(f"\n✓ 统计信息: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
