"""ir.py — Chapter Narrative IR (ANES v2, Phase 4.2, ADR-006/ADR-003).

The executable middle layer of the production compiler:

    outline  ->  chapter-ir  ->  scene-plan  ->  draft prompt
    (coarse)     (this file)     (a LOWERING   )   (rendered)

Where the scene planner (planner.py) folds an outline entry straight into a beat
skeleton, the IR makes each beat's NARRATIVE WORK explicit as five operations a
web-fiction chapter must perform:

  - turning_point   : what reverses / the decisive choice
  - emotion_shift   : where the reader's feeling moves (from -> to valence)
  - information_gain : what the reader newly learns (the anti-注水 lever)
  - reader_question : the open question that pulls them forward
  - exit_hook       : the pull out of the chapter

It also declares the chapter's `payoff_target` — the concrete promise the chapter
commits to delivering — which grounds the 4.1 `promise_delivery` score against a
stated target instead of a guess.

`build_chapter_ir` is a DETERMINISTIC projection: same outline entry + same
participants => same IR + same content_hash (reproducible like any Derived
artifact, ADR-006). `lower_to_scene_plan` turns the IR into a scene-plan v2
artifact (one scene per beat, in order) — so the scene plan is now a LOWERING of
the IR, not a second parallel fold of the outline. When the chapter has no
outline entry the IR DEGRADES to a single setup beat carrying the chapter goal —
advisory, never a gate (ADR-003).
"""
from __future__ import annotations

from typing import List, Optional

from ..llm.types import sha256_obj

# Beat roles — shared vocabulary with scene-plan.schema.json (the IR lowers 1:1).
ROLE_SETUP = "setup"
ROLE_ESCALATION = "escalation"
ROLE_TURN = "turn"
ROLE_REWARD = "reward"
ROLE_EXIT_HOOK = "exit_hook"

# Payoff kinds — must match chapter-ir.schema.json payoff_target.kind enum.
_REWARD_KIND = "reward"


def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


def _beat(index: int, role: str, intent: str, *, participants=None,
          turning_point: str = "", information_gain: str = "",
          reader_question: str = "", exit_hook: str = "",
          emotion_to: Optional[int] = None, tone: str = "") -> dict:
    """One IR beat, dropping empty optional fields so the artifact stays minimal
    and its hash is stable regardless of which optionals were absent."""
    beat = {"index": index, "role": role, "intent": intent}
    if participants:
        beat["participants"] = list(participants)
    if turning_point:
        beat["turning_point"] = turning_point
    if information_gain:
        beat["information_gain"] = information_gain
    if reader_question:
        beat["reader_question"] = reader_question
    if exit_hook:
        beat["exit_hook"] = exit_hook
    if emotion_to is not None:
        emo = {"to": emotion_to}
        if tone:
            emo["tone"] = tone
        beat["emotion_shift"] = emo
    return beat


# Deterministic valence anchors per role — a coarse authored curve the LLM
# enrichment can refine, but which already gives the drafter a rising shape
# (setup low -> escalation up -> turn peak-ish -> reward peak -> hook held high).
_ROLE_VALENCE = {
    ROLE_SETUP: 35,
    ROLE_ESCALATION: 55,
    ROLE_TURN: 70,
    ROLE_REWARD: 85,
    ROLE_EXIT_HOOK: 75,
}


def _clamp_valence(v: int) -> int:
    """Keep a beat valence inside the scene-plan schema band [0,100]."""
    return max(0, min(100, int(v)))


def _long_arc_valence_shift(coord: Optional[dict]) -> int:
    """A per-chapter valence DELTA derived from the chapter's long-arc coordinate
    (N100-072, GAP-B). The per-role table alone makes every chapter's PEAK land on
    the same 1-2 values (reward=85 when the outline promised a payoff, else
    exit_hook=75) — across a book that is the mechanical 75-75-85 loop RUN-00025
    ran 33 times. Shifting the whole chapter's curve by where the chapter sits in
    the authored arc (approaching a volume climax, on a paywall, a post-climax
    breather) makes the cross-chapter peak track the arc instead of a flat cycle.

    Deterministic pure projection (ADR-008); returns 0 when there is no coordinate
    (non-v10 / no long-arc), so the fold stays byte-identical to before. The shift
    is additive and applied uniformly to every beat, then clamped [0,100] at the
    call site — it re-shapes the curve's height, not its internal rising order."""
    if not coord:
        return 0
    shift = 0
    to_climax = coord.get("chapters_to_volume_climax")
    span = coord.get("volume_span")
    # Tension ramps as the chapter nears its volume climax: ~0 far out, up to +12 at
    # the climax, normalized by volume span so short and long volumes both ramp.
    if isinstance(to_climax, int) and isinstance(span, int) and span > 0:
        if to_climax <= 0:
            shift += 12
        else:
            proximity = max(0.0, 1.0 - to_climax / span)
            shift += round(12 * proximity)
    if coord.get("is_volume_climax"):
        shift += 3          # the climax chapter itself gets an extra bump
    if coord.get("is_paywall"):
        shift += 5          # premium volume-opener leans on a strong hook
    pos = coord.get("position_in_volume")
    if isinstance(pos, int) and pos == 1 and not coord.get("is_paywall"):
        shift -= 6          # post-climax breather so the curve doesn't plateau
    return shift


