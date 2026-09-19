"""
测试 Constitution-Aware Paywall Optimizer (C1)
"""
import pytest
import sys
from pathlib import Path
import tempfile

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.constitution_aware_paywall import (
    SellingPointDetector,
    ConstitutionAwarePaywallOptimizer,
    DeliveredSellingPoint,
    ConstitutionPaywallRecommendation,
)
from runtime.commercial_constitution import (
    CommercialConstitution,
    Platform,
    Genre,
    AgeGroup,
    Gender,
    PaymentWillingness,
    AudienceProfile,
    SellingPoint,
    ConstitutionConstraints,
)


def create_test_constitution():
    """创建测试用Constitution"""
    audience = AudienceProfile(
        age_group=AgeGroup.YOUNG_ADULT,
        gender=Gender.MALE,
        payment_willingness=PaymentWillingness.HIGH,
        reading_speed="fast",
        content_preference=["爽文", "升级"],
        pain_points=["无聊"],
        fulfillment_needs=["成就感"],
    )

    sp1 = SellingPoint(
        name="修炼升级",
        description="主角修炼突破",
        type="power",
        delivery_mechanism="每3章一次",
        frequency="every_3_chapters",
        validation_keywords=["突破", "境界", "修炼"],
        minimum_intensity=0.6,
    )

    sp2 = SellingPoint(
        name="战斗爽感",
        description="精彩战斗",
        type="emotional",
        delivery_mechanism="每章",
        frequency="every_chapter",
        validation_keywords=["战斗", "对决", "胜利"],
        minimum_intensity=0.5,
    )

    constraints = ConstitutionConstraints(
        forbidden_elements=[],
        required_elements=[],
        min_hook_score=75,
        max_chapters_without_payoff=3,
        target_chapter_length=3000,
        paywall_earliest_chapter=30,
        genre_drift_tolerance=0.3,
    )

    return CommercialConstitution(
        constitution_id="TEST-001",
        work_title="测试小说",
        target_platform=Platform.QIDIAN,
        primary_genre=Genre.XUANHUAN,
        primary_audience=audience,
        core_selling_points=[sp1, sp2],
        constraints=constraints,
    )


def test_selling_point_detector_basic():
    """测试卖点检测器基础功能"""
    constitution = create_test_constitution()
    detector = SellingPointDetector(constitution)

    chapter_content = "他经过艰苦修炼，终于突破了境界，实力大增。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "hook": 80
        }
    }

    delivered = detector.detect_delivered_selling_points(
        chapter_number=5,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata
    )

    assert len(delivered) > 0
    assert any(sp.selling_point_name == "修炼升级" for sp in delivered)


def test_selling_point_detector_no_delivery():
    """测试未兑现卖点的情况"""
    constitution = create_test_constitution()
    detector = SellingPointDetector(constitution)

    chapter_content = "他在路上走着，看到了风景。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 50,
            "hook": 60
        }
    }

    delivered = detector.detect_delivered_selling_points(
        chapter_number=5,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata
    )

    assert len(delivered) == 0


def test_selling_point_detector_multiple():
    """测试检测多个卖点"""
    constitution = create_test_constitution()
    detector = SellingPointDetector(constitution)

    chapter_content = "他修炼突破境界后，立即与敌人展开战斗，最终取得胜利。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "emotion": 80,
            "hook": 85
        }
    }

    delivered = detector.detect_delivered_selling_points(
        chapter_number=10,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata
    )

    assert len(delivered) == 2
    names = [sp.selling_point_name for sp in delivered]
    assert "修炼升级" in names
    assert "战斗爽感" in names


def test_optimizer_basic_recommendation():
    """测试基础付费点推荐"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他修炼突破境界，实力大增。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "hook": 85,
            "retention": 80,
            "reward_density": 85,
            "payoff": 80
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=35,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert isinstance(recommendation, ConstitutionPaywallRecommendation)
    assert recommendation.chapter_number == 35


def test_optimizer_early_chapter_rejection():
    """测试过早章节被拒绝"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他修炼突破境界，实力大增。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 90,
            "hook": 90,
            "retention": 85,
            "reward_density": 85,
            "payoff": 85
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=20,  # 早于30章
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert not recommendation.should_place_paywall
    assert not recommendation.earliest_chapter_met
    assert "早于最早付费章节" in recommendation.warnings[0]


def test_optimizer_low_hook_rejection():
    """测试低钩子分数被拒绝"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他修炼突破境界。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "hook": 60,  # 低于75
            "retention": 80
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=35,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert not recommendation.should_place_paywall
    assert "钩子分数" in recommendation.warnings[0]


def test_optimizer_paywall_interval():
    """测试付费点间隔检查"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他修炼突破境界，实力大增。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "hook": 85,
            "retention": 80
        }
    }

    # 上一个付费点在第30章，现在是第50章（间隔20章，<50）
    recommendation = optimizer.recommend_paywall(
        chapter_number=50,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[30]
    )

    assert not recommendation.should_place_paywall
    assert "距离上一个付费点过近" in recommendation.warnings[0]


def test_optimizer_selling_point_score():
    """测试卖点得分计算"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他修炼突破境界后，与敌人战斗并取得胜利。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 85,
            "emotion": 80,
            "hook": 85,
            "retention": 80,
            "reward_density": 85,
            "payoff": 80
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=35,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert recommendation.selling_point_score > 0.5
    assert len(recommendation.delivered_selling_points) > 0


def test_optimizer_confidence_high():
    """测试高置信度推荐"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    # 优质章节：多个卖点兑现 + 高质量分数
    chapter_content = "他经过长时间修炼终于突破境界，随后与强敌展开激烈战斗，最终取得胜利。"
    chapter_metadata = {
        "qa_scores": {
            "character_growth": 90,
            "emotion": 88,
            "hook": 90,
            "retention": 88,
            "reward_density": 90,
            "payoff": 88
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=35,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert recommendation.should_place_paywall
    assert recommendation.confidence >= 0.7
    assert len(recommendation.supporting_reasons) > 0


def test_optimizer_no_selling_point():
    """测试无卖点兑现时不推荐"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    chapter_content = "他在路上走着，看到了美丽的风景。"
    chapter_metadata = {
        "qa_scores": {
            "hook": 85,
            "retention": 80
        }
    }

    recommendation = optimizer.recommend_paywall(
        chapter_number=35,
        chapter_content=chapter_content,
        chapter_metadata=chapter_metadata,
        paywall_history=[]
    )

    assert not recommendation.should_place_paywall
    assert len(recommendation.delivered_selling_points) == 0
    assert "未检测到核心卖点兑现" in recommendation.primary_reason


def test_optimizer_timing_score_first_paywall():
    """测试第一个付费点的时机得分"""
    constitution = create_test_constitution()
    optimizer = ConstitutionAwarePaywallOptimizer(constitution)

    # 在合理范围内（30-50章）
    chapter_content = "他修炼突破境界。"
    chapter_metadata = {"qa_scores": {"character_growth": 85, "hook": 85}}

    rec1 = optimizer.recommend_paywall(35, chapter_content, chapter_metadata, [])
    assert rec1.timing_score == 1.0  # 最佳时机

    rec2 = optimizer.recommend_paywall(25, chapter_content, chapter_metadata, [])
    # 虽然会因为早于30章被拒绝，但如果能推荐，timing_score会较低
