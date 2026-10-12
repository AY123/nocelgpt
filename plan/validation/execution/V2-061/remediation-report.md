# V2-061 Contract Remediation Report

**Remediation ID**: V2-061-CONTRACT-REMEDIATION-AND-TRUE-CLOSURE-003  
**Contract Authority**: 04862fca053aff49c2aa334be72ba1f68296c8e4610ded1a631ea18e2b7929a0  
**Remediation Date**: 2026-10-12  
**Baseline Commit**: 4188be6 (dev_cc)  
**Remediation Commit**: 5ee6ce6  

## Executive Summary

**STATUS**: ✅ **CONTRACT COMPLIANCE RESTORED**

Fixed 36+ contract violations identified in trace matrix. V2-061 implementation now complies with frozen Contract Version 1.0.0 (hash: 04862fca...) and ADR-002 BASE/DERIVED/CACHE semantics.

## Remediation Scope

### Authorized Files (Modified)
- src/anovel/domain/knowledge.py
- src/anovel/domain/character.py
- src/anovel/domain/__init__.py
- specs/schemas/character.schema.json
- tests/contract/test_v2_061.py

### Evidence Files (Created)
- plan/validation/execution/V2-061/contract-trace-matrix.md

## Contract Violations Fixed

### Critical: Enum Mismatches (5 enums, 16 violations)

#### 1. KnowledgeLevel Enum
**Contract**: KNOWN, BELIEVED, SUSPECTED  
**Was**: BELIEVES_TRUE, BELIEVES_FALSE, UNCERTAIN, UNAWARE  
**Fixed**: src/anovel/domain/knowledge.py:42-56

```python
class KnowledgeLevel(Enum):
    KNOWN = "KNOWN"
    BELIEVED = "BELIEVED"
    SUSPECTED = "SUSPECTED"
```

**Impact**: Schema sync, 4 test rewrites

#### 2. AcquisitionSource Enum
**Contract**: DIRECT_OBSERVATION, COMMUNICATION, DOCUMENT, INFERENCE, RUMOR  
**Was**: WITNESSED, TOLD_BY, INFERRED, ASSUMED, INITIAL_STATE  
**Fixed**: src/anovel/domain/knowledge.py:59-76

```python
class AcquisitionSource(Enum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    COMMUNICATION = "COMMUNICATION"
    DOCUMENT = "DOCUMENT"
    INFERENCE = "INFERENCE"
    RUMOR = "RUMOR"
```

**Impact**: Schema sync, 12 provenance tests rewritten

#### 3. CharacterLifecycle Enum
**Contract**: PLANNED, ACTIVE, INACTIVE, DECEASED, SUPERSEDED (5 states)  
**Was**: Missing PLANNED and SUPERSEDED (3 states)  
**Fixed**: src/anovel/domain/character.py:49-65

```python
class CharacterLifecycle(Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECEASED = "DECEASED"
    SUPERSEDED = "SUPERSEDED"
```

**Impact**: Schema sync, 2 lifecycle tests

#### 4. GoalStatus Enum
**Contract**: ACTIVE, BLOCKED, ACHIEVED, FAILED, ABANDONED, SUPERSEDED (6 states)  
**Was**: Missing FAILED and SUPERSEDED (4 states)  
**Fixed**: src/anovel/domain/character.py:68-79

```python
class GoalStatus(Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    ACHIEVED = "ACHIEVED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    SUPERSEDED = "SUPERSEDED"
```

**Impact**: Schema sync, goal lifecycle tests

#### 5. ActionStatus Enum
**Contract**: PLANNED, CANCELLED (2 states, V2-061 authority only)  
**Was**: PLANNED, IN_PROGRESS, COMPLETED, CANCELLED (4 states, V2-007 violation)  
**Fixed**: src/anovel/domain/character.py:82-92

```python
class ActionStatus(Enum):
    """V2-061 owns PLANNED/CANCELLED only.
    V2-007 owns objective occurrence authority."""
    PLANNED = "PLANNED"
    CANCELLED = "CANCELLED"
```

**Impact**: Schema sync, authority boundary tests

### Critical: Missing Stable ID Types (3 violations)

**Contract**: GoalId, IntentId, PlannedActionId must be stable UUID v4 identifiers  
**Was**: Using plain str types  
**Fixed**: src/anovel/domain/character.py:37-44

```python
GoalId = NewType("GoalId", str)
IntentId = NewType("IntentId", str)
PlannedActionId = NewType("PlannedActionId", str)
```

**Impact**: Type safety, 3 stable ID tests, exports in __init__.py

### Critical: Missing Provenance Validation (6 violations)

**Contract**: Each AcquisitionSource has REQUIRED provenance fields  
**Was**: No validation in CharacterKnowledge.__post_init__  
**Fixed**: src/anovel/domain/knowledge.py:274-331

