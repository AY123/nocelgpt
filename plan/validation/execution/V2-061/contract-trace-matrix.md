# V2-061 Contract Trace Matrix

**Contract Authority**: `04862fca053aff49c2aa334be72ba1f68296c8e4610ded1a631ea18e2b7929a0`  
**Contract Version**: 1.0.0  
**ADR-002**: `0aadbc379da2668673cfc21d97620fedeb7e07933f2334920fa5f264d5db90f8`

## AC-1: Knowledge Acquisition Provenance

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| DIRECT_OBSERVATION requires source_ref | knowledge.py CharacterKnowledge validation | test_direct_observation_requires_source_ref | test_direct_observation_missing_source_ref_reject | ❌ MISSING |
| COMMUNICATION requires source_character | knowledge.py validation | test_communication_requires_source_character | test_communication_missing_source_character_reject | ⚠️ WRONG ENUM |
| DOCUMENT requires source_ref | knowledge.py validation | test_document_requires_source_ref | test_document_missing_source_ref_reject | ❌ MISSING |
| INFERENCE requires basis_ref (non-empty) | knowledge.py validation | test_inference_requires_basis_ref | test_inference_missing_basis_ref_reject | ❌ MISSING |
| RUMOR requires source_character OR source_ref | knowledge.py validation | test_rumor_has_source | test_rumor_missing_both_sources_reject | ❌ MISSING |
| All sources empty = REJECT | knowledge.py validation | N/A | test_knowledge_no_provenance_reject | ❌ MISSING |

**Current Issues**:
- ❌ Using WITNESSED/TOLD_BY/ASSUMED/INITIAL_STATE instead of contract enums
- ❌ Missing source reference validation
- ❌ TOLD_BY only checks source_character, wrong enum name

## AC-2: Misbelief Representation

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| KNOWN + aligns_with_fact=False = INVALID | knowledge.py validation | N/A | test_known_misaligned_reject | ❌ MISSING |
| BELIEVED + aligns_with_fact=False = VALID | knowledge.py | test_believed_misaligned_valid | N/A | ❌ MISSING |
| SUSPECTED + aligns_with_fact=False = VALID | knowledge.py | test_suspected_misaligned_valid | N/A | ❌ MISSING |
| aligns_with_fact compare=False | knowledge.py field | test_aligns_with_fact_not_in_equality | N/A | ✓ EXISTS |

**Current Issues**:
- ❌ Using BELIEVES_TRUE/BELIEVES_FALSE/UNCERTAIN/UNAWARE instead of KNOWN/BELIEVED/SUSPECTED
- ❌ Missing KNOWN+misaligned validation

## AC-3: Intent vs Occurrence Separation

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| PlannedAction status: PLANNED only | character.py | test_planned_action_planned_status | test_planned_action_in_progress_reject | ❌ WRONG |
| PlannedAction status: CANCELLED only | character.py | test_planned_action_cancelled_status | test_planned_action_completed_reject | ❌ WRONG |
| CANCELLED + occurred_event_ref != None = REJECT | character.py validation | N/A | test_cancelled_with_occurrence_reject | ❌ MISSING |
| occurred_event_ref != None ≠ occurrence proof | test_v2_061.py | test_occurred_ref_is_reference_not_authority | N/A | ✓ EXISTS |
| PlannedActionId UUID v4 | character.py | test_planned_action_id_stable | N/A | ❌ MISSING |

**Current Issues**:
- ❌ Has IN_PROGRESS/COMPLETED status (V2-007 authority violation)
- ❌ Missing PlannedActionId type
- ❌ Using string action_id instead of PlannedActionId

## AC-4: Goal Lifecycle

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| ACTIVE/BLOCKED/ACHIEVED/FAILED/ABANDONED/SUPERSEDED | character.py Goal | test_goal_all_statuses | N/A | ❌ MISSING SUPERSEDED |
| ACTIVE → ACHIEVED valid | test logic | test_goal_active_to_achieved | N/A | ❌ MISSING |
| ACHIEVED → ACTIVE invalid | test logic | N/A | test_goal_achieved_to_active_reject | ❌ MISSING |
| GoalId UUID v4 | character.py | test_goal_id_stable | N/A | ❌ MISSING |
| priority optionality per contract | character.py Goal | test_goal_priority_optional | N/A | ⚠️ WRONG TYPE |

