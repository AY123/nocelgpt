from runtime.serialize.calibration_protocol import build_calibration_protocol


def test_calibration_protocol_without_real_data():
    report = build_calibration_protocol(
        protocol_id="CAL-1",
        predicted={"retention": [0.7, 0.6, 0.8]},
        real=None,
    )
    data = report.to_dict()

    assert data["protocol_id"] == "CAL-1"
    assert data["has_real_data"] is False
    assert data["calibrates"] is False
    assert data["all_predictions_labeled"] is True
    assert data["comparison_only"] is True
    assert data["gating"] is False


def test_calibration_protocol_with_real_data():
    predicted = {"retention": [0.7] * 30, "drop_risk": [0.3] * 30}
    real = {"retention": [0.68] * 30, "drop_risk": [0.33] * 30}
    report = build_calibration_protocol(protocol_id="CAL-2", predicted=predicted, real=real, min_sample=10)
    data = report.to_dict()

    assert data["has_real_data"] is True
    assert data["calibrates"] is True
    assert len(data["metrics"]) == 2
    assert all(m["is_calibrated"] for m in data["metrics"])
