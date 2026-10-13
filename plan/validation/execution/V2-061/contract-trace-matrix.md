# V2-061 Contract Trace Matrix

**Contract Authority**: `04862fca053aff49c2aa334be72ba1f68296c8e4610ded1a631ea18e2b7929a0`  
**Contract Version**: 1.0.0  
**ADR-002**: `0aadbc379da2668673cfc21d97620fedeb7e07933f2334920fa5f264d5db90f8`  
**Implementation Checkpoint**: `0478deea2a56f1d526654bef61f493fca2f196df`

**Test Status**: 112/112 PASS (domain contract complete with delta requirements)

## AC-1: Knowledge Acquisition Provenance

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| DIRECT_OBSERVATION requires source_ref | CharacterKnowledge.__post_init__ | test_v2_061.py line 642 | test_v2_061.py line 656 | ✅ IMPL |
| COMMUNICATION requires source_character | CharacterKnowledge.__post_init__ | test_v2_061.py line 670 | test_v2_061.py line 684 | ✅ IMPL |
| DOCUMENT requires source_ref | CharacterKnowledge.__post_init__ | test_v2_061.py line 698 | test_v2_061.py line 712 | ✅ IMPL |
| INFERENCE requires basis_ref (non-empty) | CharacterKnowledge.__post_init__ | test_v2_061.py line 726 | test_v2_061.py line 742 | ✅ IMPL |
| RUMOR requires source_character | CharacterKnowledge.__post_init__ | test_v2_061.py line 757 | test_v2_061.py line 771 | ✅ IMPL |

**Implementation**: `src/anovel/domain/knowledge.py` lines 372-410  
**Tests**: `tests/contract/test_v2_061.py` TestProvenanceHardRules class

## AC-2: Misbelief Representation

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| KNOWN + aligns_with_fact=False = INVALID | CharacterKnowledge.__post_init__ | N/A | test_v2_061.py line 787 | ✅ IMPL |
| BELIEVED + aligns_with_fact=False = VALID | CharacterKnowledge dataclass | test_v2_061.py line 800 | N/A | ✅ IMPL |
| aligns_with_fact compare=False (CACHE) | CharacterKnowledge field | test_v2_061.py line 814 | N/A | ✅ IMPL |

**Implementation**: `src/anovel/domain/knowledge.py` lines 364-370  
**Tests**: `tests/contract/test_v2_061.py` TestMisbeliefRepresentation class

## AC-3: Intent vs Occurrence Separation

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| PlannedAction status: PLANNED or CANCELLED only | ActionStatus enum | test_v2_061.py line 405 | N/A | ✅ IMPL |
| CANCELLED + occurred_event_ref != None = REJECT | PlannedAction.__post_init__ | N/A | test_v2_061.py line 447 | ✅ IMPL |
| occurred_event_ref is reference, not authority | Documentation | test_v2_061.py line 465 | N/A | ✅ IMPL |
| PlannedActionId UUID v4 stable | PlannedActionId NewType | test_v2_061.py line 554 | N/A | ✅ IMPL |

**Implementation**: `src/anovel/domain/character.py` lines 75-80, 185-195  
**Tests**: `tests/contract/test_v2_061.py` TestIntentOccurrenceSeparation + TestPlannedActionModel classes

## AC-4: Goal Lifecycle

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Goal statuses: ACTIVE/BLOCKED/ACHIEVED/FAILED/ABANDONED/SUPERSEDED | GoalStatus enum | test_v2_061.py line 492 | N/A | ✅ IMPL |
| GoalId UUID v4 stable | GoalId NewType | test_v2_061.py line 502 | N/A | ✅ IMPL |
| ABANDONED → SUPERSEDED transition acceptance | Goal dataclass | test_v2_061.py line 524 | N/A | ✅ IMPL |
| Goal transitions validated | lifecycle.py validate_goal_transition | test_v2_061_lifecycle.py | N/A | ✅ IMPL |
| ACTIVE → ACHIEVED valid | transition_goal() | test_v2_061_lifecycle.py line 171 | N/A | ✅ IMPL |
| ACHIEVED → ACTIVE invalid | validate_goal_transition | N/A | test_v2_061_lifecycle.py line 197 | ✅ IMPL |

**Implementation**: `src/anovel/domain/character.py` lines 37-85  
**Lifecycle**: `src/anovel/domain/lifecycle.py` lines 171-233  
**Tests**: `tests/contract/test_v2_061.py` TestGoalLifecycle + `tests/contract/test_v2_061_lifecycle.py` TestGoalTransitions

## AC-5: Project Isolation & Knowledge Boundary

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Character.project_id == EntityIdentity.project_id | validate_project_isolation | test_v2_061.py line 893 | test_v2_061.py line 912 | ✅ IMPL |
| source_character cross-project = REJECT | validate_project_isolation | test_v2_061.py line 929 | test_v2_061.py line 948 | ✅ IMPL |
| Entity entity_type must be CHARACTER | validate_project_isolation | test_v2_061.py line 929 | test_v2_061.py line 960 | ✅ IMPL |
| Proposition subject cross-project = REJECT | validate_project_isolation | N/A | test_v2_061.py line 981 | ✅ IMPL |
| Proposition object cross-project = REJECT | validate_project_isolation | N/A | test_v2_061.py line 1022 | ✅ IMPL |
| Entity type validation via deserialization | validate_project_isolation | test_v2_061_serialization.py line 466 | test_v2_061_serialization.py line 450 | ✅ IMPL |

