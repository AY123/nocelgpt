"""ab_cleaning_report.py — tiny A/B cleaning comparison based on anonymous dialogue."""
from __future__ import annotations

from typing import Iterable

from .anonymous_dialogue import identify_speaker
from .serialization_utils import content_hash
from .speech_profile import coerce_speech_profile

AB_CLEANING_REPORT_KIND = "ab_cleaning_report"
AB_CLEANING_REPORT_VERSION = "1.0"


def build_ab_cleaning_report(*, before: str, after: str, profiles: Iterable[object]) -> dict:
    coerced = [coerce_speech_profile(p) for p in profiles]
    before_match = identify_speaker(before, coerced)
    after_match = identify_speaker(after, coerced)
    report = {
        "kind": AB_CLEANING_REPORT_KIND,
        "version": AB_CLEANING_REPORT_VERSION,
        "before": {
            "utterance": before,
            "speaker_id": before_match.speaker_id,
            "confidence": before_match.confidence,
        },
        "after": {
            "utterance": after,
            "speaker_id": after_match.speaker_id,
            "confidence": after_match.confidence,
        },
        "delta_confidence": round(after_match.confidence - before_match.confidence, 3),
        "speaker_stability": before_match.speaker_id == after_match.speaker_id,
        "profiles_used": [p.character_id for p in coerced],
    }
    report["content_hash"] = content_hash(report)
    return report
