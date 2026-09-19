"""Novel Brain subdomain (ANES v2, roadmap P15).

The Novel Brain is the AUTHORED static 'constitution' of a novel — mission,
genre, target reader, promise, writing/forbidden style, commercial position,
emotional curve. It is NOT a story fact (ADR-006) and NOT a recomputed
projection (ADR-008: StoryState is a fold; the Brain is not). It is a third
artifact class — an authored input the author writes by hand — living under
sources/, never under registry/. Every prompt reads it as the single source of
intent; this phase wires its writing_style + forbidden_style into the
chapter-draft prompt's style directive. Advisory: validating it never gates.
"""

from .loader import (brain_path, load_brain, validate_brain,
                     brain_style_directive)

__all__ = ["brain_path", "load_brain", "validate_brain", "brain_style_directive"]
