"""test_dashboard_sentinel.py — N100-075: long-run quality-trend sentinel.

The sentinel folds each chapter-run's prose detectors (ai_taste / pacing /
density / end_hook) into 10-chapter blocks and flags a block whose WARNING RATE
worsened vs the previous block. Advisory, never gates, recomputed from artifacts.

These tests write chapter-run artifacts directly (fast, deterministic) with
controlled warning patterns and assert the fold + degradation flagging.
"""
import json

from runtime import derived
from runtime.dashboard.report import _quality_sentinel_section


def _write_run(project_path, index: int, *, ai_taste_warn=False, pacing_warn=False,
               density_warn=False, end_hook_warn=False):
    def _report(warn):
        sev = "warning" if warn else "info"
        return {"reviewer": "r", "axis": "evaluative", "gating": False,
                "findings": [{"check": "c", "severity": sev, "message": "m"}]}
    run = {
        "index": index, "task_id": f"TASK-{index:05d}", "ok": True, "stage": "done",
        "ai_taste": _report(ai_taste_warn),
        "pacing": _report(pacing_warn),
        "density": _report(density_warn),
        "end_hook": _report(end_hook_warn),
    }
    derived.write_artifact(
        project_path=project_path, category="chapter-run",
        artifact_id=f"run-TASK-{index:05d}", artifact=run,
        serialized=json.dumps(run, ensure_ascii=False) + "\n")


def test_sentinel_absent_below_one_block(tmp_path):
    # fewer than block (10) chapters => no sentinel (not enough to trend)
    for i in range(1, 6):
        _write_run(tmp_path, i)
    assert _quality_sentinel_section(tmp_path) is None


def test_sentinel_folds_warning_rate_per_block(tmp_path):
    # block 1 (ch 1-10): 2/10 ai_taste warnings; block 2 (ch 11-20): 5/10
    for i in range(1, 11):
        _write_run(tmp_path, i, ai_taste_warn=(i <= 2))
    for i in range(11, 21):
        _write_run(tmp_path, i, ai_taste_warn=(i <= 15))
    section = _quality_sentinel_section(tmp_path)
    assert section is not None
    assert section["gating"] is False
    assert section["chapters_analyzed"] == 20
    blocks = section["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["warning_rate"]["ai_taste"] == 0.2
    assert blocks[1]["warning_rate"]["ai_taste"] == 0.5


def test_sentinel_flags_degradation_vs_previous_block(tmp_path):
    # ai_taste worsens block-over-block; pacing stays flat (no alert for pacing)
    for i in range(1, 11):
        _write_run(tmp_path, i, ai_taste_warn=(i <= 1))       # 10%
    for i in range(11, 21):
        _write_run(tmp_path, i, ai_taste_warn=(i <= 16))      # 60%
    section = _quality_sentinel_section(tmp_path)
    b2 = section["blocks"][1]
    assert "ai_taste" in b2["degraded_vs_prev"]
    assert "pacing" not in b2["degraded_vs_prev"]
    assert any("ai_taste" in a for a in section["alerts"])
    # the first block never has a "previous" to worsen against
    assert section["blocks"][0]["degraded_vs_prev"] == []


def test_sentinel_no_alerts_when_stable_or_improving(tmp_path):
    # block 2 improves (fewer warnings) => no degradation alerts
    for i in range(1, 11):
        _write_run(tmp_path, i, pacing_warn=(i <= 8))         # 80%
    for i in range(11, 21):
        _write_run(tmp_path, i, pacing_warn=(i <= 2))         # 20%
    section = _quality_sentinel_section(tmp_path)
    assert section["alerts"] == []
    assert section["blocks"][1]["degraded_vs_prev"] == []
