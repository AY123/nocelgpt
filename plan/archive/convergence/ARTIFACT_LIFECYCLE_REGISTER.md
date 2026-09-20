# ANovel V2 Artifact Lifecycle Register

**Document ID**: CONV-0006  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Define unified artifact envelope, canonical serialization, and operation algebra for ANovel V2

---

## 1. Unified Artifact Envelope

All persistent artifacts in ANovel V2 MUST include this envelope:

```yaml
artifact_id: <uuid or content-addressed ID>
artifact_type: <type from registry>
schema_id: <schema identifier>
schema_version: <semver>
project_id: <project UUID>
branch_id: <canon branch, default: main>
content_hash: <SHA-256 of canonical content>
producer: <service/worker ID>
input_refs: [<artifact IDs this depends on>]
input_hashes: [<hashes of inputs at execution time>]
authority: <authority level: T0-T7>
created_at: <ISO 8601 UTC timestamp>
metadata:
  run_fingerprint: <optional>
  model_policy: <optional>
  human_approved: <optional boolean>
```

**Specification**: Defined in PLATFORM_OBSERVABILITY_SECURITY_SPEC.md Section 40-45

---

## 2. Canonical Serialization Rules

To ensure stable, recomputable content hashes:

### 2.1 JSON Serialization

**Requirements**:
1. **Key Ordering**: Lexicographic (alphabetical) sort of all object keys
2. **Unicode**: UTF-8 encoding, NFC normalization
3. **Datetime**: ISO 8601 format with 'Z' timezone (UTC): `YYYY-MM-DDTHH:MM:SS.sssZ`
4. **Numbers**: 
   - Integers: No decimal point
   - Decimals: Minimum precision sufficient for semantic value
   - No exponential notation unless semantically required
5. **Null vs Missing**:
   - `null`: Explicit absence with semantic meaning (e.g., "unknown")
   - Missing key: Field not applicable
   - Canon: Prefer missing over null for absent optional fields
6. **Whitespace**: Compact (no pretty-print) for hashing, pretty-print for human inspection
7. **Ordered Lists**: Preserve order when order is semantic (e.g., timeline events)
8. **Unordered Sets**: Sort lexicographically when order is not semantic (e.g., tags)

**Hash Computation**:
```
content_hash = SHA-256(canonical_json_bytes)
```

**Test Requirement**: TEST-PLATFORM-001 "canonical_serialization_stable"

---

### 2.2 Semantic vs Non-Semantic Metadata

**Semantic Fields** (affect hash):
- Entity identity (character_id, event_id)
- Narrative facts (character name, event description)
- State values (location, wealth, relationships)
- Temporal ordering (timeline position)
- Logical dependencies (parent commit, input refs)

**Non-Semantic Fields** (excluded from content hash):
- `created_at` (when artifact was created)
- `artifact_id` (auto-generated)
- `producer` (who created it, not what it contains)
- Observability metadata (run_id, trace_id)
- Performance metrics (execution_time_ms)

**Rule**: Hash only semantic content to enable reproducibility.

---

## 3. Artifact Type Registry

**Core Artifact Types** (from DATA_OWNERSHIP_MATRIX):

### 3.1 T3 — Canon Artifacts
- `canon-event`: Individual commit to Canon Event Log
- `canon-snapshot`: Projection of Canon state at commit
- `canon-commit`: Complete commit operation record
- `canon-branch`: Branch metadata
- `retcon-record`: R1/R2/R3 retcon with invalidation cascade

### 3.2 T2 — Genre Artifacts
- `genre-pack`: Versioned GenrePack
- `genre-rule`: Genre validation rule
- `genre-extension-schema`: Canon extension definition
- `progression-model`: Progression mechanics definition

### 3.3 T4 — Planning Artifacts
- `series-vision`: Overall series direction
- `arc-plan`: Multi-chapter arc structure
- `chapter-contract`: Chapter semantic requirements
- `scene-contract`: Scene-level commitments

### 3.4 T5 — Context & Compilation
- `context-artifact`: Compiled context for one execution
- `context-policy`: Context compilation rules
- `role-spec`: Role-specific context template

