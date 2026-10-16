"""Consume exact secret dispositions from explicitly pinned authority records.

This is a post-scan decision layer, never a scanner ignore list. Its policy and
Git authority anchors must be protected by the trusted CI source boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMAS = (
    Path(__file__).resolve().parents[2]
    / "plan/validation/execution/V2-004/mainline-unblock-20261007"
)
HEX = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


class ExceptionFailure(ValueError):
    """Only fixed safe codes may be emitted; never include scanner contents."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity_digest(identity: dict[str, Any]) -> str:
    return digest(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ExceptionFailure("SECRET_EXCEPTION_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_json(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise ExceptionFailure("SECRET_EXCEPTION_JSON") from None


def _schema(value: Any, name: str) -> None:
    schema = parse_json((SCHEMAS / name).read_bytes())
    # jsonschema is already locked; its runtime validator has no bundled stubs.
    validator = import_module("jsonschema").Draft202012Validator(schema)
    if not validator.is_valid(value):
        raise ExceptionFailure("SECRET_EXCEPTION_SCHEMA")


def _path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(ord(char) < 32 for char in value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(char in value for char in "*?[]")
    ):
        raise ExceptionFailure("SECRET_EXCEPTION_PATH")
    return value


def _git(root: Path, *args: str) -> bytes:
    env = os.environ.copy()
    env["GIT_NO_LAZY_FETCH"] = "1"
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        env=env,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise ExceptionFailure("SECRET_EXCEPTION_GIT")
    return result.stdout


def _ancestor(root: Path, revision: str) -> None:
    if not HEX.fullmatch(revision):
        raise ExceptionFailure("SECRET_EXCEPTION_REVISION")
    _git(root, "merge-base", "--is-ancestor", revision, "HEAD")


def _repository(root: Path, expected: dict[str, Any], config: dict[str, Any]) -> None:
    host = "gitlab.com"
    repository_path = expected["project_path"]
    migration = config.get("repository_migration")
    if migration is not None:
        _ancestor(root, migration["revision"])
        raw, oid = _blob(root, migration["revision"], _path(migration["ref"]))
        if oid != migration["blob_oid"] or digest(raw) != migration["sha256"]:
            raise ExceptionFailure("SECRET_EXCEPTION_MIGRATION_PIN")
        record = parse_json(raw)
        if (
            not isinstance(record, dict)
            or record.get("record_type") != "repository_migration_authority"
            or type(record.get("schema_version")) is not int
            or record.get("schema_version") != 1
            or record.get("decision") != "APPROVED"
            or record.get("role") != "PROJECT_OWNER"
            or not isinstance(record.get("actor"), str)
            or not record["actor"].strip()
            or record.get("source") != {"host": "gitlab.com", **expected}
            or record.get("approved_ledger_sha256") != config["ledger_sha256"]
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_MIGRATION_AUTHORITY")
        target = record.get("target")
        if (
            not isinstance(target, dict)
            or set(target) != {"host", "repository_id", "repository_path"}
            or target["host"] != "github.com"
            or type(target["repository_id"]) is not int
            or target["repository_id"] < 1
            or not isinstance(target["repository_path"], str)
            or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", target["repository_path"]
            )
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_MIGRATION_TARGET")
        statement, _ = _blob(
            root, migration["revision"], _path(record.get("owner_statement_ref"))
        )
        if not statement.strip() or digest(statement) != record.get(
            "owner_statement_sha256"
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_MIGRATION_STATEMENT")
        if os.getenv("GITHUB_ACTIONS") == "true" and (
            os.getenv("GITHUB_REPOSITORY_ID") != str(target["repository_id"])
            or os.getenv("GITHUB_REPOSITORY") != target["repository_path"]
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_MIGRATION_RUNTIME")
        host, repository_path = target["host"], target["repository_path"]
    remote = _git(root, "remote", "get-url", "origin").decode().strip()
    if remote.startswith(f"git@{host}:"):
        path = remote.removeprefix(f"git@{host}:")
    else:
        parsed = urlsplit(remote)
        if (
            parsed.hostname != host
            or parsed.scheme not in {"https", "ssh"}
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or (
                parsed.username is not None
                and not (parsed.scheme == "ssh" and parsed.username == "git")
            )
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_REPOSITORY")
        path = parsed.path.removeprefix("/")
    if path.removesuffix(".git") != repository_path:
        raise ExceptionFailure("SECRET_EXCEPTION_REPOSITORY")


def _blob(root: Path, revision: str, path: str) -> tuple[bytes, str]:
    _path(path)
    if not HEX.fullmatch(revision):
        raise ExceptionFailure("SECRET_EXCEPTION_REVISION")
    tree = _git(root, "ls-tree", "-z", revision, "--", path).split(b"\0")
    if len(tree) != 2 or not tree[0]:
        raise ExceptionFailure("SECRET_EXCEPTION_SOURCE")
    metadata, name = tree[0].split(b"\t", 1)
    mode, kind, oid = metadata.decode().split()
    if mode not in {"100644", "100755"} or kind != "blob" or name.decode() != path:
        raise ExceptionFailure("SECRET_EXCEPTION_SOURCE")
    return _git(root, "cat-file", "blob", oid), oid


def _line_hash(data: bytes, line: int) -> str:
    lines = data.decode("utf-8").splitlines()
    if type(line) is not int or line < 1 or line > len(lines):
        raise ExceptionFailure("SECRET_EXCEPTION_LINE")
    return digest(lines[line - 1].encode())


def _fingerprint(identity: dict[str, Any]) -> str:
    value = f"{identity['path']}:{identity['rule_id']}:{identity['line']}"
    if identity["target"] == "git_history":
        value = f"{identity['commit']}:{value}"
    return digest(value.encode())


def finding_identity(
    root: Path,
    item: dict[str, Any],
    target: str,
    copied: Path,
    baseline_revision: str,
) -> dict[str, Any]:
    """Bind identities to bytes actually scanned, not a later root read."""
    rule, name, line = item.get("RuleID"), item.get("File"), item.get("StartLine")
    commit, fingerprint = item.get("Commit", ""), item.get("Fingerprint")
    if (
        not isinstance(rule, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", rule)
        or not isinstance(name, str)
        or type(line) is not int
        or line < 1
        or not isinstance(commit, str)
        or target not in {"tracked_worktree", "git_history"}
    ):
        raise ExceptionFailure("SECRET_EXCEPTION_FINDING")
    expected_raw = f"{name}:{rule}:{line}"
    if target == "git_history":
        if not HEX.fullmatch(commit):
            raise ExceptionFailure("SECRET_EXCEPTION_HISTORY_COMMIT")
        expected_raw = f"{commit}:{expected_raw}"
    elif commit:
        raise ExceptionFailure("SECRET_EXCEPTION_WORKTREE_COMMIT")
    if fingerprint != expected_raw:
        raise ExceptionFailure("SECRET_EXCEPTION_FINGERPRINT")
    prefix = str(copied) + "/"
    path = _path(name.removeprefix(prefix) if target == "tracked_worktree" else name)
    revision = commit if target == "git_history" else baseline_revision
    if target == "git_history":
        source, oid = _blob(root, revision, path)
    else:
        file = copied / path
        if (
            file.is_symlink()
            or not file.is_file()
            or not file.resolve().is_relative_to(copied.resolve())
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_SOURCE")
        source = file.read_bytes()
        # SHA-1/SHA-256 Git object identity, without ever outputting source bytes.
        algorithm = _git(root, "rev-parse", "--show-object-format").decode().strip()
        if algorithm not in {"sha1", "sha256"}:
            raise ExceptionFailure("SECRET_EXCEPTION_OBJECT_FORMAT")
        oid = hashlib.new(
            algorithm, f"blob {len(source)}\0".encode() + source
        ).hexdigest()
    identity = {
        "rule_id": rule,
        "target": target,
        "path": path,
        "line": line,
        "commit": commit,
        "source_revision": revision,
        "source_sha256": digest(source),
        "source_blob_oid": oid,
        "source_line_sha256": _line_hash(source, line),
    }
    identity["scanner_fingerprint_sha256"] = _fingerprint(identity)
    return identity


def load_ledger(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    _schema(config, "finding-exception-consumer.schema.json")
    ref = _path(config["ledger_ref"])
    source = root / ref
    if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
        raise ExceptionFailure("SECRET_EXCEPTION_LEDGER_PATH")
    payload = source.read_bytes()
    if digest(payload) != config["ledger_sha256"]:
        raise ExceptionFailure("SECRET_EXCEPTION_LEDGER_HASH")
    ledger: dict[str, Any] = parse_json(payload)
    _schema(ledger, "finding-disposition.schema.json")
    if ledger["repository"] != config["repository"]:
        raise ExceptionFailure("SECRET_EXCEPTION_REPOSITORY")
    _repository(root, ledger["repository"], config)
    _ancestor(root, ledger["baseline_revision"])
    ids: set[str] = set()
    hashes: set[str] = set()
    for row in ledger["findings"]:
        identity = row["identity"]
        _path(identity["path"])
        if row["finding_id"] in ids or row["identity_sha256"] in hashes:
            raise ExceptionFailure("SECRET_EXCEPTION_DUPLICATE_IDENTITY")
        ids.add(row["finding_id"])
        hashes.add(row["identity_sha256"])
        if identity_digest(identity) != row["identity_sha256"]:
            raise ExceptionFailure("SECRET_EXCEPTION_IDENTITY_HASH")
        history = identity["target"] == "git_history"
        if (history and identity["commit"] != identity["source_revision"]) or (
            not history
            and (
                identity["commit"]
                or identity["source_revision"] != ledger["baseline_revision"]
            )
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_SCOPE")
        if (
            identity
            and row["classification"]
            in {"POSSIBLE_EXPOSURE", "TRUNCATED_REFERENCE_UNRESOLVED"}
            and row["disposition"] != "OWNER_RISK_ACCEPTANCE"
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_RISK_CLASSIFICATION")
        if row["disposition"] == "OWNER_RISK_ACCEPTANCE" and not history:
            raise ExceptionFailure("SECRET_EXCEPTION_RISK_SCOPE")
        if _fingerprint(identity) != identity["scanner_fingerprint_sha256"]:
            raise ExceptionFailure("SECRET_EXCEPTION_FINGERPRINT")
        source_bytes, oid = _blob(root, identity["source_revision"], identity["path"])
        if (
            digest(source_bytes) != identity["source_sha256"]
            or oid != identity["source_blob_oid"]
            or _line_hash(source_bytes, identity["line"])
            != identity["source_line_sha256"]
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_SOURCE_IDENTITY")
    return ledger


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ExceptionFailure("SECRET_EXCEPTION_TIME") from None
    if result.tzinfo is None:
        raise ExceptionFailure("SECRET_EXCEPTION_TIME")
    return result.astimezone(timezone.utc)


def consume(
    root: Path,
    findings: list[dict[str, Any]],
    config: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "FAIL",
        "detected": len(findings),
        "known": 0,
        "approved_and_consumed": [],
        "unapproved": [],
        "expired": [],
        "unmatched_findings": [],
        "unused_approvals": [],
        "unmatched_approvals": [],
    }
    if config is None:
        result["unmatched_findings"] = [identity_digest(item) for item in findings]
        result["status"] = "FAIL" if findings else "PASS"
        return result
    ledger = load_ledger(root, config)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ExceptionFailure("SECRET_EXCEPTION_TIME")
    authorities: dict[str, dict[str, Any]] = {}
    authorized_hashes: set[str] = set()
    for anchor in config["trusted_authorities"]:
        _ancestor(root, anchor["revision"])
        payload, oid = _blob(root, anchor["revision"], _path(anchor["ref"]))
        if oid != anchor["blob_oid"] or digest(payload) != anchor["sha256"]:
            raise ExceptionFailure("SECRET_EXCEPTION_AUTHORITY_PIN")
        authority: dict[str, Any] = parse_json(payload)
        _schema(authority, "finding-approval.schema.json")
        if (
            authority["decision"] != "APPROVED"
            or authority["repository"] != ledger["repository"]
            or authority["authority_id"] in authorities
        ):
            raise ExceptionFailure("SECRET_EXCEPTION_AUTHORITY")
        if authority["approved_ledger_sha256"] != config["ledger_sha256"]:
            raise ExceptionFailure("SECRET_EXCEPTION_APPROVED_LEDGER_HASH")
        if not authority["actor"].strip() or not authority["reason"].strip():
            raise ExceptionFailure("SECRET_EXCEPTION_AUTHORITY")
        start = _timestamp(authority["approved_at"])
        end = _timestamp(authority["expires_at"])
        if start > now or start >= end:
            raise ExceptionFailure("SECRET_EXCEPTION_TIME")
        hashes = authority["finding_identity_sha256"]
        if len(set(hashes)) != len(hashes) or authorized_hashes.intersection(hashes):
            raise ExceptionFailure("SECRET_EXCEPTION_DUPLICATE_APPROVAL")
        authorized_hashes.update(hashes)
        authorities[authority["authority_id"]] = authority
    rows = {row["identity_sha256"]: row for row in ledger["findings"]}
    result["unmatched_approvals"] = sorted(authorized_hashes - rows.keys())
    seen: set[str] = set()
    consumed: set[str] = set()
    for item in findings:
        key = identity_digest(item)
        if key in seen:
            raise ExceptionFailure("SECRET_EXCEPTION_DUPLICATE_FINDING")
        seen.add(key)
        row = rows.get(key)
        if row is None or row["identity"] != item:
            result["unmatched_findings"].append(key)
            continue
        result["known"] += 1
        matched_authority = authorities.get(row["authority_id"])
        if (
            matched_authority is None
            or key not in matched_authority["finding_identity_sha256"]
            or matched_authority["approval_kind"] != row["disposition"]
        ):
            result["unapproved"].append(row["finding_id"])
            continue
        if (
            row["disposition"] == "OWNER_RISK_ACCEPTANCE"
            and matched_authority["role"] != "PROJECT_OWNER"
        ):
            result["unapproved"].append(row["finding_id"])
            continue
        if now >= _timestamp(matched_authority["expires_at"]):
            result["expired"].append(row["finding_id"])
            continue
        consumed.add(key)
        result["approved_and_consumed"].append(row["finding_id"])
    result["unused_approvals"] = sorted(authorized_hashes - consumed)
    result["status"] = (
        "FAIL"
        if any(
            result[key]
            for key in [
                "unapproved",
                "expired",
                "unmatched_findings",
                "unused_approvals",
            ]
        )
        else "PASS"
    )
    return result
