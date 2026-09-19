"""test_workflow_scheduler.py — checkpoint/resume smoke coverage."""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.serialize import WorkflowScheduler, build_w9_selection_policy

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, *, n_events: int = 2):
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
            "participants": ["CHR-00001"], "causes": [], "effects": [],
            "summary": f"第{i}章的核心事件"})


def test_scheduler_writes_checkpoint_manifest(tmp_path):
    _scaffold(tmp_path, n_events=2)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
    )
    result = scheduler.start("RUN-00099")
    manifest_path = tmp_path / "registry" / "derived" / "workflow-scheduler" / "RUN-00099.json"
    assert manifest_path.exists()
    manifest = scheduler.store.load("RUN-00099")
    assert manifest.run_id == "RUN-00099"
    assert manifest.status in {"paused", "completed"}
    assert manifest.cursor >= 1
    assert manifest.output_dir
    assert manifest.replay_dir
    assert result.chapters
    assert manifest.to_dict().get("selection_policy") is not None


def test_scheduler_resume_is_idempotent(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
    )
    scheduler.start("RUN-00100")
    first = scheduler.store.load("RUN-00100")
    second_result = scheduler.resume("RUN-00100")
    second = scheduler.store.load("RUN-00100")
    assert first.run_id == second.run_id
    assert second.status in {"paused", "completed"}
    assert second_result.chapters
    assert scheduler.resume_cursor("RUN-00100") == second.cursor


def test_scheduler_step_advances_cursor(tmp_path):
    _scaffold(tmp_path, n_events=2)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
    )
    scheduler.start("RUN-00101")
    before = scheduler.store.load("RUN-00101")
    scheduler.step("RUN-00101")
    after = scheduler.store.load("RUN-00101")
    assert after.cursor >= before.cursor


def test_scheduler_manual_mark_failed_and_completed(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
    )
    scheduler.start("RUN-00102")
    scheduler.mark_failed("RUN-00102", chapter=1, stage="execute:test", message="boom")
    manifest = scheduler.store.load("RUN-00102")
    assert manifest.status == "paused"
    assert manifest.failed_chapters
    scheduler.mark_completed("RUN-00102", completed_up_to=1)
    manifest2 = scheduler.store.load("RUN-00102")
    assert manifest2.status == "completed"
    assert manifest2.cursor == 2
    assert manifest2.budget_spent is not None


def test_scheduler_budget_hold_blocks_start(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
        budget_limit=0.0,
    )
    try:
        scheduler.start("RUN-00103")
        assert False, "expected budget hold to block start"
    except ValueError as exc:
        assert "admission hold" in str(exc)
    manifest = scheduler.store.load("RUN-00103")
    assert manifest.admission_status == "hold"


def test_scheduler_batch_audit_writes_manifest(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
        batch_runs=["RUN-01001"],
    )
    audit = scheduler.run_batch()
    assert audit and audit[0]["run_id"] == "RUN-01001"
    batch_manifest = tmp_path / "registry" / "derived" / "workflow-scheduler" / "BATCH-00001.json"
    assert batch_manifest.exists()


def test_scheduler_resume_blocks_when_budget_locked(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
        budget_limit=None,
    )
    scheduler.start("RUN-00104")
    scheduler.budget_limit = 1.0
    try:
        scheduler.resume("RUN-00104")
        assert False, "expected budget hold to block resume"
    except ValueError as exc:
        assert "admission hold" in str(exc)


def test_scheduler_policy_helper_can_be_attached(tmp_path):
    _scaffold(tmp_path, n_events=1)
    scheduler = WorkflowScheduler(
        project_path=tmp_path,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=tmp_path / "build-serial",
    )
    policy = build_w9_selection_policy(str(tmp_path))
    assert policy["kind"] == "w9_selection_policy"
    assert scheduler._selection_policy()["kind"] == "w9_selection_policy"
