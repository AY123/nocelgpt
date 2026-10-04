"""Read GitLab's exact-job evidence; source verification is not task acceptance.

CLI authentication comes only from ANOVELOS_GITLAB_TOKEN. The HTTP client never
follows redirects, so an artifact redirect cannot forward credentials elsewhere.
Synthetic fetchers are supported only by the Python API for logic tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import yaml

PROJECT_ID = 86656946
API_ORIGIN = "https://gitlab.com/api/v4"
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
REQUIRED_JOBS = {
    "static": "STATIC",
    "unit": "UNIT",
    "schema_contract": "SCHEMA_CONTRACT",
    "arch_fitness": "ARCH_FITNESS",
    "secret_dependency": "SECRET_DEPENDENCY",
    "postgres_env": "POSTGRES_ENV",
}
JsonObject = dict[str, object]
PYTHON_VERSION = "3.12.14"


def command_tails(job_name: str) -> list[list[str]]:
    """Fixed reviewed command contract; never execute candidate driver code."""
    target = f"dist/ci/{job_name}"
    paths = ["src/anovel", "scripts/ci"]
    tests = [
        "tests/contract/test_delivery_gates.py",
        "tests/integration/test_postgres_ci_service.py",
    ]
    bootstrap = [
        "scripts/ci/bootstrap_scanners.py",
        "--output-dir",
        "dist/tools/gitleaks-8.21.2",
        "--reuse-verified",
    ]
    plans = {
        "static": [
            ["scripts/ci/check_configuration.py"],
            ["-m", "ruff", "format", "--check", *paths, *tests],
            ["-m", "ruff", "check", "--select", "F,E9,I", *paths, *tests],
            ["-m", "mypy", "--strict", "--cache-dir", "dist/cache/mypy", *paths],
            ["scripts/ci/check_syntax.py"],
        ],
        "unit": [
            bootstrap,
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/contract",
                "tests/integration/test_repository_bootstrap.py",
                f"--junitxml={target}/junit.xml",
            ],
        ],
        "schema_contract": [
            ["scripts/check_governance.py", "--output-dir", f"{target}/governance"]
        ],
        "arch_fitness": [
            [
                "scripts/task_execution.py",
                "check",
                "--task",
                "V2-004",
                "--action",
                "IMPLEMENT",
                "--output",
                f"{target}/action-entry.json",
            ],
            [
                "scripts/check_architecture.py",
                "--output",
                f"{target}/architecture.json",
            ],
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture",
                f"--junitxml={target}/junit.xml",
            ],
        ],
        "secret_dependency": [
            bootstrap,
            ["scripts/ci/check_security.py", "--output-dir", f"{target}/security"],
        ],
        "postgres_env": [
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-s",
                "tests/integration/test_postgres_ci_service.py",
                f"--junitxml={target}/junit.xml",
            ]
        ],
    }
    if job_name not in plans:
        raise SourceError("Unregistered command contract")
    return [["-B", *command] for command in plans[job_name]]


def required_artifact_refs(job_name: str) -> set[str]:
    """Existing result files and every command log are mandatory evidence."""
    results = {
        "static": [],
        "unit": ["junit.xml"],
        "schema_contract": [
            "governance/governance-summary.json",
            "governance/plan/plan-validation.json",
            "governance/self-test/validator-self-test.json",
            "governance/governance/governance-regression.json",
            "governance/ai/ai-execution-regression.json",
            "governance/legacy.json",
            "governance/context-inventory.json",
            "governance/normative-index.json",
        ],
        "arch_fitness": ["action-entry.json", "architecture.json", "junit.xml"],
        "secret_dependency": [
            "security/security-summary.json",
            "security/secret-scan.json",
            "security/dependency-audit.json",
            "security/locked-audit-requirements.txt",
        ],
        "postgres_env": ["junit.xml"],
    }
    target = f"dist/ci/{job_name}"
    return {f"{target}/{ref}" for ref in results[job_name]} | {
        f"{target}/command-{number:02d}.{stream}.log"
        for number in range(1, len(command_tails(job_name)) + 1)
        for stream in ("stdout", "stderr")
    }


def python_executable(value: object) -> str:
    executable = string(value, "Python executable")
    path = PurePosixPath(executable)
    if (
        not path.is_absolute()
        or executable.startswith("//")
        or ".." in path.parts
        or "\\" in executable
        or "\0" in executable
        or path.as_posix() != executable
        or not executable.endswith("/.venv/bin/python")
    ):
        raise SourceError("Expected a normalized absolute project Python executable")
    return executable


class SourceError(Exception):
    """A source contradicted the expected identity or mandatory result."""


class SourceUnavailable(Exception):
    """Required authenticated source could not be read safely."""


@dataclass(frozen=True)
class ApiResponse:
    body: bytes
    headers: dict[str, str]


Fetcher = Callable[[str], ApiResponse]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        raise SourceUnavailable("HTTP redirect refused; credentials were not forwarded")


class GitLabClient:
    def __init__(self, token: str) -> None:
        if not token or any(char in token for char in "\r\n"):
            raise SourceUnavailable("ANOVELOS_GITLAB_TOKEN is missing or invalid")
        self._token = token
        self._opener = build_opener(
            HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
        )

    def fetch(self, path: str) -> ApiResponse:
        # URLs are constructed internally, never supplied by remote metadata.
        parsed = urlsplit(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or parsed.netloc
            or parsed.scheme
        ):
            raise SourceUnavailable(
                "Only fixed-origin relative API paths are supported"
            )
        request = Request(
            API_ORIGIN + path,
            headers={"PRIVATE-TOKEN": self._token, "Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise SourceUnavailable(
                        "Remote response exceeds evidence size limit"
                    )
                return ApiResponse(
                    body,
                    {key.lower(): value for key, value in response.headers.items()},
                )
        except HTTPError as error:
            raise SourceUnavailable(
                f"GitLab API request unavailable (HTTP {error.code})"
            ) from None
        except (URLError, TimeoutError, OSError):
            # Exceptions and request objects can expose headers; never print them.
            raise SourceUnavailable("GitLab API network request unavailable") from None


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def mapping(value: object, label: str) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise SourceError(f"{label} must be an object")
    return cast(JsonObject, value)


def items(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise SourceError(f"{label} must be a list")
    return cast(list[object], value)


def integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SourceError(f"{label} must be a positive integer")
    return value


def string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SourceError(f"{label} must be a nonempty string")
    return value


def parse_json(content: bytes, label: str) -> object:
    try:
        result: object = json.loads(content)
        return result
    except (ValueError, UnicodeError):
        raise SourceError(f"{label} is not valid JSON") from None


def exact(data: JsonObject, field: str, expected: object, label: str) -> None:
    actual = data.get(field)
    if type(actual) is not type(expected) or actual != expected:
        raise SourceError(f"{label}: {field} does not match expected identity/result")


def artifact_ref(value: object, job_name: str) -> str:
    ref = string(value, "artifact reference")
    path = PurePosixPath(ref)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in ref
        or ref != path.as_posix()
        or not ref.startswith(f"dist/ci/{job_name}/")
        or ref.endswith("/")
    ):
        raise SourceError("Artifact reference escapes its exact job output directory")
    return ref


def verified_artifact(
    fetch: Fetcher,
    job_id: int,
    job_name: str,
    descriptor: JsonObject,
    blobs: dict[str, bytes],
) -> JsonObject:
    if set(descriptor) != {"ref", "sha256"}:
        raise SourceError("Artifact descriptor must contain only ref and sha256")
    ref = artifact_ref(descriptor.get("ref"), job_name)
    expected_hash = string(descriptor.get("sha256"), "artifact hash")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_hash):
        raise SourceError("Invalid artifact SHA256")
    storage_ref = f"job-{job_id}/{ref}"
    body = blobs.get(storage_ref)
    if body is None:
        body = fetch(
            f"/projects/{PROJECT_ID}/jobs/{job_id}/artifacts/{quote(ref, safe='')}"
        ).body
    if digest(body) != expected_hash:
        raise SourceError(f"Job {job_id}: artifact content hash mismatch")
    blobs[storage_ref] = body
    return {"ref": ref, "sha256": expected_hash, "storage_ref": storage_ref}


def pipeline_jobs(fetch: Fetcher, pipeline_id: int) -> list[JsonObject]:
    jobs: list[JsonObject] = []
    page = 1
    while page <= 100:
        response = fetch(
            f"/projects/{PROJECT_ID}/pipelines/{pipeline_id}/jobs"
            f"?include_retried=true&per_page=100&page={page}"
        )
        page_jobs = items(parse_json(response.body, "pipeline jobs"), "pipeline jobs")
        jobs.extend(mapping(item, "job") for item in page_jobs)
        next_page = response.headers.get("x-next-page", "")
        if not next_page:
            if len(page_jobs) >= 100 and "x-next-page" not in response.headers:
                raise SourceUnavailable(
                    "Job pagination headers missing; complete coverage unknown"
                )
            return jobs
        if not next_page.isdecimal() or int(next_page) <= page:
            raise SourceError("Invalid job pagination sequence")
        page = int(next_page)
    raise SourceUnavailable("Pipeline job pagination exceeds verification limit")


def verify_job(
    fetch: Fetcher,
    job: JsonObject,
    *,
    revision: str,
    pipeline_id: int,
    ref: str,
    driver_sha256: str,
    lock_sha256: str,
    blobs: dict[str, bytes],
) -> JsonObject:
    job_id = integer(job.get("id"), "job ID")
    name = string(job.get("name"), "job name")
    exact(job, "status", "success", name)
    exact(job, "allow_failure", False, name)
    exact(job, "ref", ref, name)
    exact(mapping(job.get("commit"), "job commit"), "id", revision, name)
    pipeline = mapping(job.get("pipeline"), "job pipeline")
    for field, expected in (
        ("id", pipeline_id),
        ("project_id", PROJECT_ID),
        ("sha", revision),
    ):
        exact(pipeline, field, expected, name)
    runner = mapping(job.get("runner"), "job runner")
    runner_id = integer(runner.get("id"), "runner ID")
    trace = fetch(f"/projects/{PROJECT_ID}/jobs/{job_id}/trace").body
    start = f"ANOVELOS_GATE_START {name} {driver_sha256}".encode()
    end = f"ANOVELOS_GATE_END {name} PASS".encode()
    if (
        not trace
        or start not in trace
        or end not in trace
        or trace.index(start) >= trace.index(end)
    ):
        raise SourceError(
            f"Job {job_id}: actual trace lacks ordered driver/result markers"
        )
    trace_ref = f"job-{job_id}/trace.log"
    blobs[trace_ref] = trace
    receipt_ref = f"dist/ci/{name}/receipt.json"
    receipt_bytes = fetch(
        f"/projects/{PROJECT_ID}/jobs/{job_id}/artifacts/{quote(receipt_ref, safe='')}"
    ).body
    receipt = mapping(parse_json(receipt_bytes, "receipt"), "receipt")
    for receipt_field, receipt_value in (
        ("record_type", "ci_gate_receipt"),
        ("schema_version", "1.0"),
        ("gate", REQUIRED_JOBS[name]),
        ("job_name", name),
        ("status", "PASS"),
        ("revision", revision),
        ("project_id", str(PROJECT_ID)),
        ("pipeline_id", str(pipeline_id)),
        ("job_id", str(job_id)),
        ("driver_sha256", driver_sha256),
        ("lock_sha256", lock_sha256),
        ("python", PYTHON_VERSION),
        ("source_kind", "UNVERIFIED_GITLAB_ENVIRONMENT"),
        ("exit_code", 0),
        ("errors", []),
    ):
        exact(receipt, receipt_field, receipt_value, f"Job {job_id} receipt")
    commands = items(receipt.get("commands"), "receipt commands")
    expected_commands = command_tails(name)
    if len(commands) != len(expected_commands):
        raise SourceError("Command receipt does not cover the complete fixed plan")
    checked_commands: list[JsonObject] = []
    interpreter: str | None = None
    for number, (value, expected_tail) in enumerate(
        zip(commands, expected_commands), 1
    ):
        command = mapping(value, "command receipt")
        argv = items(command.get("argv"), "command argv")
        if not argv or any(not isinstance(arg, str) or not arg for arg in argv):
            raise SourceError("Command argv must contain nonempty string arguments")
        executable = python_executable(argv[0])
        if argv[1:] != expected_tail or (interpreter and interpreter != executable):
            raise SourceError("Command receipt differs from the fixed gate plan")
        interpreter = executable
        exact(command, "exit_code", 0, "command receipt")
        for stream in ("stdout", "stderr"):
            exact(
                mapping(command.get(stream), stream),
                "ref",
                f"dist/ci/{name}/command-{number:02d}.{stream}.log",
                "command log",
            )
        stdout = verified_artifact(
            fetch, job_id, name, mapping(command.get("stdout"), "stdout"), blobs
        )
        stderr = verified_artifact(
            fetch, job_id, name, mapping(command.get("stderr"), "stderr"), blobs
        )
        checked_commands.append(
            {"argv": argv, "exit_code": 0, "stdout": stdout, "stderr": stderr}
        )
    artifacts: list[JsonObject] = []
    by_ref: dict[str, JsonObject] = {}
    for value in items(receipt.get("artifacts"), "receipt artifacts"):
        descriptor = mapping(value, "artifact")
        ref_name = artifact_ref(descriptor.get("ref"), name)
        if ref_name in by_ref:
            raise SourceError("Receipt repeats an artifact reference")
        artifact = verified_artifact(fetch, job_id, name, descriptor, blobs)
        artifacts.append(artifact)
        by_ref[ref_name] = artifact
    if not required_artifact_refs(name).issubset(by_ref):
        raise SourceError("Receipt omits mandatory command logs or result artifacts")
    for command in checked_commands:
        for stream in ("stdout", "stderr"):
            log = mapping(command[stream], "verified log")
            listed = by_ref[string(log["ref"], "log reference")]
            if listed["sha256"] != log["sha256"]:
                raise SourceError("Command and artifact descriptors disagree")
    stored_receipt = f"job-{job_id}/{receipt_ref}"
    blobs[stored_receipt] = receipt_bytes
    return {
        "job_name": name,
        "gate": REQUIRED_JOBS[name],
        "job_id": job_id,
        "runner_id": runner_id,
        "status": "success",
        "trace": {"storage_ref": trace_ref, "sha256": digest(trace)},
        "receipt": {"storage_ref": stored_receipt, "sha256": digest(receipt_bytes)},
        "commands": checked_commands,
        "artifacts": artifacts,
    }


def verify_trust_metadata(
    fetch: Fetcher,
    policy: JsonObject,
    project: JsonObject,
    branch: JsonObject,
    ref: str,
    verified_jobs: list[JsonObject],
) -> list[str]:
    """Metadata is necessary, but cannot prove permission-denial experiments."""
    problems: list[str] = []
    trust = mapping(policy.get("trusted_execution", {}), "trusted_execution")
    runners = items(trust.get("runner_ids", []), "trusted runner IDs")
    if not runners or any(
        not isinstance(value, int) or isinstance(value, bool) for value in runners
    ):
        problems.append("Trusted runner IDs are not configured")
    if trust.get("protected_ref") != ref:
        problems.append("Trusted protected ref is not configured for the tested ref")
    configured_path = trust.get("ci_config_path")
    actual_path = project.get("ci_config_path") or ".gitlab-ci.yml"
    if (
        not isinstance(configured_path, str)
        or not configured_path
        or configured_path != actual_path
    ):
        problems.append(
            "Trusted CI configuration does not match actual project configuration"
        )
    if branch.get("protected") is not True:
        problems.append("Tested branch is not protected")
    if project.get("only_allow_merge_if_pipeline_succeeds") is not True:
        problems.append("Project does not require successful pipelines for merges")
    if problems:
        return problems
    try:
        protection = mapping(
            parse_json(
                fetch(
                    f"/projects/{PROJECT_ID}/protected_branches/{quote(ref, safe='')}"
                ).body,
                "branch protection",
            ),
            "branch protection",
        )
        exact(protection, "name", ref, "branch protection")
        if protection.get("allow_force_push") is not False:
            problems.append(
                "Protected branch allows force push or has unknown force-push policy"
            )
        push = items(protection.get("push_access_levels"), "push access levels")
        if not push or any(
            mapping(value, "push permission").get("access_level") != 0 for value in push
        ):
            problems.append(
                "Direct push to the tested protected branch is not denied to all roles"
            )
        observed_runners = {
            integer(job.get("runner_id"), "verified runner ID") for job in verified_jobs
        }
        for runner_id in sorted(observed_runners):
            if runner_id not in runners:
                problems.append(
                    "A gate ran on a runner outside the fixed trusted runner IDs"
                )
                continue
            runner = mapping(
                parse_json(fetch(f"/runners/{runner_id}").body, "runner metadata"),
                "runner metadata",
            )
            exact(runner, "id", runner_id, "runner metadata")
            if runner.get("access_level") != "ref_protected":
                problems.append("Gate runner is not limited to protected refs")
    except (SourceError, SourceUnavailable) as error:
        problems.append(str(error))
    return problems


def verify_pipeline(
    fetch: Fetcher,
    *,
    revision: str,
    pipeline_id: int,
    ref: str,
    policy: JsonObject,
    driver_sha256: str,
    lock_sha256: str,
) -> tuple[JsonObject, dict[str, bytes]]:
    blobs: dict[str, bytes] = {}
    result: JsonObject = {
        "record_type": "remote_ci_source_verification",
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "revision": revision,
        "pipeline_id": pipeline_id,
        "ref": ref,
        "status": "UNVERIFIED",
        "source_status": "UNVERIFIED",
        "trust_status": "UNVERIFIED",
        "permission_status": "UNKNOWN",
        "acceptance_eligible": False,
        "errors": [],
        "trust_issues": [],
        "job_history": [],
        "jobs": [],
        "limitations": [
            "Source verification does not certify AT-V2-004-07/08 permission denial and anti-deletion controls",
            "Configured trust identities and metadata do not prove independent approval or authorized rule changes",
        ],
    }
    try:
        if not re.fullmatch(r"[a-f0-9]{40}", revision) or any(
            not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in (driver_sha256, lock_sha256)
        ):
            raise SourceError(
                "Exact full revision, driver and lock SHA256 are required"
            )
        integer(pipeline_id, "pipeline ID")
        string(ref, "ref")
        project_policy = mapping(policy.get("project"), "fixed project policy")
        exact(project_policy, "id", PROJECT_ID, "fixed policy")
        exact(project_policy, "api_base", API_ORIGIN, "fixed policy")
        project_path = string(project_policy.get("path"), "fixed project path")
        if mapping(policy.get("required_jobs"), "required jobs") != REQUIRED_JOBS:
            raise SourceError("Fixed policy must retain all six mandatory P0 jobs")
        project = mapping(
            parse_json(fetch(f"/projects/{PROJECT_ID}").body, "project"), "project"
        )
        exact(project, "id", PROJECT_ID, "project")
        exact(project, "path_with_namespace", project_path, "project")
        pipeline = mapping(
            parse_json(
                fetch(f"/projects/{PROJECT_ID}/pipelines/{pipeline_id}").body,
                "pipeline",
            ),
            "pipeline",
        )
        result["pipeline"] = {
            field: pipeline.get(field)
            for field in (
                "id",
                "project_id",
                "sha",
                "ref",
                "status",
                "source",
                "web_url",
            )
        }
        for field, expected in (
            ("id", pipeline_id),
            ("project_id", PROJECT_ID),
            ("sha", revision),
            ("ref", ref),
        ):
            exact(pipeline, field, expected, "pipeline")
        branch = mapping(
            parse_json(
                fetch(
                    f"/projects/{PROJECT_ID}/repository/branches/{quote(ref, safe='')}"
                ).body,
                "branch",
            ),
            "branch",
        )
        exact(branch, "name", ref, "branch")
        exact(
            mapping(branch.get("commit"), "branch commit"),
            "id",
            revision,
            "branch commit",
        )
        jobs = pipeline_jobs(fetch, pipeline_id)
        history: list[JsonObject] = []
        latest: dict[str, JsonObject] = {}
        seen: set[int] = set()
        for job in jobs:
            job_id = integer(job.get("id"), "job ID")
            if job_id in seen:
                raise SourceError("Pipeline job pagination repeated a job ID")
            seen.add(job_id)
            name = string(job.get("name"), "job name")
            history.append(
                {"job_id": job_id, "job_name": name, "status": job.get("status")}
            )
            if name in REQUIRED_JOBS and (
                name not in latest or job_id > integer(latest[name].get("id"), "job ID")
            ):
                latest[name] = job
        result["job_history"] = history
        exact(pipeline, "status", "success", "pipeline")
        if set(latest) != set(REQUIRED_JOBS):
            raise SourceError("Pipeline is missing one or more mandatory P0 jobs")
        checked: list[JsonObject] = []
        result["jobs"] = checked
        for name in REQUIRED_JOBS:
            listed = latest[name]
            job_id = integer(listed.get("id"), "job ID")
            detail = mapping(
                parse_json(
                    fetch(f"/projects/{PROJECT_ID}/jobs/{job_id}").body, "job detail"
                ),
                "job detail",
            )
            exact(detail, "id", job_id, "job detail")
            exact(detail, "name", name, "job detail")
            exact(detail, "status", listed.get("status"), "job detail snapshot")
            checked.append(
                verify_job(
                    fetch,
                    detail,
                    revision=revision,
                    pipeline_id=pipeline_id,
                    ref=ref,
                    driver_sha256=driver_sha256,
                    lock_sha256=lock_sha256,
                    blobs=blobs,
                )
            )
        final_pipeline = mapping(
            parse_json(
                fetch(f"/projects/{PROJECT_ID}/pipelines/{pipeline_id}").body,
                "final pipeline",
            ),
            "final pipeline",
        )
        if any(
            final_pipeline.get(field) != pipeline.get(field)
            for field in ("id", "project_id", "sha", "ref", "status")
        ):
            result["final_pipeline"] = {
                field: final_pipeline.get(field)
                for field in ("id", "project_id", "sha", "ref", "status")
            }
            raise SourceUnavailable(
                "Pipeline changed during verification; exact current results must be queried again"
            )
        final_jobs = pipeline_jobs(fetch, pipeline_id)
        result["final_job_history"] = [
            {
                "job_id": job.get("id"),
                "job_name": job.get("name"),
                "status": job.get("status"),
            }
            for job in final_jobs
        ]
        before_jobs = {
            integer(job.get("id"), "job ID"): (
                job.get("name"),
                job.get("status"),
                job.get("allow_failure"),
            )
            for job in jobs
        }
        after_jobs = {
            integer(job.get("id"), "job ID"): (
                job.get("name"),
                job.get("status"),
                job.get("allow_failure"),
            )
            for job in final_jobs
        }
        if before_jobs != after_jobs or len(after_jobs) != len(final_jobs):
            raise SourceUnavailable(
                "Job/retry states changed during verification; exact current results must be queried again"
            )
        final_branch = mapping(
            parse_json(
                fetch(
                    f"/projects/{PROJECT_ID}/repository/branches/{quote(ref, safe='')}"
                ).body,
                "final branch",
            ),
            "final branch",
        )
        if (
            mapping(final_branch.get("commit"), "final branch commit").get("id")
            != revision
        ):
            raise SourceUnavailable(
                "Branch advanced during verification; old commit results cannot certify the current ref"
            )
        result["source_status"] = "PASS"
        trust_issues = verify_trust_metadata(
            fetch, policy, project, branch, ref, checked
        )
        result["trust_issues"] = trust_issues
        result["trust_status"] = "UNVERIFIED" if trust_issues else "METADATA_MATCHED"
        # AT-07/08 require real positive/negative permissions experiments. This
        # read-only command has no authority to promote metadata to acceptance.
    except SourceError as error:
        result["source_status"] = "FAIL"
        result["status"] = "FAIL"
        result["errors"] = [str(error)]
    except SourceUnavailable as error:
        result["errors"] = [str(error)]
    return result, blobs


def git_file(root: Path, revision: str, path: str) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise SourceError("A fixed full Git policy/revision pin is required")
    command = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if command.returncode:
        raise SourceUnavailable("Fixed Git policy or driver object is unavailable")
    return command.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--pipeline-id", required=True, type=int)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--policy-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.is_relative_to(root / "plan"):
        parser.error("Verification output must be outside normative plan inputs")
    if output.exists() or output.with_suffix("").exists():
        parser.error(
            "Use a new output path; previous verification evidence must be preserved"
        )
    try:
        policy_bytes = git_file(root, args.policy_revision, "security-policy.yaml")
        policy = mapping(yaml.safe_load(policy_bytes), "fixed policy")
        driver_bytes = git_file(root, args.revision, "scripts/ci/run_gate.py")
        lock_bytes = git_file(root, args.revision, "uv.lock")
        client = GitLabClient(os.environ.get("ANOVELOS_GITLAB_TOKEN", ""))
        result, blobs = verify_pipeline(
            client.fetch,
            revision=args.revision,
            pipeline_id=args.pipeline_id,
            ref=args.ref,
            policy=policy,
            driver_sha256=digest(driver_bytes),
            lock_sha256=digest(lock_bytes),
        )
        result["policy_revision"] = args.policy_revision
        result["policy_sha256"] = digest(policy_bytes)
        result["lock_sha256"] = digest(lock_bytes)
    except (SourceError, SourceUnavailable, yaml.YAMLError) as error:
        # YAML parser errors may include untrusted content, so keep them generic.
        reason = (
            "Fixed policy YAML could not be parsed"
            if isinstance(error, yaml.YAMLError)
            else str(error)
        )
        result = {
            "record_type": "remote_ci_source_verification",
            "schema_version": "1.0",
            "status": "UNVERIFIED",
            "source_status": "UNVERIFIED",
            "permission_status": "UNKNOWN",
            "acceptance_eligible": False,
            "errors": [reason],
        }
        blobs = {}
    result["queried_at"] = datetime.now(UTC).isoformat()
    result.update(
        project_id=PROJECT_ID,
        revision=args.revision,
        pipeline_id=args.pipeline_id,
        ref=args.ref,
        policy_revision=args.policy_revision,
    )
    storage = output.with_suffix("")
    storage.mkdir(parents=True, exist_ok=False)
    for name, content in blobs.items():
        destination = storage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    result["artifact_directory"] = str(storage)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "source_status": result["source_status"],
                "acceptance_eligible": False,
                "output": str(output),
            }
        )
    )
    return 1 if result["status"] == "FAIL" else 2


if __name__ == "__main__":
    sys.exit(main())
