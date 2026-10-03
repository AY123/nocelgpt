# V2-005 Implementation Contract

**Document ID**: V2-005-CONTRACT  
**Version**: 1.1.0  
**Date**: 2026-10-03  
**Status**: REVISED / INDEPENDENT_REVIEW_PENDING  
**Authority**: Implementation Contract (Pending Approval)  
**Baseline**: dev_cc @ 323eaae7

---

## 1. Contract Purpose

This document is the **revised implementation contract** for V2-005. This version (1.1.0) addresses issues identified in independent review. Once approved through formal review, this contract becomes binding. Changes after approval require formal contract revision.

**Revision History**:
- v1.0.0 (2026-10-03): Initial refinement
- v1.1.0 (2026-10-03): Contract revision addressing 10 identified issues

---

## 2. Public Domain Types

### 2.1 EntityId

**Definition**:
```python
from typing import NewType

EntityId = NewType('EntityId', str)
```

**Semantics**:
- Opaque stable identifier for narrative entities
- Immutable for entity lifetime
- NOT derived from name, NOT reused after entity deletion
- Format: **UUID v4 (RFC 4122)** - frozen, no environment fallback

**Format Specification**:
- Standard: UUID version 4 (random)
- Generation: Python `uuid.uuid4()`
- String form: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
  - 36 characters including hyphens
  - Lowercase hexadecimal
  - Version digit: always `4`
  - Variant bits: `[89ab]`
- Example: `EntityId("550e8400-e29b-41d4-a716-446655440000")`

**Validation Pattern**:
```python
import re
ENTITY_ID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)

def is_valid_entity_id(s: str) -> bool:
    return bool(ENTITY_ID_PATTERN.match(s))
```

**Rationale for UUID v4**:
- Standard library support (no external dependency)
- Format stable across environments
- Collision probability negligible (2^122 space)
- Universally recognized format
- No ULID fallback (avoids format inconsistency)

**Serialization**: String (36 characters, lowercase, with hyphens)

---

### 2.2 ProjectId

**Definition**:
```python
from typing import NewType

ProjectId = NewType('ProjectId', str)
```

**Semantics**:
- Scope boundary for entity resolution
- All entity operations scoped to project
- Opaque identifier (format not specified by V2-005)

**Validation Rules**:
- Non-empty after stripping whitespace
- No control characters (U+0000 to U+001F, U+007F)
- Length ≥ 1 after strip()

**Validation Function**:
```python
def validate_project_id(s: str) -> ProjectId:
    """
    Validate and construct ProjectId.
    
    Args:
        s: Raw project ID string
    
    Returns:
        ProjectId (validated)
    
    Raises:
        ValueError: If s is invalid
    """
    if not s or not s.strip():
        raise ValueError("ProjectId cannot be empty or whitespace-only")
    
    stripped = s.strip()
    
    # Check for control characters
    if any(ord(c) < 0x20 or c == '\x7f' for c in stripped):
        raise ValueError("ProjectId cannot contain control characters")
    
    return ProjectId(stripped)
```

**Usage**:
- **create_identity**: Accepts `ProjectId` type (caller must validate)
- **Deserialization**: MUST validate via `validate_project_id()`
- **EntityRegistry**: Assumes input already validated (no re-validation)

**Serialization**: String (trimmed, no control characters)

**Example**: `ProjectId("urban_business_01")`

---

### 2.3 EntityIdentity

**Definition**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class EntityIdentity:
    """Immutable identity aggregate for narrative entities."""
    
    entity_id: EntityId
    project_id: ProjectId
    canonical_name: str
    aliases: frozenset[str]
    entity_type: Optional[str] = None
```

**Semantics**:

**entity_id**: Stable unique identifier (never changes)

**project_id**: Project scope (never changes after creation)

**canonical_name**: Current primary name (MAY change via rename)

**aliases**: Set of alternative names (MAY change via add/remove)
- Does NOT include canonical_name (stored separately)
- Unordered set (no priority)
- Each alias unique within aliases set

**entity_type**: Optional entity type tag
- Examples: "CHARACTER", "LOCATION", "FACTION"
- None = type not specified
- String, not enum (allows genre extensions)

**Invariants**:
1. entity_id never changes for same entity
2. project_id never changes for same entity
3. canonical_name always non-empty
4. aliases never contains empty strings
5. canonical_name MAY exist as alias (after rename)

**Immutability Guarantees**:
1. `@dataclass(frozen=True)` prevents field reassignment
2. `aliases` is `frozenset[str]` (immutable collection)
3. **Input Defense**: Operations accepting collection input convert to `frozenset`
   - If input is already `frozenset[str]`, safe to reuse (immutable)
   - If input is mutable (`set`, `list`), convert to `frozenset`
4. **Output Isolation**: 
   - Returned `EntityIdentity` is new object (frozen guarantees)
   - `entity.aliases` is `frozenset`, external code cannot modify

**Isolation Test Requirements**:
- External modification of input collection MUST NOT affect created entity
- External holding reference to `entity.aliases` MUST NOT be able to modify internal state
- Operations return new objects, never mutate input

**JSON Schema Reference**: `specs/schemas/entity-identity.schema.json`

---

### 2.4 ResolutionStatus

**Definition**:
```python
from enum import Enum

