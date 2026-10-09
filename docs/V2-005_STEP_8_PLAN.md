# V2-005 Step 8 Implementation Plan

**Document ID**: V2-005-STEP-8-PLAN  
**Version**: 1.0.0  
**Date**: 2026-10-06  
**Status**: PLANNING  
**Baseline**: 48eb836bcb44abce88453c0f07a45d0c31eb96d5 (Step 7 SSOT verified)

---

## 1. Step 8 Scope

### 1.1 What Step 8 IS

Step 8 is the **final integration and acceptance** phase for V2-005. It does NOT implement new operations but rather:

1. **Schema Contract** (§13):
   - Create `specs/schemas/entity-identity.schema.json`
   - JSON Schema Draft 2020-12 compliant
   - Validates EntityIdentity serialization format

2. **Consolidated Contract Tests** (§11):
   - Create `tests/contract/test_v2_005.py`
   - Minimum 25 named test functions per §11.1
   - Covers all acceptance criteria (AC-005-01 through AC-005-10)
   - Covers all negative scenarios (NS-1 through NS-6)
   - Serialization round-trip test
   - JSON schema validation test

3. **Architecture Boundary Tests** (§11.2):
   - Add to `tests/architecture/test_dependency_boundaries.py`
   - Verify no persistence imports in identity.py
   - Verify no provider/gateway imports in identity.py

4. **Module Documentation** (§12):
   - Update identity.py module docstring per §12.1
   - Ensure all public API documented

5. **Acceptance Checklist** (§17):
   - Verify all checklist items complete
   - Document final acceptance evidence

### 1.2 What Step 8 IS NOT

Step 8 does NOT:
- ❌ Modify Step 1-7 verified implementations
- ❌ Change EntityId, ProjectId, EntityIdentity semantics
- ❌ Modify create_identity, rename_identity, add_alias, remove_alias, resolve_alias
- ❌ Change normalize_for_lookup behavior
- ❌ Modify EntityRegistry (already implemented in Step 4)
- ❌ Implement persistence (V2-007)
- ❌ Implement relationship tracking (V2-006)
- ❌ Add new operations beyond contract scope
- ❌ Refactor existing code structure
- ❌ Change CI gates or test infrastructure

---

## 2. Current State Analysis

### 2.1 Completed (Steps 1-7)

**Step 1-2: Types**
- ✅ EntityId (NewType)
- ✅ ProjectId (NewType)
- ✅ EntityIdentity (dataclass, frozen, immutable)
- ✅ ResolutionStatus (enum)
- ✅ ResolvedResult, NotFoundResult, AmbiguousResult, InvalidInputResult
- ✅ ResolutionResult (union type)

**Step 3: Normalization & ID Generation**
- ✅ normalize_for_lookup() (§3.6)
- ✅ _generate_entity_id() (UUID v4)
- ✅ 29 tests

**Step 4: EntityRegistry**
- ✅ EntityRegistry in-memory implementation (§4)
- ✅ add_entity (idempotent)
- ✅ get_entity
- ✅ get_entities (project-scoped)
- ✅ 20 tests

**Step 5: create_identity & rename_identity**
- ✅ create_identity (§3.1)
- ✅ rename_identity (§3.2)
- ✅ 32 tests

**Step 6: add_alias & remove_alias**
- ✅ add_alias (§3.3)
- ✅ remove_alias (§3.4)
- ✅ 35 tests

**Step 7: resolve_alias**
- ✅ resolve_alias (§3.5)
- ✅ 26 tests

**Total Existing Tests**: 142 (Step 3: 29, Step 4: 20, Step 5: 32, Step 6: 35, Step 7: 26)

### 2.2 Missing (Step 8 Scope)

1. **Schema File**: `specs/schemas/entity-identity.schema.json` does not exist
2. **Consolidated Test File**: `tests/contract/test_v2_005.py` does not exist
3. **Architecture Tests**: Missing V2-005 boundary checks
4. **Module Docstring**: Needs update per §12.1 format
5. **Acceptance Evidence**: Final checklist verification

---

## 3. Step 8 Implementation Tasks

### 3.1 Task 1: Create JSON Schema

**File**: `specs/schemas/entity-identity.schema.json`

