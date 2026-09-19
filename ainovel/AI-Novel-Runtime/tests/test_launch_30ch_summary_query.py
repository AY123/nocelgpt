from runtime.serialize.launch_30ch_summary_artifacts import write_30ch_launch_summary
from runtime.serialize.launch_30ch_summary_query import list_30ch_launch_summaries, load_30ch_launch_summary


def test_30ch_launch_summary_query(tmp_path):
    rel = write_30ch_launch_summary(
        project_path=tmp_path,
        summary_id="SUM-0001",
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="summary query",
    )
    assert rel == "registry/derived/30ch-launch-summaries/SUM-0001.json"
    summaries = list_30ch_launch_summaries(tmp_path)
    loaded = load_30ch_launch_summary(tmp_path, "SUM-0001")
    assert summaries and summaries[0]["id"] == "SUM-0001"
    assert loaded is not None
    assert loaded["kind"] == "30ch_launch_summary"