class ResolutionStatus(Enum):
    """Status of alias resolution attempt."""
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    INVALID_INPUT = "invalid_input"
```

**Semantics**:

**RESOLVED**: Exactly one entity matched

**NOT_FOUND**: Zero entities matched

**AMBIGUOUS**: Multiple entities matched (≥2)

**INVALID_INPUT**: Query invalid (empty, whitespace-only, None)

---

### 2.5 ResolutionResult

**Definition**:
```python
from dataclasses import dataclass
from typing import Literal, Union

@dataclass(frozen=True)
class ResolvedResult:
    """Resolution found exactly one entity."""
    status: Literal[ResolutionStatus.RESOLVED]
    entity_id: EntityId

@dataclass(frozen=True)
class NotFoundResult:
    """Resolution found no matching entities."""
    status: Literal[ResolutionStatus.NOT_FOUND]

@dataclass(frozen=True)
class AmbiguousResult:
    """Resolution found multiple matching entities."""
    status: Literal[ResolutionStatus.AMBIGUOUS]
    candidates: frozenset[EntityId]  # Unordered, ≥2 elements

@dataclass(frozen=True)
class InvalidInputResult:
    """Resolution input was invalid."""
    status: Literal[ResolutionStatus.INVALID_INPUT]
    reason: str

ResolutionResult = Union[
    ResolvedResult,
    NotFoundResult,
    AmbiguousResult,
    InvalidInputResult
]
```

**Semantics**:
- Discriminated union (type-safe pattern matching)
- Immutable (frozen=True)
- AmbiguousResult.candidates is **unordered** (no implicit priority)
- InvalidInputResult.reason provides human-readable explanation

---

## 3. Public Operations

### 3.1 create_identity

**Signature**:
```python
def create_identity(
    project_id: ProjectId,
    canonical_name: str,
    entity_type: Optional[str] = None
) -> EntityIdentity:
    ...
```

**Preconditions**:
- `project_id` is non-empty string
- `canonical_name` is non-empty, non-whitespace string
- `entity_type` is None or non-empty string

**Postconditions**:
- Returns new EntityIdentity with fresh entity_id
- entity_id is unique (never previously issued)
- aliases = frozenset() (empty)
- canonical_name stored after normalization

**Side Effects**: None (pure function, in-memory only)

**Exceptions**:
- `ValueError` if canonical_name is empty or whitespace-only
- `ValueError` if project_id is empty

**Determinism**: 
- entity_id generation is non-deterministic (ULID includes timestamp)
- Same input MAY produce different entity_id
- This is acceptable; identity is entity_id, not input

---

### 3.2 rename_identity

**Signature**:
```python
def rename_identity(
    identity: EntityIdentity,
    new_canonical_name: str
) -> EntityIdentity:
    ...
```

**Preconditions**:
- `identity` exists
- `new_canonical_name` is non-empty, non-whitespace string

**Postconditions**:
- Returns new EntityIdentity (frozen, immutable)
- entity_id UNCHANGED
- project_id UNCHANGED
- canonical_name = new_canonical_name
- Old canonical_name ADDED to aliases (automatic preservation)
- If old canonical_name already in aliases, no duplicate

**Side Effects**: None (returns new immutable object)

**Exceptions**:
- `ValueError` if new_canonical_name is empty or whitespace-only

**Exception Safety**:
- If `ValueError` raised (input validation failure), no side effects
- Original `identity` object unchanged (frozen guarantees)
- Caller catching exception can continue using original `identity`

**Example - Exception Safety**:
```python
original = create_identity(proj, "张三")
try:
    renamed = rename_identity(original, "")  # Empty name
except ValueError:
    pass  # original still valid

assert original.canonical_name == "张三"  # Unchanged
```

**Invariant Check**:
```python
original = create_identity(proj, "老名字")
renamed = rename_identity(original, "新名字")

assert renamed.entity_id == original.entity_id  # MUST hold
assert renamed.canonical_name == "新名字"
assert "老名字" in renamed.aliases  # Automatic alias
```

---

### 3.3 add_alias

**Signature**:
```python
def add_alias(
    identity: EntityIdentity,
    alias: str
) -> EntityIdentity:
    ...
