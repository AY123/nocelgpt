import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.quality_center import SCORE_DIMENSIONS
from runtime.execution.review_panel import (
    Panelist,
    ReviewPanel,
    build_review_panel,
    ROLE_SPECIALTY,
)
from runtime.execution.revision import revise_until


class RecordingModel:
    """Returns a fixed judge JSON and records every prompt it was given, so we
    can assert panelists scored INDEPENDENTLY (no cross-reference)."""

    def __init__(self, scores, model_id="rec-v1"):
        self.model_id = model_id
        self._scores = scores
        self.prompts = []

    def generate(self, prompt: str):
        self.prompts.append(prompt)

        class _Out:
            pass
        o = _Out()
        o.text = json.dumps({"scores": self._scores, "dimensions": [],
                             "revision_plan": [], "predictions": {}}, ensure_ascii=False)
        o.model_id = self.model_id
        o.model_kind = "llm"
        return o


class BrokenModel:
    model_id = "broken-v1"

    def generate(self, prompt: str):
        raise RuntimeError("panelist down")


class JunkModel:
    model_id = "junk-v1"

    def generate(self, prompt: str):
        class _Out:
            text = "我今天不输出 JSON"
            model_id = "junk-v1"
            model_kind = "llm"
        return _Out()


def _scores(**ov):
    base = {d: 60 for d in SCORE_DIMENSIONS}
    base["originality_risk"] = 20
    base.update(ov)
    return base


ARTIFACT = {"task_id": "TASK-00001", "body": "正文：主角抵达小镇。",
            "content_hash": "sha256:" + "0" * 64,
            "provenance": {"package_hash": "sha256:" + "a" * 64,
                           "derived_from": ["CHR-00001@v1"], "source_version": 1}}
PACKAGE = {"task": {"goal": "chapter 1", "capability": "ChapterDraft", "task_id": "TASK-00001"},
           "content_hash": "sha256:" + "a" * 64,
           "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
           "context": {"characters": [{"id": "CHR-00001", "name": "Edric"}]}}


