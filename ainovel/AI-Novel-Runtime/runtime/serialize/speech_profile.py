"""speech_profile.py — lightweight speech profile data for character voice."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SpeechProfile:
    character_id: str
    name: str
    tone: str
    sentence_length: str
    vocabulary_level: str
    forbidden_patterns: tuple[str, ...] = ()
    preferred_patterns: tuple[str, ...] = ()

    def to_prompt_line(self) -> str:
        forbidden = f" 禁止:{'、'.join(self.forbidden_patterns)}" if self.forbidden_patterns else ""
        preferred = f" 偏好:{'、'.join(self.preferred_patterns)}" if self.preferred_patterns else ""
        return (
            f"{self.name}({self.character_id}) 语气:{self.tone} 句长:{self.sentence_length} "
            f"词汇:{self.vocabulary_level}{preferred}{forbidden}"
        )


def build_speech_profile(character_id: str, name: str, tone: str, sentence_length: str,
                         vocabulary_level: str, forbidden_patterns: Iterable[str] = (),
                         preferred_patterns: Iterable[str] = ()) -> SpeechProfile:
    return SpeechProfile(
        character_id=character_id,
        name=name,
        tone=tone,
        sentence_length=sentence_length,
        vocabulary_level=vocabulary_level,
        forbidden_patterns=tuple(forbidden_patterns),
        preferred_patterns=tuple(preferred_patterns),
    )


def render_speech_profiles(profiles: Iterable[SpeechProfile]) -> str:
    lines = ["角色语音约束："]
    for profile in profiles:
        lines.append(f"- {profile.to_prompt_line()}")
    return "\n".join(lines)


def merge_speech_profiles(*blocks: str) -> str:
    parts = [b for b in blocks if b]
    return "\n\n".join(parts)


def coerce_speech_profile(item) -> SpeechProfile:
    if isinstance(item, SpeechProfile):
        return item
    if isinstance(item, dict):
        return build_speech_profile(
            character_id=item.get("character_id", ""),
            name=item.get("name", item.get("character_id", "")),
            tone=item.get("tone", "中性"),
            sentence_length=item.get("sentence_length", "中等"),
            vocabulary_level=item.get("vocabulary_level", "中性"),
            forbidden_patterns=item.get("forbidden_patterns", ()),
            preferred_patterns=item.get("preferred_patterns", ()),
        )
    raise TypeError(f"unsupported speech profile item: {type(item)!r}")
