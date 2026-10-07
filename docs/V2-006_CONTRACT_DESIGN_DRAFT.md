# V2-006 Contract Design Draft

**Document ID**: V2-006-CONTRACT-DESIGN-DRAFT  
**Version**: 0.2.0  
**Date**: 2026-10-06  
**Status**: DRAFT - REVISION AFTER REVIEW  
**Authority**: Pre-Implementation Design (Not Yet Binding)  
**Depends On**: V2-005 (Entity Identity & Alias Resolution)

**Revision History**:
- v0.1.0 (2026-10-06): Initial draft
- v0.2.0 (2026-10-06): Revision after design review - removed metadata, removed timestamps, tightened type system

---

## Executive Summary

### Purpose

V2-006 extends the ANovelOS V2 narrative kernel by adding **entity relationship tracking** on top of the V2-005 identity foundation. Where V2-005 answers "Who is this entity?", V2-006 answers "How do entities relate to each other?"

### Scope

**In Scope**:
- Relationship identity and lifecycle
- Directed relationships between entities
- Relationship type system
- Relationship metadata (optional attributes)
- Relationship query operations
- Project-scoped relationship isolation

**Out of Scope** (V2-006):
- Persistence (V2-007)
- Relationship inference/reasoning
- Temporal relationship tracking (event sourcing)
- Transitive relationship queries
- Graph algorithms (shortest path, centrality, etc.)
- Relationship versioning/history

### Key Design Decision

**V2-006 implements a GENERAL-PURPOSE entity relationship engine**, not a domain-specific (novel-only) model. Relationship types are extensible strings, not hardcoded enums. This allows:
- Flexibility for different narrative genres
- Future extension without contract changes
- Domain-specific relationship types defined at application layer

---

## 1. Design Decisions (Resolved)

The following design questions have been resolved in v0.2.0:

### Q1: Relationship Directionality
**Decision**: ✅ **Directed Only**  
Relationships are directed edges. No automatic inverse creation.

### Q2: Duplicate Relationships
**Decision**: ✅ **Idempotent (ID-based)**  
Identity is `relationship_id`. Uniqueness constraint is `(source, target, type, project)` tuple.

### Q3: Relationship Metadata
**Decision**: ✅ **Deferred to V2-007+**  
No metadata field in V2-006 MVP. Avoids schema/validation complexity.

### Q4: Relationship Identity
**Decision**: ✅ **Explicit RelationshipId (UUID v4)**  
Aligns with V2-005 EntityId pattern. Provides stable identity.

### Q5: Query Operations
**Decision**: ✅ **get_relationships Only**  
Minimal query scope. Advanced queries (type filters, graph traversal) deferred to future.

### Q6: Timestamps
**Decision**: ✅ **No Timestamps**  
Domain objects are timeless. Temporal concerns managed by persistence layer (V2-007).

### Q7: RelationshipType
**Decision**: ✅ **NewType String (Strongly Typed)**  
`RelationshipType = NewType('RelationshipType', str)`. Aligns with V2-005 pattern. Not Enum (extensible).

### Q8: Field Count
**Decision**: ✅ **5 Fields Only**  
Minimal model: relationship_id, project_id, source_entity_id, target_entity_id, relationship_type.

---

## 2. Proposed Domain Model

### 2.1 Core Types

**Minimal Model** (5 fields only):

```python
from typing import NewType
from dataclasses import dataclass

RelationshipId = NewType('RelationshipId', str)  # UUID v4 format
RelationshipType = NewType('RelationshipType', str)  # Extensible string (strongly typed)

@dataclass(frozen=True)
class EntityRelationship:
    """
    Directed relationship between two entities.
    
    Immutable after creation. Relationship identity is relationship_id.
    Uniqueness constraint: (source_entity_id, target_entity_id, relationship_type, project_id)
    is enforced by registry layer (idempotent add).
    """
    relationship_id: RelationshipId
    project_id: ProjectId
    source_entity_id: EntityId
    target_entity_id: EntityId
    relationship_type: RelationshipType
```

