from runtime import derived
from runtime.serialize.ab_cleaning_flow import build_ab_cleaning_flow
from runtime.serialize.ab_cleaning_query import list_ab_cleaning_reports, load_ab_cleaning_report
from runtime.serialize.speech_profile import build_speech_profile


def test_ab_cleaning_query_lists_and_loads_reports(tmp_path):
    profiles = [
        build_speech_profile("CHR-0001", "马伦", "冷静克制", "短句", "口语化"),
        build_speech_profile("CHR-0002", "埃德里克", "低声克制", "中短句", "简洁"),
    ]
    flow = build_ab_cleaning_flow(
        samples=[("冷静克制 短句 口语化", "冷静克制 短句 口语化")],
        profiles=profiles,
    )
    rel = derived.write_artifact(
        project_path=tmp_path,
        category="ab-cleaning-reports",
        artifact_id="AB-00001",
        artifact=flow,
        serialized=__import__("json").dumps(flow, ensure_ascii=False, sort_keys=True, indent=2),
    )
    assert rel == "registry/derived/ab-cleaning-reports/AB-00001.json"
    reports = list_ab_cleaning_reports(tmp_path)
    loaded = load_ab_cleaning_report(tmp_path, "AB-00001")

    assert reports and reports[0]["id"] == "AB-00001"
    assert loaded is not None
    assert loaded["kind"] == "ab_cleaning_flow"
