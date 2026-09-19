"""llm_planner.py — LLM scene-plan ENRICHMENT (ANES v2, ADR-003).

`LLMScenePlanner.enrich` takes a deterministic scene-plan skeleton (plan_scenes)
and fills, per scene, the qualitative detail a one-line beat can't carry: the POV
character, an emotion target (valence + tone), and 2-4 within-scene micro-beats.

DISCIPLINE — enrich, never replace:
  - The deterministic skeleton is the CONTRACT. The LLM may only ADD detail
    inside it; it may NOT change the scene count, a scene's beat, or its
    participants. Any scene whose enrichment fails structural validation keeps
    its skeleton form (per-scene degrade). If the model call fails entirely, the
    whole plan degrades to the skeleton (ADR-003: advisory, never gates).
  - Reuses the seam pattern of LLMReaderSimulator / LLMQualityJudge: depends only
    on the execution Model protocol, so a fake model proves the parse/validate
    logic in CI without network; a real provider drops in unchanged.
  - Preserves reproducibility discipline: the enriched artifact's content_hash is
    recomputed over its new semantic core.
"""
from __future__ import annotations

from typing import List, Optional

from ..llm.types import sha256_obj
from ..execution.quality_center import _extract_json, _clamp_score

_MICRO_KINDS = {"action", "dialogue", "interior", "description"}


_ENRICH_TEMPLATE = """# 角色
你是一名资深网文责编，为一章的分镜骨架补充导演级细节。你不改变结构，只在每个既定
场景内部填充：视角、情绪、以及场景内的微节拍。

# 本章分镜骨架（顺序与场景数固定，不可增删、不可改动 beat 与出场角色）
{skeleton}

# 出场角色（只能从中选 POV）
{participants}
{psych}
# 任务
为上面每一个场景补充：
  - pov：该场景用哪个角色的视角来写（从出场角色里选一个 CHR 编号；无合适则留空）
  - emotion.valence：0-100 的情绪强度（0=最压抑/低谷，100=最高昂/爽点顶点）
  - emotion.tone：一个简短基调词（如 压抑/紧张/爽快/温情）
  - beats_within：2-4 个场景内微节拍，每个含 kind(action/dialogue/interior/description) 与 text
整章的 valence 序列应形成有起伏的情绪曲线，服务节奏，不要全程一个水平。
{psych_instruction}

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown 代码块：
{{
  "scenes": [
    {{"index": 场景序号(与骨架一致), "pov": "CHR-xxxxx 或空",
      "emotion": {{"valence": 0-100, "tone": "基调词"}},
      "beats_within": [{{"kind": "action", "text": "……"}}]}}
  ]
}}

# 失败兜底
无法处理时输出 {{"scenes": []}}，系统会保留骨架原样。"""


_PSYCH_INSTRUCTION = (
    "\n# 人物内在状态的落地（重要）\n"
    "上面给出了主要角色进入本章时的内在状态（情绪/信念/价值取向/决策倾向）。不要把它"
    "当作背景描述，而要把它转化为该 POV 角色在 beats_within 里的具体、可观察的行动与选择：\n"
    "  - 让 interior 微节拍显影其信念/恐惧如何在此刻被触动；\n"
    "  - 让紧随其后的 action/dialogue 微节拍，体现其决策倾向真正驱动了一个动作或选择"
    "（趋于回避 or 迎难而上，要在行为上看得见）。\n"
    "目标：读者从角色做了什么、怎么选，就能感到这个人的性格与变化，而不是被告知。"
)


def build_enrich_prompt(base_plan: dict, psych: str = "") -> str:
    """Render the skeleton into the enrichment prompt. The skeleton lines are the
    contract the model must fill within, not rewrite.

    `psych` (optional) is a rendered character-runtime psych block. When supplied
    (the psych-beats arm), the prompt additionally instructs the model to convert
    each lead's STANDING inner state into concrete in-scene ACTIONS/choices inside
    beats_within — the hypothesis under test (a beat instructs the action a state
    causes, which the judge reads, vs a static block that merely describes state).
    Absent (the generic arm), both new slots render empty => byte-identical prompt."""
    lines = []
    all_participants: set = set()
    for s in base_plan.get("scenes", []):
        parts = s.get("participants", []) or []
        all_participants.update(parts)
        lines.append(
            f"  场景{s['index']}（beat={s.get('beat')}，出场={','.join(parts) or '无'}）："
            f"{s.get('purpose', '')}")
    psych = (psych or "").strip()
    return _ENRICH_TEMPLATE.format(
        skeleton="\n".join(lines) or "（无场景）",
        participants="、".join(sorted(all_participants)) or "（无）",
        psych=(f"\n# 主要角色进入本章时的内在状态\n{psych}\n" if psych else ""),
        psych_instruction=(_PSYCH_INSTRUCTION if psych else ""),
    )



