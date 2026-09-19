"""
Production Decision Engine - 统一生产决策逻辑 (P0-1, P0-2)

提供单一的决策引擎，消除 comparison_report, Production Card,
final chapter 之间的决策冲突。

P0-1: Returns canonical ChapterDecision, the single source of truth.
P0-2: 未校准评分只能用于advisory警告，不能触发hold/block。
只有校准后的decision级维度可以gate生产。
"""
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
import json

from .chapter.state_machine import (
    ChapterDecision,
    ChapterState,
    create_approved_decision,
    create_blocked_decision,
    create_held_decision,
)


def load_calibration_status(project_path: Path) -> Dict:
    """加载评审校准状态，返回可信维度列表。

    P0-2: 未校准维度的评分只能用于advisory警告，不能触发hold。
    只有校准后的decision级维度才能gate生产流程。

    Returns:
        {
            "status": "uncalibrated_insufficient_real_samples" | "calibrated" | "unknown",
            "trusted_dimensions": [...],  # 可信维度（向后兼容）
            "decision_dimensions": [...],  # decision级维度（可gate）
            "diagnostic_dimensions": [...] # diagnostic级维度（仅advisory）
        }
    """
    golden_set = project_path / "quality-golden-set"
    summary_path = golden_set / "metadata" / "w9-calibration-summary.json"

    if not summary_path.exists():
        return {
            "status": "unknown",
            "trusted_dimensions": [],
            "decision_dimensions": [],
            "diagnostic_dimensions": []
        }

    try:
        with open(summary_path, encoding="utf-8") as f:
            data = json.load(f)

        grading = data.get("dimension_grading", {})
        return {
            "status": data.get("status", "unknown"),
            "trusted_dimensions": data.get("trusted_dimensions", []),
            "decision_dimensions": grading.get("decision", []),
            "diagnostic_dimensions": grading.get("diagnostic", [])
        }
    except (json.JSONDecodeError, IOError):
        return {
            "status": "unknown",
            "trusted_dimensions": [],
            "decision_dimensions": [],
            "diagnostic_dimensions": []
        }


