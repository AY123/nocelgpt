"""director.py — Phase 6 Narrative Director control layer.

This subdomain turns narrative state, quality, commercial, and signal inputs
into chapter objectives, director briefs, critique, rewrite decisions, version
comparisons, and selection records. It is advisory and read-side: it never
writes facts, never publishes, and never calibrates real reader signals.
"""

from .consumption import build_consumption_evidence
from .consumption_report import build_consumption_ab_report
from .semantic_ledger import render_semantic_ledger
from .plan import (build_chapter_objective, validate_chapter_objective,
                   render_chapter_objective)
from .brief import (build_director_brief, validate_director_brief,
                    render_director_brief)
from .critique import build_director_critique, validate_director_critique
from .rewrite import build_rewrite_decision, validate_rewrite_decision
from .compare import build_version_comparison, validate_version_comparison
from .select import build_version_selection, validate_version_selection
from .session import build_director_session, validate_director_session
from .feedback import build_director_feedback, prev_run_signals
from .mandate import (project_narrative_mandate, validate_narrative_mandate,
                      render_narrative_mandate)
from .mandate_check import check_mandate_chapter, check_mandate_series

__all__ = [
    "build_consumption_evidence",
    "build_consumption_ab_report",
    "render_semantic_ledger",
    "build_chapter_objective",
    "validate_chapter_objective",
    "render_chapter_objective",
    "build_director_brief",
    "validate_director_brief",
    "render_director_brief",
    "build_director_critique",
    "validate_director_critique",
    "build_rewrite_decision",
    "validate_rewrite_decision",
    "build_version_comparison",
    "validate_version_comparison",
    "build_version_selection",
    "validate_version_selection",
    "build_director_session",
    "validate_director_session",
    "build_director_feedback",
    "prev_run_signals",
    "project_narrative_mandate",
    "validate_narrative_mandate",
    "render_narrative_mandate",
    "check_mandate_chapter",
    "check_mandate_series",
]
