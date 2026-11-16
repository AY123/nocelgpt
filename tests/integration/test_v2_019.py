"""Gateway contracts, durable SQLite accounting and actual loopback HTTP.

The HTTP server is an explicit local protocol fixture, not external OpenAI.
This suite does not make paid calls, write Canon, or prove actual vendor billing.
"""

import copy
import json
import os
import pickle
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Barrier, Event, Lock, Thread
from time import monotonic

import pytest

from anovel.canon.identity import canonical_bytes
from anovel.context.models import (
    ContextArtifact,
    ContextBudget,
    ContextItem,
    ContextRequest,
    ContextRole,
)
from anovel.gateway.ledger import BudgetLedger, DispatchPermit
from anovel.gateway.models import (
    BudgetBlocked,
    BudgetLimit,
    GatewayError,
    GatewayRequest,
    IdentityConflict,
    ModelPolicy,
    ProviderReply,
    RetryDecision,
    UnknownRetryRequired,
    Usage,
    validate_output,
)
from anovel.gateway.provider import OpenAIResponsesAdapter, response_payload
from anovel.gateway.service import ModelGateway

FUTURE = "2099-01-01T00:00:00Z"
SCHEMA = canonical_bytes(
    {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }
)


def context_for(*, role=ContextRole.WRITER, project="gateway-component", text="旧事实"):
    budget = ContextBudget(100000)
    identity = ContextRequest(
        project, "main", "sha256:" + "a" * 64, "b" * 64, role, budget
    )
    content = canonical_bytes({"fact": text})
    item = ContextItem(
        "fact-1",
        "FACT",
        content,
        "synthetic:test",
        sha256(content).hexdigest(),
        True,
        "required",
    )
    return ContextArtifact(
        project,
        "main",
        identity.parent_ref,
        identity.contract_hash,
        "c" * 64,
        "d" * 64,
        role,
        None,
        None,
        "e" * 64,
        identity.content_hash,
        (item,),
        (),
        budget,
    )


def policy_for(**changes):
    base = ModelPolicy(
        "primary",
        "local-model-v1",
        "http://127.0.0.1:1/v1/responses",
        1000,
        100,
        1_000_000,
        1_000_000,
        "synthetic-price-v1",
        FUTURE,
        timeout_seconds=1,
        test_mode=True,
    )
    return replace(base, **changes)


def request_for(*, policies=None, logical="chapter-scene", run="run-1", context=None):
    ctx = context or context_for()
    return GatewayRequest(
        ctx.project,
        ctx.branch,
        run,
        logical,
        ctx,
        "只返回场景正文。",
        "fixture-v1",
        SCHEMA,
        policies or (policy_for(),),
    )


def limit_for(request, **changes):
    return replace(
        BudgetLimit(
            request.project, request.branch, request.run_id, 100000, 10, FUTURE, 2, 2
        ),
        **changes,
    )


def ledger_for(tmp_path, request=None, **changes):
    request = request or request_for()
    ledger = BudgetLedger(tmp_path / "gateway-budget.sqlite3")
    ledger.provision(limit_for(request, **changes))
    return ledger


def success_reply(policy=None, *, marker="original", usage=None):
    policy = policy or policy_for()
    return ProviderReply(
        "SUCCESS",
        response_body=canonical_bytes({"synthetic": marker}),
        provider_request_id="request-" + marker,
        observed_model=policy.model,
        usage=usage or Usage(30, 10, 40),
        output_bytes=canonical_bytes({"text": marker}),
        http_status=200,
    )


def finish_attempt(ledger, request, attempt="a1", *, reply=None, policy=None):
    policy = policy or request.policies[0]
    assert ledger.reserve(request, policy, attempt) is None
    ledger.mark_dispatch(request.run_id, attempt)
    return ledger.finish(request, policy, attempt, reply or success_reply(policy))


@pytest.mark.parametrize(
    "kind", ["policy", "request", "budget", "usage", "retry", "reply", "result"]
)
def test_gateway_closed_records_roundtrip_and_reject_extra_fields(tmp_path, kind):
    request = request_for()
    result = finish_attempt(ledger_for(tmp_path, request), request)
    value = {
        "policy": request.policies[0],
        "request": request,
        "budget": limit_for(request),
        "usage": Usage(30, 10, 40),
        "retry": RetryDecision("test-authority", "test-retry", True),
        "reply": result.reply,
        "result": result,
    }[kind]
    restored = type(value).from_dict(value.to_dict())
    assert restored == value
    assert restored.to_bytes() == value.to_bytes()
    assert restored.content_hash == sha256(value.to_bytes()).hexdigest()
    with pytest.raises(GatewayError):
        type(value).from_dict({**value.to_dict(), "unexpected": "field"})


@pytest.mark.parametrize("bad", [True, -1, 0, 1.5, "10", None])
def test_budget_total_requires_positive_exact_integer(bad):
    with pytest.raises(GatewayError):
        limit_for(request_for(), total_microusd=bad)


@pytest.mark.parametrize("field", ["max_attempts", "max_inflight", "max_unknown"])
def test_budget_limits_cannot_use_boolean_or_zero(field):
    for bad in (True, 0):
        with pytest.raises(GatewayError):
            limit_for(request_for(), **{field: bad})


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://evil.invalid/v1/responses",
        "http://192.0.2.1/v1/responses",
        "http://127.0.0.1/v1/responses?key=x",
        "http://user:password@127.0.0.1/v1/responses",
        "http://127.0.0.1/v1/chat/completions",
    ],
)
def test_test_policy_only_allows_explicit_loopback_responses_endpoint(endpoint):
    with pytest.raises(GatewayError):
        policy_for(endpoint=endpoint)


@pytest.mark.parametrize(
    "params",
    [
        {"store": True},
        {"stream": True},
        {"input": "override"},
        {"max_output_tokens": 1},
        {"temperature": True},
    ],
)
def test_model_parameters_cannot_override_transport_or_use_boolean_number(params):
    with pytest.raises(GatewayError):
        policy_for(params_bytes=canonical_bytes(params))


