# V2-006 Implementation Contract

**Document ID**: V2-006-CONTRACT  
**Version**: 1.0.0  
**Date**: 2026-10-06  
**Status**: FROZEN CONTRACT  
**Authority**: Binding Implementation Contract  
**Depends On**: V2-005 (Entity Identity & Alias Resolution)

---

## 1. Contract Purpose

This document is the **binding implementation contract** for V2-006 Entity Relationship Tracking. This contract extends the V2-005 identity foundation by adding directed relationships between entities. Once approved, this contract becomes the sole authority for V2-006 implementation. Changes after approval require formal contract revision.

**What V2-005 Provides**:
- Entity identity (EntityId, EntityIdentity)
- Entity operations (create, rename, add/remove alias, resolve)
- Project isolation (ProjectId)
- In-memory EntityRegistry

**What V2-006 Adds**:
- Relationship identity (RelationshipId, EntityRelationship)
- Relationship operations (create, delete, query)
- Directed relationship semantics
- In-memory RelationshipRegistry

---

## 2. Scope

### 2.1 In Scope

V2-006 implements **general-purpose entity relationship tracking**:

✅ **Relationship Identity**: RelationshipId (UUID v4), stable identifier  
✅ **Relationship Model**: EntityRelationship (5-field immutable dataclass)  
✅ **Relationship Types**: Extensible string-based types (not domain-specific enum)  
✅ **Directed Relationships**: A → B (no automatic inverse)  
✅ **Relationship Operations**: create, delete, query  
✅ **Project Isolation**: Relationships scoped to ProjectId  
✅ **In-Memory Registry**: RelationshipRegistry for tests/prototyping  
✅ **Idempotency**: create and delete are idempotent  
✅ **Immutability**: EntityRelationship is frozen (no updates)

### 2.2 Out of Scope

The following are **explicitly excluded** from V2-006:

❌ **Relationship Metadata**: Deferred to V2-007+ (avoids schema/validation complexity)  
❌ **Timestamps**: Domain timelessness (persistence layer concern, V2-007)  
❌ **Persistence**: No database, SQLAlchemy, or storage (V2-007)  
❌ **Referential Integrity**: No enforcement that entities exist  
❌ **Relationship Inference**: No automatic inverse relationship creation  
❌ **Graph Algorithms**: No transitive queries, shortest path, centrality  
❌ **Relationship Updates**: Immutable model (to change: delete + create)  
❌ **Bulk Operations**: No batch add/delete  
❌ **Advanced Queries**: No type filtering, no graph traversal (defer to V2-006.1+)  
❌ **Relationship Versioning**: No history tracking  
❌ **Domain-Specific Types**: Not hardcoded to novel/character concepts

---

## 3. Domain Types

### 3.1 RelationshipId

**Definition**:
```python
from typing import NewType

RelationshipId = NewType('RelationshipId', str)
```

**Semantics**:
- Opaque stable identifier for relationships
- Immutable for relationship lifetime
- Format: UUID v4 (lowercase, with hyphens, 36 characters)
- Generated via `uuid.uuid4()` from Python standard library

**Example**:
```python
RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
```

**Validation**: Must match UUID v4 pattern `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`

### 3.2 RelationshipType

**Definition**:
```python
from typing import NewType

RelationshipType = NewType('RelationshipType', str)
```

**Semantics**:
- Extensible relationship type identifier
- Application-defined semantics (not constrained by V2-006)
- Examples: "parent_of", "knows", "depends_on", "belongs_to"
- NOT an enum (allows future extension without contract changes)

**Validation Rules**:
- Non-empty after stripping whitespace
- Length ≥ 1 after `strip()`
- No validation of semantic meaning (application responsibility)

**Validation Function**:
```python
def validate_relationship_type(s: str) -> RelationshipType:
    """
    Validate and construct RelationshipType.
    
    Args:
        s: Raw relationship type string
    
    Returns:
        RelationshipType if valid
    
    Raises:
        ValueError: If empty or whitespace-only
    """
    trimmed = s.strip()
    if not trimmed:
        raise ValueError("RelationshipType cannot be empty or whitespace-only")
    return RelationshipType(trimmed)
```

