from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import ChapterIntent


@dataclass
class ChapterIntentBuilder:
    chapter_no: int
    chapter_id: str
    goal: str
    conflict_target: Optional[str] = None
    emotion_target: Optional[str] = None
    information_target: Optional[str] = None
    commercial_target: Optional[str] = None
    hook_target: Optional[str] = None
    constraints: Optional[list[str]] = None
    required_facts: Optional[list[str]] = None
    character_focus: Optional[list[str]] = None
    state_cursor: Optional[str] = None
    story_state: Optional[str] = None
    chapter_ir: Optional[str] = None
    character_runtime: Optional[str] = None
    director_objective: Optional[str] = None

    def build(self) -> ChapterIntent:
        return ChapterIntent(
            chapter_id=self.chapter_id,
            chapter_no=self.chapter_no,
            goal=self.goal,
            conflict_target=self.conflict_target,
            emotion_target=self.emotion_target,
            information_target=self.information_target,
            commercial_target=self.commercial_target,
            hook_target=self.hook_target,
            constraints=list(self.constraints or []),
            required_facts=list(self.required_facts or []),
            character_focus=list(self.character_focus or []),
            state_cursor=self.state_cursor,
            story_state=self.story_state,
            chapter_ir=self.chapter_ir,
            character_runtime=self.character_runtime,
            director_objective=self.director_objective,
        )
