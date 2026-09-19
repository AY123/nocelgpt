"""Market Snapshot synthesis (Market DSL) with staleness (roadmap P0).

Assembles the deterministic analysis into a pinned MarketSnapshot artifact that
validates against market-snapshot.schema.json. Staleness is computed from the
oldest observation's fetched_at vs a freshness window: an aged snapshot is
MARKED stale and warned about, but this is ADVISORY (gating const false) — a
stale market read never blocks the pipeline, it just tells the author their
market judgment is old.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from .sources import MarketObservation

DEFAULT_FRESHNESS_DAYS = 90
SNAPSHOT_VERSION = "1.0"


def _channel_block(channel: str, signals: list[dict]) -> dict:
    hot = []
    for s in signals:
        entry = {"genre": s["genre"], "heat": s["heat"]}
        if s.get("why_hot"):
            entry["why_hot"] = s["why_hot"]
        if s.get("drop_points"):
            entry["drop_points"] = s["drop_points"]
        hot.append(entry)
    return {"channel": channel, "hot_genres": hot}


def _earliest_fetched_at(observations: list[MarketObservation]) -> Optional[str]:
    dates = [o.fetched_at for o in observations if o.fetched_at]
    return min(dates) if dates else None


def _compute_staleness(fetched_at: Optional[str], *, freshness_days: int,
                       today: Optional[date] = None) -> dict:
    today = today or date.today()
    block = {"freshness_days": freshness_days, "is_stale": False, "gating": False}
    if not fetched_at:
        block["is_stale"] = True
        block["note"] = "no fetched_at on any observation; treat market read as unverified-age"
        return block
    try:
        fetched = datetime.strptime(fetched_at, "%Y-%m-%d").date()
    except ValueError:
        block["is_stale"] = True
        block["note"] = f"unparseable fetched_at {fetched_at!r}"
        return block
    age = (today - fetched).days
    block["age_days"] = max(0, age)
    block["is_stale"] = age > freshness_days
    if block["is_stale"]:
        block["note"] = (f"market observations are {age} days old "
                         f"(> {freshness_days}); refresh before trusting positioning")
    return block


def build_market_snapshot(analysis: dict, observations: list[MarketObservation], *,
                          project_id: str, freshness_days: int = DEFAULT_FRESHNESS_DAYS,
                          today: Optional[date] = None) -> dict:
    fetched_at = _earliest_fetched_at(observations)
    channels = [
        _channel_block("男频", analysis.get("male_signals", [])),
        _channel_block("女频", analysis.get("female_signals", [])),
    ]
    return {
        "id": "MARKET-00001",
        "kind": "market_snapshot",
        "version": SNAPSHOT_VERSION,
        "fetched_at": fetched_at or "unknown",
        "sources": [
            {"id": o.id, "filename": o.filename, "sha256": o.sha256, "platform": o.platform}
            for o in observations
        ],
        "channels": channels,
        "signals": {
            "trending_genres": analysis.get("trending_genres", []),
            "common_drop_points": analysis.get("common_drop_points", []),
            "evidence": analysis.get("evidence", []),
        },
        "staleness": _compute_staleness(fetched_at, freshness_days=freshness_days, today=today),
        "provenance": {"project_id": project_id, "analysis_summary": analysis},
    }
