"""launch_30ch_run_summary_query.py — read-side query for 30 chapter run summaries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .. import derived

CATEGORY = "30ch-run-summaries"


def list_30ch_run_summaries(project_path) -> list[dict]:
    index = derived._load_index(project_path)
    artifacts = index.get("artifacts", [])
    summaries = [entry for entry in artifacts if isinstance(entry, dict) and entry.get("category") == CATEGORY]
    return sorted(summaries, key=lambda entry: entry.get("id", ""))


def load_30ch_run_summary(project_path, summary_id: str) -> Optional[dict]:
    path = Path(project_path) / "registry" / "derived" / CATEGORY / f"{summary_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
