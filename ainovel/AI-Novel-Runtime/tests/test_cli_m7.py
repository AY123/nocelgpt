from __future__ import annotations

from runtime.cli import main
from runtime.execution.m7_audit import M7RegressionSample, write_m7_regression_sample


def test_cli_m7_audit_lists_samples(tmp_path, capsys):
    write_m7_regression_sample(
        tmp_path,
        M7RegressionSample(
            id="M7-SMP-0001",
            sample_type="hard_redline",
            title="红线样本",
            body="有人企图颠覆国家政权。",
            expected_risk_level="L3",
            expected_recommendation="block",
        ),
    )
    code = main(["m7", "audit", "--project", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "M7-SMP-0001" in out
