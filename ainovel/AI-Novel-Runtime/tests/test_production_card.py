"""
测试 Production Card 数据结构
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.production_card import ProductionCard


def test_production_card_basic():
    """测试基本 Production Card 创建"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        contract_deviations=0
    )

    assert card.chapter == 1
    assert card.draft_hash == "abc123"
    assert card.contract_status == "pass"
    assert card.publish_recommendation == "recommend"


def test_production_card_to_dict():
    """测试序列化"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass"
    )

    data = card.to_dict()
    assert isinstance(data, dict)
    assert data["chapter"] == 1
    assert data["draft_hash"] == "abc123"


def test_production_card_from_dict():
    """测试反序列化"""
    data = {
        "chapter": 1,
        "draft_hash": "abc123",
        "draft_timestamp": "2026-08-15T10:00:00Z",
        "contract_status": "pass",
        "contract_deviations": 0,
        "critical_deviations": 0,
        "high_deviations": 0,
        "medium_deviations": 0,
        "minor_deviations": 0,
        "final_quality_scores": {},
        "initial_quality_scores": {},
        "quality_delta": {},
        "reader_simulation": None,
        "dropout_risk": None,
        "continuation_rate": None,
        "prose_checks": {},
        "m7_originality": None,
        "publish_recommendation": "recommend",
        "redline_passed": True,
        "blocking_issues": [],
        "warnings": [],
        "human_decision": "pending",
        "human_decision_by": None,
        "human_decision_at": None,
        "human_decision_notes": None,
        "generated_at": "2026-08-15T10:00:00Z",
        "review_model": None,
        "strict_mode": False
    }

    card = ProductionCard.from_dict(data)
    assert card.chapter == 1
    assert card.contract_status == "pass"


def test_production_card_critical_blocks():
    """测试关键偏差阻断"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="invalid",
        contract_deviations=1,
        critical_deviations=1
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "block"
    assert len(card.blocking_issues) > 0
    assert "Critical" in card.blocking_issues[0]


def test_production_card_redline_blocks():
    """测试红线检查阻断"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        redline_passed=False
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "block"
    assert any("redline" in issue.lower() for issue in card.blocking_issues)


def test_production_card_high_severity_holds():
    """测试高级别偏差产生 hold"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="warning",
        contract_deviations=2,
        high_deviations=2
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "hold"
    assert len(card.warnings) > 0


def test_production_card_quality_degradation_holds():
    """测试质量退化产生 hold"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={"character_consistency": 85},
        final_quality_scores={"character_consistency": 70},
        quality_delta={
            "character_consistency": {
                "initial": 85,
                "final": 70,
                "delta": -15
            }
        }
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "hold"
    assert len(card.warnings) > 0
    # Check for degradation warning (updated to match actual implementation)
    assert any("character_consistency" in warning and "70" in warning for warning in card.warnings)


def test_production_card_strict_mode_low_confidence():
    """测试严格模式下低置信度阻断"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        final_quality_scores={"overall_confidence": 0.5},
        strict_mode=True
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "block"
    assert any("confidence" in issue.lower() for issue in card.blocking_issues)


def test_production_card_all_pass():
    """测试全部通过"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        contract_deviations=0,
        final_quality_scores={
            "character_consistency": 85,
            "world_consistency": 88,
            "pacing": 78
        },
        dropout_risk=0.05,
        redline_passed=True
    )

    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"
    assert len(card.blocking_issues) == 0


def test_production_card_approval():
    """测试人工批准"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass"
    )

    card.approve(by="editor@example.com", notes="Looks good")

    assert card.human_decision == "approved"
    assert card.human_decision_by == "editor@example.com"
    assert card.human_decision_notes == "Looks good"
    assert card.human_decision_at is not None


def test_production_card_rejection():
    """测试人工拒绝"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass"
    )

    card.reject(by="editor@example.com", notes="Needs work")

    assert card.human_decision == "rejected"
    assert card.human_decision_by == "editor@example.com"
    assert card.human_decision_notes == "Needs work"


def test_production_card_summary():
    """测试摘要生成"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123def",
        draft_timestamp="2026-08-15T10:00:00Z",
        contract_status="pass",
        final_quality_scores={
            "character_consistency": 85,
            "world_consistency": 88
        },
        dropout_risk=0.08
    )

    summary = card.summary()
    assert "Chapter 1" in summary
    assert "abc123de" in summary  # 前8位
    assert "pass" in summary
    assert "8.00%" in summary or "0.08" in summary
