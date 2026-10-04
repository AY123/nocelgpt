# V2-005 Task Refinement

**Document ID**: V2-005-REFINEMENT  
**Version**: 1.1.0  
**Date**: 2026-10-03  
**Status**: REVISED / INDEPENDENT_REVIEW_PENDING  
**Authority**: Task Implementation Contract Input (Pending Approval)  
**Baseline**: dev_cc @ 323eaae7

---

## 1. Goal

Establish stable entity identity and project-scoped alias resolution for ANovelOS V2 Narrative Kernel.

**Success means**: From this moment forward, no narrative capability can depend on name-based entity guessing.

---

## 2. Problem Statement

Without stable entity identity:
- Rename creates duplicate entities
- Same name in different projects causes cross-contamination
- Alias collision has no explicit resolution
- RAG/LLM similarity becomes accidental identity oracle
- Database auto-increment IDs become semantic identity
- "林凡" in Project A accidentally resolves to entity from Project B

**V1 Lessons** (per historical forensic analysis):
- Character drift from name-based resolution
- No distinction between "not found" and "ambiguous"
- Implicit "first match" semantics

**Current Risk** if V2-005 fails:
- V2-006 (Character) cannot distinguish rename from new character
- V2-008 (NarrativeDelta) cannot reference stable entities
- V2-009 (Canon persistence) stores unreliable identifiers
- Entire narrative kernel collapses to string matching

---

## 3. In Scope

### 3.1 Core Types

**EntityId**
- Opaque, stable, immutable identifier
- NOT derived from name
- Serializable, comparable
- Schema-validatable

**ProjectId**
- Scope boundary for entity resolution
- Prevents cross-project contamination
- Serializable, comparable

**EntityIdentity** (aggregate)
- entity_id
- project_id
- canonical_name
- aliases (collection)
- Optional: entity_type (if authority requires)

**Alias** (value object)
- Raw alias string
- Optional: normalized_alias (if normalization defined)
- Binding to entity_id
- Scoped to project_id

**ResolutionResult** (discriminated union)
- RESOLVED(entity_id)
- NOT_FOUND
- AMBIGUOUS(candidates)
- INVALID_INPUT

### 3.2 Operations

**Create Identity**
```
Input: project_id, canonical_name, [entity_type?]
Output: EntityIdentity
Precondition: None
Postcondition: Stable entity_id assigned
Invariant: entity_id never changes
```

**Rename Identity**
```
Input: entity_id, new_canonical_name
Output: EntityIdentity (same entity_id)
Precondition: entity exists
Postcondition: canonical_name updated, entity_id unchanged
Invariant: entity_id stable across rename
Decision: old canonical_name → alias? (see § 6)
```

**Add Alias**
```
Input: entity_id, alias_string
Output: Updated EntityIdentity
Precondition: entity exists, alias not ambiguous in project
Postcondition: alias → entity_id mapping added
```

**Remove Alias**
```
Input: entity_id, alias_string
Output: Updated EntityIdentity
Precondition: alias exists for entity
Postcondition: alias no longer resolves to entity_id
```

**Resolve Alias**
```
Input: project_id, lookup_string
Output: ResolutionResult
Precondition: project_id valid
Postcondition: deterministic result for same input + state
```

### 3.3 Acceptance Criteria (from backlog)

**AC-005-01**: Same name, different projects
```
Project A: "王林" → entity_A
Project B: "王林" → entity_B
Resolution in A MUST NOT return entity_B
```

**AC-005-02**: Stable ID after rename
```
entity_id = E1, name = "陈平安"
Rename to "陈某"
MUST: entity_id still E1
```

**AC-005-03**: Ambiguous alias detection
```
Project X:
  Entity A: alias = "小明"
  Entity B: alias = "小明"
Resolve("小明", project_id=X) → AMBIGUOUS
MUST NOT return A or B arbitrarily
```

---

## 4. Out of Scope

### 4.1 NOT in V2-005

**Persistence**
- Database tables
- SQLAlchemy models
- Repository implementations
- Migrations
→ Deferred to V2-009 (Canon Persistence)

**Complex NLP**
- Fuzzy matching
- Embedding similarity
- LLM-based resolution
- Character recognition
→ May be P10/P11 intelligence layer

**Domain Semantics**
- Character attributes
- Relationship data
- Knowledge state
- Timeline
→ V2-006/007/008