### 3.3 EntityRelationship

**Definition**:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EntityRelationship:
    """
    Directed relationship between two entities.
    
    Immutable after creation. Identity is relationship_id.
    Uniqueness constraint: (source_entity_id, target_entity_id, relationship_type, project_id).
    """
    relationship_id: RelationshipId
    project_id: ProjectId
    source_entity_id: EntityId
    target_entity_id: EntityId
    relationship_type: RelationshipType
```

**Field Semantics**:

- `relationship_id`: Stable unique identifier (UUID v4)
- `project_id`: Project scope (from V2-005)
- `source_entity_id`: Source entity (from V2-005)
- `target_entity_id`: Target entity (from V2-005)
- `relationship_type`: Type of relationship (extensible string)

**Invariants**:
- Immutable (frozen dataclass)
- All fields required (no None values)
- Source and target may be equal (self-relationships allowed)

**Example**:
```python
EntityRelationship(
    relationship_id=RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8"),
    project_id=ProjectId("proj_001"),
    source_entity_id=EntityId("550e8400-e29b-41d4-a716-446655440000"),
    target_entity_id=EntityId("650e8400-e29b-41d4-a716-446655440001"),
    relationship_type=RelationshipType("knows")
)
```

---

## 4. RelationshipRegistry (In-Memory)

### 4.1 Purpose

RelationshipRegistry provides an in-memory store for relationships during tests and prototyping. It is **not intended for production persistence** (see V2-007).

### 4.2 Interface

```python
class RelationshipRegistry:
    """
    In-memory relationship store.
    
    Identity: relationship_id (primary)
    Uniqueness: (source_entity_id, target_entity_id, relationship_type, project_id) tuple
    """
    
    def add_relationship(self, relationship: EntityRelationship) -> None:
        """
        Add relationship to registry.
        
        Idempotent based on relationship_id:
        - If relationship_id exists with same content → no-op
        - If relationship_id exists with different content → ValueError
        
        Uniqueness constraint:
        - If (source, target, type, project) tuple exists with different ID → no-op (idempotent)
        
        Args:
            relationship: EntityRelationship to add
        
        Raises:
            ValueError: If relationship_id exists with different content
        """
    
    def remove_relationship(self, relationship_id: RelationshipId) -> None:
        """
        Remove relationship by ID.
        
        Idempotent: no-op if relationship_id not found (does not raise).
        
        Args:
            relationship_id: ID of relationship to remove
        """
    
    def get_relationship(self, relationship_id: RelationshipId) -> EntityRelationship | None:
        """
        Get relationship by ID.
        
        Args:
            relationship_id: ID to lookup
        
        Returns:
            EntityRelationship if found, None otherwise
        """
    
    def get_relationships(
        self, 
        entity_id: EntityId, 
        project_id: ProjectId
    ) -> list[EntityRelationship]:
        """
        Get all relationships for an entity (source or target).
        
        Returns relationships where entity_id appears as source OR target,
        within the specified project.
        
        Args:
            entity_id: Entity to find relationships for
            project_id: Project scope
        
        Returns:
            List of EntityRelationship (empty if none found)
            Order is deterministic but unspecified (implementation-defined)
        """
```

### 4.3 Implementation Notes

**Storage**:
- Internal dict keyed by `relationship_id`
- Secondary index by `(source, target, type, project)` tuple for uniqueness
- Project-scoped index for efficient `get_relationships`

**Thread Safety**: Not required (single-threaded tests only)

**Performance**: O(1) add/remove/get by ID, O(n) get_relationships where n = total relationships in project

---

## 5. Public Operations

### 5.1 create_relationship

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
    Does NOT validate that source/target entities exist (no referential integrity).
    
    Args:
        source_entity_id: Source entity
        target_entity_id: Target entity
        relationship_type: Type of relationship
        project_id: Project scope
    
    Returns:
        New EntityRelationship instance
    
    Raises:
        ValueError: If relationship_type is empty or whitespace-only
    
    Example:
        >>> rel = create_relationship(
        ...     EntityId("550e8400-e29b-41d4-a716-446655440000"),
        ...     EntityId("650e8400-e29b-41d4-a716-446655440001"),
        ...     RelationshipType("knows"),
        ...     ProjectId("proj_001")
        ... )
        >>> rel.relationship_id  # UUID v4 generated
        RelationshipId("a1b2c3d4-e5f6-4789-a012-b3c4d5e6f7a8")
    
    Contract: V2-006 §5.1
    """
```