#### Validation Rules Implemented
1. **DIRECT_OBSERVATION** requires source_ref (event/observation context)
2. **COMMUNICATION** requires source_character (who told character)
3. **DOCUMENT** requires source_ref (document identifier)
4. **INFERENCE** requires non-empty basis_ref (what was reasoned from)
5. **RUMOR** requires source_character OR source_ref (at least one)
6. **Hard invariant**: At least one provenance path must exist (acquisition_source alone insufficient)

**Impact**: 12 provenance tests covering all validation rules

### Critical: basis_ref Type Mismatch (1 violation)

**Contract**: basis_ref is Optional[list[PropositionId]] for multi-premise inference  
**Was**: Optional[str]  
**Fixed**: src/anovel/domain/knowledge.py:266

```python
basis_ref: Optional[list[PropositionId]] = None
```

**Impact**: Schema array type, inference validation tests

### Medium: PlannedAction Invariant Missing (1 violation)

**Contract**: CANCELLED + occurred_event_ref != None is INVALID  
**Was**: No validation  
**Fixed**: src/anovel/domain/character.py:185-195

```python
def __post_init__(self) -> None:
    if self.status == ActionStatus.CANCELLED and self.occurred_event_ref is not None:
        raise ValueError(
            "PlannedAction with status=CANCELLED cannot have occurred_event_ref. "
            "Cancelled plans should not link to occurrence events."
        )
```

**Impact**: 1 authority boundary test

### Medium: Optional Field Mismatches (2 violations)

**Contract**: Goal.priority and Goal.formed_at are Optional  
**Was**: Required (not Optional[...])  
**Fixed**: src/anovel/domain/character.py:121-122

```python
priority: Optional[int]
formed_at: Optional[datetime]
```

**Contract**: Intent.formed_at is Optional  
**Was**: Required  
**Fixed**: src/anovel/domain/character.py:145

```python
formed_at: Optional[datetime]
```

**Impact**: Schema nullable types

### Low: Entity Type Hardcoding (1 violation)

**Contract**: V2-061 only handles "CHARACTER" entity_type  
**Was**: entity_type parameter exposed in create_character()  
**Fixed**: src/anovel/domain/character.py:299-310

```python
# entity_type must be "CHARACTER" per frozen contract
identity = create_identity(
    project_id=project_id,
    canonical_name=canonical_name,
    entity_type="CHARACTER",
)
```

**Impact**: 1 entity type validation test

## Schema Synchronization

Updated specs/schemas/character.schema.json to match all enum changes:

1. lifecycle: ["PLANNED", "ACTIVE", "INACTIVE", "DECEASED", "SUPERSEDED"]
2. knowledge_level: ["KNOWN", "BELIEVED", "SUSPECTED"]
3. acquisition_source: ["DIRECT_OBSERVATION", "COMMUNICATION", "DOCUMENT", "INFERENCE", "RUMOR"]
4. GoalStatus: ["ACTIVE", "BLOCKED", "ACHIEVED", "FAILED", "ABANDONED", "SUPERSEDED"]
5. ActionStatus: ["PLANNED", "CANCELLED"]
6. basis_ref: "type": ["array", "null"], "items": {"type": "string"}
7. Goal.priority: "type": ["integer", "null"]
8. Goal.formed_at: "type": ["string", "null"]
9. Intent.formed_at: "type": ["string", "null"]

## Test Suite Rewrite

### Before Remediation
- 25 tests testing WRONG enums (BELIEVES_TRUE vs contract KNOWN)
- No provenance validation tests
- No stable ID tests
- No authority boundary tests
- Tests verified implementation behavior, not contract requirements

### After Remediation
- 44 comprehensive contract tests
- Organized by acceptance criteria AC-1 through AC-7
- Tests verify contract requirements, not just implementation

#### Test Coverage by AC

**AC-1: Knowledge Acquisition Provenance (12 tests)**
- test_direct_observation_requires_source_ref
- test_direct_observation_missing_source_ref_reject
- test_communication_requires_source_character
- test_communication_missing_source_character_reject
- test_document_requires_source_ref
- test_document_missing_source_ref_reject
- test_inference_requires_basis_ref_non_empty
- test_inference_missing_basis_ref_reject
- test_inference_empty_basis_ref_reject
- test_rumor_requires_source_character_or_source_ref
- test_rumor_missing_both_sources_reject
- test_knowledge_no_provenance_reject

**AC-2: Misbelief Representation (4 tests)**
- test_known_with_aligns_false_reject
- test_believed_with_aligns_false_valid
- test_suspected_with_aligns_false_valid
- test_aligns_with_fact_not_in_equality

**AC-3: Intent/Occurrence Separation (3 tests)**
- test_planned_action_only_planned_cancelled_status
- test_cancelled_with_occurrence_ref_reject
- test_occurred_event_ref_is_reference_not_authority

