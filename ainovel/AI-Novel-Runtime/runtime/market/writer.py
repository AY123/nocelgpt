"""Writers + workflow for Market Intelligence (roadmap P0).

Persists the Market Snapshot under registry/derived/market/ (a derived artifact,
ADR-006) and NEVER under registry/facts/ — a market read is not a story fact.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .sources import load_market_observations
from .analyzer import analyze_observations
from .snapshot import build_market_snapshot, DEFAULT_FRESHNESS_DAYS


def derived_market_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "registry" / "derived" / "market"


def _project_id(project_path: str | Path) -> str:
    project = Path(project_path)
    pid = project / "registry" / "_meta" / "project-id"
    return pid.read_text(encoding="utf-8").strip() if pid.exists() else project.name


def load_market_snapshot(project_path: str | Path) -> Optional[dict]:
    """Return the current derived Market Snapshot if one exists, else None.
    Consumers (outline) treat its absence as 'no market read yet' and fall back."""
    path = derived_market_dir(project_path) / "MARKET-00001.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class MarketSnapshotResult:
    ok: bool
    stage: str
    message: str
    snapshot_json: str | None = None
    is_stale: bool | None = None
    errors: list[str] | None = None


def build_market_intelligence(project_path: str | Path, *,
                              freshness_days: int = DEFAULT_FRESHNESS_DAYS,
                              today: Optional[date] = None) -> MarketSnapshotResult:
    project = Path(project_path)
    check = load_market_observations(project)
    if not check.ok:
        return MarketSnapshotResult(ok=False, stage="observations",
                                    message="market observation validation failed",
                                    errors=check.errors)

    analysis = analyze_observations(project, check.observations)
    snapshot = build_market_snapshot(
        analysis, check.observations, project_id=_project_id(project),
        freshness_days=freshness_days, today=today)

    out_dir = derived_market_dir(project)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MARKET-00001.json"
    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

    return MarketSnapshotResult(
        ok=True, stage="done",
        message="market snapshot produced",
        snapshot_json=str(json_path.relative_to(project)),
        is_stale=snapshot["staleness"]["is_stale"])