@pytest.mark.parametrize("tokens", [(True, 1, 2), (-1, 1, 0), (1, 2, 4), (1.5, 1, 2.5)])
def test_usage_is_exact_and_additive(tokens):
    with pytest.raises(GatewayError):
        Usage(*tokens)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {}, "required": []},
        {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": [],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"text": {"$ref": "https://unavailable.invalid/schema"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    ],
)
def test_response_schema_must_be_closed_and_never_fetch_external_references(schema):
    with pytest.raises(GatewayError):
        replace(request_for(), schema_bytes=canonical_bytes(schema))


def test_response_schema_checks_actual_output_without_leaking_invalid_values():
    request = request_for()
    validate_output(request.schema, {"text": "合格的本地结构输出"})
    with pytest.raises(GatewayError) as failure:
        validate_output(request.schema, {"text": 3, "untrusted": "private-value"})
    assert "private-value" not in str(failure.value)


def test_schema_property_named_ref_is_data_and_local_reference_still_validates():
    schema = {
        "type": "object",
        "properties": {"$ref": {"$ref": "#/$defs/local"}},
        "required": ["$ref"],
        "additionalProperties": False,
        "$defs": {"local": {"type": "string"}},
    }
    request = replace(request_for(), schema_bytes=canonical_bytes(schema))
    validate_output(request.schema, {"$ref": "这是数据字段"})
    with pytest.raises(GatewayError):
        validate_output(request.schema, {"$ref": 17})


@pytest.mark.parametrize("position", ["$defs", "properties", "dependentSchemas"])
def test_nested_external_schema_reference_cannot_trigger_network_lookup(position):
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
        position: {"unsafe": {"$ref": "https://must-not-contact.invalid/schema"}},
    }
    with pytest.raises(GatewayError):
        replace(request_for(), schema_bytes=canonical_bytes(schema))


def test_no_body_unknown_has_no_fabricated_hash_and_received_empty_body_is_distinct():
    unknown = ProviderReply("UNKNOWN", error_code="INTERRUPTED_AFTER_DISPATCH")
    assert unknown.response_hash is None
    assert unknown.count_hash is None
    assert unknown.provider_request_id is None
    assert unknown.usage is None
    empty = ProviderReply("FAILED", response_body=b"", error_code="EMPTY")
    assert empty.response_hash == sha256(b"").hexdigest()
    assert empty.response_hash != unknown.response_hash
    forged = {**unknown.to_dict(), "response_hash": sha256(b"").hexdigest()}
    with pytest.raises(GatewayError):
        ProviderReply.from_dict(forged)


def test_request_scope_and_semantics_bind_safe_context_and_model_policy():
    request = request_for()
    with pytest.raises(GatewayError):
        replace(request, project="different-project")
    changed = [
        replace(request, instructions="变更指令"),
        replace(request, template_version="fixture-v2"),
        replace(request, context=context_for(text="changed fact")),
        replace(
            request,
            policies=(
                policy_for(model="local-model-v2", accepted_models=("local-model-v2",)),
            ),
        ),
    ]
    assert all(value.semantic_hash != request.semantic_hash for value in changed)
    with pytest.raises(FrozenInstanceError):
        request.logical_id = "mutable"


def test_unprovisioned_budget_blocks_before_adapter_is_invoked(tmp_path):
    class NeverSend:
        def send(self, *args):
            pytest.fail("unfunded request reached transport")

    with pytest.raises(GatewayError):
        ModelGateway(BudgetLedger(tmp_path / "empty.sqlite3"), NeverSend()).submit(
            request_for(), "primary", "a1"
        )


def test_durable_budget_cannot_be_reset_or_moved_to_another_scope(tmp_path):
    request = request_for()
    ledger = ledger_for(tmp_path, request)
    restarted = BudgetLedger(ledger.path)
    restarted.provision(limit_for(request))
    with pytest.raises(IdentityConflict):
        restarted.provision(limit_for(request, total_microusd=999999))
    with pytest.raises(IdentityConflict):
        restarted.reserve(
            request_for(context=context_for(project="other-project")),
            request.policies[0],
            "a1",
        )
    assert restarted.summary(request.run_id)["attempts"] == 0


@pytest.mark.parametrize(
    "field,value",
    [("instructions", "new instruction"), ("template_version", "new-template")],
)
def test_existing_logical_id_rejects_changed_request_even_after_success(
    tmp_path, field, value
):
    request = request_for()
    ledger = ledger_for(tmp_path, request)
    finish_attempt(ledger, request)
    with pytest.raises(IdentityConflict):
        ledger.reserve(replace(request, **{field: value}), request.policies[0], "a2")
    assert ledger.summary(request.run_id)["attempts"] == 1


def test_success_is_replayed_durably_without_new_attempt_or_reservation(tmp_path):
    request = request_for()
    ledger = ledger_for(tmp_path, request)
    original = finish_attempt(ledger, request)
    replay = BudgetLedger(ledger.path).reserve(
        request, request.policies[0], "never-sent"
    )
    assert replay is not None and replay.replayed
    assert replay.attempt_id == original.attempt_id
    assert replay.reply == original.reply
    assert ledger.summary(request.run_id)["attempts"] == 1
    assert ledger.summary(request.run_id)["spent_microusd"] == 40


@pytest.mark.parametrize("same_attempt", [True, False])
def test_concurrent_reservations_cannot_duplicate_attempt_or_double_spend(
    tmp_path, same_attempt
):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(
        tmp_path, request, total_microusd=policy.reserve_microusd, max_inflight=2
    )
    barrier = Barrier(2)

    def reserve(index):
        local = BudgetLedger(ledger.path)
        barrier.wait(timeout=5)
        try:
            local.reserve(
                request
                if same_attempt
                else replace(request, logical_id=f"logical-{index}"),
                policy,
                "a1" if same_attempt else f"a{index}",
            )
        except GatewayError:
            return "BLOCKED"
        return "RESERVED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, (0, 1)))
    assert sorted(outcomes) == ["BLOCKED", "RESERVED"]
    summary = ledger.summary(request.run_id)
    assert summary["attempts"] == 1
    assert summary["inflight_microusd"] == policy.reserve_microusd
    assert summary["spent_microusd"] == summary["unknown_microusd"] == 0


