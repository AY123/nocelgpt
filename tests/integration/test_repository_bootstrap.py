"""Bootstrap acceptance: clean install, real distributions, preserved inputs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def run(argv, *, cwd, env, check=True):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    if check:
        assert result.returncode == 0, f"{argv!r}\n{result.stdout}\n{result.stderr}"
    return result


@pytest.fixture
def clean_project(tmp_path):
    uv = shutil.which("uv")
    assert uv, "uv 0.12.17 must be on PATH; see README"
    source = tmp_path / "project"
    source.mkdir()
    for name in ("pyproject.toml", "uv.lock", ".python-version", "README.md"):
        shutil.copyfile(ROOT / name, source / name)
    shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    env = os.environ.copy()
    for key in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    env["UV_PROJECT_ENVIRONMENT"] = str(source / ".venv")
    env["UV_PYTHON"] = sys.executable
    return uv, source, env


def test_clean_locked_install_and_import(clean_project, tmp_path):
    uv, source, env = clean_project
    lock = (source / "uv.lock").read_bytes()
    assert not (source / ".venv").exists()
    run([uv, "sync", "--locked", "--no-editable"], cwd=source, env=env)
    python = source / ".venv/bin/python"
    result = run([str(python), "-I", "-c", "import anovel,sys; from importlib.metadata import version; assert version('anovelos') == anovel.__version__; assert sys.version_info[:3] == (3,12,14); print(anovel.__file__)"], cwd=tmp_path, env=env)
    assert "/site-packages/anovel/" in result.stdout
    assert (source / "uv.lock").read_bytes() == lock
    discovered = run([str(python), "-m", "pytest", "--collect-only", "-q", str(ROOT / "tests")], cwd=tmp_path, env=env)
    assert "test_postgres_start_connect_and_cleanup" in discovered.stdout
    assert "test_clean_locked_install_and_import" in discovered.stdout
    print("CLEAN_INSTALL Python=3.12.14 non-editable site-packages import; lock unchanged; pytest discovery succeeded")


def test_locked_install_rejects_manifest_drift(clean_project):
    uv, source, env = clean_project
    lock = (source / "uv.lock").read_bytes()
    manifest = source / "pyproject.toml"
    original = manifest.read_text()
    # Prove a valid lock can be read offline with an independent empty cache.
    # Adding a registry dependency here previously failed on uncached metadata
    # before uv could reach the lock-drift check, especially in fresh Linux CI.
    cache = source.parent / "cold-lock-cache"
    assert not cache.exists()
    env = dict(env, UV_CACHE_DIR=str(cache))
    check = [uv, "sync", "--locked", "--offline", "--dry-run", "--no-install-project", "--no-default-groups"]
    run(check, cwd=source, env=env)
    assert (source / "uv.lock").read_bytes() == lock

    # Removing fixture dev/runtime dependencies is a valid dependency-graph change,
    # not a syntax error or a modification to the real project requirements.
    before, dependency_tail = original.split("dev = [", 1)
    _, after = dependency_tail.split("\n]", 1)
    changed = before + "dev = []" + after
    runtime = tomllib.loads(original)["project"]["dependencies"]
    runtime_line = next(line for line in original.splitlines() if line.startswith("dependencies = "))
    changed = changed.replace(runtime_line, "dependencies = []")
    expected = tomllib.loads(original)
    expected["dependency-groups"]["dev"] = []
    assert runtime  # Canon introduces runtime packages; preserve the cold-cache test.
    expected["project"]["dependencies"] = []
    assert tomllib.loads(changed) == expected
    manifest.write_text(changed)
    permitted = run([arg for arg in check if arg != "--locked"], cwd=source, env=env)
    assert "Would update lockfile" in permitted.stderr
    assert (source / "uv.lock").read_bytes() == lock

    # Keep the real installation command and prove its specific locked refusal,
    # rather than accepting any nonzero network or configuration error.
    negative_cache = source.parent / "negative-lock-cache"
    assert not negative_cache.exists()
    env["UV_CACHE_DIR"] = str(negative_cache)
    result = run([uv, "sync", "--locked", "--offline"], cwd=source, env=env, check=False)
    assert result.returncode != 0
    assert "lock" in result.stderr.lower()
    assert "The lockfile at `uv.lock` needs to be updated, but `--locked` was provided." in result.stderr
    assert "network was disabled" not in result.stderr
    assert (source / "uv.lock").read_bytes() == lock


def test_builds_exclude_archive_and_tools(clean_project, tmp_path):
    uv, source, env = clean_project
    out = tmp_path / "distributions"
    # Build the real repository, so exclusion assertions exercise its real archive.
    run([uv, "build", "--out-dir", str(out)], cwd=ROOT, env=env)
    wheels = list(out.glob("*.whl"))
    sdists = list(out.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
        assert "anovel/__init__.py" in names
        assert "anovel/canon/sql/0001_root.sql" in names
        assert "anovel/canon/sql/0002_chapter.sql" in names
        assert all(name.startswith(("anovel/", "anovelos-0.1.0.dist-info/")) for name in names)
    with tarfile.open(sdists[0]) as sdist:
        names = [str(Path(member.name).relative_to("anovelos-0.1.0")) for member in sdist.getmembers()]
        assert "src/anovel/__init__.py" in names
        assert "src/anovel/canon/sql/0001_root.sql" in names
        assert "src/anovel/canon/sql/0002_chapter.sql" in names
        assert not any(Path(name).parts and Path(name).parts[0] in {"plan", ".claude", "tests", "scripts", "docs", "dist"} for name in names)
    # A wheel must also import outside the source checkout, without editable paths.
    target = tmp_path / "wheel-env"
    run([uv, "venv", "--python", sys.executable, str(target)], cwd=tmp_path, env=env)
    run([uv, "pip", "install", "--python", str(target / "bin/python"), "--no-deps", str(wheels[0])], cwd=tmp_path, env=env)
    result = run([str(target / "bin/python"), "-I", "-c", "import anovel; print(anovel.__file__)"], cwd=tmp_path, env=env)
    assert str(target) in result.stdout
    print("DISTRIBUTIONS wheel+sdist inspected; archive/tooling absent; wheel import succeeded")


def test_historical_materials_preserved():
    migration = json.loads((ROOT / "docs/repository-layout-migration.json").read_text())
    retained = [entry for entry in migration["entries"] if "retained_path" in entry]
    assert any(entry["source"].startswith(".claude/convergence/") for entry in retained)
    assert any(entry["action"] == "ARCHIVE_UNIQUE_AND_REMOVE_ROOT" for entry in retained)
    for entry in retained:
        contents = (ROOT / entry["retained_path"]).read_bytes()
        assert len(contents) == entry["bytes"], entry["source"]
        assert hashlib.sha256(contents).hexdigest() == entry["sha256"], entry["source"]
        assert not (ROOT / entry["source"]).exists(), entry["source"]
    sources = yaml.safe_load((ROOT / "plan/machine/source-register.yaml").read_text())["files"]
    for item in sources:
        contents = (ROOT / "plan" / item["archive_path"]).read_bytes()
        assert len(contents) == item["bytes"]
        assert hashlib.sha256(contents).hexdigest() == item["sha256"]
    print(f"MIGRATION {len(retained)} retained files and {len(sources)} registered snapshots match; hidden history covered")


def test_current_entrypoints_and_runtime_decision():
    assert "plan/README.md" in (ROOT / "README.md").read_text()
    assert "plan/README.md" in (ROOT / "AGENTS.md").read_text()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["requires-python"] == "==" + (ROOT / ".python-version").read_text().strip()
    assert project["tool"]["uv"]["required-version"] == "==0.12.17"
    packet = yaml.safe_load((ROOT / "plan/validation/execution/V2-001/execution-packet.yaml").read_text())
    assert packet["task_id"] == "V2-001"
    assert packet["plan_version"] == "1.3.0"
    assert packet["environment"]["runtime_versions"]["python"] == "3.12.14"
    assert packet["implementer"] and packet["verifier"] and packet["repository_revision"]
    assert packet["environment"]["ci_context"] is None


def test_canon_runtime_dependencies_and_sql_present_without_dev_group(clean_project, tmp_path):
    uv, source, env = clean_project
    run([uv, "sync", "--locked", "--no-editable", "--no-default-groups"], cwd=source, env=env)
    python = source / ".venv/bin/python"
    result = run([str(python), "-I", "-c", "from anovel.canon.commit_service import CanonCommitService; from anovel.canon.migrations import migrate; from importlib.resources import files; import sqlalchemy,psycopg; assert b'CREATE SCHEMA anovel_canon' in files('anovel.canon').joinpath('sql/0001_root.sql').read_bytes(); assert files('anovel.canon').joinpath('sql/0002_chapter.sql').read_bytes(); print('CANON_RUNTIME_AND_MIGRATION_READY')"], cwd=tmp_path, env=env)
    assert result.stdout.strip() == "CANON_RUNTIME_AND_MIGRATION_READY"
