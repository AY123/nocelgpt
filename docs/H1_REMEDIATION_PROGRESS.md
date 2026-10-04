# H1 Focused Remediation Script

**Scope**: Fix 8 specific issues only
**Branch**: work/h1-focused-remediation
**Target**: Delta review readiness

---

## Batch Remediation Plan

Due to token constraints, I'll create a comprehensive remediation script for you to review and approve before execution.

### H1-01: Status Convergence (PARTIAL COMPLETE)
✅ V2-005_REFINEMENT_SUMMARY.md - major declarations fixed
⏳ V2-005_DECISION_GATES.md - Gate 3/4 need rewrite
⏳ Other documents need verification

### H1-02: UUID Convergence
Files need ULID→UUID cleanup:
- V2-005_TASK_REFINEMENT.md (lines 953, 1053, 1057, 1111, 1142)
- V2-005_REFINEMENT_SUMMARY.md (check for ULID mentions)
- V2-005_DECISION_GATES.md (line 99, 172)
- V2-005_IMPLEMENTATION_CONTRACT.md (JSON example with ULID)

### H1-03: EntityId Validator
- Change `pattern.match()` to `pattern.fullmatch()`
- Add explicit negative test cases

### H1-04: Schema Enforcement
- Add UUID v4 pattern to JSON Schema

### H1-05: Full-Width Space
- Change algorithm to explicit `s.replace("　", "")` before space collapse

### H1-06: Storage Model
- Clarify input/stored/lookup distinction

### H1-07: Equality Terminology
- Replace "bitwise equality" with "value equality"

### H1-08: Package Integrity
- Regenerate manifest from actual files

---

## Recommendation

Given token constraints and the systematic nature of these changes:

**Option A** (Recommended): 
- Commit current partial H1-01 progress
- Provide you with detailed search/replace instructions
- You verify and execute remaining changes
- AI performs final validation

**Option B**:
- AI continues with remaining items
- Risk of token exhaustion before completion

Which approach do you prefer?