**Design Rationale**:
- **No metadata**: Deferred to V2-007+ (avoids schema/validation/serialization complexity)
- **No timestamps**: Domain objects are timeless (persistence layer manages temporal aspects)
- **RelationshipType as NewType**: Strong typing, aligns with V2-005 EntityId/ProjectId pattern
- **5 fields only**: Minimal viable model, extensible later without breaking changes

### 2.2 Relationship Registry (In-Memory)

```python
class RelationshipRegistry:
    """
    In-memory relationship store for tests and prototyping.
    
    NOT for production persistence (see V2-007).
    
    Uniqueness: (source_entity_id, target_entity_id, relationship_type, project_id)
    Identity: relationship_id (primary)
    """
    def add_relationship(self, relationship: EntityRelationship) -> None:
        """
        Add relationship. Idempotent based on relationship_id.
        
        If relationship_id already exists:
            - Same content → no-op
            - Different content → ValueError
        
        If (source, target, type, project) tuple already exists with different ID:
            - no-op (returns existing relationship)
        """
    
    def remove_relationship(self, relationship_id: RelationshipId) -> None:
        """
        Remove relationship by ID. 
        
        Idempotent: no-op if relationship_id not found (does not raise).
        """
    
    def get_relationship(self, relationship_id: RelationshipId) -> EntityRelationship | None:
        """Get relationship by ID. Returns None if not found."""
    
    def get_relationships(self, entity_id: EntityId, project_id: ProjectId) -> list[EntityRelationship]:
        """
        Get all relationships where entity_id is source OR target.
        
        Returns empty list if no relationships found.
        Order is deterministic but unspecified (implementation-defined).
        """
```

### 2.3 Operations

```python
def create_relationship(
    source_entity_id: EntityId,
    target_entity_id: EntityId,
    relationship_type: RelationshipType,
    project_id: ProjectId
) -> EntityRelationship:
    """
    Create a directed relationship between two entities.
    
    Generates a new RelationshipId (UUID v4).
    
    Args:
        source_entity_id: Source entity
        target_entity_id: Target entity
        relationship_type: Type of relationship (extensible string, strongly typed)
        project_id: Project scope
    
    Returns:
        New EntityRelationship instance
    
    Raises:
        ValueError: If relationship_type is empty or whitespace-only
    
    Note: Does not validate that source/target entities exist (no referential integrity).
    """

def delete_relationship(
    relationship_id: RelationshipId,
    registry: RelationshipRegistry
) -> None:
    """
    Delete a relationship by ID.
    
    Idempotent: no-op if relationship_id not found (does not raise).
    Does not cascade or affect inverse relationships.
    """

def get_relationships(
    entity_id: EntityId,
    project_id: ProjectId,
    registry: RelationshipRegistry
) -> list[EntityRelationship]:
    """
    Get all relationships for an entity (source or target).
    
    Returns relationships where entity_id is either source OR target,
    within the specified project.
    
    Returns empty list if no relationships found.
    Order is deterministic but unspecified.
    """
```

---

## 3. Architecture Constraints

### 3.1 Domain Boundaries

**ALLOWED**:
- ✅ Relationship types and operations (domain logic)
- ✅ In-memory RelationshipRegistry (for tests)
- ✅ Relationship validation
- ✅ Relationship query model (in-memory)

**FORBIDDEN**:
- ❌ Database tables (SQLAlchemy, Alembic)
- ❌ ORM mappings
- ❌ Persistence logic
- ❌ API endpoints
- ❌ Message queues
- ❌ External storage systems
- ❌ LLM provider integrations

**Rationale**: V2-006 is pure domain logic. Persistence is V2-007.

### 3.2 Dependency on V2-005

V2-006 **depends on** V2-005:
- Uses EntityId, ProjectId types from V2-005
- Assumes entities exist before relationships (no referential integrity enforcement in V2-006)
- Project isolation aligns with V2-005 semantics

V2-006 **does NOT modify** V2-005:
- No changes to EntityIdentity
- No changes to V2-005 operations
- No changes to EntityRegistry

---

## 4. Relationship Semantics

### 4.1 Directionality

Relationships are **directed**:
- `A --parent_of--> B` does NOT imply `B --child_of--> A`
- Inverse relationships must be created explicitly
- No automatic inference

