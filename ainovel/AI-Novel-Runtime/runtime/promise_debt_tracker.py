"""
Promise Debt Tracker - Promise债务监控器 (C3-1)

跨章节追踪Promise状态，检测债务累积，提供自动提醒。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class PromiseUrgency(Enum):
    """Promise紧急程度"""
    CRITICAL = "critical"      # 严重逾期（>20章未兑现）
    HIGH = "high"              # 高度紧急（15-20章）
    MEDIUM = "medium"          # 中度紧急（10-15章）
    LOW = "low"                # 低紧急（5-10章）
    NORMAL = "normal"          # 正常（<5章）


@dataclass
class PromiseDebtItem:
    """
    Promise债务项

    表示一个需要兑现的Promise及其紧急程度。
    """
    promise_id: str
    promise_type: str          # "setup" | "foreshadow" | "relationship" | ...
    description: str

    # 时间信息
    created_chapter: int       # 创建章节
    current_chapter: int       # 当前章节
    chapters_pending: int      # 已等待章节数

    # 紧急程度
    urgency: PromiseUrgency
    target_chapter: Optional[int] = None  # 计划兑现章节

    # 上下文
    related_characters: List[str] = field(default_factory=list)
    related_plot_lines: List[str] = field(default_factory=list)

    # 元数据
    importance: float = 0.5    # 重要性 0-1
    reader_expectation: float = 0.5  # 读者期待度 0-1


@dataclass
class DebtReport:
    """
    债务报告

    汇总当前所有Promise债务情况。
    """
    current_chapter: int
    total_pending_promises: int

    # 按紧急程度分类
    critical_debts: List[PromiseDebtItem] = field(default_factory=list)
    high_urgency_debts: List[PromiseDebtItem] = field(default_factory=list)
    medium_urgency_debts: List[PromiseDebtItem] = field(default_factory=list)
    low_urgency_debts: List[PromiseDebtItem] = field(default_factory=list)
    normal_debts: List[PromiseDebtItem] = field(default_factory=list)

    # 统计
    average_pending_chapters: float = 0.0
    max_pending_chapters: int = 0

    # 建议
    recommendations: List[str] = field(default_factory=list)
    next_chapter_suggestions: List[str] = field(default_factory=list)


class PromiseDebtTracker:
    """
    Promise债务追踪器

    跨章节监控Promise状态，检测债务累积。
    """

    def __init__(self):
        # 紧急程度阈值（章节数）
        self.urgency_thresholds = {
            PromiseUrgency.CRITICAL: 20,
            PromiseUrgency.HIGH: 15,
            PromiseUrgency.MEDIUM: 10,
            PromiseUrgency.LOW: 5,
        }

    def analyze_debt(
        self,
        current_chapter: int,
        promise_ledger: Dict[str, Any]
    ) -> DebtReport:
        """
        分析当前Promise债务情况

        Args:
            current_chapter: 当前章节号
            promise_ledger: Promise账本数据

        Returns:
            债务报告
        """
        # 1. 提取所有pending的Promise
        pending_promises = self._extract_pending_promises(
            current_chapter,
            promise_ledger
        )

        # 2. 计算紧急程度
        debt_items = []
        for promise in pending_promises:
            debt_item = self._create_debt_item(promise, current_chapter)
            debt_items.append(debt_item)

        # 3. 按紧急程度分类
        categorized = self._categorize_by_urgency(debt_items)

        # 4. 计算统计数据
        stats = self._calculate_statistics(debt_items)

        # 5. 生成建议
        recommendations = self._generate_recommendations(
            categorized,
            current_chapter
        )

        next_suggestions = self._generate_next_chapter_suggestions(
            categorized
        )

        # 6. 构建报告
        return DebtReport(
            current_chapter=current_chapter,
            total_pending_promises=len(debt_items),
            critical_debts=categorized[PromiseUrgency.CRITICAL],
            high_urgency_debts=categorized[PromiseUrgency.HIGH],
            medium_urgency_debts=categorized[PromiseUrgency.MEDIUM],
            low_urgency_debts=categorized[PromiseUrgency.LOW],
            normal_debts=categorized[PromiseUrgency.NORMAL],
            average_pending_chapters=stats["average"],
            max_pending_chapters=stats["max"],
            recommendations=recommendations,
            next_chapter_suggestions=next_suggestions,
        )

    def get_priority_promises(
        self,
        debt_report: DebtReport,
        top_n: int = 3
    ) -> List[PromiseDebtItem]:
        """
        获取优先级最高的Promise

        Args:
            debt_report: 债务报告
            top_n: 返回前N个

        Returns:
            优先级最高的Promise列表
        """
        # 按紧急程度排序
        all_debts = (
            debt_report.critical_debts +
            debt_report.high_urgency_debts +
            debt_report.medium_urgency_debts +
            debt_report.low_urgency_debts +
            debt_report.normal_debts
        )

        # 按多个维度排序
        sorted_debts = sorted(
            all_debts,
            key=lambda x: (
                -self._urgency_score(x.urgency),  # 紧急程度（高优先）
                -x.importance,                     # 重要性（高优先）
                -x.reader_expectation,             # 读者期待（高优先）
                -x.chapters_pending                # 等待时间（长优先）
            )
        )

        return sorted_debts[:top_n]

    def _extract_pending_promises(
        self,
        current_chapter: int,
        promise_ledger: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """提取所有pending的Promise"""
        pending = []

        promises = promise_ledger.get("promises", [])
        for promise in promises:
            # 检查状态
            status = promise.get("status", "pending")
            if status == "pending":
                pending.append(promise)

        return pending

    def _create_debt_item(
        self,
        promise: Dict[str, Any],
        current_chapter: int
    ) -> PromiseDebtItem:
        """创建债务项"""
        promise_id = promise.get("id", "")
        created_chapter = promise.get("created_chapter", 0)
        chapters_pending = current_chapter - created_chapter

        # 计算紧急程度
        urgency = self._calculate_urgency(chapters_pending)

        return PromiseDebtItem(
            promise_id=promise_id,
            promise_type=promise.get("type", "unknown"),
            description=promise.get("description", ""),
            created_chapter=created_chapter,
            current_chapter=current_chapter,
            chapters_pending=chapters_pending,
            urgency=urgency,
            target_chapter=promise.get("target_chapter"),
            related_characters=promise.get("related_characters", []),
            related_plot_lines=promise.get("plot_lines", []),
            importance=promise.get("importance", 0.5),
            reader_expectation=promise.get("reader_expectation", 0.5),
        )

    def _calculate_urgency(self, chapters_pending: int) -> PromiseUrgency:
        """计算紧急程度"""
        if chapters_pending >= self.urgency_thresholds[PromiseUrgency.CRITICAL]:
            return PromiseUrgency.CRITICAL
        elif chapters_pending >= self.urgency_thresholds[PromiseUrgency.HIGH]:
            return PromiseUrgency.HIGH
        elif chapters_pending >= self.urgency_thresholds[PromiseUrgency.MEDIUM]:
            return PromiseUrgency.MEDIUM
        elif chapters_pending >= self.urgency_thresholds[PromiseUrgency.LOW]:
            return PromiseUrgency.LOW
        else:
            return PromiseUrgency.NORMAL

    def _categorize_by_urgency(
        self,
        debt_items: List[PromiseDebtItem]
    ) -> Dict[PromiseUrgency, List[PromiseDebtItem]]:
        """按紧急程度分类"""
        categorized = {
            PromiseUrgency.CRITICAL: [],
            PromiseUrgency.HIGH: [],
            PromiseUrgency.MEDIUM: [],
            PromiseUrgency.LOW: [],
            PromiseUrgency.NORMAL: [],
        }

        for item in debt_items:
            categorized[item.urgency].append(item)

        return categorized

    def _calculate_statistics(
        self,
        debt_items: List[PromiseDebtItem]
    ) -> Dict[str, float]:
        """计算统计数据"""
        if not debt_items:
            return {"average": 0.0, "max": 0}

        pending_chapters = [item.chapters_pending for item in debt_items]

        return {
            "average": sum(pending_chapters) / len(pending_chapters),
            "max": max(pending_chapters),
        }

    def _generate_recommendations(
        self,
        categorized: Dict[PromiseUrgency, List[PromiseDebtItem]],
        current_chapter: int
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 检查critical债务
        if categorized[PromiseUrgency.CRITICAL]:
            count = len(categorized[PromiseUrgency.CRITICAL])
            recommendations.append(
                f"⚠️ 严重：有{count}个Promise严重逾期（>20章），必须尽快兑现"
            )

        # 检查high债务
        if categorized[PromiseUrgency.HIGH]:
            count = len(categorized[PromiseUrgency.HIGH])
            recommendations.append(
                f"⚠️ 高度紧急：有{count}个Promise高度紧急（15-20章），建议在3章内兑现"
            )

        # 检查medium债务
        if categorized[PromiseUrgency.MEDIUM]:
            count = len(categorized[PromiseUrgency.MEDIUM])
            recommendations.append(
                f"⚠️ 中度紧急：有{count}个Promise中度紧急（10-15章），建议在5章内兑现"
            )

        # 总体债务检查
        total = sum(len(items) for items in categorized.values())
        if total > 10:
            recommendations.append(
                f"📊 债务过多：当前有{total}个待兑现Promise，建议加快兑现节奏"
            )

        return recommendations

    def _generate_next_chapter_suggestions(
        self,
        categorized: Dict[PromiseUrgency, List[PromiseDebtItem]]
    ) -> List[str]:
        """生成下一章建议"""
        suggestions = []

        # 优先处理critical
        critical = categorized[PromiseUrgency.CRITICAL]
        if critical:
            for item in critical[:2]:  # 最多2个
                suggestions.append(
                    f"💡 建议兑现：{item.description} "
                    f"(已等待{item.chapters_pending}章)"
                )

        # 如果没有critical，考虑high
        if not suggestions:
            high = categorized[PromiseUrgency.HIGH]
            if high:
                item = high[0]
                suggestions.append(
                    f"💡 建议兑现：{item.description} "
                    f"(已等待{item.chapters_pending}章)"
                )

        return suggestions

    def _urgency_score(self, urgency: PromiseUrgency) -> int:
        """将紧急程度转换为分数"""
        scores = {
            PromiseUrgency.CRITICAL: 5,
            PromiseUrgency.HIGH: 4,
            PromiseUrgency.MEDIUM: 3,
            PromiseUrgency.LOW: 2,
            PromiseUrgency.NORMAL: 1,
        }
        return scores.get(urgency, 0)

    def generate_summary(self, debt_report: DebtReport) -> str:
        """生成可读的债务摘要"""
        lines = []
        lines.append(f"=== Promise债务报告 (第{debt_report.current_chapter}章) ===")
        lines.append(f"总待兑现Promise: {debt_report.total_pending_promises}个")
        lines.append(f"平均等待: {debt_report.average_pending_chapters:.1f}章")
        lines.append(f"最长等待: {debt_report.max_pending_chapters}章")
        lines.append("")

        # 紧急程度分布
        lines.append("紧急程度分布:")
        if debt_report.critical_debts:
            lines.append(f"  🔴 严重: {len(debt_report.critical_debts)}个")
        if debt_report.high_urgency_debts:
            lines.append(f"  🟠 高: {len(debt_report.high_urgency_debts)}个")
        if debt_report.medium_urgency_debts:
            lines.append(f"  🟡 中: {len(debt_report.medium_urgency_debts)}个")
        if debt_report.low_urgency_debts:
            lines.append(f"  🟢 低: {len(debt_report.low_urgency_debts)}个")
        if debt_report.normal_debts:
            lines.append(f"  ⚪ 正常: {len(debt_report.normal_debts)}个")

        # 建议
        if debt_report.recommendations:
            lines.append("")
            lines.append("建议:")
            for rec in debt_report.recommendations:
                lines.append(f"  {rec}")

        # 下一章建议
        if debt_report.next_chapter_suggestions:
            lines.append("")
            lines.append("下一章建议:")
            for sug in debt_report.next_chapter_suggestions:
                lines.append(f"  {sug}")

        return "\n".join(lines)
