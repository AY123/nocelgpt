# V2-005 Implementation Plan

**Document ID**: V2-005-IMPLEMENTATION-PLAN  
**Version**: 1.1.0  
**Date**: 2026-10-03  
**Status**: REVISED / INDEPENDENT_REVIEW_PENDING  
**Authority**: Implementation Roadmap (Pending Approval)  
**Baseline**: dev_cc @ 323eaae7

---

## Overview

This plan provides the step-by-step implementation sequence for V2-005 (Core Entity IDs and Alias Resolution). Each step is designed to be atomic, verifiable, and non-blocking.

**Total Estimated Steps**: 8 steps  
**Estimated Duration**: 2-4 implementation sessions  
**Critical Path**: Yes (blocks P1 → P2 transition)

---

## Implementation Sequence

### Step 1: Create Module Structure

**Objective**: Establish basic module skeleton with imports and docstring.

**Files Touched**:
- `src/anovel/domain/__init__.py` (create if not exists)
- `src/anovel/domain/identity.py` (create)

**Actions**:
1. Create `src/anovel/domain/` directory if not exists
2. Create `__init__.py` with module-level docstring
3. Create `identity.py` with module docstring (per contract § 12.1)
4. Add basic imports (dataclasses, enum, typing, Optional, NewType, Union, Literal)
5. NO implementation yet, only structure

**Expected Content** (`identity.py`):
```python
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

Contract: V2-005 Implementation Contract
Authority: plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, NewType, Optional, Union

# Type aliases will be defined here
# Enums will be defined here
# Dataclasses will be defined here
# Functions will be defined here
```

**Exit Criteria**:
- Files exist
- Module can be imported (`from anovel.domain import identity`)
- No syntax errors
- No implementation yet

**Tests**: None yet (structure only)

**Why This Step**: Establishes clean foundation; verifies package structure works.

---

### Step 2: Implement Core Types

**Objective**: Define all domain types (EntityId, ProjectId, EntityIdentity, ResolutionResult variants).

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Define `EntityId = NewType('EntityId', str)`
2. Define `ProjectId = NewType('ProjectId', str)`
3. Define `ResolutionStatus(Enum)` with all four variants
4. Define `EntityIdentity` dataclass (frozen=True) with all fields
5. Define all four ResolutionResult variants (ResolvedResult, NotFoundResult, AmbiguousResult, InvalidInputResult)
6. Define `ResolutionResult` Union type
7. Add docstrings to all types
8. NO operations yet

**Expected Additions**:
```python
EntityId = NewType('EntityId', str)
ProjectId = NewType('ProjectId', str)

class ResolutionStatus(Enum):
    """Status of alias resolution attempt."""
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    INVALID_INPUT = "invalid_input"

@dataclass(frozen=True)
class EntityIdentity:
    """Immutable identity aggregate for narrative entities."""
    entity_id: EntityId
    project_id: ProjectId
    canonical_name: str
    aliases: frozenset[str]
    entity_type: Optional[str] = None

# ... (all ResolutionResult variants)
```

**Exit Criteria**:
- All types defined
- Types can be imported and instantiated
- frozen=True verified
- All docstrings present
- mypy passes (or equivalent type checker)

**Tests**: Can begin writing type instantiation tests (not required yet)

**Why This Step**: Core types are foundation for all operations; verify immutability works.

---

### Step 3: Implement ID Generation and normalize_for_lookup

**Objective**: Implement helper functions for ID generation and normalization.

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Implement `_generate_entity_id() -> EntityId` (private function)
   - Use UUID v4: `import uuid` then `EntityId(str(uuid.uuid4()))`
2. Implement `normalize_for_lookup(s: str) -> str` (public function)
   - Strip whitespace (ASCII space + U+3000)
   - Collapse internal spaces
   - ASCII lowercase if `s.isascii()`, else unchanged
   - Full docstring per contract § 12.2
3. Add unit tests for normalization edge cases

