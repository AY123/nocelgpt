"""
progression/__init__.py — 进阶系统抽象（P0-B）

解决 power_system 硬耦合问题，支持多种题材的进阶体系：
- PowerSystem: 玄幻/奇幻修炼体系
- WealthSystem: 都市财富/地位体系
- TechSystem: 科幻科技体系
- InfluenceSystem: 权谋/政治影响力体系
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ProgressionSystem:
    """进阶系统抽象基类"""

    # 系统类型
    type: str  # "power" | "wealth" | "tech" | "influence"

    # 等级/阶层
    tiers: List[str]

    # 突破条件
    breakthrough_condition: str

    # 硬限制
    hard_limits: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "type": self.type,
            "tiers": self.tiers,
            "breakthrough_condition": self.breakthrough_condition,
            "hard_limits": self.hard_limits,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProgressionSystem:
        """从字典创建（用于 JSON 反序列化）"""
        prog_type = data.get("type", "power")

        if prog_type == "wealth":
            return WealthSystem.from_dict(data)
        elif prog_type == "tech":
            return TechSystem.from_dict(data)
        elif prog_type == "influence":
            return InfluenceSystem.from_dict(data)
        else:
            return PowerSystem.from_dict(data)


class PowerSystem(ProgressionSystem):
    """玄幻/奇幻修炼体系"""

    def __init__(self, tiers: List[str], breakthrough_condition: str, hard_limits: List[str]):
        super().__init__(
            type="power",
            tiers=tiers,
            breakthrough_condition=breakthrough_condition,
            hard_limits=hard_limits,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PowerSystem:
        return cls(
            tiers=data.get("tiers", []),
            breakthrough_condition=data.get("breakthrough_condition", ""),
            hard_limits=data.get("hard_limits", []),
        )


class WealthSystem(ProgressionSystem):
    """都市财富/地位体系"""

    def __init__(self, tiers: List[str], breakthrough_condition: str, hard_limits: List[str]):
        super().__init__(
            type="wealth",
            tiers=tiers,
            breakthrough_condition=breakthrough_condition,
            hard_limits=hard_limits,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WealthSystem:
        return cls(
            tiers=data.get("tiers", []),
            breakthrough_condition=data.get("breakthrough_condition", ""),
            hard_limits=data.get("hard_limits", []),
        )


class TechSystem(ProgressionSystem):
    """科幻科技体系"""

    def __init__(self, tiers: List[str], breakthrough_condition: str, hard_limits: List[str]):
        super().__init__(
            type="tech",
            tiers=tiers,
            breakthrough_condition=breakthrough_condition,
            hard_limits=hard_limits,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TechSystem:
        return cls(
            tiers=data.get("tiers", []),
            breakthrough_condition=data.get("breakthrough_condition", ""),
            hard_limits=data.get("hard_limits", []),
        )


class InfluenceSystem(ProgressionSystem):
    """权谋/政治影响力体系"""

    def __init__(self, tiers: List[str], breakthrough_condition: str, hard_limits: List[str]):
        super().__init__(
            type="influence",
            tiers=tiers,
            breakthrough_condition=breakthrough_condition,
            hard_limits=hard_limits,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InfluenceSystem:
        return cls(
            tiers=data.get("tiers", []),
            breakthrough_condition=data.get("breakthrough_condition", ""),
            hard_limits=data.get("hard_limits", []),
        )


def infer_progression_type(genre: str) -> str:
    """根据题材推断进阶系统类型"""
    genre_lower = genre.lower()

    if "都市" in genre_lower:
        return "wealth"
    elif "科幻" in genre_lower:
        return "tech"
    elif "权谋" in genre_lower or "朝堂" in genre_lower:
        return "influence"
    else:
        # 默认：玄幻/仙侠/奇幻
        return "power"


def create_default_progression(genre: str) -> ProgressionSystem:
    """根据题材创建默认进阶系统"""
    prog_type = infer_progression_type(genre)

    if prog_type == "wealth":
        return WealthSystem(
            tiers=["贫困", "温饱", "小康", "富裕", "富豪"],
            breakthrough_condition="完成重大商业项目或投资",
            hard_limits=["不能违反法律", "不能操控他人意志", "财富需要合理来源"],
        )
    elif prog_type == "tech":
        return TechSystem(
            tiers=["行星文明", "恒星文明", "星系文明", "星团文明", "宇宙文明"],
            breakthrough_condition="解锁新科技等级，扩展势力范围",
            hard_limits=["物理法则限制", "资源消耗", "时间成本"],
        )
    elif prog_type == "influence":
        return InfluenceSystem(
            tiers=["无名", "小吏", "地方官", "朝廷重臣", "权倾朝野"],
            breakthrough_condition="获得关键支持，扩大政治影响",
            hard_limits=["朝堂规则", "势力制衡", "民心向背"],
        )
    else:
        # 默认 power system
        return PowerSystem(
            tiers=["炼气", "筑基", "金丹", "元婴", "化神"],
            breakthrough_condition="突破境界瓶颈",
            hard_limits=["资源稀缺", "天赋限制", "寿命限制"],
        )


# 向后兼容：保持 power_system 字段名
def normalize_progression_dict(data: Dict[str, Any], genre: Optional[str] = None) -> Dict[str, Any]:
    """
    规范化 progression 字典

    支持：
    1. 旧格式：{"tiers": [...], ...} 没有 type 字段
    2. 新格式：{"type": "wealth", "tiers": [...], ...}

    返回统一的新格式
    """
    if "type" in data:
        # 已经是新格式
        return data

    # 旧格式，推断类型
    if genre:
        prog_type = infer_progression_type(genre)
    else:
        # 尝试从 tiers 内容推断
        tiers_str = str(data.get("tiers", []))
        if any(kw in tiers_str for kw in ["打工", "老板", "企业家", "资本家"]):
            prog_type = "wealth"
        elif any(kw in tiers_str for kw in ["文明", "科技", "星际"]):
            prog_type = "tech"
        else:
            prog_type = "power"

    return {
        "type": prog_type,
        **data
    }
