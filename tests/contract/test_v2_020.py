"""Offline Workflow-to-Draft slice, not complete AT-V2-020 certification.

Contract and Context compilation, Gateway admission and both SQLite stores are
real. The explicit local adapter supplies synthetic boundary responses without
HTTP or credentials. Synthetic author/root inputs are not human or PostgreSQL
evidence. Overlay, extraction, production Permit and acceptance remain pending.
"""

import json
import socket
import sqlite3
import subprocess
import sys
import unicodedata
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_v2_017 import BRANCH, PROJECT, make_case

import anovel.workflow.__main__ as workflow_cli
from anovel.canon.identity import canonical_bytes
from anovel.context.compiler import compile_context
from anovel.context.models import (
    ContextBudget,
    ContextRequest,
    ContextRole,
    FrozenContextInputs,
)
from anovel.contracts.compiler import compile_contract
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import (
    BudgetLimit,
    ModelPolicy,
    ProviderReply,
    RetryDecision,
    Usage,
)
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.store import WorkflowStore

FUTURE = "2099-01-01T00:00:00Z"
RUN = "offline-workflow-run"
LOGICAL = "offline-chapter-request"
ATTEMPT = "offline-attempt-1"
BODY = "离线契约测试数据，不是小说样章。".encode()
EDIT = "离线人工修订数据，只用于验证版本血缘。".encode()
_DEFAULT_OUTPUT = object()


@pytest.fixture(autouse=True)
def no_network_or_provider_construction(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("These Workflow tests must not use a network or Provider")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)


def policy_for(**changes):
    # All amounts and the distant expiry belong to this synthetic local fixture.
    return replace(
        ModelPolicy(
            "offline-primary",
            "offline-model-v1",
            "http://127.0.0.1:1/v1/responses",
            16384,
            1024,
            1_000_000,
            1_000_000,
            "synthetic-local-price-not-provider-billing",
            FUTURE,
            timeout_seconds=1,
            test_mode=True,
        ),
        **changes,
    )


def source_case(
    *,
    anchor="urban.business.realistic",
    review="APPROVED",
    max_units=100000,
    instructions="只返回闭合JSON对象中的text测试正文。",
    policies=None,
):
    fixture, history, view = make_case(anchor=anchor, review=review)
    policies = policies or (policy_for(),)
    budget = ContextBudget(max_units)
    frozen = FrozenChapterInput.freeze(
        history=history,
        chapter_id=fixture.vision.chapters[0].id,
        fixture=fixture,
        view=view,
        budget=budget,
        policies=policies,
        instructions=instructions,
        template_version="offline-workflow-fixture-v1",
    )
    return SimpleNamespace(
        frozen=frozen,
        fixture=fixture,
        history=history,
        view=view,
        budget=budget,
        policies=policies,
    )


class SimulatedProcessExit(BaseException):
    """Bypass normal adapter-error handling to exercise dispatched recovery."""


class CountingLocalAdapter:
    def __init__(
        self,
        *,
        outcome="SUCCESS",
        output=_DEFAULT_OUTPUT,
        usage=Usage(20, 10, 30),
        observed_model=None,
        crash=False,
        exception=None,
    ):
        self.outcome = outcome
        self.output = {"text": BODY.decode()} if output is _DEFAULT_OUTPUT else output
        self.usage = usage
        self.observed_model = observed_model
        self.crash = crash
        self.exception = exception
        self.calls = 0
        self.requests = []

    def send(self, request, policy, attempt_id, permit):
        permit.consume(request, policy, attempt_id)
        self.calls += 1
        self.requests.append(request)
        if self.crash:
            raise SimulatedProcessExit("synthetic interruption after dispatch")
        if self.exception is not None:
            raise self.exception
        if self.outcome != "SUCCESS":
            return ProviderReply(
                self.outcome,
                response_body=canonical_bytes({"synthetic_outcome": self.outcome}),
                error_code="SYNTHETIC_" + self.outcome,
                http_status=400 if self.outcome == "FAILED" else None,
            )
        return ProviderReply(
            "SUCCESS",
            response_body=canonical_bytes({"synthetic_output": self.output}),
            provider_request_id="synthetic-workflow-response",
            observed_model=self.observed_model or policy.model,
            usage=self.usage,
            output_bytes=canonical_bytes(self.output),
            http_status=200,
        )


def harness(tmp_path, *, adapter=None, provision=True):
    adapter = adapter or CountingLocalAdapter()
    store_path = tmp_path / "workflow.sqlite"
    ledger_path = tmp_path / "gateway.sqlite"
    ledger = BudgetLedger(ledger_path)
    if provision:
        ledger.provision(BudgetLimit(PROJECT, BRANCH, RUN, 100000, 3, FUTURE, 1, 1))
    store = WorkflowStore(store_path)
    gateway = ModelGateway(ledger, adapter)
    return SimpleNamespace(
        adapter=adapter,
        ledger=ledger,
        gateway=gateway,
        store=store,
        store_path=store_path,
        ledger_path=ledger_path,
        workflow=ChapterWorkflow(store, gateway),
    )


def start(env, case, **changes):
    arguments = {
        "run_id": RUN,
        "logical_id": LOGICAL,
        "attempt_id": ATTEMPT,
        "policy_id": case.policies[0].id,
    }
    arguments.update(changes)
    return env.workflow.start(case.frozen, **arguments)


def reopen(env):
    adapter = CountingLocalAdapter()
    ledger = BudgetLedger(env.ledger_path)
    workflow = ChapterWorkflow(
        WorkflowStore(env.store_path), ModelGateway(ledger, adapter)
    )
    return workflow, ledger, adapter


def recover(workflow, case):
    return workflow.recover(case.frozen, project=PROJECT, branch=BRANCH, run_id=RUN)


def recovery_database_bytes(*paths):
    return {
        candidate: candidate.read_bytes()
        for path in paths
        for candidate in path.parent.glob(path.name + "*")
        if candidate.is_file()
    }


def recovery_result_metadata(result):
    return {
        "status": result.status,
        "charge_status": result.charge_status,
        "result_hash": sha256(result.to_bytes()).hexdigest(),
        "response_hash": result.reply.response_hash,
    }


@pytest.mark.parametrize(
    "anchor", ["urban.business.realistic", "fantasy.eastern.progression"]
)
def test_real_compilers_gateway_and_sqlite_publish_a_retained_draft(tmp_path, anchor):
    case, env = source_case(anchor=anchor), harness(tmp_path)
    result = start(env, case)
    expected = compile_contract(
        case.history, case.fixture.vision.chapters[0].id, case.fixture, case.view
    )
    assert expected.ok and expected.contract is not None
    writer = compile_context(
        FrozenContextInputs.from_contract(
            expected.contract,
            ContextRequest(
                PROJECT,
                BRANCH,
                case.view.parent_ref,
                expected.contract.content_hash,
                ContextRole.WRITER,
                case.budget,
            ),
        )
    )
    assert writer.ok and writer.artifact is not None
    assert result.state == "DRAFT_SAVED"
    assert result.prose == BODY and result.prose_hash == sha256(BODY).hexdigest()
    assert result.revision == 1 and result.input_hash == case.frozen.content_hash
    assert result.contract.content_hash == expected.contract.content_hash
    assert result.context.to_bytes() == writer.artifact.to_bytes()
    assert env.adapter.requests[0].context.to_bytes() == writer.artifact.to_bytes()
    assert result.result.to_bytes() == env.ledger.lookup(RUN, LOGICAL).to_bytes()
    assert result.accepted is False
    assert set(result.pending_capabilities) == {
        "EXTRACTION",
        "SCENE_OVERLAY",
        "Q0_Q3",
        "PERMIT",
    }
    assert result.invalidated_evidence == () and env.adapter.calls == 1
    assert result.versions[0].origin == "MODEL"


def test_complete_frozen_input_roundtrip_cannot_be_changed_through_exported_dict():
    case = source_case()
    exported = case.frozen.to_dict()
    restored = FrozenChapterInput.from_dict(exported)
    assert restored.content_hash == case.frozen.content_hash
    exported["instructions"] = "external edit to an exported copy"
    assert case.frozen.to_dict()["instructions"] != exported["instructions"]


def test_non_test_policy_is_refused_without_provider_or_credentials(tmp_path):
    env = harness(tmp_path)
    production = policy_for(
        endpoint="https://api.openai.com/v1/responses", test_mode=False
    )
    with pytest.raises(WorkflowError):
        start(env, source_case(policies=(production,)))
    assert env.adapter.calls == 0


@pytest.mark.parametrize("options", [{"review": "DRAFT"}, {"max_units": 1}])
def test_real_contract_or_context_failure_stops_before_gateway(tmp_path, options):
    env = harness(tmp_path)
    with pytest.raises(WorkflowError):
        start(env, source_case(**options))
    assert env.adapter.calls == 0
    assert env.ledger.summary(RUN)["attempts"] == 0


def test_identical_start_and_reopened_recovery_never_resubmit(tmp_path):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    duplicate = start(env, case)
    workflow, ledger, adapter = reopen(env)
    recovered = recover(workflow, case)
    assert first.record_hash == duplicate.record_hash == recovered.record_hash
    assert env.adapter.calls == 1 and adapter.calls == 0
    assert ledger.summary(RUN)["attempts"] == 1


@pytest.mark.parametrize(
    "identity", ["logical_id", "attempt_id", "policy_id", "frozen_input"]
)
def test_same_run_rejects_changed_frozen_identity_without_resend(tmp_path, identity):
    case, env = source_case(), harness(tmp_path)
    saved = start(env, case)
    with pytest.raises(WorkflowError):
        if identity == "frozen_input":
            start(env, source_case(instructions="changed frozen instructions"))
        else:
            start(env, case, **{identity: "different-identity"})
    assert env.adapter.calls == 1
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


@pytest.mark.parametrize("operation", ["inspect", "recover", "replace"])
@pytest.mark.parametrize("scope", ["project", "branch"])
def test_every_existing_run_access_refuses_wrong_scope_without_returning_prose(
    tmp_path, operation, scope
):
    case, env = source_case(), harness(tmp_path)
    saved = start(env, case)
    arguments = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    arguments[scope] = "another-scope"
    with pytest.raises(WorkflowError) as failure:
        if operation == "inspect":
            env.workflow.inspect(**arguments)
        elif operation == "recover":
            env.workflow.recover(case.frozen, **arguments)
        else:
            env.workflow.replace_draft(
                case.frozen,
                **arguments,
                expected_revision=1,
                expected_prose_hash=saved.prose_hash,
                prose=EDIT,
            )
    assert BODY.decode() not in str(failure.value)
    assert env.adapter.calls == 1


@pytest.mark.parametrize("outcome", ["FAILED", "UNKNOWN"])
def test_gateway_stop_outcomes_keep_real_result_and_never_publish_or_retry(
    tmp_path, outcome
):
    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(outcome=outcome))
    stopped = start(env, case)
    assert stopped.state == outcome and stopped.prose is None and not stopped.accepted
    assert (
        stopped.result.status == outcome and stopped.result.charge_status == "PENDING"
    )
    workflow, ledger, adapter = reopen(env)
    recovered = recover(workflow, case)
    assert recovered.record_hash == stopped.record_hash
    assert adapter.calls == 0 and env.adapter.calls == 1
    assert ledger.summary(RUN)["attempts"] == 1
    assert ledger.summary(RUN)["unknown_microusd"] == case.policies[0].reserve_microusd


@pytest.mark.parametrize(
    "reason", ["missing_usage", "unexpected_model", "oversized_usage"]
)
def test_success_with_unresolved_accounting_is_blocked_without_prose(tmp_path, reason):
    changes = {
        "missing_usage": {"usage": None},
        "unexpected_model": {"observed_model": "unexpected-fixture-model"},
        "oversized_usage": {"usage": Usage(20, 1025, 1045)},
    }[reason]
    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(**changes))
    stopped = start(env, case)
    assert stopped.state == "BLOCKED" and stopped.prose is None
    assert (
        stopped.result.status == "SUCCESS" and stopped.result.charge_status == "PENDING"
    )
    assert not stopped.accepted and stopped.versions == ()
    workflow, _ledger, adapter = reopen(env)
    assert recover(workflow, case).record_hash == stopped.record_hash
    assert env.adapter.calls == 1 and adapter.calls == 0


@pytest.mark.parametrize(
    "output",
    [
        {"text": 3},
        {},
        {"text": ""},
        {"text": "  \n"},
        {"text": "ok", "extra": True},
        [],
    ],
)
def test_actual_gateway_success_with_invalid_writer_payload_cannot_become_a_draft(
    tmp_path, output
):
    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(output=output))
    stopped = start(env, case)
    assert (
        stopped.state == "BLOCKED" and stopped.prose is None and stopped.revision == 0
    )
    assert (
        stopped.result.status == "SUCCESS"
        and stopped.result.charge_status == "ESTIMATED"
    )
    assert env.ledger.lookup(RUN, LOGICAL).status == "SUCCESS"
    assert env.adapter.calls == 1 and not stopped.accepted


def test_publish_failure_after_ledger_success_recovers_original_result_without_send(
    tmp_path, monkeypatch
):
    case, env = source_case(), harness(tmp_path)
    publish = env.store.publish
    failures = []

    def fail_result_once(before, after):
        if after.result is not None and not failures:
            failures.append(after.result.to_bytes())
            raise OSError("synthetic transaction publication failure")
        return publish(before, after)

    monkeypatch.setattr(env.store, "publish", fail_result_once)
    with pytest.raises(WorkflowError):
        start(env, case)
    assert failures and env.adapter.calls == 1
    retained = env.ledger.lookup(RUN, LOGICAL)
    assert retained.status == "SUCCESS" and retained.to_bytes() == failures[0]
    unfinished = env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert unfinished.state != "DRAFT_SAVED" and unfinished.prose is None
    workflow, ledger, adapter = reopen(env)
    recovered = recover(workflow, case)
    assert recovered.state == "DRAFT_SAVED" and recovered.prose == BODY
    assert recovered.result.to_bytes() == retained.to_bytes()
    assert adapter.calls == 0 and ledger.summary(RUN)["attempts"] == 1


def test_dispatched_process_interruption_recovers_unknown_without_freeing_liability(
    tmp_path,
):
    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(crash=True))
    with pytest.raises(SimulatedProcessExit):
        start(env, case)
    assert env.adapter.calls == 1 and env.ledger.summary(RUN)["inflight_attempts"] == 1
    workflow, ledger, adapter = reopen(env)
    recovered = recover(workflow, case)
    assert recovered.state == "UNKNOWN" and recovered.prose is None
    assert (
        recovered.result.status == "UNKNOWN"
        and recovered.result.charge_status == "PENDING"
    )
    assert recovered.result.charge_microusd is None
    assert start(env, case).record_hash == recovered.record_hash
    assert recover(workflow, case).record_hash == recovered.record_hash
    assert env.adapter.calls == 1
    assert ledger.summary(RUN)["unknown_microusd"] == case.policies[0].reserve_microusd
    assert ledger.summary(RUN)["attempts"] == 1 and adapter.calls == 0


def test_recovery_diagnostic_reads_late_attempt_without_promoting_unknown(tmp_path):
    from anovel.workflow.interfaces import snapshot_summary

    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(crash=True), provision=False)
    env.ledger.provision(
        BudgetLimit(PROJECT, BRANCH, RUN, 100000, 3, FUTURE, max_unknown=2)
    )
    with pytest.raises(SimulatedProcessExit):
        start(env, case)
    workflow, ledger, adapter = reopen(env)
    pending = recover(workflow, case)
    assert pending.state == "UNKNOWN" and pending.prose is None
    assert pending.result.charge_status == "PENDING"
    source_input = case.frozen.to_dict()
    request = {
        "operation": "INSPECT_RECOVERY",
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "current_input": source_input,
        "gateway_ledger": str(env.ledger_path),
    }
    save_request = request | {"operation": "SAVE_LATE_RECOVERY_SUCCESS"}
    task = WorkflowTaskAdapter(ChapterWorkflow(WorkflowStore(env.store_path)))
    before = recovery_database_bytes(env.store_path, env.ledger_path)
    initial = snapshot_summary(task.execute(request))
    assert (
        initial["stored_result"]
        == initial["ledger_result"]
        == recovery_result_metadata(pending.result)
    )
    assert initial["stored_result"]["response_hash"] is None
    assert recovery_database_bytes(env.store_path, env.ledger_path) == before

    other = ModelGateway(ledger, adapter).submit(
        env.adapter.requests[0],
        case.policies[0].id,
        "explicit-offline-retry",
        RetryDecision(
            "offline-test", "Different attempt for the same logical request", True
        ),
    )
    assert other.status == "SUCCESS" and ledger.lookup(RUN, LOGICAL) == other
    before = recovery_database_bytes(env.store_path, env.ledger_path)
    assert snapshot_summary(task.execute(request)) == initial
    with pytest.raises(WorkflowError, match="^RECOVERY_LATE_SUCCESS_UNAVAILABLE$"):
        task.execute(save_request)
    assert recovery_database_bytes(env.store_path, env.ledger_path) == before

    late_prose = "晚到正文不进入恢复诊断。"
    late_response = "合成响应体只留在原账本。"
    late = ledger.finish(
        env.adapter.requests[0],
        case.policies[0],
        ATTEMPT,
        ProviderReply(
            "SUCCESS",
            response_body=canonical_bytes({"synthetic": late_response}),
            provider_request_id="synthetic-late-recovery-reply",
            observed_model=case.policies[0].model,
            usage=Usage(20, 10, 30),
            output_bytes=canonical_bytes({"text": late_prose}),
            http_status=200,
        ),
    )
    assert late.status == "SUCCESS" and late.attempt_id == ATTEMPT
    assert ledger.lookup(RUN, LOGICAL) == other
    input_path = tmp_path / "current.json"
    input_path.write_bytes(case.frozen.payload)
    before = recovery_database_bytes(env.store_path, env.ledger_path)
    result = snapshot_summary(task.execute(request))
    assert result["state"] == "UNKNOWN" and result["source_current"] is True
    assert result["attempt_id"] == ATTEMPT
    assert result["record_hash"] == pending.record_hash
    assert result["stored_result"] == initial["stored_result"]
    assert result["ledger_result"] == recovery_result_metadata(late)
    assert all(
        result[key] is False
        for key in (
            "can_dispatch",
            "can_commit",
            "can_issue_permit",
            "accepted",
            "published",
        )
    )
    cli = run_cli(
        env,
        "recover",
        "--input",
        input_path,
        "--gateway-ledger",
        env.ledger_path,
        "--diagnose-only",
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert json.loads(cli.stdout) == result
    assert late_prose not in cli.stdout and late_response not in cli.stdout
    with pytest.raises(WorkflowError, match="^WORKFLOW_INPUT_CHANGED$"):
        task.execute(
            request
            | {"current_input": source_input | {"instructions": "新的写作要求。"}}
        )
    assert recover(workflow, case).record_hash == pending.record_hash
    assert recovery_database_bytes(env.store_path, env.ledger_path) == before
    assert ledger.summary(RUN)["attempts"] == 2
    assert env.adapter.calls == adapter.calls == 1

    forged = replace(late, attempt_id="some-other-attempt")
    with closing(sqlite3.connect(env.ledger_path)) as connection, connection:
        connection.execute(
            "UPDATE attempts SET result_record=? WHERE run_id=? AND attempt_id=?",
            (forged.to_bytes(), RUN, ATTEMPT),
        )
    corrupted = recovery_database_bytes(env.store_path, env.ledger_path)
    with pytest.raises(WorkflowError, match="^RECOVERY_LEDGER_RESULT_MISMATCH$"):
        task.execute(request)
    with pytest.raises(WorkflowError, match="^RECOVERY_LEDGER_RESULT_MISMATCH$"):
        task.execute(save_request)
    assert recovery_database_bytes(env.store_path, env.ledger_path) == corrupted

    wrong_start = replace(late, started_at="2000-01-01T00:00:00.000000Z")
    with closing(sqlite3.connect(env.ledger_path)) as connection, connection:
        connection.execute(
            "UPDATE attempts SET result_record=? WHERE run_id=? AND attempt_id=?",
            (wrong_start.to_bytes(), RUN, ATTEMPT),
        )
    unbound = recovery_database_bytes(env.store_path, env.ledger_path)
    with pytest.raises(WorkflowError, match="^RECOVERY_LATE_SUCCESS_NOT_APPLICABLE$"):
        task.execute(save_request)
    assert recovery_database_bytes(env.store_path, env.ledger_path) == unbound

    with closing(sqlite3.connect(env.ledger_path)) as connection, connection:
        connection.execute(
            "UPDATE attempts SET result_record=? WHERE run_id=? AND attempt_id=?",
            (late.to_bytes(), RUN, ATTEMPT),
        )
    ledger_before = recovery_database_bytes(env.ledger_path)
    cli = run_cli(
        env,
        "recover",
        "--input",
        input_path,
        "--gateway-ledger",
        env.ledger_path,
        "--save-late-success",
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    saved = workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert saved.state == "DRAFT_SAVED" and saved.revision == 1
    assert saved.prose == late_prose.encode() and saved.result == late
    assert saved.accepted is False
    assert json.loads(cli.stdout) == snapshot_summary(saved)
    assert late_prose not in cli.stdout and late_response not in cli.stdout
    after = recovery_database_bytes(env.store_path, env.ledger_path)
    assert task.execute(save_request).record_hash == saved.record_hash
    assert recovery_database_bytes(env.store_path, env.ledger_path) == after
    assert recovery_database_bytes(env.ledger_path) == ledger_before
    assert ledger.lookup(RUN, LOGICAL) == other
    assert ledger.summary(RUN)["attempts"] == 2
    assert env.adapter.calls == adapter.calls == 1


def test_manual_edit_preserves_both_versions_and_invalidates_future_evidence(tmp_path):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    edited = env.workflow.replace_draft(
        case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        expected_revision=1,
        expected_prose_hash=first.prose_hash,
        prose=EDIT,
    )
    assert edited.state == "DRAFT_SAVED" and edited.revision == 2
    assert edited.prose == EDIT and edited.prose_hash == sha256(EDIT).hexdigest()
    assert [version.prose for version in edited.versions] == [BODY, EDIT]
    assert [version.origin for version in edited.versions] == ["MODEL", "MANUAL"]
    assert edited.versions[1].previous_hash == first.prose_hash
    assert edited.invalidated_evidence == ("EXTRACTION", "CHECKS", "CONFIRMATION")
    assert edited.result.to_bytes() == first.result.to_bytes()
    workflow, ledger, adapter = reopen(env)
    assert recover(workflow, case).record_hash == edited.record_hash
    assert (
        env.adapter.calls == 1
        and adapter.calls == 0
        and ledger.summary(RUN)["attempts"] == 1
    )
    assert not edited.accepted


@pytest.mark.parametrize("fault", ["revision", "prose_hash"])
def test_edit_compare_and_swap_rejects_stale_identity_and_keeps_original(
    tmp_path, fault
):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    arguments = {"expected_revision": 1, "expected_prose_hash": first.prose_hash}
    arguments["expected_" + fault] = 0 if fault == "revision" else "0" * 64
    with pytest.raises(WorkflowError):
        env.workflow.replace_draft(
            case.frozen,
            project=PROJECT,
            branch=BRANCH,
            run_id=RUN,
            prose=EDIT,
            **arguments,
        )
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == first.record_hash
    )
    assert env.adapter.calls == 1


@pytest.mark.parametrize("operation", ["recover", "replace"])
def test_changed_frozen_inputs_cannot_reuse_a_saved_run(tmp_path, operation):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    changed = source_case(instructions="revised frozen input, not a retry")
    with pytest.raises(WorkflowError):
        if operation == "recover":
            recover(env.workflow, changed)
        else:
            env.workflow.replace_draft(
                changed.frozen,
                project=PROJECT,
                branch=BRANCH,
                run_id=RUN,
                expected_revision=1,
                expected_prose_hash=first.prose_hash,
                prose=EDIT,
            )
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == first.record_hash
    )
    assert env.adapter.calls == 1


