"""Deterministic market-observation analysis for Market Intelligence (P0).

Keyword/heuristic extraction gives the subdomain a non-network, reproducible
analysis stage. A later LLM market analyst replaces the heuristics behind the
same shapes (mirrors runtime.outline.analyzer). It extracts, per channel, which
genres are hot and — crucially — WHY, plus where readers drop, from the dated
observation text a project supplies.
"""
from __future__ import annotations

from dataclasses import dataclass

from .sources import MarketObservation, iter_observation_texts

# Channel routing by genre keyword. Deterministic and auditable.
MALE_GENRES = {
    "无限流": ["无限流", "副本", "轮回", "求生"],
    "幕后流": ["幕后", "布局", "隐藏", "操控"],
    "领主流": ["领主", "建城", "领地", "经营"],
    "修仙": ["修仙", "修真", "灵气", "渡劫", "境界"],
    "克苏鲁": ["克苏鲁", "旧日", "神话", "疯狂", "污染"],
    "都市异能": ["都市", "异能", "觉醒", "系统"],
    "科幻": ["星际", "机甲", "宇宙", "人工智能"],
}
FEMALE_GENRES = {
    "治愈": ["治愈", "温暖", "日常", "美食"],
    "救赎": ["救赎", "偏执", "追妻", "弥补"],
    "疯批": ["疯批", "病娇", "偏执", "黑化"],
    "双强": ["双强", "势均力敌", "并肩", "强强"],
    "宅斗宫斗": ["宅斗", "宫斗", "后宅", "嫡女"],
}

WHY_HOT_HINTS = ["爽", "代入", "反转", "情绪", "解压", "新鲜", "共鸣", "追读"]
DROP_HINTS = ["弃书", "掉订", "劝退", "拖沓", "崩", "注水", "断更", "弃坑"]


@dataclass(frozen=True)
class ChannelGenreSignal:
    channel: str
    genre: str
    heat: int
    why_hot: str
    drop_points: list[str]


def _count(text: str, keywords: list[str]) -> int:
    return sum(text.count(k) for k in keywords)


def _why_for_genre(text: str, keywords: list[str]) -> str:
    """Find a sentence that mentions THIS genre's keywords — preferring one that
    also carries a why-hot hint. Anchoring on the genre's own keywords stops
    every genre from being annotated with the same generic first sentence (a
    real bug: 'why_hot' must explain THIS genre, not the corpus in general)."""
    import re
    sentences = [s.strip() for s in re.split(r"[。！？!?\n]", text) if s.strip()]
    genre_sentences = [s for s in sentences if any(k in s for k in keywords)]
    for s in genre_sentences:
        if any(h in s for h in WHY_HOT_HINTS):
            return s[:80]
    return genre_sentences[0][:80] if genre_sentences else ""


def _drops_for_genre(text: str, keywords: list[str], *, limit: int = 2) -> list[str]:
    """Drop-point sentences. Prefer ones mentioning this genre; fall back to any
    drop-point sentence in the corpus (drop patterns are often cross-genre)."""
    import re
    sentences = [s.strip() for s in re.split(r"[。！？!?\n]", text) if s.strip()]
    drop_sentences = [s for s in sentences if any(d in s for d in DROP_HINTS)]
    genre_first = [s for s in drop_sentences if any(k in s for k in keywords)]
    ordered = genre_first + [s for s in drop_sentences if s not in genre_first]
    return [s[:80] for s in ordered[:limit]]


def _analyze_channel(text: str, channel: str, genre_map: dict) -> list[ChannelGenreSignal]:
    signals = []
    for genre, keywords in genre_map.items():
        heat = _count(text, keywords)
        if heat <= 0:
            continue
        signals.append(ChannelGenreSignal(
            channel=channel,
            genre=genre,
            heat=min(100, heat * 10),
            why_hot=_why_for_genre(text, keywords),
            drop_points=_drops_for_genre(text, keywords),
        ))
    return sorted(signals, key=lambda s: s.heat, reverse=True)


def analyze_observations(project_path, observations: list[MarketObservation]) -> dict:
    """Merge all observation texts into deterministic per-channel genre signals."""
    corpus = "\n".join(
        text for _obs, text in iter_observation_texts(project_path, observations))

    male = _analyze_channel(corpus, "男频", MALE_GENRES)
    female = _analyze_channel(corpus, "女频", FEMALE_GENRES)

    all_drops: list[str] = []
    trending: list[str] = []
    for sig in male + female:
        trending.append(sig.genre)
        for d in sig.drop_points:
            if d not in all_drops:
                all_drops.append(d)

    return {
        "version": "1.0",
        "male_signals": [s.__dict__ for s in male],
        "female_signals": [s.__dict__ for s in female],
        "trending_genres": trending[:8],
        "common_drop_points": all_drops[:8],
        "evidence": [
            f"{obs.id} {obs.filename} (platform={obs.platform}, fetched_at={obs.fetched_at})"
            for obs in observations
        ],
    }
