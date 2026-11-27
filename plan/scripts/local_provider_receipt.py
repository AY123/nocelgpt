"""Read back the one Owner-approved OpenAI receipt for the P5 decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
from contextlib import closing
from inspect import getfile
from pathlib import Path
from typing import Any

RECEIPT_DIRECTORY = Path("validation/execution/V2-019/openai-first-probe-20261125")
GP5_APPROVAL_REF = (RECEIPT_DIRECTORY / "GP5_REUSE_AUTHORIZATION.json").as_posix()
GP5_READBACK_REF = (RECEIPT_DIRECTORY / "GP5_RECEIPT_READBACK.json").as_posix()
OBSERVATION_REF = RECEIPT_DIRECTORY / "LOCAL_OBSERVATION.json"
REGRESSION_REF = RECEIPT_DIRECTORY / "SAME_SOURCE_READBACK.json"
OBSERVATION_SHA256 = "225bd3899ca70e8667834ef29659e2012cdbff29ff20a2ef8d7a1a6460b22493"
REGRESSION_SHA256 = "eca977f526531cba93088fc40c8e1aa0dee2d30cbc66f98faa0ae79165b75623"
OBSERVED_COMPONENT_SHA256 = (
    "10dd38cd85546c71af22cf2ee7a99494a6b93db1fa4bac45725c2bc119f24d78"
)
SOURCE_PATHS = (
    "src/anovel/gateway",
    "src/anovel/context",
    "src/anovel/contracts",
    "src/anovel/domain",
    "src/anovel/canon/identity.py",
    "uv.lock",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: object, code: str) -> None:
    if not condition:
        raise ValueError(code)


def read_record(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        values = dict(pairs)
        require(len(values) == len(pairs), "GP5_DUPLICATE_JSON_KEY")
        return values

    data = json.loads(path.read_bytes(), object_pairs_hook=unique)
    require(type(data) is dict, "GP5_RECORD")
    return data


def git(root: Path, *args: str) -> bytes:
    run = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    require(run.returncode == 0, "GP5_CANDIDATE_GIT")
    return run.stdout


def component_sha256(root: Path, revision: str) -> str:
    """Identify the Gateway and its request types and locked runtime at a commit."""
    require(
        type(revision) is str
        and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", revision),
        "GP5_CANDIDATE_REVISION",
    )
    require(
        git(root, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
        == revision,
        "GP5_CANDIDATE_REVISION",
    )
    inventory = []
    for entry in git(root, "ls-tree", "-rz", revision, "--", *SOURCE_PATHS).split(
        b"\0"
    ):
        if not entry:
            continue
        header, name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        require(kind == "blob" and mode in {"100644", "100755"}, "GP5_CANDIDATE_SOURCE")
        inventory.append(
            (name.decode(), mode, digest(git(root, "cat-file", "blob", blob)))
        )
    require(
        all(
            any(p == prefix or p.startswith(prefix + "/") for p, _, _ in inventory)
            for prefix in SOURCE_PATHS
        ),
        "GP5_CANDIDATE_SOURCE",
    )
    return digest(json.dumps(sorted(inventory), separators=(",", ":")).encode())


def approval_record() -> dict[str, object]:
    return {
        "record_type": "gp5_openai_receipt_reuse_authorization",
        "schema_version": "1.0",
        "date": "2026-11-27",
        "phase": "P5",
        "task_id": "V2-019",
        "owner_response": "批准复用回执和一次常规 CI",
        "maximum_routine_ci_runs": 1,
        "provider_requests_allowed": False,
        "observation_sha256": OBSERVATION_SHA256,
        "regression_sha256": REGRESSION_SHA256,
        "observed_component_sha256": OBSERVED_COMPONENT_SHA256,
    }


def approved_input(plan: Path) -> tuple[str, dict[str, Any]]:
    for ref, expected in (
        (OBSERVATION_REF, OBSERVATION_SHA256),
        (REGRESSION_REF, REGRESSION_SHA256),
    ):
        require(
            digest((plan / ref).read_bytes()) == expected,
            "GP5_RETAINED_EVIDENCE_CHANGED",
        )
    approval_path = plan / GP5_APPROVAL_REF
    approval = read_record(approval_path)
    require(
        json.dumps(approval, sort_keys=True)
        == json.dumps(approval_record(), sort_keys=True),
        "GP5_OWNER_APPROVAL",
    )
    return digest(approval_path.read_bytes()), read_record(plan / OBSERVATION_REF)


def expected_readback(
    plan: Path, candidate_root: Path, revision: str
) -> dict[str, object]:
    approval_sha, observation = approved_input(plan)
    component = component_sha256(candidate_root, revision)
    require(component == OBSERVED_COMPONENT_SHA256, "GP5_CANDIDATE_GATEWAY_CHANGED")
    return {
        "record_type": "gp5_openai_private_receipt_readback",
        "schema_version": "1.0",
        "source": "OWNER_APPROVED_LOCAL_RECEIPT",
        "candidate_revision": revision,
        "component_sha256": component,
        "approval_sha256": approval_sha,
        "original_source_revision": observation["source_revision"],
        "original_runtime_sha256": observation["source_sha256"],
        "original_action_revision": observation["action_revision"],
        "original_response_sha256": observation["response_sha256"],
        "private_manifest_sha256": observation["private_archive_manifest_sha256"],
        "observation_sha256": OBSERVATION_SHA256,
        "regression_sha256": REGRESSION_SHA256,
        "observed_model": "gpt-6.2-sol",
        "http_status": 200,
        "ledger_attempts": 1,
        "provider_requests": 0,
    }


def validate_gp5_receipt(plan: Path, record: dict[str, Any]) -> None:
    """Validate the sanitized artifacts of the authorized local witness."""
    plan = plan.resolve()
    expected = expected_readback(plan, plan.parent, record["revision"])
    for ref in (GP5_APPROVAL_REF, GP5_READBACK_REF):
        path = plan / ref
        required = {"ref": ref, "sha256": digest(path.read_bytes())}
        require(
            path.resolve() == path and record["artifacts"].count(required) == 1,
            "GP5_ARTIFACT_BINDING",
        )
    actual = read_record(plan / GP5_READBACK_REF)
    require(
        json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True),
        "GP5_READBACK_IDENTITY",
    )


def verify_private_receipt(plan: Path, snapshot: Path, private: Path) -> None:
    """Check the immutable raw receipt and exact ledger row before any attestation."""
    _, observation = approved_input(plan)
    revision = observation["source_revision"]
    require(
        component_sha256(snapshot, revision) == OBSERVED_COMPONENT_SHA256,
        "GP5_ORIGINAL_SOURCE",
    )
    sys.path[:0] = [
        str(snapshot),
        str(snapshot / "src"),
        str(snapshot / "plan/scripts"),
    ]
    from probe_dispatch import fingerprint_source

    from scripts.ci.run_live_provider import _private_record, summarize_observation

    require(
        all(
            Path(getfile(call)).resolve().is_relative_to(snapshot)
            for call in (fingerprint_source, _private_record, summarize_observation)
        ),
        "GP5_ORIGINAL_SOURCE",
    )
    require(
        fingerprint_source(snapshot)
        == fingerprint_source(snapshot, revision)
        == observation["source_sha256"],
        "GP5_ORIGINAL_SOURCE",
    )
    require(stat.S_IMODE(private.stat().st_mode) == 0o700, "GP5_PRIVATE_DIRECTORY")
    manifest = _private_record(private / "SHA256SUMS.json")
    require(
        digest(manifest) == observation["private_archive_manifest_sha256"],
        "GP5_PRIVATE_MANIFEST",
    )
    names = json.loads(manifest)
    records = {name: _private_record(private / name) for name in names}
    require(
        {name: digest(raw) for name, raw in records.items()} == names,
        "GP5_PRIVATE_RECEIPT_CHANGED",
    )
    checked = summarize_observation(
        observation["action_revision"],
        0,
        records["grant.json"],
        records["request.json"],
        records["task-receipt.json"],
        records["provider.json"],
    )
    require(
        checked["observation"] == "OPENAI_STRUCTURED_SUCCESS"
        and checked["probe"]["response_hash"] == observation["response_sha256"],
        "GP5_PRIVATE_RESPONSE",
    )
    wal = private / "ledger.sqlite-wal"
    require(not wal.exists() or wal.stat().st_size == 0, "GP5_LEDGER_NOT_CHECKPOINTED")
    ledger_uri = (private / "ledger.sqlite").as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(ledger_uri, uri=True)) as ledger:
        attempts = ledger.execute(
            "SELECT attempt_id,state,result_record,retry_record FROM attempts"
        ).fetchall()
    original = json.loads(records["provider.json"])["result"]
    require(
        len(attempts) == 1
        and attempts[0][:2] == (original["attempt_id"], "FINISHED")
        and json.loads(attempts[0][2]) == original
        and attempts[0][3] is None,
        "GP5_PRIVATE_LEDGER_ATTEMPT",
    )
    require(
        digest(_private_record(private / "ledger.sqlite")) == names["ledger.sqlite"],
        "GP5_PRIVATE_LEDGER_CHANGED",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--private-receipt", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = Path(__file__).resolve().parents[1]
    result = expected_readback(
        plan, args.candidate_root.resolve(), args.candidate_revision
    )
    verify_private_receipt(
        plan, args.snapshot.resolve(), args.private_receipt.resolve()
    )
    with os.fdopen(
        os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as report:
        json.dump(result, report, indent=2)
        report.write("\n")
    print("GP5_LOCAL_RECEIPT_READBACK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