def test_prepared_recovery_keeps_reservation_until_proven_unsent_cancel(tmp_path):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request)
    ledger.reserve(request, policy, "a1")
    restarted = BudgetLedger(ledger.path)
    assert restarted.recover(request.run_id, "a1") is None
    assert (
        restarted.summary(request.run_id)["inflight_microusd"]
        == policy.reserve_microusd
    )
    restarted.cancel_prepared(request.run_id, "a1", "test proves adapter never invoked")
    summary = restarted.summary(request.run_id)
    assert summary["inflight_microusd"] == summary["unknown_microusd"] == 0
    assert summary["attempts"] == 1


def test_dispatched_recovery_is_unknown_and_cannot_release_by_cancelling(tmp_path):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request)
    ledger.reserve(request, policy, "a1")
    ledger.mark_dispatch(request.run_id, "a1")
    with pytest.raises(IdentityConflict):
        ledger.cancel_prepared(request.run_id, "a1", "cannot prove unsent")
    result = BudgetLedger(ledger.path).recover(request.run_id, "a1")
    assert result.status == "UNKNOWN"
    assert result.reply.response_body is result.reply.response_hash is None
    assert result.charge_status == "PENDING" and result.charge_microusd is None
    summary = ledger.summary(request.run_id)
    assert summary["unknown_microusd"] == policy.reserve_microusd
    assert summary["inflight_microusd"] == summary["spent_microusd"] == 0
    assert ledger.recover(request.run_id, "a1") == result


def test_unknown_retry_needs_explicit_risk_acceptance_and_preserves_first_liability(
    tmp_path,
):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request, total_microusd=policy.reserve_microusd * 2)
    finish_attempt(
        ledger, request, reply=ProviderReply("UNKNOWN", error_code="TEST_TIMEOUT")
    )
    for decision in (None, RetryDecision("test-authority", "retry", False)):
        with pytest.raises(UnknownRetryRequired):
            ledger.reserve(request, policy, "a2", decision)
    ledger.reserve(
        request,
        policy,
        "a2",
        RetryDecision("test-authority", "duplicate cost accepted", True),
    )
    summary = ledger.summary(request.run_id)
    assert (
        summary["unknown_microusd"]
        == summary["inflight_microusd"]
        == policy.reserve_microusd
    )
    assert summary["spent_microusd"] == 0
    with pytest.raises(BudgetBlocked):
        ledger.reserve(replace(request, logical_id="unrelated"), policy, "a3")


def test_unknown_count_cap_cannot_be_bypassed_by_risk_acceptance(tmp_path):
    request = request_for()
    ledger = ledger_for(tmp_path, request, max_unknown=1)
    finish_attempt(
        ledger, request, reply=ProviderReply("UNKNOWN", error_code="TEST_TIMEOUT")
    )
    with pytest.raises(BudgetBlocked):
        ledger.reserve(
            request,
            request.policies[0],
            "a2",
            RetryDecision("test-authority", "retry", True),
        )
    assert ledger.summary(request.run_id)["attempts"] == 1


def test_late_actual_reply_replaces_synthetic_recovery_but_not_first_success_pointer(
    tmp_path,
):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request)
    ledger.reserve(request, policy, "original")
    ledger.mark_dispatch(request.run_id, "original")
    unknown = ledger.recover(request.run_id, "original")
    assert unknown.status == "UNKNOWN"
    ledger.reserve(
        request,
        policy,
        "retry",
        RetryDecision("test-authority", "accepted pending responsibility", True),
    )
    ledger.mark_dispatch(request.run_id, "retry")
    first = ledger.finish(request, policy, "retry", success_reply(marker="retry"))
    late = ledger.finish(
        request, policy, "original", success_reply(marker="late-original")
    )
    assert late.status == "SUCCESS"
    assert ledger.lookup(request.run_id, request.logical_id) == first
    summary = ledger.summary(request.run_id)
    assert summary["spent_microusd"] == 80
    assert summary["unknown_microusd"] == summary["inflight_microusd"] == 0
    assert ledger.finish(request, policy, "original", late.reply) == late
    with pytest.raises(IdentityConflict):
        ledger.finish(request, policy, "original", success_reply(marker="changed"))


def test_pending_known_failure_reconciles_once_with_evidence_and_keeps_outcome(
    tmp_path,
):
    request = request_for()
    ledger = ledger_for(tmp_path, request)
    failed = finish_attempt(
        ledger,
        request,
        reply=ProviderReply(
            "FAILED",
            response_body=b'{"error":"rejected"}',
            http_status=400,
            error_code="HTTP_400",
        ),
    )
    assert failed.status == "FAILED" and failed.charge_status == "PENDING"
    with pytest.raises(GatewayError):
        ledger.reconcile(request.run_id, "a1", 0, "", "test-authority")
    settled = ledger.reconcile(
        request.run_id, "a1", 7, "synthetic:test-bill", "test-authority"
    )
    assert settled.status == "FAILED" and settled.charge_status == "VERIFIED"
    assert settled.reply == failed.reply
    assert (
        ledger.reconcile(
            request.run_id, "a1", 7, "synthetic:test-bill", "test-authority"
        )
        == settled
    )
    with pytest.raises(IdentityConflict):
        ledger.reconcile(request.run_id, "a1", 0, "different", "test-authority")
    assert ledger.summary(request.run_id)["spent_microusd"] == 7
    assert ledger.summary(request.run_id)["unknown_microusd"] == 0


@pytest.mark.parametrize("anomaly", ["model", "usage", "reconciliation"])
def test_observed_anomaly_freezes_run_without_dropping_cost_responsibility(
    tmp_path, anomaly
):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request)
    if anomaly == "reconciliation":
        finish_attempt(
            ledger, request, reply=ProviderReply("UNKNOWN", error_code="timeout")
        )
        ledger.reconcile(
            request.run_id,
            "a1",
            policy.reserve_microusd + 1,
            "synthetic:bill",
            "test-authority",
        )
    else:
        reply = (
            success_reply(usage=Usage(1001, 100, 1101))
            if anomaly == "usage"
            else replace(success_reply(), observed_model="unapproved-model")
        )
        result = finish_attempt(ledger, request, reply=reply)
        assert result.charge_status == "PENDING"
    summary = ledger.summary(request.run_id)
    assert summary["blocked"]
    assert (
        summary["spent_microusd"] + summary["unknown_microusd"]
        >= policy.reserve_microusd
    )
    with pytest.raises(BudgetBlocked):
        ledger.reserve(replace(request, logical_id="next-scene"), policy, "a2")


