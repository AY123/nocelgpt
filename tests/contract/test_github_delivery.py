"""GitHub migration and mandatory-gate controls; all authority fixtures are synthetic."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_secret_exceptions import (
    REPOSITORY,
    ApprovalCase,
    encode,
    exceptions,
    git,
    sha,
)
from test_secret_exceptions import (
    approved_case as approved_case,
)

ROOT = Path(__file__).resolve().parents[2]


def module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/ci" / (name + ".py")
    )
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


context = module("github_context")
configuration = module("github_configuration")


def pin_migration(case: ApprovalCase, record: dict[str, Any]) -> None:
    ref = "records/migration.json"
    (case.root / ref).write_bytes(encode(record))
    git(case.root, "add", "records")
    git(
        case.root,
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "synthetic migration fixture",
    )
    revision = git(case.root, "rev-parse", "HEAD").decode().strip()
    case.config["repository_migration"] = {
        "ref": ref,
        "revision": revision,
        "blob_oid": git(case.root, "rev-parse", revision + ":" + ref).decode().strip(),
        "sha256": sha((case.root / ref).read_bytes()),
    }


@pytest.fixture
def migrated_case(approved_case: ApprovalCase) -> tuple[ApprovalCase, dict[str, Any]]:
    case = approved_case
    statement = case.root / "records/statement.txt"
    statement.write_text(
        "Synthetic owner migration statement; never production authority.\n"
    )
    record = {
        "record_type": "repository_migration_authority",
        "schema_version": 1,
        "actor": "Disposable Owner Fixture",
        "role": "PROJECT_OWNER",
        "decision": "APPROVED",
        "source": {"host": "gitlab.com", **REPOSITORY},
        "target": {
            "host": "github.com",
            "repository_id": 1421585508,
            "repository_path": "AY123/nocelgpt",
        },
        "approved_ledger_sha256": case.config["ledger_sha256"],
        "owner_statement_ref": "records/statement.txt",
        "owner_statement_sha256": sha(statement.read_bytes()),
    }
    pin_migration(case, record)
    git(
        case.root,
        "remote",
        "set-url",
        "origin",
        "https://github.com/AY123/nocelgpt.git",
    )
    return case, record


def test_exact_repository_migration_preserves_original_finding_approval(
    migrated_case: Any,
) -> None:
    case, _ = migrated_case
    result = case.consume()
    assert result["status"] == "PASS"
    assert len(result["approved_and_consumed"]) == len(case.findings)


def test_github_without_migration_authority_is_not_implicitly_trusted(
    migrated_case: Any,
) -> None:
    case, _ = migrated_case
    del case.config["repository_migration"]
    with pytest.raises(
        exceptions.ExceptionFailure, match="SECRET_EXCEPTION_REPOSITORY"
    ):
        case.consume()


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision", "PENDING"),
        ("role", "DEVELOPER"),
        ("actor", ""),
        (
            "source",
            {"host": "gitlab.com", "project_id": 999, "project_path": "other/project"},
        ),
        ("approved_ledger_sha256", "0" * 64),
        ("schema_version", True),
        ("owner_statement_sha256", "0" * 64),
    ],
)
def test_pinned_but_unauthorized_migration_fails(
    migrated_case: Any, field: str, value: Any
) -> None:
    case, record = migrated_case
    record[field] = value
    pin_migration(case, record)
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_migration_git_pin_cannot_be_replaced_by_worktree_record(
    migrated_case: Any,
) -> None:
    case, _ = migrated_case
    case.config["repository_migration"]["sha256"] = "0" * 64
    with pytest.raises(exceptions.ExceptionFailure, match="MIGRATION_PIN"):
        case.consume()


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/other/nocelgpt.git",
        "https://example.invalid/AY123/nocelgpt.git",
        "https://github.com/AY123/nocelgpt.git?extra=1",
    ],
)
def test_migration_does_not_authorize_other_repository(
    migrated_case: Any, url: str
) -> None:
    case, _ = migrated_case
    git(case.root, "remote", "set-url", "origin", url)
    with pytest.raises(exceptions.ExceptionFailure, match="REPOSITORY"):
        case.consume()


def test_github_runtime_id_must_match_authorized_target(
    migrated_case: Any, monkeypatch: Any
) -> None:
    case, _ = migrated_case
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY_ID", "999")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AY123/nocelgpt")
    with pytest.raises(exceptions.ExceptionFailure, match="MIGRATION_RUNTIME"):
        case.consume()


@pytest.fixture
def github_environment() -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "AY123/nocelgpt",
        "GITHUB_REPOSITORY_ID": "1421585508",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": "AY123/nocelgpt/.github/workflows/v2-004.yml@refs/heads/main",
        "GITHUB_JOB": "gates",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
    }


def test_exact_github_context_is_source_only_not_permission_acceptance(
    github_environment: Any,
) -> None:
    result = context.validate_context(github_environment, "a" * 40, "unit")
    assert result["run_id"] == "123"
    assert result["permission_boundary"] == "NOT_VERIFIED_BY_ENVIRONMENT"


def test_history_baseline_is_a_minimum_and_never_hides_new_history() -> None:
    context.validate_history(["a" * 40], ["a" * 40, "b" * 40])


@pytest.mark.parametrize(
    "required,available",
    [
        ([], ["a" * 40]),
        (["a" * 40], []),
        (["a" * 40], ["b" * 40]),
        (["a" * 40, "a" * 40], ["a" * 40]),
        ([True], ["a" * 40]),
        (["a" * 40], ["a" * 40, "unknown"]),
    ],
)
def test_missing_or_malformed_history_is_blocked(required: Any, available: Any) -> None:
    with pytest.raises(ValueError, match="COMPLETE_HISTORY"):
        context.validate_history(required, available)


@pytest.mark.parametrize(
    "field,value",
    [
        ("GITHUB_ACTIONS", "false"),
        ("GITHUB_REPOSITORY", "other/repo"),
        ("GITHUB_REPOSITORY_ID", "999"),
        ("GITHUB_SHA", "b" * 40),
        ("GITHUB_WORKFLOW_SHA", "b" * 40),
        ("GITHUB_REF", "refs/heads/other"),
        ("GITHUB_EVENT_NAME", "pull_request_target"),
        ("GITHUB_RUN_ID", "0"),
        ("GITHUB_RUN_ATTEMPT", "unknown"),
        ("GITHUB_JOB", "other"),
    ],
)
def test_wrong_github_context_fails_closed(
    github_environment: Any, field: str, value: str
) -> None:
    github_environment[field] = value
    with pytest.raises(ValueError):
        context.validate_context(github_environment, "a" * 40, "unit")


def workflow() -> dict[str, Any]:
    return yaml.safe_load((ROOT / ".github/workflows/v2-004.yml").read_text())  # type: ignore[no-any-return]


def test_real_actions_workflow_has_all_six_mandatory_gates() -> None:
    assert configuration.validate_github_configuration(workflow()) == []


def test_missing_github_workflow_cannot_fall_back_to_legacy_ci(
    tmp_path: Path, monkeypatch: Any
) -> None:
    checker = module("check_configuration")
    (tmp_path / ".gitlab-ci.yml").write_bytes((ROOT / ".gitlab-ci.yml").read_bytes())
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker.main() == 1


@pytest.mark.parametrize(
    "change",
    [
        "remove_security",
        "allow_failure",
        "conditional_job",
        "replace_command",
        "shallow_checkout",
        "skip_history_tags",
        "broad_token",
        "skip_artifacts",
        "unpin_action",
        "remove_postgres",
        "security_fail_fast",
        "push_trigger",
    ],
)
def test_weakened_actions_configuration_is_rejected(change: str) -> None:
    document = copy.deepcopy(workflow())
    gates = document["jobs"]["gates"]
    if change == "remove_security":
        gates["strategy"]["matrix"]["include"].pop()
    elif change == "allow_failure":
        gates["continue-on-error"] = True
    elif change == "conditional_job":
        gates["if"] = "false"
    elif change == "replace_command":
        gates["steps"][3]["run"] = "true"
    elif change == "shallow_checkout":
        gates["steps"][0]["with"]["fetch-depth"] = 1
    elif change == "skip_history_tags":
        gates["steps"][0]["with"]["fetch-tags"] = False
    elif change == "broad_token":
        document["permissions"] = "write-all"
    elif change == "skip_artifacts":
        gates["steps"].pop()
    elif change == "unpin_action":
        gates["steps"][0]["uses"] = "actions/checkout@main"
    elif change == "remove_postgres":
        del document["jobs"]["postgres_env"]["services"]
    elif change == "security_fail_fast":
        gates["strategy"]["fail-fast"] = True
    elif change == "push_trigger":
        document["on"] = {"push": None}
    assert configuration.validate_github_configuration(document)


@pytest.mark.parametrize("job", ["gates", "postgres_env"])
def test_container_ownership_trust_is_limited_to_checkout(job: str) -> None:
    document = yaml.safe_load((ROOT / ".github/workflows/v2-004.yml").read_text())
    step = document["jobs"][job]["steps"][1]
    assert step["run"].splitlines() == [
        'git config --global --add safe.directory "$GITHUB_WORKSPACE"',
        "python -I -B scripts/ci/github_context.py",
    ]
    assert configuration.validate_github_configuration(document) == []
    step["run"] = step["run"].replace('"$GITHUB_WORKSPACE"', "'*'")
    assert configuration.validate_github_configuration(document)
