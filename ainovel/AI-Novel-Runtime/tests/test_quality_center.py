import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.quality_center import (
    LLMQualityJudge,
    QualityReport,
    build_judge_prompt,
    degraded_report,
    is_degraded_scores,
    llm_quality_judge,
    parse_judge_response,
    quality_judge_output_schema,
    SCORE_DIMENSIONS,
)
from runtime.execution.envelope import wrap


class FakeModel:
    """Stands in for an execution Model: `.generate(prompt) -> obj.text`."""

    model_id = "fake-judge-v1"

    def __init__(self, text: str):
        self._text = text

    def generate(self, prompt: str):
        class _Out:
            text = self._text
            model_id = "fake-judge-v1"
        return _Out()


class BrokenModel:
    model_id = "broken-judge-v1"

    def generate(self, prompt: str):
        raise RuntimeError("provider exploded")


def quality_schema() -> dict:
    # Runtime now emits v2 reports (Phase 4.1); validate against the v2 contract.
    path = (
        Path(__file__).resolve().parents[2]
        / "AI-Novel-Standard" / "contracts" / "quality-report.v2.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


ARTIFACT = {
    "body": "边境的风带着铁锈味。马伦推开作坊门，看见荒道上倒着一个佩甲的男人。",
    "task_id": "TASK-00001",
}
PACKAGE = {
    "task": {"goal": "draft chapter 1", "capability": "ChapterDraft"},
    "context": {
        "characters": [
            {"id": "CHR-00001", "name": "Edric Vance", "notes": "流亡骑士"},
        ],
        "world_rules": [
            {"id": "MAG-00001", "name": "誓言绑定术", "statement": "以血起誓，违背者剧痛。"},
        ],
    },
}

GOOD_JSON = json.dumps({
    "scores": {
        "hook": 82, "conflict": 70, "reward_density": 55,
        "character_consistency": 90, "world_consistency": 88,
        "emotion": 75, "commercial": 68, "originality_risk": 20,
    },
    "dimensions": [
        {"name": "hook", "score": 82, "evidence": "章末‘停止追赶’", "comment": "钩子尚可"},
        {"name": "reward_density", "score": 55, "evidence": "无明确爽点", "comment": "偏弱"},
    ],
    "revision_plan": [
        {"dimension": "reward_density", "issue": "本章无兑现爽点",
         "action": "在中段加入一次主角的小胜", "evidence": "第4段", "priority": "high"},
    ],
    "predictions": {"subscription": 60, "retention": 65, "reader_satisfaction": 70},
}, ensure_ascii=False)


def test_parse_good_json_produces_valid_report():
    report = parse_judge_response(GOOD_JSON, reviewer="llm-quality-judge-v1", model_id="m1")
    assert isinstance(report, QualityReport)
    assert report.scores["hook"] == 82
    assert set(report.scores) == set(SCORE_DIMENSIONS)
    assert report.revision_plan[0]["dimension"] == "reward_density"
    # Predictive block is comparison-only and non-gating.
    assert report.predictions["gating"] is False
    assert report.predictions["comparison_only"] is True


def test_report_validates_against_contract():
    report = parse_judge_response(GOOD_JSON, reviewer="llm-quality-judge-v1")
    schema = quality_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]


def test_gating_invariant_holds_for_all_paths():
    # No matter the input, the report can never gate.
    for text in (GOOD_JSON, "garbage not json", "", "```json\n{}\n```"):
        report = parse_judge_response(text, reviewer="r")
        assert report.axis == "evaluative"
        assert report.gating is False


def test_fenced_json_is_extracted():
    fenced = f"这是评审结果：\n```json\n{GOOD_JSON}\n```\n完毕。"
    report = parse_judge_response(fenced, reviewer="r")
    assert report.scores["hook"] == 82
    assert report.judge_provenance["parse_ok"] is True


def test_scores_are_clamped_and_coerced():
    messy = json.dumps({"scores": {"hook": 250, "conflict": -10, "emotion": "abc"}})
    report = parse_judge_response(messy, reviewer="r")
    assert report.scores["hook"] == 100
    assert report.scores["conflict"] == 0
    assert report.scores["emotion"] == 0
    # missing dims default to 0, never absent
    assert set(report.scores) == set(SCORE_DIMENSIONS)


def test_unparseable_output_degrades_without_raising():
    report = parse_judge_response("模型今天不想输出 JSON", reviewer="r", model_id="m")
    assert report.judge_provenance["degraded"] is True
    assert report.gating is False
    assert all(v == 0 for v in report.scores.values())
    assert any(f["check"] == "judge-degraded" for f in report.findings)


def test_truncated_response_degrades_not_silently_zero():
    # A truncated judge response loses its outer closing brace, so the balanced-
    # span fallback returns the first COMPLETE inner object — the `scores` object
    # itself, which has no "scores" key. That must degrade (parse failure), NOT
    # forge a non-degraded all-zero report that silently poisons revision/serial.
    # (Regression: real DeepSeek run, max_tokens too small → 18-dim + evidence
    # overflowed, every chapter scored a false all-zero with degraded=False.)
    truncated = (
        '{\n  "scores": {\n    "hook": 90,\n    "conflict": 85,\n'
        '    "reward_density": 75,\n    "character_consistency": 90'
        # ...cut off here: outer object never closes, inner scores obj is complete
    )
    report = parse_judge_response(truncated, reviewer="r", model_id="m")
    assert report.judge_provenance["degraded"] is True
    assert report.gating is False
    assert any(f["check"] == "judge-degraded" for f in report.findings)


