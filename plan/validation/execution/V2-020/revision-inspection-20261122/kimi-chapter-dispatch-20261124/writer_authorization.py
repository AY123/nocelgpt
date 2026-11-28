"""Bind one V2-020 Draft job after the protected task entry clears LIVE_CALL."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Literal, Never, cast

from anovel.canon.identity import decode_canonical
from anovel.domain.identity import EntityId
from anovel.gateway.models import BudgetLimit, EstimateFeeBound, GatewayRequest
from anovel.workflow.chapter import (
    DraftChapterBrief,
    KimiDraftWriter,
    OpenAIDraftWriter,
)
from anovel.workflow.models import FrozenChapterInput

_TASK = "V2-020"
_SOURCE_DIR = Path("validation/execution") / _TASK
WriterProvider = Literal["KIMI", "OPENAI"]
_GRANT_IDENTITY = {
    "schema_version": "1.0",
    "task_id": _TASK,
    "action": "LIVE_CALL",
    "artifact_state": "DRAFT",
}
_INPUT_NAMES = frozenset(
    {
        "current.json",
        "handoff.json",
        "brief.json",
        "request.json",
        "budget.json",
        "workflow.sqlite",
    }
)
_FEE_NAME = "estimate-fee.json"


class WriterAuthorizationError(ValueError):
    """A proposed job has no matching, current writing authorization."""


@dataclass(frozen=True, slots=True)
class ChapterJob:
    provider: WriterProvider
    grant_sha256: str
    directory: Path
    request: GatewayRequest = field(repr=False)
    budget: BudgetLimit
    estimate_fee: EstimateFeeBound | None
    current: FrozenChapterInput = field(repr=False)
    handoff: bytes = field(repr=False)
    brief: DraftChapterBrief = field(repr=False)
    source_chapter_id: EntityId | None
    revision_hash: str
    root_step_id: str | None
    workflow_db: Path
    ledger: Path
    output: Path
    claim: Path
    expected_target_revision_hash: str | None = None


def _fail(code: str) -> Never:
    raise WriterAuthorizationError("KIMI_DRAFT_AUTH_" + code)


def _digest_text(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail("HASH")
    return value


def _object(value: object) -> dict[str, object]:
    if type(value) is not dict:
        _fail("FIELDS")
    return cast(dict[str, object], value)


def _read_regular(path: Path, *, private: bool = False) -> bytes:
    if not path.is_absolute() or path != path.resolve(strict=True):
        _fail("PATH")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    )
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or (
            private
            and (
                info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
            )
        ):
            _fail("FILE")
        raw = stream.read()
        # Include ctime so an overwritten input with a restored mtime still fails.
        for check in (os.fstat(stream.fileno()), path.lstat()):
            if (
                check.st_dev,
                check.st_ino,
                check.st_mtime_ns,
                check.st_ctime_ns,
                check.st_size,
            ) != (
                info.st_dev,
                info.st_ino,
                info.st_mtime_ns,
                info.st_ctime_ns,
                info.st_size,
            ):
                _fail("INPUT_CHANGED")
    return raw


def _bound_sources(
    root: Path, packet: dict[str, object], claim_id: str, count: int
) -> tuple[tuple[bytes, str], ...]:
    claims = packet.get("claims")
    if type(claims) is not list:
        _fail("CLAIM")
    matches = [
        claim for item in claims if (claim := _object(item)).get("id") == claim_id
    ]
    if len(matches) != 1 or matches[0].get("kind") != "FACT":
        _fail("CLAIM")
    sources = matches[0].get("sources")
    if type(sources) is not list or len(sources) != count:
        _fail("CLAIM_SOURCES")
    bound = []
    for value in sources:
        source = _object(value)
        ref = source.get("ref")
        if set(source) != {"ref", "sha256"} or type(ref) is not str:
            _fail("SOURCE_REF")
        relative = Path(ref)
        if (
            str(relative) != ref
            or ".." in relative.parts
            or _SOURCE_DIR not in relative.parents
        ):
            _fail("SOURCE_REF")
        raw = _read_regular(root / "plan" / relative)
        digest = _digest_text(source["sha256"])
        if not raw.strip() or sha256(raw).hexdigest() != digest:
            _fail("SOURCE_HASH")
        bound.append((raw, digest))
    if len({digest for _, digest in bound}) != count:
        _fail("CLAIM_SOURCES")
    return tuple(bound)


def _grant_record(
    root: Path, packet: dict[str, object], provider: WriterProvider
) -> tuple[dict[str, object], str, str]:
    grant_kind = f"v2_020_{provider.lower()}_draft_authorization"
    identity = _GRANT_IDENTITY | {"record_type": grant_kind}
    sources = _bound_sources(root, packet, f"V2_020_{provider}_DRAFT_GRANT", 2)
    for candidate, digest in sources:
        try:
            grant = decode_canonical(candidate)
        except ValueError:
            continue
        if type(grant) is not dict or grant.get("record_type") != grant_kind:
            continue
        fields = identity.keys() | {
            "job_dir",
            "input_sha256",
            "owner_approval_sha256",
            "root_step_id",
        }
        if provider == "OPENAI" and "expected_target_revision_hash" in grant:
            fields.add("expected_target_revision_hash")
        if set(grant) != fields or any(
            grant[key] != value for key, value in identity.items()
        ):
            _fail("GRANT")
        owner_digest = _digest_text(grant["owner_approval_sha256"])
        if not any(
            other == owner_digest != digest and raw.decode("utf-8").strip()
            for raw, other in sources
        ):
            _fail("OWNER_APPROVAL")
        return cast(dict[str, object], grant), digest, owner_digest
    _fail("GRANT")


def _load_inputs(root: Path, grant: dict[str, object]) -> tuple[Path, dict[str, bytes]]:
    raw_directory = grant["job_dir"]
    if type(raw_directory) is not str:
        _fail("PATH")
    directory = Path(raw_directory)
    if (
        not directory.is_absolute()
        or str(directory) != raw_directory
        or directory != directory.resolve(strict=True)
    ):
        _fail("PATH")
    if directory.is_relative_to(root) and not directory.is_relative_to(root / "dist"):
        _fail("PATH")
    info = directory.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or info.st_uid != os.getuid()
    ):
        _fail("PATH")
    hashes = _object(grant["input_sha256"])
    if set(hashes) not in (_INPUT_NAMES, _INPUT_NAMES | {_FEE_NAME}):
        _fail("INPUTS")
    if any(
        (directory / f"workflow.sqlite{suffix}").is_symlink()
        or (directory / f"workflow.sqlite{suffix}").exists()
        for suffix in ("-journal", "-wal", "-shm")
    ):
        _fail("WORKFLOW_SIDECAR")
    inputs = {}
    for name, expected in hashes.items():
        raw = _read_regular(directory / name, private=True)
        if sha256(raw).hexdigest() != _digest_text(expected):
            _fail("INPUT_HASH")
        inputs[name] = raw
    database = inputs.pop("workflow.sqlite")
    if (
        not database.startswith(b"SQLite format 3\x00")
        or database[18:20] != b"\x01\x01"
    ):
        _fail("WORKFLOW_DATABASE")
    return directory, inputs


def _estimate_fee(
    root: Path,
    packet: dict[str, object],
    inputs: dict[str, bytes],
    authority_digests: tuple[str, str],
) -> EstimateFeeBound | None:
    raw = inputs.get(_FEE_NAME)
    claim = (
        "V2_020_KIMI_ESTIMATE_ZERO_COST"
        if raw is None
        else "V2_020_KIMI_ESTIMATE_FEE_BOUND"
    )
    ((_, evidence_digest),) = _bound_sources(root, packet, claim, 1)
    if evidence_digest in authority_digests:
        _fail("ESTIMATE_FEE")
    if raw is None:
        return None
    fee = EstimateFeeBound.from_dict(decode_canonical(raw))
    if fee.to_bytes() != raw or fee.evidence_sha256 != evidence_digest:
        _fail("ESTIMATE_FEE")
    return fee


def _check_budget(
    packet: dict[str, object],
    request: GatewayRequest,
    budget: BudgetLimit,
    fee: EstimateFeeBound | None,
) -> None:
    declared = _object(packet.get("budget"))
    model_cost = declared.get("model_cost_cap")
    runtime_seconds = declared.get("maximum_runtime")
    if (
        declared.get("paid_calls_allowed") is not True
        or type(declared.get("maximum_attempts")) is not int
        or declared["maximum_attempts"] != 1
        or type(model_cost) not in (int, float)
        or type(runtime_seconds) not in (int, float)
        or (budget.max_attempts, budget.max_inflight, budget.max_unknown) != (1, 1, 1)
        or (budget.project, budget.branch, budget.run_id)
        != (request.project, request.branch, request.run_id)
    ):
        _fail("BUDGET")
    cap = Decimal(str(model_cost)) * 1_000_000
    runtime = Decimal(str(runtime_seconds))
    policy = request.policies[0]
    reserve = policy.reserve_microusd + (fee.maximum_microusd if fee is not None else 0)
    if (
        not cap.is_finite()
        or not runtime.is_finite()
        or cap != cap.to_integral_value()
        or policy.input_rate <= 0
        or policy.output_rate <= 0
        or not reserve <= budget.total_microusd <= cap
        or not 0 < policy.timeout_seconds <= runtime
    ):
        _fail("BUDGET")
    deadline = datetime.fromisoformat(budget.deadline_at)
    remaining = Decimal(str((deadline - datetime.now(UTC)).total_seconds()))
    if (
        not 0 < remaining <= runtime
        or deadline > datetime.fromisoformat(policy.price_expires_at)
        or (fee is not None and deadline > datetime.fromisoformat(fee.expires_at))
    ):
        _fail("DEADLINE")


def validate_job(
    root: Path, packet: dict[str, object], *, provider: WriterProvider = "KIMI"
) -> ChapterJob:
    """Read the packet-bound job without prompting, writing, or authorizing I/O.

    The caller supplies the packet from the formal task checker. Local hashes
    bind exact evidence bytes; Owner review establishes what those bytes mean.
    """
    try:
        packet = _object(packet)
        if packet.get("task_id") != _TASK or packet.get("action") != "LIVE_CALL":
            _fail("ACTION")
        root = root.resolve(strict=True)
        grant, grant_digest, owner_digest = _grant_record(root, packet, provider)
        directory, inputs = _load_inputs(root, grant)
        ledger = directory / "writer.sqlite"
        current = FrozenChapterInput(inputs["current.json"])
        brief = DraftChapterBrief(inputs["brief.json"])
        request = GatewayRequest.from_dict(decode_canonical(inputs["request.json"]))
        budget = BudgetLimit.from_dict(decode_canonical(inputs["budget.json"]))
        if (
            request.to_bytes() != inputs["request.json"]
            or budget.to_bytes() != inputs["budget.json"]
        ):
            _fail("INPUT_IDENTITY")
        # Reuse the same template, closed schema, model and private ledger checks as dispatch.
        if provider == "KIMI":
            KimiDraftWriter(request=request, ledger_path=ledger)
            fee = _estimate_fee(root, packet, inputs, (grant_digest, owner_digest))
        else:
            OpenAIDraftWriter(request=request, ledger_path=ledger)
            if _FEE_NAME in inputs:
                _fail("INPUTS")
            fee = None
        _check_budget(packet, request, budget, fee)
        handoff_raw = inputs["handoff.json"]
        handoff = _object(decode_canonical(handoff_raw))
        source = EntityId.from_dict(handoff["source_chapter_id"])
        target = EntityId.from_dict(handoff["target_chapter_id"])
        current_chapter = EntityId.from_dict(current.to_dict()["chapter_id"])
        if (
            (
                handoff.get("record_type"),
                handoff.get("schema_version"),
                handoff.get("artifact_state"),
            )
            != ("next_chapter_draft_input", "1.0", "DRAFT")
            or (
                handoff.get("project"),
                handoff.get("branch"),
                handoff.get("source_run_id"),
            )
            != (request.project, request.branch, request.run_id)
            or not source.project
            == target.project
            == current_chapter.project
            == request.project
        ):
            _fail("HANDOFF")
        brief.for_handoff(handoff)
        root_step_id = grant["root_step_id"]
        return ChapterJob(
            provider=provider,
            grant_sha256=grant_digest,
            directory=directory,
            request=request,
            budget=budget,
            estimate_fee=fee,
            current=current,
            handoff=handoff_raw,
            brief=brief,
            source_chapter_id=None if source == current_chapter else source,
            revision_hash=_digest_text(handoff["source_revision_hash"]),
            root_step_id=None if root_step_id is None else _digest_text(root_step_id),
            workflow_db=directory / "workflow.sqlite",
            ledger=ledger,
            output=directory / "draft.json",
            claim=directory / "dispatch-claim.json",
            expected_target_revision_hash=_digest_text(
                grant["expected_target_revision_hash"]
            )
            if "expected_target_revision_hash" in grant
            else None,
        )
    except WriterAuthorizationError as error:
        if provider == "OPENAI":
            raise WriterAuthorizationError(
                str(error).replace("KIMI_DRAFT_AUTH_", "OPENAI_DRAFT_AUTH_", 1)
            ) from None
        raise
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        InvalidOperation,
        OverflowError,
    ):
        raise WriterAuthorizationError(f"{provider}_DRAFT_AUTH_INVALID_JOB") from None
