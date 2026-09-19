"""test_run_manifest.py — Production Run Manifest (roadmap Phase 5.5).

Pins the invariants of the serial run's audit record:
  - A run persists a SCHEMA-VALID manifest under registry/derived/run-manifests/.
  - NEVER gates (ADR-003): gating is false.
  - Records artifacts (draft_hash/state_hash/output_path), failures (skipped
    chapters + reason), outputs, and — HONESTLY — no cost for a deterministic run
    (live_calls 0, cost null), since the stub incurs none.
  - Folds a chapter's publish_readiness from its persisted envelope (approvals).
  - The manifest is a read-side fold: run_serial is untouched, so the existing
    serial suite still passes.
  - RUN ids are monotone (RUN-00001 → RUN-00002 on a second run).

Deterministic — no live model.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import registry_loader, derived
from runtime.serialize import run_serial, write_run_manifest, next_run_id

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
_MANIFEST_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "production-run-manifest.schema.json").read_text(encoding="utf-8")))


def _manifest_errors(m: dict) -> list:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _MANIFEST_SCHEMA.iter_errors(m)]


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, *, n_events: int = 3):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
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
            "summary": f"第{i}章的核心事件"})


def _run(root: Path, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


# --------------------------------------------------------------------------- #
# A run persists a schema-valid manifest recording every chapter               #
# --------------------------------------------------------------------------- #
def test_manifest_is_schema_valid_and_records_all_chapters(tmp_path):
    _scaffold(tmp_path, n_events=3)
    result = _run(tmp_path)
    manifest, rel = write_run_manifest(project_path=tmp_path, result=result,
                                       params={"prompt_version": "1.0.0"})
    assert _manifest_errors(manifest) == []
    assert (tmp_path / rel).exists()
    assert manifest["id"] == "RUN-00001"
    assert manifest["gating"] is False
    # every attempted chapter is recorded
    assert len(manifest["chapters"]) == len(result.chapters)
    assert manifest["totals"]["produced"] == result.produced
    assert manifest["totals"]["skipped"] == result.skipped
    assert manifest["totals"]["final_state_hash"] == result.final_state_hash


def test_produced_chapters_carry_artifact_pins(tmp_path):
    _scaffold(tmp_path, n_events=2)
    result = _run(tmp_path)
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)
    produced = [c for c in manifest["chapters"] if c["ok"]]
    assert produced, "expected at least one produced chapter"
    for c in produced:
        assert c["draft_hash"] is not None
        assert c["state_hash"] is not None
        assert c["output_path"] is not None
        assert (tmp_path / c["output_path"]).exists()


# --------------------------------------------------------------------------- #
# Honest cost: a deterministic run incurs none                                 #
# --------------------------------------------------------------------------- #
def test_deterministic_run_records_no_cost(tmp_path):
    _scaffold(tmp_path, n_events=2)
    result = _run(tmp_path)
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)
    assert manifest["totals"]["live_calls"] == 0
    assert manifest["totals"]["cost"] is None
    assert manifest["totals"]["token_usage"] == {"input": 0, "output": 0, "total": 0}
    # no produced chapter fabricates an llm block
    assert all(c["llm"] is None for c in manifest["chapters"] if c["ok"])


# --------------------------------------------------------------------------- #
# Failures (skipped chapters) are recorded with their reason                   #
# --------------------------------------------------------------------------- #
def test_skipped_chapter_is_recorded_as_failure(tmp_path):
    # cap depth so a chapter whose seeds exceed it fails to build → skipped.
    # Simpler: an empty project has no events → zero chapters; instead corrupt one
    # event's timeline ref to force a build/gate skip on that chapter.
    _scaffold(tmp_path, n_events=3)
    # point EVT-00002 at a non-existent timeline → its chapter build/gate fails
    bad = tmp_path / "registry/facts/events/EVT-00002.yaml"
    rec = yaml.safe_load(bad.read_text(encoding="utf-8"))
    rec["timeline"] = "TML-99999"
    bad.write_text(yaml.safe_dump(rec, allow_unicode=True), encoding="utf-8")

    result = _run(tmp_path)
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)
    assert _manifest_errors(manifest) == []
    skipped = [c for c in manifest["chapters"] if not c["ok"]]
    assert skipped, "expected at least one skipped chapter"
    for c in skipped:
        assert c["stage"]  # a stage like build:* / execute:*
        assert c["draft_hash"] is None
        assert c["llm"] is None
    assert manifest["totals"]["skipped"] == len(skipped)


# --------------------------------------------------------------------------- #
# publish_readiness on an envelope is folded into the chapter                  #
# --------------------------------------------------------------------------- #
def test_chapter_final_is_folded_into_run_manifest(tmp_path):
    _scaffold(tmp_path, n_events=1)
    result = _run(tmp_path)
    produced = [c for c in result.chapters if c.ok]
    assert produced
    task_id = produced[0].spec.task_id
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)
    ch = next(c for c in manifest["chapters"] if c["task_id"] == task_id)
    assert ch["chapter_final"] is not None
    assert ch["chapter_final"]["chapter_id"] == task_id
    assert ch["chapter_final"]["final_text"]
    # chapters.items is additionalProperties:false and declares no
    # prompt_provenance slot, so the manifest must NOT carry one (ADR-007).
    # The provenance stays on the draft envelope, reachable via task_id.
    assert "prompt_provenance" not in ch
    from runtime.serialize.run_manifest import _load_envelope
    envelope = _load_envelope(tmp_path, task_id)
    assert (envelope or {}).get("prompt_provenance")


def test_workflow_scheduler_batches_include_chapter_finals(tmp_path):
    _scaffold(tmp_path, n_events=2)
    from runtime.serialize.workflow_scheduler import WorkflowScheduler

    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
        batch_runs=["RUN-00001"],
    )
    result, run_manifest = scheduler._run_one("RUN-00001", start_chapter=1)
    assert result.produced == 2
    assert run_manifest["chapter_finals"]
    assert run_manifest["chapter_finals"][0]["final"] is not None


# --------------------------------------------------------------------------- #
# RUN ids are monotone across runs                                             #
# --------------------------------------------------------------------------- #
def test_run_ids_are_monotone(tmp_path):
    _scaffold(tmp_path, n_events=1)
    first, _ = write_run_manifest(project_path=tmp_path, result=_run(tmp_path))
    second, _ = write_run_manifest(project_path=tmp_path, result=_run(tmp_path))
    assert first["id"] == "RUN-00001"
    assert second["id"] == "RUN-00002"


def test_next_run_id_deterministic():
    assert next_run_id([]) == "RUN-00001"
    assert next_run_id(["RUN-00001", "RUN-00002"]) == "RUN-00003"
    assert next_run_id(["RUN-00005"]) == "RUN-00006"
