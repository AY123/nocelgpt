"""Read-only current run observations; never quality checks or commit authority.

Successful paths use real local Gateway receipts. Historical unpublished cuts
and explicitly labelled typed faults exercise stopped states only. A normal
module seed and one existing tail seed avoid repeating generation per control.
"""

import json
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_v2_017 import BRANCH, PROJECT
from test_v2_020 import ATTEMPT, LOGICAL, RUN, harness, run_cli, source_case, start
from test_v2_020_assembly import (
    FIRST,
    SECOND,
    clone_workflow,
    edit,
    make_seed,
    store_child,
)
from test_v2_020_scene import scene_case
from test_v2_020_scene_generation import dump_database
from test_v2_021 import extract, forbid_discovery, make_extraction_seed
from test_v2_022 import check as check_q0
from test_v2_022 import forbid_native_runner, run_q0_cli

from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.models import ProviderReply
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.quality import q0
from anovel.quality.q1 import BoundQ1Annotations, ReaderRevealClaim
from anovel.quality.q2 import METHOD_POLICY_HASH as Q2_METHOD_POLICY_HASH
from anovel.quality.q3 import METHOD_POLICY_HASH as Q3_METHOD_POLICY_HASH
from anovel.workflow import extractor
from anovel.workflow import store as workflow_store
from anovel.workflow.__main__ import _require_existing_run, main
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.extractor import ExactSpan
from anovel.workflow.gateway_binding import existing_gateway_ledger
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.models import DraftRevision, WorkflowSnapshot
from anovel.workflow.run import RunAssessment
from anovel.workflow.store import WorkflowStore

STAGES = (
    "FROZEN_INPUTS",
    "SOURCE_DRAFT",
    "SCENE_BINDING",
    "SCENE_DRAFT",
    "CHAPTER_ASSEMBLY",
    "WHOLE_CHAPTER_EXTRACTION",
    "Q0_Q3",
    "PRODUCTION_PERMIT",
    "CANON_ACCEPTANCE",
)
FUTURE = (
    ("NOT_IMPLEMENTED", "DELEGATED_EXTRACTION_NOT_IMPLEMENTED"),
    ("NOT_IMPLEMENTED", "DELEGATED_Q0_Q3_NOT_IMPLEMENTED"),
    ("NOT_AUTHORIZED", "PRODUCTION_PERMIT_NOT_AUTHORIZED"),
    ("NOT_REACHED", "CANON_ACCEPTANCE_NOT_REACHED"),
)
QUALITY_CHECKS = ("Q0", "Q1", "Q2", "Q3")
EVIDENCE_SCOPES = {
    "1.0": "LOCAL_ARTIFACT_OBSERVATION_NOT_Q0_Q3",
    "1.1": "LOCAL_ARTIFACT_OBSERVATION_NOT_Q0_Q3",
    "1.2": "LOCAL_ARTIFACT_AND_Q0_OBSERVATION_NOT_PRODUCTION_QUALITY",
    "1.3": "LOCAL_ARTIFACT_AND_QUALITY_OBSERVATIONS_NOT_PRODUCTION_QUALITY",
}


@pytest.fixture(scope="module", autouse=True)
def no_network_or_provider_construction():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Run assessment controls must remain offline")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(socket.socket, "connect", forbidden)
        patch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
        yield


@pytest.fixture(scope="module")
def seed_factory(tmp_path_factory):
    seeds = {}

    def get(kind):
        if kind not in seeds:
            recorded = {}
            original = WorkflowStore.publish

            def recording(store, before, after):
                if before.state == "DISPATCHING" and after.result_bytes is not None:
                    recorded["root_unpublished"] = before
                return original(store, before, after)

            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(WorkflowStore, "publish", recording)
                path = tmp_path_factory.mktemp("run-assessment-" + kind)
                seed = (
                    make_extraction_seed(path, False)
                    if kind == "finite-extraction"
                    else make_seed(path, kind)
                )
            seed.root_unpublished = recorded["root_unpublished"]
            seeds[kind] = seed
        return seeds[kind]

    return get


@pytest.fixture
def run_case(seed_factory, tmp_path, monkeypatch, request):
    seed = seed_factory(getattr(request, "param", "normal"))
    case = clone_workflow(seed, tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "Assessment cannot dispatch, recover, issue, commit or initialize budgets"
        )

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
    return case


def assess(case, *, current=None, step_id=None, **changes):
    return case.service.assess_run(
        current or case.case.frozen,
        **(
            {
                "project": PROJECT,
                "branch": BRANCH,
                "run_id": RUN,
                "step_id": step_id,
            }
            | changes
        ),
    )


def assert_observation_only(report):
    assert report.observation_only
    assert report.evidence_scope == EVIDENCE_SCOPES[report.schema_version]
    for name in (
        "can_commit",
        "can_issue_permit",
        "can_dispatch",
        "accepted",
        "published",
    ):
        assert getattr(report, name) is False
    assert tuple(row.stage for row in report.stages) == STAGES
    start = {"1.0": 5, "1.1": 6, "1.2": 7, "1.3": 7}[report.schema_version]
    assert (
        tuple((row.state, row.reason) for row in report.stages[start:])
        == FUTURE[start - 5 :]
    )
    assert all(not row.refs for row in report.stages[start:])


def quality_rows(report):
    rows = report.to_dict()["quality_observations"]
    assert tuple(row["check"] for row in rows) == QUALITY_CHECKS
    assert all(set(row) == {"check", "state", "refs"} for row in rows)
    return {row["check"]: row for row in rows}


def assert_unreached_quality(report):
    for row in quality_rows(report).values():
        assert row["state"] == "NOT_REACHED" and not row["refs"]


def assert_stop(report, stage, state, reason):
    assert_observation_only(report)
    assert report.schema_version == "1.3"
    assert not report.draft_ready and report.handoff == "STOPPED"
    assert (report.stop_stage, report.stop_code) == (stage, reason)
    index = STAGES.index(stage)
    assert (report.stages[index].state, report.stages[index].reason) == (state, reason)
    assert all(row.state == "CURRENT" for row in report.stages[:index])
    assert all(
        (row.state, row.reason, row.refs)
        == ("NOT_REACHED", "PREREQUISITE_NOT_CURRENT", ())
        for row in report.stages[index + 1 : 7]
    )
    assert_unreached_quality(report)


def store_root(case, snapshot):
    raw = snapshot.payload_bytes()
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "UPDATE runs SET payload=?,payload_hash=? WHERE run_id=?",
            (raw, sha256(raw).hexdigest(), RUN),
        )


