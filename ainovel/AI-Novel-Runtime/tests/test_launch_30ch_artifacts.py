from runtime.serialize.launch_30ch_artifacts import write_30ch_launch_plan


def test_write_30ch_launch_plan(tmp_path):
    plan = {
        "kind": "30ch_launch_plan",
        "version": "1.0",
        "chapter_target": 30,
        "content_hash": "abc",
    }
    rel = write_30ch_launch_plan(project_path=tmp_path, report_id="L30-00001", plan=plan)

    assert rel == "registry/derived/30ch-launch-plans/L30-00001.json"
    assert (tmp_path / rel).exists()
