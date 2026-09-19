"""D180-03: 100-chapter long-run execution report and recovery audit.

Builds a run-level report from chapter artifacts, long-run checkpoints, and
baseline summaries. Also exposes a recovery audit scaffold to verify resume
behavior does not duplicate costs or rewrite finals. Advisory-only (ADR-003);
never gates.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RecoveryAudit:
    run_id: str
    interrupted: bool
    resumed: bool
    rewritten_final: bool
    duplicate_cost: bool
    half_written_facts: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongRunExecutionReport:
    kind: str
    version: str
    project_id: str
    chapter_count: int
    checkpoint_count: int
    produced_count: int
    skipped_count: int
    total_cost: float | None
    cost_currency: str | None
    quality_trend: dict[str, Any]
    promise_trend: dict[str, Any]
    recovery_audit: RecoveryAudit
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "chapter_count": self.chapter_count,
            "checkpoint_count": self.checkpoint_count,
            "produced_count": self.produced_count,
            "skipped_count": self.skipped_count,
            "total_cost": self.total_cost,
            "cost_currency": self.cost_currency,
            "quality_trend": self.quality_trend,
            "promise_trend": self.promise_trend,
            "recovery_audit": self.recovery_audit.to_dict(),
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def _window_metrics(chapters: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    quality_warnings = 0
    produced = 0
    skipped = 0
    cost_total = 0.0
    currency = None
    for c in chapters:
        if c.get("ok"):
            produced += 1
        else:
            skipped += 1
        q = c.get("quality") or {}
        if str(q.get("verdict") or "") not in ("", "pass", "ok"):
            quality_warnings += 1
        cost = (c.get("cost") or {}).get("cost")
        if isinstance(cost, dict):
            cost_total += float(cost.get("total_cost", 0) or 0)
            currency = cost.get("currency", currency)
    return {
        "produced": produced,
        "skipped": skipped,
        "quality_warnings": quality_warnings,
        "cost_total": round(cost_total, 6),
        "cost_currency": currency,
    }


def build_long_run_execution_report(
    *,
    project_id: str,
    chapters: Sequence[Mapping[str, Any]],
    checkpoints: Sequence[Mapping[str, Any]] | None = None,
    promise_ledger: Mapping[str, Any] | None = None,
    recovery_audit: Mapping[str, Any] | None = None,
) -> LongRunExecutionReport:
    chapter_count = len(chapters)
    checkpoint_count = len(checkpoints or [])
    window = _window_metrics(chapters)
    quality_trend = {
        "windows": checkpoint_count,
        "quality_warnings": window["quality_warnings"],
        "front_half_produced": sum(1 for c in list(chapters)[: chapter_count // 2] if c.get("ok")),
        "back_half_produced": sum(1 for c in list(chapters)[chapter_count // 2 :] if c.get("ok")),
    }
    promise_trend = {
        "overdue": list((promise_ledger or {}).get("overdue") or []),
        "resolved": list((promise_ledger or {}).get("resolved") or []),
        "pending": list((promise_ledger or {}).get("pending") or []),
        "metadata": (promise_ledger or {}).get("metadata") or {},
    }
    audit = RecoveryAudit(
        run_id=str((recovery_audit or {}).get("run_id") or "RUN-UNKNOWN"),
        interrupted=bool((recovery_audit or {}).get("interrupted", False)),
        resumed=bool((recovery_audit or {}).get("resumed", False)),
        rewritten_final=bool((recovery_audit or {}).get("rewritten_final", False)),
        duplicate_cost=bool((recovery_audit or {}).get("duplicate_cost", False)),
        half_written_facts=bool((recovery_audit or {}).get("half_written_facts", False)),
        notes=str((recovery_audit or {}).get("notes") or ""),
    )
    return LongRunExecutionReport(
        kind="long_run_execution_report",
        version="1.0",
        project_id=project_id,
        chapter_count=chapter_count,
        checkpoint_count=checkpoint_count,
        produced_count=window["produced"],
        skipped_count=window["skipped"],
        total_cost=round(window["cost_total"], 6) if window["cost_total"] else None,
        cost_currency=window["cost_currency"],
        quality_trend=quality_trend,
        promise_trend=promise_trend,
        recovery_audit=audit,
        metadata={"window_metrics": window},
    )


def write_long_run_execution_report(path: str | Path, report: LongRunExecutionReport) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
