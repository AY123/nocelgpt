"""
Paywall Optimizer - 事件驱动付费点优化器 (P2-2)

从固定章号付费墙升级为基于内容事件的智能付费点推荐。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class PaywallEventType(Enum):
    """付费点事件类型"""
    ABILITY_FIRST_DELIVERY = "ability_first_delivery"       # 核心能力首次兑现
    STAGE_VICTORY = "stage_victory"                          # 阶段胜利
    RELATIONSHIP_MILESTONE = "relationship_milestone"        # 关系里程碑
    IDENTITY_REVEAL = "identity_reveal"                      # 身份揭示
    POWER_BREAKTHROUGH = "power_breakthrough"                # 重大突破
    PAYOFF_CLUSTER = "payoff_cluster"                       # 爽点集群
    ARC_COMPLETION = "arc_completion"                       # 故事弧完结


@dataclass
class PaywallEvent:
    """
    付费点事件

    表示一个可能适合设置付费墙的事件。
    """
    event_type: PaywallEventType
    chapter_number: int
    importance: float           # 事件重要性 (0-1)
    description: str            # 事件描述
    evidence: Dict[str, Any]    # 证据数据

    # 质量指标
    content_quality: float = 0.0     # 内容质量 (0-1)
    reader_engagement: float = 0.0   # 读者投入度 (0-1)
    timing_score: float = 0.0        # 时机得分 (0-1)

    def calculate_score(self) -> float:
        """
        计算付费点综合得分

        Returns:
            综合得分 (0-1)
        """
        return (
            self.importance * 0.4 +
            self.content_quality * 0.3 +
            self.reader_engagement * 0.2 +
            self.timing_score * 0.1
        )


@dataclass
class PaywallRecommendation:
    """
    付费墙推荐

    建议是否在某章节设置付费墙。
    """
    should_place_paywall: bool
    chapter_number: int
    confidence: float           # 推荐置信度 (0-1)

    # 支持信息
    primary_event: Optional[PaywallEvent] = None
    supporting_events: List[PaywallEvent] = field(default_factory=list)

    # 决策理由
    reasoning: str = ""
    alternative_chapters: List[int] = field(default_factory=list)


class PaywallDetector:
    """
    付费点事件检测器

    检测章节中可能适合设置付费墙的事件。
    """

    def __init__(self):
        pass

    def detect_events(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any],
        story_state: Optional[Dict[str, Any]] = None
    ) -> List[PaywallEvent]:
        """
        检测付费点事件

        Args:
            chapter_number: 章节号
            chapter_content: 章节正文
            chapter_metadata: 章节元数据（QA分数、Promise等）
            story_state: 故事状态（可选）

        Returns:
            检测到的事件列表
        """
        events = []

        # 1. 检测核心能力首次兑现
        ability_event = self._detect_ability_first_delivery(
            chapter_number, chapter_content, chapter_metadata
        )
        if ability_event:
            events.append(ability_event)

        # 2. 检测阶段胜利
        victory_event = self._detect_stage_victory(
            chapter_number, chapter_content, chapter_metadata
        )
        if victory_event:
            events.append(victory_event)

        # 3. 检测关系里程碑
        relationship_event = self._detect_relationship_milestone(
            chapter_number, chapter_content, chapter_metadata
        )
        if relationship_event:
            events.append(relationship_event)

        # 4. 检测身份揭示
        identity_event = self._detect_identity_reveal(
            chapter_number, chapter_content, chapter_metadata
        )
        if identity_event:
            events.append(identity_event)

        # 5. 检测重大突破
        breakthrough_event = self._detect_power_breakthrough(
            chapter_number, chapter_content, chapter_metadata
        )
        if breakthrough_event:
            events.append(breakthrough_event)

        # 6. 检测爽点集群
        cluster_event = self._detect_payoff_cluster(
            chapter_number, chapter_metadata, story_state
        )
        if cluster_event:
            events.append(cluster_event)

        return events

    def _detect_ability_first_delivery(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[PaywallEvent]:
        """检测核心能力首次兑现"""
        # 检查Promise delivery
        promises_delivered = chapter_metadata.get("promises_delivered", [])

        # 简单实现：检查是否有核心能力类Promise兑现
        core_ability_keywords = ["能力", "技能", "天赋", "力量", "突破"]
        for promise_id in promises_delivered:
            # 假设promise_id包含描述信息
            if any(kw in str(promise_id) for kw in core_ability_keywords):
                # 检查payoff分数
                payoff_score = chapter_metadata.get("qa_scores", {}).get("payoff", 0)
                if payoff_score >= 80:
                    return PaywallEvent(
                        event_type=PaywallEventType.ABILITY_FIRST_DELIVERY,
                        chapter_number=chapter_number,
                        importance=0.9,  # 高重要性
                        description=f"核心能力首次兑现：{promise_id}",
                        evidence={
                            "promise_id": promise_id,
                            "payoff_score": payoff_score
                        },
                        content_quality=payoff_score / 100,
                        reader_engagement=0.8,
                        timing_score=0.9,
                    )

        return None

    def _detect_stage_victory(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[PaywallEvent]:
        """检测阶段胜利"""
        qa_scores = chapter_metadata.get("qa_scores", {})

        # 检查高reward_density + 高payoff
        reward_density = qa_scores.get("reward_density", 0)
        payoff = qa_scores.get("payoff", 0)

        # 阶段胜利的特征：reward和payoff都很高
        if reward_density >= 85 and payoff >= 85:
            # 检查是否有"胜利"相关关键词
            victory_keywords = ["胜利", "成功", "打败", "战胜", "完成"]
            has_victory = any(kw in chapter_content for kw in victory_keywords)

            if has_victory:
                return PaywallEvent(
                    event_type=PaywallEventType.STAGE_VICTORY,
                    chapter_number=chapter_number,
                    importance=0.85,
                    description="阶段性胜利达成",
                    evidence={
                        "reward_density": reward_density,
                        "payoff": payoff
                    },
                    content_quality=(reward_density + payoff) / 200,
                    reader_engagement=0.85,
                    timing_score=0.8,
                )

        return None

    def _detect_relationship_milestone(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[PaywallEvent]:
        """检测关系里程碑"""
        # 检查emotion分数
        emotion_score = chapter_metadata.get("qa_scores", {}).get("emotion", 0)

        # 检查关系相关关键词
        relationship_keywords = ["关系", "感情", "信任", "友谊", "爱", "认可"]
        has_relationship = any(kw in chapter_content for kw in relationship_keywords)

        if emotion_score >= 85 and has_relationship:
            return PaywallEvent(
                event_type=PaywallEventType.RELATIONSHIP_MILESTONE,
                chapter_number=chapter_number,
                importance=0.7,
                description="重要关系达成里程碑",
                evidence={
                    "emotion_score": emotion_score
                },
                content_quality=emotion_score / 100,
                reader_engagement=0.75,
                timing_score=0.7,
            )

        return None

    def _detect_identity_reveal(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[PaywallEvent]:
        """检测身份揭示"""
        # 检查identity相关关键词
        identity_keywords = ["真相", "身份", "原来", "其实", "竟然是", "揭示"]
        has_reveal = any(kw in chapter_content for kw in identity_keywords)

        if has_reveal:
            # 检查curiosity分数（好奇心满足）
            curiosity = chapter_metadata.get("qa_scores", {}).get("curiosity", 0)
            if curiosity >= 80:
                return PaywallEvent(
                    event_type=PaywallEventType.IDENTITY_REVEAL,
                    chapter_number=chapter_number,
                    importance=0.8,
                    description="重要身份或真相揭示",
                    evidence={
                        "curiosity": curiosity
                    },
                    content_quality=curiosity / 100,
                    reader_engagement=0.8,
                    timing_score=0.85,
                )

        return None

    def _detect_power_breakthrough(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[PaywallEvent]:
        """检测重大突破"""
        # 检查突破相关关键词
        breakthrough_keywords = ["突破", "进阶", "升级", "境界提升", "质变"]
        has_breakthrough = any(kw in chapter_content for kw in breakthrough_keywords)

        if has_breakthrough:
            # 检查character_growth分数
            growth_score = chapter_metadata.get("qa_scores", {}).get("character_growth", 0)
            if growth_score >= 85:
                return PaywallEvent(
                    event_type=PaywallEventType.POWER_BREAKTHROUGH,
                    chapter_number=chapter_number,
                    importance=0.75,
                    description="主角实力重大突破",
                    evidence={
                        "character_growth": growth_score
                    },
                    content_quality=growth_score / 100,
                    reader_engagement=0.7,
                    timing_score=0.75,
                )

        return None

    def _detect_payoff_cluster(
        self,
        chapter_number: int,
        chapter_metadata: Dict[str, Any],
        story_state: Optional[Dict[str, Any]]
    ) -> Optional[PaywallEvent]:
        """检测爽点集群"""
        # 需要跨章节数据，简单实现先跳过
        # 实际应检查最近3章的reward_density
        return None