@pytest.mark.parametrize(
    "boundary", ["money", "attempts", "deadline", "price", "inflight"]
)
def test_original_budget_boundaries_are_enforced_before_reservation(tmp_path, boundary):
    request = request_for()
    policy = request.policies[0]
    now = datetime(2030, 1, 1, tzinfo=UTC)
    changes = (
        {"total_microusd": policy.reserve_microusd - 1} if boundary == "money" else {}
    )
    if boundary == "deadline":
        changes["deadline_at"] = now.isoformat()
    if boundary == "attempts":
        changes["max_attempts"] = 1
    if boundary == "inflight":
        changes["max_inflight"] = 1
    if boundary == "price":
        policy = replace(policy, price_expires_at=now.isoformat())
        request = replace(request, policies=(policy,))
    ledger = ledger_for(tmp_path, request, **changes)
    if boundary in {"attempts", "inflight"}:
        ledger.reserve(request, policy, "a1", now=now)
        if boundary == "attempts":
            ledger.cancel_prepared(request.run_id, "a1", "proven unsent", now=now)
        request = replace(request, logical_id="next")
    with pytest.raises(BudgetBlocked):
        ledger.reserve(request, policy, "blocked", now=now)


def test_deadline_is_rechecked_at_dispatch_and_does_not_release_reservation(tmp_path):
    request = request_for()
    now = datetime(2030, 1, 1, tzinfo=UTC)
    deadline = now + timedelta(seconds=1)
    ledger = ledger_for(tmp_path, request, deadline_at=deadline.isoformat())
    ledger.reserve(request, request.policies[0], "a1", now=now)
    with pytest.raises(BudgetBlocked):
        ledger.mark_dispatch(request.run_id, "a1", now=deadline)
    assert (
        ledger.summary(request.run_id)["inflight_microusd"]
        == request.policies[0].reserve_microusd
    )


def test_dispatch_permit_cannot_be_constructed_serialized_copied_or_reissued(tmp_path):
    request = request_for()
    policy = request.policies[0]
    with pytest.raises(GatewayError):
        DispatchPermit(
            request.semantic_hash, policy.content_hash, request.run_id, "a1", FUTURE
        )
    ledger = ledger_for(tmp_path, request)
    ledger.reserve(request, policy, "a1")
    permit = ledger.mark_dispatch(request.run_id, "a1")
    for operation in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError):
            operation(permit)
    with pytest.raises(AttributeError):
        permit.attempt_id = "changed"
    with pytest.raises(IdentityConflict):
        BudgetLedger(ledger.path).mark_dispatch(request.run_id, "a1")
    assert ledger.summary(request.run_id)["attempts"] == 1


@pytest.mark.parametrize("mismatch", ["request", "policy", "run"])
def test_dispatch_permit_rejects_changed_frozen_content_before_consumption(
    tmp_path, mismatch
):
    request = request_for()
    policy = request.policies[0]
    ledger = ledger_for(tmp_path, request)
    ledger.reserve(request, policy, "a1")
    permit = ledger.mark_dispatch(request.run_id, "a1")
    wrong_request, wrong_policy = request, policy
    if mismatch == "request":
        wrong_request = replace(request, instructions="changed scene")
    elif mismatch == "run":
        wrong_request = replace(request, run_id="other-run")
    else:
        wrong_policy = replace(
            policy, model="different-model", accepted_models=("different-model",)
        )
    with pytest.raises(IdentityConflict):
        permit.consume(wrong_request, wrong_policy, "a1")
    permit.consume(request, policy, "a1")
    with pytest.raises(IdentityConflict):
        permit.consume(request, policy, "a1")


def test_dispatch_permit_expiry_does_not_release_dispatched_cost(tmp_path):
    request = request_for()
    policy = request.policies[0]
    now = datetime(2030, 1, 1, tzinfo=UTC)
    deadline = now + timedelta(seconds=1)
    ledger = ledger_for(tmp_path, request, deadline_at=deadline.isoformat())
    ledger.reserve(request, policy, "a1", now=now)
    permit = ledger.mark_dispatch(request.run_id, "a1", now=now)
    with pytest.raises(BudgetBlocked):
        permit.consume(request, policy, "a1", now=deadline)
    result = ledger.recover(request.run_id, "a1", now=deadline)
    assert result.status == "UNKNOWN"
    assert result.reply.response_hash is None
    assert ledger.summary(request.run_id)["unknown_microusd"] == policy.reserve_microusd


def test_fallback_requires_frozen_policy_and_shares_original_attempt_budget(tmp_path):
    primary = policy_for()
    fallback = policy_for(
        id="fallback", model="local-model-v2", accepted_models=("local-model-v2",)
    )
    request = request_for(policies=(primary, fallback))
    ledger = ledger_for(tmp_path, request, max_attempts=2)
    finish_attempt(
        ledger,
        request,
        reply=ProviderReply("FAILED", response_body=b"bad", error_code="TEST_ERROR"),
    )
    decision = RetryDecision(
        "test-authority", "explicit fallback pending responsibility", True
    )
    ledger.reserve(request, fallback, "fallback-attempt", decision)
    ledger.mark_dispatch(request.run_id, "fallback-attempt")
    result = ledger.finish(
        request, fallback, "fallback-attempt", success_reply(fallback)
    )
    assert result.policy_hash == fallback.content_hash
    assert result.reply.observed_model == fallback.model
    restarted = BudgetLedger(ledger.path)
    with pytest.raises(BudgetBlocked):
        restarted.reserve(replace(request, logical_id="repair"), primary, "a3")
    with pytest.raises(IdentityConflict):
        restarted.provision(limit_for(request, max_attempts=99))
    assert restarted.summary(request.run_id)["attempts"] == 2


def test_adapter_exception_is_unknown_without_credential_text_or_blind_retry(tmp_path):
    class BrokenAdapter:
        calls = 0

        def send(self, *args):
            self.calls += 1
            raise OSError("synthetic-private-credential-must-not-be-recorded")

    request = request_for()
    adapter = BrokenAdapter()
    ledger = ledger_for(tmp_path, request)
    result = ModelGateway(ledger, adapter).submit(request, "primary", "a1")
    assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
    assert result.reply.response_hash is None
    assert b"synthetic-private-credential" not in result.to_bytes()
    assert adapter.calls == 1
    with pytest.raises(UnknownRetryRequired):
        ModelGateway(ledger, adapter).submit(request, "primary", "a2")
    assert adapter.calls == 1


