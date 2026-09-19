"""test_llm_contract_conformance.py — the LLM boundary contracts have a consumer.

llm-request.schema.json / llm-response.schema.json contract the ADR-005 LLM
boundary. The live layer is runtime/llm/types.py (LLMRequest / LLMResponse),
imported by execution/llm_model.py + deepseek_model.py + the scene planners and
round-tripped through the replay store. These tests are the schemas' CONSUMER:
they assert the live dataclasses serialize to schema-valid dicts, so a future
field added to the dataclass without updating the schema (the exact drift that
let `attempts` slip through additionalProperties:false) fails CI.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.llm.types import (
    LLMRequest, LLMResponse, TokenUsage, CostMetrics, ModelVersionPin,
    TemperatureContract, PromptMessage, PromptProvenance, to_dict,
    response_from_dict)

CONTRACTS = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard" / "contracts"
_REQ = Draft202012Validator(json.loads((CONTRACTS / "llm-request.schema.json").read_text(encoding="utf-8")))
_RES = Draft202012Validator(json.loads((CONTRACTS / "llm-response.schema.json").read_text(encoding="utf-8")))


def _errs(v, obj):
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in v.iter_errors(obj)]


def _request():
    return LLMRequest(
        request_id="LLM-" + "a" * 8, capability="ChapterDraft",
        messages=[PromptMessage("system", "you are a novelist"),
                  PromptMessage("user", "写第一章")],
        model_pin=ModelVersionPin("deepseek", "deepseek-chat", "1.0"),
        temperature=TemperatureContract(0.7, top_p=0.95),
        timeout_seconds=180, max_output_tokens=3000,
        prompt_provenance=PromptProvenance(
            "chapter-draft", "sha256:aa", None, None, "pkghash", [], "2026-07-04"))


def _response(**over):
    base = dict(
        request_id="LLM-" + "a" * 8, provider="deepseek", model="deepseek-chat",
        text="正文", finish_reason="stop",
        token_usage=TokenUsage(10, 20, 30),
        cost=CostMetrics("USD", 0.001, 0.002, 0.003, "2026-01"),
        latency_ms=120, response_hash="sha256:bb",
        provider_request_id="prov-1", replay_ref=None)
    base.update(over)
    return LLMResponse(**base)


def test_schemas_are_valid_draft2020():
    Draft202012Validator.check_schema(_REQ.schema)
    Draft202012Validator.check_schema(_RES.schema)


def test_live_request_dataclass_is_schema_valid():
    assert _errs(_REQ, to_dict(_request())) == []


def test_live_response_dataclass_is_schema_valid():
    assert _errs(_RES, to_dict(_response())) == []


def test_response_with_fallback_attempts_is_schema_valid():
    # the attempts trail (fallback.py) must validate — the drift that motivated
    # extending the schema. ok + transient_error entries both.
    resp = _response(attempts=[
        {"provider": "deepseek", "status": "transient_error", "error": "TimeoutError"},
        {"provider": "openai", "status": "ok"},
    ])
    assert _errs(_RES, to_dict(resp)) == []


def test_response_round_trips_through_dict():
    # response_from_dict is used by the replay store; a dict that validates must
    # rebuild into an equal dataclass.
    resp = _response(attempts=[{"provider": "deepseek", "status": "ok"}])
    d = to_dict(resp)
    assert _errs(_RES, d) == []
    assert response_from_dict(d) == resp
