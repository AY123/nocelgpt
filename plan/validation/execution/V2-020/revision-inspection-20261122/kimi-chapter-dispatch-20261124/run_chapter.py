"""Run one approved V2-020 Draft through the chapter workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from writer_authorization import (
    ChapterJob,
    WriterAuthorizationError,
    WriterProvider,
    validate_job,
)

from anovel.gateway.models import (
    BudgetLimit,
    EstimateFeeBound,
    GatewayRequest,
)
from anovel.gateway.probe_runtime import private_probe_directory, read_hidden_credential
from anovel.workflow.chapter import (
    ChapterWorkflow,
    KimiDraftWriter,
    NextChapterWrittenDraft,
    OpenAIDraftWriter,
)
from anovel.workflow.interfaces import snapshot_summary
from anovel.workflow.models import WorkflowError
from anovel.workflow.openai_settings import check_openai_env, read_openai_credential
from anovel.workflow.store import WorkflowStore
from anovel.workflow.written_draft import WrittenDraftRevision

ROOT = Path(__file__).resolve().parents[6]


def _checked_job(
    root: Path, *, own_claim: Path | None = None, provider: WriterProvider = "KIMI"
) -> tuple[ChapterJob, dict[str, object]]:
    sys.path.insert(0, str(root / "plan/scripts"))
    try:
        from change_review import review_changes
        from task_entry import (
            bind_change_review,
            git,
            observe,
            safe_output,
            validate_context,
        )

        errors, packet = validate_context(root, "V2-020", "LIVE_CALL")
        if errors or packet is None:
            raise WorkflowError(f"{provider}_CHAPTER_LIVE_ACTION_NOT_AUTHORIZED")
        before = observe(root)
        errors, packet = validate_context(root, "V2-020", "LIVE_CALL")
        if errors or packet is None:
            raise WorkflowError(f"{provider}_CHAPTER_LIVE_ACTION_NOT_AUTHORIZED")
        pins = argparse.Namespace(
            scope_revision=None, scope_ref=None, review_revision=None, review_ref=None
        )
        bind_change_review(packet, "LIVE_CALL", pins)
        review = review_changes(root, task_id="V2-020", **vars(pins))
        if review["status"] != "PASS":
            raise WorkflowError(f"{provider}_CHAPTER_LIVE_ACTION_NOT_AUTHORIZED")
        job = validate_job(root, packet, provider=provider)
        if job.workflow_db.is_relative_to(root):
            relative = str(job.workflow_db.relative_to(root))
            ignored = subprocess.run(
                ["git", "-C", str(root), "check-ignore", "--quiet", "--", relative],
                check=False,
            )
            if ignored.returncode != 0 or git(root, "ls-files", "--", relative).strip():
                raise WorkflowError(f"{provider}_CHAPTER_WORKING_COPY_REQUIRED")
        if provider == "OPENAI":
            check_openai_env(root / ".env", job.request.policies[0])
        for path in (job.ledger, job.output, job.claim):
            if path == own_claim:
                if path != job.claim:
                    raise WorkflowError(f"{provider}_CHAPTER_AUTHORIZATION_CHANGED")
                continue
            if path.exists() or path.is_symlink():
                raise WorkflowError(f"{provider}_CHAPTER_ALREADY_ATTEMPTED")
            safe_output(root, path)
        if observe(root) != before:
            raise WorkflowError(f"{provider}_CHAPTER_AUTHORIZATION_CHANGED")
        return job, before
    finally:
        sys.path.pop(0)


def run_job(
    job: ChapterJob, revalidate: Callable[[], None], *, env_path: Path | None = None
) -> NextChapterWrittenDraft | WrittenDraftRevision:
    """Compose an admitted job with the existing Writer and save a Draft."""
    provider = job.provider
    env_path = env_path if env_path is not None else ROOT / ".env"
    policy = job.request.policies[0]
    if provider == "OPENAI":
        check_openai_env(env_path, policy)
    attempt_id = job.request.logical_id + "-attempt-1"
    with private_probe_directory(job.ledger, job.output, job.claim) as private:
        if any(path.exists() for path in (job.ledger, job.output, job.claim)):
            raise WorkflowError(f"{provider}_CHAPTER_ALREADY_ATTEMPTED")

        def authorize(
            request: GatewayRequest,
            budget: BudgetLimit,
            ledger: Path,
            attempt: str,
            estimate_fee: EstimateFeeBound | None,
        ) -> bool:
            if (request, budget, ledger, attempt, estimate_fee) != (
                job.request,
                job.budget,
                job.ledger,
                attempt_id,
                job.estimate_fee,
            ):
                return False
            revalidate()
            private.claim_authorization("V2-020:" + job.grant_sha256, attempt_id)
            return True

        def credential() -> str:
            if provider == "OPENAI":
                value = read_openai_credential(env_path, policy)
            else:
                value = read_hidden_credential(
                    deadline_at=job.budget.deadline_at, kimi=True
                )
            private.verify_files()
            if not job.claim.is_file():
                raise WorkflowError(f"{provider}_CHAPTER_AUTHORIZATION_CHANGED")
            revalidate()
            return value

        if provider == "OPENAI":
            workflow = ChapterWorkflow(
                WorkflowStore(job.workflow_db),
                openai_writer=OpenAIDraftWriter(
                    job.request, job.ledger, job.budget, authorize, credential
                ),
                draft_handoff_step_id=job.root_step_id,
            )
        else:
            workflow = ChapterWorkflow(
                WorkflowStore(job.workflow_db),
                kimi_writer=KimiDraftWriter(
                    job.request,
                    job.ledger,
                    job.budget,
                    authorize,
                    credential,
                    job.estimate_fee,
                ),
                draft_handoff_step_id=job.root_step_id,
            )
        result: NextChapterWrittenDraft | WrittenDraftRevision
        if job.expected_target_revision_hash is None:
            result = workflow.write_next_chapter_draft(
                job.current,
                project=job.request.project,
                branch=job.request.branch,
                run_id=job.request.run_id,
                expected_revision_hash=job.revision_hash,
                retained_payload=job.handoff,
                output=job.output,
                source_chapter_id=job.source_chapter_id,
                brief=job.brief,
            )
        else:
            result = workflow.rewrite_next_chapter_draft(
                job.current,
                project=job.request.project,
                branch=job.request.branch,
                run_id=job.request.run_id,
                expected_revision_hash=job.revision_hash,
                expected_target_revision_hash=job.expected_target_revision_hash,
                retained_payload=job.handoff,
                output=job.output,
                source_chapter_id=job.source_chapter_id,
                brief=job.brief,
            )
        private.verify_files()
        return result


def main(argv: list[str] | None = None, *, provider: WriterProvider = "OPENAI") -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Run the authorized job using the selected provider credentials",
    )
    args = parser.parse_args(argv)
    try:
        job, before = _checked_job(ROOT, provider=provider)
        if not args.execute_live:
            summary: dict[str, object] = {
                "status": f"{provider}_CHAPTER_AUTHORIZATION_CHECKED",
                "artifact_state": "DRAFT",
                "request_hash": job.request.semantic_hash,
            }
        else:

            def revalidate() -> None:
                current, observed = _checked_job(
                    ROOT,
                    own_claim=job.claim if job.claim.is_file() else None,
                    provider=provider,
                )
                if current != job or observed != before:
                    raise WorkflowError(f"{provider}_CHAPTER_AUTHORIZATION_CHANGED")

            summary = snapshot_summary(run_job(job, revalidate))
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (WorkflowError, WriterAuthorizationError) as error:
        print(json.dumps({"status": "BLOCKED", "code": str(error)}))
        return 2
    except (OSError, ValueError, subprocess.SubprocessError):
        print(
            json.dumps(
                {"status": "BLOCKED", "code": f"{provider}_CHAPTER_DISPATCH_BLOCKED"}
            )
        )
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"status": "INTERRUPTED", "automatic_retry": False}))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