**Genre Extensions**
- Cultivation realms
- Company equity
- Faction-specific identity rules
→ P3 Genre Kernel

**Full Event Sourcing**
- Rename history tracking
- Alias change events
- Audit log
→ V2-009 may add if needed

**Multi-project Entities**
- Cross-project entity references
- Universe-scoped entities
→ Explicitly prohibited by architecture

---

### 4.2 Explicitly Deferred

**Normalization Complexity**
- Full Unicode NFKC/NFKD
- CJK variant normalization
- Homoglyph detection
- Sophisticated fuzzy matching

**Decision**: Implement **minimum sufficient** normalization only (§ 8).

**Lifecycle Management**
- Entity deletion/tombstone
- Soft delete semantics
→ V2-006 Character lifecycle

**Authorization**
- Who can create entities
- Who can rename
→ Canon Commit layer (V2-010)

---

## 5. Dependencies

### 5.1 Satisfied Dependencies

✅ **V2-001**: Repository bootstrap
- Python 3.12.14 locked
- Package structure exists
- Test infrastructure ready

### 5.2 No ADR Blockers

Per `decision-register.yaml`:
```yaml
V2-005:
  required_decisions: []
```

**Implication**: V2-005 can make local design decisions.

### 5.3 Downstream Consumers

**V2-006**: Character domain
- Will use EntityId as character identifier
- Will reference EntityIdentity

**V2-007**: Event/Timeline
- Events reference entities by EntityId

**V2-008**: NarrativeDelta
- Delta operations reference EntityId

**V2-013**: GenrePack
- Genre-specific entities use same identity primitives

---

## 6. Invariants

### INV-005-01: Stable Identity
```
∀ entity e, ∀ operations O:
  e.entity_id(t0) = e.entity_id(t1)
  where t1 = after(O)
```

Rename, alias addition, alias removal **MUST NOT** change entity_id.

### INV-005-02: Project Isolation
```
∀ project p1, p2 where p1 ≠ p2:
  resolve(name, p1) ∩ resolve(name, p2) = ∅
```

No lookup in project A can return entity from project B.

### INV-005-03: Alias is Lookup Key
```
alias ∈ KeySpace
entity_id ∈ IdentitySpace
alias ≠ entity_id
```

Alias is never used as identity; only as lookup mechanism.

### INV-005-04: Explicit Ambiguity
```
∀ lookup L, scope S:
  |candidates(L, S)| > 1 ⟹ Result = AMBIGUOUS
  Result ≠ RESOLVED(candidates[0])
  Result ≠ RESOLVED(random_choice(candidates))
```

Multiple matches **MUST** fail with AMBIGUOUS, not silently choose.

### INV-005-05: Determinism
```
∀ lookup L, state σ:
  resolve(L, σ) = resolve(L, σ)
```

Same input + same canonical state → same result.
No dependency on:
- Hash map iteration order
- Database row order  
- LLM output
- Random selection

### INV-005-06: Rename Preservation

**Design Decision Required**: Does rename automatically preserve old canonical_name as alias?

**Option A**: Automatic alias
```python
rename(entity_id="E1", old="陈平安", new="陈某")
→ entity_id=E1, canonical_name="陈某", aliases=["陈平安"]
```

**Option B**: Explicit alias
```python
rename(entity_id="E1", old="陈平安", new="陈某")
→ entity_id=E1, canonical_name="陈某", aliases=[]

add_alias(entity_id="E1", alias="陈平安")
→ entity_id=E1, canonical_name="陈某", aliases=["陈平安"]
```

**Recommendation**: **Option A** (automatic)

**Rationale**:
- Historical name remains valid lookup
- Prevents accidental "not found" after rename
- Aligns with narrative continuity expectations
- Can be removed explicitly if needed

**Invariant** (if Option A adopted):
```
rename(e, old_name, new_name) ⟹ old_name ∈ e.aliases
```

---

## 7. Acceptance Criteria (Expanded)

### AC-005-01: Project Isolation
```python
# Given
proj_a = ProjectId("proj_a")
proj_b = ProjectId("proj_b")

entity_a = create_identity(proj_a, "王林")
entity_b = create_identity(proj_b, "王林")

# When
result = resolve_alias(proj_a, "王林")

# Then
assert result == RESOLVED(entity_a.entity_id)
assert entity_b.entity_id not in result
```

