"""Exact post-scan approval controls; disposable Git fixtures are not authority evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
REPOSITORY = {"project_id": 86656946, "project_path": "ayitnovel/ainovelos"}
LEDGER_REF = "records/dispositions.json"
AUTHORITY_REF = "records/authority.json"


def load_ci_module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/ci" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exceptions = load_ci_module("secret_exceptions")
load_ci_module("bootstrap_scanners")
security = load_ci_module("check_security")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def git(root: Path, *arguments: str) -> bytes:
    # All mutation-capable Git calls in this file target pytest's disposable repo.
    assert root != ROOT and root.is_dir()
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, "Disposable Git fixture setup failed"
    return result.stdout


def fixture_identity(
    root: Path, revision: str, target: str, line: int
) -> dict[str, Any]:
    path = "historical-material.txt"
    source = git(root, "show", f"{revision}:{path}")
    commit = revision if target == "git_history" else ""
    fingerprint = f"{path}:generic-api-key:{line}"
    if commit:
        fingerprint = f"{commit}:{fingerprint}"
    return {
        "rule_id": "generic-api-key",
        "target": target,
        "path": path,
        "line": line,
        "commit": commit,
        "source_revision": revision,
        "source_sha256": sha(source),
        "source_blob_oid": git(root, "rev-parse", f"{revision}:{path}")
        .decode()
        .strip(),
        "source_line_sha256": sha(source.decode().splitlines()[line - 1].encode()),
        "scanner_fingerprint_sha256": sha(fingerprint.encode()),
    }


@dataclass
class ApprovalCase:
    root: Path
    findings: list[dict[str, Any]]
    ledger: dict[str, Any]
    authority: dict[str, Any]
    config: dict[str, Any]

    def write_ledger(self) -> None:
        source = self.root / LEDGER_REF
        source.parent.mkdir(parents=True, exist_ok=True)
        payload = encode(self.ledger)
        source.write_bytes(payload)
        self.config["ledger_sha256"] = sha(payload)

    def pin_authority(
        self,
        payload: bytes | None = None,
        *,
        ref: str = AUTHORITY_REF,
        preserve_binding: bool = False,
    ) -> dict[str, Any]:
        if payload is None and not preserve_binding:
            self.authority["approved_ledger_sha256"] = sha(
                (self.root / LEDGER_REF).read_bytes()
            )
            dispositions = {
                row["disposition"]
                for row in self.ledger["findings"]
                if row["identity_sha256"] in self.authority["finding_identity_sha256"]
            }
            assert len(dispositions) == 1, "Fixture approval needs one explicit kind"
            self.authority["approval_kind"] = dispositions.pop()
        source = self.root / ref
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(encode(self.authority) if payload is None else payload)
        git(self.root, "add", "--", ref)
        git(
            self.root,
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "pin disposable authority",
        )
        revision = git(self.root, "rev-parse", "HEAD").decode().strip()
        anchor = {
            "ref": ref,
            "revision": revision,
            "blob_oid": git(self.root, "rev-parse", f"{revision}:{ref}")
            .decode()
            .strip(),
            "sha256": sha(source.read_bytes()),
        }
        self.config["trusted_authorities"] = [anchor]
        return anchor

    def consume(
        self, findings: list[dict[str, Any]] | None = None, *, now: datetime = NOW
    ) -> dict[str, Any]:
        return exceptions.consume(
            self.root,
            self.findings if findings is None else findings,
            self.config,
            now=now,
        )


@pytest.fixture
def approved_case(tmp_path: Path) -> ApprovalCase:
    root = tmp_path / "disposable-repository"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "config", "user.name", "Disposable Approval Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "remote", "add", "origin", "https://gitlab.com/ayitnovel/ainovelos.git")
    (root / "historical-material.txt").write_text(
        "".join(f"public historical reference {number}\n" for number in range(1, 9))
    )
    git(root, "add", "historical-material.txt")
    git(root, "commit", "--quiet", "-m", "safe historical fixture")
    baseline = git(root, "rev-parse", "HEAD").decode().strip()
    findings = [
        fixture_identity(root, baseline, "tracked_worktree", 1),
        fixture_identity(root, baseline, "git_history", 2),
    ]
    hashes = [exceptions.identity_digest(item) for item in findings]
    ledger = {
        "schema_version": 1,
        "record_type": "secret_finding_dispositions",
        "repository": copy.deepcopy(REPOSITORY),
        "baseline_revision": baseline,
        "findings": [
            {
                "finding_id": f"V2-004-SF-{number:03}",
                "identity": identity,
                "identity_sha256": fingerprint,
                "classification": "PUBLIC_IDENTIFIER",
                "disposition": "PRECISE_EXCEPTION",
                "authority_id": "FIXTURE-AUTHORITY",
            }
            for number, (identity, fingerprint) in enumerate(zip(findings, hashes), 1)
        ],
    }
    authority = {
        "schema_version": 1,
        "record_type": "secret_exception_authority",
        "authority_id": "FIXTURE-AUTHORITY",
        "actor": "Disposable Project Owner",
        "role": "PROJECT_OWNER",
        "repository": copy.deepcopy(REPOSITORY),
        "decision": "APPROVED",
        "approved_at": "2026-10-07T00:00:00Z",
        "expires_at": "2026-11-06T00:00:00Z",
        "reason": "Disposable exact approval fixture; no actual risk accepted.",
        "finding_identity_sha256": hashes,
    }
    config = {
        "repository": copy.deepcopy(REPOSITORY),
        "ledger_ref": LEDGER_REF,
        "ledger_sha256": "0" * 64,
        "trusted_authorities": [],
    }
    case = ApprovalCase(root, copy.deepcopy(findings), ledger, authority, config)
    case.write_ledger()
    case.pin_authority()
    return case


def rejected(
    case: ApprovalCase, findings: list[dict[str, Any]] | None = None
) -> dict[str, Any] | None:
    try:
        result = case.consume(findings)
    except exceptions.ExceptionFailure as error:
        assert re.fullmatch(r"[A-Z0-9_]+", str(error)), (
            "Errors must be fixed safe codes"
        )
        return None
    assert result["status"] == "FAIL"
    return result


@pytest.mark.parametrize("role", ["PROJECT_OWNER", "SECURITY_APPROVER"])
def test_exact_approved_worktree_and_history_findings_are_consumed(
    approved_case: ApprovalCase, role: str
) -> None:
    case = approved_case
    case.authority["role"] = role
    case.pin_authority()
    assert case.authority["approved_ledger_sha256"] == sha(
        (case.root / LEDGER_REF).read_bytes()
    )
    assert case.authority["approval_kind"] == "PRECISE_EXCEPTION"
    result = case.consume()
    assert result["status"] == "PASS"
    assert result["detected"] == result["known"] == 2
    assert result["approved_and_consumed"] == ["V2-004-SF-001", "V2-004-SF-002"]
    assert not any(
        result[key]
        for key in ("unapproved", "expired", "unmatched_findings", "unused_approvals")
    )


def test_one_owner_acceptance_binds_seven_history_identities_without_credentials(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    baseline = case.ledger["baseline_revision"]
    case.findings = [
        fixture_identity(case.root, baseline, "git_history", line)
        for line in range(1, 8)
    ]
    case.ledger["findings"] = [
        {
            "finding_id": f"V2-004-SF-{number:03}",
            "identity": identity,
            "identity_sha256": exceptions.identity_digest(identity),
            "classification": "POSSIBLE_EXPOSURE",
            "disposition": "OWNER_RISK_ACCEPTANCE",
            "authority_id": "FIXTURE-AUTHORITY",
        }
        for number, identity in enumerate(case.findings, 1)
    ]
    case.authority["finding_identity_sha256"] = [
        row["identity_sha256"] for row in case.ledger["findings"]
    ]
    case.write_ledger()
    case.pin_authority()
    assert case.authority["approved_ledger_sha256"] == case.config["ledger_sha256"]
    assert case.authority["approval_kind"] == "OWNER_RISK_ACCEPTANCE"
    result = case.consume()
    assert result["status"] == "PASS"
    assert len(result["approved_and_consumed"]) == result["known"] == 7
    extra = fixture_identity(case.root, baseline, "git_history", 8)
    assert rejected(case, [*case.findings, extra])["unmatched_findings"] == [
        exceptions.identity_digest(extra)
    ]


def test_stale_owner_precise_approval_cannot_authorize_new_risk_disposition(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.authority["reason"] = "Approve only the exact public identifier exceptions."
    case.pin_authority()
    assert case.consume()["status"] == "PASS"
    original_anchor = copy.deepcopy(case.config["trusted_authorities"][0])
    original_authority = copy.deepcopy(case.authority)
    original_payload = git(
        case.root, "show", f"{original_anchor['revision']}:{AUTHORITY_REF}"
    )
    original_identity = case.ledger["findings"][1]["identity_sha256"]
    case.ledger["findings"][1]["classification"] = "POSSIBLE_EXPOSURE"
    case.ledger["findings"][1]["disposition"] = "OWNER_RISK_ACCEPTANCE"
    case.write_ledger()
    assert case.ledger["findings"][1]["identity_sha256"] == original_identity
    assert case.config["trusted_authorities"] == [original_anchor]
    assert case.authority == original_authority
    assert case.config["ledger_sha256"] != original_authority["approved_ledger_sha256"]
    assert (
        git(case.root, "show", f"{original_anchor['revision']}:{AUTHORITY_REF}")
        == original_payload
    )
    with pytest.raises(
        exceptions.ExceptionFailure, match="^SECRET_EXCEPTION_APPROVED_LEDGER_HASH$"
    ):
        case.consume()


def test_classification_only_change_requires_new_exact_ledger_approval(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    original_authority = copy.deepcopy(case.authority)
    original_anchor = copy.deepcopy(case.config["trusted_authorities"][0])
    row = case.ledger["findings"][1]
    original_identity = copy.deepcopy(row["identity"])
    row["classification"] = "TEST_FIXTURE"
    case.write_ledger()
    assert row["identity"] == original_identity
    assert row["disposition"] == original_authority["approval_kind"]
    assert case.authority == original_authority
    assert case.config["trusted_authorities"] == [original_anchor]
    with pytest.raises(
        exceptions.ExceptionFailure, match="^SECRET_EXCEPTION_APPROVED_LEDGER_HASH$"
    ):
        case.consume()


def test_new_approval_for_unchanged_semantics_binds_current_ledger_bytes(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    original_authority = copy.deepcopy(case.authority)
    original_anchor = copy.deepcopy(case.config["trusted_authorities"][0])
    case.ledger["findings"].reverse()
    case.write_ledger()
    assert case.authority == original_authority
    assert case.config["ledger_sha256"] != original_authority["approved_ledger_sha256"]
    new_anchor = case.pin_authority()
    assert new_anchor != original_anchor
    assert case.authority["approved_ledger_sha256"] == case.config["ledger_sha256"]
    assert case.authority["approval_kind"] == original_authority["approval_kind"]
    result = case.consume()
    assert result["status"] == "PASS"
    assert result["approved_and_consumed"] == ["V2-004-SF-001", "V2-004-SF-002"]


@pytest.mark.parametrize(
    "mutation,value,code",
    [
        ("wrong", "f" * 64, "SECRET_EXCEPTION_APPROVED_LEDGER_HASH"),
        ("missing", None, "SECRET_EXCEPTION_SCHEMA"),
        ("malformed", "not-a-sha256", "SECRET_EXCEPTION_SCHEMA"),
        ("short", "f" * 63, "SECRET_EXCEPTION_SCHEMA"),
        ("uppercase", "F" * 64, "SECRET_EXCEPTION_SCHEMA"),
        ("null", None, "SECRET_EXCEPTION_SCHEMA"),
        ("boolean", True, "SECRET_EXCEPTION_SCHEMA"),
    ],
)
def test_approval_ledger_digest_is_mandatory_exact_and_well_formed(
    approved_case: ApprovalCase, mutation: str, value: Any, code: str
) -> None:
    case = approved_case
    if mutation == "missing":
        del case.authority["approved_ledger_sha256"]
    else:
        case.authority["approved_ledger_sha256"] = value
    case.pin_authority(preserve_binding=True)
    with pytest.raises(exceptions.ExceptionFailure, match=f"^{code}$"):
        case.consume()


@pytest.mark.parametrize(
    "mutation,value",
    [
        ("missing", None),
        ("invalid", "GLOBAL_EXCEPTION"),
        ("wrong-case", "precise_exception"),
        ("null", None),
        ("boolean", True),
    ],
)
def test_approval_kind_is_mandatory_and_limited_to_exact_dispositions(
    approved_case: ApprovalCase, mutation: str, value: Any
) -> None:
    case = approved_case
    if mutation == "missing":
        del case.authority["approval_kind"]
    else:
        case.authority["approval_kind"] = value
    case.pin_authority(preserve_binding=True)
    with pytest.raises(exceptions.ExceptionFailure, match="^SECRET_EXCEPTION_SCHEMA$"):
        case.consume()


@pytest.mark.parametrize(
    "disposition,wrong_kind",
    [
        ("PRECISE_EXCEPTION", "OWNER_RISK_ACCEPTANCE"),
        ("OWNER_RISK_ACCEPTANCE", "PRECISE_EXCEPTION"),
    ],
)
def test_correct_ledger_digest_cannot_compensate_for_wrong_approval_kind(
    approved_case: ApprovalCase, disposition: str, wrong_kind: str
) -> None:
    case = approved_case
    case.findings = case.findings[1:]
    row = case.ledger["findings"][1]
    row["disposition"] = disposition
    if disposition == "OWNER_RISK_ACCEPTANCE":
        row["classification"] = "POSSIBLE_EXPOSURE"
    case.ledger["findings"] = [row]
    case.authority["finding_identity_sha256"] = [row["identity_sha256"]]
    case.write_ledger()
    case.pin_authority()
    assert case.consume()["status"] == "PASS"
    case.authority["approval_kind"] = wrong_kind
    case.pin_authority(preserve_binding=True)
    assert case.authority["approved_ledger_sha256"] == case.config["ledger_sha256"]
    result = rejected(case)
    assert result is not None and result["known"] == 1
    assert result["unapproved"] == [row["finding_id"]]
    assert result["approved_and_consumed"] == []
    assert result["unused_approvals"] == [row["identity_sha256"]]
    assert result["expired"] == result["unmatched_findings"] == []


def test_new_explicit_owner_risk_record_authorizes_refreshed_ledger(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.findings = case.findings[1:]
    row = case.ledger["findings"][1]
    case.ledger["findings"] = [row]
    case.authority["finding_identity_sha256"] = [row["identity_sha256"]]
    case.write_ledger()
    original_anchor = case.pin_authority()
    original_authority = copy.deepcopy(case.authority)
    assert case.consume()["status"] == "PASS"
    row["classification"] = "POSSIBLE_EXPOSURE"
    row["disposition"] = "OWNER_RISK_ACCEPTANCE"
    row["authority_id"] = "NEW-EXPLICIT-RISK-AUTHORITY"
    case.write_ledger()
    case.authority["authority_id"] = row["authority_id"]
    case.authority["reason"] = "Explicit disposable historical risk acceptance."
    new_anchor = case.pin_authority(ref="records/new-risk-authority.json")
    assert new_anchor != original_anchor
    assert case.authority["authority_id"] != original_authority["authority_id"]
    assert case.authority["approved_ledger_sha256"] == case.config["ledger_sha256"]
    assert (
        case.authority["approved_ledger_sha256"]
        != original_authority["approved_ledger_sha256"]
    )
    assert case.authority["approval_kind"] == "OWNER_RISK_ACCEPTANCE"
    assert case.authority["role"] == "PROJECT_OWNER"
    result = case.consume()
    assert result["status"] == "PASS"
    assert result["approved_and_consumed"] == [row["finding_id"]]
    assert result["unapproved"] == result["expired"] == result["unused_approvals"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("rule_id", "another-scanner-rule"),
        ("path", "moved-material.txt"),
        ("line", 8),
        ("scanner_fingerprint_sha256", "f" * 64),
        ("source_sha256", "f" * 64),
        ("source_blob_oid", "f" * 40),
        ("source_line_sha256", "f" * 64),
        ("source_revision", "f" * 40),
        ("target", "git_history"),
        ("commit", "f" * 40),
    ],
)
def test_identity_change_is_unmatched_and_cannot_consume_approval(
    approved_case: ApprovalCase, field: str, value: Any
) -> None:
    case = approved_case
    changed = copy.deepcopy(case.findings)
    changed[0][field] = value
    result = rejected(case, changed)
    assert result is not None
    assert result["known"] == 1
    assert result["approved_and_consumed"] == ["V2-004-SF-002"]
    assert result["unmatched_findings"] == [exceptions.identity_digest(changed[0])]
    assert result["unused_approvals"] == [case.ledger["findings"][0]["identity_sha256"]]


def test_additional_finding_fails_even_when_all_known_findings_are_approved(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    extra = fixture_identity(
        case.root, case.ledger["baseline_revision"], "tracked_worktree", 3
    )
    result = rejected(case, [*case.findings, extra])
    assert result is not None and result["detected"] == 3
    assert len(result["approved_and_consumed"]) == 2
    assert result["unmatched_findings"] == [exceptions.identity_digest(extra)]


def test_missing_authority_is_not_inferred_from_owner_or_disposition(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.config["trusted_authorities"] = []
    result = rejected(case)
    assert result is not None
    assert result["unapproved"] == ["V2-004-SF-001", "V2-004-SF-002"]
    assert result["approved_and_consumed"] == []


def test_unused_approval_is_reported_and_fails_closed(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    result = rejected(case, case.findings[:1])
    assert result is not None
    assert result["unused_approvals"] == [case.ledger["findings"][1]["identity_sha256"]]
    assert result["approved_and_consumed"] == ["V2-004-SF-001"]


def test_authorized_identity_absent_from_ledger_is_unmatched_not_global_permission(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.authority["finding_identity_sha256"].append("f" * 64)
    case.pin_authority()
    result = rejected(case)
    assert result is not None
    assert result["unmatched_approvals"] == ["f" * 64]
    assert "f" * 64 in result["unused_approvals"]


@pytest.mark.parametrize("expiry", ["2026-10-07T12:00:00Z", "2026-10-06T00:00:00Z"])
def test_expired_approval_cannot_be_consumed(
    approved_case: ApprovalCase, expiry: str
) -> None:
    case = approved_case
    case.authority["expires_at"] = expiry
    case.authority["approved_at"] = "2026-10-05T00:00:00Z"
    case.pin_authority()
    result = rejected(case)
    assert result is not None
    assert result["expired"] == ["V2-004-SF-001", "V2-004-SF-002"]
    assert result["approved_and_consumed"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("approved_at", "2026-10-08T00:00:00Z"),
        ("approved_at", "2026-10-07T00:00:00"),
        ("expires_at", "not-a-time"),
        ("expires_at", "2026-10-06T00:00:00Z"),
    ],
)
def test_invalid_or_future_approval_time_is_rejected(
    approved_case: ApprovalCase, field: str, value: str
) -> None:
    case = approved_case
    case.authority[field] = value
    case.pin_authority()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize(
    "mutation",
    [
        "extra-field",
        "missing-role",
        "developer-role",
        "not-approved",
        "broad-path",
        "wrong-project",
        "wrong-project-id",
    ],
)
def test_malformed_or_unauthorized_approval_is_rejected(
    approved_case: ApprovalCase, mutation: str
) -> None:
    case = approved_case
    if mutation == "extra-field":
        case.authority["allow_all_history"] = True
    elif mutation == "missing-role":
        del case.authority["role"]
    elif mutation == "developer-role":
        case.authority["role"] = "DEVELOPER"
    elif mutation == "not-approved":
        case.authority["decision"] = "PENDING"
    elif mutation == "broad-path":
        case.authority["paths"] = ["*.md"]
    elif mutation == "wrong-project":
        case.authority["repository"]["project_path"] = "other/project"
    else:
        case.authority["repository"]["project_id"] += 1
    case.pin_authority()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_security_approver_cannot_consume_owner_risk_acceptance(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.ledger["findings"][1]["disposition"] = "OWNER_RISK_ACCEPTANCE"
    case.ledger["findings"][1]["classification"] = "POSSIBLE_EXPOSURE"
    case.ledger["findings"][1]["authority_id"] = "FIXTURE-RISK-AUTHORITY"
    case.authority["role"] = "SECURITY_APPROVER"
    case.write_ledger()
    case.authority["finding_identity_sha256"] = [
        case.ledger["findings"][0]["identity_sha256"]
    ]
    ordinary_anchor = case.pin_authority()
    case.authority["authority_id"] = "FIXTURE-RISK-AUTHORITY"
    case.authority["finding_identity_sha256"] = [
        case.ledger["findings"][1]["identity_sha256"]
    ]
    risk_anchor = case.pin_authority(ref="records/risk-authority.json")
    assert case.authority["approval_kind"] == "OWNER_RISK_ACCEPTANCE"
    case.config["trusted_authorities"] = [ordinary_anchor, risk_anchor]
    result = rejected(case)
    assert result is not None and result["unapproved"] == ["V2-004-SF-002"]
    assert result["approved_and_consumed"] == ["V2-004-SF-001"]
    assert result["unused_approvals"] == [case.ledger["findings"][1]["identity_sha256"]]


def test_owner_risk_acceptance_cannot_cover_current_worktree(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    case.ledger["findings"][0]["disposition"] = "OWNER_RISK_ACCEPTANCE"
    case.ledger["findings"][0]["classification"] = "POSSIBLE_EXPOSURE"
    case.write_ledger()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-id",
        "duplicate-identity",
        "identity-hash",
        "line-hash",
        "blob-oid",
        "source-sha",
        "fingerprint",
        "history-commit",
        "worktree-revision",
        "broad-path",
        "unknown-scope",
        "boolean-line",
        "extra-field",
    ],
)
def test_malformed_or_inconsistent_ledger_is_rejected(
    approved_case: ApprovalCase, mutation: str
) -> None:
    case = approved_case
    row = case.ledger["findings"][0]
    if mutation == "duplicate-id":
        case.ledger["findings"][1]["finding_id"] = row["finding_id"]
    elif mutation == "duplicate-identity":
        case.ledger["findings"].append(copy.deepcopy(row))
        case.ledger["findings"][-1]["finding_id"] = "V2-004-SF-003"
    elif mutation == "identity-hash":
        row["identity_sha256"] = "f" * 64
    elif mutation == "extra-field":
        row["allow_rule"] = True
    else:
        field, value = {
            "line-hash": ("source_line_sha256", "f" * 64),
            "blob-oid": ("source_blob_oid", "f" * 40),
            "source-sha": ("source_sha256", "f" * 64),
            "fingerprint": ("scanner_fingerprint_sha256", "f" * 64),
            "history-commit": ("commit", "f" * 40),
            "worktree-revision": ("source_revision", "f" * 40),
            "broad-path": ("path", "plan/**/*.md"),
            "unknown-scope": ("target", "all_history"),
            "boolean-line": ("line", True),
        }[mutation]
        row["identity"][field] = value
        row["identity_sha256"] = exceptions.identity_digest(row["identity"])
    case.write_ledger()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_nonancestor_baseline_is_rejected(approved_case: ApprovalCase) -> None:
    case = approved_case
    tree = git(case.root, "rev-parse", "HEAD^{tree}").decode().strip()
    unrelated = (
        git(case.root, "commit-tree", tree, "-m", "unrelated synthetic baseline")
        .decode()
        .strip()
    )
    case.ledger["baseline_revision"] = unrelated
    case.write_ledger()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize(
    "origin",
    [
        "https://gitlab.com/other/project.git",
        "https://example.invalid/ayitnovel/ainovelos.git",
        "ssh://git@example.invalid/ayitnovel/ainovelos.git",
    ],
)
def test_wrong_repository_origin_is_rejected(
    approved_case: ApprovalCase, origin: str
) -> None:
    git(approved_case.root, "remote", "set-url", "origin", origin)
    with pytest.raises(exceptions.ExceptionFailure):
        approved_case.consume()


def test_wrong_numeric_project_binding_is_rejected(approved_case: ApprovalCase) -> None:
    case = approved_case
    case.config["repository"]["project_id"] += 1
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize("field", ["sha256", "blob_oid", "revision"])
def test_authority_git_pin_tampering_is_rejected(
    approved_case: ApprovalCase, field: str
) -> None:
    case = approved_case
    case.config["trusted_authorities"][0][field] = "f" * (
        64 if field == "sha256" else 40
    )
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_candidate_approval_edit_cannot_replace_immutable_authority(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    pinned_bytes = git(
        case.root,
        "show",
        f"{case.config['trusted_authorities'][0]['revision']}:{AUTHORITY_REF}",
    )
    case.authority["finding_identity_sha256"].append("f" * 64)
    (case.root / AUTHORITY_REF).write_bytes(encode(case.authority))
    assert case.consume()["status"] == "PASS"
    assert (
        git(
            case.root,
            "show",
            f"{case.config['trusted_authorities'][0]['revision']}:{AUTHORITY_REF}",
        )
        == pinned_bytes
    )
    extra = fixture_identity(
        case.root, case.ledger["baseline_revision"], "tracked_worktree", 3
    )
    assert rejected(case, [*case.findings, extra])["unmatched_findings"]


def test_unpinned_candidate_approval_cannot_self_authorize(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    (case.root / "candidate-approval.json").write_bytes(encode(case.authority))
    case.config["trusted_authorities"] = []
    assert rejected(case)["unapproved"] == ["V2-004-SF-001", "V2-004-SF-002"]


def test_duplicate_approval_identity_is_rejected(approved_case: ApprovalCase) -> None:
    case = approved_case
    case.authority["finding_identity_sha256"].append(
        case.authority["finding_identity_sha256"][0]
    )
    case.pin_authority()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_multiple_authorities_cannot_approve_same_identity(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    old_anchor = copy.deepcopy(case.config["trusted_authorities"][0])
    case.authority["authority_id"] = "SECOND-FIXTURE-AUTHORITY"
    new_anchor = case.pin_authority(ref="records/other-authority.json")
    case.config["trusted_authorities"] = [old_anchor, new_anchor]
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_duplicate_actual_finding_is_rejected(approved_case: ApprovalCase) -> None:
    with pytest.raises(exceptions.ExceptionFailure):
        approved_case.consume([*approved_case.findings, approved_case.findings[0]])


@pytest.mark.parametrize(
    "payload",
    [b'{"schema_version":1,"schema_version":1}', b"not json", b"[]", b"null", b"\xff"],
)
def test_malformed_authority_bytes_fail_with_safe_code(
    approved_case: ApprovalCase, payload: bytes
) -> None:
    case = approved_case
    case.pin_authority(payload)
    with pytest.raises(exceptions.ExceptionFailure) as error:
        case.consume()
    assert re.fullmatch(r"[A-Z0-9_]+", str(error.value))


@pytest.mark.parametrize("mutation", ["hash", "path-escape", "broad-path", "symlink"])
def test_ledger_configuration_cannot_redirect_or_modify_scope(
    approved_case: ApprovalCase, mutation: str, tmp_path: Path
) -> None:
    case = approved_case
    if mutation == "hash":
        case.config["ledger_sha256"] = "f" * 64
    elif mutation == "path-escape":
        case.config["ledger_ref"] = "../dispositions.json"
    elif mutation == "broad-path":
        case.config["ledger_ref"] = "records/*.json"
    else:
        source = case.root / LEDGER_REF
        outside = tmp_path / "outside-ledger.json"
        outside.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(outside)
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


def test_unconfigured_consumer_accepts_no_findings_but_rejects_any_new_finding(
    approved_case: ApprovalCase,
) -> None:
    case = approved_case
    assert exceptions.consume(case.root, [], None, now=NOW)["status"] == "PASS"
    result = exceptions.consume(case.root, case.findings[:1], None, now=NOW)
    assert result["status"] == "FAIL"
    assert result["approved_and_consumed"] == []
    assert result["unmatched_findings"] == [
        exceptions.identity_digest(case.findings[0])
    ]


def test_naive_verification_clock_is_rejected(approved_case: ApprovalCase) -> None:
    with pytest.raises(exceptions.ExceptionFailure):
        approved_case.consume(now=NOW.replace(tzinfo=None))


def test_identity_digest_is_order_independent_and_sensitive_to_every_field(
    approved_case: ApprovalCase,
) -> None:
    identity = approved_case.findings[0]
    expected = sha(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    assert (
        exceptions.identity_digest(dict(reversed(list(identity.items())))) == expected
    )
    for field in identity:
        changed = dict(identity)
        changed[field] = "different"
        assert exceptions.identity_digest(changed) != expected


def prepare_real_scanner_approval(
    case: ApprovalCase, tmp_path: Path
) -> tuple[Path, str]:
    binary = Path(
        os.environ.get(
            "ANOVELOS_GITLEAKS", str(ROOT / "dist/tools/gitleaks-8.21.2/gitleaks")
        )
    )
    assert binary.is_file(), "Missing pinned scanner is a failure, never a skip"
    # Generated shape-only values have never been issued by any service.
    token = "ghp_" + secrets.token_hex(18)
    source = case.root / "historical-material.txt"
    source.write_text(f"github_token = '{token}'\n")
    git(case.root, "add", source.name)
    git(case.root, "commit", "--quiet", "-m", "shape-only scanner fixture")
    baseline = git(case.root, "rev-parse", "HEAD").decode().strip()
    initial_output = tmp_path / "initial-scan"
    initial_output.mkdir()
    initial = security.scan_secrets(case.root, initial_output, binary)
    assert initial["status"] == initial["raw_status"] == "FAIL"
    case.findings = initial["finding_identities"]
    assert {item["target"] for item in case.findings} == {
        "tracked_worktree",
        "git_history",
    }
    case.ledger["baseline_revision"] = baseline
    case.ledger["findings"] = [
        {
            "finding_id": f"V2-004-SF-{number:03}",
            "identity": identity,
            "identity_sha256": exceptions.identity_digest(identity),
            "classification": "TEST_FIXTURE",
            "disposition": "PRECISE_EXCEPTION",
            "authority_id": "FIXTURE-AUTHORITY",
        }
        for number, identity in enumerate(case.findings, 1)
    ]
    now = datetime.now(UTC)
    case.authority["approved_at"] = (now - timedelta(minutes=1)).isoformat()
    case.authority["expires_at"] = (now + timedelta(days=1)).isoformat()
    case.authority["finding_identity_sha256"] = [
        row["identity_sha256"] for row in case.ledger["findings"]
    ]
    case.write_ledger()
    case.pin_authority()
    return binary, token


def test_real_scanner_exact_approval_preserves_raw_findings_and_rejects_new_secret(
    approved_case: ApprovalCase, tmp_path: Path
) -> None:
    case = approved_case
    binary, token = prepare_real_scanner_approval(case, tmp_path)
    approved_output = tmp_path / "approved-scan"
    approved_output.mkdir()
    approved = security.scan_secrets(
        case.root, approved_output, binary, policy={"secret_exceptions": case.config}
    )
    assert approved["status"] == "PASS"
    assert approved["raw_status"] == "FAIL"
    assert approved["finding_identities"] == case.findings
    assert len(approved["exception_consumption"]["approved_and_consumed"]) == len(
        case.findings
    )
    assert all(row["exit_code"] == 1 for row in approved["scans"])

    new_token = "ghp_" + secrets.token_hex(18)
    (case.root / "additional-material.txt").write_text(
        f"github_token = '{new_token}'\n"
    )
    git(case.root, "add", "additional-material.txt")
    git(case.root, "commit", "--quiet", "-m", "additional shape-only fixture")
    rejected_output = tmp_path / "new-secret-scan"
    rejected_output.mkdir()
    report = security.scan_secrets(
        case.root, rejected_output, binary, policy={"secret_exceptions": case.config}
    )
    assert report["status"] == report["raw_status"] == "FAIL"
    assert report["exception_consumption"]["unmatched_findings"]
    assert any(
        item["path"] == "additional-material.txt"
        for item in report["finding_identities"]
    )
    for output in (tmp_path / "initial-scan", approved_output, rejected_output):
        payload = (output / "secret-scan.json").read_text()
        assert token not in payload and new_token not in payload


@pytest.mark.parametrize("exit_code", [0, 2, 127])
def test_scanner_exit_report_mismatch_cannot_pass_with_exact_approvals(
    approved_case: ApprovalCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
) -> None:
    case = approved_case
    binary, _ = prepare_real_scanner_approval(case, tmp_path)
    original_run = subprocess.run

    def alter_scanner_exit(*arguments: Any, **kwargs: Any) -> Any:
        result = original_run(*arguments, **kwargs)
        argv = arguments[0]
        if argv[0] == str(binary) and argv[1] in {"dir", "git"}:
            return subprocess.CompletedProcess(
                result.args, exit_code, result.stdout, result.stderr
            )
        return result

    monkeypatch.setattr(security.subprocess, "run", alter_scanner_exit)
    output = tmp_path / "scanner-mismatch"
    output.mkdir()
    result = security.scan_secrets(
        case.root, output, binary, policy={"secret_exceptions": case.config}
    )
    assert result["status"] == "FAIL"
    assert result["exception_consumption"]["status"] == "PASS"
    assert all(
        row["error"] == "SECURITY_SECRET_EXIT_REPORT_MISMATCH"
        for row in result["scans"]
    )


@pytest.mark.parametrize("absolute_name", [False, True])
def test_worktree_identity_normalizes_scanner_path_to_copied_bytes(
    approved_case: ApprovalCase, tmp_path: Path, absolute_name: bool
) -> None:
    case = approved_case
    copied = tmp_path / "copied"
    copied.mkdir()
    name = "historical-material.txt"
    (copied / name).write_bytes((case.root / name).read_bytes())
    scanner_name = str(copied / name) if absolute_name else name
    item = {
        "RuleID": "generic-api-key",
        "File": scanner_name,
        "StartLine": 1,
        "Commit": "",
        "Fingerprint": f"{scanner_name}:generic-api-key:1",
    }
    identity = exceptions.finding_identity(
        case.root, item, "tracked_worktree", copied, case.ledger["baseline_revision"]
    )
    assert identity == case.findings[0]
    changed = b"different copied bytes\n"
    (copied / name).write_bytes(changed)
    identity = exceptions.finding_identity(
        case.root, item, "tracked_worktree", copied, case.ledger["baseline_revision"]
    )
    assert identity["source_sha256"] == sha(changed)
    assert (
        identity["source_blob_oid"]
        == hashlib.sha1(f"blob {len(changed)}\0".encode() + changed).hexdigest()
    )
    assert identity["source_sha256"] != case.findings[0]["source_sha256"]
    assert rejected(case, [identity, case.findings[1]])["unmatched_findings"]


@pytest.mark.parametrize(
    "mutation",
    ["bool-line", "wrong-fingerprint", "history-commit", "missing-fingerprint"],
)
def test_scanner_metadata_cannot_forge_finding_identity(
    approved_case: ApprovalCase, tmp_path: Path, mutation: str
) -> None:
    case = approved_case
    copied = tmp_path / "copied"
    copied.mkdir()
    name = "historical-material.txt"
    (copied / name).write_bytes((case.root / name).read_bytes())
    item = {
        "RuleID": "generic-api-key",
        "File": name,
        "StartLine": 1,
        "Commit": "",
        "Fingerprint": f"{name}:generic-api-key:1",
    }
    if mutation == "bool-line":
        item["StartLine"] = True
    elif mutation == "wrong-fingerprint":
        item["Fingerprint"] = "unrelated-fingerprint"
    elif mutation == "history-commit":
        item["Commit"] = case.ledger["baseline_revision"]
    else:
        del item["Fingerprint"]
    with pytest.raises(exceptions.ExceptionFailure):
        exceptions.finding_identity(
            case.root,
            item,
            "tracked_worktree",
            copied,
            case.ledger["baseline_revision"],
        )


@pytest.mark.parametrize(
    "policy", [{}, {"secret_exceptions": None}, {"secret_exceptions": []}]
)
def test_explicit_policy_with_missing_or_malformed_consumer_fails_even_when_scan_is_safe(
    approved_case: ApprovalCase, tmp_path: Path, policy: dict[str, Any]
) -> None:
    binary = Path(
        os.environ.get(
            "ANOVELOS_GITLEAKS", str(ROOT / "dist/tools/gitleaks-8.21.2/gitleaks")
        )
    )
    assert binary.is_file(), "Missing pinned scanner is a failure, never a skip"
    output = tmp_path / "invalid-policy-safe-scan"
    output.mkdir()
    result = security.scan_secrets(approved_case.root, output, binary, policy=policy)
    assert result["status"] == "FAIL"
    assert result["raw_status"] == "PASS"
    assert result["finding_identities"] == []
    assert result["exception_consumption"]["status"] == "FAIL"
    assert result["exception_consumption"]["error"]
    assert {row["target"] for row in result["scans"]} == {
        "tracked_worktree",
        "git_history",
    }
    assert (output / "secret-scan.json").is_file()


@pytest.mark.parametrize(
    "mutation", ["invalid-json", "duplicate-json-key", "wrong-fingerprint"]
)
def test_malformed_first_scan_preserves_failure_and_still_scans_second_target(
    approved_case: ApprovalCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    case = approved_case
    binary, token = prepare_real_scanner_approval(case, tmp_path)
    original_run = subprocess.run
    scanner_targets: list[str] = []

    def corrupt_first_report(*arguments: Any, **kwargs: Any) -> Any:
        result = original_run(*arguments, **kwargs)
        argv = arguments[0]
        if argv[0] == str(binary) and argv[1] in {"dir", "git"}:
            scanner_targets.append(argv[1])
            if argv[1] == "dir":
                report = Path(argv[argv.index("--report-path") + 1])
                if mutation == "invalid-json":
                    report.write_bytes(b"malformed scanner JSON")
                elif mutation == "duplicate-json-key":
                    report.write_bytes(b'[{"RuleID":"one","RuleID":"two"}]')
                else:
                    payload = json.loads(report.read_bytes())
                    assert payload, "Real scanner must detect the shape-only fixture"
                    payload[0]["Fingerprint"] = "invalid scanner fingerprint"
                    report.write_bytes(encode(payload))
        return result

    monkeypatch.setattr(security.subprocess, "run", corrupt_first_report)
    output = tmp_path / "malformed-first-scan"
    output.mkdir()
    result = security.scan_secrets(
        case.root, output, binary, policy={"secret_exceptions": case.config}
    )
    assert scanner_targets == ["dir", "git"]
    assert result["status"] == result["raw_status"] == "FAIL"
    assert len(result["scans"]) == 2
    first, second = result["scans"]
    assert first["target"] == "tracked_worktree" and first["error"]
    assert second["target"] == "git_history" and second["finding_count"] > 0
    assert second["locations"]
    assert result["exception_consumption"]["detected"] > 0
    assert result["exception_consumption"]["identified"] > 0
    if mutation == "wrong-fingerprint":
        assert (
            result["exception_consumption"]["detected"]
            > result["exception_consumption"]["identified"]
        )
    payload = (output / "secret-scan.json").read_text()
    assert token not in payload
    assert json.loads(payload)["status"] == "FAIL"


@pytest.mark.parametrize("field", ["actor", "reason"])
def test_whitespace_only_authority_identity_or_reason_is_rejected(
    approved_case: ApprovalCase, field: str
) -> None:
    case = approved_case
    case.authority[field] = " \t\n"
    case.pin_authority()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize(
    "classification", ["POSSIBLE_EXPOSURE", "TRUNCATED_REFERENCE_UNRESOLVED"]
)
def test_owner_risk_classification_cannot_be_consumed_as_precise_exception(
    approved_case: ApprovalCase, classification: str
) -> None:
    case = approved_case
    case.ledger["findings"][1]["classification"] = classification
    assert case.ledger["findings"][1]["disposition"] == "PRECISE_EXCEPTION"
    case.write_ledger()
    with pytest.raises(exceptions.ExceptionFailure):
        case.consume()


@pytest.mark.parametrize("failure", ["timeout", "missing-report"])
def test_first_scanner_execution_or_report_failure_still_records_history_target(
    approved_case: ApprovalCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    case = approved_case
    binary, token = prepare_real_scanner_approval(case, tmp_path)
    original_run = subprocess.run
    scanner_targets: list[str] = []

    def interrupt_first_scan(*arguments: Any, **kwargs: Any) -> Any:
        argv = arguments[0]
        scanner = argv[0] == str(binary) and argv[1] in {"dir", "git"}
        if scanner:
            scanner_targets.append(argv[1])
            if argv[1] == "dir" and failure == "timeout":
                raise subprocess.TimeoutExpired(argv, timeout=600)
        result = original_run(*arguments, **kwargs)
        if scanner and argv[1] == "dir" and failure == "missing-report":
            Path(argv[argv.index("--report-path") + 1]).unlink()
        return result

    monkeypatch.setattr(security.subprocess, "run", interrupt_first_scan)
    output = tmp_path / "first-scanner-failure"
    output.mkdir()
    result = security.scan_secrets(
        case.root, output, binary, policy={"secret_exceptions": case.config}
    )
    assert scanner_targets == ["dir", "git"]
    assert result["status"] == result["raw_status"] == "FAIL"
    assert len(result["scans"]) == 2
    first, second = result["scans"]
    assert first["target"] == "tracked_worktree" and first["status"] == "FAIL"
    assert first["error"] == (
        "SECURITY_SECRET_EXECUTION"
        if failure == "timeout"
        else "SECURITY_SECRET_REPORT_MISSING"
    )
    assert second["target"] == "git_history" and second["locations"]
    assert result["exception_consumption"]["identified"] > 0
    assert result["exception_consumption"]["detected"] > 0
    payload = (output / "secret-scan.json").read_text()
    assert token not in payload
    assert json.loads(payload)["status"] == "FAIL"


def test_worktree_copy_under_symlink_temp_prefix_has_normalized_identity(
    approved_case: ApprovalCase, tmp_path: Path
) -> None:
    case = approved_case
    real_parent = tmp_path / "real-temporary-root"
    real_parent.mkdir()
    alias = tmp_path / "temporary-root-alias"
    alias.symlink_to(real_parent, target_is_directory=True)
    copied = alias / "tracked"
    copied.mkdir()
    assert copied != copied.resolve()
    name = "historical-material.txt"
    (copied / name).write_bytes((case.root / name).read_bytes())
    scanner_name = str(copied / name)
    item = {
        "RuleID": "generic-api-key",
        "File": scanner_name,
        "StartLine": 1,
        "Commit": "",
        "Fingerprint": f"{scanner_name}:generic-api-key:1",
    }
    identity = exceptions.finding_identity(
        case.root, item, "tracked_worktree", copied, case.ledger["baseline_revision"]
    )
    assert identity == case.findings[0]
    assert identity["path"] == name
    assert case.consume([identity, case.findings[1]])["status"] == "PASS"
