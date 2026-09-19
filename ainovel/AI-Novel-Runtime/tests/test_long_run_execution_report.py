from runtime.serialize.long_run_execution_report import build_long_run_execution_report, write_long_run_execution_report


CHAPTERS = []
for i in range(1, 101):
    CHAPTERS.append({
        "chapter_index": i,
        "ok": True,
        "quality": {"verdict": "pass"},
        "cost": {"cost": {"currency": "USD", "total_cost": 0.01}},
    })


def test_long_run_execution_report_builds():
    report = build_long_run_execution_report(
        project_id="PROJ-1",
        chapters=CHAPTERS,
        checkpoints=[{"window": "ch001-010"}, {"window": "ch011-020"}],
        promise_ledger={"overdue": [], "resolved": ["P-01"], "pending": ["P-02"], "metadata": {"chapter_count": 100}},
        recovery_audit={"run_id": "RUN-001", "interrupted": True, "resumed": True, "rewritten_final": False, "duplicate_cost": False, "half_written_facts": False, "notes": "clean resume"},
    )
    data = report.to_dict()

    assert data["kind"] == "long_run_execution_report"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["chapter_count"] == 100
    assert data["checkpoint_count"] == 2
    assert data["produced_count"] == 100
    assert data["skipped_count"] == 0
    assert data["recovery_audit"]["interrupted"] is True
    assert data["recovery_audit"]["resumed"] is True
    assert data["recovery_audit"]["rewritten_final"] is False
    assert data["quality_trend"]["front_half_produced"] == 50
    assert data["quality_trend"]["back_half_produced"] == 50


def test_long_run_execution_report_writes(tmp_path):
    report = build_long_run_execution_report(project_id="PROJ-1", chapters=CHAPTERS[:30])
    out = write_long_run_execution_report(tmp_path / "long-run-report.json", report)
    assert out.exists()


def test_recovery_audit_no_rewritten_final():
    report = build_long_run_execution_report(
        project_id="PROJ-1",
        chapters=CHAPTERS[:10],
        recovery_audit={"run_id": "RUN-002", "interrupted": True, "resumed": True, "rewritten_final": False, "duplicate_cost": False, "half_written_facts": False},
    )
    assert report.recovery_audit.rewritten_final is False
    assert report.recovery_audit.duplicate_cost is False
