"""
A.3 Genesis 真实性验证

验证 Genesis 是否真正使用了 LLM 生成原创内容，而不是回退到模板。

问题：
- 当前 Genesis 在 LLM 失败时会回退到确定性模板
- 没有明确记录哪些组件是 LLM 生成的，哪些是模板
- "全模板项目"可能被误认为是真正的原创项目

解决方案：
1. 在 Genesis 产物中记录每个组件的生成方式（llm / fallback_template）
2. 禁止全模板项目被当作成功的 Genesis
3. 提供端到端验证工具
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class GenerationMethod(Enum):
    """组件生成方式"""
    LLM = "llm"                      # 真实 LLM 生成
    FALLBACK_TEMPLATE = "fallback_template"  # 回退到模板
    DETERMINISTIC = "deterministic"  # 确定性生成（不需要 LLM）


@dataclass
class ComponentProvenance:
    """组件来源记录"""
    component_name: str         # 组件名称：outline / brain / position / long_arc
    method: GenerationMethod    # 生成方式
    model: Optional[str] = None # 模型标识（如果是 LLM）
    provider: Optional[str] = None  # 提供商（如果是 LLM）
    cost: Optional[float] = None    # 成本（如果有）
    fallback_reason: Optional[str] = None  # 回退原因（如果是 fallback）

    def to_dict(self) -> dict:
        return {
            "component_name": self.component_name,
            "method": self.method.value,
            "model": self.model,
            "provider": self.provider,
            "cost": self.cost,
            "fallback_reason": self.fallback_reason
        }


@dataclass
class GenesisProvenance:
    """Genesis 完整来源记录"""
    components: List[ComponentProvenance] = field(default_factory=list)

    def add_component(self, provenance: ComponentProvenance):
        """添加组件来源"""
        self.components.append(provenance)

    def llm_component_count(self) -> int:
        """LLM 生成的组件数量"""
        return sum(1 for c in self.components if c.method == GenerationMethod.LLM)

    def template_component_count(self) -> int:
        """模板组件数量"""
        return sum(1 for c in self.components if c.method == GenerationMethod.FALLBACK_TEMPLATE)

    def is_all_template(self) -> bool:
        """是否全部是模板（没有真正的 LLM 生成）"""
        # 排除确定性组件（它们本来就不需要 LLM）
        non_deterministic = [c for c in self.components
                            if c.method != GenerationMethod.DETERMINISTIC]

        if not non_deterministic:
            return False  # 如果只有确定性组件，不算"全模板"

        return all(c.method == GenerationMethod.FALLBACK_TEMPLATE
                  for c in non_deterministic)

    def has_critical_llm_component(self) -> bool:
        """是否至少有一个关键 LLM 组件（outline）"""
        # Outline 是最关键的组件，必须有真实 LLM 生成
        outline_components = [c for c in self.components if c.component_name == "outline"]
        return any(c.method == GenerationMethod.LLM for c in outline_components)

    def to_dict(self) -> dict:
        return {
            "components": [c.to_dict() for c in self.components],
            "statistics": {
                "total_components": len(self.components),
                "llm_generated": self.llm_component_count(),
                "template_fallback": self.template_component_count(),
                "is_all_template": self.is_all_template(),
                "has_critical_llm": self.has_critical_llm_component()
            }
        }


@dataclass
class GenesisValidationResult:
    """Genesis 验证结果"""
    valid: bool                 # 是否有效（不是全模板）
    provenance: GenesisProvenance
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "provenance": self.provenance.to_dict(),
            "issues": self.issues,
            "warnings": self.warnings
        }


def validate_genesis_authenticity(provenance: GenesisProvenance) -> GenesisValidationResult:
    """
    验证 Genesis 的真实性

    规则：
    1. 不能全部是模板（必须至少有一个 LLM 组件）
    2. Outline 必须是 LLM 生成的（这是最核心的组件）
    3. Brain/Position/LongArc 可以是确定性生成（它们从 outline fold）

    Args:
        provenance: Genesis 来源记录

    Returns:
        GenesisValidationResult
    """
    issues = []
    warnings = []

    # 检查 1: 不能全部是模板
    if provenance.is_all_template():
        issues.append(
            "All components fell back to templates - not a real LLM genesis. "
            "At least one component (preferably outline) must be LLM-generated."
        )

    # 检查 2: Outline 必须是 LLM 生成的
    if not provenance.has_critical_llm_component():
        issues.append(
            "Outline was not LLM-generated. The outline is the core component "
            "and must be authored by a real LLM, not a template."
        )

    # 检查 3: 如果有多个模板回退，发出警告
    template_count = provenance.template_component_count()
    if template_count > 0 and not provenance.is_all_template():
        template_components = [c.component_name for c in provenance.components
                              if c.method == GenerationMethod.FALLBACK_TEMPLATE]
        warnings.append(
            f"{template_count} component(s) fell back to templates: "
            f"{', '.join(template_components)}. "
            f"Consider re-running with a working LLM connection."
        )

    # 决定是否有效
    valid = len(issues) == 0

    return GenesisValidationResult(
        valid=valid,
        provenance=provenance,
        issues=issues,
        warnings=warnings
    )


def extract_provenance_from_outline_bootstrap(boot_result, model) -> ComponentProvenance:
    """
    从 outline bootstrap 结果提取来源信息

    Args:
        boot_result: OutlineBootstrapResult
        model: 使用的模型（None 表示 deterministic）

    Returns:
        ComponentProvenance
    """
    if model is None:
        # 没有模型 = deterministic 模板
        return ComponentProvenance(
            component_name="outline",
            method=GenerationMethod.FALLBACK_TEMPLATE,
            fallback_reason="model=None (deterministic mode)"
        )

    # 有模型但失败了
    if not boot_result.ok:
        return ComponentProvenance(
            component_name="outline",
            method=GenerationMethod.FALLBACK_TEMPLATE,
            fallback_reason=f"bootstrap failed: {boot_result.message}"
        )

    # 成功使用了 LLM
    provider = getattr(model, "provider", "unknown")
    model_id = getattr(model, "model_id", "unknown")

    return ComponentProvenance(
        component_name="outline",
        method=GenerationMethod.LLM,
        model=model_id,
        provider=provider
    )


def extract_provenance_from_brain(brain_result: dict) -> ComponentProvenance:
    """
    Brain 是从 outline 确定性 fold 的，不需要 LLM

    Returns:
        ComponentProvenance
    """
    return ComponentProvenance(
        component_name="brain",
        method=GenerationMethod.DETERMINISTIC
    )


def extract_provenance_from_position(position_result: dict) -> ComponentProvenance:
    """
    Position 是从 outline 确定性 fold 的，不需要 LLM

    Returns:
        ComponentProvenance
    """
    return ComponentProvenance(
        component_name="position",
        method=GenerationMethod.DETERMINISTIC
    )


def extract_provenance_from_long_arc(long_arc_result: dict) -> ComponentProvenance:
    """
    Long Arc 是从 outline/brain/position 确定性 fold 的，不需要 LLM

    Returns:
        ComponentProvenance
    """
    return ComponentProvenance(
        component_name="long_arc",
        method=GenerationMethod.DETERMINISTIC
    )