def test_unknown_run_is_not_fabricated_as_a_saved_draft(tmp_path):
    env = harness(tmp_path)
    with pytest.raises(WorkflowError):
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert env.adapter.calls == 0


def test_reopened_inspection_returns_exact_retained_evidence(tmp_path):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    workflow, _ledger, adapter = reopen(env)
    saved = workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert saved.payload_bytes() == first.payload_bytes()
    assert saved.record_hash == sha256(saved.payload_bytes()).hexdigest()
    assert saved.result.reply.response_body == first.result.reply.response_body
    assert adapter.calls == 0


def test_frozen_parser_rejects_unbound_extra_authority_field():
    value = source_case().frozen.to_dict()
    value["accepted"] = True
    with pytest.raises(WorkflowError):
        FrozenChapterInput.from_dict(value)


@pytest.mark.parametrize("fault", ["accepted", "extra", "prose_hash", "state"])
def test_snapshot_closed_parser_rejects_tampering_without_changing_store(
    tmp_path, fault
):
    case, env = source_case(), harness(tmp_path)
    saved = start(env, case)
    value = saved.to_dict()
    if fault == "accepted":
        value["accepted"] = True
    elif fault == "extra":
        value["permit"] = "invented-authority"
    elif fault == "prose_hash":
        value["versions"][0]["prose_hash"] = "0" * 64
    else:
        value["state"] = "ACCEPTED"
    with pytest.raises(WorkflowError):
        type(saved).from_bytes(canonical_bytes(value))
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )


def test_adapter_error_keeps_unknown_without_exposing_exception_or_retry(tmp_path):
    marker = "synthetic-private-exception-detail"
    case = source_case()
    env = harness(tmp_path, adapter=CountingLocalAdapter(exception=OSError(marker)))
    stopped = start(env, case)
    assert stopped.state == "UNKNOWN" and stopped.prose is None
    assert marker.encode() not in stopped.payload_bytes()
    assert env.adapter.calls == 1
    workflow, ledger, adapter = reopen(env)
    assert recover(workflow, case).record_hash == stopped.record_hash
    assert adapter.calls == 0 and ledger.summary(RUN)["attempts"] == 1


def task_start(case):
    return {
        "operation": "START",
        "current_input": case.frozen.to_dict(),
        "run_id": RUN,
        "logical_id": LOGICAL,
        "attempt_id": ATTEMPT,
        "policy_id": case.policies[0].id,
    }


def run_cli(env, *arguments, project=PROJECT, branch=BRANCH):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "anovel.workflow",
            "--db",
            str(env.store_path),
            "--project",
            project,
            "--branch",
            branch,
            "--run-id",
            RUN,
            *map(str, arguments),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_task_start_and_inspect_use_the_real_application_service(tmp_path):
    case, env = source_case(), harness(tmp_path)
    adapter = WorkflowTaskAdapter(env.workflow)
    saved = adapter.execute(task_start(case))
    assert saved.state == "DRAFT_SAVED" and saved.prose == BODY
    inspected = adapter.execute(
        {"operation": "INSPECT", "project": PROJECT, "branch": BRANCH, "run_id": RUN}
    )
    assert inspected.record_hash == saved.record_hash
    assert inspected.result.to_bytes() == env.ledger.lookup(RUN, LOGICAL).to_bytes()
    assert env.adapter.calls == 1 and not inspected.accepted


def test_task_request_rejects_unknown_authority_and_extra_fields_before_send(tmp_path):
    case, env = source_case(), harness(tmp_path)
    adapter = WorkflowTaskAdapter(env.workflow)
    for request in (
        {**task_start(case), "operation": "ACCEPT"},
        {**task_start(case), "accepted": True},
        {**task_start(case), "policy_id": None},
    ):
        with pytest.raises(WorkflowError):
            adapter.execute(request)
    assert env.adapter.calls == 0 and env.ledger.summary(RUN)["attempts"] == 0


def test_actual_cli_inspects_edits_and_exports_the_same_durable_version(tmp_path):
    case, env = source_case(), harness(tmp_path)
    first = start(env, case)
    current_input, edited_prose = tmp_path / "current-input.json", tmp_path / "edit.txt"
    current_input.write_bytes(canonical_bytes(case.frozen.to_dict()))
    edited_prose.write_bytes(EDIT)
    inspected = run_cli(env, "inspect")
    assert inspected.returncode == 0, inspected.stdout + inspected.stderr
    assert json.loads(inspected.stdout)["record_hash"] == first.record_hash
    edited = run_cli(
        env,
        "replace",
        "--input",
        current_input,
        "--prose",
        edited_prose,
        "--expected-revision",
        "1",
        "--expected-prose-hash",
        first.prose_hash,
    )
    assert edited.returncode == 0, edited.stdout + edited.stderr
    summary = json.loads(edited.stdout)
    assert (
        summary["revision"] == 2 and summary["prose_hash"] == sha256(EDIT).hexdigest()
    )
    exported_path = tmp_path / "exported-draft.txt"
    exported = run_cli(env, "export", "--output", exported_path)
    assert exported.returncode == 0, exported.stdout + exported.stderr
    assert exported_path.read_bytes() == EDIT
    saved = env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert summary["record_hash"] == saved.record_hash
    assert [version.prose for version in saved.versions] == [BODY, EDIT]
    assert saved.invalidated_evidence == ("EXTRACTION", "CHECKS", "CONFIRMATION")
    for completed in (inspected, edited, exported):
        assert (
            BODY.decode() not in completed.stdout
            and EDIT.decode() not in completed.stdout
        )
        assert completed.stderr == ""
    assert env.adapter.calls == 1 and env.ledger.summary(RUN)["attempts"] == 1


def test_actual_cli_reprojects_edited_ending_for_the_next_draft_scene(tmp_path):
    from test_v2_020_scene import ENDING_TEXT, OUTSIDE, binding_for, saved_scene, spans

    from anovel.context.scene import SceneSpan
    from anovel.workflow.scene import SceneProjection

    case, env, first = saved_scene(tmp_path)
    current = tmp_path / "current-input.json"
    current.write_bytes(case.frozen.payload)
    guard = """
import runpy
import socket

def refuse_network(*args, **kwargs):
    raise AssertionError("Draft CLI replay must stay offline")

socket.create_connection = refuse_network
socket.socket.connect = refuse_network
socket.socket.connect_ex = refuse_network
runpy.run_module("anovel.workflow", run_name="__main__")
"""

    def invoke(operation, *options):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                guard,
                "--db",
                str(env.store_path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                operation,
                "--input",
                str(current),
                *map(str, options),
            ],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert completed.stderr == ""
        assert OUTSIDE not in completed.stdout and ENDING_TEXT not in completed.stdout
        return completed.returncode, json.loads(completed.stdout)

    def selection_for(draft):
        source, _, first_line = spans(draft.prose)
        start_of_ending = first_line.end + 1
        ending = SceneSpan(start_of_ending, source.end, source.quote[start_of_ending:])
        selection = tmp_path / f"selection-{draft.revision}.json"
        selection.write_bytes(
            canonical_bytes(
                {
                    "source_scene_id": draft.contract.scenes[0].id.to_dict(),
                    "target_scene_id": draft.contract.scenes[1].id.to_dict(),
                    "source_span": source.to_dict(),
                    "ending_span": ending.to_dict(),
                    "delta_binding": binding_for(draft, case).to_dict(),
                }
            )
        )
        return selection

    def project_at(draft, selection, path):
        before = env.store_path.read_bytes(), env.ledger_path.read_bytes()
        result = invoke(
            "project-scene",
            "--expected-record-hash",
            draft.record_hash,
            "--selection",
            selection,
            "--output",
            path,
        )
        assert (env.store_path.read_bytes(), env.ledger_path.read_bytes()) == before
        assert env.adapter.calls == 1 and env.ledger.summary(RUN)["attempts"] == 1
        return result

    old_selection = selection_for(first)
    old_output = tmp_path / "before-edit.json"
    code, original = project_at(first, old_selection, old_output)
    assert code == 0 and original["state"] == "DRAFT_SCENE_PROJECTED"
    previous = json.loads(old_output.read_bytes())
    revised_ending = "编辑测试：留下下一场核对线索。" + ENDING_TEXT
    prose = tmp_path / "edited-prose.txt"
    prose.write_bytes(
        first.prose.replace(ENDING_TEXT.encode(), revised_ending.encode())
    )
    code, replacement = invoke(
        "replace",
        "--prose",
        prose,
        "--expected-revision",
        first.revision,
        "--expected-prose-hash",
        first.prose_hash,
    )
    assert code == 0 and replacement["revision"] == first.revision + 1
    edited = env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    assert replacement["record_hash"] == edited.record_hash != first.record_hash

    stale_path = tmp_path / "stale-projection.json"
    assert project_at(first, old_selection, stale_path) == (
        2,
        {"status": "BLOCKED", "code": "SCENE_SOURCE_CHANGED"},
    )
    assert not stale_path.exists()
    assert project_at(edited, old_selection, stale_path) == (
        2,
        {"status": "BLOCKED", "code": "INVALID_CANDIDATE_SCENE_PROJECTION"},
    )
    assert not stale_path.exists()
    new_selection = selection_for(edited)
    assert project_at(edited, new_selection, env.store_path) == (
        2,
        {"status": "BLOCKED", "code": "SCENE_PROJECTION_EXPORT_RESERVED_PATH"},
    )
    new_output = tmp_path / "after-edit.json"
    code, summary = project_at(edited, new_selection, new_output)
    assert code == 0 and summary["state"] == "DRAFT_SCENE_PROJECTED"
    assert summary["source_record_hash"] == edited.record_hash
    assert summary["source_revision"] == edited.revision
    assert summary["projection_hash"] != original["projection_hash"]
    assert all(
        summary[field] is False
        for field in (
            "can_commit",
            "can_issue_permit",
            "can_dispatch",
            "accepted",
            "published",
        )
    )
    raw = new_output.read_bytes()
    projection_record = json.loads(raw)
    projection = SceneProjection.from_dict(projection_record)
    assert raw == canonical_bytes(projection_record)
    assert summary["projection_hash"] == sha256(raw).hexdigest()
    assert summary["candidate_hash"] == projection.candidate.content_hash
    assert summary["context_hash"] == projection.context.content_hash
    old_stat = new_output.stat()
    assert old_stat.st_mode & 0o777 == 0o600
    assert project_at(edited, new_selection, new_output) == (
        2,
        {"status": "BLOCKED", "code": "SCENE_PROJECTION_EXPORT_FAILED"},
    )
    new_stat = new_output.stat()
    assert new_output.read_bytes() == raw
    assert (new_stat.st_ino, new_stat.st_mtime_ns) == (
        old_stat.st_ino,
        old_stat.st_mtime_ns,
    )

    task = WorkflowTaskAdapter(env.workflow)
    request = {
        "operation": "START_SCENE",
        "current_input": case.frozen.to_dict(),
        "projection": previous,
        "attempt_id": "offline-revised-scene",
        "policy_id": case.policies[0].id,
    }
    before = env.ledger.summary(RUN)
    with pytest.raises(WorkflowError, match="^SCENE_SOURCE_CHANGED$"):
        task.execute(request)
    assert env.ledger.summary(RUN) == before and env.adapter.calls == 1
    env.adapter.output = {"text": "第二场合成测试数据。"}
    child = task.execute(request | {"projection": projection_record})
    assert child.state == "DRAFT_SAVED" and child.accepted is False
    assert child.source.record_hash == edited.record_hash
    forwarded = env.adapter.requests[-1].context
    assert forwarded == projection.context
    ending = next(
        item for item in forwarded.items if item.kind == "ACTUAL_PRECEDING_SCENE_ENDING"
    )
    assert ending.data["text"] == revised_ending
    assert OUTSIDE not in forwarded.to_bytes().decode()
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 2


def test_revision_quality_cli_and_task_share_bound_request_and_summary(
    tmp_path, capsys, monkeypatch
):
    from anovel.domain.identity import EntityId
    from anovel.quality.q1 import BoundQ1Annotations
    from anovel.workflow.chapter import RevisionCheckReadback, RevisionQualityReadback
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.models import WorkflowSnapshot

    current = source_case().frozen
    chapter_id = EntityId.from_dict(current.to_dict()["chapter_id"])
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    contract, context, request = current.request(RUN, LOGICAL)
    assert store.create(
        WorkflowSnapshot(
            current,
            request.to_bytes(),
            canonical_bytes(contract.to_dict()),
            context.to_bytes(),
            ATTEMPT,
            request.policies[0].id,
        )
    )
    current_file = tmp_path / "current.json"
    current_file.write_bytes(current.payload)
    annotations_file = tmp_path / "annotations.json"
    draft_annotations = {"fixture": "annotation parsing boundary"}
    annotations_file.write_bytes(canonical_bytes(draft_annotations))
    annotation_object = object.__new__(BoundQ1Annotations)

    def parse_annotations(value):
        assert value == draft_annotations
        return annotation_object

    monkeypatch.setattr(BoundQ1Annotations, "from_dict", parse_annotations)
    missing = RevisionCheckReadback("MISSING", None)
    base = RevisionQualityReadback(
        "1" * 64,
        2,
        "2" * 64,
        "3" * 64,
        "4" * 64,
        "5" * 64,
        None,
        missing,
        missing,
        missing,
        missing,
    )
    checked = replace(base, q0=RevisionCheckReadback("PASS", "6" * 64))

    def assert_selection(frozen, annotations, arguments):
        assert frozen == current and annotations is annotation_object
        assert arguments == dict(
            project=PROJECT, branch=BRANCH, chapter_id=chapter_id, expected_run_id=RUN
        )

    def inspect(service, frozen, annotations, **arguments):
        assert service.gateway is None
        assert_selection(frozen, annotations, arguments)
        return base

    def check(service, frozen, annotations, *, expected_revision_hash, **arguments):
        assert service.gateway is None
        assert_selection(frozen, annotations, arguments)
        assert expected_revision_hash == base.revision_hash
        return checked

    monkeypatch.setattr(ChapterWorkflow, "inspect_revision_quality", inspect)
    monkeypatch.setattr(ChapterWorkflow, "check_revision_quality", check)
    argv = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
    ]
    common = ["--input", str(current_file), "--annotations", str(annotations_file)]
    before = store.path.read_bytes()
    for operation, options, expected in (
        ("inspect-revision-quality", [], base),
        (
            "check-revision-quality",
            ["--expected-revision-hash", base.revision_hash],
            checked,
        ),
    ):
        assert workflow_cli.main([*argv, operation, *common, *options]) == 0
        output = capsys.readouterr()
        summary = json.loads(output.out)
        assert summary == snapshot_summary(expected)
        assert summary["state"] == "DRAFT_REVISION_QUALITY"
        assert summary["missing_checks"] == (
            ["Q0", "Q1", "Q2", "Q3"] if expected is base else ["Q1", "Q2", "Q3"]
        )
        assert summary["aggregate_status"] == "BLOCKED"
        assert all(
            summary[flag] is False
            for flag in (
                "can_commit",
                "can_issue_permit",
                "can_dispatch",
                "accepted",
                "published",
            )
        )
        assert output.err == ""
    assert store.path.read_bytes() == before


def test_revision_quality_keeps_one_bound_revision_between_check_groups(monkeypatch):
    from anovel.domain.identity import EntityId
    from anovel.quality.q1 import BoundQ1Annotations

    workflow = object.__new__(ChapterWorkflow)
    current = object()
    annotations = object.__new__(BoundQ1Annotations)
    starting = SimpleNamespace(run_id=RUN, record_hash="1" * 64)
    edited = SimpleNamespace(run_id=RUN, record_hash="2" * 64)
    active = starting
    reads = []
    stages = []
    scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "chapter_id": EntityId(PROJECT, "draft"),
    }

    def load(**arguments):
        assert arguments == scope
        reads.append(active.record_hash)
        return active

    def read_checks(actual_input, actual_annotations, revision):
        assert actual_input is current and actual_annotations is annotations
        assert revision is starting
        stages.append("inspect")
        return SimpleNamespace(
            q0=SimpleNamespace(record_hash=None), q123_record_hash=None
        )

    def check_q0(actual_input, **arguments):
        nonlocal active
        assert actual_input is current
        assert arguments == dict(scope, execute=True, bound_revision=starting)
        stages.append("Q0")
        active = edited

    def check_q123(actual_input, actual_annotations, **arguments):
        assert actual_input is current and actual_annotations is annotations
        assert active is edited
        assert arguments == dict(scope, execute=True, bound_revision=starting)
        stages.append("Q123")
        raise WorkflowError("CHAPTER_REVISION_CHANGED")

    monkeypatch.setattr(workflow, "load_chapter_revision", load)
    monkeypatch.setattr(workflow, "_read_revision_quality", read_checks)
    monkeypatch.setattr(workflow, "_revision_q0", check_q0)
    monkeypatch.setattr(workflow, "_revision_q123", check_q123)
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        workflow.check_revision_quality(
            current,
            annotations,
            **scope,
            expected_run_id=RUN,
            expected_revision_hash=starting.record_hash,
        )
    assert reads == [starting.record_hash]
    assert stages == ["inspect", "Q0", "Q123"]


@pytest.mark.parametrize("group", ["Q0", "Q123"])
def test_revision_evidence_reuses_exact_bytes_and_revalidates_row(group, monkeypatch):
    from anovel.quality.revision_q0 import RevisionQ0Run
    from anovel.quality.revision_q123 import RevisionQ123Run

    if group == "Q0":
        run_class, read_row = RevisionQ0Run, WorkflowStore._decode_revision_q0
    else:
        run_class, read_row = RevisionQ123Run, WorkflowStore._decode_revision_q123
    payload = b"retained-check"
    row = {
        "project": PROJECT,
        "branch": BRANCH,
        "chapter_id": "draft",
        "revision_hash": "1" * 64,
        "policy_hash": "2" * 64,
        "annotations_hash": "3" * 64,
        "version": 2,
        "payload": payload,
        "payload_hash": sha256(payload).hexdigest(),
    }
    calls = []

    def decode(raw):
        calls.append(raw)
        return SimpleNamespace(
            revision=SimpleNamespace(
                project=PROJECT,
                branch=BRANCH,
                chapter_id=SimpleNamespace(local_id="draft"),
                version=2,
            ),
            revision_hash=row["revision_hash"],
            policy_hash=row["policy_hash"],
            annotations_hash=row["annotations_hash"],
        )

    monkeypatch.setattr(run_class, "from_bytes", staticmethod(decode))
    with WorkflowStore.reuse_observation_decodes():
        first = read_row(row)
        assert read_row(dict(row)) is first
        diagnostic = f"^CORRUPT_REVISION_{group}_EXECUTION$"
        with pytest.raises(WorkflowError, match=diagnostic):
            read_row(row | {"payload_hash": "0" * 64})
        with pytest.raises(WorkflowError, match=diagnostic):
            read_row(row | {"version": 1})
        assert calls == [payload]
        changed = b"other-retained-check"
        changed_row = row | {
            "payload": changed,
            "payload_hash": sha256(changed).hexdigest(),
        }
        assert read_row(changed_row) is not first
        assert calls == [payload, changed]
    assert read_row(row) is not first
    assert calls == [payload, changed, payload]


def test_save_chapter_revision_cli_delegates_exact_observation_and_predecessor(
    tmp_path, capsys, monkeypatch
):
    from test_canon_commit import candidate as sample_candidate

    from anovel.domain.identity import EntityId
    from anovel.workflow.chapter_revision import ChapterRevision
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.models import WorkflowSnapshot

    current = source_case().frozen
    chapter = EntityId.from_dict(current.to_dict()["chapter_id"])
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    contract, context, request = current.request(RUN, LOGICAL)
    saved = WorkflowSnapshot(
        current,
        request.to_bytes(),
        canonical_bytes(contract.to_dict()),
        context.to_bytes(),
        ATTEMPT,
        request.policies[0].id,
    )
    assert store.create(saved)
    input_path = tmp_path / "current.json"
    input_path.write_bytes(current.payload)

    # Re-key an inert typed fixture to the real frozen run used by the CLI.
    template = sample_candidate()
    op = template.delta.operations[0]
    op = replace(
        op,
        meta=replace(
            op.meta,
            id=EntityId(PROJECT, op.meta.id.local_id),
            target_id=EntityId(PROJECT, op.meta.target_id.local_id),
            evidence=replace(op.meta.evidence, source_id=chapter),
        ),
    )
    draft = replace(
        template,
        id=chapter,
        branch=BRANCH,
        parent_ref=contract.parent_ref,
        delta=replace(
            template.delta,
            id=EntityId(PROJECT, template.delta.id.local_id),
            branch=BRANCH,
            parent_ref=contract.parent_ref,
            source_id=chapter,
            operations=(op,),
        ),
    )
    first = ChapterRevision(
        chapter,
        RUN,
        "1" * 64,
        saved.input_hash,
        "2" * 64,
        "3" * 64,
        "observe-v1",
        None,
        draft,
    )
    second = replace(
        first,
        request_id="observe-v2",
        previous_revision_hash=first.record_hash,
        candidate=replace(draft, version=2),
    )

    calls = []

    def save(service, frozen, **arguments):
        assert service.gateway is None and frozen == current
        calls.append(arguments)
        return (first, second)[arguments["version"] - 1]

    monkeypatch.setattr(ChapterWorkflow, "save_observed_chapter_revision", save)
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    root_args = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
    ]
    before = store.path.read_bytes()
    for revision in (first, second):
        selection = {
            "project": PROJECT,
            "branch": BRANCH,
            "run_id": RUN,
            "step_id": revision.step_id,
            "expected_observation_hash": revision.observation_hash,
            "version": revision.version,
            "request_id": revision.request_id,
            "expected_revision_hash": revision.previous_revision_hash,
        }
        task_request = {
            "operation": "SAVE_CHAPTER_REVISION",
            "current_input": current.to_dict(),
            **selection,
        }
        args = [
            *root_args,
            "save-chapter-revision",
            "--input",
            str(input_path),
            "--step-id",
            revision.step_id,
            "--expected-observation-hash",
            revision.observation_hash,
            "--version",
            str(revision.version),
            "--request-id",
            revision.request_id,
        ]
        if revision.previous_revision_hash is not None:
            args.extend(("--expected-revision-hash", revision.previous_revision_hash))
        assert task.execute(task_request) is revision
        assert workflow_cli.main(args) == 0
        output = capsys.readouterr()
        assert not output.err and draft.prose.decode().strip() not in output.out
        summary = json.loads(output.out)
        assert summary == snapshot_summary(revision)
        assert {"prose", "candidate", "dependencies"}.isdisjoint(summary)
        assert summary["state"] == "DRAFT_CHAPTER_REVISION_SAVED"
        assert summary["revision_hash"] == revision.record_hash
        assert summary["candidate_version"] == revision.version
        assert summary["observation_hash"] == revision.observation_hash
        assert summary["previous_revision_hash"] == revision.previous_revision_hash
        assert all(
            summary[flag] is False
            for flag in (
                "can_commit",
                "can_issue_permit",
                "can_dispatch",
                "accepted",
                "published",
            )
        )
        assert calls[-2:] == [selection, selection]
        for invalid in (
            {"prose": "client supplied unbound content"},
            {"version": True},
            {"expected_revision_hash": 1},
        ):
            with pytest.raises(WorkflowError, match="^INVALID_WORKFLOW_TASK_REQUEST$"):
                task.execute(task_request | invalid)
    assert len(calls) == 4
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    inspection_calls = []

    def inspect(service, frozen, **arguments):
        assert service.gateway is None and frozen == current
        assert arguments == scope
        inspection_calls.append(arguments)
        return second

    monkeypatch.setattr(ChapterWorkflow, "inspect_chapter_revision", inspect)
    request = {
        "operation": "INSPECT_CHAPTER_REVISION",
        "current_input": current.to_dict(),
        **scope,
    }
    assert task.execute(request) is second
    assert (
        workflow_cli.main(
            [*root_args, "inspect-chapter-revision", "--input", str(input_path)]
        )
        == 0
    )
    output = capsys.readouterr()
    assert not output.err and draft.prose.decode().strip() not in output.out
    assert json.loads(output.out) == snapshot_summary(second)
    for extra in ({"version": 1}, {"annotations": {}}, {"accepted": True}):
        with pytest.raises(WorkflowError, match="^INVALID_WORKFLOW_TASK_REQUEST$"):
            task.execute(request | extra)
    assert inspection_calls == [scope, scope]

    finished = tmp_path / "chapter.txt"
    finish_args = {
        **scope,
        "step_id": second.step_id,
        "version": 2,
        "request_id": second.request_id,
        "expected_revision_hash": first.record_hash,
        "output": finished,
    }
    finishes = []

    def finish(service, frozen, **arguments):
        assert service.gateway is None and frozen == current
        finishes.append(arguments)
        return second

    monkeypatch.setattr(ChapterWorkflow, "finish_chapter_draft", finish)
    assert (
        workflow_cli.main(
            [
                *root_args,
                "finish-chapter",
                "--input",
                str(input_path),
                "--step-id",
                second.step_id,
                "--version",
                "2",
                "--request-id",
                second.request_id,
                "--expected-revision-hash",
                first.record_hash,
                "--output",
                str(finished),
            ]
        )
        == 0
    )
    assert finishes == [finish_args]
    assert json.loads(capsys.readouterr().out) == snapshot_summary(second)
    assert store.path.read_bytes() == before


