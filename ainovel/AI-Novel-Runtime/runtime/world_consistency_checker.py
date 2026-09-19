"""
World Consistency Checker - 世界设定一致性检查器 (C3-2)

跨章节追踪世界规则，检测设定矛盾，提供修正建议。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class InconsistencyType(Enum):
    """矛盾类型"""
    RULE_VIOLATION = "rule_violation"           # 规则违反
    POWER_LEVEL = "power_level"                 # 实力体系矛盾
    TIMELINE = "timeline"                       # 时间线矛盾
    GEOGRAPHY = "geography"                     # 地理矛盾
    CHARACTER_ABILITY = "character_ability"     # 角色能力矛盾
    WORLD_LAW = "world_law"                     # 世界法则矛盾


class InconsistencySeverity(Enum):
    """严重程度"""
    CRITICAL = "critical"      # 严重（破坏世界观）
    HIGH = "high"              # 高（明显矛盾）
    MEDIUM = "medium"          # 中（可能矛盾）
    LOW = "low"                # 低（小瑕疵）


@dataclass
class WorldRule:
    """
    世界规则定义

    记录世界设定中的规则和约束。
    """
    rule_id: str
    rule_type: str             # "power_system" | "magic" | "geography" | ...
    description: str

    # 规则内容
    constraints: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    # 来源
    established_chapter: int = 0
    source_text: str = ""


@dataclass
class Inconsistency:
    """
    设定矛盾

    记录检测到的世界设定矛盾。
    """
    inconsistency_id: str
    inconsistency_type: InconsistencyType
    severity: InconsistencySeverity

    # 矛盾描述
    description: str
    conflicting_statements: List[str] = field(default_factory=list)

    # 位置信息
    chapters: List[int] = field(default_factory=list)
    related_rules: List[str] = field(default_factory=list)

    # 修正建议
    suggestion: str = ""
    auto_fixable: bool = False


@dataclass
class ConsistencyReport:
    """
    一致性报告

    汇总世界设定的一致性检查结果。
    """
    current_chapter: int
    total_rules: int
    total_inconsistencies: int

    # 按严重程度分类
    critical_inconsistencies: List[Inconsistency] = field(default_factory=list)
    high_inconsistencies: List[Inconsistency] = field(default_factory=list)
    medium_inconsistencies: List[Inconsistency] = field(default_factory=list)
    low_inconsistencies: List[Inconsistency] = field(default_factory=list)

    # 按类型分类
    by_type: Dict[str, List[Inconsistency]] = field(default_factory=dict)

    # 建议
    recommendations: List[str] = field(default_factory=list)

    # 统计
    consistency_score: float = 1.0  # 0-1, 1表示完全一致


class WorldConsistencyChecker:
    """
    世界一致性检查器

    跨章节检测世界设定矛盾。
    """

    def __init__(self):
        # 已知规则库
        self.rules: Dict[str, WorldRule] = {}
        # 已知事实
        self.established_facts: Dict[str, Any] = {}

    def check_consistency(
        self,
        current_chapter: int,
        chapter_content: str,
        story_state: Dict[str, Any]
    ) -> ConsistencyReport:
        """
        检查世界设定一致性

        Args:
            current_chapter: 当前章节号
            chapter_content: 章节正文
            story_state: 故事状态（包含世界设定）

        Returns:
            一致性报告
        """
        # 1. 更新规则库
        self._update_rules(story_state)

        # 2. 提取本章设定相关内容
        chapter_facts = self._extract_facts(chapter_content)

        # 3. 检测矛盾
        inconsistencies = []

        # 检查实力体系矛盾
        power_issues = self._check_power_system(chapter_facts, current_chapter)
        inconsistencies.extend(power_issues)

        # 检查时间线矛盾
        timeline_issues = self._check_timeline(chapter_facts, current_chapter)
        inconsistencies.extend(timeline_issues)

        # 检查地理矛盾
        geography_issues = self._check_geography(chapter_facts, current_chapter)
        inconsistencies.extend(geography_issues)

        # 检查世界法则矛盾
        law_issues = self._check_world_laws(chapter_facts, current_chapter)
        inconsistencies.extend(law_issues)

        # 4. 按严重程度分类
        categorized = self._categorize_by_severity(inconsistencies)

        # 5. 按类型分类
        by_type = self._categorize_by_type(inconsistencies)

        # 6. 计算一致性得分
        consistency_score = self._calculate_consistency_score(inconsistencies)

        # 7. 生成建议
        recommendations = self._generate_recommendations(inconsistencies)

        # 8. 构建报告
        return ConsistencyReport(
            current_chapter=current_chapter,
            total_rules=len(self.rules),
            total_inconsistencies=len(inconsistencies),
            critical_inconsistencies=categorized[InconsistencySeverity.CRITICAL],
            high_inconsistencies=categorized[InconsistencySeverity.HIGH],
            medium_inconsistencies=categorized[InconsistencySeverity.MEDIUM],
            low_inconsistencies=categorized[InconsistencySeverity.LOW],
            by_type=by_type,
            recommendations=recommendations,
            consistency_score=consistency_score,
        )

    def _update_rules(self, story_state: Dict[str, Any]):
        """更新规则库"""
        # 从story_state提取规则
        world_rules = story_state.get("world_rules", [])
        for rule_data in world_rules:
            rule_id = rule_data.get("id", "")
            if rule_id and rule_id not in self.rules:
                self.rules[rule_id] = WorldRule(
                    rule_id=rule_id,
                    rule_type=rule_data.get("type", "unknown"),
                    description=rule_data.get("description", ""),
                    constraints=rule_data.get("constraints", []),
                    examples=rule_data.get("examples", []),
                    established_chapter=rule_data.get("chapter", 0),
                )

    def _extract_facts(self, chapter_content: str) -> Dict[str, Any]:
        """从章节内容提取设定相关事实"""
        facts = {}

        # 简单实现：检测关键词
        # 实际应该使用NLP或LLM提取

        # 实力相关
        power_keywords = ["突破", "境界", "实力", "修为", "等级"]
        facts["has_power_content"] = any(kw in chapter_content for kw in power_keywords)

        # 时间相关
        time_keywords = ["天前", "月前", "年前", "之后", "当时"]
        facts["has_time_reference"] = any(kw in chapter_content for kw in time_keywords)

        # 地理相关
        geography_keywords = ["到达", "距离", "位于", "方位"]
        facts["has_geography"] = any(kw in chapter_content for kw in geography_keywords)

        return facts

    def _check_power_system(
        self,
        chapter_facts: Dict[str, Any],
        current_chapter: int
    ) -> List[Inconsistency]:
        """检查实力体系矛盾"""
        issues = []

        # 简单实现：检查是否有实力体系规则
        if chapter_facts.get("has_power_content"):
            # 检查规则库中是否有实力体系定义
            power_rules = [r for r in self.rules.values() if r.rule_type == "power_system"]

            if not power_rules:
                # 没有明确定义实力体系，但出现了实力相关内容
                issues.append(Inconsistency(
                    inconsistency_id=f"POWER-{current_chapter}",
                    inconsistency_type=InconsistencyType.POWER_LEVEL,
                    severity=InconsistencySeverity.MEDIUM,
                    description="章节中出现实力相关内容，但缺少明确的实力体系定义",
                    chapters=[current_chapter],
                    suggestion="建议在设定中明确实力体系的等级和规则",
                    auto_fixable=False,
                ))

        return issues

    def _check_timeline(
        self,
        chapter_facts: Dict[str, Any],
        current_chapter: int
    ) -> List[Inconsistency]:
        """检查时间线矛盾"""
        issues = []

        # 简化实现
        # 实际应该维护完整的时间线并检测矛盾

        return issues

    def _check_geography(
        self,
        chapter_facts: Dict[str, Any],
        current_chapter: int
    ) -> List[Inconsistency]:
        """检查地理矛盾"""
        issues = []

        # 简化实现
        # 实际应该维护地图信息并检测位置矛盾

        return issues

    def _check_world_laws(
        self,
        chapter_facts: Dict[str, Any],
        current_chapter: int
    ) -> List[Inconsistency]:
        """检查世界法则矛盾"""
        issues = []

        # 简化实现
        # 实际应该检查魔法规则、物理法则等是否一致

        return issues

    def _categorize_by_severity(
        self,
        inconsistencies: List[Inconsistency]
    ) -> Dict[InconsistencySeverity, List[Inconsistency]]:
        """按严重程度分类"""
        categorized = {
            InconsistencySeverity.CRITICAL: [],
            InconsistencySeverity.HIGH: [],
            InconsistencySeverity.MEDIUM: [],
            InconsistencySeverity.LOW: [],
        }

        for inc in inconsistencies:
            categorized[inc.severity].append(inc)

        return categorized

    def _categorize_by_type(
        self,
        inconsistencies: List[Inconsistency]
    ) -> Dict[str, List[Inconsistency]]:
        """按类型分类"""
        by_type: Dict[str, List[Inconsistency]] = {}

        for inc in inconsistencies:
            type_key = inc.inconsistency_type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(inc)

        return by_type

    def _calculate_consistency_score(
        self,
        inconsistencies: List[Inconsistency]
    ) -> float:
        """计算一致性得分"""
        if not inconsistencies:
            return 1.0

        # 根据严重程度计算扣分
        severity_weights = {
            InconsistencySeverity.CRITICAL: 0.2,
            InconsistencySeverity.HIGH: 0.1,
            InconsistencySeverity.MEDIUM: 0.05,
            InconsistencySeverity.LOW: 0.02,
        }

        total_penalty = sum(
            severity_weights.get(inc.severity, 0)
            for inc in inconsistencies
        )

        score = max(0.0, 1.0 - total_penalty)
        return score

    def _generate_recommendations(
        self,
        inconsistencies: List[Inconsistency]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 按严重程度统计
        critical = [inc for inc in inconsistencies if inc.severity == InconsistencySeverity.CRITICAL]
        high = [inc for inc in inconsistencies if inc.severity == InconsistencySeverity.HIGH]

        if critical:
            recommendations.append(
                f"🔴 严重：发现{len(critical)}个严重的设定矛盾，必须立即修正"
            )

        if high:
            recommendations.append(
                f"🟠 高：发现{len(high)}个明显矛盾，建议尽快修正"
            )

        # 按类型统计
        power_issues = [inc for inc in inconsistencies if inc.inconsistency_type == InconsistencyType.POWER_LEVEL]
        if len(power_issues) > 2:
            recommendations.append(
                f"📊 实力体系：检测到多处实力相关矛盾，建议明确实力体系规则"
            )

        return recommendations

    def generate_summary(self, report: ConsistencyReport) -> str:
        """生成可读的一致性摘要"""
        lines = []
        lines.append(f"=== 世界设定一致性报告 (第{report.current_chapter}章) ===")
        lines.append(f"已定义规则: {report.total_rules}条")
        lines.append(f"检测到矛盾: {report.total_inconsistencies}个")
        lines.append(f"一致性得分: {report.consistency_score:.1%}")
        lines.append("")

        # 严重程度分布
        if report.total_inconsistencies > 0:
            lines.append("严重程度分布:")
            if report.critical_inconsistencies:
                lines.append(f"  🔴 严重: {len(report.critical_inconsistencies)}个")
            if report.high_inconsistencies:
                lines.append(f"  🟠 高: {len(report.high_inconsistencies)}个")
            if report.medium_inconsistencies:
                lines.append(f"  🟡 中: {len(report.medium_inconsistencies)}个")
            if report.low_inconsistencies:
                lines.append(f"  🟢 低: {len(report.low_inconsistencies)}个")

        # 建议
        if report.recommendations:
            lines.append("")
            lines.append("建议:")
            for rec in report.recommendations:
                lines.append(f"  {rec}")

        return "\n".join(lines)
