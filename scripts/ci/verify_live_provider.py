"""Read back a protected GitHub observation or verify a hosted approval."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
import zlib
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPOSITORY = "AY123/nocelgpt"
REPOSITORY_ID = 1421585508
OWNER_ID = 20210118
WORKFLOW = ".github/workflows/v2-019-live-provider.yml"
HOSTED_WORKFLOW = ".github/workflows/v2-019-live-provider-hosted.yml"
HOSTED_ENVIRONMENT = "anovelos-live-provider-hosted"
HOSTED_JOB = "hosted_preflight"
RUNNER_GROUP = "anovelos-live-provider"
RUN_ATTEMPT = 1
ARCHIVE_MEMBER = "live-provider.json"
MAX_ARCHIVE_BYTES = 65_536
MAX_REPORT_BYTES = 16_384
MAX_API_BYTES = 1_048_576
_COMMON_PROBE_DIGESTS = {
    "authorization_sha256",
    "task_receipt_sha256",
    "result_sha256",
    "request_hash",
    "policy_hash",
    "response_hash",
}
_PROBE_DIGESTS = _COMMON_PROBE_DIGESTS | {
    "count_hash",
    "provider_request_id_sha256",
}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(value: object, error: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(type(key) is not str for key in value):
        raise ValueError(error)
    return value


def _matches(
    observed: dict[str, object], expected: dict[str, object], error: str
) -> None:
    for key, value in expected.items():
        actual = observed.get(key)
        if type(actual) is not type(value) or actual != value:
            raise ValueError(error)


def _positive_id(value: object, error: str) -> int:
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError(error)
    return value


def _one_record(root: object, name: str, error: str) -> dict[str, object]:
    response = _object(root, error)
    _matches(response, {"total_count": 1}, error)
    records = response.get(name)
    if not isinstance(records, list) or len(records) != 1:
        raise ValueError(error)
    return _object(records[0], error)


def _require_identity(revision: str, run_id: int) -> None:
    if type(revision) is not str or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("LIVE_PROVIDER_REVISION")
    _positive_id(run_id, "LIVE_PROVIDER_RUN_ID")


def validate_hosted_context(env: Mapping[str, str], revision: str) -> int:
    """Bind the checkout to the first attempt of the one hosted preflight job."""
    expected: dict[str, object] = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REPOSITORY_ID": str(REPOSITORY_ID),
        "GITHUB_ACTOR_ID": str(OWNER_ID),
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/{HOSTED_WORKFLOW}@refs/heads/main",
        "GITHUB_JOB": HOSTED_JOB,
        "GITHUB_RUN_ATTEMPT": str(RUN_ATTEMPT),
        "RUNNER_ENVIRONMENT": "github-hosted",
        "GITHUB_SHA": revision,
        "GITHUB_WORKFLOW_SHA": revision,
    }
    _matches(dict(env), expected, "LIVE_PROVIDER_HOSTED_CONTEXT")
    value = env.get("GITHUB_RUN_ID", "")
    if type(value) is not str or re.fullmatch(r"[1-9][0-9]{0,17}", value) is None:
        raise ValueError("LIVE_PROVIDER_HOSTED_RUN_ID")
    run_id = int(value)
    _require_identity(revision, run_id)
    return run_id


def _hosted_environment_id(environment_record: object, branch_policies: object) -> int:
    error = "LIVE_PROVIDER_HOSTED_ENVIRONMENT"
    environment = _object(environment_record, error)
    _matches(environment, {"name": HOSTED_ENVIRONMENT}, error)
    environment_id = _positive_id(environment.get("id"), error)
    _matches(
        _object(environment.get("deployment_branch_policy"), error),
        {"protected_branches": False, "custom_branch_policies": True},
        error,
    )
    branch = _one_record(branch_policies, "branch_policies", error)
    _matches(branch, {"name": "main"}, error)
    # The official list response can omit the branch-vs-tag type.
    if "type" in branch:
        _matches(branch, {"type": "branch"}, error)
    raw_rules = environment.get("protection_rules")
    if not isinstance(raw_rules, list):
        raise ValueError(error)
    rules = [_object(item, error) for item in raw_rules]
    required = [rule for rule in rules if rule.get("type") == "required_reviewers"]
    if len(required) != 1:
        raise ValueError(error)
    _matches(required[0], {"prevent_self_review": False}, error)
    reviewers = required[0].get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) != 1:
        raise ValueError(error)
    reviewer = _object(reviewers[0], error)
    _matches(reviewer, {"type": "User"}, error)
    _matches(_object(reviewer.get("reviewer"), error), {"id": OWNER_ID}, error)
    return environment_id


def validate_hosted_approval(
    *,
    env: Mapping[str, str],
    revision: str,
    run: object,
    environment_record: object,
    branch_policies: object,
    reviews: object,
    now: datetime,
) -> dict[str, object]:
    """Validate one exact approval record without enabling provider execution."""
    run_id = validate_hosted_context(env, revision)
    run_error = "LIVE_PROVIDER_HOSTED_RUN"
    record = _object(run, run_error)
    _matches(
        record,
        {
            "id": run_id,
            "run_attempt": RUN_ATTEMPT,
            "head_branch": "main",
            "head_sha": revision,
            "path": HOSTED_WORKFLOW,
            "event": "workflow_dispatch",
            "status": "in_progress",
            "conclusion": None,
        },
        run_error,
    )
    for key in ("actor", "triggering_actor"):
        _matches(
            _object(record.get(key), run_error),
            {"id": OWNER_ID, "login": "AY123"},
            run_error,
        )
    for key in ("repository", "head_repository"):
        _matches(
            _object(record.get(key), run_error),
            {"id": REPOSITORY_ID, "full_name": REPOSITORY},
            run_error,
        )

    environment_id = _hosted_environment_id(environment_record, branch_policies)
    error = "LIVE_PROVIDER_HOSTED_APPROVAL"
    if not isinstance(reviews, list) or len(reviews) != 1:
        raise ValueError(error)
    review = _object(reviews[0], error)
    _matches(review, {"state": "approved"}, error)
    _matches(
        _object(review.get("user"), error), {"id": OWNER_ID, "login": "AY123"}, error
    )
    environments = review.get("environments")
    if not isinstance(environments, list) or len(environments) != 1:
        raise ValueError(error)
    _matches(
        _object(environments[0], error),
        {"id": environment_id, "name": HOSTED_ENVIRONMENT},
        error,
    )
    comment = review.get("comment")
    if type(comment) is not str:
        raise ValueError(error)
    utc = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    terms = re.fullmatch(
        rf"ANOVELOS V2-019 HOSTED-PREFLIGHT {run_id} {revision} ({utc}) ({utc}) USD0 POST0",
        comment,
    )
    if terms is None:
        raise ValueError(error)
    time_error = "LIVE_PROVIDER_HOSTED_APPROVAL_TIME"
    try:
        issued, deadline = (
            datetime.fromisoformat(value[:-1] + "+00:00") for value in terms.groups()
        )
    except ValueError:
        raise ValueError(time_error) from None
    if (
        now.utcoffset() is None
        or not issued <= now < deadline
        or deadline - issued > timedelta(seconds=120)
    ):
        raise ValueError(time_error)

    return {
        "record_type": "live_provider_hosted_approval_preflight",
        "schema_version": "1.0",
        "scope": "HOSTED_APPROVAL_PREFLIGHT",
        "status": "PASS",
        "source": "LOCAL_INPUT_VALIDATED",
        "run_id": run_id,
        "run_attempt": RUN_ATTEMPT,
        "revision": revision,
        "environment_id": environment_id,
        "reviewer_id": OWNER_ID,
        "approval_sha256": _digest(comment.encode()),
        "provider_requests": 0,
        "gate_verified": False,
    }


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    record = dict(pairs)
    if len(record) != len(pairs):
        raise ValueError("LIVE_PROVIDER_DUPLICATE_JSON_KEY")
    return record


def _reject_constant(_value: str) -> None:
    raise ValueError("LIVE_PROVIDER_INVALID_JSON_CONSTANT")


def _decode(raw: bytes) -> object:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("LIVE_PROVIDER_INVALID_JSON") from None


def _report_bytes(archive: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(archive), "r") as source:
            entries = source.infolist()
            if len(entries) != 1:
                raise ValueError("LIVE_PROVIDER_ARCHIVE_MEMBERS")
            entry = entries[0]
            if (
                entry.filename != ARCHIVE_MEMBER
                or entry.orig_filename != ARCHIVE_MEMBER
                or entry.is_dir()
                or entry.flag_bits & 1
                or stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG)
                or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or not 0 < entry.file_size <= MAX_REPORT_BYTES
            ):
                raise ValueError("LIVE_PROVIDER_ARCHIVE_MEMBER")
            with source.open(entry) as member:
                raw = member.read(MAX_REPORT_BYTES + 1)
            if len(raw) != entry.file_size:
                raise ValueError("LIVE_PROVIDER_ARCHIVE_LENGTH")
            return raw
    except (zipfile.BadZipFile, OSError, RuntimeError, zlib.error):
        raise ValueError("LIVE_PROVIDER_INVALID_ARCHIVE") from None


def _artifact_info(
    revision: str, run_id: int, artifacts: object
) -> tuple[dict[str, object], int, int]:
    artifact = _one_record(artifacts, "artifacts", "LIVE_PROVIDER_ARTIFACT_COUNT")
    artifact_id = _positive_id(artifact.get("id"), "LIVE_PROVIDER_ARTIFACT_ID")
    error = "LIVE_PROVIDER_ARTIFACT_IDENTITY"
    _matches(
        artifact,
        {
            "name": f"live-provider-{run_id}-{RUN_ATTEMPT}",
            "expired": False,
            "archive_download_url": (
                f"https://api.github.com/repos/{REPOSITORY}"
                f"/actions/artifacts/{artifact_id}/zip"
            ),
        },
        error,
    )
    _matches(
        _object(artifact.get("workflow_run"), error),
        {
            "id": run_id,
            "repository_id": REPOSITORY_ID,
            "head_repository_id": REPOSITORY_ID,
            "head_branch": "main",
            "head_sha": revision,
        },
        error,
    )
    archive_size = _positive_id(
        artifact.get("size_in_bytes"), "LIVE_PROVIDER_ARCHIVE_SIZE"
    )
    if archive_size > MAX_ARCHIVE_BYTES:
        raise ValueError("LIVE_PROVIDER_ARCHIVE_SIZE")
    return artifact, artifact_id, archive_size


def validate_live_artifact(
    revision: str,
    run_id: int,
    run: object,
    jobs: object,
    artifacts: object,
    archive: bytes,
) -> dict[str, object]:
    """Validate matching decoded API objects and artifact bytes without provenance claims."""
    _require_identity(revision, run_id)
    run_error = "LIVE_PROVIDER_RUN_IDENTITY"
    run_record = _object(run, run_error)
    _matches(
        run_record,
        {
            "id": run_id,
            "run_attempt": RUN_ATTEMPT,
            "head_branch": "main",
            "head_sha": revision,
            "path": WORKFLOW,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
        },
        run_error,
    )
    workflow_id = _positive_id(run_record.get("workflow_id"), run_error)
    for key in ("actor", "triggering_actor"):
        _matches(
            _object(run_record.get(key), run_error),
            {"id": OWNER_ID, "login": "AY123"},
            run_error,
        )
    for key in ("repository", "head_repository"):
        _matches(
            _object(run_record.get(key), run_error),
            {"id": REPOSITORY_ID, "full_name": REPOSITORY},
            run_error,
        )

    job = _one_record(jobs, "jobs", "LIVE_PROVIDER_JOB_COUNT")
    job_error = "LIVE_PROVIDER_JOB_IDENTITY"
    _matches(
        job,
        {
            "run_id": run_id,
            "run_attempt": RUN_ATTEMPT,
            "head_sha": revision,
            "head_branch": "main",
            "name": "LIVE_PROVIDER",
            "status": "completed",
            "conclusion": "success",
            "runner_group_name": RUNNER_GROUP,
        },
        job_error,
    )
    job_id = _positive_id(job.get("id"), job_error)
    runner_id = _positive_id(job.get("runner_id"), job_error)
    runner_group_id = _positive_id(job.get("runner_group_id"), job_error)
    labels = job.get("labels")
    if (
        not isinstance(labels, list)
        or any(type(label) is not str or not label for label in labels)
        or RUNNER_GROUP not in labels
        or any(label.startswith("ubuntu-") for label in labels)
    ):
        raise ValueError("LIVE_PROVIDER_RUNNER_LABEL")

    artifact, artifact_id, archive_size = _artifact_info(revision, run_id, artifacts)
    if type(archive) is not bytes or len(archive) != archive_size:
        raise ValueError("LIVE_PROVIDER_ARCHIVE_SIZE")
    archive_digest = _digest(archive)
    _matches(
        artifact, {"digest": "sha256:" + archive_digest}, "LIVE_PROVIDER_ARCHIVE_DIGEST"
    )
    raw = _report_bytes(archive)
    report_error = "LIVE_PROVIDER_REPORT_IDENTITY"
    report = _object(_decode(raw), report_error)
    version = report.get("schema_version")
    if type(version) is not str or version not in {"1.0", "1.1"}:
        raise ValueError(report_error)
    expected: dict[str, object] = {
        "record_type": "live_provider_observation",
        "schema_version": version,
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "run_id": run_id,
        "run_attempt": RUN_ATTEMPT,
        "revision": revision,
        "observation": "KIMI_STRUCTURED_SUCCESS",
    }
    if set(report) != set(expected) | {"probe"}:
        raise ValueError(report_error)
    _matches(report, expected, report_error)
    probe = _object(report["probe"], report_error)
    probe_identity: dict[str, object] = {
        "observed_model": "kimi-k3.1-pro",
        "charge_status": "ESTIMATED",
    }
    if version == "1.1":
        digests = _COMMON_PROBE_DIGESTS | {"provider_response_id_sha256"}
        probe_identity["token_estimate"] = "NOT_REQUESTED"
        fields = digests | set(probe_identity) | {"provider_request_id_sha256"}
        if probe.get("provider_request_id_sha256") is not None:
            digests.add("provider_request_id_sha256")
    else:
        digests = _PROBE_DIGESTS
        fields = digests | set(probe_identity)
    if set(probe) != fields:
        raise ValueError(report_error)
    _matches(probe, probe_identity, report_error)
    for key in digests:
        value = probe[key]
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("LIVE_PROVIDER_REPORT_DIGEST")
    return {
        "record_type": "live_provider_first_observation_readback",
        "schema_version": "1.0",
        "source": "LOCAL_INPUT_VALIDATED",
        "revision": revision,
        "run_id": run_id,
        "run_attempt": RUN_ATTEMPT,
        "workflow_id": workflow_id,
        "job_id": job_id,
        "runner_id": runner_id,
        "runner_group_id": runner_group_id,
        "artifact_id": artifact_id,
        "archive_sha256": archive_digest,
        "observation_sha256": _digest(raw),
        "observation": report,
        "gate_verified": False,
    }


def _read_github(path: str, limit: int = MAX_API_BYTES) -> bytes:
    # gh resolves its own GitHub credential. Do not expose Provider variables
    # to the child or relay stderr that can contain transport details.
    keys = (
        "PATH",
        "HOME",
        "XDG_CONFIG_HOME",
        "GH_CONFIG_DIR",
        "GH_TOKEN",
        "GITHUB_TOKEN",
    )
    environment = {key: os.environ[key] for key in keys if key in os.environ}
    try:
        response = subprocess.run(
            ["gh", "api", "--hostname", "github.com", "--method", "GET", path],
            env=environment | {"GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("LIVE_PROVIDER_GITHUB_READ_FAILED") from None
    if not 0 < len(response.stdout) <= limit:
        raise ValueError("LIVE_PROVIDER_GITHUB_RESPONSE_SIZE")
    return response.stdout


def read_hosted_approval_preflight(root: Path) -> dict[str, object]:
    """Read the selected run and approval from official GitHub endpoints."""

    def git(*args: str) -> bytes:
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), *args], stderr=subprocess.PIPE, timeout=10
            )
        except (OSError, subprocess.SubprocessError):
            raise ValueError("LIVE_PROVIDER_HOSTED_CHECKOUT") from None

    try:
        revision = git("rev-parse", "HEAD").decode("ascii").strip()
    except UnicodeDecodeError:
        raise ValueError("LIVE_PROVIDER_HOSTED_CHECKOUT") from None
    run_id = validate_hosted_context(os.environ, revision)
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("LIVE_PROVIDER_HOSTED_DIRTY")
    base = f"repos/{REPOSITORY}"
    run_path = f"{base}/actions/runs/{run_id}"
    environment_path = f"{base}/environments/{HOSTED_ENVIRONMENT}"
    raw = {
        "run": _read_github(run_path),
        "environment_record": _read_github(environment_path),
        "branch_policies": _read_github(
            f"{environment_path}/deployment-branch-policies?per_page=2"
        ),
        "reviews": _read_github(f"{run_path}/approvals"),
    }
    result = validate_hosted_approval(
        env=os.environ,
        revision=revision,
        run=_decode(raw["run"]),
        environment_record=_decode(raw["environment_record"]),
        branch_policies=_decode(raw["branch_policies"]),
        reviews=_decode(raw["reviews"]),
        now=datetime.now(timezone.utc),
    )
    if git("rev-parse", "HEAD").strip() != revision.encode("ascii") or git(
        "status", "--porcelain", "--untracked-files=all"
    ):
        raise ValueError("LIVE_PROVIDER_HOSTED_CHECKOUT_CHANGED")
    result["source"] = "GITHUB_API_READBACK"
    result["api_response_sha256"] = {name: _digest(data) for name, data in raw.items()}
    return result


def read_live_artifact(
    revision: str, run_id: int, output_dir: Path | None = None
) -> dict[str, object]:
    """Read fixed official GitHub endpoints for one run without invoking it."""
    _require_identity(revision, run_id)
    if output_dir is not None and (output_dir.exists() or output_dir.is_symlink()):
        raise FileExistsError("LIVE_PROVIDER_OUTPUT_ALREADY_EXISTS")
    repo_path = f"repos/{REPOSITORY}/actions"
    run_path = f"{repo_path}/runs/{run_id}"
    run_raw = _read_github(run_path)
    jobs_raw = _read_github(f"{run_path}/attempts/{RUN_ATTEMPT}/jobs?per_page=2")
    artifacts_raw = _read_github(f"{run_path}/artifacts?per_page=2")
    run, jobs, artifacts = map(_decode, (run_raw, jobs_raw, artifacts_raw))
    _, artifact_id, size = _artifact_info(revision, run_id, artifacts)
    archive = _read_github(f"{repo_path}/artifacts/{artifact_id}/zip", limit=size)
    result = validate_live_artifact(revision, run_id, run, jobs, artifacts, archive)
    result["source"] = "GITHUB_API_READBACK"
    result["api_response_sha256"] = {
        "run": _digest(run_raw),
        "jobs": _digest(jobs_raw),
        "artifacts": _digest(artifacts_raw),
    }
    if output_dir is not None:
        output_dir.mkdir(mode=0o700)
        for name, data in (
            ("run.json", run_raw),
            ("jobs.json", jobs_raw),
            ("artifacts.json", artifacts_raw),
            ("observation.zip", archive),
            ("readback.json", (json.dumps(result, indent=2) + "\n").encode()),
        ):
            target = output_dir / name
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--hosted-approval-preflight", action="store_true")
    args = parser.parse_args(argv)
    artifact_args = (args.revision, args.run_id, args.output_dir)
    if args.hosted_approval_preflight:
        if any(value is not None for value in artifact_args):
            parser.error("--hosted-approval-preflight takes no artifact arguments")
    elif any(value is None for value in artifact_args):
        parser.error("--revision, --run-id and --output-dir are required")
    try:
        if args.hosted_approval_preflight:
            receipt = read_hosted_approval_preflight(
                Path(__file__).resolve().parents[2]
            )
        else:
            receipt = read_live_artifact(args.revision, args.run_id, args.output_dir)
    except (ValueError, OSError) as error:
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "LIVE_PROVIDER_OUTPUT_FAILED"
        )
        print(message, file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
