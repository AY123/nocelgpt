"""test_publishing.py — Publishing OS (roadmap 4.6, the final Phase-4 piece).

Pins the 4.6 invariants: the Production Card is a per-chapter read-side fold that
CITES publish-readiness (never recomputes it); the Volume/Direction review folds a
window of cards into a health verdict; the Direction review PROPOSES a Market
Position revision where production diverged from the thesis (never auto-written,
ADR-009); the dashboard grows a book_health verdict from signals it already folds;
everything is deterministic, never gates (ADR-003), authority stays human, and the
verdicts validate against the Standard schemas.

Read-side + fixture-validated — no live model needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from runtime.publishing.card import build_production_card, write_production_card
from runtime.publishing.review import build_review, _summarize, _position_revision
from runtime.dashboard.report import _book_health_section

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_CARD_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "production-card.schema.json").read_text(encoding="utf-8")))
_REVIEW_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "review-report.schema.json").read_text(encoding="utf-8")))


def _errs(validator, obj) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in validator.iter_errors(obj)]


# --------------------------------------------------------------------------- #
# A minimal project fixture: draft envelopes in a derived index                #
# --------------------------------------------------------------------------- #
def _draft_envelope(task_id, *, qa=None, publish=None, commercial=None,
                    content_hash="sha256:x"):
    """A draft-on-disk envelope: inner ChapterDraft + optional sibling signals."""
    env = {"artifact_format": "anes.v2", "kind": "prose", "capability": "ChapterDraft",
           "task_id": task_id, "content_hash": content_hash, "body": "正文"}
    if qa is not None:
        env["qa_review"] = qa
    if publish is not None:
        env["publish_readiness"] = publish
    if commercial is not None:
        env["commercial_session"] = commercial
    return env


def _scaffold_project(tmp_path, chapters):
    """chapters: list of (task_id, envelope dict). Writes each under
    registry/derived/drafts/ and builds the derived index the readers use."""
    drafts_dir = tmp_path / "registry" / "derived" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for task_id, env in chapters:
        rel = f"registry/derived/drafts/{task_id}.json"
        (tmp_path / rel).write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
        artifacts.append({"id": task_id, "category": "drafts", "path": rel})
    index = {"artifacts": artifacts}
    meta = tmp_path / "registry" / "derived"
    (meta / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    # derived._load_index resolves the index; write both common names to be safe
    (meta / "_index.yaml").write_text(yaml.safe_dump(index, allow_unicode=True),
                                      encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------- #
# Production Card                                                              #
# --------------------------------------------------------------------------- #
def test_card_cites_publish_readiness_and_validates(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope(
            "TASK-00001",
            qa={"reviewer": "panel", "scores": {"retention": 80, "subscription": 70,
                                                "payoff": 75, "reader_drop_risk": 20}},
            publish={"recommendation": "recommend",
                     "basis": {"redline": {"passed": True}},
                     "rationale": "clean"})),
    ])
    card = build_production_card(tmp_path, "TASK-00001")
    assert card["gating"] is False
    assert card["authority"] == "human"
    # cites (does not recompute) the envelope's publish-readiness
    assert card["publish_readiness"]["recommendation"] == "recommend"
    assert card["publish_readiness"]["redline_passed"] is True
    assert card["quality"]["retention"] == 80
    assert _errs(_CARD_SCHEMA, card) == []


def test_card_flags_blocked_and_high_drop_risk(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope(
            "TASK-00001",
            qa={"reviewer": "panel", "scores": {"retention": 40, "reader_drop_risk": 75}},
            publish={"recommendation": "block",
                     "basis": {"redline": {"passed": False}}},
            commercial={"verdict": "regressed",
                        "rounds": [{"mean_pay_probability_delta": -8,
                                    "newly_pay_lost": ["打赏党"]}]})),
    ])
    card = build_production_card(tmp_path, "TASK-00001")
    assert "publish-blocked" in card["flags"]
    assert "high-drop-risk" in card["flags"]
    assert "pay-leak" in card["flags"]
    assert card["commercial"]["pay_probability_delta"] == -8
    assert _errs(_CARD_SCHEMA, card) == []


def test_card_degrades_when_no_publish_readiness(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001",
                                       qa={"reviewer": "j", "scores": {"retention": 70}})),
    ])
    card = build_production_card(tmp_path, "TASK-00001")
    assert card["publish_readiness"]["recommendation"] == "unknown"
    assert "publish-unknown" in card["flags"]
    assert _errs(_CARD_SCHEMA, card) == []


# --------------------------------------------------------------------------- #
# Volume / Direction review                                                    #
# --------------------------------------------------------------------------- #
def test_summarize_health_matches_dashboard_precedence():
    # low retention + high drop risk -> at_risk (not merely watch)
    cards = [
        {"quality": {"retention": 40, "reader_drop_risk": 70},
         "publish_readiness": {"recommendation": "hold"}, "commercial": {}},
        {"quality": {"retention": 50, "reader_drop_risk": 65},
         "publish_readiness": {"recommendation": "recommend"}, "commercial": {}},
    ]
    s = _summarize(cards)
    assert s["health"] == "at_risk"
    assert s["quality_averages"]["retention"] == 45.0


def test_volume_review_validates_and_never_gates(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001",
            qa={"reviewer": "j", "scores": {"retention": 80, "reader_drop_risk": 20}},
            publish={"recommendation": "recommend", "basis": {"redline": {"passed": True}}})),
        ("TASK-00002", _draft_envelope("TASK-00002",
            qa={"reviewer": "j", "scores": {"retention": 78, "reader_drop_risk": 25}},
            publish={"recommendation": "recommend", "basis": {"redline": {"passed": True}}})),
    ])
    review = build_review(tmp_path, scope="volume")
    assert review["gating"] is False
    assert review["authority"] == "human"
    assert review["scope"] == "volume"
    assert review["window"]["chapters_in_window"] == 2
    assert review["summary"]["health"] == "healthy"
    # volume review carries NO market_position_revision
    assert "market_position_revision" not in review
    assert _errs(_REVIEW_SCHEMA, review) == []


def test_direction_review_proposes_position_revision(tmp_path):
    # sagging retention over the window + an authored position -> proposes edits
    chapters = []
    for i in range(1, 4):
        chapters.append((f"TASK-{i:05d}", _draft_envelope(
            f"TASK-{i:05d}",
            qa={"reviewer": "j", "scores": {"retention": 45, "reader_drop_risk": 70}},
            publish={"recommendation": "hold", "basis": {"redline": {"passed": True}}})))
    _scaffold_project(tmp_path, chapters)
    (tmp_path / "sources").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sources" / "market-position.yaml").write_text(yaml.safe_dump({
        "id": "MPOS-00001", "kind": "market_position", "version": "1.0", "channel": "男频",
        "reader_segment": {"primary": "读者", "drop_triggers": ["节奏慢"]},
        "trope_map": {"leans_on": ["逆袭"]},
        "commercial_promise": {"pay_trigger": "打脸", "first_30_hook": "开局钩子",
                               "sustainability_100": "升级线"},
    }, allow_unicode=True), encoding="utf-8")

    review = build_review(tmp_path, scope="direction", size=3, standard_root=STANDARD)
    assert review["scope"] == "direction"
    assert review["summary"]["health"] == "at_risk"
    rev = review["market_position_revision"]
    assert rev["proposed"] is True
    fields = {e["field"] for e in rev["edits"]}
    # retention sag -> sustainability edit; drop risk -> drop_triggers; holds -> pay_trigger
    assert "commercial_promise.sustainability_100" in fields
    assert "reader_segment.drop_triggers" in fields
    assert rev["market_position_id"] == "MPOS-00001"
    assert _errs(_REVIEW_SCHEMA, review) == []


def test_direction_review_no_position_proposes_nothing(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001",
            qa={"reviewer": "j", "scores": {"retention": 40, "reader_drop_risk": 80}},
            publish={"recommendation": "hold", "basis": {"redline": {"passed": True}}})),
    ])
    review = build_review(tmp_path, scope="direction", size=1, standard_root=STANDARD)
    assert review["market_position_revision"]["proposed"] is False
    assert _errs(_REVIEW_SCHEMA, review) == []


def test_review_is_deterministic(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001",
            qa={"reviewer": "j", "scores": {"retention": 70}},
            publish={"recommendation": "recommend", "basis": {"redline": {"passed": True}}})),
    ])
    a = build_review(tmp_path, scope="volume")
    b = build_review(tmp_path, scope="volume")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --------------------------------------------------------------------------- #
# Dashboard book_health (operations-board verdict)                             #
# --------------------------------------------------------------------------- #
def test_book_health_at_risk_on_low_retention_trend():
    qt = {"dimension_averages": {"retention": 45, "reader_drop_risk": 70}}
    h = _book_health_section(schedule=None, production={}, quality_trend=qt,
                             pacing=None, latest_signals={})
    assert h["health"] == "at_risk"
    assert h["gating"] is False
    assert any("retention" in r for r in h["reasons"])


def test_book_health_watch_on_thin_stock_and_hold():
    h = _book_health_section(
        schedule={"break_risk": "none"},
        production={"funnel": {"thin_stock": True, "ready": 2, "ready_target": 10}},
        quality_trend={"dimension_averages": {"retention": 75, "reader_drop_risk": 20}},
        pacing=None,
        latest_signals={"publish_readiness": {"recommendation": "hold"}})
    assert h["health"] == "watch"


def test_book_health_healthy_when_all_clear():
    h = _book_health_section(
        schedule={"break_risk": "none"},
        production={"funnel": {"thin_stock": False}},
        quality_trend={"dimension_averages": {"retention": 80, "reader_drop_risk": 20}},
        pacing={"chapters_with_pacing_warnings": 0},
        latest_signals={"publish_readiness": {"recommendation": "recommend"}})
    assert h["health"] == "healthy"
    assert h["reasons"] == ["no attention signals"]


def test_book_health_thresholds_in_sync_with_review():
    from runtime.dashboard import report as dash
    from runtime.publishing import review as rev
    assert dash._RETENTION_WATCH_AT == rev._RETENTION_WATCH_AT
    assert dash._DROP_RISK_WATCH_AT == rev._DROP_RISK_WATCH_AT