**Implementation**: `src/anovel/domain/character.py` lines 286-386 (validate_project_isolation)  
**Tests**: `tests/contract/test_v2_061.py` TestProjectIsolation + `tests/contract/test_v2_061_serialization.py` TestEntityTypeValidation

## AC-6: Schema Round-Trip & BASE/DERIVED/CACHE Semantics

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Character BASE fields serialized | serialization.py serialize_character | test_v2_061_serialization.py line 51 | N/A | ✅ IMPL |
| DERIVED fields excluded (active_goals) | serialization.py | test_v2_061_serialization.py line 137 | N/A | ✅ IMPL |
| DERIVED fields excluded (knowledge_count) | serialization.py | test_v2_061_serialization.py line 182 | N/A | ✅ IMPL |
| CACHE fields excluded (aligns_with_fact) | serialization.py | test_v2_061_serialization.py line 211 | N/A | ✅ IMPL |
| Round-trip preserves BASE state | deserialize_character | test_v2_061_serialization.py line 228 | N/A | ✅ IMPL |
| DERIVED recomputed after deserialization | deserialize_character | test_v2_061_serialization.py line 330 | N/A | ✅ IMPL |
| CACHE reset to None after deserialization | deserialize_character | test_v2_061_serialization.py line 372 | N/A | ✅ IMPL |
| Schema validation compliance | validate_against_schema | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |
| Nested dict context JSON compatibility | _thaw_context | test_v2_061_serialization.py line 566 | N/A | ✅ IMPL |
| Nested list context JSON compatibility | _thaw_context | test_v2_061_serialization.py line 618 | N/A | ✅ IMPL |
| Nested mixed context JSON compatibility | _thaw_context | test_v2_061_serialization.py line 670 | N/A | ✅ IMPL |

**Implementation**: `src/anovel/domain/serialization.py` (full module, including _thaw_context lines 124-158)
**Tests**: `tests/contract/test_v2_061_serialization.py` (5 test classes, 18 tests)

## AC-7: Lifecycle Semantics

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| DECEASED cannot form goals by default | validate_goal_formation | test_v2_061_lifecycle.py line 44 | test_v2_061_lifecycle.py line 37 | ✅ IMPL |
| DECEASED cannot form intents by default | validate_intent_formation | test_v2_061_lifecycle.py line 56 | test_v2_061_lifecycle.py line 49 | ✅ IMPL |
| PLANNED cannot acquire story knowledge | validate_knowledge_acquisition | test_v2_061_lifecycle.py line 63 | test_v2_061_lifecycle.py line 61 | ✅ IMPL |
| DECEASED → ACTIVE invalid by default | validate_lifecycle_transition | test_v2_061_lifecycle.py line 129 | test_v2_061_lifecycle.py line 122 | ✅ IMPL |
| PLANNED → ACTIVE valid | validate_lifecycle_transition | test_v2_061_lifecycle.py line 102 | N/A | ✅ IMPL |
| SUPERSEDED cannot be referenced in new content | validate_character_not_superseded | test_superseded.py line 24 | test_superseded.py line 51 | ✅ IMPL |

**Implementation**:
- Lifecycle constraints: `src/anovel/domain/lifecycle.py` lines 21-102
- SUPERSEDED validation: `src/anovel/domain/superseded.py` lines 15-38

**Tests**:
- `tests/contract/test_v2_061_lifecycle.py` TestLifecycleConstraints + TestLifecycleTransitions
- `tests/contract/test_superseded.py` TestSupersededValidation class

## AC-8: Proposition Collision Invariant

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Same PropositionId + same BASE = VALID | validate_proposition_collision | test_v2_061.py line 1064 | N/A | ✅ IMPL |
| Same PropositionId + different predicate = REJECT | validate_proposition_collision | N/A | test_v2_061.py line 1080 | ✅ IMPL |
| Same PropositionId + different subject = REJECT | validate_proposition_collision | N/A | test_v2_061.py line 1098 | ✅ IMPL |
| Same PropositionId + different object = REJECT | validate_proposition_collision | N/A | test_v2_061.py line 1121 | ✅ IMPL |
| Same PropositionId + different context = REJECT | validate_proposition_collision | N/A | test_v2_061.py line 1146 | ✅ IMPL |
| Same PropositionId + different project_id = REJECT | validate_proposition_collision | N/A | test_v2_061.py line 1171 | ✅ IMPL |

**Implementation**: `src/anovel/domain/knowledge.py` lines 439-491  
**Tests**: `tests/contract/test_v2_061.py` TestPropositionCollision class (6 tests)

