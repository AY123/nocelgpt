"""Read-only evidence about a saved checkpoint and its exact Gateway attempt."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anovel.domain.identity import EntityId
    from anovel.gateway.models import GatewayResult

    from .generation import SceneGenerationSnapshot
    from .models import WorkflowSnapshot


@dataclass(frozen=True, slots=True)
class WrittenDraftCancellation:
    chapter_id: EntityId
    writer_input_hash: str
    revision_hash: str | None

    @property
    def state(self) -> str:
        return "CANCELLED" if self.revision_hash is None else "DRAFT_SAVED"

    def summary(self) -> dict[str, object]:
        return {
            "state": self.state,
            "artifact_state": "DRAFT",
            "chapter_id": self.chapter_id.to_dict(),
            "writer_input_hash": self.writer_input_hash,
            "revision_hash": self.revision_hash,
        }


def _result_metadata(result: GatewayResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "status": result.status,
        "charge_status": result.charge_status,
        "result_hash": sha256(result.to_bytes()).hexdigest(),
        "response_hash": result.reply.response_hash,
    }


@dataclass(frozen=True, slots=True)
class RecoveryReadback:
    project: str
    branch: str
    run_id: str
    step_id: str | None
    state: str
    record_hash: str
    attempt_id: str
    source_current: bool
    stored_result: dict[str, object] | None
    ledger_result: dict[str, object] | None

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: WorkflowSnapshot | SceneGenerationSnapshot,
        result: GatewayResult | None,
        *,
        step_id: str | None,
        source_current: bool,
    ) -> RecoveryReadback:
        return cls(
            checkpoint.project,
            checkpoint.branch,
            checkpoint.run_id,
            step_id,
            checkpoint.state,
            checkpoint.record_hash,
            checkpoint.attempt_id,
            source_current,
            _result_metadata(checkpoint.result),
            _result_metadata(result),
        )

    def summary(self) -> dict[str, object]:
        return {
            "project": self.project,
            "branch": self.branch,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "state": self.state,
            "record_hash": self.record_hash,
            "attempt_id": self.attempt_id,
            "source_current": self.source_current,
            "stored_result": self.stored_result,
            "ledger_result": self.ledger_result,
            "can_dispatch": False,
            "can_commit": False,
            "can_issue_permit": False,
            "accepted": False,
            "published": False,
        }
