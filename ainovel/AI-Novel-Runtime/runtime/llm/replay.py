from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .types import sha256_obj, to_dict


def _stable_request_payload(request) -> dict:
    payload = to_dict(request) if hasattr(request, "__dataclass_fields__") else dict(request)
    # Strip fields that are volatile or OPERATIONAL, not part of the semantic
    # request: two identical prompts differing only in these must share a cache
    # entry. request_id is per-call; timeout_seconds is "how long we'll wait",
    # not "what we asked" — including it made a rerun with a different --timeout
    # miss the cache and re-bill the provider.
    payload.pop("request_id", None)
    payload.pop("timeout_seconds", None)
    provenance = payload.get("prompt_provenance")
    if isinstance(provenance, dict):
        provenance = dict(provenance)
        provenance.pop("rendered_at", None)
        payload["prompt_provenance"] = provenance
    return payload


def stable_request_hash(request) -> str:
    """Hash the semantic request exactly as replay does.

    Audit producers use this instead of hashing only prompt text, so optional
    wire contracts such as a structured-output schema are covered too.
    """
    return sha256_obj(_stable_request_payload(request))


class ReplayStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def key_for(self, request) -> str:
        return stable_request_hash(request)

    def path_for(self, request) -> Path:
        key = self.key_for(request).replace(":", "_")
        return self.root / f"{key}.json"

    def get(self, request) -> Optional[dict]:
        path = self.path_for(request)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, request, response) -> str:
        path = self.path_for(request)
        payload = {
            "request_hash": self.key_for(request),
            "request": to_dict(request),
            "response": to_dict(response),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8")
        return str(path)
