"""test_speech.py — Character Speech Profiles, the authored expression layer (roadmap §15).

Pins the §15 invariants: the Speech Profile is an AUTHORED input (absent /
pristine is not an error), its schema rejects malformed profiles and carries the
gating/authority const, its rendered block carries the six voice axes, and — the
load-bearing guarantee — a serial with NO profiles produces byte-identical drafts
to v6 (profiles are purely additive), while authoring a profile for a character
who APPEARS in a chapter changes that chapter's draft (the consumer is real). It
is the direct remedy for the §14 finding that all models wrote one uniform voice.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import yaml

from runtime import compiler
from runtime.pipeline import build_task_package
from runtime.serialize import run_serial
from runtime.prompt.binding import bind_chapter_draft
from runtime.speech.loader import (load_speech, validate_speech,
                                   speech_path, speech_profiles_by_id,
                                   render_speech_profiles)

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
    """A minimal serial project with two leads (CHR-00001 central, CHR-00002 major)
    who both participate in every event, so a per-character voice test is meaningful."""
    facts, meta = root / "registry" / "facts", root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "埃德里克", "status": "active",
        "fact_version": 1, "importance": "central"})
    _write(facts / "characters" / "CHR-00002.yaml", {
        "id": "CHR-00002", "name": "马伦", "status": "active",
        "fact_version": 1, "importance": "major"})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001", "CHR-00002"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章"})


_VALID = {
    "kind": "character_speech_profile", "authority": "human", "gating": False,
    "schema_version": "1.0",
    "profiles": [
        {"character_id": "CHR-00002", "name": "马伦",
         "vocabulary": {"register": "colloquial",
                        "signature_words": ["废铁", "该还的债"], "avoids": ["华丽辞藻"]},
         "sentence": {"length": "short", "style": "直接、少修饰"},
         "verbal_habits": ["习惯用反问", "不叫敬称"],
         "taboo": ["不会主动示弱"],
         "thinking_pattern": "务实、先算代价",
         "emotion_default": "沉静克制"},
    ],
}


def _author_speech(root: Path, profiles: dict):
    (root / "sources").mkdir(parents=True, exist_ok=True)
    speech_path(root).write_text(
        yaml.safe_dump(profiles, allow_unicode=True, sort_keys=False), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Schema: an authored profile is validated; malformed is rejected             #
# --------------------------------------------------------------------------- #
def test_valid_profiles_pass_schema():
    assert validate_speech(_VALID, standard_root=STANDARD) == []


def test_unknown_field_is_rejected():
    bad = dict(_VALID, surprise="nope")
    errs = validate_speech(bad, standard_root=STANDARD)
    assert any("Additional properties" in e for e in errs)


def test_bad_register_enum_is_rejected():
    bad = {**_VALID, "profiles": [
        {**_VALID["profiles"][0],
         "vocabulary": {"register": "fancy"}}]}
    errs = validate_speech(bad, standard_root=STANDARD)
    assert any("register" in e for e in errs)


def test_bad_character_id_pattern_is_rejected():
    bad = {**_VALID, "profiles": [
        {"character_id": "MAREN", "name": "马伦"}]}
    errs = validate_speech(bad, standard_root=STANDARD)
    assert any("character_id" in e for e in errs)


def test_gating_and_authority_const_enforced():
    # gating must be false, authority must be human (the ADR-003 / ADR-009 consts)
    assert validate_speech(dict(_VALID, gating=True), standard_root=STANDARD)
    assert validate_speech(dict(_VALID, authority="ai"), standard_root=STANDARD)


# --------------------------------------------------------------------------- #
# Render: the block carries the six voice axes                                #
# --------------------------------------------------------------------------- #
def test_render_carries_the_six_axes():
    block = render_speech_profiles(_VALID["profiles"])
    assert "马伦" in block
    assert "废铁" in block                 # signature word (vocabulary)
    assert "华丽辞藻" in block             # avoids
    assert "直接、少修饰" in block          # sentence style
    assert "习惯用反问" in block           # verbal habit
    assert "不会主动示弱" in block          # taboo
    assert "务实、先算代价" in block        # thinking pattern
    assert "沉静克制" in block             # emotion default


def test_render_empty_is_a_neutral_sentinel():
    # empty => a stable neutral-voice sentinel (the v7 slot is always bound),
    # mirroring render_character_runtime's empty case — not a render failure.
    out = render_speech_profiles([])
    assert out and "中性声音" in out


def test_index_by_id():
    idx = speech_profiles_by_id(_VALID)
    assert set(idx) == {"CHR-00002"}
    assert speech_profiles_by_id(None) == {}


# --------------------------------------------------------------------------- #
# Loader: absence / pristine is not an error                                  #
# --------------------------------------------------------------------------- #
def test_absent_profiles_returns_none(tmp_path):
    assert load_speech(tmp_path) is None
    assert speech_path(tmp_path).name == "character-speech-profiles.yaml"


def test_all_commented_parses_as_absent(tmp_path):
    (tmp_path / "sources").mkdir()
    speech_path(tmp_path).write_text(
        "# kind: character_speech_profile\n# profiles: []\n", encoding="utf-8")
    assert load_speech(tmp_path) is None


# --------------------------------------------------------------------------- #
# Binding allowlist: v1-v6 binding is byte-identical with or without the var   #
# --------------------------------------------------------------------------- #
def test_binding_omits_speech_profiles_unless_supplied(tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(FIXTURE, project)
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00070", "draft", "ChapterDraft",
                                     ["CHR-00001", "EVT-00002"]),
        out_dir=tmp_path / "build")
    assert r.ok, r.message
    b_plain = bind_chapter_draft(r.package, {})
    assert "speech_profiles" not in b_plain.variables
    b_spk = bind_chapter_draft(r.package, {"speech_profiles": "马伦：口语"})
    assert "speech_profiles" in b_spk.variables
    assert b_plain.hash_payload() != b_spk.hash_payload()


# --------------------------------------------------------------------------- #
# Load-bearing guarantee: profiles are ADDITIVE — no profile => byte-identical  #
# to v6; a profile for an APPEARING character changes that chapter's draft      #
# --------------------------------------------------------------------------- #
def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_v6_is_frozen_regardless_of_authored_speech():
    # The load-bearing freeze (v6 precedent): authoring a Speech Profile source
    # must NOT change a v6 run — v6 never reads speech. Only v7 consumes it.
    tmp = Path(tempfile.mkdtemp(prefix="anes-speech-"))
    try:
        plain, authored = tmp / "plain", tmp / "authored"
        _scaffold(plain, 3)
        _scaffold(authored, 3)
        _author_speech(authored, _VALID)
        r_plain = _run(plain, prompt_version="6.0.0")
        r_authored = _run(authored, prompt_version="6.0.0")
        assert r_plain.produced == r_authored.produced == 3
        assert [c.draft_hash for c in r_plain.chapters] == [c.draft_hash for c in r_authored.chapters]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_v7_without_profiles_is_deterministic_and_never_gates():
    # v7 is intentionally a DIFFERENT template from v6 (it carries the speech slot),
    # so v7 != v6. The guarantee here is that v7 with NO profiles is a stable,
    # reproducible degradation (the neutral-voice sentinel) and never gates.
    tmp = Path(tempfile.mkdtemp(prefix="anes-speech-"))
    try:
        a, b = tmp / "a", tmp / "b"
        _scaffold(a, 3)
        _scaffold(b, 3)
        ra = _run(a, prompt_version="7.0.0")
        rb = _run(b, prompt_version="7.0.0")
        assert ra.produced == rb.produced == 3
        assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]
        assert ra.gating is False and rb.gating is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_authoring_a_profile_for_an_appearing_character_changes_the_draft():
    tmp = Path(tempfile.mkdtemp(prefix="anes-speech-"))
    try:
        base, spk = tmp / "base", tmp / "spk"
        _scaffold(base, 3)
        _scaffold(spk, 3)
        _author_speech(spk, _VALID)          # CHR-00002 appears in every event
        r_base = _run(base, prompt_version="7.0.0")
        r_spk = _run(spk, prompt_version="7.0.0")
        assert r_base.produced == r_spk.produced == 3
        # the language block flowed into the prompt => the deterministic drafts differ
        assert [c.draft_hash for c in r_base.chapters] != [c.draft_hash for c in r_spk.chapters]
        # state is a fold of the SAME facts => per-chapter state hashes unchanged
        assert [c.state_hash for c in r_base.chapters] == [c.state_hash for c in r_spk.chapters]
        assert r_spk.gating is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_profile_for_a_non_appearing_character_is_a_noop():
    # A profile whose character never appears binds nothing => byte-identical to
    # no profiles at all (clean degradation, matched by appearance not authorship).
    tmp = Path(tempfile.mkdtemp(prefix="anes-speech-"))
    try:
        base, ghost = tmp / "base", tmp / "ghost"
        _scaffold(base, 3)
        _scaffold(ghost, 3)
        _author_speech(ghost, {**_VALID, "profiles": [
            {"character_id": "CHR-09999", "name": "幽灵",
             "vocabulary": {"register": "archaic"}}]})
        r_base = _run(base, prompt_version="7.0.0")
        r_ghost = _run(ghost, prompt_version="7.0.0")
        assert [c.draft_hash for c in r_base.chapters] == [c.draft_hash for c in r_ghost.chapters]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
