from runtime.serialize.speech_profile import build_speech_profile, coerce_speech_profile, merge_speech_profiles, render_speech_profiles


def test_build_speech_profile_shapes():
    profile = build_speech_profile(
        character_id="CHR-0001",
        name="马伦",
        tone="冷静克制",
        sentence_length="短句",
        vocabulary_level="口语化",
        forbidden_patterns=["官话", "模板句"],
        preferred_patterns=["嗯", "行"],
    )

    assert profile.character_id == "CHR-0001"
    assert profile.name == "马伦"
    assert profile.tone == "冷静克制"
    assert profile.sentence_length == "短句"
    assert profile.vocabulary_level == "口语化"
    assert profile.forbidden_patterns == ("官话", "模板句")
    assert profile.preferred_patterns == ("嗯", "行")


def test_render_speech_profiles_contains_constraints():
    text = render_speech_profiles([
        build_speech_profile(
            character_id="CHR-0001",
            name="马伦",
            tone="冷静克制",
            sentence_length="短句",
            vocabulary_level="口语化",
            forbidden_patterns=["官话"],
            preferred_patterns=["嗯"],
        ),
        build_speech_profile(
            character_id="CHR-0002",
            name="埃德里克",
            tone="低声克制",
            sentence_length="中短句",
            vocabulary_level="简洁",
        ),
    ])

    assert "角色语音约束" in text
    assert "马伦" in text
    assert "埃德里克" in text
    assert "官话" in text
    assert "偏好" in text


def test_merge_speech_profiles():
    merged = merge_speech_profiles("A", "", "B")
    assert merged == "A\n\nB"


def test_coerce_speech_profile_from_dict():
    profile = coerce_speech_profile({
        "character_id": "CHR-0003",
        "tone": "锐利",
        "sentence_length": "短句",
        "vocabulary_level": "简洁",
    })
    assert profile.character_id == "CHR-0003"
    assert profile.name == "CHR-0003"
