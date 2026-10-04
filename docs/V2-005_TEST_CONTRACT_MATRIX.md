# V2-005 Test Contract Matrix

**Document ID**: V2-005-TEST-MATRIX  
**Version**: 1.1.0  
**Date**: 2026-10-03  
**Status**: REVISED / INDEPENDENT_REVIEW_PENDING  
**Authority**: Test Specification (Pending Approval)  
**Baseline**: dev_cc @ 323eaae7

---

## Test Coverage Matrix

| ID | Scenario | Input | Expected Result | Negative Condition | Contract Layer |
|---|---|---|---|---|---|
| **TC-005-001** | Create identity with valid inputs | project_id="proj_a", canonical_name="张三" | EntityIdentity with fresh entity_id, empty aliases | N/A | Domain Logic |
| **TC-005-002** | Create identity empty name | project_id="proj_a", canonical_name="" | ValueError raised | Empty string rejected | Input Validation |
| **TC-005-003** | Create identity whitespace name | project_id="proj_a", canonical_name="   " | ValueError raised | Whitespace-only rejected | Input Validation |
| **TC-005-004** | Rename preserves entity_id | entity with id=E1, rename to "新名字" | entity_id still E1, canonical_name="新名字" | entity_id changed | Identity Stability |
| **TC-005-005** | Rename old name becomes alias | entity name="陈平安", rename to "陈某" | "陈平安" in aliases | Old name not preserved | Rename Preservation |
| **TC-005-006** | Rename empty name | entity, new_canonical_name="" | ValueError raised | Empty name accepted | Input Validation |
| **TC-005-007** | Add alias to entity | entity, alias="老张" | "老张" in entity.aliases | Alias not added | Alias Management |
| **TC-005-008** | Add alias idempotent | entity with alias="test", add "test" again | aliases still contains single "test" | Duplicate created | Idempotency |
| **TC-005-009** | Add empty alias | entity, alias="" | ValueError raised | Empty accepted | Input Validation |
| **TC-005-010** | Remove alias from entity | entity with alias="test", remove "test" | "test" not in aliases | Alias still present | Alias Management |
| **TC-005-011** | Remove nonexistent alias | entity, remove "nonexistent" | No error, aliases unchanged | Error raised | Idempotency |
| **TC-005-012** | Remove canonical name as alias | entity canonical_name="张三", remove "张三" | ValueError raised | Canonical name removed | Safety Check |
| **TC-005-013** | Resolve unique alias | project with one "老魔" → entity_A | RESOLVED(entity_A.entity_id) | Wrong entity or NOT_FOUND | Resolution Logic |
| **TC-005-014** | Resolve not found | project_id, lookup="不存在的名字" | NOT_FOUND | RESOLVED or AMBIGUOUS | Resolution Logic |
| **TC-005-015** | Resolve ambiguous alias | Two entities both have alias="小明" | AMBIGUOUS(candidates={E1, E2}) | RESOLVED(E1) or RESOLVED(E2) | Ambiguity Detection |
| **TC-005-016** | Resolve empty string | project_id, lookup="" | INVALID_INPUT | RESOLVED or NOT_FOUND | Input Validation |
| **TC-005-017** | Resolve whitespace only | project_id, lookup="   " | INVALID_INPUT | Treated as valid | Input Validation |
| **TC-005-018** | Resolve None | project_id, lookup=None | INVALID_INPUT | Exception or crash | Input Validation |
| **TC-005-019** | Project isolation - same name | proj_a: "王林"→E1, proj_b: "王林"→E2, resolve in proj_a | RESOLVED(E1), E2 not in result | E2 leaked to proj_a | Project Isolation |
| **TC-005-020** | Project isolation - different projects | Entity in proj_a, resolve in proj_b with same name | NOT_FOUND | Entity from proj_a returned | Project Isolation |
| **TC-005-021** | Canonical name collision | proj: E1 canonical="林凡", E2 canonical="林凡", resolve "林凡" | AMBIGUOUS({E1, E2}) | RESOLVED(E1) arbitrarily | Collision Handling |
| **TC-005-022** | Alias vs canonical collision | E1 canonical="林凡", E2 alias="林凡", resolve "林凡" | AMBIGUOUS({E1, E2}) | Canonical has priority | Equality Semantics |
| **TC-005-023** | Normalization whitespace | lookup="  张三  " matches canonical="张三" | RESOLVED(entity) | NOT_FOUND | Normalization |
| **TC-005-024** | Normalization ASCII case | lookup="john" matches canonical="John" | RESOLVED(entity) | NOT_FOUND | Normalization |
| **TC-005-025** | Normalization Chinese case | lookup="张三" does NOT match "張三" (variants) | NOT_FOUND | False match | Normalization |
| **TC-005-026** | Normalization full-width space | lookup="李　明" (U+3000) matches "李明" | RESOLVED(entity with canonical="李明") | NOT_FOUND | Normalization |
| **TC-005-027** | Deterministic resolution - same input | Resolve "test" twice with identical state | result1 == result2 (bitwise) | Different results | Determinism |
| **TC-005-028** | Ambiguous result unordered | AMBIGUOUS with candidates | isinstance(candidates, frozenset) | List with ordering | Determinism |
| **TC-005-029** | No database order dependency | Mock registry with varying iteration order | Always AMBIGUOUS, never varies | Different entity on different calls | Determinism |
| **TC-005-030** | Serialization round-trip | entity → JSON → entity' | entity == entity' | Data loss or corruption | Serialization |
| **TC-005-031** | JSON schema validation | Valid EntityIdentity JSON | Schema validation passes | Invalid JSON accepted | Schema Contract |
| **TC-005-032** | Aliases unique in set | add_alias "test" twice | Only one "test" in aliases | Duplicates present | Data Integrity |
| **TC-005-033** | Entity ID uniqueness | create 1000 entities | All entity_ids distinct | Collision detected | ID Generation |
| **TC-005-034** | Canonical name always resolves | Any entity's canonical_name | RESOLVED or AMBIGUOUS, never NOT_FOUND | NOT_FOUND for own name | Invariant |
| **TC-005-035** | Cross-project leakage attack | Create E1 in proj_a, attempt resolve in proj_b | NOT_FOUND | E1 returned | Security |
| **TC-005-036** | Implicit selection prevention | Two entities match, resolve 100 times | All 100 times AMBIGUOUS | Varies between entities | Anti-Pattern |
| **TC-005-037** | Name change not new entity | Rename entity E1 | E1 still exists with new name, not E2 created | Two entities after rename | Anti-Pattern |
| **TC-005-038** | Cross-entity alias duplication | E1 has alias "X", E2 adds alias "X" | resolve("X") → AMBIGUOUS({E1, E2}) | Error raised or E1 loses alias | Resolution Logic |

