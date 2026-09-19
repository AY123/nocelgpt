from runtime.serialize.ab_cleaning_report import build_ab_cleaning_report
from runtime.serialize.speech_profile import build_speech_profile


def test_ab_cleaning_report_structure():
    profiles = [
        build_speech_profile("CHR-0001", "马伦", "冷静克制", "短句", "口语化"),
        build_speech_profile("CHR-0002", "埃德里克", "低声克制", "中短句", "简洁"),
    ]
    report = build_ab_cleaning_report(
        before="冷静克制 短句 口语化",
        after="冷静克制 短句 口语化",
        profiles=profiles,
    )

    assert report["kind"] == "ab_cleaning_report"
    assert report["before"]["speaker_id"] == "CHR-0001"
    assert report["after"]["speaker_id"] == "CHR-0001"
    assert "content_hash" in report
