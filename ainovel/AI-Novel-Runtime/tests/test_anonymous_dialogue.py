from runtime.serialize.anonymous_dialogue import identify_speaker, score_dialogue_against_profile
from runtime.serialize.speech_profile import build_speech_profile


def test_score_dialogue_against_profile_uses_preferred_and_forbidden_patterns():
    profile = build_speech_profile(
        character_id="CHR-0001",
        name="马伦",
        tone="冷静克制",
        sentence_length="短句",
        vocabulary_level="口语化",
        forbidden_patterns=["官话"],
        preferred_patterns=["嗯"],
    )
    assert score_dialogue_against_profile("嗯，行。", profile) > score_dialogue_against_profile("官话套话。", profile)


def test_identify_speaker_prefers_matching_profile():
    profiles = [
        build_speech_profile("CHR-0001", "马伦", "冷静克制", "短句", "口语化", preferred_patterns=["嗯"]),
        build_speech_profile("CHR-0002", "埃德里克", "低声克制", "中短句", "简洁", preferred_patterns=["低声"]),
    ]
    match = identify_speaker("嗯，行。", profiles)
    assert match.speaker_id == "CHR-0001"
    assert match.confidence >= 0
