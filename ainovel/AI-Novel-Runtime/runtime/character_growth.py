"""
Character Growth State Machine - 升级人物成长模型 (P1-4)

从"出场次数"升级为状态机跟踪，只有状态转移才推进成长阶段。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class GrowthStage(Enum):
    """成长阶段"""
    INTRODUCED = "introduced"          # 初次登场（建立存在感）
    ESTABLISHED = "established"        # 人设确立（性格特点明确）
    CHALLENGED = "challenged"          # 面临挑战（核心冲突出现）
    TRANSFORMED = "transformed"        # 完成转变（质的改变）
    EVOLVED = "evolved"                # 持续进化（新层次）


class TransitionType(Enum):
    """转移类型"""
    DESIRE_REVEALED = "desire_revealed"              # 欲望揭示
    BELIEF_CHALLENGED = "belief_challenged"          # 信念挑战
    FEAR_CONFRONTED = "fear_confronted"             # 恐惧面对
    VALUE_SHIFTED = "value_shifted"                 # 价值观转变
    STRATEGY_CHANGED = "strategy_changed"           # 策略改变
    RELATIONSHIP_EVOLVED = "relationship_evolved"   # 关系演变
    ABILITY_UNLOCKED = "ability_unlocked"          # 能力解锁
    PRICE_PAID = "price_paid"                      # 代价付出
    IRREVERSIBLE_CHOICE = "irreversible_choice"    # 不可逆选择


@dataclass
class CharacterState:
    """人物状态"""
    # 核心驱动
    desires: List[str] = field(default_factory=list)          # 欲望（想要什么）
    false_beliefs: List[str] = field(default_factory=list)    # 错误信念（误解）
    fears: List[str] = field(default_factory=list)            # 恐惧（害怕什么）
    values: List[str] = field(default_factory=list)           # 价值观（在乎什么）

    # 行为模式
    strategies: List[str] = field(default_factory=list)       # 行动策略（如何做）

    # 外部维度
    relationships: Dict[str, str] = field(default_factory=dict)  # 关系（与谁：状态）
    abilities: List[str] = field(default_factory=list)        # 能力（能做什么）

    # 成长印记
    prices_paid: List[str] = field(default_factory=list)      # 已付代价
    irreversible_choices: List[str] = field(default_factory=list)  # 不可逆选择


@dataclass
class StateTransition:
    """状态转移记录"""
    chapter_id: str                    # 发生在哪章
    transition_type: TransitionType    # 转移类型
    description: str                   # 转移描述

    # 状态变化
    before: Dict[str, Any]            # 转移前状态
    after: Dict[str, Any]             # 转移后状态

    # 上下文
    trigger_event: str                # 触发事件
    impact_score: float = 0.0         # 影响程度(0-1)


@dataclass
class CharacterGrowth:
    """
    人物成长追踪器（状态机版本）

    核心理念：
    - 不再简单计数出场次数
    - 追踪内在状态（欲望/信念/恐惧/价值）
    - 追踪行为模式（策略/关系/能力）
    - 只有状态转移才推进成长阶段
    """
    character_id: str
    name: str

    # 当前状态
    current_stage: GrowthStage = GrowthStage.INTRODUCED
    current_state: CharacterState = field(default_factory=CharacterState)

    # 历史记录
    transitions: List[StateTransition] = field(default_factory=list)
    stage_history: List[Dict[str, Any]] = field(default_factory=list)

    # 统计（辅助）
    appearance_count: int = 0          # 出场次数（仅供参考）
    last_appearance: Optional[str] = None  # 最后出场章节

    def record_appearance(self, chapter_id: str):
        """记录出场（不改变状态）"""
        self.appearance_count += 1
        self.last_appearance = chapter_id

    def record_transition(
        self,
        chapter_id: str,
        transition_type: TransitionType,
        description: str,
        state_changes: Dict[str, Any],
        trigger_event: str,
        impact_score: float = 0.5
    ):
        """
        记录状态转移

        Args:
            chapter_id: 章节ID
            transition_type: 转移类型
            description: 转移描述
            state_changes: 状态变化 {"desires": ["新增的欲望"], ...}
            trigger_event: 触发事件
            impact_score: 影响程度(0-1)
        """
        # 保存转移前状态
        before = self._capture_state()

        # 应用状态变化
        self._apply_state_changes(state_changes)

        # 保存转移后状态
        after = self._capture_state()

        # 记录转移
        transition = StateTransition(
            chapter_id=chapter_id,
            transition_type=transition_type,
            description=description,
            before=before,
            after=after,
            trigger_event=trigger_event,
            impact_score=impact_score,
        )
        self.transitions.append(transition)

        # 检查是否需要推进成长阶段
        self._evaluate_stage_progression()

    def _capture_state(self) -> Dict[str, Any]:
        """捕获当前状态快照"""
        return {
            "desires": self.current_state.desires.copy(),
            "false_beliefs": self.current_state.false_beliefs.copy(),
            "fears": self.current_state.fears.copy(),
            "values": self.current_state.values.copy(),
            "strategies": self.current_state.strategies.copy(),
            "relationships": self.current_state.relationships.copy(),
            "abilities": self.current_state.abilities.copy(),
            "prices_paid": self.current_state.prices_paid.copy(),
            "irreversible_choices": self.current_state.irreversible_choices.copy(),
        }

    def _apply_state_changes(self, changes: Dict[str, Any]):
        """应用状态变化"""
        for key, value in changes.items():
            if key == "desires":
                self.current_state.desires.extend(value)
            elif key == "false_beliefs":
                self.current_state.false_beliefs.extend(value)
            elif key == "fears":
                self.current_state.fears.extend(value)
            elif key == "values":
                self.current_state.values.extend(value)
            elif key == "strategies":
                self.current_state.strategies.extend(value)
            elif key == "relationships":
                self.current_state.relationships.update(value)
            elif key == "abilities":
                self.current_state.abilities.extend(value)
            elif key == "prices_paid":
                self.current_state.prices_paid.extend(value)
            elif key == "irreversible_choices":
                self.current_state.irreversible_choices.extend(value)
            elif key == "remove_false_beliefs":
                # 移除错误信念（成长的标志）
                for belief in value:
                    if belief in self.current_state.false_beliefs:
                        self.current_state.false_beliefs.remove(belief)

    def _evaluate_stage_progression(self):
        """评估是否应该推进成长阶段"""
        current_stage = self.current_stage

        # 根据状态转移历史判断
        if current_stage == GrowthStage.INTRODUCED:
            # 条件：有明确的欲望+恐惧，或有至少2次转移
            if (self.current_state.desires and self.current_state.fears) or len(self.transitions) >= 2:
                self._advance_to_stage(GrowthStage.ESTABLISHED)

        elif current_stage == GrowthStage.ESTABLISHED:
            # 条件：有错误信念被挑战，或有不可逆选择
            has_belief_challenged = any(
                t.transition_type == TransitionType.BELIEF_CHALLENGED
                for t in self.transitions
            )
            has_irreversible = bool(self.current_state.irreversible_choices)

            if has_belief_challenged or has_irreversible:
                self._advance_to_stage(GrowthStage.CHALLENGED)

        elif current_stage == GrowthStage.CHALLENGED:
            # 条件：有错误信念被移除，或付出重大代价
            has_belief_removed = any(
                t.transition_type == TransitionType.BELIEF_CHALLENGED and
                len(t.after.get("false_beliefs", [])) < len(t.before.get("false_beliefs", []))
                for t in self.transitions
            )
            has_major_price = any(
                t.transition_type == TransitionType.PRICE_PAID and t.impact_score >= 0.7
                for t in self.transitions
            )

            if has_belief_removed or has_major_price:
                self._advance_to_stage(GrowthStage.TRANSFORMED)

        elif current_stage == GrowthStage.TRANSFORMED:
            # 条件：有新的价值观建立，或能力质变
            has_value_shift = any(
                t.transition_type == TransitionType.VALUE_SHIFTED
                for t in self.transitions[-5:]  # 检查最近5次转移
            )
            has_ability_unlock = any(
                t.transition_type == TransitionType.ABILITY_UNLOCKED
                for t in self.transitions[-5:]
            )

            if has_value_shift or has_ability_unlock:
                self._advance_to_stage(GrowthStage.EVOLVED)

    def _advance_to_stage(self, new_stage: GrowthStage):
        """推进到新阶段"""
        old_stage = self.current_stage

        # 记录阶段变化
        self.stage_history.append({
            "from": old_stage.value,
            "to": new_stage.value,
            "at_chapter": self.last_appearance,
            "transition_count": len(self.transitions),
        })

        self.current_stage = new_stage

    def get_growth_summary(self) -> Dict[str, Any]:
        """获取成长摘要"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "current_stage": self.current_stage.value,
            "appearance_count": self.appearance_count,
            "transition_count": len(self.transitions),
            "stage_progression": [
                {
                    "stage": h["to"],
                    "chapter": h["at_chapter"],
                }
                for h in self.stage_history
            ],
            "current_state_summary": {
                "desires_count": len(self.current_state.desires),
                "fears_count": len(self.current_state.fears),
                "false_beliefs_count": len(self.current_state.false_beliefs),
                "values_count": len(self.current_state.values),
                "abilities_count": len(self.current_state.abilities),
                "relationships_count": len(self.current_state.relationships),
                "prices_paid_count": len(self.current_state.prices_paid),
                "irreversible_choices_count": len(self.current_state.irreversible_choices),
            },
            "recent_transitions": [
                {
                    "type": t.transition_type.value,
                    "chapter": t.chapter_id,
                    "description": t.description,
                    "impact": t.impact_score,
                }
                for t in self.transitions[-3:]  # 最近3次
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "current_stage": self.current_stage.value,
            "appearance_count": self.appearance_count,
            "last_appearance": self.last_appearance,
            "current_state": {
                "desires": self.current_state.desires,
                "false_beliefs": self.current_state.false_beliefs,
                "fears": self.current_state.fears,
                "values": self.current_state.values,
                "strategies": self.current_state.strategies,
                "relationships": self.current_state.relationships,
                "abilities": self.current_state.abilities,
                "prices_paid": self.current_state.prices_paid,
                "irreversible_choices": self.current_state.irreversible_choices,
            },
            "transitions": [
                {
                    "chapter_id": t.chapter_id,
                    "type": t.transition_type.value,
                    "description": t.description,
                    "trigger_event": t.trigger_event,
                    "impact_score": t.impact_score,
                    "before": t.before,
                    "after": t.after,
                }
                for t in self.transitions
            ],
            "stage_history": self.stage_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterGrowth":
        """从字典反序列化"""
        growth = cls(
            character_id=data["character_id"],
            name=data["name"],
            current_stage=GrowthStage(data["current_stage"]),
            appearance_count=data.get("appearance_count", 0),
            last_appearance=data.get("last_appearance"),
        )

        # 恢复当前状态
        state_data = data.get("current_state", {})
        growth.current_state = CharacterState(
            desires=state_data.get("desires", []),
            false_beliefs=state_data.get("false_beliefs", []),
            fears=state_data.get("fears", []),
            values=state_data.get("values", []),
            strategies=state_data.get("strategies", []),
            relationships=state_data.get("relationships", {}),
            abilities=state_data.get("abilities", []),
            prices_paid=state_data.get("prices_paid", []),
            irreversible_choices=state_data.get("irreversible_choices", []),
        )

        # 恢复转移历史
        for t_data in data.get("transitions", []):
            transition = StateTransition(
                chapter_id=t_data["chapter_id"],
                transition_type=TransitionType(t_data["type"]),
                description=t_data["description"],
                trigger_event=t_data["trigger_event"],
                impact_score=t_data.get("impact_score", 0.5),
                before=t_data.get("before", {}),
                after=t_data.get("after", {}),
            )
            growth.transitions.append(transition)

        # 恢复阶段历史
        growth.stage_history = data.get("stage_history", [])

        return growth
