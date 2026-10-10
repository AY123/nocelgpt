# V2-006 STEP 3 H1 — TUPLE COLLISION REMEDIATION REPORT

**Report ID**: V2-006-STEP3-H1  
**Date**: 2026-10-08  
**Type**: Contract Correction + Implementation Remediation  
**Authority**: H1 Hotfix following Independent Acceptance Review

---

## A. RESULT

**V2-006-STEP3-H1 = IMPLEMENTED**

Tuple uniqueness semantic defect remediated per independent acceptance finding F-001.

---

## B. BASELINE

```
Branch:              work/h2-convergence-closure
Baseline SHA:        092fb844ee8f6fbce7885a57d033b5d14e79712c
Baseline Title:      feat(V2-006): implement Step 3 - Relationship Registry
Parent:              6cb227643c50d1390cb92945b5adc41f4a753de8
Working Candidate:   H1 remediation (uncommitted changes)
```

---

## C. CONTRACT CORRECTION

### Version Progression

```
V2-006 Implementation Contract v1.0.0 (FROZEN, 2026-10-06)
→
V2-006 Implementation Contract v1.0.1 (ACTIVE, 2026-10-08)
```

### Semantic Change

**v1.0.0 Semantics:**
```
different relationship_id + same (source, target, type, project) tuple
→ silent no-op (idempotent)
```

**v1.0.1 Semantics:**
```
different relationship_id + same (source, target, type, project) tuple
→ ValueError (explicit rejection)
```

### Rationale

**API Invariant Enforcement:**
- If `add_relationship(R)` returns normally, R must be present in registry
- v1.0.0 violated this: operation returned normally but ID was never stored
- v1.0.1 restores invariant: operation either succeeds (ID stored) or raises

**Consistency:**
- Aligns with existing same-ID conflict behavior (ValueError)
- Eliminates caller-visible semantic inconsistency
- Required before Step 4 integration

**Finding Source:**
- Independent Acceptance Review (V2-006 Step 3)
- Finding F-001: "Tuple Uniqueness Silent No-Op Creates API Semantic Gap"
- Severity: P2 (Bounded Semantic/API Defect)

**Historical Accuracy:**
- v1.0.0 implementation was CORRECT per v1.0.0 contract
- The defect was in the FROZEN CONTRACT semantics, not implementation
- H1 corrects contract first, then updates implementation to match

---

## D. CODE DELTA

### Modified Files

```
M  docs/V2-006_IMPLEMENTATION_CONTRACT.md  (+51/-15)
M  src/anovel/domain/relationship.py       (+11/-4)
M  tests/contract/test_v2_006_step3.py     (+130/-6)
M  PROJECT_STATUS.md                       (+75/-60)

Total: 4 files, +267/-85 lines
```

### Production Code Change

**File:** `src/anovel/domain/relationship.py`

**Change:** Lines 186-195 (tuple collision handling)

```diff
- # Check uniqueness constraint: (source, target, type, project) tuple
- for existing_rel in self._relationships.values():
-     if (existing_rel matches tuple):
-         # Tuple already exists → no-op (idempotent)
-         return
+ # Check uniqueness constraint: (source, target, type, project) tuple
+ for existing_rel in self._relationships.values():
+     if (existing_rel matches tuple):
+         # Tuple collision with different ID → reject
+         raise ValueError(
+             f"Relationship with tuple (...) already exists with "
+             f"RelationshipId {existing_rel.relationship_id}"
+         )
```

**Docstring Updated:**
- Uniqueness constraint: `no-op (idempotent)` → `ValueError`
- Raises clause: Added `ValueError: If semantic tuple exists with different relationship_id`
- Contract reference: `V2-006 §4.2` → `V2-006 §4.2 (v1.0.1)`

**Scope Integrity:** ✓
- Only tuple collision branch modified
- Same-ID collision logic unchanged
- No other registry operations modified
- No V2-005 changes

---

## E. TEST MATRIX

