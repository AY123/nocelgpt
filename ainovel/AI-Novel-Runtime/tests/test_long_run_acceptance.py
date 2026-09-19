import json
from pathlib import Path

from runtime.serialize.long_run_acceptance import (
    build_long_run_acceptance_audit,
    write_long_run_acceptance_audit,
)
from runtime.serialize.experiment_protocol import build_experiment_protocol
from runtime.serialize.serialization_utils import content_hash


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _project(tmp_path: Path, *, chapters: int) -> tuple[Path, Path, Path]:
    project = tmp_path / "book"
    _write(project / "registry" / "derived" / "outline" / "OUTLINE-00001.json", {
        "first_30_chapters": [
            {"chapter_no": index, "goal": f"goal-{index}"}
            for index in range(1, min(chapters, 30) + 1)
        ],
        "chapters": [
            {"chapter_no": index, "goal": f"goal-{index}"}
            for index in range(31, 101)
        ] if chapters == 100 else [],
    })
    _write(project / "registry" / "derived" / "long-arc" / "LONGARC-001.json", {
        "chapter_bands": [
            {"start": start, "end": start + 9}
            for start in range(1, 101, 10)
        ]
    })
    manifest = _write(project / "registry" / "derived" / "run-manifests" / "RUN-1.json", {
        "id": "RUN-1",
        "chapters": [
            {"index": index, "task_id": f"TASK-{index:05d}", "ok": True}
            for index in range(1, chapters + 1)
        ],
        "totals": {"produced": chapters, "skipped": 0},
    })
    protocol_value = build_experiment_protocol(
        protocol_id="P-1", project_id="book",
        model_provider="test", model_id="test-model",
        prompt_version="1.0.0", prompt_bundle_ref="test.prompt.yaml",
        schema_ref="standard@test", budget_limit_cny=1,
    )
    protocol = _write(
        project / "analysis" / "100-chapter-protocol.json", protocol_value)
    ledger_value = {
        "run_id": "RUN-1", "chapter_count": chapters,
        "protocol_content_hash": protocol_value["content_hash"],
        "chapters": [
            {"chapter_index": index, "ok": True}
            for index in range(1, chapters + 1)
        ],
    }
    ledger_value["content_hash"] = "sha256:" + content_hash(ledger_value)
    _write(project / "analysis" / "run-1-chapter-evidence-ledger.json", ledger_value)
    return project, manifest, protocol


def _write_admission(project: Path) -> None:
    _write(project / "registry" / "derived" / "golden-three-reviews" / "G3R-1.json", {
        "independent_reviews": [
            {"reviewer": "editor-a", "authority": "human", "verdict": "pass"},
            {"reviewer": "editor-b", "authority": "human", "verdict": "pass"},
        ],
        "review_outcome": {"mode": "dual_reviewer", "verdict": "pass"},
    })
    _write(project / "registry" / "derived" / "long-run-gates" / "gate-030.json", {
        "decision": "go", "authority": "human",
    })
    for chapter in (10, 20, 30):
        _write(project / "registry" / "derived" / "serial-checkpoints" / f"cp-{chapter:03d}.json", {})


def test_audit_holds_a_thirty_chapter_run_without_authority_and_plan(tmp_path):
    project, _, _ = _project(tmp_path, chapters=30)
    _write(project / "registry" / "derived" / "golden-three-reviews" / "G3R-1.json", {
        "review_outcome": {
            "mode": "single_reviewer", "verdict": "pass",
            "reviewer": "editor-a", "authority": "human",
        },
    })
    report = build_long_run_acceptance_audit(project_path=project, run_id="RUN-1")

    assert report["status"] == "blocked_before_31"
    assert report["ready_for_31_60"] is False
    failed = {item["check_id"] for item in report["admission_checks"] if not item["passed"]}
    assert "golden_three_two_humans" in failed
    golden = next(item for item in report["admission_checks"]
                  if item["check_id"] == "golden_three_two_humans")
    assert "independent_human_reviewers=1" in golden["detail"]
    assert "gate_30_human_go" in failed
    assert "next_window_plan_31_40" in failed


def test_audit_admits_31_to_60_only_when_all_admission_evidence_exists(tmp_path):
    project, _, _ = _project(tmp_path, chapters=100)
    _write_admission(project)
    report = build_long_run_acceptance_audit(project_path=project, run_id="RUN-1")

    assert report["ready_for_31_60"] is True
    assert report["complete_100"] is False
    assert report["status"] == "ready_for_31_60"


