# V2-005 Current State Audit

**Document ID**: V2-005-AUDIT  
**Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: REFINEMENT_PHASE  
**Authority**: Task Refinement Input

---

## Executive Summary

This audit establishes the baseline for V2-005 (Core Entity IDs and Alias Resolution) implementation. The audit confirms:

- **No conflicting identity primitives exist** in current codebase
- **Historical schema provides design reference** but requires authority-driven adaptation
- **Project isolation already established** at architecture level
- **Clear reuse opportunities** for normative patterns from P0
- **Zero implementation conflicts** detected

V2-005 can proceed with implementation after this refinement is approved.

---

## A1. Existing Identity Concepts

### A1.1 Codebase State

**Current `src/anovel/` structure:**
```
src/anovel/
├── __init__.py (minimal package marker)
└── __pycache__/
```

**Status**: No domain implementation exists yet.

**Implication**: V2-005 will establish the **first** domain primitive. Zero conflict risk.

---

### A1.2 Historical Schema Reference

**Location**: `plan/archive/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/`

**Files**:
- `NARRATIVE_DOMAIN_SPEC.md` (comprehensive narrative ontology)
- `narrative-entity.schema.json` (base entity schema)

**Key Concepts from Historical Reference**:

```yaml
# From narrative-entity.schema.json
id: string (required, minLength: 1)
entity_type: string (required)
canonical_name: string (required)
aliases: array of string (unique items)
scope: enum [book, series, universe]
lifecycle: string
authority: string
provenance: object
```

**From NARRATIVE_DOMAIN_SPEC.md Section 5**:
- Stable ID is authoritative over display name
- Alias resolution must not mint new entity if identity confidence sufficient
- Name change ≠ entity recreation
- Example ID format: `char_01H...`, `loc_01H...`

**Authority Status**: `archive/gptdoc/` = HISTORICAL_DESIGN_INPUT per governance § 2

**Evaluation**:
- ✅ Aligns with V2-005 goals
- ✅ Provides conceptual foundation
- ⚠️ Must be validated against current normative specs before adoption
- ⚠️ ID format (`char_01H...`) is **suggestion**, not frozen decision

---

### A1.3 Normative Specifications

**Primary Authority**: `plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md`

**Key Requirements**:

```text
§ 1. 领域最小集合
- P1 实现稳定实体 ID、带作用域的别名
- 名字不作为主键
- 项目内同名、角色改名、别名歧义必须有独立结果
- 不能随意合并实体
```

**Explicit Invariants**:
1. Name ≠ Primary Key
2. Same name + different project → distinct entities
3. Rename preserves stable ID
4. Ambiguous alias → explicit conflict result (not random choice)

---

### A1.4 Existing ID Conventions

**From V2-001 through V2-004 P0 implementation**:

No domain entity IDs established yet. However, infrastructure patterns exist:

**Task IDs**: `V2-001`, `V2-005` (string format, stable)  
**Finding IDs**: `AR-01`, `CA-05` (prefix + number)  
**ADR IDs**: `ADR-001` (string format)

**Pattern observation**: Project uses **opaque string IDs** with semantic prefixes.

---

### A1.5 ProjectId Status

**Search Result**: No existing `ProjectId` or `project_id` primitive found in `src/anovel/`.

**Implication from Normative Spec** (`03_DOMAIN_CANON...` § 1):
> "项目内同名...必须有独立结果"

This implies **project scope is mandatory** for entity resolution.

**From Architecture Baseline** (`02_ARCHITECTURE...` § 2):
> Canon repository must enforce "跨项目关系写入被拒绝"

**Conclusion**: 
- ProjectId concept **required** by architecture
- Not yet implemented
- **V2-005 MUST define ProjectId** or explicitly depend on another task for it
- No evidence of prior ProjectId definition found

---

### A1.6 EntityType Status

**Historical reference** suggests:
```
CHARACTER
LOCATION
FACTION
OBJECT
CONCEPT
```

**Current normative spec** (`03_DOMAIN...` § 1) mentions:
```
Character/Relationship/Knowledge
Event/Timeline/Promise
```

**Decision Required**: 
- Does V2-005 need EntityType enum, or generic Entity only?
- Authority check needed against backlog

---

## A2. Reuse Opportunities

### A2.1 REUSE: Governance Patterns

