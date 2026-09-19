"""test_genesis.py — Brain fold + genesis orchestration (ANES v2, M2 / Phase 8).

Pins the end-to-end book opening: build_brain folds a schema-valid Novel Brain
from an outline; run_genesis stitches bootstrap → Brain → land, previewing by
default (no facts) and minting only on confirm (ADR-009); the opened project can
run a long serial and carries a Brain.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from runtime.outline.agents import (propose_candidates, review_candidate,
                                    synthesize_final_outline)
from runtime.genesis import build_brain, write_brain, run_genesis
from runtime.brain.loader import validate_brain, load_brain, brain_path
from runtime.positioning import (build_position, write_position, validate_position,
                                 load_position, position_path)
from runtime.serialize.loop import plan_chapters
from runtime import registry_loader

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = str(STANDARD / "phase-1" / "generated" / "json-schema")

_MERGED = {"genre_signals": ["玄幻"], "reader_rewards": ["实力突破", "打脸翻身"],
           "structure_signals": ["linear"], "originality_guardrails": ["no-copy"]}


def _outline():
    c = propose_candidates(_MERGED)
    r = [review_candidate(x, _MERGED) for x in c]
    return synthesize_final_outline(c, r, _MERGED, "proj-genesis", [])


def _project_with_reference() -> Path:
    proj = Path(tempfile.mkdtemp(prefix="genesis-cmd-"))
    (proj / "sources" / "reference-novels").mkdir(parents=True)
    meta = proj / "registry" / "_meta"
    meta.mkdir(parents=True)
    meta.joinpath("project-id").write_text("novel\n", encoding="utf-8")
    meta.joinpath("registry-version").write_text("1\n", encoding="utf-8")
    meta.joinpath("standard.pin").write_text("2.0.0\n", encoding="utf-8")
    (proj / "sources" / "reference-novels" / "ref.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。"
        "他发现秘密线索，突破境界并赢得第一次胜利。" * 3, encoding="utf-8")
    return proj


# --------------------------------------------------------------------------- #
# Brain fold                                                                  #
# --------------------------------------------------------------------------- #
def test_folded_brain_is_schema_valid():
    brain = build_brain(_outline())
    assert validate_brain(brain, standard_root=STANDARD) == []
    assert brain["forbidden_style"]                     # >=1 (schema minItems)
    assert brain["genre"]["primary"] and brain["mission"] and brain["promise"]


def test_brain_fold_is_deterministic():
    assert build_brain(_outline()) == build_brain(_outline())


def test_write_brain_refuses_to_clobber_authored_brain():
    proj = Path(tempfile.mkdtemp(prefix="genesis-brain-"))
    try:
        brain = build_brain(_outline())
        write_brain(proj, brain, standard_root=STANDARD)
        assert load_brain(proj)["id"] == brain["id"]
        with pytest.raises(FileExistsError):
            write_brain(proj, brain, standard_root=STANDARD)
        write_brain(proj, brain, standard_root=STANDARD, overwrite=True)  # ok
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Orchestration: preview vs confirm                                           #
# --------------------------------------------------------------------------- #
def test_genesis_preview_writes_no_facts():
    proj = _project_with_reference()
    try:
        r = run_genesis(proj, schema_dir=SCHEMA, standard_root=STANDARD, confirm=False)
        assert r.ok and r.stage == "preview"
        assert r.events_planned >= 30
        assert r.brain_written and brain_path(proj).exists()   # brain is a draft, not a fact
        assert r.preview_count > 0
        # ADR-009: preview crosses no boundary — no facts on disk
        assert not list((proj / "registry" / "facts").rglob("*.yaml"))
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_genesis_confirm_opens_a_runnable_book():
    proj = _project_with_reference()
    try:
        # preview then confirm (same second → exercises the run-dir disambiguation)
        run_genesis(proj, schema_dir=SCHEMA, standard_root=STANDARD, confirm=False)
        r = run_genesis(proj, schema_dir=SCHEMA, standard_root=STANDARD,
                        confirm=True, actor="test")
        assert r.ok and r.stage == "landed" and r.landed
        assert r.receipt_id and r.minted_count >= 30
        # the opened project runs a long serial (the §14.4 unlock)
        reg = registry_loader.load(proj, schema_dir=SCHEMA)
        assert len(plan_chapters(reg)) >= 30
        # and carries a Brain
        assert load_brain(proj) is not None
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Market Position fold + admission wiring (M2-B3)                              #
# --------------------------------------------------------------------------- #
def test_folded_position_is_schema_valid():
    pos = build_position(_outline())
    assert validate_position(pos, standard_root=STANDARD) == []
    # the three admission-scored blocks are populated, not stubs
    assert pos["reader_segment"]["primary"]
    assert pos["trope_map"]["leans_on"]                 # >=1 (schema minItems)
    cp = pos["commercial_promise"]
    assert cp["pay_trigger"] and cp["first_30_hook"] and cp["sustainability_100"]


def test_position_fold_is_deterministic():
    assert build_position(_outline()) == build_position(_outline())


def test_position_channel_agrees_with_brain():
    # a folded Position and Brain must not disagree on channel — that would be a
    # false admission conflict (both default 男频 for a 玄幻 outline).
    outline = _outline()
    assert build_position(outline)["channel"] == build_brain(outline)["genre"]["channel"]


def test_write_position_refuses_to_clobber_authored_position():
    proj = Path(tempfile.mkdtemp(prefix="genesis-pos-"))
    try:
        pos = build_position(_outline())
        write_position(proj, pos, standard_root=STANDARD)
        assert load_position(proj)["id"] == pos["id"]
        with pytest.raises(FileExistsError):
            write_position(proj, pos, standard_root=STANDARD)
        write_position(proj, pos, standard_root=STANDARD, overwrite=True)  # ok
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_genesis_folds_position_and_runs_admission():
    """M2-B3: genesis now closes the 参考→开书→市场准入 chain. The previously
    built-but-dead positioning + admission fold runs on the open-book path: a
    Position is written to sources/ and an admission verdict is pinned + surfaced,
    without crossing the ADR-009 boundary (no facts)."""
    proj = _project_with_reference()
    try:
        r = run_genesis(proj, schema_dir=SCHEMA, standard_root=STANDARD, confirm=False)
        assert r.ok and r.stage == "preview"
        # Position folded + written under sources/ (an authored input, not a fact)
        assert r.position_written and position_path(proj).exists()
        assert validate_position(load_position(proj), standard_root=STANDARD) == []
        # admission ran and produced an advisory verdict (was always 'hold' before)
        assert r.admission_recommendation in {"admit", "revise", "hold"}
        assert r.admission_recommendation != "hold", "a folded Position should not hold"
        assert r.admission_id and r.admission_rationale
        # verdict pinned as a DERIVED artifact (ADR-006), never a fact (ADR-009)
        assert (proj / "registry" / "derived" / "market-admission"
                / f"{r.admission_id}.json").exists()
        assert not list((proj / "registry" / "facts").rglob("*.yaml"))
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)
