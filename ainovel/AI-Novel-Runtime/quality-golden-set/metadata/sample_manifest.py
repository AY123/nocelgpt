"""sample_manifest.py — N100-011 golden-set sample manifest helpers.

This module turns the existing golden-set sample schema into a concrete manifest
shape so the 50/50 sample set can be audited as a proper human-quality corpus.
It is intentionally conservative: no synthetic content is generated here; the
module only validates and inventories sample folders.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from runtime.serialize.serialization_utils import content_hash, dump_pretty_json

MANIFEST_KIND = "quality_golden_set_sample_manifest"
MANIFEST_VERSION = "1.0"

REQUIRED_FILES = ("body.txt", "meta.json", "human_scores.json", "labels.json", "notes.md")


def load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def validate_sample_dir(sample_dir: str | Path) -> dict:
    sample_dir = Path(sample_dir)
    meta = load_json(sample_dir / "meta.json") or {}
    missing = [name for name in REQUIRED_FILES if not (sample_dir / name).is_file()]
    body = (sample_dir / "body.txt").read_text(encoding="utf-8") if (sample_dir / "body.txt").is_file() else ""
    record = {
        "sample_id": meta.get("sample_id"),
        "title": meta.get("title"),
        "genre": meta.get("genre"),
        "chapter_position": meta.get("chapter_position"),
        "source_type": meta.get("source_type"),
        "source_hint": meta.get("source_hint"),
        "risk_flags": meta.get("risk_flags") or [],
        "revision_candidate": meta.get("revision_candidate"),
        "target_dimensions": meta.get("target_dimensions") or [],
        "missing_files": missing,
        "has_all_required_files": not missing,
        "body_chars": len(body),
        "content_hash": content_hash({
            "meta": meta,
            "body": body,
        }),
    }
    record["status"] = "complete" if not missing and meta.get("sample_id") else "incomplete"
    return record


def inventory_samples(root: str | Path) -> dict:
    root = Path(root)
    rows = []
    for sample_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (sample_dir / "meta.json").is_file():
            continue
        rows.append(validate_sample_dir(sample_dir))
    manifest = {
        "kind": MANIFEST_KIND,
        "version": MANIFEST_VERSION,
        "root": str(root),
        "sample_count": len(rows),
        "complete_count": sum(1 for r in rows if r["status"] == "complete"),
        "rows": rows,
    }
    manifest["content_hash"] = content_hash({k: v for k, v in manifest.items() if k != "content_hash"})
    return manifest


def write_manifest(path: str | Path, manifest: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(manifest) + "\n", encoding="utf-8")
    return path