**Content** (per §13.1):
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
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
      "description": "Stable unique identifier (UUID v4 format)"
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
      "description": "Alternative names (optional)"
    },
    "entity_type": {
      "type": "string",
      "description": "Entity classification (optional, e.g., CHARACTER, LOCATION)"
    }
  },
  "additionalProperties": false
}
```

**Validation**:
- Must validate against JSON Schema Draft 2020-12 meta-schema
- Must pass jsonschema library validation

### 3.2 Task 2: Create Consolidated Contract Tests

**File**: `tests/contract/test_v2_005.py`

**Purpose**: Single comprehensive test file covering all V2-005 acceptance criteria

**Minimum 25 Test Functions** (per §11.1):
1. `test_create_identity_generates_stable_id`
2. `test_create_identity_empty_name_raises`
3. `test_rename_preserves_entity_id`
4. `test_rename_old_name_becomes_alias`
5. `test_rename_empty_name_raises`
6. `test_add_alias_adds_to_set`
7. `test_add_alias_idempotent`
8. `test_add_alias_empty_raises`
9. `test_remove_alias_removes_from_set`
10. `test_remove_alias_idempotent`
11. `test_remove_alias_canonical_name_raises`
12. `test_resolve_unique_alias_returns_resolved`
13. `test_resolve_not_found_returns_not_found`
14. `test_resolve_ambiguous_returns_ambiguous`
15. `test_resolve_empty_string_returns_invalid`
16. `test_resolve_whitespace_only_returns_invalid`
17. `test_project_isolation`
18. `test_same_name_different_projects`
19. `test_normalization_whitespace`
20. `test_normalization_ascii_case_insensitive`
21. `test_normalization_chinese_case_sensitive`
22. `test_serialization_round_trip`
23. `test_json_schema_validation`
24. `test_deterministic_resolution`
25. `test_ambiguous_result_unordered`

**Additional Negative Scenario Tests** (NS-1 through NS-6):
- NS-1: Cross-project leakage
- NS-2: No random selection on ambiguity
- NS-3: No database row order dependency
- NS-4: No implicit rename creating new entity
- NS-5: No silent alias overwrite
- NS-6: Name is not identity

**Note**: These tests will REFERENCE existing Step 3-7 implementations. They are a **contract verification layer**, not duplicate implementations.

### 3.3 Task 3: Add Architecture Boundary Tests

**File**: `tests/architecture/test_dependency_boundaries.py`

**Add Functions** (per §11.2):
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

### 3.4 Task 4: Update Module Docstring

**File**: `src/anovel/domain/identity.py`

**Update Module Docstring** (per §12.1):
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
        normalize_for_lookup
    Data Structures:
        EntityRegistry (in-memory, for tests)

Contract: V2-005 Implementation Contract v1.1.0
"""
```

---

## 4. Prohibited Modifications

### 4.1 Do NOT Modify

**Verified Implementations** (Steps 1-7):
- ❌ EntityId, ProjectId, EntityIdentity definitions
- ❌ ResolutionResult types
- ❌ normalize_for_lookup() logic
- ❌ _generate_entity_id() logic
- ❌ EntityRegistry implementation
- ❌ create_identity() logic
- ❌ rename_identity() logic
- ❌ add_alias() logic
- ❌ remove_alias() logic
- ❌ resolve_alias() logic

**Test Files** (Steps 3-7):
- ❌ tests/contract/test_v2_005_step3.py
- ❌ tests/contract/test_v2_005_step4.py
- ❌ tests/contract/test_v2_005_step5.py
- ❌ tests/contract/test_v2_005_step6.py
- ❌ tests/contract/test_v2_005_step7.py

**Infrastructure**:
- ❌ .gitlab-ci.yml
- ❌ CI gate definitions
- ❌ Schema validation gate (unless adding new schema)

### 4.2 Why These Are Frozen

Steps 1-7 have been:
1. Independently verified against frozen contract
2. Passed exact-SHA CI (6/6 gates)
3. Preserved baseline test counts
4. Accepted through formal review

Any modification to these components would:
- Break chain of verified evidence
- Require re-verification of entire V2-005
- Risk introducing regressions
- Violate frozen contract authority

---

## 5. Expected Outcomes

### 5.1 New Files Created

1. `specs/schemas/entity-identity.schema.json` (JSON Schema)
2. `tests/contract/test_v2_005.py` (25+ contract tests)