**Expected Additions**:
```python
import uuid

def _generate_entity_id() -> EntityId:
    """Generate unique entity ID using UUID v4."""
    return EntityId(str(uuid.uuid4()))

def normalize_for_lookup(s: str) -> str:
    """
    Normalize string for alias lookup.
    
    Steps:
    1. Strip outer whitespace (ASCII and full-width U+3000)
    2. Delete all internal full-width spaces: s.replace('　', '')
    3. Collapse internal ASCII spaces: ' '.join(s.split())
    4. Lowercase ASCII only: s.lower() if s.isascii() else s
    
    Args:
        s: Input string to normalize
    
    Returns:
        Normalized string for comparison
    
    Example:
        >>> normalize_for_lookup("  John  ")
        'john'
        >>> normalize_for_lookup("李　明")
        '李明'
    """
    # Strip outer whitespace (ASCII and full-width)
    s = s.strip().strip('　')
    # Delete all internal full-width spaces
    s = s.replace('　', '')
    # Collapse internal ASCII spaces
    s = ' '.join(s.split())
    # ASCII lowercase only
    return s.lower() if s.isascii() else s
```

**Exit Criteria**:
- `_generate_entity_id()` returns unique IDs
- `normalize_for_lookup()` handles all contract cases
- Tests verify normalization (TC-005-023 through TC-005-026)
- No prohibited imports (standard library uuid acceptable)

**Tests**: 
- `test_normalize_whitespace`
- `test_normalize_ascii_case`
- `test_normalize_chinese_case_sensitive`
- `test_normalize_full_width_space`

**Why This Step**: Core utilities needed by all operations; verify early.

---

### Step 4: Implement EntityRegistry

**Objective**: Implement in-memory registry for testing and contract satisfaction.

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Implement `EntityRegistry` class
   - `__init__`: Initialize internal dicts
   - `add_entity(entity: EntityIdentity) -> None`
   - `get_entity(entity_id: EntityId) -> Optional[EntityIdentity]`
   - `get_entities(project_id: ProjectId) -> Iterable[EntityIdentity]`
2. Internal storage: 
   - `_entities: dict[EntityId, EntityIdentity]`
   - `_by_project: dict[ProjectId, set[EntityId]]`
3. Add docstrings per contract

**Expected Addition**:
```python
class EntityRegistry:
    """In-memory registry for entity storage (V2-005 testing only)."""
    
    def __init__(self):
        self._entities: dict[EntityId, EntityIdentity] = {}
        self._by_project: dict[ProjectId, set[EntityId]] = {}
    
    def add_entity(self, entity: EntityIdentity) -> None:
        """Add entity with uniqueness check per §4.1."""
        if entity.entity_id in self._entities:
            existing = self._entities[entity.entity_id]
            if existing != entity:
                raise ValueError(
                    f"Entity ID {entity.entity_id} already registered "
                    f"with different content"
                )
            # Same content → idempotent, no-op
            return
        
        # Normal registration
        self._entities[entity.entity_id] = entity
        self._by_project.setdefault(entity.project_id, set()).add(entity.entity_id)
    
    def get_entity(self, entity_id: EntityId) -> Optional[EntityIdentity]:
        """Retrieve entity by ID."""
        return self._entities.get(entity_id)
    
    def get_entities(self, project_id: ProjectId) -> list[EntityIdentity]:
        """Retrieve all entities in project."""
        entity_ids = self._by_project.get(project_id, set())
        return [self._entities[eid] for eid in entity_ids]
```

**Exit Criteria**:
- Registry stores and retrieves entities
- Project isolation works
- No persistence (in-memory only)

**Tests**:
- Basic registry operations
- Project isolation in registry

**Why This Step**: Required for resolve_alias implementation and tests.

---

### Step 5: Implement create_identity and rename_identity

**Objective**: Implement entity creation and rename operations.

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Implement `create_identity(project_id, canonical_name, entity_type=None) -> EntityIdentity`
   - Validate inputs (ValueError if empty/whitespace)
   - Generate fresh entity_id
   - Return EntityIdentity with empty aliases
   - Full docstring per contract § 12.2
2. Implement `rename_identity(identity, new_canonical_name) -> EntityIdentity`
   - Validate new_canonical_name
   - Return new EntityIdentity (frozen, immutable)
   - Preserve entity_id and project_id
   - Add old canonical_name to aliases (automatic preservation)
   - Full docstring per contract § 12.2

