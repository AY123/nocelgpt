"""Offline extraction observations, never natural-prose quality or acceptance.

The finite backends read raw prose and value-free identities. Expected labels
remain test assertions. Two genuine local Gateway/SQLite module seeds cover
the application boundary; each fault gets a separate Workflow database while
retaining the original, unmodified Gateway ledger and receipts.
"""

import inspect
import json
import socket
import sqlite3
from base64 import b64encode
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from test_v2_017 import BRANCH, PROJECT, eid
from test_v2_020 import (
    RUN,
    CountingLocalAdapter,
    SimulatedProcessExit,
    harness,
    run_cli,
    start,
)
from test_v2_020_assembly import clone_workflow, edit
from test_v2_020_scene import scene_case
from test_v2_020_scene_generation import dump_database, start_child

from anovel.canon.chapter import ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes
from anovel.context.scene import SceneDeltaBinding, SceneSpan
from anovel.domain.delta import NoChange, ScalarKind
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.workflow import extractor
from anovel.workflow.assembly import ChapterAssembly
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.extractor import ExtractionObservation, FactAlias
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.store import WorkflowStore

QUIET = "风掠过窗边。"
ACTUAL = "balance变为20。"
CATALOG = (FactAlias(eid("balance"), "balance", ScalarKind.NUMBER),)


@pytest.fixture(scope="module", autouse=True)
def no_network_or_provider_construction():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("V021 observations must remain offline")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(socket.socket, "connect", forbidden)
        patch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
        yield


def make_extraction_seed(directory, quiet):
    # The nonzero draft deliberately disagrees with Contract's requested 30.
    # Discovery must report the text's 20 rather than copy the writing plan.
    case = scene_case(target_required=not quiet)
    env = harness(directory, adapter=CountingLocalAdapter(output={"text": QUIET}))
    source = start(env, case)
    projection = env.workflow.project_scene(
        case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        expected_record_hash=source.record_hash,
        source_scene_id=source.contract.scenes[0].id,
        target_scene_id=source.contract.scenes[1].id,
        source_span=SceneSpan(0, len(QUIET), QUIET),
        ending_span=SceneSpan(0, len(QUIET), QUIET),
        delta_binding=SceneDeltaBinding(None, "synthetic-quiet-scene/not-human-review"),
    )
    env.adapter.output = {"text": QUIET if quiet else ACTUAL}
    child = start_child(env, case, projection)
    assembly = env.workflow.assemble_chapter(
        case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        step_id=child.step_id,
    )
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 2
    return SimpleNamespace(
        case=case,
        env=env,
        source=source,
        child=child,
        projection=projection,
        assembly=assembly,
    )


@pytest.fixture(scope="module")
def extraction_seeds(tmp_path_factory):
    seeds = {}

    def get(quiet=False):
        if quiet not in seeds:
            seeds[quiet] = make_extraction_seed(
                tmp_path_factory.mktemp("v021-quiet" if quiet else "v021-finite"),
                quiet,
            )
        return seeds[quiet]

    return get


