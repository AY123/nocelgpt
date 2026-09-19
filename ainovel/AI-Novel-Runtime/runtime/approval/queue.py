from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import json

from .. import derived

APPROVAL_REQUEST_CATEGORY = "approval-requests"
APPROVAL_RECORD_CATEGORY = "approval-records"


class ApprovalTargetType(str, Enum):
    MINT = "mint"
    PUBLISH = "publish"
    GENESIS = "genesis"
    MARKET_POSITION_REVISION = "market_position_revision"
    OUTLINE_IMPORT = "outline_import"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    NEEDS_MORE_INFO = "needs_more_info"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    NEEDS_MORE_INFO = "needs_more_info"


class ApprovalNotFound(KeyError):
    """Raised when a decision targets a request id not in the queue."""


class ApprovalStateError(RuntimeError):
    """Raised when a decision is attempted on a request in a terminal state."""


# A request may still be decided while it sits in one of these open states.
# Everything else (approved/rejected/executed/cancelled) is terminal: it is an
# audit fact and re-deciding it would rewrite history.
_OPEN_STATES = frozenset({
    ApprovalStatus.PENDING.value,
    ApprovalStatus.DEFERRED.value,
    ApprovalStatus.NEEDS_MORE_INFO.value,
})

# The status a request lands in once a given decision is recorded. A decision
# is the human's verdict; the request status is the projection of that verdict.
_DECISION_TO_STATUS = {
    ApprovalDecision.APPROVED.value: ApprovalStatus.APPROVED.value,
    ApprovalDecision.REJECTED.value: ApprovalStatus.REJECTED.value,
    ApprovalDecision.DEFERRED.value: ApprovalStatus.DEFERRED.value,
    ApprovalDecision.NEEDS_MORE_INFO.value: ApprovalStatus.NEEDS_MORE_INFO.value,
}


@dataclass
class ApprovalRequest:
    id: str
    target_type: str
    target_id: str
    action: str
    reason: str
    authority: str = "system"
    status: str = ApprovalStatus.PENDING.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    # Triage/audit fields (task 5). Stored now, consumed next round — no sorting,
    # filtering, or auto-expiry keys off them yet. All optional + defaulted so old
    # on-disk requests (written before these existed) reload without error.
    risk_level: str = ""          # future enum: low/medium/high/critical ("" = unassessed)
    priority: int = 0             # higher = more urgent; 0 = unset (numeric for future sort)
    source_module: str = ""       # the requesting module; auto-derived from requested_by
    expires_at: str = ""          # ISO timestamp; stored only, no auto-expiry runs on it
    requested_by: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # source_module mirrors requested_by.module so a single query dimension
        # works whether the caller set it explicitly or only passed requested_by.
        if not self.source_module and isinstance(self.requested_by, dict):
            self.source_module = self.requested_by.get("module", "") or ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "approval_request",
            "id": self.id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "action": self.action,
            "reason": self.reason,
            "authority": self.authority,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at or self.created_at,
            "risk_level": self.risk_level,
            "priority": self.priority,
            "source_module": self.source_module,
            "expires_at": self.expires_at,
            "requested_by": self.requested_by,
            "context": self.context,
        }


@dataclass(frozen=True)
class ApprovalRecord:
    id: str
    request_id: str
    target_type: str
    target_id: str
    decision: str
    decided_by: str
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "approval_record",
            "id": self.id,
            "request_id": self.request_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "notes": self.notes,
            "snapshot": self.snapshot,
        }


