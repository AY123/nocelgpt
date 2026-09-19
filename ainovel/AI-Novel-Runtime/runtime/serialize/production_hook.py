"""
Chapter Production Hook - 章节生产钩子

在章节生产的关键节点插入契约验证和状态管理。
这是一个轻量级的钩子系统，不破坏现有的 Serial 逻辑。
"""

from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import logging

from ..contract import ProductionState
from .contract_integration import ContractIntegration


logger = logging.getLogger(__name__)


@dataclass
class ChapterProductionContext:
    """章节生产上下文"""
    chapter_number: int
    project_path: Path
    previous_state: Optional[ProductionState] = None
    draft_text: Optional[str] = None
    metadata: Dict[str, Any] = None


class ChapterProductionHook:
    """
    章节生产钩子

    在章节生产的关键节点执行验证和状态管理：
    1. before_generate - 生成前验证入口条件
    2. after_generate - 生成后验证契约
    3. before_save - 保存前设置状态
    """

    def __init__(self, integration: Optional[ContractIntegration] = None):
        """
        初始化钩子

        Args:
            integration: ContractIntegration 实例（可选）
        """
        self.integration = integration
        self.enabled = integration is not None and integration.is_enabled()

        # 统计信息
        self.stats = {
            'total_chapters': 0,
            'validated_chapters': 0,
            'passed_chapters': 0,
            'blocked_chapters': 0,
            'errors': [],
        }

    def before_generate(self, ctx: ChapterProductionContext) -> tuple[bool, list[str]]:
        """
        生成前钩子：验证入口条件

        Args:
            ctx: 章节生产上下文

        Returns:
            tuple[bool, list[str]]: (是否可以继续, 错误列表)
        """
        if not self.enabled:
            return True, []

        logger.info(f"=" * 60)
        logger.info(f"第{ctx.chapter_number}章 - 入口验证")
        logger.info(f"=" * 60)

        # 验证入口条件
        can_proceed, errors = self.integration.validate_chapter_entry(
            ctx.chapter_number,
            ctx.previous_state
        )

        if not can_proceed:
            logger.error(f"✗ 第{ctx.chapter_number}章入口验证失败")
            for error in errors:
                logger.error(f"  - {error}")
            self.stats['blocked_chapters'] += 1
            self.stats['errors'].extend(errors)
        else:
            logger.info(f"✓ 第{ctx.chapter_number}章入口验证通过")

        return can_proceed, errors

    def after_generate(self, ctx: ChapterProductionContext) -> tuple[bool, dict]:
        """
        生成后钩子：验证契约

        Args:
            ctx: 章节生产上下文（必须包含 draft_text）

        Returns:
            tuple[bool, dict]: (是否通过验证, 验证结果详情)
        """
        if not self.enabled:
            return True, {'message': '契约验证未启用'}

        if not ctx.draft_text:
            logger.warning(f"第{ctx.chapter_number}章缺少草稿文本，跳过契约验证")
            return True, {'message': '缺少草稿文本'}

        logger.info(f"=" * 60)
        logger.info(f"第{ctx.chapter_number}章 - 契约验证")
        logger.info(f"=" * 60)

        self.stats['total_chapters'] += 1
        self.stats['validated_chapters'] += 1

        # 验证契约
        passed, result = self.integration.validate_chapter_draft(
            ctx.chapter_number,
            ctx.draft_text
        )

        if passed:
            logger.info(f"✓ 第{ctx.chapter_number}章契约验证通过")
            self.stats['passed_chapters'] += 1
        else:
            logger.warning(f"✗ 第{ctx.chapter_number}章契约验证失败")
            logger.warning(f"  错误: {result.get('errors', [])}")
            logger.warning(f"  警告: {result.get('warnings', [])}")
            self.stats['blocked_chapters'] += 1
            self.stats['errors'].extend(result.get('errors', []))

        # 输出警告（即使通过）
        if result.get('warnings'):
            logger.warning(f"  警告: {result.get('warnings', [])}")

        return passed, result

    def before_save(self, ctx: ChapterProductionContext, validation_passed: bool) -> ProductionState:
        """
        保存前钩子：设置生产状态

        Args:
            ctx: 章节生产上下文
            validation_passed: 契约验证是否通过

        Returns:
            ProductionState: 应该设置的状态
        """
        if not self.enabled:
            return ProductionState.GENERATED

        # 根据验证结果决定状态
        if validation_passed:
            state = ProductionState.GENERATED
            logger.info(f"第{ctx.chapter_number}章状态: {state}")
        else:
            state = ProductionState.BLOCKED
            logger.warning(f"第{ctx.chapter_number}章状态: {state} (验证失败)")

        return state

    def update_story_state(self, ctx: ChapterProductionContext):
        """
        更新故事状态

        Args:
            ctx: 章节生产上下文（必须包含 draft_text）
        """
        if not self.enabled or not ctx.draft_text:
            return

        logger.info(f"更新故事状态到第{ctx.chapter_number}章")

        try:
            new_state = self.integration.update_state_from_draft(
                ctx.chapter_number,
                ctx.draft_text
            )
            logger.info(f"✓ 状态更新完成")
            logger.debug(new_state.summary())
        except Exception as e:
            logger.error(f"更新故事状态失败: {e}")

    def get_statistics(self) -> dict:
        """
        获取统计信息

        Returns:
            dict: 统计信息
        """
        stats = self.stats.copy()

        if stats['validated_chapters'] > 0:
            stats['pass_rate'] = stats['passed_chapters'] / stats['validated_chapters'] * 100
        else:
            stats['pass_rate'] = 0

        return stats

    def print_summary(self):
        """打印统计摘要"""
        if not self.enabled:
            logger.info("契约验证未启用")
            return

        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("契约验证统计摘要")
        logger.info("=" * 60)
        logger.info(f"总章节数: {stats['total_chapters']}")
        logger.info(f"已验证: {stats['validated_chapters']}")
        logger.info(f"通过: {stats['passed_chapters']}")
        logger.info(f"阻塞: {stats['blocked_chapters']}")
        logger.info(f"通过率: {stats['pass_rate']:.1f}%")

        if stats['errors']:
            logger.info(f"\n常见错误:")
            error_counts = {}
            for error in stats['errors']:
                # 提取错误类型
                error_type = error.split(':')[0] if ':' in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {error_type}: {count}次")

        logger.info("=" * 60)


def create_production_hook(
    project_path: Path,
    enable_contract_integration: bool = False
) -> ChapterProductionHook:
    """
    创建章节生产钩子

    Args:
        project_path: 项目路径
        enable_contract_integration: 是否启用契约集成

    Returns:
        ChapterProductionHook: 钩子实例
    """
    if not enable_contract_integration:
        logger.info("契约验证未启用，创建空钩子")
        return ChapterProductionHook(integration=None)

    from .contract_integration import create_integration

    integration = create_integration(
        project_path=project_path,
        enable_contract_integration=True
    )

    if not integration:
        logger.warning("契约集成创建失败，创建空钩子")
        return ChapterProductionHook(integration=None)

    hook = ChapterProductionHook(integration=integration)
    logger.info("契约验证已启用")
    logger.info(integration.summary())

    return hook
