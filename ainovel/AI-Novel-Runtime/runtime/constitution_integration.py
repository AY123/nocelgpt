"""
Constitution Integration Helper - 宪法集成辅助工具 (P2-1阶段2)

帮助将Constitution验证集成到生成流程中。
"""
from typing import Dict, Any, Optional
from pathlib import Path
from .commercial_constitution import CommercialConstitution
from .constitution_validator import ConstitutionValidator, ConstitutionCompliance


class ConstitutionIntegration:
    """
    宪法集成辅助类

    提供便捷方法将Constitution验证集成到生成流程中。
    """

    def __init__(self, constitution_path: Optional[str] = None):
        """
        初始化

        Args:
            constitution_path: Constitution文件路径（可选）
        """
        self.constitution = None
        self.validator = None

        if constitution_path and Path(constitution_path).exists():
            self.load_constitution(constitution_path)

    def load_constitution(self, filepath: str):
        """加载Constitution"""
        self.constitution = CommercialConstitution.load_from_file(filepath)
        self.validator = ConstitutionValidator(self.constitution)

    def validate_chapter(
        self,
        chapter_content: str,
        chapter_metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        验证章节

        Args:
            chapter_content: 章节正文
            chapter_metadata: 章节元数据（包含QA分数等）

        Returns:
            合规性报告（字典格式），如果没有Constitution则返回None
        """
        if not self.validator:
            return None

        compliance = self.validator.validate_chapter(chapter_content, chapter_metadata)

        # 转换为字典格式（用于Production Card）
        return {
            "is_compliant": compliance.is_compliant,
            "overall_score": compliance.overall_score,
            "genre_alignment": compliance.genre_alignment,
            "selling_point_hit": compliance.selling_point_hit,
            "audience_match": compliance.audience_match,
            "constraint_pass": compliance.constraint_pass,
            "violations": [
                {
                    "type": v.type,
                    "severity": v.severity,
                    "description": v.description,
                    "evidence": v.evidence,
                    "suggestion": v.suggestion,
                }
                for v in compliance.violations
            ],
        }

    def get_decision_impact(self, compliance_dict: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """
        获取宪法合规性对决策的影响

        Args:
            compliance_dict: 合规性报告字典

        Returns:
            (action, reason) 或 (None, None) 如果不影响决策
        """
        if not compliance_dict:
            return None, None

        # 检查critical违规
        critical_violations = [
            v for v in compliance_dict.get("violations", [])
            if v["severity"] == "critical"
        ]

        if critical_violations:
            reasons = [v["description"] for v in critical_violations]
            return "block", f"Critical constitution violations: {'; '.join(reasons)}"

        # 检查high违规
        high_violations = [
            v for v in compliance_dict.get("violations", [])
            if v["severity"] == "high"
        ]

        if high_violations:
            reasons = [v["description"] for v in high_violations]
            return "hold", f"High severity constitution violations: {'; '.join(reasons)}"

        # 检查总体不合规
        if not compliance_dict.get("is_compliant", True):
            return "hold", f"Constitution compliance failed (score: {compliance_dict.get('overall_score', 0):.2%})"

        return None, None

    def generate_summary_message(self, compliance_dict: Dict[str, Any]) -> str:
        """
        生成人类可读的合规性摘要

        Args:
            compliance_dict: 合规性报告字典

        Returns:
            摘要文本
        """
        if not compliance_dict:
            return "No constitution defined"

        lines = []
        lines.append(f"Constitution Compliance: {'✅ PASS' if compliance_dict['is_compliant'] else '❌ FAIL'}")
        lines.append(f"Overall Score: {compliance_dict['overall_score']:.1%}")
        lines.append(f"  Genre: {compliance_dict['genre_alignment']:.1%}")
        lines.append(f"  Selling Points: {compliance_dict['selling_point_hit']:.1%}")
        lines.append(f"  Audience: {compliance_dict['audience_match']:.1%}")
        lines.append(f"  Constraints: {'✅' if compliance_dict['constraint_pass'] else '❌'}")

        violations = compliance_dict.get("violations", [])
        if violations:
            lines.append(f"\nViolations ({len(violations)}):")
            for i, v in enumerate(violations[:3], 1):  # 只显示前3个
                lines.append(f"  {i}. [{v['severity']}] {v['description']}")
            if len(violations) > 3:
                lines.append(f"  ... and {len(violations) - 3} more")

        return "\n".join(lines)


def integrate_constitution_check(
    chapter_content: str,
    chapter_metadata: Dict[str, Any],
    constitution_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：验证章节的宪法合规性

    Args:
        chapter_content: 章节正文
        chapter_metadata: 章节元数据
        constitution_path: Constitution文件路径

    Returns:
        合规性报告字典，如果没有Constitution则返回None
    """
    if not constitution_path:
        return None

    integration = ConstitutionIntegration(constitution_path)
    return integration.validate_chapter(chapter_content, chapter_metadata)
