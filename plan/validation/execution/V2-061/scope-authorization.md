# V2-061 Implementation Scope Authorization

## Authorization Context

Task: V2-061 Character Knowledge & Intent Core
Action: IMPLEMENT
Authorization Date: 2026-10-11
Baseline Revision: c1131f0f242b73f6f166205513a0629bab882c5e

## Scope Boundary

This authorization permits implementation of Character domain core according to:
- Frozen Contract: docs/V2-061_IMPLEMENTATION_CONTRACT.md (d35be3d)
- Accepted ADR: plan/decisions/ADR-002_CHARACTER_BASE_DERIVED_SCHEMA.md

## Allowed File Modifications

### Production Implementation
- src/anovel/domain/character.py (CREATE)
- src/anovel/domain/knowledge.py (CREATE)
- src/anovel/domain/lifecycle.py (CREATE - post-hoc ratified)
- src/anovel/domain/serialization.py (CREATE - post-hoc ratified)
- src/anovel/domain/superseded.py (CREATE - post-hoc ratified)
- src/anovel/domain/__init__.py (MODIFY - exports only)

### Schema
- specs/schemas/character.schema.json (CREATE)

### Tests
- tests/contract/test_v2_061.py (CREATE)
- tests/contract/test_v2_061_serialization.py (CREATE - post-hoc ratified)
- tests/contract/test_v2_061_lifecycle.py (CREATE - post-hoc ratified)
- tests/contract/test_superseded.py (CREATE - post-hoc ratified)

### Evidence and Governance
- plan/validation/execution/V2-061/ (directory - execution artifacts)
- plan/machine/implementation-backlog.yaml (MODIFY - evidence binding only)

## Prohibited Actions

- No modification to V2-005 EntityIdentity authority
- No modification to V2-006 Relationship authority
- No database implementation
- No Provider implementation
- No Canon persistence implementation
- No expansion to V2-007 or V2-008 scope
- No repository-wide or unlimited scope operations

## Authority Constraints

- BASE fields only in character.schema.json (no CACHE)
- aligns_with_fact must be field(compare=False)
- Proposition.context must be recursively deep-frozen
- EntityId reused from V2-005, not redesigned

## Scope Verification

Authorized paths exactly match execution packet allowed_paths.
Any operation outside allowed_paths requires explicit authorization.
