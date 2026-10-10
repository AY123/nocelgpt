# V2-006 Task Identity Reconciliation

**Change ID**: CHG-2026-10-08-V2-006-IDENTITY  
**Date**: 2026-10-08  
**Type**: Governance - Task Identity Split and Rehoming  
**Authority**: Project Owner Decision  
**Plan Version**: 1.3.0 → 1.3.1

---

## Executive Summary

This change record documents the formal reconciliation of V2-006 task identity conflict discovered during post-consolidation SSOT audit. The conflict arose between the historical machine task definition and the implemented and independently accepted contract.

**Decision**: Formal scope split and rehoming  
**Action**: V2-006 retained for implemented scope; unimplemented requirements rehomed to new V2-061  
**Impact**: Plan version 1.3.1, task count 60 → 61

---

## 1. Historical Machine V2-006 Scope

**Original Machine Definition** (implementation-backlog.yaml):
```yaml
task_id: V2-006
title: Character relationship knowledge core
goal: 合法派生字段和非默认值往返不丢失
artifacts:
  - src/anovel/domain/character.py
  - src/anovel/domain/knowledge.py
  - specs/schemas/character.schema.json
acceptance_criteria:
  - 合法派生字段和非默认值往返不丢失
  - 错误实体类型与生命周期被拒绝
  - 角色误信与客观事实并存且角色不能凭空知情
  - 角色目标/意图、误信与客观事件分别建模
  - 计划动作不被当作已发生事实
status: OPEN
```

**Scope**: Character-specific knowledge state including:
- Character lifecycle and type validation
- Objective facts vs subjective beliefs
- Knowledge acquisition boundaries
- Goals and intent modeling
- Planned action vs occurred event distinction

---

## 2. Implemented V2-006 Scope

**Implemented Contract**: V2-006 Implementation Contract v1.0.1

```
Title: Entity Relationship Tracking
Contract: docs/V2-006_IMPLEMENTATION_CONTRACT.md v1.0.1
Status: CLOSED
Closure SHA: bba1061ef27669ece55530bfdd846767b2fe21af
Tag: v2.006-complete
```

**Artifacts**:
- src/anovel/domain/relationship.py
- specs/schemas/entity-relationship.schema.json
- tests/contract/test_v2_006*.py (Steps 1-8)

**Scope**: General-purpose entity relationship tracking:
- RelationshipId (UUID v4 stable identity)
- RelationshipType (extensible string-based)
- EntityRelationship (5-field immutable dataclass)
- Directed relationships (no automatic inverse)
- Project isolation
- Create/delete/query operations
- In-memory RelationshipRegistry
- No persistence coupling
- No graph traversal/inference

**Acceptance Evidence**:
- Local: 447/447 contract tests, 226/226 architecture tests
- Remote: Pipeline 2925763616, 899/899 tests, 6/6 gates SUCCESS
- Independent acceptance: Complete (Steps 1-8 verified)

---

## 3. How the Drift Occurred

### Timeline

1. **Historical baseline** (Plan v1.3.0): Machine backlog defined V2-006 as character knowledge core
2. **Implementation phase**: V2-006 contract authored as "Entity Relationship Tracking"
3. **Authorization**: V2-006 Implementation Authorization granted for relationship tracking scope
4. **Implementation**: Steps 1-8 completed per relationship tracking contract
5. **Independent acceptance**: V2-006 closed at bba1061 (2026-10-08)
6. **Post-consolidation audit**: Task identity conflict detected

### Root Cause

The machine task definition (backlog.yaml) was not updated when the V2-006 contract scope was defined. The implementation proceeded under the authorized contract scope without synchronizing back to machine task metadata.

**Detection**: Post-V2-006 closure SSOT reconciliation audit identified that machine V2-006 definition did not match CLOSED implementation.

---

## 4. Why Completed V2-006 Remains Valid

The implemented V2-006 "Entity Relationship Tracking" is **independently verified and valid**:

1. ✅ Formal implementation contract (v1.0.1)
2. ✅ Independent contract review and approval
3. ✅ Implementation authorization grant
4. ✅ Step-by-step independent acceptance (Steps 1-8)
5. ✅ Local technical acceptance (447/447 tests)
6. ✅ Remote CI acceptance (899/899 tests, 6/6 gates)
7. ✅ Immutable closure tag (v2.006-complete)
8. ✅ H1 semantic correction ratified

**Conclusion**: V2-006 closure evidence is sound. The conflict is metadata reconciliation, not technical defect.

---

## 5. Unimplemented Requirements

The following requirements from historical machine V2-006 remain **unimplemented**:

### Character-Specific Semantics
- ❌ Character lifecycle and type validation
- ❌ Objective fact vs subjective belief distinction
- ❌ Character knowledge acquisition boundaries (cannot know without path)
- ❌ Goals and intent modeling (separate from belief)
- ❌ Planned action vs occurred event distinction
- ❌ Character.py domain model
- ❌ knowledge.py domain model
- ❌ character.schema.json

### Still Required
These requirements are **NOT discarded**. They represent necessary P1 narrative domain semantics.

---

## 6. Creation of V2-061

**New Task**: V2-061 Character Knowledge & Intent Core

```yaml
task_id: V2-061
title: Character Knowledge & Intent Core
phase: P1
priority: P0
status: OPEN
readiness: PLANNED
dependencies:
  - V2-005  # Entity identity foundation
  - V2-006  # Relationship edges for knowledge paths
```

**Purpose**: Preserve and implement the unimplemented character knowledge requirements from historical V2-006 definition.

