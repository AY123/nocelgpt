"""Inventory subdomain (ANES v2, roadmap P19 — serial production funnel).

Completes the serial production loop (SOP stage 14, 库存管理). The inventory is
NOT mutable operational state a job edits; like the Story State (ADR-008) and the
schedule (P17) it is a PROJECTION folded from products that already exist:

    inventory@now = fold(produced-draft index, draft envelope QA markers,
                         authored published log)

  - drafted   = a chapter draft exists in the derived draft index.
  - reviewed  = its envelope carries a qa_review (evaluative QA ran).
  - published = a human authorized it in sources/published-log.yaml. Publishing
    is an irreversible outward transition; per ADR-009 it is NEVER inferred from
    a draft existing — it comes only from the authored log.
  - ready (库存) = produced - published: stock available to publish.

DISCIPLINE:
  - PURE + DETERMINISTIC: same products => same funnel. Reads only; never writes
    facts (ADR-006) and never writes the published log (ADR-009).
  - ADVISORY, never gates (ADR-003): a thin ready-stock WARNS; it never blocks.
"""
from .loader import load_published_log, validate_published_log, published_log_path
from .projection import project_inventory, InventoryReport

__all__ = [
    "load_published_log", "validate_published_log", "published_log_path",
    "project_inventory", "InventoryReport",
]
