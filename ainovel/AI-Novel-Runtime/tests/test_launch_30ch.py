from runtime.serialize.launch_30ch import build_30ch_launch_plan


def test_30ch_launch_plan_structure():
    plan = build_30ch_launch_plan(
        project_path="/tmp/project",
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
    )

    assert plan["kind"] == "30ch_launch_plan"
    assert plan["chapter_target"] == 30
    assert plan["budget_limit"] == 100.0
    assert "content_hash" in plan
