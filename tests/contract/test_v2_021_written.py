"""Exercise V2-021 against versioned drafts saved through the Writer store."""

import json
from hashlib import sha256

import pytest
from test_v2_017 import BRANCH, PROJECT
from test_v2_020 import RUN, _written_draft_setup, policy_for

import anovel.workflow.__main__ as workflow_cli
from anovel.canon.identity import canonical_bytes
from anovel.gateway.service import ModelGateway
from anovel.workflow import extractor
from anovel.workflow.chapter import ChapterWorkflow, WorkflowError
from anovel.workflow.interfaces import WorkflowTaskAdapter, snapshot_summary
from anovel.workflow.store import WorkflowStore
from anovel.workflow.written_draft import WrittenDraftRevision

SOURCE = (
    "听说balance变为77。\r\n"
    "误信balance变为66。\r\n"
    "计划balance变为55。\r\n"
    "灯牌上的月亮🌙e\u0301还亮着。\r\n"
    "balance变为21。"
)
AUTHORITY = ("can_commit", "can_dispatch", "can_issue_permit", "accepted", "published")


@pytest.fixture
def saved_chapter(tmp_path, monkeypatch):
    current, store, root, _, (_, chapter2, _) = _written_draft_setup(
        tmp_path,
        monkeypatch,
        "从上一章接起。",
        template_version="local-written-extraction",
    )
    revision = store.append_written_draft(
        WrittenDraftRevision(
            chapter_id=chapter2.id,
            chapter_number=chapter2.number,
            branch=BRANCH,
            run_id=RUN,
            input_hash=current.content_hash,
            source_chapter_id=root.chapter_id,
            source_revision_hash=root.record_hash,
            writer_input_hash="4" * 64,
            version=1,
            previous_revision_hash=None,
            prose=SOURCE.encode(),
        )
    )
    scope = {"project": PROJECT, "branch": BRANCH, "run_id": RUN}
    workflow = ChapterWorkflow(store)
    _, root_observation = workflow._current_chapter_revision(current, **scope)
    root_observation.assembly.child.source = store.load(**scope)

    def retained_root(_store, **lookup):
        assert lookup == scope | {
            "chapter_id": root.chapter_id,
            "source_revision_hash": root.record_hash,
            "retained_step_id": None,
        }
        return root_observation

    monkeypatch.setattr(WorkflowStore, "load_retained_root_observation", retained_root)

    def forbidden(*_args, **_kwargs):
        pytest.fail(
            "Inspecting drafts and preparing an input must not dispatch a model"
        )

    monkeypatch.setattr(ModelGateway, "submit", forbidden)
    request = scope | {
        "current_input": current.to_dict(),
        "chapter_id": chapter2.id.to_dict(),
        "expected_revision_hash": revision.record_hash,
    }
    return current, store, revision, WorkflowTaskAdapter(workflow), request


def test_written_extraction_task_and_cli_bind_every_quote_to_the_saved_source(
    saved_chapter, tmp_path, capsys
):
    current, store, revision, task, request = saved_chapter
    before = store.path.read_bytes()
    inspect = request | {"operation": "INSPECT_WRITTEN_DRAFT_EXTRACTION"}
    report = task.execute(inspect)
    summary = snapshot_summary(report)
    assert summary["source_revision_hash"] == revision.record_hash
    assert summary["prose_hash"] == sha256(revision.prose).hexdigest()
    assert summary["semantic_status"] == "UNKNOWN"
    assert summary["version"] == 1
    assert all(summary[key] is False for key in AUTHORITY)
    assert [(segment.kind, segment.value) for segment in report.facts] == [
        ("ACTUAL", 21)
    ]
    assert {segment.kind for segment in report.coverage} >= {
        "ACTUAL",
        "RUMOR",
        "BELIEF",
        "PLANNED",
        "UNSUPPORTED",
        "WHITESPACE",
    }
    spans = [segment.span for segment in report.coverage]
    assert "".join(span.quote for span in spans) == SOURCE
    byte_cursor = 0
    for span in spans:
        assert span.byte_start == byte_cursor
        assert revision.prose[span.byte_start : span.byte_end] == span.quote.encode()
        assert SOURCE[span.start : span.end] == span.quote
        byte_cursor = span.byte_end
    assert byte_cursor == len(revision.prose)

    current_path = tmp_path / "current.json"
    current_path.write_bytes(current.payload)
    output = tmp_path / "extraction.json"
    cli = [
        "--db",
        str(store.path),
        "--project",
        PROJECT,
        "--branch",
        BRANCH,
        "--run-id",
        RUN,
        "inspect-written-draft-extraction",
        "--input",
        str(current_path),
        "--chapter-id",
        revision.chapter_id.local_id,
        "--expected-revision-hash",
        revision.record_hash,
        "--output",
        str(output),
    ]
    assert workflow_cli.main(cli) == 0
    displayed = capsys.readouterr().out
    assert json.loads(displayed) == summary
    assert SOURCE not in displayed and "balance变为21" not in displayed
    assert output.read_bytes() == report.payload_bytes()
    assert output.stat().st_mode & 0o777 == 0o600
    for invalid in ({"version": True}, {"can_commit": True}, {"quote": "任意内容。"}):
        with pytest.raises(WorkflowError, match="^INVALID_WORKFLOW_TASK_REQUEST$"):
            task.execute(inspect | invalid)
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(inspect | {"expected_revision_hash": "a" * 64})
    assert store.path.read_bytes() == before


