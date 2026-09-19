"""character_runtime.py — Character Runtime as a projection (ANES v2, roadmap 4.3, ADR-008).

The Character Runtime is NOT a mutable per-character object each chapter edits.
Like Story State (state.py), it is a pure fold:

    CharacterRuntime@N = fold(facts, events[1..N], outline)  |  leads only

For each LEAD (protagonist + major roles) it makes the character's dramatic engine
explicit as the chapter opens — goal / pressure / secret / fear / desire /
relationship_tension / growth_stage / next_likely_action — so the drafter keeps
behavior CONTINUOUS across chapters (the lead acts from a standing goal + pressure,
not reinvented each chapter) and an editor can trace growth causally.

DISCIPLINE:
  - PURE + DETERMINISTIC (ADR-008): no model call, no randomness, no I/O in the
    fold. Same facts + same cursor + same outline => same content_hash. It reuses
    project_state's fold (the appearance/relationship views) rather than re-deriving.
  - DERIVED, never a fact (ADR-006): written under registry/derived/, pinned to
    its sources, inherits staleness for free.
  - ADVISORY, never gates (ADR-003): `gating=false`. growth_stage is a BUCKET of
    the fold (a consequence of appearing in events, not a written-back counter);
    next_likely_action is a deterministic PREDICTION from goal+pressure that
    constrains the drafter but which the chapter may deliberately subvert.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..execution.agent import _hash
from .state import project_state

# A character is a LEAD (carries a runtime engine) if its fact marks it important.
# The character-schema `importance` enum is minor/supporting/major/central — the
# top two rungs are leads. A bit player (minor/supporting) has no standing engine
# worth carrying into the prompt. `role` (an outline concept) is also honored.
_LEAD_IMPORTANCE = ("central", "major")
_LEAD_ROLES = ("protagonist", "hero", "主角", "male_lead", "female_lead")

# growth_stage buckets, keyed by how many folded events the lead appears in. This
# is the fold made legible: growth is a CONSEQUENCE of being on stage, not a field
# anyone writes. Thresholds are deliberately coarse (advisory, ADR-003).
_GROWTH_BUCKETS = (
    (0, "introduced"),    # 0 appearances yet — just declared / entering
    (1, "introduced"),    # on stage once
    (2, "developing"),    # recurring
    (4, "tested"),        # through several trials
    (7, "transformed"),   # a long arc behind them
)


def _lead_ids(facts: dict) -> List[str]:
    """Every character id that reads as a lead, in stable id order. Falls back to
    protagonist-by-role when no importance is marked, and finally (if the project
    marks nobody) to the single lowest-id character so a runtime is never empty
    for a project that clearly has a protagonist."""
    leads = []
    for rid, rec in sorted(facts.items()):
        if not rid.startswith("CHR-"):
            continue
        importance = str(rec.get("importance", "")).lower()
        role = str(rec.get("role", "")).lower()
        if importance in _LEAD_IMPORTANCE or role in _LEAD_ROLES:
            leads.append(rid)
    if leads:
        return leads
    # No importance marked anywhere: treat the lowest-id character as the lead so
    # the projection still carries the protagonist a small project obviously has.
    chr_ids = sorted(r for r in facts if r.startswith("CHR-"))
    return chr_ids[:1]


def _growth_stage(appearance_count: int) -> str:
    stage = _GROWTH_BUCKETS[0][1]
    for threshold, label in _GROWTH_BUCKETS:
        if appearance_count >= threshold:
            stage = label
    return stage


def _outline_character(outline: Optional[dict], name: str) -> dict:
    """Find the outline's character entry by name (outlines key characters by
    name, not fact id). Empty dict when absent."""
    if not outline:
        return {}
    for c in outline.get("characters") or []:
        if isinstance(c, dict) and c.get("name") == name:
            return c
    return {}


def _goal(outline_char: dict, protagonist_engine: dict, fact: dict, is_protagonist: bool) -> str:
    """The lead's standing objective. Prefer the outline's declared motivation;
    for the protagonist fall back to protagonist_engine.desire; finally the fact's
    arc/notes. Deterministic priority order."""
    motivation = (outline_char.get("motivation") or "").strip()
    if motivation:
        return motivation
    arc = (outline_char.get("arc") or "").strip()
    if is_protagonist:
        desire = (protagonist_engine.get("desire") or "").strip()
        if desire:
            return desire
    if arc:
        return arc
    fact_arc = fact.get("arcs") or []
    if fact_arc and isinstance(fact_arc[0], str):
        return fact_arc[0].strip()
    return (fact.get("notes") or "").strip() or "推进自身处境"


def _pressure(tensions: List[dict], open_setups: List[dict], is_protagonist: bool,
              conflict_ladder: List[dict]) -> str:
    """The force pushing against the goal right now, folded from active charged
    relationships + (for the protagonist) the current conflict-ladder rung. Empty
    when nothing is currently pressing."""
    parts: List[str] = []
    for t in tensions:
        if t.get("kind") in ("enemy", "rival", "antagonist", "敌人", "宿敌"):
            parts.append(f"与{t.get('with_name') or t.get('with')}的{t.get('kind')}对抗")
    if is_protagonist and conflict_ladder:
        rung = conflict_ladder[0]
        src = (rung.get("pressure_source") or rung.get("enemy") or "").strip()
        if src:
            parts.append(src)
    if not parts and open_setups:
        parts.append(f"悬而未决的伏笔（{open_setups[0].get('event')}）带来的压力")
    return "；".join(dict.fromkeys(parts))  # dedup, keep order


def _relationship_tension(cid: str, state, facts: dict) -> List[dict]:
    """The lead's currently-active charged relationships, folded from REL facts
    not yet ended by their until_event (state.relationships already computed the
    active flag). Each summarized in one line."""
    out: List[dict] = []
    for rid, rel in sorted(state.relationships.items()):
        if not rel.get("active"):
            continue
        if rel.get("from") != cid and rel.get("to") != cid:
            continue
        other = rel.get("to") if rel.get("from") == cid else rel.get("from")
        other_name = state.characters.get(other, {}).get("name", other) if other else None
        rec = facts.get(rid, {})
        tension = (rec.get("label") or rec.get("notes") or rec.get("kind") or "").strip()
        entry = {"with": other, "kind": rel.get("kind") or "关系"}
        if other_name:
            entry["with_name"] = other_name
        if tension:
            entry["tension"] = tension[:80]
        if other and other.startswith("CHR-"):
            out.append(entry)
    return out


def _next_likely_action(goal: str, pressure: str, growth_stage: str) -> str:
    """A plausible next move, synthesized DETERMINISTICALLY from goal + pressure
    (no model). Constrains the drafter toward continuous behavior; advisory
    (ADR-003) — the chapter may subvert it. Same inputs => same line."""
    if pressure:
        return f"在“{pressure}”的压力下，继续为“{goal}”采取行动"
    if growth_stage in ("tested", "transformed"):
        return f"以更成熟的姿态推进“{goal}”"
    return f"主动推进“{goal}”"


# --- psych state (§12.1 short-fall ②): STANDING inner state as the chapter opens.
# All four are DETERMINISTIC folds (no model) from the authored engine + the
# already-folded pressure / growth_stage / fear — a consequence of the fold, not a
# mutable field (ADR-008). They are the position BEFORE the mandate's per-chapter
# inner_shift MOVEMENT, never the movement itself, so the two layers stay distinct.
# Each returns "" when its source is absent, so the field is simply omitted.

def _emotion(pressure: str, growth_stage: str, has_tension: bool) -> str:
    """Standing emotional state, from whether the lead is under pressure/tension
    and how far they've come. Early + pressured reads tense; a transformed lead
    under pressure reads composed-but-braced."""
    if pressure or has_tension:
        if growth_stage in ("tested", "transformed"):
            return "沉着中透着戒备，压力下仍能自持"
        return "紧绷、警惕，被眼前的威胁牵动"
    if growth_stage in ("tested", "transformed"):
        return "沉稳内敛"
    return "尚在适应，情绪未定"


def _belief(desire: str, growth_stage: str) -> str:
    """Core conviction, from the protagonist's desire hardened by growth. Empty
    when no desire is authored (a bit-player lead carries no engine)."""
    if not desire:
        return ""
    if growth_stage == "transformed":
        return f"坚信“{desire}”值得付出一切代价"
    if growth_stage == "tested":
        return f"在动摇后重新认定“{desire}”"
    if growth_stage == "developing":
        return f"逐渐相信“{desire}”并非奢望"
    return f"隐约渴望“{desire}”，尚未笃定"


def _value(outline_char: dict, desire: str, fear: str) -> str:
    """The principle prioritized under pressure: authored value/principle if the
    outline gives one, else the tension between what the lead wants and dreads."""
    authored = (outline_char.get("value") or outline_char.get("principle") or "").strip()
    if authored:
        return authored
    if desire and fear:
        return f"在“{desire}”与“{fear}”之间，选择前者时最见其底线"
    return ""


def _decision_policy(fear: str, growth_stage: str) -> str:
    """How the lead decides under pressure, from their fear tempered by growth.
    A feared, green lead avoids; a transformed one confronts. Empty without a
    fear to react against."""
    if not fear:
        if growth_stage in ("tested", "transformed"):
            return "临事果断，依既定目标行动"
        return ""
    if growth_stage == "transformed":
        return f"已能直面“{fear}”，压力下迎难而上"
    if growth_stage == "tested":
        return f"仍忌惮“{fear}”，但会权衡后出手"
    return f"因“{fear}”而趋于谨慎、回避风险"


@dataclass(frozen=True)
class CharacterRuntime:
    """A point-in-time per-lead projection, folded from facts (ADR-008)."""
    reviewer: str
    chapter_no: int
    task_id: str
    up_to_event: Optional[str]
    outline_ref: Optional[str]
    leads: List[dict] = field(default_factory=list)
    gating: bool = False   # ADR-003 evaluative axis — advisory, never blocks

    def core(self) -> dict:
        return {
            "chapter_no": self.chapter_no,
            "task_id": self.task_id,
            "up_to_event": self.up_to_event,
            "outline_ref": self.outline_ref,
            "leads": self.leads,
        }

    @property
    def content_hash(self) -> str:
        return _hash(self.core())


def project_character_runtime(reg, *, chapter_no: int, task_id: str,
                              up_to_event: Optional[str] = None,
                              outline: Optional[dict] = None,
                              derived_from: Optional[List[str]] = None,
                              source_version: Optional[int] = None,
                              reviewer_id: str = "character-runtime-v1") -> dict:
    """Fold the Registry facts + ordered event log (up to the cursor) + the
    authored outline into a per-lead Character Runtime artifact (conforms to
    character-runtime.schema.json). Pure + deterministic (ADR-008): same facts +
    cursor + outline => same content_hash.

    `up_to_event` is the fold cursor — the leads' standing as they ENTER this
    chapter (the PREVIOUS chapter's event); None on the opening chapter. The
    Story State projection is reused for the appearance/relationship fold rather
    than re-deriving it. `derived_from`/`source_version` are the provenance pins
    the caller already computed; when omitted they are derived from the Registry.
    """
    facts = reg.facts
    state = project_state(reg, up_to_event=up_to_event)
    protagonist_engine = (outline or {}).get("protagonist_engine") or {}
    conflict_ladder = (outline or {}).get("conflict_ladder") or []

    lead_ids = _lead_ids(facts)
    protagonist_id = lead_ids[0] if lead_ids else None

    leads: List[dict] = []
    for cid in lead_ids:
        fact = facts.get(cid, {})
        char_view = state.characters.get(cid, {})
        name = fact.get("name", cid)
        is_protagonist = (cid == protagonist_id)
        outline_char = _outline_character(outline, name)

        appears_in = list(char_view.get("appears_in") or [])
        tensions = _relationship_tension(cid, state, facts)
        goal = _goal(outline_char, protagonist_engine, fact, is_protagonist)
        pressure = _pressure(tensions, state.open_setups, is_protagonist, conflict_ladder)
        growth_stage = _growth_stage(len(appears_in))

        lead = {
            "character_id": cid,
            "name": name,
            "goal": goal,
            "growth_stage": growth_stage,
            "next_likely_action": _next_likely_action(goal, pressure, growth_stage),
        }
        role = (outline_char.get("role") or fact.get("role") or "").strip()
        if is_protagonist and not role:
            role = "protagonist"
        if role:
            lead["role"] = role
        if pressure:
            lead["pressure"] = pressure
        # secret / fear / desire — drawn from the outline where authored; fear
        # falls back to the protagonist engine's flaw/cost for the protagonist.
        secret = (outline_char.get("secret") or "").strip()
        if secret:
            lead["secret"] = secret
        fear = (outline_char.get("fear") or "").strip()
        if not fear and is_protagonist:
            fear = (protagonist_engine.get("flaw") or protagonist_engine.get("cost") or "").strip()
        if fear:
            lead["fear"] = fear
        desire = (outline_char.get("desire") or "").strip()
        if not desire and is_protagonist:
            desire = (protagonist_engine.get("desire") or "").strip()
        # keep desire only when it adds something beyond the tactical goal
        if desire and desire != goal:
            lead["desire"] = desire
        # psych state (§12.1 ②): STANDING inner position as the chapter opens,
        # folded deterministically from what's already computed (pressure /
        # growth_stage / fear / desire / tensions). Each omitted when its source
        # is absent, so a bit-player lead carries no phantom psych fields.
        emotion = _emotion(pressure, growth_stage, bool(tensions))
        if emotion:
            lead["emotion"] = emotion
        belief = _belief(desire, growth_stage)
        if belief:
            lead["belief"] = belief
        value = _value(outline_char, desire, fear)
        if value:
            lead["value"] = value
        decision_policy = _decision_policy(fear, growth_stage)
        if decision_policy:
            lead["decision_policy"] = decision_policy
        if tensions:
            lead["relationship_tension"] = tensions
        if appears_in:
            lead["appears_in"] = appears_in
        lead["last_event"] = char_view.get("last_event")
        leads.append(lead)

    if derived_from is None:
        derived_from = [f"{rid}@v{int(rec.get('fact_version', 0))}"
                        for rid, rec in sorted(facts.items())]
    if source_version is None:
        source_version = reg.version

    runtime = CharacterRuntime(
        reviewer=reviewer_id, chapter_no=chapter_no, task_id=task_id,
        up_to_event=up_to_event, outline_ref=(outline or {}).get("id"),
        leads=leads)

    artifact = {
        "artifact_format": "1.0",
        "kind": "character_runtime",
        "chapter_no": chapter_no,
        "task_id": task_id,
        "up_to_event": up_to_event,
        "outline_ref": (outline or {}).get("id"),
        "leads": leads,
        "provenance": {
            "derived_from": list(derived_from),
            "source_version": source_version,
        },
    }
    artifact["content_hash"] = runtime.content_hash
    return artifact


_STAGE_LABELS = {
    "introduced": "初登场",
    "developing": "成长中",
    "tested": "历经考验",
    "transformed": "蜕变",
}


def render_character_runtime(artifact: dict, *, max_leads: int = 4) -> str:
    """Compress a Character Runtime into a compact string for the v5 prompt's
    character_runtime variable. Deterministic + bounded, mirroring state_digest /
    render_scene_plan. This is what keeps each lead's behavior CONTINUOUS: the
    drafter sees where the lead stands (goal + pressure) and their plausible next
    move, so they act from it rather than being reinvented."""
    leads = artifact.get("leads", [])[:max_leads]
    if not leads:
        return "（本章无主要角色运行时数据）"
    lines: List[str] = ["主要角色运行时（各角色带着既定目标与压力进入本章，行为需连续）："]
    for ld in leads:
        stage = _STAGE_LABELS.get(ld.get("growth_stage"), ld.get("growth_stage", ""))
        head = f"  ◆ {ld.get('name')}（{stage}）"
        role = ld.get("role")
        if role:
            head += f"[{role}]"
        lines.append(head)
        lines.append(f"      目标：{ld.get('goal')}")
        if ld.get("pressure"):
            lines.append(f"      压力：{ld['pressure']}")
        if ld.get("desire"):
            lines.append(f"      深层渴望：{ld['desire']}")
        if ld.get("fear"):
            lines.append(f"      恐惧：{ld['fear']}")
        if ld.get("secret"):
            lines.append(f"      秘密：{ld['secret']}")
        if ld.get("emotion"):
            lines.append(f"      当前情绪：{ld['emotion']}")
        if ld.get("belief"):
            lines.append(f"      信念：{ld['belief']}")
        if ld.get("value"):
            lines.append(f"      价值取向：{ld['value']}")
        if ld.get("decision_policy"):
            lines.append(f"      决策倾向：{ld['decision_policy']}")
        for t in ld.get("relationship_tension", [])[:3]:
            who = t.get("with_name") or t.get("with")
            lines.append(f"      关系张力→{who}（{t.get('kind')}）：{t.get('tension', '')}".rstrip())
        lines.append(f"      本章可能的行动：{ld.get('next_likely_action')}")
    return "\n".join(lines)