def insert_child(case, snapshot):
    raw = snapshot.payload_bytes()
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "INSERT INTO scene_generations VALUES(?,?,?,?,?,?)",
            (RUN, snapshot.step_id, PROJECT, BRANCH, raw, sha256(raw).hexdigest()),
        )


def test_observation_decode_reuses_only_exact_bytes_within_bounded_scope():
    failed_reads = []

    class Decoder:
        @classmethod
        def decode(cls, raw):
            if raw == b"invalid":
                failed_reads.append(raw)
                raise ValueError("invalid payload")
            return object()

    class OtherDecoder(Decoder):
        pass

    raw = b"original"
    copied_raw = memoryview(raw).tobytes()
    assert raw == copied_raw and raw is not copied_raw
    decode = workflow_store._decode_retained_payload
    with WorkflowStore.reuse_observation_decodes():
        original = decode(raw, Decoder.decode)
        assert decode(copied_raw, Decoder.decode) is original
        assert decode(b"originaL", Decoder.decode) is not original
        assert decode(raw, OtherDecoder.decode) is not original
        for _ in range(2):
            with pytest.raises(ValueError, match="invalid payload"):
                decode(b"invalid", Decoder.decode)
        assert failed_reads == [b"invalid", b"invalid"]

        for index in range(workflow_store._OBSERVATION_DECODE_LIMIT):
            decode(str(index).encode("ascii"), Decoder.decode)
        evicted = decode(raw, Decoder.decode)
        assert evicted is not original

        oversized = b"x" * (workflow_store._OBSERVATION_DECODE_MAX_PAYLOAD + 1)
        assert decode(oversized, Decoder.decode) is not decode(
            oversized, Decoder.decode
        )

    assert decode(raw, Decoder.decode) is not evicted
    assert decode(raw, Decoder.decode) is not decode(raw, Decoder.decode)
    with WorkflowStore.reuse_observation_decodes():
        assert decode(raw, Decoder.decode) is not evicted


def test_complete_real_graph_is_current_but_stops_before_unimplemented_quality_and_authority(
    run_case,
):
    case = run_case
    before_store, before_ledger = (
        dump_database(case.store_path),
        dump_database(case.ledger_path),
    )
    report = assess(case, step_id=case.child.step_id)
    assert_observation_only(report)
    assert all(row.state == row.reason == "CURRENT" for row in report.stages[:5])
    assert report.draft_ready and report.handoff == "LOCAL_DRAFT_HANDOFF"
    assert report.stop_stage == "WHOLE_CHAPTER_EXTRACTION"
    assert report.schema_version == "1.3"
    assert report.stop_code == "EXTRACTION_OBSERVATION_UNAVAILABLE"
    assert report.first_blocker == report.stages[5]
    assert report.first_blocker.state == "MISSING" and not report.first_blocker.refs
    assert report.stages[6].state == "NOT_REACHED" and not report.stages[6].refs
    assert_unreached_quality(report)
    assert report.input_hash == case.case.frozen.content_hash
    assert report.source_record_hash == case.source.record_hash
    assert dict(report.stages[3].refs)["child_record_hash"] == case.child.record_hash
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


def test_omitted_step_derives_only_the_current_source_slot(run_case):
    case = run_case
    implicit = assess(case)
    explicit = assess(case, step_id=case.child.step_id)
    assert implicit.step_id == case.child.step_id
    assert implicit.payload_bytes() == explicit.payload_bytes()


def test_deterministic_reopen_roundtrip_and_strict_report_claims_cannot_grant_authority(
    run_case,
):
    case = run_case
    report = assess(case)
    restored = RunAssessment.from_bytes(report.payload_bytes())
    assert restored.record_hash == restored.content_hash == report.record_hash
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    observed = reopened.assess_run(
        case.case.frozen, project=PROJECT, branch=BRANCH, run_id=RUN
    )
    assert observed.payload_bytes() == report.payload_bytes()
    for fault in (
        "can_commit",
        "can_dispatch",
        "can_issue_permit",
        "accepted",
        "future-pass",
        "missing-stage",
        "missing-current-ref",
    ):
        row = report.to_dict()
        if fault == "future-pass":
            row["stages"][6]["state"] = "CURRENT"
            row["stages"][6]["reason"] = "CURRENT"
        elif fault == "missing-stage":
            row["stages"].pop()
        elif fault == "missing-current-ref":
            row["stages"][3]["refs"].pop("child_result_hash")
        else:
            row[fault] = True
        with pytest.raises(WorkflowError, match="INVALID_RUN_ASSESSMENT"):
            RunAssessment.from_bytes(canonical_bytes(row))


@pytest.mark.parametrize("version", ["1.0", "1.1", "1.2"])
def test_historical_run_assessment_keeps_exact_canonical_bytes(run_case, version):
    report = assess(run_case)
    historical = legacy_report(report, version)
    if version != "1.2":
        state, reason = FUTURE[1]
        historical["stages"][6] = {
            "stage": "Q0_Q3",
            "state": state,
            "reason": reason,
            "refs": {},
        }
    if version == "1.0":
        state, reason = FUTURE[0]
        historical["stages"][5] = {
            "stage": "WHOLE_CHAPTER_EXTRACTION",
            "state": state,
            "reason": reason,
            "refs": {},
        }
        historical["stop_code"] = reason
    raw = canonical_bytes(historical)
    restored = RunAssessment.from_bytes(raw)
    assert_observation_only(restored)
    assert restored.schema_version == version and restored.payload_bytes() == raw
    assert restored.record_hash == sha256(raw).hexdigest()
    for record in (
        {**historical, "schema_version": "1.3"},
        {**report.to_dict(), "schema_version": version},
        {**historical, "evidence_scope": report.evidence_scope},
    ):
        with pytest.raises(WorkflowError, match="INVALID_RUN_ASSESSMENT"):
            RunAssessment.from_dict(record)


def legacy_report(report, version):
    record = report.to_dict()
    record.pop("quality_observations")
    record.pop("q1_annotations_hash")
    record["schema_version"] = version
    record["evidence_scope"] = EVIDENCE_SCOPES[version]
    return record