class LocalResponses:
    """Real local HTTP transport with deterministic synthetic wire responses."""

    def __init__(self, *, mode="success", count=30, count_mode="success"):
        self.mode = mode
        self.count = count
        self.count_mode = count_mode
        self.requests = []
        self.response_bodies = []
        self.lock = Lock()
        self.received_generation = Event()
        self.release_timeout = Event()
        self.response_completed = Event()
        self.observer = None
        self.observed_reservations = []

    @property
    def count_requests(self):
        return [v for v in self.requests if v["path"].endswith("/input_tokens")]

    @property
    def generation_requests(self):
        return [v for v in self.requests if v["path"] == "/v1/responses"]

    def completed(self, model):
        row = {
            "id": "body-response-id-not-header-request-id",
            "model": model,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"text":"本地合成场景，不是模型生成。"}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 30, "output_tokens": 10, "total_tokens": 40},
        }
        if self.mode == "missing_usage":
            del row["usage"]
        elif self.mode == "invalid_usage":
            row["usage"]["total_tokens"] = 999
        elif self.mode == "wrong_model":
            row["model"] = "unexpected-local-model"
        elif self.mode == "incomplete":
            row["status"] = "incomplete"
        elif self.mode == "refusal":
            row["output"][0]["content"] = [
                {"type": "refusal", "refusal": "local refusal fixture"}
            ]
        elif self.mode == "schema":
            row["output"][0]["content"][0]["text"] = '{"text":37}'
        elif self.mode == "duplicate_output_key":
            row["output"][0]["content"][0]["text"] = '{"text":"first","text":"second"}'
        elif self.mode == "missing_model":
            del row["model"]
        elif self.mode == "wrong_role":
            row["output"][0]["role"] = "user"
        elif self.mode == "empty_output":
            row["output"] = []
        elif self.mode == "reasoning":
            row["output"].insert(0, {"type": "reasoning", "summary": []})
        elif self.mode == "unexpected_service_tier":
            row["service_tier"] = "priority"
        return row


@contextmanager
def loopback_server(**options):
    state = LocalResponses(**options)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            payload = json.loads(raw)
            with state.lock:
                state.requests.append(
                    {
                        "path": self.path,
                        "body": raw,
                        "payload": payload,
                        "placeholder_auth_matches": self.headers.get("Authorization")
                        == "Bearer not-a-key",
                    }
                )
                if state.observer is not None:
                    state.observed_reservations.append(state.observer())
            is_count = self.path == "/v1/responses/input_tokens"
            mode = state.count_mode if is_count else state.mode
            if not is_count:
                state.received_generation.set()
            if mode == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if mode == "timeout":
                state.release_timeout.wait(timeout=3)
                self.close_connection = True
                return
            if mode == "delayed":
                state.release_timeout.wait(timeout=2)
            status = 200
            headers = {
                "x-request-id": "count-header-id"
                if is_count
                else "generation-header-id"
            }
            if mode == "echo_header_credential":
                headers["x-request-id"] = "reflected-not-a-key"
            if mode.startswith("http_"):
                status = int(mode.removeprefix("http_"))
                body = b'{"error":{"type":"local_fixture_error"}}'
            elif mode == "redirect":
                status = 307
                headers["Location"] = "/must-not-follow"
                body = b'{"error":"local redirect fixture"}'
            elif mode == "malformed":
                body = b'{"not valid JSON'
            elif mode == "duplicate_json":
                body = b'{"status":"completed","status":"failed"}'
            elif mode == "nonfinite_json":
                body = b'{"status":NaN}'
            elif mode == "list_json":
                body = b"[]"
            elif mode == "invalid_utf8":
                body = b"\xff"
            elif mode == "oversize":
                body = b"x" * 4_000_001
            elif mode == "empty":
                body = b""
            elif mode == "echo_credential":
                body = b'{"unsafe_echo":"not-a-key"}'
            elif is_count:
                number = True if mode == "boolean" else state.count
                body = canonical_bytes(
                    {
                        "object": "wrong-kind"
                        if mode == "wrong_kind"
                        else "response.input_tokens",
                        "input_tokens": number,
                    }
                )
            else:
                body = canonical_bytes(state.completed(payload["model"]))
            with state.lock:
                state.response_bodies.append((self.path, body))
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                if mode == "slowdrip":
                    for byte in body:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        if state.release_timeout.wait(timeout=0.01):
                            break
                else:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if not is_count:
                    state.response_completed.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1/responses"
    thread = Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    try:
        yield state
    finally:
        state.release_timeout.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def http_gateway(tmp_path, server, **budget_changes):
    request = request_for(policies=(policy_for(endpoint=server.endpoint),))
    ledger = ledger_for(tmp_path, request, **budget_changes)
    adapter = OpenAIResponsesAdapter("not-a-key", allow_test_transport=True)
    return ModelGateway(ledger, adapter), request, ledger


