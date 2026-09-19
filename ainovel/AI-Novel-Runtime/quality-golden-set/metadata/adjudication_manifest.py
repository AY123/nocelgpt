"""adjudication_manifest.py — N100-012 double-blind review and adjudication ledger.

This module consumes the sample manifest and the per-sample human score files,
then emits a compact audit manifest for two-editor review and final adjudication.
It does not generate scores; it only inventories already-present human truth.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from runtime.serialize.serialization_utils import content_hash, dump_pretty_json

MANIFEST_KIND = "quality_golden_set_adjudication_manifest"
MANIFEST_VERSION = "1.0"


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def load_sample(sample_dir: str | Path) -> dict:
    sample_dir = Path(sample_dir)
    meta = _load_json(sample_dir / "meta.json") or {}
    human_scores = _load_json(sample_dir / "human_scores.json") or {}
    labels = _load_json(sample_dir / "labels.json") or {}
    body = (sample_dir / "body.txt").read_text(encoding="utf-8") if (sample_dir / "body.txt").is_file() else ""
    notes = (sample_dir / "notes.md").read_text(encoding="utf-8") if (sample_dir / "notes.md").is_file() else ""
    return {
        "sample_id": meta.get("sample_id"),
        "path": str(sample_dir),
        "title": meta.get("title"),
        "genre": meta.get("genre"),
        "chapter_position": meta.get("chapter_position"),
        "source_type": meta.get("source_type"),
        "risk_flags": meta.get("risk_flags") or [],
        "revision_candidate": meta.get("revision_candidate"),
        "target_dimensions": meta.get("target_dimensions") or [],
        "editor_a": human_scores.get("editor_a") or {},
        "editor_b": human_scores.get("editor_b") or {},
        "consensus": human_scores.get("consensus"),
        "disagreement_notes": human_scores.get("disagreement_notes") or [],
        "final_judgement": human_scores.get("final_judgement"),
        "labels": labels,
        "body_chars": len(body),
        "notes_chars": len(notes),
        "has_body": bool(body),
        "has_human_scores": bool(human_scores),
        "has_labels": bool(labels),
        "has_notes": bool(notes),
    }


def inventory_adjudication_samples(root: str | Path) -> dict:
    root = Path(root)
    rows = []
    for sample_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (sample_dir / "meta.json").is_file():
            continue
        rows.append(load_sample(sample_dir))
    manifest = {
        "kind": MANIFEST_KIND,
        "version": MANIFEST_VERSION,
        "root": str(root),
        "sample_count": len(rows),
        "boundary_count": sum(1 for r in rows if (r.get("labels") or {}).get("boundary_case")),
        "use_for_calibration_only_count": sum(1 for r in rows if (r.get("final_judgement") == "use_for_calibration_only")),
        "rows": rows,
    }
    manifest["content_hash"] = content_hash({k: v for k, v in manifest.items() if k != "content_hash"})
    return manifest


def write_manifest(path: str | Path, manifest: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(manifest) + "\n", encoding="utf-8")
    return path
