import json
import shutil
from pathlib import Path

import pytest

from runtime import compiler
from runtime.pipeline import build_task_package
from runtime.execution.refine import refine_package
from runtime.execution.envelope import ENVELOPE_FORMAT, unwrap
from runtime.execution.quality_center import SCORE_DIMENSIONS, llm_quality_judge
from runtime.execution.review_panel import build_review_panel

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _scores(**ov):
    base = {d: 60 for d in SCORE_DIMENSIONS}
    base["originality_risk"] = 20
    base.update(ov)
    return base


class SeqModel:
    """Returns a fixed sequence of texts on successive .generate() calls."""
    model_id = "seq-v1"

    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def generate(self, prompt):
        text = self.seq[min(self.i, len(self.seq) - 1)]
        self.i += 1

        class _Out:
            pass
        o = _Out()
        o.text = text
        o.model_id = "seq-v1"
        o.model_kind = "llm"
        return o


@pytest.fixture
def project(tmp_path):
    proj = tmp_path / "proj"
    shutil.copytree(FIXTURE, proj)
    return proj


def _build(project, out):
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00018", "draft chapter 18: the severance",
                                     "ChapterDraft", ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    assert r.ok, r.message
    return r.package


LOW_PLAN = [{"dimension": "reward_density", "issue": "无爽点",
             "action": "加一次小胜", "priority": "high"}]


def test_refine_closes_full_loop_and_writes_artifact(project, tmp_path):
    package = _build(project, tmp_path / "build")
    # judge: initial low reward_density (flagged) -> after rewrite high
    judge = llm_quality_judge(SeqModel([
        json.dumps({"scores": _scores(reward_density=55), "dimensions": [],
                    "revision_plan": LOW_PLAN, "predictions": {}}, ensure_ascii=False),
        json.dumps({"scores": _scores(reward_density=88), "dimensions": [],
                    "revision_plan": [], "predictions": {}}, ensure_ascii=False),
    ]))
    rewrite = SeqModel(["修订稿：主角在中段打赢了一场关键冲突，兑现爽点，读者获得强烈满足。" * 5])

    result = refine_package(
        package=package, standard_root=STANDARD, project_path=project,
        reviewer=judge, rewrite_model=rewrite, max_rounds=2)

    assert result.ok, result.message
    assert result.verdict == "improved"
    assert result.rounds == 1
    assert result.scores_before["reward_density"] == 55
    assert result.scores_after["reward_density"] == 88
    # final draft differs from the initial (rewrite happened)
    assert result.final_hash != result.initial_hash
    # written under registry/derived/, never facts
    assert "registry/derived/" in result.artifact_path
    assert "facts" not in result.artifact_path


def test_refine_envelope_carries_review_and_session(project, tmp_path):
    package = _build(project, tmp_path / "build")
    judge = llm_quality_judge(SeqModel([
        json.dumps({"scores": _scores(reward_density=55), "dimensions": [],
                    "revision_plan": LOW_PLAN, "predictions": {}}, ensure_ascii=False),
        json.dumps({"scores": _scores(reward_density=88), "dimensions": [],
                    "revision_plan": [], "predictions": {}}, ensure_ascii=False),
    ]))
    rewrite = SeqModel(["修订稿：主角中段打赢一场关键冲突，兑现爽点。" * 5])
    result = refine_package(package=package, standard_root=STANDARD, project_path=project,
                            reviewer=judge, rewrite_model=rewrite, max_rounds=2)
    assert result.ok

    on_disk = json.loads((project / result.artifact_path).read_text(encoding="utf-8"))
    assert on_disk["envelope_format"] == ENVELOPE_FORMAT
    # both advisory blocks ride the envelope, never the inner contract artifact
    assert on_disk["qa_review"]["axis"] == "evaluative"
    assert on_disk["revision_session"]["gating"] is False
    assert on_disk["revision_session"]["verdict"] == "improved"
    inner = unwrap(on_disk)
    assert "revision_session" not in inner
    assert "qa_review" not in inner
    # inner draft's hash matches what refine reported as final
    assert inner["content_hash"] == result.final_hash


def test_refine_final_draft_still_passes_deterministic_gate(project, tmp_path):
    package = _build(project, tmp_path / "build")
    # rewrite returns EMPTY prose -> rewrite_once yields None -> loop keeps the
    # (non-empty) initial draft; final gate must still pass on that draft.
    judge = llm_quality_judge(SeqModel([
        json.dumps({"scores": _scores(reward_density=55), "dimensions": [],
                    "revision_plan": LOW_PLAN, "predictions": {}}, ensure_ascii=False),
    ]))
    rewrite = SeqModel([""])   # degenerate rewrite
    result = refine_package(package=package, standard_root=STANDARD, project_path=project,
                            reviewer=judge, rewrite_model=rewrite, max_rounds=1)
    # loop degraded on the empty rewrite, but the initial draft is intact & gated
    assert result.ok
    assert result.final_hash == result.initial_hash


def test_refine_gate_blocks_too_short_final_draft(project, tmp_path):
    package = _build(project, tmp_path / "build")
    judge = llm_quality_judge(SeqModel([
        json.dumps({"scores": _scores(), "dimensions": [], "revision_plan": [],
                    "predictions": {}}, ensure_ascii=False),
    ]))
    # min_words huge -> stage-1 execute gate fails before any revision
    result = refine_package(package=package, standard_root=STANDARD, project_path=project,
                            reviewer=judge, rewrite_model=SeqModel(["x"]),
                            min_words=10_000, max_rounds=1)
    assert not result.ok
    assert result.stage in ("draft-qa", "final-draft-qa")


def test_refine_works_with_panel(project, tmp_path):
    package = _build(project, tmp_path / "build")
    # a panel is a DraftReviewer too — refine must accept it unchanged.
    panel_model = SeqModel([
        json.dumps({"scores": _scores(reward_density=55), "dimensions": [],
                    "revision_plan": LOW_PLAN, "predictions": {}}, ensure_ascii=False),
        json.dumps({"scores": _scores(reward_density=85), "dimensions": [],
                    "revision_plan": [], "predictions": {}}, ensure_ascii=False),
    ])
    panel = build_review_panel({"commercial": panel_model})
    rewrite = SeqModel(["修订稿：主角中段打赢一场关键冲突，兑现爽点。" * 5])
    result = refine_package(package=package, standard_root=STANDARD, project_path=project,
                            reviewer=panel, rewrite_model=rewrite, max_rounds=2)
    assert result.ok
    assert result.session["gating"] is False
