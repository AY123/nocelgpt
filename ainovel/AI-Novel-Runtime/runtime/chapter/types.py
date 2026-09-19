from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ChapterIntent:
    chapter_id: str
    chapter_no: int
    goal: str
    chapter_role: Optional[str] = None
    target_length_cjk: Optional[int] = None
    conflict_target: Optional[str] = None
    emotion_target: Optional[str] = None
    information_target: Optional[str] = None
    commercial_target: Optional[str] = None
    hook_target: Optional[str] = None
    constraints: list[str] = field(default_factory=list)
    required_facts: list[str] = field(default_factory=list)
    character_focus: list[str] = field(default_factory=list)
    reader_signal: Optional[str] = None
    platform_feedback: Optional[str] = None
    state_cursor: Optional[str] = None
    story_state: Optional[str] = None
    chapter_ir: Optional[str] = None
    character_runtime: Optional[str] = None
    director_objective: Optional[str] = None

    def adjusted_for_review(
        self,
        *,
        overall_verdict: str,
        issues: list[str],
        scores: dict[str, float],
    ) -> "ChapterIntent":
        target = self.target_length_cjk or 700
        if overall_verdict != "pass":
            target += 200
        if scores.get("pacing", 1.0) < 0.6:
            target += 200
        if scores.get("hook_strength", 1.0) < 0.6:
            target += 100
        return ChapterIntent(
            chapter_id=self.chapter_id,
            chapter_no=self.chapter_no,
            goal=self.goal,
            chapter_role=self.chapter_role,
            target_length_cjk=target,
            conflict_target=self.conflict_target,
            emotion_target=self.emotion_target,
            information_target=self.information_target,
            commercial_target=self.commercial_target,
            hook_target=self.hook_target,
            constraints=list(self.constraints) + [f"review_feedback:{issue}" for issue in issues],
            required_facts=list(self.required_facts),
            character_focus=list(self.character_focus),
            reader_signal=self.reader_signal,
            platform_feedback=self.platform_feedback,
            state_cursor=self.state_cursor,
            story_state=self.story_state,
            chapter_ir=self.chapter_ir,
            character_runtime=self.character_runtime,
            director_objective=self.director_objective,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "chapter_no": self.chapter_no,
            "goal": self.goal,
            "chapter_role": self.chapter_role,
            "target_length_cjk": self.target_length_cjk,
            "conflict_target": self.conflict_target,
            "emotion_target": self.emotion_target,
            "information_target": self.information_target,
            "commercial_target": self.commercial_target,
            "hook_target": self.hook_target,
            "constraints": list(self.constraints),
            "required_facts": list(self.required_facts),
            "character_focus": list(self.character_focus),
            "reader_signal": self.reader_signal,
            "platform_feedback": self.platform_feedback,
            "state_cursor": self.state_cursor,
            "story_state": self.story_state,
            "chapter_ir": self.chapter_ir,
            "character_runtime": self.character_runtime,
            "director_objective": self.director_objective,
        }


@dataclass(frozen=True)
class Beat:
    beat_id: str
    purpose: str
    summary: str
    participants: list[str] = field(default_factory=list)
    required_information: list[str] = field(default_factory=list)
    expected_emotion: Optional[str] = None
    turn: Optional[str] = None
    scene_weight: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "purpose": self.purpose,
            "summary": self.summary,
            "participants": list(self.participants),
            "required_information": list(self.required_information),
            "expected_emotion": self.expected_emotion,
            "turn": self.turn,
            "scene_weight": self.scene_weight,
        }


