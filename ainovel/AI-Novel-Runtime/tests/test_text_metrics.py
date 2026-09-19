from runtime.serialize.text_metrics import measure_text_length


def test_measure_text_length_counts_basic_units():
    metrics = measure_text_length("第一段\n\n第二段 abc")

    assert metrics.body_chars == len("第一段\n\n第二段 abc")
    assert metrics.nonspace_chars == 9
    assert metrics.line_count == 3
    assert metrics.paragraph_count == 2
    assert metrics.token_estimate > 0
