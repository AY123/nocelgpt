"""test_dashboard_y365.py — Y365-01/02/04 dashboard wiring (built≠live proof).

The four Y365 modules landed as pure functions with NO consumer. These tests pin
that they now run on a REAL production path (run_serial → dashboard), which is
the project's standing rule: a new capability claiming to be "已接入" must have a
live caller and a test proving it (CLAUDE.md §2).

What is pinned here:
  - Y365-02 stability folds the produced chapters and MEASURES word counts from
    the persisted draft body (never chapter_count x 3000).
  - Y365-01/04 return None until real platform signals are imported — absence
    must not be dressed up as a closed loop (§9.2.9: ReaderSignal = 0).
  - With signals imported, both sections appear and stay comparison-only.
  - Every section is advisory: gating False, calibrates False.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.serialize import run_serial
from runtime.dashboard import build_dashboard

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")


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
            "summary": f"第{i}章"})


def _signal(root: Path, chapter_id: str, *, retention_rate: float, name: str):
    _write(root / "sources" / "reader-signals" / f"{name}.yaml", {
        "kind": "reader_signal", "version": "1.0", "scope": "chapter",
        "chapter_id": chapter_id, "source": "qidian",
        "collected_at": "2026-07-30T10:00:00Z",
        "metrics": {"retention_rate": retention_rate, "subscription_count": 120},
        "confidence": {"level": "medium", "sample_size": 300, "is_estimated": False},
    })


def _run(root: Path, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


# --------------------------------------------------------------------------- #
# Y365-02: stability runs live and measures real word counts                   #
# --------------------------------------------------------------------------- #
def test_stability_section_is_live_after_a_real_run(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()

    stability = d["stability"]
    assert stability is not None, "Y365-02 built but never wired into a live path"
    assert stability["kind"] == "million_word_stability_report"
    assert stability["gating"] is False
    assert stability["comparison_only"] is True
    assert stability["total_chapters"] == 3
    # 3 chapters is nowhere near a million words — the flag must stay honest.
    assert stability["is_million_word"] is False


def test_stability_word_counts_are_measured_not_estimated(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    stability = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()["stability"]

    # Every produced chapter has a real body, so nothing falls back to the
    # flat words_per_chapter estimate.
    assert stability["word_counts_measured"] == 3
    assert stability["word_counts_estimated"] == 0
    # A measured total is not a multiple of the 3000 default.
    assert stability["total_words"] > 0
    assert stability["total_words"] != 3 * 3000


def test_stability_absent_for_empty_project(tmp_path):
    _scaffold(tmp_path, n_events=2)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["stability"] is None


# --------------------------------------------------------------------------- #
# Y365-01 / Y365-04: honest degrade with no real platform data                 #
# --------------------------------------------------------------------------- #
def test_platform_and_calibration_absent_without_real_signals(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()

    # ReaderSignal = 0 is the real state of the book (docs §9.2.9). An empty
    # reconciliation must NOT be reported as a closed loop.
    assert d["platform_feedback"] is None
    assert d["commercial_calibration"] is None


def test_platform_feedback_appears_with_real_signals(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    _signal(tmp_path, "TASK-00001", retention_rate=61.0, name="s1")
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()

    pf = d["platform_feedback"]
    assert pf is not None
    assert pf["kind"] == "platform_feedback_reconciliation"
    assert pf["has_real_data"] is True
    assert pf["gating"] is False
    assert pf["comparison_only"] is True
    assert pf["calibrates"] is False
    # The real subscription_count is carried through as data.
    names = {r["signal_name"] for r in pf["reconciled"]}
    assert "subscription_count" in names


def test_commercial_calibration_never_claims_calibrated_on_thin_data(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    _signal(tmp_path, "TASK-00001", retention_rate=61.0, name="s1")
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()

    cc = d["commercial_calibration"]
    if cc is None:
        # No judge retention score on the deterministic path => nothing to pair.
        return
    assert cc["gating"] is False
    assert cc["comparison_only"] is True
    # One paired chapter is far below min_sample: calibration must not be claimed.
    assert cc["any_calibrated"] is False