**Behavior**:
- Generate new RelationshipId via `uuid.uuid4()`
- Validate relationship_type (non-empty after strip)
- Return new EntityRelationship
- No side effects (pure function)

### 5.2 delete_relationship

```python
def delete_relationship(
    relationship_id: RelationshipId,
    registry: RelationshipRegistry
) -> None:
    """
    Delete a relationship by ID.
    
    Idempotent: no-op if relationship_id not found (does not raise).
    Does NOT cascade or affect inverse relationships.
    
    Args:
        relationship_id: ID of relationship to delete
        registry: RelationshipRegistry to delete from
    
    Example:
        >>> delete_relationship(rel_id, registry)
        >>> # Second call is no-op:
        >>> delete_relationship(rel_id, registry)  # No error
    
    Contract: V2-006 §5.2
    """
```

**Behavior**:
- Remove relationship from registry
- If not found: no-op (no error)
- Does not affect other relationships (no cascade)

### 5.3 get_relationships

```python
def get_relationships(
    entity_id: EntityId,
    project_id: ProjectId,
    registry: RelationshipRegistry
) -> list[EntityRelationship]:
    """
    Get all relationships for an entity (source or target).
    
    Returns relationships where entity_id appears as source OR target,
    within the specified project.
    
    Args:
        entity_id: Entity to find relationships for
        project_id: Project scope
        registry: RelationshipRegistry to query
    
    Returns:
        List of EntityRelationship (empty list if none found)
        Order is deterministic but unspecified
    
    Example:
        >>> rel1 = create_relationship(A, B, "knows", proj)
        >>> rel2 = create_relationship(B, C, "likes", proj)
        >>> registry.add_relationship(rel1)
        >>> registry.add_relationship(rel2)
        >>> get_relationships(B, proj, registry)
        [rel1, rel2]  # B appears as target in rel1, source in rel2
    
    Contract: V2-006 §5.3
    """
```

**Behavior**:
- Query registry for relationships where entity_id is source OR target
- Filter by project_id
- Return empty list if no matches
- Order is deterministic but implementation-defined

---

## 6. Relationship Semantics

### 6.1 Directionality

Relationships are **directed**:
- `A --parent_of--> B` does NOT imply `B --child_of--> A`
- Inverse relationships must be created explicitly
- No automatic inference or symmetry

### 6.2 Identity and Uniqueness

**Identity**: Relationships are identified by `relationship_id` (UUID v4).

**Uniqueness Constraint**: The tuple `(source_entity_id, target_entity_id, relationship_type, project_id)` is unique within a registry. Attempting to add a second relationship with the same tuple results in idempotent behavior (no-op).

### 6.3 Self-Relationships

**Allowed**:
```python
A --reflects_on--> A  # Source == Target is valid
```

### 6.4 Project Isolation

Relationships are scoped to ProjectId:
- Entities in different projects cannot have relationships
- Query operations respect project boundaries
- No cross-project relationship visibility

### 6.5 Immutability

EntityRelationship is immutable (frozen dataclass):
- No update operations in V2-006
- To modify a relationship: delete old, create new

### 6.6 No Referential Integrity

V2-006 does **not** enforce that source/target entities exist:
- `create_relationship` accepts any valid EntityId
- Referential integrity is deferred to persistence layer (V2-007)
- Allows flexible relationship creation order

---

## 7. Error Semantics

### 7.1 ValueError Cases

**create_relationship**:
- Empty relationship_type (after strip)
- Whitespace-only relationship_type

**RelationshipRegistry.add_relationship**:
- relationship_id exists with different content

### 7.2 No Errors (Idempotent)

**delete_relationship**:
- relationship_id not found → no-op

**RelationshipRegistry.add_relationship**:
- relationship_id exists with same content → no-op
- (source, target, type, project) tuple exists → no-op

### 7.3 No Type Errors

