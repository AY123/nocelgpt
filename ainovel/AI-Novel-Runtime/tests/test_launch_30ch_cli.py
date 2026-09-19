from runtime.cli import main


def test_30ch_launch_bundle_cli_json(tmp_path):
    code = main([
        "serial", "validation-report",
        "--project", str(tmp_path),
        "--report-id", "missing",
    ])
    assert code == 2
