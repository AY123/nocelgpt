"""generate.py — fold a Market Position draft from an outline (ANES v2, M2-B3).

The Market Position is an AUTHORED commercial thesis the strategist normally writes
by hand (sources/market-position.yaml). Genesis proposes a DETERMINISTIC first draft
folded from the outline the bootstrap already produced, so a freshly-opened book has
a positioning to run the pre-book ADMISSION check against — closing the
参考→开书→市场准入 chain (previously genesis folded a Brain but no Position, so
`project_admission` always degraded to 'hold: no positioning authored').

DISCIPLINE (mirrors brain_gen.py exactly):
  - Deterministic: same outline => same Position draft. No model, no API.
  - AUTHORED source, not a fact (ADR-006) or a projection (ADR-008): writes to
    sources/, validated against the frozen market-position schema before write.
  - Never clobbers a hand-authored Position unless overwrite=True (the human wins).
  - Advisory only — authoring/validating it never gates (ADR-003).

An LLM refinement pass can drop in later behind the same shape (like the Speech
Profile / Brain staged path); v1 is the deterministic fold.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from .loader import position_path, validate_position
# One home for genre→channel routing. Sharing the leaf with brain_gen is what
# guarantees a folded Brain + Position can never disagree on channel (a
# disagreement would surface as a false admission conflict); the two used to
# hold hand-synced literal sets that were both missing 武侠/都市/历史/游戏 and
# every 二级分类 name.
from ..genre_taxonomy import resolve_channel
from ..progression import normalize_progression_dict


def _first(seq, default=""):
    return seq[0] if isinstance(seq, list) and seq else default


def build_position(outline: dict, *, position_id: str = "MPOS-00001",
                   version: str = "0.1") -> dict:
    """Fold an outline into a schema-valid MarketPosition dict. Deterministic.

    Field map (every value comes from an outline the bootstrap produced):
      channel            <- market_position.channel (or genre-based default)
      reader_segment     <- channel + genre + reward_types (pull) + drop_points
      trope_map.leans_on <- reward_types restated as leaned-on commercial levers
      trope_map.subverts <- originality_delta.our_variation (the differentiators)
      commercial_promise <- reward_loop / core_hook / power-and-conflict long arc
    """
    mp = outline.get("market_position", {}) or {}
    reward_loop = outline.get("reward_loop", {}) or {}
    genre_list = outline.get("genre") or []
    primary_genre = _first(genre_list, mp.get("sub_genre", "原创类型"))
    channel = resolve_channel(mp.get("channel"), primary_genre)

    reward_types = list(reward_loop.get("reward_types") or [])
    cadence = reward_loop.get("cadence_chapters")
    drop_points = list(mp.get("known_drop_points") or [])
    logline = (outline.get("core_hook") or outline.get("logline") or "").strip()

    # --- reader_segment (required: primary) ---
    reader_segment = {
        "primary": f"追爽的{channel}{primary_genre}核心读者",
    }
    if reward_types:
        reader_segment["pull_triggers"] = reward_types[:4]
    if drop_points:
        reader_segment["drop_triggers"] = drop_points

    # --- trope_map (required: leans_on, minItems 1) ---
    # Lean on the reward levers the outline already commits to; if the outline is
    # bare, fall back to a genre-anchored comfort trope so leans_on is never empty.
    leans_on = list(dict.fromkeys(reward_types)) or [f"{primary_genre}套路化爽点"]
    subverts: List[str] = []
    for d in outline.get("originality_delta", []) or []:
        var = (d.get("our_variation") or "").strip()
        if var:
            subverts.append(var)
    trope_map: dict = {"leans_on": leans_on}
    if subverts:
        trope_map["subverts"] = subverts
    differentiation = _first(subverts) or logline
    if differentiation:
        trope_map["differentiation"] = differentiation

    # --- commercial_promise (required: pay_trigger, first_30_hook, sustainability_100) ---
    pay_trigger = (mp.get("reader_promise")
                   or (f"每{cadence}章兑现一次爽点，付费点落在奖励回环的兑现节点"
                       if cadence else "")
                   or "在关键爽点兑现处设置付费点").strip()
    first_30_hook = (logline
                     or "开局即抛出强钩子与身份/实力反差，30 章内持续兑现追读动力").strip()
    # the long-arc engine that prevents 后劲不足: prefer the authored power/conflict
    # spine, then the reward cadence, then a safe default.
    # Support both old "power_system" and new "progression_system" with type field
    progression = outline.get("progression_system") or outline.get("power_system") or {}
    if progression and "type" not in progression:
        # Normalize old format to new format
        from ..progression import normalize_progression_dict
        progression = normalize_progression_dict(progression, genre=primary_genre)

    conflict = outline.get("conflict_ladder") or {}
    if progression or conflict:
        # Use appropriate terminology based on progression type
        prog_type = progression.get("type", "power") if progression else "power"
        if prog_type == "wealth":
            sustainability = "以财富升级与商业冲突为长线引擎，百章仍有明确的资产/地位推进空间"
        elif prog_type == "tech":
            sustainability = "以科技升级与文明冲突为长线引擎，百章仍有明确的科技/势力推进空间"
        elif prog_type == "influence":
            sustainability = "以权力升级与政治冲突为长线引擎，百章仍有明确的影响力/势力推进空间"
        else:
            sustainability = "以升级线与冲突阶梯为长线引擎，百章仍有明确的实力/势力推进空间"
    elif cadence:
        sustainability = f"以每{cadence}章的奖励回环维持百章追读节奏"
    else:
        sustainability = "以主线悬念与主角成长弧维持百章追读动力"

    commercial_promise = {
        "pay_trigger": pay_trigger,
        "first_30_hook": first_30_hook,
        "sustainability_100": sustainability,
    }
    comparables = list(mp.get("competitor_refs") or [])
    if comparables:
        commercial_promise["comparables"] = comparables

    return {
        "id": position_id,
        "kind": "market_position",
        "version": version,
        "channel": channel,
        "reader_segment": reader_segment,
        "trope_map": trope_map,
        "commercial_promise": commercial_promise,
    }


def position_yaml(position: dict) -> str:
    """Serialize a Position dict to the YAML the strategist edits."""
    return yaml.safe_dump(position, allow_unicode=True, sort_keys=False)


def write_position(project_path: str | Path, position: dict, *,
                   standard_root: Optional[str | Path] = None,
                   overwrite: bool = False) -> Path:
    """Write the folded Position to sources/market-position.yaml. Validates against
    the frozen schema first — a Genesis that would write an invalid Position refuses
    instead. Never clobbers an authored Position unless overwrite=True."""
    errs = validate_position(position, standard_root=standard_root)
    if errs:
        raise ValueError("folded Position failed schema validation: " + "; ".join(errs))
    path = position_path(project_path)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"a Market Position already exists at {path}; pass overwrite=True to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(position_yaml(position), encoding="utf-8")
    return path
