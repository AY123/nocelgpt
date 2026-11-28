"""One durable offline scene child, never a completed chapter or acceptance.

All receipts come from the real Gateway ledger and a finite local adapter.
SQLite/CAS, replay and interruption are exercised without HTTP, credentials,
automatic retry, source prose extraction or Canon writes.
"""

import json
import socket
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from threading import Event

import pytest
from test_v2_017 import BRANCH, PROJECT
from test_v2_020 import (
    ATTEMPT,
    FUTURE,
    LOGICAL,
    RUN,
    CountingLocalAdapter,
    SimulatedProcessExit,
    harness,
    recovery_database_bytes,
    recovery_result_metadata,
    run_cli,
    start,
)
from test_v2_020_scene import PROSE, project, saved_scene, scene_case

import anovel.gateway.ledger as ledger_module
from anovel.canon.identity import canonical_bytes
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import BudgetLimit, ProviderReply, Usage
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.generation import SceneGenerationSnapshot
from anovel.workflow.interfaces import WorkflowTaskAdapter, snapshot_summary
from anovel.workflow.store import WorkflowStore

CHILD_ATTEMPT = "offline-second-scene-attempt"
CHILD_PROSE = "第二场合成契约数据；仅验证持久化与恢复。".encode()


@pytest.fixture(autouse=True)
def no_network_or_provider_construction(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Scene generation tests must remain entirely offline")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)


def ready(
    tmp_path, *, anchor="urban.business.realistic", limit=None, replayed_parent=False
):
    if limit is None and not replayed_parent:
        case, env, source = saved_scene(tmp_path, anchor=anchor)
    else:
        case = scene_case(anchor=anchor)
        env = harness(
            tmp_path,
            adapter=CountingLocalAdapter(output={"text": PROSE.decode()}),
            provision=False,
        )
        env.ledger.provision(
            limit or BudgetLimit(PROJECT, BRANCH, RUN, 100000, 3, FUTURE, 1, 1)
        )
        if replayed_parent:
            request = case.frozen.request(RUN, LOGICAL)[2]
            env.gateway.submit(request, case.policies[0].id, ATTEMPT)
        source = start(env, case)
    projection = project(env, case, source)
    env.adapter.output = {"text": CHILD_PROSE.decode()}
    return case, env, source, projection


def expected_step(source, projection):
    return sha256(
        canonical_bytes(
            {
                "run_id": source.run_id,
                "source_record_hash": source.record_hash,
                "target_scene_id": projection.candidate.target_scene_id.to_dict(),
            }
        )
    ).hexdigest()


def start_child(env, case, projection, *, attempt_id=CHILD_ATTEMPT, policy_id=None):
    return env.workflow.start_scene(
        case.frozen,
        projection,
        attempt_id=attempt_id,
        policy_id=policy_id or case.policies[0].id,
    )


def recover_child(workflow, case, step_id):
    return workflow.recover_scene(
        case.frozen, project=PROJECT, branch=BRANCH, run_id=RUN, step_id=step_id
    )


def inspect_child(workflow, step_id, **changes):
    args = {"project": PROJECT, "branch": BRANCH, "run_id": RUN, "step_id": step_id}
    args.update(changes)
    return workflow.inspect_scene(**args)


def stage_attempt(path, attempt_id=CHILD_ATTEMPT):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT state,result_record,request_record,policy_record FROM attempts WHERE run_id=? AND attempt_id=?",
            (RUN, attempt_id),
        ).fetchone()