@pytest.fixture
def extraction_case(extraction_seeds, tmp_path, monkeypatch, request):
    seed = extraction_seeds(getattr(request, "param", False))
    case = clone_workflow(seed, tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "Extraction cannot dispatch, recover, provision, issue or commit"
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


@pytest.fixture(scope="module")
def observed_seed(extraction_seeds):
    seed = extraction_seeds()
    return SimpleNamespace(
        seed=seed, observation=extractor.extract_assembly(seed.assembly)
    )


def scope(case, **changes):
    return {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": case.child.step_id,
    } | changes


def extract(case, *, current=None, **changes):
    return case.service.extract_chapter(
        current or case.case.frozen, **scope(case, **changes)
    )


def inspect_saved(case, *, service=None, current=None, **changes):
    return (service or case.service).inspect_extraction(
        current or case.case.frozen, **scope(case, **changes)
    )


def assert_observation_only(observation):
    assert type(observation) is ExtractionObservation
    assert observation.semantic_status == "UNKNOWN"
    assert observation.can_commit is False
    assert observation.can_issue_permit is False
    assert observation.can_dispatch is False
    assert observation.accepted is observation.published is False


def forbid_discovery(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Existing observations cannot rerun a discovery backend")

    monkeypatch.setattr(extractor, "extract_assembly", forbidden)
    monkeypatch.setattr("anovel.workflow.chapter.extract_assembly", forbidden)
    monkeypatch.setattr(extractor, "proposal_backend", forbidden)
    monkeypatch.setattr(extractor, "blind_inventory", forbidden)


def raw_discovery(text, *, catalog=CATALOG, backend=None):
    raw = text.encode()
    backend = backend or extractor.proposal_backend
    document = json.loads(backend(raw, catalog))
    assert document["prose_hash"] == sha256(raw).hexdigest()
    return document


def core_only_assembly(seed, second):
    """Untrusted structural input for pure core tests, not a genuine receipt.

    This deliberately changes an audit DTO, never the Store or real ledger.
    Only the original module seed is used for successful Workflow consumption.
    """
    child = seed.child
    result = child.result
    reply = replace(
        result.reply,
        response_body=canonical_bytes({"synthetic_core_only": second}),
        output_bytes=canonical_bytes({"text": second}),
    )
    result = replace(result, reply=reply)
    child = replace(child, result_bytes=result.to_bytes(), prose=second.encode())
    return ChapterAssembly(child)


def test_discovery_inputs_are_only_raw_prose_and_value_free_catalog():
    for function in (extractor.proposal_backend, extractor.blind_inventory):
        assert tuple(inspect.signature(function).parameters) == ("prose", "catalog")
    assert CATALOG[0].fact_id == eid("balance")
    assert set(CATALOG[0].to_dict()) == {"fact_id", "alias", "value_kind"}
    raw = "balance变为73。".encode()
    proposal = extractor.proposal_backend(raw, CATALOG)
    inventory = extractor.blind_inventory(raw, CATALOG)
    assert b"73" in proposal and b"73" in inventory
    with pytest.raises(TypeError):
        extractor.proposal_backend(raw, CATALOG, gold={"value": 30})


@pytest.mark.parametrize("value", [73, -4, 0])
def test_actual_values_are_discovered_without_an_expected_result(value):
    text = f"balance变为{value}。"
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, backend=backend)["segments"]
        assert len(segments) == 1
        assert segments[0]["kind"] == "ACTUAL"
        assert segments[0]["operation"] == "SET_FACT"
        assert segments[0]["fact_id"] == eid("balance").to_dict()
        assert segments[0]["value"] == value
        assert segments[0]["span"]["quote"] == text


@pytest.mark.parametrize(
    "text,kind",
    [
        ("听说" + ACTUAL, "RUMOR"),
        ("误信" + ACTUAL, "BELIEF"),
        ("并非" + ACTUAL, "NEGATED"),
        ("梦中" + ACTUAL, "DREAM"),
        ("计划" + ACTUAL, "PLANNED"),
        ("回忆" + ACTUAL, "RECOLLECTION"),
        ("引用：“" + ACTUAL + "”", "QUOTATION"),
    ],
)
def test_complete_context_wrappers_are_not_promoted_to_actual_events(text, kind):
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, backend=backend)["segments"]
        assert len(segments) == 1
        assert segments[0]["kind"] == kind
        assert segments[0]["span"]["quote"] == text
        assert segments[0]["fact_id"] == eid("balance").to_dict()


def test_repeated_identical_inner_quotes_retain_distinct_contexts_and_offsets():
    text = "听说" + ACTUAL + "\n并非" + ACTUAL + "\n" + ACTUAL
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, backend=backend)["segments"]
        claims = [item for item in segments if item["kind"] != "WHITESPACE"]
        assert [item["kind"] for item in claims] == ["RUMOR", "NEGATED", "ACTUAL"]
        assert [item["span"]["start"] for item in claims] == [
            0,
            len("听说" + ACTUAL + "\n"),
            len("听说" + ACTUAL + "\n并非" + ACTUAL + "\n"),
        ]


@pytest.mark.parametrize(
    "text",
    ["未知角色施展了无法识别的能力。", "unknown变为20。", "balance似乎也许变为20。"],
)
def test_out_of_profile_text_is_retained_as_unsupported(text):
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, backend=backend)["segments"]
        assert any(item["kind"] == "UNSUPPORTED" for item in segments)
        assert "".join(item["span"]["quote"] for item in segments) == text
        assert not any(item["kind"] == "ACTUAL" for item in segments)


