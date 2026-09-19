"""test_promise_detectors.py — Promise detectors tests (Stage B.2).

Tests the unified detection layer.
"""
import pytest
from unittest.mock import Mock

from runtime.promise.detectors import (
    detect_packaging_promises,
    detect_narrative_setups,
    detect_plot_threads,
    detect_all_promises,
    detect_promises_summary,
)


def test_detect_packaging_promises_empty():
    """Test detecting promises from empty packaging."""
    promises = detect_packaging_promises(None, [])
    assert len(promises) == 0

    promises = detect_packaging_promises({}, [])
    assert len(promises) == 0


def test_detect_packaging_promises_basic():
    """Test detecting promises from packaging."""
    packaging = {
        "promises": [
            {
                "promise_id": "P1",
                "promise_type": "金手指",
                "statement": "主角将获得特殊能力",
                "must_appear_by": 3,
                "evidence_terms": ["梦晶", "精神力"],
            },
            {
                "promise_id": "P2",
                "promise_type": "复仇",
                "statement": "主角将复仇",
                "must_appear_by": 5,
                "evidence_terms": ["报仇"],
            },
        ]
    }

    promises = detect_packaging_promises(packaging, [])

    assert len(promises) == 2
    assert promises[0].type == "packaging"
    assert promises[0].level == "critical"
    assert promises[0].must_deliver_by == 3
    assert "梦晶" in promises[0].evidence_terms
    assert promises[1].must_deliver_by == 5


def test_detect_narrative_setups_empty():
    """Test detecting setups from empty registry."""
    mock_reg = Mock()
    mock_reg.facts = {}

    setups = detect_narrative_setups(mock_reg, [])
    assert len(setups) == 0


def test_detect_narrative_setups_basic():
    """Test detecting narrative setups from events."""
    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "[伏笔] 神秘人物出现",
            "notes": "",
            "sequence_index": 0,
        },
        "EVT-00002": {
            "summary": "普通事件",
            "notes": "",
            "sequence_index": 1,
        },
        "EVT-00003": {
            "summary": "神秘线索",
            "notes": "[setup] 发现古老遗迹",
            "sequence_index": 2,
        },
    }

    setups = detect_narrative_setups(mock_reg, [])

    assert len(setups) == 2
    assert all(s.type == "narrative" for s in setups)
    assert all(s.level == "important" for s in setups)
    assert setups[0].created_at_chapter == 1  # sequence_index 0 => chapter 1
    assert setups[1].created_at_chapter == 3  # sequence_index 2 => chapter 3


def test_detect_narrative_setups_delivered():
    """Test detecting delivered narrative setups."""
    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "[伏笔] 埋下线索",
            "notes": "",
            "sequence_index": 0,
        },
        "EVT-00002": {
            "summary": "回收伏笔",
            "notes": "",
            "sequence_index": 1,
            "causes": ["EVT-00001"],  # References EVT-00001
        },
    }

    setups = detect_narrative_setups(mock_reg, [])

    assert len(setups) == 1
    assert setups[0].status == "delivered"  # EVT-00001 was picked up by EVT-00002


def test_detect_plot_threads_empty():
    """Test detecting threads from empty registry."""
    mock_reg = Mock()
    mock_reg.facts = {}

    threads = detect_plot_threads(mock_reg, [])
    assert len(threads) == 0


def test_detect_plot_threads_basic():
    """Test detecting open plot threads."""
    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "引发事件",
            "notes": "",
            "sequence_index": 0,
        },
        "EVT-00002": {
            "summary": "悬而未决",
            "notes": "",
            "sequence_index": 1,
            "causes": ["EVT-00001"],  # Has cause but no effect
        },
        "EVT-00003": {
            "summary": "已解决",
            "notes": "",
            "sequence_index": 2,
            "causes": ["EVT-00001"],
            "effects": ["something"],  # Has effect, so not open
        },
    }

    threads = detect_plot_threads(mock_reg, [])

    # Only EVT-00002 is an open thread (has cause but no effect)
    assert len(threads) == 1
    assert threads[0].type == "thread"
    assert threads[0].level == "optional"
    assert threads[0].status == "open"
    assert threads[0].created_in_event == "EVT-00002"


def test_detect_all_promises_integration():
    """Test detecting all promises from all sources."""
    packaging = {
        "promises": [
            {
                "promise_id": "P1",
                "statement": "包装承诺",
                "must_appear_by": 3,
                "evidence_terms": ["关键词"],
            },
        ]
    }

    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "[伏笔] 叙事伏笔",
            "sequence_index": 0,
        },
        "EVT-00002": {
            "summary": "线索",
            "causes": ["EVT-00001"],
            "sequence_index": 1,
        },
    }

    all_promises = detect_all_promises(mock_reg, packaging)

    # Should have: 1 packaging + 1 narrative + 1 thread
    assert len(all_promises) == 3
    types = [p.type for p in all_promises]
    assert "packaging" in types
    assert "narrative" in types
    assert "thread" in types


def test_detect_promises_summary():
    """Test promise detection summary."""
    packaging = {
        "promises": [
            {"promise_id": "P1", "statement": "Test", "evidence_terms": ["x"]},
            {"promise_id": "P2", "statement": "Test2", "evidence_terms": ["y"]},
        ]
    }

    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {"summary": "[伏笔] Setup", "sequence_index": 0},
    }

    summary = detect_promises_summary(mock_reg, packaging)

    assert summary["total"] == 3
    assert summary["by_type"]["packaging"] == 2
    assert summary["by_type"]["narrative"] == 1
    assert summary["by_type"]["thread"] == 0
    assert summary["by_level"]["critical"] == 2  # packaging
    assert summary["by_level"]["important"] == 1  # narrative
    assert summary["with_deadlines"] == 2  # Both packaging have deadlines


def test_detector_id_generation():
    """Test that detectors generate non-conflicting IDs."""
    packaging = {
        "promises": [
            {"promise_id": "P1", "statement": "First", "evidence_terms": []},
        ]
    }

    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {"summary": "[伏笔] Second", "sequence_index": 0},
    }

    all_promises = detect_all_promises(mock_reg, packaging)

    # IDs should be sequential and unique
    ids = [p.id for p in all_promises]
    assert len(ids) == len(set(ids))  # All unique
    assert ids[0] == "PROMISE-00001"
    assert ids[1] == "PROMISE-00002"


def test_detector_marker_cleanup():
    """Test that [伏笔] markers are cleaned from statements."""
    mock_reg = Mock()
    mock_reg.facts = {
        "EVT-00001": {
            "summary": "[伏笔] 这是一个伏笔",
            "sequence_index": 0,
        },
        "EVT-00002": {
            "summary": "正常内容 【伏笔】 更多内容",
            "notes": "[setup] 注释中的标记",
            "sequence_index": 1,
        },
    }

    setups = detect_narrative_setups(mock_reg, [])

    # Markers should be removed from statements
    assert "[伏笔]" not in setups[0].statement
    assert "这是一个伏笔" in setups[0].statement
    assert "【伏笔】" not in setups[1].statement
    assert "[setup]" not in setups[1].statement
