"""
测试 Constitution Integration (P2-1阶段2)
"""
import pytest
import sys
from pathlib import Path
import tempfile

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.commercial_constitution import (
    CommercialConstitution,
    Platform,
    Genre,
    AgeGroup,
    Gender,
    PaymentWillingness,
    AudienceProfile,
    ConstitutionConstraints,
)
from runtime.constitution_integration import (
    ConstitutionIntegration,
    integrate_constitution_check,
)


def test_integration_without_constitution():
    """测试没有Constitution的情况"""
    integration = ConstitutionIntegration()

    chapter_content = "测试内容"
    chapter_metadata = {"qa_scores": {"hook": 80}}

    result = integration.validate_chapter(chapter_content, chapter_metadata)

    assert result is None


def test_integration_with_constitution():
    """测试有Constitution的情况"""
    # 创建临时Constitution
    audience = AudienceProfile(
        age_group=AgeGroup.YOUNG_ADULT,
        gender=Gender.MALE,
        payment_willingness=PaymentWillingness.HIGH,
        reading_speed="fast",
        content_preference=["爽文"],
        pain_points=["无聊"],
        fulfillment_needs=["成就感"],
    )

    constraints = ConstitutionConstraints(
        forbidden_elements=["政治"],
        required_elements=[],
        min_hook_score=75,
        max_chapters_without_payoff=3,
        target_chapter_length=3000,
        paywall_earliest_chapter=30,
        genre_drift_tolerance=0.3,
    )

    constitution = CommercialConstitution(
        constitution_id="TEST-001",
        work_title="测试",
        target_platform=Platform.QIDIAN,
        primary_genre=Genre.XUANHUAN,
        primary_audience=audience,
        constraints=constraints,
    )

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    constitution.save_to_file(filepath)

    # 创建integration
    integration = ConstitutionIntegration(filepath)

    # 验证章节
    chapter_content = "他运转灵力，修炼功法，终于突破了境界。"
    chapter_metadata = {"qa_scores": {"hook": 80}}

    result = integration.validate_chapter(chapter_content, chapter_metadata)

    assert result is not None
    assert "is_compliant" in result
    assert "overall_score" in result
    assert "violations" in result

    # 清理
    Path(filepath).unlink()


def test_integration_decision_impact_critical():
    """测试critical违规对决策的影响"""
    compliance_dict = {
        "is_compliant": False,
        "overall_score": 0.4,
        "violations": [
            {
                "type": "constraint_violation",
                "severity": "critical",
                "description": "包含禁止元素",
                "evidence": "政治敏感",
                "suggestion": "移除"
            }
        ]
    }

    integration = ConstitutionIntegration()
    action, reason = integration.get_decision_impact(compliance_dict)

    assert action == "block"
    assert "Critical constitution violations" in reason


def test_integration_decision_impact_high():
    """测试high违规对决策的影响"""
    compliance_dict = {
        "is_compliant": False,
        "overall_score": 0.55,
        "violations": [
            {
                "type": "genre_drift",
                "severity": "high",
                "description": "题材偏离",
                "evidence": "对齐度50%",
                "suggestion": "调整"
            }
        ]
    }

    integration = ConstitutionIntegration()
    action, reason = integration.get_decision_impact(compliance_dict)

    assert action == "hold"
    assert "High severity" in reason


def test_integration_decision_impact_none():
    """测试合规时没有影响"""
    compliance_dict = {
        "is_compliant": True,
        "overall_score": 0.85,
        "violations": []
    }

    integration = ConstitutionIntegration()
    action, reason = integration.get_decision_impact(compliance_dict)

    assert action is None
    assert reason is None


def test_integration_summary_message():
    """测试摘要生成"""
    compliance_dict = {
        "is_compliant": False,
        "overall_score": 0.65,
        "genre_alignment": 0.7,
        "selling_point_hit": 0.6,
        "audience_match": 0.8,
        "constraint_pass": False,
        "violations": [
            {
                "type": "constraint_violation",
                "severity": "high",
                "description": "钩子分数过低",
                "evidence": "60分",
                "suggestion": "增强钩子"
            }
        ]
    }

    integration = ConstitutionIntegration()
    summary = integration.generate_summary_message(compliance_dict)

    assert "Constitution Compliance" in summary
    assert "Overall Score" in summary
    assert "Genre" in summary
    assert "Violations" in summary


def test_integrate_constitution_check_helper():
    """测试便捷函数"""
    # 创建临时Constitution
    audience = AudienceProfile(
        age_group=AgeGroup.YOUNG_ADULT,
        gender=Gender.MALE,
        payment_willingness=PaymentWillingness.HIGH,
        reading_speed="fast",
        content_preference=["爽文"],
        pain_points=["无聊"],
        fulfillment_needs=["成就感"],
    )

    constitution = CommercialConstitution(
        constitution_id="TEST-001",
        work_title="测试",
        target_platform=Platform.QIDIAN,
        primary_genre=Genre.XUANHUAN,
        primary_audience=audience,
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    constitution.save_to_file(filepath)

    # 使用便捷函数
    chapter_content = "他运转灵力。"
    chapter_metadata = {"qa_scores": {"hook": 80}}

    result = integrate_constitution_check(chapter_content, chapter_metadata, filepath)

    assert result is not None
    assert "is_compliant" in result

    # 清理
    Path(filepath).unlink()


def test_integrate_constitution_check_no_path():
    """测试便捷函数没有路径的情况"""
    chapter_content = "测试"
    chapter_metadata = {"qa_scores": {"hook": 80}}

    result = integrate_constitution_check(chapter_content, chapter_metadata, None)

    assert result is None
