from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..llm.types import sha256_obj
from ..text_metrics import count_words
from .types import BeatPlan, ChapterDraft, ChapterIntent


@dataclass
class DraftWriter:
    version: int = 1

    def write(self, intent: ChapterIntent, beat_plan: BeatPlan, *, text: str, llm_meta: Optional[dict[str, Any]] = None, produced_by: Optional[dict[str, Any]] = None, source_refs: Optional[list[str]] = None, style_profile: Optional[str] = None) -> ChapterDraft:
        draft_hash = sha256_obj({
            "chapter_id": intent.chapter_id,
            "intent": intent.to_dict(),
            "beat_plan": beat_plan.to_dict(),
            "text": text,
        })
        return ChapterDraft(
            chapter_id=intent.chapter_id,
            version=self.version,
            text=text,
            word_count=count_words(text),
            draft_hash=draft_hash,
            style_profile=style_profile,
            llm_meta=llm_meta,
            produced_by=produced_by,
            source_refs=list(source_refs or []),
            artifact_id=intent.chapter_id,
        )
