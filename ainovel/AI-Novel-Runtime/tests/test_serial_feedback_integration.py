from runtime.chapter.types import ChapterIntent
from runtime.scene.serial_humanization import render_recent_openings


def test_recent_openings_prompt_block_is_stable_and_non_empty():
    block = render_recent_openings([
        "第一章：旧城雨夜\n\n他推开门。",
        "第二章：档案楼\n\n她抬头看向走廊。",
    ])
    assert "最近 2 章的开篇如下" in block
    assert "不要重复相同的主语起手或句式" in block


def test_opening_intent_can_absorb_serial_feedback():
    intent = ChapterIntent(
        chapter_id="CH-1",
        chapter_no=1,
        goal="开篇",
        chapter_role="opening",
        target_length_cjk=900,
    )
    adjusted = intent.adjusted_for_review(
        overall_verdict="revise",
        issues=["opening repetition"],
        scores={"pacing": 0.55, "hook_strength": 0.58},
    )
    assert adjusted.target_length_cjk == 1400
    assert adjusted.constraints[-1] == "review_feedback:opening repetition"
