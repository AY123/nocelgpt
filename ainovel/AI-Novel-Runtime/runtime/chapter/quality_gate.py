"""
A.2 质量门控 - Final Draft Quality Gate

在章节最终写入前执行综合质量检查，将高风险问题纳入门控。
这是 Phase A.2 的核心：不只检查 draft 生成，而是检查最终成品。

设计原则（ADR-003）:
- 确定性红线（deterministic）：可以阻断（gating=True）
- 评估性判断（evaluative）：只能建议，不能阻断（gating=False）
- 本模块只实现确定性门控，评估性信号已在 loop.py 中收集

检查维度：
1. 文本完整性（integrity）- 已有，确定性，可阻断
2. 承诺债务（promise_debt）- 新增，确定性阈值，可建议人工审批
3. 跨章连续性（continuity）- 新增，确定性检查，可建议人工审批
4. 长度失控（length）- 已有，评估性，只警告
5. AI味道（ai_taste）- 已有，评估性，只警告

输出：
- FinalQualityGateResult: 包含是否通过、阻断原因、警告列表
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class GateSeverity(Enum):
    """门控严重程度"""
    BLOCK = "block"        # 硬阻断（确定性红线）
    HOLD = "hold"          # 需要人工审批
    WARN = "warn"          # 警告，但不阻断
    INFO = "info"          # 信息性提示


@dataclass
class GateIssue:
    """质量门控问题"""
    dimension: str            # 维度：integrity / promise_debt / continuity / length / ai_taste
    severity: GateSeverity    # 严重程度
    message: str              # 描述
    detail: Optional[Dict[str, Any]] = None  # 详细数据

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "severity": self.severity.value,
            "message": self.message,
            "detail": self.detail
        }


@dataclass
class FinalQualityGateResult:
    """最终质量门控结果"""
    passed: bool              # 是否通过（无阻断）
    blocked: bool             # 是否被硬阻断
    requires_approval: bool   # 是否需要人工审批

    issues: List[GateIssue] = field(default_factory=list)

    # 统计
    block_count: int = 0
    hold_count: int = 0
    warn_count: int = 0

    # 建议
    recommendation: str = "proceed"  # proceed / hold_for_review / block

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "requires_approval": self.requires_approval,
            "issues": [issue.to_dict() for issue in self.issues],
            "block_count": self.block_count,
            "hold_count": self.hold_count,
            "warn_count": self.warn_count,
            "recommendation": self.recommendation
        }


def assess_final_quality_gate(
    *,
    chapter_index: int,
    chapter_draft: dict,
    chapter_run: Any,  # ChapterRun from loop.py
    story_state: Optional[Any] = None,
    promise_ledger: Optional[Dict] = None,
    previous_chapters: Optional[List[dict]] = None,
) -> FinalQualityGateResult:
    """
    评估最终草稿的质量门控

    在 loop.py 的 result.chapters.append(ChapterRun(...)) 之前调用。

    Args:
        chapter_index: 章节索引
        chapter_draft: 最终草稿（经过 revision/commercial/hygiene）
        chapter_run: ChapterRun 对象（包含所有检查结果）
        story_state: 故事状态（用于连续性检查）
        promise_ledger: 承诺账本（用于债务检查）
        previous_chapters: 前面的章节（用于连续性检查）

    Returns:
        FinalQualityGateResult
    """

    issues: List[GateIssue] = []

    # ===================================================================
    # 1. 文本完整性 - 硬阻断（确定性红线）
    # ===================================================================
    integrity = chapter_run.integrity
    if integrity and integrity.get("status") == "fail":
        issues.append(GateIssue(
            dimension="integrity",
            severity=GateSeverity.BLOCK,
            message=f"文本完整性检查失败: {', '.join(integrity.get('reason_codes', []))}",
            detail=integrity
        ))

    # ===================================================================
    # 2. 承诺债务 - 超过阈值需要审批（确定性阈值）
    # ===================================================================
    if promise_ledger:
        # 计算当前章节的承诺债务
        pending_promises = []
        for promise_id, promise in promise_ledger.items():
            if isinstance(promise, dict):
                created_ch = promise.get("created_chapter", 0)
                status = promise.get("status", "pending")

                if status == "pending" and created_ch < chapter_index:
                    chapters_pending = chapter_index - created_ch
                    pending_promises.append({
                        "promise_id": promise_id,
                        "chapters_pending": chapters_pending,
                        "created_chapter": created_ch,
                        "description": promise.get("description", "")
                    })

        # 检查是否有严重逾期的承诺
        critical_debts = [p for p in pending_promises if p["chapters_pending"] > 20]
        high_debts = [p for p in pending_promises if 15 <= p["chapters_pending"] <= 20]

        if critical_debts:
            issues.append(GateIssue(
                dimension="promise_debt",
                severity=GateSeverity.HOLD,
                message=f"{len(critical_debts)} 个承诺严重逾期（>20章未兑现）",
                detail={
                    "critical_count": len(critical_debts),
                    "critical_promises": critical_debts[:3],  # 只显示前3个
                    "total_pending": len(pending_promises)
                }
            ))
        elif high_debts:
            issues.append(GateIssue(
                dimension="promise_debt",
                severity=GateSeverity.WARN,
                message=f"{len(high_debts)} 个承诺高度紧急（15-20章未兑现）",
                detail={
                    "high_count": len(high_debts),
                    "high_promises": high_debts[:3],
                    "total_pending": len(pending_promises)
                }
            ))

    # ===================================================================
    # 3. 跨章连续性 - 检测高风险断裂（确定性检查）
    # ===================================================================
    if previous_chapters and len(previous_chapters) > 0:
        # 简单的连续性检查：检测时间/地点/人物的突变
        # 更完整的实现需要从 story_state 中提取时间线/人物位置等

        # 这里是一个简化的示例：检查章节长度的突变
        current_length = len(chapter_draft.get("body", ""))
        prev_length = len(previous_chapters[-1].get("body", "")) if previous_chapters else 0

        if prev_length > 0:
            length_ratio = current_length / prev_length

            # 长度突变超过3倍可能是连续性问题
            if length_ratio > 3.0 or length_ratio < 0.33:
                issues.append(GateIssue(
                    dimension="continuity",
                    severity=GateSeverity.WARN,
                    message=f"章节长度突变：当前{current_length}字，前章{prev_length}字（{length_ratio:.2f}x）",
                    detail={
                        "current_length": current_length,
                        "previous_length": prev_length,
                        "ratio": round(length_ratio, 2)
                    }
                ))

    # ===================================================================
    # 4. 长度失控 - 评估性，只警告（已在 loop.py 中检查）
    # ===================================================================
    length = chapter_run.length
    if length and isinstance(length, dict):
        findings = length.get("findings", [])
        for finding in findings:
            if isinstance(finding, dict):
                severity_str = finding.get("severity", "info")
                if severity_str in ("warning", "error"):
                    issues.append(GateIssue(
                        dimension="length",
                        severity=GateSeverity.WARN,
                        message=finding.get("message", "长度超出目标范围"),
                        detail=length
                    ))
                    break  # 只添加一次

    # ===================================================================
    # 5. AI味道 - 评估性，只警告（已在 loop.py 中检查）
    # ===================================================================
    ai_taste = chapter_run.ai_taste
    if ai_taste and isinstance(ai_taste, dict):
        findings = ai_taste.get("findings", [])
        warning_findings = [f for f in findings
                           if isinstance(f, dict) and f.get("severity") in ("warning", "error")]

        if len(warning_findings) >= 3:  # 3个或以上警告才提示
            issues.append(GateIssue(
                dimension="ai_taste",
                severity=GateSeverity.WARN,
                message=f"AI味道检测到 {len(warning_findings)} 个问题",
                detail={"warning_count": len(warning_findings), "findings": warning_findings[:3]}
            ))

    # ===================================================================
    # 汇总结果
    # ===================================================================
    block_issues = [i for i in issues if i.severity == GateSeverity.BLOCK]
    hold_issues = [i for i in issues if i.severity == GateSeverity.HOLD]
    warn_issues = [i for i in issues if i.severity == GateSeverity.WARN]

    blocked = len(block_issues) > 0
    requires_approval = len(hold_issues) > 0
    passed = not blocked  # 只要没有硬阻断就算通过

    # 决定建议
    if blocked:
        recommendation = "block"
    elif requires_approval:
        recommendation = "hold_for_review"
    else:
        recommendation = "proceed"

    return FinalQualityGateResult(
        passed=passed,
        blocked=blocked,
        requires_approval=requires_approval,
        issues=issues,
        block_count=len(block_issues),
        hold_count=len(hold_issues),
        warn_count=len(warn_issues),
        recommendation=recommendation
    )