def dump_database(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()


def stop_before_dispatch(monkeypatch, case, env, source, projection):
    original = env.store.publish_scene

    def interrupted(before, after, *, expected_parent_hash):
        if after.state == "DISPATCHING":
            raise OSError("synthetic interruption before Gateway admission")
        return original(before, after, expected_parent_hash=expected_parent_hash)

    monkeypatch.setattr(env.store, "publish_scene", interrupted)
    with pytest.raises(WorkflowError):
        start_child(env, case, projection)
    monkeypatch.setattr(env.store, "publish_scene", original)
    return inspect_child(env.workflow, expected_step(source, projection))


def interrupt_after_dispatch(case, env, source, projection):
    env.adapter.crash = True
    with pytest.raises(SimulatedProcessExit):
        start_child(env, case, projection)
    env.adapter.crash = False
    child = inspect_child(env.workflow, expected_step(source, projection))
    assert child.state == "DISPATCHING" and child.result is None
    assert stage_attempt(env.ledger_path)[0] == "DISPATCHED"
    return child


def edit_source(env, case, source, *, prose=None):
    return env.workflow.replace_draft(
        case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        expected_revision=source.revision,
        expected_prose_hash=source.prose_hash,
        prose=prose
        if prose is not None
        else source.prose + "\n显式人工修订尾注。".encode(),
    )


@pytest.mark.parametrize(
    "anchor", ["urban.business.realistic", "fantasy.eastern.progression"]
)
def test_real_second_scene_receipt_and_draft_share_original_run_without_changing_parent(
    tmp_path, anchor
):
    case, env, source, projection = ready(tmp_path, anchor=anchor)
    canon_before = canonical_bytes(case.view.to_dict())
    before = env.ledger.summary(RUN)
    child = start_child(env, case, projection)
    after = env.ledger.summary(RUN)
    assert child.state == "DRAFT_SAVED" and child.prose == CHILD_PROSE
    assert child.step_id == expected_step(source, projection)
    assert child.request.logical_id == "scene-v1-" + child.step_id
    assert child.run_id == source.run_id == child.request.run_id == RUN
    assert child.request.context == projection.context
    assert child.request.context.scene_id == projection.candidate.target_scene_id
    assert child.result.attempt_id == CHILD_ATTEMPT
    assert child.result.request_hash == child.request.content_hash
    assert child.result.policy_hash == case.policies[0].content_hash
    assert not child.accepted and child.source.record_hash == source.record_hash
    assert after["attempts"] == before["attempts"] + 1 == 2
    assert (
        after["spent_microusd"]
        == before["spent_microusd"] + child.result.charge_microusd
    )
    assert after["total_microusd"] == before["total_microusd"]
    assert after["deadline_at"] == before["deadline_at"]
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).payload_bytes()
        == source.payload_bytes()
    )
    assert canonical_bytes(case.view.to_dict()) == canon_before
    assert env.adapter.calls == 2


def test_reopen_and_strict_roundtrip_retain_child_without_resending(tmp_path):
    case, env, _source, projection = ready(tmp_path)
    child = start_child(env, case, projection)
    restored = SceneGenerationSnapshot.from_bytes(child.payload_bytes())
    assert restored.record_hash == child.record_hash
    fresh_adapter = CountingLocalAdapter()
    reopened = ChapterWorkflow(
        WorkflowStore(env.store_path),
        ModelGateway(BudgetLedger(env.ledger_path), fresh_adapter),
    )
    assert (
        inspect_child(reopened, child.step_id).payload_bytes() == child.payload_bytes()
    )
    assert recover_child(reopened, case, child.step_id).record_hash == child.record_hash
    assert fresh_adapter.calls == 0
    assert env.ledger.summary(RUN)["attempts"] == 2


def test_duplicate_start_uses_existing_child_and_zero_new_reservation(tmp_path):
    case, env, _source, projection = ready(tmp_path)
    first = start_child(env, case, projection)
    before = env.ledger.summary(RUN)
    second = start_child(env, case, projection)
    assert second.record_hash == first.record_hash
    assert env.ledger.summary(RUN) == before and env.adapter.calls == 2


def test_existing_step_cannot_be_restarted_under_another_attempt(tmp_path):
    case, env, _source, projection = ready(tmp_path)
    child = start_child(env, case, projection)
    before = env.ledger.summary(RUN)
    with pytest.raises(WorkflowError, match="SCENE_GENERATION_CONFLICT"):
        start_child(env, case, projection, attempt_id="another-attempt")
    assert inspect_child(env.workflow, child.step_id).record_hash == child.record_hash
    assert env.ledger.summary(RUN) == before


