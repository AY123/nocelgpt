"""projection.py — the serial production funnel as a projection (ANES v2).

`project_inventory` folds three products that already exist into a
drafted/reviewed/published/ready funnel plus a per-chapter status. It is PURE and
DETERMINISTIC (same products => same report), ADVISORY and never gates (ADR-003),
and READS only — it never writes the published log (ADR-009) or facts (ADR-006).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .. import derived
from ..execution.envelope import unwrap

# Chapter lifecycle stages, lowest to highest. A chapter's status is the highest
# stage it has reached.
STAGE_DRAFTED = "drafted"
STAGE_REVIEWED = "reviewed"
STAGE_PUBLISHED = "published"


@dataclass(frozen=True)
class InventoryReport:
    reviewer: str
    drafted: int
    reviewed: int
    published: int
    ready: int                       # produced - published (库存 available to publish)
    ready_target: int
    thin_stock: bool                 # ready < ready_target (advisory break-risk)
    chapters: List[dict] = field(default_factory=list)
    gating: bool = False             # ADR-003: this projection never gates

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "drafted": self.drafted,
            "reviewed": self.reviewed,
            "published": self.published,
            "ready": self.ready,
            "ready_target": self.ready_target,
            "thin_stock": self.thin_stock,
            "chapters": self.chapters,
            "gating": self.gating,
        }


def _draft_entries(project_path) -> List[dict]:
    """Draft index entries, sorted by id — the SSOT of what was produced."""
    index = derived._load_index(project_path)
    return sorted((e for e in index.get("artifacts", [])
                   if e.get("category") == "drafts"),
                  key=lambda e: e.get("id", ""))


def _reviewed_task_ids(project_path, entries: List[dict]) -> set:
    """task_ids whose on-disk envelope carries a qa_review (evaluative QA ran).
    A bare pre-envelope draft, a missing/unparseable file, or a null qa_review
    all degrade to 'not reviewed' — never an error."""
    reviewed = set()
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        if isinstance(qa, dict) and qa.get("scores"):
            reviewed.add(unwrap(obj).get("task_id"))
    return reviewed


def _published_task_ids(log: Optional[dict]) -> set:
    """task_ids a human authorized as published (ADR-009). Only from the authored
    log; never inferred. Absent log => empty set."""
    if not log:
        return set()
    return {p.get("task_id") for p in log.get("published", [])
            if isinstance(p, dict) and p.get("task_id")}



def project_inventory(project_path: str | Path, *,
                      published_log: Optional[dict] = None,
                      ready_target: int = 0,
                      reviewer: str = "inventory-v1") -> InventoryReport:
    """Fold the produced-draft index + envelope QA markers + authored published
    log into the production funnel. Pure/deterministic; advisory, never gates.

    `published_log` is the authored log (loader.load_published_log); when None,
    published=0 (nothing authorized yet, ADR-009). `ready_target` is the desired
    stock of produced-but-unpublished chapters; ready below it flags thin stock
    (advisory only — consistent with the schedule's backlog_target, P17)."""
    entries = _draft_entries(project_path)
    reviewed_ids = _reviewed_task_ids(project_path, entries)
    published_ids = _published_task_ids(published_log)

    chapters: List[dict] = []
    drafted = reviewed = published = 0
    for e in entries:
        # A draft's task_id is the stable per-chapter key; fall back to its
        # artifact id (drafts are indexed by task_id, so these coincide).
        task_id = e.get("id")
        drafted += 1
        is_reviewed = task_id in reviewed_ids
        is_published = task_id in published_ids
        if is_reviewed:
            reviewed += 1
        if is_published:
            published += 1
        # highest stage reached
        if is_published:
            status = STAGE_PUBLISHED
        elif is_reviewed:
            status = STAGE_REVIEWED
        else:
            status = STAGE_DRAFTED
        chapters.append({"task_id": task_id, "status": status})

    ready = drafted - published
    return InventoryReport(
        reviewer=reviewer,
        drafted=drafted,
        reviewed=reviewed,
        published=published,
        ready=ready,
        ready_target=ready_target,
        thin_stock=ready < ready_target,
        chapters=chapters,
    )

