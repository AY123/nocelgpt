"""
测试 World Consistency Checker (C3-2)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.world_consistency_checker import (
    WorldConsistencyChecker,
    WorldRule,
    Inconsistency,
    ConsistencyReport,
    InconsistencyType,
    InconsistencySeverity,
)


def create_test_story_state():
    """创建测试用故事状态"""
    return {
        "world_rules": [
            {
                "id": "RULE-001",
                "type": "power_system",
                "description": "修炼境界：炼气 < 筑基 < 金丹 < 元婴",
                "constraints": [
                    "低境界不能战胜高境界（除非特殊情况）",
                    "境界突破需要时间积累"
                ],
                "chapter": 1
            },
            {
                "id": "RULE-002",
                "type": "magic",
                "description": "魔法需要咒语才能施放",
                "constraints": ["必须念咒", "无咒语无法施法"],
                "chapter": 5
            }
        ]
    }


def test_checker_initialization():
    """测试检查器初始化"""
    checker = WorldConsistencyChecker()

    assert len(checker.rules) == 0
    assert len(checker.established_facts) == 0


def test_update_rules():
    """测试规则更新"""
    checker = WorldConsistencyChecker()
    story_state = create_test_story_state()

    checker._update_rules(story_state)

    assert len(checker.rules) == 2
    assert "RULE-001" in checker.rules
    assert checker.rules["RULE-001"].rule_type == "power_system"


def test_basic_consistency_check():
    """测试基础一致性检查"""
    checker = WorldConsistencyChecker()
    story_state = create_test_story_state()

    chapter_content = "主角在修炼中突破了境界。"

    report = checker.check_consistency(
        current_chapter=10,
        chapter_content=chapter_content,
        story_state=story_state
    )

    assert report.current_chapter == 10
    assert report.total_rules == 2


def test_power_system_detection():
    """测试实力体系内容检测"""
    checker = WorldConsistencyChecker()
    story_state = create_test_story_state()

    # 包含实力相关内容
    chapter_content = "主角从筑基突破到金丹境界，实力大增。"

    report = checker.check_consistency(
        current_chapter=20,
        chapter_content=chapter_content,
        story_state=story_state
    )

    # 应该检测到实力相关内容，但不应报矛盾（因为符合规则）
    assert report.consistency_score > 0.8


def test_no_power_rule_warning():
    """测试缺少实力体系定义的警告"""
    checker = WorldConsistencyChecker()

    # 空规则
    story_state = {"world_rules": []}

    # 但有实力相关内容
    chapter_content = "主角突破到新境界，实力达到金丹期。"

    report = checker.check_consistency(
        current_chapter=30,
        chapter_content=chapter_content,
        story_state=story_state
    )

    # 应该有警告（缺少实力体系定义）
    assert report.total_inconsistencies > 0
    assert len(report.medium_inconsistencies) > 0


def test_consistency_score_calculation():
    """测试一致性得分计算"""
    checker = WorldConsistencyChecker()

    # 无矛盾
    inconsistencies_none = []
    score_perfect = checker._calculate_consistency_score(inconsistencies_none)
    assert score_perfect == 1.0

    # 一个MEDIUM矛盾
    inconsistencies_medium = [
        Inconsistency(
            inconsistency_id="INC-1",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.MEDIUM,
            description="测试",
        )
    ]
    score_medium = checker._calculate_consistency_score(inconsistencies_medium)
    assert 0.9 < score_medium < 1.0

    # 一个CRITICAL矛盾
    inconsistencies_critical = [
        Inconsistency(
            inconsistency_id="INC-2",
            inconsistency_type=InconsistencyType.RULE_VIOLATION,
            severity=InconsistencySeverity.CRITICAL,
            description="测试",
        )
    ]
    score_critical = checker._calculate_consistency_score(inconsistencies_critical)
    assert score_critical == 0.8


def test_categorize_by_severity():
    """测试按严重程度分类"""
    checker = WorldConsistencyChecker()

    inconsistencies = [
        Inconsistency(
            inconsistency_id="INC-1",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.CRITICAL,
            description="严重矛盾",
        ),
        Inconsistency(
            inconsistency_id="INC-2",
            inconsistency_type=InconsistencyType.TIMELINE,
            severity=InconsistencySeverity.HIGH,
            description="高度矛盾",
        ),
        Inconsistency(
            inconsistency_id="INC-3",
            inconsistency_type=InconsistencyType.GEOGRAPHY,
            severity=InconsistencySeverity.MEDIUM,
            description="中度矛盾",
        ),
    ]

    categorized = checker._categorize_by_severity(inconsistencies)

    assert len(categorized[InconsistencySeverity.CRITICAL]) == 1
    assert len(categorized[InconsistencySeverity.HIGH]) == 1
    assert len(categorized[InconsistencySeverity.MEDIUM]) == 1
    assert len(categorized[InconsistencySeverity.LOW]) == 0


def test_categorize_by_type():
    """测试按类型分类"""
    checker = WorldConsistencyChecker()

    inconsistencies = [
        Inconsistency(
            inconsistency_id="INC-1",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.HIGH,
            description="实力矛盾1",
        ),
        Inconsistency(
            inconsistency_id="INC-2",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.MEDIUM,
            description="实力矛盾2",
        ),
        Inconsistency(
            inconsistency_id="INC-3",
            inconsistency_type=InconsistencyType.TIMELINE,
            severity=InconsistencySeverity.HIGH,
            description="时间矛盾",
        ),
    ]

    by_type = checker._categorize_by_type(inconsistencies)

    assert len(by_type["power_level"]) == 2
    assert len(by_type["timeline"]) == 1


def test_generate_recommendations():
    """测试建议生成"""
    checker = WorldConsistencyChecker()

    inconsistencies = [
        Inconsistency(
            inconsistency_id="INC-1",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.CRITICAL,
            description="严重矛盾",
        ),
        Inconsistency(
            inconsistency_id="INC-2",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.HIGH,
            description="高度矛盾",
        ),
    ]

    recommendations = checker._generate_recommendations(inconsistencies)

    # 应该有严重矛盾的建议
    assert any("严重" in rec for rec in recommendations)
    assert any("1个严重" in rec for rec in recommendations)


def test_summary_generation():
    """测试摘要生成"""
    checker = WorldConsistencyChecker()
    story_state = create_test_story_state()

    chapter_content = "主角修炼突破。"

    report = checker.check_consistency(
        current_chapter=40,
        chapter_content=chapter_content,
        story_state=story_state
    )

    summary = checker.generate_summary(report)

    # 检查关键信息
    assert "第40章" in summary
    assert "已定义规则" in summary
    assert "一致性得分" in summary


def test_multiple_inconsistencies():
    """测试多个矛盾"""
    checker = WorldConsistencyChecker()

    inconsistencies = [
        Inconsistency(
            inconsistency_id=f"INC-{i}",
            inconsistency_type=InconsistencyType.POWER_LEVEL,
            severity=InconsistencySeverity.MEDIUM,
            description=f"矛盾{i}",
        )
        for i in range(5)
    ]

    score = checker._calculate_consistency_score(inconsistencies)

    # 5个MEDIUM矛盾：5 * 0.05 = 0.25扣分
    assert abs(score - 0.75) < 0.01


def test_extract_facts_power():
    """测试提取实力相关事实"""
    checker = WorldConsistencyChecker()

    content_with_power = "主角突破境界，修为大增，实力达到金丹期。"
    facts = checker._extract_facts(content_with_power)

    assert facts["has_power_content"] is True


def test_extract_facts_time():
    """测试提取时间相关事实"""
    checker = WorldConsistencyChecker()

    content_with_time = "三年前发生的事情，主角至今难忘。"
    facts = checker._extract_facts(content_with_time)

    assert facts["has_time_reference"] is True


def test_extract_facts_geography():
    """测试提取地理相关事实"""
    checker = WorldConsistencyChecker()

    content_with_geography = "主角到达了目的地，距离出发点有百里之遥。"
    facts = checker._extract_facts(content_with_geography)

    assert facts["has_geography"] is True
