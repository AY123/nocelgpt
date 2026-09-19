import json
from runtime.publishing.release_package import build_release_package, write_release_package


def _setup_project(tmp_path):
    (tmp_path / "registry" / "_meta").mkdir(parents=True, exist_ok=True)
    (tmp_path / "registry" / "_meta" / "project-id").write_text("PROJ-1", encoding="utf-8")
    outline_dir = tmp_path / "registry" / "derived" / "outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    outline = {
        "id": "OUTLINE-00001",
        "title": "灰烬纪元的执灯人",
        "logline": "少年在灾变中觉醒",
        "genre": ["玄幻"],
        "themes": ["秩序重建", "个人代价"],
        "market_position": {"reader_promise": "废土重建的爽文体验"},
        "first_30_chapters": [
            {"chapter_no": 1, "goal": "开局", "end_hook": "悬念1"},
            {"chapter_no": 2, "goal": "推进", "end_hook": "悬念2"},
        ],
        "originality_report": {"risk_level": "low", "notes": ["ok"]},
    }
    (outline_dir / "OUTLINE-00001.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_release_package_built_from_outline(tmp_path):
    project = _setup_project(tmp_path)
    package = build_release_package(project, project_id="PROJ-1")
    data = package.to_dict()

    assert data["kind"] == "release_package"
    assert data["publish_authority"] == "human"
    assert data["gating"] is False
    assert data["comparison_only"] is True
    assert data["metadata"]["title"] == "灰烬纪元的执灯人"
    assert data["metadata"]["genre"] == ["玄幻"]
    assert "废土重建" in data["metadata"]["selling_points"][0]
    assert len(data["first_30_chapters"]) == 2
    assert data["content_hash"].startswith("sha256:")
    assert data["version"] == "1.2"  # P0-2: Version bumped for fail-closed semantics


def test_release_package_with_baseline_and_long_run(tmp_path):
    project = _setup_project(tmp_path)
    package = build_release_package(
        project,
        project_id="PROJ-1",
        baseline_report={"go_iterate_stop": "go"},
        long_run_report={"produced_count": 100},
    )
    data = package.to_dict()

    assert data["baseline_report"]["go_iterate_stop"] == "go"
    assert data["long_run_report"]["produced_count"] == 100


def test_release_package_writes(tmp_path):
    project = _setup_project(tmp_path)
    package = build_release_package(project, project_id="PROJ-1")
    out = write_release_package(project / "registry" / "derived" / "release-package" / "RELEASE-PROJ-1.json", package)
    assert out.exists()
