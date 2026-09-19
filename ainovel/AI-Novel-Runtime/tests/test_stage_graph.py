from runtime.serialize.stage_graph import build_default_stage_graph


def test_stage_graph_has_all_stages():
    graph = build_default_stage_graph()
    data = graph.to_dict()

    assert data["kind"] == "stage_graph"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["stages"]) == 6

    stage_ids = [s["stage_id"] for s in data["stages"]]
    assert "genesis" in stage_ids
    assert "golden_three" in stage_ids
    assert "serial_1_30" in stage_ids
    assert "gate_30" in stage_ids
    assert "serial_31_100" in stage_ids
    assert "baseline_100" in stage_ids


def test_stage_dependencies():
    graph = build_default_stage_graph()
    stages = {s.stage_id: s for s in graph.stages}

    assert "genesis" in stages["golden_three"].depends_on
    assert "golden_three" in stages["serial_1_30"].depends_on
    assert "serial_1_30" in stages["gate_30"].depends_on
    assert "gate_30" in stages["serial_31_100"].depends_on
    assert "serial_31_100" in stages["baseline_100"].depends_on


def test_stage_recovery_keys():
    graph = build_default_stage_graph()
    for stage in graph.stages:
        assert stage.recovery_key, f"{stage.stage_id} missing recovery_key"
