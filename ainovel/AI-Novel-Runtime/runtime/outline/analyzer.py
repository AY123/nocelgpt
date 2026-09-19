"""Deterministic reference-novel analysis for Outline Bootstrap v0.2.

This module gives the architecture a non-network analysis stage. Later LLM
agents can replace these heuristics behind the same artifact shapes.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .chunker import chunk_text
from .sources import ReferenceSource, iter_source_texts

GENRE_HINTS = {
    "都市": ["公司", "创业", "职场", "商业", "投资", "股票", "房地产",
             "互联网", "金融", "校园", "高考", "大学", "城市", "CBD"],
    "都市重生": ["重生", "回到", "再来一次", "前世", "这一世", "重活"],
    "玄幻": ["灵气", "修炼", "宗门", "丹药", "神通", "境界", "法宝", "天道", "突破境界"],
    "仙侠": ["飞剑", "道心", "仙门", "渡劫", "元婴", "天劫", "仙缘", "剑修"],
    "科幻": ["星舰", "宇宙", "殖民", "人工智能", "量子", "机甲", "星际", "虫洞"],
    "悬疑": ["案件", "尸体", "线索", "凶手", "调查", "密室", "推理"],
    "奇幻": ["王国", "魔法", "骑士", "魔导", "精灵", "诅咒", "魔导师", "巨龙"],  # "龙"改为"巨龙"
}

# 负向关键词：某些题材不应该出现的词
GENRE_CONFLICTS = {
    "都市": ["灵气", "修炼", "魔法", "修仙", "法宝", "渡劫", "元婴"],
    "玄幻": ["公司", "股票", "互联网", "创业", "投资"],
    "奇幻": ["公司", "股票", "互联网", "创业", "投资"],
}

CONFLICT_HINTS = ["危机", "仇", "战", "杀", "逃", "背叛", "争夺", "阴谋", "秘密"]
REWARD_HINTS = ["突破", "觉醒", "逆袭", "胜利", "传承", "宝物", "揭晓", "重逢"]


@dataclass(frozen=True)
class ChunkAnalysis:
    index: int
    chars: int
    summary: str
    conflict_score: int
    reward_score: int


@dataclass(frozen=True)
class ReferenceAnalysis:
    reference_id: str
    filename: str
    chars: int
    chunk_count: int
    genre_hints: list[str]
    core_hook: str
    main_conflicts: list[str]
    reader_rewards: list[str]
    avoid_direct_copy: list[str]
    chunks: list[ChunkAnalysis]

    def to_dict(self) -> dict:
        return {
            "reference_id": self.reference_id,
            "filename": self.filename,
            "chars": self.chars,
            "chunk_count": self.chunk_count,
            "genre_hints": self.genre_hints,
            "core_hook": self.core_hook,
            "main_conflicts": self.main_conflicts,
            "reader_rewards": self.reader_rewards,
            "avoid_direct_copy": self.avoid_direct_copy,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
        }


def _score_keywords(text: str, keywords: list[str]) -> int:
    return sum(text.count(keyword) for keyword in keywords)


def _first_sentence(text: str, *, max_chars: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if not compact:
        return "空文本参考源。"
    pieces = re.split(r"[。！？!?\n]", compact, maxsplit=1)
    sentence = pieces[0].strip() or compact
    return sentence[:max_chars]


def _detect_genres(text: str) -> list[str]:
    scored = []
    for genre, keywords in GENRE_HINTS.items():
        score = _score_keywords(text, keywords)

        # 应用负向关键词惩罚
        if genre in GENRE_CONFLICTS:
            conflict_count = sum(1 for kw in GENRE_CONFLICTS[genre] if kw in text)
            score = max(0, score - conflict_count * 2)  # 负向词权重更高

        # 特殊加权："都市重生"如果检测到，强制提升都市相关题材
        if genre in ["都市", "都市重生"] and "重生" in text:
            score += 10  # 重生关键词额外加权

        if score:
            scored.append((score, genre))

    # 排序并返回前3个
    result = [genre for _, genre in sorted(scored, reverse=True)[:3]]

    # 后处理：如果"都市重生"在列表中，确保"都市"也在前面
    if "都市重生" in result and "都市" in result:
        # 把都市相关的往前排
        result = ["都市", "都市重生"] + [g for g in result if g not in ["都市", "都市重生"]]

    return result or ["待判定"]


def _chunk_analysis(chunks: list[str]) -> list[ChunkAnalysis]:
    results = []
    for index, chunk in enumerate(chunks, start=1):
        results.append(
            ChunkAnalysis(
                index=index,
                chars=len(chunk),
                summary=_first_sentence(chunk),
                conflict_score=_score_keywords(chunk, CONFLICT_HINTS),
                reward_score=_score_keywords(chunk, REWARD_HINTS),
            )
        )
    return results


def analyze_reference(source: ReferenceSource, text: str, *, max_chars: int = 6000) -> ReferenceAnalysis:
    chunks = chunk_text(text, max_chars=max_chars, overlap=min(300, max_chars // 10))
    chunk_results = _chunk_analysis(chunks)
    genre_hints = _detect_genres(text)
    core_hook = _first_sentence(text)
    top_conflicts = sorted(chunk_results, key=lambda item: item.conflict_score, reverse=True)[:3]
    top_rewards = sorted(chunk_results, key=lambda item: item.reward_score, reverse=True)[:3]

    return ReferenceAnalysis(
        reference_id=source.id,
        filename=source.filename,
        chars=len(text),
        chunk_count=len(chunks),
        genre_hints=genre_hints,
        core_hook=core_hook,
        main_conflicts=[f"chunk-{item.index}: conflict_score={item.conflict_score}" for item in top_conflicts],
        reader_rewards=[f"chunk-{item.index}: reward_score={item.reward_score}" for item in top_rewards],
        avoid_direct_copy=[
            "不得复用参考小说的专有名词、角色姓名、门派/组织名称。",
            "只抽象结构与节奏，不复刻桥段顺序和关键反转。",
            "最终大纲必须建立新的世界规则、人物动机与核心冲突。",
        ],
        chunks=chunk_results,
    )


def analyze_project_sources(project_path, sources: list[ReferenceSource]) -> list[ReferenceAnalysis]:
    return [
        analyze_reference(source, text)
        for source, text in iter_source_texts(project_path, sources)
    ]


def merge_reference_analysis(analyses: list[ReferenceAnalysis]) -> dict:
    """Merge per-reference signals into the contract consumed by outline agents."""
    genre_counts: dict[str, int] = {}
    reward_scores: list[tuple[int, str]] = []
    conflict_scores: list[tuple[int, str]] = []
    total_chars = 0
    total_chunks = 0
    guardrails: list[str] = []

    for analysis in analyses:
        total_chars += analysis.chars
        total_chunks += analysis.chunk_count
        # 保留题材顺序权重：第一题材权重3，第二题材权重2，第三题材权重1
        for idx, genre in enumerate(analysis.genre_hints):
            weight = 3 - idx  # 第一个得3分，第二个得2分，第三个得1分
            genre_counts[genre] = genre_counts.get(genre, 0) + weight
        for item in analysis.chunks:
            reward_scores.append((item.reward_score, f"{analysis.reference_id}:chunk-{item.index}"))
            conflict_scores.append((item.conflict_score, f"{analysis.reference_id}:chunk-{item.index}"))
        for rule in analysis.avoid_direct_copy:
            if rule not in guardrails:
                guardrails.append(rule)

    genre_signals = [
        genre for genre, _count in sorted(
            genre_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ] or ["待判定"]
    avg_chunk_chars = int(total_chars / total_chunks) if total_chunks else 0
    structure_signals = [
        "multi-reference-synthesis" if len(analyses) > 1 else "single-reference-abstraction",
        "chunked-longform-analysis" if total_chunks > len(analyses) else "shortform-analysis",
    ]
    if avg_chunk_chars >= 4000:
        structure_signals.append("large-act-blocks")
    else:
        structure_signals.append("compact-opening-material")

    top_rewards = [
        f"{label}: reward_score={score}"
        for score, label in sorted(reward_scores, reverse=True)[:5]
    ]
    top_conflicts = [
        f"{label}: conflict_score={score}"
        for score, label in sorted(conflict_scores, reverse=True)[:5]
    ]

    return {
        "version": "0.2",
        "reference_count": len(analyses),
        "total_chars": total_chars,
        "total_chunks": total_chunks,
        "genre_signals": genre_signals,
        "structure_signals": structure_signals,
        "reader_rewards": top_rewards or ["curiosity"],
        "conflict_pressure": top_conflicts or ["low explicit conflict signal"],
        "core_hooks": [
            {"reference_id": item.reference_id, "hook": item.core_hook}
            for item in analyses
        ],
        "originality_guardrails": guardrails,
    }
