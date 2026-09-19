"""launch_30ch_bundle.py — bundle query for 30 chapter launch artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .. import derived

PLAN_CATEGORY = "30ch-launch-plans"
REPORT_CATEGORY = "30ch-launch-reports"
LINK_CATEGORY = "30ch-launch-links"
RUN_CATEGORY = "30ch-launch-runs"


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def list_30ch_launch_bundle(project_path) -> dict:
    index = derived._load_index(project_path).get("artifacts", [])
    return {
        "plan_ids": [e["id"] for e in index if e.get("category") == PLAN_CATEGORY],
        "report_ids": [e["id"] for e in index if e.get("category") == REPORT_CATEGORY],
        "link_ids": [e["id"] for e in index if e.get("category") == LINK_CATEGORY],
        "run_ids": [e["id"] for e in index if e.get("category") == RUN_CATEGORY],
    }


def load_30ch_launch_bundle(project_path, bundle_id: str) -> dict:
    base = Path(project_path) / "registry" / "derived"
    bundle = {
        "kind": "30ch_launch_bundle",
        "version": "1.0",
        "bundle_id": bundle_id,
        "plan": None,
        "report": None,
        "link": None,
        "run": None,
    }
    # best-effort loaders keyed by bundle_id suffix conventions
    bundle["plan"] = _load_json(base / PLAN_CATEGORY / f"{bundle_id}.json")
    bundle["report"] = _load_json(base / REPORT_CATEGORY / f"{bundle_id}.json")
    bundle["link"] = _load_json(base / LINK_CATEGORY / f"{bundle_id}.json")
    bundle["run"] = _load_json(base / RUN_CATEGORY / f"{bundle_id}.json")
    return bundle
