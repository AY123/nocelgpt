"""planner.py — deterministic scene-plan projection (ANES v2, ADR-006/ADR-003).

`plan_scenes` turns one chapter into an ordered beat skeleton by folding two
inputs that already exist but never met:

  - the chapter's orphaned outline intent: outline["first_30_chapters"][k] with
    goal / conflict / escalation / reward_if_any / end_hook, and
  - the event participants the chapter dramatizes (CHR-* from the event fact).

The v1 mapping is mechanical and total: given the same outline entry and the
same participants it always yields the same plan (reproducible like any Derived
artifact). When the chapter has no outline entry the plan DEGRADES to a single
setup scene carrying the chapter goal — advisory, never a gate (ADR-003).
"""
from __future__ import annotations

from typing import List, Optional

from ..llm.types import sha256_obj

# Beat vocabulary — must match scene-plan.schema.json enum.
BEAT_SETUP = "setup"
BEAT_ESCALATION = "escalation"
BEAT_TURN = "turn"
BEAT_REWARD = "reward"
BEAT_EXIT_HOOK = "exit_hook"


def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


def _scene(index: int, beat: str, purpose: str, *, participants=None,
           conflict: str = "", turn: str = "", exit_hook: str = "") -> dict:
    """One scene object, dropping empty optional fields so the artifact stays
    minimal and its hash is stable regardless of which optionals were absent."""
    scene = {"index": index, "beat": beat, "purpose": purpose}
    if participants:
        scene["participants"] = list(participants)
    if conflict:
        scene["conflict"] = conflict
    if turn:
        scene["turn"] = turn
    if exit_hook:
        scene["exit_hook"] = exit_hook
    return scene


def _beats_from_outline(entry: dict, participants: List[str]) -> List[dict]:
    """Map an outline chapter entry into an ordered beat skeleton. Each outline
    field contributes at most one beat, in fixed narrative order, so the number
    of scenes reflects how much intent the outline actually carried."""
    goal = _clean(entry.get("goal"))
    conflict = _clean(entry.get("conflict"))
    escalation = _clean(entry.get("escalation"))
    reward = _clean(entry.get("reward_if_any"))
    end_hook = _clean(entry.get("end_hook"))

    scenes: List[dict] = []
    idx = 1

    # setup — always present: establish the chapter's goal and who is on stage.
    scenes.append(_scene(
        idx, BEAT_SETUP,
        goal or "开场：确立本章目标与处境",
        participants=participants, conflict=conflict))
    idx += 1

    # escalation — only if the outline named one.
    if escalation:
        scenes.append(_scene(
            idx, BEAT_ESCALATION,
            "升级：压力加码，把冲突推向临界",
            participants=participants, conflict=escalation or conflict))
        idx += 1

    # turn — the reversal; anchored on the escalation/conflict when present.
    if escalation or conflict:
        scenes.append(_scene(
            idx, BEAT_TURN,
            "转折：局面反转或主角做出关键选择",
            participants=participants, turn=escalation or conflict))
        idx += 1

    # reward — only if the outline promised a payoff this chapter.
    if reward:
        scenes.append(_scene(
            idx, BEAT_REWARD,
            "兑现：交付本章的爽点/成长回报",
            participants=participants, turn=reward))
        idx += 1

    # exit_hook — the pull into the next chapter; the single strongest retention
    # lever, so it is always emitted (falls back to a generic hook line).
    scenes.append(_scene(
        idx, BEAT_EXIT_HOOK,
        "收尾钩子：留下让读者追更的悬念",
        exit_hook=end_hook or "以未解的悬念或新威胁收束本章"))
    return scenes


def _beats_degraded(goal: str, participants: List[str]) -> List[dict]:
    """No outline entry for this chapter: a single setup scene carrying the
    chapter goal. This is the advisory degrade path (ADR-003) — the draft still
    gets its goal, just without a paced skeleton."""
    return [_scene(1, BEAT_SETUP, goal or "开场：确立本章目标与处境",
                   participants=participants)]



def _find_outline_entry(outline: Optional[dict], chapter_no: int) -> Optional[dict]:
    """Pull first_30_chapters[chapter_no] by its declared chapter_no (not list
    position, which can be sparse or reordered)."""
    if not outline:
        return None
    for entry in outline.get("first_30_chapters") or []:
        if isinstance(entry, dict) and entry.get("chapter_no") == chapter_no:
            return entry
    return None