### 3.5 T1 — Workflow Artifacts
- `workflow-run`: Complete workflow execution
- `stage-result`: Individual stage output
- `checkpoint`: Resumption point
- `idempotency-receipt`: Deduplication record

### 3.6 T6 — Proposal Artifacts
- `draft-text`: Generated chapter text
- `narrative-delta`: Extracted story changes
- `changeset`: Validated changes ready for commit
- `repair-plan`: Proposed fixes

### 3.7 T7 — Evaluation Artifacts
- `quality-report`: Quality evaluation results
- `quality-finding`: Individual quality issue
- `experiment-result`: Learning experiment outcome
- `market-signal`: Real reader behavior data

### 3.8 Domain Entity Artifacts
- `character`: Character entity
- `relationship`: Relationship between entities
- `event`: Story event
- `knowledge`: Knowledge/belief entity
- `promise`: Reader promise
- `mystery`: Story mystery
- `location`: Place entity
- `faction`: Group/organization
- `object`: Significant item

### 3.9 Provenance Artifacts
- `run-fingerprint`: Production conditions snapshot
- `manifest`: Artifact contents inventory
- `audit-log-entry`: Security/authority action record

---

## 4. Operation Algebra (NarrativeDelta / ChangeSet)

NarrativeDelta and ChangeSet MUST use typed operations, not free-form objects.

### 4.1 Core Operation Types

**Initial Operation Set** (expandable via versioning):

#### Entity Operations
```yaml
CREATE_ENTITY:
  entity_type: <character|location|faction|object>
  entity_id: <new ID>
  initial_state: <entity attributes>
  
UPDATE_ENTITY:
  entity_id: <existing ID>
  updates: <attribute changes>
  
DELETE_ENTITY:
  entity_id: <existing ID>
  reason: <why entity removed>
```

#### Fact Operations
```yaml
SET_FACT:
  entity_id: <entity ID>
  fact_type: <fact category>
  fact_key: <specific fact>
  value: <new value>
  replaces: <previous value, if any>
  
END_FACT:
  entity_id: <entity ID>
  fact_key: <fact to end>
  reason: <why fact ended>
```

#### Relationship Operations
```yaml
ADD_RELATIONSHIP:
  relationship_id: <new ID>
  from_entity: <entity ID>
  to_entity: <entity ID>
  relationship_type: <type>
  properties: <relationship attributes>
  
UPDATE_RELATIONSHIP:
  relationship_id: <existing ID>
  updates: <attribute changes>
  
REMOVE_RELATIONSHIP:
  relationship_id: <existing ID>
  reason: <why removed>
```

#### Knowledge Operations
```yaml
ADD_KNOWLEDGE:
  entity_id: <entity that knows>
  knowledge_id: <new ID>
  content: <what is known>
  source: <how learned>
  certainty: <confidence level>
  
UPDATE_BELIEF:
  knowledge_id: <existing ID>
  new_certainty: <updated confidence>
  reason: <why belief changed>
```

#### Event Operations
```yaml
CREATE_EVENT:
  event_id: <new ID>
  event_type: <event template>
  participants: [<entity IDs>]
  location: <location ID>
  time: <timeline position>
  description: <what happened>
  consequences: [<other operation IDs>]
```

#### Promise Operations
```yaml
OPEN_PROMISE:
  promise_id: <new ID>
  promise_type: <type>
  setup_chapter: <chapter ID>
  expected_payoff: <chapter range>
  description: <reader expectation>
  
PAY_PROMISE:
  promise_id: <existing ID>
  payoff_chapter: <chapter ID>
  satisfaction_level: <how well paid off>
```

#### Goal Operations
```yaml
UPDATE_GOAL:
  entity_id: <entity ID>
  goal_id: <goal ID>
  status: <active|achieved|abandoned|blocked>
  progress: <progress value>
```

#### State Change Operations
```yaml
MOVE_ENTITY:
  entity_id: <entity ID>
  from_location: <location ID>
  to_location: <location ID>
  
TRANSFER_OBJECT:
  object_id: <object ID>
  from_entity: <entity ID>
  to_entity: <entity ID>
  
CHANGE_RESOURCE:
  entity_id: <entity ID>
  resource_type: <wealth|power|influence|etc>
  delta: <change amount>
  new_value: <resulting value>
```

