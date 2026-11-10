"""The sole Canon writer: roots and authorized finite-Delta chapter protocol.

Callers are trusted application composition code supplying an authenticated
actor. No HTTP authentication or production Q0-Q3 issuer is implemented here.
P2 test Permits require explicit isolated composition; production rejects them.
Provisioning/revocation and the separate issuer belong to trusted composition.
"""

from sqlalchemy import Engine

from anovel.canon import projection
from anovel.canon.chapter import ChapterCandidate, StoredChapter
from anovel.canon.models import CommitReceipt, ExecutionTicket, RootSeed, StoredRoot
from anovel.canon.repository import Repository, _test_database
from anovel.domain.delta import FactBaseline


class CanonCommitService:
    def __init__(self, engine: Engine, *, test_database: str | None = None) -> None:
        if test_database is not None:
            _test_database(engine, test_database)
        self._test_database = test_database
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

    def _require_test(self) -> None:
        if self._test_database is None:
            from anovel.canon.models import CanonPermissionError

            raise CanonPermissionError(
                "P2 chapter setup requires isolated test composition"
            )

    def configure_chapter_authority(
        self,
        project: str,
        branch: str,
        actor: str,
        issuer_id: str,
        policy_version: str = "TEST-POLICY-1",
    ) -> int:
        """Deployment capability, never an endpoint granted to a Worker."""
        self._require_test()
        return self._repository._configure_chapter_authority(
            project, branch, actor, issuer_id, policy_version
        )

    def begin_chapter(
        self, project: str, branch: str, actor: str, request_id: str, parent_ref: str
    ) -> ExecutionTicket:
        self._require_test()
        return self._repository._begin_chapter(
            project, branch, actor, request_id, parent_ref
        )

    def commit(
        self, ticket: ExecutionTicket, candidate: ChapterCandidate, permit_ref: str
    ) -> CommitReceipt:
        return self._repository._commit_chapter(
            ticket, candidate, permit_ref, accept_test=self._test_database is not None
        )

    def revoke_chapter_authority(self, project: str, branch: str, actor: str) -> int:
        self._require_test()
        return self._repository._revoke_chapter_authority(project, branch, actor)

    def load_commit(self, project: str, branch: str, commit_id: str) -> StoredChapter:
        return self._repository.load_commit(project, branch, commit_id)

    def load_baseline(self, project: str, branch: str, commit_id: str) -> FactBaseline:
        return self._repository.load_baseline(project, branch, commit_id)

    def rebuild_snapshot(
        self, project: str, branch: str, commit_id: str
    ) -> projection.RebuiltSnapshot:
        """Rebuild accepted history read-only; failure cannot roll back Canon."""
        history = self._repository.load_history(project, branch, commit_id)
        receipt = history[-1].content.receipt
        try:
            return projection.rebuild(history)
        except Exception as error:
            # Source verification happened above. An invalid/missing history
            # never receives a fabricated successful target receipt here.
            raise projection.ProjectionError(
                "snapshot projection failed; original Canon remains committed", receipt
            ) from error

    def review_submission(
        self, ticket: ExecutionTicket, candidate: ChapterCandidate
    ) -> dict[str, object]:
        return self._repository.review_submission(ticket, candidate)


class ProtectedPermitIssuer:
    """P2-only isolated test capability, separately held by trusted composition.

    This service executes deterministic test checks itself. It does not accept
    caller-supplied PASS/ALLOW records or a production source label. P7 provides
    actual production quality integration; possession of the DB engine remains
    outside the ordinary caller's capability boundary.
    """

    def __init__(self, engine: Engine, *, test_database: str, issuer_id: str) -> None:
        from anovel.canon.models import identifier

        _test_database(engine, test_database)
        self._issuer_id = identifier(issuer_id)
        self._repository = Repository(engine)

    def issue(
        self,
        ticket: ExecutionTicket,
        candidate: ChapterCandidate,
        ttl_seconds: int = 300,
    ) -> str:
        return self._repository._issue_permit(
            ticket, candidate, self._issuer_id, ttl_seconds
        )

    def revoke(self, project: str, branch: str, permit_ref: str) -> None:
        self._repository._revoke_permit(project, branch, permit_ref, self._issuer_id)
