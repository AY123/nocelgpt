from runtime.serialize.run_aggregate import build_run_aggregate
from runtime.serialize.run_aggregate_artifacts import write_run_aggregate


def test_run_aggregate_wire_write(tmp_path):
    rel = write_run_aggregate(
        project_path=tmp_path,
        aggregate_id="RAG-0002",
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="wire",
    )
    assert rel == "registry/derived/run-aggregates/RAG-0002.json"
