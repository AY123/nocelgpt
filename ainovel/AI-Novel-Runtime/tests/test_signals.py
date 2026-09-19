"""test_signals.py — Reader Signal Store (roadmap Phase 5.6), the Phase 5 closer.

Pins the invariants of the REAL-signal seam:
  - A well-formed reader signal is schema-valid; a malformed one fails validation.
  - ABSENCE is not an error: a project with no signals loads as [] (like the
    Brain / Market Snapshot).
  - The reconcile is COMPARISON-ONLY and NEVER GATES (ADR-003), and NEVER
    calibrates the model (roadmap: the seam is wired, not fired).
  - Only continue_rate ↔ retention_rate is a real gap; other metrics are reported
    side-by-side WITHOUT a fabricated prediction (personas ≠ real readers).
  - Low confidence is surfaced so a noisy real number is never over-read.
  - No prediction → a real-only readout, never a crash.

Deterministic — no live model.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime.signals import (load_reader_signals, signal_for_chapter,
                             validate_signal, reconcile_signal)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_SIGNAL_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "reader-signal.schema.json").read_text(encoding="utf-8")))


def _errors(sig: dict) -> list:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _SIGNAL_SCHEMA.iter_errors(sig)]


def _good_signal(**over) -> dict:
    sig = {
        "kind": "reader_signal", "version": "1.0", "scope": "chapter",
        "chapter_id": "TASK-00001", "source": "起点", "collected_at": "2026-07-01",
        "metrics": {"retention_rate": 55, "first_day_subscriptions": 1200,
                    "reward_count": 30},
        "confidence": {"level": "high", "sample_size": 5000},
    }
    sig.update(over)
    return sig


def _import(project: Path, name: str, sig: dict):
    d = project / "sources" / "reader-signals"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(yaml.safe_dump(sig, allow_unicode=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Schema                                                                       #
# --------------------------------------------------------------------------- #
def test_wellformed_signal_is_schema_valid():
    assert _errors(_good_signal()) == []


def test_book_scope_signal_is_valid():
    # a book-level signal needs no chapter_id (it is optional in the schema)
    sig = {"kind": "reader_signal", "version": "1.0", "scope": "book",
           "source": "番茄", "collected_at": "2026-07-01",
           "metrics": {"subscription_count": 90000},
           "confidence": {"level": "medium"}}
    assert _errors(sig) == []


def test_unknown_metric_fails_validation():
    bad = _good_signal()
    bad["metrics"]["clicks"] = 999  # not in the fixed metric set
    assert _errors(bad) != []


def test_bad_scope_fails_validation():
    assert _errors(_good_signal(scope="paragraph")) != []


def test_validate_signal_helper_matches_schema(tmp_path):
    assert validate_signal(_good_signal(), standard_root=STANDARD) == []
    assert validate_signal(_good_signal(scope="paragraph"), standard_root=STANDARD) != []


# --------------------------------------------------------------------------- #
# Loader — graceful absence + chapter lookup                                   #
# --------------------------------------------------------------------------- #
def test_absent_signals_load_as_empty(tmp_path):
    assert load_reader_signals(tmp_path) == []


def test_underscore_files_are_skipped(tmp_path):
    _import(tmp_path, "_EXAMPLE.yaml", _good_signal())
    assert load_reader_signals(tmp_path) == []


def test_signal_for_chapter_finds_most_recent(tmp_path):
    _import(tmp_path, "old.yaml", _good_signal(collected_at="2026-06-01",
                                               metrics={"retention_rate": 40}))
    _import(tmp_path, "new.yaml", _good_signal(collected_at="2026-07-01",
                                               metrics={"retention_rate": 55}))
    sig = signal_for_chapter(tmp_path, "TASK-00001")
    assert sig is not None
    assert sig["metrics"]["retention_rate"] == 55  # the later measurement wins
    assert signal_for_chapter(tmp_path, "TASK-99999") is None


# --------------------------------------------------------------------------- #
# Reconcile — comparison-only, never gates, never calibrates                   #
# --------------------------------------------------------------------------- #
def test_reconcile_is_comparison_only_and_never_gates():
    r = reconcile_signal({"continue_rate": 70}, _good_signal())
    assert r["comparison_only"] is True
    assert r["gating"] is False
    assert r["calibrates"] is False


def test_retention_gap_is_deterministic_and_directional():
    r = reconcile_signal({"continue_rate": 70}, _good_signal())  # real retention 55
    ret = next(c for c in r["comparisons"] if c["metric"] == "retention")
    assert ret["predicted"] == 70
    assert ret["real"] == 55
    assert ret["gap"] == 15                    # predicted - real
    assert ret["direction"] == "prediction optimistic"


def test_non_retention_metrics_have_no_fabricated_prediction():
    r = reconcile_signal({"continue_rate": 70}, _good_signal())
    for c in r["comparisons"]:
        if c["metric"] != "retention":
            assert c["predicted"] is None
            assert c["gap"] is None
            assert c["direction"] == "no comparable prediction"


def test_low_confidence_is_flagged():
    sig = _good_signal(confidence={"level": "low"})
    r = reconcile_signal({"continue_rate": 70}, sig)
    assert "LOW confidence" in r["note"]


def test_no_prediction_is_real_only_readout():
    r = reconcile_signal(None, _good_signal())
    assert r["comparison_only"] is True
    assert r["gating"] is False
    # no retention gap without a prediction; real numbers still reported
    assert all(c["gap"] is None for c in r["comparisons"])
    assert "real-only" in r["note"]