def assert_historical_q0_roundtrip(report, observation, retained):
    historical = legacy_report(report, "1.2")
    historical["stop_code"] = "Q1_Q3_EVIDENCE_NOT_INSPECTED"
    historical["stages"][6] = {
        "stage": "Q0_Q3",
        "state": "BLOCKED",
        "reason": historical["stop_code"],
        "refs": {
            "assembly_hash": observation.assembly_hash,
            "assembly_prose_hash": observation.prose_hash,
            "extraction_observation_hash": observation.record_hash,
            "q0_input_hash": retained.input_hash,
            "q0_run_hash": retained.record_hash,
        },
    }
    raw = canonical_bytes(historical)
    restored = RunAssessment.from_bytes(raw)
    assert_observation_only(restored)
    assert restored.schema_version == "1.2" and restored.payload_bytes() == raw


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
def test_historical_current_extraction_still_stops_at_original_q0_q3_stage(run_case):
    extract(run_case)
    historical = legacy_report(assess(run_case), "1.1")
    state, reason = FUTURE[1]
    historical["stages"][6] = {
        "stage": "Q0_Q3",
        "state": state,
        "reason": reason,
        "refs": {},
    }
    historical["stop_code"] = reason
    raw = canonical_bytes(historical)
    restored = RunAssessment.from_bytes(raw)
    assert_observation_only(restored)
    assert restored.schema_version == "1.1" and restored.payload_bytes() == raw
    assert restored.stages[5].state == "CURRENT" and restored.stages[5].refs
    assert restored.stop_stage == "Q0_Q3"