def _beats_from_outline(entry: dict, participants: List[str],
                        long_arc_coord: Optional[dict] = None) -> List[dict]:
    """Map an outline chapter entry into an ordered IR beat sequence. Each outline
    field contributes at most one beat, in fixed narrative order, so the number of
    beats reflects how much intent the outline actually carried. Each beat is
    populated with the narrative ops the outline field implies.

    `long_arc_coord` (optional): the chapter's long-arc coordinate. When present,
    every beat's valence is shifted by _long_arc_valence_shift so the chapter's
    curve height tracks the authored arc (N100-072). Absent => shift 0 =>
    byte-identical to before."""
    shift = _long_arc_valence_shift(long_arc_coord)

    def _val(role: str) -> int:
        return _clamp_valence(_ROLE_VALENCE[role] + shift)

    goal = _clean(entry.get("goal"))
    conflict = _clean(entry.get("conflict"))
    escalation = _clean(entry.get("escalation"))
    reward = _clean(entry.get("reward_if_any"))
    end_hook = _clean(entry.get("end_hook"))

    beats: List[dict] = []
    idx = 1

    # setup — always present: establish the chapter's goal, plant the question.
    beats.append(_beat(
        idx, ROLE_SETUP, goal or "开场：确立本章目标与处境",
        participants=participants,
        information_gain=(f"读者了解本章处境：{goal}" if goal else ""),
        reader_question=(f"本章目标能否达成：{goal}？" if goal else ""),
        emotion_to=_val(ROLE_SETUP), tone="铺垫"))
    idx += 1

    # escalation — only if the outline named one; raises the stake.
    if escalation:
        beats.append(_beat(
            idx, ROLE_ESCALATION, "升级：压力加码，把冲突推向临界",
            participants=participants,
            information_gain=f"新的压力浮现：{escalation}",
            reader_question="局面还会更糟吗？",
            emotion_to=_val(ROLE_ESCALATION), tone="紧张"))
        idx += 1

    # turn — the reversal; the beat carrying the turning_point op.
    if escalation or conflict:
        beats.append(_beat(
            idx, ROLE_TURN, "转折：局面反转或主角做出关键选择",
            participants=participants,
            turning_point=escalation or conflict,
            information_gain="局势因反转而改变",
            reader_question="反转之后会怎样？",
            emotion_to=_val(ROLE_TURN), tone="转机"))
        idx += 1

    # reward — only if the outline promised a payoff this chapter; the beat that
    # cashes in the chapter's payoff_target.
    if reward:
        beats.append(_beat(
            idx, ROLE_REWARD, "兑现：交付本章的爽点/成长回报",
            participants=participants,
            turning_point=reward,
            information_gain=f"承诺兑现：{reward}",
            emotion_to=_val(ROLE_REWARD), tone="爽快"))
        idx += 1

    # exit_hook — always emitted (the single strongest retention lever); carries
    # the chapter's closing hook + the question left open for the next chapter.
    beats.append(_beat(
        idx, ROLE_EXIT_HOOK, "收尾钩子：留下让读者追更的悬念",
        exit_hook=end_hook or "以未解的悬念或新威胁收束本章",
        reader_question=end_hook or "接下来会发生什么？",
        emotion_to=_val(ROLE_EXIT_HOOK), tone="悬念"))
    return beats


def _beats_degraded(goal: str, participants: List[str]) -> List[dict]:
    """No outline entry: a single setup beat carrying the chapter goal. The
    advisory degrade path (ADR-003) — the draft still gets its goal + intent, just
    without a full narrative-op sequence."""
    return [_beat(1, ROLE_SETUP, goal or "开场：确立本章目标与处境",
                  participants=participants,
                  reader_question=(f"本章目标能否达成：{goal}？" if goal else ""))]


