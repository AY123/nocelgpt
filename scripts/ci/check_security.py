"""Run real pinned scanners on tracked worktree, full Git history and locked packages.

Scanner output is captured privately. Reports contain hashes and safe metadata,
never secret values or scanner stdout/stderr. Local PASS is not remote CI trust.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path, PurePosixPath
from typing import Any, Callable, cast

import yaml
from bootstrap_scanners import ARCHIVES, VERSION, verify_cached_scanner
from secret_exceptions import (
    ExceptionFailure,
    consume,
    finding_identity,
    load_ledger,
    parse_json,
)

ROOT = Path(__file__).resolve().parents[2]
AUDIT_VERSION = "2.10.1"
PACKAGE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?")
PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([A-Za-z0-9][A-Za-z0-9_.+!-]*)")
CODE = re.compile(r"[A-Za-z0-9_.-]{1,200}")


class SecurityFailure(ValueError):
    """A fixed safe error code; never carry scanner/credential content."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def git(root: Path, *arguments: str) -> bytes:
    env = os.environ.copy()
    env["GIT_NO_LAZY_FETCH"] = "1"
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        env=env,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise SecurityFailure("SECURITY_GIT_COMMAND")
    return result.stdout


def read_policy(root: Path) -> dict[str, Any]:
    value = yaml.safe_load((root / "security-policy.yaml").read_text())
    if not isinstance(value, dict):
        raise SecurityFailure("SECURITY_POLICY")
    scanner = value.get("secret_scanner")
    if (
        not isinstance(scanner, dict)
        or scanner.get("version") != VERSION
        or scanner.get("linux_x64_sha256") != ARCHIVES[("Linux", "x86_64")][1]
    ):
        raise SecurityFailure("SECURITY_SCANNER_PIN")
    if sorted(value.get("scan_targets", [])) != ["git_history", "tracked_worktree"]:
        raise SecurityFailure("SECURITY_SCAN_TARGETS")
    exceptions = value.get("dependency_exceptions")
    if not isinstance(exceptions, list):
        raise SecurityFailure("SECURITY_DEPENDENCY_EXCEPTIONS")
    identities: set[tuple[str, str, str]] = set()
    for exception in exceptions:
        if (
            not isinstance(exception, dict)
            or set(exception)
            != {"vulnerability_id", "package", "version", "owner", "reason", "expiry"}
            or not all(
                isinstance(exception.get(key), str) and exception[key].strip()
                for key in exception
            )
        ):
            raise SecurityFailure("SECURITY_EXCEPTION_FIELDS")
        if not PACKAGE.fullmatch(exception["package"]) or not CODE.fullmatch(
            exception["vulnerability_id"]
        ):
            raise SecurityFailure("SECURITY_EXCEPTION_IDENTITY")
        try:
            expiry = date.fromisoformat(exception["expiry"])
        except ValueError as exc:
            raise SecurityFailure("SECURITY_EXCEPTION_EXPIRY") from exc
        if expiry < datetime.now(timezone.utc).date():
            raise SecurityFailure("SECURITY_EXCEPTION_EXPIRED")
        identity = (
            canonical(exception["package"]),
            exception["version"],
            exception["vulnerability_id"],
        )
        if identity in identities:
            raise SecurityFailure("SECURITY_EXCEPTION_DUPLICATE")
        identities.add(identity)
    return cast(dict[str, Any], value)


def prepare_output(root: Path, output: Path) -> Path:
    output = output.resolve()
    if output.exists():
        raise SecurityFailure("SECURITY_OUTPUT_EXISTS")
    if output.is_relative_to(root):
        relative = output.relative_to(root)
        if not relative.parts or relative.parts[0] in {"plan", ".git"}:
            raise SecurityFailure("SECURITY_OUTPUT_SOURCE")
        ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--quiet", "--", str(relative)],
            capture_output=True,
            check=False,
        )
        if ignored.returncode or git(root, "ls-files", "--", str(relative)).strip():
            raise SecurityFailure("SECURITY_OUTPUT_SOURCE")
    output.mkdir(parents=True, exist_ok=False)
    return output


