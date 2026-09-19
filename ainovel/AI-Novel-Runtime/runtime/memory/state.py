"""state.py — Story State as a projection over facts (ANES v2, roadmap P14, ADR-008).

Story State is NOT a mutable object that each chapter edits. It is a pure fold:

    StoryState@N = fold(facts, events[1..N])

Every view here (timeline / foreshadow / characters / items / relationships) is
RECOMPUTED from the Registry's declarative facts plus the ordered event log.
Advancing the story never mutates state — it appends a fact (a new event, an
entity with a bumped fact_version); the projection is then recomputed and the
open sets change on their own. Chapter 71 "resolving" foreshadow #18 is authored
as a new Event that picks it up; #18 then drops out of `open_setups` by itself.

DISCIPLINE:
  - PURE + DETERMINISTIC (ADR-008): no model call, no randomness, no I/O in the
    fold. Same facts => same `state_hash` (same canonical sha256 the rest of the
    Runtime uses, via execution.agent).
  - DERIVED, never a fact (ADR-006): the projection is written under
    registry/derived/, pinned to its sources, and inherits staleness for free.
  - ADVISORY, never gates (ADR-003): `gating=false`. The only gating continuity
    rule stays the deterministic cause-precedes-effect check in validator.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .. import refs
from ..execution.agent import _hash
from .threads import _is_setup, _referenced_as_cause

_INACTIVE = ("deprecated", "tombstoned")


def _ordered_event_ids(facts: dict) -> List[str]:
    """Total order the fold walks (ADR-008): indexed events by sequence_index
    (ties broken by id), then any un-indexed events in stable id order after the
    indexed ones. A sparse index is not an error — consistent with the temporal
    gate's "missing index is not a break" stance.

    Filters out:
    - deprecated/tombstoned events (status in _INACTIVE)
    - arc metadata events (arc_metadata: true)
    """
    indexed, unindexed = [], []
    for rid, rec in facts.items():
        if not rid.startswith("EVT-"):
            continue
        # Skip inactive events (deprecated, tombstoned)
        if rec.get("status") in _INACTIVE:
            continue
        # Skip arc metadata events (not for chapter generation)
        if rec.get("arc_metadata"):
            continue
        (indexed if rec.get("sequence_index") is not None else unindexed).append(rid)
    indexed.sort(key=lambda r: (facts[r]["sequence_index"], r))
    unindexed.sort()
    return indexed + unindexed


@dataclass(frozen=True)
class StoryState:
    """A point-in-time projection of the whole story, folded from facts.

    `up_to_event` is the last event id folded in (the story's "cursor"); None
    means the full log. `state_hash` makes the projection byte-reproducible and
    lets a consumer detect an unchanged state without re-reading it."""
    reviewer: str
    up_to_event: Optional[str]
    event_order: List[str] = field(default_factory=list)
    open_setups: List[dict] = field(default_factory=list)
    resolved_setups: List[dict] = field(default_factory=list)
    characters: Dict[str, dict] = field(default_factory=dict)
    items: Dict[str, dict] = field(default_factory=dict)
    relationships: Dict[str, dict] = field(default_factory=dict)
    timelines: Dict[str, dict] = field(default_factory=dict)
    gating: bool = False   # ADR-003 evaluative axis — advisory, never blocks

    def core(self) -> dict:
        """The hashed, replay-stable projection body (no reviewer label, which is
        cosmetic). Same facts + same cursor => same core => same state_hash."""
        return {
            "up_to_event": self.up_to_event,
            "event_order": self.event_order,
            "open_setups": self.open_setups,
            "resolved_setups": self.resolved_setups,
            "characters": self.characters,
            "items": self.items,
            "relationships": self.relationships,
            "timelines": self.timelines,
        }

    @property
    def state_hash(self) -> str:
        return _hash(self.core())

    def to_dict(self) -> dict:
        d = {"reviewer": self.reviewer, "gating": self.gating,
             "state_hash": self.state_hash}
        d.update(self.core())
        return d


def project_state(reg, *, up_to_event: Optional[str] = None,
                  reviewer_id: str = "story-state-v1") -> StoryState:
    """Fold the Registry's facts + ordered event log into a StoryState (ADR-008).

    Pure and deterministic: no model, no randomness, no I/O. If `up_to_event` is
    given, only events up to and including it (in the fold order) are folded in —
    the story's state "as of" that chapter's event. Entities (characters/items/
    relationships) are projected from their declarative facts, annotated with
    what the folded events did to them; nothing is mutated and nothing is written
    back to facts.
    """
    facts = reg.facts
    order = _ordered_event_ids(facts)
    if up_to_event is not None and up_to_event in order:
        order = order[: order.index(up_to_event) + 1]
    seen = set(order)
    paid_off = _referenced_as_cause({k: facts[k] for k in seen})

    open_setups: List[dict] = []
    resolved_setups: List[dict] = []
    for rid in order:
        rec = facts[rid]
        if not _is_setup(rec):
            continue
        picked_up = rid in paid_off or bool(rec.get("effects"))
        entry = {"event": rid,
                 "summary": (rec.get("summary") or rec.get("notes") or "")[:80]}
        (resolved_setups if picked_up else open_setups).append(entry)

    # Entity projections — facts annotated with fold-derived status (never mutated).
    characters, items, relationships, timelines = {}, {}, {}, {}
    for rid, rec in sorted(facts.items()):
        if rid.startswith("CHR-"):
            appearances = [e for e in order if rid in (facts[e].get("participants") or [])]
            characters[rid] = {
                "name": rec.get("name", rid),
                "status": rec.get("status"),
                "appears_in": appearances,
                "last_event": appearances[-1] if appearances else None,
            }
        elif rid.startswith("ITM-"):
            owner_raw = rec.get("owner")
            owner = refs.parse(owner_raw).id if owner_raw else None
            owner_rec = reg.get(owner) if owner else None
            items[rid] = {
                "name": rec.get("name", rid),
                "owner": owner,
                "owner_active": bool(owner_rec) and owner_rec.get("status") not in _INACTIVE,
            }
        elif rid.startswith("REL-"):
            until = rec.get("until_event")
            until_id = refs.parse(until).id if until else None
            relationships[rid] = {
                "kind": rec.get("kind"),
                "from": refs.parse(rec["from"]).id if rec.get("from") else None,
                "to": refs.parse(rec["to"]).id if rec.get("to") else None,
                # a relationship is "ended" once its until_event has been folded in
                "active": not (until_id and until_id in seen),
            }
        elif rid.startswith("TML-"):
            tl_events = [e for e in order if facts[e].get("timeline") == rid]
            timelines[rid] = {
                "name": rec.get("name", rid),
                "kind": rec.get("kind"),
                "events_so_far": len(tl_events),
                "latest_event": tl_events[-1] if tl_events else None,
            }

    return StoryState(
        reviewer=reviewer_id,
        up_to_event=up_to_event,
        event_order=order,
        open_setups=open_setups,
        resolved_setups=resolved_setups,
        characters=characters,
        items=items,
        relationships=relationships,
        timelines=timelines,
    )


def state_artifact(reg, state: StoryState) -> dict:
    """Wrap a StoryState as a Derived Artifact (ADR-006/ADR-008): pin every
    source fact at its current `fact_version` so the stored projection inherits
    staleness for free. When any source advances, `derived.check_staleness`
    marks this projection stale and it is recomputed (a fold is total + cheap).

    `content_hash` is the projection's `state_hash`, so the artifact is
    byte-reproducible and the derived index keys on it like any other artifact.
    """
    derived_from = [f"{rid}@v{int(rec.get('fact_version', 0))}"
                    for rid, rec in sorted(reg.facts.items())]
    return {
        "artifact_format": "1.0",
        "kind": "story-state",
        "capability": "StoryState",
        "task_id": f"story-state-{state.up_to_event or 'full'}",
        "content_hash": state.state_hash,
        "provenance": {
            "derived_from": derived_from,
            "source_version": reg.version,
        },
        "state": state.core(),
    }


def state_digest(state: StoryState, *, max_items: int = 6) -> str:
    """Compress a StoryState projection into a compact "story so far" recap for a
    prompt's story_state variable. Deterministic (no randomness, stable order):
    same state => same digest. Bounded by max_items so a long serial's recap
    stays token-sane. Empty state yields a single explicit line rather than "".
    """
    lines: List[str] = []

    active_chars = [v.get("name", cid) for cid, v in sorted(state.characters.items())
                    if v.get("status") == "active"]
    if active_chars:
        shown = active_chars[:max_items]
        more = f" 等{len(active_chars)}人" if len(active_chars) > max_items else ""
        lines.append("活跃角色：" + "、".join(shown) + more)

    if state.open_setups:
        lines.append("未回收伏笔（勿当新坑重开）：")
        for s in state.open_setups[:max_items]:
            summ = (s.get("summary") or "").strip()
            lines.append(f"  - {s['event']}：{summ}" if summ else f"  - {s['event']}")

    active_rels = [f"{v.get('from')}→{v.get('to')}({v.get('kind')})"
                   for rid, v in sorted(state.relationships.items()) if v.get("active")]
    if active_rels:
        lines.append("当前关系：" + "、".join(active_rels[:max_items]))

    # latest event across all timelines (by fold order)
    if state.event_order:
        lines.append(f"最近事件：{state.event_order[-1]}")

    return "\n".join(lines) if lines else "（暂无前情，本章为开篇）"