---

## Revision 1.1.0: Additional Test Cases

| ID | Scenario | Input | Expected Result | Negative Condition | Contract Layer |
|---|---|---|---|---|---|
| **TC-005-039** | Repeated rename alias accumulation | Entity: "A" → rename "B" → rename "C" | aliases = {"A", "B"}, canonical="C" | Old names not preserved | Rename Preservation |
| **TC-005-040** | Normalized name collision with alias | E1: canonical="John Smith"; E2: canonical="李四", aliases=["john smith"] | resolve("john smith") → AMBIGUOUS({E1, E2}) | E1 takes priority | Resolution Priority |
| **TC-005-041** | Rename creates normalized collision | E1: canonical="Test"; E2: canonical="Other", aliases=["test"]. E1 rename to "test" | resolve("test") → AMBIGUOUS({E1, E2}) | E1 overwrites E2 alias | Resolution Conflict |
| **TC-005-042** | Whitespace-only normalized to empty | normalize_for_lookup("   ") → "" | Empty string not matched to any entity | False match to entity | Normalization Edge |
| **TC-005-043** | Registration order independence | Same entities registered in different orders | resolve() results identical (status + candidates as set) | Different results by order | Determinism |
| **TC-005-044** | Single entity multiple name matches | Entity canonical="John", aliases=["JOHN", "john doe"]; resolve("john") | RESOLVED(entity), not AMBIGUOUS | Multiple candidates for same entity | De-duplication |
| **TC-005-045** | Cross-project entity not resolved | Entity in proj_a; resolve in proj_b with same name | NOT_FOUND | Entity from proj_a returned | Project Isolation |
| **TC-005-046** | Duplicate ID with same content (idempotent) | add_entity(E1), add_entity(E1) with same content | No error, single registration | Duplicate created | Idempotency |
| **TC-005-047** | Duplicate ID with different content | add_entity(E1), add_entity(E1_modified) | ValueError("Entity ID already registered") | Silent overwrite | Uniqueness |
| **TC-005-048** | Rename failure leaves state unchanged | original = create(...); rename(original, "") raises ValueError | original.canonical_name unchanged | original modified | Exception Safety |
| **TC-005-049** | Normalized empty string no match | Entity with canonical="Test"; normalize("   ") = ""; resolve("   ") | INVALID_INPUT, not match to "Test" | False positive match | Normalization Edge |
| **TC-005-050** | Input collection modification isolation | mutable_list = ["alias1"]; create entity; modify mutable_list | entity.aliases unchanged | External modification affects entity | Immutability |
| **TC-005-051** | Output collection modification blocked | entity.aliases is frozenset; cannot append/remove | Modification attempt raises AttributeError | Entity state changed | Immutability |

