from runtime.prompt.binding import bind_chapter_draft


PACKAGE = {
    "task": {"task_id": "T-1", "goal": "写章节"},
    "content_hash": "sha256:" + "1" * 64,
    "provenance": {"derived_from": ["CHR-1"], "source_version": 1},
    "context": {"knowledge": [{"id": "K-1", "name": "知识A"}]},
}


def test_semantic_ledger_renders_text_block():
    binding = bind_chapter_draft(
        PACKAGE,
        {
            "semantic_ledger": {
                "knowledge": [
                    {"entry_id": "K-1", "text": "主角知道门后有人"},
                ],
                "promise": [
                    {"promise_id": "P-1", "promise_text": "今晚必须开门", "status": "pending"},
                ],
            }
        },
    )
    values = binding.values()

    assert "【知识】" in values["semantic_ledger_text"]
    assert "主角知道门后有人" in values["semantic_ledger_text"]
    assert "【承诺】" in values["semantic_ledger_text"]
    assert "今晚必须开门" in values["semantic_ledger_text"]
    assert values["semantic_ledger_raw"]["knowledge"][0]["entry_id"] == "K-1"
