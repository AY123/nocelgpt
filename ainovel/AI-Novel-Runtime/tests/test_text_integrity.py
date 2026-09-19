from __future__ import annotations

from runtime.execution.text_integrity import assess_text_integrity


def _artifact(body: str) -> dict:
    return {"body": body, "content_hash": "sha256:" + "a" * 64}


def test_normal_paragraph_break_passes():
    art = _artifact("第一句结束。\n\n第二句继续。")
    rep = assess_text_integrity(art)
    assert rep.status == "pass"
    assert rep.action == "allow"


def test_sentence_boundary_double_newline_passes():
    art = _artifact("他停住了。\n\n然后转身离开。")
    rep = assess_text_integrity(art)
    assert rep.status == "pass"


def test_word_split_with_double_newline_fails():
    art = _artifact("车\n\n祸来了。")
    rep = assess_text_integrity(art)
    assert rep.status == "fail"
    assert "word_split" in rep.reason_codes
    assert rep.action == "block"


def test_whitespace_anomaly_reports_review_required():
    art = _artifact("他 走进了房间。")
    rep = assess_text_integrity(art)
    assert rep.status in ("review_required", "pass")
    if rep.status == "review_required":
        assert "whitespace_anomaly" in rep.reason_codes


def test_empty_body_not_assessed():
    rep = assess_text_integrity(_artifact("   "))
    assert rep.status == "not_assessed"


# --- RUN-00020 regression: a chapter-END marker the model writes into the body
# （第一章 完）/（未完待续）spaces inside the bracket; _WORD_JOIN_RE fired
# whitespace_anomaly on it, dropping the gate pass-rate from a true 3/3 to 2/3.
# The marker is legitimate layout, not serialization word-splitting, so the body
# must still pass. See memory register-length-baseline-report-2026-07-16.
def test_chapter_end_marker_does_not_trip_whitespace_anomaly():
    body = "他望着窗外，久久没有说话。\n\n（第一章 完）"
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "pass"
    assert "whitespace_anomaly" not in rep.reason_codes


def test_various_chapter_end_markers_pass():
    for marker in ("（本章完）", "（未完待续）", "——全文完——", "第三章 完"):
        body = f"故事在这里停下。\n\n{marker}"
        rep = assess_text_integrity(_artifact(body))
        assert rep.status == "pass", f"{marker} should not trip the gate"


def test_real_word_join_corruption_still_flagged():
    # the marker exclusion must NOT suppress a genuine mid-line word-join
    # corruption on normal prose (over-suppression guard).
    rep = assess_text_integrity(_artifact("他 慢慢 走 进 房间，看到那封信。"))
    assert rep.status == "review_required"
    assert "whitespace_anomaly" in rep.reason_codes


# --- RUN-00023 regression: a scene-divider line the model writes to separate
# scenes within a chapter (a bare #, a —— dash run, ***, etc.) is orphaned by
# blank lines and looks like a ≤2-char word-split fragment. word_split is a
# GATING check (action=block), so this false-positive blocked 2 clean chapters
# from production (5→3). 3rd instance of this class (heading=A7, chapter-end
# marker=48f6459, scene-divider=here). See memory exp-b-fullstack-2026-07-17.
def test_bare_hash_scene_divider_passes():
    body = "他终于闭上眼睛，把所有情绪压进最深处。\n\n#\n\n周洛铭发现自己站在一片旷野。"
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "pass", f"bare # divider should not block; got {rep.reason_codes}"
    assert "word_split" not in rep.reason_codes


def test_dash_run_scene_divider_passes():
    body = "“明天。”\n\n——\n\n第二天晚上，北城废弃的厂房里灯火通明。"
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "pass", f"—— divider should not block; got {rep.reason_codes}"
    assert "word_split" not in rep.reason_codes


def test_symbol_row_scene_dividers_pass():
    for div in ("***", "* * *", "===", "◇◆◇", "· · ·"):
        body = f"上一幕在这里收束。\n\n{div}\n\n新的场景就此展开，光线骤然亮起。"
        rep = assess_text_integrity(_artifact(body))
        assert rep.status == "pass", f"{div!r} divider should not block; got {rep.reason_codes}"