---

### 4.2 Operation Structure

**Every Operation MUST Include**:
```yaml
operation_type: <from registry above>
operation_id: <unique ID for this operation>
payload: <type-specific fields>
preconditions:
  required_entities: [<entity IDs that must exist>]
  required_facts: [<facts that must be true>]
  forbidden_states: [<states that must not exist>]
evidence:
  source_text_ref: <chapter:scene:paragraph>
  extraction_confidence: <E1-E4>
  genre_alignment: <passes genre rules>
metadata:
  extracted_by: <extractor ID>
  extraction_time: <timestamp>
```

---

### 4.3 Operation Validation Rules

**Validation MUST Check**:
1. **Operation Type**: Is registered and versioned
2. **Payload Schema**: Matches type-specific schema
3. **Preconditions**: All required entities/facts exist in Canon
4. **Entity Existence**: Referenced entities exist (or are created in same ChangeSet)
5. **Fact Mutability**: Immutable facts not mutated (per NARRATIVE_DOMAIN_SPEC Section 45-48)
6. **Genre Rules**: Operation doesn't violate Genre Hard Rules
7. **Temporal Consistency**: Event ordering preserved
8. **Evidence Level**: Sufficient confidence for operation type

**Test Requirement**: TEST-DOMAIN-010 "operation_validation_comprehensive"

---

### 4.4 Reducer Semantics

**Canon State Projection**:
```
Canon Snapshot N+1 = reduce(Canon Snapshot N, ChangeSet Operations)
```

Each operation type MUST have deterministic reducer:
- **CREATE_ENTITY**: Add entity to state
- **SET_FACT**: Update entity fact (validate mutability)
- **ADD_RELATIONSHIP**: Add to relationship graph
- **CREATE_EVENT**: Append to timeline, update participant states
- **PAY_PROMISE**: Mark promise fulfilled, update promise tracking

**Idempotency**: 
- Same ChangeSet applied twice = same result
- Use operation_id for deduplication

---

### 4.5 Idempotency Semantics

**Requirements**:
1. Every ChangeSet has unique `changeset_id`
2. Every CanonCommit checks if `changeset_id` already committed
3. If already committed: Return existing commit record (no duplicate)
4. If new: Execute commit transaction
5. Atomic: Either all operations in ChangeSet succeed, or none

**Test Requirement**: TEST-CANON-008 "duplicate_changeset_idempotent"

---

### 4.6 Unknown Behavior

**When Operation Cannot Be Validated**:
- If preconditions unknown (missing entities): Status = BLOCKED
- If evidence insufficient: Status = REQUIRES_HUMAN_REVIEW
- If genre alignment ambiguous: Status = REQUIRES_GENRE_DECISION
- If operation type unrecognized: Status = UNKNOWN_OPERATION (reject)

**Rule**: Unknown operations MUST NOT enter Canon.

**Test Requirement**: TEST-CANON-009 "unknown_operation_rejected"

---

## 5. Hash Rules and Content Addressing

### 5.1 Primary Content Hash

**Computation**:
```python
def compute_content_hash(artifact):
    canonical_content = serialize_canonical(artifact.semantic_content)
    return hashlib.sha256(canonical_content.encode('utf-8')).hexdigest()
```

**Semantic Content Includes**:
- All domain entity fields
- All operation payloads
- All preconditions and validations
- Schema version (to detect schema changes)

**Semantic Content Excludes**:
- artifact_id (may be hash itself)
- created_at
- producer
- Observability metadata

---

### 5.2 Parent Hash Chain

**Canon Commits**:
```yaml
commit:
  commit_id: <UUID or hash>
  parent_commit_hash: <SHA-256 of parent commit>
  changeset_hash: <SHA-256 of changeset>
  canon_snapshot_hash: <SHA-256 of resulting state>
  genre_pack_hash: <SHA-256 of active GenrePack>
```

**Chain Validation**:
- Every commit MUST reference valid parent
- Hash chain MUST be unbroken from root to HEAD
- Branch points explicitly marked

**Test Requirement**: TEST-CANON-010 "parent_hash_chain_valid"

---

### 5.3 Input Hash Binding