def test_export_chapter_revision_reads_current_whole_draft_from_cli_and_task(
    tmp_path, capsys, monkeypatch
):
    from test_v2_017 import eid
    from test_v2_021 import ACTUAL, make_extraction_seed

    from anovel.context.scene import SceneSpan, evidence_ref
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.scene import SceneProjection

    seed = make_extraction_seed(tmp_path, False)
    env = seed.env
    current = seed.case.frozen
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}

    def save_revision(step_id, version, previous=None):
        observation = env.workflow.extract_chapter(current, **scope, step_id=step_id)
        return env.workflow.save_observed_chapter_revision(
            current,
            **scope,
            step_id=step_id,
            expected_observation_hash=observation.record_hash,
            version=version,
            request_id=f"draft-export-v{version}",
            expected_revision_hash=previous,
        )

    first = save_revision(seed.child.step_id, 1)
    new_line = "全章导出测试：第二版含作者改动。"
    revised_ending = ACTUAL.replace("20", "30")
    current_input = tmp_path / "current.json"
    current_input.write_bytes(current.payload)

    def invoke(
        destination,
        revision_hash,
        *,
        operation="export-chapter-revision",
        path_option="--output",
    ):
        code = workflow_cli.main(
            [
                "--db",
                str(env.store_path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                operation,
                "--input",
                str(current_input),
                "--expected-revision-hash",
                revision_hash,
                path_option,
                str(destination),
            ]
        )
        captured = capsys.readouterr()
        assert captured.err == ""
        assert new_line not in captured.out
        assert ACTUAL not in captured.out and revised_ending not in captured.out
        return code, json.loads(captured.out)

    v1_handoff = tmp_path / "next-from-v1.json"
    code, summary = invoke(
        v1_handoff, first.record_hash, operation="project-next-chapter"
    )
    assert code == 0 and summary["source_revision_hash"] == first.record_hash
    assert json.loads(v1_handoff.read_bytes())["ending"]["quote"] == ACTUAL
    first_export = tmp_path / "chapter-v1.txt"
    assert invoke(first_export, first.record_hash) == (0, snapshot_summary(first))
    assert first_export.read_bytes() == first.candidate.prose

    changed_fact = "secret变为false。"
    edited_ending = new_line + " \t\n"
    prefix = seed.source.prose.decode() + "\n" + changed_fact + "\r\n \r\n"
    edited_text = prefix + edited_ending
    intermediate = env.workflow.replace_draft(
        current,
        **scope,
        expected_revision=seed.source.revision,
        expected_prose_hash=seed.source.prose_hash,
        prose=(prefix + seed.source.prose.decode()).encode(),
    )
    author_file = tmp_path / "author-fact-edits.json"
    author_file.write_text(
        json.dumps(
            {"fact_edits": [{"quote": changed_fact, "value": False}]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def project_scene(record_hash, output, *, path=author_file, option="--fact-edits"):
        code = workflow_cli.main(
            [
                "--db",
                str(env.store_path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                "project-scene",
                "--input",
                str(current_input),
                "--expected-record-hash",
                record_hash,
                option,
                str(path),
                "--output",
                str(output),
            ]
        )
        return code, json.loads(capsys.readouterr().out)

    prior_file = tmp_path / "prior-projection.json"
    assert project_scene(intermediate.record_hash, prior_file)[0] == 0
    prior = SceneProjection.from_dict(json.loads(prior_file.read_bytes()))
    proposed = tmp_path / "edited-first-scene.txt"
    proposed.write_bytes(edited_text.encode())
    projection_file = tmp_path / "edited-projection.json"
    assert (
        workflow_cli.main(
            [
                "--db",
                str(env.store_path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                "replace",
                "--input",
                str(current_input),
                "--expected-revision",
                str(intermediate.revision),
                "--expected-prose-hash",
                intermediate.prose_hash,
                "--prose",
                str(proposed),
                "--fact-edits",
                str(author_file),
                "--projection-output",
                str(projection_file),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["state"] == "DRAFT_SCENE_PROJECTED"
    edited = env.workflow.inspect(**scope)
    assert (summary["source_revision"], summary["source_record_hash"]) == (
        edited.revision,
        edited.record_hash,
    )
    assert (
        edited.revision == intermediate.revision + 1
        and edited.prose == proposed.read_bytes()
    )
    stale_projection = tmp_path / "stale-projection.json"
    assert project_scene(intermediate.record_hash, stale_projection) == (
        2,
        {"status": "BLOCKED", "code": "SCENE_SOURCE_CHANGED"},
    )
    assert not stale_projection.exists()
    prior_binding = tmp_path / "prior-binding.json"
    prior_binding.write_bytes(canonical_bytes(prior.candidate.binding.to_dict()))
    assert project_scene(
        edited.record_hash,
        stale_projection,
        path=prior_binding,
        option="--delta-binding",
    ) == (
        2,
        {"status": "BLOCKED", "code": "INVALID_CANDIDATE_SCENE_PROJECTION"},
    )
    assert not stale_projection.exists()
    with pytest.raises(WorkflowError, match="^SCENE_SOURCE_CHANGED$"):
        env.workflow.consume_scene_projection(current, prior)
    projection = SceneProjection.from_dict(json.loads(projection_file.read_bytes()))
    assert projection.candidate.source_span.quote == edited_text
    assert projection.candidate.ending_span == SceneSpan(
        len(prefix), len(edited_text), edited_ending
    )
    binding = projection.candidate.binding
    start = edited_text.index(changed_fact)
    span = binding.operation_quotes[0].span
    assert span == SceneSpan(start, start + len(changed_fact), changed_fact)
    (change,) = binding.delta.operations
    assert change.meta.target_id == eid("secret") and change.value is False
    assert change.meta.expected.state.value is True
    assert change.meta.evidence.evidence_ref == evidence_ref(
        RUN, edited.revision, edited.prose_hash, span
    )
    assert projection_file.stat().st_mode & 0o777 == 0o600
    send = env.adapter.send

    def send_edited_scene(request, policy, attempt_id, permit):
        ending = next(
            item
            for item in request.context.items
            if item.kind == "ACTUAL_PRECEDING_SCENE_ENDING"
        )
        fact = next(item for item in request.context.items if item.id == "fact:secret")
        assert ending.data["text"] == edited_ending
        assert (
            fact.kind == "DRAFT_CANDIDATE_FACT" and fact.data["state"]["value"] is False
        )
        assert seed.source.prose not in request.context.model_bytes
        return send(request, policy, attempt_id, permit)

    monkeypatch.setattr(env.adapter, "send", send_edited_scene)
    env.adapter.output = {"text": revised_ending}
    writer = WorkflowTaskAdapter(env.workflow)
    continuation = {
        "operation": "CONTINUE_CHAPTER_DRAFT",
        "current_input": current.to_dict(),
        "projection": projection.to_dict(),
        "attempt_id": "draft-export-child-v2",
        "policy_id": edited.policy_id,
        "version": 2,
        "request_id": "draft-export-v2",
        "expected_revision_hash": first.record_hash,
        "output": str(tmp_path / "finished.txt"),
    }
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CONFLICT$"):
        writer.execute(continuation | {"expected_revision_hash": "8" * 64})
    assert env.ledger.summary(RUN)["attempts"] == 2
    second = writer.execute(continuation)
    expected = edited_text.encode() + b"\n\n" + revised_ending.encode()
    assert second.candidate.prose == expected != first.candidate.prose
    assert first_export.read_bytes() == first.candidate.prose
    assert (tmp_path / "finished.txt").read_bytes() == expected
    retry = tmp_path / "finished-retry.txt"
    assert writer.execute(continuation | {"output": str(retry)}) == second
    assert retry.read_bytes() == expected
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 3

    before = env.store_path.read_bytes(), env.ledger_path.read_bytes()

    v2_handoff = tmp_path / "next-from-v2.json"
    code, summary = invoke(
        v2_handoff, second.record_hash, operation="project-next-chapter"
    )
    assert code == 0 and summary["state"] == "DRAFT_NEXT_CHAPTER_INPUT"
    assert summary["source_revision_hash"] == second.record_hash
    assert summary["target_chapter_id"] == {"project": PROJECT, "local_id": "chapter-2"}
    assert (
        summary["target_chapter_number"] == 2 and summary["artifact_state"] == "DRAFT"
    )
    assert all(
        summary[flag] is False
        for flag in (
            "can_commit",
            "can_issue_permit",
            "can_dispatch",
            "accepted",
            "published",
        )
    )
    raw_handoff = v2_handoff.read_bytes()
    payload = json.loads(raw_handoff)
    assert payload["ending"]["quote"] == revised_ending
    assert payload["source_revision_hash"] == second.record_hash
    assert payload["target_chapter_id"] == summary["target_chapter_id"]
    assert (
        payload["target_chapter_number"] == 2 and payload["artifact_state"] == "DRAFT"
    )
    assert v2_handoff.stat().st_mode & 0o777 == 0o600
    assert sha256(raw_handoff).hexdigest() == summary["record_hash"]
    assert invoke(
        v2_handoff,
        second.record_hash,
        operation="verify-next-chapter",
        path_option="--handoff",
    ) == (0, summary)
    stale_handoff = tmp_path / "next-from-stale.json"
    assert invoke(
        stale_handoff, first.record_hash, operation="project-next-chapter"
    ) == (2, {"status": "BLOCKED", "code": "CHAPTER_REVISION_CHANGED"})
    assert not stale_handoff.exists()
    assert invoke(
        v1_handoff,
        second.record_hash,
        operation="verify-next-chapter",
        path_option="--handoff",
    ) == (2, {"status": "BLOCKED", "code": "NEXT_CHAPTER_INPUT_CHANGED"})

    cli_path = tmp_path / "chapter-cli.txt"
    assert invoke(cli_path, second.record_hash) == (0, snapshot_summary(second))
    assert cli_path.read_bytes() == expected
    assert cli_path.stat().st_mode & 0o777 == 0o600

    task_path = tmp_path / "chapter-task.txt"
    task = WorkflowTaskAdapter(ChapterWorkflow(WorkflowStore(env.store_path)))
    result = task.execute(
        {
            "operation": "EXPORT_CHAPTER_REVISION",
            "current_input": current.to_dict(),
            **scope,
            "expected_revision_hash": second.record_hash,
            "output": str(task_path),
        }
    )
    assert result == second
    assert task_path.read_bytes() == expected
    assert task_path.stat().st_mode & 0o777 == 0o600

    stale_path = tmp_path / "stale.txt"
    assert invoke(stale_path, first.record_hash) == (
        2,
        {"status": "BLOCKED", "code": "CHAPTER_REVISION_CHANGED"},
    )
    assert not stale_path.exists()

    sentinel = tmp_path / "already-exists.txt"
    sentinel.write_bytes(b"keep existing author text")
    assert invoke(sentinel, second.record_hash) == (
        2,
        {"status": "BLOCKED", "code": "CHAPTER_REVISION_EXPORT_FAILED"},
    )
    assert sentinel.read_bytes() == b"keep existing author text"

    ledger_alias = env.ledger_path.with_name(env.ledger_path.name + "-JOURNAL")
    assert not ledger_alias.exists()
    assert invoke(ledger_alias, second.record_hash) == (
        2,
        {"status": "BLOCKED", "code": "CHAPTER_REVISION_EXPORT_RESERVED_PATH"},
    )
    assert not ledger_alias.exists()
    assert (env.store_path.read_bytes(), env.ledger_path.read_bytes()) == before
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 3


def test_next_chapter_writer_checks_current_material_before_writing_draft(
    tmp_path, monkeypatch
):
    from anovel.context.scene import SceneSpan
    from anovel.domain.events import NarrativePosition
    from anovel.domain.identity import EntityId
    from anovel.planning.models import RevealBoundary
    from anovel.workflow.extractor import ExactSpan, ExtractionSegment
    from anovel.workflow.interfaces import snapshot_summary

    balance = EntityId(PROJECT, "balance")
    secret = EntityId(PROJECT, "secret")
    fixture, history, view = make_case(
        reader_boundaries=(RevealBoundary(secret, NarrativePosition(2, 2)),)
    )
    current = FrozenChapterInput.freeze(
        history=history,
        chapter_id=fixture.vision.chapters[0].id,
        fixture=fixture,
        view=view,
        budget=ContextBudget(100000),
        policies=(policy_for(),),
        instructions="返回text。",
        template_version="local-draft-test",
    )
    choice = "甲选择交付。"
    ending = "balance变为30。"
    previous = choice + "\n\n" + ending
    revision = SimpleNamespace(
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        chapter_id=fixture.vision.chapters[0].id,
        version=2,
        record_hash="2" * 64,
        candidate=SimpleNamespace(prose=previous.encode()),
    )
    choice_span = SceneSpan(0, len(choice), choice)
    balance_fact = ExtractionSegment(
        "ACTUAL",
        ExactSpan.from_source(previous.encode(), len(choice) + 2, len(previous)),
        balance,
        "SET_FACT",
        canonical_bytes(30),
    )
    hidden_fact = ExtractionSegment(
        "ACTUAL",
        ExactSpan.from_source(previous.encode(), 0, len(choice)),
        secret,
        "SET_FACT",
        canonical_bytes(True),
    )
    observation = SimpleNamespace(
        record_hash="3" * 64,
        coverage=(balance_fact, hidden_fact),
        assembly=SimpleNamespace(
            child=SimpleNamespace(
                prose=ending.encode(),
                ledger_pin=SimpleNamespace(path=str(tmp_path / "gateway.sqlite")),
                projection=SimpleNamespace(
                    candidate=SimpleNamespace(ending_span=choice_span)
                ),
            )
        ),
    )
    prose = "甲查回单，按照三十的余额继续交付。".encode()
    received = []

    def writer(payload):
        received.append(payload)
        return prose

    store = WorkflowStore(tmp_path / "workflow.sqlite")
    workflow = ChapterWorkflow(store, next_chapter_writer=writer)
    monkeypatch.setattr(
        workflow,
        "_current_chapter_revision",
        lambda *_args, **_kwargs: (revision, observation),
    )
    monkeypatch.setattr(workflow, "load_chapter_revision", lambda **_kwargs: revision)
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    handoff = workflow.next_chapter_draft_input(
        current, **scope, expected_revision_hash=revision.record_hash
    )
    target_file = tmp_path / "chapter-2.json"
    task = WorkflowTaskAdapter(workflow)
    request = {
        "operation": "WRITE_NEXT_CHAPTER_DRAFT",
        "current_input": current.to_dict(),
        **scope,
        "expected_revision_hash": revision.record_hash,
        "handoff": handoff.to_dict(),
        "output": str(target_file),
    }
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(request | {"expected_revision_hash": "1" * 64})
    v1_handoff = handoff.to_dict() | {
        "ending": SceneSpan(len(choice) + 2, len(previous), "balance变为20。").to_dict()
    }
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        task.execute(request | {"handoff": v1_handoff})
    journal_alias = tmp_path / "gateway.sqlite-JOURNAL"
    with pytest.raises(
        WorkflowError, match="^NEXT_CHAPTER_DRAFT_EXPORT_RESERVED_PATH$"
    ):
        task.execute(request | {"output": str(journal_alias)})
    assert not journal_alias.exists()
    assert not received and not target_file.exists()

    result = task.execute(request)
    (raw,) = received
    context = json.loads(raw)
    assert context["handoff"] == handoff.to_dict()
    assert context["handoff"]["ending"]["quote"] == ending
    assert context["previous_scene_ending"] == choice_span.to_dict()
    assert context["observed_draft_facts"] == [balance_fact.to_dict()]
    assert context["source_observation_hash"] == observation.record_hash
    draft = json.loads(target_file.read_bytes())
    assert draft["prose"] == prose.decode()
    assert draft["writer_input_hash"] == sha256(raw).hexdigest()
    assert target_file.stat().st_mode & 0o777 == 0o600
    summary = snapshot_summary(result)
    assert summary["state"] == "DRAFT_NEXT_CHAPTER_WRITTEN"
    assert summary["artifact_state"] == "DRAFT"
    assert summary["source_revision_hash"] == revision.record_hash
    assert summary["target_chapter_id"] == fixture.vision.chapters[1].id.to_dict()
    assert not any(summary[flag] for flag in ("can_commit", "accepted", "published"))
    assert "prose" not in summary
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_DRAFT_EXPORT_FAILED$"):
        task.execute(request)
    assert received == [raw]


@pytest.mark.parametrize("with_brief", [False, True], ids=["legacy", "chapter-brief"])
def test_next_chapter_model_gateway_prepares_and_saves_the_same_request(
    tmp_path, with_brief
):
    from test_v2_021 import ACTUAL, QUIET, make_extraction_seed

    from anovel.workflow.interfaces import snapshot_summary

    seed = make_extraction_seed(tmp_path, False)
    env, current, policy = seed.env, seed.case.frozen, seed.case.policies[0]
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    observation = env.workflow.extract_chapter(
        current, **scope, step_id=seed.child.step_id
    )
    reader = ChapterWorkflow(env.store, draft_handoff_step_id=seed.child.step_id)
    selection = scope | {"expected_revision_hash": observation.record_hash}
    handoff = reader.next_chapter_draft_input(current, **selection)
    task_args = selection | {
        "current_input": current.to_dict(),
        "handoff": handoff.to_dict(),
    }
    brief_fields = {
        "story_title": "街坊试片",
        "setting": "校园摄影社的本地创作约定。",
        "arc_goal": "在交片前找到一个值得拍摄的人。",
        "character_motives": ["许甲想交出自己能署名的作品。"],
        "chapter_title": "灯要收了",
        "chapter_goal": "让许甲的选镜决定带来一次实在的损失。",
        "opening": "从上一章最后的账单接起。",
        "causal_beats": ["许甲选定人物采访。对方拒绝。他赶回时失去了原定机位。"],
        "constraints": ["后续安排只供后续章节使用。"],
    }
    brief = {
        "record_type": "draft_chapter_brief",
        "schema_version": "1.0",
        "artifact_state": "DRAFT",
        "project": PROJECT,
        "branch": BRANCH,
        "source_chapter_id": handoff.source.chapter_id.to_dict(),
        "target_chapter_id": handoff.target.id.to_dict(),
        "source_prose_hash": handoff.to_dict()["source_prose_hash"],
        **brief_fields,
    }
    if with_brief:
        task_args["brief"] = brief
    target = handoff.target.id
    stale = handoff.to_dict() | {"source_revision_hash": "0" * 64}

    before = env.store_path.read_bytes(), env.ledger_path.read_bytes()
    request_file = tmp_path / "model-request.json"
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        reader.prepare_next_chapter_model_request(
            current,
            **selection,
            retained_payload=canonical_bytes(stale),
            policy=policy,
            output=request_file,
        )
    assert not request_file.exists()
    prepared = WorkflowTaskAdapter(reader).execute(
        task_args
        | {
            "operation": "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
            "policy": policy.to_dict(),
            "output": str(request_file),
        }
    )
    assert request_file.read_bytes() == prepared.to_bytes()
    assert request_file.stat().st_mode & 0o777 == 0o600
    assert (env.store_path.read_bytes(), env.ledger_path.read_bytes()) == before
    assert env.adapter.calls == 2
    assert prepared.context.role is ContextRole.WRITER
    assert prepared.context.parent_ref == seed.source.context.parent_ref
    assert prepared.context.contract_hash == seed.source.contract.content_hash
    model_context = prepared.context.model_bytes.decode()
    assert (
        ACTUAL in model_context
        and QUIET in model_context
        and "balance" in model_context
    )
    if with_brief:
        payload = next(
            item.data for item in prepared.context.items if item.kind == "DRAFT_HANDOFF"
        )
        assert payload["chapter_brief"] == brief_fields
        writer_handoff = payload["handoff"]
        assert writer_handoff["target_purpose"] == brief_fields["chapter_goal"]
        assert writer_handoff["start_intent"] == brief_fields["opening"]
        assert writer_handoff["ending"] == handoff.ending.to_dict()
        assert payload["previous_scene_ending"] == (
            seed.projection.candidate.ending_span.to_dict()
        )
        assert payload["observed_draft_facts"] == [
            fact.to_dict() for fact in observation.coverage if fact.kind == "ACTUAL"
        ]
        assert handoff.target.start_intent not in model_context
        assert {item.kind for item in prepared.context.items} == {
            "ROLE_POLICY",
            "DRAFT_HANDOFF",
        }
    else:
        assert handoff.target.start_intent in model_context
        assert "chapter_brief" not in model_context
        assert any(item.kind == "WORLD_RULES" for item in prepared.context.items)
    assert seed.case.fixture.reader_promises[0] not in model_context
    assert current.to_dict()["instructions"] != prepared.instructions

    draft_prose = "下一章网关结果测试：已按交接核对回单。"
    env.adapter.output = {"text": draft_prose}
    workflow = ChapterWorkflow(
        env.store,
        env.gateway,
        next_chapter_policy=policy,
        draft_handoff_step_id=seed.child.step_id,
    )
    destination = tmp_path / "chapter-2.json"
    write = task_args | {
        "operation": "WRITE_NEXT_CHAPTER_DRAFT",
        "output": str(destination),
    }
    task = WorkflowTaskAdapter(workflow)
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        task.execute(write | {"handoff": stale})
    if with_brief:
        with pytest.raises(WorkflowError, match="^INVALID_NEXT_CHAPTER_BRIEF$"):
            task.execute(write | {"brief": brief | {"future_chapters": "不得进入请求"}})
        with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_BRIEF_SOURCE_CHANGED$"):
            task.execute(write | {"brief": brief | {"source_prose_hash": "0" * 64}})
    assert not destination.exists() and env.adapter.calls == 2
    generated = task.execute(write)
    assert generated.prose == draft_prose.encode()
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 3
    assert env.adapter.requests[-1].to_bytes() == prepared.to_bytes()
    receipt = env.ledger.lookup(RUN, prepared.logical_id)
    assert receipt is not None and receipt.request_hash == prepared.semantic_hash
    assert receipt.policy_hash == policy.content_hash and receipt.status == "SUCCESS"
    assert json.loads(destination.read_bytes())["prose"] == draft_prose
    assert snapshot_summary(generated)["artifact_state"] == "DRAFT"

    store = WorkflowStore(env.store_path)
    stored = store.load_written_draft(project=PROJECT, branch=BRANCH, chapter_id=target)
    assert (
        stored.prose == generated.prose
        and stored.source_revision_hash == observation.record_hash
    )
    cold_adapter = CountingLocalAdapter(outcome="UNKNOWN")
    cold_ledger = BudgetLedger(env.ledger_path)
    cold = WorkflowTaskAdapter(
        ChapterWorkflow(
            store,
            ModelGateway(cold_ledger, cold_adapter),
            next_chapter_policy=policy,
            draft_handoff_step_id=seed.child.step_id,
        )
    )
    replay_path = tmp_path / "chapter-2-replay.json"
    assert cold.execute(write | {"output": str(replay_path)}) == generated
    assert replay_path.read_bytes() == destination.read_bytes()
    assert cold_adapter.calls == 0 and cold_ledger.summary(RUN)["attempts"] == 3


@pytest.mark.parametrize(
    "cancel_first", [True, False], ids=["cancel-wins", "save-wins"]
)
def test_next_chapter_writer_cancellation_fences_draft_not_receipt(
    tmp_path, monkeypatch, cancel_first
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from test_v2_021 import make_extraction_seed

    from anovel.workflow.chapter import NextChapterWrittenDraft
    from anovel.workflow.interfaces import snapshot_summary

    seed = make_extraction_seed(tmp_path, False)
    env, current, policy = seed.env, seed.case.frozen, seed.case.policies[0]
    step_id = seed.child.step_id
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    observation = env.workflow.extract_chapter(current, **scope, step_id=step_id)
    reader = ChapterWorkflow(env.store, draft_handoff_step_id=step_id)
    selection = scope | {"expected_revision_hash": observation.record_hash}
    handoff = reader.next_chapter_draft_input(current, **selection)
    source_path = tmp_path / "current.json"
    source_path.write_bytes(current.payload)
    handoff_path = tmp_path / "handoff.json"
    handoff_path.write_bytes(handoff.payload_bytes())
    source_args = selection | {"current_input": current.to_dict()}
    task_args = source_args | {"handoff": handoff.to_dict()}
    cancel = task_args | {"operation": "CANCEL_NEXT_CHAPTER_DRAFT"}
    draft_path = tmp_path / "next-chapter.json"
    write = task_args | {
        "operation": "WRITE_NEXT_CHAPTER_DRAFT",
        "output": str(draft_path),
    }
    writer = WorkflowTaskAdapter(
        ChapterWorkflow(
            env.store,
            env.gateway,
            next_chapter_policy=policy,
            draft_handoff_step_id=step_id,
        )
    )
    env.adapter.output = {"text": BODY.decode()}

    def cancel_from_cli():
        cli = run_cli(
            env,
            "--draft-handoff-step-id",
            step_id,
            "cancel-next-chapter-draft",
            "--input",
            source_path,
            "--expected-revision-hash",
            observation.record_hash,
            "--handoff",
            handoff_path,
        )
        assert cli.returncode == 0, cli.stdout + cli.stderr
        return json.loads(cli.stdout)

    entered, release = Event(), Event()

    def wait_for_cancel():
        entered.set()
        assert release.wait(60), (
            "the cancellation CLI did not finish while the Writer paused"
        )

    if cancel_first:
        send = env.adapter.send

        def paused_send(*args):
            wait_for_cancel()
            return send(*args)

        monkeypatch.setattr(env.adapter, "send", paused_send)
    else:
        append = env.store.append_written_draft

        def paused_append(*args, **kwargs):
            saved = append(*args, **kwargs)
            wait_for_cancel()
            return saved

        monkeypatch.setattr(env.store, "append_written_draft", paused_append)

    with ThreadPoolExecutor(max_workers=1) as pool:
        active = pool.submit(writer.execute, write)
        try:
            assert entered.wait(30), (
                active.exception()
                if active.done()
                else "Writer did not reach the pause"
            )
            assert not draft_path.exists()
            summary = cancel_from_cli()
            assert summary["state"] == ("CANCELLED" if cancel_first else "DRAFT_SAVED")
            assert (summary["revision_hash"] is None) == cancel_first
        finally:
            release.set()
        if cancel_first:
            with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_WRITE_CANCELLED$"):
                active.result(timeout=15)
        else:
            written = active.result(timeout=15)
            assert (
                written.prose == BODY
                and draft_path.read_bytes() == written.payload_bytes()
            )

    cold_store = WorkflowStore(env.store_path)
    cold_reader = WorkflowTaskAdapter(
        ChapterWorkflow(cold_store, draft_handoff_step_id=step_id)
    )
    assert snapshot_summary(cold_reader.execute(cancel)) == summary
    writer_request = env.adapter.requests[-1]
    receipt = env.ledger.lookup(RUN, writer_request.logical_id)
    assert (
        receipt.status == "SUCCESS"
        and receipt.request_hash == writer_request.semantic_hash
        and receipt.attempt_id == writer_request.logical_id + "-attempt-1"
    )
    attempts = env.ledger.summary(RUN)["attempts"]
    assert attempts == env.adapter.calls == 3

    saved_scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "chapter_id": handoff.target.id,
    }
    cold_adapter = CountingLocalAdapter(outcome="UNKNOWN")
    cold_writer = WorkflowTaskAdapter(
        ChapterWorkflow(
            cold_store,
            ModelGateway(BudgetLedger(env.ledger_path), cold_adapter),
            next_chapter_policy=policy,
            draft_handoff_step_id=step_id,
        )
    )
    retry_path = tmp_path / "retry-next-chapter.json"
    retry = write | {"output": str(retry_path)}
    before = env.store_path.read_bytes(), env.ledger_path.read_bytes()
    if cancel_first:
        with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_WRITE_CANCELLED$"):
            cold_writer.execute(retry)
        packet = reader._next_chapter_writer_request(current, handoff, observation)
        manual_draft = NextChapterWrittenDraft(
            handoff, sha256(packet).hexdigest(), BODY
        )
        with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_WRITE_CANCELLED$"):
            cold_reader.execute(
                source_args
                | {
                    "operation": "SAVE_NEXT_CHAPTER_DRAFT",
                    "draft": manual_draft.to_dict(),
                }
            )
        with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_UNAVAILABLE$"):
            cold_store.load_written_draft(**saved_scope)
        assert not draft_path.exists() and not retry_path.exists()
    else:
        retained = cold_store.load_written_draft(**saved_scope)
        assert (
            retained.version == 1 and retained.record_hash == summary["revision_hash"]
        )
        assert cold_writer.execute(retry) == written
        assert retry_path.read_bytes() == draft_path.read_bytes()
    assert (env.store_path.read_bytes(), env.ledger_path.read_bytes()) == before
    assert (
        env.ledger.lookup(RUN, writer_request.logical_id).to_bytes()
        == receipt.to_bytes()
    )
    assert cold_adapter.calls == 0 and env.ledger.summary(RUN)["attempts"] == attempts


def test_next_chapter_kimi_writer_saves_and_recovers_exact_receipt(
    tmp_path, monkeypatch, capsys
):
    from test_v2_021 import make_extraction_seed

    from anovel.gateway.models import (
        KIMI_CHAT_ENDPOINT,
        KIMI_CONTEXT_WINDOW,
        KIMI_MODEL,
    )
    from anovel.gateway.provider import KimiChatCompletionsAdapter
    from anovel.workflow.chapter import DraftChapterBrief, KimiDraftWriter
    from anovel.workflow.gateway_binding import read_kimi_writer_receipt

    seed = make_extraction_seed(tmp_path, False)
    env, current = seed.env, seed.case.frozen
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    observation = env.workflow.extract_chapter(
        current, **scope, step_id=seed.child.step_id
    )
    selection = scope | {"expected_revision_hash": observation.record_hash}
    reader = ChapterWorkflow(env.store, draft_handoff_step_id=seed.child.step_id)
    handoff = reader.next_chapter_draft_input(current, **selection)
    brief = {
        "record_type": "draft_chapter_brief",
        "schema_version": "1.0",
        "artifact_state": "DRAFT",
        "project": PROJECT,
        "branch": BRANCH,
        "source_chapter_id": handoff.source.chapter_id.to_dict(),
        "target_chapter_id": handoff.target.id.to_dict(),
        "source_prose_hash": handoff.to_dict()["source_prose_hash"],
        "story_title": "离线续章集成夹具",
        "setting": "校园拍摄的合成场景",
        "arc_goal": "交付试片",
        "character_motives": ["许甲要找到有说服力的素材。"],
        "chapter_title": "失去机位",
        "chapter_goal": "让人物选择影响可用素材。",
        "opening": "承接前章账单。",
        "causal_beats": ["许甲选择等采访，采访被拒后失去备用机位。"],
        "constraints": ["只覆盖当前章。"],
    }
    policy = ModelPolicy(
        "synthetic-kimi-draft-policy",
        KIMI_MODEL,
        KIMI_CHAT_ENDPOINT,
        KIMI_CONTEXT_WINDOW,
        1024,
        1,
        1,
        "synthetic-local-policy-not-provider-approval",
        FUTURE,
        timeout_seconds=1,
        params_bytes=canonical_bytes({"reasoning_effort": "high"}),
    )
    request_path = tmp_path / "approved-request.json"
    retained_payload = handoff.payload_bytes()
    model_request = reader.prepare_next_chapter_model_request(
        current,
        **selection,
        retained_payload=retained_payload,
        brief=DraftChapterBrief.from_dict(brief),
        policy=policy,
        output=request_path,
    )
    private = tmp_path.resolve() / "writer-ledger"
    private.mkdir(mode=0o700)
    ledger_path = private / "ledger.sqlite"
    attempt = model_request.logical_id + "-attempt-1"
    budget = BudgetLimit(PROJECT, BRANCH, RUN, 10_000, 1, FUTURE, 1, 1)
    approvals, credential_reads, posts = [], [], []

    def authorize(request, limit, path, attempt_id, estimate_fee):
        approvals.append((request.to_bytes(), limit, path, attempt_id, estimate_fee))
        return True

    def credential():
        credential_reads.append(True)
        return "synthetic-kimi-draft-credential"

    writer = KimiDraftWriter(model_request, ledger_path, budget, authorize, credential)
    with pytest.raises(WorkflowError, match="^KIMI_DRAFT_AUTHORIZATION_REQUIRED$"):
        replace(writer, authorize=lambda *_: False).result(
            model_request, attempt, recover_only=False
        )
    with pytest.raises(WorkflowError, match="^KIMI_DRAFT_REQUEST_CHANGED$"):
        writer.result(
            replace(model_request, instructions="different chapter instructions"),
            attempt,
            recover_only=False,
        )
    assert not approvals and not credential_reads and not ledger_path.exists()

    count_url = KIMI_CHAT_ENDPOINT.removesuffix("/v1/chat/completions") + (
        "/v1/tokenizers/estimate-token-count"
    )
    prose = "这是一条离线结构化续章验证记录。"
    reply = canonical_bytes(
        {
            "id": "synthetic-kimi-draft-body",
            "object": "chat.completion",
            "model": KIMI_MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": canonical_bytes({"text": prose}).decode(),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }
    )

    def post(_adapter, url, body, _timeout):
        posts.append((url, json.loads(body)))
        if url == count_url:
            return (
                200,
                canonical_bytes({"data": {"total_tokens": 30}}),
                "draft-count-id",
            )
        assert url == KIMI_CHAT_ENDPOINT
        return 200, reply, "draft-generation-id"

    monkeypatch.setattr(KimiChatCompletionsAdapter, "_post", post)
    workflow = ChapterWorkflow(
        env.store, kimi_writer=writer, draft_handoff_step_id=seed.child.step_id
    )
    draft_path = tmp_path / "chapter-2.json"
    result = WorkflowTaskAdapter(workflow).execute(
        selection
        | {
            "operation": "WRITE_NEXT_CHAPTER_DRAFT",
            "current_input": current.to_dict(),
            "handoff": handoff.to_dict(),
            "brief": brief,
            "output": str(draft_path),
        }
    )
    assert result.prose == prose.encode()
    assert approvals == [(model_request.to_bytes(), budget, ledger_path, attempt, None)]
    assert credential_reads == [True]
    assert [url for url, _payload in posts] == [count_url, KIMI_CHAT_ENDPOINT]
    assert posts[0][1]["messages"] == posts[1][1]["messages"]
    assert (
        posts[1][1]["messages"][-1]["content"]
        == model_request.context.model_bytes.decode()
    )
    assert brief["causal_beats"][0] in posts[1][1]["messages"][-1]["content"]
    assert (
        posts[1][1]["response_format"]["json_schema"]["schema"] == model_request.schema
    )
    assert env.ledger.summary(RUN)["attempts"] == 2
    receipt = read_kimi_writer_receipt(ledger_path, model_request, attempt)
    assert receipt is not None and receipt.status == "SUCCESS"
    assert receipt.reply.response_hash == sha256(reply).hexdigest()
    assert receipt.reply.provider_request_id == "draft-generation-id"
    assert receipt.request_hash == model_request.semantic_hash
    assert receipt.policy_hash == policy.content_hash
    assert (
        env.store.load_written_draft(
            project=PROJECT, branch=BRANCH, chapter_id=handoff.target.id
        ).prose
        == prose.encode()
    )

    handoff_path, brief_path, input_path = (
        tmp_path / name for name in ("handoff.json", "brief.json", "input.json")
    )
    handoff_path.write_bytes(retained_payload)
    brief_path.write_bytes(canonical_bytes(brief))
    input_path.write_bytes(current.payload)
    recovery_path = tmp_path / "chapter-2-recovered.json"
    ledger_bytes, store_bytes = ledger_path.read_bytes(), env.store_path.read_bytes()
    assert (
        workflow_cli.main(
            [
                "--db",
                str(env.store_path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                "--draft-handoff-step-id",
                seed.child.step_id,
                "recover-next-chapter-kimi",
                "--input",
                str(input_path),
                "--expected-revision-hash",
                observation.record_hash,
                "--handoff",
                str(handoff_path),
                "--brief",
                str(brief_path),
                "--request",
                str(request_path),
                "--writer-ledger",
                str(ledger_path),
                "--output",
                str(recovery_path),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["artifact_state"] == "DRAFT"
    assert not any(summary[key] for key in ("can_commit", "accepted", "published"))
    assert "prose" not in summary
    assert recovery_path.read_bytes() == draft_path.read_bytes()
    assert (ledger_path.read_bytes(), env.store_path.read_bytes()) == (
        ledger_bytes,
        store_bytes,
    )
    assert len(approvals) == 1 and len(credential_reads) == 1 and len(posts) == 2


@pytest.mark.parametrize(
    ("outcome", "diagnostic"),
    [
        ("UNKNOWN", "NEXT_CHAPTER_MODEL_OUTCOME_UNKNOWN"),
        ("invalid_schema", "INVALID_WRITER_OUTPUT"),
    ],
)
def test_next_chapter_model_gateway_never_publishes_or_resends_bad_responses(
    tmp_path, outcome, diagnostic
):
    from test_v2_021 import make_extraction_seed

    seed = make_extraction_seed(tmp_path, False)
    env, current, policy = seed.env, seed.case.frozen, seed.case.policies[0]
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    observation = env.workflow.extract_chapter(
        current, **scope, step_id=seed.child.step_id
    )
    workflow = ChapterWorkflow(
        env.store,
        env.gateway,
        next_chapter_policy=policy,
        draft_handoff_step_id=seed.child.step_id,
    )
    selection = scope | {"expected_revision_hash": observation.record_hash}
    handoff = workflow.next_chapter_draft_input(current, **selection)
    if outcome == "UNKNOWN":
        env.adapter.outcome = "UNKNOWN"
    else:
        env.adapter.output = {"unexpected_field": "invalid response fixture"}
    output = tmp_path / "chapter-2.json"
    for _ in range(2):
        with pytest.raises(WorkflowError, match=f"^{diagnostic}$"):
            workflow.write_next_chapter_draft(
                current,
                **selection,
                retained_payload=handoff.payload_bytes(),
                output=output,
            )
        assert not output.exists()
        assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 3
        with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_UNAVAILABLE$"):
            env.store.load_written_draft(
                project=PROJECT, branch=BRANCH, chapter_id=handoff.target.id
            )
    live_policy = policy_for(
        endpoint="https://api.openai.com/v1/responses", test_mode=False
    )
    with pytest.raises(WorkflowError, match="^OFFLINE_NEXT_CHAPTER_MODEL_REQUIRED$"):
        ChapterWorkflow(env.store, env.gateway, next_chapter_policy=live_policy)


@pytest.mark.parametrize("receipt_only", [False, True], ids=["local", "openai-receipt"])
def test_next_chapter_model_gateway_rewrites_with_the_edited_source(
    tmp_path, receipt_only
):
    from test_v2_020_scene import scene_case
    from test_v2_020_scene_generation import start_child
    from test_v2_021 import ACTUAL, QUIET

    from anovel.context.scene import SceneDeltaBinding, SceneSpan

    case = scene_case(target_required=True)
    env = harness(
        tmp_path, adapter=CountingLocalAdapter(output={"text": QUIET}), provision=False
    )
    env.ledger.provision(BudgetLimit(PROJECT, BRANCH, RUN, 100000, 5, FUTURE, 1, 1))
    source = start(env, case)
    current, policy = case.frozen, case.policies[0]
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    first_span = SceneSpan(0, len(QUIET), QUIET)
    projection = env.workflow.project_scene(
        current,
        **scope,
        expected_record_hash=source.record_hash,
        source_scene_id=source.contract.scenes[0].id,
        target_scene_id=source.contract.scenes[1].id,
        source_span=first_span,
        ending_span=first_span,
        delta_binding=SceneDeltaBinding(None, "first-source-test"),
    )
    env.adapter.output = {"text": ACTUAL}
    child = start_child(env, case, projection)

    def save_revision(child_step, version, previous=None):
        observation = env.workflow.extract_chapter(current, **scope, step_id=child_step)
        return env.workflow.save_observed_chapter_revision(
            current,
            **scope,
            step_id=child_step,
            expected_observation_hash=observation.record_hash,
            version=version,
            request_id=f"chapter-1-v{version}",
            expected_revision_hash=previous,
        )

    first = save_revision(child.step_id, 1)
    workflow = ChapterWorkflow(env.store, env.gateway, next_chapter_policy=policy)
    old_selection = scope | {"expected_revision_hash": first.record_hash}
    old_handoff = workflow.next_chapter_draft_input(current, **old_selection)
    first_result = "第一版下游模型草稿。"
    env.adapter.output = {"text": first_result}
    workflow.write_next_chapter_draft(
        current,
        **old_selection,
        retained_payload=old_handoff.payload_bytes(),
        output=tmp_path / "chapter-2-v1.json",
    )
    target_scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "chapter_id": old_handoff.target.id,
    }
    old_target = env.store.load_written_draft(**target_scope)

    revised_choice = "改稿选择：甲决定暂停交付。"
    revised_ending = "balance变为45。"
    edited = env.workflow.replace_draft(
        current,
        **scope,
        expected_revision=source.revision,
        expected_prose_hash=source.prose_hash,
        prose=revised_choice.encode(),
    )
    if not receipt_only:
        input_path = tmp_path / "historical-input.json"
        input_path.write_bytes(current.payload)
        history_path = tmp_path / "chapter-2-v1-historical.txt"
        inspect = (
            "inspect-written-draft",
            "--input",
            input_path,
            "--chapter-id",
            old_target.chapter_id.local_id,
        )
        before = env.store_path.read_bytes(), env.ledger_path.read_bytes()
        archived = run_cli(env, *inspect, "--version", 1, "--output", history_path)
        assert archived.returncode == 0, archived.stdout + archived.stderr
        summary = json.loads(archived.stdout)
        assert summary["candidate_version"] == 1
        assert summary["revision_hash"] == old_target.record_hash
        assert summary["source_revision_hash"] == first.record_hash
        assert all(
            summary[key] is False
            for key in (
                "can_dispatch",
                "can_commit",
                "can_issue_permit",
                "accepted",
                "published",
            )
        )
        assert history_path.read_bytes() == old_target.prose == first_result.encode()
        assert history_path.stat().st_mode & 0o777 == 0o600

        refused = tmp_path / "refused-historical.txt"
        for flags, branch, diagnostic in (
            ((), BRANCH, "CHAPTER_ASSEMBLY_NOT_READY"),
            (("--version", 99), BRANCH, "WRITTEN_DRAFT_UNAVAILABLE"),
            (("--version", 1), "another-branch", "WORKFLOW_RUN_UNAVAILABLE"),
        ):
            blocked = run_cli(env, *inspect, *flags, "--output", refused, branch=branch)
            assert blocked.returncode == 2, blocked.stdout + blocked.stderr
            assert json.loads(blocked.stdout)["code"] == diagnostic
        assert not refused.exists()
        reserved = env.ledger_path.with_name(env.ledger_path.name + "-journal")
        reserved_output = run_cli(env, *inspect, "--version", 1, "--output", reserved)
        assert reserved_output.returncode == 2, (
            reserved_output.stdout + reserved_output.stderr
        )
        assert (
            json.loads(reserved_output.stdout)["code"]
            == "WRITTEN_DRAFT_EXPORT_RESERVED_PATH"
        )
        assert not reserved.exists()

        handoff_path = tmp_path / "old-handoff.json"
        handoff_path.write_bytes(old_handoff.payload_bytes())
        continuation = run_cli(
            env,
            "verify-next-chapter",
            "--input",
            input_path,
            "--expected-revision-hash",
            first.record_hash,
            "--handoff",
            handoff_path,
        )
        assert continuation.returncode == 2, continuation.stdout + continuation.stderr
        assert json.loads(continuation.stdout)["code"] == "CHAPTER_ASSEMBLY_NOT_READY"
        assert (env.store_path.read_bytes(), env.ledger_path.read_bytes()) == before
        assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 3

    selected = SceneSpan(0, len(revised_choice), revised_choice)
    next_projection = env.workflow.project_scene(
        current,
        **scope,
        expected_record_hash=edited.record_hash,
        source_scene_id=edited.contract.scenes[0].id,
        target_scene_id=edited.contract.scenes[1].id,
        source_span=selected,
        ending_span=selected,
        delta_binding=SceneDeltaBinding(None, "rewritten-source-test"),
    )
    env.adapter.output = {"text": revised_ending}
    second_child = start_child(
        env, case, next_projection, attempt_id="chapter-1-v2-child"
    )
    second = save_revision(second_child.step_id, 2, first.record_hash)
    new_selection = scope | {"expected_revision_hash": second.record_hash}
    new_handoff = workflow.next_chapter_draft_input(current, **new_selection)
    second_result = "第二版下游模型草稿。"
    env.adapter.output = {"text": second_result}
    request = new_selection | {
        "source_chapter_id": first.chapter_id,
        "expected_target_revision_hash": old_target.record_hash,
        "output": tmp_path / "chapter-2-v2.json",
    }

    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        workflow.rewrite_next_chapter_draft(
            current, **request, retained_payload=old_handoff.payload_bytes()
        )
    assert env.adapter.calls == 4 and not request["output"].exists()
    if receipt_only:
        from anovel.gateway.models import OPENAI_RESPONSES_ENDPOINT, GatewayRequest
        from anovel.workflow.chapter import DraftChapterBrief, OpenAIDraftWriter

        openai_policy = policy_for(endpoint=OPENAI_RESPONSES_ENDPOINT, test_mode=False)
        brief = _commitment_timing_brief(
            second.chapter_id,
            new_handoff.target.id,
            new_handoff.to_dict()["source_prose_hash"],
        )
        pinned = {
            "retained_payload": new_handoff.payload_bytes(),
            "policy": openai_policy,
            "brief": DraftChapterBrief.from_dict(brief),
        }
        unbound = workflow.prepare_next_chapter_model_request(
            current, **new_selection, **pinned, output=tmp_path / "unbound-request.json"
        )
        paths = {
            key: tmp_path / f"{key}.json"
            for key in ("input", "handoff", "brief", "policy", "request")
        }
        paths["input"].write_bytes(current.payload)
        paths["handoff"].write_bytes(new_handoff.payload_bytes())
        paths["brief"].write_bytes(canonical_bytes(brief))
        paths["policy"].write_bytes(openai_policy.to_bytes())
        arguments = (
            "--input",
            paths["input"],
            "--handoff",
            paths["handoff"],
            "--brief",
            paths["brief"],
            "--expected-revision-hash",
            second.record_hash,
            "--expected-target-revision-hash",
            old_target.record_hash,
        )
        prepared = run_cli(
            env,
            "prepare-next-chapter-model-request",
            *arguments,
            "--policy",
            paths["policy"],
            "--output",
            paths["request"],
        )
        assert prepared.returncode == 0, prepared.stdout + prepared.stderr
        model_request = GatewayRequest.from_dict(
            json.loads(paths["request"].read_bytes())
        )
        assert model_request.semantic_hash != unbound.semantic_hash
        assert model_request.context.model_bytes == unbound.context.model_bytes
        model_context = model_request.context.model_bytes.decode()
        assert revised_choice in model_context and revised_ending in model_context
        assert ACTUAL not in model_context

        private = tmp_path.resolve() / "openai-ledger"
        private.mkdir(mode=0o700)
        ledger_path = private / "writer.sqlite"
        ledger_path.touch(mode=0o600)
        writer_ledger = BudgetLedger(ledger_path)
        writer_ledger.provision(
            BudgetLimit(PROJECT, BRANCH, RUN, 100_000, 1, FUTURE, 1, 1)
        )
        synthetic = CountingLocalAdapter(output={"text": second_result})
        receipt = ModelGateway(writer_ledger, synthetic).submit(
            model_request, openai_policy.id, model_request.logical_id + "-attempt-1"
        )
        assert receipt.status == "SUCCESS"
        readback = OpenAIDraftWriter(model_request, ledger_path)
        reopen_task = WorkflowTaskAdapter(
            ChapterWorkflow(env.store, openai_writer=readback)
        )
        rewrite = new_selection | {
            "operation": "REWRITE_NEXT_CHAPTER_DRAFT",
            "current_input": current.to_dict(),
            "source_chapter_id": second.chapter_id.to_dict(),
            "expected_target_revision_hash": old_target.record_hash,
            "handoff": new_handoff.to_dict(),
            "brief": brief,
            "output": str(request["output"]),
        }
        for override, diagnostic in (
            ({"expected_revision_hash": first.record_hash}, "CHAPTER_REVISION_CHANGED"),
            ({"handoff": old_handoff.to_dict()}, "NEXT_CHAPTER_INPUT_CHANGED"),
            (
                {"expected_target_revision_hash": "0" * 64},
                "WRITTEN_DRAFT_REVISION_CONFLICT",
            ),
        ):
            with pytest.raises(WorkflowError, match=f"^{diagnostic}$"):
                reopen_task.execute(rewrite | override)
        for stale_writer, diagnostic in (
            (replace(readback, request=unbound), "OPENAI_DRAFT_REQUEST_CHANGED"),
            (
                replace(readback, ledger_path=private / "missing.sqlite"),
                "OPENAI_DRAFT_RECEIPT_UNAVAILABLE",
            ),
        ):
            with pytest.raises(WorkflowError, match=f"^{diagnostic}$"):
                WorkflowTaskAdapter(
                    ChapterWorkflow(env.store, openai_writer=stale_writer)
                ).execute(rewrite)
        assert (
            not request["output"].exists() and not (private / "missing.sqlite").exists()
        )
        assert env.store.load_written_draft(**target_scope) == old_target

        recovery_args = (
            "recover-next-chapter-openai",
            *arguments,
            "--request",
            paths["request"],
            "--writer-ledger",
            ledger_path,
        )
        recovered = run_cli(env, *recovery_args, "--output", request["output"])
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        cold = WorkflowStore(env.store_path)
        rewritten = cold.load_written_draft(**target_scope)
        assert rewritten.version == 2 and rewritten.prose == second_result.encode()
        assert rewritten.source_revision_hash == second.record_hash
        assert rewritten.previous_revision_hash == old_target.record_hash
        assert cold.load_written_draft(**target_scope, version=1) == old_target
        assert request["output"].read_bytes() == rewritten.payload_bytes()
        summary = json.loads(recovered.stdout)
        assert (
            summary["artifact_state"] == "DRAFT"
            and summary["revision_hash"] == rewritten.record_hash
        )

        before = env.store_path.read_bytes(), ledger_path.read_bytes()
        replay_path = tmp_path / "chapter-2-v2-recovered.json"
        replayed = run_cli(env, *recovery_args, "--output", replay_path)
        assert replayed.returncode == 0, replayed.stdout + replayed.stderr
        assert json.loads(replayed.stdout) == summary
        assert replay_path.read_bytes() == request["output"].read_bytes()
        assert (env.store_path.read_bytes(), ledger_path.read_bytes()) == before
        assert (
            writer_ledger.lookup(RUN, model_request.logical_id).to_bytes()
            == receipt.to_bytes()
        )
        assert writer_ledger.summary(RUN)["attempts"] == synthetic.calls == 1
        assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 4
        return

    rewritten = workflow.rewrite_next_chapter_draft(
        current,
        **request,
        retained_payload=new_handoff.payload_bytes(),
    )
    assert rewritten.prose == second_result.encode() and rewritten.version == 2
    assert rewritten.source_revision_hash == second.record_hash
    assert rewritten.previous_revision_hash == old_target.record_hash
    model_context = env.adapter.requests[-1].context.model_bytes.decode()
    assert revised_choice in model_context and revised_ending in model_context
    assert ACTUAL not in model_context
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 5
    cold = WorkflowStore(env.store_path)
    assert (
        cold.load_written_draft(**target_scope, version=1).prose
        == first_result.encode()
    )
    assert cold.load_written_draft(**target_scope) == rewritten


def _written_draft_setup(tmp_path, monkeypatch, *start_intents, template_version):
    from anovel.context.scene import SceneSpan
    from anovel.domain.delta import ScalarKind
    from anovel.domain.identity import EntityId
    from anovel.planning.versions import PlanHistory, PlanVersion
    from anovel.workflow.extractor import ExactSpan, ExtractionSegment, FactAlias
    from anovel.workflow.models import WorkflowSnapshot

    fixture, history, view = make_case()
    arc = fixture.vision.arcs[0]
    chapter1, chapter2 = arc.chapters
    chapters = arc.chapters + tuple(
        replace(
            chapter2,
            id=EntityId(PROJECT, f"chapter-{number}"),
            number=number,
            scenes=(
                replace(chapter2.scenes[0], id=EntityId(PROJECT, f"scene-{number}")),
            ),
            start_intent=start_intent,
        )
        for number, start_intent in enumerate(start_intents, 3)
    )
    vision = replace(fixture.vision, arcs=(replace(arc, chapters=chapters),))
    fixture = replace(fixture, vision=vision)
    history = PlanHistory(
        (PlanVersion(history.active.id, 1, None, vision, fixture.content_hash),)
    )
    policy = policy_for()
    current = FrozenChapterInput.freeze(
        history=history,
        chapter_id=chapter1.id,
        fixture=fixture,
        view=view,
        budget=ContextBudget(100000),
        policies=(policy,),
        instructions="返回text。",
        template_version=template_version,
    )
    root_choice = "甲根据已知事实“balance为10”选择交付。"
    root_ending = "balance变为30。"
    root_text = root_choice + "\n\n" + root_ending
    root_revision = SimpleNamespace(
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        chapter_id=chapter1.id,
        version=2,
        record_hash="2" * 64,
        candidate=SimpleNamespace(prose=root_text.encode()),
    )
    fact_id = EntityId(PROJECT, "balance")
    root_fact = ExtractionSegment(
        "ACTUAL",
        ExactSpan.from_source(root_text.encode(), len(root_choice) + 2, len(root_text)),
        fact_id,
        "SET_FACT",
        canonical_bytes(30),
    )
    contract, context, request = current.request(RUN, LOGICAL)
    observation = SimpleNamespace(
        record_hash="3" * 64,
        coverage=(root_fact,),
        catalog=(FactAlias(fact_id, "balance", ScalarKind.NUMBER),),
        assembly=SimpleNamespace(
            child=SimpleNamespace(
                prose=root_ending.encode(),
                source=SimpleNamespace(context=context),
                ledger_pin=SimpleNamespace(path=str(tmp_path / "gateway.sqlite")),
                projection=SimpleNamespace(
                    candidate=SimpleNamespace(
                        ending_span=SceneSpan(0, len(root_choice), root_choice)
                    )
                ),
            )
        ),
    )
    # Only the previously validated root extraction is a fixture. All Draft
    # writes, cold reads, revisions and continuation dispatch use the real store.
    monkeypatch.setattr(
        ChapterWorkflow,
        "_current_chapter_revision",
        lambda _self, _current, **_scope: (root_revision, observation),
    )
    monkeypatch.setattr(
        ChapterWorkflow, "load_chapter_revision", lambda _self, **_scope: root_revision
    )
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    assert store.create(
        WorkflowSnapshot(
            current,
            request.to_bytes(),
            canonical_bytes(contract.to_dict()),
            context.to_bytes(),
            ATTEMPT,
            policy.id,
        )
    )
    return current, store, root_revision, fact_id, chapters


def _commitment_timing_brief(source_id, target_id, source_prose_hash):
    return {
        "record_type": "draft_chapter_brief",
        "schema_version": "1.0",
        "artifact_state": "DRAFT",
        "project": PROJECT,
        "branch": BRANCH,
        "source_chapter_id": source_id.to_dict(),
        "target_chapter_id": target_id.to_dict(),
        "source_prose_hash": source_prose_hash,
        "story_title": "本地写作测试",
        "setting": "校园摄影社。",
        "arc_goal": "完成第一场试拍。",
        "character_motives": ["甲想保住原来的场地。"],
        "chapter_title": "借用机位",
        "chapter_goal": "让人物选择带来可见后果。",
        "opening": "从上一章散场接起。",
        "causal_beats": ["甲留下来争取场地。"],
        "constraints": ["按本章安排写。"],
    }


def test_next_chapter_brief_defers_only_open_commitments(tmp_path, monkeypatch):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    current, store, root, _, (_, chapter2, chapter3) = _written_draft_setup(
        tmp_path,
        monkeypatch,
        "承接上一章。",
        template_version="local-commitment-timing",
    )
    events = (
        ("答应周一给家里回电话。", "call-home", "周一", "DUE_UNEXPLAINED"),
        ("约好周三交试片。", "send-clip", "周三", "NOT_DUE"),
        ("上周已经分完账。", "split-payment", "上周五", "FULFILLED"),
    )
    prose = "\n".join(event[0] for event in events)
    notes = []
    for quote, key, due, status in events:
        start = prose.index(quote)
        notes.append(
            DraftContinuity(
                "COMMITMENT",
                SceneSpan(start, start + len(quote), quote),
                commitment=DraftCommitment(key, due, status),
            )
        )
    saved = store.append_written_draft(
        WrittenDraftRevision(
            chapter_id=chapter2.id,
            chapter_number=chapter2.number,
            branch=BRANCH,
            run_id=RUN,
            input_hash=current.content_hash,
            source_chapter_id=root.chapter_id,
            source_revision_hash=root.record_hash,
            writer_input_hash="3" * 64,
            version=1,
            previous_revision_hash=None,
            prose=prose.encode(),
            continuity=tuple(notes),
        )
    )
    workflow = ChapterWorkflow(store)
    selection = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "expected_revision_hash": saved.record_hash,
    }
    handoff = workflow.next_chapter_draft_input(
        current, **selection, source_chapter_id=chapter2.id
    ).to_dict()
    assert [(item["key"], item["status"]) for item in handoff["open_commitments"]] == [
        ("call-home", "DUE_UNEXPLAINED"),
        ("send-clip", "NOT_DUE"),
    ]
    evidence = {
        "source_chapter_id": chapter2.id.to_dict(),
        "source_chapter_number": chapter2.number,
        "source_revision_hash": saved.record_hash,
        "source_prose_hash": saved.prose_hash,
        "span": notes[-1].span.to_dict(),
    }
    fulfilled = [
        {
            "key": "split-payment",
            "due": "上周五",
            "status": "FULFILLED",
            "origin": evidence,
            "latest": evidence,
        }
    ]
    assert handoff["fulfilled_commitments"] == fulfilled
    brief = _commitment_timing_brief(chapter2.id, chapter3.id, saved.prose_hash)
    task = WorkflowTaskAdapter(workflow)
    destination = tmp_path / "model-request.json"
    request = selection | {
        "operation": "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
        "current_input": current.to_dict(),
        "source_chapter_id": chapter2.id.to_dict(),
        "handoff": handoff,
        "policy": policy_for().to_dict(),
        "output": str(destination),
    }
    before = store.path.read_bytes()
    for incorrect in ("call-home", ["call-home", "call-home"], [" "], [1]):
        with pytest.raises(WorkflowError, match="^INVALID_NEXT_CHAPTER_BRIEF$"):
            task.execute(request | {"brief": brief | {"defer_commitments": incorrect}})
    for key in ("unknown", "split-payment"):
        with pytest.raises(WorkflowError, match="^UNKNOWN_INCOMING_DRAFT_COMMITMENT$"):
            task.execute(request | {"brief": brief | {"defer_commitments": [key]}})
    assert not destination.exists()

    legacy = task.execute(
        request | {"brief": brief, "output": str(tmp_path / "legacy-request.json")}
    )
    deferred = ["send-clip", "call-home"]
    prepared = task.execute(
        request | {"brief": brief | {"defer_commitments": deferred}}
    )
    payload = next(
        item["content"]
        for item in json.loads(prepared.context.model_bytes)["items"]
        if item["kind"] == "DRAFT_HANDOFF"
    )
    assert payload["chapter_brief"]["defer_commitments"] == deferred
    assert payload["handoff"]["open_commitments"] == handoff["open_commitments"]
    assert payload["handoff"]["fulfilled_commitments"] == fulfilled
    assert b"defer_commitments" not in legacy.to_bytes()
    assert "fulfilled_commitments" in legacy.instructions
    assert "fulfilled_commitments" in prepared.instructions
    assert "让这些结果影响接下来的选择和关系" in prepared.instructions
    assert "避免把同一次兑现当成新事件重演" in prepared.instructions
    assert "chapter_brief.defer_commitments" in prepared.instructions
    assert "约定仍保持未结" in prepared.instructions
    assert destination.read_bytes() == prepared.to_bytes()
    assert store.path.read_bytes() == before


def test_legacy_fulfillment_handoff_recovers_only_exact_retained_receipt(
    tmp_path, monkeypatch
):
    from anovel.context.scene import SceneSpan
    from anovel.gateway.models import OPENAI_RESPONSES_ENDPOINT
    from anovel.workflow.chapter import (
        DraftChapterBrief,
        OpenAIDraftWriter,
        _next_chapter_model_request,
    )
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    current, store, root, _, (_, chapter2, chapter3) = _written_draft_setup(
        tmp_path, monkeypatch, "承接兑现后的局面。", template_version="legacy-payoff"
    )
    quote = "上周已经分完账。"
    earlier = store.append_written_draft(
        WrittenDraftRevision(
            chapter2.id,
            chapter2.number,
            BRANCH,
            RUN,
            current.content_hash,
            root.chapter_id,
            root.record_hash,
            "3" * 64,
            1,
            None,
            quote.encode(),
            continuity=(
                DraftContinuity(
                    "COMMITMENT",
                    SceneSpan(0, len(quote), quote),
                    commitment=DraftCommitment("split-payment", "上周五", "FULFILLED"),
                ),
            ),
        )
    )
    reader = ChapterWorkflow(store)
    scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "expected_revision_hash": earlier.record_hash,
    }
    handoff, observation = reader._current_next_chapter_draft_input(
        current, **scope, source_chapter_id=chapter2.id
    )
    current_handoff = handoff.to_dict()
    assert current_handoff["fulfilled_commitments"][0]["key"] == "split-payment"
    legacy = replace(handoff, include_fulfilled_commitments=False)
    legacy_handoff = legacy.to_dict()
    assert legacy_handoff == {
        key: value
        for key, value in current_handoff.items()
        if key != "fulfilled_commitments"
    }
    brief = _commitment_timing_brief(chapter2.id, chapter3.id, earlier.prose_hash)
    legacy_packet = reader._next_chapter_writer_request(
        current, legacy, observation, DraftChapterBrief.from_dict(brief)
    )
    policy = policy_for(endpoint=OPENAI_RESPONSES_ENDPOINT, test_mode=False)
    legacy_request = _next_chapter_model_request(
        legacy, legacy_packet, observation.assembly.child.source.context, policy
    )
    assert b"fulfilled_commitments" not in legacy_request.to_bytes()
    request = scope | {
        "current_input": current.to_dict(),
        "source_chapter_id": chapter2.id.to_dict(),
        "handoff": current_handoff,
    }
    task = WorkflowTaskAdapter(reader)
    verify = request | {"operation": "VERIFY_NEXT_CHAPTER"}
    assert task.execute(verify).payload_bytes() == handoff.payload_bytes()
    prepared_path = tmp_path / "model-request.json"
    prepare = request | {
        "operation": "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
        "policy": policy.to_dict(),
        "brief": brief,
        "output": str(prepared_path),
    }
    for operation in (verify, prepare):
        with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
            task.execute(operation | {"handoff": legacy_handoff})
    assert not prepared_path.exists()
    assert task.execute(prepare).to_bytes() != legacy_request.to_bytes()

    private = tmp_path.resolve() / "writer-ledger"
    private.mkdir(mode=0o700)
    ledger_path = private / "ledger.sqlite"
    ledger_path.touch(mode=0o600)
    ledger = BudgetLedger(ledger_path)
    budget = BudgetLimit(PROJECT, BRANCH, RUN, 100_000, 1, FUTURE, 1, 1)
    ledger.provision(budget)
    adapter = CountingLocalAdapter()
    result = ModelGateway(ledger, adapter).submit(
        legacy_request, policy.id, legacy_request.logical_id + "-attempt-1"
    )
    assert result.status == "SUCCESS" and adapter.calls == 1

    def forbidden(*_args):
        pytest.fail("Retained receipt recovery must not authorize or read credentials")

    output = tmp_path / "recovered.json"
    write = request | {
        "operation": "WRITE_NEXT_CHAPTER_DRAFT",
        "handoff": legacy_handoff,
        "brief": brief,
        "output": str(output),
    }
    reader_writer = OpenAIDraftWriter(legacy_request, ledger_path)
    budgeted = WorkflowTaskAdapter(
        ChapterWorkflow(
            store,
            openai_writer=replace(
                reader_writer, budget=budget, authorize=forbidden, credential=forbidden
            ),
        )
    )
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        budgeted.execute(write)
    missing_ledger = private / "missing.sqlite"
    missing_receipt = WorkflowTaskAdapter(
        ChapterWorkflow(
            store, openai_writer=replace(reader_writer, ledger_path=missing_ledger)
        )
    )
    with pytest.raises(WorkflowError, match="^OPENAI_DRAFT_RECEIPT_UNAVAILABLE$"):
        missing_receipt.execute(write)
    assert not missing_ledger.exists()
    recovery = WorkflowTaskAdapter(ChapterWorkflow(store, openai_writer=reader_writer))
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        recovery.execute(
            write | {"handoff": legacy_handoff | {"start_intent": "替换开场。"}}
        )
    assert not output.exists()
    ledger_before = ledger_path.read_bytes()
    recovered = recovery.execute(write)
    assert recovered.handoff.payload_bytes() == legacy.payload_bytes()
    assert recovered.writer_input_hash == sha256(legacy_packet).hexdigest()
    assert recovered.prose == BODY
    assert output.read_bytes() == recovered.payload_bytes()
    assert ledger_path.read_bytes() == ledger_before
    assert ledger.summary(RUN)["attempts"] == adapter.calls == 1


def test_written_draft_annotations_bind_unique_quotes_and_preserve_existing_notes():
    from anovel.context.scene import SceneSpan
    from anovel.domain.identity import EntityId
    from anovel.workflow.written_draft import DraftContinuity, WrittenDraftRevision

    prose = "他收起了相机。她走向后台。灯灭了。灯灭了。"
    first, second = "他收起了相机。", "她走向后台。"
    old_span = SceneSpan(0, len(first), first)
    note = DraftContinuity("FACT", old_span)
    draft = WrittenDraftRevision(
        EntityId(PROJECT, "chapter-2"),
        2,
        BRANCH,
        RUN,
        "1" * 64,
        EntityId(PROJECT, "chapter-1"),
        "2" * 64,
        "3" * 64,
        1,
        None,
        prose.encode(),
        choice=old_span,
        continuity=(note,),
    )
    choice, notes = draft.bind_annotation_quotes(
        {
            "choice": second,
            "add_continuity": [
                {"kind": "FACT", "quote": first},
                {"kind": "CONSEQUENCE", "quote": second},
            ],
        }
    )
    assert choice == SceneSpan(len(first), len(first) + len(second), second)
    assert notes == (note, DraftContinuity("CONSEQUENCE", choice))
    assert draft.bind_annotation_quotes({"choice": None}) == (None, (note,))
    with pytest.raises(WorkflowError, match="^DRAFT_ANNOTATION_QUOTE_MISSING$"):
        draft.bind_annotation_quotes({"choice": "她走出后台。"})
    with pytest.raises(WorkflowError, match="^DRAFT_ANNOTATION_QUOTE_AMBIGUOUS$"):
        draft.bind_annotation_quotes(
            {"add_continuity": [{"kind": "FACT", "quote": "灯灭了。"}]}
        )


def test_written_draft_commitment_review_checks_exact_current_excerpts(
    tmp_path, monkeypatch, capsys
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    current, store, root, _, (_, chapter2, chapter3) = _written_draft_setup(
        tmp_path, monkeypatch, "承接约定。", template_version="local-commitment-review"
    )
    earlier_quote = "说好周一给家里回电话。"
    clip_quote = "答应周三交试片。"
    earlier_prose = f"{earlier_quote}\n{clip_quote}"
    earlier = store.append_written_draft(
        WrittenDraftRevision(
            chapter2.id,
            2,
            BRANCH,
            RUN,
            current.content_hash,
            root.chapter_id,
            root.record_hash,
            "3" * 64,
            1,
            None,
            earlier_prose.encode(),
            continuity=(
                DraftContinuity(
                    "COMMITMENT",
                    SceneSpan(0, len(earlier_quote), earlier_quote),
                    commitment=DraftCommitment("call-home", "周一", "DUE_UNEXPLAINED"),
                ),
                DraftContinuity(
                    "COMMITMENT",
                    SceneSpan(len(earlier_quote) + 1, len(earlier_prose), clip_quote),
                    commitment=DraftCommitment("send-clip", "周三", "NOT_DUE"),
                ),
            ),
        )
    )
    quote = "母亲接听了电话。"
    draft = store.append_written_draft(
        WrittenDraftRevision(
            chapter3.id,
            3,
            BRANCH,
            RUN,
            current.content_hash,
            chapter2.id,
            earlier.record_hash,
            "4" * 64,
            1,
            None,
            quote.encode(),
        )
    )
    selection = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "current_input": current.to_dict(),
        "chapter_id": chapter3.id.to_dict(),
        "expected_revision_hash": draft.record_hash,
    }
    request = selection | {
        "operation": "REVIEW_WRITTEN_DRAFT_COMMITMENTS",
        "review": {},
    }
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    unchanged = store.path.read_bytes()
    root_brief = _commitment_timing_brief(
        root.chapter_id, chapter2.id, sha256(root.candidate.prose).hexdigest()
    ) | {"defer_commitments": []}
    direct_root = task.execute(
        request
        | {
            "chapter_id": chapter2.id.to_dict(),
            "expected_revision_hash": earlier.record_hash,
            "brief": root_brief,
        }
    )
    assert direct_root.commitments == ()
    unobserved_clip = {
        "key": "send-clip",
        "incoming_status": "NOT_DUE",
        "observed_status": None,
        "review_status": "REVIEW_REQUIRED",
    }
    assert snapshot_summary(task.execute(request))["commitments"] == [
        {
            "key": "call-home",
            "incoming_status": "DUE_UNEXPLAINED",
            "observed_status": None,
            "review_status": "REVIEW_REQUIRED",
        },
        unobserved_clip,
    ]
    observations = [{"key": "call-home", "status": "FULFILLED", "quote": quote}]
    review = {"defer": ["call-home", "send-clip"], "observations": observations}
    manual = task.execute(request | {"review": review})
    expected = snapshot_summary(manual)
    assert expected["commitments"] == [
        {
            "key": "call-home",
            "incoming_status": "DUE_UNEXPLAINED",
            "observed_status": "FULFILLED",
            "review_status": "FULFILLED_BEFORE_PLANNED_CHAPTER",
        },
        unobserved_clip,
    ]
    assert not any(
        expected[flag]
        for flag in (
            "can_commit",
            "can_dispatch",
            "can_issue_permit",
            "accepted",
            "published",
        )
    )
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(request | {"review": review, "expected_revision_hash": "a" * 64})
    with pytest.raises(WorkflowError, match="^DRAFT_ANNOTATION_QUOTE_MISSING$"):
        task.execute(
            request
            | {
                "review": review
                | {"observations": [observations[0] | {"quote": "旧原句。"}]}
            }
        )
    with pytest.raises(WorkflowError, match="^UNKNOWN_INCOMING_DRAFT_COMMITMENT$"):
        task.execute(request | {"review": review | {"defer": ["other"]}})
    with pytest.raises(WorkflowError, match="^INVALID_DRAFT_COMMITMENT_REVIEW$"):
        task.execute(request | {"review": review | {"observations": observations * 2}})

    brief = _commitment_timing_brief(chapter2.id, chapter3.id, earlier.prose_hash) | {
        "defer_commitments": ["send-clip", "call-home"],
    }
    implicit = request | {"review": {"observations": observations}, "brief": brief}
    assert task.execute(implicit) == manual
    assert task.execute(implicit | {"review": review}) == manual
    brief_report = tmp_path / "brief-report.json"
    export = implicit | {"output": str(brief_report)}
    with pytest.raises(WorkflowError, match="^DRAFT_COMMITMENT_TIMING_CONFLICT$"):
        task.execute(export | {"review": review | {"defer": ["call-home"]}})
    stale = brief | {"source_prose_hash": "0" * 64}
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_BRIEF_SOURCE_CHANGED$"):
        task.execute(export | {"brief": stale})
    with pytest.raises(WorkflowError, match="^UNKNOWN_INCOMING_DRAFT_COMMITMENT$"):
        task.execute(export | {"brief": brief | {"defer_commitments": ["other"]}})
    assert not brief_report.exists()

    input_path = tmp_path / "current.json"
    input_path.write_bytes(current.payload)
    review_path = tmp_path / "review.json"
    review_path.write_bytes(canonical_bytes(review))
    report = tmp_path / "private-report.json"
    cli = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
        "review-written-draft-commitments",
        "--input",
        str(input_path),
        "--chapter-id",
        chapter3.id.local_id,
        "--expected-revision-hash",
        draft.record_hash,
        "--review",
        str(review_path),
    ]
    assert workflow_cli.main(cli + ["--output", str(report)]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    rows = json.loads(report.read_bytes())["commitments"]
    assert rows[0]["evidence"]["span"]["quote"] == quote
    assert rows[0]["incoming"]["latest"]["span"]["quote"] == earlier_quote
    assert report.stat().st_mode & 0o777 == 0o600
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(canonical_bytes(stale))
    review_path.write_bytes(canonical_bytes({"observations": observations}))
    with_brief = cli + ["--brief", str(brief_path), "--output", str(brief_report)]
    assert workflow_cli.main(with_brief) == 2
    assert (
        json.loads(capsys.readouterr().out)["code"]
        == "NEXT_CHAPTER_BRIEF_SOURCE_CHANGED"
    )
    assert not brief_report.exists()
    brief_path.write_bytes(canonical_bytes(brief))
    assert workflow_cli.main(with_brief) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert brief_report.read_bytes() == report.read_bytes()
    assert brief_report.stat().st_mode & 0o777 == 0o600
    assert store.path.read_bytes() == unchanged

    new_quote = "甲答应晚些再拨回去。"
    revised = task.execute(
        selection
        | {"operation": "EDIT_WRITTEN_DRAFT", "text": new_quote, "choice": None}
    )
    after_edit = store.path.read_bytes()
    latest = implicit | {"expected_revision_hash": revised.record_hash}
    with pytest.raises(WorkflowError, match="^DRAFT_ANNOTATION_QUOTE_MISSING$"):
        task.execute(latest)
    revised_review = {
        "observations": [
            observations[0] | {"status": "DUE_UNEXPLAINED", "quote": new_quote}
        ],
    }
    current_review = task.execute(latest | {"review": revised_review})
    assert current_review.commitments[0]["review_status"] == "REVIEWED"
    assert current_review.commitments[0]["observed_status"] == "DUE_UNEXPLAINED"
    assert current_review.commitments[0]["deferred"] is True
    assert current_review.commitments[0]["evidence"]["span"]["quote"] == new_quote
    assert store.path.read_bytes() == after_edit

    # The synthetic root has no retained extraction row. Keep the real
    # archived child lineage while supplying its one original observation.
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    _, observation = task.service._current_chapter_revision(current, **scope)
    observation.assembly.child.source = store.load(**scope)
    observation.prose_hash = sha256(root.candidate.prose).hexdigest()

    def retained_root(_store, **lookup):
        assert lookup == scope | {
            "chapter_id": root.chapter_id,
            "source_revision_hash": root.record_hash,
            "retained_step_id": None,
        }
        return observation

    monkeypatch.setattr(WorkflowStore, "load_retained_root_observation", retained_root)
    new_predecessor = store.append_written_draft(
        replace(
            earlier,
            version=2,
            previous_revision_hash=earlier.record_hash,
            prose="她改了原定安排。".encode(),
            continuity=(),
        )
    )
    before_history = store.path.read_bytes()
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_SOURCE_CHANGED$"):
        task.execute(latest | {"review": revised_review})
    historical = implicit | {"version": 1}
    archived = task.execute(historical)
    assert archived.payload_bytes() == manual.payload_bytes()
    assert archived.commitments[0]["evidence"]["span"]["quote"] == quote
    latest_archived = task.execute(latest | {"review": revised_review, "version": 2})
    assert latest_archived.payload_bytes() == current_review.payload_bytes()
    assert (
        task.execute(
            request
            | {
                "version": 1,
                "chapter_id": chapter2.id.to_dict(),
                "expected_revision_hash": earlier.record_hash,
                "brief": root_brief,
            }
        )
        == direct_root
    )
    for invalid, diagnostic in (
        ({"expected_revision_hash": revised.record_hash}, "CHAPTER_REVISION_CHANGED"),
        ({"review": revised_review}, "DRAFT_ANNOTATION_QUOTE_MISSING"),
        (
            {"brief": brief | {"source_prose_hash": new_predecessor.prose_hash}},
            "NEXT_CHAPTER_BRIEF_SOURCE_CHANGED",
        ),
        ({"save_observations": True}, "INVALID_DRAFT_COMMITMENT_REVIEW_SAVE"),
        ({"version": True}, "INVALID_WORKFLOW_TASK_REQUEST"),
    ):
        with pytest.raises(WorkflowError, match=f"^{diagnostic}$"):
            task.execute(historical | invalid)

    historical_args = cli + ["--brief", str(brief_path), "--version", "1"]
    historical_report = tmp_path / "historical-review.json"
    assert (
        workflow_cli.main(historical_args + ["--output", str(historical_report)]) == 0
    )
    assert json.loads(capsys.readouterr().out) == snapshot_summary(archived)
    assert historical_report.read_bytes() == report.read_bytes()
    assert historical_report.stat().st_mode & 0o777 == 0o600
    assert workflow_cli.main(historical_args + ["--save-observations"]) == 2
    assert (
        json.loads(capsys.readouterr().out)["code"]
        == "INVALID_DRAFT_COMMITMENT_REVIEW_SAVE"
    )
    assert store.path.read_bytes() == before_history


def test_saved_commitment_review_updates_next_chapter_handoff(
    tmp_path, monkeypatch, capsys
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    current, store, root, _, (_, chapter2, chapter3, chapter4) = _written_draft_setup(
        tmp_path,
        monkeypatch,
        "承接约定。",
        "处理试片。",
        template_version="commitment-save",
    )

    def locate(prose, quote):
        start = prose.index(quote)
        return SceneSpan(start, start + len(quote), quote)

    home_quote = "约好周一给家里回电话。"
    clip_quote = "约好周三交试片。"
    old_payoff_quote = "上周已经分完账。"
    earlier_prose = f"{home_quote}\n{clip_quote}\n{old_payoff_quote}"
    open_home = DraftCommitment("call-home", "周一", "DUE_UNEXPLAINED")
    open_clip = DraftCommitment("send-clip", "周三", "NOT_DUE")
    earlier = store.append_written_draft(
        WrittenDraftRevision(
            chapter2.id,
            2,
            BRANCH,
            RUN,
            current.content_hash,
            root.chapter_id,
            root.record_hash,
            "3" * 64,
            1,
            None,
            earlier_prose.encode(),
            continuity=(
                DraftContinuity(
                    "COMMITMENT",
                    locate(earlier_prose, home_quote),
                    commitment=open_home,
                ),
                DraftContinuity(
                    "COMMITMENT",
                    locate(earlier_prose, clip_quote),
                    commitment=open_clip,
                ),
                DraftContinuity(
                    "COMMITMENT",
                    locate(earlier_prose, old_payoff_quote),
                    commitment=DraftCommitment("split-payment", "上周五", "FULFILLED"),
                ),
            ),
        )
    )
    choice_quote = "甲决定先给家里回电话。"
    fulfilment_quote = "母亲接听了电话。"
    fact_quote = "试片仍在桌上。"
    prose = f"{choice_quote}\n{fulfilment_quote}\n{fact_quote}"
    choice = locate(prose, choice_quote)
    fact = DraftContinuity("FACT", locate(prose, fact_quote))
    draft = store.append_written_draft(
        WrittenDraftRevision(
            chapter3.id,
            3,
            BRANCH,
            RUN,
            current.content_hash,
            chapter2.id,
            earlier.record_hash,
            "4" * 64,
            1,
            None,
            prose.encode(),
            choice=choice,
            continuity=(
                DraftContinuity("COMMITMENT", choice, commitment=open_home),
                fact,
            ),
        )
    )
    common = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "current_input": current.to_dict(),
        "expected_revision_hash": draft.record_hash,
    }
    review = {
        "observations": [
            {"key": "call-home", "status": "FULFILLED", "quote": fulfilment_quote},
        ],
    }
    brief = _commitment_timing_brief(chapter2.id, chapter3.id, earlier.prose_hash) | {
        "defer_commitments": ["call-home", "send-clip"],
    }
    request = common | {
        "operation": "REVIEW_WRITTEN_DRAFT_COMMITMENTS",
        "chapter_id": chapter3.id.to_dict(),
        "brief": brief,
        "review": review,
    }
    projection = common | {
        "operation": "PROJECT_NEXT_CHAPTER",
        "source_chapter_id": chapter3.id.to_dict(),
        "output": str(tmp_path / "handoff-before.json"),
    }
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    old_handoff = task.execute(projection).to_dict()
    assert {item["key"] for item in old_handoff["open_commitments"]} == {
        "call-home",
        "send-clip",
    }
    assert "fulfilled_commitments" not in old_handoff
    before_model = task.execute(
        projection
        | {
            "operation": "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
            "handoff": old_handoff,
            "policy": policy_for().to_dict(),
            "output": str(tmp_path / "request-before.json"),
        }
    )
    assert b"fulfilled_commitments" not in before_model.to_bytes()
    before = store.path.read_bytes()
    preview = task.execute(request)
    assert preview.saved_revision is None
    assert preview.commitments[0]["review_status"] == "FULFILLED_BEFORE_PLANNED_CHAPTER"

    input_path = tmp_path / "current.json"
    input_path.write_bytes(current.payload)
    review_path = tmp_path / "review.json"
    review_path.write_bytes(canonical_bytes(review))
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(canonical_bytes(brief))
    report_path = tmp_path / "refused-report.json"
    save = request | {"save_observations": True}
    with pytest.raises(WorkflowError, match="^INVALID_DRAFT_COMMITMENT_REVIEW_SAVE$"):
        task.execute(save | {"output": str(report_path)})
    cli = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
        "review-written-draft-commitments",
        "--input",
        str(input_path),
        "--chapter-id",
        chapter3.id.local_id,
        "--expected-revision-hash",
        draft.record_hash,
        "--brief",
        str(brief_path),
        "--review",
        str(review_path),
        "--save-observations",
    ]
    assert workflow_cli.main(cli + ["--output", str(report_path)]) == 2
    assert (
        json.loads(capsys.readouterr().out)["code"]
        == "INVALID_DRAFT_COMMITMENT_REVIEW_SAVE"
    )
    assert not report_path.exists()
    assert store.path.read_bytes() == before

    assert workflow_cli.main(cli) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["artifact_state"] == "DRAFT"
    assert summary["revision_hash"] == draft.record_hash
    assert summary["saved_version"] == 2
    assert summary["commitments"] == preview.summary()["commitments"]
    cold = WorkflowStore(store.path)
    scope = {"project": PROJECT, "branch": BRANCH, "chapter_id": chapter3.id}
    saved = cold.load_written_draft(**scope)
    assert saved.record_hash == summary["saved_revision_hash"]
    assert saved.previous_revision_hash == draft.record_hash
    assert saved.prose == draft.prose and saved.choice == choice
    assert fact in saved.continuity
    assert [note for note in saved.continuity if note.commitment is not None] == [
        DraftContinuity(
            "COMMITMENT",
            locate(prose, fulfilment_quote),
            commitment=replace(open_home, status="FULFILLED"),
        ),
    ]
    assert cold.load_written_draft(**scope, version=1) == draft

    after = store.path.read_bytes()
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(save)
    latest = save | {"expected_revision_hash": saved.record_hash}
    assert task.execute(latest).saved_revision == saved
    assert task.execute(latest | {"review": {}}).saved_revision == saved
    assert store.path.read_bytes() == after

    new_handoff = task.execute(
        projection
        | {
            "expected_revision_hash": saved.record_hash,
            "output": str(tmp_path / "handoff-after.json"),
        }
    ).to_dict()
    assert new_handoff["artifact_state"] == "DRAFT"
    assert new_handoff["target_chapter_id"] == chapter4.id.to_dict()
    assert new_handoff["source_revision_hash"] == saved.record_hash
    assert new_handoff["source_prose_hash"] == old_handoff["source_prose_hash"]
    assert new_handoff["ending"] == old_handoff["ending"]
    assert new_handoff["open_commitments"] == [
        item for item in old_handoff["open_commitments"] if item["key"] == "send-clip"
    ]
    original_home = next(
        item for item in old_handoff["open_commitments"] if item["key"] == "call-home"
    )
    assert new_handoff["fulfilled_commitments"] == [
        {
            "key": "call-home",
            "due": "周一",
            "status": "FULFILLED",
            "origin": original_home["origin"],
            "latest": {
                "source_chapter_id": chapter3.id.to_dict(),
                "source_chapter_number": chapter3.number,
                "source_revision_hash": saved.record_hash,
                "source_prose_hash": saved.prose_hash,
                "span": locate(prose, fulfilment_quote).to_dict(),
            },
        }
    ]


def test_written_draft_cli_relocates_unprovided_annotations(
    tmp_path, monkeypatch, capsys
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    frozen, store, root, _, (_, chapter2) = _written_draft_setup(
        tmp_path, monkeypatch, template_version="local-draft-cli-annotation-test"
    )
    choice = "甲选择回拨。"
    fulfilment = "母亲接听了电话。"
    consequence = "通话使甲错过排练。"
    original = f"{choice}\n{fulfilment}\n{consequence}"

    def locate(body, quote):
        start = body.index(quote)
        return SceneSpan(start, start + len(quote), quote)

    notes = (
        DraftContinuity(
            "COMMITMENT",
            locate(original, fulfilment),
            commitment=DraftCommitment("callback", "周一中午", "FULFILLED"),
        ),
        DraftContinuity("CONSEQUENCE", locate(original, consequence)),
    )
    saved = store.append_written_draft(
        WrittenDraftRevision(
            chapter_id=chapter2.id,
            chapter_number=chapter2.number,
            branch=BRANCH,
            run_id=RUN,
            input_hash=frozen.content_hash,
            source_chapter_id=root.chapter_id,
            source_revision_hash=root.record_hash,
            writer_input_hash="3" * 64,
            version=1,
            previous_revision_hash=None,
            prose=original.encode(),
            choice=locate(original, choice),
            continuity=notes,
        )
    )
    input_path = tmp_path / "current.json"
    input_path.write_bytes(frozen.payload)
    prose_path = tmp_path / "edited.txt"
    args = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
        "edit-written-draft",
        "--input",
        str(input_path),
        "--chapter-id",
        chapter2.id.local_id,
        "--prose",
        str(prose_path),
    ]

    def edit(text, base, *options):
        prose_path.write_bytes(text.encode())
        code = workflow_cli.main(
            args + ["--expected-revision-hash", base.record_hash, *options]
        )
        captured = capsys.readouterr()
        assert not captured.err
        return code, json.loads(captured.out)

    def latest():
        return WorkflowStore(store.path).load_written_draft(
            project=PROJECT, branch=BRANCH, chapter_id=chapter2.id
        )

    def blocked(text, base, error, *options):
        before = store.path.read_bytes()
        assert edit(text, base, *options) == (2, {"status": "BLOCKED", "code": error})
        assert store.path.read_bytes() == before

    def save(text, base, *options):
        code, result = edit(text, base, *options)
        assert code == 0 and result["artifact_state"] == "DRAFT"
        revision = latest()
        assert revision.record_hash == result["revision_hash"]
        assert revision.previous_revision_hash == base.record_hash
        assert revision.prose == text.encode()
        return revision

    blocked(
        original.replace(fulfilment, ""), saved, "DRAFT_EDIT_PREVIEW_REVIEW_REQUIRED"
    )
    blocked(original + choice, saved, "DRAFT_EDIT_PREVIEW_REVIEW_REQUIRED")
    assert latest() == saved

    shifted_text = "改一处𠮷字与😀。\n" + original
    shifted = save(shifted_text, saved)
    assert shifted.choice == locate(shifted_text, choice)
    assert shifted.continuity == tuple(
        replace(note, span=locate(shifted_text, note.span.quote)) for note in notes
    )
    blocked(shifted_text, saved, "CHAPTER_REVISION_CHANGED")

    new_choice = "甲决定先发消息。"
    replaced_text = shifted_text.replace(choice, new_choice)
    choice_path = tmp_path / "choice.json"
    choice_span = locate(replaced_text, new_choice)
    choice_path.write_bytes(canonical_bytes(choice_span.to_dict()))
    chosen = save(replaced_text, shifted, "--choice", str(choice_path))
    assert chosen.choice == choice_span
    assert chosen.continuity == tuple(
        replace(note, span=locate(replaced_text, note.span.quote)) for note in notes
    )

    continuity_path = tmp_path / "continuity.json"
    continuity_path.write_bytes(canonical_bytes([]))
    cleared_notes = save(new_choice, chosen, "--continuity", str(continuity_path))
    assert cleared_notes.choice == locate(new_choice, new_choice)
    assert cleared_notes.continuity == ()

    choice_path.write_bytes(canonical_bytes(None))
    cleared_choice = save("甲离开了。", cleared_notes, "--choice", str(choice_path))
    assert cleared_choice.choice is None and cleared_choice.continuity == ()


@pytest.mark.parametrize(
    ("original", "edited", "quote", "reason"),
    [
        ("原有选段。", "修改选段。", "原有选段。", "QUOTE_MISSING"),
        ("café", "cafe\u0301", "café", "QUOTE_MISSING"),
        ("单次原句。", "单次原句。单次原句。", "单次原句。", "QUOTE_AMBIGUOUS"),
        ("aaa", "aa", "aa", "QUOTE_AMBIGUOUS"),
        ("aa", "aaa", "aa", "QUOTE_AMBIGUOUS"),
    ],
)
def test_written_draft_preview_reports_nonunique_or_missing_exact_anchors(
    original, edited, quote, reason
):
    from anovel.context.scene import SceneSpan
    from anovel.domain.identity import EntityId
    from anovel.workflow.written_draft import DraftContinuity, WrittenDraftRevision

    span = SceneSpan(0, len(quote), quote)
    revision = WrittenDraftRevision(
        chapter_id=EntityId(PROJECT, "chapter-2"),
        chapter_number=2,
        branch=BRANCH,
        run_id=RUN,
        input_hash="1" * 64,
        source_chapter_id=EntityId(PROJECT, "chapter-1"),
        source_revision_hash="2" * 64,
        writer_input_hash="3" * 64,
        version=1,
        previous_revision_hash=None,
        prose=original.encode(),
        choice=span,
        continuity=(DraftContinuity("FACT", span, carry_to_chapter=4),),
    )
    before = revision.payload_bytes()

    preview = revision.preview_edit(edited.encode())

    assert preview.choice is None and preview.continuity == ()
    assert [
        (item.kind, item.note_index, item.reason, item.span) for item in preview.issues
    ] == [
        ("CHOICE", None, reason, span),
        ("FACT", 0, reason, span),
    ]
    assert revision.payload_bytes() == before


def test_written_draft_preview_relocates_exact_anchors_before_explicit_edit(
    tmp_path, monkeypatch
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    frozen, store, root, _, (_, chapter2, _, _) = _written_draft_setup(
        tmp_path,
        monkeypatch,
        "试演交接。",
        "兑现约定。",
        template_version="local-draft-preview-test",
    )
    text = "甲选择回拨。\n母亲接听了电话。\n双方约定周三交试片。"

    def locate(body, quote):
        start = body.index(quote)
        return SceneSpan(start, start + len(quote), quote)

    choice = locate(text, "甲选择回拨。")
    continuity = (
        DraftContinuity(
            "COMMITMENT",
            locate(text, "母亲接听了电话。"),
            commitment=DraftCommitment("callback", "周一中午", "FULFILLED"),
        ),
        DraftContinuity(
            "FACT", locate(text, "双方约定周三交试片。"), carry_to_chapter=4
        ),
    )
    saved = store.append_written_draft(
        WrittenDraftRevision(
            chapter_id=chapter2.id,
            chapter_number=chapter2.number,
            branch=BRANCH,
            run_id=RUN,
            input_hash=frozen.content_hash,
            source_chapter_id=root.chapter_id,
            source_revision_hash=root.record_hash,
            writer_input_hash="3" * 64,
            version=1,
            previous_revision_hash=None,
            prose=text.encode(),
            choice=choice,
            continuity=continuity,
        )
    )
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    edited = "补一处𠮷字与😀。\n" + text
    selection = {
        "current_input": frozen.to_dict(),
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "chapter_id": chapter2.id.to_dict(),
        "expected_revision_hash": saved.record_hash,
        "text": edited,
    }
    before = store.path.read_bytes()
    preview_path = tmp_path / "preview.json"
    preview = task.execute(
        selection
        | {"operation": "PREVIEW_WRITTEN_DRAFT_EDIT", "output": str(preview_path)}
    )
    expected_choice = locate(edited, choice.quote)
    expected_continuity = tuple(
        replace(item, span=locate(edited, item.span.quote)) for item in continuity
    )
    assert preview.chapter_id == chapter2.id
    assert preview.revision_hash == saved.record_hash
    assert preview.prose_hash == sha256(edited.encode()).hexdigest()
    assert preview.choice == expected_choice
    assert preview.continuity == expected_continuity
    assert preview.issues == ()
    assert preview_path.read_bytes() == canonical_bytes(preview.to_dict())
    assert preview_path.stat().st_mode & 0o777 == 0o600
    summary = snapshot_summary(preview)
    assert summary["state"] == "DRAFT_EDIT_PREVIEW"
    assert summary["artifact_state"] == "DRAFT"
    assert summary["review_required_count"] == 0
    assert choice.quote not in json.dumps(summary, ensure_ascii=False)
    assert not any(summary[flag] for flag in ("can_commit", "accepted", "published"))
    assert store.path.read_bytes() == before

    edit = selection | {"operation": "EDIT_WRITTEN_DRAFT"}
    with pytest.raises(WorkflowError, match="^INVALID_WRITTEN_DRAFT$"):
        task.execute(
            edit
            | {
                "choice": choice.to_dict(),
                "continuity": [item.to_dict() for item in continuity],
            }
        )
    assert store.path.read_bytes() == before
    updated = task.execute(
        edit
        | {
            "choice": expected_choice.to_dict(),
            "continuity": [item.to_dict() for item in expected_continuity],
        }
    )
    assert updated.version == 2
    assert updated.previous_revision_hash == saved.record_hash
    assert updated.choice == expected_choice
    assert updated.continuity == expected_continuity
    stale_path = tmp_path / "stale.json"
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(
            selection
            | {"operation": "PREVIEW_WRITTEN_DRAFT_EDIT", "output": str(stale_path)}
        )
    assert not stale_path.exists()


def test_apply_written_draft_preview_saves_only_exact_reviewed_prose(
    tmp_path, monkeypatch
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.written_draft import (
        DraftCommitment,
        DraftContinuity,
        WrittenDraftRevision,
    )

    frozen, store, root, _, (_, chapter2, _, _) = _written_draft_setup(
        tmp_path,
        monkeypatch,
        "复核本次约定。",
        "兑现余下约定。",
        template_version="local-draft-preview-apply-test",
    )
    old_choice = "甲打算周一再打电话。"
    new_choice = "甲决定今天就打电话。"
    kept_quote = "母亲接听了电话。"
    old_fact = "试片由甲保管。"
    new_fact = "试片已交给搭档。"
    removed_quote = "搭档因此漏了一次排练。"
    original = f"{old_choice}\n{kept_quote}\n{old_fact}\n{removed_quote}"
    edited = f"加一处𠮷字与😀。\n{new_choice}\n{kept_quote}\n{new_fact}"

    def locate(text, quote):
        start = text.index(quote)
        return SceneSpan(start, start + len(quote), quote)

    notes = (
        DraftContinuity(
            "COMMITMENT",
            locate(original, kept_quote),
            commitment=DraftCommitment("callback", "周一中午", "FULFILLED"),
        ),
        DraftContinuity("FACT", locate(original, old_fact), carry_to_chapter=4),
        DraftContinuity("CONSEQUENCE", locate(original, removed_quote)),
    )
    saved = store.append_written_draft(
        WrittenDraftRevision(
            chapter_id=chapter2.id,
            chapter_number=chapter2.number,
            branch=BRANCH,
            run_id=RUN,
            input_hash=frozen.content_hash,
            source_chapter_id=root.chapter_id,
            source_revision_hash=root.record_hash,
            writer_input_hash="3" * 64,
            version=1,
            previous_revision_hash=None,
            prose=original.encode(),
            choice=locate(original, old_choice),
            continuity=notes,
        )
    )
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    selection = {
        "current_input": frozen.to_dict(),
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "chapter_id": chapter2.id.to_dict(),
        "text": edited,
    }
    before = store.path.read_bytes()
    preview_path = tmp_path / "review-preview.json"
    preview = task.execute(
        selection
        | {
            "operation": "PREVIEW_WRITTEN_DRAFT_EDIT",
            "expected_revision_hash": saved.record_hash,
            "output": str(preview_path),
        }
    )
    assert [issue.note_index for issue in preview.issues] == [None, 1, 2]
    preview_payload = json.loads(preview_path.read_bytes())
    choice = locate(edited, new_choice)
    fact = locate(edited, new_fact)
    resolutions = [
        {"note_index": 2, "span": None},
        {"note_index": None, "span": choice.to_dict()},
        {"note_index": 1, "span": fact.to_dict()},
    ]
    apply = selection | {
        "operation": "APPLY_WRITTEN_DRAFT_EDIT_PREVIEW",
        "preview": preview_payload,
    }
    for invalid in (
        {},
        {"resolutions": resolutions[:-1]},
        {"resolutions": resolutions + resolutions[:1]},
        {"resolutions": resolutions + [{"note_index": 0, "span": None}]},
    ):
        with pytest.raises(WorkflowError, match="^DRAFT_EDIT_PREVIEW_REVIEW_REQUIRED$"):
            task.execute(apply | invalid)
    with pytest.raises(WorkflowError, match="^INVALID_WRITTEN_DRAFT$"):
        task.execute(
            apply
            | {
                "resolutions": resolutions[:-1]
                + [{"note_index": 1, "span": notes[1].span.to_dict()}],
            }
        )
    approved = apply | {"resolutions": resolutions}
    with pytest.raises(WorkflowError, match="^DRAFT_EDIT_PREVIEW_PROSE_CHANGED$"):
        task.execute(approved | {"text": edited + "换了拟改正文。"})
    with pytest.raises(WorkflowError, match="^DRAFT_EDIT_PREVIEW_CHANGED$"):
        task.execute(approved | {"preview": preview_payload | {"continuity": []}})
    assert store.path.read_bytes() == before

    updated = task.execute(approved)
    assert updated.prose == edited.encode()
    assert updated.version == 2 and updated.previous_revision_hash == saved.record_hash
    assert updated.choice == choice
    assert updated.continuity == (
        replace(notes[0], span=locate(edited, kept_quote)),
        replace(notes[1], span=fact),
    )
    assert snapshot_summary(updated)["artifact_state"] == "DRAFT"
    cold = WorkflowStore(store.path)
    for revision in (saved, updated):
        assert (
            cold.load_written_draft(
                project=PROJECT,
                branch=BRANCH,
                chapter_id=chapter2.id,
                version=revision.version,
            )
            == revision
        )
    after = store.path.read_bytes()
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(approved)
    assert store.path.read_bytes() == after

    followup = "再校一处。\n" + edited
    next_preview = task.execute(
        selection
        | {
            "operation": "PREVIEW_WRITTEN_DRAFT_EDIT",
            "text": followup,
            "expected_revision_hash": updated.record_hash,
            "output": str(tmp_path / "issue-free-preview.json"),
        }
    )
    assert next_preview.issues == ()
    finalized = task.execute(
        apply | {"text": followup, "preview": next_preview.to_dict()}
    )
    assert finalized.prose == followup.encode()
    assert (
        finalized.version == 3
        and finalized.previous_revision_hash == updated.record_hash
    )
    assert finalized.choice == locate(followup, new_choice)
    assert finalized.continuity == tuple(
        replace(item, span=locate(followup, item.span.quote))
        for item in updated.continuity
    )


def test_reopened_written_draft_edit_drives_the_third_chapter(
    tmp_path, monkeypatch, capsys
):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.interfaces import snapshot_summary

    current, store, root_revision, fact_id, (_, chapter2, chapter3) = (
        _written_draft_setup(
            tmp_path,
            monkeypatch,
            "承接第二章的决定并核对回单。",
            template_version="local-three-chapter-draft-test",
        )
    )
    # Same UTF-8 prose as the retained Chapter 2 export used in the local replay.
    chapter2_prose = "本地续写测试。交付后，余额仍为30。".encode()
    new_choice = "甲改变主意，决定先暂停交付。"
    new_ending = "balance变为45。"
    revised_prose = new_choice + "\n\nbalance变为30。\n\n" + new_ending
    chapter3_prose = "甲遵照暂停交付的决定，核对了四十五的回单。".encode()
    latest_choice = "甲核过退货单，决定改由自己送货。"
    latest_ending = "balance变为72。"
    latest_prose = latest_choice + "\n\nbalance变为45。\n\n" + latest_ending
    rewritten_chapter3_prose = "甲把七十二的回单收好，决定亲自送货。".encode()
    expected_third_writes = iter(
        (
            (new_choice, new_ending, 45, chapter3_prose),
            (latest_choice, latest_ending, 72, rewritten_chapter3_prose),
        )
    )
    writer_inputs = []

    def writer(raw):
        material = json.loads(raw)
        writer_inputs.append(material)
        if material["handoff"]["target_chapter_number"] == 2:
            return chapter2_prose
        choice, ending, balance, prose = next(expected_third_writes)
        assert material["handoff"]["target_chapter_id"] == chapter3.id.to_dict()
        assert material["handoff"]["ending"]["quote"] == ending
        assert material["previous_scene_ending"]["quote"] == choice
        assert material["handoff"]["start_intent"] == chapter3.start_intent
        assert [
            (fact["fact_id"], fact["value"], fact["span"]["quote"])
            for fact in material["observed_draft_facts"]
        ] == [(fact_id.to_dict(), balance, ending)]
        return prose

    task = WorkflowTaskAdapter(ChapterWorkflow(store, next_chapter_writer=writer))
    root = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "current_input": current.to_dict(),
    }
    first_selection = root | {"expected_revision_hash": root_revision.record_hash}
    initial_handoff = task.execute(
        first_selection
        | {
            "operation": "PROJECT_NEXT_CHAPTER",
            "output": str(tmp_path / "initial-handoff.json"),
        }
    )
    chapter2_path = tmp_path / "chapter-2.json"
    task.execute(
        first_selection
        | {
            "operation": "WRITE_NEXT_CHAPTER_DRAFT",
            "handoff": initial_handoff.to_dict(),
            "output": str(chapter2_path),
        }
    )
    saved = task.execute(
        first_selection
        | {
            "operation": "SAVE_NEXT_CHAPTER_DRAFT",
            "draft": json.loads(chapter2_path.read_bytes()),
        }
    )
    assert saved.version == 1 and saved.prose == chapter2_prose

    # Reopen independently so that a cached object cannot satisfy the test.
    reopened_store = WorkflowStore(store.path)
    reopened = WorkflowTaskAdapter(
        ChapterWorkflow(reopened_store, next_chapter_writer=writer)
    )
    second = root | {"chapter_id": chapter2.id.to_dict()}
    recovered = reopened.execute(second | {"operation": "INSPECT_WRITTEN_DRAFT"})
    assert recovered.payload_bytes() == saved.payload_bytes()
    continuation = root | {"source_chapter_id": chapter2.id.to_dict()}
    old_handoff = reopened.execute(
        continuation
        | {
            "operation": "PROJECT_NEXT_CHAPTER",
            "expected_revision_hash": saved.record_hash,
            "output": str(tmp_path / "before-edit.json"),
        }
    )
    edit = second | {
        "operation": "EDIT_WRITTEN_DRAFT",
        "expected_revision_hash": saved.record_hash,
        "text": revised_prose,
        "choice": SceneSpan(0, len(new_choice), new_choice).to_dict(),
    }
    edited = reopened.execute(edit)
    assert edited.version == 2 and edited.previous_revision_hash == saved.record_hash
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        reopened.execute(edit | {"text": revised_prose + "另一份旧版本修改。"})
    assert (
        reopened_store.load_written_draft(
            project=PROJECT, branch=BRANCH, chapter_id=chapter2.id, version=1
        ).prose
        == chapter2_prose
    )
    new_selection = continuation | {"expected_revision_hash": edited.record_hash}
    new_handoff = reopened.execute(
        new_selection
        | {
            "operation": "PROJECT_NEXT_CHAPTER",
            "output": str(tmp_path / "after-edit.json"),
        }
    )
    assert new_handoff.to_dict()["ending"]["quote"] == new_ending
    chapter3_path = tmp_path / "chapter-3.json"
    write = new_selection | {
        "operation": "WRITE_NEXT_CHAPTER_DRAFT",
        "handoff": new_handoff.to_dict(),
        "output": str(chapter3_path),
    }
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        reopened.execute(write | {"expected_revision_hash": saved.record_hash})
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        reopened.execute(write | {"handoff": old_handoff.to_dict()})
    assert len(writer_inputs) == 1 and not chapter3_path.exists()
    result = reopened.execute(write)
    assert result.prose == chapter3_prose
    assert json.loads(chapter3_path.read_bytes())["artifact_state"] == "DRAFT"
    stored_third = WorkflowStore(store.path).load_written_draft(
        project=PROJECT, branch=BRANCH, chapter_id=chapter3.id
    )
    assert stored_third.version == 1 and stored_third.prose == chapter3_prose
    assert stored_third.source_revision_hash == edited.record_hash
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_DRAFT_EXPORT_FAILED$"):
        reopened.execute(write)
    retry_path = tmp_path / "chapter-3-reopened.json"
    reopened.execute(write | {"output": str(retry_path)})
    assert retry_path.read_bytes() == chapter3_path.read_bytes()
    assert len(writer_inputs) == 2

    latest_source = reopened.execute(
        edit
        | {
            "expected_revision_hash": edited.record_hash,
            "text": latest_prose,
            "choice": SceneSpan(0, len(latest_choice), latest_choice).to_dict(),
        }
    )
    assert latest_source.version == 3
    assert latest_source.previous_revision_hash == edited.record_hash

    reopened = WorkflowTaskAdapter(
        ChapterWorkflow(WorkflowStore(store.path), next_chapter_writer=writer)
    )
    inspect_third = root | {
        "operation": "INSPECT_WRITTEN_DRAFT",
        "chapter_id": chapter3.id.to_dict(),
    }
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_SOURCE_CHANGED$"):
        reopened.execute(inspect_third)

    current_selection = continuation | {
        "expected_revision_hash": latest_source.record_hash
    }
    latest_handoff = reopened.execute(
        current_selection
        | {
            "operation": "PROJECT_NEXT_CHAPTER",
            "output": str(tmp_path / "after-second-edit.json"),
        }
    )
    rewrite_path = tmp_path / "chapter-3-rewritten.json"
    rewrite = current_selection | {
        "operation": "REWRITE_NEXT_CHAPTER_DRAFT",
        "expected_target_revision_hash": stored_third.record_hash,
        "handoff": latest_handoff.to_dict(),
        "output": str(rewrite_path),
    }
    refusals = (
        ({"expected_revision_hash": edited.record_hash}, "CHAPTER_REVISION_CHANGED"),
        ({"handoff": new_handoff.to_dict()}, "NEXT_CHAPTER_INPUT_CHANGED"),
        (
            {"expected_target_revision_hash": "f" * 64},
            "WRITTEN_DRAFT_REVISION_CONFLICT",
        ),
    )
    for changes, code in refusals:
        with pytest.raises(WorkflowError, match=f"^{code}$"):
            reopened.execute(rewrite | changes)
    assert len(writer_inputs) == 2 and not rewrite_path.exists()

    rewritten = reopened.execute(rewrite)
    assert rewritten.version == 2 and rewritten.prose == rewritten_chapter3_prose
    assert rewritten.previous_revision_hash == stored_third.record_hash
    assert rewritten.source_revision_hash == latest_source.record_hash
    assert rewritten.writer_input_hash != stored_third.writer_input_hash
    assert rewrite_path.read_bytes() == rewritten.payload_bytes()
    assert rewrite_path.stat().st_mode & 0o777 == 0o600
    summary = snapshot_summary(rewritten)
    assert summary["artifact_state"] == "DRAFT"
    assert not any(
        summary[flag]
        for flag in (
            "can_commit",
            "can_dispatch",
            "can_issue_permit",
            "accepted",
            "published",
        )
    )

    cold = WorkflowTaskAdapter(
        ChapterWorkflow(WorkflowStore(store.path), next_chapter_writer=writer)
    )
    assert cold.execute(inspect_third).payload_bytes() == rewritten.payload_bytes()
    historical = cold.execute(inspect_third | {"version": 1})
    assert historical.payload_bytes() == stored_third.payload_bytes()

    current_path = tmp_path / "current.json"
    current_path.write_bytes(current.payload)
    compare_paths = (tmp_path / "chapter-3-v1.txt", tmp_path / "chapter-3-v2.txt")
    for revision, destination in zip(
        (historical, rewritten), compare_paths, strict=True
    ):
        assert (
            workflow_cli.main(
                [
                    "--db",
                    str(store.path),
                    "--project",
                    PROJECT,
                    "--branch",
                    BRANCH,
                    "--run-id",
                    RUN,
                    "inspect-written-draft",
                    "--input",
                    str(current_path),
                    "--chapter-id",
                    chapter3.id.local_id,
                    "--version",
                    str(revision.version),
                    "--output",
                    str(destination),
                ]
            )
            == 0
        )
        cli = capsys.readouterr()
        assert not cli.err
        assert json.loads(cli.out) == snapshot_summary(revision)
        assert destination.read_bytes() == revision.prose
        assert destination.stat().st_mode & 0o777 == 0o600

    rewrite_retry = tmp_path / "chapter-3-rewrite-retry.json"
    retrieved = cold.execute(rewrite | {"output": str(rewrite_retry)})
    assert (
        retrieved.payload_bytes()
        == rewrite_retry.read_bytes()
        == rewrite_path.read_bytes()
    )
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_SOURCE_UNCHANGED$"):
        cold.execute(
            rewrite
            | {
                "expected_target_revision_hash": rewritten.record_hash,
                "output": str(tmp_path / "unnecessary-rewrite.json"),
            }
        )
    assert len(writer_inputs) == 3


def test_written_draft_impact_orders_two_rewrites(tmp_path, monkeypatch, capsys):
    from anovel.context.scene import SceneSpan
    from anovel.workflow.interfaces import snapshot_summary

    current, store, root_revision, fact_id, (_, chapter2, chapter3, chapter4) = (
        _written_draft_setup(
            tmp_path,
            monkeypatch,
            "根据第二章的决定处理交付。",
            "承接第三章作出的交付安排。",
            template_version="local-four-chapter-draft-test",
        )
    )
    scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "current_input": current.to_dict(),
    }
    # These two passages exactly match the previously retained Chapter 2 and 3
    # exports. The fourth chapter extends the frozen plan for this local replay.
    old_prose = {
        2: "本地续写测试。交付后，余额仍为30。",
        3: "甲按核过的七十二元回单安排分批交付。",
        4: "甲依照回单，将第一批货送到约定地点。",
    }
    second_choice = "甲决定先亲自清点库存，再安排交付。"
    second_ending = "balance变为90。"
    third_choice = "甲决定暂停剩余交付，等乙复核清单。"
    third_ending = "balance变为82。"
    third_prose = (
        "甲照约亲自清点库存，发现一件破损，先退了八元。\n\n"
        f"{second_ending}\n\n{third_choice}\n\n{third_ending}"
    )
    fourth_prose = "乙照甲的决定复核清单，确认已退八元。第二批暂缓，账上结余八十二元。"
    expected_rewrites = {
        3: (second_choice, second_ending, 90, third_prose),
        4: (third_choice, third_ending, 82, fourth_prose),
    }
    writer_inputs = []
    baseline = True

    def writer(raw):
        request = json.loads(raw)
        writer_inputs.append(request)
        number = request["handoff"]["target_chapter_number"]
        assert request["artifact_state"] == "DRAFT"
        if baseline:
            return old_prose[number].encode()
        choice, ending, balance, output = expected_rewrites[number]
        assert request["previous_scene_ending"]["quote"] == choice
        assert request["handoff"]["ending"]["quote"] == ending
        assert [
            (fact["fact_id"], fact["value"], fact["span"]["quote"])
            for fact in request["observed_draft_facts"]
        ] == [(fact_id.to_dict(), balance, ending)]
        return output.encode()

    task = WorkflowTaskAdapter(ChapterWorkflow(store, next_chapter_writer=writer))

    def selection(source):
        return scope | {
            "source_chapter_id": source.chapter_id.to_dict(),
            "expected_revision_hash": source.record_hash,
        }

    def project(fields, name):
        task_output = tmp_path / name
        handoff = task.execute(
            fields | {"operation": "PROJECT_NEXT_CHAPTER", "output": str(task_output)}
        )
        assert json.loads(task_output.read_bytes()) == handoff.to_dict()
        return handoff.to_dict()

    def write(fields, handoff, name, *, target=None):
        request = fields | {"handoff": handoff, "output": str(tmp_path / name)}
        if target is None:
            return request | {"operation": "WRITE_NEXT_CHAPTER_DRAFT"}
        return request | {
            "operation": "REWRITE_NEXT_CHAPTER_DRAFT",
            "expected_target_revision_hash": target.record_hash,
        }

    def inspect(chapter):
        return scope | {
            "operation": "INSPECT_WRITTEN_DRAFT",
            "chapter_id": chapter.id.to_dict(),
        }

    def impact(source):
        return selection(source) | {"operation": "INSPECT_WRITTEN_DRAFT_IMPACT"}

    root = scope | {"expected_revision_hash": root_revision.record_hash}
    task.execute(write(root, project(root, "chapter-2-handoff.json"), "chapter-2.json"))
    second = task.execute(
        root
        | {
            "operation": "SAVE_NEXT_CHAPTER_DRAFT",
            "draft": json.loads((tmp_path / "chapter-2.json").read_bytes()),
        }
    )
    old_handoff3 = project(selection(second), "chapter-3-old-handoff.json")
    task.execute(write(selection(second), old_handoff3, "chapter-3-original.json"))
    third = task.execute(inspect(chapter3))
    old_handoff4 = project(selection(third), "chapter-4-old-handoff.json")
    task.execute(write(selection(third), old_handoff4, "chapter-4-original.json"))
    fourth = task.execute(inspect(chapter4))
    assert not task.execute(impact(second)).affected_chapters

    baseline = False
    task = WorkflowTaskAdapter(
        ChapterWorkflow(WorkflowStore(store.path), next_chapter_writer=writer)
    )
    revised_second = task.execute(
        inspect(chapter2)
        | {
            "operation": "EDIT_WRITTEN_DRAFT",
            "expected_revision_hash": second.record_hash,
            "text": f"{second_choice}\n\nbalance变为30。\n\n{second_ending}",
            "choice": SceneSpan(0, len(second_choice), second_choice).to_dict(),
        }
    )

    def check_impact(name, rows):
        db_hash = sha256(store.path.read_bytes()).hexdigest()
        report = task.execute(impact(revised_second))
        assert report.source_revision_hash == revised_second.record_hash
        assert [
            (item.chapter_number, item.revision_hash, item.ready_to_rewrite)
            for item in report.affected_chapters
        ] == [
            (previous.chapter_number, previous.record_hash, ready)
            for previous, ready in rows
        ]
        assert [item.source_revision_hash for item in report.affected_chapters] == [
            previous.source_revision_hash for previous, _ in rows
        ]
        view = snapshot_summary(report)
        assert view["artifact_state"] == "DRAFT"
        assert view["state"] == "DRAFT_DOWNSTREAM_IMPACT"
        assert not any(
            view[flag]
            for flag in (
                "can_commit",
                "can_dispatch",
                "can_issue_permit",
                "accepted",
                "published",
            )
        )
        output = tmp_path / name
        output.write_bytes(canonical_bytes(view))
        output.chmod(0o600)
        assert sha256(store.path.read_bytes()).hexdigest() == db_hash
        return view

    first_impact = check_impact(
        "impact-after-chapter-2.json", ((third, True), (fourth, False))
    )
    current_path = tmp_path / "current.json"
    current_path.write_bytes(current.payload)
    cli_scope = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
    ]
    assert (
        workflow_cli.main(
            cli_scope
            + [
                "inspect-written-draft-impact",
                "--input",
                str(current_path),
                "--source-chapter-id",
                chapter2.id.local_id,
                "--expected-revision-hash",
                revised_second.record_hash,
            ]
        )
        == 0
    )
    cli = capsys.readouterr()
    assert not cli.err
    assert json.loads(cli.out) == first_impact

    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(impact(second))
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_SOURCE_CHANGED$"):
        task.execute(impact(third))
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_SOURCE_CHANGED$"):
        task.execute(
            write(selection(third), old_handoff4, "out-of-order.json", target=fourth)
        )
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        task.execute(
            write(
                selection(revised_second),
                old_handoff3,
                "chapter-3-stale.json",
                target=third,
            )
        )
    assert len(writer_inputs) == 3 and not (tmp_path / "out-of-order.json").exists()
    assert not (tmp_path / "chapter-3-stale.json").exists()

    handoff3 = project(selection(revised_second), "chapter-3-new-handoff.json")
    rewritten_third = task.execute(
        write(
            selection(revised_second),
            handoff3,
            "chapter-3-rewritten.json",
            target=third,
        )
    )
    assert rewritten_third.prose.decode() == third_prose
    assert rewritten_third.source_revision_hash == revised_second.record_hash
    check_impact("impact-after-chapter-3.json", ((fourth, True),))
    choice_start = third_prose.index(third_choice)
    revised_third = task.execute(
        inspect(chapter3)
        | {
            "operation": "EDIT_WRITTEN_DRAFT",
            "expected_revision_hash": rewritten_third.record_hash,
            "text": third_prose,
            "choice": SceneSpan(
                choice_start, choice_start + len(third_choice), third_choice
            ).to_dict(),
        }
    )
    assert revised_third.prose == rewritten_third.prose
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        task.execute(
            write(
                selection(revised_third),
                old_handoff4,
                "chapter-4-stale.json",
                target=fourth,
            )
        )
    assert len(writer_inputs) == 4 and not (tmp_path / "chapter-4-stale.json").exists()
    handoff4 = project(selection(revised_third), "chapter-4-new-handoff.json")
    rewritten_fourth = task.execute(
        write(
            selection(revised_third),
            handoff4,
            "chapter-4-rewritten.json",
            target=fourth,
        )
    )
    assert rewritten_fourth.prose.decode() == fourth_prose
    assert rewritten_fourth.source_revision_hash == revised_third.record_hash
    assert [
        request["handoff"]["target_chapter_number"] for request in writer_inputs
    ] == [2, 3, 4, 3, 4]
    inputs_path = tmp_path / "rewrite-writer-inputs.json"
    inputs_path.write_bytes(canonical_bytes(writer_inputs[-2:]))
    inputs_path.chmod(0o600)

    task = WorkflowTaskAdapter(ChapterWorkflow(WorkflowStore(store.path)))
    check_impact("impact-after-chapter-4.json", ())
    assert not task.execute(impact(rewritten_fourth)).affected_chapters
    for chapter, previous, rewritten in (
        (chapter3, third, revised_third),
        (chapter4, fourth, rewritten_fourth),
    ):
        assert task.execute(inspect(chapter)).record_hash == rewritten.record_hash
        for revision, label in ((previous, "before"), (rewritten, "after")):
            path = tmp_path / f"{chapter.id.local_id}-{label}.txt"
            saved = task.execute(
                inspect(chapter) | {"version": revision.version, "output": str(path)}
            )
            assert saved.payload_bytes() == revision.payload_bytes()
            assert path.read_bytes() == revision.prose
            assert path.stat().st_mode & 0o777 == 0o600
            assert snapshot_summary(saved)["artifact_state"] == "DRAFT"


def test_save_observed_revision_refuses_bad_selection_and_stale_extraction(
    tmp_path, monkeypatch
):
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    workflow = ChapterWorkflow(store)
    current = object()
    calls = []
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN, "step_id": "1" * 64}

    def load_observation(frozen, **arguments):
        assert frozen is current and arguments == scope
        calls.append(arguments)
        return SimpleNamespace(record_hash="2" * 64)

    def reject_append(*args, **kwargs):
        pytest.fail("An unbound observation must not append a Draft revision")

    monkeypatch.setattr(workflow, "_q0_observation", load_observation)
    monkeypatch.setattr(store, "append_chapter_revision", reject_append)
    selection = {
        **scope,
        "request_id": "draft-selection",
        "expected_observation_hash": "3" * 64,
        "version": 1,
        "expected_revision_hash": None,
    }
    before = store.path.read_bytes()
    for invalid in (
        {"version": 0},
        {"version": 2},
        {"expected_revision_hash": "5" * 64},
        {"expected_observation_hash": "not-a-digest"},
    ):
        with pytest.raises(WorkflowError, match="^INVALID_CHAPTER_REVISION_SELECTION$"):
            workflow.save_observed_chapter_revision(current, **(selection | invalid))
    assert not calls
    with pytest.raises(WorkflowError, match="^EXTRACTION_SOURCE_CHANGED$"):
        workflow.save_observed_chapter_revision(current, **selection)
    assert calls == [scope]
    assert store.path.read_bytes() == before


def test_bind_revision_annotations_cli_and_task_parse_only_author_input(
    tmp_path, capsys, monkeypatch
):
    from anovel.contracts.models import KnowledgeSnapshot
    from anovel.domain.events import StoryTime
    from anovel.domain.identity import EntityId
    from anovel.quality.q1 import (
        PROFILE,
        ActivityClaim,
        BoundQ1Annotations,
        DeathTiming,
    )
    from anovel.workflow.chapter import RevisionAnnotationBinding
    from anovel.workflow.extractor import ExactSpan
    from anovel.workflow.interfaces import snapshot_summary
    from anovel.workflow.models import WorkflowSnapshot

    case = source_case()
    current = case.frozen
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    contract, context, request = current.request(RUN, LOGICAL)
    saved = WorkflowSnapshot(
        current,
        request.to_bytes(),
        canonical_bytes(contract.to_dict()),
        context.to_bytes(),
        ATTEMPT,
        request.policies[0].id,
    )
    assert store.create(saved)
    current_file = tmp_path / "current.json"
    current_file.write_bytes(current.payload)
    actor = EntityId(PROJECT, "alice")
    claim = ActivityClaim(ExactSpan.from_source(BODY, 0, 3), actor, StoryTime.exact(2))
    death = DeathTiming(actor, StoryTime.exact(5))
    knowledge = KnowledgeSnapshot(
        PROJECT,
        contract.parent_ref,
        "offline-author-input",
        case.fixture.knowledge_bytes,
    )
    source = {
        "claims": [claim.to_dict()],
        "author_knowledge": knowledge.to_dict(),
        "death_times": [death.to_dict()],
    }
    annotations = BoundQ1Annotations.from_dict(
        source
        | {
            "record_type": "bound_q1_annotations",
            "schema_version": "1.0",
            "profile": PROFILE,
            "project": PROJECT,
            "branch": BRANCH,
            "run_id": RUN,
            "step_id": "1" * 64,
            "observation_hash": "2" * 64,
            "assembly_hash": "3" * 64,
            "prose_hash": sha256(BODY).hexdigest(),
            "source_input_hash": saved.input_hash,
            "parent_ref": contract.parent_ref,
            "contract_hash": contract.content_hash,
            "pack_hash": contract.pack_hash,
            "frozen_knowledge_hash": contract.knowledge_hash,
            "author_knowledge_hash": sha256(
                canonical_bytes(knowledge.to_dict())
            ).hexdigest(),
        }
    )
    binding = RevisionAnnotationBinding("4" * 64, 2, "2" * 64, annotations)
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    expected = scope | {
        "expected_revision_hash": binding.revision_hash,
        "claims": (claim,),
        "author_knowledge": knowledge,
        "death_times": (death,),
    }
    calls = []

    def bind(service, frozen, **arguments):
        assert service.gateway is None and frozen == current
        calls.append(arguments)
        return binding

    monkeypatch.setattr(ChapterWorkflow, "bind_revision_annotations", bind)
    task = WorkflowTaskAdapter(ChapterWorkflow(store))
    task_request = {
        "operation": "BIND_REVISION_ANNOTATIONS",
        "current_input": current.to_dict(),
        "author_input": source,
        "expected_revision_hash": binding.revision_hash,
        "output": None,
        **scope,
    }
    before = store.path.read_bytes()
    assert task.execute(task_request) is binding
    assert calls == [expected | {"output": None}]
    assert (
        task.execute(
            task_request | {"author_input": {"claims": [], "author_knowledge": None}}
        )
        is binding
    )
    assert calls[-1] == expected | {
        "claims": (),
        "author_knowledge": None,
        "death_times": (),
        "output": None,
    }
    for invalid in (
        {},
        {"claims": [], "accepted": True},
        {"claims": [], "observation_hash": binding.observation_hash},
        {"claims": [], "death_times": "not-an-array"},
    ):
        with pytest.raises(WorkflowError, match="^INVALID_Q1_AUTHOR_INPUT$"):
            task.execute(task_request | {"author_input": invalid})
    assert len(calls) == 2

    input_path = tmp_path / "author-input.json"
    input_path.write_bytes(canonical_bytes(source))
    output_path = tmp_path / "annotations.json"
    assert (
        workflow_cli.main(
            [
                "--db",
                str(store.path),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                "bind-revision-annotations",
                "--input",
                str(current_file),
                "--author-input",
                str(input_path),
                "--expected-revision-hash",
                binding.revision_hash,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )
    output = capsys.readouterr()
    assert output.err == "" and claim.span.quote not in output.out
    summary = json.loads(output.out)
    assert summary == snapshot_summary(binding)
    assert summary["state"] == "DRAFT_REVISION_ANNOTATIONS_BOUND"
    assert summary["revision_hash"] == binding.revision_hash
    assert summary["observation_hash"] == binding.observation_hash
    assert summary["annotations_hash"] == annotations.record_hash
    assert summary["claim_count"] == 1 and summary["coverage_status"] == "NOT_VERIFIED"
    assert {"annotations", "claims", "author_knowledge", "death_times"}.isdisjoint(
        summary
    )
    assert all(
        summary[flag] is False
        for flag in (
            "can_commit",
            "can_issue_permit",
            "can_dispatch",
            "accepted",
            "published",
        )
    )
    assert calls[-1] == expected | {"output": output_path}
    assert not output_path.exists()
    assert store.path.read_bytes() == before


def test_bind_revision_annotations_rejects_stale_revision_before_export(
    tmp_path, monkeypatch
):
    from anovel.quality.q1 import BoundQ1Annotations

    current = source_case().frozen
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    workflow = ChapterWorkflow(store)
    revision = SimpleNamespace(run_id=RUN, record_hash="2" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("A stale revision must not read the extraction or bind annotations")

    monkeypatch.setattr(workflow, "load_chapter_revision", lambda **kwargs: revision)
    monkeypatch.setattr(workflow, "_q0_observation", forbidden)
    monkeypatch.setattr(BoundQ1Annotations, "freeze", forbidden)
    output = tmp_path / "annotations.json"
    before = store.path.read_bytes()
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        workflow.bind_revision_annotations(
            current,
            project=PROJECT,
            branch=BRANCH,
            run_id=RUN,
            expected_revision_hash="1" * 64,
            claims=(),
            author_knowledge=None,
            death_times=(),
            output=output,
        )
    assert not output.exists() and store.path.read_bytes() == before


@pytest.mark.parametrize(
    ("scenario", "diagnostic"),
    [
        ("current", None),
        ("another-run", "CHAPTER_REVISION_RUN_MISMATCH"),
        ("new-revision", "CHAPTER_REVISION_CHANGED"),
    ],
)
def test_inspect_chapter_revision_rechecks_source_and_latest(
    tmp_path, monkeypatch, scenario, diagnostic
):
    from anovel.domain.identity import EntityId

    current = source_case().frozen
    store = WorkflowStore(tmp_path / "workflow.sqlite")
    workflow = ChapterWorkflow(store)
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    chapter_id = EntityId.from_dict(current.to_dict()["chapter_id"])
    observed = object()
    calls = []

    def require_observation(value):
        assert value is observed
        calls.append("binding")

    revision = SimpleNamespace(
        run_id="another-run" if scenario == "another-run" else RUN,
        step_id="1" * 64,
        record_hash="2" * 64,
        require_observation=require_observation,
    )
    later = SimpleNamespace(record_hash="3" * 64)
    revisions = iter((revision, later if scenario == "new-revision" else revision))

    def latest(**arguments):
        assert arguments == {
            "project": PROJECT,
            "branch": BRANCH,
            "chapter_id": chapter_id,
        }
        calls.append("latest")
        return next(revisions)

    def source(frozen, **arguments):
        assert frozen is current and arguments == scope | {"step_id": revision.step_id}
        calls.append("source")
        return observed

    monkeypatch.setattr(workflow, "load_chapter_revision", latest)
    monkeypatch.setattr(workflow, "_q0_observation", source)
    before = store.path.read_bytes()
    if diagnostic is None:
        assert workflow.inspect_chapter_revision(current, **scope) is revision
    else:
        with pytest.raises(WorkflowError, match=f"^{diagnostic}$"):
            workflow.inspect_chapter_revision(current, **scope)
    assert calls == (
        ["latest"]
        if scenario == "another-run"
        else ["latest", "source", "binding", "latest"]
    )
    assert store.path.read_bytes() == before


def test_actual_cli_recovery_uses_the_original_gateway_receipt_without_dispatch(
    tmp_path, monkeypatch
):
    case, env = source_case(), harness(tmp_path)
    publish = env.store.publish

    def fail_result(before, after):
        if after.result is not None:
            raise OSError("synthetic failure before atomic Draft publication")
        return publish(before, after)

    monkeypatch.setattr(env.store, "publish", fail_result)
    with pytest.raises(WorkflowError):
        start(env, case)
    retained = env.ledger.lookup(RUN, LOGICAL)
    current_input = tmp_path / "current-input.json"
    current_input.write_bytes(canonical_bytes(case.frozen.to_dict()))
    completed = run_cli(
        env,
        "recover",
        "--input",
        current_input,
        "--gateway-ledger",
        env.ledger_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    saved = WorkflowStore(env.store_path).load(
        project=PROJECT, branch=BRANCH, run_id=RUN
    )
    assert saved.state == "DRAFT_SAVED" and saved.prose == BODY
    assert saved.result.to_bytes() == retained.to_bytes()
    assert json.loads(completed.stdout)["record_hash"] == saved.record_hash
    assert env.adapter.calls == 1 and env.ledger.summary(RUN)["attempts"] == 1
    assert BODY.decode() not in completed.stdout


def test_actual_cli_rejects_wrong_scope_output_overwrite_and_generation_command(
    tmp_path,
):
    case, env = source_case(), harness(tmp_path)
    saved = start(env, case)
    wrong_scope = run_cli(env, "inspect", project="another-project")
    assert wrong_scope.returncode != 0 and BODY.decode() not in wrong_scope.stdout
    sentinel = tmp_path / "user-owned.txt"
    sentinel.write_bytes(b"KEEP-USER-BYTES")
    before = sentinel.stat()
    overwrite = run_cli(env, "export", "--output", sentinel)
    assert overwrite.returncode != 0
    assert sentinel.read_bytes() == b"KEEP-USER-BYTES"
    assert (sentinel.stat().st_ino, sentinel.stat().st_mtime_ns) == (
        before.st_ino,
        before.st_mtime_ns,
    )
    unknown = run_cli(env, "start")
    assert unknown.returncode != 0
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )
    assert env.adapter.calls == 1 and env.ledger.summary(RUN)["attempts"] == 1


@pytest.mark.parametrize("corruption", ["checksum", "rehashed_authority"])
def test_actual_sqlite_reads_reject_corruption_without_repair_or_resend(
    tmp_path, corruption
):
    case, env = source_case(), harness(tmp_path)
    saved = start(env, case)
    modified = saved.to_dict()
    modified["accepted"] = True
    raw = canonical_bytes(modified)
    with sqlite3.connect(env.store_path) as connection:
        if corruption == "checksum":
            connection.execute("UPDATE runs SET payload=? WHERE run_id=?", (raw, RUN))
        else:
            connection.execute(
                "UPDATE runs SET payload=?,payload_hash=? WHERE run_id=?",
                (raw, sha256(raw).hexdigest(), RUN),
            )
    workflow, ledger, adapter = reopen(env)
    for operation in (
        lambda: workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN),
        lambda: recover(workflow, case),
    ):
        with pytest.raises(WorkflowError) as failure:
            operation()
        assert BODY.decode() not in str(failure.value)
    with sqlite3.connect(env.store_path) as connection:
        assert (
            connection.execute(
                "SELECT payload FROM runs WHERE run_id=?", (RUN,)
            ).fetchone()[0]
            == raw
        )
    assert env.adapter.calls == 1 and adapter.calls == 0
    assert ledger.summary(RUN)["attempts"] == 1


@pytest.mark.parametrize(
    "alias",
    [
        "-wal",
        "-shm",
        "-journal",
        "-WAL",
        "lock_child",
        "parent_symlink",
        "unicode_lock",
    ],
)
def test_reserved_export_paths_cannot_create_database_or_lock_artifacts(
    tmp_path, alias
):
    case, env = source_case(), harness(tmp_path)
    if alias == "unicode_lock":
        env.store = WorkflowStore(tmp_path / "wórkflow.sqlite")
        env.store_path = env.store.path
        env.workflow = ChapterWorkflow(env.store, env.gateway)
    saved = start(env, case)
    if alias == "unicode_lock":
        parent = Path(unicodedata.normalize("NFD", str(env.store.lock_directory)))
        if not parent.exists():
            parent.mkdir(mode=0o700)
        output = parent / "not-a-run-lock.txt"
        real_output = output
    elif alias == "lock_child":
        output = env.store.lock_directory / "not-a-run-lock.txt"
        real_output = output
    elif alias == "parent_symlink":
        parent = tmp_path / "directory-alias"
        parent.symlink_to(env.store_path.parent, target_is_directory=True)
        output = parent / (env.store_path.name + "-wal")
        real_output = env.store_path.with_name(env.store_path.name + "-wal")
    else:
        output = env.store_path.with_name(env.store_path.name + alias)
        real_output = output
    assert not real_output.exists()
    with pytest.raises(WorkflowError, match="DRAFT_EXPORT_RESERVED_PATH"):
        env.workflow.export_draft(
            project=PROJECT, branch=BRANCH, run_id=RUN, output=output
        )
    assert not real_output.exists()
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == saved.record_hash
    )
    assert env.adapter.calls == 1


def table_names(path):
    with sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True) as connection:
        return tuple(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        )


@pytest.mark.parametrize(
    "candidate_kind",
    ["same", "symlink", "hardlink", "other_workflow", "unrelated_sqlite"],
)
def test_invalid_cli_ledger_is_refused_before_writable_gateway_construction(
    tmp_path, monkeypatch, capsys, candidate_kind
):
    case, env = source_case(), harness(tmp_path)
    start(env, case)
    candidate = env.store_path
    if candidate_kind == "symlink":
        candidate = tmp_path / "ledger-symlink.sqlite"
        candidate.symlink_to(env.store_path)
    elif candidate_kind == "hardlink":
        candidate = tmp_path / "ledger-hardlink.sqlite"
        candidate.hardlink_to(env.store_path)
    elif candidate_kind == "other_workflow":
        candidate = tmp_path / "other-workflow" / "other.sqlite"
        WorkflowStore(candidate)
    elif candidate_kind == "unrelated_sqlite":
        candidate = tmp_path / "unrelated.sqlite"
        with sqlite3.connect(candidate) as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
            connection.execute("INSERT INTO unrelated(value) VALUES('KEEP')")
        candidate.chmod(0o600)
    paths = {env.store_path, candidate.resolve()}
    before = {path: (path.read_bytes(), table_names(path)) for path in paths}
    alias_info = candidate.lstat()
    calls = []

    def forbidden_constructor(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError(
            "An invalid ledger reached the writable Gateway constructor"
        )

    monkeypatch.setattr(workflow_cli, "BudgetLedger", forbidden_constructor)
    current_input = tmp_path / "current-input.json"
    current_input.write_bytes(canonical_bytes(case.frozen.to_dict()))
    code = workflow_cli.main(
        [
            "--db",
            str(env.store_path),
            "--project",
            PROJECT,
            "--branch",
            BRANCH,
            "--run-id",
            RUN,
            "recover",
            "--input",
            str(current_input),
            "--gateway-ledger",
            str(candidate),
        ]
    )
    captured = capsys.readouterr()
    assert code != 0 and json.loads(captured.out)["status"] == "BLOCKED"
    assert calls == [] and BODY.decode() not in captured.out
    assert {path: (path.read_bytes(), table_names(path)) for path in paths} == before
    assert (candidate.lstat().st_ino, candidate.lstat().st_mode) == (
        alias_info.st_ino,
        alias_info.st_mode,
    )
    assert env.adapter.calls == 1


@pytest.mark.parametrize("mismatch", ["request", "policy"])
def test_foreign_gateway_binding_is_rejected_before_its_dispatched_attempt_is_recovered(
    tmp_path,
    mismatch,
):
    case = source_case(
        policies=(
            policy_for(),
            policy_for(
                id="offline-secondary",
                model="offline-model-v2",
                accepted_models=("offline-model-v2",),
            ),
        )
    )
    env = harness(tmp_path, adapter=CountingLocalAdapter(crash=True))
    with pytest.raises(SimulatedProcessExit):
        start(env, case)
    unfinished = env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN)
    foreign = BudgetLedger(tmp_path / "foreign-gateway.sqlite")
    foreign.provision(BudgetLimit(PROJECT, BRANCH, RUN, 100000, 3, FUTURE, 1, 1))
    different = unfinished.request
    selected_policy = case.policies[1]
    if mismatch == "request":
        different = replace(
            unfinished.request,
            instructions="Different frozen request in another ledger",
        )
        selected_policy = case.policies[0]
    foreign.reserve(different, selected_policy, ATTEMPT)
    foreign.mark_dispatch(RUN, ATTEMPT)
    assert foreign.summary(RUN)["inflight_attempts"] == 1
    before = foreign.path.read_bytes()
    adapter = CountingLocalAdapter()
    workflow = ChapterWorkflow(
        WorkflowStore(env.store_path), ModelGateway(foreign, adapter)
    )
    with pytest.raises(WorkflowError):
        recover(workflow, case)
    assert foreign.summary(RUN)["inflight_attempts"] == 1
    assert foreign.summary(RUN)["unknown_attempts"] == 0
    assert foreign.lookup(RUN, LOGICAL) is None and foreign.path.read_bytes() == before
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == unfinished.record_hash
    )
    assert env.ledger.summary(RUN)["inflight_attempts"] == 1
    assert env.adapter.calls == 1 and adapter.calls == 0
