"""
Constitution-Aware Paywall Optimizer - 基于商业规则的付费点优化器

集成Commercial Constitution，在核心卖点兑现时智能推荐付费点。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# 导入现有模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.commercial_constitution import (
    CommercialConstitution,
    SellingPoint,
)


@dataclass
class DeliveredSellingPoint:
    """
    已兑现的卖点

    表示一个卖点在章节中的兑现情况。
    """
    selling_point_name: str
    delivery_quality: float      # 0-1, 兑现质量
    evidence: Dict[str, Any]     # 证据（关键词命中、分数等）
    chapter_number: int


@dataclass
class ConstitutionPaywallRecommendation:
    """
    基于Constitution的付费点推荐

    综合考虑卖点兑现、商业规则、钩子强度等因素。
    """
    should_place_paywall: bool
    chapter_number: int
    confidence: float            # 0-1, 推荐置信度

    # Constitution相关
    delivered_selling_points: List[DeliveredSellingPoint] = field(default_factory=list)
    constitution_compliance: bool = True
    earliest_chapter_met: bool = True

    # 评分维度
    selling_point_score: float = 0.0    # 卖点得分 0-1
    hook_strength_score: float = 0.0    # 钩子强度 0-1
    timing_score: float = 0.0           # 时机得分 0-1
    quality_score: float = 0.0          # 质量得分 0-1

    # 决策理由
    primary_reason: str = ""
    supporting_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SellingPointDetector:
    """
    卖点兑现检测器

    检测章节中哪些核心卖点得到了兑现。
    """

    def __init__(self, constitution: CommercialConstitution):
        self.constitution = constitution

    def detect_delivered_selling_points(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> List[DeliveredSellingPoint]:
        """
        检测已兑现的卖点

        Args:
            chapter_number: 章节号
            chapter_content: 章节正文
            chapter_metadata: 章节元数据（QA分数、Promise等）

        Returns:
            已兑现的卖点列表
        """
        delivered = []

        for sp in self.constitution.core_selling_points:
            delivery = self._check_selling_point_delivery(
                sp, chapter_number, chapter_content, chapter_metadata
            )
            if delivery:
                delivered.append(delivery)

        return delivered

    def _check_selling_point_delivery(
        self,
        selling_point: SellingPoint,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[DeliveredSellingPoint]:
        """检查单个卖点是否兑现"""

        # 1. 检查关键词命中
        keywords_hit = sum(
            1 for kw in selling_point.validation_keywords
            if kw in chapter_content
        )

        if keywords_hit == 0:
            return None

        keyword_ratio = keywords_hit / len(selling_point.validation_keywords)

        # 2. 检查相关QA分数
        qa_scores = chapter_metadata.get("qa_scores", {})
        relevant_score = self._get_relevant_qa_score(selling_point, qa_scores)

        # 3. 计算兑现质量
        delivery_quality = (
            keyword_ratio * 0.4 +
            relevant_score / 100 * 0.6
        )

        # 4. 检查是否达到最低强度
        if delivery_quality < selling_point.minimum_intensity:
            return None

        # 5. 构建证据
        evidence = {
            "keywords_hit": keywords_hit,
            "keywords_total": len(selling_point.validation_keywords),
            "keyword_ratio": keyword_ratio,
            "relevant_qa_score": relevant_score,
        }

        return DeliveredSellingPoint(
            selling_point_name=selling_point.name,
            delivery_quality=delivery_quality,
            evidence=evidence,
            chapter_number=chapter_number,
        )

    def _get_relevant_qa_score(
        self,
        selling_point: SellingPoint,
        qa_scores: Dict[str, float]
    ) -> float:
        """获取与卖点相关的QA分数"""

        # 根据卖点类型映射到QA维度
        type_to_qa = {
            "power": "character_growth",
            "emotional": "emotion",
            "plot": "curiosity",
            "relationship": "emotion",
        }

        qa_dimension = type_to_qa.get(selling_point.type, "payoff")
        return qa_scores.get(qa_dimension, 0)


class ConstitutionAwarePaywallOptimizer:
    """
    基于Constitution的付费点优化器

    集成商业规则，在卖点兑现时机推荐付费点。
    """

    def __init__(self, constitution: CommercialConstitution):
        self.constitution = constitution
        self.detector = SellingPointDetector(constitution)

    def recommend_paywall(
        self,
        chapter_number: int,
        chapter_content: str,
        chapter_metadata: Dict[str, Any],
        paywall_history: Optional[List[int]] = None
    ) -> ConstitutionPaywallRecommendation:
        """
        推荐是否在此章设置付费点

        Args:
            chapter_number: 章节号
            chapter_content: 章节正文
            chapter_metadata: 章节元数据
            paywall_history: 已设置的付费点列表

        Returns:
            付费点推荐
        """
        if paywall_history is None:
            paywall_history = []

        # 1. 检查Constitution约束
        constraints_ok, constraint_warnings = self._check_constraints(
            chapter_number, chapter_metadata, paywall_history
        )

        if not constraints_ok:
            return ConstitutionPaywallRecommendation(
                should_place_paywall=False,
                chapter_number=chapter_number,
                confidence=0.0,
                constitution_compliance=False,
                earliest_chapter_met=False,  # 修复：标记为False
                primary_reason="不满足Constitution约束",
                warnings=constraint_warnings,
            )

        # 2. 检测卖点兑现
        delivered_sps = self.detector.detect_delivered_selling_points(
            chapter_number, chapter_content, chapter_metadata
        )

        # 3. 计算各维度得分
        selling_point_score = self._calculate_selling_point_score(delivered_sps)
        hook_strength_score = self._calculate_hook_strength(chapter_metadata)
        timing_score = self._calculate_timing_score(
            chapter_number, paywall_history
        )
        quality_score = self._calculate_quality_score(chapter_metadata)

        # 4. 综合决策
        overall_score = (
            selling_point_score * 0.4 +
            hook_strength_score * 0.3 +
            timing_score * 0.2 +
            quality_score * 0.1
        )

        # 5. 判断是否推荐
        should_place = overall_score >= 0.7 and len(delivered_sps) > 0

        # 6. 生成理由
        primary_reason = self._generate_primary_reason(
            should_place, delivered_sps, overall_score
        )

        supporting_reasons = self._generate_supporting_reasons(
            delivered_sps, chapter_metadata
        )

        return ConstitutionPaywallRecommendation(
            should_place_paywall=should_place,
            chapter_number=chapter_number,
            confidence=overall_score,
            delivered_selling_points=delivered_sps,
            constitution_compliance=True,
            earliest_chapter_met=True,
            selling_point_score=selling_point_score,
            hook_strength_score=hook_strength_score,
            timing_score=timing_score,
            quality_score=quality_score,
            primary_reason=primary_reason,
            supporting_reasons=supporting_reasons,
        )

    def _check_constraints(
        self,
        chapter_number: int,
        chapter_metadata: Dict[str, Any],
        paywall_history: List[int]
    ) -> tuple[bool, List[str]]:
        """检查Constitution约束"""
        warnings = []

        if not self.constitution.constraints:
            return True, warnings

        constraints = self.constitution.constraints

        # 检查最早付费章节
        if chapter_number < constraints.paywall_earliest_chapter:
            warnings.append(
                f"早于最早付费章节({constraints.paywall_earliest_chapter})"
            )
            return False, warnings

        # 检查钩子分数
        hook_score = chapter_metadata.get("qa_scores", {}).get("hook", 0)
        if hook_score < constraints.min_hook_score:
            warnings.append(
                f"钩子分数({hook_score})低于阈值({constraints.min_hook_score})"
            )
            return False, warnings

        # 检查付费点间隔（建议至少50章）
        if paywall_history:
            last_paywall = max(paywall_history)
            if chapter_number - last_paywall < 50:
                warnings.append("距离上一个付费点过近（<50章）")
                return False, warnings

        return True, warnings

    def _calculate_selling_point_score(
        self,
        delivered_sps: List[DeliveredSellingPoint]
    ) -> float:
        """计算卖点得分"""
        if not delivered_sps:
            return 0.0

        # 平均兑现质量
        avg_quality = sum(sp.delivery_quality for sp in delivered_sps) / len(delivered_sps)

        # 兑现数量加成（最多3个卖点）
        quantity_bonus = min(len(delivered_sps) / 3, 1.0) * 0.2

        return min(avg_quality + quantity_bonus, 1.0)

    def _calculate_hook_strength(
        self,
        chapter_metadata: Dict[str, Any]
    ) -> float:
        """计算钩子强度得分"""
        hook_score = chapter_metadata.get("qa_scores", {}).get("hook", 0)
        return hook_score / 100

    def _calculate_timing_score(
        self,
        chapter_number: int,
        paywall_history: List[int]
    ) -> float:
        """计算时机得分"""
        if not paywall_history:
            # 第一个付费点，检查是否在合理范围（30-50章）
            if 30 <= chapter_number <= 50:
                return 1.0
            elif chapter_number < 30:
                return 0.5
            else:
                return 0.8

        # 后续付费点，检查间隔是否合适（50-100章）
        last_paywall = max(paywall_history)
        interval = chapter_number - last_paywall

        if 50 <= interval <= 100:
            return 1.0
        elif interval < 50:
            return 0.3  # 过近
        else:
            return 0.6  # 过远

    def _calculate_quality_score(
        self,
        chapter_metadata: Dict[str, Any]
    ) -> float:
        """计算质量得分"""
        qa_scores = chapter_metadata.get("qa_scores", {})

        # 关键质量维度
        key_dimensions = ["retention", "reward_density", "payoff"]
        scores = [qa_scores.get(dim, 0) for dim in key_dimensions]

        if not scores:
            return 0.0

        return sum(scores) / len(scores) / 100

    def _generate_primary_reason(
        self,
        should_place: bool,
        delivered_sps: List[DeliveredSellingPoint],
        overall_score: float
    ) -> str:
        """生成主要理由"""
        if not should_place:
            if not delivered_sps:
                return "未检测到核心卖点兑现"
            else:
                return f"综合得分不足({overall_score:.2%})"

        # 列出兑现的卖点
        sp_names = [sp.selling_point_name for sp in delivered_sps]
        return f"核心卖点兑现: {', '.join(sp_names)}"

    def _generate_supporting_reasons(
        self,
        delivered_sps: List[DeliveredSellingPoint],
        chapter_metadata: Dict[str, Any]
    ) -> List[str]:
        """生成支持理由"""
        reasons = []

        # 卖点详情
        for sp in delivered_sps:
            reasons.append(
                f"{sp.selling_point_name}: 质量{sp.delivery_quality:.1%}"
            )

        # 质量指标
        qa_scores = chapter_metadata.get("qa_scores", {})
        hook = qa_scores.get("hook", 0)
        if hook >= 80:
            reasons.append(f"钩子强度优秀({hook}分)")

        return reasons