def plan_scenes(*, task_id: str, chapter_no: int, goal: str,
                participants: List[str], derived_from: List[str],
                source_version: int, outline: Optional[dict] = None,
                outline_ref: Optional[str] = None) -> dict:
    """Fold a chapter's outline intent + event participants into a scene-plan
    Derived artifact (conforms to scene-plan.schema.json). Deterministic: same
    inputs => same artifact, including content_hash.

    `participants` are the CHR-* ids the chapter dramatizes. `derived_from` /
    `source_version` are the provenance pins the caller already computed for the
    chapter (so staleness is inherited for free, ADR-006). `outline` is the
    optional NovelOutline artifact; when it lacks an entry for this chapter the
    plan degrades to a single goal-bearing scene (advisory, ADR-003)."""
    entry = _find_outline_entry(outline, chapter_no)
    if entry is not None:
        scenes = _beats_from_outline(entry, participants)
        used_outline_ref = outline_ref or (outline or {}).get("id")
    else:
        scenes = _beats_degraded(goal, participants)
        used_outline_ref = None

    artifact = {
        "artifact_format": "1.0",
        "kind": "scene_plan",
        "chapter_no": chapter_no,
        "task_id": task_id,
        "outline_ref": used_outline_ref,
        "scenes": scenes,
        "provenance": {
            "derived_from": list(derived_from),
            "source_version": source_version,
        },
    }
    # Hash the semantic core only — exclude content_hash itself (set after).
    artifact["content_hash"] = sha256_obj({k: v for k, v in artifact.items()
                                           if k != "content_hash"})
    return artifact


_BEAT_LABELS = {
    BEAT_SETUP: "铺垫",
    BEAT_ESCALATION: "升级",
    BEAT_TURN: "转折",
    BEAT_REWARD: "兑现",
    BEAT_EXIT_HOOK: "钩子",
}


def _emotion_curve(scenes: List[dict]) -> Optional[str]:
    """Render the valence sequence across scenes as a readable curve, e.g.
    '30(紧张) → 55 → 80(爽快)'. None when no scene carries an emotion (a bare
    deterministic skeleton), so the recap stays byte-identical to before
    enrichment existed."""
    points = []
    for s in scenes:
        emo = s.get("emotion")
        if isinstance(emo, dict) and "valence" in emo:
            tone = emo.get("tone")
            points.append(f"{emo['valence']}（{tone}）" if tone else str(emo["valence"]))
    return " → ".join(points) if points else None


def render_scene_plan(artifact: dict) -> str:
    """Compress a scene-plan artifact into a compact string for the prompt's
    scene_plan variable. Deterministic and bounded, mirroring state_digest's
    style. When the plan was LLM-enriched (pov/emotion/beats_within present) the
    recap adds those; a bare skeleton renders exactly as before (non-breaking)."""
    scenes = artifact.get("scenes", [])
    lines: List[str] = ["本章分镜（按顺序推进，逐场景完成其目的）："]
    for scene in scenes:
        label = _BEAT_LABELS.get(scene.get("beat"), scene.get("beat", ""))
        parts = [f"  {scene['index']}. [{label}] {scene.get('purpose', '')}"]
        if scene.get("pov"):
            parts.append(f"视角：{scene['pov']}")
        if scene.get("conflict"):
            parts.append(f"冲突：{scene['conflict']}")
        if scene.get("turn"):
            parts.append(f"转折：{scene['turn']}")
        emo = scene.get("emotion")
        if isinstance(emo, dict) and "valence" in emo:
            tone = emo.get("tone")
            parts.append(f"情绪：{emo['valence']}" + (f"（{tone}）" if tone else ""))
        if scene.get("exit_hook"):
            parts.append(f"钩子：{scene['exit_hook']}")
        lines.append("；".join(parts))
        for b in scene.get("beats_within", []):
            lines.append(f"       - [{b.get('kind')}] {b.get('text')}")
    curve = _emotion_curve(scenes)
    if curve:
        lines.append(f"情绪曲线：{curve}")
    return "\n".join(lines)