def test_replayed_parent_result_matches_real_ledger_receipt_after_normalization(
    tmp_path,
):
    case, env, source, projection = ready(tmp_path, replayed_parent=True)
    assert source.result.replayed
    assert env.ledger.lookup(RUN, LOGICAL).replayed is False
    child = start_child(env, case, projection)
    assert child.state == "DRAFT_SAVED" and env.adapter.calls == 2


def test_new_source_steps_still_exhaust_original_run_attempt_cap(tmp_path):
    case, env, source, projection = ready(tmp_path)
    first = start_child(env, case, projection)
    edited = edit_source(env, case, source)
    next_projection = project(env, case, edited)
    second = start_child(env, case, next_projection, attempt_id="second-source-attempt")
    assert second.state == "DRAFT_SAVED" and second.step_id != first.step_id
    edited_again = edit_source(env, case, edited)
    blocked = start_child(
        env, case, project(env, case, edited_again), attempt_id="third-source-attempt"
    )
    assert blocked.state == "BLOCKED" and blocked.prose is None
    assert env.ledger.summary(RUN)["attempts"] == env.adapter.calls == 3
    assert env.ledger.summary(RUN)["total_microusd"] == 100000
    assert inspect_child(env.workflow, first.step_id).state == "STALE_SOURCE"
    assert inspect_child(env.workflow, second.step_id).state == "STALE_SOURCE"
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == edited_again.record_hash
    )


def test_original_spend_is_not_removed_from_second_scene_budget_admission(tmp_path):
    case = scene_case()
    total = case.policies[0].reserve_microusd + 29
    limit = BudgetLimit(PROJECT, BRANCH, RUN, total, 3, FUTURE, 1, 1)
    case, env, _source, projection = ready(tmp_path, limit=limit)
    before = env.ledger.summary(RUN)
    assert before["spent_microusd"] == 30
    child = start_child(env, case, projection)
    assert child.state == "BLOCKED" and child.prose is None
    assert env.ledger.summary(RUN) == before and env.adapter.calls == 1


def test_original_deadline_cannot_be_extended_for_second_scene(tmp_path, monkeypatch):
    case, env, _source, projection = ready(tmp_path)
    monkeypatch.setattr(
        ledger_module, "_now", lambda _now=None: datetime.fromisoformat(FUTURE)
    )
    child = start_child(env, case, projection)
    assert child.state == "BLOCKED" and child.prose is None
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 1


@pytest.mark.parametrize("fault", ["missing-parent-attempt", "different-parent-result"])
def test_parent_receipt_must_exist_and_match_before_child_dispatch(tmp_path, fault):
    case, env, _source, projection = ready(tmp_path)
    with sqlite3.connect(env.ledger_path) as connection:
        if fault == "missing-parent-attempt":
            connection.execute(
                "DELETE FROM attempts WHERE run_id=? AND attempt_id=?", (RUN, ATTEMPT)
            )
        else:
            result = env.ledger.lookup(RUN, LOGICAL)
            reply = replace(
                result.reply, response_body=b'{"different-synthetic-receipt":true}'
            )
            changed = replace(result, reply=reply)
            connection.execute(
                "UPDATE attempts SET reply_record=?,result_record=? WHERE run_id=? AND attempt_id=?",
                (reply.to_bytes(), changed.to_bytes(), RUN, ATTEMPT),
            )
    before = dump_database(env.ledger_path)
    with pytest.raises(WorkflowError):
        start_child(env, case, projection)
    assert dump_database(env.ledger_path) == before and env.adapter.calls == 1


def test_workflow_database_cannot_be_used_as_gateway_ledger(tmp_path, monkeypatch):
    case, env, source, projection = ready(tmp_path)
    before = dump_database(env.store_path)
    monkeypatch.setattr(env.ledger, "path", env.store_path)
    with pytest.raises(WorkflowError):
        start_child(env, case, projection)
    assert dump_database(env.store_path) == before and env.adapter.calls == 1
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == source.record_hash
    )


