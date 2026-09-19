"""
Contract Integration Helper

集成 ChapterContract 和 StoryState 到 Serial 生产流程。
这是一个辅助模块，不破坏现有的 Serial 逻辑。
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

from ..contract import (
    ChapterContract,
    StoryState,
    ProductionState,
    load_story_bible_contracts,
)


logger = logging.getLogger(__name__)


class ContractIntegration:
    """
    契约集成助手

    在 Serial 生产流程中集成 ChapterContract 和 StoryState。
    """

    def __init__(self, project_path: Path, story_bible_path: Optional[Path] = None):
        """
        初始化契约集成

        Args:
            project_path: 项目路径
            story_bible_path: Story Bible 路径（可选，默认为 project_path/registry/story-bible/BIBLE-00001.yaml）
        """
        self.project_path = Path(project_path)
        self.story_bible_path = story_bible_path or (
            self.project_path / "registry" / "story-bible" / "BIBLE-00001.yaml"
        )

        self.contracts: Dict[int, ChapterContract] = {}
        self.current_state: Optional[StoryState] = None
        self.enabled = False

        # 尝试加载契约
        self._load_contracts()

    def _load_contracts(self):
        """加载所有契约"""
        if not self.story_bible_path.exists():
            logger.warning(f"Story Bible 不存在: {self.story_bible_path}")
            return

        try:
            contracts_list = load_story_bible_contracts(str(self.story_bible_path))
            self.contracts = {c.chapter_number: c for c in contracts_list}
            self.enabled = True
            logger.info(f"成功加载 {len(self.contracts)} 个契约")
        except Exception as e:
            logger.error(f"加载契约失败: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """是否启用契约集成"""
        return self.enabled

    def get_contract(self, chapter_number: int) -> Optional[ChapterContract]:
        """
        获取指定章节的契约

        Args:
            chapter_number: 章节号

        Returns:
            ChapterContract 或 None
        """
        return self.contracts.get(chapter_number)

    def initialize_state(self) -> StoryState:
        """
        初始化故事状态（第0章）

        Returns:
            StoryState: 初始状态
        """
        import yaml

        # 从 Story Bible 读取初始信息
        if self.story_bible_path.exists():
            with open(self.story_bible_path, 'r', encoding='utf-8') as f:
                bible = yaml.safe_load(f)

            self.current_state = StoryState.create_initial_state(bible)
        else:
            # 降级：使用默认值
            from ..contract.story_state import Character
            protagonist = Character(
                id="CHR-90001",
                name="陈默",
                role="protagonist",
                status="active",
                first_appearance_chapter=0
            )

            self.current_state = StoryState(
                current_date="2013-01-15",
                current_location="江城",
                chapter_number=0,
                protagonist=protagonist,
                characters={"CHR-90001": protagonist},
            )

        logger.info(f"初始化故事状态: {self.current_state.summary()}")
        return self.current_state

    def validate_chapter_entry(
        self,
        chapter_number: int,
        previous_state: Optional[ProductionState] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证章节入口条件

        Args:
            chapter_number: 章节号
            previous_state: 上一章的生产状态

        Returns:
            Tuple[bool, List[str]]: (是否可以继续, 错误消息列表)
        """
        errors = []

        # 1. 检查契约是否存在
        contract = self.get_contract(chapter_number)
        if not contract:
            errors.append(f"第{chapter_number}章缺少契约")
            return False, errors

        # 2. 检查上一章状态（如果不是第一章）
        if chapter_number > 1:
            if previous_state is None:
                errors.append(f"第{chapter_number}章缺少上一章状态信息")
                return False, errors

            if not previous_state.can_proceed_next():
                errors.append(
                    f"第{chapter_number-1}章状态为 {previous_state.display_name()}，"
                    f"无法继续生成第{chapter_number}章"
                )
                return False, errors

        # 3. 检查状态连续性（如果有当前状态）
        if self.current_state and chapter_number > 1:
            if self.current_state.chapter_number != chapter_number - 1:
                errors.append(
                    f"状态不连续: 当前状态为第{self.current_state.chapter_number}章，"
                    f"尝试生成第{chapter_number}章"
                )
                return False, errors

        return len(errors) == 0, errors

    def validate_chapter_draft(
        self,
        chapter_number: int,
        draft_text: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证章节草稿

        Args:
            chapter_number: 章节号
            draft_text: 草稿文本
            extracted_data: 提取的结构化数据（可选）

        Returns:
            Tuple[bool, Dict]: (是否通过, 验证结果详情)
        """
        contract = self.get_contract(chapter_number)
        if not contract:
            return True, {"message": "无契约，跳过验证"}

        # 如果没有提供提取数据，使用简单提取
        if extracted_data is None:
            extracted_data = self._simple_extract(draft_text, chapter_number)

        # 验证契约
        validation_result = contract.validate(draft_text, extracted_data)

        result_dict = {
            "passed": validation_result.passed,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "contract_id": contract.chapter_id,
        }

        return validation_result.passed, result_dict

    def _simple_extract(self, draft_text: str, chapter_number: int) -> Dict[str, Any]:
        """
        简单的数据提取（启发式）

        Args:
            draft_text: 草稿文本
            chapter_number: 章节号

        Returns:
            Dict: 提取的数据
        """
        # 这是一个非常简化的提取逻辑
        # 实际应该使用更复杂的 NLP 或 LLM 提取

        extracted = {
            "protagonist_name": "陈默" if "陈默" in draft_text else None,
            "date": None,  # 需要复杂的日期提取
            "locations": [],  # 需要复杂的地点提取
            "characters": [],  # 需要复杂的人物提取
        }

        return extracted

    def update_state_from_draft(
        self,
        chapter_number: int,
        draft_text: str
    ) -> StoryState:
        """
        从草稿更新故事状态

        Args:
            chapter_number: 章节号
            draft_text: 草稿文本

        Returns:
            StoryState: 更新后的状态
        """
        new_state = StoryState.extract_from_draft(
            draft_text=draft_text,
            chapter_number=chapter_number,
            previous_state=self.current_state
        )

        # 验证连续性
        if self.current_state:
            continuity_errors = new_state.validate_continuity(self.current_state)
            if continuity_errors:
                logger.warning(f"第{chapter_number}章连续性错误: {continuity_errors}")

        self.current_state = new_state
        logger.info(f"更新状态到第{chapter_number}章: {new_state.summary()}")

        return new_state

    def get_current_state(self) -> Optional[StoryState]:
        """获取当前状态"""
        return self.current_state

    def summary(self) -> str:
        """生成集成状态摘要"""
        lines = [
            "Contract Integration Summary:",
            f"  Enabled: {self.enabled}",
            f"  Contracts loaded: {len(self.contracts)}",
            f"  Story Bible: {self.story_bible_path}",
        ]

        if self.current_state:
            lines.append(f"  Current state: Chapter {self.current_state.chapter_number}")

        return "\n".join(lines)


def create_integration(
    project_path: Path,
    enable_contract_integration: bool = False
) -> Optional[ContractIntegration]:
    """
    创建契约集成实例

    Args:
        project_path: 项目路径
        enable_contract_integration: 是否启用契约集成

    Returns:
        ContractIntegration 或 None
    """
    if not enable_contract_integration:
        return None

    try:
        integration = ContractIntegration(project_path)
        if integration.is_enabled():
            integration.initialize_state()
            return integration
        else:
            logger.warning("契约集成未启用（Story Bible 不存在或加载失败）")
            return None
    except Exception as e:
        logger.error(f"创建契约集成失败: {e}")
        return None
