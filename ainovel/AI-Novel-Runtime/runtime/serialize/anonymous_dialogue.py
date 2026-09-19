"""anonymous_dialogue.py — lightweight anonymous dialogue identification helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .speech_profile import SpeechProfile, coerce_speech_profile


@dataclass(frozen=True)
class AnonymousDialogueMatch:
    utterance: str
    speaker_id: str
    confidence: float


def score_dialogue_against_profile(utterance: str, profile: SpeechProfile) -> float:
    score = 0.0
    if profile.tone and profile.tone in utterance:
        score += 1.5
    if profile.vocabulary_level and profile.vocabulary_level in utterance:
        score += 1.0
    if profile.sentence_length == "短句" and len(utterance) < 20:
        score += 1.0
    if profile.sentence_length == "中短句" and 10 <= len(utterance) <= 30:
        score += 1.0
    for forbidden in profile.forbidden_patterns:
        if forbidden in utterance:
            score -= 1.0
    return round(max(score, 0.0), 3)


def identify_speaker(utterance: str, profiles: Iterable[SpeechProfile | dict]) -> AnonymousDialogueMatch:
    coerced = [coerce_speech_profile(p) for p in profiles]
    scored = [(p.character_id, score_dialogue_against_profile(utterance, p)) for p in coerced]
    scored.sort(key=lambda item: item[1], reverse=True)
    speaker_id, confidence = scored[0] if scored else ("", 0.0)
    return AnonymousDialogueMatch(utterance=utterance, speaker_id=speaker_id, confidence=confidence)
