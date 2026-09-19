from runtime.serialize.launch_30ch_report import build_30ch_launch_report


def test_30ch_launch_report_structure():
    report = build_30ch_launch_report(
        project_path="/tmp/project",
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        notes="launch report",
    )

    assert report["kind"] == "30ch_launch_report"
    assert report["plan"]["chapter_target"] == 30
    assert report["notes"] == "launch report"
    assert "content_hash" in report