### AC-005-02: Rename Stability
```python
# Given
entity = create_identity(project_id, "陈平安")
original_id = entity.entity_id

# When
renamed = rename_identity(entity.entity_id, "陈某")

# Then
assert renamed.entity_id == original_id
assert renamed.canonical_name == "陈某"
```

### AC-005-03: Old Name as Alias (if automatic)
```python
# Given
entity = create_identity(project_id, "陈平安")

# When
renamed = rename_identity(entity.entity_id, "陈某")

# Then
assert "陈平安" in renamed.aliases
result = resolve_alias(project_id, "陈平安")
assert result == RESOLVED(entity.entity_id)
```

### AC-005-04: Unique Alias Resolution
```python
# Given
entity = create_identity(project_id, "张三")
add_alias(entity.entity_id, "老魔")

# When
result = resolve_alias(project_id, "老魔")

# Then
assert result == RESOLVED(entity.entity_id)
```

### AC-005-05: Ambiguous Alias
```python
# Given
entity_a = create_identity(project_id, "角色A")
entity_b = create_identity(project_id, "角色B")
add_alias(entity_a.entity_id, "小明")
add_alias(entity_b.entity_id, "小明")

# When
result = resolve_alias(project_id, "小明")

# Then
assert result.status == AMBIGUOUS
assert entity_a.entity_id in result.candidates
assert entity_b.entity_id in result.candidates
```

### AC-005-06: Not Found
```python
# Given
project with no entities named "不存在"

# When
result = resolve_alias(project_id, "不存在")

# Then
assert result == NOT_FOUND
```

### AC-005-07: Canonical Name Collision

**Decision Required**: Can two entities in same project have identical canonical_name?

**Option A**: Allowed (names not unique)
```
Entity A: canonical_name = "林凡", id = E1
Entity B: canonical_name = "林凡", id = E2
Resolve("林凡") → AMBIGUOUS
```

**Option B**: Prohibited (names must be unique within project)
```
Entity A: canonical_name = "林凡", id = E1
create_identity(project, "林凡") → ERROR: name collision
```

**Recommendation**: **Option A** (allow collision)

**Rationale**:
- Matches real-world ambiguity (multiple people with same name)
- Forces explicit disambiguation
- Aligns with alias semantics
- Prevents artificial uniqueness constraints

**Invariant** (if Option A):
```
canonical_name = regular_alias
No implicit priority for canonical_name
```

### AC-005-08: Alias vs Canonical Name Collision

**Given**: Option A from AC-005-07 (canonical names not special)

**Test**:
```python
# Given
entity_a = create_identity(project, canonical_name="林凡")
entity_b = create_identity(project, canonical_name="另一个人")
add_alias(entity_b.entity_id, "林凡")

# When
result = resolve_alias(project_id, "林凡")

# Then
assert result.status == AMBIGUOUS
assert entity_a.entity_id in result.candidates
assert entity_b.entity_id in result.candidates
```

**No implicit priority** for canonical_name.

### AC-005-09: Empty / Invalid Input
```python
# Test empty string
assert resolve_alias(project, "") == INVALID_INPUT

# Test whitespace-only
assert resolve_alias(project, "   ") == INVALID_INPUT

# Test None
assert resolve_alias(project, None) == INVALID_INPUT
```

### AC-005-10: Determinism
```python
# Given
same project state σ
same lookup "test_name"

# When
result_1 = resolve_alias(project, "test_name")
result_2 = resolve_alias(project, "test_name")

# Then
assert result_1 == result_2
# Must be byte-identical, not just semantically equivalent
```

---

## 8. Normalization Policy

### 8.1 Problem

Raw user input may vary:
```
"  张三  "  (leading/trailing spaces)
"　张三　"  (full-width spaces)
"SMITH"
"Smith"
"smith"
```

### 8.2 Minimum Sufficient Normalization

**MUST**:
1. Strip leading/trailing ASCII whitespace
2. Strip leading/trailing full-width spaces (U+3000)
3. Collapse internal consecutive spaces to single space

**MUST NOT** (deferred):
- Unicode NFKC/NFKD normalization (complex, lossy)
- CJK variant normalization (requires large tables)
- Case folding for Chinese (inappropriate)
- Pinyin conversion
- Homoglyph detection