@dataclass
class ApprovalQueue:
    project_path: Path
    requests: list[ApprovalRequest] = field(default_factory=list)
    records: list[ApprovalRecord] = field(default_factory=list)

    def enqueue(self, request: ApprovalRequest) -> ApprovalRequest:
        self.requests.append(request)
        self._persist_request(request)
        return request

    def decide(self, request_id: str, *, decision: ApprovalDecision, decided_by: str, notes: str = "") -> ApprovalRecord:
        """Record a human verdict and project it onto the request's status.

        A decision is only legal while the request sits in an open state; the
        terminal states (approved/rejected/executed/cancelled) are audit facts,
        so re-deciding them is refused rather than silently rewriting history.
        The request status is bumped and re-persisted so a reloaded queue no
        longer reports a decided request as pending."""
        request = self.get_request(request_id)
        if request is None:
            raise ApprovalNotFound(request_id)
        if request.status not in _OPEN_STATES:
            raise ApprovalStateError(
                f"request {request_id} is in terminal state '{request.status}'; "
                f"cannot apply decision '{decision.value}'")

        record = ApprovalRecord(
            id=self._next_record_id(),
            request_id=request.id,
            target_type=request.target_type,
            target_id=request.target_id,
            decision=decision.value,
            decided_by=decided_by,
            notes=notes,
            snapshot=request.to_dict(),
        )
        self.records.append(record)
        self._persist(record)

        request.status = _DECISION_TO_STATUS[decision.value]
        request.updated_at = record.decided_at
        self._persist_request(request)
        return record

    # --- queries (pure reads over the in-memory lists) -----------------------

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return next((r for r in self.requests if r.id == request_id), None)

    def list_requests(
        self,
        *,
        status: Optional[str] = None,
        target_type: Optional[str] = None,
        action: Optional[str] = None,
        source_module: Optional[str] = None,
    ) -> list[ApprovalRequest]:
        out = self.requests
        if status is not None:
            out = [r for r in out if r.status == status]
        if target_type is not None:
            out = [r for r in out if r.target_type == target_type]
        if action is not None:
            out = [r for r in out if r.action == action]
        if source_module is not None:
            out = [r for r in out if r.requested_by.get("module") == source_module]
        return list(out)

    def list_by_status(self, status: str) -> list[ApprovalRequest]:
        return self.list_requests(status=status)

    def list_by_target(self, target_type: str) -> list[ApprovalRequest]:
        return self.list_requests(target_type=target_type)

    def list_pending(self) -> list[ApprovalRequest]:
        return self.list_requests(status=ApprovalStatus.PENDING.value)

    def records_for(self, request_id: str) -> list[ApprovalRecord]:
        return [r for r in self.records if r.request_id == request_id]

    def list_records(self) -> list[ApprovalRecord]:
        return list(self.records)

    def stats(self) -> dict[str, Any]:
        """Aggregate counts for a run-through view: totals by status and by
        target type, plus the record count. Deterministic, sorted keys."""
        by_status: dict[str, int] = {}
        by_target: dict[str, int] = {}
        for r in self.requests:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            by_target[r.target_type] = by_target.get(r.target_type, 0) + 1
        return {
            "total_requests": len(self.requests),
            "total_records": len(self.records),
            "by_status": dict(sorted(by_status.items())),
            "by_target_type": dict(sorted(by_target.items())),
        }

    def _persist_request(self, request: ApprovalRequest) -> None:
        derived.write_artifact(
            project_path=self.project_path,
            category=APPROVAL_REQUEST_CATEGORY,
            artifact_id=request.id,
            artifact=request.to_dict(),
            serialized=json.dumps(request.to_dict(), ensure_ascii=False, sort_keys=True, indent=2),
        )

    def _persist(self, record: ApprovalRecord) -> None:
        derived.write_artifact(
            project_path=self.project_path,
            category=APPROVAL_RECORD_CATEGORY,
            artifact_id=record.id,
            artifact=record.to_dict(),
            serialized=json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, indent=2),
        )

    def _next_record_id(self) -> str:
        # Records get their own REC- namespace so a record id can never collide
        # with a request id in the flat derived index (which dedups by id across
        # categories) — a decision must never clobber the request it decided.
        existing = [e.get("id", "") for e in derived._load_index(self.project_path).get("artifacts", []) if e.get("category") == APPROVAL_RECORD_CATEGORY]
        nums = [int(x.split("-", 1)[1]) for x in existing if x.startswith("REC-") and x.split("-", 1)[1].isdigit()]
        return f"REC-{(max(nums) + 1) if nums else 1:05d}"


def _read_payload(project_path: Path, entry: dict) -> dict[str, Any]:
    """Read a derived artifact's payload from the file it was written to.

    The provenance index only carries id/category/path/hash — never the payload
    itself — so the fields (status, request_id, ...) must be read back from the
    JSON file at entry['path'], not off the index entry. Falls back to the index
    entry only if the file is missing or unreadable."""
    path = project_path / entry.get("path", "")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return entry


def load_approval_queue(project_path: str | Path) -> ApprovalQueue:
    queue = ApprovalQueue(project_path=Path(project_path))
    index = derived._load_index(queue.project_path)
    for artifact in index.get("artifacts", []):
        if artifact.get("category") == APPROVAL_REQUEST_CATEGORY:
            payload = _read_payload(queue.project_path, artifact)
            queue.requests.append(ApprovalRequest(
                id=payload.get("id", ""),
                target_type=payload.get("target_type", "other"),
                target_id=payload.get("target_id", ""),
                action=payload.get("action", ""),
                reason=payload.get("reason", ""),
                authority=payload.get("authority", "system"),
                status=payload.get("status", ApprovalStatus.PENDING.value),
                created_at=payload.get("created_at", datetime.now(timezone.utc).isoformat()),
                updated_at=payload.get("updated_at", ""),
                risk_level=payload.get("risk_level", ""),
                priority=payload.get("priority", 0),
                source_module=payload.get("source_module", ""),
                expires_at=payload.get("expires_at", ""),
                requested_by=payload.get("requested_by", {}),
                context=payload.get("context", {}),
            ))
        elif artifact.get("category") == APPROVAL_RECORD_CATEGORY:
            payload = _read_payload(queue.project_path, artifact)
            queue.records.append(ApprovalRecord(
                id=payload.get("id", ""),
                request_id=payload.get("request_id", ""),
                target_type=payload.get("target_type", "other"),
                target_id=payload.get("target_id", ""),
                decision=payload.get("decision", "approved"),
                decided_by=payload.get("decided_by", "human"),
                decided_at=payload.get("decided_at", datetime.now(timezone.utc).isoformat()),
                notes=payload.get("notes", ""),
                snapshot=payload.get("snapshot", {}),
            ))
    return queue


def create_approval_request(
    *,
    request_id: str,
    target_type: str,
    target_id: str,
    action: str,
    reason: str,
    requested_by: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
    risk_level: str = "",
    priority: int = 0,
    expires_at: str = "",
) -> ApprovalRequest:
    # source_module is intentionally omitted: it is auto-derived from
    # requested_by.module in __post_init__ so the two never drift.
    return ApprovalRequest(
        id=request_id,
        target_type=target_type,
        target_id=target_id,
        action=action,
        reason=reason,
        risk_level=risk_level,
        priority=priority,
        expires_at=expires_at,
        requested_by=requested_by or {},
        context=context or {},
    )


def record_approval_decision(
    queue: ApprovalQueue,
    *,
    request_id: str,
    decision: ApprovalDecision,
    decided_by: str,
    notes: str = "",
) -> ApprovalRecord:
    return queue.decide(request_id, decision=decision, decided_by=decided_by, notes=notes)
