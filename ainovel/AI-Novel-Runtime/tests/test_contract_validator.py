"""
Contract Validator 测试
"""

import pytest
from pathlib import Path
from runtime.publishing.contract_validator import (
    validate_chapter_contracts_for_release,
    get_release_validation_summary,
)


class TestContractValidator:
    """Contract Validator 测试"""

    @pytest.fixture
    def novel_dushi_path(self):
        """返回 novel-dushi 项目路径"""
        tests_dir = Path(__file__).parent
        runtime_dir = tests_dir.parent
        ai_novel_dir = runtime_dir.parent
        novel_dushi = ai_novel_dir / "novel-dushi"
        return novel_dushi

    def test_validate_single_chapter(self, novel_dushi_path):
        """测试验证单个章节"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        result = validate_chapter_contracts_for_release(
            project_path=novel_dushi_path,
            chapter_list=[1]
        )

        assert result is not None
        assert 'passed' in result
        assert 'blocking_issues' in result
        assert 'statistics' in result
        assert result['statistics']['total_chapters'] == 1

        print(f"\n验证结果: {result['passed']}")
        print(f"统计: {result['statistics']}")

    def test_validate_multiple_chapters(self, novel_dushi_path):
        """测试验证多个章节"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        result = validate_chapter_contracts_for_release(
            project_path=novel_dushi_path,
            chapter_list=[1, 2, 3]
        )

        assert result['statistics']['total_chapters'] == 3
        print(f"\n验证 3 章: {result['passed']}")
        print(f"通过: {result['statistics']['approved_chapters']}/3")

    def test_validation_summary(self, novel_dushi_path):
        """测试生成验证摘要"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        result = validate_chapter_contracts_for_release(
            project_path=novel_dushi_path,
            chapter_list=[1, 2, 3]
        )

        summary = get_release_validation_summary(result)
        assert summary
        assert "Release Validation Summary" in summary
        print(f"\n{summary}")

    def test_chapter_validations_detail(self, novel_dushi_path):
        """测试每章详细验证结果"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        result = validate_chapter_contracts_for_release(
            project_path=novel_dushi_path,
            chapter_list=[1]
        )

        chapter_validations = result.get('chapter_validations', {})
        assert 1 in chapter_validations

        chapter_1 = chapter_validations[1]
        assert 'exists' in chapter_1
        assert 'state_check' in chapter_1
        assert 'contract_check' in chapter_1

        print(f"\n第1章验证:")
        print(f"  存在: {chapter_1['exists']}")
        print(f"  状态: {chapter_1['state_check']}")
        print(f"  契约: {chapter_1['contract_check']}")

    def test_nonexistent_chapters(self, novel_dushi_path):
        """测试不存在的章节"""
        if not novel_dushi_path.exists():
            pytest.skip(f"novel-dushi 不存在: {novel_dushi_path}")

        result = validate_chapter_contracts_for_release(
            project_path=novel_dushi_path,
            chapter_list=[999]  # 不存在的章节
        )

        # 应该标记为失败
        assert not result['passed']
        assert len(result['blocking_issues']) > 0
        print(f"\n不存在章节的阻塞问题: {result['blocking_issues']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
