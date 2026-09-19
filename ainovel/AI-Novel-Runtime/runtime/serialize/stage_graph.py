"""D180-01: declarative stage graph.

Defines each production stage as a dataclass with explicit inputs, outputs,
recovery keys, budget, and authority. Each stage is independently testable and
resumable. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class StageNode:
    stage_id: str
    name: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    recovery_key: str = ""
    budget_limit: float | None = None
    authority: str = "runtime"
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    resumable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageGraph:
    kind: str
    version: str
    stages: list[StageNode]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "stages": [s.to_dict() for s in self.stages],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_default_stage_graph() -> StageGraph:
    stages = [
        StageNode(
            stage_id="genesis",
            name="开书生成",
            inputs=["reference_sources", "market_snapshot", "genesis_preference"],
            outputs=["outline", "import_plan", "ci_m4_ledger", "promise_ledger", "semantic_ledger"],
            recovery_key="registry/derived/outline/OUTLINE-00001.json",
            budget_limit=5.0,
            authority="runtime",
            description="从参考作品和市场信号生成大纲与导入计划",
        ),
        StageNode(
            stage_id="golden_three",
            name="黄金三章",
            inputs=["outline", "import_plan"],
            outputs=["golden_three_drafts", "golden_three_review"],
            recovery_key="registry/derived/golden-three/",
            budget_limit=10.0,
            authority="runtime",
            depends_on=["genesis"],
            description="生成并评审黄金三章",
        ),
        StageNode(
            stage_id="serial_1_30",
            name="1-30章生产",
            inputs=["outline", "golden_three_drafts"],
            outputs=["chapters_1_30", "checkpoints_10_20_30", "run_manifest"],
            recovery_key="registry/derived/serial-checkpoints/",
            budget_limit=50.0,
            authority="runtime",
            depends_on=["golden_three"],
            description="生产前30章，每10章检查点",
        ),
        StageNode(
            stage_id="gate_30",
            name="30章Gate",
            inputs=["chapters_1_30", "run_manifest", "chapter_evidence_ledger"],
            outputs=["gate_30_verdict", "baseline_report"],
            recovery_key="registry/derived/gate-30-verdict.json",
            budget_limit=2.0,
            authority="human",
            depends_on=["serial_1_30"],
            description="人工审核30章Gate",
        ),
        StageNode(
            stage_id="serial_31_100",
            name="31-100章长跑",
            inputs=["outline", "gate_30_verdict", "long_arc_plan"],
            outputs=["chapters_31_100", "checkpoints_40_50_60_70_80_90_100", "long_run_baseline"],
            recovery_key="registry/derived/serial-checkpoints/",
            budget_limit=200.0,
            authority="runtime",
            depends_on=["gate_30"],
            description="生产31-100章，每10章检查点与恢复",
        ),
        StageNode(
            stage_id="baseline_100",
            name="100章产品基线",
            inputs=["chapters_31_100", "chapters_1_30", "promise_ledger", "chapter_evidence_ledger"],
            outputs=["hundred_chapter_baseline", "release_package"],
            recovery_key="registry/derived/release-package/",
            budget_limit=5.0,
            authority="human",
            depends_on=["serial_31_100"],
            description="汇总100章产品基线与上架包",
        ),
    ]
    return StageGraph(
        kind="stage_graph",
        version="1.0",
        stages=stages,
        metadata={"stage_count": len(stages), "max_budget": sum(s.budget_limit or 0 for s in stages)},
    )
