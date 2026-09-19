from runtime.serialize.ab_cleaning_artifacts import write_ab_cleaning_flow
from runtime.serialize.speech_profile import build_speech_profile


def test_write_ab_cleaning_flow(tmp_path):
    profiles = [build_speech_profile("CHR-0001", "马伦", "冷静克制", "短句", "口语化")]
    rel = write_ab_cleaning_flow(
        project_path=tmp_path,
        report_id="AB-00002",
        samples=[("冷静克制", "冷静克制")],
        profiles=profiles,
    )
    assert rel == "registry/derived/ab-cleaning-reports/AB-00002.json"
    assert (tmp_path / rel).exists()
