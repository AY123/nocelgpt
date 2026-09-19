"""mint/ — the EXECUTION half of prose→fact evolution (roadmap Phase 5.2).

This is the ONLY module in the system that writes registry/facts/. It exists as
a separate subdomain on purpose: it makes the ADR-009 preparation/execution split
PHYSICAL. runtime/candidates/ prepares and stages (and a fitness guard forbids it
from writing facts); runtime/mint/ is the single authorized fact-writer. Crossing
the human-authority boundary lives in exactly one place, auditable and testable.

DISCIPLINE:
  - HUMAN-AUTHORIZED ONLY (ADR-009): mint runs only on explicit confirmation and
    only over candidates a human accepted. Preparation's mere existence is never
    consent; a preview writes nothing.
  - ADDITIVE ONLY (this phase): mint applies only `additive` candidates — fill an
    empty field on an existing entity + bump fact_version. It never overwrites a
    declared fact (`conflicting` is a retcon, out of scope) and never creates an
    entity (`new` needs the ID Mint Ledger, 5.4). Non-additive accepted
    candidates are REFUSED.
  - VALIDATE-THEN-WRITE: the post-mint registry is built and validated in memory
    against the full deterministic gate; facts are committed to disk ONLY if it
    passes. A mint that would introduce a dangling ref, tombstone ref, or
    causality cycle is rejected and writes nothing. The SSOT is never left in a
    half-written or invalid state.
  - STALE PLANS REFUSED (ADR-006): a plan whose reconciliation was computed
    against a fact that has since advanced is stale; you must not mint from a
    superseded reconciliation.
"""
from .executor import (
    MintRefused,
    plan_mint,
    preview_mint,
    execute_mint,
)
from ..approval import (
    ApprovalDecision,
    ApprovalQueue,
    ApprovalRequest,
    ApprovalRecord,
    create_approval_request,
    record_approval_decision,
    load_approval_queue,
)
# genesis_apply.py is the SECOND authorized fact-writer, for a different job: it
# lands an outline's STRUCTURED batch (events with timeline/refs) and remaps
# intra-plan candidate ids to minted ids. It shares executor's landing discipline
# (idmint allocation, validate-then-write gate, atomic commit); it does not fork
# the write path. Both live here so guard #16 (only mint/ writes facts) still holds.
from .genesis_apply import (
    preview_genesis,
    execute_genesis,
)

__all__ = ["MintRefused", "plan_mint", "preview_mint", "execute_mint",
           "preview_genesis", "execute_genesis", "ApprovalDecision",
           "ApprovalQueue", "ApprovalRequest", "ApprovalRecord",
           "create_approval_request", "record_approval_decision",
           "load_approval_queue"]
