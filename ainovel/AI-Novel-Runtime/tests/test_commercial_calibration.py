from runtime.serialize.commercial_calibration import build_commercial_calibration


def test_commercial_calibration_without_real_data():
    report = build_commercial_calibration(
        project_id="PROJ-1",
        simulated_signals={"retention": [0.7] * 20, "drop_risk": [0.3] * 20},
    )
    data = report.to_dict()

    assert data["kind"] == "commercial_calibration_report"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["any_calibrated"] is False
    assert all(m["label"] == "predicted" for m in data["metrics"])


def test_commercial_calibration_with_real_data():
    report = build_commercial_calibration(
        project_id="PROJ-1",
        simulated_signals={"retention": [0.7] * 20},
        real_signals={"retention": [0.68] * 20},
        min_sample=10,
    )
    data = report.to_dict()

    assert data["any_calibrated"] is True
    assert data["metrics"][0]["label"] == "calibrated"
    assert data["metrics"][0]["mae"] is not None


def test_commercial_calibration_diagnostic():
    report = build_commercial_calibration(
        project_id="PROJ-1",
        simulated_signals={"retention": [0.7] * 20},
        real_signals={"retention": [0.3] * 20},
        min_sample=10,
    )
    data = report.to_dict()

    assert data["any_calibrated"] is False
    assert data["metrics"][0]["label"] == "diagnostic"
