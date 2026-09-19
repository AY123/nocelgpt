"""Narrative State subdomain (ANES v2, M3-B5, ADR-008).

The narrative state of a long serial lived FRAGMENTED across four projections:
  - StoryState (memory/state.py)      — open/resolved setups, entities (facts fold)
  - narrative-mandate (director/)     — escalation ladder + protagonist inner shift
  - chapter-ir (scene/ir.py)          — reader questions + payoff targets per beat
  - chapter-run (serialize/loop.py)   — realized pacing peaks (emotional curve)

Nothing read all four at once, so no consumer could answer "what narrative PHASE
is the story in, how much payoff DEBT has accrued, is the emotion curve fatiguing,
which reader questions are still open". This subdomain folds them into ONE read-
side `narrative-state` projection.

DISCIPLINE (mirrors StoryState exactly):
  - PURE + DETERMINISTIC fold (ADR-008): reads facts + already-persisted derived
    artifacts; no model, no randomness. Same inputs => same projection.
  - DERIVED, never a fact (ADR-006): written under registry/derived/, recomputable.
  - ADVISORY, never gates (ADR-003): gating=false. It informs the director
    objective / dashboard / revision, it decides nothing.
"""
from .state import (NarrativeState, project_narrative_state,
                    narrative_state_artifact)

__all__ = ["NarrativeState", "project_narrative_state",
           "narrative_state_artifact"]