**Scope**:
- Character-scoped knowledge state
- Objective fact vs subjective belief
- Goals and intent
- Knowledge acquisition boundaries
- Character lifecycle/type correctness
- Planned action vs occurred event distinction

**Artifacts**:
- src/anovel/domain/character.py
- src/anovel/domain/knowledge.py
- specs/schemas/character.schema.json
- tests/contract/test_v2_061.py

**Dependencies**: V2-061 depends on V2-006 because relationship edges provide the structural foundation for knowledge paths between entities.

---

## 7. Dependency Impact

### P1 Phase Membership

**Before**:
```
P1:
  - V2-005
  - V2-006
  - V2-007
  - V2-008
```

**After**:
```
P1:
  - V2-005  (CLOSED)
  - V2-006  (CLOSED)
  - V2-061  (OPEN)
  - V2-007  (OPEN)
  - V2-008  (OPEN)
```

### V2-008 Dependencies

**Before**:
```yaml
dependencies:
  - V2-006
  - V2-007
```

**After**:
```yaml
dependencies:
  - V2-006  # Relationship edges
  - V2-007  # Event timeline
  - V2-061  # Character knowledge/belief/intent
```

**Rationale**: V2-008 NarrativeDelta requires the complete P1 narrative state:
- V2-006 supplies relationship structure
- V2-061 supplies character knowledge semantics
- V2-007 supplies event/timeline/promise semantics

---

## 8. Acceptance Test Identity Impact

### AT-V2-006

**Historical**: Described character knowledge core acceptance

**New**: Entity Relationship Tracking acceptance
- Tests relationship identity, directed semantics, project isolation
- Tests create/delete/query operations
- Tests tuple uniqueness (H1 v1.0.1)
- Tests no persistence/provider coupling

### AT-V2-061

**New**: Character Knowledge & Intent Core acceptance (transferred from old AT-V2-006)
- Character lifecycle/type validation
- Objective vs subjective knowledge
- Knowledge acquisition boundaries
- Goals/intent modeling
- Planned vs occurred distinction

**Action**: test-catalog.yaml updated to reflect identity split.

---

## 9. Why V2-007...V2-060 Are NOT Renumbered

**Decision**: Task IDs V2-007 through V2-060 remain **unchanged**.

**Rationale**:
1. Mass renumbering creates extensive evidence/reference damage
2. Existing dependencies, findings, and references remain stable
3. Plan v1.3.1 explicitly documents 61-task baseline
4. Task ID gap is less disruptive than mass renumbering

**Impact**: Task count becomes 61 (was 60 in Plan v1.3.0).

---

## 10. Immutable Tag Preservation

**Critical Requirement**: Immutable closure tags must not be retargeted.

```
v2.005-complete → bd303e64dab6475bd12b69d273afa6c64eaa38ad (unchanged)
v2.006-complete → bba1061ef27669ece55530bfdd846767b2fe21af (unchanged)
```

**Verification**:
```bash
git rev-parse 'v2.005-complete^{commit}'
# bd303e64dab6475bd12b69d273afa6c64eaa38ad

git rev-parse 'v2.006-complete^{commit}'
# bba1061ef27669ece55530bfdd846767b2fe21af
```

The reconciliation creates a **descendant commit** of bba1061 for governance metadata only. The immutable closure revisions remain unchanged.

---

## 11. Plan Version Update

**Plan v1.3.0 Statement** (now obsolete):
> "The 60 original task identities, stages, and dependencies remain unchanged."

**Plan v1.3.1 Correction**:
> "Plan v1.3.1 introduces V2-061 to reconcile V2-006 task identity split. Task count: 61. Task IDs V2-001 through V2-060 remain stable; V2-061 is a governance addition, not a renumbering."

**Change Classification**: Governance task identity reconciliation (not feature addition).

---

## 12. Related Findings Reclassification

Historical V2-006 findings:
```
AR-03, CA-06, RR-05, RR-06, SUP-03, FND-003, EXT-005
```

**Reclassification**:
- **V2-006 (Relationship Tracking)**: AR-03 (relationship identity), RR-05 (relationship registry patterns)
- **V2-061 (Character Knowledge)**: CA-06 (character semantics), RR-06 (knowledge modeling), SUP-03 (belief/truth), FND-003 (knowledge foundations), EXT-005 (knowledge practices)

**Action**: Findings reassigned per semantic content.

---

## 13. Next Task Recommendation

**Next Task Candidate**: V2-061 Character Knowledge & Intent Core

**Rationale**:
1. Restores missing P1 semantic foundation
2. Required by V2-008 NarrativeDelta
3. Originally planned as serial P1 task before V2-007
4. Completes character domain before event timeline

**Authorization State**: NOT YET AUTHORIZED (requires contract refinement)

---

## 14. References

- V2-006 Implementation Contract v1.0.1: docs/V2-006_IMPLEMENTATION_CONTRACT.md
- V2-006 Authorization: docs/reports/V2-006_IMPLEMENTATION_AUTHORIZATION.md
- V2-006 Closure: docs/archive/v2-005-remediation/V2-006_FINAL_CLOSURE_CANDIDATE.md
- Post-consolidation audit: (This reconciliation task)
- Immutable closure tag: v2.006-complete (bba1061ef27669ece55530bfdd846767b2fe21af)

---

## 15. Approval

**Decision**: APPROVED  
**Authority**: Project Owner  
**Effective**: 2026-10-08  
**Plan Version**: 1.3.1

---

**END OF CHANGE RECORD**