@pytest.mark.parametrize("fault", ["path", "inode", "limit"])
def test_frozen_ledger_pin_refuses_replacement_or_limit_change_before_recovery(
    tmp_path, monkeypatch, fault
):
    case, env, source, projection = ready(tmp_path)
    child = stop_before_dispatch(monkeypatch, case, env, source, projection)
    assert child.state == "PREPARED" and stage_attempt(env.ledger_path) is None
    if fault == "limit":
        with sqlite3.connect(env.ledger_path) as connection:
            row = connection.execute(
                "SELECT limit_record FROM budgets WHERE run_id=?", (RUN,)
            ).fetchone()
            changed = replace(
                BudgetLimit.from_dict(json.loads(row[0])), max_attempts=99
            )
            connection.execute(
                "UPDATE budgets SET limit_record=? WHERE run_id=?",
                (changed.to_bytes(), RUN),
            )
    else:
        copied = tmp_path / "copied-gateway.sqlite"
        source_connection = sqlite3.connect(env.ledger_path)
        copied_connection = sqlite3.connect(copied)
        try:
            source_connection.backup(copied_connection)
        finally:
            copied_connection.close()
            source_connection.close()
        if fault == "path":
            monkeypatch.setattr(env.ledger, "path", copied)
        else:
            env.ledger_path.rename(tmp_path / "retained-original-gateway.sqlite")
            copied.rename(env.ledger_path)
    ledger_path = env.ledger.path
    before = dump_database(ledger_path)
    with pytest.raises(WorkflowError):
        recover_child(env.workflow, case, child.step_id)
    assert dump_database(ledger_path) == before and env.adapter.calls == 1
    assert inspect_child(env.workflow, child.step_id).record_hash == child.record_hash


@pytest.mark.parametrize("fault", ["request", "policy"])
def test_foreign_child_attempt_binding_is_rejected_before_marking_unknown(
    tmp_path, fault
):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    with sqlite3.connect(env.ledger_path) as connection:
        if fault == "request":
            changed = replace(
                child.request, instructions="different-synthetic-child-request"
            ).to_bytes()
            column = "request_record"
        else:
            changed = replace(case.policies[0], max_output_tokens=512).to_bytes()
            column = "policy_record"
        connection.execute(
            "UPDATE attempts SET " + column + "=? WHERE run_id=? AND attempt_id=?",
            (changed, RUN, CHILD_ATTEMPT),
        )
    before = stage_attempt(env.ledger_path)
    with pytest.raises(WorkflowError):
        recover_child(env.workflow, case, child.step_id)
    assert stage_attempt(env.ledger_path) == before
    assert before[0] == "DISPATCHED" and env.adapter.calls == 2


def unpublished_child_success(case, env, source, projection, monkeypatch):
    original = env.store.publish_scene
    failed = False

    def interrupted(before, after, *, expected_parent_hash):
        nonlocal failed
        if after.result_bytes is not None and not failed:
            failed = True
            raise OSError("synthetic interruption after durable Gateway success")
        return original(before, after, expected_parent_hash=expected_parent_hash)

    monkeypatch.setattr(env.store, "publish_scene", interrupted)
    with pytest.raises(WorkflowError):
        start_child(env, case, projection)
    monkeypatch.setattr(env.store, "publish_scene", original)
    child = inspect_child(env.workflow, expected_step(source, projection))
    assert child.state == "DISPATCHING" and child.result is None
    assert env.ledger.lookup(RUN, child.request.logical_id).status == "SUCCESS"
    return child


