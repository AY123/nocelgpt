"""threads.py — cross-chapter continuity tracking (ANES v2, roadmap P13).

Long Novel Memory: the Registry (facts + derived + mint-ledger) already IS the
project's memory — nothing is forgotten. What was missing is a checker that
surfaces the continuity failures that kill long serials: foreshadowing that is
never paid off, threads left dangling, resources held by characters who have
been written out.

DISCIPLINE (ADR-003): this is ADVISORY, gating=false. Mid-serialization, an
un-paid-off foreshadow is NORMAL (the payoff is 200 chapters away) — so this can
NEVER gate a build. It is a read-only analysis over SSOT facts (writes nothing).
The hard, gating continuity rule (a cause must precede its effect) lives in
validator.py as a deterministic check; THIS module is the soft, advisory layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .. import refs

# Markers an author puts in Event notes/summary to flag a deliberate setup.
_SETUP_MARKERS = ("[伏笔]", "[foreshadow]", "[setup]", "【伏笔】", "伏笔:", "伏笔：")


@dataclass(frozen=True)
class ThreadReport:
    reviewer: str
    open_threads: List[dict] = field(default_factory=list)
    dangling_setups: List[dict] = field(default_factory=list)
    orphan_items: List[dict] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    gating: bool = False   # structural invariant — advisory, never blocks

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "open_threads": self.open_threads,
            "dangling_setups": self.dangling_setups,
            "orphan_items": self.orphan_items,
            "findings": self.findings,
        }


def _is_setup(record: dict) -> bool:
    text = f"{record.get('summary', '')} {record.get('notes', '')}"
    return any(m in text for m in _SETUP_MARKERS)


def _referenced_as_cause(reg_facts: dict) -> set:
    """Every event id that some LATER event lists in its `causes` (i.e. is picked
    up / paid off by a subsequent event)."""
    referenced = set()
    for rid, record in reg_facts.items():
        if not rid.startswith("EVT-"):
            continue
        for raw in record.get("causes", []) or []:
            referenced.add(refs.parse(raw).id)
    return referenced


_INACTIVE = ("deprecated", "tombstoned")


def track_threads(reg, *, reviewer_id: str = "thread-tracker-v1") -> ThreadReport:
    """Scan SSOT facts for continuity threads that a long serial tends to drop.
    Everything here is ADVISORY (gating=false)."""
    facts = reg.facts
    paid_off = _referenced_as_cause(facts)

    dangling_setups: List[dict] = []
    open_threads: List[dict] = []
    for rid, record in facts.items():
        if not rid.startswith("EVT-"):
            continue
        picked_up = rid in paid_off or bool(record.get("effects"))
        if _is_setup(record) and not picked_up:
            dangling_setups.append({
                "event": rid,
                "summary": (record.get("summary") or record.get("notes") or "")[:80],
                "note": "标记为伏笔/setup 但没有后续事件回收它",
            })
        elif not picked_up and (record.get("causes") or []):
            # an event caused by something but leading nowhere yet — an open thread
            open_threads.append({
                "event": rid,
                "summary": (record.get("summary") or record.get("notes") or "")[:80],
                "note": "有前因但暂无后续 effect，线索悬而未结",
            })

    # Resources held by characters who have been written out, or with no origin.
    orphan_items: List[dict] = []
    for rid, record in facts.items():
        if not rid.startswith("ITM-"):
            continue
        owner_raw = record.get("owner")
        if owner_raw:
            owner = reg.get(refs.parse(owner_raw).id)
            if owner and owner.get("status") in _INACTIVE:
                orphan_items.append({
                    "item": rid,
                    "owner": refs.parse(owner_raw).id,
                    "note": f"资源仍归属已{owner.get('status')}的角色，需转移或回收",
                })
        elif not record.get("origin_event"):
            orphan_items.append({
                "item": rid,
                "note": "既无 owner 也无 origin_event，来历与归属都悬空",
            })

    findings = [{
        "check": "thread-tracker",
        "severity": "info",
        "message": (f"open_threads={len(open_threads)} "
                    f"dangling_setups={len(dangling_setups)} "
                    f"orphan_items={len(orphan_items)} (advisory, never gates)"),
    }]
    for d in dangling_setups:
        findings.append({"check": "dangling-setup", "severity": "warning",
                         "message": f"{d['event']}: {d['note']}"})
    for o in orphan_items:
        findings.append({"check": "orphan-item", "severity": "warning",
                         "message": f"{o['item']}: {o['note']}"})

    return ThreadReport(
        reviewer=reviewer_id,
        open_threads=open_threads,
        dangling_setups=dangling_setups,
        orphan_items=orphan_items,
        findings=findings,
    )