**Case handling**:
- **Chinese names**: case-sensitive (no folding)
- **ASCII names**: **case-insensitive** comparison

**Rationale**:
- Chinese has no case distinction
- ASCII names commonly vary by case ("John" vs "john")
- Prevents "SMITH" and "smith" creating duplicate entities

### 8.3 Implementation

Store **two** values:

**raw_alias**: Original user input (after whitespace trim)
**lookup_key**: Normalized for comparison

```python
def normalize_for_lookup(s: str) -> str:
    # Strip whitespace
    s = s.strip().strip('　')
    # Collapse internal spaces
    s = ' '.join(s.split())
    # ASCII case-insensitive
    return s.lower() if s.isascii() else s
```

**Lookup**:
```python
lookup_key = normalize_for_lookup(user_input)
# Match against stored lookup_keys
```

**Display**:
Use `raw_alias` for display.

### 8.4 Schema Representation

```json
{
  "alias": "  张三  ",           // Original
  "normalized_alias": "张三",     // For lookup
  "entity_id": "...",
  "project_id": "..."
}
```

Or:

```json
{
  "raw": "John Smith",
  "lookup_key": "john smith",   // ASCII lowercased
  "entity_id": "...",
  "project_id": "..."
}
```

---

## 9. Error Model

### 9.1 Result Type Taxonomy

**ResolutionStatus** (enum):
```python
class ResolutionStatus(Enum):
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    INVALID_INPUT = "invalid_input"
```

**ResolutionResult** (discriminated union):
```python
@dataclass(frozen=True)
class ResolvedResult:
    status: Literal[ResolutionStatus.RESOLVED]
    entity_id: EntityId

@dataclass(frozen=True)
class NotFoundResult:
    status: Literal[ResolutionStatus.NOT_FOUND]

@dataclass(frozen=True)
class AmbiguousResult:
    status: Literal[ResolutionStatus.AMBIGUOUS]
    candidates: frozenset[EntityId]  # Unordered!

@dataclass(frozen=True)
class InvalidInputResult:
    status: Literal[ResolutionStatus.INVALID_INPUT]
    reason: str

ResolutionResult = Union[
    ResolvedResult,
    NotFoundResult,
    AmbiguousResult,
    InvalidInputResult
]
```

### 9.2 Why Not `Entity | None`?

**Problem**:
```python
def resolve(name) -> Entity | None:
    # Cannot distinguish:
    # - Not found
    # - Ambiguous (multiple matches)
    # - Invalid input
```

**Solution**: Explicit discriminated union.

### 9.3 Exception vs Result

