from runtime import derived
from runtime.serialize.winner_drift_artifacts import write_winner_drift_report
from runtime.serialize.winner_drift_query import list_winner_drift_reports, load_winner_drift_report


def test_winner_drift_query_lists_and_loads_reports(tmp_path):
    rel = write_winner_drift_report(
        project_path=tmp_path,
        report_id="WDR-00001",
        scored_hash="abc",
        written_hash="xyz",
        scored_id="cand-1",
        written_id="cand-1",
        evidence_ref="registry/derived/version-comparison/cmp.json",
        notes="winner drift check",
    )
    assert rel == "registry/derived/winner-drift-reports/WDR-00001.json"
    reports = list_winner_drift_reports(tmp_path)
    loaded = load_winner_drift_report(tmp_path, "WDR-00001")

    assert reports and reports[0]["id"] == "WDR-00001"
    assert loaded is not None
    assert loaded["kind"] == "winner_drift_report"
