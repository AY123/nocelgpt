"""Long Novel Memory subdomain (ANES v2, roadmap P13).

The Registry is the project's long-term memory (facts never forgotten). This
subdomain adds the CONTINUITY layer a long serial needs: advisory tracking of
open threads, un-paid-off foreshadowing, and orphaned resources. The hard,
gating continuity rule (cause precedes effect) lives in runtime.validator as a
deterministic check; this subdomain is the soft, advisory counterpart.
"""

from .threads import ThreadReport, track_threads
from .state import StoryState, project_state, state_artifact, state_digest
from .character_runtime import (CharacterRuntime, project_character_runtime,
                                render_character_runtime)

__all__ = ["ThreadReport", "track_threads", "StoryState", "project_state",
           "state_artifact", "state_digest", "CharacterRuntime",
           "project_character_runtime", "render_character_runtime"]
