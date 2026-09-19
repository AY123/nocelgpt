from runtime.serialize.ab_cleaning_flow import build_ab_cleaning_flow
from runtime.serialize.speech_profile import build_speech_profile


def test_ab_cleaning_flow_summary():
    profiles = [
        build_speech_profile("CHR-0001", "马伦", "冷静克制", "短句", "口语化"),
        build_speech_profile("CHR-0002", "埃德里克", "低声克制", "中短句", "简洁"),
    ]
    flow = build_ab_cleaning_flow(
        samples=[
            ("冷静克制 短句 口语化", "冷静克制 短句 口语化"),
            ("低声克制 中短句 简洁", "低声克制 中短句 简洁"),
        ],
        profiles=profiles,
    )

    assert flow["kind"] == "ab_cleaning_flow"
    assert flow["sample_count"] == 2
    assert len(flow["reports"]) == 2
