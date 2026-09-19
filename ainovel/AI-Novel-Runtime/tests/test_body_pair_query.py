from runtime.serialize.body_pair_report import build_body_pair_validation_report
from runtime.serialize.validation_artifacts import write_short_run_validation_report
from runtime.serialize.body_pair_query import list_body_pair_validation_reports, load_body_pair_validation_report
from runtime import derived


def test_body_pair_query_lists_and_loads_reports(tmp_path):
    report = build_body_pair_validation_report(
        before=[("CH-00001", "第一章。")],
        after=[("CH-00001", "第一章 improved。")],
    )
    rel = derived.write_artifact(
        project_path=tmp_path,
        category="body-pair-validation-reports",
        artifact_id="BP-00001",
        artifact=report,
        serialized=__import__("json").dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
    )
    assert rel == "registry/derived/body-pair-validation-reports/BP-00001.json"
    reports = list_body_pair_validation_reports(tmp_path)
    loaded = load_body_pair_validation_report(tmp_path, "BP-00001")

    assert reports and reports[0]["id"] == "BP-00001"
    assert loaded is not None
    assert loaded["kind"] == "body_pair_validation_report"
