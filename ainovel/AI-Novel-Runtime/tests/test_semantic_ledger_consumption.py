"""Tests that the semantic ledger flows into the next-chapter prompt binding."""
from runtime.director import render_semantic_ledger
from runtime.outline.ledgers import build_semantic_ledger
from runtime.prompt.binding import bind_chapter_draft
from runtime.prompt.renderer import render_template
from runtime.prompt.types import PromptVersion


OUTLINE = {
    "first_30_chapters": [
        {"chapter_no": 1, "goal": "开局", "end_hook": "悬念1", "reward_if_any": "奖励1"},
        {"chapter_no": 2, "goal": "推进", "end_hook": "悬念2", "reward_if_any": ""},
        {"chapter_no": 3, "goal": "翻身", "end_hook": "悬念3", "reward_if_any": "奖励3"},
    ],
    "characters": [
        {"role": "protagonist", "name": "林照夜", "arc": "从求生者到秩序重建者", "motivation": "重建秩序"},
        {"role": "rival", "name": "沈无咎", "arc": "从对抗到理解", "motivation": "维护旧秩序"},
    ],
    "protagonist_engine": {"desire": "成为掌局者", "flaw": "不敢信任他人"},
}


def _package():
    return {
        "task": {"task_id": "TASK-00003", "goal": "推进冲突", "capability": "ChapterDraft"},
        "context": {},
        "content_hash": "sha256:package",
        "provenance": {"derived_from": [], "source_version": 1},
    }


def _prompt():
    return PromptVersion(
        prompt_id="chapter-draft", version="test", capability="ChapterDraft", engine="format",
        source_path="test", source_hash="sha256:template",
        required_variables=["task_id", "goal"],
        optional_variables=["semantic_ledger"],
        messages=[{"role": "user", "content": "{task_id}|{semantic_ledger}"}],
    )


def test_render_semantic_ledger_is_nonempty_for_real_outline():
    ledger = build_semantic_ledger(OUTLINE).to_dict()
    block = render_semantic_ledger(ledger)
    assert "【知识】" in block
    assert "【承诺】" in block
    assert "P-01" in block


def test_render_semantic_ledger_empty_for_empty_ledger():
    block = render_semantic_ledger({})
    assert block == ""


def test_semantic_ledger_changes_prompt_binding_and_render():
    package = _package()
    ledger = build_semantic_ledger(OUTLINE).to_dict()
    block = render_semantic_ledger(ledger)

    absent = bind_chapter_draft(package)
    present = bind_chapter_draft(package, {"semantic_ledger": block})

    assert "semantic_ledger" not in absent.variables
    assert present.variables["semantic_ledger"].source == "runtime"

    a = render_template(_prompt(), absent)
    b = render_template(_prompt(), present)

    assert a.binding_hash != b.binding_hash
    assert a.rendered_hash != b.rendered_hash
    assert "P-01" in b.rendered_text