```

**Preconditions**:
- `identity` exists
- `alias` is non-empty, non-whitespace string

**Postconditions**:
- Returns new EntityIdentity
- entity_id, project_id, canonical_name UNCHANGED
- `alias` added to aliases (after normalization)
- If alias already in aliases, no change (idempotent)

**Side Effects**: None

**Exceptions**:
- `ValueError` if alias is empty or whitespace-only

**Note**: This operation does NOT check for cross-entity conflicts. Conflict detection happens at resolution time or via separate validation.

---

### 3.4 remove_alias

**Signature**:
```python
def remove_alias(
    identity: EntityIdentity,
    alias: str
) -> EntityIdentity:
    ...
```

**Preconditions**:
- `identity` exists
- `alias` is string

**Postconditions**:
- Returns new EntityIdentity
- entity_id, project_id, canonical_name UNCHANGED
- `alias` removed from aliases (after normalization)
- If alias not in aliases, no change (idempotent)

**Side Effects**: None

**Exceptions**:
- `ValueError` if alias == canonical_name (cannot remove canonical name)

**Safety**:
```python
identity = create_identity(proj, "张三")
remove_alias(identity, "张三")  # Raises ValueError
```

---

### 3.5 resolve_alias

**Signature**:
```python
def resolve_alias(
    project_id: ProjectId,
    lookup: str,
    registry: EntityRegistry  # In-memory registry for V2-005
) -> ResolutionResult:
    ...
```

**Preconditions**:
- `project_id` valid
- `lookup` is string (may be empty, handled as INVALID_INPUT)
- `registry` contains current entity state

**Postconditions**:
- Returns ResolutionResult (one of four variants)
- Result is deterministic for same (project_id, lookup, registry state)
- Does NOT modify registry

**Behavior**:

**Input validation**:
```python
if not lookup or lookup.isspace():
    return InvalidInputResult(
        status=ResolutionStatus.INVALID_INPUT,
        reason="Lookup string is empty or whitespace-only"
    )
```

**Normalization**:
```python
lookup_key = normalize_for_lookup(lookup)
```

**Matching** (within project_id scope):
```python
candidates = {
    entity.entity_id
    for entity in registry.get_entities(project_id)
    if lookup_key in {
        normalize_for_lookup(entity.canonical_name),
        *{normalize_for_lookup(a) for a in entity.aliases}
    }
}
```

**Matching Semantics** (§ 3.5.1):

**Unified Candidate Set**:
- Canonical name and aliases enter the same candidate pool
- NO implicit priority: canonical name is not preferred over aliases
- Each entity checked: if ANY name (canonical or alias) matches, entity enters candidates
- Same entity with multiple matching names counts once (de-duplicated by entity_id)

**Example - No Priority**:
```python
Entity E1: canonical="林凡", aliases=[]
Entity E2: canonical="另一个", aliases=["林凡"]

resolve(project, "林凡", registry)
→ AMBIGUOUS({E1, E2})  # Both match, no priority
```

**Example - Single Entity Multiple Matches** (§ 3.5.2):
```python
Entity E3: canonical="John", aliases=["JOHN", "john doe"]

resolve(project, "john", registry)  # Matches canonical AND alias
→ RESOLVED(E3)  # One entity, not multiple candidates
```

**De-duplication**: By `entity_id` (set membership)

**Result**:
```python
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

**Determinism Guarantee**:
- No iteration order dependency (uses set)
- No database row order dependency (in-memory)
- No random selection
- Same input + state → same output (bitwise identical)

**Side Effects**: None (read-only)

**Exceptions**: None (all error cases return result variants)

---

### 3.6 normalize_for_lookup

**Signature**:
```python
def normalize_for_lookup(s: str) -> str:
    """Normalize string for case-insensitive lookup."""
    ...
```

**Behavior**:

1. Strip leading/trailing whitespace:
   - ASCII space (U+0020)
   - Full-width space (U+3000)

2. Collapse internal consecutive spaces to single space

3. ASCII lowercase:
   - If `s.isascii()`: return `s.lower()`
   - Else: return `s` unchanged (preserve Chinese case)

**Examples**:
```python
normalize_for_lookup("  张三  ")        # → "张三"
normalize_for_lookup("Zhang  San")     # → "zhang san"
normalize_for_lookup("SMITH")          # → "smith"
normalize_for_lookup("李　明")         # → "李明" (full-width space removed)
```

**Rationale**:
- Chinese: case-sensitive (no case in Chinese)
- ASCII: case-insensitive (common name variation)
- Whitespace: normalized (user input variation)

**Not Implemented** (deferred):
- Unicode NFKC/NFKD
- CJK variant normalization
- Homoglyph detection
- Pinyin conversion

---

## 4. EntityRegistry (In-Memory)

