"""
Production Card: 统一的章节发布质量卡片

用于聚合所有最终稿检查结果，提供统一的发布决策依据。

P0-1: Uses canonical ChapterDecision from decision_engine.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List
from datetime import datetime, timezone


# Quality thresholds for absolute score checks (configurable)
QUALITY_THRESHOLDS = {
    "hook": 75,
    "retention": 75,
    "reward_density": 70,
    "payoff": 70,
    "character_consistency": 80,
    "world_consistency": 80,
    "curiosity": 75,
    "pacing": 72,
}

# Risk dimensions where HIGHER is WORSE (inverse threshold)
RISK_THRESHOLDS = {
    "reader_drop_risk": 30,  # max acceptable
    "originality_risk": 40,  # max acceptable
    "safety_risk": 20,  # max acceptable
}


@dataclass
class ProductionCard:
    """
    章节生产质量卡片

    聚合最终稿的所有质量、契约、商业、原创性检查结果，
    提供统一的发布建议和人工审批接口。
    """

    # 基本信息
    chapter: int
    draft_hash: str
    draft_timestamp: str

    # 契约状态
    contract_status: str  # "pass" | "warning" | "invalid"
    contract_deviations: int = 0
    critical_deviations: int = 0
    high_deviations: int = 0
    medium_deviations: int = 0
    minor_deviations: int = 0

    # 质量评分（最终稿）
    final_quality_scores: Dict[str, float] = field(default_factory=dict)
    initial_quality_scores: Dict[str, float] = field(default_factory=dict)
    quality_delta: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 读者响应（最终稿，可选）
    reader_simulation: Optional[Dict] = None
    dropout_risk: Optional[float] = None
    continuation_rate: Optional[float] = None

    # Promise delivery（Stage B.3）
    promises_delivered: List[str] = field(default_factory=list)
    promises_pending: List[str] = field(default_factory=list)

    # P0-3: Governance Module Reports (Stage B.4)
    governance_reports: Optional[Dict] = None

    # 商业宪法合规性 (P2-1)
    constitution_compliance: Optional[Dict] = None

    # 确定性检查
    prose_checks: Dict = field(default_factory=dict)
    m7_originality: Optional[Dict] = None

    # 发布建议
    publish_recommendation: str = "recommend"  # "recommend" | "hold" | "block"
    redline_passed: bool = True
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # P0-1: Canonical decision (optional, NEW)
    canonical_decision: Optional[Dict] = None  # ChapterDecision.to_dict()

    # 人工决策
    human_decision: str = "pending"  # "pending" | "approved" | "rejected"
    human_decision_by: Optional[str] = None
    human_decision_at: Optional[str] = None
    human_decision_notes: Optional[str] = None

    # 审计
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    review_model: Optional[str] = None
    strict_mode: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProductionCard':
        """从字典创建"""
        return cls(**data)

    def compute_recommendation(self, project_path: Optional[str] = None) -> str:
        """
        计算发布建议 (P0-1: deprecated, use canonical_decision instead)

        P0-1: If canonical_decision is present, use it as source of truth.
        Otherwise, fall back to legacy computation.

        Args:
            project_path: 项目路径，用于加载校准状态（可选）

        Returns:
            "recommend" | "hold" | "block"
        """
        # P0-1: If canonical decision exists, derive from it
        if self.canonical_decision:
            state = self.canonical_decision.get("state")
            if state == "blocked":
                return "block"
            elif state == "held":
                return "hold"
            elif state in ("approved", "finalized"):
                return "recommend"
            else:
                return "hold"  # Conservative default

        # Legacy path: use decision engine
        from .decision_engine import ProductionDecisionEngine, load_calibration_status
        from pathlib import Path

        engine = ProductionDecisionEngine()

        # P0-2: 加载校准状态
        calibration_status = None
        if project_path:
            calibration_status = load_calibration_status(Path(project_path))

        # Check if reader simulation was degraded
        judge_prov = self.reader_simulation.get("judge_provenance", {}) if self.reader_simulation else {}
        is_degraded = judge_prov.get("degraded", False) if isinstance(judge_prov, dict) else False

        action, blocking_issues, warnings = engine.decide(
            critical_deviations=self.critical_deviations,
            high_deviations=self.high_deviations,
            redline_passed=self.redline_passed,
            final_quality_scores=self.final_quality_scores,
            quality_delta=self.quality_delta,
            calibration_status=calibration_status,
            dropout_risk=self.dropout_risk,
            reader_simulation_degraded=is_degraded,
            promises_overdue=self.promises_pending or [],
            strict_mode=self.strict_mode,
        )

        # Update internal state
        self.blocking_issues = blocking_issues
        self.warnings = warnings

        # Map action to recommendation
        if action == "publish":
            return "recommend"
        elif action == "block":
            return "block"
        else:  # hold or revise
            return "hold"

    def add_warning(self, message: str):
        """添加警告"""
        if message not in self.warnings:
            self.warnings.append(message)

    def add_blocking_issue(self, message: str):
        """添加阻断问题"""
        if message not in self.blocking_issues:
            self.blocking_issues.append(message)

    def approve(self, by: str, notes: Optional[str] = None):
        """人工批准"""
        self.human_decision = "approved"
        self.human_decision_by = by
        self.human_decision_at = datetime.now(timezone.utc).isoformat()
        self.human_decision_notes = notes

    def reject(self, by: str, notes: Optional[str] = None):
        """人工拒绝"""
        self.human_decision = "rejected"
        self.human_decision_by = by
        self.human_decision_at = datetime.now(timezone.utc).isoformat()
        self.human_decision_notes = notes

    def summary(self) -> str:
        """生成简要总结"""
        lines = [
            f"Production Card - Chapter {self.chapter}",
            f"Draft: {self.draft_hash[:8]}",
            f"Contract: {self.contract_status}",
            f"Deviations: {self.contract_deviations} (Critical: {self.critical_deviations}, High: {self.high_deviations})",
        ]

        if self.final_quality_scores:
            lines.append(f"Quality: {self._format_scores(self.final_quality_scores)}")

        if self.dropout_risk is not None:
            lines.append(f"Dropout Risk: {self.dropout_risk:.2%}")

        lines.append(f"Recommendation: {self.publish_recommendation}")

        if self.blocking_issues:
            lines.append(f"Blocking: {', '.join(self.blocking_issues)}")

        if self.warnings:
            lines.append(f"Warnings: {', '.join(self.warnings)}")

        lines.append(f"Decision: {self.human_decision}")

        return "\n".join(lines)

    def _format_scores(self, scores: Dict[str, float]) -> str:
        """格式化评分"""
        if not scores:
            return "N/A"

        key_dimensions = ["character_consistency", "world_consistency", "pacing", "retention"]
        parts = []
        for dim in key_dimensions:
            if dim in scores:
                parts.append(f"{dim[:4]}={scores[dim]:.0f}")

        return ", ".join(parts) if parts else "N/A"