### 5.2 Modified Files

1. `src/anovel/domain/identity.py` (module docstring only)
2. `tests/architecture/test_dependency_boundaries.py` (add 2 tests)
3. `PROJECT_STATUS.md` (Step 8 status update)

### 5.3 Test Count Changes

**Current Baseline**: 707 executions (485 unit + 222 arch)

**After Step 8**:
- Add ~25-30 new tests in test_v2_005.py
- Add 2 architecture tests
- **Expected**: ~734-739 executions

### 5.4 CI Verification

**Expected**:
- 6/6 gates PASS
- JUnit: ~734-739/~734-739 PASS
- No FAILED, ERROR, or SKIPPED
- mypy --strict: PASS

---

## 6. Acceptance Criteria

### 6.1 Code Complete

- [ ] specs/schemas/entity-identity.schema.json exists and validates
- [ ] tests/contract/test_v2_005.py exists with ≥25 tests
- [ ] Architecture tests added to test_dependency_boundaries.py
- [ ] Module docstring updated per §12.1

### 6.2 Contract Conformance

- [ ] All §11.1 required test functions present
- [ ] All AC-005-01 through AC-005-10 covered
- [ ] All NS-1 through NS-6 covered
- [ ] JSON schema validates EntityIdentity
- [ ] Architecture boundaries enforced

### 6.3 CI Verification

- [ ] 6/6 gates PASS
- [ ] All tests PASS (no FAILED/ERROR/SKIPPED)
- [ ] mypy --strict PASS
- [ ] Baseline tests preserved (707 → ~734-739)

### 6.4 No Regressions

- [ ] Step 3-7 tests still pass (142 tests)
- [ ] No modifications to verified implementations
- [ ] No breaking changes to public API

---

## 7. Implementation Order

### Phase 1: Schema (Low Risk)
1. Create specs/schemas/ directory if needed
2. Write entity-identity.schema.json
3. Validate schema file itself

### Phase 2: Consolidated Tests (Medium Risk)
1. Create tests/contract/test_v2_005.py
2. Implement 25 required test functions
3. Add negative scenario tests
4. Verify all tests pass

### Phase 3: Architecture Tests (Low Risk)
1. Add 2 boundary tests to test_dependency_boundaries.py
2. Verify tests pass

### Phase 4: Documentation (Low Risk)
1. Update identity.py module docstring
2. Verify docstring format

### Phase 5: Verification (Critical)
1. Run all tests locally (expect ~734-739 PASS)
2. Run mypy --strict
3. Commit and push
4. Verify exact-SHA CI (6/6 PASS)

---

## 8. Risk Assessment

### 8.1 Low Risk

- Creating new schema file (isolated)
- Adding new test file (additive only)
- Adding architecture tests (additive only)
- Updating module docstring (documentation only)

### 8.2 Medium Risk

- Consolidated tests might duplicate Step 3-7 tests (acceptable per contract)
- Test count increase might trigger unexpected CI issues

### 8.3 High Risk (Mitigations)

**Risk**: Accidentally modifying Step 1-7 implementations
**Mitigation**: Only modify identity.py docstring, verify diff before commit

**Risk**: Breaking existing tests
**Mitigation**: Run Step 3-7 tests before and after Step 8 changes

**Risk**: Schema validation failure
**Mitigation**: Test schema with jsonschema library before commit

---

## 9. Success Metrics

### 9.1 Quantitative

- Schema file validates: YES/NO
- Contract tests count: ≥25
- Architecture tests added: 2
- Total test executions: ~734-739
- CI gates: 6/6 PASS
- Test failures: 0

### 9.2 Qualitative

- All §17 acceptance checklist items complete
- No Step 1-7 regressions
- Contract conformance verified
- Architecture boundaries enforced

---

## 10. Next Steps After Step 8

Once Step 8 is verified:

1. **V2-005 Closure**:
   - Final acceptance report
   - Update SSOT for V2-005 COMPLETE
   - Archive contract as IMPLEMENTED

2. **V2-006 Planning**:
   - Entity relationship tracking
   - Knowledge state management

3. **V2-007 Planning**:
   - Persistence layer
   - SQLAlchemy integration

---

**Status**: READY_FOR_IMPLEMENTATION  
**Next Action**: Create schema file and consolidated tests per this plan
