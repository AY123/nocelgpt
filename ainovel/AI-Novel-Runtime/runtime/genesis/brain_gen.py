"""brain_gen.py — fold a Novel Brain draft from an outline (ANES v2, Genesis / M2).

The Novel Brain is an AUTHORED source the author normally writes by hand. Genesis
proposes a DETERMINISTIC first draft folded from the outline the bootstrap already
produced (mission/genre/target_reader/promise/writing_style/forbidden_style), so a
freshly-opened book has a Brain to start from. Deterministic: same outline => same
Brain draft. The author confirms/edits it (ADR-009 — Genesis prepares, the human
authorizes); `brain check` validates it against the Standard schema.

An LLM refinement pass can drop in later behind the same shape (like the Speech
Profile's staged path); v1 is the deterministic fold — no model, no API.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

# Reuse the loader's canonical path + validator so a folded Brain lands exactly
# where `brain check` reads it and is checked against the same schema.
from ..brain.loader import brain_path, validate_brain
# Shared with positioning/generate.py so a folded Brain and Position can never
# disagree on channel. See runtime/genre_taxonomy.py for why the old hand-synced
# literal set misrouted 武侠/都市/历史/游戏 and every 二级分类 name to 女频.
from ..genre_taxonomy import resolve_channel


def _first(seq, default=""):
    return seq[0] if isinstance(seq, list) and seq else default


def build_brain(outline: dict, *, brain_id: str = "BRAIN-00001",
                version: str = "0.1") -> dict:
    """Fold an outline into a schema-valid NovelBrain dict. Deterministic.

    Every field maps from an outline the bootstrap produced:
      mission        <- core_hook / logline (the one-sentence reason to exist)
      genre          <- genre[0] + market_position.channel
      target_reader  <- market_position (who/wants/avoids from reward_types + drop_points)
      promise        <- market_position.reader_promise / reward cadence
      writing_style  <- market_position pacing + a genre-appropriate voice
      forbidden_style<- originality_delta variations restated as anti-patterns +
                        known_drop_points, plus the universal 注水/上帝视角 rules
    """
    mp = outline.get("market_position", {}) or {}
    reward_loop = outline.get("reward_loop", {}) or {}
    genre_list = outline.get("genre") or []
    primary_genre = _first(genre_list, mp.get("sub_genre", "原创类型"))
    channel = resolve_channel(mp.get("channel"), primary_genre)

    logline = (outline.get("core_hook") or outline.get("logline") or "").strip()
    mission = logline or f"写一本让{channel}读者持续追读的{primary_genre}长篇。"

    reward_types = reward_loop.get("reward_types") or []
    cadence = reward_loop.get("cadence_chapters")
    promise = (mp.get("reader_promise")
               or (f"每{cadence}章兑现一次爽点" if cadence else "")
               or "持续兑现即时爽感与追读动力").strip()

    wants: List[str] = list(reward_types[:4])
    avoids: List[str] = list(mp.get("known_drop_points") or [])
    evidence = (outline.get("provenance", {}).get("analysis_summary", {}).get("narrative_evidence") or {})
    if evidence:
        pattern_effects = [
            effect
            for pattern in evidence.get("patterns", [])
            if isinstance(pattern, dict)
            for effect in pattern.get("effects", [])
        ]
        anti_risks = [
            risk
            for pattern in evidence.get("anti_patterns", [])
            if isinstance(pattern, dict)
            for risk in pattern.get("risk", [])
        ]
        wants = list(dict.fromkeys([*wants, *pattern_effects]))[:6]
        avoids = list(dict.fromkeys([*avoids, *anti_risks]))[:6]

    # forbidden_style: restate the originality deltas as "don't copy" anti-patterns,
    # fold in any known drop points, and always include the universal web-novel
    # anti-patterns. Schema requires >=1; this is never empty.
    forbidden: List[str] = []
    for d in outline.get("originality_delta", []) or []:
        ref = (d.get("reference_pattern") or "").strip()
        if ref:
            forbidden.append(f"不复刻参考套路：{ref}")
    forbidden.extend(f"规避掉读点：{p}" for p in avoids)
    forbidden.extend(
        f"语料证据约束：{item}"
        for item in evidence.get("constraints", [])
        if isinstance(item, str) and item.strip()
    )
    forbidden.extend(["注水（无信息量的氛围铺陈）", "上帝视角剧透", "主角长期龟缩不作为"])
    # de-dup, keep order
    forbidden = list(dict.fromkeys(forbidden))

    voice = f"服务{primary_genre}爽感的第三人称限知，克制不注水"
    writing_style = {
        "voice": voice,
        "pov": "第三人称限知",
        "pacing": "快节奏，章末留钩",
    }
    devices = []
    if cadence:
        devices.append(f"每{cadence}章一个奖励回环")
    devices.append("章末悬念钩子")
    writing_style["devices"] = devices

    brain = {
        "id": brain_id,
        "kind": "novel_brain",
        "version": version,
        "mission": mission,
        "genre": _prune({
            "primary": primary_genre,
            "secondary": [g for g in genre_list[1:]] or None,
            "channel": channel,
        }),
        "target_reader": _prune({
            "who": f"{channel}{primary_genre}核心读者",
            "wants": wants or None,
            "avoids": avoids or None,
        }),
        "promise": promise,
        "writing_style": writing_style,
        "forbidden_style": forbidden,
    }
    # optional commercial_position from the outline's market read
    hook = outline.get("core_hook") or outline.get("logline")
    if hook or mp.get("monetization_model"):
        brain["commercial_position"] = _prune({
            "hook": hook,
            "monetization": mp.get("monetization_model"),
        })
    return brain


def _prune(d: dict) -> dict:
    """Drop keys whose value is None/empty so the folded Brain carries only the
    fields it actually has (schema optionals stay absent, not null)."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


def brain_yaml(brain: dict) -> str:
    """Serialize a Brain dict to the YAML the author edits (stable, unicode)."""
    return yaml.safe_dump(brain, allow_unicode=True, sort_keys=False)


def write_brain(project_path: str | Path, brain: dict, *,
                standard_root: Optional[str | Path] = None,
                overwrite: bool = False) -> Path:
    """Write the folded Brain to sources/novel-brain.yaml (where `brain check`
    reads it). Validates against the Standard schema first — a Genesis that would
    write an invalid Brain refuses instead. Never clobbers an authored Brain
    unless overwrite=True (the author's hand-edits win)."""
    errs = validate_brain(brain, standard_root=standard_root)
    if errs:
        raise ValueError("folded Brain failed schema validation: " + "; ".join(errs))
    path = brain_path(project_path)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"a Brain already exists at {path}; pass overwrite=True to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_yaml(brain), encoding="utf-8")
    return path
