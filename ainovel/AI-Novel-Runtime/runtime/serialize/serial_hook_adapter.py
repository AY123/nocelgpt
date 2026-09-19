"""
Serial Hook Adapter - Serial 钩子适配器

将 ChapterProductionHook 适配到现有的 Serial 流程中。
使用装饰器模式，最小化对现有代码的修改。
"""

from pathlib import Path
from typing import Optional, Any, Dict, Callable
import logging
from functools import wraps

from .production_hook import (
    ChapterProductionHook,
    ChapterProductionContext,
    create_production_hook,
)
from ..contract import ProductionState


logger = logging.getLogger(__name__)


class SerialHookAdapter:
    """
    Serial 钩子适配器

    拦截 Serial 流程中的关键点，注入契约验证逻辑。
    """

    def __init__(
        self,
        project_path: Path,
        enable_contract_integration: bool = False
    ):
        """
        初始化适配器

        Args:
            project_path: 项目路径
            enable_contract_integration: 是否启用契约集成
        """
        self.project_path = project_path
        self.hook = create_production_hook(
            project_path=project_path,
            enable_contract_integration=enable_contract_integration
        )
        self.enabled = self.hook.enabled

        # 记录每章的状态
        self.chapter_states: Dict[int, ProductionState] = {}

    def can_generate_chapter(
        self,
        chapter_number: int,
        force: bool = False
    ) -> tuple[bool, list[str]]:
        """
        检查是否可以生成指定章节

        Args:
            chapter_number: 章节号
            force: 是否强制生成（忽略阻塞）

        Returns:
            tuple[bool, list[str]]: (是否可以生成, 错误列表)
        """
        if not self.enabled:
            return True, []

        if force:
            logger.warning(f"强制生成第{chapter_number}章，跳过验证")
            return True, []

        # 获取上一章状态
        previous_state = None
        if chapter_number > 1:
            previous_state = self.chapter_states.get(chapter_number - 1)

            # 如果上一章状态未记录，尝试从文件加载
            if previous_state is None:
                previous_state = self._load_chapter_state(chapter_number - 1)

        # 验证入口条件
        ctx = ChapterProductionContext(
            chapter_number=chapter_number,
            project_path=self.project_path,
            previous_state=previous_state
        )

        return self.hook.before_generate(ctx)

    def validate_and_save_chapter(
        self,
        chapter_number: int,
        draft_text: str,
        save_callback: Optional[Callable] = None
    ) -> tuple[bool, ProductionState]:
        """
        验证章节并保存

        Args:
            chapter_number: 章节号
            draft_text: 草稿文本
            save_callback: 保存回调函数（可选）

        Returns:
            tuple[bool, ProductionState]: (验证是否通过, 生产状态)
        """
        if not self.enabled:
            # 不启用时，使用默认状态
            state = ProductionState.GENERATED
            if save_callback:
                save_callback(state)
            return True, state

        # 创建上下文
        ctx = ChapterProductionContext(
            chapter_number=chapter_number,
            project_path=self.project_path,
            draft_text=draft_text
        )

        # 验证契约
        validation_passed, result = self.hook.after_generate(ctx)

        # 设置状态
        production_state = self.hook.before_save(ctx, validation_passed)

        # 更新故事状态
        if validation_passed:
            self.hook.update_story_state(ctx)

        # 记录状态
        self.chapter_states[chapter_number] = production_state

        # 调用保存回调
        if save_callback:
            save_callback(production_state)

        return validation_passed, production_state

    def _load_chapter_state(self, chapter_number: int) -> Optional[ProductionState]:
        """
        从文件加载章节状态

        Args:
            chapter_number: 章节号

        Returns:
            ProductionState 或 None
        """
        import json

        # 可能的章节文件位置
        candidates = [
            self.project_path / "registry" / "derived" / "chapter-final" / f"final-TASK-{chapter_number:05d}.json",
            self.project_path / "out" / f"chapter-{chapter_number:05d}.json",
        ]

        for candidate in candidates:
            if candidate.exists():
                try:
                    with open(candidate, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        state_str = data.get('production_state', 'generated')
                        return ProductionState(state_str)
                except Exception as e:
                    logger.error(f"加载第{chapter_number}章状态失败: {e}")

        return None

    def get_statistics(self) -> dict:
        """获取统计信息"""
        if not self.enabled:
            return {}
        return self.hook.get_statistics()

    def print_summary(self):
        """打印统计摘要"""
        if not self.enabled:
            logger.info("契约验证未启用")
            return
        self.hook.print_summary()


def wrap_serial_with_hooks(
    enable_contract_integration: bool = False
):
    """
    装饰器：为 Serial 函数添加钩子支持

    用法:
        @wrap_serial_with_hooks(enable_contract_integration=True)
        def my_serial_function(project_path, ...):
            # 原有的 Serial 逻辑
            pass

    Args:
        enable_contract_integration: 是否启用契约集成

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取 project_path
            project_path = kwargs.get('project_path')
            if not project_path and len(args) > 0:
                project_path = args[0]

            if not project_path:
                logger.warning("无法获取 project_path，跳过契约集成")
                return func(*args, **kwargs)

            # 创建适配器
            adapter = SerialHookAdapter(
                project_path=Path(project_path),
                enable_contract_integration=enable_contract_integration
            )

            # 将适配器注入到 kwargs 中
            kwargs['_hook_adapter'] = adapter

            # 执行原函数
            result = func(*args, **kwargs)

            # 输出统计
            adapter.print_summary()

            return result

        return wrapper
    return decorator


# 便捷函数：创建适配器
def create_adapter(
    project_path: Path,
    enable_contract_integration: bool = False
) -> SerialHookAdapter:
    """
    创建 Serial 钩子适配器

    Args:
        project_path: 项目路径
        enable_contract_integration: 是否启用契约集成

    Returns:
        SerialHookAdapter: 适配器实例
    """
    return SerialHookAdapter(
        project_path=project_path,
        enable_contract_integration=enable_contract_integration
    )