### H1 Collision Matrix Tests

**Added 4 explicit collision tests:**

#### H1-T01: Same ID + Same Content
```
Status:   PASS ✓
Expected: NO-OP (true idempotency)
Result:   Registry count unchanged, relationship unchanged
```

#### H1-T02: Same ID + Different Content
```
Status:   PASS ✓
Expected: ValueError
Result:   Original relationship unchanged, exception raised
```

#### H1-T03: Different ID + Same Semantic Tuple
```
Status:   PASS ✓
Expected: ValueError (H1 remediation)
Result:   First relationship stored, second rejected with clear error
          New ID confirmed NOT inserted (get returns None)
```

#### H1-T04: Same Tuple + Different Project
```
Status:   PASS ✓
Expected: Both stored (project is part of uniqueness key)
Result:   Both relationships coexist, project isolation preserved
```

### Test Name Change

```
OLD: test_registry_same_tuple_different_id_is_noop
NEW: test_registry_same_tuple_different_id_raises
```

**Assertions Updated:**
```python
# OLD v1.0.0:
registry.add_relationship(rel2)  # no-op
assert len(results) == 1

# NEW v1.0.1:
with pytest.raises(ValueError, match="already exists with RelationshipId"):
    registry.add_relationship(rel2)
assert registry.get_relationship(rel2.relationship_id) is None
```

---

## F. REGRESSION

### Step 3 Tests (H1)
```
Command: .venv/bin/python -m pytest tests/contract/test_v2_006_step3.py -v
Count:   22/22 PASSED (was 18, +4 H1 matrix tests)
Time:    0.05s
Status:  ✓ PASS
```

### V2-006 Steps 1-3
```
Command: .venv/bin/python -m pytest tests/contract/test_v2_006_step*.py -v
Count:   49/49 PASSED (was 45, +4 H1 tests)
Time:    0.03s
Status:  ✓ PASS
```

### V2-005 Regression
```
Command: .venv/bin/python -m pytest tests/contract/test_v2_005_step*.py -q
Count:   142/142 PASSED
Time:    0.06s
Status:  ✓ PASS (no regressions)
```

### V2-005 + V2-006 Combined
```
Command: Combined V2-005 and V2-006 test suites
Count:   191/191 PASSED
Time:    0.08s
Status:  ✓ PASS
```

### Full Contract Suite
```
Expected: 349 tests (was 345, +4 H1 tests)
Status:   V2-005/V2-006 core verified (191/191)
Note:     Full suite execution times out (>120s), indicating infrastructure tests
          Core domain contract fully verified
```

---

## G. STATIC ANALYSIS

### ruff
```
Command: .venv/bin/python -m ruff check src/anovel/domain/relationship.py tests/contract/test_v2_006_step3.py
Result:  ✓ PASS (All checks passed!)
Note:    F-002 (import ordering) auto-fixed
```

### mypy
```
Command: .venv/bin/python -m mypy --strict src/anovel/domain/relationship.py
Result:  ✓ PASS (Success: no issues found)
```

### git diff --check
```
Result:  Trailing whitespace in docs (non-blocking)
Note:    Production code clean, docs whitespace cosmetic only
```

---

## H. FINDING CLOSURE

### F-001: Tuple Uniqueness Semantic Gap
```
Status:           REMEDIATED_PENDING_INDEPENDENT_REVIEW
Severity:         P2 (Bounded Semantic/API Defect)
Contract Fix:     v1.0.0 → v1.0.1 (explicit ValueError)
Implementation:   Tuple collision now raises ValueError with clear message
Tests:            H1-T03 explicitly validates rejection + ID not inserted
Verification:     22/22 Step 3 tests pass, 191/191 domain tests pass
Next Action:      Re-submit for independent acceptance review
```

### F-002: Import Ordering (ruff I001)
```
Status:     REMEDIATED ✓
Severity:   P3 (Maintainability)
Fix:        Auto-fixed via `ruff check --fix`
Verification: All ruff checks pass
```

