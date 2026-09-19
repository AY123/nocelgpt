"""
测试 Production Decision Engine (P0-4)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.decision_engine import ProductionDecisionEngine, align_production_decision


def test_decision_engine_redline_failure_blocks():
    """测试红线失败返回 block"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=False,
        final_quality_scores={"hook": 80}
    )

    assert action == "block"
    assert any("redline" in issue.lower() for issue in blocking)
    assert len(warnings) == 0


def test_decision_engine_critical_deviation_blocks():
    """测试关键偏差返回 block"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        critical_deviations=1,
        redline_passed=True
    )

    assert action == "block"
    assert any("Critical" in issue for issue in blocking)


def test_decision_engine_quality_threshold_holds():
    """测试质量低于阈值返回 hold（需要校准后的decision级维度）"""
    engine = ProductionDecisionEngine()

    # P0-2: 未校准评分不应hold，需要提供校准状态
    calibration_status = {
        "status": "calibrated",
        "decision_dimensions": ["hook"],  # hook是decision级维度
        "diagnostic_dimensions": ["retention"]
    }

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        final_quality_scores={"hook": 70, "retention": 80},  # hook below 75
        calibration_status=calibration_status
    )

    assert action == "hold"
    assert len(blocking) == 0
    assert any("hook" in w and "threshold" in w for w in warnings)


def test_decision_engine_quality_degradation_holds():
    """测试质量退化返回 hold"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        final_quality_scores={"hook": 80, "retention": 75},
        quality_delta={
            "retention": {"initial": 90, "final": 75, "delta": -15}
        }
    )

    assert action == "hold"
    assert any("retention" in w and "degraded" in w for w in warnings)


def test_decision_engine_all_pass_publishes():
    """测试所有检查通过返回 publish"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        critical_deviations=0,
        final_quality_scores={
            "hook": 80,
            "retention": 80,
            "character_consistency": 85
        },
        dropout_risk=0.1
    )

    assert action == "publish"
    assert len(blocking) == 0
    assert len(warnings) == 0


def test_decision_engine_priority_order():
    """测试决策优先级：redline > critical > quality"""
    engine = ProductionDecisionEngine()

    # Redline failure overrides everything
    action, _, _ = engine.decide(
        redline_passed=False,
        critical_deviations=1,
        final_quality_scores={"hook": 70}
    )
    assert action == "block"

    # Critical deviation overrides quality
    action, _, _ = engine.decide(
        redline_passed=True,
        critical_deviations=1,
        final_quality_scores={"hook": 70}
    )
    assert action == "block"


def test_align_production_decision():
    """测试决策对齐功能"""
    production_card = {
        "critical_deviations": 0,
        "high_deviations": 0,
        "redline_passed": True,
        "final_quality_scores": {"hook": 70},  # Below threshold
        "quality_delta": {},
        "dropout_risk": None,
        "reader_simulation": {},
        "promises_pending": [],
        "strict_mode": False,
        "publish_recommendation": "recommend",  # Will be overridden
        "blocking_issues": [],
        "warnings": [],
    }

    comparison_report = {
        "pipeline_decision": {
            "action": "advance",
            "hold_for_human_review": False,
        }
    }

    # P0-2: 需要校准状态才能触发hold
    calibration_status = {
        "status": "calibrated",
        "decision_dimensions": ["hook"],
    }

    # Align decisions
    aligned = align_production_decision(production_card, comparison_report, calibration_status)

    # Production Card should now say "hold"
    assert aligned["publish_recommendation"] == "hold"
    assert any("hook" in w for w in aligned["warnings"])

    # Comparison Report should also say "hold"
    assert comparison_report["pipeline_decision"]["action"] == "hold"
    assert comparison_report["pipeline_decision"]["hold_for_human_review"] is True


def test_promise_overdue_holds():
    """测试逾期承诺返回 hold"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        promises_overdue=["PKG-001", "PKG-002"]
    )

    assert action == "hold"
    assert any("Overdue promises" in w for w in warnings)


def test_dropout_risk_holds():
    """测试高弃读风险返回 hold"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        final_quality_scores={"hook": 80, "retention": 80},
        dropout_risk=0.35,
        reader_simulation_degraded=False
    )

    assert action == "hold"
    assert any("dropout risk" in w.lower() for w in warnings)


def test_dropout_risk_ignored_when_degraded():
    """测试降级的reader simulation不触发hold"""
    engine = ProductionDecisionEngine()

    action, blocking, warnings = engine.decide(
        redline_passed=True,
        final_quality_scores={"hook": 80, "retention": 80},
        dropout_risk=0.35,
        reader_simulation_degraded=True  # Degraded - should ignore
    )

    assert action == "publish"
    assert len(warnings) == 0