def quality_schema() -> dict:
    # Panel synthesis now emits v2 dimensions (Phase 4.1); validate against v2.
    path = (Path(__file__).resolve().parents[2]
            / "AI-Novel-Standard" / "contracts" / "quality-report.v2.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_panelists_score_independently():
    # Each panelist must receive only the draft/package — never another's report.
    lit = RecordingModel(_scores(emotion=90))
    com = RecordingModel(_scores(commercial=95))
    panel = build_review_panel({"literary": lit, "commercial": com})
    panel.review(ARTIFACT, PACKAGE)
    assert len(lit.prompts) == 1 and len(com.prompts) == 1
    # No panelist prompt leaks another panelist's ACTUAL scores/verdict. Each
    # prompt only contains the draft + package + its own role focus. (The word
    # "scores" appears in the output-format spec of every judge prompt, so we
    # check for the concrete leaked values instead.)
    assert "emotion=90" not in com.prompts[0] and "\"emotion\": 90" not in com.prompts[0]
    assert "commercial=95" not in lit.prompts[0] and "\"commercial\": 95" not in lit.prompts[0]
    assert "panelist-" not in lit.prompts[0] and "panelist-" not in com.prompts[0]
    # Role focus reached the specialists.
    assert "情绪" in lit.prompts[0]
    assert "商业" in com.prompts[0]


def test_weighted_synthesis_favors_specialist():
    # literary says emotion=100, commercial says emotion=40. literary is the
    # emotion specialist (weight 3 vs 1), so consensus must lean toward 100.
    lit = RecordingModel(_scores(emotion=100))
    com = RecordingModel(_scores(emotion=40))
    panel = build_review_panel({"literary": lit, "commercial": com})
    report = panel.review(ARTIFACT, PACKAGE)
    # weighted mean = (100*3 + 40*1) / 4 = 85; plain mean would be 70.
    assert report.scores["emotion"] == 85
    assert report.panel["synthesis"] == "weighted"


def test_disagreement_is_surfaced_not_hidden():
    a = RecordingModel(_scores(hook=90))
    b = RecordingModel(_scores(hook=30))
    panel = build_review_panel({"structural": a, "commercial": b})
    report = panel.review(ARTIFACT, PACKAGE)
    assert report.panel["disagreement"]["hook"] == 60
    assert any(f["check"] == "panel-disagreement" and "hook" in f["message"]
               for f in report.findings)


def test_one_degraded_panelist_does_not_kill_panel():
    good = RecordingModel(_scores(commercial=80))
    panel = ReviewPanel([
        Panelist.build("commercial", good),
        Panelist.build("literary", JunkModel()),
        Panelist.build("logic", BrokenModel()),
    ])
    report = panel.review(ARTIFACT, PACKAGE)
    # consensus is NOT degraded — it stands on the one live panelist.
    assert report.judge_provenance["degraded"] is False
    assert report.scores["commercial"] == 80
    degraded_flags = {p["role"]: p["degraded"] for p in report.panel["panelists"]}
    assert degraded_flags["literary"] is True
    assert degraded_flags["logic"] is True
    assert degraded_flags["commercial"] is False


def test_all_degraded_panelists_degrade_consensus():
    panel = ReviewPanel([
        Panelist.build("literary", JunkModel()),
        Panelist.build("logic", BrokenModel()),
    ])
    report = panel.review(ARTIFACT, PACKAGE)
    assert report.judge_provenance["degraded"] is True
    assert report.gating is False   # still never gates


def test_consensus_report_is_schema_valid():
    panel = build_review_panel({
        "literary": RecordingModel(_scores(emotion=88)),
        "structural": RecordingModel(_scores(hook=75)),
        "commercial": RecordingModel(_scores(commercial=70)),
    })
    report = panel.review(ARTIFACT, PACKAGE)
    schema = quality_schema()
    errors = list(Draft202012Validator(schema).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]


def test_panel_invariants_hold():
    panel = build_review_panel({"literary": RecordingModel(_scores())})
    report = panel.review(ARTIFACT, PACKAGE)
    assert report.axis == "evaluative"
    assert report.gating is False


def test_revision_plans_are_unioned():
    a = RecordingModel(_scores())
    b = RecordingModel(_scores())

    # inject differing plans by monkey-wrapping the model output
    def _mk(model, plan):
        def gen(prompt):
            class _Out:
                text = json.dumps({"scores": _scores(), "dimensions": [],
                                   "revision_plan": plan, "predictions": {}}, ensure_ascii=False)
                model_id = "m"
                model_kind = "llm"
            return _Out()
        model.generate = gen
        return model

    _mk(a, [{"dimension": "hook", "issue": "弱", "action": "加钩子", "priority": "high"}])
    _mk(b, [{"dimension": "commercial", "issue": "淡", "action": "加卖点", "priority": "medium"}])
    panel = build_review_panel({"structural": a, "commercial": b})
    report = panel.review(ARTIFACT, PACKAGE)
    dims = {item["dimension"] for item in report.revision_plan}
    assert dims == {"hook", "commercial"}


def test_panel_drops_into_revision_controller():
    # The panel IS a DraftReviewer: revise_until must accept it unchanged.
    # round0: low reward_density flagged; after rewrite: high.
    plan = [{"dimension": "reward_density", "issue": "无爽点", "action": "加小胜", "priority": "high"}]

    class SeqModel:
        model_id = "seq"

        def __init__(self, seq):
            self.seq = seq
            self.i = 0

        def generate(self, prompt):
            text = self.seq[min(self.i, len(self.seq) - 1)]
            self.i += 1

            class _Out:
                pass
            o = _Out()
            o.text = text
            o.model_id = "seq"
            o.model_kind = "llm"
            return o

    judge_model = SeqModel([
        json.dumps({"scores": _scores(reward_density=55), "dimensions": [],
                    "revision_plan": plan, "predictions": {}}, ensure_ascii=False),
        json.dumps({"scores": _scores(reward_density=85), "dimensions": [],
                    "revision_plan": [], "predictions": {}}, ensure_ascii=False),
    ])
    panel = build_review_panel({"commercial": judge_model})
    rewrite_model = SeqModel(["修订稿：主角中段打赢一场。"])
    result = revise_until(panel, rewrite_model, ARTIFACT, PACKAGE, max_rounds=2)
    assert result.session.gating is False
    assert result.session.rounds[0]["scores_after"]["reward_density"] == 85


def test_specialty_table_covers_all_dimensions():
    covered = set()
    for dims in ROLE_SPECIALTY.values():
        covered.update(dims)
    assert covered == set(SCORE_DIMENSIONS)
