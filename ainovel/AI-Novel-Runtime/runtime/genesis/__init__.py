"""genesis/ — Auto Project Genesis (ANES v2, roadmap M2 / Phase 8).

The book-opening orchestration layer: from reference features + human preference,
produce a PRODUCIBLE new-book project — Novel Brain + market position + character/
world/event candidates landed via the mint boundary + a runnable event log the
serial can produce against.

DISCIPLINE:
  - WRITES NO FACTS DIRECTLY (ADR-006/009): characters/world/events reach the
    registry only through runtime/mint/ (executor for prose-extraction, genesis_
    apply for the structured outline batch), always human-confirmed. This module
    orchestrates and folds; it never touches registry/facts/ itself (fitness #23).
  - The Brain draft is an AUTHORED source (sources/novel-brain.yaml); Genesis
    proposes a deterministic first draft the author confirms/edits (like the
    Speech Profile: system may prepare, human authorizes).
"""

from .brain_gen import build_brain, brain_yaml, write_brain
from .orchestrate import run_genesis, GenesisResult

__all__ = ["build_brain", "brain_yaml", "write_brain",
           "run_genesis", "GenesisResult"]