**Exceptions** for:
- Programming errors (entity_id doesn't exist when adding alias)
- Contract violations (adding alias to nonexistent entity)

**Results** for:
- Expected outcomes (not found, ambiguous)
- User-driven input (lookup)

---

## 10. Negative Scenarios

### NS-1: Cross-project Leakage
```python
# Setup
entity_a = create_identity(project_a, "林凡")

# Attack
result = resolve_alias(project_b, "林凡")

# Must
assert result == NOT_FOUND
# NOT resolved to entity_a
```

### NS-2: Random Selection on Ambiguity
```python
# Setup
entity_1 = create_identity(project, "王五")
entity_2 = create_identity(project, "王五")

# Execute multiple times
results = [resolve_alias(project, "王五") for _ in range(100)]

# Must
assert all(r.status == AMBIGUOUS for r in results)
# NOT varying between entity_1 and entity_2
```

### NS-3: Database Row Order Dependency
```python
# Setup (implementation detail: entities stored unordered)
entity_a = create_identity(project, "test", inserted_at=t1)
entity_b = create_identity(project, "test", inserted_at=t2)

# Execute (database may return different order)
result = resolve_alias(project, "test")

# Must
assert result.status == AMBIGUOUS
# NOT RESOLVED(entity_a) on first call
# NOT RESOLVED(entity_b) on second call
```

### NS-4: Implicit Rename Creates New Entity
```python
# Setup
entity = create_identity(project, "original_name")
original_id = entity.entity_id

# Accidental "rename" via create
entity_new = create_identity(project, "new_name")

# Must
assert entity_new.entity_id != original_id
# Two entities exist
```

**Prevention**: Rename must be explicit operation on existing entity.

### NS-5: Alias Overwrites Silently
```python
# Setup
entity_a = create_identity(project, "角色A")
add_alias(entity_a.entity_id, "绰号X")

# Attempt
entity_b = create_identity(project, "角色B")
add_alias(entity_b.entity_id, "绰号X")  # Same alias - allowed

# Result: Two entities with same alias
resolve_alias(project, "绰号X", registry)
# Returns: AMBIGUOUS({entity_a.entity_id, entity_b.entity_id})
```

**Note**: add_alias does NOT check for cross-entity conflicts. Conflict detection happens at resolution time, returning AMBIGUOUS.

### NS-6: Name as Identity
```python
# Setup
entity = create_identity(project, "张三")
entity_id = entity.entity_id

# Rename
rename_identity(entity_id, "李四")

# Attempt to resolve by ID
by_id = get_entity(entity_id)

# Must
assert by_id.entity_id == entity_id
assert by_id.canonical_name == "李四"
# NOT create new entity "李四" with different ID
```

---

## 11. Implementation Surface

### 11.1 Module Structure

```
src/anovel/domain/
├── __init__.py
└── identity.py          # V2-005 primary module
```

**Why `identity.py` not `entity.py`?**
- Focus is identity resolution, not full entity
- Avoids premature "god object" entity.py

### 11.2 Primary Types

**identity.py** exports:
```python
# Type aliases
EntityId = NewType('EntityId', str)
ProjectId = NewType('ProjectId', str)

# Enums
class ResolutionStatus(Enum): ...

# Value objects
@dataclass(frozen=True)
class EntityIdentity: ...

@dataclass(frozen=True)
class Alias: ...

# Result types
ResolvedResult, NotFoundResult, AmbiguousResult, InvalidInputResult
ResolutionResult = Union[...]

# Operations (functions or service class)
def create_identity(...) -> EntityIdentity: ...
def rename_identity(...) -> EntityIdentity: ...
def add_alias(...) -> EntityIdentity: ...
def remove_alias(...) -> EntityIdentity: ...
def resolve_alias(...) -> ResolutionResult: ...
```

### 11.3 Schema

```
specs/schemas/entity.schema.json
```

Minimal V2-005 schema:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://anovel.dev/schemas/entity-identity.schema.json",
  "title": "EntityIdentity",
  "type": "object",
  "required": ["entity_id", "project_id", "canonical_name"],
  "properties": {
    "entity_id": {"type": "string", "minLength": 1},
    "project_id": {"type": "string", "minLength": 1},
    "canonical_name": {"type": "string", "minLength": 1},
    "aliases": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true
    }
  },
  "additionalProperties": false
}
```

### 11.4 Tests

```
tests/contract/test_v2_005.py
```

Minimum coverage:
- AC-005-01 through AC-005-10
- NS-1 through NS-6
- Normalization edge cases
- Serialization round-trip

---

## 12. Testing Surface

### 12.1 Contract Tests

**File**: `tests/contract/test_v2_005.py`

**Coverage**:
- ✅ All acceptance criteria (AC-005-01 ~ AC-005-10)
- ✅ All negative scenarios (NS-1 ~ NS-6)
- ✅ Invariants (INV-005-01 ~ INV-005-06)
- ✅ Normalization edge cases
- ✅ Serialization/deserialization

**NOT tested** (out of scope):
- Database persistence (V2-009)
- Concurrent access (V2-009)
- Performance benchmarks (not P1 requirement)

### 12.2 Architecture Tests

**Additions to** `tests/architecture/test_dependency_boundaries.py`:

```python
def test_identity_module_no_persistence_imports():
    """V2-005: domain.identity must not import persistence"""
    assert_no_imports(
        "anovel.domain.identity",
        forbidden=[
            "sqlalchemy",
            "psycopg",
            "anovel.canon.repository"  # Future V2-009
        ]
    )

def test_identity_module_no_provider_imports():
    """V2-005: domain.identity must not import gateway/provider"""
    assert_no_imports(
        "anovel.domain.identity",
        forbidden=[
            "openai",
            "anthropic",
            "anovel.gateway"  # Future V2-019
        ]
    )