**Definition**:
```python
class EntityRegistry:
    """In-memory registry for V2-005 contract tests."""
    
    def add_entity(self, entity: EntityIdentity) -> None:
        """Add entity to registry."""
        ...
    
    def get_entity(self, entity_id: EntityId) -> Optional[EntityIdentity]:
        """Retrieve entity by ID."""
        ...
    
    def get_entities(self, project_id: ProjectId) -> Iterable[EntityIdentity]:
        """Retrieve all entities in project."""
        ...
```

**Semantics**:
- Simple in-memory storage for V2-005
- NOT persistent (persistence is V2-009)
- NOT thread-safe (concurrency is V2-009)
- Used by contract tests

---

### 4.1 Uniqueness Constraints

**Entity ID Uniqueness**:
```python
def add_entity(self, entity: EntityIdentity) -> None:
    """
    Add entity to registry with uniqueness enforcement.
    
    Uniqueness Constraint:
    - entity_id MUST be unique across registry
    - Duplicate entity_id with different content → ValueError
    
    Idempotency:
    - Same entity_id + same content (by value equality) → no-op
    - Same entity_id + different content → ValueError
    
    NOT Constrained:
    - canonical_name MAY be duplicate (across entities)
    - Aliases MAY be duplicate (across entities) → AMBIGUOUS at resolution
    """
    if entity.entity_id in self._entities:
        existing = self._entities[entity.entity_id]
        if existing != entity:  # Value equality
            raise ValueError(
                f"Entity ID {entity.entity_id} already registered "
                f"with different content"
            )
        # Same content → idempotent, no-op
        return
    
    # Normal registration
    self._entities[entity.entity_id] = entity
    self._by_project.setdefault(entity.project_id, set()).add(entity.entity_id)
```

**Rationale**:
- Entity ID is identity, MUST be unique
- Idempotency supports retry scenarios
- Distinguish "duplicate name" (allowed) from "duplicate ID" (forbidden)

---

### 4.2 Update Semantics

**EntityRegistry does NOT provide update operations.**

**Rename workflow** (external to registry):
1. Call `rename_identity(old_entity, new_name)` → `new_entity`
2. Update registry (application logic):
   - Option A (overwrite): `registry._entities[id] = new_entity`
   - Option B (remove+add): Remove old, add new

**V2-005 Scope**:
- Registry is test fixture, NOT production component
- Update semantics undefined (implementation choice)
- Production (V2-009) will define transactional boundaries

**Implementation Note**: 
- Likely a dict mapping entity_id → EntityIdentity
- Plus index by project_id for efficient get_entities

---

## 5. Preconditions

### 5.1 Input Validation

**All operations** MUST validate:
- Strings are not None
- Required strings are non-empty after strip()
- IDs conform to expected format

**Invalid inputs** trigger:
- `ValueError` for operations (create, rename, add/remove alias)
- `InvalidInputResult` for resolution (resolve_alias)

### 5.2 Entity Existence

**rename_identity, add_alias, remove_alias**:
- Operate on existing EntityIdentity object (passed by value)
- No "entity not found" error possible (entity IS the parameter)

**resolve_alias**:
- Queries registry; returns NOT_FOUND if no match

---

## 6. Postconditions

### 6.1 Identity Stability

After ANY operation on entity with ID `e`:
```python
assert resulting_identity.entity_id == e
```

**Operations that preserve ID**:
- rename_identity
- add_alias
- remove_alias

### 6.2 Project Isolation

After resolution in project `p`:
```python
result = resolve_alias(p, name, registry)
if result.status == ResolutionStatus.RESOLVED:
    entity = registry.get_entity(result.entity_id)
    assert entity.project_id == p
```

No cross-project leakage allowed.

### 6.3 Rename Preservation

After rename:
```python
original = create_identity(proj, "old_name")
renamed = rename_identity(original, "new_name")

assert "old_name" in renamed.aliases
```

Old canonical name automatically becomes alias.

### 6.4 Ambiguity Explicit

If multiple entities match:
```python
result = resolve_alias(proj, "ambiguous", registry)
if len(matching_entities) >= 2:
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert isinstance(result.candidates, frozenset)
    assert len(result.candidates) >= 2
```

NO arbitrary selection (no `candidates[0]`).

---

## 7. Invariants

### INV-1: Stable Identity
```
∀ entity e, ∀ operations O:
  e.entity_id(t0) = e.entity_id(t1)
```

Entity ID never changes.

### INV-2: Project Isolation
```
∀ project p1, p2 where p1 ≠ p2, ∀ name n:
  resolve(n, p1) ∩ resolve(n, p2) = ∅
```

Resolution in one project never returns entity from another.

### INV-3: Alias is Not Identity
```
alias ∈ String
entity_id ∈ EntityId
String ≠ EntityId (types distinct)
```

Alias is lookup key, not identity.

### INV-4: Explicit Ambiguity
```
|candidates| > 1 ⟹ Result = AMBIGUOUS
Result ≠ RESOLVED(first(candidates))
```

