from __future__ import annotations

from runtime.execution.m7_audit import (
    M7AuditRecord,
    M7AuditTrend,
    M7RegressionSample,
    archive_failed_m7_sample,
    evaluate_m7_samples,
    write_m7_audit_record,
    write_m7_regression_sample,
    write_m7_trend,
)


def test_m7_audit_record_persists(tmp_path):
    record = M7AuditRecord(
        id="M7-AUD-0001",
        chapter_id="CH-1",
        rule_set_id="default",
        risk_level="L3",
        recommendation="block",
        redline_hits=[{"rule": "political-redline", "severity": "hard", "evidence": "政治红线占位符"}],
        similarity={"overall_similarity": 1.0},
        rationale="hard redline",
    )
    rel = write_m7_audit_record(tmp_path, record)
    assert rel.endswith("M7-AUD-0001.json")


def test_m7_regression_sample_persists(tmp_path):
    sample = M7RegressionSample(
        id="M7-SMP-0001",
        sample_type="hard_redline",
        title="红线样本",
        body="政治红线占位符",
        expected_risk_level="L3",
        expected_recommendation="block",
    )
    rel = write_m7_regression_sample(tmp_path, sample)
    assert rel.endswith("M7-SMP-0001.json")


def test_m7_failed_sample_and_trend_persist(tmp_path):
    failed = archive_failed_m7_sample(tmp_path, {
        "sample_id": "M7-SMP-0002",
        "sample_type": "similarity",
        "title": "相似样本",
        "observed": {"risk_level": "L1", "recommendation": "hold"},
        "expected_risk_level": "L3",
        "expected_recommendation": "block",
    })
    trend = write_m7_trend(tmp_path, M7AuditTrend(rule_set_id="default", total=1, passed=0, failed=1, pass_rate=0.0, by_type={"similarity": 1}))
    assert failed.endswith("M7-SMP-0002.json")
    assert trend.endswith("trend-default.json")
