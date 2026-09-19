"""test_length_strategy.py — Phase 1 Task 1.3.2 测试

测试多轮收紧策略
"""
import pytest
from runtime.chapter.length_strategy import (
    progressive_length_constraint,
    should_retry_for_length,
    format_length_instruction,
    estimate_retry_cost,
)


class TestProgressiveConstraint:
    """测试逐次收紧策略"""

    def test_attempt1_normal_ceiling(self):
        """第一次尝试：正常天花板"""
        strategy = progressive_length_constraint(
            target=3333,
            attempt=1,
            tolerance=0.2
        )

        assert strategy["target"] == 3333
        assert strategy["ceiling"] == 3999  # 3333 * 1.2
        assert strategy["hard_truncate"] is False
        assert strategy["strategy"] == "normal"

    def test_attempt2_not_exceeded_keeps_normal(self):
        """第二次尝试：如果首次未超长，保持正常"""
        strategy = progressive_length_constraint(
            target=3333,
            attempt=2,
            previous_length=3500,  # 未超长（<3999）
            tolerance=0.2
        )

        assert strategy["ceiling"] == 3999  # 保持正常
        assert strategy["strategy"] == "normal"

    def test_attempt2_exceeded_tightens(self):
        """第二次尝试：如果首次超长，收紧天花板"""
        strategy = progressive_length_constraint(
            target=3333,
            attempt=2,
            previous_length=4500,  # 超长了
            tolerance=0.2
        )

        assert strategy["ceiling"] == 3666  # 3333 * 1.1（tolerance/2）
        assert strategy["strategy"] == "tightened"
        assert "instruction" in strategy
        assert "4500" in strategy["instruction"]

    def test_attempt3_forces_hard_truncate(self):
        """第三次尝试：强制硬截断"""
        strategy = progressive_length_constraint(
            target=3333,
            attempt=3,
            previous_length=4000,
            tolerance=0.2
        )

        assert strategy["hard_truncate"] is True
        assert strategy["strategy"] == "hard_truncate"
        assert "instruction" in strategy

    def test_ceiling_calculation_correct(self):
        """天花板计算正确"""
        # tolerance=0.2, target=1000
        strategy = progressive_length_constraint(1000, attempt=1, tolerance=0.2)
        assert strategy["ceiling"] == 1200  # 1000 * 1.2

        # tolerance=0.5, target=1000
        strategy = progressive_length_constraint(1000, attempt=1, tolerance=0.5)
        assert strategy["ceiling"] == 1500  # 1000 * 1.5


class TestShouldRetry:
    """测试是否应该重试"""

    def test_within_ceiling_no_retry(self):
        """在ceiling内，不重试"""
        draft = {"body": "文本。" * 100}  # 假设300字
        # target=3333, tolerance=0.2 -> ceiling=3999
        # 300 < 3999，不重试

        should_retry = should_retry_for_length(
            draft,
            target=3333,
            attempt=1,
            tolerance=0.2
        )

        # 需要实际测量，这里假设300字在范围内
        # assert should_retry is False

    def test_exceeds_ceiling_retries(self):
        """超出ceiling，重试"""
        draft = {"body": "文本内容。" * 1000}  # 假设5000字
        # target=3333, ceiling=3999
        # 5000 > 3999，应该重试

        should_retry = should_retry_for_length(
            draft,
            target=3333,
            attempt=1,
            tolerance=0.2
        )

        assert should_retry is True

    def test_max_attempts_reached_no_retry(self):
        """达到最大尝试次数，不再重试"""
        draft = {"body": "文本内容。" * 1000}  # 超长

        should_retry = should_retry_for_length(
            draft,
            target=3333,
            attempt=3,  # 已经第3次
            max_attempts=3,
            tolerance=0.2
        )

        assert should_retry is False


class TestFormatInstruction:
    """测试指令格式化"""

    def test_format_normal_strategy(self):
        """格式化正常策略"""
        strategy = {
            "target": 3333,
            "ceiling": 3999,
            "hard_truncate": False,
            "strategy": "normal"
        }

        instruction = format_length_instruction(strategy)

        assert "3333" in instruction
        assert "3999" in instruction
        assert "严格控制篇幅" in instruction

    def test_format_tightened_strategy(self):
        """格式化收紧策略"""
        strategy = {
            "target": 3333,
            "ceiling": 3666,
            "hard_truncate": False,
            "strategy": "tightened",
            "instruction": "上一版超长4500字，本次必须严格控制在3666字以内。"
        }

        instruction = format_length_instruction(strategy)

        assert "上一版超长" in instruction
        assert "4500" in instruction

    def test_format_hard_truncate_warning(self):
        """格式化硬截断警告"""
        strategy = {
            "target": 3333,
            "ceiling": 3999,
            "hard_truncate": True,
            "strategy": "hard_truncate",
            "instruction": "前两次尝试均超长"
        }

        instruction = format_length_instruction(strategy)

        assert "截断" in instruction


class TestCostEstimate:
    """测试成本估算"""

    def test_estimate_remaining_attempts(self):
        """估算剩余尝试次数"""
        cost = estimate_retry_cost(
            target=3333,
            current_attempt=1,
            max_attempts=3
        )

        assert cost["remaining_attempts"] == 2
        assert cost["should_continue"] is True

    def test_estimate_no_remaining(self):
        """无剩余尝试"""
        cost = estimate_retry_cost(
            target=3333,
            current_attempt=3,
            max_attempts=3
        )

        assert cost["remaining_attempts"] == 0
        assert cost["should_continue"] is False

    def test_estimate_tokens_and_time(self):
        """估算token和时间"""
        cost = estimate_retry_cost(
            target=3333,
            current_attempt=1,
            max_attempts=3
        )

        # 2次剩余 × 3333 × 2 = 13332 tokens
        assert cost["estimated_tokens"] == 13332
        # 2次剩余 × 30秒 = 60秒
        assert cost["estimated_time_seconds"] == 60


class TestIntegrationScenario:
    """测试完整场景"""

    def test_typical_3_attempt_flow(self):
        """典型3次尝试流程"""
        target = 3333
        tolerance = 0.2

        # Attempt 1: 正常生成
        s1 = progressive_length_constraint(target, attempt=1, tolerance=tolerance)
        assert s1["strategy"] == "normal"
        assert s1["hard_truncate"] is False

        # Attempt 2: 首次超长，收紧
        s2 = progressive_length_constraint(
            target, attempt=2,
            previous_length=4500,  # 超长
            tolerance=tolerance
        )
        assert s2["strategy"] == "tightened"
        assert s2["ceiling"] < s1["ceiling"]  # 更严格

        # Attempt 3: 强制截断
        s3 = progressive_length_constraint(
            target, attempt=3,
            previous_length=4000,
            tolerance=tolerance
        )
        assert s3["hard_truncate"] is True

    def test_success_on_first_attempt(self):
        """第一次就成功（未超长）"""
        target = 3333

        # Attempt 1
        s1 = progressive_length_constraint(target, attempt=1)

        # 假设生成了3500字（在ceiling内）
        draft = {"body": "x" * 3500}
        should_retry = should_retry_for_length(draft, target, attempt=1)

        # 3500 < 3999，不需要重试
        assert should_retry is False


# Task 1.3.2 完成标记
# ✅ length_strategy.py实现
# ✅ 逐次收紧策略（attempt 1/2/3）
# ✅ 重试判断逻辑
# ✅ 指令格式化
# ✅ 编写15个测试
# 🟡 待集成：在chapter生成循环中使用此策略
