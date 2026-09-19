"""test_serial_checkpoints.py — the checkpoint loop: writer → reader → aggregate.

Covers the three things the staged 10/20/30 review points must actually do:
  1. run_serial writes a serial_checkpoint at chapters 10/20/30 (writer).
  2. load_serial_checkpoints reads them back index-ordered (reader).
  3. build_run_aggregate cites the checkpoints on the run summary (reference end).

The first is a focused re-assertion of the writer contract these tests depend on;
2 and 3 exercise the reader/reference code that did not exist before (built≠live).
"""
import json

from runtime import derived
from runtime.serialize import (run_serial, load_serial_checkpoint,
                               load_serial_checkpoints, backfill_checkpoints,
                               build_checkpoint, CHECKPOINT_INDICES)
from runtime.serialize.run_aggregate import build_run_aggregate


def _run_30(tmp_path, monkeypatch):
    """Drive run_serial through 30 stubbed chapters (no live model)."""
    from runtime import registry_loader

    class _FakeReg:
        def __init__(self):
            self.version = "v1"
            self.facts = {}
        def get(self, _eid):
            return None

    specs = []
    for i in range(1, 31):
        specs.append(type("Spec", (), {"index": i, "task_id": f"TASK-{i:05d}",
                                        "event_id": f"EVT-{i:05d}",
                                        "seeds": ["CHR-00001"], "goal": f"g{i}"})())

    monkeypatch.setattr(registry_loader, "load", lambda _p: _FakeReg())
    monkeypatch.setattr("runtime.serialize.loop.plan_chapters", lambda _reg: specs)
    pkg = lambda **kw: type("B", (), {"ok": True, "message": "ok", "stage": "ok",
        "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}})()
    monkeypatch.setattr("runtime.pipeline.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.execute_package", lambda **kw: type("E", (), {
        "ok": True, "stage": "ok", "message": "ok",
        "artifact_path": "registry/derived/drafts/TASK-00001.json",
        "artifact": {
            "task_id": kw["package"]["provenance"]["derived_from"][0].split("@", 1)[0],
            "content_hash": "hash-draft", "body": "真实章节正文",
            "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"},
            "produced_by": {"llm": {"cost": {"total_cost": 0},
                                    "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        },
        "qa_review": {"scores": {}},
        "envelope": {"artifact": {"task_id": "TASK-00001"}},
    })())

    return run_serial(
        project_path=tmp_path, standard_root=tmp_path, schema_dir=tmp_path,
        out_dir=tmp_path / "out", model=None, reviewer=None,
        prompt_version="1.0.0", max_chapters=30,
    )


def test_writer_persists_checkpoints_at_10_20_30(tmp_path, monkeypatch):
    result = _run_30(tmp_path, monkeypatch)
    assert result.produced == 30
    cp_dir = tmp_path / "registry" / "derived" / "serial-checkpoints"
    for idx in (index for index in CHECKPOINT_INDICES if index <= 30):
        assert (cp_dir / f"cp-{idx:03d}.json").exists()
    # no checkpoint at a non-milestone chapter
    assert not (cp_dir / "cp-005.json").exists()


def test_reader_reads_checkpoints_back(tmp_path, monkeypatch):
    _run_30(tmp_path, monkeypatch)

    cps = load_serial_checkpoints(tmp_path)
    assert [c["chapter_index"] for c in cps] == [10, 20, 30]
    for c in cps:
        assert c["kind"] == "serial_checkpoint"
        assert c["chapter_id"] == f"TASK-{c['chapter_index']:05d}"

    single = load_serial_checkpoint(tmp_path, 20)
    assert single is not None and single["chapter_index"] == 20


def test_reader_degrades_when_no_run(tmp_path):
    # a project that never ran yields an empty list, not an error
    assert load_serial_checkpoints(tmp_path) == []
    assert load_serial_checkpoint(tmp_path, 10) is None


def test_run_aggregate_cites_checkpoints(tmp_path, monkeypatch):
    _run_30(tmp_path, monkeypatch)

    agg = build_run_aggregate(
        project_path=tmp_path, standard_root="/tmp/standard",
        prompt_version="10.0.0", model_provider="deepseek", model_id="deepseek-v4-pro",
        budget_limit=100.0, launch_report_id="L30R-0003",
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
        notes="checkpoint-cite",
    )
    assert [c["chapter_index"] for c in agg["checkpoints"]] == [10, 20, 30]


def test_run_aggregate_checkpoints_empty_without_run(tmp_path):
    agg = build_run_aggregate(
        project_path=tmp_path, standard_root="/tmp/standard",
        prompt_version="10.0.0", model_provider="deepseek", model_id="deepseek-v4-pro",
        budget_limit=100.0, launch_report_id="L30R-0004",
        run_manifest_ref="registry/derived/run-manifests/RUN-00002.json",
        notes="empty",
    )
    assert agg["checkpoints"] == []


def _write_run_manifest(project_path, run_id="RUN-00025", indices=range(1, 34)):
    """Persist a run-scoped run-manifest — the immutable audit record backfill
    folds from (the RUN-00025 situation: run produced before the live writer)."""
    chapters = [{
        "index": i,
        "task_id": f"TASK-{i:05d}",
        "event": f"EVT-{i:05d}",
        "draft_hash": f"sha256:draft-{i}",
        "state_hash": f"sha256:state-{i}",
        "verdict": "pass",
        "commercial_verdict": "hold",
        "chapter_final": {"final_hash": f"sha256:final-{i}"},
    } for i in indices]
    manifest = {"id": run_id, "kind": "production_run_manifest", "version": "1.0",
                "chapters": chapters}
    derived.write_artifact(
        project_path=project_path, category="run-manifests",
        artifact_id=run_id, artifact=manifest,
        serialized=json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def _write_enrichment(enrichment_dir, index, draft_hash, m7_rec="recommend"):
    """Write a chapter-run snapshot row used only to enrich m7/quality_snapshot."""
    enrichment_dir.mkdir(parents=True, exist_ok=True)
    cr = {"task_id": f"TASK-{index:05d}", "draft_hash": draft_hash,
          "m7": {"recommendation": m7_rec}, "quality_snapshot": {"score": index}}
    (enrichment_dir / f"run-TASK-{index:05d}.json").write_text(
        json.dumps(cr, ensure_ascii=False, indent=2), encoding="utf-8")


def test_backfill_folds_checkpoints_from_run_manifest(tmp_path):
    _write_run_manifest(tmp_path)
    assert load_serial_checkpoints(tmp_path) == []

    written = backfill_checkpoints(tmp_path, run_manifest_id="RUN-00025")
    assert [c["chapter_index"] for c in written] == [10, 20, 30]
    got = load_serial_checkpoints(tmp_path)
    assert [c["chapter_index"] for c in got] == [10, 20, 30]
    cp10 = load_serial_checkpoint(tmp_path, 10)
    assert cp10["kind"] == "serial_checkpoint"
    assert cp10["event_id"] == "EVT-00010"
    # core fields come from the immutable manifest
    assert cp10["draft_hash"] == "sha256:draft-10"
    assert cp10["final_hash"] == "sha256:final-10"
    # manifest omits m7 and no enrichment supplied → None (not fabricated)
    assert cp10["m7"] is None


def test_backfill_enrichment_only_when_draft_hash_matches(tmp_path):
    # This locks the correctness lesson: a snapshot archive from a DIFFERENT run
    # (mismatched draft_hash) must NOT leak its m7 into this run's checkpoint.
    _write_run_manifest(tmp_path)
    enr = tmp_path / "snapshot" / "chapter-run"
    _write_enrichment(enr, 10, draft_hash="sha256:draft-10")          # matches
    _write_enrichment(enr, 20, draft_hash="sha256:WRONG-RUN")         # mismatch

    backfill_checkpoints(tmp_path, run_manifest_id="RUN-00025", enrichment_dir=enr)
    cp10 = load_serial_checkpoint(tmp_path, 10)
    cp20 = load_serial_checkpoint(tmp_path, 20)
    # matching hash → enrichment accepted
    assert cp10["m7"]["recommendation"] == "recommend"
    assert cp10["quality_snapshot"] == {"score": 10}
    # mismatched hash → enrichment dropped, core still from manifest
    assert cp20["m7"] is None
    assert cp20["quality_snapshot"] is None
    assert cp20["draft_hash"] == "sha256:draft-20"


def test_backfill_is_idempotent(tmp_path):
    _write_run_manifest(tmp_path)
    first = backfill_checkpoints(tmp_path, run_manifest_id="RUN-00025")
    path10 = derived.derived_dir(tmp_path, "serial-checkpoints") / "cp-010.json"
    mtime1 = path10.stat().st_mtime_ns
    second = backfill_checkpoints(tmp_path, run_manifest_id="RUN-00025")
    assert [c["chapter_index"] for c in first] == [c["chapter_index"] for c in second]
    assert path10.stat().st_mtime_ns == mtime1


def test_backfill_matches_live_writer_shape(tmp_path):
    # the shared builder guarantees a backfilled checkpoint is byte-identical to a
    # live one for the same inputs (no drift between the two code paths)
    _write_run_manifest(tmp_path)
    enr = tmp_path / "snapshot" / "chapter-run"
    _write_enrichment(enr, 10, draft_hash="sha256:draft-10")
    backfilled = backfill_checkpoints(tmp_path, run_manifest_id="RUN-00025", enrichment_dir=enr)[0]
    live = build_checkpoint(
        chapter_index=10, chapter_id="TASK-00010", event_id="EVT-00010",
        draft_hash="sha256:draft-10", state_hash="sha256:state-10",
        final_hash="sha256:final-10", verdict="pass", commercial_verdict="hold",
        quality_snapshot={"score": 10}, m7={"recommendation": "recommend"},
    )
    assert backfilled == live
