"""test_draft_meta_tail.py — the draft body meta-tail sanitizer.

RUN-00001 ch13: the model echoed its own self-check block ("# 寻轨反馈\n
  [PASS] 叙事强制令：… [PASS] 导演目标：…") into the prose tail, which leaked into
final_text and false-fired the anaphora detector. _strip_meta_tail removes such a
trailing metadata block DETERMINISTICALLY; clean prose is byte-identical.
"""
from runtime.execution.agent import _strip_meta_tail


def test_strips_pass_checklist_tail():
    body = (
        "他推开门，走进矿道。空气里弥漫着晶尘的味道。\n\n"
        "远处传来脚步声，他握紧了怀里的晶石。\n\n"
        "# 寻轨反馈\n"
        "  [PASS] 叙事强制令：主角目标从实力突破转为主动布局\n"
        "  [PASS] 导演目标：完成第一次小闭环，以钩子收尾\n"
        "  [PASS] 节奏：上升 → 冲突 → 转折 → 钩子")
    cleaned = _strip_meta_tail(body)
    assert "[PASS]" not in cleaned
    assert "寻轨反馈" not in cleaned
    assert cleaned.endswith("他握紧了怀里的晶石。")   # prose body intact, no dangling ---


def test_strips_tail_with_leading_separator():
    body = ("正文最后一句。\n\n---\n\n# 反馈\n  [PASS] 检查项一\n  [PASS] 检查项二")
    cleaned = _strip_meta_tail(body)
    assert "[PASS]" not in cleaned
    assert not cleaned.rstrip().endswith("---")
    assert cleaned.rstrip().endswith("正文最后一句。")


def test_clean_prose_is_byte_identical():
    # No bracket tags => untouched (the whole non-polluted corpus relies on this).
    body = "他站起来，走向门口。风停了。她没有回头。\n\n矿道深处传来回响。"
    assert _strip_meta_tail(body) == body


def test_legit_inline_bracket_not_stripped():
    # A bracketed word inside prose (not a trailing [TAG] run) must survive.
    body = "他说：“看这里[重要]。”\n\n然后他转身离开了。"
    assert _strip_meta_tail(body) == body


def test_all_meta_body_returns_original():
    # Degenerate: if stripping would empty the body, keep the original (never
    # produce an empty draft from the sanitizer).
    body = "[PASS] 只有元数据\n[PASS] 没有正文"
    assert _strip_meta_tail(body) == body
