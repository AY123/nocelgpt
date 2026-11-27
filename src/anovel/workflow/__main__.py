"""Inspect, edit, export or recover offline Drafts; this CLI cannot dispatch."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
from pathlib import Path

from anovel.canon.identity import decode_canonical
from anovel.gateway.ledger import BudgetLedger, DispatchPermit
from anovel.gateway.models import (
    GatewayRequest,
    ModelPolicy,
    ProviderReply,
)
from anovel.gateway.provider import strict_json
from anovel.gateway.service import ModelGateway

from .assembly import ChapterAssembly
from .chapter import ChapterWorkflow, KimiDraftWriter, OpenAIDraftWriter
from .gateway_binding import existing_gateway_ledger, verify_scene_ledger
from .interfaces import WorkflowTaskAdapter, snapshot_summary
from .models import WorkflowError
from .openai_settings import check_openai_env
from .scene import SceneProjection
from .store import WorkflowStore

_CHAPTER_RECEIPT_OPERATIONS = {
    "recover-next-chapter-kimi",
    "recover-next-chapter-openai",
}

_REVISION_SCHEMA_CHECKS = (
    ("chapter_revisions", "extraction_observations", "_chapter_revision_table"),
    ("revision_q0_executions", "chapter_revisions", "_revision_q0_table"),
    ("revision_q123_executions", "chapter_revisions", "_revision_q123_table"),
    ("written_draft_revisions", "runs", "_written_draft_table"),
)


class _RecoveryOnly:
    def send(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None = None,
    ) -> ProviderReply:
        raise WorkflowError("CLI_PROVIDER_DISPATCH_FORBIDDEN")


def _regular_input_bytes(path: Path, diagnostic: str) -> bytes:
    """Freeze regular data bytes, refusing FIFO/device/link inputs without waiting."""
    descriptor = os.open(
        path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    )
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise WorkflowError(diagnostic)
        return stream.read()


def _canonical_input(path: Path, diagnostic: str) -> object:
    try:
        return decode_canonical(_regular_input_bytes(path, diagnostic))
    except (OSError, ValueError):
        raise WorkflowError(diagnostic) from None


def _scene_fact_edits_input(path: Path) -> dict[str, object]:
    diagnostic = "INVALID_SCENE_FACT_EDITS_FILE"
    try:
        selection = strict_json(_regular_input_bytes(path, diagnostic))
    except (OSError, ValueError):
        raise WorkflowError(diagnostic) from None
    if set(selection) != {"fact_edits"}:
        raise WorkflowError(diagnostic)
    return selection


def _q1_input_bytes(path: Path) -> bytes:
    return _regular_input_bytes(path, "INVALID_Q1_INPUT_FILE")


def _q2_input_bytes(path: Path) -> bytes:
    return _regular_input_bytes(path, "INVALID_Q2_INPUT_FILE")


def _q3_input_bytes(path: Path) -> bytes:
    return _regular_input_bytes(path, "INVALID_Q3_INPUT_FILE")


def _require_existing_run(
    path: Path,
    project: str,
    branch: str,
    run_id: str,
    *,
    accept_revision_tables: bool = False,
) -> None:
    """Refuse unavailable inspection inputs before the provisioning constructor.

    This preflight is a cooperative local check, not an atomic protection against
    the same owner replacing the database between this read and Store validation.
    """
    if not path.with_name(path.name + ".locks").is_dir():
        raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
    # mode=ro alone can create WAL/SHM files. The existing Store uses rollback
    # journaling; refuse WAL or a pending journal instead of repairing it here.
    with path.open("rb") as stream:
        if stream.read(20)[18:20] != b"\x01\x01":
            raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
    if any(
        candidate.exists() or candidate.is_symlink()
        for candidate in (
            path.with_name(path.name + suffix)
            for suffix in ("-journal", "-wal", "-shm")
        )
    ):
        raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
    try:
        connection = sqlite3.connect(
            path.absolute().as_uri() + "?mode=ro&immutable=1", uri=True
        )
        try:
            internal_pattern = r"sqlite\_%" if accept_revision_tables else "sqlite_%"
            names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE ? ESCAPE '\\'",
                    (internal_pattern,),
                )
            }
            revision_tables = {
                table: (parent, method)
                for table, parent, method in _REVISION_SCHEMA_CHECKS
                if accept_revision_tables and table in names
            }
            if names - revision_tables.keys() not in (
                {"runs"},
                {"runs", "scene_generations"},
                {"runs", "scene_generations", "extraction_observations"},
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q1_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q1_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q2_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q2_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q1_executions",
                    "q2_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q1_executions",
                    "q2_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q1_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q2_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q1_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q2_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q1_executions",
                    "q2_executions",
                    "q3_executions",
                },
                {
                    "runs",
                    "scene_generations",
                    "extraction_observations",
                    "q0_executions",
                    "q1_executions",
                    "q2_executions",
                    "q3_executions",
                },
            ):
                raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
            row = connection.execute(
                "SELECT 1 FROM runs WHERE project=? AND branch=? AND run_id=?",
                (project, branch, run_id),
            ).fetchone()
            if row is None:
                raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
            if revision_tables:
                connection.row_factory = sqlite3.Row
                columns = connection.execute("PRAGMA table_info(runs)").fetchall()
                if [(column["name"], column["type"].upper()) for column in columns] != [
                    ("run_id", "TEXT"),
                    ("project", "TEXT"),
                    ("branch", "TEXT"),
                    ("payload", "BLOB"),
                    ("payload_hash", "TEXT"),
                ] or columns[0]["pk"] != 1:
                    raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
                if revision_tables.keys() - {"written_draft_revisions"} and (
                    not WorkflowStore._scene_table(connection, create=False)
                    or not WorkflowStore._extraction_table(connection, create=False)
                ):
                    raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
                for parent, method in revision_tables.values():
                    validate = getattr(WorkflowStore, method, None)
                    if (
                        parent not in names
                        or not callable(validate)
                        or not validate(connection, create=False)
                    ):
                        raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
        finally:
            connection.close()
    except (sqlite3.Error, WorkflowError):
        raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--draft-handoff-step-id", help="Explicit assembled Draft root for handoff"
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("inspect")
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    edit = commands.add_parser("replace")
    edit.add_argument("--input", type=Path, required=True)
    edit.add_argument("--prose", type=Path, required=True)
    edit.add_argument("--expected-revision", type=int, required=True)
    edit.add_argument("--expected-prose-hash", required=True)
    edit.add_argument(
        "--fact-edits", type=Path, help="Validate scene fact edits before saving"
    )
    edit.add_argument(
        "--projection-output",
        type=Path,
        help="Save a private second-scene projection with --fact-edits",
    )
    recover = commands.add_parser("recover")
    recover.add_argument("--input", type=Path, required=True)
    recover.add_argument("--gateway-ledger", type=Path, required=True)
    scene_inspect = commands.add_parser("inspect-scene")
    scene_inspect.add_argument("--step-id", required=True)
    scene_recover = commands.add_parser("recover-scene")
    scene_recover.add_argument("--step-id", required=True)
    scene_recover.add_argument("--input", type=Path, required=True)
    scene_recover.add_argument("--gateway-ledger", type=Path, required=True)
    scene_project = commands.add_parser("project-scene")
    scene_project.add_argument("--input", type=Path, required=True)
    scene_project.add_argument("--expected-record-hash", required=True)
    scene_selection = scene_project.add_mutually_exclusive_group(required=True)
    scene_selection.add_argument(
        "--selection",
        type=Path,
        help="Exact scene spans and delta binding",
    )
    scene_selection.add_argument(
        "--delta-binding",
        type=Path,
        help="Use the saved first scene and its last paragraph with this fact binding",
    )
    scene_selection.add_argument(
        "--fact-edits",
        type=Path,
        help="Bind exact first-scene quotes and new values to the current draft",
    )
    scene_project.add_argument("--output", type=Path, required=True)
    inspect_revision = commands.add_parser("inspect-chapter-revision")
    inspect_revision.add_argument("--input", type=Path, required=True)
    export_revision = commands.add_parser("export-chapter-revision")
    export_revision.add_argument("--input", type=Path, required=True)
    export_revision.add_argument("--expected-revision-hash", required=True)
    export_revision.add_argument("--output", type=Path, required=True)
    for name in (
        "project-next-chapter",
        "verify-next-chapter",
        "prepare-next-chapter-model-request",
        *sorted(_CHAPTER_RECEIPT_OPERATIONS),
    ):
        next_chapter = commands.add_parser(name)
        next_chapter.add_argument("--input", type=Path, required=True)
        next_chapter.add_argument("--expected-revision-hash", required=True)
        next_chapter.add_argument("--source-chapter-id")
        if name != "verify-next-chapter":
            next_chapter.add_argument("--output", type=Path, required=True)
        if name != "project-next-chapter":
            next_chapter.add_argument("--handoff", type=Path, required=True)
        if name == "prepare-next-chapter-model-request":
            next_chapter.add_argument(
                "--policy", type=Path, required=True, help="Canonical ModelPolicy JSON"
            )
            next_chapter.add_argument(
                "--brief", type=Path, help="Canonical DraftChapterBrief JSON"
            )
            next_chapter.add_argument(
                "--openai-env",
                type=Path,
                help="Match the policy to the local OpenAI selections",
            )
        elif name in _CHAPTER_RECEIPT_OPERATIONS:
            next_chapter.add_argument(
                "--brief",
                type=Path,
                required=True,
                help="Canonical DraftChapterBrief JSON",
            )
            next_chapter.add_argument(
                "--request", type=Path, required=True, help="Frozen GatewayRequest JSON"
            )
            next_chapter.add_argument(
                "--writer-ledger",
                type=Path,
                required=True,
                help="Absolute path to the existing private writer ledger",
            )
    inspect_impact = commands.add_parser(
        "inspect-written-draft-impact", help="List downstream Drafts needing rewrite"
    )
    inspect_impact.add_argument("--input", type=Path, required=True)
    inspect_impact.add_argument("--source-chapter-id", required=True)
    inspect_impact.add_argument("--expected-revision-hash", required=True)
    review_commitments = commands.add_parser(
        "review-written-draft-commitments",
        help="Review what the current Draft does with inherited open commitments",
    )
    review_commitments.add_argument("--input", type=Path, required=True)
    review_commitments.add_argument("--chapter-id", required=True)
    review_commitments.add_argument("--expected-revision-hash", required=True)
    review_commitments.add_argument(
        "--review", type=Path, help="JSON of editorial observations"
    )
    review_commitments.add_argument(
        "--output", type=Path, help="Private JSON report with excerpts"
    )
    save_written = commands.add_parser("save-next-chapter-draft")
    save_written.add_argument("--input", type=Path, required=True)
    save_written.add_argument("--expected-revision-hash", required=True)
    save_written.add_argument("--draft", type=Path, required=True)
    for name in (
        "inspect-written-draft",
        "edit-written-draft",
        "annotate-written-draft",
        "preview-written-draft-edit",
        "apply-written-draft-edit-preview",
    ):
        written = commands.add_parser(name)
        written.add_argument("--input", type=Path, required=True)
        written.add_argument("--chapter-id", required=True)
        if name not in {"inspect-written-draft", "annotate-written-draft"}:
            written.add_argument("--prose", type=Path, required=True)
        if name in {
            "edit-written-draft",
            "annotate-written-draft",
            "preview-written-draft-edit",
        }:
            written.add_argument("--expected-revision-hash", required=True)
        if name == "edit-written-draft":
            written.add_argument("--choice", type=Path)
            written.add_argument(
                "--continuity", type=Path, help="Canonical JSON array of prose spans"
            )
        elif name == "annotate-written-draft":
            written.add_argument(
                "--annotations",
                type=Path,
                required=True,
                help="JSON of exact author-selected quotes from the saved Draft",
            )
        elif name == "preview-written-draft-edit":
            written.add_argument("--output", type=Path, required=True)
        elif name == "apply-written-draft-edit-preview":
            written.add_argument("--preview", type=Path, required=True)
            written.add_argument(
                "--resolutions",
                type=Path,
                help="Canonical JSON array of reviewed spans",
            )
        else:
            written.add_argument("--output", type=Path)
            written.add_argument("--version", type=int, help="Inspect a saved version")
    for name in ("inspect-revision-quality", "check-revision-quality"):
        revision_quality = commands.add_parser(name)
        revision_quality.add_argument("--input", type=Path, required=True)
        revision_quality.add_argument("--annotations", type=Path, required=True)
        if name == "check-revision-quality":
            revision_quality.add_argument("--expected-revision-hash", required=True)
    save_revision = commands.add_parser("save-chapter-revision")
    save_revision.add_argument("--expected-observation-hash", required=True)
    finish_chapter = commands.add_parser(
        "finish-chapter",
        help="Save a complete Draft from existing scenes and export TXT",
    )
    finish_chapter.add_argument("--output", type=Path, required=True)
    for draft_command in (save_revision, finish_chapter):
        draft_command.add_argument("--input", type=Path, required=True)
        draft_command.add_argument("--step-id", required=True)
        draft_command.add_argument("--version", type=int, required=True)
        draft_command.add_argument("--request-id", required=True)
        draft_command.add_argument(
            "--expected-revision-hash", help="Required after version 1"
        )
    bind_annotations = commands.add_parser("bind-revision-annotations")
    bind_annotations.add_argument("--input", type=Path, required=True)
    bind_annotations.add_argument(
        "--author-input",
        type=Path,
        required=True,
        help="Explicit Q1 claims and optional author evidence",
    )
    bind_annotations.add_argument("--expected-revision-hash", required=True)
    bind_annotations.add_argument("--output", type=Path, required=True)
    for name in ("assemble", "export-chapter", "verify-chapter"):
        command = commands.add_parser(name)
        command.add_argument("--step-id", required=True)
        command.add_argument("--input", type=Path, required=True)
        if name != "assemble":
            command.add_argument("--output", type=Path, required=True)
        if name == "export-chapter":
            command.add_argument("--expected-assembly-hash", required=True)
    inspect_run = commands.add_parser("inspect-run")
    inspect_run.add_argument("--input", type=Path, required=True)
    inspect_run.add_argument("--step-id")
    inspect_run.add_argument(
        "--q1-annotations-hash",
        help="Select a retained Q1 result by its annotation SHA-256",
    )
    for name in ("extract-chapter", "inspect-extraction", "check-q0", "inspect-q0"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--step-id", required=True)
    for name in ("check-q3", "inspect-q3"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--step-id", required=True)
    for name in ("check-q2", "inspect-q2"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--step-id", required=True)
    for name in ("check-q1", "inspect-q1"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--step-id", required=True)
        command.add_argument("--annotations", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "replace" and (args.fact_edits is None) != (
            args.projection_output is None
        ):
            raise WorkflowError("SCENE_FACT_EDITS_AND_PROJECTION_OUTPUT_REQUIRED")
        if not args.db.is_file():
            raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
        if args.operation in {
            "inspect-run",
            "project-scene",
            "inspect-chapter-revision",
            "export-chapter-revision",
            "project-next-chapter",
            "verify-next-chapter",
            "prepare-next-chapter-model-request",
            *_CHAPTER_RECEIPT_OPERATIONS,
            "save-next-chapter-draft",
            "inspect-written-draft",
            "inspect-written-draft-impact",
            "review-written-draft-commitments",
            "edit-written-draft",
            "annotate-written-draft",
            "preview-written-draft-edit",
            "apply-written-draft-edit-preview",
            "inspect-revision-quality",
            "check-revision-quality",
            "save-chapter-revision",
            "finish-chapter",
            "bind-revision-annotations",
            "extract-chapter",
            "inspect-extraction",
            "check-q0",
            "inspect-q0",
            "check-q1",
            "inspect-q1",
            "check-q2",
            "inspect-q2",
            "check-q3",
            "inspect-q3",
        }:
            _require_existing_run(
                args.db,
                args.project,
                args.branch,
                args.run_id,
                accept_revision_tables=True,
            )
        q1_inputs = (
            (_q1_input_bytes(args.input), _q1_input_bytes(args.annotations))
            if args.operation in {"check-q1", "inspect-q1"}
            else None
        )
        q2_input = (
            _q2_input_bytes(args.input)
            if args.operation in {"check-q2", "inspect-q2"}
            else None
        )
        q3_input = (
            _q3_input_bytes(args.input)
            if args.operation in {"check-q3", "inspect-q3"}
            else None
        )
        store = WorkflowStore(args.db)
        saved = store.load(project=args.project, branch=args.branch, run_id=args.run_id)
        gateway = None
        if args.operation == "recover":
            ledger = existing_gateway_ledger(args.gateway_ledger, store, saved)
            gateway = ModelGateway(BudgetLedger(ledger), _RecoveryOnly())
        if args.operation == "recover-scene":
            child = store.load_scene(
                project=args.project,
                branch=args.branch,
                run_id=args.run_id,
                step_id=args.step_id,
            )
            # Validate before constructing a writable ledger on a user path.
            verify_scene_ledger(
                args.gateway_ledger,
                store,
                child.source,
                child.ledger_pin,
                request=child.request,
                attempt_id=child.attempt_id,
                policy_id=child.policy_id,
            )
            gateway = ModelGateway(BudgetLedger(args.gateway_ledger), _RecoveryOnly())
        if args.operation in _CHAPTER_RECEIPT_OPERATIONS:
            openai = args.operation == "recover-next-chapter-openai"
            diagnostic = (
                "INVALID_OPENAI_DRAFT_REQUEST"
                if openai
                else "INVALID_KIMI_DRAFT_REQUEST"
            )
            try:
                request_bytes = _regular_input_bytes(args.request, diagnostic)
                frozen_writer_request = GatewayRequest.from_dict(
                    decode_canonical(request_bytes)
                )
                if frozen_writer_request.to_bytes() != request_bytes:
                    raise ValueError
            except (OSError, ValueError):
                raise WorkflowError(diagnostic) from None
            if openai:
                service = ChapterWorkflow(
                    store,
                    openai_writer=OpenAIDraftWriter(
                        frozen_writer_request, args.writer_ledger
                    ),
                    draft_handoff_step_id=args.draft_handoff_step_id,
                )
            else:
                service = ChapterWorkflow(
                    store,
                    kimi_writer=KimiDraftWriter(
                        frozen_writer_request, args.writer_ledger
                    ),
                    draft_handoff_step_id=args.draft_handoff_step_id,
                )
        else:
            service = ChapterWorkflow(
                store, gateway, draft_handoff_step_id=args.draft_handoff_step_id
            )
        if args.operation in {
            "inspect-chapter-revision",
            "export-chapter-revision",
            "project-next-chapter",
            "verify-next-chapter",
            "prepare-next-chapter-model-request",
            *_CHAPTER_RECEIPT_OPERATIONS,
            "inspect-written-draft-impact",
        }:
            chapter_revision_request = {
                "operation": "WRITE_NEXT_CHAPTER_DRAFT"
                if args.operation in _CHAPTER_RECEIPT_OPERATIONS
                else args.operation.replace("-", "_").upper(),
                "current_input": decode_canonical(
                    _regular_input_bytes(
                        args.input, "INVALID_CHAPTER_REVISION_INPUT_FILE"
                    )
                ),
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
            }
            if args.operation != "inspect-chapter-revision":
                chapter_revision_request.update(
                    expected_revision_hash=args.expected_revision_hash,
                )
            if args.operation in {"export-chapter-revision", "project-next-chapter"}:
                chapter_revision_request["output"] = str(args.output)
            if args.operation == "verify-next-chapter":
                chapter_revision_request["handoff"] = decode_canonical(
                    _regular_input_bytes(
                        args.handoff, "INVALID_NEXT_CHAPTER_INPUT_FILE"
                    )
                )
            if args.operation in {
                "prepare-next-chapter-model-request",
                *_CHAPTER_RECEIPT_OPERATIONS,
            }:
                chapter_revision_request.update(
                    handoff=_canonical_input(
                        args.handoff, "INVALID_NEXT_CHAPTER_INPUT_FILE"
                    ),
                    output=str(args.output),
                )
                if args.brief is not None:
                    chapter_revision_request["brief"] = _canonical_input(
                        args.brief, "INVALID_NEXT_CHAPTER_BRIEF"
                    )
            if args.operation == "prepare-next-chapter-model-request":
                policy_row = _canonical_input(
                    args.policy, "INVALID_NEXT_CHAPTER_MODEL_POLICY"
                )
                if args.openai_env is not None:
                    check_openai_env(args.openai_env, ModelPolicy.from_dict(policy_row))
                chapter_revision_request["policy"] = policy_row
            if (
                args.operation
                in {
                    "project-next-chapter",
                    "verify-next-chapter",
                    "prepare-next-chapter-model-request",
                    *_CHAPTER_RECEIPT_OPERATIONS,
                    "inspect-written-draft-impact",
                }
                and args.source_chapter_id is not None
            ):
                chapter_revision_request["source_chapter_id"] = {
                    "project": args.project,
                    "local_id": args.source_chapter_id,
                }
            revision = WorkflowTaskAdapter(service).execute(chapter_revision_request)
            print(json.dumps(snapshot_summary(revision), ensure_ascii=False))
            return 0
        if args.operation in {
            "save-next-chapter-draft",
            "inspect-written-draft",
            "review-written-draft-commitments",
            "edit-written-draft",
            "annotate-written-draft",
            "preview-written-draft-edit",
            "apply-written-draft-edit-preview",
        }:
            written_request: dict[str, object] = {
                "operation": args.operation.replace("-", "_").upper(),
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
                "current_input": decode_canonical(
                    _regular_input_bytes(
                        args.input, "INVALID_CHAPTER_REVISION_INPUT_FILE"
                    )
                ),
            }
            if args.operation == "save-next-chapter-draft":
                written_request.update(
                    expected_revision_hash=args.expected_revision_hash,
                    draft=decode_canonical(
                        _regular_input_bytes(args.draft, "INVALID_WRITTEN_DRAFT")
                    ),
                )
            else:
                written_request["chapter_id"] = {
                    "project": args.project,
                    "local_id": args.chapter_id,
                }
                if args.operation not in {
                    "inspect-written-draft",
                    "annotate-written-draft",
                    "review-written-draft-commitments",
                }:
                    written_request["text"] = _regular_input_bytes(
                        args.prose, "INVALID_DRAFT_PROSE"
                    ).decode("utf-8")
                if args.operation in {
                    "edit-written-draft",
                    "annotate-written-draft",
                    "preview-written-draft-edit",
                    "review-written-draft-commitments",
                }:
                    written_request["expected_revision_hash"] = (
                        args.expected_revision_hash
                    )
                if args.operation == "review-written-draft-commitments":
                    diagnostic = "INVALID_DRAFT_COMMITMENT_REVIEW_FILE"
                    try:
                        written_request["review"] = (
                            {}
                            if args.review is None
                            else strict_json(
                                _regular_input_bytes(args.review, diagnostic)
                            )
                        )
                    except (OSError, ValueError):
                        raise WorkflowError(diagnostic) from None
                    if args.output is not None:
                        written_request["output"] = str(args.output)
                elif args.operation == "edit-written-draft":
                    written_request["preserve_unprovided_annotations"] = True
                    if args.choice is not None:
                        written_request["choice"] = decode_canonical(
                            _regular_input_bytes(args.choice, "INVALID_WRITTEN_DRAFT")
                        )
                    if args.continuity is not None:
                        written_request["continuity"] = _canonical_input(
                            args.continuity, "INVALID_DRAFT_CONTINUITY"
                        )
                elif args.operation == "annotate-written-draft":
                    diagnostic = "INVALID_DRAFT_ANNOTATIONS_FILE"
                    try:
                        written_request["annotations"] = strict_json(
                            _regular_input_bytes(args.annotations, diagnostic)
                        )
                    except (OSError, ValueError):
                        raise WorkflowError(diagnostic) from None
                elif args.operation == "preview-written-draft-edit":
                    written_request["output"] = str(args.output)
                elif args.operation == "apply-written-draft-edit-preview":
                    written_request["preview"] = _canonical_input(
                        args.preview, "INVALID_DRAFT_EDIT_PREVIEW"
                    )
                    if args.resolutions is not None:
                        written_request["resolutions"] = _canonical_input(
                            args.resolutions, "INVALID_DRAFT_EDIT_RESOLUTION"
                        )
                else:
                    if args.output is not None:
                        written_request["output"] = str(args.output)
                    if args.version is not None:
                        written_request["version"] = args.version
            written_result = WorkflowTaskAdapter(service).execute(written_request)
            print(json.dumps(snapshot_summary(written_result), ensure_ascii=False))
            return 0
        if args.operation == "bind-revision-annotations":
            bound = WorkflowTaskAdapter(service).execute(
                {
                    "operation": "BIND_REVISION_ANNOTATIONS",
                    "current_input": decode_canonical(
                        _regular_input_bytes(
                            args.input, "INVALID_CHAPTER_REVISION_INPUT_FILE"
                        )
                    ),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "expected_revision_hash": args.expected_revision_hash,
                    "author_input": decode_canonical(
                        _regular_input_bytes(
                            args.author_input, "INVALID_Q1_AUTHOR_INPUT_FILE"
                        )
                    ),
                    "output": str(args.output),
                }
            )
            print(json.dumps(snapshot_summary(bound), ensure_ascii=False))
            return 0
        if args.operation in {"save-chapter-revision", "finish-chapter"}:
            draft_request: dict[str, object] = {
                "current_input": decode_canonical(
                    _regular_input_bytes(
                        args.input, "INVALID_CHAPTER_REVISION_INPUT_FILE"
                    )
                ),
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
                "step_id": args.step_id,
                "version": args.version,
                "request_id": args.request_id,
                "expected_revision_hash": args.expected_revision_hash,
            }
            if args.operation == "finish-chapter":
                draft_request.update(
                    operation="FINISH_CHAPTER_DRAFT", output=str(args.output)
                )
            else:
                draft_request.update(
                    operation="SAVE_CHAPTER_REVISION",
                    expected_observation_hash=args.expected_observation_hash,
                )
            revision = WorkflowTaskAdapter(service).execute(draft_request)
            print(json.dumps(snapshot_summary(revision), ensure_ascii=False))
            return 0
        if args.operation in {"inspect-revision-quality", "check-revision-quality"}:
            revision_request: dict[str, object] = {
                "operation": args.operation.replace("-", "_").upper(),
                "current_input": decode_canonical(_q1_input_bytes(args.input)),
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
                "annotations": decode_canonical(_q1_input_bytes(args.annotations)),
            }
            if args.operation == "check-revision-quality":
                revision_request["expected_revision_hash"] = args.expected_revision_hash
            report = WorkflowTaskAdapter(service).execute(revision_request)
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        if args.operation == "project-scene":
            if args.selection is not None:
                selection = decode_canonical(
                    _regular_input_bytes(args.selection, "INVALID_SCENE_SELECTION_FILE")
                )
            elif args.delta_binding is not None:
                selection = {
                    "delta_binding": _canonical_input(
                        args.delta_binding, "INVALID_SCENE_DELTA_BINDING_FILE"
                    )
                }
            else:
                selection = _scene_fact_edits_input(args.fact_edits)
            projection = WorkflowTaskAdapter(service).execute(
                {
                    "operation": "PROJECT_SCENE",
                    "current_input": decode_canonical(
                        _regular_input_bytes(args.input, "INVALID_SCENE_INPUT_FILE")
                    ),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "expected_record_hash": args.expected_record_hash,
                    "selection": selection,
                }
            )
            if type(projection) is not SceneProjection:
                raise WorkflowError("SCENE_PROJECTION_REQUIRED")
            service.export_scene_projection(projection, output=args.output)
            print(json.dumps(snapshot_summary(projection), ensure_ascii=False))
            return 0
        if args.operation in {"check-q3", "inspect-q3"}:
            if q3_input is None:
                raise WorkflowError("INVALID_Q3_INPUT_FILE")
            report = WorkflowTaskAdapter(service).execute(
                {
                    "operation": "CHECK_Q3"
                    if args.operation == "check-q3"
                    else "INSPECT_Q3",
                    "current_input": decode_canonical(q3_input),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "step_id": args.step_id,
                }
            )
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        if args.operation in {"check-q2", "inspect-q2"}:
            if q2_input is None:
                raise WorkflowError("INVALID_Q2_INPUT_FILE")
            report = WorkflowTaskAdapter(service).execute(
                {
                    "operation": "CHECK_Q2"
                    if args.operation == "check-q2"
                    else "INSPECT_Q2",
                    "current_input": decode_canonical(q2_input),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "step_id": args.step_id,
                }
            )
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        if args.operation in {"check-q1", "inspect-q1"}:
            if q1_inputs is None:
                raise WorkflowError("INVALID_Q1_INPUT_FILE")
            report = WorkflowTaskAdapter(service).execute(
                {
                    "operation": "CHECK_Q1"
                    if args.operation == "check-q1"
                    else "INSPECT_Q1",
                    "current_input": decode_canonical(q1_inputs[0]),
                    "annotations": decode_canonical(q1_inputs[1]),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "step_id": args.step_id,
                }
            )
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        if args.operation in {"assemble", "export-chapter", "verify-chapter"}:
            adapter = WorkflowTaskAdapter(service)
            current = decode_canonical(args.input.read_bytes())
            assembly_request: dict[str, object] = {
                "operation": "VERIFY_CHAPTER_EXPORT"
                if args.operation == "verify-chapter"
                else "ASSEMBLE_CHAPTER",
                "current_input": current,
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
                "step_id": args.step_id,
            }
            if args.operation == "verify-chapter":
                assembly_request["output"] = str(args.output)
            assembly = adapter.execute(assembly_request)
            if type(assembly) is not ChapterAssembly:
                raise WorkflowError("CHAPTER_ASSEMBLY_REQUIRED")
            if args.operation == "export-chapter":
                if assembly.record_hash != args.expected_assembly_hash:
                    raise WorkflowError("CHAPTER_ASSEMBLY_CHANGED")
                assembly = adapter.execute(
                    {
                        "operation": "EXPORT_CHAPTER",
                        "current_input": current,
                        "assembly": assembly.to_dict(),
                        "output": str(args.output),
                    }
                )
            print(json.dumps(snapshot_summary(assembly), ensure_ascii=False))
            return 0
        if args.operation in {
            "extract-chapter",
            "inspect-extraction",
            "check-q0",
            "inspect-q0",
        }:
            report = WorkflowTaskAdapter(service).execute(
                {
                    "operation": {
                        "extract-chapter": "EXTRACT_CHAPTER",
                        "inspect-extraction": "INSPECT_EXTRACTION",
                        "check-q0": "CHECK_Q0",
                        "inspect-q0": "INSPECT_Q0",
                    }[args.operation],
                    "current_input": decode_canonical(args.input.read_bytes()),
                    "project": args.project,
                    "branch": args.branch,
                    "run_id": args.run_id,
                    "step_id": args.step_id,
                }
            )
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        if args.operation == "inspect-run":
            assessment_request: dict[str, object] = {
                "operation": "ASSESS_RUN",
                "current_input": decode_canonical(args.input.read_bytes()),
                "project": args.project,
                "branch": args.branch,
                "run_id": args.run_id,
                "step_id": args.step_id,
            }
            if args.q1_annotations_hash is not None:
                assessment_request["q1_annotations_hash"] = args.q1_annotations_hash
            report = WorkflowTaskAdapter(service).execute(assessment_request)
            print(json.dumps(snapshot_summary(report), ensure_ascii=False))
            return 0
        request: dict[str, object] = {
            "operation": {
                "inspect": "INSPECT",
                "export": "EXPORT",
                "replace": "REPLACE_DRAFT",
                "recover": "RECOVER",
                "inspect-scene": "INSPECT_SCENE",
                "recover-scene": "RECOVER_SCENE",
            }[args.operation],
            "project": args.project,
            "branch": args.branch,
            "run_id": args.run_id,
        }
        if args.operation in {"replace", "recover", "recover-scene"}:
            request["current_input"] = decode_canonical(args.input.read_bytes())
        if args.operation in {"inspect-scene", "recover-scene"}:
            request["step_id"] = args.step_id
        if args.operation == "replace":
            request.update(
                text=args.prose.read_bytes().decode("utf-8"),
                expected_revision=args.expected_revision,
                expected_prose_hash=args.expected_prose_hash,
            )
            if args.fact_edits is not None:
                request.update(_scene_fact_edits_input(args.fact_edits))
                request.update(
                    operation="REPLACE_DRAFT_AND_PROJECT_SCENE",
                    output=str(args.projection_output),
                )
        if args.operation == "export":
            request["output"] = str(args.output)
        outcome = WorkflowTaskAdapter(service).execute(request)
        print(json.dumps(snapshot_summary(outcome), ensure_ascii=False))
        return 0
    except WorkflowError as error:
        print(json.dumps({"status": "BLOCKED", "code": str(error)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"status": "BLOCKED", "code": "INVALID_WORKFLOW_CLI_INPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
