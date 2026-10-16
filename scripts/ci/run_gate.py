"""Run P0 checks and retain real command results; receipts need online verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
GATES = {
    "static": "STATIC",
    "unit": "UNIT",
    "schema_contract": "SCHEMA_CONTRACT",
    "arch_fitness": "ARCH_FITNESS",
    "secret_dependency": "SECRET_DEPENDENCY",
    "postgres_env": "POSTGRES_ENV",
}
CHILD_ENVIRONMENT_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "UV_CACHE_DIR",
        "UV_PYTHON_INSTALL_DIR",
        "UV_PYTHON_DOWNLOADS",
        "UV_PYTHON",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_CERT_PATH",
        "DOCKER_TLS_VERIFY",
        "DOCKER_DEFAULT_PLATFORM",
        "DOCKER_API_VERSION",
        "CI",
        "GITLAB_CI",
        "CI_PROJECT_ID",
        "CI_PROJECT_PATH",
        "CI_PROJECT_DIR",
        "CI_COMMIT_SHA",
        "CI_COMMIT_REF_NAME",
        "CI_COMMIT_REF_PROTECTED",
        "CI_COMMIT_BRANCH",
        "CI_COMMIT_TAG",
        "CI_JOB_ID",
        "CI_JOB_NAME",
        "CI_PIPELINE_ID",
        "CI_PIPELINE_SOURCE",
        "CI_MERGE_REQUEST_ID",
        "CI_MERGE_REQUEST_IID",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME",
        "CI_MERGE_REQUEST_TARGET_BRANCH_NAME",
        "ANOVELOS_TEST_DSN",
        "GITHUB_ACTIONS",
        "GITHUB_REPOSITORY",
        "GITHUB_REPOSITORY_ID",
    }
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def commands_for(job: str, output: Path) -> list[list[str]]:
    """Actual command plans are code-reviewed with the gate driver."""
    python = [sys.executable, "-B"]
    target = str(output.relative_to(ROOT))
    if job == "static":
        paths = ["src/anovel", "scripts/ci"]
        test_paths = [
            "tests/contract/test_delivery_gates.py",
            "tests/integration/test_postgres_ci_service.py",
        ]
        return [
            python + ["scripts/ci/check_configuration.py"],
            python + ["-m", "ruff", "format", "--check", *paths, *test_paths],
            python + ["-m", "ruff", "check", "--select", "F,E9,I", *paths, *test_paths],
            python
            + ["-m", "mypy", "--strict", "--cache-dir", "dist/cache/mypy", *paths],
            python + ["scripts/ci/check_syntax.py"],
        ]
    if job == "unit":
        return [
            python
            + [
                "scripts/ci/bootstrap_scanners.py",
                "--output-dir",
                "dist/tools/gitleaks-8.21.2",
                "--reuse-verified",
            ],
            python
            + [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/contract",
                "tests/integration/test_repository_bootstrap.py",
                "--junitxml=" + target + "/junit.xml",
            ],
        ]
    if job == "schema_contract":
        return [
            python
            + ["scripts/check_governance.py", "--output-dir", target + "/governance"]
        ]
    if job == "arch_fitness":
        return [
            python
            + [
                "scripts/task_execution.py",
                "check",
                "--task",
                "V2-004",
                "--action",
                "IMPLEMENT",
                "--output",
                target + "/action-entry.json",
            ],
            python
            + [
                "scripts/check_architecture.py",
                "--output",
                target + "/architecture.json",
            ],
            python
            + [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture",
                "--junitxml=" + target + "/junit.xml",
            ],
        ]
    if job == "secret_dependency":
        return [
            python
            + [
                "scripts/ci/bootstrap_scanners.py",
                "--output-dir",
                "dist/tools/gitleaks-8.21.2",
                "--reuse-verified",
            ],
            python
            + ["scripts/ci/check_security.py", "--output-dir", target + "/security"],
        ]
    if job == "postgres_env":
        return [
            python
            + [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-s",
                "tests/integration/test_postgres_ci_service.py",
                "--junitxml=" + target + "/junit.xml",
            ]
        ]
    raise ValueError("Unregistered gate")


def child_environment(
    root: Path, source: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Test failure reprs must not expose the gate parent's API/authentication env."""
    supplied = os.environ if source is None else source
    environment = {
        key: value for key, value in supplied.items() if key in CHILD_ENVIRONMENT_KEYS
    }
    # Local Docker sockets and unauthenticated endpoints are usable. Userinfo can
    # contain passwords; never forward that value into a pytest fixture repr.
    docker_host = supplied.get("DOCKER_HOST")
    if docker_host:
        try:
            host = urlsplit(docker_host)
            if host.scheme in {"unix", "npipe", "tcp", "http", "https", "ssh"} and (
                host.username is None
                and host.password is None
                and not host.query
                and not host.fragment
            ):
                environment["DOCKER_HOST"] = docker_host
        except ValueError:
            pass
    # Proxy/index/auth variables are intentionally absent, including URLs that
    # may embed credentials. Downloads require direct public network access.
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        RUFF_CACHE_DIR=str(root / "dist/cache/ruff"),
        MYPY_CACHE_DIR=str(root / "dist/cache/mypy"),
    )
    return environment


