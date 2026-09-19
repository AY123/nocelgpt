"""baseline_freeze.py — structured baseline freeze records.

This module captures the minimum structured metadata needed to freeze a short
baseline run for later comparison: chapter ids, artifact refs, replay hooks,
and provenance notes. It is read-side only and never writes facts.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional

from .. import derived

FREEZE_VERSION = "1.0"
FREEZE_KIND = "baseline_freeze"
CATEGORY = "baseline-freezes"


def build_baseline_freeze_record(*,
                                 baseline_id: str,
                                 chapter_ids: list[str],
                                 run_manifest_ref: Optional[str] = None,
                                 live_baseline_report_ref: Optional[str] = None,
                                 prompt_version: Optional[str] = None,
                                 replay_ref: Optional[str] = None,
                                 quality_ref: Optional[str] = None,
                                 provenance_ref: Optional[str] = None,
                                 human_edits: Optional[list[dict]] = None,
                                 notes: Optional[str] = None) -> dict:
    derived_from = [ref for ref in (
        run_manifest_ref,
        live_baseline_report_ref,
        replay_ref,
        quality_ref,
        provenance_ref,
    ) if ref]
    return {
        "kind": FREEZE_KIND,
        "version": FREEZE_VERSION,
        "baseline_id": baseline_id,
        "chapter_ids": chapter_ids,
        "run_manifest_ref": run_manifest_ref,
        "live_baseline_report_ref": live_baseline_report_ref,
        "prompt_version": prompt_version,
        "replay_ref": replay_ref,
        "quality_ref": quality_ref,
        "provenance_ref": provenance_ref,
        "human_edits": human_edits or [],
        "notes": notes,
        "provenance": {"derived_from": derived_from},
    }


def _freeze_content_hash(record: dict) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_baseline_freeze_record(*, project_path, record: dict) -> str:
    frozen = dict(record)
    frozen.setdefault("provenance", {})
    frozen["provenance"] = dict(frozen["provenance"])
    frozen["provenance"].setdefault("derived_from", [])
    frozen["content_hash"] = _freeze_content_hash(frozen)
    rel = derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=frozen["baseline_id"],
        artifact=frozen,
        serialized=json.dumps(frozen, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return rel


def list_baseline_freeze_refs(project_path) -> list[dict]:
    index = derived._load_index(project_path)
    out = []
    for entry in index.get("artifacts", []):
        if entry.get("category") == CATEGORY:
            out.append({
                "id": entry.get("id"),
                "path": entry.get("path"),
                "content_hash": entry.get("content_hash"),
                "derived_from": entry.get("derived_from", []),
                "source_version": entry.get("source_version"),
            })
    return out


def load_baseline_freeze_record(project_path, baseline_id: str) -> Optional[dict]:
    path = Path(project_path) / "registry" / "derived" / CATEGORY / f"{baseline_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