**Workflow Artifacts**:
```yaml
stage_result:
  stage_id: <stage ID>
  input_artifact_refs: [<artifact IDs>]
  input_hashes: [<SHA-256 of each input at execution>]
  output_hash: <SHA-256 of this result>
```

**Purpose**: Detect stale inputs
- If input artifact changes after execution, input_hash mismatch
- Triggers recomputation or invalidation

**Test Requirement**: TEST-WF-020 "stale_input_detected"

---

## 6. Versioning Strategy

### 6.1 Schema Versioning

**Format**: Semantic Versioning (MAJOR.MINOR.PATCH)

```yaml
schema_id: character.schema
schema_version: 2.1.0
schema_hash: <SHA-256 of schema file>
```

**Compatibility**:
- PATCH: Bug fixes, clarifications (backward compatible)
- MINOR: New optional fields (backward compatible)
- MAJOR: Breaking changes (incompatible, requires migration)

**Migration**: Major version changes require ADR + migration script

---

### 6.2 Operation Versioning

**Operation Registry**:
```yaml
operation_type: CREATE_EVENT
operation_version: 1.0.0
supported_versions: [1.0.0, 1.1.0]
```

**Backward Compatibility**:
- Old operations remain valid
- New fields added as optional
- Breaking changes = new operation type

---

### 6.3 Artifact Versioning

**Versioned Artifacts** (require explicit version):
- GenrePack
- Policy files (canon-commit-policy.yaml, etc.)
- Prompt templates
- Model policies
- Quality rubrics

**Immutable Artifacts** (version = creation timestamp):
- Canon events (never change)
- Committed ChangeSet (never change)
- Audit logs (never change)

---

## 7. Lifecycle States

**Artifact Lifecycle**:
```
DRAFT → VALIDATING → VALID → COMMITTED → PUBLISHED
                        ↓
                    INVALID → REJECTED
                        ↓
                    STALE → INVALIDATED
```

**State Definitions**:
- **DRAFT**: Proposed, not validated
- **VALIDATING**: Under validation
- **VALID**: Passed validation, not committed
- **COMMITTED**: Entered Canon (immutable)
- **PUBLISHED**: External/user-visible
- **INVALID**: Failed validation
- **REJECTED**: Explicitly rejected (human decision)
- **STALE**: Based on superseded Canon state
- **INVALIDATED**: Explicitly invalidated (e.g., by Retcon)

**Test Requirement**: TEST-LIFECYCLE-001 "artifact_state_transitions_valid"

---

## 8. Staleness Detection

**Artifact Becomes Stale When**:
1. **Input Changed**: input_hash ≠ current hash of input artifact
2. **Canon Advanced**: Canon HEAD moved beyond artifact's parent_commit
3. **Schema Updated**: schema_version < current schema version (for MAJOR changes)
4. **Policy Changed**: policy_version < current policy version
5. **Retcon Occurred**: Canon state before artifact's creation was modified

**Staleness Propagation**:
- If Artifact A is stale, all artifacts depending on A become stale
- Staleness cascade logged in invalidation graph

**Test Requirement**: TEST-LIFECYCLE-002 "staleness_detection_accurate"

---

## 9. Reconstruction Rules

**Reproducible Artifacts** (can be recomputed):
- Canon Snapshot (from Event Log + reducer)
- Context Artifact (from Context Compiler + inputs)
- Derived quality metrics (from canonical content)

**Non-Reproducible Artifacts** (must be preserved):
- Model outputs (stochastic)
- Human decisions (subjective)
- Market signals (time-dependent)
- Audit logs (historical record)

**Reconstruction Requirements**:
- Same inputs + same reducer = same output
- Reproducibility tested via TEST-CANON-011 "snapshot_reconstruction_deterministic"

---

## 10. Retention Policies

**By Artifact Type** (from DATA_OWNERSHIP_MATRIX):

| Type | Retention | Rationale |
|------|-----------|-----------|
| Canon Event Log | PERMANENT | Historical record |
| GenrePack | PERMANENT | Versioned domain rules |
| Audit Logs | PERMANENT | Security/compliance |
| Experiment Results | PERMANENT | Learning corpus |
| Workflow Metadata | 1-2 years | Operational history |
| Context Artifacts | 3-12 months | Debugging |
| Checkpoints | 7-90 days | Recovery window |
| Rejected Drafts | 7-30 days | Analysis only |
| Secrets | 0 (rotated immediately) | Security |

