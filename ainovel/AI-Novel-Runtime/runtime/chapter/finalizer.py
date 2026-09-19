from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import json

from .. import derived
from ..llm.types import sha256_obj
from .types import ChapterFinal, ChapterRevision, ChapterReview
from .state_machine import ChapterDecision


@dataclass
class Finalizer:
    def finalize(
        self,
        revision: ChapterRevision,
        review: ChapterReview,
        comparison_report: Optional[dict[str, Any]] = None,
        canonical_decision: Optional[ChapterDecision] = None,  # P0-1: NEW
        *,
        project_path: str | Path | None = None,
    ) -> ChapterFinal:
        """
        Finalize chapter (P0-1: uses canonical ChapterDecision when provided)

        Args:
            revision: The chapter revision
            review: The chapter review
            comparison_report: Optional comparison report (legacy)
            canonical_decision: P0-1: The canonical decision (NEW, preferred)
            project_path: Project path for persistence

        Returns:
            ChapterFinal with consistent decision state
        """
        final_hash = sha256_obj({"chapter_id": revision.chapter_id, "text": revision.after_text})

        # 初始化列表（修复 UnboundLocalError）
        continuity_notes = []
        commercial_notes = []

        # P0 整改：题材契约门禁验证
        from ..genre_contract import validate_chapter_genre, GenreContractViolationError
        # 尝试从 project_path 获取题材信息
        declared_genre = "未知"  # 默认值
        genre_profile_id = None
        genre_contract_version = None

        if project_path:
            try:
                # P0 修复：使用正确的加载函数
                from ..outline.writer import load_project_outline
                outline = load_project_outline(project_path)
                if outline:
                    if "genre" in outline:
                        declared_genre = outline["genre"][0] if isinstance(outline["genre"], list) else outline["genre"]
                    # P0 修复：从 outline 读取 genre_profile_id
                    genre_profile_id = outline.get("genre_profile_id")
                    genre_contract_version = outline.get("genre_contract_version", "1.0")
            except Exception as e:
                # P0 修复：记录异常而不是静默吞掉
                import sys
                print(f"Warning: Failed to load outline: {e}", file=sys.stderr)
                # 保持默认值

        # 验证章节题材
        genre_result = validate_chapter_genre(
            revision.after_text,
            declared_genre,
            revision.chapter_id
        )

        # 严格模式：题材违规阻断生成
        strict_genre_gate = True  # 可配置为环境变量
        if not genre_result.ok:
            if strict_genre_gate:
                # 真正的门禁：抛出异常阻断
                raise GenreContractViolationError(genre_result)
            else:
                # 宽松模式：仅记录警告
                continuity_notes.insert(0, f"题材契约警告: {genre_result.message}")

        quality_summary = f"verdict={review.overall_verdict}; score_keys={','.join(sorted(review.scores.keys()))}"

        # 从 comparison_report 提取 notes
        continuity_notes.extend(list((comparison_report or {}).get("risk_summary", {}).get("risks", [])))
        commercial_notes.extend(list((comparison_report or {}).get("summary", {}).get("editorial", {}).get("notes", [])))
        next_chapter_bridge = None
        if comparison_report:
            headline = comparison_report.get("summary", {}).get("headline")
            recommendation = comparison_report.get("summary", {}).get("recommendation")
            next_chapter_bridge = f"{headline}; recommendation={recommendation}" if headline else recommendation

        # P0-1: Derive all decision fields from canonical_decision when provided
        if canonical_decision is not None:
            # Use canonical decision as source of truth
            production_decision = canonical_decision.to_dict()
            final_status = canonical_decision.state.value
            final_strategy = None  # Deprecated when using canonical decision

            # Validate consistency with comparison_report if present
            if comparison_report and "pipeline_decision" in comparison_report:
                old_advance = comparison_report["pipeline_decision"].get("advance_to_next_chapter")
                new_advance = canonical_decision.can_advance()
                if old_advance is not None and old_advance != new_advance:
                    # Log warning but use canonical decision
                    import logging
                    logging.warning(
                        f"Ch{revision.chapter_id}: comparison_report advance={old_advance} "
                        f"differs from canonical decision advance={new_advance}. "
                        f"Using canonical decision."
                    )
        else:
            # Legacy path: derive from comparison_report
            production_decision = (comparison_report or {}).get("pipeline_decision")
            final_strategy = (comparison_report or {}).get("selection_metadata", {}).get("selected_strategy")
            if final_strategy is None:
                winner_version = (comparison_report or {}).get("winner")
                final_strategy = "length_and_hook" if winner_version in (None, "revision") else None
            final_status = (production_decision or {}).get("action")
            if final_status == "advance":
                final_status = "accepted"
            elif final_status == "revise":
                final_status = "revised"
            else:
                final_status = "review"

        final = ChapterFinal(
            chapter_id=revision.chapter_id,
            final_text=revision.after_text,
            final_hash=final_hash,
            final_review=review.to_dict(),
            comparison_report=comparison_report,
            quality_summary=quality_summary,
            continuity_notes=continuity_notes,
            commercial_notes=commercial_notes,
            next_chapter_bridge=next_chapter_bridge,
            production_decision=production_decision,
            final_strategy=final_strategy,
            final_status=final_status,
            artifact_id=revision.chapter_id,
            genre_profile_id=genre_profile_id,  # P0 修复：从 outline 读取
            genre_contract_version=genre_contract_version or "1.0",  # P0 修复：从 outline 读取
        )
        if project_path is None:
            return final
        # Persist the ChapterFinal as its OWN derived artifact under
        # category "chapter-final" (id final-<chapter_id>), matching the serial
        # loop's convention. It must NEVER be written under "drafts": that id is
        # owned by the DraftWriter/execute_package envelope (which carries body,
        # director, openings, …). A ChapterFinal has none of those, so writing it
        # into drafts/ would clobber the frozen draft envelope and break every
        # downstream consumer (ADR §2: never overwrite the frozen draft bytes).
        project_path = Path(project_path)
        payload = final.to_dict()
        payload.setdefault("content_hash", final.final_hash)
        payload.setdefault("provenance", {"derived_from": [revision.base_draft_hash] if revision.base_draft_hash else [], "source_version": None})
        derived.write_artifact(
            project_path=project_path,
            category="chapter-final",
            artifact_id=f"final-{final.artifact_id or final.chapter_id}",
            artifact=payload,
            serialized=json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        )
        return final
