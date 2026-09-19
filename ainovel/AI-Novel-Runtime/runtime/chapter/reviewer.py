from __future__ import annotations

from dataclasses import dataclass

from ..text_metrics import count_cjk_chars
from ..chapter_length import infer_chapter_role as _infer_chapter_role, role_length
from .types import ChapterDraft, ChapterReview


# Reviewer-only quality anchors per role. The length FLOOR (min_chars) now lives
# in the shared chapter_length.ROLE_LENGTH (single source of truth, also consumed
# by execution/length_check); these structure/pacing anchors pair with it and are
# kept in lockstep with the historical values so verdicts do not shift.
_CHAPTER_ROLE_SCORES = {
    "opening": {"structure": 0.85, "pacing": 0.85},
    "advance": {"structure": 0.8, "pacing": 0.75},
    "turn": {"structure": 0.82, "pacing": 0.84},
    "hook": {"structure": 0.78, "pacing": 0.9},
    "default": {"structure": 0.8, "pacing": 0.7},
}


@dataclass
class ChapterReviewer:
    def review(self, draft: ChapterDraft) -> ChapterReview:
        text = draft.text.strip()
        role = _infer_chapter_role(text)
        anchors = _CHAPTER_ROLE_SCORES.get(role, _CHAPTER_ROLE_SCORES["default"])
        min_chars = role_length(role)["min_chars"]
        cjk_chars = count_cjk_chars(text)
        scores = {
            "structure": anchors["structure"] if cjk_chars >= min_chars else 0.5,
            "pacing": anchors["pacing"] if cjk_chars >= min_chars else 0.5,
            "readability": 0.8 if text else 0.0,
            "character_consistency": 0.7,
            "setting_consistency": 0.7,
            "emotion_progress": 0.7,
            "hook_strength": 0.7 if text.endswith(("?", "！", "!", "？")) else 0.6,
            "commercial_pull": 0.7,
            "reader_signal_alignment": 0.7,
            "platform_feedback_alignment": 0.7,
        }
        verdict = "pass" if text and cjk_chars >= min_chars else "revise"
        issues = [] if verdict == "pass" else ["draft too short or empty"]
        suggestions = [] if verdict == "pass" else ["expand the chapter body and sharpen the hook"]
        return ChapterReview(
            chapter_id=draft.chapter_id,
            overall_verdict=verdict,
            scores=scores,
            issues=issues,
            strengths=["draft produced"],
            revision_suggestions=suggestions,
            gating_recommendation="advisory",
            publish_readiness="unknown" if verdict != "pass" else "ready",
        )
