"""test_state.py — StoryState projection (roadmap P14, ADR-008).

Story State is a pure fold over facts, never mutable state. These tests pin the
ADR-008 invariants: reproducibility, fold-driven change (append a fact, don't
flip a flag), the story cursor, deterministic ordering, and never-gates.
"""
from pathlib import Path

from runtime.registry_loader import Registry
from runtime.memory.state import project_state, state_artifact, _ordered_event_ids


def _reg(facts: dict, *, version: int = 1) -> Registry:
    return Registry(project_path=Path("/tmp/none"), version=version,
                    standard_pin="2.0.0", facts=facts)


_TWO_EVENTS = {
    "EVT-00001": {"id": "EVT-00001", "sequence_index": 1, "timeline": "TML-00001",
                  "summary": "开端", "participants": ["CHR-00001"],
                  "causes": [], "effects": ["EVT-00002"]},
    "EVT-00002": {"id": "EVT-00002", "sequence_index": 2, "timeline": "TML-00001",
                  "summary": "转折", "participants": ["CHR-00001", "CHR-00002"],
                  "causes": ["EVT-00001"], "effects": []},
    "CHR-00001": {"id": "CHR-00001", "name": "主角", "status": "active"},
    "CHR-00002": {"id": "CHR-00002", "name": "导师", "status": "active"},
    "TML-00001": {"id": "TML-00001", "name": "主线", "kind": "main"},
}


# --------------------------------------------------------------------------- #
# ADR-008 core: pure, reproducible fold                                        #
# --------------------------------------------------------------------------- #
def test_projection_never_gates():
    state = project_state(_reg({}))
    assert state.gating is False
    assert state.to_dict()["gating"] is False


def test_projection_is_reproducible():
    reg = _reg(dict(_TWO_EVENTS))
    a = project_state(reg)
    b = project_state(reg)
    assert a.state_hash == b.state_hash
    assert a.state_hash.startswith("sha256:")


def test_hash_ignores_reviewer_label():
    reg = _reg(dict(_TWO_EVENTS))
    a = project_state(reg, reviewer_id="one")
    b = project_state(reg, reviewer_id="two")
    # reviewer is cosmetic; the projection body (and thus the hash) is identical
    assert a.state_hash == b.state_hash


# --------------------------------------------------------------------------- #
# ADR-008: advancing the story appends a fact — it does NOT mutate state       #
# --------------------------------------------------------------------------- #
def test_appending_an_event_changes_the_projection():
    before = project_state(_reg(dict(_TWO_EVENTS)))
    grown = dict(_TWO_EVENTS)
    grown["EVT-00003"] = {"id": "EVT-00003", "sequence_index": 3,
                          "timeline": "TML-00001", "summary": "新章",
                          "participants": ["CHR-00001"],
                          "causes": ["EVT-00002"], "effects": []}
    after = project_state(_reg(grown))
    assert after.state_hash != before.state_hash
    assert after.event_order == ["EVT-00001", "EVT-00002", "EVT-00003"]
    assert after.timelines["TML-00001"]["events_so_far"] == 3


def test_cursor_folds_only_events_up_to_it():
    reg = _reg(dict(_TWO_EVENTS))
    full = project_state(reg)
    at1 = project_state(reg, up_to_event="EVT-00001")
    assert at1.event_order == ["EVT-00001"]
    assert at1.up_to_event == "EVT-00001"
    # a different cursor is a different point-in-time => a different hash
    assert at1.state_hash != full.state_hash
    # CHR-00002 first appears at EVT-00002, so it has no appearance yet at EVT-00001
    assert at1.characters["CHR-00002"]["appears_in"] == []
    assert full.characters["CHR-00002"]["appears_in"] == ["EVT-00002"]


def test_relationship_ends_when_its_until_event_is_folded_in():
    facts = dict(_TWO_EVENTS)
    facts["REL-00001"] = {"id": "REL-00001", "kind": "mentor",
                          "from": "CHR-00002", "to": "CHR-00001",
                          "since_event": "EVT-00001", "until_event": "EVT-00002"}
    reg = _reg(facts)
    # before the severance event: relationship is active (no flag was flipped —
    # EVT-00002 simply hasn't been folded in yet)
    assert project_state(reg, up_to_event="EVT-00001").relationships["REL-00001"]["active"] is True
    # after folding EVT-00002: the same facts project an ended relationship
    assert project_state(reg).relationships["REL-00001"]["active"] is False


# --------------------------------------------------------------------------- #
# ADR-008: deterministic total order (reuses sequence_index)                   #
# --------------------------------------------------------------------------- #
def test_order_is_by_sequence_index_then_id():
    facts = {
        "EVT-00005": {"id": "EVT-00005", "sequence_index": 2},
        "EVT-00002": {"id": "EVT-00002", "sequence_index": 1},
        "EVT-00009": {"id": "EVT-00009", "sequence_index": 2},  # tie with 00005
    }
    # index 1 first; then the index-2 tie broken by id (00005 before 00009)
    assert _ordered_event_ids(facts) == ["EVT-00002", "EVT-00005", "EVT-00009"]


def test_unindexed_events_fold_after_indexed_in_id_order():
    facts = {
        "EVT-00003": {"id": "EVT-00003"},               # no sequence_index
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 7},
        "EVT-00002": {"id": "EVT-00002"},               # no sequence_index
    }
    assert _ordered_event_ids(facts) == ["EVT-00001", "EVT-00002", "EVT-00003"]


# --------------------------------------------------------------------------- #
# ADR-008: foreshadow resolution falls out of the fold                         #
# --------------------------------------------------------------------------- #
def test_unpaid_setup_is_open_then_resolved_by_a_later_event():
    setup_only = {
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 1,
                      "summary": "神秘老者留下预言 [伏笔]", "causes": [], "effects": []},
    }
    s = project_state(_reg(setup_only))
    assert any(x["event"] == "EVT-00001" for x in s.open_setups)
    assert s.resolved_setups == []

    # author a payoff event (append a fact) — the setup moves to resolved on its
    # own; no flag was flipped on EVT-00001
    paid = dict(setup_only)
    paid["EVT-00002"] = {"id": "EVT-00002", "sequence_index": 2,
                         "summary": "预言应验", "causes": ["EVT-00001"], "effects": []}
    s2 = project_state(_reg(paid))
    assert any(x["event"] == "EVT-00001" for x in s2.resolved_setups)
    assert not any(x["event"] == "EVT-00001" for x in s2.open_setups)


# --------------------------------------------------------------------------- #
# ADR-006: the projection is a pinned Derived artifact (inherits staleness)    #
# --------------------------------------------------------------------------- #
def test_state_artifact_pins_every_source_at_its_fact_version():
    facts = {
        "CHR-00001": {"id": "CHR-00001", "name": "主角", "status": "active",
                      "fact_version": 5},
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 1, "fact_version": 3,
                      "causes": [], "effects": []},
    }
    reg = _reg(facts, version=7)
    state = project_state(reg)
    art = state_artifact(reg, state)
    assert art["content_hash"] == state.state_hash
    assert art["provenance"]["source_version"] == 7
    assert set(art["provenance"]["derived_from"]) == {"CHR-00001@v5", "EVT-00001@v3"}
    assert art["kind"] == "story-state"
