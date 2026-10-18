"""Exercise the historical GitLab guard, not current GitHub trust certification."""

from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import zlib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ENROLLMENT = "plan/validation/execution/V2-004/enrollment-20261005/"
WRAPPER = ENROLLMENT + "trusted-ci.yml"
OVERLAY = ENROLLMENT + "acceptance-overlay.yml"
NORMALIZED_GUARD_SHA256 = (
    "dbd923257bc44717b9b01fd4ebcdd3a794a05c23a118ed7b98666b52ee82e25b"
)
# This commit refreshed the frozen overlay inventory for its exact source tree.
# It is a local historical fixture, not a claim of remote CI for this revision.
HISTORICAL_GUARD_REVISION = "1fa558d4965c15d445e76e033a1107ae10d971a9"


def overlay_document():
    return yaml.safe_load((ROOT / OVERLAY).read_text())


def guard_source(document=None):
    document = overlay_document() if document is None else document
    command = document["default"]["before_script"][0]
    prefix = "python -I -B - <<'ANOVELOS_TRUSTED_GUARD'\n"
    suffix = "\nANOVELOS_TRUSTED_GUARD"
    assert isinstance(command, str) and command.startswith(prefix)
    assert command.rstrip().endswith(suffix)
    source = command[len(prefix) :].rstrip()[: -len(suffix)]
    # The candidate overlay is self-excluded by the outer guard. Freeze its
    # executable body here before any subprocess is allowed to consume it.
    normalized = replace_payload(source, "__ANOVELOS_PROTECTED_PAYLOAD__")
    assert hashlib.sha256(normalized.encode()).hexdigest() == NORMALIZED_GUARD_SHA256, (
        "untrusted guard executable body"
    )
    return source


def literal_assignment(source, name):
    matches = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    ]
    assert len(matches) == 1
    return matches[0], ast.literal_eval(matches[0].value)


def payload_span(source):
    matches = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "EXPECTED_JSON_ZLIB_B64"
            for target in node.targets
        )
    ]
    assert len(matches) == 1, "guard needs one literal payload binding"
    node = matches[0]
    assert len(node.targets) == 1 and isinstance(node.targets[0], ast.Name), (
        "guard payload binding must have one target"
    )
    assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str), (
        "guard payload must be a string literal"
    )
    lines = source.encode().splitlines(keepends=True)
    value = node.value
    start = sum(len(line) for line in lines[: value.lineno - 1]) + value.col_offset
    end = (
        sum(len(line) for line in lines[: value.end_lineno - 1]) + value.end_col_offset
    )
    return start, end


def replace_payload(source, encoded):
    start, end = payload_span(source)
    raw = source.encode()
    # Replace only the literal bytes, retaining any same-line trailing code.
    return (raw[:start] + repr(encoded).encode() + raw[end:]).decode()


def encoded_manifest(manifest):
    return base64.b64encode(
        zlib.compress(json.dumps(manifest, sort_keys=True).encode())
    ).decode()


def synthetic_fixture(root):
    source = guard_source()
    _, areas = literal_assignment(source, "SOURCE_ROOTS")
    _, root_files = literal_assignment(source, "ROOT_FILES")
    _, exclusions = literal_assignment(source, "EXCLUSIONS")
    files = {}
    for area in areas:
        path = root / area / "controlled.txt"
        path.parent.mkdir(parents=True)
        path.write_text("synthetic source fixture\n")
        files[path.relative_to(root).as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    for name in [
        ".gitlab-ci.yml",
        ".gitleaks.toml",
        "pyproject.toml",
        "uv.lock",
        "security-policy.yaml",
        ".gitignore",
    ]:
        path = root / name
        path.write_text("synthetic protected configuration\n")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "record_type": "protected_source_integrity_manifest",
        "schema_version": "1.0",
        "source_roots": list(areas),
        "root_files": list(root_files),
        "self_exclusions": list(exclusions),
        "files": files,
    }
    return source, manifest


