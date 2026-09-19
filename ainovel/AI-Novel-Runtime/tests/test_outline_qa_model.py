import json
from pathlib import Path

import pytest

from runtime.outline.qa import (
    OUTLINE_REVIEW_CHECKS,
    OUTLINE_REVIEW_RESPONSE_SCHEMA,
    parse_outline_review_response,
    review_outline_with_model,
)


def _response(*, omit=None, severity="info", summary="总体可展开"):
    return json.dumps({
        "assessments": {
            check: {"severity": severity, "message": f"evidence-{check}"}
            for check in OUTLINE_REVIEW_CHECKS if check != omit
        },
        "summary": summary,
    })


@pytest.mark.parametrize("text", [
    _response(),
    f"```json\n{_response()}\n```",
])
def test_complete_json_and_markdown_json_parse(text):
    findings, summary, error = parse_outline_review_response(text)
    assert error is None
    assert summary == "总体可展开"
    assert [finding.check for finding in findings] == list(OUTLINE_REVIEW_CHECKS)


@pytest.mark.parametrize(("text", "error_part"), [
    (_response(omit=OUTLINE_REVIEW_CHECKS[-1]), "missing assessment"),
    (_response(severity="critical"), "invalid severity"),
    (_response(summary=""), "summary must be"),
    ("", "empty response"),
])
def test_invalid_contract_is_not_silently_accepted(text, error_part):
    findings, summary, error = parse_outline_review_response(text)
    assert findings is None
    assert summary is None
    assert error_part in error


class _Model:
    provider = "fake"
    model_id = "reviewer-v1"

    def __init__(self, response):
        self.response = response

    def generate(self, prompt):
        if isinstance(self.response, Exception):
            raise self.response
        return type("Out", (), {
            "text": self.response,
            "model_id": self.model_id,
        })()


def test_parse_failure_degrades_with_raw_response_and_hashes():
    report = review_outline_with_model(
        {"title": "完整大纲", "first_30_chapters": []}, _Model("not json"))
    data = report.to_dict()
    assert data["status"] == "degraded"
    assert data["gating"] is False
    assert data["provenance"]["parse_ok"] is False
    assert data["provenance"]["error"].startswith("parse error:")
    assert data["provenance"]["raw_response_summary"] == "not json"
    assert data["provenance"]["outline_hash"].startswith("sha256:")
    assert data["provenance"]["request_hash"].startswith("sha256:")
    assert data["provenance"]["response_hash"].startswith("sha256:")
    assert data["provenance"]["response_char_count"] == len("not json")


def test_provider_failure_degrades_with_error_provenance():
    report = review_outline_with_model({}, _Model(RuntimeError("offline")))
    data = report.to_dict()
    assert data["status"] == "degraded"
    assert data["findings"] == []
    assert "provider error: RuntimeError: offline" == data["provenance"]["error"]
    assert data["provenance"]["response_hash"] is None
    assert data["provenance"]["response_char_count"] == 0
    assert data["provenance"]["cost_status"] == "unpriced"


def test_structured_capable_model_uses_forced_outline_schema():
    class StructuredModel:
        provider = "claude"
        model_id = "claude-test"
        supports_structured_output = True

        def __init__(self):
            self.calls = []

        def generate(self, prompt):
            raise AssertionError("plain generation must not be used")

        def generate_structured(self, prompt, schema, *, tool_name):
            self.calls.append((prompt, schema, tool_name))
            return type("Out", (), {
                "text": _response(), "model_id": self.model_id,
            })()

    model = StructuredModel()
    report = review_outline_with_model({"title": "长篇"}, model)
    assert report.status == "completed"
    assert report.gating is False
    assert len(report.findings) == len(OUTLINE_REVIEW_CHECKS)
    assert model.calls[0][1] == OUTLINE_REVIEW_RESPONSE_SCHEMA
    assert model.calls[0][2] == "submit_outline_review"
    assert '"title": "长篇"' in model.calls[0][0]
    assert "message 不超过80个汉字" in model.calls[0][0]


def test_live_acceptance_summary_keeps_same_outline_and_auditable_results():
    path = (Path(__file__).parent / "fixtures" / "genesis-tournament-failures"
            / "outline-qa-live-acceptance-20260805.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    dual = data["same_outline_dual_model_acceptance"]
    assert dual["all_completed"] is True
    assert dual["all_parse_ok"] is True
    assert len(dual["results"]) == 2
    assert all(result["finding_count"] == len(OUTLINE_REVIEW_CHECKS)
               for result in dual["results"])
    assert all(result["request_hash"].startswith("sha256:")
               and result["response_hash"].startswith("sha256:")
               and result["token_usage"]["total_tokens"] > 0
               for result in dual["results"])
    workflow = data["workflow_acceptance"]
    assert workflow["hash_matches"] is True
    assert workflow["outline_hash"] == workflow["persisted_outline_hash"]
