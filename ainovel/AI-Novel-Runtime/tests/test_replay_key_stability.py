"""test_replay_key_stability.py — replay key ignores operational fields.

A real DeepSeek commercial rerun re-billed every call because the replay key
hashed `timeout_seconds`: rerunning with a different --timeout produced a
different key and missed the cache. The replay key must key on the SEMANTIC
request (what was asked), not operational/volatile fields (how long we'll wait,
which call it is, when it rendered).
"""
from __future__ import annotations

from dataclasses import replace

from runtime.llm.types import (LLMRequest, PromptMessage, PromptProvenance,
                               TemperatureContract, new_request_id)
from runtime.llm.adapters.openai_compatible import openai_model_pin
from runtime.llm.replay import ReplayStore


def _request(*, timeout, request_id, rendered_at):
    return LLMRequest(
        request_id=request_id,
        capability="ChapterDraft",
        messages=[PromptMessage("system", "sys"), PromptMessage("user", "写一章")],
        model_pin=openai_model_pin(provider="deepseek", model="deepseek-v4-pro",
                                   api_base="https://api.deepseek.com"),
        temperature=TemperatureContract(temperature=0.7, top_p=None),
        timeout_seconds=timeout,
        max_output_tokens=4000,
        prompt_provenance=PromptProvenance(
            prompt_id="chapter-draft", prompt_hash="sha256:abc",
            template_id="chapter-draft", template_version="1.0.0",
            package_hash="sha256:pkg", derived_from=["CHR-00001@v1"],
            rendered_at=rendered_at),
        metadata={"bridge": "test"},
    )


def _key(tmp_path, req):
    return ReplayStore(tmp_path).key_for(req)


def test_timeout_does_not_change_replay_key(tmp_path):
    a = _request(timeout=600.0, request_id="R-1", rendered_at="t1")
    b = _request(timeout=60.0, request_id="R-1", rendered_at="t1")
    assert _key(tmp_path, a) == _key(tmp_path, b)


def test_request_id_and_rendered_at_do_not_change_replay_key(tmp_path):
    a = _request(timeout=120.0, request_id="R-1", rendered_at="2026-01-01T00:00:00Z")
    b = _request(timeout=120.0, request_id="R-2", rendered_at="2026-07-02T09:00:00Z")
    assert _key(tmp_path, a) == _key(tmp_path, b)


def test_prompt_change_DOES_change_replay_key(tmp_path):
    a = _request(timeout=120.0, request_id="R-1", rendered_at="t1")
    b = replace(a, messages=[PromptMessage("system", "sys"),
                             PromptMessage("user", "写一段完全不同的内容")])
    assert _key(tmp_path, a) != _key(tmp_path, b)


def test_max_tokens_still_changes_key(tmp_path):
    # max_output_tokens is semantic (it bounds what the model returns), so unlike
    # timeout it SHOULD remain part of the key.
    a = _request(timeout=120.0, request_id="R-1", rendered_at="t1")
    b = replace(a, max_output_tokens=1000)
    assert _key(tmp_path, a) != _key(tmp_path, b)