def test_audit_aggregates_only_an_explicit_contiguous_run_chain(tmp_path):
    project, _, protocol_path = _project(tmp_path, chapters=30)
    _write_admission(project)
    _write(project / "registry" / "derived" / "run-manifests" / "RUN-2.json", {
        "id": "RUN-2",
        "chapters": [
            {"index": index, "task_id": f"TASK-{index:05d}", "ok": True}
            for index in range(31, 41)
        ],
        "totals": {"produced": 10, "skipped": 0},
    })
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    ledger = {
        "run_id": "RUN-1+RUN-2",
        "chapter_count": 40,
        "protocol_content_hash": protocol["content_hash"],
        "chapters": [
            {"chapter_index": index, "ok": True}
            for index in range(1, 41)
        ],
    }
    ledger["content_hash"] = "sha256:" + content_hash(ledger)
    ledger_path = _write(project / "analysis" / "ci-m5-chapter-evidence-ledger.json", ledger)

    report = build_long_run_acceptance_audit(
        project_path=project, run_id=["RUN-1", "RUN-2"], ledger_path=ledger_path)

    chain = next(item for item in report["admission_checks"]
                 if item["check_id"] == "run_chain_contiguous")
    assert chain["passed"] is True
    assert report["observed"]["produced"] == 40
    assert report["run_id"] == "RUN-1+RUN-2"

    reversed_report = build_long_run_acceptance_audit(
        project_path=project, run_id=["RUN-2", "RUN-1"], ledger_path=ledger_path)
    reversed_chain = next(item for item in reversed_report["admission_checks"]
                          if item["check_id"] == "run_chain_contiguous")
    assert reversed_chain["passed"] is False


def test_audit_marks_complete_only_with_100_chapter_recovery_and_baseline(tmp_path):
    project, _, _ = _project(tmp_path, chapters=100)
    _write_admission(project)
    _write(project / "registry" / "derived" / "long-run-gates" / "gate-060.json", {
        "decision": "go", "authority": "human",
    })
    for chapter in range(40, 101, 10):
        _write(project / "registry" / "derived" / "serial-checkpoints" / f"cp-{chapter:03d}.json", {})
    recovery = _write(project / "analysis" / "ci-m5-recovery-audit.json", {
        "interrupted": True, "resumed": True, "rewritten_final": False,
        "duplicate_cost": False, "half_written_facts": False,
    })
    baseline = _write(project / "analysis" / "ci-m5-100-baseline.json", {
        "kind": "hundred_chapter_baseline",
        "front_half": {
            "chapter_count": 50, "produced": 50, "skipped": 0,
            "avg_quality": 8.0, "cost_total": 1.0, "cost_currency": "CNY",
            "promise_overdue": [], "promise_resolved": ["P-1"],
        },
        "back_half": {
            "chapter_count": 50, "produced": 50, "skipped": 0,
            "avg_quality": 8.1, "cost_total": 1.1, "cost_currency": "CNY",
            "promise_overdue": [], "promise_resolved": ["P-1"],
        },
        "full_run": {"chapter_count": 100},
        "go_iterate_stop": "iterate",
        "comparison_only": True,
        "gating": False,
    })

    report = build_long_run_acceptance_audit(
        project_path=project, run_id="RUN-1",
        recovery_audit_path=recovery, baseline_path=baseline)
    assert report["complete_100"] is True
    assert report["status"] == "complete"
    assert report["gating"] is False
    assert report["human_authority_required"] is True

    out = write_long_run_acceptance_audit(tmp_path / "audit.json", report)
    assert json.loads(out.read_text(encoding="utf-8"))["content_hash"].startswith("sha256:")


def test_audit_rejects_tampered_protocol_and_ledger(tmp_path):
    project, _, protocol_path = _project(tmp_path, chapters=30)
    _write_admission(project)

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["model_id"] = "silently-changed-model"
    _write(protocol_path, protocol)
    report = build_long_run_acceptance_audit(project_path=project, run_id="RUN-1")
    protocol_check = next(
        item for item in report["admission_checks"]
        if item["check_id"] == "protocol_frozen")
    assert protocol_check["passed"] is False
    assert "integrity=False" in protocol_check["detail"]

    protocol["content_hash"] = content_hash(
        {key: value for key, value in protocol.items() if key != "content_hash"})
    _write(protocol_path, protocol)
    ledger_path = project / "analysis" / "run-1-chapter-evidence-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["chapters"][0]["chapter_index"] = 2
    _write(ledger_path, ledger)
    report = build_long_run_acceptance_audit(project_path=project, run_id="RUN-1")
    ledger_check = next(
        item for item in report["admission_checks"]
        if item["check_id"] == "chapter_evidence_current")
    assert ledger_check["passed"] is False
    assert "rows_valid=False" in ledger_check["detail"]


def test_protocol_freezes_sampling_token_budget_and_role_models():
    protocol = build_experiment_protocol(
        protocol_id="P-2", project_id="book",
        model_provider="92code", model_id="gpt-5.6-sol",
        prompt_version="14.0.0", prompt_bundle_ref="chapter-draft.v14.prompt.yaml",
        schema_ref="standard@2.0.0", budget_limit_cny=20,
        temperature_contract={"temperature": 0.2, "top_p": 0.9},
        max_output_tokens=5000,
        role_models={"review": "claude:claude-opus-5"},
    )
    assert protocol["version"] == "1.1"
    assert protocol["temperature_contract"]["temperature"] == 0.2
    assert protocol["max_output_tokens"] == 5000
    assert protocol["role_models"]["review"] == "claude:claude-opus-5"
    assert len(protocol["content_hash"]) == 64
