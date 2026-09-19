from runtime.prompt.binding import bind_chapter_draft


def test_prompt_binding_accepts_reference_anchor_alias():
    package = {
        "task": {"task_id": "TASK-00001", "goal": "推进剧情"},
        "context": {"CHR": [{"id": "CHR-00001", "name": "主角", "summary": ""}]},
        "provenance": {"derived_from": ["OUTLINE-00001"], "source_version": 1},
        "content_hash": "sha256:deadbeef",
    }
    binding = bind_chapter_draft(package, {
        "reference_abstraction": {
            "id": "REFABSTRACT-001",
            "kind": "reference_lm_abstraction",
            "market_positioning": {"core_promise": "强钩子开局"},
        }
    })
    assert "reference_anchor" in binding.values()
    assert binding.values()["reference_anchor"]["id"] == "REFABSTRACT-001"