def execute_commands(
    commands: list[list[str]], output: Path, *, root: Path = ROOT, timeout: float = 1100
) -> tuple[list[dict[str, Any]], int]:
    """No shell, no allow-failure wrapper, preserve startup/timeout failures."""
    records: list[dict[str, Any]] = []
    environment = child_environment(root)
    for number, argv in enumerate(commands, 1):
        try:
            result = subprocess.run(
                argv, cwd=root, env=environment, capture_output=True, timeout=timeout
            )
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = (
                124,
                exc.stdout or b"",
                (exc.stderr or b"") + b"\nCommand timeout\n",
            )
        except OSError as exc:
            code, stdout, stderr = 127, b"", str(exc).encode()
        row: dict[str, Any] = {"argv": argv, "exit_code": code}
        for name, value in (("stdout", stdout), ("stderr", stderr)):
            file = output / f"command-{number:02d}.{name}.log"
            file.write_bytes(value)
            row[name] = {
                "ref": file.relative_to(root).as_posix(),
                "sha256": digest(value),
            }
        records.append(row)
        print(f"COMMAND {number} EXIT {code}", flush=True)
        if code:
            return records, code if code > 0 else 128 - code
    return records, 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=GATES)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    output = args.output_dir or ROOT / "dist/ci" / args.job
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "dist"):
        parser.error("Use a new directory under dist; never overwrite prior artifacts")
    output.mkdir(parents=True)
    driver_hash = digest(Path(__file__).read_bytes())
    receipt: dict[str, Any] = {
        "record_type": "ci_gate_receipt",
        "schema_version": "1.0",
        "job_name": args.job,
        "gate": GATES[args.job],
        "status": "FAIL",
        "revision": git("rev-parse", "HEAD"),
        "project_id": os.getenv("CI_PROJECT_ID"),
        "pipeline_id": os.getenv("CI_PIPELINE_ID"),
        "job_id": os.getenv("CI_JOB_ID"),
        "driver_sha256": driver_hash,
        "source_kind": "UNVERIFIED_GITLAB_ENVIRONMENT"
        if os.getenv("GITLAB_CI") == "true"
        else "LOCAL",
        "python": platform.python_version(),
        "lock_sha256": digest((ROOT / "uv.lock").read_bytes()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "commands": [],
        "artifacts": [],
        "errors": [],
        "not_certified": ["remote provenance", "permission boundary", "P0 exit"],
    }
    print(f"ANOVELOS_GATE_START {args.job} {driver_hash}", flush=True)
    code = 2
    try:
        if platform.python_version() != "3.12.14":
            raise ValueError("Exact ADR Python version required")
        if os.getenv("GITHUB_ACTIONS") == "true":
            from github_context import validate_context

            if os.getenv("GITLAB_CI") == "true":
                raise ValueError("Ambiguous CI platform")
            receipt["source_kind"] = "UNVERIFIED_GITHUB_ENVIRONMENT"
            receipt["github"] = validate_context(
                os.environ, receipt["revision"], args.job
            )
        if os.getenv("GITLAB_CI") == "true":
            if receipt["revision"] != os.getenv("CI_COMMIT_SHA"):
                raise ValueError("Actual checkout does not match CI_COMMIT_SHA")
            if (
                os.getenv("CI_JOB_NAME") != args.job
                or os.getenv("CI_PROJECT_ID") != "86656946"
            ):
                raise ValueError("GitLab job/project context mismatch")
        records, code = execute_commands(commands_for(args.job, output), output)
        receipt["commands"] = records
        receipt["status"] = "PASS" if code == 0 else "FAIL"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        receipt["errors"].append(f"{type(exc).__name__}: {exc}")
    receipt["exit_code"] = code
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt["artifacts"] = [
        {"ref": file.relative_to(ROOT).as_posix(), "sha256": digest(file.read_bytes())}
        for file in sorted(output.rglob("*"))
        if file.is_file() and not file.is_symlink()
    ]
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"ANOVELOS_GATE_END {args.job} {receipt['status']}", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
