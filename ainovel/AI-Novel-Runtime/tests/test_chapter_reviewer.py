from runtime.chapter.reviewer import ChapterReviewer
from runtime.chapter.types import ChapterDraft


def _draft(text: str) -> ChapterDraft:
    return ChapterDraft(chapter_id="CH-001", version=1, text=text)


def test_opening_chapter_uses_higher_length_floor():
    reviewer = ChapterReviewer()
    short = reviewer.review(_draft("第一章：开篇\n\n这是一段很短的正文。"))
    assert short.overall_verdict == "revise"


def test_advance_chapter_passes_at_reasonable_length():
    reviewer = ChapterReviewer()
    body = "第三章：推进\n\n" + ("他继续向前。" * 180)
    rep = reviewer.review(_draft(body))
    assert rep.overall_verdict == "pass"
    assert rep.publish_readiness == "ready"


def test_hook_chapter_tolerates_shorter_length():
    reviewer = ChapterReviewer()
    body = "第五章：钩子\n\n" + ("门外传来一阵敲门声。" * 80)
    rep = reviewer.review(_draft(body))
    assert rep.overall_verdict == "pass"