@pytest.mark.parametrize("changed_source", ["contract", "pack", "parent"])
def test_recovery_rejects_changed_chapter_inputs_before_using_retained_receipt(
    tmp_path, monkeypatch, changed_source
):
    case, env, source, projection = ready(tmp_path)
    child = unpublished_child_success(case, env, source, projection, monkeypatch)
    if changed_source == "contract":
        changed = scene_case(target_required=True).frozen
    elif changed_source == "pack":
        changed = scene_case(anchor="fantasy.eastern.progression").frozen
    else:
        parent_ref = "sha256:" + "c" * 64
        root = case.view.root
        view = replace(
            case.view,
            root=replace(root, receipt=replace(root.receipt, commit_id=parent_ref)),
            baseline=replace(case.view.baseline, parent_ref=parent_ref),
        )
        changed = FrozenChapterInput.from_dict(
            case.frozen.to_dict() | {"view": view.to_dict()}
        )

    compiled, _, _ = changed.request(RUN, LOGICAL)
    assert (compiled.scenes != source.contract.scenes) == (changed_source == "contract")
    assert (compiled.pack_hash != source.contract.pack_hash) == (
        changed_source == "pack"
    )
    assert (compiled.parent_ref != source.contract.parent_ref) == (
        changed_source == "parent"
    )

    adapter = CountingLocalAdapter()
    reopened = ChapterWorkflow(
        WorkflowStore(env.store_path),
        ModelGateway(BudgetLedger(env.ledger_path), adapter),
    )
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    ledger_before = dump_database(env.ledger_path)
    with pytest.raises(WorkflowError, match="^WORKFLOW_INPUT_CHANGED$"):
        reopened.recover(changed, **scope)
    with pytest.raises(WorkflowError, match="^WORKFLOW_INPUT_CHANGED$"):
        reopened.recover_scene(changed, **scope, step_id=child.step_id)

    assert reopened.inspect(**scope).record_hash == source.record_hash
    assert inspect_child(reopened, child.step_id).record_hash == child.record_hash
    assert dump_database(env.ledger_path) == ledger_before
    assert reopened.recover(case.frozen, **scope).record_hash == source.record_hash
    recovered = recover_child(reopened, case, child.step_id)
    assert recovered.state == "DRAFT_SAVED" and recovered.prose == CHILD_PROSE
    assert recovered.result.attempt_id == CHILD_ATTEMPT
    assert dump_database(env.ledger_path) == ledger_before
    assert env.adapter.calls == 2 and adapter.calls == 0


def test_ledger_success_survives_child_publication_failure_and_recovers_without_send(
    tmp_path, monkeypatch
):
    case, env, source, projection = ready(tmp_path)
    child = unpublished_child_success(case, env, source, projection, monkeypatch)
    recovered = recover_child(env.workflow, case, child.step_id)
    assert recovered.state == "DRAFT_SAVED" and recovered.prose == CHILD_PROSE
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 2


def test_prepared_child_without_ledger_attempt_stops_without_implicit_submit(
    tmp_path, monkeypatch
):
    case, env, source, projection = ready(tmp_path)
    child = stop_before_dispatch(monkeypatch, case, env, source, projection)
    assert child.state == "PREPARED"
    recovered = recover_child(env.workflow, case, child.step_id)
    assert (
        recovered.state == "BLOCKED"
        and recovered.result is None
        and recovered.prose is None
    )
    assert stage_attempt(env.ledger_path) is None and env.adapter.calls == 1


def test_dispatched_interruption_becomes_unknown_and_retains_run_liability(tmp_path):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    recovered = recover_child(env.workflow, case, child.step_id)
    assert recovered.state == "UNKNOWN" and recovered.result.status == "UNKNOWN"
    assert recovered.prose is None
    summary = env.ledger.summary(RUN)
    assert summary["attempts"] == 2 and summary["unknown_attempts"] == 1
    assert summary["unknown_microusd"] == recovered.result.reserved_microusd
    assert env.adapter.calls == 2


@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("FAILED", "FAILED"),
        ("UNKNOWN", "UNKNOWN"),
        ("PENDING", "BLOCKED"),
        ("MALFORMED", "BLOCKED"),
        ("EMPTY", "BLOCKED"),
    ],
)
def test_non_publishable_second_scene_result_is_durable_but_has_no_draft(
    tmp_path, outcome, expected
):
    case, env, source, projection = ready(tmp_path)
    if outcome in {"FAILED", "UNKNOWN"}:
        env.adapter.outcome = outcome
    elif outcome == "PENDING":
        env.adapter.usage = None
    elif outcome == "MALFORMED":
        env.adapter.output = {"unexpected": "not-the-closed-text-schema"}
    else:
        env.adapter.output = {"text": ""}
    child = start_child(env, case, projection)
    assert child.state == expected and child.result is not None and child.prose is None
    assert inspect_child(env.workflow, child.step_id).record_hash == child.record_hash
    assert (
        recover_child(env.workflow, case, child.step_id).record_hash
        == child.record_hash
    )
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == source.record_hash
    )
    assert not child.accepted and env.adapter.calls == 2


