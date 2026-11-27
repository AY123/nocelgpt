"""Pure frozen identity of the ledger admitted for one offline scene step.

The first binding of a legacy Draft identifies the supplied matching receipt
and current budget. It does not authenticate a unique historical ledger.
Filesystem and receipt checks belong to gateway_binding, not this DTO.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.gateway.models import BudgetLimit

from .models import WorkflowError


def _hash(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise WorkflowError("INVALID_SCENE_LEDGER_PIN")
    return value


@dataclass(frozen=True, slots=True)
class SceneLedgerPin:
    path: str
    device: int
    inode: int
    limit_bytes: bytes = field(repr=False)
    parent_result_hash: str

    def __post_init__(self) -> None:
        try:
            if type(self.path) is not str or "\0" in self.path:
                raise ValueError
            self.path.encode("utf-8")
            path = Path(self.path)
            if (
                not path.is_absolute()
                or not path.name
                or self.path.startswith("//")
                or ".." in path.parts
                or str(path) != self.path
                or type(self.device) is not int
                or self.device < 0
                or type(self.inode) is not int
                or self.inode < 1
                or type(self.limit_bytes) is not bytes
            ):
                raise ValueError
            limit = self.limit
            if limit.to_bytes() != self.limit_bytes:
                raise ValueError
            _hash(self.parent_result_hash)
        except (TypeError, ValueError, UnicodeError):
            raise WorkflowError("INVALID_SCENE_LEDGER_PIN") from None

    @property
    def limit(self) -> BudgetLimit:
        return BudgetLimit.from_dict(decode_canonical(self.limit_bytes))

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "scene_ledger_pin",
            "schema_version": "1.0",
            "path": self.path,
            "device": self.device,
            "inode": self.inode,
            "limit_base64": b64encode(self.limit_bytes).decode("ascii"),
            "limit_hash": sha256(self.limit_bytes).hexdigest(),
            "parent_result_hash": self.parent_result_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> SceneLedgerPin:
        try:
            if type(value) is not dict or set(value) != {
                "record_type",
                "schema_version",
                "path",
                "device",
                "inode",
                "limit_base64",
                "limit_hash",
                "parent_result_hash",
            }:
                raise ValueError
            if (
                type(value["record_type"]) is not str
                or value["record_type"] != "scene_ledger_pin"
                or type(value["schema_version"]) is not str
                or value["schema_version"] != "1.0"
                or type(value["path"]) is not str
                or type(value["device"]) is not int
                or type(value["inode"]) is not int
                or type(value["limit_base64"]) is not str
            ):
                raise ValueError
            raw = b64decode(value["limit_base64"], validate=True)
            if b64encode(raw).decode("ascii") != value["limit_base64"] or sha256(
                raw
            ).hexdigest() != _hash(value["limit_hash"]):
                raise ValueError
            return cls(
                value["path"],
                value["device"],
                value["inode"],
                raw,
                _hash(value["parent_result_hash"]),
            )
        except (TypeError, ValueError, UnicodeError):
            raise WorkflowError("INVALID_SCENE_LEDGER_PIN") from None

    @property
    def content_hash(self) -> str:
        return sha256(canonical_bytes(self.to_dict())).hexdigest()