@pytest.mark.parametrize(
    ("run_case", "correspondence"),
    [
        ("finite-extraction", "PASS"),
        ("finite-extraction", "FAIL"),
        ("normal", "UNKNOWN"),
        ("finite-extraction", "ERROR"),
    ],
    indirect=["run_case"],
)
def test_observe_persisted_extraction_with_exact_current_assembly(
    run_case, correspondence, tmp_path, monkeypatch
):
    case = run_case
    proposal = extractor.proposal_backend

    def omit_actual_segment(prose, catalog):
        document = json.loads(proposal(prose, catalog))
        document["segments"] = [
            segment for segment in document["segments"] if segment["kind"] != "ACTUAL"
        ]
        return canonical_bytes(document)

    with monkeypatch.context() as setup:
        if correspondence == "FAIL":
            setup.setattr(extractor, "proposal_backend", omit_actual_segment)
        elif correspondence == "ERROR":
            setup.setattr(extractor, "proposal_backend", lambda _prose, _catalog: b"{}")
        saved = extract(case)
    assert saved.correspondence_status == correspondence
    assert saved.semantic_status == "UNKNOWN"
    forbid_discovery(monkeypatch)

    def unexpected_write(*_args, **_kwargs):
        pytest.fail(
            "Run assessment cannot persist extraction or execute a quality check"
        )

    monkeypatch.setattr(case.store, "create_extraction", unexpected_write)
    monkeypatch.setattr(case.service, "check_q0", unexpected_write)
    before_store = dump_database(case.store_path)
    before_ledger = dump_database(case.ledger_path)
    report = assess(case)
    assert_observation_only(report)
    assert report.schema_version == "1.3"
    assert report.draft_ready and report.handoff == "LOCAL_DRAFT_HANDOFF"
    stage = report.stages[5]
    assert dict(stage.refs) == {
        "assembly_hash": saved.assembly_hash,
        "assembly_prose_hash": saved.prose_hash,
        "extraction_observation_hash": saved.record_hash,
    }
    if correspondence == "PASS":
        assert stage.state == stage.reason == "CURRENT"
        assert report.stop_stage == "Q0_Q3"
        assert report.stop_code == "LOCAL_QUALITY_OBSERVATIONS_ONLY"
        assert report.first_blocker.state == "BLOCKED" and not report.first_blocker.refs
    else:
        assert stage.state == "BLOCKED" and report.first_blocker == stage
        assert stage.reason == f"EXTRACTION_CORRESPONDENCE_{correspondence}"
        assert report.stages[6].state == "NOT_REACHED" and not report.stages[6].refs
    assert {name: row["state"] for name, row in quality_rows(report).items()} == {
        "Q0": "MISSING",
        "Q1": "INPUT_REQUIRED",
        "Q2": "MISSING",
        "Q3": "MISSING",
    }
    current = tmp_path / "current.json"
    current.write_bytes(case.case.frozen.payload)
    cli = run_cli(
        case, "inspect-run", "--input", current, "--step-id", case.child.step_id
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    adapted = WorkflowTaskAdapter(case.service).execute(
        {
            "operation": "ASSESS_RUN",
            "current_input": case.case.frozen.to_dict(),
            "project": PROJECT,
            "branch": BRANCH,
            "run_id": RUN,
            "step_id": case.child.step_id,
        }
    )
    assert adapted.payload_bytes() == report.payload_bytes()
    assert (
        RunAssessment.from_dict(json.loads(cli.stdout)).payload_bytes()
        == report.payload_bytes()
    )
    changed = report.to_dict()
    changed["stages"][5]["refs"]["assembly_hash"] = "0" * 64
    with pytest.raises(WorkflowError, match="INVALID_RUN_ASSESSMENT"):
        RunAssessment.from_dict(changed)
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


def test_corrupt_persisted_extraction_stops_without_recreating_it(
    run_case, monkeypatch
):
    case = run_case
    saved = extract(case)
    with closing(sqlite3.connect(case.store_path)) as connection, connection:
        connection.execute(
            "UPDATE extraction_observations SET payload_hash=? WHERE assembly_hash=?",
            ("0" * 64, saved.assembly_hash),
        )
    forbid_discovery(monkeypatch)
    before = dump_database(case.store_path)
    report = assess(case)
    assert_observation_only(report)
    assert report.first_blocker == report.stages[5]
    assert report.first_blocker.state == "BLOCKED"
    assert report.stop_code == "EXTRACTION_OBSERVATION_INVALID"
    assert not report.first_blocker.refs
    assert_unreached_quality(report)
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "UNKNOWN", "ERROR"])
def test_observe_persisted_q0_without_inferring_q1_q3(
    run_case, outcome, tmp_path, monkeypatch
):
    case = run_case
    observation = extract(case)
    assert observation.correspondence_status == "PASS"

    def checker_fault(*_args):
        if outcome == "ERROR":
            raise RuntimeError("transparent local checker fault")
        return q0.CheckResult(outcome, (q0.Q0Finding("TEST_LOCAL_Q0_VERDICT"),))

    with monkeypatch.context() as setup:
        if outcome != "PASS":
            setup.setattr(q0, "_check_bindings", checker_fault)
        retained = check_q0(case)
    assert retained.q0_status == outcome
    assert retained.aggregate_status == "BLOCKED"
    with pytest.raises(q0.Q0Error, match="Q0_NATIVE_EXECUTION_REQUIRED"):
        q0.require_local_execution(retained)
    forbid_native_runner(monkeypatch)
    forbid_discovery(monkeypatch)

    def unexpected(*_args, **_kwargs):
        pytest.fail("Observer cannot publish local checks or resolve Q1 through Q3")

    for method in ("create_q0", "load_q1"):
        monkeypatch.setattr(case.store, method, unexpected)
    before_store = dump_database(case.store_path)
    before_ledger = dump_database(case.ledger_path)
    report = assess(case)
    assert_observation_only(report)
    assert report.schema_version == "1.3"
    assert report.handoff == "LOCAL_DRAFT_HANDOFF" and report.draft_ready
    assert report.stop_stage == "Q0_Q3"
    assert report.first_blocker.state == "BLOCKED" and not report.first_blocker.refs
    assert report.stop_code == "LOCAL_QUALITY_OBSERVATIONS_ONLY"
    quality = quality_rows(report)
    assert quality["Q0"] == {
        "check": "Q0",
        "state": outcome,
        "refs": {
            "observation_hash": observation.record_hash,
            "input_hash": retained.input_hash,
            "record_hash": retained.record_hash,
        },
    }
    assert quality["Q1"] == {"check": "Q1", "state": "INPUT_REQUIRED", "refs": {}}
    for check in ("Q2", "Q3"):
        assert quality[check] == {"check": check, "state": "MISSING", "refs": {}}
    assert (
        RunAssessment.from_bytes(report.payload_bytes()).payload_bytes()
        == report.payload_bytes()
    )
    changed = report.to_dict()
    changed["quality_observations"][0]["refs"]["observation_hash"] = "0" * 64
    with pytest.raises(WorkflowError, match="INVALID_RUN_ASSESSMENT"):
        RunAssessment.from_dict(changed)
    if outcome == "PASS":
        assert_historical_q0_roundtrip(report, observation, retained)
        current = tmp_path / "current.json"
        current.write_bytes(case.case.frozen.payload)
        cli = run_q0_cli(
            case, "inspect-run", "--input", current, "--step-id", case.child.step_id
        )
        assert cli.returncode == 0, cli.stdout + cli.stderr
        adapted = WorkflowTaskAdapter(case.service).execute(
            {
                "operation": "ASSESS_RUN",
                "current_input": case.case.frozen.to_dict(),
                "project": PROJECT,
                "branch": BRANCH,
                "run_id": RUN,
                "step_id": case.child.step_id,
            }
        )
        assert adapted.payload_bytes() == report.payload_bytes()
        assert (
            RunAssessment.from_dict(json.loads(cli.stdout)).payload_bytes()
            == report.payload_bytes()
        )
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
def test_corrupt_retained_q0_is_blocked_without_exposing_a_record_hash(
    run_case, monkeypatch
):
    case = run_case
    observation = extract(case)
    check_q0(case)
    with closing(sqlite3.connect(case.store_path)) as connection, connection:
        connection.execute(
            "UPDATE q0_executions SET payload_hash=? WHERE observation_hash=?",
            ("0" * 64, observation.record_hash),
        )
    forbid_native_runner(monkeypatch)
    before = dump_database(case.store_path)
    report = assess(case)
    assert_observation_only(report)
    assert report.stop_stage == "Q0_Q3"
    assert report.stop_code == "LOCAL_QUALITY_OBSERVATIONS_ONLY"
    assert report.first_blocker.state == "BLOCKED" and not report.first_blocker.refs
    assert quality_rows(report)["Q0"] == {"check": "Q0", "state": "INVALID", "refs": {}}
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
def test_current_quality_chain_selects_exact_annotations_and_invalidates_on_edit(
    run_case, tmp_path, monkeypatch
):
    case = run_case
    scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": case.child.step_id,
    }
    frozen = case.case.frozen
    observation = extract(case)
    assert observation.correspondence_status == "PASS"
    assembled = observation.assembly
    first = BoundQ1Annotations.freeze(observation, claims=())
    span = ExactSpan.from_source(assembled.prose, 0, 1)
    second = BoundQ1Annotations.freeze(
        observation, claims=(ReaderRevealClaim(span, None),)
    )
    checks = {
        "Q0": case.service.check_q0(frozen, **scope),
        "Q1": case.service.check_q1(frozen, first, **scope),
        "Q2": case.service.check_q2(frozen, **scope),
        "Q3": case.service.check_q3(frozen, **scope),
    }
    alternative = case.service.check_q1(frozen, second, **scope)
    assert first.record_hash != second.record_hash
    assert checks["Q1"].record_hash != alternative.record_hash
    for saved in (*checks.values(), alternative):
        assert saved.observation_hash == observation.record_hash
        assert saved.assembly_hash == assembled.record_hash
        assert saved.prose_hash == assembled.prose_hash
        assert saved.aggregate_status == "BLOCKED"

    def unexpected(*_args, **_kwargs):
        pytest.fail("Run assessment may only read the retained quality records")

    forbid_discovery(monkeypatch)
    for check in QUALITY_CHECKS:
        name = check.lower()
        monkeypatch.setattr(case.service, "check_" + name, unexpected)
        monkeypatch.setattr(case.store, "create_" + name, unexpected)
        monkeypatch.setattr("anovel.workflow.chapter.execute_local_" + name, unexpected)
    before_store = dump_database(case.store_path)
    before_ledger = dump_database(case.ledger_path)
    selected = first.record_hash
    request = {
        "operation": "ASSESS_RUN",
        "current_input": frozen.to_dict(),
        "q1_annotations_hash": selected,
        **scope,
    }
    observed = WorkflowTaskAdapter(case.service).execute(request)
    assert_observation_only(observed)
    assert observed.schema_version == "1.3"
    assert observed.to_dict()["q1_annotations_hash"] == selected
    assert observed.handoff == "LOCAL_DRAFT_HANDOFF"
    assert observed.stop_stage == "Q0_Q3"
    assert observed.stop_code == "LOCAL_QUALITY_OBSERVATIONS_ONLY"
    assert not observed.first_blocker.refs
    assert_historical_q0_roundtrip(observed, observation, checks["Q0"])
    dimension_refs = {
        "Q0": {"input_hash": checks["Q0"].input_hash},
        "Q1": {"annotations_hash": selected},
        "Q2": {"method_policy_hash": Q2_METHOD_POLICY_HASH},
        "Q3": {"method_policy_hash": Q3_METHOD_POLICY_HASH},
    }
    rows = quality_rows(observed)
    for name, saved in checks.items():
        assert rows[name] == {
            "check": name,
            "state": getattr(saved, name.lower() + "_status"),
            "refs": {
                "observation_hash": observation.record_hash,
                "record_hash": saved.record_hash,
                **dimension_refs[name],
            },
        }

    current = tmp_path / "current.json"
    current.write_bytes(frozen.payload)
    cli = subprocess.run(
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
            "inspect-run",
            "--input",
            str(current),
            "--step-id",
            case.child.step_id,
            "--q1-annotations-hash",
            selected,
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert (
        RunAssessment.from_dict(json.loads(cli.stdout)).payload_bytes()
        == observed.payload_bytes()
    )
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger

    edited = edit(case, case.source, case.source.prose + b"\nexplicit-quality-edit")
    with monkeypatch.context() as stopped:
        for name in ("load_extraction", "load_q0", "load_q1", "load_q2", "load_q3"):
            stopped.setattr(case.store, name, unexpected)
        stale = WorkflowTaskAdapter(case.service).execute(request)
    assert_stop(stale, "SCENE_BINDING", "STALE", "SCENE_SOURCE_CHANGED")
    assert stale.source_record_hash == edited.record_hash
    assert stale.to_dict()["q1_annotations_hash"] == selected
    with closing(sqlite3.connect(case.store_path)) as connection:
        for name, saved in checks.items():
            table = name.lower() + "_executions"
            retained = {
                row[0]
                for row in connection.execute(
                    f"SELECT payload_hash FROM {table} WHERE observation_hash=?",
                    (observation.record_hash,),
                )
            }
            expected = {saved.record_hash}
            if name == "Q1":
                expected.add(alternative.record_hash)
            assert retained == expected
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
def test_selected_missing_invalid_and_stale_quality_stay_independent(
    run_case, monkeypatch
):
    case = run_case
    observation = extract(case)
    selected = BoundQ1Annotations.freeze(observation, claims=()).record_hash

    def unavailable_q2(**values):
        assert values["observation_hash"] == observation.record_hash
        assert values["method_policy_hash"] == Q2_METHOD_POLICY_HASH
        raise WorkflowError("CORRUPT_Q2_EXECUTION")

    def stale_q3(**values):
        assert values["observation_hash"] == observation.record_hash
        assert values["method_policy_hash"] == Q3_METHOD_POLICY_HASH
        raise WorkflowError("Q3_SOURCE_CHANGED")

    # Isolate two existing store error contracts without persisting fake runs.
    monkeypatch.setattr(case.store, "load_q2", unavailable_q2)
    monkeypatch.setattr(case.store, "load_q3", stale_q3)
    before = dump_database(case.store_path)
    report = assess(case, q1_annotations_hash=selected)
    assert_observation_only(report)
    assert report.to_dict()["q1_annotations_hash"] == selected
    assert report.stop_code == "LOCAL_QUALITY_OBSERVATIONS_ONLY"
    assert quality_rows(report) == {
        "Q0": {"check": "Q0", "state": "MISSING", "refs": {}},
        "Q1": {"check": "Q1", "state": "MISSING", "refs": {}},
        "Q2": {"check": "Q2", "state": "INVALID", "refs": {}},
        "Q3": {"check": "Q3", "state": "STALE", "refs": {}},
    }
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize("run_case", ["finite-extraction"], indirect=True)
@pytest.mark.parametrize(
    "change", ["appears", "same-status-replacement", "corrupt-digest"]
)
def test_final_reread_rejects_q0_changes(run_case, monkeypatch, change):
    case = run_case
    observation = extract(case)
    later = q0.execute_local_q0(observation)
    assert later.q0_status == "PASS"
    if change == "same-status-replacement":
        first = check_q0(case)
        assert (
            first.q0_status == later.q0_status
            and first.record_hash != later.record_hash
        )
    elif change == "corrupt-digest":
        assert check_q0(case).q0_status == "PASS"
    forbid_native_runner(monkeypatch)
    original = case.store.load_q0
    reads = 0

    def change_during_read(**arguments):
        nonlocal reads
        reads += 1
        if reads == 2:
            if change == "appears":
                assert case.store.create_q0(later)
            else:
                with (
                    closing(sqlite3.connect(case.store_path)) as connection,
                    connection,
                ):
                    if change == "corrupt-digest":
                        connection.execute(
                            "UPDATE q0_executions SET payload_hash=? WHERE observation_hash=?",
                            ("0" * 64, observation.record_hash),
                        )
                    else:
                        connection.execute(
                            "UPDATE q0_executions SET payload=?,payload_hash=? WHERE observation_hash=?",
                            (
                                later.payload_bytes(),
                                later.record_hash,
                                observation.record_hash,
                            ),
                        )
        return original(**arguments)

    monkeypatch.setattr(case.store, "load_q0", change_during_read)
    with pytest.raises(WorkflowError, match="RUN_CHANGED_DURING_ASSESSMENT"):
        assess(case)
    assert reads == 2


@pytest.mark.parametrize("change", ["appears", "same-status-replacement"])
def test_final_reread_rejects_extraction_changes(run_case, monkeypatch, change):
    case = run_case
    assembly = case.service.assemble_chapter(
        case.case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        step_id=case.child.step_id,
    )
    first = extractor.extract_assembly(assembly)
    if change == "same-status-replacement":
        assert case.store.create_extraction(first)
        replacement = extractor.extract_assembly(
            assembly,
            aliases=tuple(
                replace(alias, alias=alias.alias + "-alternate")
                for alias in first.catalog
            ),
        )
        assert first.correspondence_status == replacement.correspondence_status
        assert first.record_hash != replacement.record_hash
    forbid_discovery(monkeypatch)
    original = case.store.load_extraction
    reads = 0

    def replace_during_read(**arguments):
        nonlocal reads
        reads += 1
        if reads == 2:
            if change == "appears":
                assert case.store.create_extraction(first)
            else:
                with (
                    closing(sqlite3.connect(case.store_path)) as connection,
                    connection,
                ):
                    connection.execute(
                        "UPDATE extraction_observations SET payload=?,payload_hash=? WHERE assembly_hash=?",
                        (
                            replacement.payload_bytes(),
                            replacement.record_hash,
                            first.assembly_hash,
                        ),
                    )
        return original(**arguments)

    monkeypatch.setattr(case.store, "load_extraction", replace_during_read)
    with pytest.raises(WorkflowError, match="RUN_CHANGED_DURING_ASSESSMENT"):
        assess(case)
    assert reads == 2


def test_missing_current_slot_reports_missing_and_detects_a_late_appearing_record(
    run_case, monkeypatch
):
    case = run_case
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "DELETE FROM scene_generations WHERE run_id=? AND step_id=?",
            (RUN, case.child.step_id),
        )
    report = assess(case)
    assert_stop(report, "SCENE_BINDING", "MISSING", "SCENE_BINDING_REQUIRED")
    assert not any("child" in key for key, _value in report.stages[2].refs)
    original, reads = case.store.load_scene, 0

    def appeared(**arguments):
        nonlocal reads
        reads += 1
        if reads == 2:
            insert_child(case, case.child)
        return original(**arguments)

    monkeypatch.setattr(case.store, "load_scene", appeared)
    with pytest.raises(WorkflowError, match="RUN_CHANGED_DURING_ASSESSMENT"):
        assess(case)


