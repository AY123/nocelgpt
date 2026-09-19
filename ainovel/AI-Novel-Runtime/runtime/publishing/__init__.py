"""Publishing OS subdomain (ANES v2, roadmap 4.6, the final Phase-4 piece).

The Publishing OS turns the dashboard's panorama into OPERATIONS: per-chapter
Production Cards a human consults before publishing, and periodic Volume /
Direction Reviews over a window of chapters. The Direction review closes the
Phase-4 loop by proposing a revision to the authored Market Position (4.5) where
production reality diverged from the pre-book thesis.

DISCIPLINE (every module here holds it):
  - PURE read-side: every artifact is a deterministic FOLD over products that
    already exist (draft envelopes, inventory funnel, quality trend, commercial
    sessions, scene plans, publish-readiness, market-position). No new judgment
    model; same inputs => same output.
  - Never gates (ADR-003): gating const false on every artifact.
  - Human authority (ADR-009): a card informs a publish decision and a review
    PROPOSES a positioning revision, but only a human executes either. authority
    const human; the market_position_revision is never auto-written.
  - Reads only; writers persist under registry/derived/, never registry/facts/
    (ADR-006).

  ONE deliberate exception to "reads only": publish_queue.sync_publish_requests
  is an explicit ADAPTER that ENQUEUES publish approval requests (M6 ledger) for
  publish-ready chapters. It still never publishes — approving a request records
  the human go/no-go; authoring the published log (ADR-009) stays separate.
"""
from .card import build_production_card, write_production_card
from .review import build_review, write_review
from .publish_queue import sync_publish_requests

__all__ = ["build_production_card", "write_production_card",
           "build_review", "write_review",
           "sync_publish_requests"]
