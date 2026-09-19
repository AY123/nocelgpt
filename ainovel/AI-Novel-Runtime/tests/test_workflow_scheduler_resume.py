from __future__ import annotations

from pathlib import Path

import yaml

from runtime.serialize import workflow_scheduler

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, n_events: int = 3):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {"id": "TML-00001", "name": "主线", "status": "active", "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {"id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"], "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []), "summary": f"第{i}章"
        })


def test_scheduler_step_creates_checkpoint(tmp_path):
    _scaffold(tmp_path, 3)
    scheduler = workflow_scheduler(
        project_path=tmp_path, standard_root=STANDARD, schema_dir=SCHEMA,
        out_dir=tmp_path / "build", prompt_version="6.0.0", max_chapters=3,
        reviewer_id="serial-v1", budget_limit=None,
    )
    result = scheduler.step("RUN-00001")
    manifest = scheduler.store.load("RUN-00001")
    assert manifest.cursor >= 1
    assert manifest.status in ("completed", "running", "paused")
    assert result.gating is False


def test_scheduler_resume_cursor_is_stable(tmp_path):
    _scaffold(tmp_path, 2)
    scheduler = workflow_scheduler(
        project_path=tmp_path, standard_root=STANDARD, schema_dir=SCHEMA,
        out_dir=tmp_path / "build", prompt_version="6.0.0", max_chapters=2,
        reviewer_id="serial-v1", budget_limit=None,
    )
    scheduler.mark_completed("RUN-00002", completed_up_to=1)
    assert scheduler.resume_cursor("RUN-00002") == 2


def test_scheduler_resume_completed_run_replays(tmp_path):
    _scaffold(tmp_path, 2)
    scheduler = workflow_scheduler(
        project_path=tmp_path, standard_root=STANDARD, schema_dir=SCHEMA,
        out_dir=tmp_path / "build", prompt_version="6.0.0", max_chapters=2,
        reviewer_id="serial-v1", budget_limit=None,
    )
    scheduler.mark_completed("RUN-00003", completed_up_to=2)
    scheduler.store.load("RUN-00003")
    result = scheduler.resume("RUN-00003")
    assert result.gating is False
    assert len(result.chapters) == 2