def test_loopback_http_success_exact_protocol_context_and_pre_send_durable_reservation(
    tmp_path,
):
    with loopback_server() as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        server.observer = lambda: BudgetLedger(ledger.path).summary(request.run_id)
        result = gateway.submit(request, "primary", "wire-attempt")
        assert result.status == "SUCCESS"
        assert result.charge_status == "ESTIMATED" and result.charge_microusd == 40
        assert result.request_hash == request.semantic_hash
        assert result.policy_hash == request.policies[0].content_hash
        assert result.reply.provider_request_id == "generation-header-id"
        assert result.reply.count_request_id == "count-header-id"
        assert (
            result.reply.provider_request_id != "body-response-id-not-header-request-id"
        )
        assert result.reply.input_token_count == 30
        assert result.reply.usage == Usage(30, 10, 40)
        assert result.reply.observed_model == request.policies[0].model
        assert result.reply.response_body == server.response_bodies[-1][1]
        assert (
            result.reply.response_hash
            == sha256(server.response_bodies[-1][1]).hexdigest()
        )
        assert (
            result.reply.count_hash == sha256(server.response_bodies[0][1]).hexdigest()
        )
        assert result.reply.count_hash != result.reply.response_hash
        assert len(server.count_requests) == len(server.generation_requests) == 1
        generation = server.generation_requests[0]["payload"]
        assert generation["input"] == [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": request.context.model_bytes.decode()}
                ],
            }
        ]
        assert generation["instructions"] == request.instructions
        assert generation["model"] == request.policies[0].model
        assert generation["store"] is generation["stream"] is False
        assert generation["truncation"] == "disabled"
        assert generation["service_tier"] == "default"
        assert generation["max_output_tokens"] == request.policies[0].max_output_tokens
        assert generation["text"]["format"] == {
            "type": "json_schema",
            "name": "anovel_output",
            "schema": request.schema,
            "strict": True,
        }
        assert set(server.count_requests[0]["payload"]) == {
            "model",
            "input",
            "instructions",
            "text",
            "truncation",
        }
        assert server.generation_requests[0]["body"] == response_payload(
            request, request.policies[0]
        )
        assert b"content_base64" not in server.generation_requests[0]["body"]
        assert b"retained_inputs" not in server.generation_requests[0]["body"]
        assert all(row["placeholder_auth_matches"] for row in server.requests)
        assert all(
            row["attempts"] == 1
            and row["inflight_microusd"] == request.policies[0].reserve_microusd
            for row in server.observed_reservations
        )
        assert ledger.summary(request.run_id)["inflight_microusd"] == 0
        assert b"not-a-key" not in result.to_bytes()


def test_loopback_success_replay_after_restart_performs_no_additional_http(tmp_path):
    with loopback_server() as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        first = gateway.submit(request, "primary", "a1")
        restarted = ModelGateway(BudgetLedger(ledger.path), gateway.adapter)
        replay = restarted.submit(request, "primary", "unused-attempt")
        assert replay.replayed and replay.reply == first.reply
        assert len(server.requests) == 2
        assert ledger.summary(request.run_id)["attempts"] == 1
        assert ledger.summary(request.run_id)["spent_microusd"] == 40


@pytest.mark.parametrize(
    "mode,status,error",
    [
        ("schema", "FAILED", "OUTPUT_SCHEMA_INVALID"),
        ("duplicate_output_key", "FAILED", "OUTPUT_SCHEMA_INVALID"),
        ("malformed", "FAILED", "INVALID_RESPONSE_JSON"),
        ("duplicate_json", "FAILED", "INVALID_RESPONSE_JSON"),
        ("nonfinite_json", "FAILED", "INVALID_RESPONSE_JSON"),
        ("list_json", "FAILED", "INVALID_RESPONSE_JSON"),
        ("invalid_utf8", "FAILED", "INVALID_RESPONSE_JSON"),
        ("empty", "FAILED", "INVALID_RESPONSE_JSON"),
        ("refusal", "FAILED", "MODEL_REFUSAL"),
        ("incomplete", "FAILED", "RESPONSE_NOT_COMPLETED"),
        ("wrong_model", "FAILED", "UNEXPECTED_MODEL"),
        ("missing_model", "FAILED", "UNEXPECTED_MODEL"),
        ("wrong_role", "FAILED", "OUTPUT_SCHEMA_INVALID"),
        ("empty_output", "FAILED", "OUTPUT_SCHEMA_INVALID"),
        ("http_400", "FAILED", "HTTP_400"),
        ("http_401", "FAILED", "HTTP_401"),
        ("http_429", "FAILED", "HTTP_429"),
        ("http_500", "UNKNOWN", "HTTP_500"),
    ],
)
def test_loopback_response_classification_keeps_actual_body_and_never_blind_retries(
    tmp_path, mode, status, error
):
    with loopback_server(mode=mode) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == status
        assert result.reply.error_code == error
        assert result.reply.output_bytes is None
        assert result.reply.response_body == server.response_bodies[-1][1]
        assert (
            result.reply.response_hash
            == sha256(server.response_bodies[-1][1]).hexdigest()
        )
        assert len(server.count_requests) == len(server.generation_requests) == 1
        if result.reply.usage is None or mode in {"wrong_model", "missing_model"}:
            assert result.charge_status == "PENDING" and result.charge_microusd is None
            assert (
                ledger.summary(request.run_id)["unknown_microusd"]
                >= request.policies[0].reserve_microusd
            )
        else:
            assert result.charge_status == "ESTIMATED"
        assert ledger.summary(request.run_id)["attempts"] == 1


@pytest.mark.parametrize("mode", ["missing_usage", "invalid_usage"])
def test_loopback_valid_output_without_valid_usage_retains_full_pending_responsibility(
    tmp_path, mode
):
    with loopback_server(mode=mode) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "SUCCESS"
        assert result.reply.output_bytes is not None
        assert result.reply.usage is None
        assert result.charge_status == "PENDING" and result.charge_microusd is None
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )
        replay = gateway.submit(request, "primary", "unused")
        assert replay.replayed
        assert len(server.requests) == 2


@pytest.mark.parametrize("mode", ["disconnect", "timeout"])
def test_loopback_sent_but_unreceived_generation_is_unknown_without_response_hash(
    tmp_path, mode
):
    with loopback_server(mode=mode) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert server.received_generation.is_set()
        assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
        assert result.reply.response_body is result.reply.response_hash is None
        assert result.reply.provider_request_id is None
        assert result.reply.usage is None
        assert (
            result.reply.count_body is not None and result.reply.count_hash is not None
        )
        assert result.reply.count_request_id == "count-header-id"
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )
        recovered = ModelGateway(BudgetLedger(ledger.path), gateway.adapter).recover(
            request.run_id, "a1"
        )
        assert recovered == result
        assert len(server.generation_requests) == 1


@pytest.mark.parametrize(
    "count_mode",
    [
        "boolean",
        "wrong_kind",
        "malformed",
        "http_400",
        "disconnect",
        "timeout",
        "redirect",
        "invalid_utf8",
        "empty",
    ],
)
def test_loopback_unproven_count_never_starts_generation(tmp_path, count_mode):
    with loopback_server(count_mode=count_mode) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status in {"FAILED", "UNKNOWN"}
        assert len(server.count_requests) == 1 and len(server.generation_requests) == 0
        assert result.reply.response_body is result.reply.response_hash is None
        assert result.charge_status == "PENDING"
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )


@pytest.mark.parametrize("count,allowed", [(900, True), (901, False)])
def test_loopback_provider_count_plus_output_cap_controls_actual_model_window(
    tmp_path, count, allowed
):
    with loopback_server(count=count) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert request.context.estimated_units != count
        assert result.reply.input_token_count == count
        assert len(server.count_requests) == 1
        assert len(server.generation_requests) == int(allowed)
        if allowed:
            assert result.status == "SUCCESS"
        else:
            assert result.status == "FAILED"
            assert result.reply.error_code == "INPUT_WINDOW_EXCEEDED"
            assert result.reply.response_hash is None
        assert ledger.summary(request.run_id)["attempts"] == 1


def test_loopback_unfunded_or_unauthorized_policy_has_zero_http_requests(tmp_path):
    with loopback_server() as server:
        request = request_for(policies=(policy_for(endpoint=server.endpoint),))
        adapter = OpenAIResponsesAdapter("not-a-key", allow_test_transport=True)
        gateway = ModelGateway(BudgetLedger(tmp_path / "empty.sqlite3"), adapter)
        with pytest.raises(GatewayError):
            gateway.submit(request, "primary", "a1")
        with pytest.raises(GatewayError):
            gateway.submit(request, "not-frozen", "a2")
        assert server.requests == []


def test_loopback_test_transport_requires_explicit_opt_in_and_missing_permit_is_rejected(
    tmp_path,
):
    with loopback_server() as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        policy = request.policies[0]
        with pytest.raises(GatewayError):
            gateway.adapter.send(request, policy, "no-reservation", None)
        ledger.reserve(request, policy, "a1")
        permit = ledger.mark_dispatch(request.run_id, "a1")
        with pytest.raises(GatewayError):
            OpenAIResponsesAdapter("not-a-key").send(request, policy, "a1", permit)
        assert server.requests == []


def test_loopback_dispatch_ticket_is_single_use_and_wrong_identity_cannot_send(
    tmp_path,
):
    with loopback_server() as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        policy = request.policies[0]
        ledger.reserve(request, policy, "a1")
        permit = ledger.mark_dispatch(request.run_id, "a1")
        with pytest.raises(GatewayError):
            gateway.adapter.send(request, policy, "wrong-attempt", permit)
        assert server.requests == []
        reply = gateway.adapter.send(request, policy, "a1", permit)
        assert reply.outcome == "SUCCESS"
        assert len(server.requests) == 2
        with pytest.raises(GatewayError):
            gateway.adapter.send(request, policy, "a1", permit)
        assert len(server.requests) == 2


def test_loopback_reasoning_item_is_not_misread_as_text_or_discard_actual_output(
    tmp_path,
):
    with loopback_server(mode="reasoning") as server:
        gateway, request, _ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "SUCCESS"
        assert result.reply.output_bytes == canonical_bytes(
            {"text": "本地合成场景，不是模型生成。"}
        )
        assert (
            result.reply.response_hash
            == sha256(server.response_bodies[-1][1]).hexdigest()
        )
        assert len(server.requests) == 2


def test_loopback_oversized_received_response_keeps_pending_liability_without_partial_hash(
    tmp_path,
):
    with loopback_server(mode="oversize") as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "UNKNOWN"
        assert result.reply.response_body is result.reply.response_hash is None
        assert result.reply.count_hash is not None
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )
        assert len(server.generation_requests) == 1


def test_loopback_redirect_and_credential_echo_are_not_forwarded_or_recorded(tmp_path):
    with loopback_server(mode="redirect") as server:
        gateway, request, _ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "FAILED"
        assert result.reply.http_status == 307
        assert not any(v["path"] == "/must-not-follow" for v in server.requests)
    with loopback_server(mode="echo_credential") as server:
        gateway, request, _ledger = http_gateway(tmp_path / "echo", server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "UNKNOWN"
        assert result.reply.response_body is result.reply.response_hash is None
        assert b"not-a-key" not in result.to_bytes()
        assert b"not-a-key" not in repr(gateway.adapter).encode()


@pytest.mark.parametrize("reflected_at", ["count", "generation", "both"])
def test_loopback_reflected_credential_header_is_omitted_from_durable_result(
    tmp_path, reflected_at
):
    options = {
        "mode": "echo_header_credential"
        if reflected_at in {"generation", "both"}
        else "success",
        "count_mode": "echo_header_credential"
        if reflected_at in {"count", "both"}
        else "success",
    }
    with loopback_server(**options) as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "SUCCESS"
        assert b"not-a-key" not in result.to_bytes()
        if reflected_at in {"count", "both"}:
            assert result.reply.count_request_id is None
        if reflected_at in {"generation", "both"}:
            assert result.reply.provider_request_id is None
        assert (
            result.reply.response_hash
            == sha256(server.response_bodies[-1][1]).hexdigest()
        )
        assert (
            result.reply.count_hash == sha256(server.response_bodies[0][1]).hexdigest()
        )
        assert b"not-a-key" not in ledger.path.read_bytes()


def test_loopback_slow_drip_has_total_wait_bound_and_late_body_cannot_settle_unknown(
    tmp_path,
):
    with loopback_server(mode="slowdrip") as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        started = monotonic()
        result = gateway.submit(request, "primary", "a1")
        elapsed = monotonic() - started
        assert server.received_generation.is_set()
        assert elapsed < 2
        assert not server.response_completed.is_set()
        assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
        assert result.reply.response_body is result.reply.response_hash is None
        assert result.reply.count_hash is not None
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )
        # Let the one original wire operation actually finish. A late worker
        # has no persistence/callback path and cannot silently settle the run.
        assert server.response_completed.wait(timeout=6)
        assert BudgetLedger(ledger.path).recover(request.run_id, "a1") == result
        assert ledger.summary(request.run_id)["spent_microusd"] == 0
        assert len(server.generation_requests) == 1