def test_parent_edit_and_revert_keep_old_child_stale_with_original_result(tmp_path):
    case, env, source, projection = ready(tmp_path)
    child = start_child(env, case, projection)
    edited = edit_source(env, case, source)
    stale = inspect_child(env.workflow, child.step_id)
    assert stale.state == "STALE_SOURCE" and stale.prose is None
    assert stale.result.to_bytes() == child.result.to_bytes()
    reverted = edit_source(env, case, edited, prose=source.prose)
    assert (
        reverted.prose_hash == source.prose_hash
        and reverted.record_hash != source.record_hash
    )
    assert recover_child(env.workflow, case, child.step_id).state == "STALE_SOURCE"
    with pytest.raises(WorkflowError):
        start_child(env, case, projection)
    assert inspect_child(env.workflow, child.step_id).prose is None
    assert env.adapter.calls == 2


@pytest.mark.parametrize("late", ["SUCCESS", "UNKNOWN"])
def test_late_original_ledger_evidence_is_retained_after_edit_without_restoring_draft(
    tmp_path, late
):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    edited = edit_source(env, case, source)
    assert inspect_child(env.workflow, child.step_id).state == "STALE_SOURCE"
    if late == "SUCCESS":
        reply = ProviderReply(
            "SUCCESS",
            response_body=canonical_bytes({"synthetic-late": True}),
            provider_request_id="synthetic-late-receipt",
            observed_model=case.policies[0].model,
            usage=Usage(20, 10, 30),
            output_bytes=canonical_bytes({"text": CHILD_PROSE.decode()}),
            http_status=200,
        )
        env.ledger.finish(child.request, case.policies[0], CHILD_ATTEMPT, reply)
    recovered = recover_child(env.workflow, case, child.step_id)
    assert recovered.state == "STALE_SOURCE" and recovered.prose is None
    assert recovered.result is not None and recovered.result.status == late
    assert not recovered.accepted and env.adapter.calls == 2
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == edited.record_hash
    )


def finish_late_scene_receipt(case, env, child):
    return env.ledger.finish(
        child.request,
        case.policies[0],
        CHILD_ATTEMPT,
        ProviderReply(
            "SUCCESS",
            response_body=canonical_bytes({"synthetic-late": True}),
            provider_request_id="synthetic-late-scene-diagnostic",
            observed_model=case.policies[0].model,
            usage=Usage(20, 10, 30),
            output_bytes=canonical_bytes({"text": CHILD_PROSE.decode()}),
            http_status=200,
        ),
    )


def test_recovery_diagnostic_reads_late_attempt_after_scene_source_edit(tmp_path):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    pending = recover_child(env.workflow, case, child.step_id)
    assert pending.state == "UNKNOWN" and pending.result.charge_status == "PENDING"
    edited = edit_source(env, case, source)
    stale = inspect_child(env.workflow, child.step_id)
    assert stale.state == "STALE_SOURCE" and stale.prose is None
    assert stale.result.to_bytes() == pending.result.to_bytes()

    late = finish_late_scene_receipt(case, env, child)
    assert late.status == "SUCCESS" and late.attempt_id == CHILD_ATTEMPT
    task = WorkflowTaskAdapter(ChapterWorkflow(WorkflowStore(env.store_path)))
    input_path = tmp_path / "current-scene-input.json"
    input_path.write_bytes(case.frozen.payload)
    before = recovery_database_bytes(env.store_path, env.ledger_path)
    report = snapshot_summary(
        task.execute(
            {
                "operation": "INSPECT_RECOVERY",
                "project": PROJECT,
                "branch": BRANCH,
                "run_id": RUN,
                "step_id": child.step_id,
                "current_input": case.frozen.to_dict(),
                "gateway_ledger": str(env.ledger_path),
            }
        )
    )
    assert report["state"] == "STALE_SOURCE" and report["source_current"] is False
    assert report["attempt_id"] == CHILD_ATTEMPT
    assert report["record_hash"] == stale.record_hash
    assert report["stored_result"] == recovery_result_metadata(pending.result)
    assert report["ledger_result"] == recovery_result_metadata(late)
    assert all(
        report[key] is False
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
        "recover-scene",
        "--step-id",
        child.step_id,
        "--input",
        input_path,
        "--gateway-ledger",
        env.ledger_path,
        "--diagnose-only",
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert json.loads(cli.stdout) == report
    assert CHILD_PROSE.decode() not in cli.stdout
    blocked = run_cli(
        env,
        "recover-scene",
        "--step-id",
        child.step_id,
        "--input",
        input_path,
        "--gateway-ledger",
        env.ledger_path,
        "--save-late-success",
    )
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert json.loads(blocked.stdout)["code"] == "SCENE_SOURCE_CHANGED"
    assert inspect_child(env.workflow, child.step_id).record_hash == stale.record_hash
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == edited.record_hash
    )
    assert recovery_database_bytes(env.store_path, env.ledger_path) == before
    assert env.ledger.summary(RUN)["attempts"] == env.adapter.calls == 2


