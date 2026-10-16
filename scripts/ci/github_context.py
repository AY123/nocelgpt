"""Validate native Actions source identity; this does not certify branch protection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path

HISTORY_REF = (
    "plan/validation/execution/V2-004/github-migration-20261016/HISTORY_BASELINE.json"
)
HISTORY_SHA256 = "5d4976cec8eaa86b3dd6febe41d86b5a4c299b5ec935ab717e6baf49652a66f1"

REPOSITORY = "AY123/nocelgpt"
REPOSITORY_ID = "1421585508"
WORKFLOW = ".github/workflows/v2-004.yml"
REF = "refs/heads/main"
GATES = {
    "static",
    "schema_contract",
    "unit",
    "arch_fitness",
    "secret_dependency",
    "postgres_env",
}


def validate_context(
    environment: Mapping[str, str], revision: str, gate: str
) -> dict[str, str]:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_REF": REF,
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/{WORKFLOW}@{REF}",
        "GITHUB_JOB": "postgres_env" if gate == "postgres_env" else "gates",
    }
    if gate not in GATES or any(environment.get(k) != v for k, v in expected.items()):
        raise ValueError("GITHUB_SOURCE_CONTEXT_MISMATCH")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", revision)
        or environment.get("GITHUB_SHA") != revision
        or environment.get("GITHUB_WORKFLOW_SHA") != revision
        or not all(
            re.fullmatch(r"[1-9][0-9]*", environment.get(k, ""))
            for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")
        )
    ):
        raise ValueError("GITHUB_REVISION_OR_RUN_MISMATCH")
    return {
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "run_id": environment["GITHUB_RUN_ID"],
        "run_attempt": environment["GITHUB_RUN_ATTEMPT"],
        "job_key": environment["GITHUB_JOB"],
        "workflow_ref": environment["GITHUB_WORKFLOW_REF"],
        "workflow_sha": revision,
        "ref_protected": environment.get("GITHUB_REF_PROTECTED", "unknown"),
        "permission_boundary": "NOT_VERIFIED_BY_ENVIRONMENT",
    }


def validate_history(required: object, available: list[str]) -> None:
    if (
        not isinstance(required, list)
        or not required
        or not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value)
            for value in required
        )
        or len(set(required)) != len(required)
        or not available
        or not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in available)
        or len(set(available)) != len(available)
        or not set(required).issubset(available)
    ):
        raise ValueError("GITHUB_COMPLETE_HISTORY_REQUIRED")


def main() -> None:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    context = validate_context(
        os.environ, revision, os.environ.get("ANOVELOS_GATE_NAME", "")
    )
    payload = Path(HISTORY_REF).read_bytes()
    if hashlib.sha256(payload).hexdigest() != HISTORY_SHA256:
        raise ValueError("GITHUB_HISTORY_BASELINE_CHANGED")
    history = json.loads(payload)
    if (
        subprocess.check_output(
            ["git", "rev-parse", "--is-shallow-repository"], text=True
        ).strip()
        != "false"
    ):
        raise ValueError("GITHUB_SHALLOW_CHECKOUT_REFUSED")
    available = subprocess.check_output(
        ["git", "rev-list", "--all"], text=True
    ).splitlines()
    validate_history(history.get("required_commits"), available)
    objects = subprocess.check_output(
        ["git", "rev-list", "--objects", "--all", "--missing=print"], text=True
    )
    if any(line.startswith("?") for line in objects.splitlines()):
        raise ValueError("GITHUB_HISTORY_OBJECTS_MISSING")
    context["available_history_commits"] = str(len(available))
    print(json.dumps({"status": "PASS", "source_context": context}))


if __name__ == "__main__":
    main()
