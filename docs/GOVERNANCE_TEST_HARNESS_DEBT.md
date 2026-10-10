# Governance Test Harness Debt

**Severity**: MEDIUM  
**Type**: TEST_HARNESS / GOVERNANCE_REGRESSION  
**Status**: OPEN  
**Created**: 2026-10-09

---

## Description

Governance test suite positive fixture isolation for V2-005/V2-006 is incomplete.

**Current State**:
- `test_governance.py`: 46 tests, 46 FAILED
- `test_ai_execution.py`: 36 tests, 36 FAILED (dependencies)
- Root cause: V2-005/V2-006 historical closure evidence deeply embedded across multiple machine sources

**Attempted Fix** (reverted in c7d06cb):
- WIP fixture normalization approach
- Failed to achieve clean positive baseline
- Evidence references remain in phase-gates, test-catalog, and other structures

---

## Impact

### DOES NOT BLOCK:
- ✅ V2-061 architecture analysis
- ✅ Contract refinement
- ✅ ADR-002 drafting
- ✅ Acceptance criteria design
- ✅ Independent contract review

### BLOCKS:
- ❌ ADR-002 formal ratification
- ❌ V2-061 OPEN → IN_PROGRESS status change
- ❌ Implementation execution packet creation
- ❌ Implementation authorization
- ❌ Production implementation
- ❌ Task closure

---

## Requirements for Resolution

**Before V2-061 implementation authorization**:
1. `test_governance.py` must achieve PASS status
2. `test_ai_execution.py` must achieve PASS status
3. Positive fixture baseline must have 0 errors
4. All absence grandfathering tests must pass

**Technical Approach** (deferred):
- Redesign fixture architecture to handle historical CLOSED tasks
- Implement cross-file evidence reference normalization
- Consider separate fixture paths for "clean" vs "historical" states

---

## Production Impact

**NONE** - This affects test harness only.

**Production validator remains functional**:
- ✅ `validate_plan --check`: 64 findings (registered debt)
- ✅ `validate_plan --self-test`: PASS (32 cases)
- ✅ Grandfather enforcement: CORRECT
- ✅ V2-005 machine artifact: CORRECTED

---

## Related Commits

- `9f705d9`: V2-005 artifact fix (entity-identity.schema.json) ✓
- `b7a97fe`: WIP fixture isolation attempt (FAILED)
- `c7d06cb`: Revert WIP attempt ✓

---

**Next Action**: Proceed with V2-061 Contract Refinement while test harness remains in debt status.