def test_revision_refreshes_model_input_and_preserves_archived_evidence(
    saved_chapter, tmp_path
):
    current, store, revision, task, request = saved_chapter
    inspect = request | {"operation": "INSPECT_WRITTEN_DRAFT_EXTRACTION"}
    original = task.execute(inspect)
    scope = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "source_chapter_id": revision.chapter_id,
    }
    original_handoff = task.service.next_chapter_draft_input(
        current, **scope, expected_revision_hash=revision.record_hash
    )
    revised = task.execute(
        request
        | {
            "operation": "EDIT_WRITTEN_DRAFT",
            "text": SOURCE.replace("balance变为21。", "balance变为32。"),
            "choice": None,
        }
    )
    after_edit = store.path.read_bytes()
    assert revised.version == 2
    assert revised.prose_hash != revision.prose_hash
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(inspect)
    renewed = task.execute(inspect | {"expected_revision_hash": revised.record_hash})
    historical = task.execute(inspect | {"version": 1})
    assert historical.payload_bytes() == original.payload_bytes()
    assert [item.value for item in renewed.facts] == [32]
    assert [item.value for item in historical.facts] == [21]
    with pytest.raises(WorkflowError, match="^CHAPTER_REVISION_CHANGED$"):
        task.execute(
            inspect | {"version": 1, "expected_revision_hash": revised.record_hash}
        )

    selection = scope | {"expected_revision_hash": revised.record_hash}
    output = tmp_path / "next-chapter-model-request.json"
    with pytest.raises(WorkflowError, match="^NEXT_CHAPTER_INPUT_CHANGED$"):
        task.service.prepare_next_chapter_model_request(
            current,
            **selection,
            retained_payload=original_handoff.payload_bytes(),
            policy=policy_for(),
            output=output,
        )
    assert not output.exists()
    handoff = task.service.next_chapter_draft_input(current, **selection)
    prepared = task.service.prepare_next_chapter_model_request(
        current,
        **selection,
        retained_payload=handoff.payload_bytes(),
        policy=policy_for(),
        output=output,
    )
    writer = next(
        item["content"]
        for item in json.loads(prepared.context.model_bytes)["items"]
        if item["kind"] == "DRAFT_HANDOFF"
    )
    writer_source = next(
        item.source_ref
        for item in prepared.context.items
        if item.kind == "DRAFT_HANDOFF"
    )
    assert writer_source == f"{revised.chapter_id.local_id}@{revised.record_hash}"
    assert writer["handoff"]["ending"]["quote"].endswith("balance变为32。")
    assert writer["observed_draft_facts"] == [renewed.facts[0].to_dict()]
    assert store.path.read_bytes() == after_edit


@pytest.mark.parametrize(
    ("fault", "diagnostic", "state"),
    [
        ("omission", "MISSING_PROPOSITION", "FAIL"),
        ("contradiction", "PROPOSITION_MISMATCH", "FAIL"),
        ("bad-position", "PROPOSAL_RESULT_INVALID", "ERROR"),
    ],
)
def test_written_extraction_rejects_unsubstantiated_proposal_evidence(
    saved_chapter, monkeypatch, tmp_path, fault, diagnostic, state
):
    current, store, revision, task, request = saved_chapter
    before = store.path.read_bytes()
    proposal = extractor.proposal_backend
    inventory = extractor.blind_inventory
    observed = []

    def inventory_first(prose, catalog):
        observed.append("inventory")
        return inventory(prose, catalog)

    def corrupted_proposal(prose, catalog):
        assert observed == ["inventory"]
        observed.append("proposal")
        document = json.loads(proposal(prose, catalog))
        segments = document["segments"]
        tail = segments[-1]
        assert tail["span"]["quote"] == "balance变为21。"
        if fault == "omission":
            segments.pop()
        elif fault == "contradiction":
            tail["value"] = 999
        else:
            tail["span"]["start"] -= 1
        return canonical_bytes(document)

    monkeypatch.setattr(extractor, "blind_inventory", inventory_first)
    monkeypatch.setattr(extractor, "proposal_backend", corrupted_proposal)
    report = task.execute(request | {"operation": "INSPECT_WRITTEN_DRAFT_EXTRACTION"})
    assert observed == ["inventory", "proposal"]
    assert not report.facts
    finding = next(item for item in report.diagnostics if item.code == diagnostic)
    assert finding.state == state
    if fault == "omission":
        assert finding.span.quote == "balance变为21。"
        assert finding.span.byte_end == len(revision.prose)
    summary = snapshot_summary(report)
    assert all(summary[key] is False for key in AUTHORITY)
    assert summary["semantic_status"] == "UNKNOWN"
    assert summary["correspondence_status"] == state
    observed.clear()
    selection = {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "source_chapter_id": revision.chapter_id,
        "expected_revision_hash": revision.record_hash,
    }
    handoff = task.service.next_chapter_draft_input(current, **selection)
    output = tmp_path / "unreconciled-request.json"
    with pytest.raises(WorkflowError, match="^WRITTEN_DRAFT_EXTRACTION_UNRECONCILED$"):
        task.service.prepare_next_chapter_model_request(
            current,
            **selection,
            retained_payload=handoff.payload_bytes(),
            policy=policy_for(),
            output=output,
        )
    assert observed == ["inventory", "proposal"]
    assert not output.exists()
    assert store.path.read_bytes() == before