@dataclass(frozen=True)
class BeatPlan:
    chapter_id: str
    beats: list[Beat] = field(default_factory=list)
    length_target: Optional[int] = None
    emotion_curve: Optional[list[float]] = None
    information_curve: Optional[list[float]] = None
    hook_plan: Optional[str] = None
    turning_points: list[str] = field(default_factory=list)

    def adjusted_for_review(
        self,
        *,
        overall_verdict: str,
        issues: list[str],
        scores: dict[str, float],
    ) -> "BeatPlan":
        target = self.length_target or 700
        if overall_verdict != "pass":
            target += 150
        if scores.get("hook_strength", 1.0) < 0.6:
            target += 100
        if scores.get("pacing", 1.0) < 0.6:
            target += 150
        return BeatPlan(
            chapter_id=self.chapter_id,
            beats=list(self.beats),
            length_target=target,
            emotion_curve=list(self.emotion_curve) if self.emotion_curve is not None else None,
            information_curve=list(self.information_curve) if self.information_curve is not None else None,
            hook_plan=self.hook_plan,
            turning_points=list(self.turning_points),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "beats": [beat.to_dict() for beat in self.beats],
            "length_target": self.length_target,
            "emotion_curve": list(self.emotion_curve) if self.emotion_curve is not None else None,
            "information_curve": list(self.information_curve) if self.information_curve is not None else None,
            "hook_plan": self.hook_plan,
            "turning_points": list(self.turning_points),
        }


@dataclass(frozen=True)
class ChapterDraft:
    chapter_id: str
    version: int
    text: str
    word_count: Optional[int] = None
    draft_hash: Optional[str] = None
    style_profile: Optional[str] = None
    llm_meta: Optional[dict[str, Any]] = None
    produced_by: Optional[dict[str, Any]] = None
    source_refs: list[str] = field(default_factory=list)
    artifact_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "version": self.version,
            "text": self.text,
            "word_count": self.word_count,
            "draft_hash": self.draft_hash,
            "style_profile": self.style_profile,
            "llm_meta": self.llm_meta,
            "produced_by": self.produced_by,
            "source_refs": list(self.source_refs),
            "artifact_id": self.artifact_id,
        }


@dataclass(frozen=True)
class ChapterReview:
    chapter_id: str
    overall_verdict: str
    scores: dict[str, float]
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    revision_suggestions: list[str] = field(default_factory=list)
    gating_recommendation: Optional[str] = None
    publish_readiness: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "overall_verdict": self.overall_verdict,
            "scores": dict(self.scores),
            "issues": list(self.issues),
            "strengths": list(self.strengths),
            "revision_suggestions": list(self.revision_suggestions),
            "gating_recommendation": self.gating_recommendation,
            "publish_readiness": self.publish_readiness,
        }


@dataclass(frozen=True)
class ChapterRevision:
    chapter_id: str
    revision_round: int
    after_text: str
    base_draft_hash: Optional[str] = None
    before_text: Optional[str] = None
    changes: list[str] = field(default_factory=list)
    revision_reason: Optional[str] = None
    revision_strategy: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "base_draft_hash": self.base_draft_hash,
            "revision_round": self.revision_round,
            "before_text": self.before_text,
            "after_text": self.after_text,
            "changes": list(self.changes),
            "revision_reason": self.revision_reason,
            "revision_strategy": self.revision_strategy,
        }


@dataclass(frozen=True)
class ChapterFinal:
    chapter_id: str
    final_text: str
    final_hash: Optional[str] = None
    final_review: Optional[dict[str, Any]] = None
    comparison_report: Optional[dict[str, Any]] = None
    quality_summary: Optional[str] = None
    continuity_notes: list[str] = field(default_factory=list)
    commercial_notes: list[str] = field(default_factory=list)
    next_chapter_bridge: Optional[str] = None
    production_decision: Optional[dict[str, Any]] = None
    final_strategy: Optional[str] = None
    final_status: Optional[str] = None
    artifact_id: Optional[str] = None
    genre_profile_id: Optional[str] = None  # P0 修复：全链路题材标识
    genre_contract_version: Optional[str] = None  # P0 修复：契约版本

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "final_text": self.final_text,
            "final_hash": self.final_hash,
            "final_review": self.final_review,
            "comparison_report": self.comparison_report,
            "quality_summary": self.quality_summary,
            "continuity_notes": list(self.continuity_notes),
            "commercial_notes": list(self.commercial_notes),
            "next_chapter_bridge": self.next_chapter_bridge,
            "production_decision": self.production_decision,
            "final_strategy": self.final_strategy,
            "final_status": self.final_status,
            "artifact_id": self.artifact_id,
            "genre_profile_id": self.genre_profile_id,  # P0 修复
            "genre_contract_version": self.genre_contract_version,  # P0 修复
        }