def test_unicode_and_raw_bytes_are_never_normalized_or_mixed_with_codepoints():
    catalog = (FactAlias(eid("balance"), "账e\u0301🙂", ScalarKind.NUMBER),)
    text = "\ufeff\r\n账e\u0301🙂变为20。\r\n \t"
    raw = text.encode()
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, catalog=catalog, backend=backend)["segments"]
        cursor = 0
        for item in segments:
            span = item["span"]
            assert span["start"] == cursor
            assert text[span["start"] : span["end"]] == span["quote"]
            assert span["byte_start"] == len(text[: span["start"]].encode())
            assert span["byte_end"] == len(text[: span["end"]].encode())
            assert raw[span["byte_start"] : span["byte_end"]].decode() == span["quote"]
            cursor = span["end"]
        assert cursor == len(text)
        assert "".join(item["span"]["quote"] for item in segments) == text


def test_blind_inventory_is_sealed_before_proposal_and_detects_omitted_tail(
    extraction_case, monkeypatch
):
    seed = extraction_case.seed
    order = []
    inventory = extractor.blind_inventory
    producer = extractor.proposal_backend

    def recording_inventory(prose, catalog):
        order.append("inventory")
        return inventory(prose, catalog)

    def omit_tail(prose, catalog):
        assert order == ["inventory"]
        order.append("proposal")
        document = json.loads(producer(prose, catalog))
        document["segments"] = [
            item for item in document["segments"] if item["kind"] != "ACTUAL"
        ]
        return canonical_bytes(document)

    monkeypatch.setattr(extractor, "blind_inventory", recording_inventory)
    monkeypatch.setattr(extractor, "proposal_backend", omit_tail)
    result = extractor.extract_assembly(seed.assembly)
    assert order == ["inventory", "proposal"]
    assert_observation_only(result)
    assert result.correspondence_status == "FAIL"
    assert result.diagnostics


def test_multiple_transitions_and_net_zero_are_not_folded_into_one_delta(
    extraction_case,
):
    text = ACTUAL + "balance变为10。"
    for backend in (extractor.proposal_backend, extractor.blind_inventory):
        segments = raw_discovery(text, backend=backend)["segments"]
        assert [item["value"] for item in segments] == [20, 10]
    result = extractor.extract_assembly(core_only_assembly(extraction_case.seed, text))
    assert_observation_only(result)
    assert result.correspondence_status == "UNKNOWN"
    assert result.proposal_delta is None and result.operation_count == 0


def test_unsupported_tail_is_not_silent_zero_or_a_full_coverage_semantic_pass(
    extraction_case,
):
    second = ACTUAL + "未知角色施展了无法识别的能力。"
    result = extractor.extract_assembly(
        core_only_assembly(extraction_case.seed, second)
    )
    assert_observation_only(result)
    assert result.correspondence_status == "UNKNOWN"
    assert any(item.code for item in result.diagnostics)


def test_false_belief_is_retained_without_world_delta_or_knowledge_mutation(
    extraction_case,
):
    case = extraction_case
    assembly = core_only_assembly(case.seed, "误信" + ACTUAL)
    before_assembly = assembly.payload_bytes()
    before_store = dump_database(case.store_path)
    before_ledger = dump_database(case.ledger_path)
    result = extractor.extract_assembly(assembly)
    assert_observation_only(result)
    assert result.correspondence_status == "PASS"
    assert result.proposal_delta is None and result.operation_count == 0
    assert any(item.kind == "BELIEF" for item in result.coverage)
    assert result.assembly.payload_bytes() == before_assembly
    assert dump_database(case.store_path) == before_store
    assert dump_database(case.ledger_path) == before_ledger


