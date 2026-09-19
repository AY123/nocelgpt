"""w10_blind_review_package.py — N100-015 blind-review package materializer.

This module does not perform human review. It packages the already-frozen W10
batch definitions together with the blind-review result template so the review
workflow can be executed and audited without inventing new review logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from runtime.serialize.serialization_utils import content_hash, dump_pretty_json

PACKAGE_KIND = "w10_blind_review_package"
PACKAGE_VERSION = "1.0"


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def build_package(metadata_root: str | Path) -> dict:
    metadata_root = Path(metadata_root)
    batches = _load_json(metadata_root / "w10-blind-review-batches.json") or {}
    template = _load_json(metadata_root / "w10-blind-review-result-template.json") or {}
    package = {
        "kind": PACKAGE_KIND,
        "version": PACKAGE_VERSION,
        "status": batches.get("status"),
        "batch_count_target": batches.get("batch_count_target"),
        "batch_size_target": batches.get("batch_size_target"),
        "review_protocol": batches.get("review_protocol") or {},
        "batches": batches.get("batches") or [],
        "result_template": template,
        "next_actions": batches.get("next_actions") or [],
    }
    package["content_hash"] = content_hash({k: v for k, v in package.items() if k != "content_hash"})
    return package


def write_package(path: str | Path, package: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(package) + "\n", encoding="utf-8")
    return path
