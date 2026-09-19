"""promise/__init__.py — Promise tracking system (Stage B).

Unified tracking for packaging promises, narrative setups, and plot threads.
This module provides a single source of truth for all promises made to readers.
"""
from .ledger import (
    PromiseEntry,
    PromiseLedger,
    project_promise_ledger,
    ledger_artifact,
)
from .detectors import (
    detect_all_promises,
    detect_packaging_promises,
    detect_narrative_setups,
    detect_plot_threads,
    detect_promises_summary,
)
from .feedback import (
    pending_promises_for_chapter,
    overdue_promises_for_chapter,
    render_promise_brief,
    inject_promises_into_objective,
    render_promise_brief_for_prompt,
    verify_promise_delivery,
    promise_delivery_report,
)

__all__ = [
    "PromiseEntry",
    "PromiseLedger",
    "project_promise_ledger",
    "ledger_artifact",
    "detect_all_promises",
    "detect_packaging_promises",
    "detect_narrative_setups",
    "detect_plot_threads",
    "detect_promises_summary",
    "pending_promises_for_chapter",
    "overdue_promises_for_chapter",
    "render_promise_brief",
    "inject_promises_into_objective",
    "render_promise_brief_for_prompt",
    "verify_promise_delivery",
    "promise_delivery_report",
]
