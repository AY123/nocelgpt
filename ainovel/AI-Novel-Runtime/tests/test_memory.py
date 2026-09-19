from pathlib import Path

from runtime.registry_loader import Registry
from runtime.validator import (
    _check_temporal_causal,
    registered_checks,
    AXIS_GATE,
)
from runtime.memory.threads import track_threads


def _reg(facts: dict) -> Registry:
    return Registry(project_path=Path("/tmp/none"), version=1,
                    standard_pin="2.0.0", facts=facts)


# --------------------------------------------------------------------------- #
# Layer 1 — temporal-causal GATE check (deterministic, may block)             #
# --------------------------------------------------------------------------- #
def test_temporal_check_is_registered_as_gate():
    checks = dict(registered_checks())
    assert checks.get("temporal") == AXIS_GATE


def test_cause_before_effect_passes():
    reg = _reg({
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 1, "timeline": "TML-00001",
                      "causes": [], "effects": ["EVT-00002"]},
        "EVT-00002": {"id": "EVT-00002", "sequence_index": 2, "timeline": "TML-00001",
                      "causes": ["EVT-00001"], "effects": []},
    })
    assert _check_temporal_causal(reg) == []


def test_cause_after_effect_is_flagged():
    # EVT-00002 (index 2) claims to be caused by EVT-00003 (index 5) — the cause
    # happens AFTER its effect: a timeline break.
    reg = _reg({
        "EVT-00002": {"id": "EVT-00002", "sequence_index": 2, "timeline": "TML-00001",
                      "causes": ["EVT-00003"], "effects": []},
        "EVT-00003": {"id": "EVT-00003", "sequence_index": 5, "timeline": "TML-00001",
                      "causes": [], "effects": []},
    })
    findings = _check_temporal_causal(reg)
    assert len(findings) == 1
    assert findings[0].check == "temporal"
    assert "does not precede" in findings[0].message


def test_missing_sequence_index_is_not_flagged():
    # Sparsely-indexed data (like fixtures) must never be falsely flagged.
    reg = _reg({
        "EVT-00001": {"id": "EVT-00001", "timeline": "TML-00001", "causes": [], "effects": []},
        "EVT-00002": {"id": "EVT-00002", "timeline": "TML-00001",
                      "causes": ["EVT-00001"], "effects": []},
    })
    assert _check_temporal_causal(reg) == []


def test_cross_timeline_causes_not_compared():
    # Different timelines: a single integer index doesn't define ordering.
    reg = _reg({
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 9, "timeline": "TML-00002",
                      "causes": [], "effects": []},
        "EVT-00002": {"id": "EVT-00002", "sequence_index": 2, "timeline": "TML-00001",
                      "causes": ["EVT-00001"], "effects": []},
    })
    assert _check_temporal_causal(reg) == []


def test_equal_index_is_flagged():
    # A cause at the SAME index as its effect does not strictly precede it.
    reg = _reg({
        "EVT-00002": {"id": "EVT-00002", "sequence_index": 3, "timeline": "TML-00001",
                      "causes": ["EVT-00001"], "effects": []},
        "EVT-00001": {"id": "EVT-00001", "sequence_index": 3, "timeline": "TML-00001",
                      "causes": [], "effects": []},
    })
    assert len(_check_temporal_causal(reg)) == 1


# --------------------------------------------------------------------------- #
# Layer 2 — thread tracker (advisory, NEVER gates)                            #
# --------------------------------------------------------------------------- #
def test_thread_report_never_gates():
    report = track_threads(_reg({}))
    assert report.gating is False
    assert report.to_dict()["gating"] is False


def test_dangling_setup_detected():
    reg = _reg({
        "EVT-00001": {"id": "EVT-00001", "summary": "主角捡到一枚古怪玉佩 [伏笔]",
                      "causes": [], "effects": []},
        "EVT-00002": {"id": "EVT-00002", "summary": "主角进城，玉佩发烫暗示危险",
                      "causes": ["EVT-00001"], "effects": []},
    })
    report = track_threads(reg)
    # EVT-00001 is a setup AND is picked up by EVT-00002 (paid off) -> NOT dangling
    assert not any(d["event"] == "EVT-00001" for d in report.dangling_setups)


def test_unpaid_foreshadow_is_flagged():
    reg = _reg({
        "EVT-00001": {"id": "EVT-00001", "summary": "神秘老者留下预言 [伏笔]",
                      "causes": [], "effects": []},
    })
    report = track_threads(reg)
    assert any(d["event"] == "EVT-00001" for d in report.dangling_setups)
    assert any(f["check"] == "dangling-setup" for f in report.findings)


def test_orphan_item_held_by_inactive_character():
    reg = _reg({
        "CHR-00009": {"id": "CHR-00009", "status": "tombstoned"},
        "ITM-00001": {"id": "ITM-00001", "owner": "CHR-00009",
                      "origin_event": "EVT-00001"},
    })
    report = track_threads(reg)
    assert any(o["item"] == "ITM-00001" and o.get("owner") == "CHR-00009"
               for o in report.orphan_items)


def test_orphan_item_with_no_owner_or_origin():
    reg = _reg({
        "ITM-00002": {"id": "ITM-00002"},
    })
    report = track_threads(reg)
    assert any(o["item"] == "ITM-00002" for o in report.orphan_items)


def test_clean_registry_has_no_orphans_or_dangling():
    reg = _reg({
        "CHR-00001": {"id": "CHR-00001", "status": "active"},
        "ITM-00001": {"id": "ITM-00001", "owner": "CHR-00001",
                      "origin_event": "EVT-00001"},
        "EVT-00001": {"id": "EVT-00001", "summary": "普通事件",
                      "causes": [], "effects": ["EVT-00002"]},
        "EVT-00002": {"id": "EVT-00002", "summary": "后续", "causes": ["EVT-00001"],
                      "effects": []},
    })
    report = track_threads(reg)
    assert report.orphan_items == []
    assert report.dangling_setups == []
