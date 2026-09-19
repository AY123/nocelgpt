from __future__ import annotations

from runtime.serialize.live_baseline_report import build_live_baseline_report


def test_live_baseline_report_shape():
    report = build_live_baseline_report(
        project_path="/tmp/project",
        baseline_id="LIVE-5CH-001",
        status="passed",
        environment={"provider": "deepseek", "model": "deepseek-v4-pro", "prompt_version": "6.0.0", "runtime_version": "test"},
        chapters=[], failures=[], replay={"generation_records": 0, "replay_hits": 0, "live_calls": 0},
        cost={"budget_limit": 20.0, "actual_cost": 0.0, "currency": "CNY"},
        resume={"interrupted_after_chapter": None, "resumed": False, "duplicate_calls_detected": False},
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
    )
    assert report["kind"] == "live_baseline_report"
    assert report["status"] == "passed"
    assert report["gating"] is False
    assert report["chapter_summary"]["count"] == 0
    assert report["chapter_summary"]["ok"] == 0
    assert report["run_manifest_ref"]
    # Empty run: quality summary exists but every bucket is zero.
    q = report["quality_summary"]
    assert q["integrity_gate"] == {"pass": 0, "fail": 0, "review_required": 0, "not_assessed": 0}
    assert q["advisory_flags"]["ai_taste"] == {"checked": 0, "flagged": 0}
    assert q["verdicts"] == {}
    assert report["run_summary"]["integrity_failures"] == 0


def test_live_baseline_report_rolls_up_quality_signals():
    # Two chapters as a real live run would emit them: an integrity gate result,
    # ReviewReport-shaped advisory detectors, a verdict, and a reference gap.
    chapters = [
        {
            "ok": True, "stage": "written", "verdict": "pass",
            "integrity": {"status": "pass", "findings": []},
            "ai_taste": {"findings": [{"check": "ai_taste", "severity": "warning", "message": "x"}]},
            "density": {"findings": [{"check": "density", "severity": "info", "message": "clean"}]},
            "reference_gap": {"delta": -1.2},
        },
        {
            "ok": True, "stage": "written", "verdict": "revise",
            "integrity": {"status": "review_required", "findings": []},
            "ai_taste": {"findings": [{"check": "ai_taste", "severity": "info", "message": "clean"}]},
            "end_hook": {"findings": [{"check": "end_hook", "severity": "warning", "message": "weak"}]},
        },
    ]
    report = build_live_baseline_report(
        project_path="/tmp/project",
        baseline_id="LIVE-5CH-001",
        status="passed",
        environment={"provider": "deepseek", "model": "deepseek-v4-pro", "prompt_version": "6.0.0", "runtime_version": "test"},
        chapters=chapters, failures=[], replay={"generation_records": 0, "replay_hits": 0, "live_calls": 2},
        cost={"budget_limit": 20.0, "actual_cost": 0.11, "currency": "CNY"},
        resume={"interrupted_after_chapter": None, "resumed": False, "duplicate_calls_detected": False},
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
    )
    q = report["quality_summary"]
    assert q["integrity_gate"] == {"pass": 1, "fail": 0, "review_required": 1, "not_assessed": 0}
    # ai_taste: checked twice, flagged once (info doesn't count as a flag).
    assert q["advisory_flags"]["ai_taste"] == {"checked": 2, "flagged": 1}
    assert q["advisory_flags"]["density"] == {"checked": 1, "flagged": 0}
    assert q["advisory_flags"]["end_hook"] == {"checked": 1, "flagged": 1}
    assert q["verdicts"] == {"pass": 1, "revise": 1}
    assert q["reference_gap_measured"] == 1
    # review_required rolls into the run-summary integrity-failure count.
    assert report["run_summary"]["integrity_failures"] == 1
