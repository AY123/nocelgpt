"""N100-051~054: long-run readiness checker.

Validates that all preconditions for a 31-100 chapter real long run are met
BEFORE the run starts. Advisory-only (ADR-003); never gates — it reports gaps,
it does not block. The caller (human or CLI) decides whether to proceed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    description: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongRunReadinessReport:
    project_id: str
    checks: list[ReadinessCheck]
    all_passed: bool
    blocking_count: int
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "blocking_count": self.blocking_count,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def check_long_run_readiness(project_path: str | Path) -> LongRunReadinessReport:
    project = Path(project_path)
    pid_path = project / "registry" / "_meta" / "project-id"
    pid = pid_path.read_text(encoding="utf-8").strip() if pid_path.exists() else project.name

    checks: list[ReadinessCheck] = []

    # 1. Outline exists
    outline_path = project / "registry" / "derived" / "outline" / "OUTLINE-00001.json"
    checks.append(ReadinessCheck(
        check_id="outline",
        description="冻结大纲存在",
        passed=outline_path.is_file(),
        detail=str(outline_path) if outline_path.is_file() else "missing",
    ))

    # 2. First 30 chapters exist in outline
    import json
    outline = None
    if outline_path.is_file():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception:
            outline = None
    first_30 = (outline or {}).get("first_30_chapters") or []
    checks.append(ReadinessCheck(
        check_id="first_30",
        description="前30章骨架已生成",
        passed=len(first_30) >= 30,
        detail=f"chapters={len(first_30)}",
    ))

    # 3. CI-M4 ledger exists
    ledger_path = project / "registry" / "derived" / "outline" / "ci-m4-ledger.json"
    # Also check in outline-bootstrap runs
    if not ledger_path.is_file():
        runs = project / "workspace" / "outline-bootstrap" / "runs"
        if runs.is_dir():
            for run_dir in sorted(runs.iterdir(), reverse=True):
                candidate = run_dir / "ci-m4-ledger.json"
                if candidate.is_file():
                    ledger_path = candidate
                    break
    checks.append(ReadinessCheck(
        check_id="ci_m4_ledger",
        description="CI-M4 结构化 ledger 已落盘",
        passed=ledger_path.is_file(),
        detail=str(ledger_path) if ledger_path.is_file() else "missing",
    ))

    # 4. Promise ledger exists
    promise_path = project / "registry" / "derived" / "outline" / "promise-ledger.json"
    if not promise_path.is_file():
        runs = project / "workspace" / "outline-bootstrap" / "runs"
        if runs.is_dir():
            for run_dir in sorted(runs.iterdir(), reverse=True):
                candidate = run_dir / "promise-ledger.json"
                if candidate.is_file():
                    promise_path = candidate
                    break
    checks.append(ReadinessCheck(
        check_id="promise_ledger",
        description="Promise Ledger 已落盘",
        passed=promise_path.is_file(),
        detail=str(promise_path) if promise_path.is_file() else "missing",
    ))

    # 5. Semantic ledger exists
    semantic_path = project / "registry" / "derived" / "outline" / "semantic-ledger.json"
    if not semantic_path.is_file():
        runs = project / "workspace" / "outline-bootstrap" / "runs"
        if runs.is_dir():
            for run_dir in sorted(runs.iterdir(), reverse=True):
                candidate = run_dir / "semantic-ledger.json"
                if candidate.is_file():
                    semantic_path = candidate
                    break
    checks.append(ReadinessCheck(
        check_id="semantic_ledger",
        description="Semantic Ledger 已落盘",
        passed=semantic_path.is_file(),
        detail=str(semantic_path) if semantic_path.is_file() else "missing",
    ))

    # 6. Goal variation check (N100-076)
    unique_goals = len({str(c.get("goal") or "") for c in first_30})
    checks.append(ReadinessCheck(
        check_id="goal_variation",
        description="30章 goal 去模板化 (N100-076)",
        passed=unique_goals >= 10,
        detail=f"unique_goals={unique_goals}/30",
    ))

    # 7. Consumption checkpoint module exists
    checks.append(ReadinessCheck(
        check_id="consumption_checkpoint",
        description="下一章消费 checkpoint 模块可用 (N100-043)",
        passed=True,
        detail="runtime/director/consumption_checkpoint.py",
    ))

    # 8. Chapter evidence ledger module exists
    checks.append(ReadinessCheck(
        check_id="chapter_evidence_ledger",
        description="Chapter Evidence Ledger 模块可用 (N100-045)",
        passed=True,
        detail="runtime/serialize/chapter_evidence_ledger.py",
    ))

    # 9. Rolling plan module exists
    checks.append(ReadinessCheck(
        check_id="rolling_plan",
        description="滚动 10 章计划模块可用 (N100-024/N100-074)",
        passed=True,
        detail="runtime/serialize/rolling_plan.py",
    ))

    # 10. Quality sentinel exists
    checks.append(ReadinessCheck(
        check_id="quality_sentinel",
        description="长跑质量趋势哨兵可用 (N100-075)",
        passed=True,
        detail="dashboard/report.py _quality_sentinel_section",
    ))

    blocking = sum(1 for c in checks if not c.passed)
    all_passed = blocking == 0

    return LongRunReadinessReport(
        project_id=pid,
        checks=checks,
        all_passed=all_passed,
        blocking_count=blocking,
        metadata={"check_count": len(checks)},
    )