def test_save_late_scene_success_reopens_and_preserves_the_same_receipt(tmp_path):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    pending = recover_child(env.workflow, case, child.step_id)
    assert pending.state == "UNKNOWN" and pending.prose is None
    late = finish_late_scene_receipt(case, env, child)
    input_path = tmp_path / "frozen.json"
    input_path.write_bytes(case.frozen.payload)
    args = (
        "recover-scene",
        "--input",
        input_path,
        "--step-id",
        child.step_id,
        "--gateway-ledger",
        env.ledger_path,
        "--save-late-success",
    )
    ledger_before = dump_database(env.ledger_path)
    first = run_cli(env, *args)
    assert first.returncode == 0, first.stdout + first.stderr
    saved = inspect_child(env.workflow, child.step_id)
    assert saved.state == "DRAFT_SAVED" and saved.prose == CHILD_PROSE
    assert saved.result.to_bytes() == late.to_bytes() and not saved.accepted
    assert saved.source.record_hash == source.record_hash
    again = run_cli(env, *args)
    assert again.returncode == 0, again.stdout + again.stderr
    assert json.loads(again.stdout) == json.loads(first.stdout)
    assert inspect_child(env.workflow, child.step_id).record_hash == saved.record_hash
    assert env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN) == source
    assert dump_database(env.ledger_path) == ledger_before
    assert env.ledger.summary(RUN)["attempts"] == env.adapter.calls == 2


def test_child_cas_rejects_stale_writer_without_changing_parent(tmp_path, monkeypatch):
    case, env, source, projection = ready(tmp_path)
    child = stop_before_dispatch(monkeypatch, case, env, source, projection)
    after = replace(child, state="BLOCKED", diagnostic="synthetic-stop")
    published = env.store.publish_scene(
        child, after, expected_parent_hash=source.record_hash
    )
    with pytest.raises(WorkflowError):
        env.store.publish_scene(
            child,
            replace(after, diagnostic="another-writer"),
            expected_parent_hash=source.record_hash,
        )
    assert (
        inspect_child(env.workflow, child.step_id).record_hash == published.record_hash
    )
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == source.record_hash
    )


