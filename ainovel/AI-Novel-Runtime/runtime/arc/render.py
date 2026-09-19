"""render.py — render a chapter's long-arc coordinate into a prompt block.

The generation-time consumer of the Long-Arc Plan (roadmap M3): turns one
chapter's projected long-arc position into the compact 本章长弧坐标 block the v10
chapter-draft prompt injects, so the drafter knows WHERE in the whole arc this
chapter sits — its volume and that volume's goal/oppressor, how far to the volume
climax, the power tier it should be approaching, the conflict pressure of its
volume, and whether it sits on a paywall / milestone.

Deterministic: same coordinate => same block. Advisory — it shapes emphasis, it
never overrides a fact, the mandate, or the director objective.
"""
from __future__ import annotations

from typing import Optional

from .projection import LongArcPlan


def render_long_arc(plan: LongArcPlan, chapter_no: int) -> str:
    """Render chapter_no's long-arc coordinate as a prompt block. Returns a stable
    sentinel when the chapter is out of the plan's horizon, so the v10 slot always
    binds to a non-empty string."""
    coord = plan.chapter(chapter_no)
    if coord is None:
        return "（本章超出长弧规划范围，长弧坐标不约束本章）"

    lines = []
    vol_title = coord.get("volume_title") or coord.get("volume_id")
    lines.append(
        f"- 所在卷：{coord['volume_id']}「{vol_title}」"
        f"（本卷第 {coord['position_in_volume']}/{coord['volume_span']} 章）")
    if coord.get("volume_goal"):
        lines.append(f"- 本卷目标：{coord['volume_goal']}")
    if coord.get("volume_oppressor"):
        lines.append(f"- 本卷压迫源：{coord['volume_oppressor']}")

    to_climax = coord.get("chapters_to_volume_climax")
    if coord.get("is_volume_climax"):
        lines.append("- 节奏位置：★本章即本卷高潮，必须给出本卷级别的爆发/结算")
    elif isinstance(to_climax, int) and to_climax > 0:
        lines.append(f"- 节奏位置：距本卷高潮还有 {to_climax} 章，向高潮持续加压")

    if coord.get("power_tier"):
        lines.append(f"- 战力段位：本章主角应处于/逼近「{coord['power_tier']}」层级")
    if coord.get("conflict_level"):
        pressure = coord.get("conflict_pressure") or ""
        lines.append(f"- 冲突层级：{coord['conflict_level']}"
                     + (f"（{pressure}）" if pressure else ""))

    if coord.get("is_paywall"):
        lines.append("- ⚑ 本章为付费墙/新卷开篇章：开头必须强钩子，给追订理由")
    if coord.get("is_milestone"):
        lines.append("- ⚑ 本章为里程碑章：情绪/商业节点，值得一个更大的爆点")
    ref_promise = coord.get("reference_core_promise")
    if ref_promise:
        lines.append(f"- 参考抽象核心承诺：{ref_promise}")
    ref_cadence = coord.get("reference_commercial_cadence")
    if ref_cadence:
        lines.append(f"- 参考抽象商业节奏：{ref_cadence}")
    next_ms = coord.get("next_milestone")
    if isinstance(next_ms, int):
        lines.append(f"- 下一里程碑：第 {next_ms} 章")

    header = ("本章在整部长弧中的坐标（用于把控卷级节奏、战力进度与付费节奏；"
              "只影响强调与铺垫，绝不覆盖事实/强制令/导演目标）：")
    return header + "\n" + "\n".join(lines)
