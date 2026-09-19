from runtime.serialize.launch_30ch import build_30ch_launch_plan
from runtime.serialize.launch_30ch_artifacts import write_30ch_launch_plan


def test_30ch_launch_plan_writes(tmp_path):
    plan = build_30ch_launch_plan(
        project_path=str(tmp_path),
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
    )
    rel = write_30ch_launch_plan(project_path=tmp_path, report_id="L30-00001", plan=plan)
    assert rel == "registry/derived/30ch-launch-plans/L30-00001.json"
    assert (tmp_path / rel).exists()
