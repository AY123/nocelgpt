"""length_strategy.py — Phase 1 Task 1.3.2: 多轮收紧策略

策略：逐次收紧长度约束，避免第一次就硬截断。
- 第一次：正常目标（让模型自然生成）
- 第二次：如果超长，明确降低天花板
- 第三次：直接用硬截断
"""
from __future__ import annotations
from typing import Optional


def progressive_length_constraint(
    target: int,
    attempt: int,
    previous_length: Optional[int] = None,
    *,
    tolerance: float = 0.2
) -> dict:
    """逐次收紧长度约束策略。

    Args:
        target: 目标字数
        attempt: 当前尝试次数（1, 2, 3...）
        previous_length: 上次生成的长度（用于判断是否超长）
        tolerance: 基础容忍度

    Returns:
        策略字典，包含：
        - target: 目标字数
        - ceiling: 天花板（最大允许）
        - hard_truncate: 是否使用硬截断
        - instruction: 给模型的额外指令（可选）

    Strategy:
        Attempt 1: 正常目标，ceiling = target * (1 + tolerance)
        Attempt 2: 如果超长，降低ceiling到 target * (1 + tolerance/2)
        Attempt 3+: 强制硬截断

    Examples:
        >>> progressive_length_constraint(3333, attempt=1)
        {'target': 3333, 'ceiling': 3999, 'hard_truncate': False}

        >>> progressive_length_constraint(3333, attempt=2, previous_length=4500)
        {'target': 3333, 'ceiling': 3666, 'hard_truncate': False,
         'instruction': '上一版超长4500字，本次必须控制在3666字以内'}

        >>> progressive_length_constraint(3333, attempt=3, previous_length=4000)
        {'target': 3333, 'ceiling': 3999, 'hard_truncate': True}
    """
    base_ceiling = int(target * (1 + tolerance))

    # Attempt 1: 正常目标
    if attempt == 1:
        return {
            "target": target,
            "ceiling": base_ceiling,
            "hard_truncate": False,
            "strategy": "normal"
        }

    # Attempt 2: 如果首次超长，收紧天花板
    elif attempt == 2:
        if previous_length and previous_length > base_ceiling:
            # 超长了，收紧到 target * (1 + tolerance/2)
            tightened_ceiling = int(target * (1 + tolerance / 2))
            return {
                "target": target,
                "ceiling": tightened_ceiling,
                "hard_truncate": False,
                "strategy": "tightened",
                "instruction": (
                    f"上一版超长{previous_length}字，"
                    f"本次必须严格控制在{tightened_ceiling}字以内。"
                    f"目标{target}字，最多{tightened_ceiling}字。"
                )
            }
        else:
            # 未超长，继续正常策略
            return {
                "target": target,
                "ceiling": base_ceiling,
                "hard_truncate": False,
                "strategy": "normal"
            }

    # Attempt 3+: 直接硬截断
    else:
        return {
            "target": target,
            "ceiling": base_ceiling,
            "hard_truncate": True,
            "strategy": "hard_truncate",
            "instruction": (
                f"前两次尝试均超长，本次生成后将直接截断到{target}字左右。"
            )
        }


def should_retry_for_length(
    draft: dict,
    target: int,
    attempt: int,
    *,
    max_attempts: int = 3,
    tolerance: float = 0.2
) -> bool:
    """判断是否应该因为超长而重试。

    Args:
        draft: 当前草稿
        target: 目标字数
        attempt: 当前尝试次数
        max_attempts: 最大尝试次数
        tolerance: 容忍度

    Returns:
        True if should retry, False otherwise

    Strategy:
        - 如果已达到max_attempts，不再重试（改用硬截断）
        - 如果在ceiling内，不重试
        - 如果超出ceiling，重试
    """
    # 已达到最大尝试次数，不再重试
    if attempt >= max_attempts:
        return False

    # 计算当前策略的ceiling
    strategy = progressive_length_constraint(target, attempt, tolerance=tolerance)
    ceiling = strategy["ceiling"]

    # 检查draft长度
    from .length_enforcer import _count_words_cjk
    body = draft.get("body", "")
    word_count = _count_words_cjk(body)

    # 超出ceiling，需要重试
    return word_count > ceiling


def format_length_instruction(strategy: dict) -> str:
    """格式化长度约束指令，用于prompt。

    Args:
        strategy: progressive_length_constraint返回的策略字典

    Returns:
        格式化的指令文本
    """
    target = strategy["target"]
    ceiling = strategy["ceiling"]

    base_instruction = f"严格控制篇幅：目标{target}字，不得超过{ceiling}字。"

    # 如果有额外指令，追加
    if "instruction" in strategy:
        base_instruction += f" {strategy['instruction']}"

    # 如果是硬截断模式，警告
    if strategy.get("hard_truncate"):
        base_instruction += " 注意：如果超长将被强制截断。"

    return base_instruction


def estimate_retry_cost(
    target: int,
    current_attempt: int,
    max_attempts: int = 3
) -> dict:
    """估算重试的成本（token和时间）。

    Args:
        target: 目标字数
        current_attempt: 当前尝试次数
        max_attempts: 最大尝试次数

    Returns:
        成本估算字典
    """
    remaining_attempts = max_attempts - current_attempt

    # 假设每次生成约消耗 target * 2 tokens (input + output)
    tokens_per_attempt = target * 2
    total_tokens = remaining_attempts * tokens_per_attempt

    # 假设每次生成约耗时30秒（经验值）
    time_per_attempt = 30  # seconds
    total_time = remaining_attempts * time_per_attempt

    return {
        "remaining_attempts": remaining_attempts,
        "estimated_tokens": total_tokens,
        "estimated_time_seconds": total_time,
        "should_continue": remaining_attempts > 0
    }