def test_real_word_split_still_blocks_after_divider_exclusion():
    # over-suppression guard: a genuine ≤2-char word-split fragment made of REAL
    # prose characters (not divider glyphs) must STILL block. The scene-divider
    # exclusion is narrow — it only matches lines made purely of divider glyphs,
    # so a stray Chinese-word fragment orphaned by a blank line is untouched.
    rep = assess_text_integrity(_artifact("他写下一个\n\n字\n\n然后停笔。"))
    assert rep.status == "fail"
    assert "word_split" in rep.reason_codes


# --- RUN-00018 regression: a BARE 完 chapter-end marker orphaned by blank lines.
# _is_chapter_end_marker already recognises it (and line 187's whitespace_anomaly
# branch calls it), but the word_split branch never did — so a 1-char 完 read as a
# ≤2-char broken fragment and BLOCKED ch47, a chapter the judge scored 18/18.
# 4th instance of this class (heading=A7, chapter-end marker=48f6459,
# scene-divider=RUN-00023, bare 完=here). The module's own line-84 comment already
# claimed "same exclusion discipline as _is_heading / _is_chapter_end_marker" —
# the intent was documented, the wiring was missing.
def test_bare_chapter_end_marker_orphaned_by_blank_lines_passes():
    body = "只有婴儿的手掌那么大。\n\n完\n"
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "pass", f"bare 完 should not block; got {rep.reason_codes}"
    assert "word_split" not in rep.reason_codes


def test_bare_end_markers_orphaned_by_blank_lines_pass():
    for marker in ("完", "完结", "未完待续", "待续"):
        body = f"故事在这里停下。\n\n{marker}\n\n"
        rep = assess_text_integrity(_artifact(body))
        assert rep.status == "pass", f"{marker!r} should not block; got {rep.reason_codes}"
        assert "word_split" not in rep.reason_codes


def test_short_prose_fragment_still_blocks_after_end_marker_exclusion():
    # over-suppression guard: the exclusion matches only chapter-END markers, so a
    # genuine ≤2-char PROSE fragment orphaned by blank lines must STILL block.
    # 开 / 看着 are not end markers and must remain gated.
    for fragment in ("开", "看着"):
        rep = assess_text_integrity(
            _artifact(f"他写下一个\n\n{fragment}\n\n然后停笔。"))
        assert rep.status == "fail", f"{fragment!r} must still block"
        assert "word_split" in rep.reason_codes


# --- A7 live-baseline regression: a real chapter STARTING with a heading must
# not trip the gate. The old adjacency regex fired word_split on the 1-2 chars
# straddling the heading→paragraph break ("...Spoken\n\nThe"), blocking 100% of
# real chapters. See memory a7-live-baseline-findings.
def test_english_markdown_heading_then_paragraph_is_flagged_for_review():
    body = "# Chapter 1: The Oath Spoken\n\nThe archive hall smelled of old paper and pressed herbs."
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "review_required"
    assert rep.action == "require_review"
    assert "language_drift" in rep.reason_codes


def test_chinese_markdown_heading_then_paragraph_passes():
    rep = assess_text_integrity(_artifact("# 第一章：立誓\n\n档案馆里弥漫着旧纸的味道。"))
    assert rep.status == "pass"


def test_chinese_plain_chapter_heading_passes():
    # Web-novel style heading with no markdown marker.
    rep = assess_text_integrity(_artifact("第一章 立誓\n\n档案馆里弥漫着旧纸的味道。"))
    assert rep.status == "pass"


def test_chinese_volume_and_prologue_headings_pass():
    assert assess_text_integrity(_artifact("第一卷 风起\n\n他站在城墙上。")).status == "pass"
    assert assess_text_integrity(_artifact("楔子\n\n那一年，大雪封城。")).status == "pass"


def test_multi_paragraph_english_body_is_flagged_for_review():
    body = "# Ch 1\n\nShe ran.\n\nHe followed.\n\nThe end came fast."
    rep = assess_text_integrity(_artifact(body))
    assert rep.status == "review_required"
    assert rep.action == "require_review"
    assert "language_drift" in rep.reason_codes
