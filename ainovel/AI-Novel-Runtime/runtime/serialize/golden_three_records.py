"""golden_three_records.py — review record helpers for the golden three pack."""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .golden_three import build_golden_three_review_pack

GOLDEN_THREE_RECORD_KIND = "golden_three_review_record"
GOLDEN_THREE_RECORD_VERSION = "1.0"


def _content_hash(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_golden_three_review_record(*, chapters: Iterable[tuple[str, str]], reviewers: Iterable[str], notes: str = "") -> dict:
    pack = build_golden_three_review_pack(chapters=chapters)
    reviewers = list(reviewers)
    record = {
        "kind": GOLDEN_THREE_RECORD_KIND,
        "version": GOLDEN_THREE_RECORD_VERSION,
        "pack": pack,
        "reviewers": reviewers,
        "notes": notes,
        "reviewer_count": len(reviewers),
    }
    record["content_hash"] = _content_hash(record)
    return record
