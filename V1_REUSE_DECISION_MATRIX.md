# V1 Reuse Decision Matrix

**Document ID**: V1-REUSE-001  
**Version**: 1.0  
**Status**: NORMATIVE  
**Date**: 2026-09-19  
**Authority**: V1-MIGRATION-BASELINE  
**Purpose**: Define V1 code reuse strategy for V2 greenfield implementation

---

## Executive Summary

**Decision**: V2 is a **greenfield implementation**. V1 code is **NOT reused** directly.

**Rationale**:
- V1 had architectural debt (23 identified failures)
- V2 requires genre-first architecture (V1 had genre as afterthought)
- Clean canonical boundary needed (V1 had multiple write paths)
- User directive: greenfield approach

**V1 Value Extraction**:
- ✅ Design patterns preserved (state-as-projection, provenance)
- ✅ Lessons learned incorporated (23 failures → regression tests)
- ✅ Domain knowledge preserved (narrative entities, workflow stages)
- ❌ Direct code reuse rejected

---

## 1. Reuse Categories

| Category | Decision | Rationale |
|----------|----------|-----------|
| **Architecture Patterns** | ADAPT | State-as-projection, event sourcing - proven concepts |
| **Domain Models** | REDESIGN | Genre-first requires fundamental restructuring |
| **Business Logic** | REWRITE | Canon boundary violations, need clean implementation |
| **Test Fixtures** | CONVERT | V1 failures become V2 regression tests |
| **Database Schema** | GREENFIELD | New schema for genre-extensible canon |
| **API Contracts** | REDESIGN | New contract model with genre awareness |

---

## 2. V1 Patterns Preserved in V2

### 2.1 State as Projection ✅ ADOPT

**V1 Pattern**:
```python
# Canon state = fold(event log)
canonical_state = project_from_events(event_log)
```

**V2 Adoption**: CANONICAL_STATE_SPEC Section 0, V2-012 (Snapshot rebuild)

**Status**: Core V2 design principle

### 2.2 Single Write Boundary ✅ ADAPT

**V1 Pattern**:
```python
# MintService was sole Canon writer (violated in practice)
```

**V2 Adaptation**: 
- CanonCommitService (V2-010) - strengthened with architecture fitness tests
- INV-004: Only CanonCommitService can write Canon
- Enforcement via import rules

**Status**: V2 strengthens V1 concept with enforcement

### 2.3 Provenance Tracking ✅ ADAPT

**V1 Pattern**:
```python
# RunFingerprint tracked generation context
```

**V2 Adaptation**:
- Artifact envelope (ARTIFACT_LIFECYCLE_REGISTER Section 1)
- RunFingerprint + ModelFingerprint
- ADR-0015

**Status**: V2 formalizes and extends V1 concept

### 2.4 Facts vs Derived Separation ✅ PRESERVE

**V1 Pattern**:
```python
# Canon stores facts, not judgments
```

**V2 Preservation**:
- DATA_OWNERSHIP_MATRIX separates T3 (Canon facts) from T7 (Judge outputs)
- P-003: Draft ≠ Canon
- Quality scores advisory only

**Status**: Core V2 principle

---

## 3. V1 Failures Converted to V2 Regression Tests

**Source**: V1_REGRESSION_ASSET_REGISTER.md (23 failures documented)

### Critical Regressions (Must Not Repeat)

| V1 Failure | V2 Regression Test | V2 Prevention |
|------------|-------------------|---------------|
| **F01**: Secret in git | TEST-SEC-001 | V2-004 secret scan CI gate |
| **F02**: Non-atomic mint | TEST-CANON-002 | V2-011 CAS, ADR-0005 |
| **F03**: BLOCKED doesn't block | TEST-WF-001 | V2-020 fail-closed, ADR-0009 |
| **F09**: Multiple verdict centers | TEST-CANON-003 | Single ProductionState |
| **F06**: Hardcoded contracts | TEST-CONTRACT-001 | V2-017 Contract Compiler |
| **F08**: Fail-open defaults | TEST-WF-002 | BLOCK on missing, ADR-0009 |

**Status**: All 23 V1 failures mapped to V2 test requirements

---

## 4. V1 Code Disposition

### 4.1 V1 Runtime Code (59,359 lines)

**Decision**: Archive, do not port

