"""recompute/ — the Derived Recompute Engine (roadmap Phase 5.3).

The FINAL link that closes prose→fact evolution. After a mint advances a fact
(runtime/mint/), every derived artifact pinned to it — directly or transitively —
is stale (ADR-006). Staleness DETECTION already existed (runtime/derived.py);
this subdomain is the RESPONSE.

The response is a DETERMINISTIC/GENERATIVE PARTITION, the same discipline the
mint executor draws over candidates:
  - a PURE FOLD of facts (e.g. StoryState — reproducible, no model, no cost) is
    AUTO-REBUILT and written back with a fresh pin, so it is no longer stale;
  - a GENERATIVE artifact (prose draft, quality review, reader/commercial sim —
    produced by a model, an outward creative act) is NEVER auto-rebuilt; it is
    STAGED as 'regeneration required' with the exact human command. Re-authoring
    reviewed prose behind the author's back is not recompute, it's a silent
    clobber — and it crosses the ADR-009 human-authority boundary.

So this engine is to derived artifacts what the mint executor is to facts: it
does only the safe deterministic work and stages the rest for a human. It is NOT
a fact-writer (only runtime/mint/ is); it writes rebuilt derived artifacts + a
recompute-report, both under registry/derived/.
"""
from .engine import (
    ImpactItem,
    analyze_impact,
    recompute_plan,
    execute_recompute,
    register_rebuilder,
    is_deterministic,
)

__all__ = [
    "ImpactItem", "analyze_impact", "recompute_plan", "execute_recompute",
    "register_rebuilder", "is_deterministic",
]
