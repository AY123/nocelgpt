"""Character Speech Profile subdomain (ANES v2, roadmap §15).

The Speech Profile is the AUTHORED expression-layer spec for a novel's characters
— HOW each one talks (register/vocabulary, sentence shape, verbal habits, taboos,
thinking pattern, default emotion). It is the direct system remedy for the §14
real-model finding: three models all wrote every character in one voice because
the system never told any of them how two people should sound different.

It is NOT a story fact (ADR-006: the Character fact schema has no language field)
and NOT a recomputed projection (ADR-008: character_runtime folds motivation, which
is ORTHOGONAL to expression). It is a third artifact class — an authored input the
author writes by hand — living under sources/, next to the Novel Brain. Every
consumer reads it; this phase wires the language block for each appearing lead into
the v7 chapter-draft prompt. Advisory: validating it never gates (ADR-003).
"""

from .loader import (speech_path, load_speech, validate_speech,
                     speech_profiles_by_id, render_speech_profiles)

__all__ = ["speech_path", "load_speech", "validate_speech",
           "speech_profiles_by_id", "render_speech_profiles"]
