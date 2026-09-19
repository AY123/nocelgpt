"""
测试 Production Card 绝对质量阈值 (P0-2)

P0-2 fix: 这些测试需要模拟校准状态，因为未校准评分不能触发hold。
"""
import pytest
import sys
from pathlib import Path
import tempfile
import json

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.production_card import ProductionCard, QUALITY_THRESHOLDS, RISK_THRESHOLDS


def create_mock_calibrated_project(tmp_path, decision_dimensions):
    """创建一个带有校准状态的模拟项目目录"""
    golden_set = tmp_path / "quality-golden-set" / "metadata"
    golden_set.mkdir(parents=True)

    summary = {
        "status": "calibrated",
        "trusted_dimensions": decision_dimensions,
        "dimension_grading": {
            "decision": decision_dimensions,
            "diagnostic": [],
            "unreliable": []
        }
    }

    with open(golden_set / "w9-calibration-summary.json", "w") as f:
        json.dump(summary, f)

    return str(tmp_path)


def test_absolute_quality_threshold_hook_low():
    """测试 hook 分数低于阈值触发 hold（需要校准）"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = create_mock_calibrated_project(Path(tmp_dir), ["hook"])

        card = ProductionCard(
            chapter=1,
            draft_hash="abc123",
            draft_timestamp="2026-08-18T10:00:00Z",
            contract_status="pass",
            final_quality_scores={
                "hook": 70,  # Below threshold (75)
                "retention": 80,
                "character_consistency": 85,
            }
        )

        recommendation = card.compute_recommendation(project_path)
        assert recommendation == "hold"
        assert any("hook" in w and "below threshold" in w for w in card.warnings)


def test_absolute_quality_threshold_retention_low():
    """测试 retention 分数低于阈值触发 hold（需要校准）"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = create_mock_calibrated_project(Path(tmp_dir), ["retention"])

        card = ProductionCard(
            chapter=1,
            draft_hash="abc123",
            draft_timestamp="2026-08-18T10:00:00Z",
            contract_status="pass",
            final_quality_scores={
                "hook": 80,
                "retention": 70,  # Below threshold (75)
                "character_consistency": 85,
            }
        )

        recommendation = card.compute_recommendation(project_path)
        assert recommendation == "hold"
        assert any("retention" in w and "below threshold" in w for w in card.warnings)


def test_absolute_quality_threshold_character_consistency_low():
    """测试 character_consistency 分数低于阈值触发 hold（需要校准）"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = create_mock_calibrated_project(Path(tmp_dir), ["character_consistency"])

        card = ProductionCard(
            chapter=1,
            draft_hash="abc123",
            draft_timestamp="2026-08-18T10:00:00Z",
            contract_status="pass",
            final_quality_scores={
                "hook": 80,
                "retention": 80,
                "character_consistency": 75,  # Below threshold (80)
            }
        )

        recommendation = card.compute_recommendation(project_path)
        assert recommendation == "hold"
        assert any("character_consistency" in w and "below threshold" in w for w in card.warnings)


def test_risk_threshold_reader_drop_risk_high():
    """测试 reader_drop_risk 高于阈值触发 hold（需要校准）"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = create_mock_calibrated_project(Path(tmp_dir), ["reader_drop_risk"])

        card = ProductionCard(
            chapter=1,
            draft_hash="abc123",
            draft_timestamp="2026-08-18T10:00:00Z",
            contract_status="pass",
            final_quality_scores={
                "hook": 80,
                "retention": 80,
                "character_consistency": 85,
                "reader_drop_risk": 35,  # Above threshold (30)
            }
        )

        recommendation = card.compute_recommendation(project_path)
        assert recommendation == "hold"
        assert any("reader_drop_risk" in w and "above threshold" in w for w in card.warnings)


def test_absolute_quality_all_pass():
    """测试所有分数都达标时返回 recommend"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        final_quality_scores={
            "hook": 80,
            "retention": 80,
            "reward_density": 75,
            "payoff": 75,
            "character_consistency": 85,
            "world_consistency": 85,
            "curiosity": 80,
            "pacing": 75,
            "reader_drop_risk": 20,
            "originality_risk": 30,
            "safety_risk": 10,
        }
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"
    assert len(card.warnings) == 0


def test_absolute_quality_threshold_at_boundary():
    """测试分数刚好等于阈值时通过"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        final_quality_scores={
            "hook": 75,  # Exactly at threshold
            "retention": 75,  # Exactly at threshold
            "character_consistency": 80,  # Exactly at threshold
        }
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"
    assert len(card.warnings) == 0


def test_absolute_quality_missing_dimension_ignored():
    """测试缺失的维度不影响判断"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        final_quality_scores={
            "hook": 80,
            "retention": 80,
            # Missing other dimensions - should not fail
        }
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"


def test_critical_deviation_overrides_quality_threshold():
    """测试关键偏差优先级高于质量阈值（返回 block 而非 hold）"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="invalid",
        critical_deviations=1,
        final_quality_scores={
            "hook": 60,  # Below threshold
        }
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "block"  # Not "hold"
    assert any("Critical" in issue for issue in card.blocking_issues)