def run_guard(root, source, manifest=None, environment=None):
    if manifest is not None:
        source = replace_payload(source, encoded_manifest(manifest))
    env = {
        "PATH": os.environ.get("PATH", ""),
        "CI_PROJECT_ID": "86656946",
        "CI_COMMIT_BRANCH": "acceptance/v2-004",
        "CI_COMMIT_REF_PROTECTED": "true",
    }
    if environment:
        env.update(environment)
    return subprocess.run(
        [sys.executable, "-I", "-B", "-"],
        input=source,
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_trusted_wrapper_uses_fixed_original_source_and_atomic_protected_overlay():
    wrapper = yaml.safe_load((ROOT / WRAPPER).read_text())
    assert set(wrapper) == {"include"}
    assert wrapper["include"] == [
        {
            "project": "ayitnovel/ainovelos",
            "ref": "9fe51abf5ba2e050b7f48204f5c26927ace712af",
            "file": ".gitlab-ci.yml",
        },
        {
            "project": "ayitnovel/ainovelos",
            "ref": "acceptance/v2-004",
            "file": OVERLAY,
            "rules": [
                {
                    "if": '$CI_COMMIT_BRANCH == "acceptance/v2-004" && $CI_COMMIT_REF_PROTECTED == "true"'
                }
            ],
        },
    ]
    overlay = overlay_document()
    assert set(overlay) == {"default"}
    assert set(overlay["default"]) == {"tags", "before_script"}
    assert overlay["default"]["tags"] == ["trusted-acceptance"]
    original = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())
    assert (
        overlay["default"]["before_script"][1:]
        == original["default"]["before_script"]
        == [
            "python -m pip install --index-url https://pypi.org/simple uv==0.12.17",
            "uv --version",
            "uv sync --locked",
        ]
    )
    for job in [
        "static",
        "schema_contract",
        "unit",
        "arch_fitness",
        "postgres_env",
        "secret_dependency",
    ]:
        assert "tags" not in original[job]
        assert "before_script" not in original[job]
        assert original[job]["allow_failure"] is False
    assert "include:local" not in (ROOT / WRAPPER).read_text()


