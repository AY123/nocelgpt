"""The sole Canon writer, currently limited to explicit manual/test roots.

Callers are trusted application composition code supplying an authenticated
actor. There is no HTTP authentication or chapter Permit verifier here yet.
Provisioning/revocation require the deployment operator, never a model worker.
"""

from sqlalchemy import Engine

from anovel.canon.models import CommitReceipt, ExecutionTicket, RootSeed, StoredRoot
from anovel.canon.repository import Repository


class CanonCommitService:
    def __init__(self, engine: Engine) -> None:
        self._repository = Repository(engine)

    def provision(self, project: str, branch: str, initializer: str) -> None:
        """Privileged composition: empty scope/grant only, never Canon contents."""
        self._repository._provision(project, branch, initializer)

    def begin_root(
        self, project: str, branch: str, actor: str, request_id: str
    ) -> ExecutionTicket:
        return self._repository._begin_root(project, branch, actor, request_id)

    def initialize_root(
        self, ticket: ExecutionTicket, seed: RootSeed, prose: bytes
    ) -> CommitReceipt:
        return self._repository._initialize_root(ticket, seed, prose)

    def cancel(self, ticket: ExecutionTicket) -> CommitReceipt | None:
        """None confirms cancellation; a receipt means commit already won."""
        return self._repository._cancel(ticket)

    def revoke_initializer(self, project: str, branch: str, actor: str) -> int:
        return self._repository._revoke_initializer(project, branch, actor)

    def load_root(self, project: str, branch: str, commit_id: str) -> StoredRoot:
        return self._repository.load_root(project, branch, commit_id)
