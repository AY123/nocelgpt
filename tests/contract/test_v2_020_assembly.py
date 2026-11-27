"""Exact two-scene offline assembly, not extraction, quality or acceptance.

Three real local Gateway/SQLite seeds are reused as immutable audit evidence.
Each control gets its own Workflow database backup while retaining the genuine
original ledger pin. No ledger is copied/re-signed and no fake receipt passes.
"""

import json
import os
import socket
import sqlite3
import stat
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_v2_017 import BRANCH, PROJECT, eid
from test_v2_020 import RUN, CountingLocalAdapter, harness, run_cli, start
from test_v2_020_scene import ENDING_TEXT, scene_case
from test_v2_020_scene_generation import CHILD_ATTEMPT, ready, start_child

from anovel.canon.identity import canonical_bytes
from anovel.context.scene import SceneDeltaBinding, SceneSpan
from anovel.gateway.ledger import BudgetLedger
from anovel.gateway.provider import OpenAIResponsesAdapter
from anovel.gateway.service import ModelGateway
from anovel.planning.models import ScenePlan
from anovel.planning.versions import PlanHistory, PlanVersion
from anovel.workflow import assembly_io
from anovel.workflow.assembly import ChapterAssembly
from anovel.workflow.chapter import ChapterWorkflow, FrozenChapterInput, WorkflowError
from anovel.workflow.interfaces import WorkflowTaskAdapter
from anovel.workflow.store import WorkflowStore

FIRST = (
    " \t第一场合成数据：余额仍为10，编号e\u0301🙂。\n" + ENDING_TEXT + " \t\n"
).encode()
SECOND = "第二场合成数据：核对来源后结束。 \t\n".encode()
JOINER = b"\n\n"
FILES = {"chapter.txt", "assembly.json", "manifest.json"}


@pytest.fixture(scope="module", autouse=True)
def no_network_or_provider_construction():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Assembly controls must not use a network or Provider")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(socket.socket, "connect", forbidden)
        patch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
        yield


def third_scene_case():
    case = scene_case()
    arc = case.fixture.vision.arcs[0]
    first = arc.chapters[0]
    vision = replace(
        case.fixture.vision,
        arcs=(
            replace(
                arc,
                chapters=(
                    replace(
                        first,
                        scenes=(
                            *first.scenes,
                            ScenePlan(
                                eid("assembly-third-scene"),
                                3,
                                "第三场尚未生成，不能冒称整章。",
                            ),
                        ),
                    ),
                    *arc.chapters[1:],
                ),
            ),
        ),
    )
    fixture = replace(case.fixture, vision=vision)
    history = PlanHistory(
        (PlanVersion(eid("plan"), 1, None, vision, fixture.content_hash),)
    )
    row = case.frozen.to_dict()
    row.update(fixture=fixture.to_dict(), history=history.to_dict())
    return SimpleNamespace(
        **(
            vars(case)
            | {
                "fixture": fixture,
                "history": history,
                "frozen": FrozenChapterInput.from_dict(row),
            }
        )
    )


def make_seed(directory, kind):
    if kind == "tail":
        case, env, source, projection = ready(directory)
    else:
        case = third_scene_case() if kind == "three" else scene_case()
        env = harness(
            directory, adapter=CountingLocalAdapter(output={"text": FIRST.decode()})
        )
        source = start(env, case)
        text = source.prose.decode()
        projection = env.workflow.project_scene(
            case.frozen,
            project=PROJECT,
            branch=BRANCH,
            run_id=RUN,
            expected_record_hash=source.record_hash,
            source_scene_id=source.contract.scenes[0].id,
            target_scene_id=source.contract.scenes[1].id,
            source_span=SceneSpan(0, len(text), text),
            ending_span=SceneSpan(
                text.index(ENDING_TEXT), len(text), text[text.index(ENDING_TEXT) :]
            ),
            delta_binding=SceneDeltaBinding(
                None, "synthetic-quiet-scene/not-human-review"
            ),
        )
    env.adapter.output = {"text": SECOND.decode()}
    original = env.store.publish_scene
    history = {}

    def recording(before, after, *, expected_parent_hash):
        if before.state == "DISPATCHING" and after.result_bytes is not None:
            history["unpublished"] = before
        return original(before, after, expected_parent_hash=expected_parent_hash)

    env.store.publish_scene = recording
    try:
        child = start_child(env, case, projection)
    finally:
        env.store.publish_scene = original
    assert child.state == "DRAFT_SAVED" and child.prose == SECOND
    assert env.adapter.calls == env.ledger.summary(RUN)["attempts"] == 2
    return SimpleNamespace(
        kind=kind,
        case=case,
        env=env,
        source=source,
        child=child,
        projection=projection,
        unpublished=history["unpublished"],
    )