def _find_outline_entry(outline: Optional[dict], chapter_no: int) -> Optional[dict]:
    """Pull first_30_chapters[chapter_no] by its declared chapter_no (not list
    position, which can be sparse or reordered)."""
    if not outline:
        return None
    for entry in outline.get("first_30_chapters") or []:
        if isinstance(entry, dict) and entry.get("chapter_no") == chapter_no:
            return entry
    return None


def _payoff_target(entry: Optional[dict]) -> Optional[dict]:
    """Derive the chapter's concrete promise from the outline entry's reward. A
    chapter with no promised reward gets no payoff_target — promise_delivery then
    falls back to its ungrounded judgment (a pure setup/breather chapter)."""
    if not entry:
        return None
    reward = _clean(entry.get("reward_if_any"))
    if not reward:
        return None
    return {"promise": reward, "kind": _REWARD_KIND}


def build_chapter_ir(*, task_id: str, chapter_no: int, goal: str,
                     participants: List[str], derived_from: List[str],
                     source_version: int, outline: Optional[dict] = None,
                     outline_ref: Optional[str] = None,
                     long_arc_coord: Optional[dict] = None) -> dict:
    """Fold a chapter's outline intent + event participants into a Chapter IR
    Derived artifact (conforms to chapter-ir.schema.json). Deterministic: same
    inputs => same artifact, including content_hash.

    `participants` are the CHR-* ids the chapter dramatizes. `derived_from` /
    `source_version` are the provenance pins the caller already computed for the
    chapter (staleness inherited for free, ADR-006). `outline` is the optional
    NovelOutline artifact; when it lacks an entry for this chapter the IR degrades
    to a single goal-bearing beat (advisory, ADR-003).

    `long_arc_coord` (optional): the chapter's long-arc coordinate (from
    project_long_arc(...).chapter(n)). When present, the beat valences are shifted
    by where the chapter sits in the authored arc so the cross-chapter peak tracks
    the arc instead of the mechanical 75-75-85 loop (N100-072). Absent =>
    byte-identical to before."""
    entry = _find_outline_entry(outline, chapter_no)
    reference_anchor = None
    if outline and isinstance(outline.get("reference_abstraction"), dict):
        ref = outline["reference_abstraction"]
        reference_anchor = {
            "id": ref.get("id"),
            "kind": ref.get("kind"),
            "market_positioning": ref.get("market_positioning", {}),
            "structural_patterns": ref.get("structural_patterns", {}),
            "commercial_cadence": ref.get("commercial_cadence", {}),
            "transferable_abstractions": ref.get("transferable_abstractions", []),
        }
    if entry is not None:
        beats = _beats_from_outline(entry, participants, long_arc_coord)
        used_outline_ref = outline_ref or (outline or {}).get("id")
        intent = _clean(entry.get("goal")) or goal or "推进本章剧情"
        dramatic_question = _clean(entry.get("conflict"))
        payoff = _payoff_target(entry)
    else:
        beats = _beats_degraded(goal, participants)
        used_outline_ref = None
        intent = goal or "推进本章剧情"
        dramatic_question = ""
        payoff = None

    artifact = {
        "artifact_format": "1.0",
        "kind": "chapter_ir",
        "chapter_no": chapter_no,
        "task_id": task_id,
        "outline_ref": used_outline_ref,
        "reference_anchor": reference_anchor,
        "intent": intent,
        "beats": beats,
        "provenance": {
            "derived_from": list(derived_from),
            "source_version": source_version,
        },
    }
    if dramatic_question:
        artifact["dramatic_question"] = dramatic_question
    if payoff:
        artifact["payoff_target"] = payoff
    # Hash the semantic core only — exclude content_hash itself (set after).
    artifact["content_hash"] = sha256_obj({k: v for k, v in artifact.items()
                                           if k != "content_hash"})
    return artifact

