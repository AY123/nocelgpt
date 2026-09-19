from runtime.cli import main


def test_run_aggregate_cli_missing(tmp_path):
    code = main([
        "serial", "run-summary",
        "--project", str(tmp_path),
        "--summary-id", "missing",
    ])
    assert code == 2
