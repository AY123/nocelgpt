from runtime.serialize.cost_breaker import check_budget


def test_budget_no_trip():
    report = check_budget(
        project_limit=100.0, project_spent=50.0,
        volume_limit=50.0, volume_spent=20.0,
    )
    data = report.to_dict()

    assert data["kind"] == "circuit_breaker_report"
    assert data["any_tripped"] is False
    assert data["gating"] is True
    assert len(data["layers"]) == 6
    assert data["layers"][0]["remaining"] == 50.0


def test_budget_trips():
    report = check_budget(
        project_limit=10.0, project_spent=12.0,
    )
    data = report.to_dict()

    assert data["any_tripped"] is True
    assert data["layers"][0]["tripped"] is True
    assert data["layers"][0]["remaining"] == -2.0


def test_budget_no_limit():
    report = check_budget()
    data = report.to_dict()

    assert data["any_tripped"] is False
    for layer in data["layers"]:
        assert layer["limit"] is None
        assert layer["tripped"] is False
