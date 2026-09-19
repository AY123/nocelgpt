from runtime.serialize.long_run_readiness import check_long_run_readiness


def test_long_run_readiness_smoke(tmp_path):
    project = tmp_path
    (project / "registry" / "_meta").mkdir(parents=True, exist_ok=True)
    (project / "registry" / "_meta" / "project-id").write_text("PROJ-1", encoding="utf-8")
    (project / "registry" / "derived" / "outline").mkdir(parents=True, exist_ok=True)
    (project / "registry" / "derived" / "outline" / "OUTLINE-00001.json").write_text('{"first_30_chapters": []}', encoding="utf-8")

    report = check_long_run_readiness(project)
    data = report.to_dict()

    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["project_id"] == "PROJ-1"
    assert data["checks"]