@pytest.fixture(scope="module")
def seed_factory(tmp_path_factory):
    seeds = {}

    def get(kind):
        if kind not in seeds:
            seeds[kind] = make_seed(tmp_path_factory.mktemp("assembly-" + kind), kind)
        return seeds[kind]

    return get


def clone_workflow(seed, directory):
    database = directory / "workflow.sqlite"
    descriptor = os.open(database, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    original = sqlite3.connect(seed.env.store_path.as_uri() + "?mode=ro", uri=True)
    copied = sqlite3.connect(database)
    try:
        original.backup(copied)
    finally:
        copied.close()
        original.close()
    store = WorkflowStore(database)
    return SimpleNamespace(
        seed=seed,
        case=seed.case,
        source=seed.source,
        child=seed.child,
        store=store,
        service=ChapterWorkflow(store),
        store_path=database,
        ledger_path=seed.env.ledger_path,
    )


@pytest.fixture
def assembly_case(seed_factory, tmp_path, monkeypatch, request):
    seed = seed_factory(getattr(request, "param", "normal"))
    result = clone_workflow(seed, tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "Assembly may neither dispatch/recover nor initialize a budget"
        )

    monkeypatch.setattr(ModelGateway, "submit", forbidden)
    monkeypatch.setattr(ModelGateway, "recover", forbidden)
    monkeypatch.setattr(BudgetLedger, "__init__", forbidden)
    return result


def scope(case, **changes):
    return {
        "project": PROJECT,
        "branch": BRANCH,
        "run_id": RUN,
        "step_id": case.child.step_id,
    } | changes


def assemble(case, **changes):
    return case.service.assemble_chapter(case.case.frozen, **scope(case, **changes))


def verify(case, output, *, service=None):
    return (service or case.service).verify_chapter_export(
        case.case.frozen, output=output, **scope(case)
    )


def store_child(case, child):
    raw = child.payload_bytes()
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "UPDATE scene_generations SET payload=?,payload_hash=? WHERE run_id=? AND step_id=?",
            (raw, sha256(raw).hexdigest(), RUN, child.step_id),
        )


def bundle_snapshot(output):
    result = {}
    for item in output.iterdir():
        info = item.lstat()
        raw = item.read_bytes() if stat.S_ISREG(info.st_mode) else None
        result[item.name] = (info.st_mode, info.st_ino, info.st_mtime_ns, raw)
    return output.stat().st_mtime_ns, result


def export(case, output):
    artifact = assemble(case)
    case.service.export_chapter_assembly(case.case.frozen, artifact, output=output)
    return artifact


def edit(case, source, prose):
    return case.service.replace_draft(
        case.case.frozen,
        project=PROJECT,
        branch=BRANCH,
        run_id=RUN,
        expected_revision=source.revision,
        expected_prose_hash=source.prose_hash,
        prose=prose,
    )


