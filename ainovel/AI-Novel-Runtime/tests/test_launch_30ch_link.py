from runtime.serialize.launch_30ch_link import build_30ch_launch_link


def test_30ch_launch_link_structure():
    link = build_30ch_launch_link(
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="linked to manifest",
    )

    assert link["kind"] == "30ch_launch_link"
    assert link["launch_report_id"] == "L30R-0001"
    assert link["run_manifest_ref"] == "registry/derived/run-manifests/run-0001.json"
    assert "content_hash" in link
