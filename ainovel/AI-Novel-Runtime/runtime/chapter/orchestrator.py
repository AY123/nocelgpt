from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..director.compare import build_version_comparison
from ..llm.types import sha256_obj
from ..text_metrics import count_words
from .finalizer import Finalizer
from .intent import ChapterIntentBuilder
from .planner import BeatPlanner
from .reviewer import ChapterReviewer
from .reviser import RevisionEngine
from .types import ChapterDraft, ChapterFinal
from .writer import DraftWriter


@dataclass
class ChapterProductionOrchestrator:
    writer: DraftWriter
    reviewer: ChapterReviewer  # M5 produce uses ChapterReviewer.review(draft: ChapterDraft)
    reviser: RevisionEngine
    finalizer: Finalizer
    beat_planner: BeatPlanner
    last_intent: Optional[dict] = field(default=None, init=False)
    last_beat_plan: Optional[dict] = field(default=None, init=False)
    last_draft: Optional[dict] = field(default=None, init=False)
    last_review: Optional[dict] = field(default=None, init=False)
    last_revision: Optional[dict] = field(default=None, init=False)
    last_comparison: Optional[dict] = field(default=None, init=False)
    last_final: Optional[dict] = field(default=None, init=False)

    def produce(
        self,
        *,
        chapter_no: int,
        chapter_id: str,
        goal: str,
        text: str,
        conflict_target: Optional[str] = None,
        emotion_target: Optional[str] = None,
        information_target: Optional[str] = None,
        commercial_target: Optional[str] = None,
        hook_target: Optional[str] = None,
        constraints: Optional[list[str]] = None,
        required_facts: Optional[list[str]] = None,
        character_focus: Optional[list[str]] = None,
        state_cursor: Optional[str] = None,
        story_state: Optional[str] = None,
        chapter_ir: Optional[str] = None,
        character_runtime: Optional[str] = None,
        director_objective: Optional[str] = None,
        llm_meta: Optional[dict] = None,
        produced_by: Optional[dict] = None,
        source_refs: Optional[list[str]] = None,
        style_profile: Optional[str] = None,
        candidate_versions: Optional[list[dict[str, Any]]] = None,
        project_path: Optional[str] = None,
    ) -> ChapterFinal:
        intent = ChapterIntentBuilder(
            chapter_no=chapter_no,
            chapter_id=chapter_id,
            goal=goal,
            conflict_target=conflict_target,
            emotion_target=emotion_target,
            information_target=information_target,
            commercial_target=commercial_target,
            hook_target=hook_target,
            constraints=constraints,
            required_facts=required_facts,
            character_focus=character_focus,
            state_cursor=state_cursor,
            story_state=story_state,
            chapter_ir=chapter_ir,
            character_runtime=character_runtime,
            director_objective=director_objective,
        ).build()
        self.last_intent = intent.to_dict()
        beat_plan = self.beat_planner.plan(intent)
        self.last_beat_plan = beat_plan.to_dict()
        draft = self.writer.write(
            intent,
            beat_plan,
            text=text,
            llm_meta=llm_meta,
            produced_by=produced_by,
            source_refs=source_refs,
            style_profile=style_profile,
        )
        self.last_draft = draft.to_dict()
        review = self.reviewer.review(draft)
        self.last_review = review.to_dict()
        base_revision = self.reviser.revise(draft, review)
        self.last_revision = base_revision.to_dict()
        final_review = self.reviewer.review(
            ChapterDraft(
                chapter_id=draft.chapter_id,
                version=draft.version,
                text=base_revision.after_text,
                word_count=count_words(base_revision.after_text),
                draft_hash=sha256_obj({"chapter_id": draft.chapter_id, "text": base_revision.after_text}),
                style_profile=style_profile,
                llm_meta=llm_meta,
                produced_by=produced_by,
                source_refs=source_refs or [],
            )
        )
        candidates = list(candidate_versions) if candidate_versions else self.reviser.generate_candidates(draft, review)
        if len(candidates) < 2:
            candidates.append({
                "version_id": "revision",
                "text": base_revision.after_text,
                "before_text": draft.text,
                "before_review": review.to_dict(),
                "after_review": final_review.to_dict(),
                "director_score": final_review.scores.get("commercial_pull", 0.0),
                "reason": base_revision.revision_reason or "revision result",
            })
        normalized: list[dict[str, Any]] = []
        for idx, candidate in enumerate(candidates, start=1):
            version_id = candidate.get("version_id") or candidate.get("id") or f"v{idx}"
            after_text = candidate.get("after_text") or candidate.get("text") or ""
            after_review = candidate.get("after_review") or candidate.get("review") or final_review.to_dict()
            before_text = candidate.get("before_text") or draft.text
            before_review = candidate.get("before_review") or review.to_dict()
            normalized.append({
                "version_id": version_id,
                "director_score": candidate.get("director_score", after_review.get("scores", {}).get("commercial_pull", 0.0)),
                "before_text": before_text,
                "after_text": after_text,
                "before_review": before_review,
                "after_review": after_review,
                "reason": candidate.get("reason") or f"candidate {idx}",
            })
        comparison = build_version_comparison(
            chapter_id=chapter_id,
            versions=normalized,
            objective={"id": director_objective, "commercial_target": commercial_target, "hook_target": hook_target},
            brief={"id": chapter_id, "commercial_target": commercial_target, "hook_target": hook_target},
        )
        self.last_comparison = comparison
        selected_version = comparison.get("winner")
        selected = next((c for c in normalized if c["version_id"] == selected_version), normalized[0])
        selected_text = selected["after_text"]
        selected_review = selected["after_review"]
        selected_revision = base_revision if selected_version == "revision" else None
        if selected_version == "revision":
            final = self.finalizer.finalize(
                selected_revision or base_revision,
                final_review,
                comparison_report=comparison,
                project_path=project_path,
            )
        else:
            final = self.finalizer.finalize(
                base_revision,
                review,
                comparison_report=comparison,
                project_path=project_path,
            )
            final = ChapterFinal(
                chapter_id=final.chapter_id,
                final_text=selected_text,
                final_hash=sha256_obj({"chapter_id": chapter_id, "text": selected_text}),
                final_review=selected_review,
                comparison_report=comparison,
                quality_summary=final.quality_summary,
                continuity_notes=final.continuity_notes,
                commercial_notes=final.commercial_notes,
                next_chapter_bridge=final.next_chapter_bridge,
                production_decision=final.production_decision,
                artifact_id=chapter_id,
                genre_profile_id=final.genre_profile_id,  # P0 修复：保留题材元数据
                genre_contract_version=final.genre_contract_version,  # P0 修复：保留题材元数据
            )
        self.last_final = final.to_dict()
        return final
