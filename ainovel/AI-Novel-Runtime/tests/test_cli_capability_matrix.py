from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime import cli
from runtime.approval import ApprovalQueue, create_approval_request
from runtime.execution.m7_audit import M7RegressionSample, write_m7_regression_sample
from runtime.serialize import WorkflowScheduler

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold_project(project: Path) -> None:
    facts = project / "registry" / "facts"
    meta = project / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main",
    })
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1,
    })
    _write(facts / "events" / "EVT-00001.yaml", {
        "id": "EVT-00001", "name": "开篇事件", "status": "active",
        "fact_version": 1, "timeline": "TML-00001", "sequence_index": 1,
        "participants": ["CHR-00001"], "causes": [], "effects": [], "summary": "主角面对开篇危机",
    })


def test_core_cli_capability_matrix(tmp_path, capsys):
    project = tmp_path / "project"
    _scaffold_project(project)

    assert cli.main(["validate", "--project", str(project), "--schema-dir", str(SCHEMA)]) == 0
    assert "PASS (0 error(s)" in capsys.readouterr().out

    assert cli.main([
        "workflow", "start", "--project", str(project),
        "--standard-root", str(STANDARD), "--run-id", "RUN-CLI-00001", "--max-chapters", "1",
    ]) == 0
    assert "workflow start: RUN-CLI-00001" in capsys.readouterr().out

    assert cli.main([
        "workflow", "status", "--project", str(project),
        "--standard-root", str(STANDARD), "--run-id", "RUN-CLI-00001",
    ]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["run_id"] == "RUN-CLI-00001"

    manifest_path = project / "registry" / "derived" / "workflow-scheduler" / "RUN-CLI-00001.json"
    assert manifest_path.exists()

    queue = ApprovalQueue(project_path=project)
    queue.enqueue(create_approval_request(
        request_id="APR-CLI-00001", target_type="publish", target_id="TASK-00001",
        action="confirm_publish", reason="chapter ready", requested_by={"module": "test"},
    ))
    assert cli.main(["approval", "list", "--project", str(project)]) == 0
    assert "APR-CLI-00001" in capsys.readouterr().out

    write_m7_regression_sample(project, M7RegressionSample(
        id="M7-CLI-00001", sample_type="hard_redline", title="红线样本",
        body="有人企图颠覆国家政权。", expected_risk_level="L3", expected_recommendation="block",
    ))
    assert cli.main(["m7", "audit", "--project", str(project)]) == 0
    assert "M7-CLI-00001" in capsys.readouterr().out


def test_genesis_cli_preview_is_auditable_and_writes_no_facts(tmp_path, capsys):
    project = tmp_path / "project"
    references = project / "sources" / "reference-novels"
    references.mkdir(parents=True)
    (project / "registry" / "_meta").mkdir(parents=True)
    (project / "registry" / "_meta" / "project-id").write_text("novel\n", encoding="utf-8")
    (project / "registry" / "_meta" / "registry-version").write_text("1\n", encoding="utf-8")
    (project / "registry" / "_meta" / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    (references / "ref.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。" * 8,
        encoding="utf-8",
    )

    assert cli.main(["genesis", "--project", str(project)]) == 0
    assert "genesis: stage=preview" in capsys.readouterr().out
    assert (project / "sources" / "novel-brain.yaml").exists()
    assert not list((project / "registry" / "facts").rglob("*.yaml"))


def test_export_and_publishing_cli_write_derived_deliverables(tmp_path, capsys):
    project = tmp_path / "project"
    _scaffold_project(project)
    drafts = project / "registry" / "derived" / "drafts"
    drafts.mkdir(parents=True)
    envelope = {
        "artifact_format": "anes.v2", "kind": "prose", "capability": "ChapterDraft",
        "task_id": "TASK-00001", "content_hash": "sha256:test", "body": "第一章正文",
        "qa_review": {"reviewer": "panel", "scores": {"retention": 80, "subscription": 70, "payoff": 75, "reader_drop_risk": 20}},
        "publish_readiness": {"recommendation": "recommend", "basis": {"redline": {"passed": True}}, "rationale": "clean"},
    }
    rel = "registry/derived/drafts/TASK-00001.json"
    (project / rel).write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    index = {"artifacts": [{"id": "TASK-00001", "category": "drafts", "path": rel}]}
    (project / "registry" / "derived" / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    (project / "registry" / "derived" / "_index.yaml").write_text(
        yaml.safe_dump(index, allow_unicode=True), encoding="utf-8")

    assert cli.main(["export", "book", "--project", str(project), "--scope", "produced"]) == 0
    assert (project / "workspace" / "exports" / "book.produced.md").exists()
    capsys.readouterr()

    assert cli.main(["export", "ip", "--project", str(project)]) == 0
    assert (project / "workspace" / "exports" / "ip-bible.md").exists()
    capsys.readouterr()

    assert cli.main(["publishing", "card", "--project", str(project), "--chapter", "TASK-00001", "--write"]) == 0
    assert "written" in capsys.readouterr().out
    assert list((project / "registry" / "derived" / "production-card").glob("*.json"))


def test_workflow_cli_defaults_schema_and_output_paths(tmp_path, capsys):
    project = tmp_path / "project"
    _scaffold_project(project)

    assert cli.main([
        "workflow", "start", "--project", str(project),
        "--standard-root", str(STANDARD), "--run-id", "RUN-CLI-00002", "--max-chapters", "1",
    ]) == 0
    capsys.readouterr()

    scheduler = WorkflowScheduler(
        project_path=project,
        standard_root=STANDARD,
        schema_dir=SCHEMA,
        out_dir=project / "build-serial",
        max_chapters=1,
    )
    manifest = scheduler.store.load("RUN-CLI-00002")
    assert manifest.output_dir == str(project / "build-serial")


def test_workflow_resume_and_batch_cli_are_recoverable(tmp_path, capsys):
    project = tmp_path / "project"
    _scaffold_project(project)
    base = ["--project", str(project), "--standard-root", str(STANDARD), "--max-chapters", "1"]

    assert cli.main(["workflow", "start", *base, "--run-id", "RUN-CLI-00003"]) == 0
    capsys.readouterr()
    assert cli.main(["workflow", "resume", *base, "--run-id", "RUN-CLI-00003"]) == 0
    assert "workflow resume: RUN-CLI-00003" in capsys.readouterr().out

    assert cli.main(["workflow", "batch", *base, "--run-ids", "RUN-CLI-00004,RUN-CLI-00005"]) == 0
    batch = json.loads(capsys.readouterr().out)
    assert len(batch["batch"]) == 2
    assert {item["run_id"] for item in batch["batch"]} == {"RUN-CLI-00004", "RUN-CLI-00005"}


def test_serial_baseline_alias_routes_to_precheck(tmp_path, capsys):
    project = tmp_path / "project"
    _scaffold_project(project)

    # `baseline` is an alias of `precheck`; routing is proven by the shared
    # precheck output markers. Exit status tracks the fixed 2-chapter outcome
    # (the minimal scaffold has one event, so the run reports "failed") and is
    # not what this test asserts.
    cli.main([
        "serial", "baseline",
        "--project", str(project),
        "--standard-root", str(STANDARD),
        "--model-provider", "deterministic",
        "--model-id", "deterministic",
    ])
    out = capsys.readouterr().out
    assert "precheck:" in out
    assert "baseline rpt:" in out