---

## Test Count Summary

**Original Tests**: TC-005-001 through TC-005-038 (38 tests)  
**Revision 1.1.0 Added**: TC-005-039 through TC-005-051 (13 tests)  
**Total Tests**: **51 tests**

---

## Test Groups

### G1: Input Validation (7 tests)
- TC-005-002, TC-005-003, TC-005-006, TC-005-009, TC-005-016, TC-005-017, TC-005-018

### G2: Identity Stability (3 tests)
- TC-005-001, TC-005-004, TC-005-033

### G3: Rename Operations (3 tests)
- TC-005-004, TC-005-005, TC-005-006

### G4: Alias Management (6 tests)
- TC-005-007, TC-005-008, TC-005-009, TC-005-010, TC-005-011, TC-005-012

### G5: Resolution Logic (11 tests)
- TC-005-013, TC-005-014, TC-005-015, TC-005-019, TC-005-020, TC-005-021, TC-005-022, TC-005-027, TC-005-034, TC-005-035, TC-005-036

### G6: Project Isolation (3 tests)
- TC-005-019, TC-005-020, TC-005-035

### G7: Normalization (4 tests)
- TC-005-023, TC-005-024, TC-005-025, TC-005-026

### G8: Determinism (3 tests)
- TC-005-027, TC-005-028, TC-005-029

### G9: Serialization (2 tests)
- TC-005-030, TC-005-031

### G10: Anti-Patterns (3 tests)
- TC-005-036, TC-005-037, TC-005-038

### G11: Contract Revision 1.1 (13 tests)
- TC-005-039 (Repeated rename)
- TC-005-040 (Normalized collision)
- TC-005-041 (Rename collision)
- TC-005-042 (Whitespace normalization)
- TC-005-043 (Registration order)
- TC-005-044 (Single entity multi-match)
- TC-005-045 (Cross-project isolation)
- TC-005-046 (Duplicate ID idempotent)
- TC-005-047 (Duplicate ID different content)
- TC-005-048 (Rename failure safety)
- TC-005-049 (Empty normalized string)
- TC-005-050 (Input isolation)
- TC-005-051 (Output isolation)

---

## Acceptance Criteria Mapping

| AC ID | Test Cases | Status |
|---|---|---|
| AC-005-01 (Project isolation) | TC-005-019, TC-005-020 | ✅ Covered |
| AC-005-02 (Rename stability) | TC-005-004 | ✅ Covered |
| AC-005-03 (Old name as alias) | TC-005-005 | ✅ Covered |
| AC-005-04 (Unique alias resolution) | TC-005-013 | ✅ Covered |
| AC-005-05 (Ambiguous alias) | TC-005-015 | ✅ Covered |
| AC-005-06 (Not found) | TC-005-014 | ✅ Covered |
| AC-005-07 (Canonical name collision) | TC-005-021 | ✅ Covered |
| AC-005-08 (Alias vs canonical collision) | TC-005-022 | ✅ Covered |
| AC-005-09 (Empty/invalid input) | TC-005-016, TC-005-017, TC-005-018 | ✅ Covered |
| AC-005-10 (Determinism) | TC-005-027, TC-005-028, TC-005-029 | ✅ Covered |