Multiple matches always return AMBIGUOUS.

### INV-5: Determinism
```
∀ (project, lookup, state σ):
  resolve(lookup, project, σ) = resolve(lookup, project, σ)
```

Deterministic resolution (no randomness, no order dependency).

### INV-6: Rename Preservation
```
rename(e, old, new) ⟹ old ∈ e.aliases
```

Old canonical name preserved as alias.

### INV-7: Canonical Name Always Valid
```
∀ entity e:
  resolve(e.canonical_name, e.project_id, registry) 
    ∈ {RESOLVED(e.entity_id), AMBIGUOUS(...)}
```

Canonical name always resolves (unless collision).

### INV-8: Immutability
```
All public types are frozen=True
Operations return NEW objects, not mutate existing
```

Value semantics throughout.

---

## 8. Error Semantics

### 8.1 ValueError (Operations)

**Raised by**: create_identity, rename_identity, add_alias, remove_alias

**Conditions**:
- Empty or whitespace-only name/alias
- Attempting to remove canonical_name as alias
- Invalid project_id

**NOT raised for**:
- Entity not found (operations take entity as parameter)
- Ambiguity (not checked at operation level)

### 8.2 InvalidInputResult (Resolution)

**Returned by**: resolve_alias

**Conditions**:
- lookup is None, empty, or whitespace-only

**Reason field**: Human-readable explanation

### 8.3 No Exceptions for Business Logic

**Design principle**: Expected outcomes (not found, ambiguous) are **result variants**, not exceptions.

**Rationale**: 
- Type-safe pattern matching
- Explicit handling required
- Avoids "exception as control flow"

---

## 9. Serialization Contract

### 9.1 JSON Representation

**EntityIdentity**:
```json
{
  "entity_id": "01HQZQZQZQZQZQZQZQZQZQ",
  "project_id": "proj_01",
  "canonical_name": "张三",
  "aliases": ["老张", "张总"],
  "entity_type": "CHARACTER"
}
```

**Field order**: Not specified (JSON object)

**Aliases**: Array (order not significant)

**Optional fields**: `entity_type` may be null or omitted

### 9.2 Schema Validation

**JSON Schema**: `specs/schemas/entity-identity.schema.json`

**Draft**: JSON Schema Draft 2020-12

**Validation Requirements**:
- entity_id: string, minLength 1
- project_id: string, minLength 1
- canonical_name: string, minLength 1
- aliases: array of strings, uniqueItems true
- entity_type: string or null
- additionalProperties: false (closed schema)

### 9.3 Round-Trip Guarantee

```python
identity = create_identity(...)
json_str = serialize_to_json(identity)
restored = deserialize_from_json(json_str)

assert identity == restored  # Bitwise equality
```

### 9.4 Normalization Storage

**Design decision**: Store normalized form or raw?

**Recommendation**: Store BOTH:
```json
{
  "entity_id": "...",
  "canonical_name": "Zhang San",
  "canonical_name_normalized": "zhang san",
  "aliases": [
    {"raw": "  John  ", "normalized": "john"},
    {"raw": "约翰", "normalized": "约翰"}
  ]
}
```

**Alternative** (simpler): Store only normalized, lose raw form.

**Contract**: V2-005 implementation chooses; contract tests verify round-trip.

---

## 10. Determinism Contract

### 10.1 Resolution Determinism

**Scope**: Applies to `resolve_alias()` operation only.

**Given**:
- Same `project_id`
- Same `lookup` string
- Same `registry` state (same set of entities with same content)

**Then**:
```python
result1 = resolve_alias(project_id, lookup, registry)
result2 = resolve_alias(project_id, lookup, registry)

# Result status must be identical
assert result1.status == result2.status

# If RESOLVED, entity_id must be identical
if result1.status == ResolutionStatus.RESOLVED:
    assert result1.entity_id == result2.entity_id

# If AMBIGUOUS, candidate sets must be equal (as sets, unordered)
if result1.status == ResolutionStatus.AMBIGUOUS:
    assert result1.candidates == result2.candidates  # frozenset equality

# Results equal by value (not requiring object identity)
assert result1 == result2
```

**Clarification**:
- "Same registry state" means same entities by value equality
- Entity registration order does NOT affect resolution
- Result objects compared by value, not object identity

---

### 10.2 No Order Dependency

**Prohibited**:
- `candidates[0]` selection (arbitrary first element)
- Database row order dependency
- Hash map iteration order dependency
- List ordering of candidates

**Enforcement**:
- Use unordered collections: `frozenset`, `set`
- Never convert candidates to `list` for selection
- De-duplicate by `entity_id` using set operations

**Test Requirement**:
- Register same entities in different orders
- Verify resolution result unchanged (status + candidates as set)

---

### 10.3 Candidate Set Ordering