def source_only_subject(tmp_path, repository=ROOT):
    """Read a fixed Git tree; mutable worktree files never enter the fixture."""
    subject = tmp_path / "source-only-subject"
    subject.mkdir()
    document = yaml.safe_load(
        subprocess.run(
            ["git", "show", HISTORICAL_GUARD_REVISION + ":" + OVERLAY],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    source = guard_source(document)
    _, areas = literal_assignment(source, "SOURCE_ROOTS")
    _, auxiliary = literal_assignment(source, "AUXILIARY_MODULE_ROOTS")
    _, root_files = literal_assignment(source, "ROOT_FILES")
    top_level = set(
        subprocess.run(
            ["git", "ls-tree", "--name-only", "-z", HISTORICAL_GUARD_REVISION],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\0")
    )
    assert set(areas).issubset(top_level), "missing historical source roots"
    # Select roots independently of the embedded manifest. All their tracked
    # files must be checked, including any extra files absent from its payload.
    paths = [name for name in (*areas, *auxiliary, *root_files) if name in top_level]
    archive = subprocess.run(
        ["git", "archive", "--format=tar", HISTORICAL_GUARD_REVISION, "--", *paths],
        cwd=repository,
        capture_output=True,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as historical:
        historical.extractall(subject, filter="data")
    return subject, source


def test_actual_guard_accepts_current_source_only_subject(tmp_path):
    """Keep the historical test ID; its source is the fixed Git fixture, not HEAD."""
    subject, source = source_only_subject(tmp_path)
    assert not os.path.lexists(subject / ".venv")
    result = run_guard(subject, source)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "PASS"


def test_fixed_historical_subject_is_independent_of_dirty_worktree(tmp_path):
    checkout = tmp_path / "dirty-checkout"
    subprocess.run(
        [
            "git",
            "clone",
            "--shared",
            "--no-checkout",
            "--quiet",
            str(ROOT),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )
    for name in [
        "scripts/ci/run_gate.py",
        "src/anovel/new_domain.py",
        "tests/__pycache__/untracked.pyc",
        OVERLAY,
    ]:
        changed = checkout / name
        changed.parent.mkdir(parents=True, exist_ok=True)
        changed.write_text("dirty worktree content must not enter historical fixture\n")
    subject, source = source_only_subject(tmp_path, repository=checkout)
    assert not (subject / "src/anovel/new_domain.py").exists()
    assert not (subject / "tests/__pycache__").exists()
    result = run_guard(subject, source)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "PASS"


@pytest.mark.parametrize("mutation", ["changed", "missing", "extra"])
def test_actual_guard_rejects_mutated_fixed_historical_subject(tmp_path, mutation):
    subject, source = source_only_subject(tmp_path)
    item = subject / "scripts/ci/run_gate.py"
    if mutation == "changed":
        item.write_text("unapproved changed source\n")
    elif mutation == "missing":
        item.unlink()
    else:
        (subject / "scripts/unapproved.py").write_text("unapproved additional source\n")
    result = run_guard(subject, source)
    assert result.returncode == 1
    failure = json.loads(result.stderr)
    assert failure[mutation]
    assert failure["status"] == "FAIL"


def test_actual_guard_accepts_synthetic_fixture_and_unmonitored_output(tmp_path):
    source, manifest = synthetic_fixture(tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/output.txt").write_text(
        "generated outside protected source roots"
    )
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["checked_files"] == len(manifest["files"])


def test_previously_absent_scanner_configuration_cannot_be_added(tmp_path):
    source, manifest = synthetic_fixture(tmp_path)
    scanner_configuration = tmp_path / ".gitleaks.toml"
    scanner_configuration.unlink()
    del manifest["files"][".gitleaks.toml"]
    positive = run_guard(tmp_path, source, manifest)
    assert positive.returncode == 0, positive.stderr
    scanner_configuration.write_text("[allowlist]\npaths = ['.*']\n")
    negative = run_guard(tmp_path, source, manifest)
    assert negative.returncode == 1
    assert json.loads(negative.stderr)["extra"] == [".gitleaks.toml"]


@pytest.mark.parametrize(
    "name",
    [
        "pytest.ini",
        ".pytest.ini",
        "setup.cfg",
        "tox.ini",
        "conftest.py",
        "sitecustomize.py",
        "usercustomize.py",
        ".gitattributes",
        ".gitmodules",
        "setup.py",
        ".coveragerc",
    ],
)
def test_actual_guard_rejects_new_root_configuration(tmp_path, name):
    source, manifest = synthetic_fixture(tmp_path)
    (tmp_path / name).write_text("unapproved root configuration\n")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert json.loads(result.stderr)["extra"] == [name]


@pytest.mark.parametrize(
    "mutation",
    [
        "changed",
        "deleted",
        "extra",
        "ignored-extra",
        "new-policy",
        "extra-root-config",
        "file-symlink",
        "directory-symlink",
        "source-root-symlink",
        "root-config-symlink",
        "fifo",
    ],
)
def test_actual_guard_rejects_changed_or_unlisted_source(tmp_path, mutation):
    source, manifest = synthetic_fixture(tmp_path)
    item = tmp_path / "scripts/controlled.txt"
    if mutation == "changed":
        item.write_text("altered")
    elif mutation == "deleted":
        item.unlink()
    elif mutation in {"extra", "ignored-extra"}:
        if mutation == "ignored-extra":
            (tmp_path / ".gitignore").write_text("scripts/hidden.py\n")
            manifest["files"][".gitignore"] = hashlib.sha256(
                (tmp_path / ".gitignore").read_bytes()
            ).hexdigest()
        (tmp_path / "scripts/hidden.py").write_text("print('unapproved source')")
    elif mutation == "new-policy":
        (tmp_path / "plan/new-policy.yaml").write_text("allow_failure: true\n")
    elif mutation == "extra-root-config":
        (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = --ignore=tests\n")
    elif mutation == "file-symlink":
        item.unlink()
        item.symlink_to(tmp_path / "tests/controlled.txt")
    elif mutation == "directory-symlink":
        (tmp_path / "scripts/linked").symlink_to(
            tmp_path / "tests", target_is_directory=True
        )
    elif mutation == "source-root-symlink":
        item.unlink()
        (tmp_path / "scripts").rmdir()
        (tmp_path / "scripts").symlink_to(tmp_path / "tests", target_is_directory=True)
    elif mutation == "root-config-symlink":
        (tmp_path / "uv.lock").unlink()
        (tmp_path / "uv.lock").symlink_to(tmp_path / "security-policy.yaml")
    else:
        os.mkfifo(tmp_path / "scripts/pipe")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "FAIL"


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "incomplete",
        "bad-hash",
        "wrong-roots",
        "wrong-exclusions",
        "unknown-key",
        "path-escape",
        "malformed-payload",
    ],
)
def test_actual_guard_rejects_malformed_or_incomplete_manifest(tmp_path, mutation):
    source, manifest = synthetic_fixture(tmp_path)
    if mutation == "empty":
        manifest["files"] = {}
    elif mutation == "incomplete":
        del manifest["files"]["scripts/controlled.txt"]
    elif mutation == "bad-hash":
        manifest["files"]["scripts/controlled.txt"] = "invalid"
    elif mutation == "wrong-roots":
        manifest["source_roots"] = ["scripts"]
    elif mutation == "wrong-exclusions":
        manifest["self_exclusions"].append("scripts/controlled.txt")
    elif mutation == "unknown-key":
        manifest["skip_scan"] = True
    elif mutation == "path-escape":
        manifest["files"]["scripts/../outside.py"] = "0" * 64
    else:
        source = replace_payload(source, "malformed payload")
        manifest = None
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "FAIL"


@pytest.mark.parametrize(
    "environment",
    [
        {"CI_PROJECT_ID": "1"},
        {"CI_PROJECT_ID": ""},
        {"CI_COMMIT_BRANCH": "dev_gpt"},
        {"CI_COMMIT_REF_PROTECTED": "false"},
        {"CI_COMMIT_REF_PROTECTED": ""},
    ],
)
def test_actual_guard_rejects_wrong_or_missing_protected_context(tmp_path, environment):
    source, manifest = synthetic_fixture(tmp_path)
    result = run_guard(tmp_path, source, manifest, environment)
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "FAIL"


@pytest.mark.parametrize("kind", ["regular", "symlink"])
def test_only_two_protected_source_files_are_self_excluded(tmp_path, kind):
    source, manifest = synthetic_fixture(tmp_path)
    for name in [WRAPPER, OVERLAY]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "regular":
            path.write_text("provided by protected GitLab include source")
        else:
            path.symlink_to(tmp_path / "scripts/controlled.txt")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == (0 if kind == "regular" else 1), result.stderr
    _, exclusions = literal_assignment(source, "EXCLUSIONS")
    assert list(exclusions) == [WRAPPER, OVERLAY]


@pytest.mark.parametrize(
    "mutation", ["statement", "payload-semicolon", "duplicate-binding"]
)
def test_candidate_guard_code_is_rejected_before_any_execution(tmp_path, mutation):
    source = guard_source()
    marker = tmp_path / "malicious-guard-must-not-run"
    inserted = (
        "__import__('pathlib').Path("
        + repr(str(marker))
        + ").write_text('unexpected execution')"
    )
    if mutation == "statement":
        source = source.replace(
            "def regular_digest(path):", inserted + "\n\ndef regular_digest(path):", 1
        )
    elif mutation == "payload-semicolon":
        _, end = payload_span(source)
        raw = source.encode()
        source = (raw[:end] + ("; " + inserted).encode() + raw[end:]).decode()
    else:
        source = source.replace(
            "def regular_digest(path):",
            "EXPECTED_JSON_ZLIB_B64 = 'duplicate'\n"
            + inserted
            + "\n\ndef regular_digest(path):",
            1,
        )
    document = overlay_document()
    document["default"]["before_script"][0] = (
        "python -I -B - <<'ANOVELOS_TRUSTED_GUARD'\n"
        + source
        + "\nANOVELOS_TRUSTED_GUARD"
    )
    with pytest.raises(AssertionError):
        verified = guard_source(document)
        run_guard(tmp_path, verified)
    assert not marker.exists()


def test_guard_payload_data_can_change_without_changing_executable_pin(tmp_path):
    source, manifest = synthetic_fixture(tmp_path)
    changed = replace_payload(source, encoded_manifest(manifest))
    document = overlay_document()
    document["default"]["before_script"][0] = (
        "python -I -B - <<'ANOVELOS_TRUSTED_GUARD'\n"
        + changed
        + "\nANOVELOS_TRUSTED_GUARD"
    )
    verified = guard_source(document)
    result = run_guard(tmp_path, verified)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling-symlink"])
def test_preinstall_guard_rejects_every_preexisting_virtual_environment(tmp_path, kind):
    source, manifest = synthetic_fixture(tmp_path)
    environment = tmp_path / ".venv"
    if kind == "directory":
        environment.mkdir()
        (environment / "poisoned.pth").write_text("unapproved interpreter startup")
    elif kind == "file":
        environment.write_text("preexisting environment marker")
    elif kind == "symlink":
        environment.symlink_to(tmp_path / "scripts", target_is_directory=True)
    else:
        environment.symlink_to(
            tmp_path / "missing-environment", target_is_directory=True
        )
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert ".venv" in json.loads(result.stderr)["reason"]


@pytest.mark.parametrize(
    "name", ["uv.toml", "pip.conf", "pip.ini", ".pypirc", ".pip", ".uv"]
)
def test_preinstall_guard_rejects_candidate_installer_configuration(tmp_path, name):
    source, manifest = synthetic_fixture(tmp_path)
    configuration = tmp_path / name
    if name in {".pip", ".uv"}:
        configuration.mkdir()
        (configuration / "config").write_text("unapproved installation config")
    else:
        configuration.write_text("unapproved installation config")
        # Matching candidate-provided payload data does not authorize these
        # installation entry points; rejection precedes inventory decoding.
        manifest["files"][name] = hashlib.sha256(configuration.read_bytes()).hexdigest()
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert name in json.loads(result.stderr)["reason"]


@pytest.mark.parametrize(
    "name",
    [
        "pip.py",
        "pytest.py",
        "arbitrary_shadow.py",
        "other_module.pyc",
        "other_module.cpython-312-x86_64-linux-gnu.so",
    ],
)
def test_guard_rejects_any_new_root_python_or_extension_module(tmp_path, name):
    source, manifest = synthetic_fixture(tmp_path)
    (tmp_path / name).write_text("unapproved module bytes")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert name in json.loads(result.stderr)["reason"]


@pytest.mark.parametrize(
    "name", ["pip", "pytest", "arbitrary_package", "namespace_package"]
)
def test_guard_rejects_new_root_package_and_namespace_directories(tmp_path, name):
    source, manifest = synthetic_fixture(tmp_path)
    package = tmp_path / name
    package.mkdir()
    (
        package / ("child.py" if name == "namespace_package" else "__init__.py")
    ).write_text("unapproved module bytes")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert name in json.loads(result.stderr)["reason"]


def test_existing_auxiliary_root_module_identity_is_frozen(tmp_path):
    source, manifest = synthetic_fixture(tmp_path)
    module = tmp_path / "docs/existing_module.py"
    module.parent.mkdir()
    module.write_text("known module bytes")
    manifest["files"]["docs/existing_module.py"] = hashlib.sha256(
        module.read_bytes()
    ).hexdigest()
    positive = run_guard(tmp_path, source, manifest)
    assert positive.returncode == 0, positive.stderr
    module.write_text("changed module bytes")
    negative = run_guard(tmp_path, source, manifest)
    assert negative.returncode == 1
    assert json.loads(negative.stderr)["changed"] == ["docs/existing_module.py"]


@pytest.mark.parametrize(
    "name",
    [
        "docs/__init__.py",
        "docs/namespace_child.py",
        "dist/__init__.py",
        "dist/shadow.py",
    ],
)
def test_known_root_directory_cannot_acquire_unapproved_modules(tmp_path, name):
    source, manifest = synthetic_fixture(tmp_path)
    module = tmp_path / name
    module.parent.mkdir()
    module.write_text("unapproved module bytes")
    result = run_guard(tmp_path, source, manifest)
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "FAIL"
