"""
Character Arc Validator - 人物弧验证器 (C3-3)

基于P1-4的CharacterGrowth，验证跨章节人物成长的连续性和合理性。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import sys
from pathlib import Path

# 导入P1-4的CharacterGrowth
sys.path.insert(0, str(Path(__file__).parent))
from character_growth import (
    CharacterGrowth,
    GrowthStage,
    StateTransition,
    TransitionType,
)


class ArcIssueType(Enum):
    """人物弧问题类型"""
    STAGE_REGRESSION = "stage_regression"           # 阶段倒退
    MISSING_TRANSITION = "missing_transition"       # 缺少转移
    STATE_INCONSISTENCY = "state_inconsistency"     # 状态不一致
    GROWTH_TOO_FAST = "growth_too_fast"            # 成长过快
    GROWTH_STAGNANT = "growth_stagnant"            # 成长停滞
    MOTIVATION_LOST = "motivation_lost"            # 动机丢失


class ArcIssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ArcIssue:
    """
    人物弧问题

    记录人物成长中的问题。
    """
    issue_type: ArcIssueType
    severity: ArcIssueSeverity
    character_id: str

    description: str
    chapters: List[int] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class ArcValidationReport:
    """
    人物弧验证报告

    汇总人物成长的验证结果。
    """
    character_id: str
    character_name: str
    current_chapter: int

    # 成长统计
    current_stage: GrowthStage
    total_transitions: int
    appearance_count: int

    # 问题列表
    issues: List[ArcIssue] = field(default_factory=list)

    # 健康度
    arc_health_score: float = 1.0  # 0-1, 1表示完全健康

    # 建议
    recommendations: List[str] = field(default_factory=list)


class CharacterArcValidator:
    """
    人物弧验证器

    验证人物成长的连续性和合理性。
    """

    def __init__(self):
        # 阶段推进阈值
        self.stage_thresholds = {
            GrowthStage.INTRODUCED: 2,      # 2次转移可推进
            GrowthStage.ESTABLISHED: 3,     # 3次转移可推进
            GrowthStage.CHALLENGED: 3,      # 3次转移可推进
            GrowthStage.TRANSFORMED: 4,     # 4次转移可推进
        }

    def validate_arc(
        self,
        character_growth: CharacterGrowth,
        current_chapter: int,
        chapter_range: int = 20  # 检查最近N章
    ) -> ArcValidationReport:
        """
        验证人物弧

        Args:
            character_growth: CharacterGrowth对象
            current_chapter: 当前章节号
            chapter_range: 检查章节范围

        Returns:
            验证报告
        """
        issues = []

        # 1. 检查阶段倒退
        regression_issues = self._check_stage_regression(character_growth)
        issues.extend(regression_issues)

        # 2. 检查成长速度
        speed_issues = self._check_growth_speed(
            character_growth, current_chapter, chapter_range
        )
        issues.extend(speed_issues)

        # 3. 检查状态一致性
        consistency_issues = self._check_state_consistency(character_growth)
        issues.extend(consistency_issues)

        # 4. 检查动机持续性
        motivation_issues = self._check_motivation_continuity(character_growth)
        issues.extend(motivation_issues)

        # 5. 计算健康度
        arc_health = self._calculate_arc_health(issues)

        # 6. 生成建议
        recommendations = self._generate_recommendations(
            character_growth, issues, current_chapter
        )

        # 7. 构建报告
        return ArcValidationReport(
            character_id=character_growth.character_id,
            character_name=character_growth.name,
            current_chapter=current_chapter,
            current_stage=character_growth.current_stage,
            total_transitions=len(character_growth.transitions),
            appearance_count=character_growth.appearance_count,
            issues=issues,
            arc_health_score=arc_health,
            recommendations=recommendations,
        )

    def _check_stage_regression(
        self,
        character_growth: CharacterGrowth
    ) -> List[ArcIssue]:
        """检查阶段倒退"""
        issues = []

        # 检查stage_history
        stage_order = [
            GrowthStage.INTRODUCED,
            GrowthStage.ESTABLISHED,
            GrowthStage.CHALLENGED,
            GrowthStage.TRANSFORMED,
            GrowthStage.EVOLVED,
        ]

        for i in range(len(character_growth.stage_history) - 1):
            from_stage = GrowthStage(character_growth.stage_history[i]["from"])
            to_stage = GrowthStage(character_growth.stage_history[i]["to"])

            from_idx = stage_order.index(from_stage)
            to_idx = stage_order.index(to_stage)

            if to_idx < from_idx:
                # 阶段倒退
                issues.append(ArcIssue(
                    issue_type=ArcIssueType.STAGE_REGRESSION,
                    severity=ArcIssueSeverity.CRITICAL,
                    character_id=character_growth.character_id,
                    description=f"成长阶段倒退：从{from_stage.value}退回{to_stage.value}",
                    suggestion="检查是否有合理的剧情原因（如失忆、诅咒等）",
                ))

        return issues

    def _check_growth_speed(
        self,
        character_growth: CharacterGrowth,
        current_chapter: int,
        chapter_range: int
    ) -> List[ArcIssue]:
        """检查成长速度"""
        issues = []

        # 检查最近的转移频率
        recent_transitions = [
            t for t in character_growth.transitions[-10:]
            if current_chapter - int(t.chapter_id.split('-')[1]) <= chapter_range
        ] if character_growth.transitions else []

        # 成长过快：短时间内过多转移
        if len(recent_transitions) > 5:
            issues.append(ArcIssue(
                issue_type=ArcIssueType.GROWTH_TOO_FAST,
                severity=ArcIssueSeverity.MEDIUM,
                character_id=character_growth.character_id,
                description=f"最近{chapter_range}章内发生{len(recent_transitions)}次状态转移，可能过快",
                suggestion="考虑放缓成长节奏，让角色有时间消化变化",
            ))

        # 成长停滞：长时间无转移
        if character_growth.appearance_count > 10 and len(character_growth.transitions) < 3:
            issues.append(ArcIssue(
                issue_type=ArcIssueType.GROWTH_STAGNANT,
                severity=ArcIssueSeverity.HIGH,
                character_id=character_growth.character_id,
                description=f"出场{character_growth.appearance_count}次但仅{len(character_growth.transitions)}次转移，成长过慢",
                suggestion="增加角色的状态转移，推动成长",
            ))

        return issues

    def _check_state_consistency(
        self,
        character_growth: CharacterGrowth
    ) -> List[ArcIssue]:
        """检查状态一致性"""
        issues = []

        state = character_growth.current_state

        # 检查矛盾的状态
        # 例如：有欲望但没有行动策略
        if state.desires and not state.strategies:
            issues.append(ArcIssue(
                issue_type=ArcIssueType.STATE_INCONSISTENCY,
                severity=ArcIssueSeverity.LOW,
                character_id=character_growth.character_id,
                description="角色有欲望但缺少行动策略",
                suggestion="添加角色的行动策略（strategies）",
            ))

        # 检查：有恐惧但从未面对
        if state.fears and character_growth.current_stage == GrowthStage.INTRODUCED:
            # 这是正常的，刚介绍时可以有恐惧
            pass
        elif state.fears and len(character_growth.transitions) > 5:
            # 很多转移了但恐惧从未被处理
            fear_confronted = any(
                t.transition_type == TransitionType.FEAR_CONFRONTED
                for t in character_growth.transitions
            )
            if not fear_confronted:
                issues.append(ArcIssue(
                    issue_type=ArcIssueType.STATE_INCONSISTENCY,
                    severity=ArcIssueSeverity.MEDIUM,
                    character_id=character_growth.character_id,
                    description="角色有恐惧但从未面对",
                    suggestion="安排场景让角色面对恐惧",
                ))

        return issues

    def _check_motivation_continuity(
        self,
        character_growth: CharacterGrowth
    ) -> List[ArcIssue]:
        """检查动机持续性"""
        issues = []

        # 检查欲望是否突然消失
        if len(character_growth.transitions) >= 2:
            # 查看早期转移中建立的欲望
            early_desires = set()
            for t in character_growth.transitions[:3]:
                if t.transition_type == TransitionType.DESIRE_REVEALED:
                    # 从state_changes中提取desires
                    desires = t.state_changes.get("desires", [])
                    early_desires.update(desires)

            # 检查这些欲望是否还存在
            current_desires = set(character_growth.current_state.desires)
            lost_desires = early_desires - current_desires

            if lost_desires and len(character_growth.transitions) < 10:
                # 早期欲望消失了，但角色还没完全转变
                issues.append(ArcIssue(
                    issue_type=ArcIssueType.MOTIVATION_LOST,
                    severity=ArcIssueSeverity.MEDIUM,
                    character_id=character_growth.character_id,
                    description=f"早期欲望丢失：{', '.join(lost_desires)}",
                    suggestion="要么恢复这些欲望，要么通过转移明确放弃它们",
                ))

        return issues

    def _calculate_arc_health(self, issues: List[ArcIssue]) -> float:
        """计算人物弧健康度"""
        if not issues:
            return 1.0

        severity_weights = {
            ArcIssueSeverity.CRITICAL: 0.3,
            ArcIssueSeverity.HIGH: 0.15,
            ArcIssueSeverity.MEDIUM: 0.08,
            ArcIssueSeverity.LOW: 0.03,
        }

        total_penalty = sum(
            severity_weights.get(issue.severity, 0)
            for issue in issues
        )

        return max(0.0, 1.0 - total_penalty)

    def _generate_recommendations(
        self,
        character_growth: CharacterGrowth,
        issues: List[ArcIssue],
        current_chapter: int
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 按严重程度统计
        critical = [i for i in issues if i.severity == ArcIssueSeverity.CRITICAL]
        high = [i for i in issues if i.severity == ArcIssueSeverity.HIGH]

        if critical:
            recommendations.append(
                f"🔴 严重：发现{len(critical)}个严重的人物弧问题，必须修正"
            )

        if high:
            recommendations.append(
                f"🟠 高：发现{len(high)}个高优先级问题，建议尽快处理"
            )

        # 成长阶段建议
        if character_growth.current_stage == GrowthStage.INTRODUCED:
            if len(character_growth.transitions) >= 3:
                recommendations.append(
                    "💡 角色已有足够转移，可以考虑推进到ESTABLISHED阶段"
                )

        # 状态建议
        if not character_growth.current_state.desires:
            recommendations.append(
                "💡 建议明确角色的欲望（desires），这是推动成长的核心"
            )

        return recommendations

    def generate_summary(self, report: ArcValidationReport) -> str:
        """生成可读的验证摘要"""
        lines = []
        lines.append(f"=== 人物弧验证报告: {report.character_name} (第{report.current_chapter}章) ===")
        lines.append(f"当前阶段: {report.current_stage.value}")
        lines.append(f"状态转移: {report.total_transitions}次")
        lines.append(f"出场次数: {report.appearance_count}次")
        lines.append(f"健康度: {report.arc_health_score:.1%}")
        lines.append("")

        # 问题列表
        if report.issues:
            lines.append(f"发现问题 ({len(report.issues)}个):")
            for i, issue in enumerate(report.issues[:5], 1):  # 最多显示5个
                severity_icon = {
                    ArcIssueSeverity.CRITICAL: "🔴",
                    ArcIssueSeverity.HIGH: "🟠",
                    ArcIssueSeverity.MEDIUM: "🟡",
                    ArcIssueSeverity.LOW: "🟢",
                }
                icon = severity_icon.get(issue.severity, "⚪")
                lines.append(f"  {i}. {icon} {issue.description}")
                if issue.suggestion:
                    lines.append(f"     建议: {issue.suggestion}")

        # 建议
        if report.recommendations:
            lines.append("")
            lines.append("建议:")
            for rec in report.recommendations:
                lines.append(f"  {rec}")

        return "\n".join(lines)
