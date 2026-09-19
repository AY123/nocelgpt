"""meta_leak.py — 元指代泄漏的确定性测量(v13 H2 的仪器)。

为什么单独成一个模块:`tools/ab_craft_v13.py` 原来的正则是

    META_LEAK_RE = re.compile(r"上一章|下一章|前文|第[0-9一二三四五六七八九十]+章")

它把 `第N章` 一律算作泄漏,但实测(ab3-ds-v12 / genesis-pilot 真实正文)显示
这个模式同时命中三类完全不同的东西:

  1. 真泄漏(叙事内元指代):
       "那股在第一章末吞进体内的曜能还没完全压住"
     — 正文把"第一章"当成世界内的时间标记,这正是 v13 要禁的。
  2. 章节标题(格式产物):
       "# 第二十一章"、"**第十七章 引纹成阵**"
  3. 章末完结标记(格式产物):
       "（第一章 完）"

把 2/3 算进泄漏率会把章级泄漏率从 4/30 抬到 9/30(ab3-ds-v12 实测),
虚高一倍以上 —— 而这正是实验设计文档里 35% 基线的来源。用它做 H2 判据,
等于拿格式噪声当疗效。本仓库此前已有 3 次同类误报(word_split 撞 ——、
whitespace_anomaly 撞 （第一章 完）、anaphora 撞 【】面板行)。

所以本模块先剥离格式产物,再在剩余散文里数元指代。
"""
from __future__ import annotations

import re

# 叙事内元指代:出现即为泄漏,无格式产物歧义。
_UNAMBIGUOUS = {
    "上一章": re.compile(r"上一章"),
    "下一章": re.compile(r"下一章"),
    "前文": re.compile(r"前文"),
    # 用户要求纳入。注意:`本章` 是 v13 提示模板自身的小节标题用词
    # (本章长弧坐标 / 本章叙事强制令),所以只在正文里数,绝不去数提示。
    # 实测真实正文里极罕见(ab3-ds-v12 1/30、genesis-pilot 0/33),
    # 因此纳入的误报风险低,而漏检风险实在。
    "本章": re.compile(r"本章"),
}

# 有歧义的:`第N章` 既可能是叙事泄漏,也可能是标题/完结标记。
_CHAPTER_REF = re.compile(r"第[0-9一二三四五六七八九十百]+章")

# 整行就是一个章节标题(markdown #、粗体、或裸标题行)。
_HEADING_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*第[0-9一二三四五六七八九十百]+章"
    r"[^\n]{0,40}?(?:\*\*)?\s*$"
)
# 章末完结标记:（第一章 完）/ (第 1 章 完) / 【第一章完】
_END_MARKER = re.compile(
    r"[（(【]\s*第[0-9一二三四五六七八九十百]+章\s*[完终]\s*[)）】]"
)


def strip_format_artifacts(body: str) -> str:
    """剥离章节标题行与章末完结标记,返回纯叙事散文。

    只剥离**整行是标题**的情况。句中出现的 `第一章` 会被保留 —— 那才是
    真正的叙事内元指代。
    """
    without_markers = _END_MARKER.sub("", body)
    kept = [
        line for line in without_markers.splitlines()
        if not _HEADING_LINE.match(line)
    ]
    return "\n".join(kept)


def count_meta_leaks(body: str) -> dict[str, int]:
    """逐模式统计元指代泄漏次数(已剥离格式产物)。"""
    prose = strip_format_artifacts(body)
    counts = {name: len(rx.findall(prose)) for name, rx in _UNAMBIGUOUS.items()}
    counts["第N章"] = len(_CHAPTER_REF.findall(prose))
    counts["_total"] = sum(v for k, v in counts.items() if not k.startswith("_"))
    return counts


def has_meta_leak(body: str) -> bool:
    """章级二元结果:本章是否含元指代泄漏。

    H2 的检验单元。用二元而非计数,是因为计数是零膨胀的
    (多数章 0 次、少数章 2-6 次),签名秩检验在这种分布上失效。
    """
    return count_meta_leaks(body)["_total"] > 0