```

---

## 13. Risks

### R-1: ProjectId Authority Unclear

**Risk**: No existing ProjectId definition found.

**Options**:
1. V2-005 defines ProjectId (NewType)
2. V2-005 assumes ProjectId from external source

**Mitigation**: **Define ProjectId in V2-005**.

**Rationale**:
- No upstream task defines it
- Simple type (NewType('ProjectId', str))
- V2-006+ will reuse from V2-005

**Fallback**: If later task redefines ProjectId, trivial refactor (NewType alias).

### R-2: EntityType Scope Ambiguity

**Risk**: Unclear if V2-005 needs EntityType enum.

**Options**:
1. Generic entity (no type)
2. Minimal enum (CHARACTER, LOCATION, etc.)

**Mitigation**: **Add optional entity_type field**.

**Rationale**:
- Historical schema includes it
- V2-006 (Character) likely needs type distinction
- Optional field allows V2-005 to work without it
- Future-proofs for V2-006

**Decision**: Add `entity_type: str | None = None`

### R-3: Normalization Complexity Creep

**Risk**: Normalization expands into Unicode/NLP project.

**Mitigation**: **Strict scope limit** (§ 8.2).

**Gate**: Reject any normalization requiring:
- External libraries (not in lockfile)
- >100 LOC implementation
- Linguistic analysis

### R-4: Ambiguity UX Challenge

**Risk**: AMBIGUOUS result requires downstream handling.

**Mitigation**: **Not V2-005 responsibility**.

**Boundary**: V2-005 provides machine result. UI/workflow (future) handles user disambiguation.

### R-5: ID Format Bikeshedding

**Risk**: Excessive debate on ID format.

**Mitigation**: **Simple, boring choice**.

**Recommendation**: ULID (Universally Unique Lexicographically Sortable Identifier)
- String format (no UUID bytes)
- Sortable (timestamp prefix)
- No collision
- Human-readable (ish)

**Decision**: UUID v4 only (standard library, no external dependency).

**Anti-pattern**: `char_01H...` (requires entity type in ID)

---

## 14. Open Questions

### Q-1: ProjectId Source of Truth

**Question**: Does ProjectId come from external system or is V2-005 authoritative?

**Investigation**: No external Project management found in current codebase.

**Recommendation**: V2-005 defines ProjectId as `NewType('ProjectId', str)`.

**Validation**: Future V2-009/010 may add project registry; V2-005 ID remains valid.

### Q-2: Entity Creation Authorization

**Question**: Who can create entities?

**Answer**: NOT V2-005 concern.

**Boundary**: V2-005 provides pure identity operations. Authorization belongs to Canon Commit layer (V2-010).

### Q-3: Alias Limit

**Question**: Maximum aliases per entity?

**Recommendation**: **No limit in V2-005**.

**Rationale**:
- No authority specifies limit
- Storage concern, not identity concern
- Can add validation later if needed

**Practical**: Most entities: 1-5 aliases. Edge case: 20+.

### Q-4: Historical Alias Tracking

**Question**: Track when alias was added/removed?

**Recommendation**: **Not V2-005**.

**Rationale**:
- V2-005 is minimal identity kernel
- Event sourcing belongs to V2-009 (Canon)
- Current state sufficient for resolution

**Future**: V2-009 may add alias change events.

### Q-5: Alias Removal Safety

**Question**: Can canonical_name be "removed" (since it's also an alias)?

**Recommendation**: **Canonical name cannot be removed as alias**.

**Rule**:
```python
remove_alias(entity_id, entity.canonical_name) 
→ ValueError("Cannot remove canonical name")
```

**Rationale**: Canonical name always valid lookup.

---

## 15. Decision Recommendations

### D-1: Automatic Alias on Rename

**Recommendation**: ✅ **ADOPT**

Old canonical_name automatically becomes alias.

**Reason**: Prevents narrative break; old name remains valid.

### D-2: Canonical Name Collision Allowed

**Recommendation**: ✅ **ADOPT**

Multiple entities can have same canonical_name.

**Reason**: Models real-world ambiguity; forces explicit resolution.

### D-3: No Implicit Priority for Canonical Name

**Recommendation**: ✅ **ADOPT**

Canonical name = one more alias; no special resolution priority.

**Reason**: Consistent semantics; prevents hidden ordering.

### D-4: ULID for EntityId

**Recommendation**: ✅ **ADOPT**

Use ULID (or UUID v4 fallback) for entity_id format.

**Reason**: Opaque, sortable, collision-resistant.

### D-5: ProjectId Defined in V2-005

**Recommendation**: ✅ **ADOPT**

V2-005 defines `ProjectId = NewType('ProjectId', str)`.

**Reason**: No upstream definition; simple type; reusable.

### D-6: Optional entity_type Field

**Recommendation**: ✅ **ADOPT**

Add `entity_type: str | None = None` to EntityIdentity.

**Reason**: Future-proof for V2-006; optional allows minimal V2-005.

### D-7: Minimal Normalization

**Recommendation**: ✅ **ADOPT**

Whitespace trim + ASCII case folding only.

**Reason**: Sufficient for current needs; avoids complexity.

---

## 16. Implementation Readiness

### Prerequisites Satisfied

✅ **V2-001 closed**: Environment ready  
✅ **No ADR blockers**: Can proceed  
✅ **No authority conflicts**: Specs aligned  
✅ **No implementation conflicts**: Clean slate  

### Design Frozen

✅ **Types defined**: EntityId, ProjectId, EntityIdentity, Alias, ResolutionResult  
✅ **Operations defined**: create, rename, add_alias, remove_alias, resolve  
✅ **Invariants defined**: 6 core invariants documented  
✅ **Acceptance criteria**: 10 scenarios + 6 negative scenarios  
✅ **Error model**: Discriminated union result type  
✅ **Normalization policy**: Minimal sufficient normalization  

### Open Items Resolved

✅ **ProjectId**: Defined in V2-005  
✅ **EntityType**: Optional field  
✅ **Rename policy**: Automatic alias  
✅ **Collision policy**: Allowed, AMBIGUOUS result  
✅ **ID format**: ULID recommended  

---

## 17. Authority Check

### Normative Specs Compliance

✅ **03_DOMAIN_CANON... § 1**:
- "名字不作为主键" → EntityId separate from name ✅
- "项目内同名...必须有独立结果" → Project isolation ✅
- "别名歧义必须有独立结果" → AMBIGUOUS result ✅
- "不能随意合并实体" → Stable entity_id ✅

✅ **02_ARCHITECTURE... § 2**:
- domain 禁止数据库实现 → No persistence in V2-005 ✅
- domain 禁止题材专属字段 → No genre fields ✅

✅ **Implementation Backlog acceptance_criteria**:
- "同名不同项目实体不混淆" → AC-005-01 ✅
- "改名保留稳定 ID" → AC-005-02 ✅
- "歧义别名返回明确冲突而非随机选择" → AC-005-03 ✅

### Historical Reference Alignment

✅ **NARRATIVE_DOMAIN_SPEC.md § 5**:
- Stable ID requirement → EntityId immutable ✅
- Alias resolution must not mint → AMBIGUOUS on conflict ✅
- Name change ≠ new entity → Rename preserves ID ✅

**Deviations from historical**:
- Historical suggested `char_01H...` format → V2-005 uses ULID (reason: simpler, no type prefix)
- Historical had `authority` field → V2-005 defers to Canon layer (V2-010)

**Deviations justified**: Simpler V2-005 scope; Canon layer handles authority.

---

## 18. Summary

### What V2-005 Delivers

**Types**:
- EntityId (opaque stable ID)
- ProjectId (scope boundary)
- EntityIdentity (aggregate)
- Alias (lookup key)
- ResolutionResult (discriminated union)

**Operations**:
- Create, rename, add/remove alias, resolve

**Guarantees**:
- Stable identity across rename
- Project isolation (no cross-contamination)
- Explicit ambiguity detection
- Deterministic resolution
- No name-based identity

**Documentation**:
- Domain types in src/anovel/domain/identity.py
- JSON Schema in specs/schemas/entity.schema.json
- Contract tests in tests/contract/test_v2_005.py

### What V2-005 Does NOT Deliver

- Persistence (→ V2-009)
- Full event sourcing (→ V2-009)
- Character attributes (→ V2-006)
- Authorization (→ V2-010)
- Complex NLP normalization (→ P10/P11?)

### Critical Path Impact

V2-005 is **gate blocker** for P1 → P2.

All downstream tasks (V2-006/007/008/009) depend on stable EntityId.

**Implementation quality bar**: HIGH.

---

**REFINEMENT COMPLETE**

Proceed to Implementation Contract.

---

**END OF DOCUMENT**