def test_actual_root_unpublished_cut_stops_before_reading_any_child_or_receipt(
    run_case, monkeypatch
):
    case = run_case
    store_root(case, case.seed.root_unpublished)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("A non-Draft source cannot qualify later scene stages")

    monkeypatch.setattr(case.store, "load_scene", forbidden)
    monkeypatch.setattr(case.store, "load_extraction", forbidden)
    report = assess(case)
    assert_stop(report, "SOURCE_DRAFT", "BLOCKED", "SOURCE_DRAFT_NOT_READY")
    assert report.source_record_hash == case.seed.root_unpublished.record_hash


def test_actual_child_unpublished_cut_stops_without_recovering_its_finished_gateway_result(
    run_case,
):
    case = run_case
    store_child(case, case.seed.unpublished)
    before = dump_database(case.ledger_path)
    report = assess(case)
    assert_stop(report, "SCENE_DRAFT", "BLOCKED", "SCENE_DRAFT_NOT_READY")
    assert (
        case.store.load_scene(
            project=PROJECT, branch=BRANCH, run_id=RUN, step_id=case.child.step_id
        ).state
        == "DISPATCHING"
    )
    assert dump_database(case.ledger_path) == before


def test_transparent_typed_unknown_fault_is_only_a_negative_stopped_observation(
    run_case,
):
    case = run_case
    unknown = replace(
        case.child.result,
        reply=ProviderReply("UNKNOWN", error_code="SYNTHETIC_TYPED_NEGATIVE_FAULT"),
        charge_status="PENDING",
        charge_microusd=None,
    )
    fault = replace(
        case.child,
        state="UNKNOWN",
        result_bytes=unknown.to_bytes(),
        prose=None,
        diagnostic="TRANSPARENT_TYPED_NEGATIVE_FAULT_NOT_PROVIDER_EVIDENCE",
    )
    store_child(case, fault)
    before = dump_database(case.ledger_path)
    report = assess(case)
    assert_stop(report, "SCENE_DRAFT", "BLOCKED", "GATEWAY_OUTCOME_UNKNOWN")
    assert dump_database(case.ledger_path) == before