def test_real_two_scene_assembly_preserves_sources_receipts_budget_and_pending_boundaries(
    assembly_case,
):
    case = assembly_case
    before = case.seed.env.ledger.summary(RUN)
    artifact = assemble(case)
    assert artifact.prose == FIRST + JOINER + SECOND
    assert artifact.child.record_hash == case.child.record_hash
    assert artifact.source_record_hash == case.source.record_hash
    assert artifact.assembly_policy == "EXACT_TWO_SCENE_CONCAT_V1"
    assert artifact.whole_chapter_delta == "NOT_EXTRACTED_NOT_VALIDATED"
    assert artifact.semantic_status == artifact.quality_status == "UNKNOWN"
    assert artifact.accepted is artifact.published is False
    assert (
        case.service.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).payload_bytes()
        == case.source.payload_bytes()
    )
    assert (
        case.store.load_scene(**scope(case)).payload_bytes()
        == case.child.payload_bytes()
    )
    assert case.seed.env.ledger.summary(RUN) == before
    assert case.seed.env.adapter.calls == 2


def test_unicode_and_byte_segments_preserve_combining_emoji_and_all_whitespace(
    assembly_case,
):
    artifact = assemble(assembly_case)
    pieces = [FIRST, JOINER, SECOND]
    segments = artifact.to_dict()["segments"]
    assert [v["kind"] for v in segments] == [
        "SOURCE_SCENE",
        "SEPARATOR",
        "GENERATED_SCENE",
    ]
    byte_end = unicode_end = 0
    for segment, raw in zip(segments, pieces, strict=True):
        assert segment["byte_start"] == byte_end
        assert segment["unicode_start"] == unicode_end
        byte_end += len(raw)
        unicode_end += len(raw.decode())
        assert segment["byte_end"] == byte_end
        assert segment["unicode_end"] == unicode_end
        assert segment["sha256"] == sha256(raw).hexdigest()
    assert len(FIRST) != len(FIRST.decode())
    assert artifact.prose.decode().startswith(" \t") and artifact.prose.endswith(
        b" \t\n"
    )


def test_deterministic_roundtrip_and_reopened_consumer_keep_same_assembly(
    assembly_case,
):
    case = assembly_case
    first = assemble(case)
    assert assemble(case).record_hash == first.record_hash
    restored = ChapterAssembly.from_bytes(first.payload_bytes())
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    assert (
        reopened.consume_chapter_assembly(case.case.frozen, restored).payload_bytes()
        == first.payload_bytes()
    )
    assert first.content_hash == sha256(first.payload_bytes()).hexdigest()


@pytest.mark.parametrize("assembly_case", ["tail", "three"], indirect=True)
def test_unselected_source_tail_or_unfinished_third_scene_cannot_become_whole_chapter(
    assembly_case,
):
    case = assembly_case
    with pytest.raises(WorkflowError, match="INVALID_CHAPTER_ASSEMBLY"):
        ChapterAssembly(case.child)
    with pytest.raises(WorkflowError, match="INVALID_CHAPTER_ASSEMBLY"):
        assemble(case)
    assert (
        case.service.inspect(project=PROJECT, branch=BRANCH, run_id=RUN).payload_bytes()
        == case.source.payload_bytes()
    )
    assert case.seed.env.adapter.calls == 2


def test_missing_persistent_child_is_not_replaced_by_existing_gateway_success(
    assembly_case,
):
    case = assembly_case
    with sqlite3.connect(case.store_path) as connection:
        connection.execute(
            "DELETE FROM scene_generations WHERE run_id=? AND step_id=?",
            (RUN, case.child.step_id),
        )
    with pytest.raises(WorkflowError, match="SCENE_GENERATION_UNAVAILABLE"):
        assemble(case)
    assert (
        case.seed.env.ledger.lookup(RUN, case.child.request.logical_id).status
        == "SUCCESS"
    )


def test_real_unpublished_child_cut_is_rejected_despite_finished_ledger_result(
    assembly_case,
):
    case = assembly_case
    store_child(case, case.seed.unpublished)
    assert case.store.load_scene(**scope(case)).state == "DISPATCHING"
    with pytest.raises(WorkflowError, match="CHAPTER_ASSEMBLY_NOT_READY"):
        assemble(case)
    assert (
        case.seed.env.ledger.lookup(RUN, case.child.request.logical_id).status
        == "SUCCESS"
    )