def test_two_store_instances_cannot_dispatch_same_source_concurrently(
    tmp_path, monkeypatch
):
    case, env, _source, projection = ready(tmp_path)
    entered, release = Event(), Event()
    original = env.adapter.send

    def held(request, policy, attempt_id, permit):
        if attempt_id == CHILD_ATTEMPT:
            entered.set()
            if not release.wait(30):
                raise AssertionError("synthetic local caller was not released")
        return original(request, policy, attempt_id, permit)

    monkeypatch.setattr(env.adapter, "send", held)
    other = ChapterWorkflow(
        WorkflowStore(env.store_path),
        ModelGateway(BudgetLedger(env.ledger_path), env.adapter),
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        active = pool.submit(start_child, env, case, projection)
        try:
            assert entered.wait(30)
            with pytest.raises(WorkflowError, match="WORKFLOW_RUN_LOCK_UNAVAILABLE"):
                other.start_scene(
                    case.frozen,
                    projection,
                    attempt_id=CHILD_ATTEMPT,
                    policy_id=case.policies[0].id,
                )
        finally:
            release.set()
        child = active.result(timeout=30)
    assert child.state == "DRAFT_SAVED" and env.adapter.calls == 2
    assert env.ledger.summary(RUN)["attempts"] == 2


@pytest.mark.parametrize("fault", ["hash", "closed-payload"])
def test_corrupt_child_cannot_be_loaded_or_hidden_by_valid_parent(tmp_path, fault):
    case, env, source, projection = ready(tmp_path)
    child = start_child(env, case, projection)
    with sqlite3.connect(env.store_path) as connection:
        if fault == "hash":
            connection.execute(
                "UPDATE scene_generations SET payload_hash=? WHERE run_id=? AND step_id=?",
                ("0" * 64, RUN, child.step_id),
            )
        else:
            row = json.loads(child.payload_bytes())
            row["unregistered_field"] = True
            raw = canonical_bytes(row)
            connection.execute(
                "UPDATE scene_generations SET payload=?,payload_hash=? WHERE run_id=? AND step_id=?",
                (raw, sha256(raw).hexdigest(), RUN, child.step_id),
            )
    with pytest.raises(WorkflowError):
        inspect_child(env.workflow, child.step_id)
    with pytest.raises(WorkflowError):
        edit_source(env, case, source)
    assert (
        env.workflow.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).record_hash
        == source.record_hash
    )


def test_child_draft_must_equal_its_retained_gateway_result(tmp_path):
    case, env, _source, projection = ready(tmp_path)
    child = start_child(env, case, projection)
    with pytest.raises(WorkflowError):
        replace(child, prose=b"different-unreceipted-child-prose")


def test_unknown_old_scene_liability_is_not_freed_by_editing_into_new_step(tmp_path):
    case, env, source, projection = ready(tmp_path)
    child = interrupt_after_dispatch(case, env, source, projection)
    unknown = recover_child(env.workflow, case, child.step_id)
    edited = edit_source(env, case, source)
    blocked = start_child(
        env, case, project(env, case, edited), attempt_id="new-step-with-old-unknown"
    )
    assert blocked.state == "BLOCKED" and blocked.prose is None
    summary = env.ledger.summary(RUN)
    assert summary["attempts"] == 2 and summary["unknown_attempts"] == 1
    assert summary["unknown_microusd"] == unknown.result.reserved_microusd
    assert env.adapter.calls == 2


def test_task_start_and_real_cli_inspect_recover_share_one_persistent_child(tmp_path):
    case, env, source, projection = ready(tmp_path)
    task = WorkflowTaskAdapter(env.workflow)
    request = {
        "operation": "START_SCENE",
        "current_input": case.frozen.to_dict(),
        "projection": projection.to_dict(),
        "attempt_id": CHILD_ATTEMPT,
        "policy_id": case.policies[0].id,
    }
    child = task.execute(request)
    assert child.state == "DRAFT_SAVED" and child.prose == CHILD_PROSE
    with pytest.raises(WorkflowError):
        task.execute(request | {"run_id": "another-budget-run"})
    input_path = tmp_path / "current-scene-input.json"
    input_path.write_bytes(case.frozen.payload)
    commands = [
        ("inspect-scene", "--step-id", child.step_id),
        (
            "recover-scene",
            "--step-id",
            child.step_id,
            "--input",
            input_path,
            "--gateway-ledger",
            env.ledger_path,
        ),
    ]
    for command in commands:
        result = run_cli(env, *command)
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads(result.stdout)
        assert summary["record_hash"] == child.record_hash
        assert summary["source_record_hash"] == source.record_hash
        assert summary["state"] == "DRAFT_SAVED" and summary["has_draft"]
        assert summary["accepted"] is False
        assert CHILD_PROSE.decode() not in result.stdout
    wrong_scope = run_cli(
        env, "inspect-scene", "--step-id", child.step_id, branch="another-branch"
    )
    assert wrong_scope.returncode == 2
    assert child.record_hash not in wrong_scope.stdout
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 2
