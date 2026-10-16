"""Validate the exact P0 job set and hard failures; remote enforcement is separate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
JOBS = {
    "static",
    "unit",
    "schema_contract",
    "arch_fitness",
    "secret_dependency",
    "postgres_env",
}
POSTGRES = "postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652"


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(
    loader: UniqueLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("Duplicate YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def validate_configuration(source: str) -> list[str]:
    document = yaml.load(source, Loader=UniqueLoader)
    if not isinstance(document, dict):
        return ["CI mapping required"]
    errors = []
    if set(document) - JOBS - {"workflow", "stages", "variables", "default"}:
        errors.append(
            "Unknown includes/templates or top-level configuration require review"
        )
    for name in JOBS:
        job = document.get(name)
        if not isinstance(job, dict):
            errors.append("Missing mandatory job: " + name)
            continue
        if job.get("allow_failure") is not False:
            errors.append("Job must hard fail: " + name)
        if job.get("timeout") != "20 minutes":
            errors.append("Explicit job timeout required: " + name)
        if job.get("script") != [
            "uv run --locked python -B scripts/ci/run_gate.py " + name
        ]:
            errors.append("Mandatory command was replaced: " + name)
        permitted = {
            "stage",
            "timeout",
            "allow_failure",
            "script",
            "artifacts",
            "rules",
        }
        schedule = "always" if name == "secret_dependency" else "on_success"
        if job.get("rules") != [{"when": schedule}]:
            errors.append("Exact workflow-wide job inclusion required: " + name)
        if name == "secret_dependency":
            permitted.add("when")
            if job.get("when") != "always":
                errors.append("Security must run after upstream failures")
        if name == "postgres_env":
            permitted |= {"services", "variables"}
        if set(job) - permitted:
            errors.append("Unreviewed job inheritance or override: " + name)
        if any(key in job for key in ("only", "except", "after_script")):
            errors.append("Job trigger/result override requires review: " + name)
        if name != "secret_dependency" and "when" in job:
            errors.append("Job trigger/result override requires review: " + name)
    default = document.get("default", {})
    if "timeout" in default:
        errors.append("Timeout must be defined on each job")
    if default.get("image") != "python:3.12.14-bookworm":
        errors.append("Exact Python image required")
    if default.get("before_script") != [
        "python -m pip install --index-url https://pypi.org/simple uv==0.12.17",
        "uv --version",
        "uv sync --locked",
    ]:
        errors.append("Locked installation commands required")
    if document.get("variables", {}).get("GIT_DEPTH") != "0":
        errors.append("Full history required for secret gate")
    if document.get("workflow") != {
        "rules": [
            {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'},
            {
                "if": '$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS && $CI_PIPELINE_SOURCE == "push"',
                "when": "never",
            },
            {"if": "$CI_COMMIT_TAG"},
            {"if": "$CI_COMMIT_BRANCH"},
        ]
    }:
        errors.append("Pipeline workflow triggers changed")
    postgres = document.get("postgres_env", {})
    if postgres.get("services") != [{"name": POSTGRES, "alias": "postgres"}]:
        errors.append("Exact ADR PostgreSQL service identity required")
    return errors


def main() -> int:
    errors = validate_configuration((ROOT / ".gitlab-ci.yml").read_text())
    workflow = ROOT / ".github/workflows/v2-004.yml"
    if workflow.is_file() and not workflow.is_symlink():
        from github_configuration import validate_github_configuration

        errors += validate_github_configuration(
            yaml.load(workflow.read_text(), Loader=UniqueLoader)
        )
    else:
        errors.append("Missing mandatory GitHub workflow")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