@pytest.mark.parametrize(
    "fault,status",
    [
        ("missing", "FAIL"),
        ("wrong-hash", "ERROR"),
        ("wrong-quote", "ERROR"),
        ("byte-as-codepoint", "ERROR"),
        ("conflict", "ERROR"),
        ("self-pass", "ERROR"),
        ("wrong-context", "FAIL"),
    ],
)
def test_bad_missing_or_conflicting_proposal_cannot_self_authorize(
    observed_seed, fault, status
):
    original = observed_seed.observation
    proposal = json.loads(original.proposal_raw)
    actual = next(item for item in proposal["segments"] if item["kind"] == "ACTUAL")
    if fault == "missing":
        proposal["segments"].remove(actual)
    elif fault == "wrong-hash":
        proposal["prose_hash"] = "0" * 64
    elif fault == "wrong-quote":
        actual["span"]["quote"] = ACTUAL.replace("20", "21")
    elif fault == "byte-as-codepoint":
        actual["span"]["start"] = actual["span"]["byte_start"]
    elif fault == "conflict":
        proposal["segments"].append(dict(actual, value=99))
    elif fault == "self-pass":
        proposal.update(confidence=1.0, PASS=True, semantic_status="PASS")
    elif fault == "wrong-context":
        actual["kind"] = "RUMOR"
    result = extractor.reconcile(
        original.assembly,
        original.catalog,
        canonical_bytes(proposal),
        original.inventory_raw,
    )
    assert_observation_only(result)
    assert result.correspondence_status == status
    assert result.diagnostics
    assert result.proposal_delta is None
    assert (
        ExtractionObservation.from_bytes(result.payload_bytes()).record_hash
        == result.record_hash
    )


def test_full_span_no_change_paint_cannot_hide_a_supported_actual_tail(observed_seed):
    original = observed_seed.observation
    proposal = json.loads(original.proposal_raw)
    for item in proposal["segments"]:
        if item["kind"] == "ACTUAL":
            item.update(kind="QUIET", fact_id=None, operation=None, value=None)
    result = extractor.reconcile(
        original.assembly,
        original.catalog,
        canonical_bytes(proposal),
        original.inventory_raw,
    )
    assert result.correspondence_status == "FAIL"
    assert any(item.code == "PROPOSITION_MISMATCH" for item in result.diagnostics)


def test_split_negation_in_sealed_inventory_cannot_launder_an_actual_claim(
    observed_seed,
):
    assembly = core_only_assembly(observed_seed.seed, "并非" + ACTUAL)
    original = extractor.extract_assembly(assembly)
    inventory = json.loads(original.inventory_raw)
    original_segment = next(
        item for item in inventory["segments"] if item["kind"] == "NEGATED"
    )
    start = original_segment["span"]["start"]
    prefix = {
        "kind": "UNSUPPORTED",
        "span": extractor.ExactSpan.from_source(
            assembly.prose, start, start + 2
        ).to_dict(),
        "fact_id": None,
        "operation": None,
        "value": None,
    }
    actual = {
        "kind": "ACTUAL",
        "span": extractor.ExactSpan.from_source(
            assembly.prose, start + 2, original_segment["span"]["end"]
        ).to_dict(),
        "fact_id": eid("balance").to_dict(),
        "operation": "SET_FACT",
        "value": 20,
    }
    index = inventory["segments"].index(original_segment)
    inventory["segments"][index : index + 1] = [prefix, actual]
    forged = canonical_bytes(inventory)
    with pytest.raises(WorkflowError):
        extractor.reconcile(assembly, original.catalog, original.proposal_raw, forged)
    row = original.to_dict()
    row["inventory_raw_base64"] = b64encode(forged).decode()
    row["inventory_raw_hash"] = sha256(forged).hexdigest()
    with pytest.raises(WorkflowError):
        ExtractionObservation.from_dict(row)


def test_observation_hash_counts_and_permissions_are_derived_not_caller_claims(
    observed_seed,
):
    original = observed_seed.observation
    for field, value in (
        ("prose_hash", "0" * 64),
        ("assembly_hash", "0" * 64),
        ("source_id", eid("first-scene-not-whole-chapter").to_dict()),
        ("operation_count", 0),
        ("can_commit", True),
        ("can_issue_permit", True),
        ("can_dispatch", True),
        ("accepted", True),
        ("published", True),
        ("semantic_status", "PASS"),
        ("extra", "caller-grant"),
    ):
        row = original.to_dict()
        row[field] = value
        with pytest.raises(WorkflowError):
            ExtractionObservation.from_dict(row)


