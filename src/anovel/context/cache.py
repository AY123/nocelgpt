"""Disposable bounded in-process role cache; full inputs remain separately retained."""

from collections import OrderedDict
from hashlib import sha256

from anovel.canon.identity import canonical_bytes, decode_canonical

from .models import POLICY_HASH, ContextArtifact, ContextError, FrozenContextInputs


class ContextCache:
    def __init__(self, max_entries: int = 64) -> None:
        if type(max_entries) is not int or max_entries < 1:
            raise ContextError("cache capacity must be a positive exact integer")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, tuple[str, bytes]] = OrderedDict()

    def get(self, inputs: FrozenContextInputs) -> ContextArtifact | None:
        if type(inputs) is not FrozenContextInputs:
            raise ContextError("cache lookup needs complete frozen inputs")
        key = sha256(
            canonical_bytes({"inputs": inputs.content_hash, "policy": POLICY_HASH})
        ).hexdigest()
        entry = self._entries.get(key)
        if entry is None:
            return None
        digest, raw = entry
        if sha256(raw).hexdigest() != digest:
            raise ContextError("cache byte integrity mismatch")
        artifact = ContextArtifact.from_dict(decode_canonical(raw))
        r = inputs.request
        if (
            artifact.cache_key != key
            or artifact.request_hash != r.content_hash
            or artifact.input_hash != inputs.content_hash
            or (
                artifact.project,
                artifact.branch,
                artifact.parent_ref,
                artifact.contract_hash,
                artifact.role,
                artifact.actor_id,
                artifact.scene_id,
                artifact.budget,
            )
            != (
                r.project,
                r.branch,
                r.parent_ref,
                r.contract_hash,
                r.role,
                r.actor_id,
                r.scene_id,
                r.budget,
            )
        ):
            raise ContextError("cache scope or role binding mismatch")
        self._entries.move_to_end(key)
        return artifact

    def put(self, artifact: ContextArtifact) -> None:
        if type(artifact) is not ContextArtifact:
            raise ContextError("cache accepts only validated role artifacts")
        raw = artifact.to_bytes()
        self._entries[artifact.cache_key] = (sha256(raw).hexdigest(), raw)
        self._entries.move_to_end(artifact.cache_key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
