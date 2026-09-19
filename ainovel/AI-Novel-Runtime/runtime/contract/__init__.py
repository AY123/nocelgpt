"""
Contract 模块

提供章节契约、故事状态和生产状态的定义和验证功能。
"""

from .chapter_contract import (
    ChapterContract,
    ValidationResult,
    load_story_bible_contracts,
)
from .story_state import (
    StoryState,
    Character,
    Relationship,
    RelationshipType,
    Thread,
)
from .production_state import (
    ProductionState,
    validate_state_transition,
)

__all__ = [
    'ChapterContract',
    'ValidationResult',
    'load_story_bible_contracts',
    'StoryState',
    'Character',
    'Relationship',
    'RelationshipType',
    'Thread',
    'ProductionState',
    'validate_state_transition',
]