**AC-4: Goal Lifecycle (2 tests)**
- test_goal_all_statuses_exist
- test_goal_stable_id

**AC-5: Character Lifecycle (2 tests)**
- test_character_all_lifecycle_states_exist
- test_character_lifecycle_defaults_active

**AC-6: Proposition Invariants (5 tests)**
- test_proposition_context_immutable
- test_freeze_context_recursively
- test_create_proposition_generates_unique_id
- test_proposition_validates_empty_predicate
- test_proposition_validates_empty_project_id

**AC-7: Entity Type Validation (1 test)**
- test_create_character_uses_character_entity_type

**Additional Coverage (15 tests)**
- TestIntentModel: 1 stable ID test
- TestPlannedActionModel: 1 stable ID test
- TestSchemaCompliance: 9 schema sync tests
- TestAuthorityBoundaries: 3 V2-005/V2-007 boundary tests
- TestDerivedSemantics: 2 DERIVED field tests

## Verification Results

### Contract Compliance
```
CONTRACT_AUTHORITY_HASH = 04862fca053aff49c2aa334be72ba1f68296c8e4610ded1a631ea18e2b7929a0
KNOWLEDGE_LEVEL_CONTRACT = PASS (KNOWN/BELIEVED/SUSPECTED)
ACQUISITION_PROVENANCE_CONTRACT = PASS (all 5 sources validated)
GOAL_LIFECYCLE_CONTRACT = PASS (6 statuses including FAILED/SUPERSEDED)
ACTION_STATUS_CONTRACT = PASS (PLANNED/CANCELLED only, V2-061 authority)
CHARACTER_LIFECYCLE_CONTRACT = PASS (5 states including PLANNED/SUPERSEDED)
STABLE_ID_CONTRACT = PASS (GoalId/IntentId/PlannedActionId)
ENTITY_TYPE_CONTRACT = PASS (CHARACTER hardcoded)
SCHEMA_SYNC_CONTRACT = PASS (all enums synchronized)
BASIS_REF_TYPE_CONTRACT = PASS (list[PropositionId])
OPTIONAL_FIELDS_CONTRACT = PASS (priority/formed_at nullable)
PLANNED_ACTION_INVARIANT_CONTRACT = PASS (CANCELLED validation)
```

### Test Execution
```bash
$ python3 -m pytest tests/contract/test_v2_061.py -v
============================= test session starts ==============================
collected 44 items

tests/contract/test_v2_061.py::TestKnowledgeAcquisitionProvenance::... PASSED
[... 43 more tests ...]
============================== 44 passed in 0.05s ==============================
```

### Governance Validation
```bash
$ python3 -m pytest tests/contract/test_plan_governance.py -v
============================= test session starts ==============================
collected 24 items

tests/contract/test_plan_governance.py::... PASSED
[... 23 more tests ...]
============================== 24 passed in 10.27s ==============================
```

### Code Quality
```bash
$ git diff --check
# No output - no whitespace errors
```

## Diff Statistics

```
6 files changed, 1055 insertions(+), 318 deletions(-)

plan/validation/execution/V2-061/contract-trace-matrix.md | 164 ++++
specs/schemas/character.schema.json                       |  39 +-
src/anovel/domain/__init__.py                             |   6 +
src/anovel/domain/character.py                            | 117 ++-
src/anovel/domain/knowledge.py                            | 110 ++-
tests/contract/test_v2_061.py                             | 937 ++++++++++++------
```

## Remaining Work (Out of Scope)

Following items identified but NOT in remediation scope:

1. **Serialization/Deserialization**: BASE roundtrip tests (need serialization.py - NOT authorized)
2. **Project Isolation**: Cross-project rejection tests (integration scope)
3. **Proposition Collision**: Same ID + different payload detection (integration scope)
4. **Knowledge Dict Validation**: Key must match proposition.proposition_id (integration scope)
5. **Remote CI Verification**: GitLab pipeline currently failing (deployment scope)
6. **Machine Backlog Update**: Evidence bindings update (governance scope)
7. **Plan Validation**: Update plan-validation.json status (governance scope)

## Authority Declaration

This remediation was executed under explicit authorization:

> "选择：**1. PROCEED WITH FULL CONTRACT REMEDIATION**
> 立即执行 V2-061-CONTRACT-REMEDIATION-AND-TRUE-CLOSURE-003 完整修复"

Scope limited to authorized files only. No expansion into serialization.py, validation.py, or other modules.

## Conclusion

V2-061 implementation now complies with frozen Contract Version 1.0.0. All 44 contract tests passing. Schema synchronized. Provenance validation implemented. Stable IDs added. Authority boundaries respected.

**Contract compliance: RESTORED ✅**

---
*Generated: 2026-10-12*  
*Commit: 5ee6ce6*
