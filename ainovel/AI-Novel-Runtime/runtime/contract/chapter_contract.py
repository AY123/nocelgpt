"""
章节契约（Chapter Contract）

定义每章生成必须满足的输入/输出约束，确保章节间的连续性和一致性。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __bool__(self):
        return self.passed


@dataclass
class ChapterContract:
    """
    章节契约：每章生成必须满足的约束

    契约定义了每章的：
    - 输入约束（entry_state, objective, antagonist）
    - 输出约束（irreversible_change, exit_state, next_hook）
    - 连续性约束（protagonist_name, date_range, allowed_locations）
    - 溯源信息（previous_chapter_hash, story_bible_hash）
    """

    # ============================================================
    # 基本信息
    # ============================================================

    chapter_id: str  # 例如: TASK-00001
    chapter_number: int  # 1-30

    # ============================================================
    # 输入约束（生成前必须满足）
    # ============================================================

    objective: str  # 本章的具体目标（从 Story Bible 读取）
    antagonist: str  # 本章的对手
    required_beats: List[str]  # 必须经过的情节点

    # ============================================================
    # 输出约束（生成后必须满足）
    # ============================================================

    irreversible_change: str  # 本章改变了什么（必须体现在文本中）
    next_hook: str  # 下一章的起点（必须在结尾体现）

    # ============================================================
    # 连续性约束（不可变）
    # ============================================================

    protagonist_name: str = "陈默"  # 主角名字（永远不变）
    date: str = ""  # 本章日期（YYYY-MM-DD）
    allowed_locations: List[str] = field(default_factory=list)  # 允许的地点
    required_characters: List[str] = field(default_factory=list)  # 必须出现的人物

    # ============================================================
    # 溯源信息
    # ============================================================

    previous_chapter_hash: Optional[str] = None  # 上一章的内容哈希
    story_bible_hash: str = ""  # Story Bible 的哈希
    story_bible_version: str = "1.2"  # Story Bible 版本

    # ============================================================
    # 元数据
    # ============================================================

    created_at: str = ""  # 创建时间

    def validate(self, draft_text: str, extracted_data: Dict[str, Any]) -> ValidationResult:
        """
        验证草稿是否满足契约

        Args:
            draft_text: 章节草稿的完整文本
            extracted_data: 从草稿中提取的结构化数据
                - protagonist_name: 提取的主角名字
                - date: 提取的日期
                - locations: 提取的地点列表
                - characters: 提取的人物列表

        Returns:
            ValidationResult: 验证结果（passed, errors, warnings）
        """
        errors = []
        warnings = []

        # 1. 主角名字检查（硬约束）
        extracted_protagonist = extracted_data.get('protagonist_name', '')
        if extracted_protagonist and extracted_protagonist != self.protagonist_name:
            errors.append(
                f"主角名字错误: 期望 '{self.protagonist_name}'，实际 '{extracted_protagonist}'"
            )

        # 检查文本前1000字是否出现主角名字
        if self.protagonist_name not in draft_text[:1000]:
            warnings.append(f"主角名字 '{self.protagonist_name}' 未在开头1000字内出现")

        # 2. 日期检查（如果指定）
        if self.date:
            extracted_date = extracted_data.get('date', '')
            if extracted_date and extracted_date != self.date:
                errors.append(
                    f"日期错误: 期望 '{self.date}'，实际 '{extracted_date}'"
                )

        # 3. 地点检查（如果指定）
        if self.allowed_locations:
            extracted_locations = extracted_data.get('locations', [])
            for loc in extracted_locations:
                # 检查是否在允许列表中（模糊匹配）
                if not any(allowed in loc for allowed in self.allowed_locations):
                    warnings.append(f"地点 '{loc}' 不在允许列表中: {self.allowed_locations}")

        # 4. 必须出现的人物检查
        if self.required_characters:
            extracted_characters = extracted_data.get('characters', [])
            for required_char in self.required_characters:
                if required_char not in extracted_characters:
                    warnings.append(f"必须出现的人物 '{required_char}' 未在文本中找到")

        # 5. 不可逆改变检查（软约束）
        if self.irreversible_change:
            # 检查文本中是否体现了这个改变
            # 这是一个启发式检查，可以后续增强
            if len(draft_text) < 1000:
                warnings.append("文本过短，可能未充分体现不可逆改变")

        # 6. 下一章钩子检查（软约束）
        if self.next_hook:
            # 检查结尾是否体现了钩子
            ending = draft_text[-500:] if len(draft_text) > 500 else draft_text
            # 这是启发式检查，实际需要更复杂的逻辑
            if len(ending) < 100:
                warnings.append("文本结尾过短，可能未设置有效的钩子")

        # 7. 目标检查（软约束）
        if self.objective:
            # 检查文本是否朝着目标推进
            # 这是高级检查，需要语义理解，暂时跳过
            pass

        # 判断是否通过
        passed = len(errors) == 0

        return ValidationResult(passed=passed, errors=errors, warnings=warnings)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'chapter_id': self.chapter_id,
            'chapter_number': self.chapter_number,
            'objective': self.objective,
            'antagonist': self.antagonist,
            'required_beats': self.required_beats,
            'irreversible_change': self.irreversible_change,
            'next_hook': self.next_hook,
            'protagonist_name': self.protagonist_name,
            'date': self.date,
            'allowed_locations': self.allowed_locations,
            'required_characters': self.required_characters,
            'previous_chapter_hash': self.previous_chapter_hash,
            'story_bible_hash': self.story_bible_hash,
            'story_bible_version': self.story_bible_version,
            'created_at': self.created_at,
        }

    @classmethod
    def from_story_bible(cls,
                        bible_chapter: Dict[str, Any],
                        chapter_number: int,
                        story_bible_hash: str,
                        previous_chapter_hash: Optional[str] = None) -> 'ChapterContract':
        """
        从 Story Bible 的章节事件生成契约

        Args:
            bible_chapter: Story Bible 中的章节数据
            chapter_number: 章节编号
            story_bible_hash: Story Bible 的哈希值
            previous_chapter_hash: 上一章的哈希值

        Returns:
            ChapterContract: 生成的契约
        """
        from datetime import datetime

        return cls(
            chapter_id=f"TASK-{chapter_number:05d}",
            chapter_number=chapter_number,
            objective=bible_chapter.get('protagonist_goal', ''),
            antagonist=bible_chapter.get('conflict', {}).get('antagonist', ''),
            required_beats=bible_chapter.get('key_beats', []),
            irreversible_change=bible_chapter.get('irreversible_change', ''),
            next_hook=bible_chapter.get('end_hook', {}).get('content', ''),
            protagonist_name="陈默",  # 从 Story Bible 顶层读取
            date=bible_chapter.get('date', ''),
            allowed_locations=[bible_chapter.get('location', '')],
            required_characters=[],  # 可以从 bible_chapter 提取
            previous_chapter_hash=previous_chapter_hash,
            story_bible_hash=story_bible_hash,
            story_bible_version="1.2",
            created_at=datetime.now().isoformat(),
        )


def load_story_bible_contracts(bible_path: str) -> List[ChapterContract]:
    """
    从 Story Bible 加载所有30章的契约

    Args:
        bible_path: Story Bible 文件路径

    Returns:
        List[ChapterContract]: 30个契约的列表
    """
    import yaml
    import hashlib
    from pathlib import Path

    # 读取 Story Bible
    with open(bible_path, 'r', encoding='utf-8') as f:
        bible = yaml.safe_load(f)

    # 计算 Story Bible 的哈希
    with open(bible_path, 'rb') as f:
        bible_hash = hashlib.sha256(f.read()).hexdigest()

    # 提取章节事件
    chapter_events = bible.get('chapter_events', [])

    # 生成契约
    contracts = []
    previous_hash = None

    for chapter_data in chapter_events:
        chapter_num = chapter_data.get('chapter')
        contract = ChapterContract.from_story_bible(
            bible_chapter=chapter_data,
            chapter_number=chapter_num,
            story_bible_hash=bible_hash,
            previous_chapter_hash=previous_hash
        )
        contracts.append(contract)

        # 这里应该是实际的章节哈希，暂时用占位符
        previous_hash = f"placeholder-hash-{chapter_num}"

    return contracts