## AC-9: Knowledge Key Invariant

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| knowledge dict key == proposition.proposition_id (construction) | validate_knowledge_key_invariant | test_v2_061.py line 1216 | test_v2_061.py line 1240 | ✅ IMPL |
| knowledge dict key == proposition.proposition_id (deserialization) | deserialize_character | test_v2_061_serialization.py line 538 | test_v2_061_serialization.py line 512 | ✅ IMPL |

**Implementation**:
- Construction: `src/anovel/domain/character.py` lines 266-283 (validate_knowledge_key_invariant)
- Deserialization: `src/anovel/domain/serialization.py` lines 240-251 (deserialize_character validation)

**Tests**:
- `tests/contract/test_v2_061.py` TestKnowledgeKeyInvariant class
- `tests/contract/test_v2_061_serialization.py` TestKnowledgeKeyInvariantDeserialization class

## AC-10: UUID v4 Format Validation

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| PropositionId UUID v4 format (runtime) | Proposition.__post_init__ | test_v2_061.py line 1265 | test_v2_061.py line 1272 | ✅ IMPL |
| GoalId UUID v4 format (runtime) | Goal.__post_init__ | test_v2_061.py line 1279 | test_v2_061.py line 1286 | ✅ IMPL |
| IntentId UUID v4 format (runtime) | Intent.__post_init__ | test_v2_061.py line 1293 | test_v2_061.py line 1300 | ✅ IMPL |
| PlannedActionId UUID v4 format (runtime) | PlannedAction.__post_init__ | test_v2_061.py line 1307 | test_v2_061.py line 1314 | ✅ IMPL |
| PropositionId malformed format reject | Proposition.__post_init__ | N/A | test_v2_061.py line 1322 | ✅ IMPL |
| UUID v1 format reject | Proposition.__post_init__ | N/A | test_v2_061.py line 1334 | ✅ IMPL |
| Uppercase UUID reject | Proposition.__post_init__ | N/A | test_v2_061.py line 1378 | ✅ IMPL |
| PropositionId schema pattern (lowercase v4) | character.schema.json | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |
| GoalId schema pattern (lowercase v4) | character.schema.json | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |
| IntentId schema pattern (lowercase v4) | character.schema.json | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |
| PlannedActionId schema pattern (lowercase v4) | character.schema.json | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |

**Implementation**:
- Runtime: `src/anovel/domain/knowledge.py` Proposition.__post_init__, `src/anovel/domain/character.py` Goal/Intent/PlannedAction.__post_init__
- Schema: `specs/schemas/character.schema.json` UUID v4 patterns
- Validator: `src/anovel/domain/knowledge.py` lines 89-113

**Tests**: `tests/contract/test_v2_061.py` TestUUIDv4Validation class (10 tests)

## AC-11: Structured Provenance

| Requirement | Implementation | Positive Test | Negative Test | Status |
|-------------|----------------|---------------|---------------|--------|
| Character.provenance is dict[str, str] | Character dataclass | test_v2_061_serialization.py line 127 | N/A | ✅ IMPL |
| provenance required in schema | character.schema.json | test_v2_061_serialization.py line 403 | N/A | ✅ IMPL |

**Implementation**: `src/anovel/domain/character.py` line 239 + `specs/schemas/character.schema.json` lines 76-81
**Tests**: `tests/contract/test_v2_061_serialization.py` TestBASESerialization

## Summary

**Total Requirements**: 60
**Implemented**: 60 ✅
**Test Coverage**: 123/123 PASS

**Test Breakdown**:
- test_v2_061.py: 69 tests (core invariants + UUID validation + acceptance matrix)
- test_v2_061_serialization.py: 20 tests (BASE/DERIVED/CACHE + knowledge key + nested context)
- test_v2_061_lifecycle.py: 29 tests (lifecycle + goal transitions)
- test_superseded.py: 5 tests (SUPERSEDED validation)

**Contract Compliance**: COMPLETE
**Implementation Status**: Closure candidate prepared

**Known H1 Fixes Applied**:
- isinstance(EntityId) → registry.get_entity() (EntityId is NewType)
- Project isolation uses V2-005 EntityRegistry authority
- Character.provenance: Optional[str] → Dict[str, str]

**Delta Requirements Completed**:
- UUID v4 runtime enforcement across all ID types (Proposition, Goal, Intent, PlannedAction)
- Knowledge key invariant enforced at deserialization boundary
- SUPERSEDED lifecycle validation (cannot reference in new content operations)
- Nested context JSON compatibility (recursive MappingProxyType/tuple thawing)
- ABANDONED → SUPERSEDED acceptance matrix test
- Scope ratification (closure-scope-authorization.md updated)
- Contract trace matrix updated with final implementation status

**Governance Status**:
- Task entry semantic severity classification: COMPLETE
- Plan validation fatal vs informational separation: COMPLETE
- Historical provenance regression tests: COMPLETE
- Execution packet: Pending verification
- Machine evidence: Remains IN_PROGRESS pending independent acceptance