All operations are fully type-hinted. Passing wrong types is a type checker failure, not a runtime ValueError.

---

## 8. Idempotency Contract

### 8.1 create_relationship

**Semantics**: Pure function (no side effects)

Calling twice generates different RelationshipIds:
```python
rel1 = create_relationship(A, B, "knows", proj)
rel2 = create_relationship(A, B, "knows", proj)
# rel1.relationship_id != rel2.relationship_id (different UUIDs)
```

### 8.2 RelationshipRegistry.add_relationship

**Semantics**: Idempotent based on relationship_id

```python
registry.add_relationship(rel)
registry.add_relationship(rel)  # no-op (same object)
```

**Uniqueness Constraint**: If (source, target, type, project) tuple exists:
```python
rel1 = create_relationship(A, B, "knows", proj)
rel2 = create_relationship(A, B, "knows", proj)
registry.add_relationship(rel1)
registry.add_relationship(rel2)  # no-op (tuple already exists)
```

### 8.3 delete_relationship

**Semantics**: Idempotent

```python
delete_relationship(rel_id, registry)
delete_relationship(rel_id, registry)  # no-op (not found)
```

---

## 9. Implementation Steps

### Step 1: Relationship Types (Core Types)

**Scope**:
- RelationshipId (NewType, UUID v4)
- RelationshipType (NewType, string)
- validate_relationship_type function
- Basic validation tests

**Deliverables**:
- `src/anovel/domain/relationship.py` (types section)
- `tests/contract/test_v2_006_step1.py` (15 tests)

**Tests**:
- RelationshipId construction
- RelationshipType validation (empty, whitespace, valid)
- Type immutability

**Acceptance**:
- Types defined per §3.1, §3.2
- 15/15 tests pass
- mypy --strict pass

### Step 2: Relationship Identity Model

**Scope**:
- EntityRelationship (frozen dataclass)
- Field validation
- Immutability verification

**Deliverables**:
- EntityRelationship in `relationship.py`
- `tests/contract/test_v2_006_step2.py` (20 tests)

**Tests**:
- EntityRelationship construction
- Field validation
- Immutability (frozen)
- Self-relationships (source == target)
- Equality checks

**Acceptance**:
- EntityRelationship defined per §3.3
- 20/20 tests pass
- mypy --strict pass

### Step 3: Relationship Registry

**Scope**:
- RelationshipRegistry class
- add_relationship (idempotent, uniqueness constraint)
- remove_relationship (idempotent)
- get_relationship (by ID)
- get_relationships (project-scoped query)
- Project isolation

**Deliverables**:
- RelationshipRegistry in `relationship.py`
- `tests/contract/test_v2_006_step3.py` (25 tests)

**Tests**:
- add_relationship (idempotent, uniqueness)
- remove_relationship (idempotent)
- get_relationship (found/not found)
- get_relationships (empty, multiple, project isolation)
- Uniqueness constraint enforcement

**Acceptance**:
- RelationshipRegistry defined per §4
- 25/25 tests pass
- mypy --strict pass

### Step 4: create_relationship Operation

**Scope**:
- create_relationship function
- UUID v4 generation
- Input validation (relationship_type)
- No referential integrity checks

**Deliverables**:
- create_relationship in `relationship.py`
- `tests/contract/test_v2_006_step4.py` (20 tests)

**Tests**:
- Valid relationship creation
- UUID v4 format validation
- Empty relationship_type (ValueError)
- Whitespace-only relationship_type (ValueError)
- Self-relationships
- Deterministic field assignment

**Acceptance**:
- create_relationship defined per §5.1
- 20/20 tests pass
- mypy --strict pass

### Step 5: delete_relationship Operation

**Scope**:
- delete_relationship function
- Idempotent behavior
- No cascade semantics

**Deliverables**:
- delete_relationship in `relationship.py`
- `tests/contract/test_v2_006_step5.py` (15 tests)

**Tests**:
- Delete existing relationship
- Delete non-existent relationship (no error)
- Idempotency verification
- No cascade (other relationships unaffected)

**Acceptance**:
- delete_relationship defined per §5.2
- 15/15 tests pass
- mypy --strict pass