def test_real_whole_chapter_backend_extracts_text_not_contract_and_keeps_authority_false(
    extraction_case,
):
    case = extraction_case
    before_root = case.store.load(project=PROJECT, branch=BRANCH, run_id=RUN)
    before_ledger = dump_database(case.ledger_path)
    result = extract(case)
    assert_observation_only(result)
    assert result.correspondence_status == "PASS"
    assert result.operation_count == 1 and result.proposal_delta is not None
    operation = result.proposal_delta.operations[0]
    assert operation.meta.target_id == eid("balance")
    assert operation.value == 20
    assert case.child.source.contract.scenes[1].required[0].spec.value == 30
    assert (
        result.prose_hash
        == sha256(QUIET.encode() + b"\n\n" + ACTUAL.encode()).hexdigest()
    )
    assert result.assembly_hash == case.seed.assembly.record_hash
    assert result.proposal_delta.source_id == result.source_id
    assert result.source_id != case.child.source.contract.chapter_id
    assert case.store.load(project=PROJECT, branch=BRANCH, run_id=RUN) == before_root
    assert dump_database(case.ledger_path) == before_ledger
    assert case.seed.env.adapter.calls == 2


@pytest.mark.parametrize("extraction_case", [True], indirect=True)
def test_genuine_quiet_zero_observation_creates_neither_delta_nor_candidate(
    extraction_case, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Zero observations must not construct a Candidate")

    monkeypatch.setattr(ChapterCandidate, "__init__", forbidden)
    monkeypatch.setattr(NoChange, "__init__", forbidden)
    result = extract(extraction_case)
    assert_observation_only(result)
    assert result.correspondence_status == "PASS"
    assert result.operation_count == 0 and result.proposal_delta is None


def test_persistent_reopen_duplicate_and_inspect_do_not_reexecute_backend(
    extraction_case, monkeypatch
):
    case = extraction_case
    original = extract(case)

    forbid_discovery(monkeypatch)
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    restored = inspect_saved(case, service=reopened)
    duplicate = reopened.extract_chapter(case.case.frozen, **scope(case))
    assert (
        restored.payload_bytes()
        == duplicate.payload_bytes()
        == original.payload_bytes()
    )
    assert ExtractionObservation.from_bytes(original.payload_bytes()) == original
    assert case.seed.env.adapter.calls == 2


def test_creation_failure_after_commit_recovers_existing_observation_without_reexecution(
    extraction_case, monkeypatch
):
    case = extraction_case
    original = case.store.create_extraction
    recorded = []

    def after_commit(observation):
        created = original(observation)
        recorded.append(observation)
        if created:
            raise SimulatedProcessExit(
                "synthetic interruption after durable observation"
            )
        return created

    monkeypatch.setattr(case.store, "create_extraction", after_commit)
    with pytest.raises(SimulatedProcessExit):
        extract(case)
    assert len(recorded) == 1

    forbid_discovery(monkeypatch)
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    assert (
        inspect_saved(case, service=reopened).payload_bytes()
        == recorded[0].payload_bytes()
    )


def test_unpublished_failure_is_not_fabricated_by_inspect_and_explicit_extract_can_retry(
    extraction_case, monkeypatch
):
    case = extraction_case
    create = case.store.create_extraction

    def before_commit(_observation):
        raise SimulatedProcessExit("synthetic interruption before observation commit")

    monkeypatch.setattr(case.store, "create_extraction", before_commit)
    with pytest.raises(SimulatedProcessExit):
        extract(case)
    with pytest.raises(WorkflowError, match="EXTRACTION_OBSERVATION_UNAVAILABLE"):
        inspect_saved(case)
    monkeypatch.setattr(case.store, "create_extraction", create)
    result = extract(case)
    assert result.correspondence_status == "PASS"
    assert inspect_saved(case).record_hash == result.record_hash


@pytest.mark.parametrize(
    "changes",
    [{"project": "other-project"}, {"branch": "other-branch"}, {"run_id": "other-run"}],
)
def test_wrong_scope_never_returns_or_creates_an_observation(extraction_case, changes):
    before = dump_database(extraction_case.store_path)
    with pytest.raises(WorkflowError):
        extract(extraction_case, **changes)
    assert dump_database(extraction_case.store_path) == before


def test_changed_frozen_input_and_edited_source_reject_the_old_observation(
    extraction_case,
):
    case = extraction_case
    result = extract(case)
    row = case.case.frozen.to_dict()
    row["instructions"] += " altered immutable input"
    changed = FrozenChapterInput.from_dict(row)
    with pytest.raises(WorkflowError):
        inspect_saved(case, current=changed)
    edit(case, case.source, (QUIET + QUIET).encode())
    with pytest.raises(WorkflowError):
        inspect_saved(case)
    with pytest.raises(WorkflowError):
        extract(case)
    with sqlite3.connect(case.store_path) as connection:
        saved = connection.execute(
            "SELECT payload FROM extraction_observations"
        ).fetchone()[0]
    assert bytes(saved) == result.payload_bytes()


def test_corrupt_existing_observation_is_not_silently_reextracted(
    extraction_case, monkeypatch
):
    case = extraction_case
    extract(case)
    with sqlite3.connect(case.store_path) as connection:
        connection.execute("UPDATE extraction_observations SET payload=?", (b"{}",))

    forbid_discovery(monkeypatch)
    before = dump_database(case.store_path)
    with pytest.raises(WorkflowError):
        inspect_saved(case)
    with pytest.raises(WorkflowError):
        extract(case)
    assert dump_database(case.store_path) == before


@pytest.mark.parametrize("column", ["project", "branch", "assembly_hash"])
def test_damaged_existing_row_identity_is_corrupt_not_a_missing_reextract(
    extraction_case, monkeypatch, column
):
    case = extraction_case
    extract(case)
    value = "0" * 64 if column == "assembly_hash" else "wrong-scope"
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(f"UPDATE extraction_observations SET {column}=?", (value,))
    forbid_discovery(monkeypatch)
    before = dump_database(case.store_path)
    for operation in (extract, inspect_saved):
        with pytest.raises(WorkflowError, match="CORRUPT_EXTRACTION_OBSERVATION"):
            operation(case)
    assert dump_database(case.store_path) == before


def test_extraction_foreign_key_cascade_schema_is_rejected(extraction_case):
    case = extraction_case
    extract(case)
    with sqlite3.connect(case.store_path) as connection:
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='extraction_observations'"
        ).fetchone()[0]
        rows = connection.execute("SELECT * FROM extraction_observations").fetchall()
        connection.execute("DROP TABLE extraction_observations")
        altered = schema.rstrip().removesuffix(")") + " ON DELETE CASCADE)"
        connection.execute(altered)
        connection.executemany(
            "INSERT INTO extraction_observations VALUES(?,?,?,?,?,?,?)", rows
        )
    before = dump_database(case.store_path)
    with pytest.raises(WorkflowError, match="INVALID_EXTRACTION_SCHEMA"):
        inspect_saved(case)
    assert dump_database(case.store_path) == before


