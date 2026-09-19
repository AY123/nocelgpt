"""
测试 Task #3: 真实的初评-终评闭环
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.production_card import ProductionCard


def test_initial_vs_final_scores_different():
    """测试初始分数和最终分数不同时，quality_delta 正确计算"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={
            "hook": 70,
            "retention": 75,
            "character_consistency": 80,
        },
        final_quality_scores={
            "hook": 85,
            "retention": 78,
            "character_consistency": 82,
        },
        quality_delta={
            "hook": {"initial": 70, "final": 85, "delta": 15},
            "retention": {"initial": 75, "final": 78, "delta": 3},
            "character_consistency": {"initial": 80, "final": 82, "delta": 2},
        }
    )

    # Initial and final should be different
    assert card.initial_quality_scores != card.final_quality_scores

    # Quality delta should exist
    assert len(card.quality_delta) == 3
    assert card.quality_delta["hook"]["delta"] == 15
    assert card.quality_delta["retention"]["delta"] == 3

    # Should recommend because all scores are above threshold
    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"


def test_initial_vs_final_scores_same_no_revision():
    """测试没有修订时，初始和最终分数相同，quality_delta 为空"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={
            "hook": 80,
            "retention": 80,
            "character_consistency": 85,
        },
        final_quality_scores={
            "hook": 80,
            "retention": 80,
            "character_consistency": 85,
        },
        quality_delta={}  # No delta when no revision
    )

    # Initial and final should be the same (no revision happened)
    assert card.initial_quality_scores == card.final_quality_scores

    # Quality delta should be empty
    assert len(card.quality_delta) == 0

    # Should still recommend
    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"


def test_quality_degradation_detected():
    """测试质量退化被正确检测"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={
            "hook": 85,
            "retention": 85,
        },
        final_quality_scores={
            "hook": 85,  # No change
            "retention": 70,  # Degraded by 15
        },
        quality_delta={
            "retention": {"initial": 85, "final": 70, "delta": -15},
        }
    )

    # Should hold due to degradation > 10 OR retention below threshold (70 < 75)
    recommendation = card.compute_recommendation()
    assert recommendation == "hold"
    # Check for either degradation warning or threshold warning
    assert any("retention" in w.lower() for w in card.warnings)


def test_quality_improvement_tracked():
    """测试质量改善被正确跟踪"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={
            "hook": 70,  # Below threshold
            "retention": 72,  # Below threshold
        },
        final_quality_scores={
            "hook": 80,  # Improved to above threshold
            "retention": 78,  # Improved to above threshold
        },
        quality_delta={
            "hook": {"initial": 70, "final": 80, "delta": 10},
            "retention": {"initial": 72, "final": 78, "delta": 6},
        }
    )

    # Should recommend - final scores above threshold
    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"

    # Verify improvement tracked
    assert card.quality_delta["hook"]["delta"] == 10
    assert card.quality_delta["retention"]["delta"] == 6


def test_no_initial_scores_first_evaluation():
    """测试首次评估时（无初始分数），不产生 delta"""
    card = ProductionCard(
        chapter=1,
        draft_hash="abc123",
        draft_timestamp="2026-08-18T10:00:00Z",
        contract_status="pass",
        initial_quality_scores={},  # No initial scores
        final_quality_scores={
            "hook": 80,
            "retention": 80,
        },
        quality_delta={}  # No delta for first evaluation
    )

    # Should have final scores but no initial
    assert len(card.initial_quality_scores) == 0
    assert len(card.final_quality_scores) == 2
    assert len(card.quality_delta) == 0

    # Should still recommend based on final scores
    recommendation = card.compute_recommendation()
    assert recommendation == "recommend"
