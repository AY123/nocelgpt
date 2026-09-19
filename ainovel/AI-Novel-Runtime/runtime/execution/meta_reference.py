"""meta_reference.py — 正文元指代泄漏检测（ANES v2, ADR-003）。

读者读的是小说，不该在正文里看到"上一章""第5章""前文"被当作剧情内的引用。
这是叙事外的编号引用漏进了正文——人类作者写"那天夜里""三天前"，不写"第5章"。

发现来源：v11-vs-v12 双臂 A/B 抽查真实正文时发现（v11 12 处/4 章，v12 3 处/1 章），
且经核验**没有任何现有检测器覆盖**：text_integrity status=pass、hygiene 只报对白占比。

这是 scene/pacing.py、execution/density.py、execution/humanization.py、
execution/hook_check.py 的第五个孪生兄弟：同样纪律，不同信号。density 测正文
承载什么，humanization 测句子怎么造，hook_check 测结尾的功能，本模块测
**叙事层是否破裂**——正文有没有把自己当成"一份分章的文档"来引用。

DISCIPLINE:
  - DETERMINISTIC：同 body => 同 findings，不调模型、不读包/状态/IO。
  - EVALUATIVE, never gates（ADR-003）：复用 ReviewReport（axis=evaluative,
    gating=False），像 check_pacing 一样骑在 envelope 上。
  - 只读 body。标题行（# 第9章）是合法的章节标题，必须排除——否则每章必误报。
  - 保守：仅匹配高置信度的叙事外引用；世界内用法（《天衍经》第三章）显式放行。
"""
from __future__ import annotations

import re
from typing import List, Optional

from .draft_review import ReviewReport, ReviewFinding

META_REFERENCE_REVIEWER_ID = "meta-reference-check-v1"

# 一处元指代即为缺陷（不像密度类需要阈值）：叙事层破裂是二元的。
META_LEAK_MAX = 0

# 高置信度叙事外指代。
#
# 「本章」不列入：它在正文里几乎只出现在（本章完）这类结束标记中，那已由
# text_integrity 的 chapter-end marker 覆盖。
#
# 「本书/全书」已移除 —— 4 本真实爆款阴性验证抓到误报：`全书` 命中在
# 「百科全书」内。这类泛词的子串误报风险高于其信号价值。
#
# 「前文/上文/下文」加 (?!字) 负向断言 —— 同一轮验证抓到「卷轴的上文字」被
# 误命中。这是本仓库第 4 次同类子串误报（前 3 次是 word_split 误伤标题行），
# 所以任何新检测器都必须先在真实爆款上做阴性验证再上线。
_RELATIVE_REF_RE = re.compile(r"上一章|下一章|前一章|后一章|(?:前文|上文|下文)(?!字)")

# 「第N章」——中文网文里既可能是元指代（在第5章他第一次…），也可能是世界内
# 引用（《天衍经》第三章）。世界内用法的特征是紧跟典籍类名词，或紧邻书名号。
_NUMBERED_CH_RE = re.compile(r"第\s*[0-9一二三四五六七八九十百零两]+\s*章")
# 世界内放行：其后紧跟典籍/条文类名词，或其前紧邻书名号收尾。
_IN_WORLD_AFTER_RE = re.compile(r"^\s*(?:经文|经|律|律法|功法|篇|诀|典|法诀|口诀|残卷|卷)")
_IN_WORLD_BEFORE_RE = re.compile(r"[》』」]\s*$")

# 标题行：以 # 开头，或整行就是一个章节标题（第N章 …）。这些是合法结构，不是泄漏。
_HEADING_LINE_RE = re.compile(
    r"^[ \t　]*(?:#|第\s*[0-9一二三四五六七八九十百零两]+\s*[章节回卷]\s*[^\n]{0,30}$)")


def _prose_lines(body: str) -> List[str]:
    """正文行 = 去掉标题行后的行。章节标题里的「第9章」是合法的，不算泄漏。"""
    out = []
    for line in (body or "").splitlines():
        if line.strip() and not _HEADING_LINE_RE.match(line):
            out.append(line)
    return out


def _numbered_hits(text: str) -> List[str]:
    """「第N章」命中，排除世界内引用（《天衍经》第三章 / 第三章经文）。"""
    hits = []
    for m in _NUMBERED_CH_RE.finditer(text):
        if _IN_WORLD_AFTER_RE.match(text[m.end():m.end() + 8]):
            continue
        if _IN_WORLD_BEFORE_RE.search(text[max(0, m.start() - 4):m.start()]):
            continue
        hits.append(m.group(0))
    return hits


def meta_reference_summary(body: str) -> Optional[dict]:
    """把正文折成元指代特征。空正文返回 None。确定性。

    `spans` 保留命中处的上下文片段，使 hygiene 类重写能定位到具体句子
    （量化→定位，与 locate_anaphora_run 同一教训：只报计数模型会跳过）。"""
    prose = "\n".join(_prose_lines(body))
    if not prose.strip():
        return None
    relative = _RELATIVE_REF_RE.findall(prose)
    numbered = _numbered_hits(prose)
    spans: List[str] = []
    for pat in (_RELATIVE_REF_RE, _NUMBERED_CH_RE):
        for m in pat.finditer(prose):
            if pat is _NUMBERED_CH_RE:
                if _IN_WORLD_AFTER_RE.match(prose[m.end():m.end() + 8]):
                    continue
                if _IN_WORLD_BEFORE_RE.search(prose[max(0, m.start() - 4):m.start()]):
                    continue
            s = max(0, m.start() - 18)
            spans.append(prose[s:m.end() + 18].replace("\n", " ").strip())
    return {
        "meta_reference_count": len(relative) + len(numbered),
        "relative_refs": len(relative),
        "numbered_chapter_refs": len(numbered),
        "spans": spans[:5],          # 上限 5 条，避免报告膨胀
        "total_chars": len(prose),
    }


def check_meta_reference(artifact: dict, *,
                         reviewer_id: str = META_REFERENCE_REVIEWER_ID) -> ReviewReport:
    """审查正文的元指代泄漏，返回 ADVISORY 报告
    （ReviewReport: axis=evaluative, gating=False）。确定性。

    一处即告警——叙事层破裂不是程度问题。消息里引用具体片段，让重写能定位。"""
    body = (artifact or {}).get("body", "") or ""
    summary = meta_reference_summary(body)
    findings: List[ReviewFinding] = []
    if summary and summary["meta_reference_count"] > META_LEAK_MAX:
        quoted = "；".join(f"「{s}」" for s in summary["spans"])
        findings.append(ReviewFinding(
            "meta-reference", "warning",
            f"正文出现叙事外的章节指代（{summary['meta_reference_count']} 处："
            f"相对指代 {summary['relative_refs']}、章号 {summary['numbered_chapter_refs']}）："
            f"读者读的是小说，正文里不该把「上一章／第N章／前文」当作剧情内引用。"
            f"改写为叙事内的时间或事件指代（那天夜里／三天前／在矿道里那次）。"
            f"具体需改写：{quoted}"))
    return ReviewReport(reviewer=reviewer_id, findings=findings)