### 4.2 Identity and Uniqueness

**Identity**: Relationships are identified by `relationship_id` (UUID v4, primary key).

**Uniqueness Constraint**: The tuple `(source_entity_id, target_entity_id, relationship_type, project_id)` is unique. Attempting to add a second relationship with the same tuple is idempotent (no-op).

### 4.3 Self-Relationships

Allowed:
```python
A --reflects_on--> A  # Entity can have relationship to itself
```

### 4.4 Project Isolation

Relationships are scoped to ProjectId:
- Entities in different projects cannot have relationships
- Query operations respect project boundaries
- No cross-project relationship leakage

### 4.5 Immutability

EntityRelationship is immutable after creation (frozen dataclass):
- No update operations in V2-006 MVP
- To change a relationship: delete old, create new

### 4.6 No Referential Integrity

V2-006 does **not** enforce that source/target entities exist:
- create_relationship accepts any EntityId
- Referential integrity is deferred to persistence layer (V2-007)
- This allows relationships to be created before entities in certain workflows

---

## 5. Non-Goals (V2-006)

The following are **explicitly out of scope** for V2-006:

1. **Relationship Metadata** → V2-007+ (deferred to avoid schema/validation complexity)
2. **Timestamps** (created_at, updated_at) → Persistence layer concern (V2-007)
3. **Persistence** → V2-007
4. **Relationship History/Versioning** → Future
5. **Transitive Queries** (e.g., "all ancestors") → Future
6. **Graph Algorithms** (shortest path, centrality) → Future
7. **Relationship Inference** (auto-create inverse) → Out of scope
8. **Temporal Relationships** (time-based validity) → Future
9. **Bulk Operations** (add_relationships_batch) → Future
10. **Relationship Update** (in-place mutation) → Out of scope (immutable model)
11. **Referential Integrity Enforcement** → V2-007 (persistence layer)
12. **Type-Filtered Queries** (get by relationship_type) → Future (V2-006.1+)

---

## 6. Proposed Step Breakdown

### Step 1: Relationship Types
- RelationshipId (NewType, UUID v4)
- RelationshipType (NewType, string)
- Basic validation (non-empty, no whitespace-only)

**Deliverables**:
- Type definitions in domain/relationship.py
- 15 tests (type construction, validation)

### Step 2: Relationship Identity Model
- EntityRelationship (frozen dataclass, 5 fields)
- Immutability verification
- Field validation

**Deliverables**:
- EntityRelationship implementation
- 20 tests (construction, immutability, validation)

### Step 3: Relationship Registry
- RelationshipRegistry class (in-memory)
- add_relationship (idempotent, ID-based identity)
- remove_relationship (idempotent)
- get_relationship (by ID)
- Project isolation

**Deliverables**:
- RelationshipRegistry implementation
- 25 tests (CRUD, project isolation, idempotency, uniqueness constraint)

### Step 4: create_relationship Operation
- create_relationship function
- UUID v4 generation for RelationshipId
- Input validation (relationship_type non-empty)
- No referential integrity checks

**Deliverables**:
- create_relationship implementation
- 20 tests (valid/invalid inputs, ID generation)

### Step 5: delete_relationship Operation
- delete_relationship function
- Idempotent (no error on not found)
- No cascade semantics

**Deliverables**:
- delete_relationship implementation
- 15 tests (delete existing, delete non-existent, no cascade)

### Step 6: get_relationships Query
- get_relationships function
- Returns relationships where entity is source OR target
- Project-scoped
- Deterministic ordering (implementation-defined)

**Deliverables**:
- get_relationships implementation
- 20 tests (empty results, multiple relationships, project isolation, source/target filtering)

### Step 7: Integration & Edge Cases
- Self-relationships (A -> A)
- Duplicate prevention (uniqueness constraint enforcement)
- Cross-step integration tests
- Large-scale relationship sets (performance baseline)

**Deliverables**:
- 20 integration tests

### Step 8: Schema & Final Acceptance
- relationship.schema.json (JSON Schema Draft 2020-12)
- Module docstrings per §12.1 pattern
- Consolidated contract tests
- Architecture boundary tests
- Contract compliance verification