---

## Negative Scenario Mapping

| NS ID | Test Cases | Status |
|---|---|---|
| NS-1 (Cross-project leakage) | TC-005-035 | ✅ Covered |
| NS-2 (Random selection) | TC-005-036 | ✅ Covered |
| NS-3 (DB row order) | TC-005-029 | ✅ Covered |
| NS-4 (Implicit rename) | TC-005-037 | ✅ Covered |
| NS-5 (Alias overwrite) | TC-005-038 | ✅ Covered |
| NS-6 (Name as identity) | TC-005-004, TC-005-037 | ✅ Covered |

---

## Invariant Verification

| Invariant | Test Cases | Verification Method |
|---|---|---|
| INV-005-01 (Stable identity) | TC-005-004, TC-005-005, TC-005-007, TC-005-010 | Assert entity_id unchanged after operations |
| INV-005-02 (Project isolation) | TC-005-019, TC-005-020, TC-005-035 | Assert no cross-project results |
| INV-005-03 (Alias is not identity) | TC-005-013, TC-005-021 | Type system + resolution logic |
| INV-005-04 (Explicit ambiguity) | TC-005-015, TC-005-021, TC-005-022, TC-005-036 | Assert AMBIGUOUS status, no arbitrary selection |
| INV-005-05 (Determinism) | TC-005-027, TC-005-028, TC-005-029 | Multiple invocations, bitwise equality |
| INV-005-06 (Rename preservation) | TC-005-005 | Assert old name in aliases |
| INV-005-07 (Canonical always valid) | TC-005-034 | Resolve entity's own canonical_name |
| INV-005-08 (Immutability) | All operation tests | Assert operations return new objects |

---

## Test Execution Strategy

### Phase 1: Unit Tests (Domain Logic)
**Run**: `pytest tests/contract/test_v2_005.py -v`

**Coverage Target**: 100% of domain logic

**Focus**: Pure domain operations, no external dependencies

### Phase 2: Architecture Tests (Boundaries)
**Run**: `pytest tests/architecture/test_dependency_boundaries.py::test_v2_005_* -v`

**Coverage Target**: Import boundary enforcement

**Focus**: No prohibited imports (persistence, gateway)

### Phase 3: Schema Validation
**Run**: `pytest tests/contract/test_v2_005.py::test_json_schema_* -v`

**Coverage Target**: Schema compliance

**Focus**: JSON serialization and schema validation

### Phase 4: Integration Readiness
**Verify**: 
- `from anovel.domain.identity import EntityId` works
- Type hints pass mypy --strict
- All 38 test cases pass

---

## Test Data Fixtures

### F1: Basic Project and Entities
```python
@pytest.fixture
def project_a():
    return ProjectId("project_a")

@pytest.fixture
def project_b():
    return ProjectId("project_b")

@pytest.fixture
def entity_zhang_san(project_a):
    return create_identity(project_a, "张三", entity_type="CHARACTER")

@pytest.fixture
def entity_li_si(project_a):
    return create_identity(project_a, "李四", entity_type="CHARACTER")
```

### F2: Registry with Test Data
```python
@pytest.fixture
def populated_registry(project_a):
    registry = EntityRegistry()
    e1 = create_identity(project_a, "王五")
    e2 = create_identity(project_a, "赵六")
    e3 = add_alias(create_identity(project_a, "钱七"), "老钱")
    registry.add_entity(e1)
    registry.add_entity(e2)
    registry.add_entity(e3)
    return registry
```