**AmbiguousResult.candidates**:
- Type: `frozenset[EntityId]` (unordered, immutable)
- NO implicit ordering (registration order, alphabetical, lexicographic)
- Comparison: set equality, not sequence equality

**Prohibited**:
```python
# WRONG: ordering candidates
candidates_list = sorted(candidates)
return candidates_list[0]

# WRONG: relying on iteration order
for candidate in candidates:
    return candidate  # First in arbitrary order
```

**Correct**:
```python
# Correct: return unordered set
return AmbiguousResult(
    status=ResolutionStatus.AMBIGUOUS,
    candidates=frozenset(candidates)  # Unordered
)
```

---

### 10.4 Generation Non-Determinism

**Scope**: Applies to `create_identity()` only.

**entity_id Generation**:
- Non-deterministic (UUID v4 uses random number generator)
- Same `(project_id, canonical_name, entity_type)` MAY produce different `entity_id`
- This is acceptable and expected

**Rationale**:
- UUID v4 designed for uniqueness, not reproducibility
- Identity is `entity_id` itself, not generation parameters
- Resolution does NOT depend on generation order or timing

**Does NOT Affect**:
- Resolution determinism (§ 10.1)
- Matching logic (based on names, not IDs)
- Test repeatability (test uses fixed entity_id values)

---

### 10.5 No External Randomness

**Prohibited in Resolution**:
- `random.choice(candidates)` selection
- LLM-based entity selection
- Similarity ranking with non-deterministic scoring
- Time-based selection (first registered, most recent)

**Allowed**:
- `entity_id` generation randomness (§ 10.4)
- Test fixture randomness (outside contract)

---

### 10.6 Test Verification

**Required Tests**:
1. **Same Input Determinism**: Call `resolve_alias()` multiple times, verify identical results
2. **Registration Order Independence**: Register entities in different orders, verify same resolution
3. **Candidate Set Equality**: AMBIGUOUS results compared as sets, not sequences
4. **No Arbitrary Selection**: Multiple entities matching never returns arbitrary single entity

---

## 11. Test Contract Requirements

### 11.1 Minimum Test Coverage

**File**: `tests/contract/test_v2_005.py`

**Required test functions** (naming exact):

```python
def test_create_identity_generates_stable_id(): ...
def test_create_identity_empty_name_raises(): ...

def test_rename_preserves_entity_id(): ...
def test_rename_old_name_becomes_alias(): ...
def test_rename_empty_name_raises(): ...

def test_add_alias_adds_to_set(): ...
def test_add_alias_idempotent(): ...
def test_add_alias_empty_raises(): ...

def test_remove_alias_removes_from_set(): ...
def test_remove_alias_idempotent(): ...
def test_remove_alias_canonical_name_raises(): ...

def test_resolve_unique_alias_returns_resolved(): ...
def test_resolve_not_found_returns_not_found(): ...
def test_resolve_ambiguous_returns_ambiguous(): ...
def test_resolve_empty_string_returns_invalid(): ...
def test_resolve_whitespace_only_returns_invalid(): ...

def test_project_isolation(): ...
def test_same_name_different_projects(): ...

def test_normalization_whitespace(): ...
def test_normalization_ascii_case_insensitive(): ...
def test_normalization_chinese_case_sensitive(): ...

def test_serialization_round_trip(): ...
def test_json_schema_validation(): ...

def test_deterministic_resolution(): ...
def test_ambiguous_result_unordered(): ...
```

**Minimum**: 25 test cases

**Test Catalog**: Update `plan/machine/test-catalog.yaml` with AT-V2-005 reference.

### 11.2 Architecture Test

**File**: `tests/architecture/test_dependency_boundaries.py`

**Add**:
```python
def test_v2_005_identity_no_persistence_import():
    """V2-005: domain.identity must not import persistence."""
    source = get_module_source("anovel.domain.identity")
    forbidden = ["sqlalchemy", "psycopg", "alembic"]
    for f in forbidden:
        assert f not in source, f"identity.py must not import {f}"

def test_v2_005_identity_no_provider_import():
    """V2-005: domain.identity must not import gateway."""
    source = get_module_source("anovel.domain.identity")
    forbidden = ["openai", "anthropic", "anovel.gateway"]
    for f in forbidden:
        assert f not in source, f"identity.py must not import {f}"
```

### 11.3 Negative Scenario Tests

**Required**:
- NS-1: Cross-project leakage
- NS-2: Random selection on ambiguity
- NS-3: Database row order dependency (mock with different orderings)
- NS-4: Implicit rename creates new entity
- NS-5: Alias overwrites silently
- NS-6: Name as identity

---

## 12. Documentation Contract

### 12.1 Module Docstring

