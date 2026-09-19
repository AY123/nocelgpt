"""
P0-2: 未校准评分不应触发hold/block

测试未校准的LLM评分只能产生advisory警告，不能gate生产流程。
只有校准后的decision级维度才能触发hold。
"""
import pytest
from runtime.decision_engine import ProductionDecisionEngine, load_calibration_status


def test_uncalibrated_scores_are_advisory_only():
    """未校准评分应该只产生警告，不触发hold"""
    engine = ProductionDecisionEngine()

    # 模拟未校准状态（所有维度都是diagnostic）
    calibration_status = {
        "status": "uncalibrated_insufficient_real_samples",
        "trusted_dimensions": [],
        "decision_dimensions": [],
        "diagnostic_dimensions": ["hook", "retention", "pacing"]
    }

    # 低分（低于阈值75）
    final_quality_scores = {
        "hook": 60,
        "retention": 65,
        "pacing": 68
    }

    action, blocking, warnings = engine.decide(
        final_quality_scores=final_quality_scores,
        calibration_status=calibration_status
    )

    # 不应该hold
    assert action != "hold", "未校准评分不应触发hold"
    assert action != "block", "未校准评分不应触发block"
    assert action == "publish", f"应该是publish，实际是{action}"

    # 应该有advisory警告
    assert len(warnings) > 0, "应该有警告"
    assert any("uncalibrated" in w for w in warnings), \
        f"警告应包含'uncalibrated'标记: {warnings}"
    assert any("advisory only" in w for w in warnings), \
        f"警告应包含'advisory only': {warnings}"


def test_calibrated_scores_can_trigger_hold():
    """校准后的decision级维度可以触发hold"""
    engine = ProductionDecisionEngine()

    # 模拟校准完成，hook是decision级维度
    calibration_status = {
        "status": "calibrated",
        "trusted_dimensions": ["hook"],
        "decision_dimensions": ["hook"],
        "diagnostic_dimensions": ["retention", "pacing"]
    }

    # hook低分，其他正常
    final_quality_scores = {
        "hook": 60,  # 低于阈值75
        "retention": 80,
        "pacing": 78
    }

    action, blocking, warnings = engine.decide(
        final_quality_scores=final_quality_scores,
        calibration_status=calibration_status
    )

    # 应该hold
    assert action == "hold", f"校准后的低分应触发hold，实际是{action}"
    assert len(warnings) > 0
    assert any("hook" in w and "calibrated" in w for w in warnings), \
        f"应该有hook的calibrated警告: {warnings}"


def test_mixed_calibration_status():
    """部分维度校准，部分未校准"""
    engine = ProductionDecisionEngine()

    calibration_status = {
        "status": "partially_calibrated",
        "decision_dimensions": ["hook"],  # 只有hook校准
        "diagnostic_dimensions": ["retention", "pacing"]
    }

    # retention低分（未校准），hook正常（已校准）
    final_quality_scores = {
        "hook": 80,
        "retention": 60,  # 低于阈值75，但未校准
        "pacing": 78
    }

    action, blocking, warnings = engine.decide(
        final_quality_scores=final_quality_scores,
        calibration_status=calibration_status
    )

    # 不应该hold（因为低分的维度未校准）
    assert action == "publish", f"未校准维度低分不应hold，实际是{action}"

    # 应该有advisory警告
    retention_warnings = [w for w in warnings if "retention" in w]
    assert len(retention_warnings) > 0
    assert any("uncalibrated" in w for w in retention_warnings)


def test_no_calibration_status_provided():
    """没有提供校准状态时的向后兼容行为"""
    engine = ProductionDecisionEngine()

    # 不提供calibration_status
    final_quality_scores = {
        "hook": 60,  # 低于阈值
    }

    action, blocking, warnings = engine.decide(
        final_quality_scores=final_quality_scores,
        calibration_status=None
    )

    # 向后兼容：没有校准状态时，应该视为未校准，仅advisory
    assert action != "hold", "没有校准状态时不应hold"
    assert len(warnings) > 0
    assert any("hook" in w for w in warnings)


def test_risk_dimensions_respect_calibration():
    """风险维度（越低越好）也应尊重校准状态"""
    engine = ProductionDecisionEngine()

    calibration_status = {
        "decision_dimensions": [],
        "diagnostic_dimensions": ["reader_drop_risk"]
    }

    # 高风险分数（超过阈值30）
    final_quality_scores = {
        "reader_drop_risk": 40
    }

    action, blocking, warnings = engine.decide(
        final_quality_scores=final_quality_scores,
        calibration_status=calibration_status
    )

    # 未校准的风险维度不应hold
    assert action == "publish", f"未校准风险维度不应hold，实际是{action}"
    assert any("reader_drop_risk" in w and "uncalibrated" in w for w in warnings)


def test_deterministic_gates_still_work():
    """确定性gate（契约、红线）不受校准状态影响"""
    engine = ProductionDecisionEngine()

    calibration_status = {
        "decision_dimensions": []
    }

    # 测试critical_deviations仍然block
    action, blocking, warnings = engine.decide(
        critical_deviations=1,
        calibration_status=calibration_status
    )
    assert action == "block", "critical_deviations应该block"

    # 测试redline失败仍然block
    action, blocking, warnings = engine.decide(
        redline_passed=False,
        calibration_status=calibration_status
    )
    assert action == "block", "redline失败应该block"


def test_load_calibration_status_missing_file(tmp_path):
    """校准文件不存在时的处理"""
    status = load_calibration_status(tmp_path)

    assert status["status"] == "unknown"
    assert status["decision_dimensions"] == []
    assert status["trusted_dimensions"] == []


def test_load_calibration_status_real_format(tmp_path):
    """测试真实的校准摘要格式"""
    import json

    golden_set = tmp_path / "quality-golden-set" / "metadata"
    golden_set.mkdir(parents=True)

    summary = {
        "status": "uncalibrated_insufficient_real_samples",
        "trusted_dimensions": [],
        "dimension_grading": {
            "decision": [],
            "diagnostic": ["hook", "retention"],
            "unreliable": []
        }
    }

    with open(golden_set / "w9-calibration-summary.json", "w") as f:
        json.dump(summary, f)

    status = load_calibration_status(tmp_path)

    assert status["status"] == "uncalibrated_insufficient_real_samples"
    assert status["decision_dimensions"] == []
    assert status["diagnostic_dimensions"] == ["hook", "retention"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
