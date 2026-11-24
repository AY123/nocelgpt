"""Kimi Gateway controls with synthetic responses on an actual local socket."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing, contextmanager
from dataclasses import replace
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from test_v2_019 import FUTURE, finish_attempt, ledger_for, policy_for, request_for

from anovel.canon.identity import canonical_bytes
from anovel.context.models import ContextRole
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import (
    KIMI_CHAT_ENDPOINT,
    KIMI_CHAT_PATH,
    KIMI_CONTEXT_WINDOW,
    KIMI_MODEL,
    BudgetBlocked,
    EstimateFeeBound,
    GatewayError,
    GatewayRequest,
    IdentityConflict,
    ModelPolicy,
    UnknownRetryRequired,
    Usage,
)
from anovel.gateway.provider import (
    KIMI_FIRST_GENERATION_TEMPLATE,
    KimiChatCompletionsAdapter,
)
from anovel.gateway.service import ModelGateway

COUNT_PATH = "/v1/tokenizers/estimate-token-count"
PLACEHOLDER = "synthetic-kimi-key"
ESTIMATE = {"data": {"total_tokens": 30}}
OUTPUT = {"text": "Kimi 回环夹具。"}


def completion():
    return {
        "id": "completion-body-id",
        "object": "chat.completion",
        "model": KIMI_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": canonical_bytes(OUTPUT).decode(),
                    "reasoning_content": "Synthetic reasoning is distinct from output.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 30,
            "completion_tokens": 15,
            "total_tokens": 45,
            "prompt_tokens_details": {"cached_tokens": 7, "cache_write_tokens": 3},
            "completion_tokens_details": {"reasoning_tokens": 9},
        },
    }


@contextmanager
def loopback(*, count=(200, ESTIMATE), generation=None):
    if generation is None:
        generation = (200, completion())
    state = SimpleNamespace(requests=[], responses=[], observe_reservation=None)
    release_timeout = Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            state.requests.append(
                (
                    self.path,
                    json.loads(body),
                    self.headers.get("Authorization") == "Bearer " + PLACEHOLDER,
                )
            )
            if state.observe_reservation is not None:
                state.observe_reservation()
            status, payload = {
                COUNT_PATH: count,
                KIMI_CHAT_PATH: generation,
            }.get(self.path, (404, {}))
            if status == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if status == "timeout":
                release_timeout.wait(timeout=3)
                self.close_connection = True
                return
            raw = payload if isinstance(payload, bytes) else canonical_bytes(payload)
            state.responses.append(raw)
            self.send_response(status)
            self.send_header(
                "x-request-id",
                "kimi-count-id" if self.path == COUNT_PATH else "kimi-generation-id",
            )
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    state.endpoint = f"http://127.0.0.1:{server.server_port}{KIMI_CHAT_PATH}"
    try:
        yield state
    finally:
        release_timeout.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def kimi_policy(endpoint, **changes):
    return replace(
        policy_for(),
        model=KIMI_MODEL,
        accepted_models=(KIMI_MODEL,),
        params_bytes=canonical_bytes({"reasoning_effort": "high"}),
        endpoint=endpoint,
        **changes,
    )


def gateway_for(tmp_path, server, **policy_changes):
    policy = kimi_policy(server.endpoint, **policy_changes)
    request = request_for(policies=(policy,))
    ledger = ledger_for(tmp_path, request)
    adapter = KimiChatCompletionsAdapter(PLACEHOLDER, allow_test_transport=True)
    return ModelGateway(ledger, adapter), request, policy


@pytest.mark.parametrize(
    ("mode", "status", "error"),
    [
        ("valid", "SUCCESS", None),
        ("invalid-schema", "FAILED", "OUTPUT_SCHEMA_INVALID"),
        ("unreceived", "UNKNOWN", "GENERATION_TRANSPORT_UNPROVEN"),
    ],
)
def test_kimi_first_generation_sends_one_post_with_durable_reservation(
    tmp_path, monkeypatch, mode, status, error
):
    policy = kimi_policy("http://127.0.0.1:1" + KIMI_CHAT_PATH)
    request = replace(
        request_for(policies=(policy,)),
        template_version=KIMI_FIRST_GENERATION_TEMPLATE,
    )
    ledger = ledger_for(tmp_path, request, max_attempts=1)
    adapter = KimiChatCompletionsAdapter(
        PLACEHOLDER, allow_test_transport=True, generation_only=True
    )
    calls = []
    body = completion()
    if mode == "invalid-schema":
        body["choices"][0]["message"]["content"] = '{"text":37}'
    raw = canonical_bytes(body)

    def wire(url, payload, timeout):
        calls.append(
            (url, json.loads(payload), timeout, ledger.summary(request.run_id))
        )
        if mode == "unreceived":
            raise TimeoutError()
        return 200, raw, "direct-generation-id"

    monkeypatch.setattr(adapter, "_post_wire", wire)
    result = ModelGateway(ledger, adapter).submit(request, policy.id, "single")

    [(url, payload, timeout, reserved)] = calls
    assert url == policy.endpoint and 0 < timeout <= policy.timeout_seconds
    assert payload["response_format"]["json_schema"]["schema"] == request.schema
    assert reserved["attempts"] == 1
    assert reserved["inflight_microusd"] == policy.reserve_microusd
    assert ledger.estimate_fee_bound(request.run_id, "single") is None
    assert result.status == status and result.reply.error_code == error
    assert result.reply.count_hash is None
    assert result.reply.count_request_id is None
    assert result.reply.input_token_count is None
    assert result.reply.output_bytes == (
        canonical_bytes(OUTPUT) if mode == "valid" else None
    )
    if mode == "unreceived":
        assert result.reply.response_hash is None and result.charge_status == "PENDING"
        assert ledger.summary(request.run_id)["unknown_microusd"] == (
            policy.reserve_microusd
        )
    else:
        assert result.reply.response_hash == sha256(raw).hexdigest()
        assert result.reply.provider_request_id == "direct-generation-id"
        assert result.reply.usage == Usage(30, 15, 45)
        assert result.charge_status == "ESTIMATED"
    assert PLACEHOLDER.encode() not in result.to_bytes()


@pytest.mark.parametrize(
    "change",
    [
        {"template_version": "fixture-v1"},
        {"instructions": "long" * 5000},
    ],
)
def test_kimi_first_generation_rejects_other_requests_before_http(
    tmp_path, monkeypatch, change
):
    policy = kimi_policy("http://127.0.0.1:1" + KIMI_CHAT_PATH)
    request = replace(
        request_for(policies=(policy,)),
        **({"template_version": KIMI_FIRST_GENERATION_TEMPLATE} | change),
    )
    ledger = ledger_for(tmp_path, request, max_attempts=1)
    adapter = KimiChatCompletionsAdapter(
        PLACEHOLDER, allow_test_transport=True, generation_only=True
    )

    def forbidden(*_args):
        pytest.fail("A different or oversized request escaped the first probe")

    monkeypatch.setattr(adapter, "_post", forbidden)
    result = ModelGateway(ledger, adapter).submit(request, policy.id, "invalid")
    assert result.status == "UNKNOWN"
    assert result.reply.error_code == "ADAPTER_INTERRUPTED"
    assert result.reply.response_hash is None and result.reply.count_hash is None


def test_kimi_sends_frozen_messages_effort_and_schema_only_after_reservation(tmp_path):
    with loopback() as server:
        gateway, request, policy = gateway_for(tmp_path, server)
        reservations = []
        server.observe_reservation = lambda: reservations.append(
            BudgetLedger(gateway.ledger.path).summary(request.run_id)
        )
        result = gateway.submit(request, policy.id, "kimi-attempt")
        reopened = ModelGateway(BudgetLedger(gateway.ledger.path), gateway.adapter)
        replay = reopened.submit(request, policy.id, "kimi-replay")

    assert result.status == "SUCCESS"
    assert result.request_hash == request.semantic_hash
    assert result.policy_hash == policy.content_hash
    assert result.reply.output_bytes == canonical_bytes(OUTPUT)
    assert result.reply.usage == Usage(30, 15, 45)
    assert result.charge_status == "ESTIMATED" and result.charge_microusd == 45
    assert replay.replayed and replay.attempt_id == result.attempt_id
    assert replay.reply == result.reply
    assert result.reply.input_token_count == 30
    assert result.reply.count_request_id == "kimi-count-id"
    assert result.reply.provider_request_id == "kimi-generation-id"
    assert result.reply.count_hash == sha256(server.responses[0]).hexdigest()
    assert result.reply.response_hash == sha256(server.responses[1]).hexdigest()
    assert [path for path, _, _ in server.requests] == [COUNT_PATH, KIMI_CHAT_PATH]
    _, estimate, count_auth = server.requests[0]
    _, generation, generation_auth = server.requests[1]
    assert count_auth and generation_auth
    assert estimate == {"model": KIMI_MODEL, "messages": generation["messages"]}
    assert generation["model"] == KIMI_MODEL
    assert generation["messages"][-1] == {
        "role": "user",
        "content": request.context.model_bytes.decode(),
    }
    assert request.instructions in generation["messages"][0]["content"]
    assert generation["reasoning_effort"] == "high"
    assert generation["max_completion_tokens"] == policy.max_output_tokens
    assert generation["stream"] is False
    assert generation["prompt_cache_options"] == {"mode": "implicit", "ttl": "5m"}
    assert generation["response_format"]["type"] == "json_schema"
    assert generation["response_format"]["json_schema"]["schema"] == request.schema
    assert generation["response_format"]["json_schema"]["strict"] is True
    assert not {"tools", "temperature", "top_p"} & generation.keys()
    assert all(
        row["attempts"] == 1 and row["inflight_microusd"] == policy.reserve_microusd
        for row in reservations
    )
    assert len(reservations) == 2
    assert PLACEHOLDER.encode() not in result.to_bytes()


@pytest.mark.parametrize(
    ("count", "status", "error"),
    [
        ((403, {"error": {"code": "test"}}), "FAILED", "COUNT_HTTP_403"),
        ((200, {"data": {}}), "FAILED", "INVALID_TOKEN_COUNT"),
        ((200, {"data": {"total_tokens": True}}), "FAILED", "INVALID_TOKEN_COUNT"),
        (
            (200, b'{"data":{"total_tokens":3,"total_tokens":4}}'),
            "FAILED",
            "INVALID_TOKEN_COUNT_BODY",
        ),
        ((200, {"data": {"total_tokens": 901}}), "FAILED", "INPUT_WINDOW_EXCEEDED"),
        (("disconnect", None), "UNKNOWN", "TOKEN_COUNT_UNPROVEN"),
    ],
)
def test_kimi_unusable_estimate_never_sends_generation(tmp_path, count, status, error):
    with loopback(count=count) as server:
        gateway, request, policy = gateway_for(tmp_path, server)
        result = gateway.submit(request, policy.id, "estimate-failure")
    assert result.status == status and result.reply.error_code == error
    assert [path for path, _, _ in server.requests] == [COUNT_PATH]
    assert result.reply.response_hash is None
    assert result.reply.output_bytes is None
    assert result.reply.count_hash == (
        sha256(server.responses[0]).hexdigest() if server.responses else None
    )
    assert result.charge_status == "PENDING"


def test_kimi_application_bound_is_independent_of_accounting_window(tmp_path):
    with loopback(count=(200, {"data": {"total_tokens": 16384}})) as server:
        gateway, request, policy = gateway_for(tmp_path, server, context_window=20000)
        result = gateway.submit(request, policy.id, "app-window")
    assert result.status == "FAILED"
    assert result.reply.error_code == "INPUT_WINDOW_EXCEEDED"
    assert [path for path, _, _ in server.requests] == [COUNT_PATH]


@pytest.mark.parametrize(
    ("prompt", "completion_tokens", "error"),
    [
        (16380, 15, "INPUT_WINDOW_EXCEEDED"),
        (30, 101, "OUTPUT_TOKEN_LIMIT_EXCEEDED"),
    ],
)
def test_kimi_rejects_observed_tokens_outside_frozen_limits(
    tmp_path, prompt, completion_tokens, error
):
    body = completion()
    total = prompt + completion_tokens
    body["usage"].update(
        prompt_tokens=prompt, completion_tokens=completion_tokens, total_tokens=total
    )
    with loopback(generation=(200, body)) as server:
        gateway, request, policy = gateway_for(tmp_path, server, context_window=20000)
        result = gateway.submit(request, policy.id, "observed-over-limit")
    assert result.status == "FAILED" and result.reply.error_code == error
    assert result.reply.output_bytes is None
    assert result.reply.usage == Usage(prompt, completion_tokens, total)
    assert result.reply.response_hash == sha256(server.responses[-1]).hexdigest()


@pytest.mark.parametrize(
    ("mode", "error", "frozen"),
    [
        ("wrong-model", "UNEXPECTED_MODEL", True),
        ("truncated", "RESPONSE_NOT_COMPLETED", False),
        ("invalid-schema", "OUTPUT_SCHEMA_INVALID", False),
        ("duplicate-keys", "OUTPUT_SCHEMA_INVALID", False),
        ("wrong-role", "OUTPUT_SCHEMA_INVALID", False),
        ("refused", "MODEL_REFUSAL", False),
        ("unexpected-tool", "RESPONSE_NOT_COMPLETED", False),
    ],
)
def test_kimi_rejects_unusable_generation_with_actual_reply(
    tmp_path, mode, error, frozen
):
    body = completion()
    choice = body["choices"][0]
    if mode == "wrong-model":
        body["model"] = "other-kimi-model"
    elif mode == "truncated":
        choice["finish_reason"] = "length"
    elif mode == "invalid-schema":
        choice["message"]["content"] = '{"text":37}'
    elif mode == "duplicate-keys":
        choice["message"]["content"] = '{"text":"A","text":"B"}'
    elif mode == "refused":
        choice["finish_reason"] = "content_filter"
    elif mode == "unexpected-tool":
        choice["message"]["tool_calls"] = [{"id": "synthetic-tool"}]
    else:
        choice["message"]["role"] = "user"
    with loopback(generation=(200, body)) as server:
        gateway, request, policy = gateway_for(tmp_path, server)
        result = gateway.submit(request, policy.id, "generation-rejected")
    assert result.status == "FAILED" and result.reply.error_code == error
    assert result.reply.output_bytes is None
    assert result.reply.response_hash == sha256(server.responses[-1]).hexdigest()
    assert gateway.ledger.summary(request.run_id)["blocked"] is frozen


@pytest.mark.parametrize(
    "mode",
    ["missing", "unbalanced", "invalid-reasoning", "invalid-cache", "zero-output"],
)
def test_kimi_valid_output_without_valid_usage_retains_pending_liability(
    tmp_path, mode
):
    body = completion()
    if mode == "missing":
        del body["usage"]
    elif mode == "unbalanced":
        body["usage"]["total_tokens"] = 900
    elif mode == "invalid-reasoning":
        body["usage"]["completion_tokens_details"]["reasoning_tokens"] = 16
    elif mode == "invalid-cache":
        body["usage"]["prompt_tokens_details"]["cache_write_tokens"] = 24
    else:
        body["usage"].update(completion_tokens=0, total_tokens=30)
        body["usage"]["completion_tokens_details"]["reasoning_tokens"] = 0
    with loopback(generation=(200, body)) as server:
        gateway, request, policy = gateway_for(tmp_path, server)
        result = gateway.submit(request, policy.id, "pending")
    assert result.status == "SUCCESS"
    assert result.reply.usage is None
    assert result.charge_status == "PENDING" and result.charge_microusd is None
    assert (
        gateway.ledger.summary(request.run_id)["unknown_microusd"]
        == policy.reserve_microusd
    )


@pytest.mark.parametrize("transport", ["disconnect", "timeout"])
def test_kimi_unreceived_generation_keeps_unknown_on_restart(tmp_path, transport):
    with loopback(generation=(transport, None)) as server:
        gateway, request, policy = gateway_for(tmp_path, server)
        result = gateway.submit(request, policy.id, "interrupted")
        reopened = ModelGateway(BudgetLedger(gateway.ledger.path), gateway.adapter)
        assert reopened.recover(request.run_id, "interrupted") == result
        with pytest.raises(UnknownRetryRequired):
            reopened.submit(request, policy.id, "unguarded-retry")
    assert result.status == "UNKNOWN"
    assert result.reply.error_code == "GENERATION_TRANSPORT_UNPROVEN"
    assert result.reply.response_hash is None and result.reply.count_hash is not None
    assert result.charge_status == "PENDING"
    assert [path for path, _, _ in server.requests] == [COUNT_PATH, KIMI_CHAT_PATH]


def test_kimi_blocks_unauthorized_and_unfunded_attempts_before_http(tmp_path):
    with loopback() as server:
        policy = kimi_policy(server.endpoint)
        request = request_for(policies=(policy,))
        adapter = KimiChatCompletionsAdapter(PLACEHOLDER, allow_test_transport=True)
        with pytest.raises(GatewayError, match="permit"):
            adapter.send(request, policy, "unauthorized")
        ledger = ledger_for(tmp_path, request, total_microusd=1)
        with pytest.raises(BudgetBlocked):
            ModelGateway(ledger, adapter).submit(request, policy.id, "unfunded")
    assert server.requests == []


def test_kimi_live_policy_serializes_roundtrips_and_checks_exact_transport():
    policy = kimi_policy(
        KIMI_CHAT_ENDPOINT, test_mode=False, context_window=KIMI_CONTEXT_WINDOW
    )
    assert policy.is_kimi
    assert ModelPolicy.from_dict(policy.to_dict()).to_bytes() == policy.to_bytes()
    for endpoint in (
        "http://api.moonshot.cn/v1/chat/completions",
        "https://api.moonshot.ai/v1/chat/completions",
        "https://api.moonshot.cn/v1/chat/completions?key=test",
        "https://api.moonshot.cn/v1/responses",
    ):
        with pytest.raises(GatewayError):
            replace(policy, endpoint=endpoint)
    with pytest.raises(GatewayError):
        replace(policy, context_window=16384)
    with pytest.raises(GatewayError):
        replace(policy, params_bytes=canonical_bytes({"reasoning_effort": "max"}))
    assert not policy_for().is_kimi


@pytest.fixture
def request_preparation_dir():
    root = Path(__file__).resolve().parents[2]
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="kimi-request-test-", dir=dist) as directory:
        yield root, Path(directory)


def prepare_request_cli(root, output, *arguments):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "plan/validation/execution/V2-019/probe/prepare_request.py",
            "--output",
            str(output),
            *arguments,
        ],
        cwd=root,
        env={"PATH": os.defpath, "PYTHONPATH": str(root / "src")},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        start_new_session=True,
        timeout=60,
    )


def test_kimi_request_preparation_freezes_explicit_policy_and_raw_hashes(
    request_preparation_dir,
):
    root, directory = request_preparation_dir
    policy = kimi_policy(
        KIMI_CHAT_ENDPOINT,
        test_mode=False,
        context_window=KIMI_CONTEXT_WINDOW,
        price_ref="synthetic-request-preparation-only",
    )
    policy_path = directory / "policy.json"
    policy_path.write_text(json.dumps(policy.to_dict(), indent=2) + "\n")
    output = directory / "request.json"
    arguments = ("--policy-file", str(policy_path), "--run-id", "kimi-preparation-test")
    completed = prepare_request_cli(root, output, *arguments)
    assert completed.returncode == 0, completed.stderr

    raw = output.read_bytes()
    request = GatewayRequest.from_dict(json.loads(raw))
    receipt = json.loads(completed.stdout)
    assert raw == request.to_bytes()
    assert request.run_id == "kimi-preparation-test"
    assert request.context.role is ContextRole.WRITER
    assert request.template_version == "gateway-protocol-probe-v1"
    assert request.policies == (policy,)
    assert request.schema == {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }
    assert output.stat().st_mode & 0o777 == 0o600
    assert receipt["status"] == "PREPARED_NO_NETWORK"
    assert receipt["provider"] == "KIMI"
    assert receipt["live_authority"] is False and receipt["live_calls"] == 0
    assert receipt["context_bytes"] == len(request.context.model_bytes)
    assert receipt["policy_hash"] == policy.content_hash
    assert receipt["policy_file_sha256"] == sha256(policy_path.read_bytes()).hexdigest()
    assert receipt["policy_file_sha256"] != receipt["policy_hash"]
    assert receipt["request_file_sha256"] == sha256(raw).hexdigest()
    assert receipt["request_hash"] == request.content_hash

    repeated = prepare_request_cli(root, output, *arguments)
    assert repeated.returncode != 0
    assert output.read_bytes() == raw
    assert {path.name for path in directory.iterdir()} == {
        "policy.json",
        "request.json",
    }
    missing = directory / "missing.json"
    alias = directory / "alias.json"
    alias.symlink_to(missing)
    rejected = prepare_request_cli(root, alias, *arguments)
    assert rejected.returncode != 0
    assert alias.is_symlink() and not missing.exists()


@pytest.mark.parametrize(
    "invalid",
    [
        "foreign-endpoint",
        "loopback",
        "missing-run",
        "legacy-run",
        "expired",
        "oversize",
        "timeout",
        "zero-rate",
    ],
)
def test_kimi_request_preparation_refuses_invalid_inputs(
    request_preparation_dir, invalid
):
    root, directory = request_preparation_dir
    policy = kimi_policy(
        KIMI_CHAT_ENDPOINT,
        test_mode=False,
        context_window=KIMI_CONTEXT_WINDOW,
        price_ref="synthetic-request-preparation-only",
    ).to_dict()
    run_arguments = ["--run-id", "kimi-preparation-test"]
    if invalid == "foreign-endpoint":
        policy["endpoint"] = "https://api.moonshot.ai/v1/chat/completions"
    elif invalid == "loopback":
        policy.update(endpoint="http://127.0.0.1:1/v1/chat/completions", test_mode=True)
    elif invalid == "missing-run":
        run_arguments = []
    elif invalid == "legacy-run":
        run_arguments[-1] = "v2019-openai-probe-20261116"
    elif invalid == "expired":
        policy["price_expires_at"] = "2000-01-01T00:00:00.000000Z"
    elif invalid == "oversize":
        policy["max_output_tokens"] = 1025
    elif invalid == "timeout":
        policy["timeout_seconds"] = 31
    else:
        policy["input_rate"] = 0

    policy_path = directory / "policy.json"
    policy_path.write_bytes(canonical_bytes(policy))
    output = directory / "request.json"
    completed = prepare_request_cli(
        root, output, "--policy-file", str(policy_path), *run_arguments
    )
    assert completed.returncode != 0
    assert not output.exists()
    assert {path.name for path in directory.iterdir()} == {"policy.json"}


def test_request_preparation_preserves_default_openai_request(request_preparation_dir):
    root, directory = request_preparation_dir
    output = directory / "legacy.json"
    completed = prepare_request_cli(root, output)
    assert completed.returncode == 0, completed.stderr
    raw = output.read_bytes()
    record = json.loads(raw)
    request = GatewayRequest.from_dict(record)
    assert request.run_id == "v2019-openai-probe-20261116"
    assert request.logical_id == "protocol-scene-1"
    assert request.context.role is ContextRole.WRITER
    assert request.policies == (
        ModelPolicy.from_dict(json.loads((root / "model-policy.yaml").read_bytes())),
    )
    assert raw == (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
    assert json.loads(completed.stdout) == {
        "status": "PREPARED_NO_NETWORK",
        "request_hash": request.content_hash,
        "context_bytes": len(request.context.model_bytes),
        "live_calls": 0,
    }


def paid_estimate_fixture(
    tmp_path, endpoint="http://127.0.0.1:1" + KIMI_CHAT_PATH, *, deficit=0
):
    policy = kimi_policy(endpoint)
    request = request_for(policies=(policy,))
    fee = EstimateFeeBound(
        50, sha256(b"synthetic estimator tariff").hexdigest(), FUTURE
    )
    total = policy.reserve_microusd + fee.maximum_microusd
    ledger = ledger_for(
        tmp_path, request, total_microusd=total - deficit, max_attempts=1
    )
    return request, policy, fee, ledger, total


def test_paid_estimate_insufficient_aggregate_budget_sends_no_http(tmp_path):
    with loopback() as server:
        request, policy, fee, ledger, _ = paid_estimate_fixture(
            tmp_path, server.endpoint, deficit=1
        )
        adapter = KimiChatCompletionsAdapter(PLACEHOLDER, allow_test_transport=True)
        with pytest.raises(BudgetBlocked, match="cannot cover this reservation"):
            ModelGateway(ledger, adapter).submit(
                request, policy.id, "a1", estimate_fee=fee
            )
        assert not server.requests
        assert ledger.summary(request.run_id)["attempts"] == 0
        assert ledger.lookup(request.run_id, request.logical_id) is None


@pytest.mark.parametrize("overrun", [False, True])
def test_paid_estimate_success_retains_count_liability_until_split_reconciliation(
    tmp_path, overrun
):
    with loopback() as server:
        request, policy, fee, ledger, total = paid_estimate_fixture(
            tmp_path, server.endpoint
        )
        adapter = KimiChatCompletionsAdapter(PLACEHOLDER, allow_test_transport=True)
        observed_before_post = []

        def observe():
            durable = BudgetLedger(ledger.path)
            observed_before_post.append(
                (
                    durable.summary(request.run_id)["inflight_microusd"],
                    durable.estimate_fee_bound(request.run_id, "a1"),
                )
            )

        server.observe_reservation = observe
        first = ModelGateway(ledger, adapter).submit(
            request, policy.id, "a1", estimate_fee=fee
        )
        reopened = BudgetLedger(ledger.path)
        gateway = ModelGateway(reopened, adapter)
        replay = gateway.submit(request, policy.id, "a2", estimate_fee=fee)
        assert [row[0] for row in server.requests] == [COUNT_PATH, KIMI_CHAT_PATH]
        assert replay.replayed and replay.attempt_id == first.attempt_id
        assert replay.charge_status == "PENDING"
        with pytest.raises(IdentityConflict, match="frozen estimate fee bound"):
            gateway.submit(request, policy.id, "a3")

    assert observed_before_post == [(total, fee), (total, fee)]
    assert first.status == "SUCCESS" and first.reply.usage == Usage(30, 15, 45)
    assert first.charge_status == "PENDING" and first.charge_microusd is None
    assert first.reserved_microusd == total
    held = reopened.summary(request.run_id)
    assert held["attempts"] == held["unknown_attempts"] == 1
    assert held["unknown_microusd"] == 45 + fee.maximum_microusd
    assert held["inflight_microusd"] == held["spent_microusd"] == 0
    with pytest.raises(
        GatewayError, match="account for the original estimate separately"
    ):
        reopened.reconcile(request.run_id, "a1", 45, "fixture-bill", "fixture-owner")
    assert reopened.summary(request.run_id) == held

    # An estimator overrun must freeze the run even when the aggregate
    # charge is below its combined reservation.
    paid_estimate = fee.maximum_microusd + (1 if overrun else -1)
    args = (request.run_id, "a1", 45 + paid_estimate, "fixture-bill", "fixture-owner")
    settled = reopened.reconcile(*args, estimate_charge_microusd=paid_estimate)
    assert settled.charge_status == "VERIFIED"
    assert settled.charge_microusd == 45 + paid_estimate < total
    durable = BudgetLedger(ledger.path)
    assert durable.reconcile(*args, estimate_charge_microusd=paid_estimate) == settled
    with pytest.raises(IdentityConflict, match="different reconciliation"):
        durable.reconcile(*args, estimate_charge_microusd=paid_estimate - 1)
    assert durable.estimate_fee_bound(request.run_id, "a1") == fee
    paid = durable.summary(request.run_id)
    assert paid["unknown_microusd"] == 0
    assert paid["spent_microusd"] == settled.charge_microusd
    assert paid["blocked"] is overrun


def test_paid_estimate_unconfirmed_count_sends_no_generation_and_holds_both_costs(
    tmp_path,
):
    with loopback(count=("disconnect", None)) as server:
        request, policy, fee, ledger, total = paid_estimate_fixture(
            tmp_path, server.endpoint
        )
        adapter = KimiChatCompletionsAdapter(PLACEHOLDER, allow_test_transport=True)
        result = ModelGateway(ledger, adapter).submit(
            request, policy.id, "a1", estimate_fee=fee
        )
        assert [row[0] for row in server.requests] == [COUNT_PATH]

    assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
    assert result.reply.count_hash is None and result.reply.response_hash is None
    durable = BudgetLedger(ledger.path)
    assert durable.recover(request.run_id, "a1") == result
    assert durable.estimate_fee_bound(request.run_id, "a1") == fee
    assert durable.summary(request.run_id)["unknown_microusd"] == total


def test_paid_estimate_restarts_after_dispatch_claim_with_full_pending_hold(tmp_path):
    request, policy, fee, ledger, total = paid_estimate_fixture(tmp_path)
    assert ledger.reserve(request, policy, "a1", estimate_fee=fee) is None
    ledger.mark_dispatch(request.run_id, "a1")
    durable = BudgetLedger(ledger.path)
    with pytest.raises(IdentityConflict, match="never-dispatched"):
        durable.cancel_prepared(request.run_id, "a1", "fixture cancellation")
    result = durable.recover(request.run_id, "a1")
    assert result is not None
    assert result.status == "UNKNOWN" and result.charge_status == "PENDING"
    assert result.reply.error_code == "INTERRUPTED_AFTER_DISPATCH"
    assert durable.estimate_fee_bound(request.run_id, "a1") == fee
    assert durable.summary(request.run_id)["unknown_microusd"] == total


def test_paid_estimate_missing_side_record_refuses_dispatch(tmp_path):
    request, policy, fee, ledger, _ = paid_estimate_fixture(tmp_path)
    assert ledger.reserve(request, policy, "a1", estimate_fee=fee) is None
    with closing(sqlite3.connect(ledger.path)) as connection, connection:
        connection.execute(
            "DELETE FROM estimate_fee_bounds WHERE run_id=? AND attempt_id=?",
            (request.run_id, "a1"),
        )
    with pytest.raises(GatewayError, match="corrupt persisted estimate"):
        BudgetLedger(ledger.path).mark_dispatch(request.run_id, "a1")


def test_paid_estimate_additive_schema_retains_legacy_results_and_totals(tmp_path):
    request = request_for()
    ledger = ledger_for(tmp_path, request)
    first = finish_attempt(ledger, request)
    totals = ledger.summary(request.run_id)
    with closing(sqlite3.connect(ledger.path)) as connection, connection:
        connection.execute("DROP TABLE estimate_fee_bounds")

    reopened = BudgetLedger(ledger.path)
    replay = reopened.lookup(request.run_id, request.logical_id)
    assert replay is not None and replay.to_bytes() == first.to_bytes()
    assert reopened.estimate_fee_bound(request.run_id, first.attempt_id) is None
    assert reopened.summary(request.run_id) == totals
