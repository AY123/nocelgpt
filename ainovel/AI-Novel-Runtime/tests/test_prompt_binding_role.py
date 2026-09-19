from runtime.prompt.binding import bind_chapter_draft


PACKAGE = {
    "task": {"task_id": "TASK-1", "goal": "write chapter", "capability": "ChapterDraft"},
    "content_hash": "sha256:" + "a" * 64,
    "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
    "context": {"characters": [{"id": "CHR-00001", "name": "主角"}]},
}


def test_bind_chapter_role_and_length_defaults():
    binding = bind_chapter_draft(PACKAGE, {})
    assert binding.variables["chapter_role"].value == "advance"
    assert binding.variables["target_length_cjk"].value == 700


def test_bind_chapter_role_and_length_override():
    binding = bind_chapter_draft(PACKAGE, {"chapter_role": "hook", "target_length_cjk": 1200})
    assert binding.variables["chapter_role"].value == "hook"
    assert binding.variables["target_length_cjk"].value == 1200


def test_reader_signal_absent_keeps_binding_byte_identical():
    """Phase B preparation seam: reader_signal/platform_feedback are the READ side
    of a Phase B feature whose only writer lived in the (now-deleted) shadow
    serialize.py — so nothing feeds them yet. This locks the dormant contract:
    with neither key supplied, the binding is byte-identical to one produced
    before these variables existed (proxied by an equivalent extra without them),
    so every current render is unaffected. Same discipline as story_state /
    scene_plan / long_arc."""
    base_extra = {"chapter_role": "advance", "target_length_cjk": 700}
    without = bind_chapter_draft(PACKAGE, base_extra)
    # Explicitly passing the keys as None must behave exactly like omitting them.
    with_none = bind_chapter_draft(
        PACKAGE, {**base_extra, "reader_signal": None, "platform_feedback": None})

    assert "reader_signal" not in without.variables
    assert "platform_feedback" not in without.variables
    assert without.hash_payload() == with_none.hash_payload()


def test_reader_signal_present_binds_only_those_keys():
    """When Phase B eventually feeds these, they appear as runtime variables and
    add nothing else — the delta over the dormant binding is exactly two keys."""
    base_extra = {"chapter_role": "advance", "target_length_cjk": 700}
    without = bind_chapter_draft(PACKAGE, base_extra)
    binding = bind_chapter_draft(PACKAGE, {
        **base_extra,
        "reader_signal": "读者反馈：节奏偏慢，希望更快进入冲突",
        "platform_feedback": "平台：首章跳出率偏高",
    })

    assert binding.variables["reader_signal"].source == "runtime"
    assert binding.variables["platform_feedback"].source == "runtime"
    added = set(binding.variables) - set(without.variables)
    assert added == {"reader_signal", "platform_feedback"}
