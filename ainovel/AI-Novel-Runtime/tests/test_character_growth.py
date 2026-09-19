"""
测试 Character Growth State Machine (P1-4)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.character_growth import (
    CharacterGrowth,
    CharacterState,
    GrowthStage,
    TransitionType,
)


def test_character_growth_initialization():
    """测试初始化"""
    growth = CharacterGrowth(
        character_id="CHAR-001",
        name="主角",
    )

    assert growth.current_stage == GrowthStage.INTRODUCED
    assert growth.appearance_count == 0
    assert len(growth.transitions) == 0


def test_record_appearance():
    """测试记录出场"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_appearance("CH-001")
    growth.record_appearance("CH-002")

    assert growth.appearance_count == 2
    assert growth.last_appearance == "CH-002"


def test_record_transition():
    """测试记录状态转移"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-001",
        transition_type=TransitionType.DESIRE_REVEALED,
        description="揭示了想要变强的欲望",
        state_changes={"desires": ["变强", "保护同伴"]},
        trigger_event="目睹同伴受伤",
        impact_score=0.7,
    )

    assert len(growth.transitions) == 1
    assert len(growth.current_state.desires) == 2
    assert "变强" in growth.current_state.desires


def test_stage_progression_introduced_to_established():
    """测试从introduced到established的转移"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    # 添加欲望和恐惧
    growth.record_transition(
        chapter_id="CH-001",
        transition_type=TransitionType.DESIRE_REVEALED,
        description="揭示欲望",
        state_changes={"desires": ["变强"]},
        trigger_event="事件1",
    )

    growth.record_transition(
        chapter_id="CH-002",
        transition_type=TransitionType.FEAR_CONFRONTED,
        description="揭示恐惧",
        state_changes={"fears": ["失去同伴"]},
        trigger_event="事件2",
    )

    # 应该推进到established
    assert growth.current_stage == GrowthStage.ESTABLISHED
    assert len(growth.stage_history) == 1


def test_stage_progression_established_to_challenged():
    """测试从established到challenged的转移"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")
    growth.current_stage = GrowthStage.ESTABLISHED

    # 信念被挑战
    growth.record_transition(
        chapter_id="CH-003",
        transition_type=TransitionType.BELIEF_CHALLENGED,
        description="发现自己的信念是错误的",
        state_changes={"false_beliefs": ["力量至上"]},
        trigger_event="看到弱者的智慧",
    )

    # 应该推进到challenged
    assert growth.current_stage == GrowthStage.CHALLENGED


def test_stage_progression_challenged_to_transformed():
    """测试从challenged到transformed的转移"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")
    growth.current_stage = GrowthStage.CHALLENGED
    growth.current_state.false_beliefs = ["力量至上", "不能相信他人"]

    # 移除错误信念
    growth.record_transition(
        chapter_id="CH-005",
        transition_type=TransitionType.BELIEF_CHALLENGED,
        description="放弃了错误信念",
        state_changes={"remove_false_beliefs": ["力量至上"]},
        trigger_event="领悟到真正的力量",
    )

    # 应该推进到transformed
    assert growth.current_stage == GrowthStage.TRANSFORMED
    assert "力量至上" not in growth.current_state.false_beliefs


def test_irreversible_choice():
    """测试不可逆选择"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-003",
        transition_type=TransitionType.IRREVERSIBLE_CHOICE,
        description="做出了不可逆的选择",
        state_changes={"irreversible_choices": ["背叛了组织"]},
        trigger_event="为了拯救朋友",
        impact_score=0.9,
    )

    assert len(growth.current_state.irreversible_choices) == 1
    assert "背叛了组织" in growth.current_state.irreversible_choices


def test_price_paid():
    """测试代价付出"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-004",
        transition_type=TransitionType.PRICE_PAID,
        description="付出了巨大代价",
        state_changes={"prices_paid": ["失去了一只眼睛"]},
        trigger_event="保护村民",
        impact_score=0.8,
    )

    assert len(growth.current_state.prices_paid) == 1


def test_relationship_evolution():
    """测试关系演变"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-003",
        transition_type=TransitionType.RELATIONSHIP_EVOLVED,
        description="与对手成为朋友",
        state_changes={"relationships": {"对手": "朋友"}},
        trigger_event="并肩作战",
    )

    assert growth.current_state.relationships["对手"] == "朋友"


def test_ability_unlocked():
    """测试能力解锁"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-005",
        transition_type=TransitionType.ABILITY_UNLOCKED,
        description="解锁了新能力",
        state_changes={"abilities": ["火焰操控"]},
        trigger_event="突破瓶颈",
        impact_score=0.7,
    )

    assert "火焰操控" in growth.current_state.abilities


def test_get_growth_summary():
    """测试获取成长摘要"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_appearance("CH-001")
    growth.record_transition(
        chapter_id="CH-001",
        transition_type=TransitionType.DESIRE_REVEALED,
        description="揭示欲望",
        state_changes={"desires": ["变强"]},
        trigger_event="事件1",
    )

    summary = growth.get_growth_summary()

    assert summary["character_id"] == "CHAR-001"
    assert summary["name"] == "主角"
    assert summary["appearance_count"] == 1
    assert summary["transition_count"] == 1
    assert summary["current_state_summary"]["desires_count"] == 1


def test_serialization():
    """测试序列化和反序列化"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    growth.record_transition(
        chapter_id="CH-001",
        transition_type=TransitionType.DESIRE_REVEALED,
        description="揭示欲望",
        state_changes={"desires": ["变强"]},
        trigger_event="事件1",
    )

    # 序列化
    data = growth.to_dict()

    # 反序列化
    growth2 = CharacterGrowth.from_dict(data)

    assert growth2.character_id == growth.character_id
    assert growth2.name == growth.name
    assert growth2.current_stage == growth.current_stage
    assert len(growth2.transitions) == len(growth.transitions)
    assert growth2.current_state.desires == growth.current_state.desires


def test_complete_growth_cycle():
    """测试完整成长周期"""
    growth = CharacterGrowth(character_id="CHAR-001", name="主角")

    # 1. Introduced -> Established
    growth.record_transition(
        chapter_id="CH-001",
        transition_type=TransitionType.DESIRE_REVEALED,
        description="想要变强",
        state_changes={"desires": ["变强"]},
        trigger_event="目睹强者",
    )

    growth.record_transition(
        chapter_id="CH-002",
        transition_type=TransitionType.FEAR_CONFRONTED,
        description="害怕失败",
        state_changes={"fears": ["失败"]},
        trigger_event="第一次战斗",
    )

    assert growth.current_stage == GrowthStage.ESTABLISHED

    # 2. Established -> Challenged
    growth.record_transition(
        chapter_id="CH-003",
        transition_type=TransitionType.IRREVERSIBLE_CHOICE,
        description="背叛师门",
        state_changes={"irreversible_choices": ["背叛师门"]},
        trigger_event="保护朋友",
        impact_score=0.9,
    )

    assert growth.current_stage == GrowthStage.CHALLENGED

    # 3. Challenged -> Transformed
    growth.current_state.false_beliefs = ["力量至上"]
    growth.record_transition(
        chapter_id="CH-005",
        transition_type=TransitionType.BELIEF_CHALLENGED,
        description="放弃错误信念",
        state_changes={"remove_false_beliefs": ["力量至上"]},
        trigger_event="领悟",
    )

    assert growth.current_stage == GrowthStage.TRANSFORMED

    # 检查阶段历史
    assert len(growth.stage_history) == 3
