import json

import pytest

from runtime.execution.genesis_pairwise_judge import (
    GENESIS_DIMS, GENESIS_RESPONSE_SCHEMA, build_genesis_pairwise_prompt,
    compare_genesis_candidates, parse_genesis_judge_response,
)


def _response(winner="A", *, omit=None, bad_winner=None):
    payload = {
        dim: {"winner": winner, "evidence": f"because-{dim}"}
        for dim in GENESIS_DIMS if dim != omit
    }
    if bad_winner:
        payload[GENESIS_DIMS[0]]["winner"] = bad_winner
    return json.dumps(payload)


@pytest.mark.parametrize("text", [
    _response(),
    f"```json\n{_response()}\n```",
])
def test_nine_dimension_json_and_markdown_wrapped_json_parse(text):
    parsed, error = parse_genesis_judge_response(text)
    assert error is None
    assert set(parsed) == set(GENESIS_DIMS)


def test_compact_nine_dimension_json_parses_strictly():
    text = json.dumps({
        "winners": {dim: "A" for dim in GENESIS_DIMS},
        "evidence": [f"because-{dim}" for dim in GENESIS_DIMS],
    })
    parsed, error = parse_genesis_judge_response(text)
    assert error is None
    assert set(parsed) == set(GENESIS_DIMS)


@pytest.mark.parametrize("payload,error_part", [
    ({"winners": {dim: "A" for dim in GENESIS_DIMS[:-1]},
      "evidence": ["x"] * len(GENESIS_DIMS)}, "missing dimension"),
    ({"winners": {dim: "A" for dim in GENESIS_DIMS},
      "evidence": ["x"] * (len(GENESIS_DIMS) - 1)}, "exactly 9"),
    ({"winners": {**{dim: "A" for dim in GENESIS_DIMS}, GENESIS_DIMS[0]: "C"},
      "evidence": ["x"] * len(GENESIS_DIMS)}, "invalid winner"),
])
def test_compact_contract_rejects_missing_invalid_and_wrong_length(payload, error_part):
    parsed, error = parse_genesis_judge_response(json.dumps(payload))
    assert parsed is None
    assert error_part in error


@pytest.mark.parametrize(("text", "error_part"), [
    (_response(omit=GENESIS_DIMS[-1]), "missing dimension"),
    (_response(bad_winner="C"), "invalid winner"),
    ("", "empty response"),
])
def test_malformed_contract_is_an_error_not_an_ordinary_tie(text, error_part):
    parsed, error = parse_genesis_judge_response(text)
    assert parsed is None
    assert error_part in error


class _Model:
    provider = "fake"
    model_id = "judge-v1"

    def __init__(self, responses):
        self.responses = iter(responses)

    def generate(self, prompt):
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return type("Out", (), {"text": response, "model_id": self.model_id})()


def test_ab_and_ba_agreement_survives_position_swap():
    comparison = compare_genesis_candidates(
        {"title": "real-a"}, {"title": "real-b"},
        _Model([_response("A"), _response("B")]),
        label_a="A", label_b="B",
    )
    assert comparison.winner == "a"
    assert all(cell["verdict"] == "a" for cell in comparison.dimensions.values())
    assert comparison.judge_provenance["position_consistency_rate"] == 1.0


def test_position_bias_becomes_tie_but_is_not_degraded():
    comparison = compare_genesis_candidates(
        {"title": "real-a"}, {"title": "real-b"},
        _Model([_response("A"), _response("A")]),
        label_a="A", label_b="B",
    )
    assert comparison.winner == "tie"
    assert comparison.judge_provenance["degraded"] is False
    assert comparison.judge_provenance["position_consistency_rate"] == 0.0


@pytest.mark.parametrize("bad", ["", _response(omit=GENESIS_DIMS[0]), RuntimeError("offline")])
def test_parse_and_provider_failures_are_degraded_with_provenance(bad):
    comparison = compare_genesis_candidates(
        {"title": "real-a"}, {"title": "real-b"},
        _Model([bad, _response("B")]),
        label_a="A", label_b="B",
    )
    provenance = comparison.judge_provenance
    assert comparison.winner == "tie"
    assert provenance["degraded"] is True
    assert provenance["call_errors"]["order_ab"]
    assert provenance["calls"]["order_ab"]["request_hash"].startswith("sha256:")
    assert provenance["calls"]["order_ab"]["cost_status"] == "unpriced"
    if not isinstance(bad, Exception):
        assert provenance["calls"]["order_ab"]["raw_response_summary"] is not None


def test_structured_capable_model_uses_forced_schema_path():
    class StructuredModel:
        provider = "claude"
        model_id = "claude-test"
        supports_structured_output = True

        def __init__(self):
            self.calls = []

        def generate(self, prompt):
            raise AssertionError("plain generation must not be used")

        def generate_structured(self, prompt, schema, *, tool_name):
            self.calls.append((schema, tool_name))
            text = json.dumps({
                "winners": {dim: "tie" for dim in GENESIS_DIMS},
                "evidence": ["same"] * len(GENESIS_DIMS),
            })
            return type("Out", (), {"text": text, "model_id": self.model_id})()

    model = StructuredModel()
    comparison = compare_genesis_candidates(
        {"title": "a"}, {"title": "b"}, model,
        label_a="A", label_b="B")

    assert len(model.calls) == 2
    assert all(schema == GENESIS_RESPONSE_SCHEMA for schema, _ in model.calls)
    assert all(name == "submit_genesis_verdict" for _, name in model.calls)
    assert comparison.judge_provenance["degraded"] is False


def test_swapped_prompts_keep_one_content_stable_review_order():
    a = {"title": "灰烬书", "logline": "a"}
    b = {"title": "群星书", "logline": "b"}
    prompts = []

    class Capture(_Model):
        def generate(self, prompt):
            prompts.append(prompt)
            return super().generate(prompt)

    compare_genesis_candidates(
        a, b, Capture([_response("A"), _response("B")]),
        label_a="A", label_b="B")

    order_lines = [
        tuple(line for line in prompt.splitlines()
              if "先独立审阅" in line or "再独立审阅" in line)
        for prompt in prompts
    ]
    assert order_lines[0] == order_lines[1]