@pytest.mark.parametrize(
    "changed_scope", [{"project": "another-project"}, {"branch": "another-branch"}]
)
def test_wrong_scope_is_rejected_instead_of_returning_another_runs_observations(
    run_case, changed_scope
):
    with pytest.raises(WorkflowError, match="WORKFLOW_RUN_UNAVAILABLE"):
        assess(run_case, **changed_scope)


def test_changed_current_frozen_inputs_are_rejected_before_reporting_stages(run_case):
    case = run_case
    row = case.case.frozen.to_dict()
    row["instructions"] = "different-explicit-current-input"
    changed = FrozenChapterInput.from_dict(row)
    with pytest.raises(WorkflowError, match="WORKFLOW_INPUT_CHANGED"):
        assess(case, current=changed)


def test_corrupt_parent_is_rejected_without_inventing_a_run_graph(run_case):
    case = run_case
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "UPDATE runs SET payload_hash=? WHERE run_id=?", ("0" * 64, RUN)
        )
    with pytest.raises(WorkflowError, match="CORRUPT_WORKFLOW_RECORD"):
        assess(case)


def test_corrupt_child_is_localized_without_a_fabricated_child_hash(run_case):
    case = run_case
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "UPDATE scene_generations SET payload_hash=? WHERE run_id=? AND step_id=?",
            ("0" * 64, RUN, case.child.step_id),
        )
    report = assess(case)
    assert_stop(report, "SCENE_BINDING", "BLOCKED", "SCENE_RECORD_INVALID")
    assert not any("child" in key for key, _value in report.stages[2].refs)


def test_self_consistent_wrong_child_receipt_stops_at_scene_draft_not_at_quality(
    run_case,
):
    case = run_case
    prose = b"self-consistent-but-not-the-real-ledger-response"
    reply = replace(
        case.child.result.reply,
        response_body=canonical_bytes({"synthetic-forged": True}),
        output_bytes=canonical_bytes({"text": prose.decode()}),
    )
    result = replace(case.child.result, reply=reply)
    forged = replace(case.child, result_bytes=result.to_bytes(), prose=prose)
    store_child(case, forged)
    before = dump_database(case.ledger_path)
    report = assess(case)
    assert_stop(report, "SCENE_DRAFT", "BLOCKED", "SCENE_RECEIPT_INVALID")
    assert dump_database(case.ledger_path) == before


def test_default_step_after_edit_does_not_reuse_stale_previous_source_slot(run_case):
    case = run_case
    edited = edit(case, case.source, case.source.prose + b"\nexplicit-edit")
    report = assess(case)
    assert_stop(report, "SCENE_BINDING", "MISSING", "SCENE_BINDING_REQUIRED")
    assert report.source_record_hash == edited.record_hash
    assert report.step_id != case.child.step_id


@pytest.mark.parametrize("revert", [False, True])
def test_explicit_historical_step_stays_stale_after_edit_or_revert(run_case, revert):
    case = run_case
    edited = edit(case, case.source, case.source.prose + b"\nexplicit-edit")
    if revert:
        edited = edit(case, edited, case.source.prose)
        assert edited.prose_hash == case.source.prose_hash
    report = assess(case, step_id=case.child.step_id)
    assert_stop(report, "SCENE_BINDING", "STALE", "SCENE_SOURCE_CHANGED")
    assert report.source_record_hash == edited.record_hash


@pytest.mark.parametrize("which", ["parent", "child"])
def test_final_reread_rejects_a_mixed_graph_when_an_observed_row_changes(
    run_case, monkeypatch, which
):
    case = run_case
    reads = 0
    if which == "parent":
        original = case.store.load
        new_prose = case.source.prose + b"\ntransparent-concurrent-edit"
        version = DraftRevision(2, new_prose, "MANUAL", case.source.prose_hash)
        changed = replace(
            case.source,
            versions=(*case.source.versions, version),
            diagnostic="TRANSPARENT_CONCURRENT_FAULT",
        )

        def injected(**arguments):
            nonlocal reads
            reads += 1
            if reads == 3:
                store_root(case, changed)
            return original(**arguments)

        monkeypatch.setattr(case.store, "load", injected)
    else:
        original = case.store.load_scene
        changed = replace(case.child, diagnostic="TRANSPARENT_CONCURRENT_FAULT")

        def injected(**arguments):
            nonlocal reads
            reads += 1
            if reads == 3:
                store_child(case, changed)
            return original(**arguments)

        monkeypatch.setattr(case.store, "load_scene", injected)
    with pytest.raises(WorkflowError, match="RUN_CHANGED_DURING_ASSESSMENT"):
        assess(case)


