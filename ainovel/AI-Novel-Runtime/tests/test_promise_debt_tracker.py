"""
测试 Promise Debt Tracker (C3-1)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.promise_debt_tracker import (
    PromiseDebtTracker,
    PromiseDebtItem,
    DebtReport,
    PromiseUrgency,
)


def create_test_promise_ledger(current_chapter: int) -> dict:
    """创建测试用Promise Ledger"""
    return {
        "promises": [
            {
                "id": "PROMISE-001",
                "type": "setup",
                "description": "主角获得神秘力量",
                "created_chapter": current_chapter - 5,
                "status": "pending",
                "importance": 0.9,
                "reader_expectation": 0.8,
            },
            {
                "id": "PROMISE-002",
                "type": "relationship",
                "description": "与师父重逢",
                "created_chapter": current_chapter - 15,
                "status": "pending",
                "importance": 0.7,
                "reader_expectation": 0.6,
            },
            {
                "id": "PROMISE-003",
                "type": "foreshadow",
                "description": "揭示真相",
                "created_chapter": current_chapter - 25,
                "status": "pending",
                "importance": 0.95,
                "reader_expectation": 0.9,
            },
            {
                "id": "PROMISE-004",
                "type": "setup",
                "description": "学习新技能",
                "created_chapter": current_chapter - 2,
                "status": "pending",
                "importance": 0.5,
                "reader_expectation": 0.4,
            },
        ]
    }


def test_tracker_basic():
    """测试基础追踪功能"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(
        current_chapter=50,
        promise_ledger=ledger
    )

    assert report.current_chapter == 50
    assert report.total_pending_promises == 4


def test_urgency_calculation():
    """测试紧急程度计算"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)

    # PROMISE-003: 等待25章 -> CRITICAL
    assert len(report.critical_debts) == 1
    assert report.critical_debts[0].promise_id == "PROMISE-003"

    # PROMISE-002: 等待15章 -> HIGH
    assert len(report.high_urgency_debts) == 1
    assert report.high_urgency_debts[0].promise_id == "PROMISE-002"

    # PROMISE-001: 等待5章 -> LOW
    assert len(report.low_urgency_debts) == 1

    # PROMISE-004: 等待2章 -> NORMAL
    assert len(report.normal_debts) == 1


def test_statistics_calculation():
    """测试统计数据计算"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)

    # 平均等待: (5+15+25+2)/4 = 11.75
    assert abs(report.average_pending_chapters - 11.75) < 0.1

    # 最长等待: 25章
    assert report.max_pending_chapters == 25


def test_recommendations_critical():
    """测试严重债务建议"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)

    # 应该有严重逾期警告
    assert any("严重" in rec for rec in report.recommendations)
    assert any("1个Promise严重逾期" in rec for rec in report.recommendations)


def test_priority_sorting():
    """测试优先级排序"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)
    priorities = tracker.get_priority_promises(report, top_n=3)

    # 第一优先应该是PROMISE-003（CRITICAL + 高重要性 + 高期待）
    assert priorities[0].promise_id == "PROMISE-003"
    assert priorities[0].urgency == PromiseUrgency.CRITICAL

    # 应该返回3个
    assert len(priorities) == 3


def test_next_chapter_suggestions():
    """测试下一章建议"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)

    # 应该有建议
    assert len(report.next_chapter_suggestions) > 0

    # 第一个建议应该是关于PROMISE-003的
    first_suggestion = report.next_chapter_suggestions[0]
    assert "揭示真相" in first_suggestion
    assert "25章" in first_suggestion


def test_no_debt():
    """测试无债务情况"""
    tracker = PromiseDebtTracker()
    ledger = {"promises": []}

    report = tracker.analyze_debt(50, ledger)

    assert report.total_pending_promises == 0
    assert len(report.critical_debts) == 0
    assert report.average_pending_chapters == 0.0
    assert len(report.recommendations) == 0


def test_all_delivered():
    """测试所有Promise已兑现"""
    tracker = PromiseDebtTracker()
    ledger = {
        "promises": [
            {
                "id": "PROMISE-001",
                "type": "setup",
                "description": "测试",
                "created_chapter": 10,
                "status": "delivered",  # 已兑现
            }
        ]
    }

    report = tracker.analyze_debt(50, ledger)

    assert report.total_pending_promises == 0


def test_urgency_threshold_boundary():
    """测试紧急程度阈值边界"""
    tracker = PromiseDebtTracker()

    # 正好20章 -> CRITICAL
    ledger_20 = {
        "promises": [{
            "id": "P1",
            "type": "setup",
            "description": "测试",
            "created_chapter": 30,
            "status": "pending",
        }]
    }
    report_20 = tracker.analyze_debt(50, ledger_20)
    assert len(report_20.critical_debts) == 1

    # 19章 -> HIGH
    ledger_19 = {
        "promises": [{
            "id": "P1",
            "type": "setup",
            "description": "测试",
            "created_chapter": 31,
            "status": "pending",
        }]
    }
    report_19 = tracker.analyze_debt(50, ledger_19)
    assert len(report_19.high_urgency_debts) == 1


def test_summary_generation():
    """测试可读摘要生成"""
    tracker = PromiseDebtTracker()
    ledger = create_test_promise_ledger(current_chapter=50)

    report = tracker.analyze_debt(50, ledger)
    summary = tracker.generate_summary(report)

    # 检查关键信息
    assert "第50章" in summary
    assert "4个" in summary  # 总数
    assert "严重" in summary  # 有critical
    assert "建议" in summary


def test_multiple_critical():
    """测试多个严重债务"""
    tracker = PromiseDebtTracker()
    ledger = {
        "promises": [
            {
                "id": "P1",
                "type": "setup",
                "description": "Promise 1",
                "created_chapter": 10,
                "status": "pending",
            },
            {
                "id": "P2",
                "type": "setup",
                "description": "Promise 2",
                "created_chapter": 15,
                "status": "pending",
            }
        ]
    }

    report = tracker.analyze_debt(50, ledger)

    # 两个都是CRITICAL（等待40章和35章）
    assert len(report.critical_debts) == 2


def test_priority_with_importance():
    """测试优先级考虑重要性"""
    tracker = PromiseDebtTracker()
    ledger = {
        "promises": [
            {
                "id": "P1",
                "type": "setup",
                "description": "低重要性",
                "created_chapter": 30,
                "status": "pending",
                "importance": 0.3,
                "reader_expectation": 0.3,
            },
            {
                "id": "P2",
                "type": "setup",
                "description": "高重要性",
                "created_chapter": 30,  # 修改为相同创建章节，确保测试重要性
                "status": "pending",
                "importance": 0.9,
                "reader_expectation": 0.9,
            }
        ]
    }

    report = tracker.analyze_debt(50, ledger)
    priorities = tracker.get_priority_promises(report, top_n=2)

    # P2重要性更高，应该排第一
    assert priorities[0].promise_id == "P2"


def test_debt_overload_warning():
    """测试债务过载警告"""
    tracker = PromiseDebtTracker()

    # 创建12个pending Promise
    promises = [
        {
            "id": f"P{i}",
            "type": "setup",
            "description": f"Promise {i}",
            "created_chapter": 40,
            "status": "pending",
        }
        for i in range(12)
    ]

    ledger = {"promises": promises}
    report = tracker.analyze_debt(50, ledger)

    # 应该有债务过多警告
    assert any("债务过多" in rec for rec in report.recommendations)
    assert any("12个" in rec for rec in report.recommendations)
