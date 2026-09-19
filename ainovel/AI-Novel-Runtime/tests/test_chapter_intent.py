from runtime.chapter.types import ChapterIntent


def test_chapter_intent_serializes_role_and_length():
    intent = ChapterIntent(
        chapter_id="CH-001",
        chapter_no=1,
        goal="开篇",
        chapter_role="opening",
        target_length_cjk=1200,
    )
    payload = intent.to_dict()
    assert payload["chapter_role"] == "opening"
    assert payload["target_length_cjk"] == 1200