**Deliverables**:
- Schema file
- Documentation updates
- 30 consolidated contract tests
- 2 architecture tests
- Closure documentation

**Total New Tests**: ~165 tests (15+20+25+20+15+20+20+30)

---

## 7. Acceptance Criteria

### Code Complete
- [ ] RelationshipId, RelationshipType, EntityRelationship defined
- [ ] RelationshipRegistry implemented (in-memory)
- [ ] create_relationship implemented
- [ ] delete_relationship implemented
- [ ] get_relationships implemented
- [ ] 100% type hints on public API
- [ ] Module docstrings complete

### Schema Complete
- [ ] specs/schemas/entity-relationship.schema.json exists
- [ ] Schema validates against JSON Schema Draft 2020-12
- [ ] Schema validation tested

### Tests Complete
- [ ] tests/contract/test_v2_006.py exists
- [ ] Minimum 165 tests covering all operations
- [ ] All edge cases covered (self-relationships, idempotency, project isolation)
- [ ] Serialization round-trip tested
- [ ] JSON schema validation tested

### Architecture Complete
- [ ] No persistence imports in domain/relationship.py
- [ ] No LLM provider imports
- [ ] Architecture boundary tests added
- [ ] V2-005 code unchanged

### CI Complete
- [ ] 6/6 gates passing
- [ ] All tests passing
- [ ] mypy --strict passing
- [ ] No regressions in V2-005

---

## 8. Risk Assessment

### Low Risk
- Relationship model similar to V2-005 (proven pattern)
- In-memory registry only (no persistence complexity)
- Clear domain boundaries

### Medium Risk
- Metadata handling (untyped dict, application-defined schema)
- Query operation performance with large relationship counts (in-memory only)

### High Risk (Mitigations)
**Risk**: Relationship explosion (too many relationships for in-memory)  
**Mitigation**: V2-006 is test/prototype only. V2-007 adds persistence with proper indexing.

**Risk**: Metadata schema drift (no validation)  
**Mitigation**: Document that metadata validation is application layer responsibility. Future V2-006.1 can add schema validation.

---

## 9. Design Review Summary (v0.2.0)

### Changes from v0.1.0

| Aspect | v0.1.0 | v0.2.0 | Rationale |
|--------|--------|--------|-----------|
| RelationshipType | `str` | `NewType('RelationshipType', str)` | Strong typing, aligns with V2-005 pattern |
| Metadata | `dict[str, Any]` | Removed | Deferred to V2-007+ (avoids complexity) |
| Timestamps | `created_at: datetime` | Removed | Domain timelessness (persistence concern) |
| Field Count | 7 fields | 5 fields | Minimal viable model |
| Uniqueness | Tuple-based | ID-based (with tuple constraint) | Clear identity model |
| delete_relationship | May raise | Idempotent (no raise) | Consistency with V2-005 |

### Design Convergence

**Scope**: General-purpose entity relationship tracking (not domain-specific)

**Minimal Model**: 5 fields only
- relationship_id (UUID v4)
- project_id (isolation)
- source_entity_id (from V2-005)
- target_entity_id (from V2-005)
- relationship_type (extensible string, strongly typed)

**Operations**: 3 core operations
- create_relationship (idempotent via uniqueness constraint)
- delete_relationship (idempotent, no error on not found)
- get_relationships (minimal query, source OR target)

**Deferred**:
- Metadata → V2-007+
- Timestamps → Persistence layer
- Advanced queries → V2-006.1+
- Graph algorithms → Future
- Relationship updates → Out of scope (immutable model)

### Next Steps

1. ✅ Design review complete (v0.2.0)
2. ⏳ Await final approval
3. ⏳ Convert to binding V2-006_IMPLEMENTATION_CONTRACT.md
4. ⏳ Independent contract review
5. ⏳ Authorization for implementation

---

**Status**: DRAFT v0.2.0 - Awaiting Final Approval  
**Reviewer**: Project Owner  
**Next Action**: Approve or request further revision

---

**End of Draft v0.2.0**
