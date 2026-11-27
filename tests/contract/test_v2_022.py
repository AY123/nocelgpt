"""Actual offline Q0 execution and bounded required-evidence checks.

Small byte-artifact controls exercise deterministic rules without regenerating
scenes. Two module seeds retain genuine local Gateway/SQLite provenance. Their
inputs are synthetic engineering data; local Q0 PASS never supplies production
Q1--Q3, a production grant, a Permit, acceptance or publishing authority.
"""

import json
import socket
import sqlite3
import subprocess
import sys
from base64 import b64encode
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_v2_017 import BRANCH, PROJECT
from test_v2_020 import RUN, SimulatedProcessExit
from test_v2_020_assembly import clone_workflow, edit
from test_v2_020_scene_generation import dump_database
from test_v2_021 import ACTUAL, QUIET, forbid_discovery, make_extraction_seed

from anovel.canon.chapter import ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes
from anovel.domain.delta import NoChange
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.quality import q0
from anovel.quality.q0 import (
    ArtifactInput,
    CheckExecution,
    CheckResult,
    Q0Error,
    Q0Finding,
    Q0Run,
    RequiredCheckPlan,
)
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.store import WorkflowStore

KINDS = (
    "ASSEMBLY",
    "OBSERVATION",
    "RAW_PROSE",
    "FROZEN_INPUT",
    "CONTRACT",
    "CONTEXT",
    "PACK_BINDING",
    "PROPOSAL_RAW",
    "INVENTORY_RAW",
)


@pytest.fixture(scope="module", autouse=True)
def no_network_or_provider_construction():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Q0 controls must not use network or Provider")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(socket.socket, "connect", forbidden)
        patch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
        yield


def artifacts():
    # These deliberately small records test only native bytes/presence rules.
    # They are not a current Workflow bundle or evidence of Q1--Q3 execution.
    return tuple(
        ArtifactInput(
            kind,
            payload := canonical_bytes({"synthetic_artifact_kind": kind}),
            sha256(payload).hexdigest(),
        )
        for kind in KINDS
    )


@pytest.fixture(scope="module")
def q0_seeds(tmp_path_factory):
    seeds = {}

    def get(quiet=False, *, checked=False):
        key = (quiet, checked)
        if key not in seeds:
            if checked:
                original = get(quiet)
                retained = clone_workflow(
                    original, tmp_path_factory.mktemp("q0-executed-source")
                )
                result = retained.service.check_q0(
                    retained.case.frozen,
                    project=PROJECT,
                    branch=BRANCH,
                    run_id=RUN,
                    step_id=retained.child.step_id,
                )
                environment = SimpleNamespace(
                    **(
                        vars(original.env)
                        | {
                            "store_path": retained.store_path,
                            "store": retained.store,
                            "workflow": retained.service,
                        }
                    )
                )
                seeds[key] = SimpleNamespace(
                    **(vars(original) | {"env": environment, "q0_run": result})
                )
                evidence = (
                    Path(__file__).resolve().parents[2]
                    / "dist/recovery/v2022-offline-20261118-01"
                )
                reference = {
                    "evidence_scope": "SYNTHETIC_LOCAL_TEST_SEED_NOT_PRODUCTION",
                    "source_database": str(retained.store_path),
                    "gateway_ledger": str(original.env.ledger_path),
                    "current_input": str(evidence / "test-current-input.json"),
                    "current_input_hash": sha256(
                        original.case.frozen.payload
                    ).hexdigest(),
                    "project": PROJECT,
                    "branch": BRANCH,
                    "run_id": RUN,
                    "step_id": original.child.step_id,
                    "assembly_hash": result.assembly_hash,
                    "observation_hash": result.observation_hash,
                    "q0_record_hash": result.record_hash,
                    "executions": [
                        {
                            "check_id": item.check_id,
                            "record_hash": item.record_hash,
                            "input_hash": item.input_hash,
                            "request_id": item.to_dict()["request_id"],
                            "attempt_id": item.to_dict()["attempt_id"],
                        }
                        for item in result.executions
                    ],
                }
                (evidence / "test-retained-reference.json").write_bytes(
                    canonical_bytes(reference)
                )
                return seeds[key]
            seed = make_extraction_seed(
                tmp_path_factory.mktemp("q0-quiet" if quiet else "q0-finite"),
                quiet,
            )
            seed.observation = seed.env.workflow.extract_chapter(
                seed.case.frozen,
                project=PROJECT,
                branch=BRANCH,
                run_id=RUN,
                step_id=seed.child.step_id,
            )
            if not quiet:
                # Recoverable local test evidence for the final task-entry
                # demonstration. Tests operate on backups, never this source.
                evidence = (
                    Path(__file__).resolve().parents[2]
                    / "dist/recovery/v2022-offline-20261118-01"
                )
                evidence.mkdir(parents=True, exist_ok=True)
                current_path = evidence / "test-current-input.json"
                current_path.write_bytes(seed.case.frozen.payload)
                reference = {
                    "evidence_scope": "SYNTHETIC_LOCAL_TEST_SEED_NOT_PRODUCTION",
                    "source_database": str(seed.env.store_path),
                    "gateway_ledger": str(seed.env.ledger_path),
                    "current_input": str(current_path),
                    "current_input_hash": sha256(seed.case.frozen.payload).hexdigest(),
                    "project": PROJECT,
                    "branch": BRANCH,
                    "run_id": RUN,
                    "step_id": seed.child.step_id,
                    "assembly_hash": seed.assembly.record_hash,
                    "observation_hash": seed.observation.record_hash,
                }
                (evidence / "test-seed-reference.json").write_bytes(
                    canonical_bytes(reference)
                )
            seeds[key] = seed
        return seeds[key]

    return get


