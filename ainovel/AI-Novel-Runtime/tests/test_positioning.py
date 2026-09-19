"""test_positioning.py — Market Positioning / pre-book admission (roadmap 4.5).

Pins the 4.5 invariants: the admission check is a DETERMINISTIC fold of the
authored Market Position + Novel Brain + derived Market Snapshot into an
admit/revise/hold recommendation; it NEVER gates (ADR-003, gating const false);
the decision stays with a human (ADR-009, authority const human); it degrades
gracefully when any source is absent; the verdict validates against the Standard
schema; and the authored Position validates against its own schema.

Read-side + fixture-validated — no live model needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime.positioning import (load_position, validate_position,
                                 build_admission, project_admission)
from runtime.positioning.admission import write_admission

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_POS_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "market-position.schema.json").read_text(encoding="utf-8")))
_ADM_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "market-admission.schema.json").read_text(encoding="utf-8")))


def _adm_errors(v: dict) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _ADM_SCHEMA.iter_errors(v)]


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #
def _full_position() -> dict:
    return {
        "id": "MPOS-00001", "kind": "market_position", "version": "1.0",
        "channel": "男频",
        "reader_segment": {"primary": "追爽的男频升级读者",
                           "pull_triggers": ["打脸", "升级"],
                           "drop_triggers": ["节奏慢"]},
        "trope_map": {"leans_on": ["废柴逆袭", "扮猪吃虎"],
                      "subverts": ["金手指有代价"],
                      "differentiation": "金手指有代价的升级流"},
        "commercial_promise": {"pay_trigger": "第一次当众打脸",
                               "first_30_hook": "开局扮猪吃虎连环反转",
                               "sustainability_100": "境界升级线+复仇悬念线"},
    }


def _brain(channel="男频", forbidden=None) -> dict:
    return {"id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0",
            "genre": {"primary": "玄幻", "channel": channel},
            "forbidden_style": forbidden or ["注水"]}


def _snapshot(*, stale=False, channel="男频") -> dict:
    return {"id": "MARKET-00001", "kind": "market_snapshot",
            "channels": [{"channel": channel, "hot_genres": []}],
            "staleness": {"is_stale": stale, "gating": False},
            "signals": {"trending_genres": ["废柴逆袭流"],
                        "common_drop_points": ["节奏慢"]}}


# --------------------------------------------------------------------------- #
# Structural invariants: never gates, authority human, schema-valid            #
# --------------------------------------------------------------------------- #
def test_authored_position_validates_against_schema():
    assert list(_POS_SCHEMA.iter_errors(_full_position())) == []


def test_verdict_never_gates_and_authority_is_human():
    v = build_admission(_full_position(), _brain(), _snapshot())
    assert v["gating"] is False
    assert v["authority"] == "human"
    assert _adm_errors(v) == []


# --------------------------------------------------------------------------- #
# admit: complete + consistent positioning                                     #
# --------------------------------------------------------------------------- #
def test_complete_consistent_positioning_is_admitted():
    v = build_admission(_full_position(), _brain(), _snapshot())
    assert v["recommendation"] == "admit"
    # market alignments detected deterministically (trending genre + drop point)
    assert len(v["basis"]["external"]["alignments"]) == 2
    assert v["basis"]["internal"]["conflicts"] == []
    assert v["basis"]["completeness"]["missing"] == []
    assert v["sources"]["market_position_id"] == "MPOS-00001"


# --------------------------------------------------------------------------- #
# revise: fixable gaps                                                         #
# --------------------------------------------------------------------------- #
def test_missing_pay_trigger_forces_revise():
    pos = _full_position()
    del pos["commercial_promise"]["pay_trigger"]
    v = build_admission(pos, _brain(), _snapshot())
    assert v["recommendation"] == "revise"
    assert "commercial_promise.pay_trigger" in v["basis"]["completeness"]["missing"]
    assert _adm_errors(v) == []


def test_channel_conflict_with_brain_forces_revise():
    v = build_admission(_full_position(), _brain(channel="女频"), _snapshot())
    assert v["recommendation"] == "revise"
    assert any("channel mismatch" in c for c in v["basis"]["internal"]["conflicts"])


def test_leaning_on_a_brain_forbidden_trope_forces_revise():
    pos = _full_position()
    pos["trope_map"]["leans_on"] = ["大量注水桥段"]
    v = build_admission(pos, _brain(forbidden=["注水"]), _snapshot())
    assert v["recommendation"] == "revise"
    assert any("forbids" in c for c in v["basis"]["internal"]["conflicts"])


def test_channel_absent_from_snapshot_is_misalignment_revise():
    v = build_admission(_full_position(), _brain(), _snapshot(channel="女频"))
    assert v["recommendation"] == "revise"
    assert v["basis"]["external"]["misalignments"]
    assert v["basis"]["external"]["channel_in_snapshot"] is False


# --------------------------------------------------------------------------- #
# hold: nothing to open on                                                     #
# --------------------------------------------------------------------------- #
def test_absent_position_is_hold():
    v = build_admission(None, _brain(), _snapshot())
    assert v["recommendation"] == "hold"
    assert v["basis"]["completeness"]["position_authored"] is False
    assert _adm_errors(v) == []


# --------------------------------------------------------------------------- #
# Graceful degradation: missing brain / snapshot never fabricate a conflict    #
# --------------------------------------------------------------------------- #
def test_no_brain_no_snapshot_still_admits_complete_position():
    v = build_admission(_full_position(), None, None)
    assert v["recommendation"] == "admit"
    assert v["basis"]["internal"]["brain_authored"] is False
    assert v["basis"]["internal"]["conflicts"] == []
    assert v["basis"]["external"]["snapshot_present"] is False
    assert v["basis"]["external"]["misalignments"] == []
    assert _adm_errors(v) == []


def test_stale_snapshot_is_surfaced_but_still_admits():
    v = build_admission(_full_position(), _brain(), _snapshot(stale=True))
    assert v["recommendation"] == "admit"          # stale never gates/blocks
    assert v["basis"]["external"]["snapshot_stale"] is True
    assert "stale" in v["rationale"]


def test_admission_is_deterministic():
    a = build_admission(_full_position(), _brain(), _snapshot())
    b = build_admission(_full_position(), _brain(), _snapshot())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --------------------------------------------------------------------------- #
# End-to-end over a scaffolded project (loader + writer + fold)                #
# --------------------------------------------------------------------------- #
def test_project_admission_reads_sources_and_writes_derived(tmp_path):
    (tmp_path / "sources").mkdir(parents=True)
    (tmp_path / "sources" / "market-position.yaml").write_text(
        yaml.safe_dump(_full_position(), allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (tmp_path / "sources" / "novel-brain.yaml").write_text(
        yaml.safe_dump(_brain(), allow_unicode=True, sort_keys=False),
        encoding="utf-8")

    loaded = load_position(tmp_path)
    assert validate_position(loaded, standard_root=STANDARD) == []

    v = project_admission(tmp_path, standard_root=STANDARD)
    # no snapshot in the project -> external is advisory-only, still admits
    assert v["recommendation"] == "admit"
    assert v["basis"]["external"]["snapshot_present"] is False

    rel = write_admission(tmp_path, v)
    written = json.loads((tmp_path / rel).read_text(encoding="utf-8"))
    assert written["kind"] == "market_admission"
    assert _adm_errors(written) == []
    # written under derived/, never facts/
    assert "derived" in rel and "facts" not in rel


def test_all_commented_position_reads_as_absent(tmp_path):
    (tmp_path / "sources").mkdir(parents=True)
    (tmp_path / "sources" / "market-position.yaml").write_text(
        "# id: MPOS-00001\n# kind: market_position\n", encoding="utf-8")
    assert load_position(tmp_path) is None
    v = project_admission(tmp_path, standard_root=STANDARD)
    assert v["recommendation"] == "hold"
