"""Mock multi-agent collaboration for Outline Bootstrap v0.2.

Agent roles are stable architecture, while their implementation is deterministic
for now. Later each role can route to a different LLM adapter without changing
the workflow artifact shape.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

# Genre-keyed pacing default. Shared leaf (see runtime/genre_taxonomy.py) so the
# cadence table has one home instead of a literal per call site.
from ..genre_taxonomy import cadence_for_genre

AgentRole = Literal[
    "StructureAnalyst",
    "TropeAnalyst",
    "OriginalityGuard",
    "WorldBuilder",
    "PlotArchitect",
    "CharacterDesigner",
    "Critic",
    "Synthesizer",
]


@dataclass(frozen=True)
class AgentSpec:
    role: AgentRole
    model: str
    responsibility: str


DEFAULT_AGENTS: list[AgentSpec] = [
    AgentSpec("StructureAnalyst", "mock-structure-v1", "extract reusable narrative structures"),
    AgentSpec("TropeAnalyst", "mock-trope-v1", "identify genre expectations and reader rewards"),
    AgentSpec("OriginalityGuard", "mock-originality-v1", "prevent direct copying and similarity risk"),
    AgentSpec("WorldBuilder", "mock-world-v1", "create an original world premise"),
    AgentSpec("PlotArchitect", "mock-plot-v1", "design main arc, volumes, and turning points"),
    AgentSpec("CharacterDesigner", "mock-character-v1", "design protagonist, rivals, allies, and arcs"),
    AgentSpec("Critic", "mock-critic-v1", "review candidate outlines"),
    AgentSpec("Synthesizer", "mock-synthesizer-v1", "merge the best candidate into final outline"),
]


def agent_manifest() -> list[dict]:
    return [spec.__dict__ for spec in DEFAULT_AGENTS]


# --------------------------------------------------------------------------- #
# Deterministic knowledge tables. These are the fallback "template engine": an  #
# LLM agent later replaces the derivations behind the same return shapes, but   #
# the deterministic path must still produce a COMPLETE, differentiated skeleton #
# so the workflow is provable without network access.                           #
# --------------------------------------------------------------------------- #
_GENRE_POWER_TIERS = {
    "玄幻": ["淬体", "灵动", "通玄", "化神", "登仙"],
    "仙侠": ["炼气", "筑基", "金丹", "元婴", "化神"],
    "科幻": ["义体一级", "神经接驳", "量子跃迁", "群星意识", "维度行者"],
    "都市": ["初入行", "小有名气", "行业新贵", "掌控局面", "定义规则"],
    "悬疑": ["旁观者", "介入者", "揭幕者", "布局者", "终局者"],
    "奇幻": ["学徒", "见习骑士", "符文师", "秘法宗师", "传说执剑者"],
}
_DEFAULT_TIERS = ["起步", "立足", "崭露", "掌局", "问鼎"]


def _primary_genre(merged_analysis: dict) -> str:
    genres = [g for g in merged_analysis.get("genre_signals", []) if g not in ("unknown", "待判定")]
    return genres[0] if genres else "原创类型"


def _tiers_for(genre: str) -> list[str]:
    return _GENRE_POWER_TIERS.get(genre, _DEFAULT_TIERS)


def _order_genre(genre: list, target_genre: str) -> list:
    """Float the human target genre to PRIMARY (position 0) when the chosen
    candidate lists it. The LLM often orders its own genre array with a generic
    label first (["奇幻","玄幻",…]) even for a target-matching book, so the outline
    would read primary=奇幻 despite target_genre=玄幻. Reorder only — no genre is
    added or dropped. Absent target / target not in list => unchanged."""
    if not target_genre or target_genre not in (genre or []):
        return list(genre or [])
    return [target_genre] + [g for g in genre if g != target_genre]


def _tier_name(tier: str) -> str:
    """A power tier's NAME only. Live-authored tiers often carry an inline gloss
    ("醒瞳——能捕捉灵骸残留的情绪波动"); the skeleton builders bind the tier into
    enemy/oppressor/goal labels, so an unstripped gloss produces
    "醒瞳——能捕捉…阶段的小敌人". Split on the first name/gloss separator and keep the
    head; a bare template tier (淬体) passes through. The full gloss stays in
    power_system for the reader-facing setting — only the derived labels use the
    name. Mirrors long_arc.plan._tier_name (same defect, two consumers)."""
    s = str(tier).strip()
    for sep in ("——", "—", "：", ":", "，", ","):
        if sep in s:
            head = s.split(sep, 1)[0].strip()
            if head:
                return head
    return s


def derive_market_position(merged_analysis: dict, market_snapshot: dict | None = None) -> dict:
    """Deterministic commercial positioning.

    When a pinned Market Snapshot is supplied (roadmap P0), the position is
    anchored on REAL market signals (hot genre + reader_promise + drop_points +
    staleness), not just the reference novels. Absent a snapshot it falls back to
    reference-derived heuristics — so the outline pipeline works with or without
    market intelligence. An LLM positioning agent drops in behind the same shape.
    """
    genre = _primary_genre(merged_analysis)
    male_lean = {"玄幻", "仙侠", "科幻", "奇幻"}
    channel = "男频" if genre in male_lean else "女频"
    position = {
        "channel": channel,
        "site_profile": "订阅向长篇连载平台",
        "sub_genre": genre,
        "reader_promise": f"主角凭借独有金手指，在{genre}世界持续突破并兑现即时爽感。",
        "monetization_model": "章节订阅",
        "update_cadence": "日更",
        # Market-anchored (2026-07-17): the advisory length band is target ×
        # (band_low, band_high) = target × (0.6, 1.5) for the default role. 3333
        # makes that band ≈ 2000–5000 chars, which covers 96% of the reference
        # corpus's real chapters (盘龙/奥术起源/法师奥义/魔运苍茫, 3626 chapters:
        # only 1.2% fall below 2000, 3.1% above 5000). The old hardcoded 3000 was
        # NOT market-derived and sat at the low end (band 1800–4500, clipping the
        # 4000–4800 chapters that make up much of 奥术起源). Advisory only — the
        # band never gates (ADR-003); this shifts the aim + observation window,
        # not a hard constraint (a prompt ceiling does not hold — RUN-00023).
        "target_wordcount_per_chapter": 3333,
        "competitor_refs": [f"当前{genre}在榜同类作品(结构对标，不复制专名)"],
    }
    if not market_snapshot:
        return position

    # Anchor on the hottest genre for this channel from the real market read.
    channels = {c.get("channel"): c for c in market_snapshot.get("channels", [])}
    chosen = channels.get(channel) or next(iter(channels.values()), None)
    hot = (chosen or {}).get("hot_genres") or []
    if hot:
        top = hot[0]
        position["sub_genre"] = top.get("genre", genre)
        if top.get("why_hot"):
            position["reader_promise"] = top["why_hot"]
        if top.get("drop_points"):
            # Carry known drop points so downstream QA/first-30 can defend against them.
            position["known_drop_points"] = top["drop_points"]
    trending = market_snapshot.get("signals", {}).get("trending_genres", [])
    if trending:
        position["competitor_refs"] = [f"当前在榜热门题材: {g}(结构对标，不复制专名)" for g in trending[:3]]
    position["market_snapshot_id"] = market_snapshot.get("id")
    position["market_is_stale"] = market_snapshot.get("staleness", {}).get("is_stale")
    return position


def propose_candidates(merged_analysis: dict) -> list[dict]:
    genres = [item for item in merged_analysis.get("genre_signals", []) if item not in ("unknown", "待判定")] or ["原创类型"]
    rewards = merged_analysis.get("reader_rewards", []) or ["curiosity"]
    structures = merged_analysis.get("structure_signals", []) or ["linear-narrative"]
    evidence = merged_analysis.get("narrative_evidence") or {}
    pattern_focus = [
        str(item.get("pattern_type"))
        for item in evidence.get("patterns", [])[:2]
        if isinstance(item, dict) and item.get("pattern_type")
    ]
    evidence_focus = pattern_focus or []
    primary = genres[0]
    tiers = _tiers_for(primary)

    # P0 整改：根据题材选择 fallback，未知题材不静默回退奇幻
    if primary in ["都市", "都市重生"]:
        candidates = _urban_fallback_candidates(genres, tiers, rewards, structures)
    elif primary in ["玄幻", "仙侠"]:
        candidates = _xuanhuan_fallback_candidates(genres, tiers, rewards, structures)
    elif primary in ["科幻"]:
        candidates = _scifi_fallback_candidates(genres, tiers, rewards, structures)
    elif primary in ["奇幻", "原创类型"]:
        # 通用奇幻 fallback（保持向后兼容）
        candidates = _fantasy_fallback_candidates(genres, tiers, rewards, structures)
    else:
        # 未知题材：不静默回退，返回带警告的空候选
        return [{
            "id": "DEGRADED-UNKNOWN-GENRE",
            "degraded_reason": f"unknown_genre:{primary}",
            "genre": genres,
            "title": f"【需要人工确认】未知题材：{primary}",
            "logline": f"系统无法为题材'{primary}'生成确定性候选，需要人工介入。",
            "require_human_confirmation": True,
            "direction": "unknown",
            "design_focus": [],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "待定",
                "flaw": "待定",
                "golden_finger": "待定",
                "cost": "待定",
            },
            "progression_system": {
                "type": "unknown",
                "tiers": [],
                "breakthrough_condition": "待定",
                "hard_limits": [],
            },
        }]

    if evidence_focus:
        candidates[0]["design_focus"].extend(evidence_focus)
        candidates[0]["structure_basis"] = [*structures, *evidence_focus]
        candidates[0]["evidence_pack_id"] = evidence.get("id")
    return candidates


def review_candidate(candidate: dict, merged_analysis: dict) -> dict:
    guardrails = merged_analysis.get("originality_guardrails", [])
    focus = set(candidate.get("design_focus", []))
    risk = "low" if "worldbuilding" in focus or "ensemble-cast" in focus else "medium"
    candidate_originality = None
    evidence = merged_analysis.get("narrative_evidence")
    if isinstance(evidence, dict):
        from ..retrieval.originality import assess_candidate_originality
        candidate_originality = assess_candidate_originality(candidate, evidence)
        risk = max((risk, candidate_originality["risk_level"]), key={"low": 0, "medium": 1, "high": 2}.get)
    return {
        "candidate_id": candidate["id"],
        "critic": "Critic",
        "originality_guard": "OriginalityGuard",
        "score": 8 if risk == "low" else 7,
        "risk_level": risk,
        "strengths": [
            "clear commercial direction",
            "can transform reference-level patterns into an original premise",
        ],
        "concerns": [
            "needs concrete act/volume breakdown",
            "must avoid one-to-one mapping to any reference source",
        ],
        "guardrails": guardrails,
        "evidence_originality": candidate_originality,
    }


def _build_conflict_ladder(power_tiers: list[str]) -> list[dict]:
    """Map power tiers onto an escalating enemy ladder so every stage has a
    concrete pressure source (small enemy -> stage boss -> world-level)."""
    labels = ["小敌人", "阶段boss", "世界级敌人"]
    pressures = [
        "眼前的生存威胁，逼主角用出金手指",
        "掌控一片地图/资源的势力，卡住主角上升通道",
        "维系旧秩序的顶层力量，与主角的终极目标直接对立",
    ]
    ladder = []
    span = max(1, len(power_tiers) // len(labels)) if power_tiers else 1
    for i, (label, pressure) in enumerate(zip(labels, pressures)):
        tier = power_tiers[min(i * span, len(power_tiers) - 1)] if power_tiers else "未定"
        ladder.append({"level": label, "enemy": f"{tier}阶段的{label}", "pressure_source": pressure})
    return ladder


def _build_reward_loop(merged_analysis: dict) -> dict:
    """Reward types are reader-facing semantics (实力突破/打脸翻身/…), NOT the
    analyzer's score labels. merged reader_rewards look like
    'REF-00001:chunk-3: reward_score=5' — a provenance pointer, not a reward
    kind — so we derive semantic reward types from the reward keyword hints and
    genre instead of echoing source ids."""
    genre = _primary_genre(merged_analysis)
    base = ["实力突破", "打脸翻身", "获得资源/宝物", "身份跃升"]
    genre_specific = {
        "悬疑": ["真相揭晓", "反杀布局者"],
        "都市": ["事业翻盘", "打脸权贵"],
        "科幻": ["技术碾压", "夺取核心资源"],
    }
    reward_types = genre_specific.get(genre, []) + base
    # De-dup preserving order, cap at 4 concrete reward kinds.
    seen: list[str] = []
    for r in reward_types:
        if r not in seen:
            seen.append(r)
    # Cadence is genre-keyed for the same reason _GENRE_POWER_TIERS and the
    # reward types above already are: a 王朝争霸 payoff moves a faction (slow), a
    # 都市 payoff moves one person's circumstances (fast). This was hardcoded 3
    # for every genre. Unknown genre degrades to DEFAULT_CADENCE == the old 3.
    return {"cadence_chapters": cadence_for_genre(genre),
            "reward_types": seen[:4]}


def _build_volume_plan(power_tiers: list[str], ladder: list[dict]) -> list[dict]:
    templates = [
        ("VOL-01", "起势", "建立主角、金手指、第一重追杀与核心谜团", "第一处地图/新手区"),
        ("VOL-02", "破局", "扩展势力冲突，第一个大闭环与新地图", "第二处地图/进阶区"),
        ("VOL-03", "问鼎", "主角以代价完成阶段性秩序重建", "第三处地图/高阶区"),
    ]
    volumes = []
    for idx, (vid, title, purpose, default_map) in enumerate(templates):
        oppressor = ladder[min(idx, len(ladder) - 1)]["enemy"] if ladder else "阶段压迫源"
        tier = power_tiers[min(idx * 2, len(power_tiers) - 1)] if power_tiers else "未定"
        volumes.append({
            "id": vid,
            "title": title,
            "purpose": purpose,
            "map": default_map,
            "goal": f"主角在本卷突破至「{tier}」并解决当前压迫源",
            "oppressor": oppressor,
            "twist": f"本卷结尾揭示与{oppressor}相关的一个反转，抬高下一卷目标",
            "settlement": "结算本卷收益，遗留一条跨卷长线谜团",
        })
    return volumes


def _ladder_rung(ladder: list[dict], n: int) -> dict:
    """The conflict-ladder rung this chapter sits on. Chapters 1-10 face the
    small enemy, 11-20 the stage boss, 21-30 the world-level force — so the
    pressure source is CONCRETE per chapter instead of a generic template."""
    if not ladder:
        return {"level": "压迫源", "enemy": "阶段压迫源", "pressure_source": "生存威胁"}
    idx = min((n - 1) // 10, len(ladder) - 1)
    return ladder[idx]


def _build_first_30_chapters(engine: dict, reward_loop: dict,
                             conflict_ladder: list[dict] | None = None) -> list[dict]:
    """Deterministic first-30-chapter skeleton, woven from the ALREADY-AUTHORED
    protagonist engine (desire/flaw/golden_finger/cost) + conflict ladder
    (per-stage enemy/pressure) + reward cadence. An LLM PlotArchitect replaces
    this behind the same shape; the deterministic path stays complete.

    Every beat carries (a) a CONCRETE conflict naming the stage enemy, (b) a
    TIME-PRESSURE anchor so cost_of_delay stops reading `none` (the §14 / 9.6
    温水章 finding), and (c) an escalation SHAPE that varies by structural
    position (ladder transition => new_antagonist, reward cadence => reversal,
    breakthrough beats => power_reveal, else stakes_raise / time_pressure) so the
    tension ladder actually changes shape instead of a uniform '升级'. The mandate
    layer reads these words (mandate.py classifies cost_of_delay / escalation.kind
    off the beat prose), so richer beats fold into richer mandates."""
    gf = engine.get("golden_finger", "金手指")
    desire = (engine.get("desire") or "").strip()
    flaw = (engine.get("flaw") or "").strip()
    cost = (engine.get("cost") or "每次使用都有不可逆代价").strip()
    ladder = conflict_ladder or []
    cadence = reward_loop.get("cadence_chapters", 3)
    reward_types = reward_loop.get("reward_types") or ["阶段性胜利"]

    # Authored turning-point beats (goal, hook). The rest are woven below.
    pivots = {
        1: ("身份落差暴露，金手指在绝境中被逼显性化",
            f"主角在生死一线首次触发「{gf}」，代价（{cost}）随之降临"),
        3: ("抓住对手的破绽完成第一次翻身打脸",
            "打脸成功，却因锋芒毕露引来更强者的注意"),
        10: ("完成第一个小闭环，旧目标达成",
             "旧目标兑现的同一刻，一个更大的势力露出獠牙"),
        20: ("撕开阶段boss布下的困局",
             "boss倒下，却牵出其背后世界级力量的一线阴影"),
        30: ("以代价完成第一个大闭环，逼近核心真相",
             "通往新地图的门被推开，旧规则彻底失效"),
    }

    def _escalation_shape(n: int) -> str:
        # ladder transitions (a new tier of enemy enters the stage)
        if n in (11, 21):
            enemy = _ladder_rung(ladder, n).get("enemy", "更强的敌人")
            return f"新的压迫源登场：{enemy}，冲突层级整体抬高"
        # reward-cadence chapters resolve into a reversal (打脸翻身)
        if n % cadence == 0:
            return "冲突在本章反转，主角实现打脸翻身，赌注较上一章明显抬高"
        # breakthrough beats reveal more of the golden finger's power
        if n in (5, 15, 25):
            return f"主角对「{gf}」的掌控突破一层，力量升级同时代价加深"
        # everything else escalates under a tightening clock
        return "对手进逼、时间收窄，冲突较上一章升级且更难回头"

    def _woven_goal(n: int) -> str:
        # N100-076: a non-pivot chapter's goal was a single repeated line
        # ("逼近「{desire}」的下一步，直面{enemy}"), so consecutive chapters read
        # byte-identical (live preview: 11/30 unique). Vary the goal by the same
        # structural signal _escalation_shape keys on, so what the chapter DOES is
        # legible: a reward-cadence beat cashes in, a ladder transition confronts a
        # new enemy, a breakthrough beat presses the golden finger, else a stake
        # step toward the desire. Deterministic; the pivots table still overrides.
        enemy = _ladder_rung(ladder, n).get("enemy", "阶段压迫源")
        desire_text = desire or "核心目标"
        if n in (11, 21):
            return f"直面新登场的{enemy}，在更高一层的冲突中重新站稳"
        if n % cadence == 0:
            step = n // max(1, cadence)
            return f"完成第 {step} 次阶段翻身，把「{desire_text}」向前推进一格"
        if n in (5, 15, 25):
            return f"逼出「{gf}」的新用法，以加深的代价换取压制{enemy}的手段"
        # default stake-step: anchor on this stage's enemy + pressure, and rotate
        # a within-stage MOVE so consecutive stake chapters in the same ladder rung
        # (same enemy/pressure) still differ instead of repeating one line. The
        # move advances a facet (情报/布局/试探/牵制) — legible, varied, deterministic.
        pressure = _ladder_rung(ladder, n).get("pressure_source", "生存威胁")
        stage_labels = ["情报", "布局", "试探", "牵制"]
        phase = stage_labels[(n + len(desire_text)) % len(stage_labels)]
        move_map = {
            "情报": f"摸清{enemy}的底细，先拿到弱点的第一条线索",
            "布局": f"抢在{enemy}动手前布下应对的局",
            "试探": f"以一次试探逼{enemy}露出破绽",
            "牵制": f"牵制{enemy}，为下一步争取喘息与筹码",
        }
        move = move_map[phase]
        return f"在{pressure}下以{phase}推进：{move}，向「{desire_text}」再逼近一步"

    def _time_anchor(n: int) -> str:
        # rotate concrete time-pressure phrases so cost_of_delay reads high/medium,
        # never none (mandate.py keys on these exact words).
        anchors = [
            "必须在今夜之前动手，否则再无机会",
            "对手的追兵已逼近，来不及等待",
            "限时之内不解决，主角将陷入绝境",
            "拖延一步，代价便落到主角在乎的人身上",
        ]
        return anchors[n % len(anchors)]

    chapters = []
    for n in range(1, 31):
        rung = _ladder_rung(ladder, n)
        enemy = rung.get("enemy", "阶段压迫源")
        pressure = rung.get("pressure_source", "生存威胁")

        goal, hook = pivots.get(n, (_woven_goal(n), None))
        # weave the flaw into the goal on a few beats so the inner axis has fuel
        if flaw and n in (7, 17, 27):
            goal = f"{goal}；同时被自身弱点（{flaw}）反噬"

        conflict = f"主角目标与{enemy}正面碰撞——{pressure}。{_time_anchor(n)}"

        reward = ""
        if n % cadence == 0 or n in (3,):
            reward = reward_types[(n // max(1, cadence)) % len(reward_types)]

        if hook is None:
            hook = (f"第{n}章结尾，{enemy}的反制骤然逼近，抛出新的威胁悬念")

        chapters.append({
            "chapter_no": n,
            "goal": goal,
            "conflict": conflict,
            "escalation": _escalation_shape(n),
            "reward_if_any": reward,
            "end_hook": hook,
        })
    return chapters


def _build_originality_delta(merged_analysis: dict, engine: dict) -> list[dict]:
    return [
        {
            "axis": "金手指机制",
            "reference_pattern": "参考作品的能力获取方式(抽象自分析信号)",
            "our_variation": f"改为带硬代价的机制：{engine.get('cost', '每次使用都有不可逆代价')}",
        },
        {
            "axis": "开局桥段",
            "reference_pattern": "常见的遇袭/落魄开局",
            "our_variation": "打散事件顺序，替换主角动机与因果链，避免一对一复刻",
        },
        {
            "axis": "世界规则",
            "reference_pattern": "参考作品的设定专名",
            "our_variation": "建立全新专名与规则代价，不复用任何参考专有名词",
        },
    ]


def _candidate_world(best: dict) -> dict | None:
    """Prefer the candidate's own authored world (the LLM proposer supplies one;
    deterministic candidates do not). Returns a clean {summary, rules} dict, or
    None to fall back to the hardcoded default. Rules must be a non-empty list of
    non-blank strings, since import_plan folds each into a WorldRule candidate."""
    world = best.get("world")
    if not isinstance(world, dict):
        return None
    summary = str(world.get("summary", "")).strip()
    rules = [str(r).strip() for r in (world.get("rules") or []) if str(r).strip()]
    if not summary or not rules:
        return None
    return {"summary": summary, "rules": rules}


def _candidate_characters(best: dict, engine: dict) -> list[dict] | None:
    """Prefer the candidate's own authored cast. Returns a clean character list
    (role/name/arc/motivation/abilities) with a guaranteed protagonist, or None to
    fall back to the hardcoded trio. Each entry must carry a non-blank name, since
    import_plan mints one Character candidate per entry."""
    chars = best.get("characters")
    if not isinstance(chars, list) or not chars:
        return None
    cleaned: list[dict] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip()
        if not name:
            continue
        role = str(c.get("role", "")).strip() or "ally"
        abilities = c.get("abilities")
        if not isinstance(abilities, list):
            abilities = ([engine.get("golden_finger", "")]
                         if role == "protagonist" and engine.get("golden_finger") else [])
        cleaned.append({
            "role": role,
            "name": name,
            "arc": str(c.get("arc", "")).strip(),
            "motivation": str(c.get("motivation", "")).strip(),
            "abilities": [str(a).strip() for a in abilities if str(a).strip()],
        })
    if not cleaned or not any(c["role"] == "protagonist" for c in cleaned):
        # A cast with no protagonist would leave import_plan without a participant
        # anchor for the chapter events — fall back wholesale to stay complete.
        return None
    return cleaned


def synthesize_final_outline(candidates: list[dict], reviews: list[dict], merged_analysis: dict, project_id: str, references: list[dict], market_snapshot: dict | None = None) -> dict:
    # Candidate selection. On the live path the final genre comes from the CHOSEN
    # candidate's own genre, so a human target-genre preference must bias WHICH
    # candidate wins (else the genre_signals steer is bypassed — a genesis book
    # opened as 都市 despite target_genre=玄幻). Sort by (matches target, score):
    # a target-matching candidate outranks a higher-scored off-genre one; within
    # the same match class the reviewer score still decides. No target => pure
    # score (byte-identical to before).
    target_genre = (merged_analysis.get("target_genre") or "").strip()
    cand_by_id = {c["id"]: c for c in candidates}

    def _matches_target(candidate_id: str) -> int:
        if not target_genre:
            return 0
        genres = cand_by_id.get(candidate_id, {}).get("genre") or []
        return 1 if target_genre in genres else 0

    def _matches_requested_subtype(candidate_id: str) -> int:
        """Prefer the requested urban finance/rebirth lane when broad 都市
        preference also admits mystery or superpower proposals."""
        candidate = cand_by_id.get(candidate_id, {})
        text = " ".join(str(candidate.get(key, "")) for key in
                        ("direction", "title", "logline", "design_focus"))
        return 1 if any(term in text for term in
                        ("金融", "投资", "商战", "资本", "创业", "财富", "股市")) else 0

    eligible_reviews = [item for item in reviews if item.get("risk_level") != "high"]
    selection_pool = eligible_reviews or reviews
    best_review = sorted(
        selection_pool,
        key=lambda item: (_matches_target(item["candidate_id"]),
                          _matches_requested_subtype(item["candidate_id"]),
                          item["score"]),
        reverse=True)[0]
    best = next(candidate for candidate in candidates if candidate["id"] == best_review["candidate_id"])

    market_position = derive_market_position(merged_analysis, market_snapshot)
    engine = best.get("protagonist_engine", {})

    # P0 修复：优先使用 progression_system，回退到 power_system（向后兼容）
    progression = best.get("progression_system")
    if progression:
        # 使用新格式 progression_system
        progression_tiers = progression.get("tiers", [])
        power_system = {
            "tiers": progression_tiers,
            "breakthrough_condition": progression.get("breakthrough_condition", ""),
            "hard_limits": progression.get("hard_limits", []),
        }
    else:
        # 回退到旧格式 power_system
        power_system = best.get("power_system", {})
        progression_tiers = power_system.get("tiers", [])

    # power_system keeps the authored tiers verbatim (reader-facing setting); the
    # SKELETON builders bind names into enemy/oppressor/goal labels, so normalize
    # to tier NAMES here (strip any live-authored inline gloss) at the single point
    # they enter the fold — else "醒瞳——能捕捉…阶段的小敌人" leaks into every label.
    power_tiers = [_tier_name(t) for t in progression_tiers]
    conflict_ladder = _build_conflict_ladder(power_tiers)
    reward_loop = _build_reward_loop(merged_analysis)
    volumes = _build_volume_plan(power_tiers, conflict_ladder)
    # Prefer the candidate's own authored world/cast (the LLM proposer supplies
    # them; deterministic candidates do not) so genesis reviews REAL original
    # names + world rules, not the template defaults. None => keep the defaults.
    authored_world = _candidate_world(best)
    authored_characters = _candidate_characters(best, engine)
    first_30 = _build_first_30_chapters(engine, reward_loop,
                                        conflict_ladder=conflict_ladder)
    originality_delta = _build_originality_delta(merged_analysis, engine)
    provenance = {
        "project_id": project_id,
        "reference_sources": references,
        # Freeze synthesis provenance. The workflow enriches merged_analysis
        # with sibling run artifacts later; sharing it would mutate the outline
        # after a reviewer had already hashed and reviewed that outline.
        "analysis_summary": deepcopy(merged_analysis),
    }
    evidence = merged_analysis.get("narrative_evidence")
    if isinstance(evidence, dict):
        provenance["narrative_evidence_pack"] = {
            "id": evidence.get("id"),
            "pattern_types": [
                item.get("pattern_type")
                for item in evidence.get("patterns", [])
                if isinstance(item, dict) and item.get("pattern_type")
            ],
            "constraint_count": len(evidence.get("constraints", [])),
            "provenance": evidence.get("provenance", {}),
        }

    # Older authored candidates use ``power_system`` for the same progression
    # contract. Preserve a normalized progression_system in the final artifact
    # so downstream consumers do not have to guess which field is authoritative.
    progression_system = best.get("progression_system")
    if not progression_system:
        authored_text = " ".join(str(best.get(key, "")) for key in ("direction", "title", "logline"))
        progression_type = "wealth" if any(
            term in authored_text for term in ("金融", "投资", "商战", "资本", "财富", "商业")
        ) else "influence"
        progression_system = {
            "type": progression_type,
            "tiers": list(power_system.get("tiers", [])),
            "breakthrough_condition": power_system.get("breakthrough_condition", ""),
            "hard_limits": list(power_system.get("hard_limits", [])),
        }

    return {
        "id": "OUTLINE-00001",
        "kind": "novel_outline",
        "schema_version": "0.2",
        "title": best["title"],
        "genre": _order_genre(best.get("genre") or [], target_genre),
        "genre_profile_id": ("都市-v1" if (best.get("genre") and
                              best.get("genre")[0] in ("都市", "都市重生"))
                             else f"{best.get('genre', ['unknown'])[0]}-v1"),
        "genre_contract_version": "1.0",  # P0 整改：契约版本
        "logline": best["logline"],
        "core_hook": best["logline"],
        "themes": ["秩序重建", "个人代价", "被遗忘者的价值"],
        "market_position": market_position,
        "protagonist_engine": engine,
        "power_system": power_system,
        "progression_system": progression_system,  # P0 整改：统一新格式
        "conflict_ladder": conflict_ladder,
        "reward_loop": reward_loop,
        "world": authored_world or {
            "summary": "一个周期性灾变改写资源、记忆与权力结构的原创世界。主角的能力与旧纪元真相绑定，但每次使用都会改变现实记录。",
            "rules": [
                "灾变周期改变势力版图，但不复用参考作品专有设定",
                "历史记录本身是可争夺资源",
                "力量成长必须伴随记忆、关系或身份代价",
            ],
        },
        "characters": authored_characters or [
            {"role": "protagonist", "name": "林照夜", "arc": "从求生者到秩序重建者",
             "motivation": engine.get("desire", ""),
             "abilities": [engine.get("golden_finger", "")] if engine.get("golden_finger") else []},
            {"role": "rival", "name": "沈无咎", "arc": "从秩序维护者到真相叛逃者",
             "motivation": "维护旧秩序，视主角为最大变量", "abilities": []},
            {"role": "mentor", "name": "白砚", "arc": "守秘者面对旧错",
             "motivation": "赎清一段被自己掩盖的旧纪元真相", "abilities": []},
        ],
        "plot": {
            "main_arc": best["logline"],
            "volumes": volumes,
            "chapters": [],
        },
        "first_30_chapters": first_30,
        "originality_delta": originality_delta,
        "collaboration": {
            "agents": agent_manifest(),
            "selected_candidate": best["id"],
            "reviews": reviews,
        },
        "originality_report": {
            "risk_level": best_review["risk_level"],
            "notes": best_review["guardrails"],
            "evidence": [
                {"axis": item["axis"], "our_variation": item["our_variation"]}
                for item in originality_delta
            ],
            "corpus_evidence": best_review.get("evidence_originality"),
            "high_risk_candidates_excluded": [
                item["candidate_id"] for item in reviews if item.get("risk_level") == "high"
            ],
            "comparison_only": True,
            "legal_conclusion": False,
        },
        "provenance": provenance,
    }


def _urban_fallback_candidates(genres, tiers, rewards, structures):
    """都市题材确定性兜底模板"""
    return [
        {
            "id": "CANDIDATE-A",
            "direction": "都市重生创业线",
            "title": "重生之金融帝国",
            "genre": genres,
            "logline": "35岁破产者重生回18岁，利用前世记忆在股市和互联网创业浪潮中翻身，成为商业传奇。",
            "design_focus": ["fast-opening-hook", "wealth-progression", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "在商业世界证明自己，改写前世失败命运",
                "flaw": "过度自信，容易忽视人际关系",
                "golden_finger": "前世17年完整记忆，知道所有商机和危机",
                "cost": "改变历史轨迹可能导致蝴蝶效应，熟悉的人和事发生变化",
            },
            "world": {
                "summary": "2013-2023年中国金融市场与互联网创业浪潮中的真实都市商业环境",
                "rules": [
                    "股市涨跌受政策、资金、情绪多重影响，没有百分百准确的预测",
                    "资本运作必须合法合规，操纵市场和内幕交易会受到严厉处罚",
                    "商业竞争遵循实力、资源、时机的综合博弈，单靠信息差无法持续获胜",
                ],
            },
            "characters": [
                {
                    "role": "protagonist",
                    "name": "陈默",
                    "arc": "从被背叛的破产者成长为克制、守法的资本操盘者，学会在复仇与守护之间取舍",
                    "motivation": "利用前世经验修复家人和事业，查清合伙人背叛的真相",
                },
                {
                    "role": "rival",
                    "name": "周江",
                    "arc": "从导师和合伙人变成资本竞争对手，最终为自己的违规扩张承担代价",
                    "motivation": "维持金融圈话语权并吞并主角的创业项目",
                },
                {
                    "role": "ally",
                    "name": "苏晴",
                    "arc": "从财经记者成长为投资伙伴，用独立调查和媒体资源约束资本滥用",
                    "motivation": "揭露金融黑幕并建立可信的商业判断",
                },
                {
                    "role": "mentor",
                    "name": "林志远",
                    "arc": "用风控和行业经验帮助主角从信息优势转向长期经营",
                    "motivation": "培养守住合规底线的新一代投资人",
                },
            ],
            "progression_system": {  # P0 整改：生成新格式
                "type": "wealth",
                "tiers": [
                    "实习生月入三千",
                    "操盘手年入百万",
                    "私募基金经理管理十亿资金",
                    "投资公司合伙人掌控百亿资本",
                    "金融大鳄影响行业格局",
                ],
                "breakthrough_condition": "完成一个重大商业项目或投资",
                "hard_limits": ["不能违反物理规律", "不能预知所有细节", "人心难测"],
            },
        },
        {
            "id": "CANDIDATE-B",
            "direction": "都市系统爽文线",
            "title": "神豪从签到开始",
            "genre": genres,
            "logline": "普通大学生获得神豪系统，每天签到获得巨额资金和任务奖励，在都市中开启开挂人生。",
            "design_focus": ["fast-paced", "wealth-progression", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "享受财富带来的生活，证明自己不是废物",
                "flaw": "依赖系统，缺乏自主性",
                "golden_finger": "神豪系统，完成任务获得金钱和技能奖励",
                "cost": "必须完成系统任务，否则会受惩罚",
            },
            "progression_system": {  # P0 整改：生成新格式
                "type": "wealth",
                "tiers": tiers or ["贫困", "温饱", "小康", "富裕", "富豪"],
                "breakthrough_condition": "完成系统主线任务，提升系统等级",
                "hard_limits": ["不能直接操控他人意志", "财富需要合理解释来源", "系统任务必须完成"],
            },
        },
        {
            "id": "CANDIDATE-C",
            "direction": "都市职场奋斗线",
            "title": "从实习生到总裁",
            "genre": genres,
            "logline": "名牌大学毕业生进入顶级投行实习，凭借过人才华和商业头脑，在职场上一路晋升。",
            "design_focus": ["career-growth", "workplace-conflict", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "在职场上获得认可，实现财富自由",
                "flaw": "工作狂，忽视个人生活",
                "golden_finger": "超强分析能力和商业嗅觉",
                "cost": "高强度工作压力，牺牲个人时间",
            },
            "progression_system": {  # P0 整改：生成新格式
                "type": "wealth",
                "tiers": tiers or ["实习生", "职员", "主管", "经理", "总裁"],
                "breakthrough_condition": "完成重大项目，获得晋升机会",
                "hard_limits": ["职场规则限制", "需要真实业绩支撑", "人际关系复杂"],
            },
        },
    ]


def _fantasy_fallback_candidates(genres, tiers, rewards, structures):
    """奇幻题材确定性兜底模板（保持原有逻辑）"""
    return [
        {
            "id": "CANDIDATE-A",
            "direction": "商业强钩子升级线",
            "title": "灰烬纪元的执灯人",
            "genre": genres,
            "logline": f"废城少年在一次禁忌灾变中觉醒记录旧纪元真相的能力，被迫在{genres[0]}势力追杀间重建失落秩序。",
            "design_focus": ["fast-opening-hook", "progression", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "在崩坏的世界重建属于自己的秩序与归属",
                "flaw": "背负旧纪元罪名，不敢信任他人",
                "golden_finger": "能读取并短暂重演任何遗物承载的历史片段",
                "cost": "每次重演都会抹去主角自身一段真实记忆",
            },
            "power_system": {
                "tiers": tiers,
                "breakthrough_condition": "解锁一段完整的旧纪元真相",
                "hard_limits": ["记忆是有限资源", "重演过的历史无法二次读取"],
            },
        },
        {
            "id": "CANDIDATE-B",
            "direction": "群像势力博弈线",
            "title": "群星下的无名王座",
            "genre": genres,
            "logline": "五个彼此敌对的年轻人同时继承一份破碎预言，必须在旧神复苏前决定谁有资格改写世界规则。",
            "design_focus": ["ensemble-cast", "political-conflict", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "从棋子成为唯一有资格改写规则的人",
                "flaw": "出身最低，被所有继承者轻视",
                "golden_finger": "唯一能同时调用五份预言残片的人",
                "cost": "每调用一次，就与一名继承者结下不可逆的死敌",
            },
            "power_system": {
                "tiers": tiers,
                "breakthrough_condition": "夺取或说服一名继承者交出预言残片",
                "hard_limits": ["残片总数固定为五", "结仇不可撤销"],
            },
        },
        {
            "id": "CANDIDATE-C",
            "direction": "设定驱动探索线",
            "title": "第九座天穹图书馆",
            "genre": genres,
            "logline": "一个会吞噬历史的天穹图书馆降临人间，主角必须用被遗忘者的故事修补现实裂缝。",
            "design_focus": ["mystery", "worldbuilding", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "找回被图书馆吞噬的至亲记忆",
                "flaw": "过度执着于过去，逃避当下",
                "golden_finger": "能进入被遗忘者的故事并带出一件关键物证",
                "cost": "每带出一物，现实中就有一个人被世界遗忘",
            },
            "power_system": {
                "tiers": tiers,
                "breakthrough_condition": "修补一道现实裂缝",
                "hard_limits": ["遗忘不可逆", "同一个故事只能进入一次"],
            },
        },
    ]


def _xuanhuan_fallback_candidates(genres, tiers, rewards, structures):
    """玄幻题材确定性兜底模板"""
    return [
        {
            "id": "CANDIDATE-A",
            "direction": "玄幻升级流",
            "title": "九天神帝",
            "genre": genres,
            "logline": "少年意外获得上古神帝传承，从小镇少年逆袭成为主宰九天的至尊强者。",
            "design_focus": ["fast-opening-hook", "progression", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "成为至强者，守护亲人",
                "flaw": "天赋平庸，被家族轻视",
                "golden_finger": "上古神帝传承，拥有逆天修炼功法",
                "cost": "修炼过程痛苦，需要不断突破生死关",
            },
            "progression_system": {  # P0 整改：生成新格式
                "type": "power",
                "tiers": tiers or ["炼气", "筑基", "金丹", "元婴", "化神"],
                "breakthrough_condition": "突破境界瓶颈，需要天材地宝或生死磨砺",
                "hard_limits": ["修炼需要资源", "境界突破有失败风险", "寿命有限"],
            },
        },
    ]


def _scifi_fallback_candidates(genres, tiers, rewards, structures):
    """科幻题材确定性兜底模板"""
    return [
        {
            "id": "CANDIDATE-A",
            "direction": "星际探索线",
            "title": "星河之主",
            "genre": genres,
            "logline": "地球舰长意外发现远古文明遗迹，获得超光速技术，开启人类文明的星际时代。",
            "design_focus": ["exploration", "technology-tree", *rewards[:2]],
            "structure_basis": structures,
            "protagonist_engine": {
                "desire": "带领人类走向星辰大海",
                "flaw": "过于理想主义，忽视现实利益斗争",
                "golden_finger": "远古科技知识库，可以逐步解锁高级科技",
                "cost": "技术泄露会引来其他文明觊觎",
            },
            "progression_system": {  # P0 整改：生成新格式
                "type": "tech",
                "tiers": tiers or ["行星文明", "恒星文明", "星系文明", "星团文明", "宇宙文明"],
                "breakthrough_condition": "解锁新科技等级，扩展势力范围",
                "hard_limits": ["科技发展需要资源和时间", "物理法则限制", "文明冲突不可避免"],
            },
        },
    ]
