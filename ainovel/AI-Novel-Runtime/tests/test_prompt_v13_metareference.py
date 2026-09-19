"""test_prompt_v13_metareference.py — v13 generation-side metareference prevention.

This bump is intentionally narrow:
  - v12 stays unchanged and remains the old path.
  - v13 adds only the new generation-side anti-leak instruction.
  - the runtime wiring must still render the real prompt end-to-end.
  - the advisory meta_reference detector remains advisory and never gates.
"""
from __future__ import annotations

from pathlib import Path

from runtime.prompt.loader import PromptLoader
from runtime.prompt.binding import bind_chapter_draft
from runtime.prompt.renderer import render_template
from runtime.prompt.runtime import PromptRuntime
from runtime.execution.meta_reference import check_meta_reference

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent.parent / "AI-Novel-Standard" / "contracts" / "prompts"


def _package() -> dict:
    return {
        "task": {"task_id": "TASK-1", "goal": "推进剧情", "capability": "ChapterDraft"},
        "content_hash": "sha256:" + "a" * 64,
        "provenance": {"derived_from": ["OUTLINE-0001"], "source_version": 1},
        "context": {
            "characters": [
                {"id": "CHR-00001", "name": "主角", "summary": ""},
            ]
        },
    }


def _required_variables(loader: PromptLoader, version: str) -> dict[str, str]:
    prompt = loader.load("chapter-draft", version)
    return {name: name for name in prompt.required_variables if name not in {"task_id", "goal", "context_lines", "derived_from"}}


def test_v13_adds_only_the_generation_side_meta_reference_guard():
    loader = PromptLoader(PROMPTS)
    v12 = loader.load("chapter-draft", "12.0.0")
    v13 = loader.load("chapter-draft", "13.0.0")

    assert v13.version == "13.0.0"
    assert v13.required_variables == v12.required_variables
    assert v13.optional_variables == v12.optional_variables
    system_v12 = v12.messages[0]["content"]
    system_v13 = v13.messages[0]["content"]
    # v12 must NOT contain the anti-leak instruction
    assert "meta-production" not in system_v12.lower()
    assert "上一章" not in system_v12
    # v13 MUST contain it — the generation-side prevention
    assert "meta-production" in system_v13.lower()
    assert "上一章" in system_v13 and "第 5 章" in system_v13
    assert "前文提到" in system_v13 and "本章" in system_v13
    # No new constraint on dash/simile/dialogue beyond what v12 already has
    assert "PROSE TEXTURE" in system_v13
    assert system_v13.count("破折号") == system_v12.count("破折号")
    assert system_v13.count("比喻") == system_v12.count("比喻")
    assert system_v13.count("对白") == system_v12.count("对白")


def test_v13_loads_and_renders_through_the_real_prompt_runtime():
    loader = PromptLoader(PROMPTS)
    prompt = loader.load("chapter-draft", "13.0.0")
    package = _package()
    variables = _required_variables(loader, "13.0.0")
    binding = bind_chapter_draft(package, variables)
    rendered = render_template(prompt, binding)

    assert rendered.rendered_text
    assert "上一章" in rendered.rendered_text  # as a quoted prohibition in the prompt
    assert "本章" in rendered.rendered_text


def test_v13_routes_and_detector_remain_advisory():
    rt = PromptRuntime(prompt_root=PROMPTS)
    package = _package()
    variables = _required_variables(PromptLoader(PROMPTS), "13.0.0")
    rendered, manifest = rt.render(prompt_id="chapter-draft", version="13.0.0", package=package, variables=variables)

    assert manifest.version == "13.0.0"
    assert rendered.version == "13.0.0"
    assert "meta-production" in rendered.rendered_text.lower()

    rep = check_meta_reference({"body": "上一章的伤还在。" * 6})
    assert rep.gating is False
    assert rep.findings


def test_meta_reference_flag_resolves_to_v13_and_wins():
    def resolve(ns):
        if getattr(ns, "meta_reference", False):
            return "13.0.0"
        if getattr(ns, "craft_texture", False):
            return "12.0.0"
        if getattr(ns, "anti_anaphora", False):
            return "11.0.0"
        return ns.prompt_version

    base = type("NS", (), {"prompt_version": "6.0.0", "anti_anaphora": False, "craft_texture": False, "meta_reference": False})()
    assert resolve(base) == "6.0.0"
    base.craft_texture = True
    assert resolve(base) == "12.0.0"
    base.meta_reference = True
    assert resolve(base) == "13.0.0"


def test_v12_remains_byte_identical_to_old_path_source():
    loader = PromptLoader(PROMPTS)
    v12 = loader.load("chapter-draft", "12.0.0")
    v11 = loader.load("chapter-draft", "11.0.0")
    # old path unchanged; the new prompt is a separate major version
    assert v11.source_hash != v12.source_hash or v11.version != v12.version
    assert v12.source_hash == loader.load("chapter-draft", "12.0.0").source_hash
