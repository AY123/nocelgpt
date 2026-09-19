"""
Constitution Validator - 商业宪法验证器 (P2-1)

验证章节是否符合作品级商业规则。
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .commercial_constitution import (
    CommercialConstitution,
    Genre,
)


@dataclass
class ConstitutionViolation:
    """宪法违规"""
    type: str                   # "genre_drift" | "selling_point_miss" | "constraint_violation"
    severity: str               # "critical" | "high" | "medium" | "low"
    description: str
    evidence: str               # 证据（文本片段或数据）
    suggestion: str             # 建议修改


@dataclass
class ConstitutionCompliance:
    """宪法合规性报告"""
    is_compliant: bool

    # 各维度得分
    genre_alignment: float      # 题材对齐度 (0-1)
    selling_point_hit: float    # 卖点命中率 (0-1)
    audience_match: float       # 受众匹配度 (0-1)
    constraint_pass: bool       # 约束通过

    # 违规列表
    violations: List[ConstitutionViolation]

    # 总体评分
    overall_score: float        # 0-1


class ConstitutionValidator:
    """
    商业宪法验证器

    对每个章节验证：
    1. 题材是否漂移（genre drift）
    2. 卖点是否命中（selling point hit）
    3. 受众是否匹配（audience match）
    4. 约束是否违反（constraint violation）
    """

    def __init__(self, constitution: CommercialConstitution):
        self.constitution = constitution

    def validate_chapter(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> ConstitutionCompliance:
        """
        验证章节

        Args:
            chapter_content: 章节正文
            chapter_metadata: 章节元数据（包含QA分数、标签等）

        Returns:
            合规性报告
        """
        violations = []

        # 1. 检查题材对齐度
        genre_alignment = self._check_genre_alignment(chapter_content, chapter_metadata)
        if self.constitution.constraints:
            tolerance = self.constitution.constraints.genre_drift_tolerance
            if genre_alignment < (1 - tolerance):
                violations.append(ConstitutionViolation(
                    type="genre_drift",
                    severity="high",
                    description=f"题材偏离过大：对齐度{genre_alignment:.2%}，阈值{(1-tolerance):.2%}",
                    evidence=f"主题材: {self.constitution.primary_genre.value}",
                    suggestion="调整内容，确保核心题材元素明确"
                ))

        # 2. 检查卖点命中率
        selling_point_hit = self._check_selling_points(chapter_content, chapter_metadata)
        if selling_point_hit < 0.5:  # 至少命中50%的卖点
            violations.append(ConstitutionViolation(
                type="selling_point_miss",
                severity="medium",
                description=f"卖点命中不足：{selling_point_hit:.2%}",
                evidence=f"预期卖点: {[sp.name for sp in self.constitution.core_selling_points]}",
                suggestion="增强核心卖点的表现"
            ))

        # 3. 检查受众匹配度
        audience_match = self._check_audience_match(chapter_content, chapter_metadata)

        # 4. 检查约束违反
        constraint_pass = self._check_constraints(chapter_content, chapter_metadata, violations)

        # 计算总体得分
        overall_score = (
            genre_alignment * 0.3 +
            selling_point_hit * 0.3 +
            audience_match * 0.2 +
            (1.0 if constraint_pass else 0.0) * 0.2
        )

        # 判断是否合规
        is_compliant = (
            len([v for v in violations if v.severity in ["critical", "high"]]) == 0 and
            overall_score >= 0.6
        )

        return ConstitutionCompliance(
            is_compliant=is_compliant,
            genre_alignment=genre_alignment,
            selling_point_hit=selling_point_hit,
            audience_match=audience_match,
            constraint_pass=constraint_pass,
            violations=violations,
            overall_score=overall_score,
        )

    def _check_genre_alignment(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> float:
        """
        检查题材对齐度

        简单实现：基于关键词匹配
        """
        # 题材关键词映射
        genre_keywords = {
            Genre.XUANHUAN: ["灵力", "修炼", "法宝", "仙", "魔", "灵气"],
            Genre.XIUZHEN: ["筑基", "金丹", "元婴", "渡劫", "飞升", "道"],
            Genre.DUSHI: ["都市", "公司", "职场", "豪门", "商业", "现代"],
            Genre.KEHUAN: ["科技", "星际", "机甲", "未来", "AI", "宇宙"],
            Genre.LISHI: ["朝廷", "皇帝", "大臣", "兵法", "战争", "历史"],
        }

        primary_keywords = genre_keywords.get(self.constitution.primary_genre, [])
        if not primary_keywords:
            return 1.0  # 无关键词，默认通过

        # 计算关键词命中率
        hits = sum(1 for kw in primary_keywords if kw in chapter_content)
        alignment = min(hits / len(primary_keywords), 1.0)

        return alignment

    def _check_selling_points(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> float:
        """
        检查卖点命中率

        检查核心卖点是否在章节中体现
        """
        if not self.constitution.core_selling_points:
            return 1.0

        hits = 0
        for sp in self.constitution.core_selling_points:
            # 检查关键词
            if any(kw in chapter_content for kw in sp.validation_keywords):
                hits += 1

        return hits / len(self.constitution.core_selling_points)

    def _check_audience_match(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> float:
        """
        检查受众匹配度

        基于内容偏好匹配
        """
        # 简单实现：检查内容偏好关键词
        preferences = self.constitution.primary_audience.content_preference
        if not preferences:
            return 1.0

        # 内容偏好关键词映射
        preference_keywords = {
            "爽文": ["打脸", "反转", "震惊", "嚣张", "装逼"],
            "剧情": ["阴谋", "计划", "布局", "伏笔", "谜团"],
            "升级": ["突破", "晋升", "实力", "境界", "提升"],
            "感情": ["情感", "爱", "恨", "关系", "羁绊"],
        }

        total_hits = 0
        for pref in preferences:
            keywords = preference_keywords.get(pref, [])
            if any(kw in chapter_content for kw in keywords):
                total_hits += 1

        return min(total_hits / len(preferences), 1.0)

    def _check_constraints(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any],
        violations: List[ConstitutionViolation]
    ) -> bool:
        """
        检查约束违反

        Returns:
            True if pass, False if violated
        """
        if not self.constitution.constraints:
            return True

        constraints = self.constitution.constraints
        all_pass = True

        # 1. 检查禁止元素
        for forbidden in constraints.forbidden_elements:
            if forbidden in chapter_content:
                violations.append(ConstitutionViolation(
                    type="constraint_violation",
                    severity="critical",
                    description=f"包含禁止元素: {forbidden}",
                    evidence=f"禁止元素出现在正文中",
                    suggestion=f"移除或替换'{forbidden}'"
                ))
                all_pass = False

        # 2. 检查必需元素
        for required in constraints.required_elements:
            if required not in chapter_content:
                violations.append(ConstitutionViolation(
                    type="constraint_violation",
                    severity="medium",
                    description=f"缺少必需元素: {required}",
                    evidence=f"必需元素未在正文中出现",
                    suggestion=f"添加'{required}'相关内容"
                ))

        # 3. 检查钩子分数
        hook_score = chapter_metadata.get("qa_scores", {}).get("hook", 0)
        if hook_score < constraints.min_hook_score:
            violations.append(ConstitutionViolation(
                type="constraint_violation",
                severity="high",
                description=f"钩子分数过低: {hook_score} < {constraints.min_hook_score}",
                evidence=f"当前钩子分数: {hook_score}",
                suggestion="增强章末钩子，提升悬念"
            ))
            all_pass = False

        return all_pass

    def generate_compliance_summary(self, compliance: ConstitutionCompliance) -> str:
        """生成合规性摘要（人类可读）"""
        lines = []
        lines.append(f"=== 商业宪法合规性报告 ===")
        lines.append(f"总体合规: {'✅ 通过' if compliance.is_compliant else '❌ 不合规'}")
        lines.append(f"总体得分: {compliance.overall_score:.2%}")
        lines.append("")
        lines.append(f"各维度得分:")
        lines.append(f"  题材对齐度: {compliance.genre_alignment:.2%}")
        lines.append(f"  卖点命中率: {compliance.selling_point_hit:.2%}")
        lines.append(f"  受众匹配度: {compliance.audience_match:.2%}")
        lines.append(f"  约束检查: {'✅ 通过' if compliance.constraint_pass else '❌ 违反'}")

        if compliance.violations:
            lines.append("")
            lines.append(f"违规项 ({len(compliance.violations)}):")
            for i, v in enumerate(compliance.violations, 1):
                lines.append(f"  {i}. [{v.severity.upper()}] {v.type}")
                lines.append(f"     {v.description}")
                lines.append(f"     建议: {v.suggestion}")

        return "\n".join(lines)