def test_task_and_actual_cli_execute_and_inspect_the_same_durable_observation(
    extraction_case, tmp_path
):
    case = extraction_case
    task = WorkflowTaskAdapter(case.service)
    request = {
        "operation": "EXTRACT_CHAPTER",
        "current_input": case.case.frozen.to_dict(),
        **scope(case),
    }
    result = task.execute(request)
    assert_observation_only(result)
    assert (
        task.execute(request | {"operation": "INSPECT_EXTRACTION"}).record_hash
        == result.record_hash
    )
    for field, value in (
        ("PASS", True),
        ("required", []),
        ("permit", "fake"),
        ("accepted", True),
    ):
        with pytest.raises(WorkflowError):
            task.execute(request | {field: value})
    input_path = tmp_path / "current-input.json"
    input_path.write_bytes(case.case.frozen.payload)
    for command in ("extract-chapter", "inspect-extraction"):
        completed = run_cli(
            case, command, "--input", input_path, "--step-id", case.child.step_id
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        summary = json.loads(completed.stdout)
        assert summary["record_hash"] == result.record_hash
        assert summary["accepted"] is summary["published"] is False
        assert QUIET not in completed.stdout and ACTUAL not in completed.stdout
    wrong = run_cli(
        case,
        "inspect-extraction",
        "--input",
        input_path,
        "--step-id",
        case.child.step_id,
        branch="wrong-branch",
    )
    assert wrong.returncode == 2 and result.record_hash not in wrong.stdout
    assert case.seed.env.adapter.calls == 2
