from runtime.scene.ir import build_chapter_ir, render_chapter_ir


def test_chapter_ir_carries_reference_anchor():
    outline = {
        "id": "OUTLINE-00001",
        "first_30_chapters": [
            {
                "chapter_no": 1,
                "goal": "建立主角处境",
                "conflict": "冲突逼近",
                "escalation": "压力加码",
                "reward_if_any": "首次翻身",
                "end_hook": "下章更危险",
            }
        ],
        "reference_abstraction": {
            "id": "REFABSTRACT-001",
            "kind": "reference_lm_abstraction",
            "market_positioning": {"core_promise": "强钩子开局"},
            "structural_patterns": {"opening": "强钩子开局"},
            "commercial_cadence": {"mid_arc": "每个小周期均有显性回报"},
            "transferable_abstractions": ["反差开局"],
        },
    }

    ir = build_chapter_ir(
        task_id="TASK-00001",
        chapter_no=1,
        goal="建立主角处境",
        participants=["CHR-00001"],
        derived_from=["EVT-00001@v1"],
        source_version=1,
        outline=outline,
    )

    assert ir["reference_anchor"]["id"] == "REFABSTRACT-001"
    assert ir["reference_anchor"]["market_positioning"]["core_promise"] == "强钩子开局"
    rendered = render_chapter_ir(ir)
    assert "本章意图" in rendered