### F3: Collision Scenario
```python
@pytest.fixture
def collision_registry(project_a):
    registry = EntityRegistry()
    e1 = create_identity(project_a, "林凡")
    e2 = create_identity(project_a, "另一个人")
    e2 = add_alias(e2, "林凡")  # Same name as e1's canonical
    registry.add_entity(e1)
    registry.add_entity(e2)
    return registry
```

---

## Assertion Helpers

### H1: Resolution Status Check
```python
def assert_resolved(result: ResolutionResult, expected_id: EntityId):
    assert result.status == ResolutionStatus.RESOLVED
    assert isinstance(result, ResolvedResult)
    assert result.entity_id == expected_id

def assert_not_found(result: ResolutionResult):
    assert result.status == ResolutionStatus.NOT_FOUND
    assert isinstance(result, NotFoundResult)

def assert_ambiguous(result: ResolutionResult, expected_candidates: set[EntityId]):
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert isinstance(result, AmbiguousResult)
    assert result.candidates == frozenset(expected_candidates)

def assert_invalid_input(result: ResolutionResult):
    assert result.status == ResolutionStatus.INVALID_INPUT
    assert isinstance(result, InvalidInputResult)
```

### H2: Invariant Checks
```python
def assert_entity_id_stable(original: EntityIdentity, modified: EntityIdentity):
    """Verify entity_id hasn't changed."""
    assert modified.entity_id == original.entity_id
    assert modified.project_id == original.project_id

def assert_immutable(obj):
    """Verify object is frozen."""
    assert obj.__dataclass_params__.frozen
```

---

## Coverage Requirements

### Minimum Code Coverage
- Domain logic: **100%**
- Public API: **100%**
- Error paths: **100%**

### Branch Coverage
- All if/else branches: **100%**
- All match/case branches: **100%**

### Edge Cases
- Empty inputs ✅
- Whitespace variations ✅
- Unicode edge cases (full-width spaces) ✅
- Large datasets (1000 entities) ✅
- Collision scenarios ✅

---

## Test Execution Environment

### Requirements
- Python 3.12.14 (locked)
- pytest (from uv.lock)
- No external dependencies (database, network)

### Isolation
- Each test independent
- No shared state across tests
- No side effects

### Performance
- All 38 tests should complete in <1 second
- No slow tests (this is pure domain logic)

---

## Failure Analysis

### Common Failure Patterns

**F1: Cross-project leakage**
- **Symptom**: TC-005-019, TC-005-035 fail
- **Root cause**: Resolution not filtering by project_id
- **Fix**: Add project_id filter in resolve_alias

**F2: Arbitrary selection on ambiguity**
- **Symptom**: TC-005-015, TC-005-036 fail randomly
- **Root cause**: Using list[0] or similar
- **Fix**: Return AMBIGUOUS for len(candidates) > 1

**F3: Mutation instead of immutability**
- **Symptom**: Original object changes after operation
- **Root cause**: Not using frozen=True
- **Fix**: Add frozen=True to all dataclasses

**F4: Order dependency**
- **Symptom**: TC-005-029 fails intermittently
- **Root cause**: Relying on dict/set iteration order
- **Fix**: Use frozenset for unordered collections

---

## Exit Criteria

V2-005 testing complete when:

✅ **All 51 test cases implemented** (was 38, revised to 51)  
✅ **All tests pass consistently**  
✅ **100% code coverage on domain logic**  
✅ **Architecture tests pass (no prohibited imports)**  
✅ **Schema validation tests pass**  
✅ **mypy --strict passes**  
✅ **No test flakiness (run 10x, all pass)**  
✅ **Determinism verified (registration order independence)**  
✅ **Isolation verified (input/output modification blocked)**  

---

## Test Maintenance

### Adding New Tests
- Add to appropriate group (G1-G10)
- Update coverage matrix
- Maintain test ID sequence (TC-005-xxx)

### Modifying Tests
- Preserve test IDs (don't renumber)
- Update matrix if expectations change
- Maintain backward compatibility

### Deprecating Tests
- Mark deprecated, don't delete
- Explain reason in comments
- Keep in matrix as "deprecated"

---

**END OF TEST MATRIX**
