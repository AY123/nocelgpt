"""
ProductionState 单元测试
"""

import pytest
from runtime.contract.production_state import (
    ProductionState,
    validate_state_transition,
)


class TestProductionState:
    """ProductionState 测试"""

    def test_states_exist(self):
        """测试所有状态存在"""
        assert ProductionState.GENERATED
        assert ProductionState.NEEDS_REVISION
        assert ProductionState.BLOCKED
        assert ProductionState.HUMAN_APPROVED
        assert ProductionState.PUBLISHED
        assert ProductionState.INVALIDATED

    def test_can_export(self):
        """测试是否可以导出"""
        # 可以导出
        assert ProductionState.HUMAN_APPROVED.can_export()
        assert ProductionState.PUBLISHED.can_export()

        # 不能导出
        assert not ProductionState.GENERATED.can_export()
        assert not ProductionState.NEEDS_REVISION.can_export()
        assert not ProductionState.BLOCKED.can_export()
        assert not ProductionState.INVALIDATED.can_export()

    def test_can_proceed_next(self):
        """测试是否可以继续下一章"""
        # 可以继续
        assert ProductionState.HUMAN_APPROVED.can_proceed_next()
        assert ProductionState.PUBLISHED.can_proceed_next()

        # 不能继续
        assert not ProductionState.GENERATED.can_proceed_next()
        assert not ProductionState.NEEDS_REVISION.can_proceed_next()
        assert not ProductionState.BLOCKED.can_proceed_next()
        assert not ProductionState.INVALIDATED.can_proceed_next()

    def test_can_revise(self):
        """测试是否可以修改"""
        # 可以修改
        assert ProductionState.GENERATED.can_revise()
        assert ProductionState.NEEDS_REVISION.can_revise()

        # 不建议修改
        assert not ProductionState.HUMAN_APPROVED.can_revise()
        assert not ProductionState.PUBLISHED.can_revise()
        assert not ProductionState.BLOCKED.can_revise()
        assert not ProductionState.INVALIDATED.can_revise()

    def test_can_publish(self):
        """测试是否可以发布"""
        # 只有 HUMAN_APPROVED 可以发布
        assert ProductionState.HUMAN_APPROVED.can_publish()

        # 其他都不能发布
        assert not ProductionState.GENERATED.can_publish()
        assert not ProductionState.NEEDS_REVISION.can_publish()
        assert not ProductionState.BLOCKED.can_publish()
        assert not ProductionState.PUBLISHED.can_publish()
        assert not ProductionState.INVALIDATED.can_publish()

    def test_is_terminal(self):
        """测试是否是终态"""
        # 终态
        assert ProductionState.PUBLISHED.is_terminal()
        assert ProductionState.INVALIDATED.is_terminal()

        # 非终态
        assert not ProductionState.GENERATED.is_terminal()
        assert not ProductionState.NEEDS_REVISION.is_terminal()
        assert not ProductionState.BLOCKED.is_terminal()
        assert not ProductionState.HUMAN_APPROVED.is_terminal()

    def test_is_blocked(self):
        """测试是否被阻塞"""
        assert ProductionState.BLOCKED.is_blocked()

        assert not ProductionState.GENERATED.is_blocked()
        assert not ProductionState.NEEDS_REVISION.is_blocked()
        assert not ProductionState.HUMAN_APPROVED.is_blocked()
        assert not ProductionState.PUBLISHED.is_blocked()
        assert not ProductionState.INVALIDATED.is_blocked()

    def test_needs_attention(self):
        """测试是否需要关注"""
        # 需要关注
        assert ProductionState.NEEDS_REVISION.needs_attention()
        assert ProductionState.BLOCKED.needs_attention()
        assert ProductionState.INVALIDATED.needs_attention()

        # 不需要关注
        assert not ProductionState.GENERATED.needs_attention()
        assert not ProductionState.HUMAN_APPROVED.needs_attention()
        assert not ProductionState.PUBLISHED.needs_attention()

    def test_valid_transitions(self):
        """测试合法的状态转换"""
        # GENERATED -> HUMAN_APPROVED
        assert ProductionState.GENERATED.can_transition_to(ProductionState.HUMAN_APPROVED)

        # GENERATED -> BLOCKED
        assert ProductionState.GENERATED.can_transition_to(ProductionState.BLOCKED)

        # HUMAN_APPROVED -> PUBLISHED
        assert ProductionState.HUMAN_APPROVED.can_transition_to(ProductionState.PUBLISHED)

        # INVALIDATED -> GENERATED
        assert ProductionState.INVALIDATED.can_transition_to(ProductionState.GENERATED)

    def test_invalid_transitions(self):
        """测试非法的状态转换"""
        # GENERATED 不能直接到 PUBLISHED
        assert not ProductionState.GENERATED.can_transition_to(ProductionState.PUBLISHED)

        # PUBLISHED 不能回到 GENERATED
        assert not ProductionState.PUBLISHED.can_transition_to(ProductionState.GENERATED)

        # PUBLISHED 不能回到 HUMAN_APPROVED
        assert not ProductionState.PUBLISHED.can_transition_to(ProductionState.HUMAN_APPROVED)

        # BLOCKED 不能直接到 PUBLISHED
        assert not ProductionState.BLOCKED.can_transition_to(ProductionState.PUBLISHED)

    def test_next_states(self):
        """测试获取下一个可能的状态"""
        # GENERATED 的下一个状态
        next_states = ProductionState.GENERATED.next_states()
        assert ProductionState.HUMAN_APPROVED in next_states
        assert ProductionState.NEEDS_REVISION in next_states
        assert ProductionState.BLOCKED in next_states
        assert ProductionState.INVALIDATED in next_states

        # HUMAN_APPROVED 的下一个状态
        next_states = ProductionState.HUMAN_APPROVED.next_states()
        assert ProductionState.PUBLISHED in next_states
        assert ProductionState.NEEDS_REVISION in next_states
        assert ProductionState.INVALIDATED in next_states

        # PUBLISHED 的下一个状态（只能作废）
        next_states = ProductionState.PUBLISHED.next_states()
        assert next_states == [ProductionState.INVALIDATED]

    def test_display_name(self):
        """测试显示名称"""
        assert ProductionState.GENERATED.display_name() == "已生成"
        assert ProductionState.NEEDS_REVISION.display_name() == "需要修改"
        assert ProductionState.BLOCKED.display_name() == "被阻塞"
        assert ProductionState.HUMAN_APPROVED.display_name() == "人工审核通过"
        assert ProductionState.PUBLISHED.display_name() == "已发布"
        assert ProductionState.INVALIDATED.display_name() == "已作废"

    def test_display_emoji(self):
        """测试表情符号"""
        assert ProductionState.GENERATED.display_emoji() == "📝"
        assert ProductionState.NEEDS_REVISION.display_emoji() == "✏️"
        assert ProductionState.BLOCKED.display_emoji() == "🚫"
        assert ProductionState.HUMAN_APPROVED.display_emoji() == "✅"
        assert ProductionState.PUBLISHED.display_emoji() == "🎉"
        assert ProductionState.INVALIDATED.display_emoji() == "❌"

    def test_str_representation(self):
        """测试字符串表示"""
        s = str(ProductionState.HUMAN_APPROVED)
        assert "✅" in s
        assert "人工审核通过" in s