**Expected Additions**:
```python
def create_identity(
    project_id: ProjectId,
    canonical_name: str,
    entity_type: Optional[str] = None
) -> EntityIdentity:
    """
    Create a new entity identity with stable ID.
    
    Args:
        project_id: Project scope for entity
        canonical_name: Primary display name (non-empty)
        entity_type: Optional entity type tag
    
    Returns:
        EntityIdentity with fresh entity_id and empty aliases
    
    Raises:
        ValueError: If canonical_name is empty or whitespace-only
    
    Example:
        >>> entity = create_identity(ProjectId("proj_01"), "张三")
        >>> entity.canonical_name
        '张三'
    """
    if not canonical_name or canonical_name.isspace():
        raise ValueError("canonical_name cannot be empty or whitespace-only")
    
    return EntityIdentity(
        entity_id=_generate_entity_id(),
        project_id=project_id,
        canonical_name=canonical_name.strip(),
        aliases=frozenset(),
        entity_type=entity_type
    )

def rename_identity(
    identity: EntityIdentity,
    new_canonical_name: str
) -> EntityIdentity:
    """
    Rename entity, preserving old name as alias.
    
    Args:
        identity: Existing entity identity
        new_canonical_name: New primary name (non-empty)
    
    Returns:
        New EntityIdentity with updated name, same entity_id
    
    Raises:
        ValueError: If new_canonical_name is empty or whitespace-only
    
    Example:
        >>> renamed = rename_identity(entity, "新名字")
        >>> renamed.entity_id == entity.entity_id
        True
        >>> "张三" in renamed.aliases  # Old name preserved
        True
    """
    if not new_canonical_name or new_canonical_name.isspace():
        raise ValueError("new_canonical_name cannot be empty or whitespace-only")
    
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=new_canonical_name.strip(),
        aliases=identity.aliases | {identity.canonical_name},
        entity_type=identity.entity_type
    )
```

**Exit Criteria**:
- create_identity generates unique IDs
- rename_identity preserves entity_id
- Old canonical_name becomes alias
- Input validation works
- All docstrings complete

**Tests** (implement in parallel):
- TC-005-001 (create valid)
- TC-005-002, TC-005-003 (create invalid)
- TC-005-004 (rename preserves ID)
- TC-005-005 (old name becomes alias)
- TC-005-006 (rename invalid)

**Why This Step**: Core operations; enables most testing scenarios.

---

### Step 6: Implement add_alias and remove_alias

**Objective**: Implement alias management operations.

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Implement `add_alias(identity, alias) -> EntityIdentity`
   - Validate alias (ValueError if empty/whitespace)
   - Return new EntityIdentity with alias added
   - Idempotent (no duplicate if alias exists)
   - Full docstring
