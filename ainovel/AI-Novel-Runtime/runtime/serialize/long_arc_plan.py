"""D90-04: long-arc plan for the first 100 chapters.

Produces a 10-chapter banded long-arc plan covering the first 100 chapters.
Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class LongArcBand:
    band_id: str
    start: int
    end: int
    volume_goal: str
    main_conflict: str
    growth_shift: str
    world_addition: str
    commercial_peak: str
    payoff_commitment: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HundredChapterLongArcPlan:
    kind: str
    version: str
    bands: list[LongArcBand]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "bands": [b.to_dict() for b in self.bands],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_hundred_chapter_long_arc(*, outline: Mapping[str, Any]) -> HundredChapterLongArcPlan:
    title = str(outline.get("title") or "")
    logline = str(outline.get("logline") or "")
    bands: list[LongArcBand] = []
    template = [
        (1, 10, "建立主角与核心威胁", "首个对手/规则", "主角被迫采取行动", "世界规则第一次展开", "卷初钩子兑现", "建立身份与目标"),
        (11, 20, "扩张冲突与势力", "更高一级对抗", "主角在代价中升级", "引入新地图/新势力", "阶段反转", "中段推进承诺"),
        (21, 30, "卷内大闭环", "阶段 boss 与真相线索", "主角做出更难选择", "引入关键真相", "章末高潮", "前 30 章承诺回收"),
        (31, 40, "第一卷后半压力释放", "旧敌残余 / 新障碍", "主角从被动变主动", "扩展人际/资源", "持续爽点", "保持追读"),
        (41, 50, "卷间升级", "跨卷阴影", "主角牺牲换取关键进展", "开放新系统/新势力", "中卷高点", "埋下大卷伏笔"),
        (51, 60, "第二卷门槛", "新地图/新规则", "主角完成关键身份跃迁", "世界观扩展", "第二次高潮", "卷中商业峰值"),
        (61, 70, "大矛盾公开", "更强对手正面对抗", "主角牺牲/收获并存", "扩大世界规模", "高压推进", "承诺开始兑现"),
        (71, 80, "真相逼近", "旧秩序核心", "主角与核心盟友关系变化", "揭示关键背景", "情绪爆点", "高潮前夜"),
        (81, 90, "终局前清算", "终极敌对力量", "主角完成形态升级", "终极资源/武器", "终局高点", "最大承诺兑现"),
        (91, 100, "卷末收束与下一卷入口", "终极决战/余波", "主角重建秩序", "留下新局面", "终局回响", "下一卷 hook"),
    ]
    for start, end, goal, conflict, growth, world_add, peak, payoff in template:
        bands.append(LongArcBand(
            band_id=f"B-{start:03d}-{end:03d}",
            start=start,
            end=end,
            volume_goal=f"{title or '作品'}：{goal}",
            main_conflict=f"{logline}；{conflict}",
            growth_shift=growth,
            world_addition=world_add,
            commercial_peak=peak,
            payoff_commitment=payoff,
        ))
    return HundredChapterLongArcPlan(
        kind="hundred_chapter_long_arc_plan",
        version="1.0",
        bands=bands,
        metadata={"band_count": len(bands), "chapter_count": 100},
    )