@pytest.mark.parametrize("run_case", ["tail"], indirect=True)
def test_genuine_current_scene_receipts_still_stop_at_invalid_whole_source_assembly(
    run_case,
):
    report = assess(run_case)
    assert_stop(report, "CHAPTER_ASSEMBLY", "BLOCKED", "CHAPTER_ASSEMBLY_INVALID")
    assert all(stage.state == "CURRENT" for stage in report.stages[:4])
    assert not any(key.startswith("assembly_") for key, _value in report.stages[4].refs)


def test_task_and_real_cli_only_observe_and_reject_all_caller_supplied_gate_claims(
    run_case, tmp_path
):
    case = run_case
    request = {
        "operation": "ASSESS_RUN",
        "current_input": case.case.frozen.to_dict(),
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": None,
    }
    adapter = WorkflowTaskAdapter(case.service)
    expected = adapter.execute(request)
    assert_observation_only(expected)
    for field in ("report", "checks", "PASS", "required", "delta", "permit"):
        with pytest.raises(WorkflowError, match="INVALID_WORKFLOW_TASK_REQUEST"):
            adapter.execute(request | {field: {"status": "PASS"}})
    for invalid in ("", "A" * 64, "g" * 64, True, {"hash": "0" * 64}):
        with pytest.raises(WorkflowError):
            adapter.execute(request | {"q1_annotations_hash": invalid})
    current = tmp_path / "current.json"
    current.write_bytes(case.case.frozen.payload)
    before_store, before_ledger = (
        dump_database(case.store_path),
        dump_database(case.ledger_path),
    )
    for args in (
        ("inspect-run", "--input", current),
        ("inspect-run", "--input", current, "--step-id", case.child.step_id),
    ):
        result = run_cli(case, *args)
        assert result.returncode == 0, result.stdout + result.stderr
        observed = RunAssessment.from_dict(json.loads(result.stdout))
        assert observed.payload_bytes() == expected.payload_bytes()
        assert (
            FIRST.decode() not in result.stdout and SECOND.decode() not in result.stdout
        )
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