def test_loopback_token_count_crossing_price_expiry_never_starts_generation(tmp_path):
    with loopback_server(count_mode="delayed") as server:
        policy = policy_for(
            endpoint=server.endpoint,
            timeout_seconds=3,
            price_expires_at=(datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
        )
        request = request_for(policies=(policy,))
        ledger = ledger_for(tmp_path, request)
        gateway = ModelGateway(
            ledger, OpenAIResponsesAdapter("not-a-key", allow_test_transport=True)
        )
        started = monotonic()
        result = gateway.submit(request, "primary", "a1")
        assert monotonic() - started < 1.8
        assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
        assert result.reply.response_hash is None
        assert len(server.count_requests) == 1
        assert server.generation_requests == []
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == policy.reserve_microusd
        )


def test_loopback_unexpected_service_tier_keeps_cost_pending_and_freezes_further_dispatch(
    tmp_path,
):
    with loopback_server(mode="unexpected_service_tier") as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        result = gateway.submit(request, "primary", "a1")
        assert result.status == "FAILED"
        assert result.reply.error_code == "UNEXPECTED_SERVICE_TIER"
        assert result.reply.usage is None
        assert result.charge_status == "PENDING"
        assert (
            result.reply.response_hash
            == sha256(server.response_bodies[-1][1]).hexdigest()
        )
        assert ledger.summary(request.run_id)["blocked"]
        assert (
            ledger.summary(request.run_id)["unknown_microusd"]
            == request.policies[0].reserve_microusd
        )
        with pytest.raises(BudgetBlocked):
            gateway.submit(
                replace(request, logical_id="another-scene"), "primary", "a2"
            )
        assert len(server.generation_requests) == 1


def probe_files(tmp_path, request, *, budget=None, configured_policy=None):
    request_path = tmp_path / "request.json"
    budget_path = tmp_path / "budget.json"
    policy_path = tmp_path / "model-policy.yaml"
    ledger_path = tmp_path / "entry.sqlite3"
    output_path = tmp_path / "result.json"
    request_path.write_bytes(request.to_bytes())
    budget_path.write_bytes((budget or limit_for(request)).to_bytes())
    policy_path.write_bytes((configured_policy or request.policies[0]).to_bytes())
    repository = Path(__file__).resolve().parents[2]
    command = [
        sys.executable,
        "-B",
        str(repository / "scripts/run_gateway_probe.py"),
        "--request",
        str(request_path),
        "--budget",
        str(budget_path),
        "--policy-file",
        str(policy_path),
        "--policy-id",
        request.policies[0].id,
        "--ledger",
        str(ledger_path),
        "--attempt-id",
        "probe-a1",
        "--output",
        str(output_path),
    ]
    return command, ledger_path, output_path


def run_probe(command, *, credential_present=False):
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    if credential_present:
        environment["OPENAI_API_KEY"] = "not-a-key"
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
        check=False,
    )


def test_probe_default_dry_run_has_no_ledger_or_http_and_private_output(tmp_path):
    with loopback_server() as server:
        request = request_for(policies=(policy_for(endpoint=server.endpoint),))
        command, ledger_path, output_path = probe_files(tmp_path, request)
        completed = run_probe(command, credential_present=True)
        assert completed.returncode == 0
        summary = json.loads(completed.stdout)
        assert summary["status"] == "DRY_RUN_VALIDATED"
        assert summary["credential_read"] is summary["network_enabled"] is False
        assert summary["live_authority"] == "NOT_ESTABLISHED_BY_THIS_SCRIPT"
        assert summary["request_hash"] == request.content_hash
        assert json.loads(output_path.read_bytes()) == summary
        assert output_path.stat().st_mode & 0o777 == 0o600
        assert not ledger_path.exists()
        assert server.requests == []
        assert "not-a-key" not in completed.stdout
        assert "not-a-key" not in completed.stderr


@pytest.mark.parametrize("mismatch", ["scope", "price_expired", "policy_file"])
def test_probe_rejects_invalid_frozen_prerequisites_before_output_or_ledger(
    tmp_path, mismatch
):
    request = request_for()
    budget = limit_for(request)
    configured = request.policies[0]
    if mismatch == "scope":
        budget = replace(budget, project="another-project")
    elif mismatch == "price_expired":
        configured = replace(configured, price_expires_at="2000-01-01T00:00:00Z")
        request = replace(request, policies=(configured,))
    else:
        configured = replace(configured, max_output_tokens=99)
    command, ledger_path, output_path = probe_files(
        tmp_path, request, budget=budget, configured_policy=configured
    )
    completed = run_probe(command)
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["status"] == "BLOCKED_OR_UNPROVEN_REVIEW_LEDGER"
    assert not ledger_path.exists()
    assert not output_path.exists()


def test_probe_existing_output_is_not_overwritten_and_has_no_ledger(tmp_path):
    command, ledger_path, output_path = probe_files(tmp_path, request_for())
    original = b"existing evidence must survive"
    output_path.write_bytes(original)
    completed = run_probe(command)
    assert completed.returncode == 1
    assert output_path.read_bytes() == original
    assert not ledger_path.exists()


@pytest.mark.parametrize("condition", ["test_policy", "missing_credential"])
def test_probe_live_entry_blocks_before_ledger_when_test_policy_or_credential_missing(
    tmp_path, condition
):
    policy = policy_for()
    if condition == "missing_credential":
        policy = replace(
            policy, endpoint="https://api.openai.com/v1/responses", test_mode=False
        )
    request = request_for(policies=(policy,))
    command, ledger_path, output_path = probe_files(tmp_path, request)
    completed = run_probe([*command, "--execute-live"])
    assert completed.returncode == 1
    assert not ledger_path.exists()
    if output_path.exists():
        assert (
            json.loads(output_path.read_bytes())["status"]
            == "BLOCKED_OR_UNPROVEN_REVIEW_LEDGER"
        )


def test_loopback_same_context_new_logical_id_is_not_a_cross_request_creative_cache(
    tmp_path,
):
    with loopback_server() as server:
        gateway, request, ledger = http_gateway(tmp_path, server)
        first = gateway.submit(request, "primary", "a1")
        second = gateway.submit(
            replace(request, logical_id="different-creative-request"), "primary", "a2"
        )
        assert not first.replayed and not second.replayed
        assert len(server.generation_requests) == 2
        assert ledger.summary(request.run_id)["attempts"] == 2
        assert ledger.summary(request.run_id)["spent_microusd"] == 80
