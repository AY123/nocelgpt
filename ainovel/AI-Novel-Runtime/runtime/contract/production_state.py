"""
生产状态（Production State）

统一的章节生产状态枚举，替代分散的状态判断逻辑。
"""

from enum import Enum


class ProductionState(Enum):
    """
    统一的生产状态

    这是章节生产的唯一状态决策源。
    旧的字段（publish_readiness, commercial_verdict, m7_final.decision）
    保留为 advisory（建议性）信息，但不再决定状态。
    """

    # ============================================================
    # 生产流程状态
    # ============================================================

    GENERATED = "generated"
    """已生成，未验证

    章节已由 LLM 生成，但尚未经过人工审核或质量验证。
    可以进行修改、验证、审核。
    """

    NEEDS_REVISION = "needs_revision"
    """需要修改

    章节经过验证或审核，发现问题需要修改。
    可以重新生成或手动修改。
    """

    BLOCKED = "blocked"
    """被阻塞

    章节因依赖未满足而无法继续：
    - 契约验证失败
    - 连续性检查失败
    - 上一章未完成
    必须解决阻塞原因才能继续。
    """

    HUMAN_APPROVED = "human_approved"
    """人工审核通过

    章节经过人工审核，确认质量合格。
    可以导出和发布。
    """

    PUBLISHED = "published"
    """已发布

    章节已导出并发布到最终输出。
    通常不再修改（除非重大问题）。
    """

    INVALIDATED = "invalidated"
    """已作废

    章节因重大问题被作废：
    - Story Bible 更新导致不一致
    - 前置章节改变导致无效
    - 人工决定重新生成
    需要重新生成。
    """

    # ============================================================
    # 状态判断方法
    # ============================================================

    def can_export(self) -> bool:
        """
        是否可以导出

        只有 HUMAN_APPROVED 和 PUBLISHED 可以导出。
        """
        return self in [
            ProductionState.HUMAN_APPROVED,
            ProductionState.PUBLISHED,
        ]

    def can_proceed_next(self) -> bool:
        """
        是否可以继续下一章

        只有 HUMAN_APPROVED 和 PUBLISHED 可以继续。
        BLOCKED 和 NEEDS_REVISION 必须先解决。
        """
        return self in [
            ProductionState.HUMAN_APPROVED,
            ProductionState.PUBLISHED,
        ]

    def can_revise(self) -> bool:
        """
        是否可以修改

        GENERATED 和 NEEDS_REVISION 可以修改。
        HUMAN_APPROVED 和 PUBLISHED 原则上不修改（需要人工确认）。
        """
        return self in [
            ProductionState.GENERATED,
            ProductionState.NEEDS_REVISION,
        ]

    def can_publish(self) -> bool:
        """
        是否可以发布

        只有 HUMAN_APPROVED 可以发布。
        """
        return self == ProductionState.HUMAN_APPROVED

    def is_terminal(self) -> bool:
        """
        是否是终态

        PUBLISHED 和 INVALIDATED 是终态，通常不再改变。
        """
        return self in [
            ProductionState.PUBLISHED,
            ProductionState.INVALIDATED,
        ]

    def is_blocked(self) -> bool:
        """
        是否被阻塞

        BLOCKED 状态表示有阻塞问题需要解决。
        """
        return self == ProductionState.BLOCKED

    def needs_attention(self) -> bool:
        """
        是否需要关注

        NEEDS_REVISION, BLOCKED, INVALIDATED 需要人工关注。
        """
        return self in [
            ProductionState.NEEDS_REVISION,
            ProductionState.BLOCKED,
            ProductionState.INVALIDATED,
        ]

    # ============================================================
    # 状态转换规则
    # ============================================================

    def can_transition_to(self, new_state: 'ProductionState') -> bool:
        """
        是否可以转换到新状态

        定义合法的状态转换路径。
        """
        # 定义合法转换
        transitions = {
            ProductionState.GENERATED: [
                ProductionState.NEEDS_REVISION,
                ProductionState.BLOCKED,
                ProductionState.HUMAN_APPROVED,
                ProductionState.INVALIDATED,
            ],
            ProductionState.NEEDS_REVISION: [
                ProductionState.GENERATED,  # 重新生成
                ProductionState.HUMAN_APPROVED,  # 修改后通过
                ProductionState.INVALIDATED,
            ],
            ProductionState.BLOCKED: [
                ProductionState.GENERATED,  # 解决阻塞后重新生成
                ProductionState.NEEDS_REVISION,
                ProductionState.INVALIDATED,
            ],
            ProductionState.HUMAN_APPROVED: [
                ProductionState.PUBLISHED,
                ProductionState.NEEDS_REVISION,  # 发现新问题
                ProductionState.INVALIDATED,
            ],
            ProductionState.PUBLISHED: [
                ProductionState.INVALIDATED,  # 重大问题需要作废
            ],
            ProductionState.INVALIDATED: [
                ProductionState.GENERATED,  # 重新生成
            ],
        }

        allowed = transitions.get(self, [])
        return new_state in allowed

    def next_states(self) -> list['ProductionState']:
        """
        返回所有可能的下一个状态
        """
        transitions = {
            ProductionState.GENERATED: [
                ProductionState.NEEDS_REVISION,
                ProductionState.BLOCKED,
                ProductionState.HUMAN_APPROVED,
                ProductionState.INVALIDATED,
            ],
            ProductionState.NEEDS_REVISION: [
                ProductionState.GENERATED,
                ProductionState.HUMAN_APPROVED,
                ProductionState.INVALIDATED,
            ],
            ProductionState.BLOCKED: [
                ProductionState.GENERATED,
                ProductionState.NEEDS_REVISION,
                ProductionState.INVALIDATED,
            ],
            ProductionState.HUMAN_APPROVED: [
                ProductionState.PUBLISHED,
                ProductionState.NEEDS_REVISION,
                ProductionState.INVALIDATED,
            ],
            ProductionState.PUBLISHED: [
                ProductionState.INVALIDATED,
            ],
            ProductionState.INVALIDATED: [
                ProductionState.GENERATED,
            ],
        }

        return transitions.get(self, [])

    # ============================================================
    # 显示方法
    # ============================================================

    def display_name(self) -> str:
        """返回友好的显示名称"""
        names = {
            ProductionState.GENERATED: "已生成",
            ProductionState.NEEDS_REVISION: "需要修改",
            ProductionState.BLOCKED: "被阻塞",
            ProductionState.HUMAN_APPROVED: "人工审核通过",
            ProductionState.PUBLISHED: "已发布",
            ProductionState.INVALIDATED: "已作废",
        }
        return names.get(self, self.value)

    def display_emoji(self) -> str:
        """返回表情符号"""
        emojis = {
            ProductionState.GENERATED: "📝",
            ProductionState.NEEDS_REVISION: "✏️",
            ProductionState.BLOCKED: "🚫",
            ProductionState.HUMAN_APPROVED: "✅",
            ProductionState.PUBLISHED: "🎉",
            ProductionState.INVALIDATED: "❌",
        }
        return emojis.get(self, "❓")

    def __str__(self) -> str:
        return f"{self.display_emoji()} {self.display_name()}"


def validate_state_transition(current: ProductionState,
                             new: ProductionState,
                             raise_on_invalid: bool = True) -> bool:
    """
    验证状态转换是否合法

    Args:
        current: 当前状态
        new: 新状态
        raise_on_invalid: 如果非法是否抛出异常

    Returns:
        bool: 是否合法

    Raises:
        ValueError: 如果非法且 raise_on_invalid=True
    """
    is_valid = current.can_transition_to(new)

    if not is_valid and raise_on_invalid:
        raise ValueError(
            f"非法状态转换: {current.display_name()} → {new.display_name()}\n"
            f"允许的转换: {[s.display_name() for s in current.next_states()]}"
        )

    return is_valid