def test_legitimate_all_zero_sentinel_is_not_degraded():
    # The judge's prompt says: emit all-zero when it genuinely cannot assess. That
    # is a real (non-degraded) verdict carrying a "scores" key — is_degraded_scores
    # catches it downstream. The truncation fix must NOT confuse the two: a JSON
    # WITH a scores key of zeros parses cleanly (parse_ok, not degraded).
    sentinel = json.dumps({"scores": {dim: 0 for dim in SCORE_DIMENSIONS}})
    report = parse_judge_response(sentinel, reviewer="r", model_id="m")
    assert report.judge_provenance["degraded"] is False
    assert report.judge_provenance["parse_ok"] is True
    assert all(v == 0 for v in report.scores.values())


def test_malformed_advisory_array_salvages_real_scores():
    # Regression (real claude-opus-5 via relay, ch41): the relay silently DROPS the
    # forced tool call on a large judge request, so the model hand-writes JSON and
    # emitted `{"name":"retention":81,...}` — a stray `:81` inside the ADVISORY
    # `dimensions` array. json.loads dies at that offset, the balanced-span fallback
    # returns the inner `scores` object (no "scores" key) and the whole review
    # degraded to all-zero — discarding 18 perfectly good scores present in the text.
    # A complete top-level `scores` object must be salvaged instead.
    malformed = (
        '{"scores":{' + ",".join(f'"{dim}":{70 + i}' for i, dim in enumerate(SCORE_DIMENSIONS))
        + '},"dimensions":[{"name":"hook","score":82},'
          '{"name":"retention":81,"score":81}],'   # <- model's syntax error
          '"revision_plan":[],"predictions":{}}'
    )
    report = parse_judge_response(malformed, reviewer="r", model_id="m")
    assert report.judge_provenance["parse_ok"] is True
    assert report.judge_provenance["degraded"] is False
    assert report.judge_provenance["salvaged"] is True
    assert report.scores["hook"] == 70
    assert not is_degraded_scores(report.to_dict())   # must count toward baselines
    assert any(f["check"] == "quality-judge-salvaged" for f in report.findings)
    # The unparseable advisory arrays are dropped, not guessed at.
    assert report.dimensions == []
    assert report.revision_plan == []
    assert report.gating is False


def test_salvage_never_forges_scores_that_were_not_emitted():
    # The salvage must key on a REAL top-level "scores" object. Text that merely
    # mentions the word, or whose scores object is itself truncated, still degrades.
    for text in (
        '{"dimensions":[{"name":"scores"}]}',           # the word, not the object
        '{"scores":{"hook":90,"conflict":85',           # truncated mid-scores
    ):
        report = parse_judge_response(text, reviewer="r", model_id="m")
        assert report.judge_provenance["degraded"] is True, text
        assert "salvaged" not in report.judge_provenance, text
        assert all(v == 0 for v in report.scores.values()), text


def test_salvaged_report_is_schema_valid():
    malformed = (
        '{"scores":{' + ",".join(f'"{dim}":50' for dim in SCORE_DIMENSIONS)
        + '},"dimensions":[{"name":"x":1}]}'
    )
    report = parse_judge_response(malformed, reviewer="r", model_id="m")
    assert report.judge_provenance["salvaged"] is True
    errors = list(Draft202012Validator(quality_schema()).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]


def test_judge_wraps_model_and_scores_draft():
    judge = llm_quality_judge(FakeModel(GOOD_JSON))
    report = judge.review(ARTIFACT, PACKAGE)
    assert report.scores["character_consistency"] == 90
    assert report.reviewer == "llm-quality-judge-v1"


def test_structured_judge_uses_provider_enforced_schema():
    class StructuredModel:
        model_id = "claude-test"
        supports_structured_output = True

        def generate(self, prompt):
            raise AssertionError("plain generation must not be used")

        def generate_structured(self, prompt, schema, *, tool_name):
            assert set(schema["properties"]["scores"]["required"]) == set(SCORE_DIMENSIONS)
            assert tool_name == "submit_quality_review"
            class _Out:
                text = GOOD_JSON
                model_id = "claude-test"
            return _Out()

    report = LLMQualityJudge(StructuredModel()).review(ARTIFACT, PACKAGE)

    assert report.scores["hook"] == 82
    assert report.judge_provenance["parse_ok"] is True


def test_quality_judge_schema_requires_all_score_dimensions():
    schema = quality_judge_output_schema()
    Draft202012Validator.check_schema(schema)
    assert set(schema["properties"]["scores"]["required"]) == set(SCORE_DIMENSIONS)


def test_judge_survives_model_exception():
    judge = LLMQualityJudge(BrokenModel())
    report = judge.review(ARTIFACT, PACKAGE)
    assert report.gating is False
    assert report.judge_provenance["degraded"] is True


def test_report_rides_envelope_like_existing_reviewer():
    # The Quality Center report must slot into the SAME envelope path run.py
    # uses for evaluative reviews (wrap(qa_review=...)).
    report = parse_judge_response(GOOD_JSON, reviewer="r")
    envelope = wrap(ARTIFACT, None, qa_review=report.to_dict())
    assert envelope["draft"] == ARTIFACT
    assert envelope["qa_review"]["axis"] == "evaluative"
    assert envelope["qa_review"]["gating"] is False


def test_judge_prompt_includes_facts_and_body():
    prompt = build_judge_prompt(ARTIFACT, PACKAGE)
    assert "誓言绑定术" in prompt          # world rule fact reached the judge
    assert "Edric Vance" in prompt         # character fact reached the judge
    assert ARTIFACT["body"][:10] in prompt # the prose under review is present


def test_degraded_report_is_schema_valid():
    report = degraded_report("r", "some reason", model_id="m")
    schema = quality_schema()
    errors = list(Draft202012Validator(schema).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]
