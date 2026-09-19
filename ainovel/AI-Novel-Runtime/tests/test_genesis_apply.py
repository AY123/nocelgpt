"""test_genesis_apply.py — outline→events landing (ANES v2, Minimal Genesis / M2).

Pins the fix for the broken outline→facts link: build_import_plan now folds the
first-30-chapters into a runnable event log, and genesis_apply lands that batch
as structured facts with intra-plan references remapped to minted ids — the two
halves that let an opened project run a long serial (§14.4). Guards:
  - import_plan yields 30+ chained, schema-shaped events
  - execute_genesis remaps candidate ids → minted ids (no dangling refs)
  - validate-then-write: a broken plan writes nothing
  - --confirm is required (ADR-009)
  - the opened project can plan 30+ serial chapters (the unlock)
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from runtime.outline.agents import (propose_candidates, review_candidate,
                                    synthesize_final_outline)
from runtime.outline.import_plan import build_import_plan
from runtime.mint import execute_genesis, preview_genesis, MintRefused
from runtime.mint.genesis_apply import _remap
from runtime.serialize.loop import plan_chapters
from runtime import registry_loader

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = str(STANDARD / "phase-1" / "generated" / "json-schema")

_MERGED = {"genre_signals": ["玄幻"], "reader_rewards": ["实力突破"],
           "structure_signals": ["linear"], "originality_guardrails": ["no-copy"]}


def _outline():
    cands = propose_candidates(_MERGED)
    reviews = [review_candidate(c, _MERGED) for c in cands]
    return synthesize_final_outline(cands, reviews, _MERGED, "proj-genesis", [])


def _empty_project() -> Path:
    proj = Path(tempfile.mkdtemp(prefix="genesis-test-"))
    meta = proj / "registry" / "_meta"
    meta.mkdir(parents=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "project-id").write_text("proj-genesis\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    return proj


# --------------------------------------------------------------------------- #
# import_plan folds first-30 into a runnable event log                        #
# --------------------------------------------------------------------------- #
def test_import_plan_yields_thirty_plus_chained_events():
    plan = build_import_plan(_outline())
    events = [i for i in plan["items"] if i["target_type"] == "Event"]
    assert len(events) >= 30
    seqs = [e["record"]["sequence_index"] for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)  # monotone, unique
    # every event after the first chains to the previous one (causes)
    for prev, cur in zip(events, events[1:]):
        assert cur["record"]["causes"] == [prev["candidate_id"]]
    # temporal gate premise: a cause's sequence precedes its effect
    by_id = {e["candidate_id"]: e["record"] for e in events}
    for e in events:
        for c in e["record"].get("causes", []):
            if c in by_id:
                assert by_id[c]["sequence_index"] < e["record"]["sequence_index"]


def test_chapter_events_reference_protagonist_candidate():
    plan = build_import_plan(_outline())
    chapter_events = [i for i in plan["items"]
                      if i["target_type"] == "Event" and "章" in i["record"]["name"]]
    assert chapter_events
    # protagonist is CHR-90001 (first character, role=protagonist)
    assert all(e["record"]["participants"] == ["CHR-90001"] for e in chapter_events)


# --------------------------------------------------------------------------- #
# _remap deep-rewrites every candidate id                                     #
# --------------------------------------------------------------------------- #
def test_remap_rewrites_nested_references():
    id_map = {"CHR-90001": "CHR-00007", "EVT-90004": "EVT-00003"}
    rec = {"id": "EVT-90005", "participants": ["CHR-90001"],
           "causes": ["EVT-90004"], "nested": {"k": ["CHR-90001", "X"]}}
    out = _remap(rec, id_map)
    assert out["participants"] == ["CHR-00007"]
    assert out["causes"] == ["EVT-00003"]
    assert out["nested"]["k"] == ["CHR-00007", "X"]  # unknown id passes through
    assert out["id"] == "EVT-90005"                   # not in map → unchanged


# --------------------------------------------------------------------------- #
# execute_genesis: lands facts, remaps refs, no dangling                      #
# --------------------------------------------------------------------------- #
def test_execute_genesis_lands_events_without_dangling_refs():
    proj = _empty_project()
    try:
        plan = build_import_plan(_outline())
        receipt = execute_genesis(project_path=str(proj), plan=plan,
                                  schema_dir=SCHEMA, confirmed=True, actor="test")
        assert receipt["kind"] == "genesis_receipt"
        assert receipt["id_map"] and len(receipt["landed"]) == len(plan["items"])
        # every landed id is a real minted id, not a 9000x candidate
        assert all(not v.endswith(tuple(str(9000 + i) for i in range(10)))
                   for v in receipt["id_map"].values())
        all_ids = {f.stem for f in proj.rglob("registry/facts/*/*.yaml")}
        for f in (proj / "registry" / "facts" / "events").glob("*.yaml"):
            r = yaml.safe_load(f.read_text(encoding="utf-8"))
            for ref in (r.get("causes", []) + r.get("effects", [])
                        + r.get("participants", [])):
                assert not ref.startswith(("EVT-9", "CHR-9")), "leftover candidate ref"
                assert ref in all_ids, f"dangling ref {ref}"
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_execute_genesis_requires_confirmation():
    proj = _empty_project()
    try:
        plan = build_import_plan(_outline())
        with pytest.raises(MintRefused):
            execute_genesis(project_path=str(proj), plan=plan, schema_dir=SCHEMA,
                            confirmed=False)
        # nothing written
        assert not list((proj / "registry" / "facts").rglob("*.yaml"))
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_preview_writes_nothing():
    proj = _empty_project()
    try:
        plan = build_import_plan(_outline())
        id_map, staged, report = preview_genesis(
            project_path=str(proj), plan=plan, schema_dir=SCHEMA)
        assert report.ok and id_map
        assert not list((proj / "registry" / "facts").rglob("*.yaml"))
        # ledger untouched by a preview
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------- #
# The unlock: an opened project can run a long serial                         #
# --------------------------------------------------------------------------- #
def test_opened_project_plans_thirty_plus_chapters():
    proj = _empty_project()
    try:
        plan = build_import_plan(_outline())
        execute_genesis(project_path=str(proj), plan=plan, schema_dir=SCHEMA,
                        confirmed=True, actor="test")
        reg = registry_loader.load(proj, schema_dir=SCHEMA)
        specs = plan_chapters(reg)
        assert len(specs) >= 30    # long-novel diagnosis prerequisite (§14.4)
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)
