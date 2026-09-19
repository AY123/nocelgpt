"""test_meta_reference.py — 元指代泄漏检测（第五个孪生检测器）。

缺陷来源：v11-vs-v12 双臂 A/B 抽查真实正文时发现，正文里把「上一章／第5章／前文」
当作剧情内引用（v11 12 处/4 章，v12 3 处/1 章；30 章基线 10/30 章共 27 处），
且当时**没有任何检测器覆盖**（text_integrity pass、hygiene 只报对白占比）。

这些测试锁住三件事：
  1. 阳性：真实泄漏必须命中，且消息里引用具体片段（量化→定位）。
  2. **阴性：合法用法不得误报** —— 章节标题行、世界内典籍引用、以及
     「百科全书」「卷轴的上文字」这类子串。后两个是首版实测在真实爆款上
     抓到的真实误报（本仓库第 4 次同类子串误报），必须固化为回归。
  3. 纪律：advisory / never gates（ADR-003），确定性。
"""
from __future__ import annotations

from runtime.execution.meta_reference import (
    META_REFERENCE_REVIEWER_ID,
    check_meta_reference,
    meta_reference_summary,
)


def _warnings(body: str):
    return [f for f in check_meta_reference({"body": body}).findings
            if f.severity == "warning"]


# --------------------------------------------------------------------------- #
# 阳性：真实泄漏必须命中                                                        #
# --------------------------------------------------------------------------- #
def test_relative_reference_is_flagged():
    body = "段奕尘没有回头。左臂的灼痛还在，那是上一章硬接镜见川一击留下的印记。" * 6
    assert _warnings(body)


def test_numbered_chapter_reference_is_flagged():
    body = "这种反应在第5章他第一次吞噬敌人曜能时就出现过，当时是能力激活的代价。" * 6
    assert _warnings(body)


def test_message_quotes_the_offending_span():
    """只报计数会被模型跳过（同 locate_anaphora_run 的教训）——必须定位到具体句子。"""
    body = "他知道镜见川为什么这么做。上一章他逼出了灰雾的新用法，代价是左臂。" * 6
    msg = _warnings(body)[0].message
    assert "上一章" in msg and "「" in msg


def test_summary_counts_both_kinds():
    body = "上一章的伤还在。这在第5章他第一次吞噬时就出现过。前文提过那条矿渣坡。"
    s = meta_reference_summary(body)
    assert s["relative_refs"] >= 2          # 上一章 + 前文
    assert s["numbered_chapter_refs"] == 1  # 第5章
    assert s["meta_reference_count"] == s["relative_refs"] + s["numbered_chapter_refs"]


# --------------------------------------------------------------------------- #
# 阴性：合法用法不得误报（真实爆款 0/120 章）                                    #
# --------------------------------------------------------------------------- #
def test_chapter_heading_line_is_not_a_leak():
    """「# 第9章」是合法结构。若误报，每一章都会命中。

    注意夹具必须真实：标题只在正文开头出现一次、独占一行。用 `"…# 第9章…" * 6`
    构造会把标题粘到上一句尾部（凹陷处。# 第9章），那不是标题行而是行内文本，
    检测器命中它是正确行为。"""
    body = "# 第9章 破绽\n\n" + "岩洞里的空气凝成了一块冰。段奕尘靠在洞壁的凹陷处。" * 6
    assert not _warnings(body)


def test_bare_heading_line_without_hash_is_not_a_leak():
    body = "第九章 破绽\n\n" + "岩洞里的空气凝成了一块冰。段奕尘靠在洞壁的凹陷处呼吸。" * 6
    assert not _warnings(body)


def test_heading_glued_mid_line_IS_flagged():
    """反面固化：章号出现在句子中间（不是独占标题行）时必须命中——
    否则「他在第9章学会了」这类真实泄漏会被标题豁免规则漏掉。"""
    body = "岩洞里的空气凝成了一块冰。# 第9章 破绽 段奕尘靠在洞壁的凹陷处。" * 6
    assert _warnings(body)


def test_in_world_scripture_reference_is_not_a_leak():
    """《天衍经》第三章 —— 世界内典籍引用，不是叙事外指代。"""
    for body in ("他翻开《天衍经》第三章，指尖停在那行朱批上。" * 6,
                 "第三章经文写得明白：曜能不可逆引。" * 6):
        assert not _warnings(body), body[:20]


def test_encyclopedia_substring_is_not_a_leak():
    """真实误报回归：`全书` 曾命中「百科全书」（《盘龙》ch24）。"""
    body = "德林柯沃特就好像一部百科全书，好像什么都清楚。" * 6
    assert not _warnings(body)


def test_scroll_text_substring_is_not_a_leak():
    """真实误报回归：`上文` 曾命中「卷轴的上文字」（魔运苍茫 ch20）。"""
    body = "他还是无法辨认出这副卷轴的上文字和符号究竟源自哪里，无奈地放下卷轴。" * 6
    assert not _warnings(body)


def test_clean_prose_is_silent():
    body = "矿灯的光在两人之间晃了晃。镜见川站在三步开外，右手袖子里藏着一截短刀。" * 6
    assert not _warnings(body)


def test_empty_body_degrades_cleanly():
    assert meta_reference_summary("") is None
    assert not check_meta_reference({"body": ""}).findings
    assert not check_meta_reference({}).findings


# --------------------------------------------------------------------------- #
# 纪律                                                                         #
# --------------------------------------------------------------------------- #
def test_report_is_advisory_and_never_gates():
    body = "上一章的伤还在。" * 12
    rep = check_meta_reference({"body": body})
    assert rep.reviewer == META_REFERENCE_REVIEWER_ID
    assert rep.axis == "evaluative"
    assert rep.gating is False


def test_deterministic():
    body = "上一章的伤还在。这在第5章就出现过。" * 8
    a = check_meta_reference({"body": body}).to_dict()
    b = check_meta_reference({"body": body}).to_dict()
    assert a == b


def test_registered_in_advisory_and_sentinel_registries():
    """漏登记 = built≠live。三处登记表都必须含本检测器。"""
    from runtime.serialize.live_baseline_report import _ADVISORY_DETECTORS
    from runtime.dashboard.report import _SENTINEL_DETECTORS
    assert "meta_reference" in _ADVISORY_DETECTORS
    assert "meta_reference" in _SENTINEL_DETECTORS


def test_rides_the_chapter_run():
    from runtime.serialize.loop import ChapterRun
    assert "meta_reference" in ChapterRun.__dataclass_fields__
