from __future__ import annotations

from runtime.execution.m7 import assess_m7
from runtime.execution.redline import RedlineRule, check_redlines


def test_m7_blocks_on_hard_redline():
    res = assess_m7(
        {"body": "有人企图颠覆国家政权。"},
        chapter_id="CH-1",
        references=[],
    )
    assert res.recommendation == "block"
    assert res.risk_level == "L3"
    assert res.redline_passed is False


def test_m7_detects_reference_similarity_and_blocks():
    body = "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。"
    ref = {
        "source_id": "REF-1",
        "source_type": "reference_novel",
        "text": "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。",
    }
    res = assess_m7(
        {"body": body},
        chapter_id="CH-2",
        references=[ref],
    )
    assert res.risk_level == "L3"
    assert res.recommendation == "block"
    assert res.similarity["overall_similarity"] == 1.0
    assert res.similarity["matches"][0]["source_id"] == "REF-1"
    assert res.similarity["matches"][0]["aligned_spans"]


def test_m7_recommends_when_clean():
    res = assess_m7(
        {"body": "他在城门外停下脚步，重新整理行囊。"},
        chapter_id="CH-3",
        references=[{"source_id": "REF-1", "source_type": "reference_novel", "text": "完全不同的内容"}],
    )
    assert res.recommendation == "recommend"
    assert res.risk_level in {"L0", "L1"}


def test_redline_dsl_scope_and_tags():
    rules = [
        RedlineRule(rule_id="title-match", pattern="禁书", severity="hard", scope="title", action="block", priority=1),
        RedlineRule(rule_id="tag-match", pattern="", severity="soft", scope="body", action="review", tags_any=("political",), priority=2),
    ]
    hits = check_redlines({"title": "这是禁书", "body": "正文", "tags": ["political"]}, rules)
    assert [h.rule for h in hits] == ["title-match", "tag-match"]


def test_m7_similarity_is_linear_over_large_references():
    """Regression (M1-B2 follow-up): originality went default-on per chapter, and
    the old O(len²) SequenceMatcher engine HUNG the serial against full reference
    novels (98% CPU, >30 min). The linear n-gram engine must finish a large
    reference in well under a second, and clean prose must stay L0/recommend."""
    import time
    # a ~200k-char reference — big enough that an O(len²) scan would take minutes
    ref_text = "这是一段参考小说的正文内容，用于相似度检测。" * 8000
    body = "完全不同的原创章节，讲述主角在异世界的独特冒险与成长。" * 100  # ~2.8k chars
    refs = [{"source_id": "REF-BIG", "source_type": "reference_novel", "text": ref_text}]
    t = time.time()
    res = assess_m7({"body": body}, chapter_id="CH-PERF", references=refs)
    elapsed = time.time() - t
    assert elapsed < 2.0, f"similarity took {elapsed:.2f}s — quadratic regression?"
    assert res.risk_level == "L0" and res.recommendation == "recommend"


def test_m7_reference_index_is_memoized_across_chapters():
    """The per-reference index is cached ON the ref dict so a multi-chapter serial
    indexes each novel ONCE, not per chapter (the amortization that makes
    default-on originality affordable)."""
    ref = {"source_id": "REF-1", "source_type": "reference_novel",
           "text": "参考正文" * 500}
    assert "_m7_index" not in ref
    assess_m7({"body": "第一章原创正文" * 50}, chapter_id="CH-1", references=[ref])
    assert "_m7_index" in ref, "reference index must be memoized on the ref dict"
    # a second chapter reuses the cached index (same object identity)
    first_idx = ref["_m7_index"]
    assess_m7({"body": "第二章原创正文" * 50}, chapter_id="CH-2", references=[ref])
    assert ref["_m7_index"] is first_idx