def scanner_binary(path: Path) -> Path:
    try:
        return verify_cached_scanner(path)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise SecurityFailure("SECURITY_SCANNER_BOOTSTRAP") from None


def tracked_copy(root: Path, target: Path) -> dict[str, int]:
    rows = git(root, "ls-files", "--stage", "-z").split(b"\0")
    count = 0
    removed = 0
    for row in rows:
        if not row:
            continue
        metadata, raw = row.split(b"\t", 1)
        mode, _oid, stage = metadata.decode().split()
        name = os.fsdecode(raw)
        parts = PurePosixPath(name).parts
        if (
            mode not in {"100644", "100755"}
            or stage != "0"
            or not parts
            or any(p in {"..", "."} for p in parts)
        ):
            raise SecurityFailure("SECURITY_TRACKED_TYPE")
        source = root / name
        if source.is_symlink() or any(
            parent.is_symlink()
            for parent in source.parents
            if parent != root and parent.is_relative_to(root)
        ):
            raise SecurityFailure("SECURITY_TRACKED_SYMLINK")
        if not source.exists():
            removed += 1
            continue
        if not source.is_file() or not source.resolve().is_relative_to(root):
            raise SecurityFailure("SECURITY_TRACKED_PATH")
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        count += 1
    if count == 0:
        raise SecurityFailure("SECURITY_TRACKED_EMPTY")
    return {"tracked_files": count, "deleted_worktree_files": removed}


def complete_history(root: Path) -> int:
    if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise SecurityFailure("SECURITY_HISTORY_SHALLOW")
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "extensions.partialClone"],
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 1 or result.stdout:
        raise SecurityFailure("SECURITY_HISTORY_PARTIAL")
    objects = git(root, "rev-list", "--objects", "--all", "--missing=print")
    if any(line.startswith(b"?") for line in objects.splitlines()):
        raise SecurityFailure("SECURITY_HISTORY_MISSING_OBJECTS")
    count = int(git(root, "rev-list", "--all", "--count").strip())
    if count <= 0:
        raise SecurityFailure("SECURITY_HISTORY_EMPTY")
    return count


