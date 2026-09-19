from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import Beat, BeatPlan, ChapterIntent


@dataclass
class BeatPlanner:
    length_target: Optional[int] = None

    def plan(self, intent: ChapterIntent) -> BeatPlan:
        beats = [
            Beat(
                beat_id=f"{intent.chapter_id}-beat-01",
                purpose="setup",
                summary=intent.goal,
                participants=list(intent.character_focus),
                required_information=list(intent.required_facts),
                expected_emotion=intent.emotion_target,
                turn="open",
                scene_weight=0.35,
            ),
            Beat(
                beat_id=f"{intent.chapter_id}-beat-02",
                purpose="turn",
                summary=intent.conflict_target or intent.goal,
                participants=list(intent.character_focus),
                required_information=list(intent.required_facts),
                expected_emotion=intent.emotion_target,
                turn="escalate",
                scene_weight=0.35,
            ),
            Beat(
                beat_id=f"{intent.chapter_id}-beat-03",
                purpose="hook",
                summary=intent.hook_target or intent.commercial_target or intent.goal,
                participants=list(intent.character_focus),
                required_information=list(intent.required_facts),
                expected_emotion=intent.emotion_target,
                turn="close",
                scene_weight=0.3,
            ),
        ]
        return BeatPlan(
            chapter_id=intent.chapter_id,
            beats=beats,
            length_target=self.length_target,
            emotion_curve=[0.2, 0.6, 0.9],
            information_curve=[0.3, 0.7, 1.0],
            hook_plan=intent.hook_target,
            turning_points=[beat.turn for beat in beats if beat.turn],
        )