**`src/anovel/domain/identity.py`**:

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
```

### 12.2 Function Docstrings

**All public functions** MUST have:
- One-line summary
- Args section
- Returns section
- Raises section (if applicable)
- Example usage

**Example**:
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
        >>> entity = create_identity(
        ...     ProjectId("proj_01"),
        ...     "张三",
        ...     entity_type="CHARACTER"
        ... )
        >>> entity.canonical_name
        '张三'
    """
```

### 12.3 Type Hints

**Required**: 100% type hint coverage for public API.

**Tools**: mypy --strict (or equivalent)

---

## 13. Schema Contract

### 13.1 entity-identity.schema.json

**Location**: `specs/schemas/entity-identity.schema.json`

**Content**:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://anovel.dev/schemas/entity-identity.schema.json",
  "title": "EntityIdentity",
  "description": "Stable identity for narrative entities",
  "type": "object",
  "required": ["entity_id", "project_id", "canonical_name"],
  "properties": {
    "entity_id": {
      "type": "string",
      "minLength": 1,
      "description": "Stable unique identifier (ULID format)"
    },
    "project_id": {
      "type": "string",
      "minLength": 1,
      "description": "Project scope identifier"
    },
    "canonical_name": {
      "type": "string",
      "minLength": 1,
      "description": "Primary display name"
    },
    "aliases": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true,
      "default": [],
      "description": "Alternative names for lookup"
    },
    "entity_type": {
      "type": ["string", "null"],
      "description": "Optional entity type tag (e.g., CHARACTER, LOCATION)"
    }
  },
  "additionalProperties": false
}
```

**Validation**: Contract tests MUST validate sample JSON against this schema.

---

## 14. Implementation Notes

### 14.1 ID Generation

**UUID v4** (standard):
```python
import uuid

def _generate_entity_id() -> EntityId:
    """Generate unique entity ID using UUID v4."""
    return EntityId(str(uuid.uuid4()))
```

**No Fallback**: UUID v4 only, no ULID or alternative formats.

**Rationale**:
- Standard library support
- Format stability
- No external dependencies

### 14.2 Registry Implementation

**Suggested**:
```python
class EntityRegistry:
    def __init__(self):
        self._entities: dict[EntityId, EntityIdentity] = {}
        self._by_project: dict[ProjectId, set[EntityId]] = {}
    
    def add_entity(self, entity: EntityIdentity) -> None:
        self._entities[entity.entity_id] = entity
        self._by_project.setdefault(entity.project_id, set()).add(entity.entity_id)
    
    def get_entity(self, entity_id: EntityId) -> Optional[EntityIdentity]:
        return self._entities.get(entity_id)
    
    def get_entities(self, project_id: ProjectId) -> Iterable[EntityIdentity]:
        entity_ids = self._by_project.get(project_id, set())
        return [self._entities[eid] for eid in entity_ids]
```

**Contract**: Registry interface satisfied. Internal implementation flexible.

### 14.3 Frozen Dataclasses

**All domain types** use `@dataclass(frozen=True)`.

**Rationale**:
- Immutability guaranteed
- Hash-able (can use as dict keys, in sets)
- Thread-safe (no mutation)
- Value semantics

**Operations** return NEW objects:
```python
def rename_identity(identity: EntityIdentity, new_name: str) -> EntityIdentity:
    return EntityIdentity(
        entity_id=identity.entity_id,  # Same ID
        project_id=identity.project_id,  # Same project
        canonical_name=new_name,  # New name
        aliases=identity.aliases | {identity.canonical_name},  # Add old name
        entity_type=identity.entity_type
    )
```

---

## 15. Anti-Patterns (Prohibited)

### 15.1 Mutable Domain Objects
```python
# WRONG
class EntityIdentity:
    def rename(self, new_name):
        self.canonical_name = new_name  # Mutation!
```

**Correct**: Return new immutable object.

### 15.2 Name as Identity
```python
# WRONG
def get_entity_by_name(name: str) -> Entity:
    return db.query(Entity).filter_by(name=name).first()
```

**Correct**: Use entity_id for identity, name for lookup.

### 15.3 Implicit Ambiguity Resolution
```python
# WRONG
def resolve_alias(name: str) -> EntityId:
    candidates = find_all(name)
    return candidates[0]  # Arbitrary choice!
```

**Correct**: Return AMBIGUOUS result.

### 15.4 Cross-Project Resolution
```python
# WRONG
def resolve_alias(name: str) -> EntityId:
    # Searches ALL projects
    return global_search(name)
```

**Correct**: Always scoped to project_id.

### 15.5 LLM-Based Resolution
```python
# WRONG
def resolve_alias(name: str) -> EntityId:
    return llm.ask("Which entity is this?", name)
```

**Correct**: Deterministic string matching only.

### 15.6 Persistence in Domain Layer
```python
# WRONG
def create_identity(...) -> EntityIdentity:
    entity = EntityIdentity(...)
    db.session.add(entity)  # Persistence!
    db.session.commit()
    return entity
