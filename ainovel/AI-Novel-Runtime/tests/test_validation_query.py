from pathlib import Path

from runtime.serialize.validation_artifacts import write_short_run_validation_report
from runtime.serialize.validation_query import list_short_run_validation_reports, load_short_run_validation_report


def test_validation_query_lists_and_loads_reports(tmp_path):
    report_id = "SRV-00001"
    rel = write_short_run_validation_report(
        project_path=tmp_path,
        report_id=report_id,
        snapshots=[
            {"chapter_id": "CH-00001", "warning_count": 1, "length": {}, "language": {}},
            {"chapter_id": "CH-00002", "warning_count": 0, "length": {}, "language": {}},
        ],
    )
    assert rel == f"registry/derived/short-run-validation-reports/{report_id}.json"
    reports = list_short_run_validation_reports(tmp_path)
    loaded = load_short_run_validation_report(tmp_path, report_id)

    assert reports and reports[0]["id"] == report_id
    assert loaded is not None
    assert loaded["kind"] == "short_run_validation_report"