### Step 6: get_relationships Query

**Scope**:
- get_relationships function
- Source OR target filtering
- Project-scoped query
- Deterministic ordering

**Deliverables**:
- get_relationships in `relationship.py`
- `tests/contract/test_v2_006_step6.py` (20 tests)

**Tests**:
- Empty results (no relationships)
- Single relationship (source match)
- Single relationship (target match)
- Multiple relationships (mixed source/target)
- Project isolation
- Deterministic ordering

**Acceptance**:
- get_relationships defined per §5.3
- 20/20 tests pass
- mypy --strict pass

### Step 7: Integration & Contract Tests

**Scope**:
- Cross-step integration tests
- Self-relationships
- Large relationship sets
- Edge cases

**Deliverables**:
- `tests/contract/test_v2_006_step7.py` (20 integration tests)

**Tests**:
- Full lifecycle: create → add → query → delete
- Self-relationships (A → A)
- Duplicate prevention (uniqueness constraint)
- Multiple relationship types between same entities
- Project isolation integration
- Determinism verification

**Acceptance**:
- 20/20 integration tests pass
- No regressions in Steps 1-6
- mypy --strict pass

### Step 8: Schema & Final Acceptance

**Scope**:
- entity-relationship.schema.json
- Module docstrings
- Consolidated contract tests
- Architecture boundary tests
- Final closure report

**Deliverables**:
- `specs/schemas/entity-relationship.schema.json`
- `tests/contract/test_v2_006.py` (30 consolidated tests)
- `tests/architecture/test_dependency_boundaries.py` (2 V2-006 tests)
- Module docstring update
- Closure documentation

**Tests**:
- Type contract completeness
- Operation contract coverage
- Serialization round-trip
- JSON schema validation
- Architecture boundary enforcement

**Acceptance**:
- Schema exists and validates per §10
- 30/30 consolidated tests pass
- 2/2 architecture tests pass
- Module docstring complete per §11
- Final closure report generated
- mypy --strict pass

**Total New Tests**: 165 (15+20+25+20+15+20+20+30)

---

## 10. Serialization Contract

### 10.1 entity-relationship.schema.json

**Location**: `specs/schemas/entity-relationship.schema.json`

**Content**:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://anovel.dev/schemas/entity-relationship.schema.json",
  "title": "EntityRelationship",
  "description": "Directed relationship between two narrative entities",
  "type": "object",
  "required": [
    "relationship_id",
    "project_id",
    "source_entity_id",
    "target_entity_id",
    "relationship_type"
  ],
  "properties": {
    "relationship_id": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
      "description": "Stable unique identifier (UUID v4 format)"
    },
    "project_id": {
      "type": "string",
      "minLength": 1,
      "description": "Project scope identifier"
    },
    "source_entity_id": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
      "description": "Source entity UUID v4"
    },
    "target_entity_id": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
      "description": "Target entity UUID v4"
    },
    "relationship_type": {
      "type": "string",
      "minLength": 1,
      "description": "Type of relationship (application-defined)"
    }
  },
  "additionalProperties": false
}
```

**Validation**: Must validate against JSON Schema Draft 2020-12 meta-schema.

---

## 11. Documentation Contract

### 11.1 Module Docstring

**`src/anovel/domain/relationship.py`**:

```python
"""
ANovelOS V2 Entity Relationship Tracking.

This module extends the V2-005 identity foundation by adding directed
relationships between entities. Relationships are project-scoped, immutable,
and stored in-memory for tests/prototyping.

Public API:
    Types:
        RelationshipId, RelationshipType, EntityRelationship
    Operations:
        create_relationship, delete_relationship, get_relationships
    Data Structures:
        RelationshipRegistry (in-memory, for tests)

Relationship Semantics:
    - Directed (no automatic inverse)
    - Immutable (no updates)
    - Project-scoped (isolation)
    - Idempotent (create/delete)

Contract: V2-006 Implementation Contract v1.0.0
"""
```

---

## 12. Architecture Constraints

### 12.1 Allowed Dependencies

✅ **Standard Library**: uuid, dataclasses, typing  
✅ **V2-005 Types**: EntityId, ProjectId (from `anovel.domain.identity`)  
✅ **Test Infrastructure**: pytest

### 12.2 Forbidden Dependencies

❌ **Persistence**: sqlalchemy, psycopg, alembic  
❌ **LLM Providers**: openai, anthropic  
❌ **Gateway/Infrastructure**: anovel.gateway, external APIs  
❌ **Non-V2-005 Domain**: No imports from other V2-00X modules

### 12.3 Architecture Tests

**Required** (Step 8):
```python
def test_v2_006_relationship_no_persistence_import():
    """V2-006: domain.relationship must not import persistence."""
    source = get_module_source("anovel.domain.relationship")
    forbidden = ["sqlalchemy", "psycopg", "alembic"]
    for f in forbidden:
        assert f not in source