@pytest.mark.parametrize(
    "changed_scope", [{"project": "other-project"}, {"branch": "other-branch"}]
)
def test_wrong_scope_cannot_obtain_chapter_assembly(assembly_case, changed_scope):
    with pytest.raises(WorkflowError):
        assemble(assembly_case, **changed_scope)


@pytest.mark.parametrize("revert", [False, True])
def test_edit_and_revert_invalidate_old_assembly_and_export_without_removing_history(
    assembly_case, tmp_path, revert
):
    case = assembly_case
    saved = export(case, tmp_path / "old-bundle")
    before = bundle_snapshot(tmp_path / "old-bundle")
    edited = edit(case, case.source, case.source.prose + "\n明确人工修订。".encode())
    if revert:
        edited = edit(case, edited, case.source.prose)
        assert edited.prose_hash == case.source.prose_hash
    assert edited.record_hash != case.source.record_hash
    assert case.store.load_scene(**scope(case)).state == "STALE_SOURCE"
    with pytest.raises(WorkflowError):
        case.service.consume_chapter_assembly(case.case.frozen, saved)
    output = tmp_path / "stale-new-bundle"
    with pytest.raises(WorkflowError):
        case.service.export_chapter_assembly(case.case.frozen, saved, output=output)
    with pytest.raises(WorkflowError):
        verify(case, tmp_path / "old-bundle")
    assert not output.exists() and bundle_snapshot(tmp_path / "old-bundle") == before


def test_pure_assembly_rejects_false_hash_segment_or_acceptance_claims(assembly_case):
    artifact = assemble(assembly_case)
    for fault in ("prose_hash", "segments", "accepted"):
        row = artifact.to_dict()
        if fault == "prose_hash":
            row["prose_hash"] = "0" * 64
        elif fault == "segments":
            row["segments"][0]["byte_end"] += 1
        else:
            row["accepted"] = True
        with pytest.raises(WorkflowError, match="INVALID_CHAPTER_ASSEMBLY"):
            ChapterAssembly.from_bytes(canonical_bytes(row))


def test_self_consistent_resigned_child_and_row_hash_cannot_fake_real_gateway_receipt(
    assembly_case, tmp_path
):
    case = assembly_case
    forged_prose = "自洽伪造的第二场正文，真实账本从未返回它。".encode()
    reply = replace(
        case.child.result.reply,
        response_body=canonical_bytes({"synthetic-forged": True}),
        output_bytes=canonical_bytes({"text": forged_prose.decode()}),
    )
    result = replace(case.child.result, reply=reply)
    forged = replace(case.child, result_bytes=result.to_bytes(), prose=forged_prose)
    artifact = ChapterAssembly(forged)
    assert artifact.prose.endswith(
        forged_prose
    )  # Structure alone is deliberately insufficient.
    store_child(case, forged)
    assert case.store.load_scene(**scope(case)).record_hash == forged.record_hash
    with pytest.raises(WorkflowError, match="SCENE_RECEIPT_MISMATCH"):
        assemble(case)
    with pytest.raises(WorkflowError, match="SCENE_RECEIPT_MISMATCH"):
        case.service.consume_chapter_assembly(case.case.frozen, artifact)
    with pytest.raises(WorkflowError, match="SCENE_RECEIPT_MISMATCH"):
        case.service.export_chapter_assembly(
            case.case.frozen, artifact, output=tmp_path / "forged"
        )
    assert not (tmp_path / "forged").exists()


