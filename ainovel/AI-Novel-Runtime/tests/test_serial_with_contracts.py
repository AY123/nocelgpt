"""
测试 Serial with Contracts 包装器
"""

import pytest
from pathlib import Path
from runtime.serialize.serial_with_contracts import (
    run_serial_with_contracts,
    _find_chapter_file,
)


class TestSerialWithContracts:
    """Serial with Contracts 测试"""

    @pytest.fixture
    def novel_dushi_path(self):
        """返回 novel-dushi 项目路径"""
        tests_dir = Path(__file__).parent
        runtime_dir = tests_dir.parent
        ai_novel_dir = runtime_dir.parent
        novel_dushi = ai_novel_dir / "novel-dushi"
        return novel_dushi

    def test_find_chapter_file(self, novel_dushi_path):
        """测试查找章节文件"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        # 尝试查找第1章
        chapter_file = _find_chapter_file(novel_dushi_path, 1)

        if chapter_file:
            print(f"\n找到第1章: {chapter_file}")
            assert chapter_file.exists()
        else:
            print(f"\n第1章未找到（这是正常的，如果还未生成）")

    def test_integration_disabled_by_default(self, novel_dushi_path):
        """测试契约集成默认禁用"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        # 这个测试只验证接口，不实际运行 Serial
        # 因为 Serial 需要很多依赖参数

        # 验证参数默认值
        import inspect
        from runtime.serialize.serial_with_contracts import run_serial_with_contracts

        sig = inspect.signature(run_serial_with_contracts)
        enable_param = sig.parameters['enable_contract_integration']

        assert enable_param.default is False, "契约集成应该默认禁用"
        print("\n✓ 契约集成默认禁用")


class TestConceptProof:
    """概念验证测试"""

    def test_contract_integration_can_be_created(self):
        """测试可以创建契约集成"""
        from runtime.serialize.contract_integration import create_integration
        from pathlib import Path

        tests_dir = Path(__file__).parent
        runtime_dir = tests_dir.parent
        ai_novel_dir = runtime_dir.parent
        novel_dushi = ai_novel_dir / "novel-dushi"

        if not novel_dushi.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi}")

        integration = create_integration(
            project_path=novel_dushi,
            enable_contract_integration=True
        )

        assert integration is not None
        assert integration.is_enabled()
        print(f"\n{integration.summary()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
