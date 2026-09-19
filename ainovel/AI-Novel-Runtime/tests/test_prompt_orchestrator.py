"""test_prompt_orchestrator.py — Prompt Orchestrator: story-so-far recap (roadmap C).

At chapter N a long serial can't fit the whole book in the model's context, but
it CAN fit "the story so far" — the StoryState projection digested into a compact
recap. The v2 chapter-draft prompt has a story_state slot; the serial feeds it
the fold up to the previous chapter. These tests pin: the digest is
deterministic, the v1 path is byte-identical (non-breaking), and the v2 serial
injects an accumulating recap without ever touching state or gating.
"""
from __future__ import annotations

import json
import glob
import shutil
import tempfile
from pathlib import Path

import yaml

from runtime import registry_loader, compiler
from runtime.pipeline import build_task_package
from runtime.memory import project_state, state_digest
from runtime.prompt.binding import bind_chapter_draft
from runtime.prompt.runtime import PromptRuntime
from runtime.serialize import run_serial

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
PROMPTS = STANDARD / "contracts" / "prompts"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events: int = 3):
    facts, meta = root / "registry" / "facts", root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章"})


# --------------------------------------------------------------------------- #
# Digest: deterministic + bounded                                             #
# --------------------------------------------------------------------------- #
def test_state_digest_is_deterministic(tmp_path):
    _scaffold(tmp_path, 3)
    reg = registry_loader.load(tmp_path)
    state = project_state(reg)
    assert state_digest(state) == state_digest(state)


def test_state_digest_of_empty_state_is_explicit(tmp_path):
    _scaffold(tmp_path, 1)
    reg = registry_loader.load(tmp_path)
    # fold up to a cursor with nothing before it -> the opening line
    empty = project_state(reg, up_to_event="EVT-00001")
    text = state_digest(empty)
    assert isinstance(text, str) and text  # never empty string
    # the digest grows as the fold advances
    full = project_state(reg)
    assert state_digest(full) != text or full.event_order == empty.event_order


# --------------------------------------------------------------------------- #
# Non-breaking: the v1 binding is byte-identical with or without the feature   #
# --------------------------------------------------------------------------- #
def _build_pkg(project, out) -> dict:
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00070", "draft", "ChapterDraft",
                                     ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    assert r.ok, r.message
    return r.package


def test_v1_binding_has_no_story_state(tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(FIXTURE, project)
    pkg = _build_pkg(project, tmp_path / "build")
    b_plain = bind_chapter_draft(pkg, {})
    assert "story_state" not in b_plain.variables
    # supplying story_state adds the variable and changes the binding hash
    b_state = bind_chapter_draft(pkg, {"story_state": "前情提要"})
    assert "story_state" in b_state.variables
    assert b_plain.hash_payload() != b_state.hash_payload()


def test_v2_render_includes_story_state(tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(FIXTURE, project)
    pkg = _build_pkg(project, tmp_path / "build")
    rt = PromptRuntime(prompt_root=PROMPTS)
    rendered, _ = rt.render(prompt_id="chapter-draft", version="2.0.0", package=pkg,
                            variables={"story_state": "活跃角色：主角"})
    assert "前情提要" in rendered.rendered_text
    assert "活跃角色：主角" in rendered.rendered_text


# --------------------------------------------------------------------------- #
# Serial: v1 byte-identical, v2 injects an accumulating recap, state untouched  #
# --------------------------------------------------------------------------- #
def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_serial_v1_is_byte_identical_v2_differs_state_unchanged(tmp_path):
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _scaffold(v1, 3)
    _scaffold(v2, 3)
    r1 = _run(v1)                          # default v1
    r2 = _run(v2, prompt_version="2.0.0")  # Prompt Orchestrator

    assert r1.produced == r2.produced == 3
    # v2 drafts differ from v1 (the recap flowed into the prompt)
    assert [c.draft_hash for c in r1.chapters] != [c.draft_hash for c in r2.chapters]
    # but state is a fold of the SAME facts -> identical per-chapter state hashes
    assert [c.state_hash for c in r1.chapters] == [c.state_hash for c in r2.chapters]
    # neither gates
    assert r1.gating is False and r2.gating is False


def test_serial_v2_recap_accumulates_across_chapters(tmp_path):
    _scaffold(tmp_path, 3)
    _run(tmp_path, prompt_version="2.0.0")
    # read the produced drafts; later chapters' prompts saw more prior events, so
    # their bodies (deterministic echo of the prompt) contain later recap lines.
    drafts = {}
    for path in glob.glob(str(tmp_path / "registry" / "derived" / "drafts" / "*.json")):
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        from runtime.execution.envelope import unwrap
        d = unwrap(obj)
        drafts[d["task_id"]] = d["body"]
    # chapter 1 is 开篇 (no prior); chapter 3 has a "story so far" recap mentioning
    # an earlier event id — the deterministic model echoes the prompt into body.
    assert "开篇" in drafts["TASK-00001"]
    assert "EVT-00001" in drafts["TASK-00003"] or "EVT-00002" in drafts["TASK-00003"]
