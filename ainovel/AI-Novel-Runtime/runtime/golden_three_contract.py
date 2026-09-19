"""golden_three_contract.py — the generation-side 黄金三章 contract (规范 §7).

WHY THIS EXISTS:
The commercial funnel is 点击 × 前三章留存 × 免费追读 × 付费转化 × 长期稳定. This
project built ~30 modules for the last two terms and the prose texture, and had
NOTHING on the generation side for 前三章留存 — the term that decides whether a
reader stays at all. `serialize/golden_three.py` exists but only PACKAGES produced
chapters for review; there was no `chapter_no <= 3` branch anywhere in generation,
so chapter 1 and chapter 17 were written under identical instructions despite
having completely different commercial jobs.

规范 §7 states each of the first three chapters' job precisely. This module turns
that frozen prose into a per-chapter generation constraint:

  ch1 建立   — 300 字内立异常/损失，章末旧生活无法继续
  ch2 验证   — 用行动展示机制并暴露代价，「机会并不免费」
  ch3 兑现   — 第一次不靠巧合的主动胜利，读者知道以后爽在哪

MECHANISM — appended to `style`, deliberately NOT a new prompt version:
`length_directive` already established this seam (execution/run.py merges it into
`style`), and it is the right one here: frozen templates stay untouched, no
version axis growth, and a chapter outside 1-3 renders "" so its draft is
byte-identical. A prompt v15 would have bought the same effect while making every
future template inherit another required variable.

DISCIPLINE:
  - Deterministic: same chapter_no => same string. No model, no I/O.
  - ADVISORY in the ADR-003 sense — it shapes generation, gates nothing. Nothing
    here blocks a build or a publish.
  - Chapters 4+ get "" (empty), so the long-serial path is unchanged.
  - It never asserts facts. It states what the chapter must ACCOMPLISH, never what
    is true in the world, so it cannot contradict the registry or the Brain.
"""
from __future__ import annotations

from typing import Optional

# The first-300-characters requirement is the single highest-leverage rule in §7:
# a reader who is not held by the opening never reaches anything else built here.
OPENING_HOOK_CHARS = 300

_CH1 = f"""【黄金三章 · 开篇章（建立）】本章的商业职责是让读者读完并继续读下去。
- 前 {OPENING_HOOK_CHARS} 字内必须至少出现两项：异常状态／迫近的具体损失／不寻常现象／立即要完成的动作／有风险的选择／具体倒计时。要具体到数字、期限或物件，不要用概括语。
- 中段必须立住：主角当下目标、阻力、失败的具体后果、核心人格（用一次选择体现，不要用标签描述）、以及一次由主角主动发起的尝试。
- 章末必须产生不可逆变化或立即行动的需求。读完本章的状态应是：旧生活无法继续。
- 禁止：开篇倾泻世界设定与专名（只引入当前冲突需要的信息）；主角全程被动挨打；用大段回忆或解说代替当下的行动。"""

_CH2 = """【黄金三章 · 验证章】本章的商业职责是让读者确认这本书的核心玩法成立。
- 必须通过行动展示核心机制，不要用说明或旁白介绍它的规则。
- 主角必须获得一项明确、具体的收益（数量、名分、能力边界的变化都要可感）。
- 必须同时暴露机制的限制、风险或代价——收益与代价要在同一章里同时成立。
- 必须解决当前问题的一部分，并把主角带入一个更大的局面。
- 读完本章的状态应是：主角知道自己有机会，但机会并不免费。
- 禁止：把金手指写成说明书（一次列清全部能力与等级）；收益凭空到手而无代价。"""

_CH3 = """【黄金三章 · 兑现章】本章的商业职责是让读者知道这本书今后主要爽在哪里。
- 主角必须基于已知规则主动制定方案，胜利来自机制与人格共同作用。
- 对手必须提供真实阻力，胜利绝不能依赖巧合、意外或强者恰好出现。
- 必须产生明确的阶段结果，并改变主角周围的利益格局（旁观者态度、资源归属、对手损失至少变化一项）。
- 章末必须打开前十章的目标。
- 禁止：靠巧合或天降外力取胜；对手临时降智以衬托主角；胜利后局面毫无变化。"""

_CONTRACTS = {1: _CH1, 2: _CH2, 3: _CH3}


def golden_three_directive(chapter_no: Optional[int]) -> str:
    """The §7 contract for `chapter_no`, or "" for any chapter outside 1-3.

    "" is load-bearing: it keeps every chapter from the fourth onward — i.e. the
    whole long-serial path — byte-identical to before this module existed, exactly
    as `length_directive` returns "" for a project with no authored target.

    Deterministic; never raises. A bool is rejected explicitly because `True == 1`
    in Python and would otherwise silently render the chapter-1 contract.
    """
    if not isinstance(chapter_no, int) or isinstance(chapter_no, bool):
        return ""
    return _CONTRACTS.get(chapter_no, "")


def is_golden_three(chapter_no: Optional[int]) -> bool:
    """Whether this chapter is one of the three the §7 contract governs."""
    return bool(golden_three_directive(chapter_no))
