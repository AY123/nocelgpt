"""V2-004 local controls; synthetic API tests cannot certify remote permissions."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_ci_module(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/ci" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runner = load_ci_module("run_gate")
configuration = load_ci_module("check_configuration")


@pytest.mark.parametrize("failure", [1, 2, 17])
def test_real_subprocess_failure_preserved_and_stops_later_command(tmp_path, failure):
    output = tmp_path / "dist/result"
    output.mkdir(parents=True)
    records, code = runner.execute_commands(
        [
            [
                sys.executable,
                "-c",
                f"print('controlled failure'); raise SystemExit({failure})",
            ],
            [
                sys.executable,
                "-c",
                "from pathlib import Path;Path('should-not-run').touch()",
            ],
        ],
        output,
        root=tmp_path,
    )
    assert code == failure
    assert len(records) == 1 and records[0]["exit_code"] == failure
    assert not (tmp_path / "should-not-run").exists()
    assert (
        output / "command-01.stdout.log"
    ).read_text().strip() == "controlled failure"


def test_real_subprocess_success_retains_raw_logs_and_hashes(tmp_path):
    output = tmp_path / "dist/result"
    output.mkdir(parents=True)
    records, code = runner.execute_commands(
        [[sys.executable, "-c", "print('actual positive')"]], output, root=tmp_path
    )
    assert code == 0 and len(records) == 1
    log = tmp_path / records[0]["stdout"]["ref"]
    assert log.read_text().strip() == "actual positive"
    assert runner.digest(log.read_bytes()) == records[0]["stdout"]["sha256"]


def test_startup_failure_and_timeout_fail_closed(tmp_path):
    output = tmp_path / "dist/result"
    output.mkdir(parents=True)
    records, code = runner.execute_commands(
        [["/does/not/exist"]], output, root=tmp_path
    )
    assert code == 127 and records[0]["exit_code"] == 127
    records, code = runner.execute_commands(
        [[sys.executable, "-c", "import time;time.sleep(10)"]],
        output,
        root=tmp_path,
        timeout=0.05,
    )
    assert code == 124 and records[0]["exit_code"] == 124


def test_current_pipeline_contract_and_each_required_command_present():
    assert (
        configuration.validate_configuration((ROOT / ".gitlab-ci.yml").read_text())
        == []
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "delete",
        "allowed_failure",
        "command",
        "trigger",
        "postgres",
        "shallow",
        "include",
        "extends",
        "timeout_missing",
        "timeout_longer",
        "timeout_default",
        "security_skipped",
    ],
)
def test_bad_pipeline_configuration_cannot_pass(mutation):
    document = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())
    if mutation == "delete":
        del document["static"]
    elif mutation == "allowed_failure":
        document["static"]["allow_failure"] = True
    elif mutation == "command":
        document["static"]["script"] = ["true"]
    elif mutation == "trigger":
        document["static"]["rules"] = [{"when": "never"}]
    elif mutation == "postgres":
        document["postgres_env"]["services"][0]["name"] = "postgres:17.0"
    elif mutation == "include":
        document["include"] = "candidate-can-replace-gates.yml"
    elif mutation == "extends":
        document["static"]["extends"] = ".override"
    elif mutation == "timeout_missing":
        del document["unit"]["timeout"]
    elif mutation == "timeout_longer":
        document["unit"]["timeout"] = "40 minutes"
    elif mutation == "timeout_default":
        document["default"]["timeout"] = document["unit"].pop("timeout")
    elif mutation == "security_skipped":
        del document["secret_dependency"]["when"]
    else:
        document["variables"]["GIT_DEPTH"] = "1"
    assert configuration.validate_configuration(yaml.safe_dump(document))


def test_duplicate_yaml_key_is_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        configuration.validate_configuration("static: {}\nstatic: {}\n")


@pytest.mark.parametrize("name", sorted(configuration.JOBS))
@pytest.mark.parametrize(
    "mutation", ["missing", "condition", "manual", "allowed_failure"]
)
def test_workflow_gate_inclusion_cannot_be_excluded(name, mutation):
    document = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())
    if mutation == "missing":
        del document[name]["rules"]
    elif mutation == "condition":
        document[name]["rules"][0]["if"] = '$CI_PIPELINE_SOURCE == "push"'
    elif mutation == "manual":
        document[name]["rules"][0]["when"] = "manual"
    else:
        document[name]["rules"][0]["allow_failure"] = True
    assert configuration.validate_configuration(yaml.safe_dump(document))


def test_missing_real_postgres_dsn_is_failure():
    # Exercise the actual existing runtime probe; never use SQLite or skip.
    import os

    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("ANOVELOS_TEST_")
    }
    result = subprocess.run(
        [sys.executable, "-B", "scripts/check_postgres.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
    )
    assert result.returncode == 2
    assert not result.stdout


def test_gate_output_cannot_overwrite_sources_or_prior_receipt(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "scripts/ci/run_gate.py",
            "static",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
    )
    assert result.returncode == 2
    assert b"never overwrite" in result.stderr


@pytest.fixture
def architecture_task(tmp_path, monkeypatch):
    # Action behavior must not depend on whether the live task is already done.
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    registry = tmp_path / "plan/machine/implementation-backlog.yaml"
    registry.parent.mkdir(parents=True)
    packet = tmp_path / "plan/validation/execution/V2-004/packet.yaml"
    packet.parent.mkdir(parents=True)
    task = {
        "task_id": "V2-004",
        "status": "IMPLEMENTED",
        "execution_packet_ref": "validation/execution/V2-004/packet.yaml",
    }
    binding = {
        "scope_revision": "a" * 40,
        "scope_ref": "plan/validation/scope.json",
        "review_revision": "b" * 40,
        "review_ref": "plan/validation/review.json",
    }
    registry.write_text(yaml.safe_dump({"tasks": [task]}))
    packet.write_text(
        yaml.safe_dump(
            {
                "record_type": "task_execution_packet",
                "task_id": "V2-004",
                "action": "IMPLEMENT",
                "change_review": binding,
            }
        )
    )
    return registry, packet, task, binding


def test_production_architecture_and_action_entry_are_actual_commands(
    architecture_task,
):
    # Active implementation still needs the original restricted-action entry.
    commands = runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")
    assert any("scripts/check_architecture.py" in command for command in commands)
    assert any(
        "scripts/task_execution.py" in command and "IMPLEMENT" in command
        for command in commands
    )
    commands = runner.commands_for(
        "schema_contract", runner.ROOT / "dist/ci/schema_contract"
    )
    assert any("scripts/check_governance.py" in command for command in commands)


@pytest.mark.parametrize("status", ["VERIFIED", "CLOSED"])
def test_completed_architecture_task_audits_exact_pins_and_keeps_all_checks(
    architecture_task, status
):
    registry, _, task, binding = architecture_task
    task["status"] = status
    registry.write_text(yaml.safe_dump({"tasks": [task]}))
    commands = runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")
    assert len(commands) == 3
    assert commands[0][2:5] == ["scripts/check_changes.py", "--task", "V2-004"]
    for key, value in binding.items():
        assert commands[0][commands[0].index("--" + key.replace("_", "-")) + 1] == value
    assert "scripts/check_architecture.py" in commands[1]
    assert "tests/architecture" in commands[2]
    assert "IMPLEMENT" not in commands[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_task",
        "duplicate_task",
        "null_status",
        "missing_packet",
        "outside_packet",
        "wrong_task",
        "missing_binding",
        "missing_scope",
        "null_review",
        "empty_review",
    ],
)
def test_completed_architecture_entry_rejects_missing_or_bad_evidence(
    architecture_task, mutation
):
    registry, packet, task, binding = architecture_task
    task["status"] = "CLOSED"
    document = {
        "record_type": "task_execution_packet",
        "task_id": "V2-004",
        "action": "IMPLEMENT",
        "change_review": binding,
    }
    if mutation == "null_status":
        task["status"] = None
    elif mutation == "missing_packet":
        task["execution_packet_ref"] = None
    elif mutation == "outside_packet":
        task["execution_packet_ref"] = "validation/../../README.md"
    elif mutation == "wrong_task":
        document["task_id"] = "V2-005"
    elif mutation == "missing_binding":
        document.pop("change_review")
    elif mutation == "missing_scope":
        binding.pop("scope_revision")
    elif mutation == "null_review":
        binding["review_revision"] = None
    elif mutation == "empty_review":
        binding["review_ref"] = ""
    tasks = [] if mutation == "missing_task" else [task]
    if mutation == "duplicate_task":
        tasks.append(task.copy())
    registry.write_text(yaml.safe_dump({"tasks": tasks}))
    packet.write_text(yaml.safe_dump(document))
    with pytest.raises(ValueError):
        runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")


@pytest.fixture
def current_architecture_task(architecture_task):
    registry, _, historical, binding = architecture_task
    historical["status"] = "CLOSED"
    current = {
        "task_id": "V2-005",
        "status": "IN_PROGRESS",
        "execution_packet_ref": "validation/execution/V2-005/packet.yaml",
    }
    packet = runner.ROOT / "plan" / current["execution_packet_ref"]
    packet.parent.mkdir(parents=True)
    packet.write_text(
        yaml.safe_dump(
            {
                "record_type": "task_execution_packet",
                "task_id": "V2-005",
                "action": "IMPLEMENT",
                "change_review": binding,
            }
        )
    )
    registry.write_text(yaml.safe_dump({"tasks": [historical, current]}))
    return registry, packet, historical, current, binding


@pytest.mark.parametrize("status", ["IN_PROGRESS", "IMPLEMENTED"])
@pytest.mark.parametrize("review_required", [False, True])
def test_current_task_uses_restricted_entry_and_packet_bindings(
    current_architecture_task, status, review_required
):
    registry, packet, historical, current, binding = current_architecture_task
    current["status"] = status
    if not review_required:
        del binding["review_revision"]
        del binding["review_ref"]
        document = yaml.safe_load(packet.read_text())
        document["change_review"] = binding
        packet.write_text(yaml.safe_dump(document))
    registry.write_text(yaml.safe_dump({"tasks": [historical, current]}))
    commands = runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")
    assert commands[0] == [
        sys.executable,
        "-B",
        "scripts/task_execution.py",
        "check",
        "--task",
        "V2-005",
        "--action",
        "IMPLEMENT",
        "--output",
        "dist/ci/arch_fitness/action-entry.json",
    ]
    assert len(commands) == 3
    assert "scripts/check_architecture.py" in commands[1]
    assert "tests/architecture" in commands[2]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_packet",
        "missing_file",
        "outside_packet",
        "symlink_packet",
        "template",
        "wrong_task",
        "wrong_action",
        "missing_binding",
        "missing_scope_revision",
        "missing_scope_ref",
        "bad_scope_revision",
        "absolute_scope_ref",
        "escaping_scope_ref",
        "missing_review_revision",
        "missing_review_ref",
        "null_review",
        "empty_review",
        "bad_review_revision",
    ],
)
def test_current_task_rejects_invalid_packet_without_falling_back_to_closed_task(
    current_architecture_task, mutation
):
    registry, packet, historical, current, _ = current_architecture_task
    document = yaml.safe_load(packet.read_text())
    binding = document["change_review"]
    if mutation == "missing_packet":
        current["execution_packet_ref"] = None
    elif mutation == "outside_packet":
        current["execution_packet_ref"] = "validation/../../README.md"
    elif mutation == "template":
        document["record_type"] = "execution_packet_template"
    elif mutation == "wrong_task":
        document["task_id"] = "V2-004"
    elif mutation == "wrong_action":
        document["action"] = "PREPARE"
    elif mutation == "missing_binding":
        document.pop("change_review")
    elif mutation.startswith("missing_") and mutation not in {"missing_file"}:
        binding.pop(mutation.removeprefix("missing_"))
    elif mutation == "bad_scope_revision":
        binding["scope_revision"] = "not-a-pinned-commit"
    elif mutation == "absolute_scope_ref":
        binding["scope_ref"] = "/tmp/unchecked.json"
    elif mutation == "escaping_scope_ref":
        binding["scope_ref"] = "../unchecked.json"
    elif mutation == "null_review":
        binding["review_revision"] = None
    elif mutation == "empty_review":
        binding["review_ref"] = ""
    elif mutation == "bad_review_revision":
        binding["review_revision"] = "not-a-pinned-commit"
    registry.write_text(yaml.safe_dump({"tasks": [historical, current]}))
    packet.write_text(yaml.safe_dump(document))
    if mutation in {"missing_file", "symlink_packet"}:
        packet.unlink()
        if mutation == "symlink_packet":
            packet.symlink_to(runner.ROOT / "plan" / historical["execution_packet_ref"])
    with pytest.raises(ValueError):
        runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")


@pytest.mark.parametrize("second_status", ["IN_PROGRESS", "IMPLEMENTED"])
def test_multiple_active_tasks_are_rejected(current_architecture_task, second_status):
    registry, _, historical, current, _ = current_architecture_task
    historical["status"] = second_status
    registry.write_text(yaml.safe_dump({"tasks": [historical, current]}))
    with pytest.raises(ValueError, match="ambiguous"):
        runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")


def test_environment_cannot_select_task_or_override_packet_scope(
    current_architecture_task, monkeypatch
):
    monkeypatch.setenv("ANOVELOS_GATE_TASK", "V2-004")
    monkeypatch.setenv("ANOVELOS_SCOPE_REVISION", "c" * 40)
    monkeypatch.setenv("ANOVELOS_REVIEW_REVISION", "d" * 40)
    commands = runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")
    assert commands[0][commands[0].index("--task") + 1] == "V2-005"
    assert "--scope-revision" not in commands[0]
    assert "--review-revision" not in commands[0]
    assert runner.child_environment(runner.ROOT).get("ANOVELOS_GATE_TASK") is None


@pytest.mark.parametrize(
    "mutation", ["non_object", "bad_id", "bad_status", "duplicate"]
)
def test_malformed_task_registry_cannot_hide_active_task(
    current_architecture_task, mutation
):
    registry, _, historical, current, _ = current_architecture_task
    tasks = [historical, current]
    if mutation == "non_object":
        tasks.append("not-a-task")
    elif mutation == "bad_id":
        current["task_id"] = "unregistered-task"
    elif mutation == "bad_status":
        current["status"] = "READY"
    else:
        tasks.append(current.copy())
    registry.write_text(yaml.safe_dump({"tasks": tasks}))
    with pytest.raises(ValueError):
        runner.commands_for("arch_fitness", runner.ROOT / "dist/ci/arch_fitness")


"""Synthetic API controls cover logic; they are not real CI/permission evidence."""

import copy
import json
import os
from pathlib import Path
from urllib.parse import quote

import pytest

remote = load_ci_module("verify_remote")

SOURCE_REVISION = "a" * 40
SOURCE_DRIVER_HASH = "b" * 64
SOURCE_LOCK_HASH = "d" * 64
SOURCE_PIPELINE_ID = 91
SOURCE_RUNNER_TAG = "anovel-protected-acceptance"
SOURCE_PYTHON = "/builds/ayitnovel/ainovelos/.venv/bin/python"
SOURCE_RESULT_PATHS = {
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


def source_response(value):
    return remote.ApiResponse(json.dumps(value).encode(), {"x-next-page": ""})


def source_fixture():
    project = remote.PROJECT_ID
    policy = {
        "project": {
            "id": project,
            "api_base": remote.API_ORIGIN,
            "path": "ayitnovel/ainovelos",
        },
        "required_jobs": remote.REQUIRED_JOBS,
        "trusted_execution": {
            "runner_ids": [],
            "ci_config_path": None,
            "protected_ref": None,
        },
    }
    pipeline = {
        "id": SOURCE_PIPELINE_ID,
        "project_id": project,
        "sha": SOURCE_REVISION,
        "ref": "dev_gpt",
        "status": "success",
    }
    responses = {
        f"/projects/{project}": source_response(
            {
                "id": project,
                "path_with_namespace": "ayitnovel/ainovelos",
                "ci_config_path": None,
                "only_allow_merge_if_pipeline_succeeds": True,
            }
        ),
        f"/projects/{project}/pipelines/{SOURCE_PIPELINE_ID}": source_response(
            pipeline
        ),
        f"/projects/{project}/repository/branches/dev_gpt": source_response(
            {"name": "dev_gpt", "commit": {"id": SOURCE_REVISION}, "protected": False}
        ),
    }
    jobs = []
    for job_id, (name, gate) in enumerate(remote.REQUIRED_JOBS.items(), start=101):
        job = {
            "id": job_id,
            "name": name,
            "status": "success",
            "allow_failure": False,
            "ref": "dev_gpt",
            "commit": {"id": SOURCE_REVISION},
            "pipeline": copy.deepcopy(pipeline),
            "runner": {"id": 88},
        }
        jobs.append(job)
        responses[f"/projects/{project}/jobs/{job_id}"] = source_response(job)
        responses[f"/projects/{project}/jobs/{job_id}/trace"] = remote.ApiResponse(
            f"ANOVELOS_GATE_START {name} {SOURCE_DRIVER_HASH}\n"
            f"ANOVELOS_GATE_END {name} PASS\n".encode(),
            {},
        )
        commands = []
        artifacts = []

        def retain(ref, content):
            descriptor = {"ref": ref, "sha256": remote.digest(content)}
            path = quote(ref, safe="")
            responses[f"/projects/{project}/jobs/{job_id}/artifacts/{path}"] = (
                remote.ApiResponse(content, {})
            )
            artifacts.append(descriptor)
            return descriptor

        if name == "arch_fitness":
            # This synthetic GitLab source models the historical implementation
            # receipt, not the now-completed task in the live working copy.
            source_commands = [
                [
                    sys.executable,
                    "-B",
                    "scripts/task_execution.py",
                    "check",
                    "--task",
                    "V2-004",
                    "--action",
                    "IMPLEMENT",
                    "--output",
                    "dist/ci/arch_fitness/action-entry.json",
                ],
                [
                    sys.executable,
                    "-B",
                    "scripts/check_architecture.py",
                    "--output",
                    "dist/ci/arch_fitness/architecture.json",
                ],
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "tests/architecture",
                    "--junitxml=dist/ci/arch_fitness/junit.xml",
                ],
            ]
        elif name == "postgres_env":
            # Frozen GitLab-era receipt. V2-009 extends the current GitHub gate.
            source_commands = [
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-s",
                    "tests/integration/test_postgres_ci_service.py",
                    "--junitxml=dist/ci/postgres_env/junit.xml",
                ]
            ]
        else:
            source_commands = runner.commands_for(name, ROOT / "dist/ci" / name)
        for number, argv in enumerate(source_commands, 1):
            commands.append(
                {
                    "argv": [SOURCE_PYTHON, *argv[1:]],
                    "exit_code": 0,
                    "stdout": retain(
                        f"dist/ci/{name}/command-{number:02d}.stdout.log", b"passed\n"
                    ),
                    "stderr": retain(
                        f"dist/ci/{name}/command-{number:02d}.stderr.log", b""
                    ),
                }
            )
        for ref in SOURCE_RESULT_PATHS[name]:
            # Safe synthetic bytes exercise required references/hash coverage;
            # this fixture is not an actual test/scanner result or CI acceptance.
            retain(f"dist/ci/{name}/{ref}", b"synthetic result bytes\n")
        receipt = {
            "record_type": "ci_gate_receipt",
            "schema_version": "1.0",
            "gate": gate,
            "job_name": name,
            "status": "PASS",
            "revision": SOURCE_REVISION,
            "project_id": str(project),
            "pipeline_id": str(SOURCE_PIPELINE_ID),
            "job_id": str(job_id),
            "driver_sha256": SOURCE_DRIVER_HASH,
            "lock_sha256": SOURCE_LOCK_HASH,
            "python": "3.12.14",
            "source_kind": "UNVERIFIED_GITLAB_ENVIRONMENT",
            "exit_code": 0,
            "errors": [],
            "commands": commands,
            "artifacts": artifacts,
        }
        path = quote(f"dist/ci/{name}/receipt.json", safe="")
        responses[f"/projects/{project}/jobs/{job_id}/artifacts/{path}"] = (
            source_response(receipt)
        )
    jobs_path = (
        f"/projects/{project}/pipelines/{SOURCE_PIPELINE_ID}/jobs"
        "?include_retried=true&per_page=100&page=1"
    )
    responses[jobs_path] = source_response(jobs)
    return policy, responses, jobs_path


def source_verify(policy, responses):
    def fetch(path):
        if path not in responses:
            raise remote.SourceUnavailable("Synthetic source unavailable")
        return responses[path]

    return remote.verify_pipeline(
        fetch,
        revision=SOURCE_REVISION,
        pipeline_id=SOURCE_PIPELINE_ID,
        ref="dev_gpt",
        policy=policy,
        driver_sha256=SOURCE_DRIVER_HASH,
        lock_sha256=SOURCE_LOCK_HASH,
    )


def source_mutate(responses, path, mutate):
    value = json.loads(responses[path].body)
    mutate(value)
    responses[path] = source_response(value)


def test_synthetic_source_positive_keeps_actual_permission_unknown():
    policy, responses, _ = source_fixture()
    result, blobs = source_verify(policy, responses)
    assert result["source_status"] == "PASS"
    assert result["status"] == result["trust_status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False
    assert len(result["jobs"]) == 6
    assert blobs["job-101/dist/ci/static/command-01.stdout.log"] == b"passed\n"


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_id", 1),
        ("sha", "c" * 40),
        ("ref", "dev_cc"),
        ("status", "canceled"),
        ("status", "failed"),
        ("status", "running"),
    ],
)
def test_remote_source_rejects_wrong_or_incomplete_pipeline(field, value):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/pipelines/{SOURCE_PIPELINE_ID}"
    source_mutate(responses, path, lambda record: record.update({field: value}))
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "999"),
        ("revision", "c" * 40),
        ("driver_sha256", "c" * 64),
        ("gate", "UNIT"),
        ("status", "FAIL"),
        ("lock_sha256", "e" * 64),
        ("python", "3.13.14"),
        ("source_kind", "LOCAL"),
        ("exit_code", 1),
        ("exit_code", False),
        ("errors", ["controlled execution error"]),
    ],
)
def test_remote_source_rejects_receipt_identity_forgery(field, value):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"
    source_mutate(responses, path, lambda record: record.update({field: value}))
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


@pytest.mark.parametrize(
    "field,value",
    [("argv", []), ("argv", ["python", ""]), ("exit_code", 1), ("exit_code", False)],
)
def test_remote_source_rejects_empty_or_failed_command_receipt(field, value):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"
    source_mutate(
        responses, path, lambda record: record["commands"][0].update({field: value})
    )
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


@pytest.mark.parametrize("name", remote.REQUIRED_JOBS)
def test_remote_source_fixed_command_contract_matches_actual_driver(
    name, architecture_task
):
    # Preserve the historical GitLab implementation receipt contract separately
    # from the completed-task audit path tested above.
    actual = runner.commands_for(name, runner.ROOT / "dist/ci" / name)
    if name == "postgres_env":
        legacy = [
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-s",
            "tests/integration/test_postgres_ci_service.py",
            "--junitxml=dist/ci/postgres_env/junit.xml",
        ]
        assert remote.command_tails(name) == [legacy]
        assert [argv[1:] for argv in actual] == [
            legacy[:-1]
            + [
                "tests/integration/test_v2_009.py",
                "tests/integration/test_v2_010.py",
                "tests/integration/test_v2_011.py",
                "tests/integration/test_v2_012.py",
                "tests/integration/test_v2_015_postgres.py",
                "tests/integration/test_v2_016_postgres.py",
                legacy[-1],
            ]
        ]
    else:
        assert [argv[1:] for argv in actual] == remote.command_tails(name)


@pytest.mark.parametrize(
    "mutation", ["replace", "delete", "append", "reorder", "option", "output"]
)
def test_remote_source_rejects_command_plan_changes(mutation):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/102/artifacts/{quote('dist/ci/unit/receipt.json', safe='')}"

    def mutate(record):
        commands = record["commands"]
        if mutation == "replace":
            commands[0]["argv"] = [SOURCE_PYTHON, "-B", "-c", "pass"]
        elif mutation == "delete":
            commands.pop()
        elif mutation == "append":
            commands.append(copy.deepcopy(commands[-1]))
        elif mutation == "reorder":
            commands.reverse()
        elif mutation == "option":
            commands[1]["argv"].remove("no:cacheprovider")
        else:
            commands[1]["argv"][-1] = "--junitxml=dist/ci/unit/other.xml"

    source_mutate(responses, path, mutate)
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "FAIL"
    assert result["acceptance_eligible"] is False


@pytest.mark.parametrize(
    "executable",
    [
        "python",
        "/usr/bin/python",
        "//builds/project/.venv/bin/python",
        "/builds/../project/.venv/bin/python",
        "/builds//project/.venv/bin/python",
        "/builds/project/.venv/bin/./python",
        "/builds/project\\.venv/bin/python",
        "/builds/project/.venv/bin/python\0",
    ],
)
def test_remote_source_rejects_unsafe_or_unexpected_interpreter(executable):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"
    source_mutate(
        responses,
        path,
        lambda record: record["commands"][0]["argv"].__setitem__(0, executable),
    )
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_accepts_normalized_runner_project_python_path():
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"

    def relocate(record):
        for command in record["commands"]:
            command["argv"][0] = "/builds/runner-slot/project/.venv/bin/python"

    source_mutate(responses, path, relocate)
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False


@pytest.mark.parametrize("name", remote.REQUIRED_JOBS)
def test_remote_source_rejects_removed_mandatory_artifact_reference(name):
    policy, responses, _ = source_fixture()
    job_id = 101 + list(remote.REQUIRED_JOBS).index(name)
    path = f"/projects/{remote.PROJECT_ID}/jobs/{job_id}/artifacts/{quote(f'dist/ci/{name}/receipt.json', safe='')}"
    ref = f"dist/ci/{name}/" + (
        SOURCE_RESULT_PATHS[name][0]
        if SOURCE_RESULT_PATHS[name]
        else "command-05.stdout.log"
    )
    source_mutate(
        responses,
        path,
        lambda record: record.update(
            artifacts=[item for item in record["artifacts"] if item["ref"] != ref]
        ),
    )
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


@pytest.mark.parametrize("mutation", ["duplicate", "extra_field", "hash", "wrong_log"])
def test_remote_source_rejects_invalid_or_inconsistent_artifact_descriptors(mutation):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"

    def mutate(record):
        if mutation == "duplicate":
            record["artifacts"].append(copy.deepcopy(record["artifacts"][0]))
        elif mutation == "extra_field":
            record["artifacts"][0]["candidate_override"] = True
        elif mutation == "hash":
            record["artifacts"][0]["sha256"] = "e" * 64
        else:
            record["commands"][0]["stdout"]["ref"] = (
                "dist/ci/static/command-02.stdout.log"
            )

    source_mutate(responses, path, mutate)
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_rejects_removed_mandatory_gate():
    policy, responses, jobs_path = source_fixture()
    source_mutate(responses, jobs_path, lambda jobs: jobs.pop())
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"
    policy["required_jobs"] = {"static": "STATIC"}
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_rejects_artifact_content_tampering():
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/command-01.stdout.log', safe='')}"
    responses[path] = remote.ApiResponse(b"forged PASS\n", {})
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_missing_artifact_stays_unverified():
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"
    responses.pop(path)
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == result["status"] == "UNVERIFIED"
    assert result["acceptance_eligible"] is False


@pytest.mark.parametrize(
    "ref",
    [
        "../unit/pass.json",
        "/tmp/pass.json",
        "dist/ci/unit/pass.json",
        "dist/ci/static/../unit/pass.json",
        "dist/ci/static/a\\b",
    ],
)
def test_remote_source_rejects_artifact_path_escape(ref):
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/jobs/101/artifacts/{quote('dist/ci/static/receipt.json', safe='')}"
    source_mutate(
        responses, path, lambda record: record["commands"][0]["stdout"].update(ref=ref)
    )
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_requires_actual_job_trace_markers():
    policy, responses, _ = source_fixture()
    responses[f"/projects/{remote.PROJECT_ID}/jobs/101/trace"] = remote.ApiResponse(
        b"PASS\n", {}
    )
    assert source_verify(policy, responses)[0]["source_status"] == "FAIL"


def test_remote_source_preserves_failed_retry_history_when_latest_succeeds():
    policy, responses, jobs_path = source_fixture()
    jobs = json.loads(responses[jobs_path].body)
    old = copy.deepcopy(jobs[0])
    old.update(id=99, status="failed")
    jobs.append(old)
    responses[jobs_path] = source_response(jobs)
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert {"job_id": 99, "job_name": "static", "status": "failed"} in result[
        "job_history"
    ]


def test_remote_source_rejects_new_failed_retry_over_old_green_job():
    policy, responses, jobs_path = source_fixture()
    jobs = json.loads(responses[jobs_path].body)
    latest = copy.deepcopy(jobs[0])
    latest.update(id=999, status="failed")
    jobs.append(latest)
    responses[jobs_path] = source_response(jobs)
    responses[f"/projects/{remote.PROJECT_ID}/jobs/999"] = source_response(latest)
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "FAIL"
    assert {"job_id": 999, "job_name": "static", "status": "failed"} in result[
        "job_history"
    ]


def test_remote_source_uses_all_job_pages():
    policy, responses, jobs_path = source_fixture()
    jobs = json.loads(responses[jobs_path].body)
    responses[jobs_path] = remote.ApiResponse(
        json.dumps(jobs[:3]).encode(), {"x-next-page": "2"}
    )
    responses[jobs_path.replace("&page=1", "&page=2")] = source_response(jobs[3:])
    assert source_verify(policy, responses)[0]["source_status"] == "PASS"


def test_remote_client_rejects_arbitrary_origin_and_redirect_before_forwarding_credentials():
    client = remote.GitLabClient("synthetic_invalid_token")
    with pytest.raises(remote.SourceUnavailable, match="fixed-origin"):
        client.fetch("https://example.invalid/steal")
    with pytest.raises(remote.SourceUnavailable, match="fixed-origin"):
        client.fetch("//example.invalid/steal")
    with pytest.raises(remote.SourceUnavailable, match="redirect refused"):
        remote.NoRedirect().redirect_request(
            None, None, 302, "Found", {}, "https://example.invalid/steal"
        )


def trusted_source_fixture():
    policy, responses, _ = source_fixture()
    project = remote.PROJECT_ID
    policy["trusted_execution"] = {
        "runner_ids": [88],
        "runner_tag": SOURCE_RUNNER_TAG,
        "ci_config_path": ".gitlab-ci.yml",
        "protected_ref": "dev_gpt",
    }
    source_mutate(
        responses,
        f"/projects/{project}/repository/branches/dev_gpt",
        lambda record: record.update(protected=True),
    )
    responses[f"/projects/{project}/protected_branches/dev_gpt"] = source_response(
        {
            "name": "dev_gpt",
            "allow_force_push": False,
            "push_access_levels": [{"access_level": 0}],
        }
    )
    responses["/runners/88"] = source_response(
        {
            "id": 88,
            "runner_type": "project_type",
            "is_shared": False,
            "locked": True,
            "run_untagged": False,
            "access_level": "ref_protected",
            "projects": [{"id": project}],
            "tag_list": [SOURCE_RUNNER_TAG],
        }
    )
    for job_id in range(101, 107):
        source_mutate(
            responses,
            f"/projects/{project}/jobs/{job_id}",
            lambda job: job.update(tag_list=[SOURCE_RUNNER_TAG]),
        )
    return policy, responses


def test_configured_protection_metadata_cannot_self_certify_permission_boundary():
    policy, responses = trusted_source_fixture()
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert result["trust_status"] == "METADATA_MATCHED"
    assert result["status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False
    assert all(job["tag_list"] == [SOURCE_RUNNER_TAG] for job in result["jobs"])


def assert_trust_metadata_rejected(policy, responses):
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert result["trust_status"] == "UNVERIFIED"
    assert result["trust_issues"]
    assert result["status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("runner_type", "instance_type"),
        ("runner_type", "group_type"),
        ("runner_type", None),
        ("is_shared", True),
        ("is_shared", None),
        ("is_shared", 0),
        ("locked", False),
        ("locked", None),
        ("locked", 1),
        ("run_untagged", True),
        ("run_untagged", None),
        ("run_untagged", 0),
        ("access_level", "not_protected"),
        ("access_level", None),
        ("projects", []),
        ("projects", None),
        ("projects", {"id": remote.PROJECT_ID}),
        ("projects", [{"id": remote.PROJECT_ID + 1}]),
        ("projects", [{"id": remote.PROJECT_ID}, {"id": remote.PROJECT_ID + 1}]),
        ("projects", [{"id": remote.PROJECT_ID}, {"id": remote.PROJECT_ID}]),
        ("projects", [{"id": True}]),
        ("projects", [{"id": str(remote.PROJECT_ID)}]),
        ("projects", [{"id": float(remote.PROJECT_ID)}]),
        ("projects", [{"id": 0}]),
        ("projects", [{"id": -1}]),
        ("projects", [{}]),
        ("tag_list", []),
        ("tag_list", None),
        ("tag_list", SOURCE_RUNNER_TAG),
        ("tag_list", ["unrelated-runner-tag"]),
        ("tag_list", [SOURCE_RUNNER_TAG, ""]),
        ("tag_list", [SOURCE_RUNNER_TAG, " "]),
        ("tag_list", [SOURCE_RUNNER_TAG, 7]),
    ],
)
def test_trusted_project_runner_rejects_wrong_or_malformed_metadata(field, value):
    policy, responses = trusted_source_fixture()
    source_mutate(
        responses, "/runners/88", lambda record: record.update({field: value})
    )
    assert_trust_metadata_rejected(policy, responses)


@pytest.mark.parametrize(
    "field",
    [
        "runner_type",
        "is_shared",
        "locked",
        "run_untagged",
        "access_level",
        "projects",
        "tag_list",
    ],
)
def test_trusted_project_runner_rejects_missing_metadata(field):
    policy, responses = trusted_source_fixture()
    source_mutate(responses, "/runners/88", lambda record: record.pop(field))
    assert_trust_metadata_rejected(policy, responses)


@pytest.mark.parametrize("value", [None, "", " ", [], True, 7])
def test_trusted_project_runner_requires_fixed_policy_tag(value):
    policy, responses = trusted_source_fixture()
    policy["trusted_execution"]["runner_tag"] = value
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_rejects_missing_policy_tag():
    policy, responses = trusted_source_fixture()
    del policy["trusted_execution"]["runner_tag"]
    assert_trust_metadata_rejected(policy, responses)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        SOURCE_RUNNER_TAG,
        ["unrelated-job-tag"],
        [SOURCE_RUNNER_TAG, ""],
        [SOURCE_RUNNER_TAG, " "],
        [SOURCE_RUNNER_TAG, True],
    ],
)
def test_trusted_project_runner_rejects_job_without_valid_dedicated_tag(value):
    policy, responses = trusted_source_fixture()
    source_mutate(
        responses,
        f"/projects/{remote.PROJECT_ID}/jobs/101",
        lambda job: job.update(tag_list=value),
    )
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_rejects_missing_job_tag():
    policy, responses = trusted_source_fixture()
    source_mutate(
        responses,
        f"/projects/{remote.PROJECT_ID}/jobs/101",
        lambda job: job.pop("tag_list"),
    )
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_rejects_unreadable_runner_metadata():
    policy, responses = trusted_source_fixture()
    del responses["/runners/88"]
    assert_trust_metadata_rejected(policy, responses)


def test_remote_source_keeps_missing_job_tags_unknown_without_source_failure():
    policy, responses, _ = source_fixture()
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert all(job["tag_list"] is None for job in result["jobs"])
    assert result["trust_status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False


def test_trusted_project_runner_retains_additional_nonempty_job_and_runner_tags():
    policy, responses = trusted_source_fixture()
    tags = [SOURCE_RUNNER_TAG, "linux-arm64"]
    source_mutate(responses, "/runners/88", lambda record: record.update(tag_list=tags))
    source_mutate(
        responses,
        f"/projects/{remote.PROJECT_ID}/jobs/101",
        lambda job: job.update(tag_list=tags),
    )
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert result["trust_status"] == "METADATA_MATCHED"
    assert result["jobs"][0]["tag_list"] == tags
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False


@pytest.mark.parametrize("job_id", [101, 106])
def test_trusted_project_runner_requires_all_job_tags_on_actual_runner(job_id):
    policy, responses = trusted_source_fixture()
    source_mutate(
        responses,
        f"/projects/{remote.PROJECT_ID}/jobs/{job_id}",
        lambda job: job.update(tag_list=[SOURCE_RUNNER_TAG, "linux-arm64"]),
    )
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_accepts_tag_superset_and_different_order():
    policy, responses = trusted_source_fixture()
    source_mutate(
        responses,
        "/runners/88",
        lambda record: record.update(
            tag_list=["linux-arm64", SOURCE_RUNNER_TAG, "additional-runner-tag"]
        ),
    )
    for job_id, tags in (
        (101, [SOURCE_RUNNER_TAG, "linux-arm64"]),
        (106, ["linux-arm64", SOURCE_RUNNER_TAG]),
    ):
        source_mutate(
            responses,
            f"/projects/{remote.PROJECT_ID}/jobs/{job_id}",
            lambda job, tags=tags: job.update(tag_list=tags),
        )
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "PASS"
    assert result["trust_status"] == "METADATA_MATCHED"
    assert result["status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False
    assert result["jobs"][0]["tag_list"] == [SOURCE_RUNNER_TAG, "linux-arm64"]
    assert result["jobs"][-1]["tag_list"] == ["linux-arm64", SOURCE_RUNNER_TAG]


def set_source_job_runner(responses, job_id, runner_id):
    source_mutate(
        responses,
        f"/projects/{remote.PROJECT_ID}/jobs/{job_id}",
        lambda job: job.update(runner={"id": runner_id}),
    )
    jobs_path = (
        f"/projects/{remote.PROJECT_ID}/pipelines/{SOURCE_PIPELINE_ID}/jobs"
        "?include_retried=true&per_page=100&page=1"
    )
    jobs = json.loads(responses[jobs_path].body)
    for job in jobs:
        if job["id"] == job_id:
            job["runner"] = {"id": runner_id}
    responses[jobs_path] = source_response(jobs)


def test_trusted_project_runner_cannot_combine_tags_from_different_runners():
    policy, responses = trusted_source_fixture()
    policy["trusted_execution"]["runner_ids"] = [88, 89]
    second_runner = json.loads(responses["/runners/88"].body)
    second_runner.update(id=89, tag_list=[SOURCE_RUNNER_TAG, "linux-arm64"])
    responses["/runners/89"] = source_response(second_runner)
    set_source_job_runner(responses, 106, 89)
    for job_id in (101, 106):
        source_mutate(
            responses,
            f"/projects/{remote.PROJECT_ID}/jobs/{job_id}",
            lambda job: job.update(tag_list=[SOURCE_RUNNER_TAG, "linux-arm64"]),
        )
    # Runner 89 covers its job's tags; runner 88 does not cover job 101.
    # A union of both runners' tags would incorrectly accept this input.
    assert_trust_metadata_rejected(policy, responses)


@pytest.mark.parametrize(
    "body",
    [b'{"id":', b"\xff", b"[]", b"null", b'"runner metadata"'],
    ids=["invalid-json", "invalid-utf8", "list", "null", "string"],
)
def test_trusted_project_runner_rejects_malformed_response(body):
    policy, responses = trusted_source_fixture()
    responses["/runners/88"] = remote.ApiResponse(body, {})
    assert_trust_metadata_rejected(policy, responses)


@pytest.mark.parametrize("runner_id", [89, True])
def test_trusted_project_runner_rejects_wrong_response_identity(runner_id):
    policy, responses = trusted_source_fixture()
    source_mutate(responses, "/runners/88", lambda record: record.update(id=runner_id))
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_rejects_missing_response_identity():
    policy, responses = trusted_source_fixture()
    source_mutate(responses, "/runners/88", lambda record: record.pop("id"))
    assert_trust_metadata_rejected(policy, responses)


def test_trusted_project_runner_rejects_actual_runner_outside_fixed_ids():
    policy, responses = trusted_source_fixture()
    set_source_job_runner(responses, 106, 89)
    assert_trust_metadata_rejected(policy, responses)


def test_cancelled_source_preserves_actual_pipeline_and_jobs_state():
    policy, responses, _ = source_fixture()
    path = f"/projects/{remote.PROJECT_ID}/pipelines/{SOURCE_PIPELINE_ID}"
    source_mutate(responses, path, lambda record: record.update(status="canceled"))
    result = source_verify(policy, responses)[0]
    assert result["source_status"] == "FAIL"
    assert result["pipeline"]["status"] == "canceled"
    assert len(result["job_history"]) == 6


def test_remote_source_rejects_job_retry_started_during_artifact_verification():
    policy, responses, jobs_path = source_fixture()
    calls = 0

    def fetch(path):
        nonlocal calls
        if path == jobs_path:
            calls += 1
            if calls == 2:
                jobs = json.loads(responses[path].body)
                retry = copy.deepcopy(jobs[0])
                retry.update(id=999, status="running")
                return source_response(jobs + [retry])
        return responses[path]

    result, _ = remote.verify_pipeline(
        fetch,
        revision=SOURCE_REVISION,
        pipeline_id=SOURCE_PIPELINE_ID,
        ref="dev_gpt",
        policy=policy,
        driver_sha256=SOURCE_DRIVER_HASH,
        lock_sha256=SOURCE_LOCK_HASH,
    )
    assert result["source_status"] == result["status"] == "UNVERIFIED"
    assert {"job_id": 999, "job_name": "static", "status": "running"} in result[
        "final_job_history"
    ]


def test_remote_cli_reads_fixed_git_policy_and_missing_credentials_stay_unverified(
    tmp_path,
):
    # Local synthetic checkout verifies CLI pin semantics only, not GitLab provenance.
    checkout = tmp_path / "checkout"
    scripts = checkout / "scripts" / "ci"
    scripts.mkdir(parents=True)
    cli = scripts / "verify_remote.py"
    cli.write_bytes(Path(remote.__file__).read_bytes())
    (scripts / "run_gate.py").write_text("# synthetic driver\n")
    (checkout / "uv.lock").write_text("version = 1\n")
    policy = checkout / "security-policy.yaml"
    policy.write_text(
        "project:\n  id: 86656946\n  path: ayitnovel/ainovelos\n  api_base: https://gitlab.com/api/v4\n"
    )
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "user.name=source-fixture",
            "-c",
            "user.email=source@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=checkout, check=True, capture_output=True)
    pin = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()
    # Malformed candidate policy cannot replace the fixed committed input.
    policy.write_text("malformed: [\n")
    output = tmp_path / "verification.json"
    env = os.environ.copy()
    env["ANOVELOS_GITLAB_TOKEN"] = ""
    process = subprocess.run(
        [
            sys.executable,
            str(cli),
            "--revision",
            pin,
            "--pipeline-id",
            "91",
            "--ref",
            "dev_gpt",
            "--policy-revision",
            pin,
            "--output",
            str(output),
        ],
        cwd=checkout,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 2
    result = json.loads(output.read_text())
    assert result["source_status"] == result["status"] == "UNVERIFIED"
    assert result["permission_status"] == "UNKNOWN"
    assert result["acceptance_eligible"] is False
    assert result["policy_revision"] == pin
    assert "TOKEN is missing" in result["errors"][0]
    assert "malformed" not in result["errors"][0]
    with pytest.raises(remote.SourceError, match="full Git"):
        remote.git_file(checkout, pin[:8], "security-policy.yaml")


"""Security gate tests to merge into tests/contract/test_delivery_gates.py."""


import secrets
from pathlib import Path
from typing import Any

import pytest

SECURITY_ROOT = (
    Path(__file__).resolve().parents[2]
    if "tests" in Path(__file__).resolve().parts
    else Path.cwd()
)
sys.path.insert(0, str(SECURITY_ROOT / "scripts/ci"))
import check_security as security


def security_git(root: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    assert result.returncode == 0


@pytest.fixture
def security_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    security_git(root, "init", "--quiet")
    security_git(root, "config", "user.name", "Disposable Security Fixture")
    security_git(root, "config", "user.email", "fixture@example.invalid")
    (root / "README.md").write_text("Disposable test repository, no credentials.\n")
    security_git(root, "add", "README.md")
    security_git(root, "commit", "--quiet", "-m", "safe fixture")
    return root


@pytest.fixture
def pinned_gitleaks() -> Path:
    binary = Path(
        os.environ.get(
            "ANOVELOS_GITLEAKS",
            str(SECURITY_ROOT / "dist/tools/gitleaks-8.21.2/gitleaks"),
        )
    )
    assert binary.is_file(), (
        "Run the pinned bootstrap_scanners.py first; missing scanner is a failure"
    )
    return security.scanner_binary(binary)


def test_real_gitleaks_accepts_tracked_worktree_and_complete_history(
    security_repository: Path, pinned_gitleaks: Path, tmp_path: Path
) -> None:
    output = tmp_path / "scan-safe"
    output.mkdir()
    report = security.scan_secrets(security_repository, output, pinned_gitleaks)
    assert report["status"] == "PASS"
    assert report["history_commits"] == 1
    assert {row["target"] for row in report["scans"]} == {
        "tracked_worktree",
        "git_history",
    }
    assert all(
        row["exit_code"] == 0 and row["finding_count"] == 0 for row in report["scans"]
    )


def test_real_gitleaks_rejects_tracked_secret_and_ignores_candidate_suppressions(
    security_repository: Path, pinned_gitleaks: Path, tmp_path: Path
) -> None:
    # Shape-only fixture generated here; it has never been issued by a service.
    token = "ghp_" + secrets.token_hex(18)
    (security_repository / "fixture.txt").write_text(
        f"github_token = '{token}' # gitleaks:allow\n"
    )
    (security_repository / ".gitleaks.toml").write_text("[allowlist]\npaths = ['.*']\n")
    (security_repository / ".gitleaksignore").write_text("fixture.txt\n")
    security_git(
        security_repository, "add", "fixture.txt", ".gitleaks.toml", ".gitleaksignore"
    )
    output = tmp_path / "scan-secret"
    output.mkdir()
    report = security.scan_secrets(security_repository, output, pinned_gitleaks)
    assert report["status"] == "FAIL"
    worktree = next(
        row for row in report["scans"] if row["target"] == "tracked_worktree"
    )
    assert worktree["exit_code"] == 1 and worktree["finding_count"] > 0
    assert token not in json.dumps(report)
    assert any(location["path"] == "fixture.txt" for location in worktree["locations"])


def test_real_gitleaks_finds_deleted_secret_in_full_history(
    security_repository: Path, pinned_gitleaks: Path, tmp_path: Path
) -> None:
    token = "ghp_" + secrets.token_hex(18)
    source = security_repository / "historical-fixture.txt"
    source.write_text(f"github_token = '{token}'\n")
    security_git(security_repository, "add", source.name)
    security_git(
        security_repository, "commit", "--quiet", "-m", "shape-only historical test"
    )
    security_git(security_repository, "rm", "--quiet", source.name)
    security_git(security_repository, "commit", "--quiet", "-m", "remove fixture")
    output = tmp_path / "scan-history"
    output.mkdir()
    report = security.scan_secrets(security_repository, output, pinned_gitleaks)
    assert report["status"] == "FAIL"
    history = next(row for row in report["scans"] if row["target"] == "git_history")
    assert history["exit_code"] == 1 and history["finding_count"] > 0
    assert token not in (output / "secret-scan.json").read_text()


def test_security_rejects_real_shallow_checkout(
    security_repository: Path, tmp_path: Path
) -> None:
    clone = tmp_path / "shallow"
    result = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            security_repository.as_uri(),
            str(clone),
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    with pytest.raises(security.SecurityFailure, match="SECURITY_HISTORY_SHALLOW"):
        security.complete_history(clone)


def test_security_cli_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_text("prior record")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SECURITY_ROOT / "scripts/ci/check_security.py"),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert sentinel.read_text() == "prior record"
    assert "SECURITY_OUTPUT_EXISTS" in result.stdout


def security_lock_fixture(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1"\n'
        '[build-system]\nrequires = ["uv_build==0.12.17"]\n'
    )
    (root / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "fixture"\nversion = "0.1"\n'
        'source = { editable = "." }\n[[package]]\nname = "safe-package"\n'
        'version = "1.2.3"\nsource = { registry = "https://pypi.org/simple" }\n'
        'sdist = { hash = "sha256:' + "0" * 64 + '" }\n'
    )


def test_security_audits_lock_packages_and_exact_build_backend(tmp_path: Path) -> None:
    security_lock_fixture(tmp_path)
    assert security.locked_packages(tmp_path) == {
        ("safe-package", "1.2.3"),
        ("uv-build", "0.12.17"),
    }


@pytest.mark.parametrize(
    "mutation,code",
    [
        ('source = { registry = "https://pypi.org/simple" }', "SECURITY_LOCK_SOURCE"),
        ("sha256:" + "0" * 64, "SECURITY_LOCK_HASH"),
        ("uv_build==0.12.17", "SECURITY_BUILD_DEPENDENCY_PIN"),
    ],
)
def test_security_rejects_unsupported_or_unpinned_dependencies(
    tmp_path: Path, mutation: str, code: str
) -> None:
    security_lock_fixture(tmp_path)
    source = tmp_path / (
        "pyproject.toml" if mutation.startswith("uv_build") else "uv.lock"
    )
    replacement = (
        "uv_build>=0.12"
        if source.name == "pyproject.toml"
        else 'source = { git = "https://example.invalid/repository.git" }'
        if code == "SECURITY_LOCK_SOURCE"
        else "sha256:bad"
    )
    source.write_text(source.read_text().replace(mutation, replacement))
    # A malformed unsupported source is rejected before any audit subprocess.
    with pytest.raises(security.SecurityFailure, match=code):
        security.locked_packages(tmp_path)


@pytest.mark.parametrize(
    "exception",
    [
        {
            "vulnerability_id": "CVE-2020-1",
            "package": "pkg",
            "version": "1",
            "owner": "owner",
            "reason": "specific",
            "expiry": "2000-01-01",
        },
        {"package": "pkg", "owner": "owner", "reason": "blanket"},
    ],
)
def test_security_rejects_expired_or_incomplete_dependency_exception(
    tmp_path: Path, exception: dict[str, Any]
) -> None:
    import yaml

    policy = {
        "secret_scanner": {
            "version": "8.21.2",
            "linux_x64_sha256": security.ARCHIVES[("Linux", "x86_64")][1],
        },
        "scan_targets": ["tracked_worktree", "git_history"],
        "dependency_exceptions": [exception],
    }
    (tmp_path / "security-policy.yaml").write_text(yaml.safe_dump(policy))
    with pytest.raises(security.SecurityFailure, match="SECURITY_EXCEPTION"):
        security.read_policy(tmp_path)


import hashlib
import io
import platform
import sys
import tarfile
from pathlib import Path

import pytest

REVIEW_SOURCE_ROOT = (
    Path(__file__).resolve().parents[2]
    if "tests" in Path(__file__).resolve().parts
    else Path.cwd()
)
sys.path.insert(0, str(REVIEW_SOURCE_ROOT / "scripts/ci"))
import bootstrap_scanners as archive_bootstrap
import check_security as archive_security


@pytest.fixture
def pinned_archive_fixture(tmp_path, monkeypatch):
    # A synthetic trusted archive isolates content provenance logic from network.
    binary = b'#!/bin/sh\nprintf "8.21.2\\n"\n'
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as target:
        member = tarfile.TarInfo("gitleaks")
        member.size = len(binary)
        member.mode = 0o755
        target.addfile(member, io.BytesIO(binary))
    archive = buffer.getvalue()
    checksum = hashlib.sha256(archive).hexdigest()
    monkeypatch.setattr(
        archive_bootstrap,
        "ARCHIVES",
        {(platform.system(), platform.machine()): ("synthetic_fixture", checksum)},
    )
    archive_name, _ = archive_bootstrap.archive_identity()
    output = tmp_path / "cache"
    output.mkdir()
    executable = output / "gitleaks"
    executable.write_bytes(binary)
    executable.chmod(0o755)
    receipt = {
        "record_type": "pinned_scanner_bootstrap",
        "version": "8.21.2",
        "archive": archive_name,
        "archive_sha256": checksum,
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
    }
    (output / "bootstrap-scanners.json").write_text(json.dumps(receipt))
    (output / archive_name).write_bytes(archive)
    return output, executable, archive_name, archive, receipt


def test_archive_byte_verification_accepts_matching_binary(pinned_archive_fixture):
    output, executable, _, _, _ = pinned_archive_fixture
    assert archive_bootstrap.provision(output, reuse_verified=True) == executable
    assert archive_security.scanner_binary(executable) == executable


def test_forged_binary_and_sidecar_do_not_pass_pinned_archive(pinned_archive_fixture):
    output, executable, _, _, receipt = pinned_archive_fixture
    original_receipt = output / "bootstrap-scanners.json"
    forged = b'#!/bin/sh\nprintf "8.21.2\\n"\n# fake scanner: return green\n'
    executable.write_bytes(forged)
    receipt["binary_sha256"] = hashlib.sha256(forged).hexdigest()
    original_receipt.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="BINARY_MISMATCH"):
        archive_bootstrap.provision(output, reuse_verified=True)
    with pytest.raises(archive_security.SecurityFailure, match="SCANNER_BOOTSTRAP"):
        archive_security.scanner_binary(executable)
    assert executable.read_bytes() == forged
    assert json.loads(original_receipt.read_text()) == receipt


def test_forged_archive_and_recomputed_sidecar_digest_rejected(pinned_archive_fixture):
    output, executable, archive_name, _, receipt = pinned_archive_fixture
    forged = b"not the pinned official archive"
    (output / archive_name).write_bytes(forged)
    receipt["archive_sha256"] = hashlib.sha256(forged).hexdigest()
    (output / "bootstrap-scanners.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="ARCHIVE_CHECKSUM"):
        archive_bootstrap.provision(output, reuse_verified=True)
    with pytest.raises(archive_security.SecurityFailure, match="SCANNER_BOOTSTRAP"):
        archive_security.scanner_binary(executable)


def test_missing_archive_cannot_be_self_certified_by_existing_sidecar(
    pinned_archive_fixture,
):
    output, executable, archive_name, _, _ = pinned_archive_fixture
    (output / archive_name).unlink()
    with pytest.raises(archive_security.SecurityFailure, match="SCANNER_BOOTSTRAP"):
        archive_security.scanner_binary(executable)
    assert not (output / archive_name).exists()


def test_explicit_cache_migration_preserves_binary_and_old_receipt(
    pinned_archive_fixture, monkeypatch
):
    output, executable, archive_name, archive, _ = pinned_archive_fixture
    (output / archive_name).unlink()
    before_binary = executable.read_bytes()
    receipt_file = output / "bootstrap-scanners.json"
    before_receipt = receipt_file.read_bytes()
    requested = []

    def download(url, timeout):
        requested.append((url, timeout))
        return io.BytesIO(archive)

    monkeypatch.setattr(archive_bootstrap.urllib.request, "urlopen", download)
    assert archive_bootstrap.provision(output, reuse_verified=True) == executable
    assert requested == [(archive_bootstrap.archive_url(archive_name), 30)]
    assert (output / archive_name).read_bytes() == archive
    assert executable.read_bytes() == before_binary
    assert receipt_file.read_bytes() == before_receipt
    assert archive_security.scanner_binary(executable) == executable


def test_migration_cannot_overwrite_a_forged_existing_binary(
    pinned_archive_fixture, monkeypatch
):
    output, executable, archive_name, archive, receipt = pinned_archive_fixture
    (output / archive_name).unlink()
    forged = b'#!/bin/sh\nprintf "8.21.2\\n"\n# forged\n'
    executable.write_bytes(forged)
    receipt["binary_sha256"] = hashlib.sha256(forged).hexdigest()
    (output / "bootstrap-scanners.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(
        archive_bootstrap.urllib.request,
        "urlopen",
        lambda url, timeout: io.BytesIO(archive),
    )
    with pytest.raises(ValueError, match="BINARY_MISMATCH"):
        archive_bootstrap.provision(output, reuse_verified=True)
    assert not (output / archive_name).exists()
    assert executable.read_bytes() == forged


def test_fresh_bootstrap_retains_archive_for_later_verified_reuse(
    pinned_archive_fixture, monkeypatch, tmp_path
):
    _, _, archive_name, archive, _ = pinned_archive_fixture
    monkeypatch.setattr(
        archive_bootstrap.urllib.request,
        "urlopen",
        lambda url, timeout: io.BytesIO(archive),
    )
    fresh = tmp_path / "fresh"
    executable = archive_bootstrap.provision(fresh)
    assert (fresh / archive_name).read_bytes() == archive
    assert archive_security.scanner_binary(executable) == executable


"""Real child-process environment controls; no production credentials are used."""

import shutil
import sys
from pathlib import Path

import pytest

environment_runner = globals().get("runner")
if environment_runner is None:
    # Standalone /tmp execution starts at the repository root. Once merged, use
    # the existing path-loaded module so clean installed-package discovery does
    # not need the repository's scripts directory to be importable as a package.
    environment_spec = importlib.util.spec_from_file_location(
        "environment_control_run_gate", Path.cwd() / "scripts/ci/run_gate.py"
    )
    assert environment_spec is not None and environment_spec.loader is not None
    environment_runner = importlib.util.module_from_spec(environment_spec)
    sys.modules[environment_spec.name] = environment_runner
    environment_spec.loader.exec_module(environment_runner)


def environment_control_child(tmp_path, monkeypatch, values):
    # Seed every source key from a synthetic fixture, never the host token set.
    for key in tuple(os.environ):
        monkeypatch.delenv(key)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    output = tmp_path / "dist/environment"
    output.mkdir(parents=True)
    records, code = environment_runner.execute_commands(
        [
            [
                sys.executable,
                "-c",
                "import json,os; print(json.dumps(dict(os.environ),sort_keys=True))",
            ]
        ],
        output,
        root=tmp_path,
    )
    assert code == 0 and records[0]["exit_code"] == 0
    stdout = (output / "command-01.stdout.log").read_text()
    stderr = (output / "command-01.stderr.log").read_text()
    assert not stderr
    return json.loads(stdout), stdout, json.dumps(records)


def test_real_gate_child_omits_auth_keys_and_credential_proxy_urls(
    tmp_path, monkeypatch
):
    marker = "environment-control-only-fake-secret-marker"
    blocked = {
        "ANOVELOS_GITLAB_TOKEN": marker,
        "ANOVELOS_GITLAB_READ_TOKEN": marker,
        "ANOVELOS_GITLAB_OTHER": marker,
        "CI_JOB_TOKEN": marker,
        "CI_DEPLOY_PASSWORD": marker,
        "OPENAI_API_KEY": marker,
        "ANTHROPIC_API_KEY": marker,
        "AWS_SECRET_ACCESS_KEY": marker,
        "PIP_INDEX_URL": "https://fixture:" + marker + "@example.invalid/simple",
        "PIP_EXTRA_INDEX_URL": marker,
        "PIP_CONFIG_FILE": marker,
        "UV_INDEX_PASSWORD": marker,
        "UV_DEFAULT_INDEX": marker,
        "DOCKER_AUTH_CONFIG": marker,
        "HTTP_PROXY": "http://fixture:" + marker + "@example.invalid:8080",
        "HTTPS_PROXY": "http://fixture:" + marker + "@example.invalid:8080",
        "ALL_PROXY": marker,
        "http_proxy": marker,
        "https_proxy": marker,
        "all_proxy": marker,
        "NO_PROXY": marker,
        "no_proxy": marker,
        "PYTHONPATH": marker,
        "UNREGISTERED_FUTURE_PROVIDER_SECRET": marker,
    }
    child, stdout, records = environment_control_child(
        tmp_path,
        monkeypatch,
        {"PATH": os.defpath, "HOME": str(tmp_path), **blocked},
    )
    assert all(key not in child for key in blocked)
    assert marker not in stdout and marker not in records
    assert child["PYTHONDONTWRITEBYTECODE"] == "1"
    assert child["MYPY_CACHE_DIR"] == str(tmp_path / "dist/cache/mypy")
    assert child["RUFF_CACHE_DIR"] == str(tmp_path / "dist/cache/ruff")


def test_real_gate_child_retains_local_uv_and_runtime_configuration(
    tmp_path, monkeypatch
):
    uv = shutil.which("uv")
    if uv is None:
        uv = str(environment_runner.ROOT / "dist/tools/uv-bootstrap/bin/uv")
    assert os.path.isfile(uv), "A real locked uv executable is required"
    values = {
        "PATH": os.path.dirname(uv) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "TMP": str(tmp_path),
        "TEMP": str(tmp_path),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "C.UTF-8",
        "UV_CACHE_DIR": str(tmp_path / "dist/cache/uv"),
        "UV_PYTHON_INSTALL_DIR": str(tmp_path / "dist/tools/python"),
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PYTHON": sys.executable,
    }
    child, _stdout, _records = environment_control_child(tmp_path, monkeypatch, values)
    assert all(child[key] == value for key, value in values.items())
    output = tmp_path / "dist/uv-command"
    output.mkdir()
    records, code = environment_runner.execute_commands(
        [["uv", "--version"]], output, root=tmp_path
    )
    assert code == 0 and records[0]["exit_code"] == 0
    assert (output / "command-01.stdout.log").read_text().startswith("uv 0.12.17")


def test_real_gate_child_retains_ci_metadata_and_ephemeral_postgres_dsn(
    tmp_path, monkeypatch
):
    # This checks DSN transport in a real process, not a database connection.
    # The separate PostgreSQL acceptance tests must still connect to PostgreSQL.
    values = {
        "PATH": os.defpath,
        "HOME": str(tmp_path),
        "CI": "true",
        "GITLAB_CI": "true",
        "CI_PROJECT_ID": "86656946",
        "CI_PROJECT_PATH": "ayitnovel/ainovelos",
        "CI_PROJECT_DIR": str(tmp_path),
        "CI_COMMIT_SHA": "a" * 40,
        "CI_COMMIT_REF_NAME": "dev_gpt",
        "CI_COMMIT_REF_PROTECTED": "false",
        "CI_COMMIT_BRANCH": "dev_gpt",
        "CI_JOB_ID": "9101",
        "CI_JOB_NAME": "postgres_env",
        "CI_PIPELINE_ID": "9201",
        "CI_PIPELINE_SOURCE": "merge_request_event",
        "CI_MERGE_REQUEST_ID": "9301",
        "CI_MERGE_REQUEST_IID": "1",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "dev_gpt",
        "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main",
        "ANOVELOS_TEST_DSN": (
            "postgresql+psycopg://bootstrap_test:"
            "ci_ephemeral_database_only_invalid_for_production"
            "@postgres:5432/bootstrap_test"
        ),
    }
    child, _stdout, _records = environment_control_child(
        tmp_path,
        monkeypatch,
        {**values, "CI_JOB_TOKEN": "fake-ci-token-not-for-any-server"},
    )
    assert all(child[key] == value for key, value in values.items())
    assert "CI_JOB_TOKEN" not in child


def test_real_gate_child_retains_local_docker_connection_metadata(
    tmp_path, monkeypatch
):
    values = {
        "PATH": os.defpath,
        "HOME": str(tmp_path),
        "DOCKER_HOST": "unix:///tmp/environment-control-docker.sock",
        "DOCKER_CONTEXT": "desktop-linux",
        "DOCKER_CONFIG": str(tmp_path / "docker-config"),
        "DOCKER_CERT_PATH": str(tmp_path / "docker-certs"),
        "DOCKER_TLS_VERIFY": "1",
        "DOCKER_DEFAULT_PLATFORM": "linux/arm64",
        "DOCKER_API_VERSION": "1.45",
    }
    child, _stdout, _records = environment_control_child(
        tmp_path,
        monkeypatch,
        {**values, "DOCKER_AUTH_CONFIG": "fake-registry-auth-never-valid"},
    )
    assert all(child[key] == value for key, value in values.items())
    assert "DOCKER_AUTH_CONFIG" not in child


@pytest.mark.parametrize(
    "host",
    [
        "tcp://fixture:fake-docker-password@localhost:2376",
        "ssh://fixture@localhost",
        "https://fixture:fake-docker-password@example.invalid",
        "tcp://localhost:2376?password=fake-docker-password#credential",
        "not-a-supported-endpoint",
        "tcp://[invalid-ipv6",
    ],
)
def test_real_gate_child_rejects_docker_host_userinfo_or_invalid_endpoint(
    tmp_path, monkeypatch, host
):
    child, stdout, records = environment_control_child(
        tmp_path,
        monkeypatch,
        {"PATH": os.defpath, "HOME": str(tmp_path), "DOCKER_HOST": host},
    )
    assert "DOCKER_HOST" not in child
    assert "fake-docker-password" not in stdout
    assert "fake-docker-password" not in records


def test_postgres_gate_runs_canon_persistence_without_dropping_service_check():
    commands = runner.commands_for("postgres_env", ROOT / "dist/ci/postgres_env")
    pytest_commands = [command for command in commands if "pytest" in command]
    assert len(pytest_commands) == 1
    command = pytest_commands[0]
    assert "tests/integration/test_postgres_ci_service.py" in command
    assert "tests/integration/test_v2_009.py" in command
    assert "tests/integration/test_v2_010.py" in command
    assert "tests/integration/test_v2_011.py" in command
    assert "tests/integration/test_v2_012.py" in command
    assert "tests/integration/test_v2_015_postgres.py" in command
    assert "tests/integration/test_v2_016_postgres.py" in command
    assert not {"--ignore", "--deselect", "-k", "-m"}.intersection(
        command[command.index("pytest") + 1 :]
    )
