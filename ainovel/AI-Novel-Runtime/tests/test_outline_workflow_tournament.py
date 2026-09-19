import hashlib
import json

from runtime.execution.genesis_pairwise_judge import GENESIS_DIMS
from runtime.outline.qa import OUTLINE_REVIEW_CHECKS
from runtime.outline.workflow import run_outline_bootstrap


class _StubModel:
    model_id = "stub"

    def generate(self, prompt: str):
        class _Out:
            text = json.dumps({
                dim: {"winner": "tie", "evidence": "same"}
                for dim in GENESIS_DIMS
            })
        return _Out()


class _CaptureJudge(_StubModel):
    provider = "fake"

    def __init__(self, model_id):
        self.model_id = model_id
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return super().generate(prompt)


class _OutlineQAModel:
    provider = "fake"
    model_id = "outline-qa-v1"

    def __init__(self, response=None):
        self.response = response
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
        text = self.response or json.dumps({
            "assessments": {
                check: {"severity": "info", "message": f"ok-{check}"}
                for check in OUTLINE_REVIEW_CHECKS
            },
            "summary": "可继续展开",
        })
        return type("Out", (), {"text": text, "model_id": self.model_id})()


def _scaffold(project):
    """A bootstrap-able project. N100-021 requires 1-5 reference novels with a
    traceable source, so a project with none legitimately fails at stage
    'sources' — the reference input is part of the contract, not optional."""
    meta = project / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "project-id").write_text("PROJ-1", encoding="utf-8")
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    refs = project / "sources" / "reference-novels"
    refs.mkdir(parents=True, exist_ok=True)
    (refs / "ref.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。"
        "他发现秘密线索，突破境界并赢得第一次胜利。" * 3, encoding="utf-8")


def test_outline_bootstrap_uses_enriched_tournament_input(tmp_path):
    project = tmp_path
    _scaffold(project)

    result = run_outline_bootstrap(project, model=_StubModel())
    assert result.ok is True
    assert result.stage == "done"


def test_outline_bootstrap_writes_archives(tmp_path):
    project = tmp_path
    _scaffold(project)

    result = run_outline_bootstrap(project, model=_StubModel())
    assert result.ok is True
    run_root = project / result.run_dir
    assert run_root.exists()
    assert (run_root / "tournament.json").exists()
    assert (run_root / "ci-m4-ledger.json").exists()
    assert (run_root / "promise-ledger.json").exists()
    assert (run_root / "semantic-ledger.json").exists()
    assert (run_root / "chapter-evidence-ledger.json").exists()
    # Y365-03: the deterministic proposal scoreboard is archived beside the
    # pairwise LLM tournament (built≠live proof — it has a real caller).
    comparison_path = run_root / "proposal-comparison.json"
    assert comparison_path.exists()
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert comparison["kind"] == "multi_proposal_comparison"
    assert comparison["gating"] is False
    assert comparison["comparison_only"] is True
    # Selection stays a human call (ADR-009); the winner is advisory only.
    assert comparison["publish_authority"] == "human"
    assert len(comparison["proposals"]) >= 2
    assert comparison["winner_id"] in {p["proposal_id"] for p in comparison["proposals"]}


def test_same_complete_candidate_snapshot_is_reused_by_two_judges(tmp_path):
    project = tmp_path
    _scaffold(project)
    first = _CaptureJudge("judge-one")
    second = _CaptureJudge("judge-two")

    result = run_outline_bootstrap(
        project,
        run_id="frozen-multi-judge",
        judge_models=[("fake:judge-one", first), ("fake:judge-two", second)],
    )

    assert result.ok is True
    run_root = project / result.run_dir
    candidates = json.loads((run_root / "candidates.json").read_text(encoding="utf-8"))
    assert len(candidates) == 3
    for candidate in candidates:
        for key in ("title", "genre", "logline", "protagonist_engine",
                    "power_system", "world", "characters", "first_30_chapters"):
            assert candidate[key]
        assert len(candidate["first_30_chapters"]) == 30
    tournament = json.loads((run_root / "tournament.json").read_text(encoding="utf-8"))
    assert len(first.prompts) == len(second.prompts) == 6
    assert first.prompts == second.prompts
    assert {judge["candidate_hash"] for judge in tournament["judges"]} == {
        tournament["candidate_hash"]}
    assert tournament["outline_qa"]["status"] == "not_model_integrated"


def test_outline_model_review_is_archived_as_advisory_sibling(tmp_path):
    project = tmp_path
    _scaffold(project)
    qa_model = _OutlineQAModel()

    result = run_outline_bootstrap(
        project, run_id="outline-qa-live-path", outline_qa_model=qa_model)

    assert result.ok is True
    assert len(qa_model.prompts) == 1
    run_root = project / result.run_dir
    review = json.loads((run_root / "outline-review.json").read_text(encoding="utf-8"))
    assert review["axis"] == "evaluative"
    assert review["gating"] is False
    assert review["reviewer"] == "heuristic-outline-reviewer-v1"
    assert review["model_integration"] == {"status": "integrated", "gating": False}
    assert review["model_review"]["status"] == "completed"
    assert review["model_review"]["gating"] is False
    assert len(review["model_review"]["findings"]) == len(OUTLINE_REVIEW_CHECKS)
    final_outline = json.loads(
        (run_root / "final-outline.json").read_text(encoding="utf-8"))
    canonical = json.dumps(
        final_outline, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    persisted_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert review["model_review"]["provenance"]["outline_hash"] == persisted_hash
    tournament = json.loads((run_root / "tournament.json").read_text(encoding="utf-8"))
    assert tournament["outline_qa"]["status"] == "model_integrated"
    assert tournament["outline_qa"]["gating"] is False


def test_outline_model_failure_is_degraded_and_never_gates(tmp_path):
    project = tmp_path
    _scaffold(project)

    result = run_outline_bootstrap(
        project, run_id="outline-qa-degraded",
        outline_qa_model=_OutlineQAModel(RuntimeError("offline")))

    assert result.ok is True
    review = json.loads(
        (project / result.run_dir / "outline-review.json").read_text(encoding="utf-8"))
    assert review["model_integration"]["status"] == "degraded"
    assert review["model_review"]["status"] == "degraded"
    assert review["model_review"]["gating"] is False
    assert "provider error" in review["model_review"]["provenance"]["error"]
    tournament = json.loads(
        (project / result.run_dir / "tournament.json").read_text(encoding="utf-8"))
    assert tournament["outline_qa"]["status"] == "model_degraded"


def test_deterministic_outline_gate_runs_before_model_review(monkeypatch, tmp_path):
    project = tmp_path
    _scaffold(project)
    qa_model = _OutlineQAModel()

    monkeypatch.setattr(
        "runtime.outline.workflow.synthesize_final_outline",
        lambda *args, **kwargs: {
            "protagonist_engine": {"golden_finger": "", "cost": ""},
            "power_system": {"tiers": []},
            "conflict_ladder": [],
            "reward_loop": {},
            "first_30_chapters": [],
            "plot": {"volumes": []},
        },
    )
    result = run_outline_bootstrap(project, outline_qa_model=qa_model)

    assert result.ok is False
    assert result.stage == "outline-qa"
    assert qa_model.prompts == []