def test_missing_actual_child_receipt_blocks_assembly_without_recovery_or_mutation(
    assembly_case,
):
    case = assembly_case
    with sqlite3.connect(case.ledger_path) as connection:
        original = connection.execute(
            "SELECT result_record FROM attempts WHERE run_id=? AND attempt_id=?",
            (RUN, CHILD_ATTEMPT),
        ).fetchone()[0]
        connection.execute(
            "UPDATE attempts SET result_record=NULL WHERE run_id=? AND attempt_id=?",
            (RUN, CHILD_ATTEMPT),
        )
    try:
        with pytest.raises(WorkflowError, match="SCENE_RECEIPT_UNAVAILABLE"):
            assemble(case)
        with sqlite3.connect(case.ledger_path) as connection:
            assert connection.execute(
                "SELECT state,result_record FROM attempts WHERE run_id=? AND attempt_id=?",
                (RUN, CHILD_ATTEMPT),
            ).fetchone() == ("FINISHED", None)
    finally:
        with sqlite3.connect(case.ledger_path) as connection:
            connection.execute(
                "UPDATE attempts SET result_record=? WHERE run_id=? AND attempt_id=?",
                (original, RUN, CHILD_ATTEMPT),
            )


def test_new_private_bundle_is_verified_after_reopen_without_rewriting_any_files(
    assembly_case, tmp_path
):
    case = assembly_case
    output = tmp_path / "bundle"
    artifact = export(case, output)
    assert {v.name for v in output.iterdir()} == FILES
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    for file in output.iterdir():
        assert stat.S_IMODE(file.stat().st_mode) == 0o600 and file.stat().st_nlink == 1
    assert (output / "chapter.txt").read_bytes() == artifact.prose
    assert (output / "assembly.json").read_bytes() == artifact.payload_bytes()
    manifest = json.loads((output / "manifest.json").read_bytes())
    assert (
        manifest["assembly_hash"] == artifact.record_hash
        and manifest["accepted"] is False
    )
    before = bundle_snapshot(output)
    reopened = ChapterWorkflow(WorkflowStore(case.store_path))
    assert verify(case, output, service=reopened).record_hash == artifact.record_hash
    assert verify(case, output).record_hash == artifact.record_hash
    assert bundle_snapshot(output) == before


