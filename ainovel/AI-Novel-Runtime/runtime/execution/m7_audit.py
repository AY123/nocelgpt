from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

import json

from .. import derived

M7_AUDIT_CATEGORY = "m7-audit"
M7_REGRESSION_CATEGORY = "m7-regression"
M7_FAILED_CATEGORY = "m7-regression-failed"
M7_TREND_CATEGORY = "m7-trend"


@dataclass(frozen=True)
class M7AuditRecord:
    id: str
    chapter_id: str
    rule_set_id: str
    risk_level: str
    recommendation: str
    redline_hits: list[dict] = field(default_factory=list)
    similarity: dict = field(default_factory=dict)
    rationale: str = ""
    source_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "m7_audit_record",
            "id": self.id,
            "chapter_id": self.chapter_id,
            "rule_set_id": self.rule_set_id,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
            "redline_hits": self.redline_hits,
            "similarity": self.similarity,
            "rationale": self.rationale,
            "provenance": {"derived_from": [], "source_version": self.source_version},
        }


@dataclass(frozen=True)
class M7RegressionSample:
    id: str
    sample_type: str
    title: str
    body: str
    references: list[dict[str, Any]] = field(default_factory=list)
    expected_risk_level: str = ""
    expected_recommendation: str = ""
    rule_set_id: str = "default"
    notes: str = ""
    source_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "m7_regression_sample",
            "id": self.id,
            "sample_type": self.sample_type,
            "title": self.title,
            "body": self.body,
            "references": self.references,
            "expected_risk_level": self.expected_risk_level,
            "expected_recommendation": self.expected_recommendation,
            "rule_set_id": self.rule_set_id,
            "notes": self.notes,
            "provenance": {"derived_from": [], "source_version": self.source_version},
        }


@dataclass(frozen=True)
class M7AuditTrend:
    rule_set_id: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "m7_audit_trend",
            "rule_set_id": self.rule_set_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "by_type": self.by_type,
        }


def write_m7_audit_record(project_path: str | Path, record: M7AuditRecord) -> str:
    payload = record.to_dict()
    return derived.write_artifact(
        project_path=project_path,
        category=M7_AUDIT_CATEGORY,
        artifact_id=record.id,
        artifact=payload,
        serialized=json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
    )


def write_m7_regression_sample(project_path: str | Path, sample: M7RegressionSample) -> str:
    payload = sample.to_dict()
    return derived.write_artifact(
        project_path=project_path,
        category=M7_REGRESSION_CATEGORY,
        artifact_id=sample.id,
        artifact=payload,
        serialized=json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
    )


def archive_failed_m7_sample(project_path: str | Path, result: dict[str, Any]) -> str:
    sample_id = str(result.get("sample_id", "M7-FAILED"))
    payload = {
        "kind": "m7_failed_sample",
        "sample_id": sample_id,
        "sample_type": result.get("sample_type", ""),
        "title": result.get("title", ""),
        "observed": result.get("observed", {}),
        "expected_risk_level": result.get("expected_risk_level", ""),
        "expected_recommendation": result.get("expected_recommendation", ""),
        "notes": result.get("notes", ""),
        "provenance": {"derived_from": [], "source_version": 1},
    }
    return derived.write_artifact(
        project_path=project_path,
        category=M7_FAILED_CATEGORY,
        artifact_id=sample_id,
        artifact=payload,
        serialized=json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
    )


def write_m7_trend(project_path: str | Path, trend: M7AuditTrend) -> str:
    payload = trend.to_dict()
    return derived.write_artifact(
        project_path=project_path,
        category=M7_TREND_CATEGORY,
        artifact_id=f"trend-{trend.rule_set_id}",
        artifact=payload,
        serialized=json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
    )


def load_m7_regression_samples(project_path: str | Path) -> list[dict[str, Any]]:
    index = derived._load_index(project_path)
    samples = []
    for entry in index.get("artifacts", []):
        if entry.get("category") != M7_REGRESSION_CATEGORY:
            continue
        path = Path(project_path) / entry.get("path", "")
        try:
            samples.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return samples


def evaluate_m7_regression(project_path: str | Path, runner) -> list[dict[str, Any]]:
    # No Registry is needed: this is a pure fold over the persisted regression
    # samples through the caller's runner. (It previously took an unused `reg`
    # param, which forced evaluate_m7_samples to construct Registry() with no
    # args and crash — Registry needs project_path/version/standard_pin.)
    results = []
    for sample in load_m7_regression_samples(project_path):
        observed = runner(sample)
        expected_risk = sample.get("expected_risk_level", "")
        expected_rec = sample.get("expected_recommendation", "")
        observed_risk = observed.get("risk_level", "") if isinstance(observed, dict) else ""
        observed_rec = observed.get("recommendation", "") if isinstance(observed, dict) else ""
        results.append({
            "sample_id": sample.get("id", ""),
            "sample_type": sample.get("sample_type", ""),
            "title": sample.get("title", ""),
            "observed": observed,
            "expected_risk_level": expected_risk,
            "expected_recommendation": expected_rec,
            "matches": observed_risk == expected_risk and observed_rec == expected_rec,
        })
    return results


def evaluate_m7_samples(project_path: str | Path, runner, *, rule_set_id: str = "default") -> dict[str, Any]:
    results = evaluate_m7_regression(project_path, runner)
    total = len(results)
    passed = sum(1 for r in results if r.get("matches"))
    failed = [r for r in results if not r.get("matches")]
    by_type: dict[str, int] = {}
    for r in results:
        by_type[r["sample_type"]] = by_type.get(r["sample_type"], 0) + 1
    trend = M7AuditTrend(
        rule_set_id=rule_set_id,
        total=total,
        passed=passed,
        failed=len(failed),
        pass_rate=(passed / total) if total else 1.0,
        by_type=dict(sorted(by_type.items())),
    )
    return {
        "total": total,
        "passed": passed,
        "failed": len(failed),
        "pass_rate": trend.pass_rate,
        "by_type": trend.by_type,
        "results": results,
        "failed_samples": failed,
        "trend": trend.to_dict(),
    }


def summarize_m7_regression(project_path: str | Path, runner) -> dict[str, Any]:
    return evaluate_m7_samples(project_path, runner)
