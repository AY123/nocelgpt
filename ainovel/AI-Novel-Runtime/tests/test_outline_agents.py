from runtime.outline.agents import _build_first_30_chapters


def test_first_30_chapters_goal_is_not_monotone():
    chapters = _build_first_30_chapters(
        {"desire": "成为掌局者", "flaw": "不敢信任他人", "golden_finger": "记忆重演", "cost": "失去记忆"},
        {"cadence_chapters": 3, "reward_types": ["实力突破", "打脸翻身"]},
        conflict_ladder=[
            {"level": "小敌人", "enemy": "淬体阶段的小敌人", "pressure_source": "眼前的生存威胁"},
            {"level": "阶段boss", "enemy": "通玄阶段的阶段boss", "pressure_source": "掌控一片地图/资源的势力"},
            {"level": "世界级敌人", "enemy": "登仙阶段的世界级敌人", "pressure_source": "维系旧秩序的顶层力量"},
        ],
    )

    goals = [c["goal"] for c in chapters]
    assert len(goals) == 30
    assert len(set(goals)) > 10