**Current Issues**:
- ❌ Missing SUPERSEDED status
- ❌ Using string goal_id instead of GoalId
- ❌ priority type wrong (int | None vs int in schema)

## AC-5: Project Isolation & Knowledge Boundary

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Character.project_id == EntityIdentity.project_id | validation | test_character_project_matches_identity | test_character_project_mismatch_reject | ❌ MISSING |
| knower cross-project = REJECT | validation | N/A | test_knower_cross_project_reject | ❌ MISSING |
| source_character cross-project = REJECT | validation | N/A | test_source_character_cross_project_reject | ❌ MISSING |
| Proposition subject/object cross-project = REJECT | validation | N/A | test_proposition_cross_project_reject | ❌ MISSING |
| knowledge provenance cross-project = REJECT | validation | N/A | test_knowledge_provenance_cross_project_reject | ❌ MISSING |

**Current Issues**:
- ❌ No project isolation validation implemented

## AC-6: Schema Round-Trip

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Real serialization → JSON → validation → deserialize | serialization.py | test_character_real_roundtrip | N/A | ❌ MISSING |
| BASE exact equality | roundtrip | test_base_exact_preservation | N/A | ⚠️ FAKE |
| DERIVED recomputed equivalent | roundtrip | test_derived_recomputation | N/A | ❌ MISSING |
| CACHE not persisted | roundtrip | test_cache_not_serialized | N/A | ⚠️ FAKE |
| Invalid entity_type = REJECT | validation | N/A | test_invalid_entity_type_reject | ❌ MISSING |
| Invalid lifecycle = REJECT | validation | N/A | test_invalid_lifecycle_reject | ❌ MISSING |

**Current Issues**:
- ❌ Test manually creates payload dict, not real serialization
- ❌ No production serializer/deserializer

## AC-7: Identity Authority Boundary

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Character has NO canonical_name field | character.py | test_character_no_canonical_name | N/A | ✓ CORRECT |
| Character has NO aliases field | character.py | test_character_no_aliases | N/A | ✓ CORRECT |
| Character.entity_id from V2-005 | character.py | test_entity_id_from_v2_005 | N/A | ✓ CORRECT |
| Get name via EntityRegistry | integration | test_get_name_via_registry | N/A | ❌ MISSING |

**Current Issues**:
- ✓ Authority boundary correctly maintained

## Additional Contract Requirements

### Character Lifecycle

| Requirement | Status |
|-------------|--------|
| PLANNED/ACTIVE/INACTIVE/DECEASED/SUPERSEDED | ❌ Missing PLANNED/SUPERSEDED |
| DECEASED cannot form new goals/intents (default) | ❌ No validation |
| PLANNED cannot have story-event knowledge | ❌ No validation |
| SUPERSEDED cannot be in new content refs | ❌ No validation |

### Entity Type Validation

| Requirement | Status |
|-------------|--------|
| entity_type != "CHARACTER" = REJECT | ❌ Not validated |

### Intent Model

| Requirement | Status |
|-------------|--------|
| IntentId UUID v4 | ❌ Using string |
| goal_ref optionality per contract | ⚠️ Check type |

### Proposition Collision Invariant

| Requirement | Status |
|-------------|--------|
| Same PropositionId + different BASE = REJECT | ❌ Not tested with real collision |
| knowledge dict key == proposition.proposition_id | ❌ Not validated |

### Schema Compliance

| Requirement | Status |
|-------------|--------|
| Use contract enums (KNOWN/BELIEVED/SUSPECTED) | ❌ Wrong enums |
| Use contract acquisition sources | ❌ Wrong enums |
| Use contract PlannedAction statuses | ❌ Wrong enums |
| BASE fields only | ✓ Correct |
| No CACHE in schema | ✓ Correct |

## Summary

**Total Requirements**: 50+  
**Implemented Correctly**: 8  
**Partially Implemented**: 6  
**Missing/Wrong**: 36+

**Critical Failures**:
1. Wrong KnowledgeLevel enum (BELIEVES_TRUE vs KNOWN)
2. Wrong AcquisitionSource enum (WITNESSED vs DIRECT_OBSERVATION)
3. Wrong ActionStatus enum (has IN_PROGRESS/COMPLETED)
4. Missing ID types (GoalId, IntentId, PlannedActionId)
5. Missing provenance validation
6. Missing project isolation validation
7. Missing real serialization/deserialization
8. Missing lifecycle validation
9. Missing entity type validation
10. Missing proposition collision detection