class TestValidateStateTransition:
    """validate_state_transition 测试"""

    def test_valid_transition_returns_true(self):
        """测试合法转换返回 True"""
        result = validate_state_transition(
            ProductionState.GENERATED,
            ProductionState.HUMAN_APPROVED,
            raise_on_invalid=False
        )
        assert result is True

    def test_invalid_transition_returns_false(self):
        """测试非法转换返回 False"""
        result = validate_state_transition(
            ProductionState.GENERATED,
            ProductionState.PUBLISHED,
            raise_on_invalid=False
        )
        assert result is False

    def test_invalid_transition_raises_error(self):
        """测试非法转换抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            validate_state_transition(
                ProductionState.GENERATED,
                ProductionState.PUBLISHED,
                raise_on_invalid=True
            )

        assert "非法状态转换" in str(exc_info.value)
        assert "已生成" in str(exc_info.value)
        assert "已发布" in str(exc_info.value)


class TestStateTransitionScenarios:
    """状态转换场景测试"""

    def test_normal_workflow(self):
        """测试正常工作流"""
        # 生成 -> 审核通过 -> 发布
        state = ProductionState.GENERATED
        assert state.can_transition_to(ProductionState.HUMAN_APPROVED)

        state = ProductionState.HUMAN_APPROVED
        assert state.can_transition_to(ProductionState.PUBLISHED)

    def test_revision_workflow(self):
        """测试修改工作流"""
        # 生成 -> 需要修改 -> 重新生成 -> 审核通过
        state = ProductionState.GENERATED
        assert state.can_transition_to(ProductionState.NEEDS_REVISION)

        state = ProductionState.NEEDS_REVISION
        assert state.can_transition_to(ProductionState.GENERATED)

        state = ProductionState.GENERATED
        assert state.can_transition_to(ProductionState.HUMAN_APPROVED)

    def test_blocked_workflow(self):
        """测试阻塞工作流"""
        # 生成 -> 阻塞 -> 重新生成
        state = ProductionState.GENERATED
        assert state.can_transition_to(ProductionState.BLOCKED)

        state = ProductionState.BLOCKED
        assert state.can_transition_to(ProductionState.GENERATED)

    def test_invalidation_workflow(self):
        """测试作废工作流"""
        # 发布 -> 作废 -> 重新生成
        state = ProductionState.PUBLISHED
        assert state.can_transition_to(ProductionState.INVALIDATED)

        state = ProductionState.INVALIDATED
        assert state.can_transition_to(ProductionState.GENERATED)
