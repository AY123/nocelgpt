from runtime.serialize.launch_30ch_run_summary_artifacts import write_30ch_run_summary
from runtime.serialize.launch_30ch_run_summary_query import list_30ch_run_summaries, load_30ch_run_summary


def test_30ch_run_summary_query(tmp_path):
    rel = write_30ch_run_summary(
        project_path=tmp_path,
        summary_id="RSUM-0001",
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="run summary query",
    )
    assert rel == "registry/derived/30ch-run-summaries/RSUM-0001.json"
    summaries = list_30ch_run_summaries(tmp_path)
    loaded = load_30ch_run_summary(tmp_path, "RSUM-0001")
    missing = load_30ch_run_summary(tmp_path, "RSUM-4040")
    assert summaries and summaries[0]["id"] == "RSUM-0001"
    assert loaded is not None
    assert missing is None
    # The run-summary envelope wrapper was consolidated away (8ae2a6f):
    # write_30ch_run_summary now persists the launch summary directly.
    assert loaded["kind"] == "30ch_launch_summary"