**Deletion Policy**:
- Deletion MUST be logged (audit trail)
- Deletion MUST preserve artifact_id + metadata (tombstone)
- Deletion MUST NOT break hash chains

---

## 11. Provenance Requirements

**Every Persistent Artifact MUST Record**:
1. **Producer**: What created it (service, worker, human)
2. **Inputs**: What it depended on (artifact refs + hashes)
3. **Policy**: What rules applied (policy version)
4. **Schema**: What structure it followed (schema version)
5. **Authority**: What authority level it has (T0-T7)
6. **Timestamp**: When it was created (ISO 8601 UTC)

**RunFingerprint** (for Canon commits):
```yaml
run_fingerprint:
  constitution_version: 1.0.0
  code_commit: <git SHA>
  architecture_version: <version>
  genre_pack_hash: <hash>
  schema_set_hash: <hash>
  canon_parent_hash: <hash>
  contract_hash: <hash>
  context_policy_hash: <hash>
  prompt_hash: <hash>
  model_policy_hash: <hash>
  sampling_policy: <config>
  workflow_hash: <hash>
  quality_policy_hash: <hash>
```

**Goal**: Know exactly what conditions produced a result

**Test Requirement**: TEST-PLATFORM-010 "provenance_complete"

---

## 12. Cross-Specification Alignment

**Artifact Envelope Defined In**:
- PLATFORM_OBSERVABILITY_SECURITY_SPEC Section 40-45

**Canonical Serialization Defined In**:
- CANONICAL_STATE_SPEC Section 15-17
- PLATFORM_OBSERVABILITY_SECURITY_SPEC Section 42

**Operation Algebra Defined In**:
- NARRATIVE_DOMAIN_SPEC Section 56-60 (NarrativeDelta)
- CANONICAL_STATE_SPEC Section 18-22 (ChangeSet operations)

**Hash Rules Defined In**:
- CANONICAL_STATE_SPEC Section 42-44 (parent hash chain)
- PLATFORM_OBSERVABILITY_SECURITY_SPEC Section 44 (artifact integrity)

**Versioning Defined In**:
- PROJECT_CONSTITUTION Section 23 (version baseline)
- All specs include schema_version fields

---

## 13. Implementation Gates

**P0 (V2-002)**:
- ✅ Artifact envelope structure frozen
- ✅ Canonical serialization rules frozen
- ⏳ Hash computation library chosen

**P2 (V2-006)**:
- ⏳ Operation algebra implemented
- ⏳ Operation registry established
- ⏳ Reducer functions for each operation type

**P3 (V2-009)**:
- ⏳ Parent hash chain validation
- ⏳ Idempotency checking
- ⏳ Staleness detection

**P5 (V2-013)**:
- ⏳ Context artifact envelope
- ⏳ Input hash binding

**P9 (V2-036)**:
- ⏳ RunFingerprint complete implementation
- ⏳ Provenance tracking end-to-end

---

## 14. Test Requirements Summary

| Test ID | Purpose | Phase |
|---------|---------|-------|
| TEST-PLATFORM-001 | Canonical serialization stable | P0 |
| TEST-CANON-008 | Duplicate changeset idempotent | P3 |
| TEST-CANON-009 | Unknown operation rejected | P3 |
| TEST-CANON-010 | Parent hash chain valid | P3 |
| TEST-CANON-011 | Snapshot reconstruction deterministic | P3 |
| TEST-DOMAIN-010 | Operation validation comprehensive | P2 |
| TEST-LIFECYCLE-001 | Artifact state transitions valid | P2 |
| TEST-LIFECYCLE-002 | Staleness detection accurate | P3 |
| TEST-WF-020 | Stale input detected | P8 |
| TEST-PLATFORM-010 | Provenance complete | P9 |

---

**Document Status**: NORMATIVE  
**Next Update**: After P2 operation implementation  
**Owner**: Platform + Canon domains

---

**END OF ARTIFACT LIFECYCLE REGISTER**
