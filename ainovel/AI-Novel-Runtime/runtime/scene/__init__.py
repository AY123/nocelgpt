"""Scene planning subdomain (ANES v2).

The missing layer between the outline and chapter drafting. `plan_scenes`
folds a chapter's orphaned outline intent (outline.first_30_chapters[chapter_no])
together with the event participants the chapter dramatizes into an ordered
beat skeleton (setup -> escalation -> turn -> reward -> exit_hook). This gives
the drafting prompt a paced structure instead of a single one-line goal.

DISCIPLINE:
  - A scene plan is a DERIVED design artifact (ADR-006): never a fact, never an
    event, never mutable state. Same facts + same outline => same plan.
  - Schema validity is DETERMINISTIC (may gate one plan). Beat quality is
    EVALUATIVE and never gates (ADR-003): a missing/weak plan degrades to the
    chapter goal, the serial keeps producing.
  - v1 is a deterministic mechanical projection (no LLM). A richer LLM scene
    planner can drop in later behind the same seam, exactly as the LLM quality
    judge dropped into the DraftReviewer seam.
"""
from .planner import plan_scenes, render_scene_plan
from .pacing import check_pacing, curve_summary
from .serial_pacing import check_serial_pacing
from .serial_humanization import check_serial_openings, render_recent_openings
from .serial_function_repeat import check_serial_function_repeat
from .serial_genre_drift import check_serial_genre_drift, marker_density
from .ir import build_chapter_ir, lower_to_scene_plan, render_chapter_ir

__all__ = ["plan_scenes", "render_scene_plan", "check_pacing", "curve_summary",
           "check_serial_pacing", "check_serial_openings", "render_recent_openings",
           "check_serial_function_repeat",
           "check_serial_genre_drift", "marker_density",
           "build_chapter_ir", "lower_to_scene_plan", "render_chapter_ir"]