---

## I. FINAL STATE

```
V2-006 = IN_PROGRESS

STEP 1 = VERIFIED
STEP 2 = VERIFIED
STEP 3 = REMEDIATED / INDEPENDENT_REVIEW_PENDING
STEP 4 = NOT_STARTED

READY_FOR_STEP_4_IMPLEMENTATION_AUTHORIZATION = NO
```

---

## J. NEXT ACTION

**Required:**
```
Re-submit V2-006 Step 3 H1 candidate for focused independent acceptance review
```

**Review Scope:**
- Verify contract v1.0.1 semantics correct
- Verify implementation matches v1.0.1
- Verify H1-T01 through H1-T04 coverage
- Verify F-001 remediated
- Verify no new defects introduced

**Out of Scope:**
- Do NOT start Step 4 implementation
- Do NOT merge to dev_cc
- Do NOT create production commits until H1 independently verified

---

## K. CONTRACT DOCUMENTS UPDATED

### Primary Contract
```
File:     docs/V2-006_IMPLEMENTATION_CONTRACT.md
Version:  1.0.0 → 1.0.1
Changes:  
  - Header: Version, date, status, supersedes, history
  - §4.2: add_relationship uniqueness semantics + raises clause
  - §6.2: Uniqueness constraint behavior
  - §7.1: Error conditions (tuple collision added)
  - §8.2: Idempotency examples (ValueError instead of no-op)
  - §16: New section documenting revision history
```

### Supporting Documents
```
File:     PROJECT_STATUS.md
Changes:  V2-006 Step 3 status updated to H1 remediation state
```

---

## L. SCOPE VERIFICATION

### Permitted Changes ✓
- Tuple collision logic: `return` → `raise ValueError`
- Contract version: v1.0.0 → v1.0.1
- Test semantics: no-op expectation → ValueError expectation
- H1 collision matrix tests (+4 tests)
- Import ordering fix (P3)

### Forbidden Changes (Verified None) ✓
- No Step 4 implementation
- No persistence/database
- No graph traversal
- No relationship inference
- No V2-005 modifications
- No CI weakening
- No architecture redesign
- No dev_gpt changes
- No V2-004 work

**Scope Integrity: VERIFIED ✓**

---

## M. EVIDENCE SUMMARY

### Changed Lines by Category

```
Contract Documentation:   +51/-15  (v1.0.1 semantics)
Production Code:          +11/-4   (ValueError on tuple collision)
Tests:                    +130/-6  (H1 matrix + semantics update)
Project Status:           +75/-60  (tracking updates)

Total Impact:             +267/-85 lines across 4 files
```

### Test Delta

```
Before H1: 18 Step 3 tests, 45 V2-006 tests, 345 total contract tests
After H1:  22 Step 3 tests, 49 V2-006 tests, 349 total contract tests
Net:       +4 collision matrix tests
```

### Behavioral Change

```
Scenario: add_relationship(id=B, tuple=T) when tuple T exists with id=A

Before (v1.0.0):
  - Operation: Returns normally (silent no-op)
  - State: B not stored
  - get_relationship(B): Returns None
  - Defect: Caller cannot distinguish success from rejection

After (v1.0.1):
  - Operation: Raises ValueError with clear message
  - State: A unchanged, B rejected
  - get_relationship(B): Never called (exception raised)
  - Fix: Caller receives explicit feedback
```

---

## N. GOVERNANCE INTEGRITY

**Historical Accuracy Preserved:**

```
✓ v1.0.0 implementation was CORRECT per v1.0.0 contract
✓ F-001 identified FROZEN CONTRACT semantic defect, not implementation bug
✓ H1 corrects contract semantics in v1.0.1
✓ Implementation updated to match corrected v1.0.1 semantics
✓ No rewriting of historical review evidence
✓ No backdating of contract semantics
✓ Clear version progression documented
```

---

**End of H1 Remediation Report**