```

**Correct**: Domain operations are pure; persistence is separate (V2-009).

---

## 16. Future-Proofing

### 16.1 Extensibility Points

**entity_type**: String (not enum) allows genre extensions without core changes.

**EntityIdentity**: Can add optional fields in future (backward compatible).

**ResolutionResult**: Can add new variant types (discriminated union extends).

### 16.2 Migration Path to Persistence

**V2-009** will consume V2-005 types:

```python
# V2-009 (future)
class EntityRepository:
    def save(self, identity: EntityIdentity) -> None:
        # Persist to database
        ...
    
    def load(self, entity_id: EntityId) -> Optional[EntityIdentity]:
        # Load from database, return V2-005 domain type
        ...
```

**V2-005 types remain unchanged**. Repository adapts.

### 16.3 Event Sourcing (Future)

**V2-009** may add event types:

```python
# Future events (not V2-005)
@dataclass
class EntityCreated:
    entity_id: EntityId
    canonical_name: str
    ...

@dataclass
class EntityRenamed:
    entity_id: EntityId
    old_name: str
    new_name: str
    ...
```

**V2-005 operations** become event producers. Types unchanged.

---

## 17. Acceptance Checklist

Implementation complete when ALL checked:

### Code
- [ ] `src/anovel/domain/__init__.py` exists
- [ ] `src/anovel/domain/identity.py` implemented
- [ ] All public types defined (EntityId, ProjectId, EntityIdentity, ResolutionResult)
- [ ] All public operations implemented (create, rename, add/remove alias, resolve)
- [ ] normalize_for_lookup implemented per spec
- [ ] EntityRegistry implemented (in-memory)
- [ ] 100% type hints on public API
- [ ] Module and function docstrings complete

### Schema
- [ ] `specs/schemas/entity-identity.schema.json` exists
- [ ] Schema validates against JSON Schema Draft 2020-12
- [ ] Schema validation tested

### Tests
- [ ] `tests/contract/test_v2_005.py` exists
- [ ] All 25+ required tests implemented
- [ ] All AC-005-01 through AC-005-10 covered
- [ ] All NS-1 through NS-6 covered
- [ ] Architecture boundary tests added
- [ ] All tests pass

### Architecture
- [ ] No imports: sqlalchemy, psycopg, alembic, openai, anthropic, anovel.gateway
- [ ] Architecture tests pass

### Documentation
- [ ] Implementation contract reviewed
- [ ] All docstrings complete
- [ ] Type hints 100%

### Validation
- [ ] mypy --strict passes (or equivalent)
- [ ] All invariants tested
- [ ] Determinism verified
- [ ] Serialization round-trip verified

### Integration
- [ ] V2-006 can import and use EntityId
- [ ] Ready for downstream consumption

---

## 18. Non-Implementation Boundaries

V2-005 does **NOT** implement:

❌ Database tables / migrations (V2-009)  
❌ SQLAlchemy models (V2-009)  
❌ Repository pattern (V2-009)  
❌ Transaction management (V2-010)  
❌ Authorization (V2-010)  
❌ Character attributes (V2-006)  
❌ Relationship data (V2-006)  
❌ Knowledge state (V2-006)  
❌ Event sourcing (V2-009)  
❌ LLM integration (V2-019)  
❌ Genre extensions (P3)  

**Boundary enforcement**: Architecture tests verify no prohibited imports.

---

## 19. Summary

### What V2-005 Implements

**Types** (8):
- EntityId, ProjectId (opaque IDs)
- EntityIdentity (aggregate)
- ResolutionStatus (enum)
- ResolvedResult, NotFoundResult, AmbiguousResult, InvalidInputResult (discriminated union)

**Operations** (6):
- create_identity
- rename_identity
- add_alias
- remove_alias
- resolve_alias
- normalize_for_lookup

**Data Structures** (1):
- EntityRegistry (in-memory, for tests)

**Schemas** (1):
- entity-identity.schema.json

**Tests** (25+):
- Contract tests (all acceptance criteria + negative scenarios)
- Architecture tests (boundary enforcement)

### Contract Guarantees

✅ Stable entity_id across rename  
✅ Project isolation (no cross-contamination)  
✅ Explicit ambiguity (no random selection)  
✅ Deterministic resolution  
✅ Immutable domain objects  
✅ Type-safe result handling  
✅ Minimal normalization (whitespace + ASCII case)  

### Exit Criteria

Implementation complete when:
1. All code implemented and documented
2. All tests pass
3. Architecture boundaries enforced
4. Schema validated
5. Ready for V2-006 consumption

---

**CONTRACT FROZEN**

This contract is binding once approved. Implementation must follow exactly.

---

**END OF CONTRACT**
