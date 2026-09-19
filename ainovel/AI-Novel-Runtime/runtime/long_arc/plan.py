"""plan.py — long-arc planning projection (ANES v2, M3 / Phase 9).

This module folds authored high-level planning inputs (Novel Brain, market
position, outline beats, and event skeletons) into a derived long-arc plan with
chapter-band goals, commercial cadence, and map-change conditions.

DISCIPLINE:
  - Advisory only, never gates (ADR-003).
  - Derived artifact, never a fact (ADR-006).
  - Pure/deterministic fold: same inputs => same content_hash (ADR-008).
  - Does not write the registry facts path; it writes under registry/derived.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "1.0"
PLAN_ID = "LONGARC-001"

_SCHEMA_PATH = (Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
                / "contracts" / "long-arc-plan.schema.json")


def _hash(obj) -> str:
    canonical = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _prune_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "", [], {}, ())}


@dataclass(frozen=True)
class LongArcPlan:
    id: str
    kind: str
    schema_version: str
    chapter_bands: list[dict]
    commercial_cadence: dict
    map_change_conditions: list[dict]
    progression_ladders: list[dict]
    constraints: list[str]
    provenance: dict
    content_hash: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "schema_version": self.schema_version,
            "chapter_bands": self.chapter_bands,
            "commercial_cadence": self.commercial_cadence,
            "map_change_conditions": self.map_change_conditions,
            "progression_ladders": self.progression_ladders,
            "constraints": self.constraints,
            "provenance": self.provenance,
            "content_hash": self.content_hash,
        }


def _outline_chapter_count(outline: dict) -> int:
    beats = outline.get("first_30_chapters") or outline.get("plot", {}).get("chapters") or []
    if isinstance(beats, list) and beats:
        return max(int(b.get("chapter_no") or i + 1) for i, b in enumerate(beats) if isinstance(b, dict))
    return 30


def _market_band(outline: dict) -> dict:
    mp = outline.get("market_position") or {}
    target = int(mp.get("target_wordcount_per_chapter") or 3333)
    return {
        "target_wordcount_per_chapter": target,
        "advisory_band": [int(target * 0.6), int(target * 1.5)],
        "channel": mp.get("channel") or "男频",
        "sub_genre": mp.get("sub_genre") or (outline.get("genre") or ["原创类型"])[0],
        "reader_promise": mp.get("reader_promise") or outline.get("logline") or "持续追读爽感",
    }


def _chapter_band(start: int, end: int, goal: str, commercial: str, map_change: bool = False) -> dict:
    return _prune_none({
        "id": f"BAND-{start:03d}-{end:03d}",
        "start": start,
        "end": end,
        "goal": goal,
        "commercial_goal": commercial,
        "map_change": map_change,
    })


def _tier_name(tier: str) -> str:
    """A tier's NAME only. Live-authored tiers often carry an inline gloss
    ("醒瞳——能捕捉灵骸残留的情绪波动"); the band goal wants just the name
    ("醒瞳"), else the label reads "推进至「醒瞳——能捕捉…」 · 直面「醒瞳——…阶段的
    小敌人」". Split on the first name/gloss separator (——/—/：/:/，) and keep the
    head; a bare name passes through unchanged."""
    s = str(tier).strip()
    for sep in ("——", "—", "：", ":", "，", ","):
        if sep in s:
            head = s.split(sep, 1)[0].strip()
            if head:
                return head
    return s


def _power_tiers(outline: dict) -> list[str]:
    """The authored progression ladder, if the outline declares one. Names only —
    the projection binds them into band goals, it never invents tiers.

    Supports both old "power_system" and new "progression_system" with type field."""
    # Support both old and new formats
    progression = outline.get("progression_system") or outline.get("power_system") or {}
    tiers = progression.get("tiers") if isinstance(progression, dict) else None
    return [_tier_name(t) for t in tiers] if isinstance(tiers, list) and tiers else []


def _conflict_enemies(outline: dict) -> list[str]:
    """The authored conflict ladder's enemy per escalation level, if present."""
    ladder = outline.get("conflict_ladder")
    if not isinstance(ladder, list):
        return []
    out = []
    for rung in ladder:
        if isinstance(rung, dict):
            enemy = rung.get("enemy") or rung.get("level")
            if enemy:
                out.append(str(enemy))
    return out


