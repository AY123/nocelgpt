from runtime.serialize.text_language import measure_text_language


def test_measure_text_language_detects_ascii_drift():
    metrics = measure_text_language("这是中文 prose with aVeryLongEnglishRunAndMore")

    assert metrics.body_chars > 0
    assert metrics.ascii_word_count > 0
    assert metrics.chinese_char_count > 0
    assert metrics.long_ascii_run is True


def test_measure_text_language_detects_english_dominance():
    metrics = measure_text_language("This is English only content")

    assert metrics.english_dominant is True
    assert metrics.chinese_char_count == 0
