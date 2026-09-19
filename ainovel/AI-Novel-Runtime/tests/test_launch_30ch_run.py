from runtime.serialize.launch_30ch_run import build_30ch_run_attachment


def test_30ch_run_attachment_uses_launch_link():
    attachment = build_30ch_run_attachment(
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="attached",
    )

    assert attachment["kind"] == "30ch_launch_link"
    assert attachment["launch_report_id"] == "L30R-0001"
    assert attachment["run_manifest_ref"] == "registry/derived/run-manifests/run-0001.json"