@pytest.mark.parametrize("filename", ["chapter.txt", "assembly.json", "manifest.json"])
def test_tampered_bundle_is_rejected_and_never_repaired_from_expected_content(
    assembly_case, tmp_path, filename
):
    case = assembly_case
    output = tmp_path / "bundle"
    export(case, output)
    if filename == "chapter.txt":
        raw = b"changed-self-signed-chapter"
        (output / filename).write_bytes(raw)
        manifest = json.loads((output / "manifest.json").read_bytes())
        manifest["files"][filename] = {
            "sha256": sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
        (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    else:
        (output / filename).write_bytes(b"tampered-synthetic-bundle")
    before = bundle_snapshot(output)
    with pytest.raises(WorkflowError):
        verify(case, output)
    assert bundle_snapshot(output) == before


@pytest.mark.parametrize("fault", ["missing-manifest", "extra", "symlink", "fifo"])
def test_incomplete_or_nonregular_bundle_never_gains_completion_from_manifest(
    assembly_case, tmp_path, fault
):
    case = assembly_case
    output = tmp_path / "bundle"
    export(case, output)
    if fault == "missing-manifest":
        (output / "manifest.json").unlink()
    elif fault == "extra":
        (output / "unknown.txt").write_bytes(b"unregistered-owned-test-data")
    else:
        target = output / "chapter.txt"
        target.unlink()
        if fault == "symlink":
            outside = tmp_path / "outside.txt"
            outside.write_bytes(b"outside-owned-test-data")
            target.symlink_to(outside)
        else:
            os.mkfifo(target, 0o600)
    before = bundle_snapshot(output)
    if fault == "fifo":
        current = tmp_path / "current.json"
        current.write_bytes(case.case.frozen.payload)
        result = subprocess.run(
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
                "verify-chapter",
                "--input",
                str(current),
                "--step-id",
                case.child.step_id,
                "--output",
                str(output),
            ],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 2, result.stdout + result.stderr
    else:
        with pytest.raises(WorkflowError):
            verify(case, output)
    assert bundle_snapshot(output) == before


def test_existing_reserved_and_alias_output_paths_are_preserved(
    assembly_case, tmp_path
):
    case = assembly_case
    artifact = assemble(case)
    output = tmp_path / "existing"
    output.mkdir(mode=0o700)
    (output / "owner-data").write_bytes(b"preserve-existing-output")
    before = bundle_snapshot(output)
    with pytest.raises(WorkflowError):
        case.service.export_chapter_assembly(case.case.frozen, artifact, output=output)
    assert bundle_snapshot(output) == before
    paths = [
        case.store_path.with_name(case.store_path.name + "-journal"),
        case.ledger_path.with_name(case.ledger_path.name + "-journal"),
        case.store.lock_directory / "forbidden-bundle",
    ]
    for target in paths:
        assert not target.exists()
        with pytest.raises(WorkflowError, match="ASSEMBLY_BUNDLE_RESERVED_PATH"):
            case.service.export_chapter_assembly(
                case.case.frozen, artifact, output=target
            )
        assert not target.exists()
    alias = tmp_path / "alias"
    alias.symlink_to(output, target_is_directory=True)
    with pytest.raises(WorkflowError):
        case.service.export_chapter_assembly(
            case.case.frozen, artifact, output=alias / "new-bundle"
        )
    assert not (output / "new-bundle").exists()


def test_failed_completion_marker_keeps_partial_export_and_requires_new_output(
    assembly_case, tmp_path, monkeypatch
):
    case = assembly_case
    artifact = assemble(case)
    original = assembly_io._write_file

    def interrupted(directory, name, raw):
        if name == "manifest.json":
            raise OSError("synthetic interruption before completion marker")
        return original(directory, name, raw)

    monkeypatch.setattr(assembly_io, "_write_file", interrupted)
    output = tmp_path / "partial"
    with pytest.raises(WorkflowError):
        case.service.export_chapter_assembly(case.case.frozen, artifact, output=output)
    monkeypatch.setattr(assembly_io, "_write_file", original)
    assert {v.name for v in output.iterdir()} == {"chapter.txt", "assembly.json"}
    before = bundle_snapshot(output)
    with pytest.raises(WorkflowError):
        verify(case, output)
    with pytest.raises(WorkflowError):
        case.service.export_chapter_assembly(case.case.frozen, artifact, output=output)
    assert bundle_snapshot(output) == before


def test_task_and_actual_cli_assemble_export_verify_use_the_same_application(
    assembly_case, tmp_path
):
    case = assembly_case
    task = WorkflowTaskAdapter(case.service)
    request = {
        "operation": "ASSEMBLE_CHAPTER",
        "current_input": case.case.frozen.to_dict(),
        **scope(case),
    }
    artifact = task.execute(request)
    assert artifact.prose == FIRST + JOINER + SECOND
    with pytest.raises(WorkflowError):
        task.execute(request | {"accepted": True})
    input_path = tmp_path / "current.json"
    input_path.write_bytes(case.case.frozen.payload)
    output = tmp_path / "cli-bundle"
    commands = [
        ("assemble", "--input", input_path, "--step-id", case.child.step_id),
        (
            "export-chapter",
            "--input",
            input_path,
            "--step-id",
            case.child.step_id,
            "--expected-assembly-hash",
            artifact.record_hash,
            "--output",
            output,
        ),
        (
            "verify-chapter",
            "--input",
            input_path,
            "--step-id",
            case.child.step_id,
            "--output",
            output,
        ),
    ]
    for command in commands:
        result = run_cli(case, *command)
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads(result.stdout)
        assert summary["record_hash"] == artifact.record_hash
        assert summary["state"] == "DRAFT_ASSEMBLED"
        assert summary["accepted"] is summary["published"] is False
        assert (
            FIRST.decode() not in result.stdout and SECOND.decode() not in result.stdout
        )
    assert verify(case, output).record_hash == artifact.record_hash
    wrong = run_cli(
        case,
        "export-chapter",
        "--input",
        input_path,
        "--step-id",
        case.child.step_id,
        "--expected-assembly-hash",
        "0" * 64,
        "--output",
        tmp_path / "wrong-hash",
    )
    assert wrong.returncode == 2 and not (tmp_path / "wrong-hash").exists()
    assert case.seed.env.adapter.calls == 2
