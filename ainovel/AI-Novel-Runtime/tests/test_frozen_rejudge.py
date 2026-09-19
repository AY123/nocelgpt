import json
from pathlib import Path

from runtime.execution.quality_center import SCORE_DIMENSIONS
from runtime.serialize.frozen_rejudge import rejudge_frozen_chapters


class _StructuredModel:
    model_id = "claude-test"
    supports_structured_output = True

    def generate_structured(self, prompt, schema, *, tool_name):
        class _Out:
            text = json.dumps({
                "scores": {dimension: 80 for dimension in SCORE_DIMENSIONS},
                "dimensions": [], "revision_plan": [], "predictions": {},
            })
            model_id = "claude-test"
        return _Out()


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_frozen_rejudge_updates_review_without_changing_draft(tmp_path):
    project = tmp_path / "book"
    package_dir = tmp_path / "packages"
    draft = {"task_id": "TASK-00031", "body": "frozen body",
             "content_hash": "sha256:frozen"}
    _write(project / "registry/derived/drafts/TASK-00031.json", {
        "envelope_format": "runtime-draft/1.0", "draft": draft,
        "qa_review": {"judge_provenance": {"degraded": True}},
        "publish_readiness": {"basis": {"redline": {"hits": []}}},
    })
    _write(project / "registry/derived/chapter-run/run-TASK-00031.json", {
        "index": 31, "task_id": "TASK-00031", "qa_scores": {},
        "verdict": "degraded"})
    _write(package_dir / "TASK-00031.package.json", {
        "task": {"goal": "goal"}, "context": {}})

    result = rejudge_frozen_chapters(
        project_path=project, package_dir=package_dir, model=_StructuredModel(),
        start_chapter=31, end_chapter=31)

    envelope = json.loads(
        (project / "registry/derived/drafts/TASK-00031.json").read_text())
    assert envelope["draft"] == draft
    assert envelope["qa_review"]["scores"]["hook"] == 80
    assert result["n_degraded"] == 0
    assert (project / "registry/derived/chapter-quality-review/review-TASK-00031.json").is_file()
