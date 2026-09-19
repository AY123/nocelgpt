from runtime.serialize.launch_30ch_bundle import list_30ch_launch_bundle
from runtime.serialize.launch_30ch import build_30ch_launch_plan
from runtime.serialize.launch_30ch_artifacts import write_30ch_launch_plan


def test_30ch_launch_bundle_lists(tmp_path):
    plan = build_30ch_launch_plan(
        project_path=str(tmp_path),
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
    )
    write_30ch_launch_plan(project_path=tmp_path, report_id="BND-0001", plan=plan)
    bundle = list_30ch_launch_bundle(tmp_path)
    assert bundle["plan_ids"] == ["BND-0001"]