2. Implement `remove_alias(identity, alias) -> EntityIdentity`
   - Validate alias != canonical_name (ValueError if match)
   - Return new EntityIdentity with alias removed
   - Idempotent (no error if alias doesn't exist)
   - Full docstring

**Expected Additions**:
```python
def add_alias(
    identity: EntityIdentity,
    alias: str
) -> EntityIdentity:
    """
    Add alias to entity.
    
    Args:
        identity: Existing entity identity
        alias: Alternative name to add
    
    Returns:
        New EntityIdentity with alias added
    
    Raises:
        ValueError: If alias is empty or whitespace-only
    """
    if not alias or alias.isspace():
        raise ValueError("alias cannot be empty or whitespace-only")
    
    normalized_alias = alias.strip()
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=identity.canonical_name,
        aliases=identity.aliases | {normalized_alias},
        entity_type=identity.entity_type
    )

def remove_alias(
    identity: EntityIdentity,
    alias: str
) -> EntityIdentity:
    """
    Remove alias from entity.
    
    Args:
        identity: Existing entity identity
        alias: Alias to remove
    
    Returns:
        New EntityIdentity with alias removed
    
    Raises:
        ValueError: If attempting to remove canonical_name
    """
    normalized_alias = alias.strip()
    if normalized_alias == identity.canonical_name:
        raise ValueError("Cannot remove canonical_name as alias")
    
    return EntityIdentity(
        entity_id=identity.entity_id,
        project_id=identity.project_id,
        canonical_name=identity.canonical_name,
        aliases=identity.aliases - {normalized_alias},
        entity_type=identity.entity_type
    )
```

**Exit Criteria**:
- Alias addition works
- Alias removal works
- Idempotency verified
- Canonical name protection works
- All docstrings complete

**Tests** (implement in parallel):
- TC-005-007, TC-005-008 (add alias)
- TC-005-009 (add empty)
- TC-005-010, TC-005-011 (remove alias)
- TC-005-012 (remove canonical name)
- TC-005-032 (aliases unique)

**Why This Step**: Completes CRUD operations on identity; enables alias resolution.

---

### Step 7: Implement resolve_alias

**Objective**: Implement core resolution logic with all result variants.

**Files Touched**:
- `src/anovel/domain/identity.py` (modify)

**Actions**:
1. Implement `resolve_alias(project_id, lookup, registry) -> ResolutionResult`
   - Validate input (INVALID_INPUT if empty/whitespace)
   - Normalize lookup string
   - Find all matching entities in project
   - Return appropriate result variant (RESOLVED, NOT_FOUND, AMBIGUOUS)
   - Deterministic (no order dependency)
   - Full docstring per contract § 12.2

**Expected Addition**:
```python
def resolve_alias(
    project_id: ProjectId,
    lookup: str,
    registry: EntityRegistry
) -> ResolutionResult:
    """
    Resolve alias to entity within project scope.
    
    Args:
        project_id: Project to search within
        lookup: Name or alias to resolve
        registry: Entity registry to query
    
    Returns:
        ResolutionResult (RESOLVED, NOT_FOUND, AMBIGUOUS, or INVALID_INPUT)
    
    Example:
        >>> result = resolve_alias(project_id, "张三", registry)
        >>> if result.status == ResolutionStatus.RESOLVED:
        ...     print(f"Found: {result.entity_id}")
    """
    # Validate input
    if not lookup or lookup.isspace():
        return InvalidInputResult(
            status=ResolutionStatus.INVALID_INPUT,
            reason="Lookup string is empty or whitespace-only"
        )
    
    # Normalize lookup
    lookup_key = normalize_for_lookup(lookup)
    
    # Find matching entities (project-scoped)
    candidates = set()
    for entity in registry.get_entities(project_id):
        # Check canonical name
        if normalize_for_lookup(entity.canonical_name) == lookup_key:
            candidates.add(entity.entity_id)
            continue
        # Check aliases
        for alias in entity.aliases:
            if normalize_for_lookup(alias) == lookup_key:
                candidates.add(entity.entity_id)
                break
    
    # Return appropriate result
    if len(candidates) == 0:
        return NotFoundResult(status=ResolutionStatus.NOT_FOUND)
    elif len(candidates) == 1:
        return ResolvedResult(
            status=ResolutionStatus.RESOLVED,
            entity_id=candidates.pop()
        )
    else:  # len(candidates) >= 2
        return AmbiguousResult(
            status=ResolutionStatus.AMBIGUOUS,
            candidates=frozenset(candidates)
        )
```

**Exit Criteria**:
- Resolution returns correct result variants
- Project isolation enforced
- Determinism verified
- Ambiguity detection works
- All docstrings complete

**Tests** (implement in parallel):
- TC-005-013 (resolve unique)
- TC-005-014 (not found)
- TC-005-015 (ambiguous)
- TC-005-016, TC-005-017, TC-005-018 (invalid input)
- TC-005-019, TC-005-020 (project isolation)
- TC-005-021, TC-005-022 (collisions)
- TC-005-027, TC-005-028, TC-005-029 (determinism)

**Why This Step**: Core resolution logic; completes functional implementation.

---

### Step 8: Create Schema and Complete Tests

**Objective**: Add JSON Schema, complete test suite, verify architecture boundaries.

**Files Touched**:
- `specs/schemas/entity-identity.schema.json` (create)
- `tests/contract/test_v2_005.py` (create/complete)
- `tests/architecture/test_dependency_boundaries.py` (modify)

**Actions**:

**8.1 JSON Schema**:
1. Create `specs/schemas/` directory if not exists
2. Create `entity-identity.schema.json` per contract § 13.1
3. Verify schema is valid JSON Schema Draft 2020-12

**8.2 Complete Contract Tests**:
1. Ensure all 38 test cases implemented (TC-005-001 through TC-005-038)
2. Add test fixtures (F1, F2, F3)
3. Add assertion helpers (H1, H2)
4. Verify all AC-005-01 through AC-005-10 covered
5. Verify all NS-1 through NS-6 covered
6. Add serialization tests (TC-005-030, TC-005-031)

**8.3 Architecture Tests**:
1. Add to `tests/architecture/test_dependency_boundaries.py`:
   ```python
   def test_v2_005_identity_no_persistence_import():
       """V2-005: domain.identity must not import persistence."""
       # Implementation per contract § 11.2
   
   def test_v2_005_identity_no_provider_import():
       """V2-005: domain.identity must not import gateway."""
       # Implementation per contract § 11.2
   ```

**8.4 Final Verification**:
1. Run full test suite: `pytest tests/contract/test_v2_005.py -v`
2. Verify 100% test pass rate
3. Run architecture tests: `pytest tests/architecture/ -k v2_005 -v`
4. Run type checker: `mypy src/anovel/domain/identity.py --strict`
5. Verify no prohibited imports

**Exit Criteria**:
- All 38+ tests implemented and passing
- JSON Schema valid and tested
- Architecture boundaries enforced
- Type checking passes
- No flaky tests (run 10x)
- 100% code coverage on domain logic

**Tests**: All remaining tests from matrix

**Why This Step**: Final verification; ensures contract fully satisfied.

---

## Dependencies Between Steps

```
Step 1 (Structure)
  ↓
Step 2 (Types) ←──────────┐
  ↓                        │
Step 3 (Helpers)           │
  ↓                        │
Step 4 (Registry)          │
  ↓                        │
Step 5 (Create/Rename) ────┤ (Tests can run in parallel)
  ↓                        │
Step 6 (Add/Remove Alias) ─┤
  ↓                        │
Step 7 (Resolve) ──────────┤
  ↓                        │
Step 8 (Schema + Tests) ───┘
```

**Critical Path**: Steps 1-7 must be sequential. Step 8 can be partially parallel (tests written alongside implementation).

---

## Verification Checklist

After each step, verify:

- [ ] Files exist and can be imported
- [ ] No syntax errors
- [ ] Type hints present and correct
- [ ] Docstrings complete
- [ ] Relevant tests pass
- [ ] No prohibited imports (run architecture tests)
- [ ] Git commit with clear message

---

## Risk Mitigation

### R1: No External Dependencies Required

**Mitigation**: UUID v4 from standard library only.

**Verification**: No external ID generation libraries needed.

### R2: Test Failures Due to Non-Determinism

**Mitigation**: Use frozenset (unordered) for candidates in Step 7.

**Verification**: Run tests 10x to detect flakiness.

### R3: Type Checking Failures

**Mitigation**: Add type hints incrementally, verify with mypy after each step.

**Verification**: `mypy --strict` must pass.

### R4: Accidental Persistence Import

**Mitigation**: Architecture tests in Step 8 catch prohibited imports.

**Verification**: Run architecture tests after Steps 5, 6, 7.

---

## Rollback Strategy

If any step fails:

1. **Review contract**: Ensure understanding of requirements
2. **Check tests**: Verify test expectations match contract
3. **Isolate issue**: Use debugger / print statements
4. **Fix incrementally**: Don't move to next step until current passes
5. **Seek clarification**: If contract ambiguous, document and raise

**Do NOT**:
- Skip tests
- Comment out failing assertions
- Proceed with known failures

---

## Final Acceptance

V2-005 implementation complete when:

✅ **All 8 steps completed**  
✅ **All tests pass (38+ test cases)**  
✅ **Architecture tests pass**  
✅ **Type checking passes (mypy --strict)**  
✅ **JSON Schema validates**  
✅ **No prohibited imports**  
✅ **Documentation complete**  
✅ **Ready for V2-006 consumption**  

---

## Post-Implementation

After V2-005 accepted:

1. **Update backlog**: Mark V2-005 status = IMPLEMENTING or CLOSED (when done)
2. **Update phase gates**: Check if G-P0 → G-P1 prerequisites met
3. **Communicate to V2-006**: EntityId available for import
4. **Archive refinement**: Move docs to appropriate location
5. **Prepare V2-006**: Begin refinement for Character domain

---

**IMPLEMENTATION PLAN READY**

Proceed with Step 1 when authorized.

---

**END OF PLAN**
