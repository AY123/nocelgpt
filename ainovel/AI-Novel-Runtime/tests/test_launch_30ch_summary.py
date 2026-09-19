from runtime.serialize.launch_30ch_summary import build_30ch_launch_summary


def test_30ch_launch_summary_structure(tmp_path):
    summary = build_30ch_launch_summary(
        project_path=str(tmp_path),
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="summary",
    )

    assert summary["kind"] == "30ch_launch_summary"
    # The bridge wrapper was consolidated away (8ae2a6f); the summary now folds the
    # launch artifacts directly as bundle/plan/report/link/run.
    assert "bundle" in summary
    for key in ("plan", "report", "link", "run"):
        assert key in summary
    assert "content_hash" in summary