# --------------------------------------------------------------------------- #
# Lowering: Chapter IR -> scene-plan v2. The scene plan is now a LOWERING of the #
# IR (one scene per beat, in order), not a second parallel fold of the outline.  #
# The IR beat's narrative ops map onto the scene as:                             #
#   role            -> beat                                                       #
#   intent          -> purpose                                                   #
#   turning_point   -> turn        (existing v1 field)                           #
#   emotion_shift   -> emotion     (existing v1 field: {valence, tone})          #
#   information_gain -> information_gain  (new v2 field)                          #
#   reader_question -> reader_question    (new v2 field)                         #
#   exit_hook       -> exit_hook   (existing v1 field)                           #
# --------------------------------------------------------------------------- #
def _scene_from_beat(beat: dict) -> dict:
    """Lower one IR beat into one scene-plan scene, dropping empty optionals so
    the artifact stays minimal and hash-stable."""
    scene = {"index": beat["index"], "beat": beat["role"],
             "purpose": beat.get("intent", "")}
    if beat.get("participants"):
        scene["participants"] = list(beat["participants"])
    if beat.get("turning_point"):
        scene["turn"] = beat["turning_point"]
    if beat.get("exit_hook"):
        scene["exit_hook"] = beat["exit_hook"]
    if beat.get("information_gain"):
        scene["information_gain"] = beat["information_gain"]
    if beat.get("reader_question"):
        scene["reader_question"] = beat["reader_question"]
    emo = beat.get("emotion_shift")
    if isinstance(emo, dict) and "to" in emo:
        out = {"valence": emo["to"]}
        if emo.get("tone"):
            out["tone"] = emo["tone"]
        scene["emotion"] = out
    return scene


def lower_to_scene_plan(ir: dict) -> dict:
    """Lower a Chapter IR into a scene-plan v2 artifact (one scene per IR beat, in
    order). Deterministic: same IR => same scene plan + content_hash. The plan
    carries `ir_ref` linking back to the IR it was lowered from; provenance is
    inherited from the IR (same sources), so staleness is detectable identically.

    This REPLACES the old outline->scene direct fold in the v4 path: the scene
    plan is now downstream of the IR, so the two artifacts can never disagree on
    the chapter's beats."""
    scenes = [_scene_from_beat(b) for b in ir.get("beats", [])]
    artifact = {
        "artifact_format": "1.0",
        "kind": "scene_plan",
        "chapter_no": ir["chapter_no"],
        "task_id": ir["task_id"],
        "outline_ref": ir.get("outline_ref"),
        "ir_ref": f"ir-{ir['task_id']}",
        "scenes": scenes,
        "provenance": {
            "derived_from": list(ir.get("provenance", {}).get("derived_from", [])),
            "source_version": ir.get("provenance", {}).get("source_version", 1),
        },
    }
    artifact["content_hash"] = sha256_obj({k: v for k, v in artifact.items()
                                           if k != "content_hash"})
    return artifact


_ROLE_LABELS = {
    ROLE_SETUP: "铺垫",
    ROLE_ESCALATION: "升级",
    ROLE_TURN: "转折",
    ROLE_REWARD: "兑现",
    ROLE_EXIT_HOOK: "钩子",
}


def render_chapter_ir(ir: dict) -> str:
    """Compress a Chapter IR into a compact string for the v4 prompt's chapter_ir
    variable. Deterministic and bounded, mirroring render_scene_plan's style. This
    is what the drafter reads to see the chapter's INTENT and per-beat narrative
    operations (not just the scene skeleton), so it writes toward declared payoff
    and information gain rather than freewheeling."""
    lines: List[str] = [f"本章意图：{ir.get('intent', '')}"]
    if ir.get("dramatic_question"):
        lines.append(f"核心悬念：{ir['dramatic_question']}")
    payoff = ir.get("payoff_target")
    if isinstance(payoff, dict) and payoff.get("promise"):
        kind = payoff.get("kind")
        lines.append(f"本章必须兑现的承诺（payoff）：{payoff['promise']}"
                     + (f"（类型：{kind}）" if kind else ""))
    lines.append("叙事节拍（按顺序推进，逐拍完成其叙事操作）：")
    for b in ir.get("beats", []):
        label = _ROLE_LABELS.get(b.get("role"), b.get("role", ""))
        parts = [f"  {b['index']}. [{label}] {b.get('intent', '')}"]
        if b.get("turning_point"):
            parts.append(f"转折：{b['turning_point']}")
        if b.get("information_gain"):
            parts.append(f"信息增量：{b['information_gain']}")
        if b.get("reader_question"):
            parts.append(f"读者悬念：{b['reader_question']}")
        emo = b.get("emotion_shift")
        if isinstance(emo, dict) and "to" in emo:
            tone = emo.get("tone")
            parts.append(f"情绪→{emo['to']}" + (f"（{tone}）" if tone else ""))
        if b.get("exit_hook"):
            parts.append(f"钩子：{b['exit_hook']}")
        lines.append("；".join(parts))
    return "\n".join(lines)