def _bind_goal(generic_goal: str, band_idx: int, tiers: list[str], enemies: list[str]) -> str:
    """Fold the authored power tier + conflict enemy for this band into the
    generic stage goal, binding the plan to a SPECIFIC work. Deterministic:
    band_idx maps to a tier/enemy by fixed proportion over 10 bands. Absent
    authored data, the generic goal passes through unchanged (backward-compat)."""
    parts = [generic_goal]
    if tiers:
        # 10 bands span the tier ladder proportionally (2 bands per tier for 5).
        tier = tiers[min(band_idx * len(tiers) // 10, len(tiers) - 1)]
        parts.append(f"主角推进至「{tier}」")
    if enemies:
        enemy = enemies[min(band_idx * len(enemies) // 10, len(enemies) - 1)]
        parts.append(f"直面「{enemy}」")
    return " · ".join(parts)


def build_long_arc_plan(outline: dict, *, brain: Optional[dict] = None,
                        market_position: Optional[dict] = None,
                        event_skeleton: Optional[dict] = None,
                        plan_id: str = PLAN_ID) -> LongArcPlan:
    """Fold a long-arc plan from authored planning inputs.

    The fold is deliberately simple and conservative: it derives 10 bands over the
    first 100 chapters, but only the first N bands are tightly shaped by the outline
    beat count. Additional inputs (Brain, market_position, event skeleton) refine
    the commercial promise and map-change conditions without changing the base
    structure. This keeps existing runs stable while giving M3 a concrete plan
    artifact to consume.
    """
    brain = brain or {}
    market_position = market_position or outline.get("market_position") or {}
    event_skeleton = event_skeleton or {}

    total = max(100, _outline_chapter_count(outline))
    # authored ladders bind the generic bands to a SPECIFIC work when present
    tiers = _power_tiers(outline)
    enemies = _conflict_enemies(outline)
    bands: list[dict] = []
    for idx, (start, end, goal, commercial, map_change) in enumerate([
        (1, 10, "建立核心冲突与角色目标", "hook / retention", False),
        (11, 20, "扩展冲突场并稳固关系张力", "retention / differentiation", False),
        (21, 30, "完成第一轮大回报并确认主线", "payoff / follow-through", False),
        (31, 40, "抬升代价并防止中段停滞", "avoid plateau", False),
        (41, 50, "逼迫关键选择并准备换地图", "renew urgency", True),
        (51, 60, "打开下一层冲突", "new layer of conflict", False),
        (61, 70, "推进更大的承诺与兑现", "promise delivery", False),
        (71, 80, "放大情感投资与策略压力", "sustain momentum", False),
        (81, 90, "逼近次高潮并收束前置线", "climax runway", False),
        (91, 100, "交付高潮并接到下一长弧", "climax / transition", True),
    ], start=1):
        # Allow the outline's chapter count to trim band goals if we have fewer
        # authored beats than 100. This keeps genesis preview-friendly.
        if start > total:
            break
        bound_goal = _bind_goal(goal, idx - 1, tiers, enemies)
        bands.append(_chapter_band(start, min(end, total), bound_goal, commercial, map_change))

    promises = outline.get("market_position", {}).get("reader_promise") or market_position.get("reader_promise")
    if not promises:
        promises = outline.get("logline") or "持续追读爽感"

    commercial_cadence = {
        "opening": "fast-opening-hook",
        "mid_arc": "escalate_every_10_chapters",
        "chapter_end": "hook_every_chapter",
        "long_run": "one_payoff_or_map_shift_per_band",
        "reader_promise": promises,
    }
    if brain.get("promise"):
        commercial_cadence["brain_promise"] = brain["promise"]
    if event_skeleton.get("major_events"):
        commercial_cadence["event_skeleton_count"] = len(event_skeleton.get("major_events") or [])

    map_change_conditions = [
        {"band": "41-50", "condition": "new objective / new map / new enemy source"},
        {"band": "91-100", "condition": "climax resolves and transitions to next arc"},
    ]
    # the power axis carries the authored tier ladder verbatim when present, so
    # the plan is bound to the work's real progression rather than echoing the
    # generic band goals; falls back to band goals for a bare outline.
    power_bands = tiers if tiers else [b["goal"] for b in bands[:4]]

    # Determine progression axis name based on genre
    genre = (outline.get("genre") or ["原创类型"])[0]
    progression_axis = "power"  # default
    if "都市" in genre:
        progression_axis = "wealth"
    elif "科幻" in genre:
        progression_axis = "tech"
    elif "权谋" in genre or "朝堂" in genre:
        progression_axis = "influence"

    progression_ladders = [
        {"axis": progression_axis, "bands": power_bands},
        {"axis": "relationship", "bands": ["信任建立", "张力加深", "冲突升级", "关系重排"]},
        {"axis": "commercial", "bands": [b["commercial_goal"] for b in bands]},
    ]
    constraints = [
        "每10章必须有可追溯目标",
        "换地图条件必须明确",
        "商业高潮必须可识别",
        "长弧目标可修订但不可失去连续性",
    ]
    evidence = (outline.get("provenance", {}).get("analysis_summary", {}).get("narrative_evidence") or {})
    constraints.extend(
        item for item in evidence.get("constraints", [])
        if isinstance(item, str) and item.strip() and item not in constraints
    )
    evidence_axes = [
        effect
        for pattern in evidence.get("patterns", [])
        if isinstance(pattern, dict)
        for effect in pattern.get("effects", [])
        if isinstance(effect, str) and effect.strip()
    ]
    if evidence_axes:
        progression_ladders.append({"axis": "corpus_evidence", "bands": list(dict.fromkeys(evidence_axes))})

    plan = LongArcPlan(
        id=plan_id,
        kind="long_arc_plan",
        schema_version=SCHEMA_VERSION,
        chapter_bands=bands,
        commercial_cadence=commercial_cadence,
        map_change_conditions=map_change_conditions,
        progression_ladders=progression_ladders,
        constraints=constraints,
        provenance={
            "derived_from": _prune_none({
                "outline_id": outline.get("id"),
                "brain_id": brain.get("id"),
                "market_position_id": market_position.get("id"),
                "event_skeleton_id": event_skeleton.get("id"),
                "narrative_evidence_pack_id": evidence.get("id"),
            }),
        },
        content_hash="",
    )
    core = {k: v for k, v in plan.to_dict().items() if k not in ("content_hash", "provenance")}
    object.__setattr__(plan, "content_hash", _hash(core))
    return plan


def validate_long_arc_plan(plan: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(plan), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def write_long_arc_plan(project_path: str | Path, plan: dict) -> Path:
    project = Path(project_path)
    out_dir = project / "registry" / "derived" / "long-arc"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{plan.get('id', PLAN_ID)}.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
