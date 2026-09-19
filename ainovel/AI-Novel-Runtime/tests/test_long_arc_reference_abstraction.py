from runtime.arc import project_long_arc, render_long_arc


def test_long_arc_uses_reference_abstraction():
    outline = {
        "plot": {
            "volumes": [
                {"id": "VOL-01", "title": "起势", "goal": "建立主角"},
                {"id": "VOL-02", "title": "破局", "goal": "扩大冲突"},
            ]
        },
        "power_system": {"tiers": ["起步", "立足", "崭露"]},
        "conflict_ladder": [
            {"level": "小敌人", "pressure_source": "生存威胁"},
            {"level": "阶段boss", "pressure_source": "资源封锁"},
        ],
        "reward_loop": {"cadence_chapters": 3},
        "reference_abstraction": {
            "market_positioning": {"core_promise": "强钩子开局"},
            "commercial_cadence": {"mid_arc": "每个小周期均有显性回报"},
        },
    }

    plan = project_long_arc(outline, chapter_limit=6)

    assert plan.chapters[0]["reference_core_promise"] == "强钩子开局"
    assert plan.chapters[0]["reference_commercial_cadence"] == "每个小周期均有显性回报"
    assert plan.to_dict()["chapters"][0]["reference_core_promise"] == "强钩子开局"
    block = render_long_arc(plan, 1)
    assert "参考抽象核心承诺：强钩子开局" in block
