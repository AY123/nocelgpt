"""test_brain.py — Novel Brain, the authored static constitution (roadmap P15).

Pins the P15 invariants: the Brain is an AUTHORED input (absent is not an error),
its schema rejects malformed constitutions, its style directive carries writing +
forbidden style, and — the load-bearing guarantee — a project with NO Brain
produces a byte-identical deterministic draft (Brain is purely additive).
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from runtime import compiler
from runtime.pipeline import build_task_package
from runtime.execution.run import execute_package
from runtime.brain.loader import (load_brain, validate_brain,
                                   brain_style_directive, brain_path)

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


_VALID_BRAIN = {
    "id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0",
    "mission": "让读者一口气追到天亮",
    "genre": {"primary": "玄幻", "channel": "男频"},
    "target_reader": {"who": "18-30岁男性", "wants": ["越级战斗"], "avoids": ["注水"]},
    "promise": "每三章一个高潮",
    "writing_style": {"voice": "冷峻克制的第三人称", "pov": "第三人称限知",
                      "pacing": "快", "devices": ["悬念钩子"]},
    "forbidden_style": ["注水", "主角龟缩"],
}


# --------------------------------------------------------------------------- #
# Schema: an authored constitution is validated; malformed is rejected         #
# --------------------------------------------------------------------------- #
def test_valid_brain_passes_schema():
    assert validate_brain(_VALID_BRAIN, standard_root=STANDARD) == []


def test_unknown_field_is_rejected():
    bad = dict(_VALID_BRAIN, surprise="nope")
    errs = validate_brain(bad, standard_root=STANDARD)
    assert any("Additional properties" in e for e in errs)


def test_missing_required_field_is_rejected():
    bad = {k: v for k, v in _VALID_BRAIN.items() if k != "mission"}
    errs = validate_brain(bad, standard_root=STANDARD)
    assert any("mission" in e for e in errs)


def test_forbidden_style_must_be_non_empty():
    bad = dict(_VALID_BRAIN, forbidden_style=[])
    errs = validate_brain(bad, standard_root=STANDARD)
    assert errs  # minItems: 1


# --------------------------------------------------------------------------- #
# Style directive: carries writing_style + forbidden_style                     #
# --------------------------------------------------------------------------- #
def test_style_directive_includes_writing_and_forbidden():
    d = brain_style_directive(_VALID_BRAIN)
    assert "冷峻克制的第三人称" in d      # voice
    assert "第三人称限知" in d            # pov
    assert "注水" in d and "主角龟缩" in d  # forbidden
    assert "Never:" in d


def test_style_directive_falls_back_when_empty():
    assert brain_style_directive({}) == "neutral literary prose"


# --------------------------------------------------------------------------- #
# Loader: absence is not an error                                              #
# --------------------------------------------------------------------------- #
def test_absent_brain_returns_none(tmp_path):
    assert load_brain(tmp_path) is None
    assert brain_path(tmp_path).name == "novel-brain.yaml"


def test_all_commented_brain_parses_as_absent(tmp_path):
    # the scaffolded template is fully commented => yaml parses to None => treated
    # exactly like an absent Brain (no false "invalid" on a pristine project)
    (tmp_path / "sources").mkdir()
    brain_path(tmp_path).write_text("# just comments\n# id: BRAIN-00001\n",
                                    encoding="utf-8")
    assert load_brain(tmp_path) is None


# --------------------------------------------------------------------------- #
# Load-bearing guarantee: Brain is ADDITIVE — no Brain => byte-identical draft  #
# --------------------------------------------------------------------------- #
def _build(project, out) -> dict:
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00042", "draft chapter 42",
                                     "ChapterDraft", ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    assert r.ok, r.message
    return r.package


def test_no_brain_is_byte_identical_and_brain_changes_the_draft():
    tmp = Path(tempfile.mkdtemp(prefix="anes-brain-"))
    try:
        project = tmp / "proj"
        shutil.copytree(FIXTURE, project)
        package = _build(project, tmp / "build")

        # 1) no Brain authored -> the draft hash is what the loop always produced
        r_none = execute_package(package=package, standard_root=STANDARD,
                                 project_path=project)
        assert r_none.ok, r_none.message
        hash_without_brain = r_none.artifact["content_hash"]

        # re-run with no Brain: still byte-identical (deterministic + additive)
        r_none2 = execute_package(package=package, standard_root=STANDARD,
                                  project_path=project)
        assert r_none2.artifact["content_hash"] == hash_without_brain

        # 2) author a Brain -> the style directive flows into the prompt, so the
        #    deterministic draft body (and thus hash) changes: the consumer is real
        (project / "sources").mkdir(parents=True, exist_ok=True)
        import yaml
        brain_path(project).write_text(
            yaml.safe_dump(_VALID_BRAIN, allow_unicode=True), encoding="utf-8")
        r_brain = execute_package(package=package, standard_root=STANDARD,
                                  project_path=project)
        assert r_brain.ok, r_brain.message
        assert r_brain.artifact["content_hash"] != hash_without_brain
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