class ProductionDecisionEngine:
    """
    统一的生产决策引擎 (P0-1)

    按优先级处理所有决策因素，输出单一明确的 ChapterDecision。
    """

    def __init__(self):
        """初始化决策引擎，加载默认阈值"""
        self.priority_order = [
            "hard_redline",
            "critical_contract",
            "promise_overdue",
            "absolute_quality",
            "quality_degradation",
            "reader_dropout",
            "prose_warnings",
            "human_approval",
        ]

    def decide_chapter_state(
        self,
        *,
        # Contract checks
        critical_deviations: int = 0,
        high_deviations: int = 0,
        redline_passed: bool = True,

        # Quality scores
        final_quality_scores: Optional[Dict[str, float]] = None,
        quality_delta: Optional[Dict] = None,

        # Calibration status (P0-2)
        calibration_status: Optional[Dict] = None,

        # Reader simulation
        dropout_risk: Optional[float] = None,
        reader_simulation_degraded: bool = False,

        # Promise delivery
        promises_overdue: Optional[List[str]] = None,

        # Prose checks
        prose_warnings: Optional[List[str]] = None,

        # Human decision
        human_decision: str = "pending",

        # Strict mode
        strict_mode: bool = False,
    ) -> ChapterDecision:
        """
        计算统一的生产决策 (P0-1: returns ChapterDecision)

        Returns:
            ChapterDecision: 包含状态、是否可推进、问题列表等的规范决策
        """
        blocking_issues = []
        warnings = []
        state = ChapterState.REVIEWED  # Default starting state
        advance = True
        human_approval = False

        # Priority 1: Hard redlines (BLOCK)
        if not redline_passed:
            blocking_issues.append("M7 redline check failed")
            return create_blocked_decision(
                reason="M7 redline check failed",
                provenance={
                    "engine": "ProductionDecisionEngine",
                    "version": "P0-1",
                    "blocker": "redline",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Priority 2: Critical contract violations (BLOCK)
        if critical_deviations > 0:
            blocking_issues.append(f"Critical contract deviations: {critical_deviations}")
            return create_blocked_decision(
                reason=f"Critical contract deviations: {critical_deviations}",
                provenance={
                    "engine": "ProductionDecisionEngine",
                    "version": "P0-1",
                    "blocker": "contract_critical",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Priority 3: Strict mode confidence check (BLOCK)
        if strict_mode and final_quality_scores:
            overall_conf = final_quality_scores.get("overall_confidence", 1.0)
            if overall_conf < 0.7:
                blocking_issues.append(f"Low confidence: {overall_conf:.2f} < 0.7")
                return create_blocked_decision(
                    reason=f"Low confidence: {overall_conf:.2f} < 0.7",
                    provenance={
                        "engine": "ProductionDecisionEngine",
                        "version": "P0-1",
                        "blocker": "strict_mode_confidence",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        # Priority 4: High severity contract issues (HOLD)
        if high_deviations > 0:
            warnings.append(f"High severity deviations: {high_deviations}")
            state = ChapterState.HELD
            advance = False
            human_approval = True

        # Priority 5: Promise overdue (HOLD)
        if promises_overdue and state != ChapterState.HELD:
            warnings.append(f"Overdue promises: {', '.join(promises_overdue[:3])}")
            state = ChapterState.HELD
            advance = False
            human_approval = True

        # Priority 6: Absolute quality thresholds (HOLD)
        # P0-2: 只有校准后的decision级维度可以触发hold。
        # 未校准维度仅产生advisory警告，不能gate生产（ADR-003）。
        from .production_card import QUALITY_THRESHOLDS, RISK_THRESHOLDS

        if final_quality_scores and state != ChapterState.HELD:
            # 确定哪些维度是已校准的decision级维度
            decision_dims = []
            if calibration_status:
                decision_dims = calibration_status.get("decision_dimensions", [])
                # 向后兼容：如果没有decision_dimensions，使用trusted_dimensions
                if not decision_dims:
                    decision_dims = calibration_status.get("trusted_dimensions", [])

            # Check positive dimensions (higher is better)
            for dim, min_score in QUALITY_THRESHOLDS.items():
                score = final_quality_scores.get(dim)
                if score is not None and score < min_score:
                    if dim in decision_dims:
                        # 已校准维度：可以触发hold
                        warnings.append(f"{dim} score {score:.0f} below threshold {min_score} (calibrated)")
                        state = ChapterState.HELD
                        advance = False
                        human_approval = True
                        break
                    else:
                        # 未校准维度：仅advisory警告
                        warnings.append(f"{dim} score {score:.0f} below threshold {min_score} (uncalibrated, advisory only)")

            # Check risk dimensions (lower is better)
            if state != ChapterState.HELD:
                for dim, max_score in RISK_THRESHOLDS.items():
                    score = final_quality_scores.get(dim)
                    if score is not None and score > max_score:
                        if dim in decision_dims:
                            # 已校准维度：可以触发hold
                            warnings.append(f"{dim} score {score:.0f} above threshold {max_score} (calibrated)")
                            state = ChapterState.HELD
                            advance = False
                            human_approval = True
                            break
                        else:
                            # 未校准维度：仅advisory警告
                            warnings.append(f"{dim} score {score:.0f} above threshold {max_score} (uncalibrated, advisory only)")

        # Priority 7: Quality degradation (HOLD)
        if quality_delta and state != ChapterState.HELD:
            degraded = False
            for dimension, delta_info in quality_delta.items():
                if isinstance(delta_info, dict) and delta_info.get("delta", 0) < -10:
                    warnings.append(f"{dimension} degraded by {abs(delta_info['delta']):.0f} points")
                    degraded = True

            if degraded:
                state = ChapterState.HELD
                advance = False
                human_approval = True

        # Priority 8: Reader dropout risk (HOLD)
        if not reader_simulation_degraded and dropout_risk and dropout_risk > 0.3 and state != ChapterState.HELD:
            warnings.append(f"High dropout risk: {dropout_risk:.2f}")
            state = ChapterState.HELD
            advance = False
            human_approval = True

        # Priority 9: Prose warnings (advisory only, don't change state)
        if prose_warnings:
            for warning in prose_warnings:
                warnings.append(warning)

        # Priority 10: Human decision rejection (BLOCK)
        if human_decision == "rejected":
            blocking_issues.append("Human decision: rejected")
            return create_blocked_decision(
                reason="Human decision: rejected",
                provenance={
                    "engine": "ProductionDecisionEngine",
                    "version": "P0-1",
                    "blocker": "human_rejection",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # If no issues, approve
        if state == ChapterState.REVIEWED and not blocking_issues and advance:
            state = ChapterState.APPROVED

        # Build canonical decision
        return ChapterDecision(
            state=state,
            advance_to_next=advance,
            blocking_issues=blocking_issues,
            warnings=warnings,
            human_approval_required=human_approval,
            decision_provenance={
                "engine": "ProductionDecisionEngine",
                "version": "P0-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Legacy method for backward compatibility
    def decide(
        self,
        *,
        critical_deviations: int = 0,
        high_deviations: int = 0,
        redline_passed: bool = True,
        final_quality_scores: Optional[Dict[str, float]] = None,
        quality_delta: Optional[Dict] = None,
        calibration_status: Optional[Dict] = None,
        dropout_risk: Optional[float] = None,
        reader_simulation_degraded: bool = False,
        promises_overdue: Optional[List[str]] = None,
        prose_warnings: Optional[List[str]] = None,
        human_decision: str = "pending",
        strict_mode: bool = False,
    ) -> Tuple[str, List[str], List[str]]:
        """
        Legacy method: returns (action, blocking_issues, warnings)

        DEPRECATED: Use decide_chapter_state() instead.
        This method is kept for backward compatibility only.
        """
        decision = self.decide_chapter_state(
            critical_deviations=critical_deviations,
            high_deviations=high_deviations,
            redline_passed=redline_passed,
            final_quality_scores=final_quality_scores,
            quality_delta=quality_delta,
            calibration_status=calibration_status,
            dropout_risk=dropout_risk,
            reader_simulation_degraded=reader_simulation_degraded,
            promises_overdue=promises_overdue,
            prose_warnings=prose_warnings,
            human_decision=human_decision,
            strict_mode=strict_mode,
        )

        # Map ChapterState to legacy action
        if decision.state == ChapterState.BLOCKED:
            action = "block"
        elif decision.state == ChapterState.HELD:
            action = "hold"
        elif decision.state == ChapterState.APPROVED:
            action = "publish"
        else:
            action = "revise"

        return action, decision.blocking_issues, decision.warnings


def align_production_decision(
    production_card_dict: Dict,
    comparison_report: Optional[Dict] = None,
    calibration_status: Optional[Dict] = None,
) -> Dict:
    """
    对齐 Production Card 和 Comparison Report 的决策

    使用 ProductionDecisionEngine 生成统一决策，
    更新两个产物使其一致。

    Args:
        production_card_dict: Production Card 字典
        comparison_report: Comparison Report 字典（可选）
        calibration_status: 校准状态字典（P0-2，可选）

    Returns:
        更新后的 production_card_dict
    """
    engine = ProductionDecisionEngine()

    # Extract decision inputs from Production Card
    action, blocking_issues, warnings = engine.decide(
        critical_deviations=production_card_dict.get("critical_deviations", 0),
        high_deviations=production_card_dict.get("high_deviations", 0),
        redline_passed=production_card_dict.get("redline_passed", True),
        final_quality_scores=production_card_dict.get("final_quality_scores", {}),
        quality_delta=production_card_dict.get("quality_delta", {}),
        calibration_status=calibration_status,
        dropout_risk=production_card_dict.get("dropout_risk"),
        reader_simulation_degraded=(
            production_card_dict.get("reader_simulation", {})
            .get("judge_provenance", {})
            .get("degraded", False)
        ),
        promises_overdue=production_card_dict.get("promises_pending", []),
        strict_mode=production_card_dict.get("strict_mode", False),
    )

    # Update Production Card
    production_card_dict["publish_recommendation"] = action
    production_card_dict["blocking_issues"] = blocking_issues
    production_card_dict["warnings"] = warnings

    # If comparison report exists, align its decision too
    if comparison_report:
        pipeline_decision = comparison_report.get("pipeline_decision", {})
        pipeline_decision["action"] = "advance" if action == "publish" else action
        pipeline_decision["hold_for_human_review"] = (action in ["hold", "block"])
        pipeline_decision["trigger_revision_round"] = (action == "revise")
        pipeline_decision["advance_to_next_chapter"] = (action == "publish")

        comparison_report["pipeline_decision"] = pipeline_decision

    return production_card_dict