def _valid_pov(pov, allowed: set) -> Optional[str]:
    """A POV is accepted only if it names a character actually on stage in the
    scene (skeleton participants). Anything else is dropped — the LLM cannot
    introduce a character the deterministic plan didn't place there."""
    if isinstance(pov, str) and pov in allowed:
        return pov
    return None


def _valid_emotion(emotion) -> Optional[dict]:
    if not isinstance(emotion, dict) or "valence" not in emotion:
        return None
    out = {"valence": _clamp_score(emotion.get("valence", 0))}
    tone = emotion.get("tone")
    if isinstance(tone, str) and tone.strip():
        out["tone"] = tone.strip()
    return out


def _valid_beats(beats) -> List[dict]:
    """Keep only well-formed micro-beats (known kind + non-empty text), capped at
    4 so the shot list stays bounded."""
    if not isinstance(beats, list):
        return []
    out = []
    for b in beats:
        if not isinstance(b, dict):
            continue
        kind, text = b.get("kind"), b.get("text")
        if kind in _MICRO_KINDS and isinstance(text, str) and text.strip():
            out.append({"kind": kind, "text": text.strip()})
        if len(out) >= 4:
            break
    return out


def _apply_enrichment(scene: dict, patch: dict) -> dict:
    """Merge a validated enrichment patch INTO a skeleton scene, without touching
    its structural fields (index/beat/purpose/participants/conflict/turn/
    exit_hook). Returns a new dict; the skeleton scene is never mutated."""
    enriched = dict(scene)
    allowed = set(scene.get("participants", []) or [])
    pov = _valid_pov(patch.get("pov"), allowed)
    if pov:
        enriched["pov"] = pov
    emotion = _valid_emotion(patch.get("emotion"))
    if emotion:
        enriched["emotion"] = emotion
    beats = _valid_beats(patch.get("beats_within"))
    if beats:
        enriched["beats_within"] = beats
    return enriched



class LLMScenePlanner:
    """Enriches a deterministic scene-plan skeleton with LLM-authored detail,
    inside the skeleton's structural contract. Depends only on the execution
    Model protocol (model.generate(prompt) -> obj with .text/.model_id)."""

    def __init__(self, model, *, reviewer_id: str = "scene-planner-v1"):
        self.model = model
        self.reviewer_id = reviewer_id

    def enrich(self, base_plan: dict, psych: str = "") -> dict:
        """Return a NEW scene-plan artifact with per-scene enrichment merged in.
        The skeleton is never mutated. On any model failure the plan degrades to
        the skeleton unchanged (advisory, never gates). The enriched artifact
        carries an `enrichment` provenance block and a recomputed content_hash.

        `psych` (optional) is a rendered character-runtime psych block; when given
        the enrich prompt asks the model to land each lead's standing inner state
        as concrete in-scene actions inside beats_within (the psych-beats arm).
        Absent => the generic enrichment, byte-identical to before."""
        model_id = getattr(self.model, "model_id", "")
        scenes = base_plan.get("scenes", [])

        patches_by_index = {}
        degraded = False
        try:
            output = self.model.generate(build_enrich_prompt(base_plan, psych=psych))
            model_id = getattr(output, "model_id", model_id)
            parsed = _extract_json(getattr(output, "text", "")) or {}
            for p in parsed.get("scenes", []):
                if isinstance(p, dict) and isinstance(p.get("index"), int):
                    patches_by_index[p["index"]] = p
            if not patches_by_index:
                degraded = True
        except Exception:
            degraded = True

        enriched_scenes = []
        enriched_count = 0
        for scene in scenes:
            patch = patches_by_index.get(scene.get("index"))
            if patch:
                new_scene = _apply_enrichment(scene, patch)
                if new_scene != scene:
                    enriched_count += 1
                enriched_scenes.append(new_scene)
            else:
                enriched_scenes.append(dict(scene))

        artifact = {k: v for k, v in base_plan.items()
                    if k not in ("scenes", "content_hash", "enrichment")}
        artifact["scenes"] = enriched_scenes
        artifact["enrichment"] = {
            "reviewer": self.reviewer_id,
            "model_id": model_id,
            "degraded": degraded,
            "scenes_enriched": enriched_count,
            "psych_beats": bool((psych or "").strip()),  # which arm produced this
            "axis": "evaluative",   # structural invariant — enrichment never gates
            "gating": False,
        }
        artifact["content_hash"] = sha256_obj({k: v for k, v in artifact.items()
                                               if k != "content_hash"})
        return artifact


def llm_scene_planner(model, **kwargs) -> LLMScenePlanner:
    return LLMScenePlanner(model, **kwargs)