def scan_secrets(
    root: Path,
    output: Path,
    executable: Path,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executable = scanner_binary(executable)
    commits = complete_history(root)
    scans: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    exception_config = policy.get("secret_exceptions") if policy is not None else None
    baseline = git(root, "rev-parse", "HEAD").decode().strip()
    exception_error: str | None = (
        "SECRET_EXCEPTION_CONFIG_MISSING"
        if policy is not None and "secret_exceptions" not in policy
        else None
    )
    if policy is not None and "secret_exceptions" in policy:
        try:
            if not isinstance(exception_config, dict):
                raise ExceptionFailure("SECRET_EXCEPTION_SCHEMA")
            baseline = load_ledger(root, exception_config)["baseline_revision"]
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            # Continue the complete scan; invalid approval metadata cannot hide it.
            exception_error = (
                str(exc)
                if isinstance(exc, ExceptionFailure)
                else "SECRET_EXCEPTION_INVALID"
            )
    with tempfile.TemporaryDirectory(prefix="anovel-secret-scan-") as temporary:
        private = Path(temporary)
        copied = private / "tracked"
        copied.mkdir()
        inventory = tracked_copy(root, copied)
        config = private / "scanner.toml"
        config.write_text("[extend]\nuseDefault = true\n")
        ignore = private / "empty-ignore"
        ignore.write_text("")
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GITLEAKS_")
        }
        for label, command, source in [
            ("tracked_worktree", "dir", copied),
            ("git_history", "git", root),
        ]:
            report = private / f"{label}.json"
            argv = [
                str(executable),
                command,
                str(source),
                "--config",
                str(config),
                "--gitleaks-ignore-path",
                str(ignore),
                "--ignore-gitleaks-allow",
                "--redact=100",
                "--no-banner",
                "--no-color",
                "--report-format",
                "json",
                "--report-path",
                str(report),
                "--exit-code",
                "1",
            ]
            if command == "git":
                argv.append("--log-opts=--all --full-history --root")
            try:
                result = subprocess.run(
                    argv,
                    cwd=private,
                    env=env,
                    capture_output=True,
                    timeout=600,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                scans.append(
                    {
                        "target": label,
                        "status": "FAIL",
                        "error": "SECURITY_SECRET_EXECUTION",
                    }
                )
                continue
            row: dict[str, Any] = {
                "target": label,
                "exit_code": result.returncode,
                "stdout_sha256": sha(result.stdout),
                "stderr_sha256": sha(result.stderr),
            }
            if not report.is_file():
                row.update(status="FAIL", error="SECURITY_SECRET_REPORT_MISSING")
            else:
                try:
                    payload = report.read_bytes()
                    row["report_sha256"] = sha(payload)
                    findings = parse_json(payload)
                    if not isinstance(findings, list) or any(
                        not isinstance(item, dict) for item in findings
                    ):
                        raise SecurityFailure("SECURITY_SECRET_REPORT_INVALID")
                    row.update(
                        finding_count=len(findings),
                        locations=[],
                        finding_fingerprints=[
                            sha(str(item.get("Fingerprint", "")).encode())
                            for item in findings
                        ],
                        status="PASS"
                        if result.returncode == 0 and not findings
                        else "FAIL",
                    )
                    for item in findings:
                        try:
                            identity = finding_identity(
                                root, item, label, copied, baseline
                            )
                            identities.append(identity)
                            row["locations"].append(
                                {
                                    key: identity[key]
                                    for key in ("rule_id", "path", "line", "commit")
                                }
                            )
                        except (
                            OSError,
                            ValueError,
                            TypeError,
                            KeyError,
                            subprocess.SubprocessError,
                        ) as exc:
                            row.update(
                                status="FAIL",
                                error=str(exc)
                                if isinstance(exc, ExceptionFailure)
                                else "SECURITY_SECRET_FINDING_INVALID",
                            )
                    if not (
                        (result.returncode == 0 and not findings)
                        or (result.returncode == 1 and findings)
                    ):
                        row["error"] = "SECURITY_SECRET_EXIT_REPORT_MISMATCH"
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    row.update(
                        status="FAIL",
                        error=str(exc)
                        if isinstance(exc, (ExceptionFailure, SecurityFailure))
                        else "SECURITY_SECRET_REPORT_INVALID",
                    )
            scans.append(row)
    try:
        decisions = consume(root, identities, exception_config)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        decisions = {
            "status": "FAIL",
            "detected": len(identities),
            "error": str(exc)
            if isinstance(exc, ExceptionFailure)
            else "SECRET_EXCEPTION_INVALID",
        }
    decisions["detected"] = sum(row.get("finding_count", 0) for row in scans)
    decisions["identified"] = len(identities)
    if exception_error is not None:
        decisions.update(status="FAIL", error=exception_error)
    scan_complete = all("error" not in row and "locations" in row for row in scans)
    raw_status = "PASS" if all(row["status"] == "PASS" for row in scans) else "FAIL"
    result_data: dict[str, Any] = {
        "status": "PASS" if scan_complete and decisions["status"] == "PASS" else "FAIL",
        "raw_status": raw_status,
        "scanner": "gitleaks",
        "version": VERSION,
        "history_commits": commits,
        **inventory,
        "scans": scans,
        "finding_identities": identities,
        "exception_consumption": decisions,
    }
    (output / "secret-scan.json").write_text(json.dumps(result_data, indent=2) + "\n")
    return result_data


def locked_packages(root: Path) -> set[tuple[str, str]]:
    lock = tomllib.loads((root / "uv.lock").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    if (
        lock.get("version") != 1
        or not isinstance(lock.get("package"), list)
        or not lock["package"]
    ):
        raise SecurityFailure("SECURITY_LOCK_FORMAT")
    packages: set[tuple[str, str]] = set()
    local = 0
    for package in lock["package"]:
        name = package.get("name", "")
        version = package.get("version", "")
        if (
            not isinstance(name, str)
            or not isinstance(version, str)
            or not PIN.fullmatch(f"{name}=={version}")
        ):
            raise SecurityFailure("SECURITY_LOCK_PACKAGE")
        source = package.get("source")
        if (
            source == {"editable": "."}
            and canonical(name) == canonical(project["project"]["name"])
            and version == project["project"]["version"]
        ):
            local += 1
            continue
        if source not in (
            {"registry": "https://pypi.org/simple"},
            {"registry": "https://pypi.org/simple/"},
        ):
            raise SecurityFailure("SECURITY_LOCK_SOURCE")
        artifacts = ([package["sdist"]] if "sdist" in package else []) + package.get(
            "wheels", []
        )
        if not artifacts or any(
            not re.fullmatch(r"sha256:[0-9a-f]{64}", item.get("hash", ""))
            for item in artifacts
        ):
            raise SecurityFailure("SECURITY_LOCK_HASH")
        packages.add((canonical(name), version))
    if local != 1 or not packages:
        raise SecurityFailure("SECURITY_LOCK_PROJECT")
    # uv.lock does not include the PEP 517 build backend. Audit its exact pin too.
    for requirement in project.get("build-system", {}).get("requires", []):
        match = PIN.fullmatch(requirement) if isinstance(requirement, str) else None
        if match is None:
            raise SecurityFailure("SECURITY_BUILD_DEPENDENCY_PIN")
        packages.add((canonical(match[1]), match[2]))
    return packages


def audit_dependencies(
    root: Path, output: Path, policy: dict[str, Any]
) -> dict[str, Any]:
    packages = locked_packages(root)
    scanner_versions = {version for name, version in packages if name == "pip-audit"}
    if (
        scanner_versions != {AUDIT_VERSION}
        or installed_version("pip-audit") != AUDIT_VERSION
    ):
        raise SecurityFailure("SECURITY_AUDIT_VERSION")
    requirements = output / "locked-audit-requirements.txt"
    requirements.write_text(
        "".join(f"{name}=={version}\n" for name, version in sorted(packages))
    )
    raw_report = output / "dependency-audit.json"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PIP_AUDIT_")
    }
    argv = [
        sys.executable,
        "-B",
        "-m",
        "pip_audit",
        "--requirement",
        str(requirements),
        "--no-deps",
        "--disable-pip",
        "--strict",
        "--format",
        "json",
        "--desc",
        "off",
        "--aliases",
        "on",
        "--vulnerability-service",
        "pypi",
        "--progress-spinner",
        "off",
        "--timeout",
        "30",
        "--output",
        str(raw_report),
    ]
    process = subprocess.run(
        argv, cwd=root, env=env, capture_output=True, timeout=600, check=False
    )
    row: dict[str, Any] = {
        "scanner": "pip-audit",
        "version": next(iter(scanner_versions)),
        "exit_code": process.returncode,
        "stdout_sha256": sha(process.stdout),
        "stderr_sha256": sha(process.stderr),
        "lock_sha256": sha((root / "uv.lock").read_bytes()),
        "requirements_sha256": sha(requirements.read_bytes()),
        "expected_packages": len(packages),
    }
    if not raw_report.is_file():
        row.update(status="FAIL", error="SECURITY_AUDIT_REPORT_MISSING")
        return row
    payload = json.loads(raw_report.read_text())
    dependencies = payload.get("dependencies") if isinstance(payload, dict) else payload
    if not isinstance(dependencies, list):
        raise SecurityFailure("SECURITY_AUDIT_REPORT_INVALID")
    seen: set[tuple[str, str]] = set()
    unresolved: list[dict[str, str]] = []
    exemptions: list[dict[str, str]] = []
    total_vulns = 0
    for dependency in dependencies:
        if not isinstance(dependency, dict) or "skip_reason" in dependency:
            raise SecurityFailure("SECURITY_AUDIT_SKIPPED_PACKAGE")
        name, version = dependency.get("name"), dependency.get("version")
        if (
            not isinstance(name, str)
            or not isinstance(version, str)
            or not PIN.fullmatch(f"{name}=={version}")
        ):
            raise SecurityFailure("SECURITY_AUDIT_PACKAGE")
        identity = (canonical(name), version)
        if (
            identity in seen
            or identity not in packages
            or not isinstance(dependency.get("vulns"), list)
        ):
            raise SecurityFailure("SECURITY_AUDIT_COVERAGE")
        seen.add(identity)
        for vulnerability in dependency["vulns"]:
            if (
                not isinstance(vulnerability, dict)
                or not isinstance(vulnerability.get("id"), str)
                or not CODE.fullmatch(vulnerability["id"])
            ):
                raise SecurityFailure("SECURITY_AUDIT_VULNERABILITY")
            total_vulns += 1
            identifiers = {vulnerability["id"]} | set(vulnerability.get("aliases", []))
            match = next(
                (
                    exception
                    for exception in policy["dependency_exceptions"]
                    if canonical(exception["package"]) == identity[0]
                    and exception["version"] == version
                    and exception["vulnerability_id"] in identifiers
                ),
                None,
            )
            finding = {
                "package": identity[0],
                "version": version,
                "vulnerability_id": vulnerability["id"],
            }
            (exemptions if match else unresolved).append(finding)
    if seen != packages:
        raise SecurityFailure("SECURITY_AUDIT_COVERAGE")
    # Exit 1 is acceptable only for fully enumerated, explicitly exempt findings.
    pass_result = not unresolved and (
        (process.returncode == 0 and total_vulns == 0)
        or (process.returncode == 1 and total_vulns > 0)
    )
    row.update(
        status="PASS" if pass_result else "FAIL",
        audited_packages=len(seen),
        vulnerability_count=total_vulns,
        unresolved=unresolved,
        exemptions=exemptions,
        report_sha256=sha(raw_report.read_bytes()),
    )
    return row


def check_security(root: Path, output: Path, executable: Path) -> dict[str, Any]:
    output = prepare_output(root, output)
    summary: dict[str, Any] = {
        "record_type": "local_security_checks",
        "status": "FAIL",
        "revision": git(root, "rev-parse", "HEAD").decode().strip(),
        "checks": {},
        "limitations": ["Pinned local scanner execution; remote trust is not attested"],
    }
    try:
        policy = read_policy(root)
        actions: list[tuple[str, Callable[[], dict[str, Any]]]] = [
            ("secret", lambda: scan_secrets(root, output, executable, policy)),
            ("dependency", lambda: audit_dependencies(root, output, policy)),
        ]
        for name, action in actions:
            try:
                summary["checks"][name] = action()
            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
                PackageNotFoundError,
                subprocess.SubprocessError,
            ) as exc:
                summary["checks"][name] = {
                    "status": "FAIL",
                    "error": str(exc)
                    if isinstance(exc, SecurityFailure)
                    else type(exc).__name__,
                }
        summary["status"] = (
            "PASS"
            if all(check["status"] == "PASS" for check in summary["checks"].values())
            else "FAIL"
        )
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        summary["error"] = (
            str(exc) if isinstance(exc, SecurityFailure) else type(exc).__name__
        )
    (output / "security-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--gitleaks",
        type=Path,
        default=Path(
            os.environ.get(
                "ANOVELOS_GITLEAKS", str(ROOT / "dist/tools/gitleaks-8.21.2/gitleaks")
            )
        ),
    )
    args = parser.parse_args()
    try:
        summary = check_security(ROOT, args.output_dir, args.gitleaks)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": str(exc)
                    if isinstance(exc, SecurityFailure)
                    else type(exc).__name__,
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "checks": {
                    name: row["status"] for name, row in summary["checks"].items()
                },
            }
        )
    )
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