def test_v2_006_relationship_no_provider_import():
    """V2-006: domain.relationship must not import LLM providers."""
    source = get_module_source("anovel.domain.relationship")
    forbidden = ["openai", "anthropic", "anovel.gateway"]
    for f in forbidden:
        assert f not in source
```

---

## 13. Forbidden Modifications

### 13.1 Do NOT Modify

V2-006 must **not** change:

❌ V2-005 code (`anovel.domain.identity`)  
❌ EntityId, ProjectId, EntityIdentity definitions  
❌ V2-005 operations (create_identity, rename_identity, etc.)  
❌ EntityRegistry (from V2-005)  
❌ V2-005 tests  
❌ V2-005 contract

### 13.2 Rationale

V2-005 is frozen and verified. Any modifications would:
- Break V2-005 evidence chain
- Require re-verification of entire V2-005
- Risk introducing regressions

---

## 14. Acceptance Checklist

Implementation complete when ALL checked:

### Code
- [ ] `src/anovel/domain/relationship.py` implemented
- [ ] RelationshipId, RelationshipType, EntityRelationship defined
- [ ] RelationshipRegistry implemented (in-memory)
- [ ] create_relationship, delete_relationship, get_relationships implemented
- [ ] 100% type hints on public API
- [ ] Module docstring complete per §11.1

### Schema
- [ ] `specs/schemas/entity-relationship.schema.json` exists
- [ ] Schema validates against JSON Schema Draft 2020-12
- [ ] Schema validation tested

### Tests
- [ ] `tests/contract/test_v2_006_step1.py` through step8 exist (165 tests total)
- [ ] `tests/contract/test_v2_006.py` exists (30 consolidated tests)
- [ ] All Steps 1-8 tests pass
- [ ] All edge cases covered
- [ ] Serialization round-trip tested
- [ ] JSON schema validation tested

### Architecture
- [ ] No persistence imports in relationship.py
- [ ] No LLM provider imports
- [ ] Architecture boundary tests added (2 tests)
- [ ] V2-005 code unchanged

### CI
- [ ] 6/6 gates passing
- [ ] All tests passing (baseline + 165 new)
- [ ] mypy --strict passing
- [ ] No regressions in V2-005

---

## 15. Summary

### What V2-006 Implements

**Types** (3):
- RelationshipId (UUID v4)
- RelationshipType (extensible string)
- EntityRelationship (5-field immutable)

**Operations** (3):
- create_relationship (generate UUID, validate type)
- delete_relationship (idempotent)
- get_relationships (project-scoped query)

**Data Structures** (1):
- RelationshipRegistry (in-memory)

**Schemas** (1):
- entity-relationship.schema.json

**Tests** (165 new):
- Step 1-7: 135 step-specific tests
- Step 8: 30 consolidated tests + 2 architecture tests

### Contract Guarantees

1. **Identity Stability**: RelationshipId never changes
2. **Directionality**: No automatic inverse relationships
3. **Project Isolation**: All operations project-scoped
4. **Immutability**: EntityRelationship frozen after creation
5. **Idempotency**: create/delete operations are idempotent
6. **No Referential Integrity**: Domain layer does not enforce entity existence
7. **Architecture Boundaries**: No persistence/provider coupling

---

**Contract Status**: FROZEN v1.0.0  
**Next Action**: Independent Contract Review  
**Implementation**: NOT AUTHORIZED (awaiting review approval)

---

**End of Contract**
