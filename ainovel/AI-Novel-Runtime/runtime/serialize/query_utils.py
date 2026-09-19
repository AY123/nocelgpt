"""query_utils.py — shared helpers for derived-artifact query modules."""
from __future__ import annotations

import json
from pathlib import Path

from .. import derived


def list_artifacts(project_path, category: str) -> list[dict]:
    index = derived._load_index(project_path)
    artifacts = index.get("artifacts", [])
    items = [entry for entry in artifacts if isinstance(entry, dict) and entry.get("category") == category]
    return sorted(items, key=lambda entry: entry.get("id", ""))


def load_artifact(project_path, category: str, artifact_id: str):
    path = Path(project_path) / "registry" / "derived" / category / f"{artifact_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
