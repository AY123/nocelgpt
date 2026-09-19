"""Import-plan boundary for Outline Bootstrap.

This module converts a confirmed final outline into candidate Registry facts for
human review. It deliberately produces a plan artifact only; applying the plan
and minting real IDs is a separate workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

IMPORT_PLAN_VERSION = 1


@dataclass(frozen=True)
class ImportPlanItem:
    plan_id: str
    action: str
    target_type: str
    candidate_id: str
    facts_dir: str
    review_status: str
    reason: str
    record: dict

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "action": self.action,
            "target_type": self.target_type,
            "candidate_id": self.candidate_id,
            "facts_dir": self.facts_dir,
            "review_status": self.review_status,
            "reason": self.reason,
            "record": self.record,
        }


def _base_record(candidate_id: str, name: str) -> dict:
    return {
        "id": candidate_id,
        "name": name,
        "status": "active",
        "fact_version": 1,
    }


def _item(
    index: int,
    *,
    target_type: str,
    candidate_id: str,
    facts_dir: str,
    reason: str,
    record: dict,
) -> ImportPlanItem:
    return ImportPlanItem(
        plan_id=f"PLAN-{index:05d}",
        action="create_candidate",
        target_type=target_type,
        candidate_id=candidate_id,
        facts_dir=facts_dir,
        review_status="needs_human_review",
        reason=reason,
        record=record,
    )


def build_import_plan(outline: dict) -> dict:
    """Build candidate facts from an outline without mutating the Registry."""
    items: list[ImportPlanItem] = []
    next_index = 1
    protagonist_id: str | None = None

    timeline = _base_record("TML-90001", "主时间线")
    timeline.update({
        "kind": "main",
        "ordering": "relative",
        "notes": f"候选时间线，来源大纲 {outline.get('id', 'OUTLINE-00001')}。",
    })
    items.append(_item(
        next_index,
        target_type="Timeline",
        candidate_id=timeline["id"],
        facts_dir="timelines",
        reason="final outline defines a main plot axis",
        record=timeline,
    ))
    next_index += 1

    for offset, character in enumerate(outline.get("characters", []), start=1):
        candidate_id = f"CHR-{90000 + offset:05d}"
        if protagonist_id is None and character.get("role") == "protagonist":
            protagonist_id = candidate_id
        record = _base_record(candidate_id, character.get("name") or f"候选角色{offset}")
        # Carry authored aliases (译名/别称) into the candidate fact so downstream
        # fact extraction can resolve a prose reference — often in a different
        # rendering than the setting name — back to this entity instead of minting
        # a duplicate. Cleaned: drop non-strings and blanks; deterministic.
        aliases = [a.strip() for a in (character.get("aliases") or [])
                   if isinstance(a, str) and a.strip()]
        record.update({
            "aliases": aliases,
            "importance": "central" if character.get("role") == "protagonist" else "supporting",
            "certainty": "canon",
            "age_facts": [],
            "affiliations": [],
            "locations_known": [],
            "abilities": [],
            "possessions": [],
            "arcs": [],
            "physical_facts": {},
            "notes": f"{character.get('role', 'character')} arc: {character.get('arc', '')}",
        })
        items.append(_item(
            next_index,
            target_type="Character",
            candidate_id=candidate_id,
            facts_dir="characters",
            reason="final outline proposes a named character",
            record=record,
        ))
        next_index += 1

    for offset, rule in enumerate(outline.get("world", {}).get("rules", []), start=1):
        candidate_id = f"MAG-{90000 + offset:05d}"
        record = _base_record(candidate_id, f"世界规则{offset}")
        record.update({
            "rule_kind": "natural_law",
            "statement": rule,
            "constraints": [],
            "enables": [],
            "requires": [],
            "known_by": [],
            "invariant_links": [],
            "certainty": "canon",
            "notes": f"候选世界规则，来源大纲 {outline.get('id', 'OUTLINE-00001')}。",
        })
        items.append(_item(
            next_index,
            target_type="WorldRule",
            candidate_id=candidate_id,
            facts_dir="world_rules",
            reason="final outline proposes a testable world rule",
            record=record,
        ))
        next_index += 1

    previous_event_id = None
    for offset, volume in enumerate(outline.get("plot", {}).get("volumes", []), start=1):
        candidate_id = f"EVT-{90000 + offset:05d}"
        record = _base_record(candidate_id, volume.get("title") or f"候选事件{offset}")
        record.update({
            "timeline": "TML-90001",
            "sequence_index": offset,
            "duration": "",
            "participants": [],
            "locations": [],
            "causes": [previous_event_id] if previous_event_id else [],
            "effects": [],
            "certainty": "canon",
            "summary": volume.get("purpose", ""),
            "notes": f"候选卷级事件，来源 {volume.get('id', '')}。",
        })
        if previous_event_id:
            previous = items[-1].record
            if previous.get("id", "").startswith("EVT-"):
                previous["effects"] = [candidate_id]
        items.append(_item(
            next_index,
            target_type="Event",
            candidate_id=candidate_id,
            facts_dir="events",
            reason="final outline volume can seed a timeline event",
            record=record,
        ))
        next_index += 1
        previous_event_id = candidate_id

    # Chapter-level events: fold each of first_30_chapters into a concrete Event
    # candidate, so the outline seeds a runnable event LOG (not just 3 coarse
    # volume events). This is what lets the serial actually run ~30 chapters
    # (serialize.plan_chapters emits one chapter per event) — the prerequisite
    # for long-novel drift diagnosis (§14.4). Events chain causally after the
    # volume events on the same timeline, sequence_index continuing monotonically,
    # so the temporal-causal gate (cause precedes effect) holds. participants
    # reference the protagonist CANDIDATE id; genesis_apply remaps candidate ids
    # to minted ids so the references never dangle.
    volume_count = sum(1 for it in items if it.target_type == "Event")
    prev_event_item = items[-1] if (items and items[-1].target_type == "Event") else None
    for chapter in outline.get("first_30_chapters", []):
        chapter_no = chapter.get("chapter_no")
        if not isinstance(chapter_no, int):
            continue
        seq = volume_count + chapter_no
        candidate_id = f"EVT-{90000 + seq:05d}"
        goal = (chapter.get("goal") or f"第{chapter_no}章").strip()
        record = _base_record(candidate_id, f"第{chapter_no}章：{goal[:24]}")
        record.update({
            "timeline": "TML-90001",
            "sequence_index": seq,
            "duration": "",
            "participants": [protagonist_id] if protagonist_id else [],
            "locations": [],
            "causes": [previous_event_id] if previous_event_id else [],
            "effects": [],
            "certainty": "canon",
            "summary": goal,
            "notes": (f"候选章节事件（第{chapter_no}章），钩子：{chapter.get('end_hook', '')}"),
        })
        if prev_event_item is not None:
            prev_event_item.record["effects"] = [candidate_id]
        item = _item(
            next_index,
            target_type="Event",
            candidate_id=candidate_id,
            facts_dir="events",
            reason="final outline chapter seeds a runnable timeline event",
            record=record,
        )
        items.append(item)
        next_index += 1
        previous_event_id = candidate_id
        prev_event_item = item

    return {
        "version": IMPORT_PLAN_VERSION,
        "kind": "outline_import_plan",
        "source_outline_id": outline.get("id", "OUTLINE-00001"),
        "review_status": "needs_human_review",
        "policy": {
            "writes_registry_facts": False,
            "requires_id_mint_review": True,
            "requires_human_approval": True,
        },
        "items": [item.to_dict() for item in items],
    }