@pytest.fixture(scope="module")
def actual_run(q0_seeds):
    # This invokes the real finite runner; no hand-authored execution PASS.
    seed = q0_seeds(checked=True)
    return SimpleNamespace(seed=seed, run=seed.q0_run)


@pytest.fixture(scope="module")
def other_retained_source(q0_seeds):
    return q0_seeds(True)


@pytest.fixture
def q0_case(q0_seeds, tmp_path, monkeypatch, request):
    parameter = getattr(request, "param", False)
    seed = q0_seeds(parameter is True, checked=parameter == "saved")
    case = clone_workflow(seed, tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Q0 cannot generate, provision, issue or commit")

    for owner, name in (
        (ModelGateway, "submit"),
        (ModelGateway, "recover"),
        (BudgetLedger, "__init__"),
        (CanonCommitService, "__init__"),
        (CanonCommitService, "commit"),
        (ProtectedPermitIssuer, "__init__"),
        (ProtectedPermitIssuer, "issue"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    forbid_discovery(monkeypatch)
    return case


def scope(case, **changes):
    return {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": case.child.step_id,
    } | changes


def check(case, *, current=None, **changes):
    return case.service.check_q0(current or case.case.frozen, **scope(case, **changes))


def inspect_saved(case, *, service=None, current=None, **changes):
    return (service or case.service).inspect_q0(
        current or case.case.frozen, **scope(case, **changes)
    )


def assert_no_authority(result):
    assert type(result) is Q0Run
    assert result.can_commit is result.can_issue_permit is False
    assert result.can_dispatch is result.accepted is result.published is False
    assert result.aggregate_status == "BLOCKED"


def forbid_native_runner(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Existing Q0 records cannot rerun the native checker")

    monkeypatch.setattr(q0, "execute_local_q0", forbidden)
    monkeypatch.setattr("anovel.workflow.chapter.execute_local_q0", forbidden)


def run_q0_cli(case, *arguments):
    # New Q0 audit decoding has no 60-second product SLO. Its measured cold
    # workload warrants a bounded 180 seconds; the original CLI helper/tests
    # and every product/Provider deadline remain untouched.
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "anovel.workflow",
            "--db",
            str(case.store_path),
            "--project",
            PROJECT,
            "--branch",
            BRANCH,
            "--run-id",
            RUN,
            *map(str, arguments),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def synthetic_record(original, *, verdict=None, state="FINISHED"):
    """Small, explicitly synthetic audit data for pure closure algorithms.

    Parsing does not authenticate these modified records. They never enter the
    Workflow publication path and never represent actual future Q1--Q3 runs.
    """
    row = original.to_dict()
    row["execution_status"] = state
    if state != "FINISHED":
        row.update(
            finished_at=None,
            verdict=None,
            raw_result_base64=None,
            raw_result_hash=None,
            findings=[],
        )
    else:
        result = CheckResult(
            verdict,
            () if verdict == "PASS" else (Q0Finding("SYNTHETIC_" + verdict),),
        )
        raw = result.payload_bytes()
        row.update(
            verdict=result.verdict,
            raw_result_base64=b64encode(raw).decode(),
            raw_result_hash=sha256(raw).hexdigest(),
            findings=[item.to_dict() for item in result.findings],
        )
    return CheckExecution.from_dict(row)


def test_native_artifact_rule_really_executes_and_can_have_no_findings():
    result = q0.check_artifacts(artifacts())
    assert result.verdict == "PASS"
    assert result.findings == ()


@pytest.mark.parametrize("missing", KINDS)
def test_each_required_artifact_is_independently_required(missing):
    inputs = tuple(item for item in artifacts() if item.kind != missing)
    result = q0.check_artifacts(inputs)
    assert result.verdict == "FAIL" and result.findings


@pytest.mark.parametrize("fault", ["wrong-hash", "same-length-change", "duplicate"])
def test_native_bytes_rule_rejects_wrong_hash_or_duplicate_identity(fault):
    inputs = list(artifacts())
    original = inputs[0]
    if fault == "wrong-hash":
        inputs[0] = ArtifactInput(original.kind, original.payload, "0" * 64)
    elif fault == "same-length-change":
        changed = original.payload.replace(b"ASSEMBLY", b"ASSEMBLX")
        assert len(changed) == len(original.payload) and changed != original.payload
        inputs[0] = ArtifactInput(original.kind, changed, original.expected_hash)
    else:
        inputs.append(original)
    result = q0.check_artifacts(tuple(inputs))
    assert result.verdict == "FAIL" and result.findings


def test_unknown_artifact_kind_cannot_expand_the_fixed_registry():
    payload = b"synthetic-extra-kind"
    with pytest.raises(Q0Error):
        q0.check_artifacts(
            (
                *artifacts(),
                ArtifactInput("CALLER_PASS", payload, sha256(payload).hexdigest()),
            )
        )


@pytest.mark.parametrize("raw", [b"x\r\n", b"\xef\xbb\xbfx\n", "e\u0301🙂\n".encode()])
def test_raw_prose_bytes_are_hashed_without_normalization(raw):
    inputs = tuple(
        ArtifactInput("RAW_PROSE", raw, sha256(raw).hexdigest())
        if item.kind == "RAW_PROSE"
        else item
        for item in artifacts()
    )
    assert q0.check_artifacts(inputs).verdict == "PASS"
    changed = tuple(
        ArtifactInput(item.kind, item.payload + b" ", item.expected_hash)
        if item.kind == "RAW_PROSE"
        else item
        for item in inputs
    )
    assert q0.check_artifacts(changed).verdict == "FAIL"


def test_empty_findings_cannot_replace_an_execution_or_a_required_record(actual_run):
    run = actual_run.run
    for record in ({"findings": []}, {"verdict": "PASS", "findings": []}):
        with pytest.raises(Q0Error):
            CheckExecution.from_dict(record)
    missing = q0.assess_required(run.local_plan, ())
    assert missing.status == "BLOCKED"
    assert missing.missing == run.local_plan.requirements
    assert all(item.execution_status == "FINISHED" for item in run.executions)
    assert all(item.result_bytes is not None for item in run.executions)
    assert all(item.findings == () for item in run.executions)


def test_complete_actual_local_evidence_is_positive_only_for_its_local_plan(actual_run):
    run = actual_run.run
    local = q0.assess_required(run.local_plan, run.executions)
    assert local.status == "PASS" and local.missing == local.diagnostics == ()
    production = q0.assess_required(run.required_plan, run.executions)
    assert production.status == "BLOCKED"
    assert production.missing == run.required_plan.requirements
    assert {"Q1_CANON_V1", "Q2_WORLD_RULES_V1", "Q3_CONTRACT_V1"} <= set(
        production.missing
    )
    assert_no_authority(run)


@pytest.mark.parametrize("verdict", ["FAIL", "UNKNOWN", "ERROR"])
def test_synthetic_nonpass_results_block_the_pure_local_closure(actual_run, verdict):
    run = actual_run.run
    synthetic = synthetic_record(run.executions[0], verdict=verdict)
    result = q0.assess_required(run.local_plan, (synthetic, *run.executions[1:]))
    assert result.status == "BLOCKED"
    assert any(item.code == "CHECK_" + verdict for item in result.diagnostics)


@pytest.mark.parametrize("state", ["RUNNING", "INTERRUPTED"])
def test_unfinished_synthetic_attempts_are_not_finished_empty_findings(
    actual_run, state
):
    run = actual_run.run
    synthetic = synthetic_record(run.executions[0], state=state)
    assert synthetic.verdict is None and synthetic.result_bytes is None
    result = q0.assess_required(run.local_plan, (synthetic, *run.executions[1:]))
    assert result.status == "BLOCKED"
    assert any(item.code == "CHECK_NOT_FINISHED" for item in result.diagnostics)


@pytest.mark.parametrize("state", ["NOT_RUN", "SKIP", "NOT_APPLICABLE"])
def test_caller_cannot_invent_a_successful_or_skipped_execution_state(
    actual_run, state
):
    with pytest.raises(Q0Error):
        synthetic_record(actual_run.run.executions[0], state=state)


def test_unauthorized_skip_verdict_cannot_become_a_check_result():
    with pytest.raises(Q0Error):
        CheckResult("SKIP", (Q0Finding("SYNTHETIC_SKIP"),))


def test_conflicting_records_are_not_resolved_by_last_pass_or_order(actual_run):
    run = actual_run.run
    synthetic_failure = synthetic_record(run.executions[0], verdict="FAIL")
    records = (*run.executions, synthetic_failure)
    for ordering in (records, tuple(reversed(records))):
        result = q0.assess_required(run.local_plan, ordering)
        assert result.status == "BLOCKED"
        assert any(
            item.code == "CONFLICTING_CHECK_EXECUTIONS" for item in result.diagnostics
        )
        assert any(item.code == "CHECK_FAIL" for item in result.diagnostics)


def test_wrong_input_hash_is_missing_evidence_not_a_reusable_old_pass(actual_run):
    run = actual_run.run
    plan = q0.local_required_plan("0" * 64)
    result = q0.assess_required(plan, run.executions)
    assert result.status == "BLOCKED" and result.missing == plan.requirements
    assert any(item.code == "CHECK_INPUT_CHANGED" for item in result.diagnostics)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority", "PRODUCTION_OWNER"),
        ("profile", "PRODUCTION_REQUIRED"),
        ("registry_hash", "0" * 64),
        ("check_version", "2.0"),
        ("method_id", "model-confidence-1.0"),
        ("raw_result_hash", "0" * 64),
        ("adjudication", {"actor": "Owner", "PASS": True}),
    ],
)
def test_fake_or_changed_execution_provenance_is_not_trusted(actual_run, field, value):
    row = actual_run.run.executions[0].to_dict()
    row[field] = value
    with pytest.raises(Q0Error):
        CheckExecution.from_dict(row)


def test_required_plan_cannot_be_reduced_or_given_caller_authority(actual_run):
    for original in (actual_run.run.local_plan, actual_run.run.required_plan):
        for field, value in (
            ("requirements", []),
            ("authority", "Owner"),
            ("registry_hash", "0" * 64),
        ):
            row = original.to_dict()
            row[field] = value
            with pytest.raises(Q0Error):
                RequiredCheckPlan.from_dict(row)


def test_retained_run_cannot_self_assign_a_gate_pass_or_commit_rights(actual_run):
    original = actual_run.run
    for field, value in (
        ("aggregate_status", "PASS"),
        ("can_commit", True),
        ("can_issue_permit", True),
        ("can_dispatch", True),
        ("accepted", True),
        ("published", True),
        ("semantic_status", "PASS"),
        ("observation_hash", "0" * 64),
    ):
        row = original.to_dict()
        row[field] = value
        with pytest.raises(Q0Error):
            Q0Run.from_dict(row)


def test_actual_q0_execution_is_durable_but_does_not_complete_the_gate(q0_case):
    case = q0_case
    before_ledger = dump_database(case.ledger_path)
    before_root = case.store.load(project=PROJECT, branch=BRANCH, run_id=RUN)
    result = check(case)
    assert_no_authority(result)
    assert result.q0_status == "PASS"
    assert result.observation_hash == case.seed.observation.record_hash
    assert result.assembly_hash == case.seed.assembly.record_hash
    assert result.observation.payload_bytes() == case.seed.observation.payload_bytes()
    assert result.executions
    assert all(item.verdict == "PASS" for item in result.executions)
    assert all(item.findings == () for item in result.executions)
    assert case.store.load(project=PROJECT, branch=BRANCH, run_id=RUN) == before_root
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


@pytest.mark.parametrize("q0_case", [True], indirect=True)
def test_zero_delta_observation_is_checked_without_inventing_a_candidate(
    q0_case, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Quiet Q0 must not pad Delta or create a Candidate")

    monkeypatch.setattr(NoChange, "__init__", forbidden)
    monkeypatch.setattr(ChapterCandidate, "__init__", forbidden)
    result = check(q0_case)
    assert_no_authority(result)
    assert result.q0_status == "PASS"
    assert result.observation.proposal_delta is None
    assert result.observation.operation_count == 0


def test_missing_saved_observation_does_not_start_extraction(q0_case):
    case = q0_case
    with sqlite3.connect(case.store_path) as connection:
        connection.execute("DELETE FROM extraction_observations")
    before = dump_database(case.store_path)
    with pytest.raises(WorkflowError):
        check(case)
    assert dump_database(case.store_path) == before


def test_json_roundtrip_has_no_native_publication_capability(q0_case):
    case = q0_case
    native = q0.execute_local_q0(case.seed.observation)
    restored = Q0Run.from_bytes(native.payload_bytes())
    assert restored.payload_bytes() == native.payload_bytes()
    before = dump_database(case.store_path)
    with pytest.raises(WorkflowError, match="Q0_NATIVE_EXECUTION_REQUIRED"):
        case.store.create_q0(restored)
    assert dump_database(case.store_path) == before
    assert case.store.create_q0(native)
    assert inspect_saved(case).record_hash == native.record_hash


@pytest.mark.parametrize("q0_case", ["saved"], indirect=True)
def test_reopen_and_duplicate_check_read_the_original_execution_without_rerun(
    q0_case, monkeypatch
):
    case = q0_case
    original = case.seed.q0_run
    forbid_native_runner(monkeypatch)
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    inspected = inspect_saved(case, service=reopened)
    duplicate = reopened.check_q0(case.case.frozen, **scope(case))
    assert (
        inspected.payload_bytes()
        == duplicate.payload_bytes()
        == original.payload_bytes()
    )


def test_after_commit_interruption_recovers_original_execution(q0_case, monkeypatch):
    case = q0_case
    create = case.store.create_q0
    recorded = []

    def after_commit(run):
        created = create(run)
        recorded.append(run)
        if created:
            raise SimulatedProcessExit("synthetic exit after Q0 commit")
        return created

    monkeypatch.setattr(case.store, "create_q0", after_commit)
    with pytest.raises(SimulatedProcessExit):
        check(case)
    assert len(recorded) == 1
    forbid_native_runner(monkeypatch)
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    assert (
        inspect_saved(case, service=reopened).payload_bytes()
        == recorded[0].payload_bytes()
    )


def test_before_commit_interruption_is_not_fabricated_by_inspect(q0_case, monkeypatch):
    case = q0_case
    create = case.store.create_q0

    def before_commit(_run):
        raise SimulatedProcessExit("synthetic exit before Q0 commit")

    monkeypatch.setattr(case.store, "create_q0", before_commit)
    with pytest.raises(SimulatedProcessExit):
        check(case)
    with pytest.raises(WorkflowError, match="Q0_EXECUTION_UNAVAILABLE"):
        inspect_saved(case)
    monkeypatch.setattr(case.store, "create_q0", create)
    assert check(case).q0_status == "PASS"


@pytest.mark.parametrize(
    "column", ["payload", "project", "observation_hash", "run_id", "step_id"]
)
@pytest.mark.parametrize("q0_case", ["saved"], indirect=True)
def test_corrupt_q0_record_is_not_missing_and_never_triggers_a_rerun(
    q0_case, monkeypatch, column
):
    case = q0_case
    assert case.seed.q0_run.observation_hash == case.seed.observation.record_hash
    value = (
        b"{}"
        if column == "payload"
        else "0" * 64
        if column in {"observation_hash", "step_id"}
        else "other-project"
    )
    with sqlite3.connect(case.store_path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(f"UPDATE q0_executions SET {column}=?", (value,))
    forbid_native_runner(monkeypatch)
    before = dump_database(case.store_path)
    for operation in (check, inspect_saved):
        with pytest.raises(WorkflowError):
            operation(case)
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize("q0_case", ["saved"], indirect=True)
def test_existing_fk_target_does_not_let_a_corrupt_q0_key_appear_missing(
    q0_case, other_retained_source, monkeypatch
):
    case, other = q0_case, other_retained_source
    assert case.seed.q0_run.observation_hash == case.seed.observation.record_hash
    # Transparent negative SQL fault: retain genuine bytes from another local
    # seed solely as an existing FK target. This does not claim it was appended
    # through this run's normal application history or authenticate its ledger.
    child_raw = other.child.payload_bytes()
    observation_raw = other.observation.payload_bytes()
    with sqlite3.connect(case.store_path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            "INSERT INTO scene_generations VALUES(?,?,?,?,?,?)",
            (
                RUN,
                other.child.step_id,
                PROJECT,
                BRANCH,
                child_raw,
                sha256(child_raw).hexdigest(),
            ),
        )
        connection.execute(
            "INSERT INTO extraction_observations VALUES(?,?,?,?,?,?,?)",
            (
                RUN,
                other.child.step_id,
                other.assembly.record_hash,
                PROJECT,
                BRANCH,
                observation_raw,
                sha256(observation_raw).hexdigest(),
            ),
        )
        connection.execute(
            "UPDATE q0_executions SET step_id=?,assembly_hash=?",
            (other.child.step_id, other.assembly.record_hash),
        )
        assert (
            connection.execute("PRAGMA foreign_key_check(q0_executions)").fetchall()
            == []
        )
    forbid_native_runner(monkeypatch)
    before = dump_database(case.store_path)
    for operation in (check, inspect_saved):
        with pytest.raises(WorkflowError, match="CORRUPT_Q0_EXECUTION"):
            operation(case)
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize(
    "change", [{"project": "other"}, {"branch": "other"}, {"run_id": "other"}]
)
def test_wrong_scope_does_not_return_or_create_q0_execution(q0_case, change):
    before = dump_database(q0_case.store_path)
    with pytest.raises(WorkflowError):
        check(q0_case, **change)
    assert dump_database(q0_case.store_path) == before


@pytest.mark.parametrize("q0_case", ["saved"], indirect=True)
def test_changed_input_or_source_invalidates_old_q0_without_erasing_history(q0_case):
    case = q0_case
    saved = case.seed.q0_run
    row = case.case.frozen.to_dict()
    row["instructions"] += " immutable-input-change"
    current = FrozenChapterInput.from_dict(row)
    with pytest.raises(WorkflowError):
        inspect_saved(case, current=current)
    edit(case, case.source, (QUIET + QUIET).encode())
    for operation in (check, inspect_saved):
        with pytest.raises(WorkflowError):
            operation(case)
    with sqlite3.connect(case.store_path) as connection:
        retained = connection.execute("SELECT payload FROM q0_executions").fetchone()[0]
    assert bytes(retained) == saved.payload_bytes()


@pytest.mark.parametrize("q0_case", ["saved"], indirect=True)
def test_task_and_actual_cli_use_same_q0_service_and_reject_caller_authority(
    q0_case, tmp_path
):
    case = q0_case
    task = WorkflowTaskAdapter(case.service)
    request = {
        "operation": "CHECK_Q0",
        "current_input": case.case.frozen.to_dict(),
        **scope(case),
    }
    result = task.execute(request)
    assert_no_authority(result)
    assert (
        task.execute(request | {"operation": "INSPECT_Q0"}).record_hash
        == result.record_hash
    )
    for field, value in (
        ("PASS", True),
        ("required", []),
        ("executions", []),
        ("actor", "Owner"),
        ("grant", "fake"),
    ):
        with pytest.raises(WorkflowError):
            task.execute(request | {field: value})
    input_path = tmp_path / "current.json"
    input_path.write_bytes(case.case.frozen.payload)
    for command in ("check-q0", "inspect-q0"):
        completed = run_q0_cli(
            case, command, "--input", input_path, "--step-id", case.child.step_id
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        summary = json.loads(completed.stdout)
        assert summary["record_hash"] == result.record_hash
        assert summary["q0_status"] == "PASS"
        assert summary["aggregate_status"] == "BLOCKED"
        assert (
            summary["evidence_scope"] == "LOCAL_DETERMINISTIC_Q0_NOT_PRODUCTION_QUALITY"
        )
        assert (
            summary["source_correspondence_status"]
            == case.seed.observation.correspondence_status
        )
        assert summary["can_commit"] is summary["can_issue_permit"] is False
        assert QUIET not in completed.stdout and ACTUAL not in completed.stdout
    assert case.seed.env.adapter.calls == 2
