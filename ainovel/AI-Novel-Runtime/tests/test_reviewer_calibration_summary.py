from runtime.serialize.reviewer_calibration_summary import build_reviewer_calibration


def test_reviewer_calibration_with_sufficient_samples():
    report = build_reviewer_calibration(
        reviewer_id="judge-v1",
        model_scores={"quality": [8, 7, 9, 8, 7, 9, 8, 7, 9, 8], "hook": [7, 8, 7, 8, 7, 8, 7, 8, 7, 8]},
        human_scores={"quality": [7, 8, 9, 7, 8, 9, 7, 8, 9, 7], "hook": [7, 7, 7, 8, 7, 8, 7, 8, 7, 8]},
        min_sample=10,
    )
    data = report.to_dict()

    assert data["kind"] == "reviewer_calibration_report"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["dimensions"]) == 2
    assert data["dimensions"][0]["sample_size"] == 10
    assert data["overall_mae"] is not None


def test_reviewer_calibration_insufficient_samples():
    report = build_reviewer_calibration(
        reviewer_id="judge-v1",
        model_scores={"quality": [8, 7]},
        human_scores={"quality": [7, 8]},
        min_sample=10,
    )
    data = report.to_dict()

    assert data["dimensions"][0]["confidence"] == "insufficient"
    assert data["dimensions"][0]["is_calibrated"] is False


def test_reviewer_calibration_empty():
    report = build_reviewer_calibration(reviewer_id="judge-v1", model_scores={}, human_scores={}, min_sample=10)
    assert report.dimensions == []
    assert report.overall_mae is None
