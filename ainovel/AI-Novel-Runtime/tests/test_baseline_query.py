from runtime import derived
from runtime.serialize.baseline_artifacts import write_baseline_report
from runtime.serialize.baseline_query import list_baseline_reports, load_baseline_report


def test_baseline_query_lists_and_loads_reports(tmp_path):
    rel = write_baseline_report(
        project_path=tmp_path,
        report_id="BLR-00001",
        chapters=[("CH-00001", "第一章"), ("CH-00002", "第二章"), ("CH-00003", "第三章")],
        reviewers=["reviewer-a", "reviewer-b"],
        notes="baseline query",
    )
    assert rel == "registry/derived/baseline-reports/BLR-00001.json"
    reports = list_baseline_reports(tmp_path)
    loaded = load_baseline_report(tmp_path, "BLR-00001")

    assert reports and reports[0]["id"] == "BLR-00001"
    assert loaded is not None
    assert loaded["kind"] == "baseline_report"
