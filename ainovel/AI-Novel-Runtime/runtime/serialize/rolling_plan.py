"""rolling_plan.py — N100-024 rolling 10-chapter execution plan.

This module projects a work-scoped long-arc into a narrow executable window for
checkpointed production. It does not invent new arc logic; it only extracts the
next 10–20 chapters, tracks active goals, and records forward-only changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from .. import derived
from .serialization_utils import content_hash, dump_pretty_json

ROLLING_PLAN_KIND = "rolling_10_chapter_plan"
ROLLING_PLAN_VERSION = "1.0"
ROLLING_PLAN_CATEGORY = "rolling-plans"


def rolling_plan_source(project_path, checkpoint_index: int) -> Optional[dict]:
    """Return an auditable source descriptor for one persisted rolling plan.

    A rolling plan is planning input, never a Fact. Its reference and hash stay
    separate from the Fact event used as the serial's story-state cursor.
    """
    plan = load_rolling_plan(project_path, checkpoint_index)
    if plan is None:
        return None
    plan_hash = str(plan.get("content_hash") or content_hash(plan))
    if not plan_hash.startswith("sha256:"):
        plan_hash = "sha256:" + plan_hash
    return {
        "kind": "rolling_plan",
        "ref": (
            f"registry/derived/{ROLLING_PLAN_CATEGORY}/"
            f"rolling-{checkpoint_index:03d}.json"
        ),
        "content_hash": plan_hash,
        "checkpoint": plan.get("checkpoint"),
        "current_chapter": plan.get("current_chapter"),
        "plan": plan,
    }


@dataclass(frozen=True)
class RollingGoal:
    chapter_no: int
    band_id: str
    active_goal: str
    commercial_goal: str
    status: str = "active"
    risk_notes: str = ""
    depends_on: list[str] | None = None
    change_type: str = ""


@dataclass(frozen=True)
class RollingChangeRecord:
    change_id: str
    chapter_no: int
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str
    approved_by: str = ""
    approval_timestamp: str = ""
    requires_recompute: bool = False


def _next_band(long_arc: dict, chapter_no: int) -> dict[str, Any] | None:
    for band in long_arc.get("chapter_bands", []) or []:
        if int(band.get("start", 0)) <= chapter_no <= int(band.get("end", 0)):
            return band
    return None


def build_rolling_plan(long_arc: dict, *, checkpoint: str = "cp-000",
                       current_chapter: int = 0, active_window: int = 10,
                       preview_window: int = 20) -> dict:
    """Project the next 10–20 chapters from a long-arc plan.

    The plan is forward-only: it starts after current_chapter and never rewrites
    completed chapters. It is deterministic for the same long_arc/checkpoint.
    """
    bands = long_arc.get("chapter_bands") or []
    if not bands:
        raise ValueError("long_arc missing chapter_bands")

    start_chapter = current_chapter + 1
    end_chapter = min(current_chapter + preview_window, max(int(b.get("end", 0)) for b in bands))
    active_end = min(current_chapter + active_window, end_chapter)

    active_goals: list[dict[str, Any]] = []
    preview_goals: list[dict[str, Any]] = []
    for ch in range(start_chapter, end_chapter + 1):
        band = _next_band(long_arc, ch)
        if not band:
            continue
        goal = RollingGoal(
            chapter_no=ch,
            band_id=str(band.get("id") or f"BAND-{ch:03d}"),
            active_goal=str(band.get("goal") or ""),
            commercial_goal=str(band.get("commercial_goal") or ""),
            status="active" if ch <= active_end else "preview",
            risk_notes="",
            depends_on=[str(band.get("id"))] if band.get("id") else [],
            change_type="initial_projection",
        )
        item = goal.__dict__
        if ch <= active_end:
            active_goals.append(item)
        else:
            preview_goals.append(item)

    plan = {
        "kind": ROLLING_PLAN_KIND,
        "version": ROLLING_PLAN_VERSION,
        "checkpoint": checkpoint,
        "current_chapter": current_chapter,
        "active_window": active_window,
        "preview_window": preview_window,
        "active_goals": active_goals,
        "preview_goals": preview_goals,
        "change_records": [],
        "long_arc_ref": {
            "id": long_arc.get("id"),
            "content_hash": long_arc.get("content_hash"),
        },
    }
    plan["content_hash"] = content_hash({k: v for k, v in plan.items() if k != "content_hash"})
    return plan


def add_change_record(plan: dict, record: dict) -> dict:
    if record.get("chapter_no") is None:
        raise ValueError("change record missing chapter_no")
    if not record.get("reason"):
        raise ValueError("change record missing reason")
    plan = dict(plan)
    records = list(plan.get("change_records") or [])
    records.append(record)
    plan["change_records"] = records
    plan["content_hash"] = content_hash({k: v for k, v in plan.items() if k != "content_hash"})
    return plan


def write_rolling_plan(path: str | Path, plan: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(plan) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Read side — the rolling plans run_serial persists at each checkpoint         #
# (rolling-{010,020,030}.json). Mirrors checkpoints.py so the plans are not     #
# write-only: nothing read them back before this (N100-074).                    #
# --------------------------------------------------------------------------- #
def load_rolling_plan(project_path, checkpoint_index: int) -> Optional[dict]:
    """Load the rolling plan persisted at a checkpoint index (10/20/30), or None
    if absent / unreadable (a run may not have reached that checkpoint)."""
    path = derived.derived_dir(project_path, ROLLING_PLAN_CATEGORY) / f"rolling-{checkpoint_index:03d}.json"
    if not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def load_rolling_plans(project_path) -> List[dict]:
    """Fold every persisted rolling plan into a checkpoint-ordered list. Returns
    only the plans actually on disk (missing ones skipped). Empty when none."""
    from .checkpoints import CHECKPOINT_INDICES
    out: List[dict] = []
    for idx in CHECKPOINT_INDICES:
        rp = load_rolling_plan(project_path, idx)
        if rp is not None:
            out.append(rp)
    return out