**From V2-002**:
- Schema validation contracts (JSON Schema Draft 2020-12)
- Evidence-based verification patterns
- Machine-readable specification format

**Application to V2-005**:
- Entity schema → `specs/schemas/entity.schema.json`
- Test contracts → `tests/contract/test_v2_005.py`
- Validation evidence pattern

---

### A2.2 REUSE: Architecture Fitness Patterns

**From V2-003**:
- Module boundary enforcement
- Dependency prohibition (domain ≠ database)
- Contract test philosophy

**Application to V2-005**:
- `src/anovel/domain/identity.py` must not import persistence
- Resolution logic must be pure domain
- Tests verify observable contract, not implementation

---

### A2.3 REUSE: Python Conventions

**From P0 implementation**:
- Python 3.12.14 locked
- Type hints expected
- Pydantic v2 for boundary validation (available in lockfile)

**Recommended for V2-005**:
```python
from dataclasses import dataclass
from enum import Enum
from typing import NewType

EntityId = NewType('EntityId', str)
ProjectId = NewType('ProjectId', str)

@dataclass(frozen=True)
class EntityIdentity:
    entity_id: EntityId
    project_id: ProjectId
    canonical_name: str
    # ...
```

---

### A2.4 EXTEND: Schema Conventions

**From V2-002 schemas**:
- `$schema`: JSON Schema Draft 2020-12
- `$id`: project-specific URI
- `required` fields explicit
- `additionalProperties: false` for closed schemas

**V2-005 should extend** this to entity domain.

---

### A2.5 NEW: Identity Resolution

**No existing resolver** found in codebase.

**Must create**:
- Alias lookup API
- Ambiguity detection
- NOT_FOUND vs AMBIGUOUS distinction
- Project-scoped resolution

---

### A2.6 DO_NOT_USE: Archive Implementation

**Location**: `plan/archive/` contains historical designs.

**Governance Rule** (`00_GOVERNANCE...` § 2):
> "历史设计输入...不直接成为实现或发布授权"

**V2-005 must NOT**:
- Copy archived code without validation
- Assume archived decisions are current authority
- Treat archived schemas as normative

---

## A3. Conflicts

### A3.1 Authority Conflicts

**NONE DETECTED**

Verification:
- Normative spec (`03_DOMAIN...`) is unambiguous on identity requirements
- No competing definitions in active `plan/` docs
- Archive material explicitly subordinate to current plan

---

### A3.2 Naming Conflicts

**NONE DETECTED**

No competing definitions of:
- EntityId
- ProjectId  
- canonical_name
- alias

---

### A3.3 Schema Conflicts

**NONE DETECTED**

Historical schema aligns with normative requirements. Key difference:

**Historical**: suggested `id: "char_01H..."`  
**Normative**: requires stable ID, format unspecified  

**Resolution**: V2-005 chooses format based on technical requirements, not historical suggestion.

---

### A3.4 Duplicate Primitive Risk

**LOW RISK**

Current state:
- No domain primitives implemented
- No parallel identity work in progress (per backlog review)
- V2-006/007/008 explicitly depend on V2-005

**Mitigation**:
- V2-005 artifacts clearly marked as authoritative
- Subsequent tasks must import from `anovel.domain.identity`

---

## A4. Dependency Analysis

### A4.1 Direct Dependencies

**Per implementation-backlog.yaml**:
```yaml
task_id: V2-005
dependencies:
  - V2-001
```

**V2-001 provides**:
- Locked Python environment
- Package structure (`src/anovel/`)
- Test infrastructure

**Status**: V2-001 CLOSED ✅

**V2-005 can proceed**.

---

### A4.2 Downstream Dependencies

**Tasks depending on V2-005**:
- V2-006 (Character/Relationship/Knowledge)
- V2-007 (Event/Timeline/Promise)
- V2-013 (GenrePack)

**Implication**: V2-005 is **critical path** (confirmed in phase-gates.yaml).

---

### A4.3 Cross-Cutting Dependencies

**ADR Status**:
```yaml
# From decision-register.yaml
ADR-002: Character Schema (REQUIRED, due V2-006)
ADR-003: Event/Promise timing (REQUIRED, due V2-007)
ADR-004: NarrativeDelta (REQUIRED, due V2-008)
```