**Location**: Git history (commit 63b60f7 and earlier), removed from working tree (commit 03c68b0)

**Value Extraction Method**:
- Forensic analysis completed (V1_FORENSIC_LESSONS.md)
- Failure catalog created (V1_REGRESSION_ASSET_REGISTER.md)
- Design patterns documented (DATA_OWNERSHIP_MATRIX, CANONICAL_STATE_SPEC)

### 4.2 V1 Test Code (43,418 lines)

**Decision**: Convert failing tests to V2 regression fixtures

**Conversion Strategy**:
- 23 V1 test failures → V2 regression test requirements
- V1 test structure NOT reused (new pytest structure)
- Test data preserved as fixtures where relevant

### 4.3 V1 Domain Knowledge

**Decision**: Extract and formalize in V2 specs

**Extraction Complete**:
- ✅ Narrative entities → NARRATIVE_DOMAIN_SPEC
- ✅ Workflow stages → PRODUCTION_WORKFLOW_SPEC
- ✅ Quality dimensions → QUALITY_SPEC
- ✅ Canon operations → CANONICAL_STATE_SPEC

---

## 5. Migration Risk Assessment

### 5.1 Risk: Lost V1 Domain Knowledge

**Mitigation**:
- ✅ Comprehensive V1 forensic analysis completed
- ✅ All V1 concepts mapped to V2 specs
- ✅ V1 code preserved in git history for reference

**Status**: CONTROLLED

### 5.2 Risk: Regression of V1 Bugs

**Mitigation**:
- ✅ 23 V1 failures cataloged
- ✅ Regression test requirements defined
- ✅ V2-004 includes regression test CI gate

**Status**: CONTROLLED

### 5.3 Risk: Genre Refactor Repeats V1 Mistake

**Mitigation**:
- ✅ V2 makes genre foundational (P3 Genre Kernel)
- ✅ GenrePack architecture from day 1
- ✅ LESSON-V1-001: "Genre Afterthought" explicitly addressed

**Status**: CONTROLLED

---

## 6. V1 Availability for Reference

**Git History**: V1 code remains available in commits prior to 03c68b0

**Access Method**:
```bash
# View V1 code at last V1 commit
git show 63b60f7:ainovel/

# View specific V1 file
git show 63b60f7:ainovel/runtime/core/mint_service.py
```

**Use Cases**:
- Reference implementation details during V2 development
- Verify V1 behavior for regression test creation
- Historical context for design decisions

**Not Allowed**:
- Direct code copy-paste from V1 to V2
- V1 architecture patterns without greenfield redesign review

---

## 7. Success Criteria

**V1 Reuse Strategy Succeeds If**:

✅ All V1 lessons incorporated in V2 design  
✅ 0 V1 critical failures repeated in V2  
✅ V2 achieves genre-first architecture (V1 couldn't)  
✅ V2 Canon boundary cleaner than V1  
✅ V2 test coverage includes V1 regression scenarios  

**Measurement**:
- Regression test suite covers all 23 V1 failures
- Architecture fitness tests enforce V1 lesson mitigations
- M1 milestone demonstrates genre-first capability (impossible in V1)

---

## 8. Related Documents

- **V1_REGRESSION_ASSET_REGISTER.md**: 23 V1 failures → V2 regression tests
- **V1_FORENSIC_LESSONS.md**: Deep V1 failure analysis (referenced by convergence)
- **CANONICAL_STATE_SPEC**: Incorporates V1 state-as-projection pattern
- **ARCHITECTURE_READINESS_REPORT.md Section 5**: V1 lesson incorporation assessment

---

## 9. Change Control

**This decision is FROZEN** as part of convergence baseline.

**Rationale for Freeze**:
- User directive: greenfield V2
- V1 debt documented (23 failures)
- V2 architecture requires genre-first (incompatible with V1 structure)

**Any proposal to reuse V1 code directly requires**:
- Formal ADR
- Demonstration that V1 code satisfies V2 architecture fitness tests
- Proof that genre-first architecture not compromised

**Current Status**: No V1 code reuse proposals under consideration

---

**END OF V1 REUSE DECISION MATRIX**

**Date**: 2026-09-19  
**Verdict**: GREENFIELD V2, V1 LESSONS PRESERVED, V1 CODE ARCHIVED
