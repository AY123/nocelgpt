from runtime.serialize.blind_evaluation import build_blind_evaluation


def test_blind_evaluation_auto_wins():
    report = build_blind_evaluation(
        chapter_id="CH-001",
        arms=[
            {"arm_id": "A", "label": "original", "text_hash": "sha256:orig", "score": 7.0},
            {"arm_id": "B", "label": "auto_revised", "text_hash": "sha256:auto", "score": 8.5, "fact_damage_count": 0},
            {"arm_id": "C", "label": "human_revised", "text_hash": "sha256:human", "score": 8.0},
        ],
    )
    data = report.to_dict()

    assert data["kind"] == "blind_evaluation_report"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["winner"] == "auto_revised"
    assert data["auto_revised_wins"] == 2
    assert data["auto_revised_losses"] == 0
    assert data["net_benefit"] == "positive"
    assert data["fact_damage_total"] == 0


def test_blind_evaluation_auto_loses():
    report = build_blind_evaluation(
        chapter_id="CH-002",
        arms=[
            {"arm_id": "A", "label": "original", "text_hash": "sha256:orig", "score": 9.0},
            {"arm_id": "B", "label": "auto_revised", "text_hash": "sha256:auto", "score": 6.0, "fact_damage_count": 1},
            {"arm_id": "C", "label": "human_revised", "text_hash": "sha256:human", "score": 8.0},
        ],
    )
    data = report.to_dict()

    assert data["winner"] == "original"
    assert data["auto_revised_wins"] == 0
    assert data["auto_revised_losses"] == 2
    assert data["net_benefit"] == "negative"
    assert data["fact_damage_total"] == 1


def test_blind_evaluation_neutral():
    report = build_blind_evaluation(
        chapter_id="CH-003",
        arms=[
            {"arm_id": "A", "label": "original", "text_hash": "sha256:orig", "score": 8.0},
            {"arm_id": "B", "label": "auto_revised", "text_hash": "sha256:auto", "score": 8.0},
        ],
    )
    assert report.net_benefit == "neutral"
    assert report.auto_revised_wins == 0
    assert report.auto_revised_losses == 0
