"""
ANovelOS V2 Entity Identity and Alias Resolution.

This module provides the foundational identity layer for narrative entities.
Entity identity is stable and independent from display names. Alias resolution
is project-scoped and fails explicitly on ambiguity.

Public API:
    Types:
        EntityId, ProjectId, EntityIdentity, ResolutionResult
    Operations:
        create_identity, rename_identity, add_alias, remove_alias, resolve_alias

Invariants:
    - Entity ID never changes (stable across rename)
    - Project isolation (no cross-project resolution)
    - Explicit ambiguity (no random selection)
    - Deterministic resolution

Contract: V2-005 Implementation Contract v1.1.0
Authority: docs/V2-005_IMPLEMENTATION_CONTRACT.md
Baseline: 4248258339fa1c90df1c9e34572df24abe13330d
"""

# Type aliases will be defined in Step 2
# Enums will be defined in Step 2
# Dataclasses will be defined in Step 2
# Functions will be defined in Step 3+