def storage_snapshot(directory):
    return {
        str(path.relative_to(directory)): (
            path.lstat().st_mode,
            path.lstat().st_ino,
            path.lstat().st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
        for path in (directory, *sorted(directory.rglob("*")))
    }


@pytest.mark.parametrize(
    "kind",
    [
        "zero-byte",
        "empty-sqlite",
        "foreign",
        "missing-run",
        "missing-locks",
        "foreign-wal",
        "valid-wal",
        "valid-journal",
    ],
)
def test_cli_preflight_rejects_unavailable_existing_stores_without_provisioning(
    tmp_path, kind
):
    case = scene_case()
    database = tmp_path / "existing.sqlite"
    database.touch(mode=0o600)
    if kind in {"empty-sqlite", "foreign", "foreign-wal"}:
        connection = sqlite3.connect(database)
        try:
            if kind == "foreign-wal":
                assert (
                    connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
                )
            connection.execute("PRAGMA user_version=1")
            if kind in {"foreign", "foreign-wal"}:
                connection.execute("CREATE TABLE owner_data(value TEXT NOT NULL)")
                connection.execute(
                    "INSERT INTO owner_data VALUES ('preserve-existing-data')"
                )
            connection.commit()
        finally:
            connection.close()
        database.with_name(database.name + ".locks").mkdir(mode=0o700)
    elif kind in {"missing-run", "missing-locks", "valid-wal", "valid-journal"}:
        store = WorkflowStore(database)
        existing_run = "another-existing-run" if kind == "missing-run" else RUN
        contract, context, request = case.frozen.request(existing_run, LOGICAL)
        prepared = WorkflowSnapshot(
            case.frozen,
            request.to_bytes(),
            canonical_bytes(contract.to_dict()),
            context.to_bytes(),
            ATTEMPT,
            case.policies[0].id,
        )
        assert store.create(prepared)
        if kind == "missing-locks":
            store.lock_directory.rmdir()
        elif kind == "valid-wal":
            connection = sqlite3.connect(database)
            try:
                assert (
                    connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
                )
            finally:
                connection.close()
        elif kind == "valid-journal":
            journal = database.with_name(database.name + "-journal")
            journal.write_bytes(b"pre-existing-owned-test-journal")
            journal.chmod(0o600)
    if kind in {"foreign-wal", "valid-wal"}:
        assert database.read_bytes()[18:20] == b"\x02\x02"
        assert not database.with_name(database.name + "-wal").exists()
        assert not database.with_name(database.name + "-shm").exists()
    current = tmp_path / "current.json"
    current.write_bytes(case.frozen.payload)

    before = storage_snapshot(tmp_path)
    result = run_cli(
        SimpleNamespace(store_path=database), "inspect-run", "--input", current
    )
    assert storage_snapshot(tmp_path) == before, (
        "inspect-run modified an unavailable existing store or its directories"
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "BLOCKED"


@pytest.mark.parametrize(
    ("table", "with_extraction", "alter_parent"),
    [
        pytest.param("sqliteXforeign", False, None, id="foreign-table"),
        pytest.param("chapter_revisions", False, None, id="missing-extraction"),
        pytest.param("revision_q0_executions", True, None, id="missing-q0-parent"),
        pytest.param("revision_q123_executions", True, None, id="missing-q123-parent"),
        pytest.param("chapter_revisions", True, None, id="malformed-revision"),
        pytest.param("chapter_revisions", True, "runs", id="malformed-runs"),
        pytest.param(
            "chapter_revisions", True, "scene_generations", id="malformed-scene"
        ),
        pytest.param(
            "chapter_revisions",
            True,
            "extraction_observations",
            id="malformed-extraction",
        ),
    ],
)
def test_cli_rejects_invalid_revision_schema_before_opening_store(
    run_case, tmp_path, monkeypatch, capsys, table, with_extraction, alter_parent
):
    database = run_case.store_path
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if with_extraction:
            assert WorkflowStore._extraction_table(connection, create=True)
        if alter_parent:
            connection.execute(
                f'ALTER TABLE "{alter_parent}" ADD COLUMN unexpected TEXT'
            )
        connection.execute(f'CREATE TABLE "{table}" (payload BLOB)')

    def unexpected_init(*_args, **_kwargs):
        pytest.fail("Inspecting an invalid schema reached the Store constructor")

    monkeypatch.setattr(WorkflowStore, "__init__", unexpected_init)
    current = tmp_path / "current.json"
    current.write_bytes(run_case.case.frozen.payload)
    before = storage_snapshot(tmp_path)
    assert (
        main(
            [
                "--db",
                str(database),
                "--project",
                PROJECT,
                "--branch",
                BRANCH,
                "--run-id",
                RUN,
                "inspect-run",
                "--input",
                str(current),
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {
        "status": "BLOCKED",
        "code": "WORKFLOW_RUN_UNAVAILABLE",
    }
    assert storage_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("operation", "valid_schema"),
    (
        ("extract-chapter", True),
        ("inspect-extraction", True),
        ("check-q0", True),
        ("inspect-q0", True),
        ("check-q1", True),
        ("inspect-q1", True),
        ("check-q2", True),
        ("inspect-q2", True),
        ("check-q3", True),
        ("inspect-q3", True),
        ("extract-chapter", False),
        ("inspect-q3", False),
    ),
)
def test_cli_preflights_revision_schema_before_task(
    tmp_path, monkeypatch, capsys, operation, valid_schema
):
    database = tmp_path / "workflow.sqlite"
    store = WorkflowStore(database)
    case = scene_case()
    frozen = case.frozen
    contract, context, request = frozen.request(RUN, LOGICAL)
    prepared = WorkflowSnapshot(
        frozen,
        request.to_bytes(),
        canonical_bytes(contract.to_dict()),
        context.to_bytes(),
        ATTEMPT,
        case.policies[0].id,
    )
    assert store.create(prepared)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        assert WorkflowStore._scene_table(connection, create=True)
        assert WorkflowStore._extraction_table(connection, create=True)
        assert WorkflowStore._chapter_revision_table(connection, create=True)
        assert WorkflowStore._revision_q0_table(connection, create=True)
        assert WorkflowStore._revision_q123_table(connection, create=True)
        if not valid_schema:
            connection.execute(
                "ALTER TABLE chapter_revisions ADD COLUMN unexpected TEXT"
            )

    step_id = "a" * 64
    current = tmp_path / "current.json"
    current.write_bytes(frozen.payload)
    arguments = [
        "--db",
        str(database),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
        operation,
        "--input",
        str(current),
        "--step-id",
        step_id,
    ]
    expected = {
        "operation": operation.replace("-", "_").upper(),
        "current_input": frozen.to_dict(),
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": step_id,
    }
    if operation.endswith("-q1"):
        annotations = tmp_path / "annotations.json"
        annotations.write_bytes(canonical_bytes({}))
        arguments.extend(("--annotations", str(annotations)))
        expected["annotations"] = {}

    def stop_at_task(_adapter, request):
        assert request == expected
        raise WorkflowError("TEST_TASK_REACHED")

    monkeypatch.setattr(WorkflowTaskAdapter, "execute", stop_at_task)
    before = storage_snapshot(tmp_path)
    assert main(arguments) == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "BLOCKED",
        "code": "TEST_TASK_REACHED" if valid_schema else "WORKFLOW_RUN_UNAVAILABLE",
    }
    assert storage_snapshot(tmp_path) == before


def test_revision_schema_validators_use_read_only_connection(run_case, monkeypatch):
    database = run_case.store_path
    validators = {
        "chapter_revisions": "_chapter_revision_table",
        "revision_q0_executions": "_revision_q0_table",
        "revision_q123_executions": "_revision_q123_table",
    }
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        assert WorkflowStore._extraction_table(connection, create=True)
        for table in validators:
            connection.execute(f'CREATE TABLE "{table}" (payload TEXT)')
            connection.execute(f'INSERT INTO "{table}" VALUES (?)', (table,))

    checked = []

    def validator_for(table):
        def validate(connection, *, create):
            assert create is False
            row = connection.execute(f'SELECT payload FROM "{table}"').fetchone()
            assert isinstance(row, sqlite3.Row) and row["payload"] == table
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                connection.execute("CREATE TABLE unexpected (value TEXT)")
            checked.append(table)
            return True

        return staticmethod(validate)

    for table, method in validators.items():
        monkeypatch.setattr(WorkflowStore, method, validator_for(table), raising=False)

    with pytest.raises(WorkflowError, match="WORKFLOW_RUN_UNAVAILABLE"):
        _require_existing_run(database, PROJECT, BRANCH, RUN)
    assert not checked
    _require_existing_run(database, PROJECT, BRANCH, RUN, accept_revision_tables=True)
    assert checked == list(validators)

    monkeypatch.delattr(WorkflowStore, validators["chapter_revisions"])
    with pytest.raises(WorkflowError, match="WORKFLOW_RUN_UNAVAILABLE"):
        _require_existing_run(
            database, PROJECT, BRANCH, RUN, accept_revision_tables=True
        )
    assert checked == list(validators)


@pytest.mark.parametrize(
    ("statements", "valid_schema"),
    (
        pytest.param((), True, id="current"),
        pytest.param(("DROP TABLE estimate_fee_bounds",), True, id="legacy"),
        pytest.param(
            ("CREATE TABLE sqliteXforeign (value TEXT)",), False, id="unknown-table"
        ),
        pytest.param(
            (
                "DROP TABLE estimate_fee_bounds",
                (
                    "CREATE TABLE estimate_fee_bounds (run_id TEXT NOT NULL, "
                    "attempt_id TEXT NOT NULL, fee_record BLOB NOT NULL, "
                    "PRIMARY KEY (run_id, attempt_id))"
                ),
            ),
            False,
            id="missing-composite-foreign-key",
        ),
        pytest.param(
            (
                "DROP TABLE estimate_fee_bounds",
                (
                    "CREATE VIEW estimate_fee_bounds AS "
                    "SELECT run_id, attempt_id, result_record AS fee_record FROM attempts"
                ),
            ),
            False,
            id="same-name-view",
        ),
    ),
)
def test_existing_gateway_ledger_recognizes_known_schemas_without_writes(
    tmp_path, statements, valid_schema
):
    env = harness(tmp_path)
    saved = start(env, source_case())
    assert saved.state == "DRAFT_SAVED" and saved.result is not None
    with closing(sqlite3.connect(env.ledger_path)) as connection, connection:
        # Keep the snapshot independent of transient SQLite WAL reader files.
        assert (
            connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
        )
        for statement in statements:
            connection.execute(statement)
    before = storage_snapshot(tmp_path)
    if valid_schema:
        assert existing_gateway_ledger(env.ledger_path, env.store, saved) == (
            env.ledger_path.resolve()
        )
    else:
        with pytest.raises(WorkflowError, match="^INVALID_GATEWAY_LEDGER$"):
            existing_gateway_ledger(env.ledger_path, env.store, saved)
    assert storage_snapshot(tmp_path) == before
    assert env.adapter.calls == 1
