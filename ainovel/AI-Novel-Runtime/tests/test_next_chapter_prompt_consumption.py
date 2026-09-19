from pathlib import Path

from runtime.prompt.binding import bind_chapter_draft
from runtime.prompt.renderer import render_template
from runtime.prompt.types import PromptVersion


def _package():
    return {
        "task": {"task_id": "TASK-00002", "goal": "推进冲突", "capability": "ChapterDraft"},
        "context": {},
        "content_hash": "sha256:package",
        "provenance": {"derived_from": [], "source_version": 1},
    }


def _prompt():
    return PromptVersion(
        prompt_id="chapter-draft", version="test", capability="ChapterDraft", engine="format",
        source_path="test", source_hash="sha256:template", required_variables=["task_id", "goal"],
        optional_variables=["approved_state"], messages=[{"role": "user", "content": "{task_id}|{approved_state}"}],
    )


def test_approved_state_uses_existing_binding_and_changes_manifest_inputs():
    package = _package()
    absent = bind_chapter_draft(package)
    present = bind_chapter_draft(package, {"approved_state": "mint=EVT-00031; state=sha256:after"})
    assert "approved_state" not in absent.variables
    assert present.variables["approved_state"].source == "runtime"
    a = render_template(_prompt(), absent)
    b = render_template(_prompt(), present)
    assert "TASK-00002|" in a.rendered_text
    assert "EVT-00031" in b.rendered_text
    assert a.binding_hash != b.binding_hash
    assert a.rendered_hash != b.rendered_hash