**V2-005 has no ADR dependency** per decision-register.yaml.

**Implication**: V2-005 can make local design decisions without blocking on ADRs.

---

## A5. Test Infrastructure Status

**From V2-001/002/003 evidence**:
- `pytest` available and locked
- Contract test pattern established (`tests/contract/`)
- Architecture test pattern established (`tests/architecture/`)

**V2-005 test location**:
```
tests/contract/test_v2_005.py
```

Per acceptance criteria in backlog:
```yaml
tests:
  - AT-V2-005
```

**Test catalog reference exists** (not yet implemented).

---

## A6. Persistence Boundary

**Per architecture baseline** (`02_ARCHITECTURE...` § 2):

```text
domain | 实体、知识、时间、类型化变化、端口定义 | 
       | 禁止：Provider SDK、数据库实现、题材专属字段
```

**Confirmed**: V2-005 must NOT implement:
- Database tables
- Repository classes
- SQLAlchemy models

**V2-009** (Canon persistence) will consume V2-005 domain types.

---

## A7. Serialization Requirements

**From normative spec** (`03_DOMAIN...` § 6):

```text
Artifact 身份、哈希与血缘
- artifact_id/type
- schema_id/version
- content_hash
- created_at
```

**Implication for V2-005**:
- EntityId must be **serializable**
- Schema version must be tracked
- JSON representation required (for downstream Canon)

---

## A8. Normalization Policy Discovery

**Searched for existing normalization**:
- No Unicode normalization policy found
- No alias canonicalization rules defined

**Recommendation**: V2-005 must define **minimum sufficient normalization**.

**Historical reference suggests** (not authoritative):
- trim whitespace
- case handling (Chinese names: case-insensitive inappropriate)

**Decision point for refinement**.

---

## A9. Genre Isolation

**From architecture** (`02_ARCHITECTURE...` § 2):
> "domain 禁止：题材专属字段"

**From normative spec** (`03_DOMAIN...` § 1):
> "Core 不包含 cultivation_level 或公司财务专属字段"

**V2-005 Constraint**: 
- EntityId must work for ALL genres
- No genre-specific identity logic
- Extensions handled separately (not V2-005 scope)

---

## A10. Findings Register Impact

**Relevant findings**:

**AR-03**: Character Schema composition
- Status: OPEN_TRACKED
- Related: V2-005, V2-006
- Acceptance: "identity 等字段正例通过"

**Implication**: V2-005 closure evidence must demonstrate identity fields work correctly.

---

## A11. Documentation Convention

**From P0**:
- Markdown for specifications
- YAML for machine data
- JSON Schema for contracts

**V2-005 should produce**:
- Python domain code
- JSON Schema for entity structure
- Contract tests
- (This refinement doc as planning artifact)

---

## A12. Critical Path Confirmation

**From phase-gates.yaml**:
```yaml
critical_path:
- V2-005  # ← First item after P0
- V2-008
- V2-009
- V2-010
- ...
```

**Status**: V2-005 is **gate blocker** for P1 → P2 transition.

**Implication**: Quality bar must be high; cannot defer core decisions.

---

## Summary Table

| Aspect | Status | Action |
|--------|--------|--------|
| Existing Primitives | None | **NEW** - V2-005 defines first domain types |
| Historical Schema | Reference available | **VALIDATE** against normative specs |
| ProjectId | Not defined | **MUST DEFINE** in V2-005 |
| EntityType | Unclear scope | **DECIDE** generic vs typed |
| Normalization | Undefined | **DEFINE** minimum policy |
| Test Infrastructure | Ready | **REUSE** P0 patterns |
| Authority Conflicts | None | **CLEAR** to proceed |
| Critical Path | Confirmed | **HIGH PRIORITY** |

---

## Readiness Assessment

✅ **Dependencies satisfied** (V2-001 closed)  
✅ **No blocking conflicts**  
✅ **Clear authority** (normative specs unambiguous)  
✅ **Test infrastructure ready**  
✅ **Architecture patterns established**  

⚠️ **Design decisions required**:
1. EntityId format
2. ProjectId definition vs delegation
3. EntityType scope
4. Normalization depth
5. Alias collision policy

**CONCLUSION**: V2-005 refinement can proceed to implementation contract definition.

---

**END OF AUDIT**
