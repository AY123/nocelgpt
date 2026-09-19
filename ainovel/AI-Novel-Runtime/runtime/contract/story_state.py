"""
故事状态（Story State）

定义跨章节传递的世界状态，确保连续性。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class RelationshipType(Enum):
    """人物关系类型"""
    ALLY = "ally"  # 盟友
    ENEMY = "enemy"  # 敌人
    NEUTRAL = "neutral"  # 中立
    MENTOR = "mentor"  # 导师
    SUBORDINATE = "subordinate"  # 下属
    PARTNER = "partner"  # 合作伙伴


@dataclass
class Character:
    """人物信息"""
    id: str  # CHR-90001
    name: str  # 陈默
    role: str  # protagonist, antagonist, ally, etc.
    status: str  # active, dead, disappeared
    first_appearance_chapter: int  # 首次出现章节


@dataclass
class Relationship:
    """人物关系"""
    from_character: str  # CHR-90001
    to_character: str  # CHR-90002
    relationship_type: RelationshipType
    description: str  # 关系描述


@dataclass
class Thread:
    """故事线索"""
    id: str  # 线索ID
    description: str  # 线索描述
    opened_chapter: int  # 打开的章节
    closed_chapter: Optional[int] = None  # 关闭的章节（None表示未关闭）


@dataclass
class StoryState:
    """
    故事状态：跨章节共享的世界状态

    这个状态在每章生成后提取，传递给下一章作为输入。
    确保章节之间的连续性和一致性。
    """

    # ============================================================
    # 时空信息
    # ============================================================

    current_date: str  # 当前日期（YYYY-MM-DD）
    current_location: str  # 当前地点
    chapter_number: int  # 当前章节号

    # ============================================================
    # 主角状态
    # ============================================================

    protagonist: Character

    # ============================================================
    # 人物关系图
    # ============================================================

    characters: Dict[str, Character] = field(default_factory=dict)  # id -> Character
    relationships: List[Relationship] = field(default_factory=list)

    # ============================================================
    # 未完成的线索
    # ============================================================

    open_threads: List[Thread] = field(default_factory=list)
    resolved_threads: List[Thread] = field(default_factory=list)

    # ============================================================
    # 世界事实（可选）
    # ============================================================

    world_facts: Dict[str, Any] = field(default_factory=dict)

    def validate_continuity(self, prev_state: 'StoryState') -> List[str]:
        """
        验证与上一个状态的连续性

        Args:
            prev_state: 上一章的状态

        Returns:
            List[str]: 连续性错误列表（空列表表示无错误）
        """
        errors = []

        # 1. 主角名字不能变
        if self.protagonist.name != prev_state.protagonist.name:
            errors.append(
                f"主角名字改变: {prev_state.protagonist.name} → {self.protagonist.name}"
            )

        # 2. 时间只能前进
        if self.current_date < prev_state.current_date:
            errors.append(
                f"时间倒流: {prev_state.current_date} → {self.current_date}"
            )

        # 3. 章节号必须递增
        if self.chapter_number != prev_state.chapter_number + 1:
            errors.append(
                f"章节号不连续: {prev_state.chapter_number} → {self.chapter_number}"
            )

        # 4. 活跃的人物不能凭空消失（除非状态改变）
        for char_id, char in prev_state.characters.items():
            if char.status == "active":
                if char_id not in self.characters:
                    errors.append(
                        f"活跃人物消失: {char.name} ({char_id})"
                    )
                elif self.characters[char_id].status not in ["active", "dead", "disappeared"]:
                    errors.append(
                        f"人物状态异常: {char.name} {char.status} → {self.characters[char_id].status}"
                    )

        # 5. 人物不能复活（dead -> active）
        for char_id, char in prev_state.characters.items():
            if char.status == "dead":
                if char_id in self.characters and self.characters[char_id].status == "active":
                    errors.append(
                        f"死者复活: {char.name} ({char_id})"
                    )

        return errors

    @staticmethod
    def extract_from_draft(draft_text: str,
                          chapter_number: int,
                          previous_state: Optional['StoryState'] = None) -> 'StoryState':
        """
        从章节草稿中提取状态（简化版本）

        这是一个基础实现，实际应该使用更复杂的NLP提取逻辑。
        当前版本主要用于演示架构。

        Args:
            draft_text: 章节草稿文本
            chapter_number: 章节号
            previous_state: 上一章状态（可选）

        Returns:
            StoryState: 提取的状态
        """
        # 如果有上一章状态，继承大部分信息
        if previous_state:
            # 复制上一章的状态
            new_state = StoryState(
                current_date=previous_state.current_date,  # 待更新
                current_location=previous_state.current_location,  # 待更新
                chapter_number=chapter_number,
                protagonist=previous_state.protagonist,
                characters=previous_state.characters.copy(),
                relationships=previous_state.relationships.copy(),
                open_threads=previous_state.open_threads.copy(),
                resolved_threads=previous_state.resolved_threads.copy(),
                world_facts=previous_state.world_facts.copy(),
            )

            # TODO: 从 draft_text 中提取更新的信息
            # - 提取新的日期
            # - 提取新的地点
            # - 提取新出现的人物
            # - 提取关闭的线索

            return new_state
        else:
            # 第一章，创建初始状态
            protagonist = Character(
                id="CHR-90001",
                name="陈默",
                role="protagonist",
                status="active",
                first_appearance_chapter=1
            )

            return StoryState(
                current_date="2013-01-15",  # 从draft中提取
                current_location="恒远投资公司",  # 从draft中提取
                chapter_number=chapter_number,
                protagonist=protagonist,
                characters={"CHR-90001": protagonist},
            )

    @staticmethod
    def create_initial_state(bible: Dict[str, Any]) -> 'StoryState':
        """
        从 Story Bible 创建初始状态

        Args:
            bible: Story Bible 数据

        Returns:
            StoryState: 第0章的初始状态
        """
        # 从 Story Bible 读取主角信息
        protagonist_data = bible.get('protagonist', {})
        protagonist = Character(
            id="CHR-90001",
            name=protagonist_data.get('name', '陈默'),
            role="protagonist",
            status="active",
            first_appearance_chapter=0
        )

        # 从 Story Bible 读取时间线
        timeline = bible.get('timeline', {})
        start_date = timeline.get('start_date', '2013-01-15')

        # 从 Story Bible 读取世界信息
        world = bible.get('world', {})
        primary_city = world.get('primary_city', '江城')

        return StoryState(
            current_date=start_date,
            current_location=primary_city,
            chapter_number=0,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'current_date': self.current_date,
            'current_location': self.current_location,
            'chapter_number': self.chapter_number,
            'protagonist': {
                'id': self.protagonist.id,
                'name': self.protagonist.name,
                'role': self.protagonist.role,
                'status': self.protagonist.status,
            },
            'characters': {
                char_id: {
                    'id': char.id,
                    'name': char.name,
                    'role': char.role,
                    'status': char.status,
                }
                for char_id, char in self.characters.items()
            },
            'open_threads': [
                {'id': t.id, 'description': t.description, 'opened_chapter': t.opened_chapter}
                for t in self.open_threads
            ],
            'resolved_threads': [
                {'id': t.id, 'description': t.description, 'opened_chapter': t.opened_chapter, 'closed_chapter': t.closed_chapter}
                for t in self.resolved_threads
            ],
        }

    def summary(self) -> str:
        """生成状态摘要"""
        return f"""
StoryState 摘要 (第{self.chapter_number}章):
  日期: {self.current_date}
  地点: {self.current_location}
  主角: {self.protagonist.name}
  人物数: {len(self.characters)}
  未完成线索: {len(self.open_threads)}
  已完成线索: {len(self.resolved_threads)}
        """.strip()
