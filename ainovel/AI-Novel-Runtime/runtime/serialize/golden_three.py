"""golden_three.py — helpers for the golden three chapters review pack."""
from __future__ import annotations

from typing import Iterable

from .serialization_utils import content_hash


def _content_hash(data: dict) -> str:
    return content_hash(data)


def build_golden_three_review_pack(*, chapters: Iterable[tuple[str, str]]) -> dict:
    chapters = list(chapters)
    pack = {
        "kind": "golden_three_review_pack",
        "version": "1.0",
        "chapter_ids": [cid for cid, _ in chapters],
        "chapters": [{"chapter_id": cid, "body": body} for cid, body in chapters],
        "chapter_count": len(chapters),
    }
    pack["content_hash"] = _content_hash(pack)
    return pack
