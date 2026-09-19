# ANovel V2 Phase & Task Registry (SSOT)

**Document ID**: REGISTRY-0001  
**Version**: 1.0  
**Status**: NORMATIVE  
**Authority**: CONTROL-PLANE-BASELINE  
**Source**: Derived from gptdoc/ANovel_V2_Implementation_Plan_v1.0/  
**Purpose**: Single source of truth for Phase and Task identity

---

## 0. Authority Declaration

This document is the **SINGLE SOURCE OF TRUTH** for:
- Phase definitions (P0-P14)
- Task identity (V2-001 to V2-060)
- Gate model semantics

**All other documents MUST reference this registry. No document may redefine Phase or Task semantics.**

**Canonical Source**: `gptdoc/ANovel_V2_Implementation_Plan_v1.0/implementation-backlog.yaml`

---

## 1. Phase Registry (P0-P14)

**Source**: IMPLEMENTATION_PLAN.md Section 6 "Phase Map"

| Phase ID | Phase Name | Goal | Milestone |
|----------|-----------|------|-----------|
| **P0** | **Repository & Governance** | Establish greenfield repo with architecture enforcement from day 1 | **M0** |
| **P1** | **Narrative Kernel** | Implement Genre-agnostic minimal Narrative Domain | **M1** |
| **P2** | **Canon Kernel** | Implement single Canon write boundary with Event Log + Snapshot | **M1** |
| **P3** | **Genre Kernel** | Implement GenrePack loader and dual anchor genres | **M1** |
| **P4** | **Planning & Contracts** | Implement Contract Compiler and validation | **M2** |
| **P5** | **Context & Model Gateway** | Implement Context Compiler and Provider abstraction | **M2** |
| **P6** | **Single-Chapter Production** | First end-to-end chapter workflow | **M2** |
| **P7** | **Quality & Repair** | Implement Q0-Q3 hard gates and patch repair | **M3** |
| **P8** | **Dual-Genre 10-Chapter Certification** | Prove dual genre works at 10-chapter scale | **M3** |
| **P9** | **30-Chapter Certification** | Prove production stability at 30-chapter scale | **M3** |
| **P10** | **Genesis & Reference Intelligence** | Multi-source Genesis and originality guard | **M4-M6** |
| **P11** | **Human Calibration & Learning** | Human blind review and quality calibration | **M4-M6** |
| **P12** | **100-Chapter Reliability** | Prove long-run reliability | **M5** |
| **P13** | **Reader / Market Feedback** | Real reader signal integration | **M6-M7** |
| **P14** | **300+ Chapter / Million-word Evolution** | Sustained long-form production | **M7** |

---

## 2. Task Registry (V2-001 to V2-060)

**Source**: `implementation-backlog.yaml`

### P0 — Repository & Governance (V2-001 to V2-004)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-001** | Repository bootstrap | P0 | Python package, formatter/linter/type checker, pytest, PostgreSQL fixture, migrations |
| **V2-002** | Normative documentation index | P0 | Import all normative specs, establish NORMATIVE_INDEX.md |
| **V2-003** | Architecture fitness harness | P0 | Automated boundary checks (import rules, dependency direction) |
| **V2-004** | Security baseline | P0 | Secret scan, dependency scan, audit logging foundation |

**P0 Scope**: Pure repository/governance work. **No narrative or workflow business logic.**

**M0 Close Gate**:
- CI green
- lockfile committed
- no secrets in repo
- normative index complete
- architecture fitness enforced

---

### P1 — Narrative Kernel (V2-005 to V2-008)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-005** | Character / Relationship | P1 | EntityId, NarrativeEntity, Character, Relationship, FactClaim, FactMutability |
| **V2-006** | Knowledge / Goal | P1 | Knowledge, Goal, belief tracking |
| **V2-007** | Event / Timeline / Promise | P1 | Event, Timeline, Promise, temporal structure |
| **V2-008** | NarrativeDelta | P1 | Narrative change proposal extraction and typing |

**P1 Scope**: Genre-agnostic narrative entities. **No realm, equity, box_office, reader sim** (those are extensions).

**P1 Exit Gate**: Can represent pure realistic test story (characters, relationships, locations, events, knowledge, promises).

---

### P2 — Canon Kernel (V2-009 to V2-012)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-009** | Canon Event Log | P2 | Append-only Canon commit log, Event Sourcing foundation |
| **V2-010** | CanonCommitService | P2 | Single Canon write boundary (INV-004), ChangeSet validation |
| **V2-011** | Canon idempotency and CAS | P2 | Compare-and-swap, duplicate commit detection |
| **V2-012** | Snapshot rebuild and projection | P2 | State-as-Projection: Canon Snapshot = fold(Event Log) |

**P2 Scope**: Canon transaction boundary. **Minimal Canon Bootstrap** (manual fixture → ChangeSet → CanonCommit) should be implemented here, not in P0.

**M1 Partial Achievement**: After P1+P2, Narrative Kernel functional.

---

### P3 — Genre Kernel (V2-013 to V2-016)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-013** | GenreProfile and GenrePack loader | P3 | GenrePack versioning, loading, validation |
| **V2-014** | Genre Hard Policy | P3 | Genre Hard Rules that can block CanonCommit |
| **V2-015** | Urban Extension | P3 | urban.business.realistic GenrePack (GPK-U01) |
| **V2-016** | Fantasy Extension | P3 | fantasy.eastern.progression GenrePack (GPK-X01) |

**P3 Scope**: Genre as first-class domain. Canon extension namespace (ADR-0024) resolved here + in P2.

**M1 Full Achievement**: After P1+P2+P3, Narrative Kernel + Canon + Genre complete.

---

### P4 — Planning & Contracts (V2-017)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-017** | Contract Compiler | P4 | SeriesVision, ArcPlan, ChapterContract, SceneContract compilation and validation |

**P4 Scope**: Planning domain. Promise temporal binding (ADR-0022) partially resolved here.

---

### P5 — Context & Model Gateway (V2-018 to V2-019)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-018** | Context Compiler | P5 | ContextArtifact assembly, SourcePrecedence (T0-T7), token budget management |
| **V2-019** | Model Gateway | P5 | Provider abstraction, retry, unknown result handling, cost tracking |

**P5 Scope**: Context compilation and Model Gateway. 

**ADR Ownership**:
- ADR-0025 (Context Overflow): V2-018
- ADR-0007 (Provider Gateway): V2-019
- **Provider UNKNOWN semantics**: V2-019 (not V2-002)

**M2 Partial Achievement**: After P4+P5, Planning + Context ready.

---

### P6 — Single-Chapter Production (V2-020)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-020** | Single Chapter Workflow | P6 | End-to-end: Context → Writer → Extractor → Validator → CanonCommit |

**P6 Scope**: First complete workflow. **ADR-0010 (Durable Workflow)** partially resolved here.

**M2 Full Achievement**: After P6, first chapter can be produced.

---

### P7 — Quality & Repair (V2-021 to V2-026)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-021** | Q0 Schema Validation | P7 | JSON Schema validation, deterministic checks |
| **V2-022** | Q1 Canon Consistency | P7 | Entity existence, fact validity, relationship integrity |
| **V2-023** | Q2 Contract Compliance | P7 | ChapterContract satisfaction, RequiredTransition validation |
| **V2-024** | Q3 Genre Compliance | P7 | Genre Hard Rule enforcement |
| **V2-025** | RepairPlan and Patch | P7 | Targeted repair generation (patch-first policy) |
| **V2-026** | Q4-Q6 Soft Gates | P7 | Semantic quality, craft, reader simulation (advisory only) |

**P7 Scope**: Quality gates and repair. Q0-Q3 are hard gates (can block commit).

---

### P8 — Dual-Genre 10-Chapter Certification (V2-027 to V2-030)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-027** | Workflow Retry / Checkpoint | P8 | Resume, idempotency, unknown result reconciliation |
| **V2-028** | Dual-Genre 10-Chapter Run | P8 | Run urban + fantasy 10 chapters each |
| **V2-029** | Real-provider Contract Tests | P8 | Claude/DeepSeek/OpenAI real tests |
| **V2-030** | Genre Contamination Detection | P8 | Verify 0 cross-genre contamination |

**P8 Scope**: Dual genre certification at 10-chapter scale.

**ADR Ownership**:
- ADR-0010 (Durable Workflow): V2-027 (primary)
- **Provider UNKNOWN**: V2-027 (reconciliation logic)

**M3 Partial Achievement**: After P8, dual genre proven at 10 chapters.

---

### P9 — 30-Chapter Certification (V2-031 to V2-035)

| Task ID | Title | Phase | Description |
|---------|-------|-------|-------------|
| **V2-031** | 30-Chapter Urban Run | P9 | urban.business.realistic 30 chapters |
| **V2-032** | 30-Chapter Fantasy Run | P9 | fantasy.eastern.progression 30 chapters |
| **V2-033** | Long-run Promise Tracking | P9 | Verify promise debt doesn't accumulate |
| **V2-034** | Long-run Continuity | P9 | Verify character/event consistency across 30 chapters |
| **V2-035** | 30-Chapter Certification Report | P9 | Evidence: 0 Canon errors, 0 genre contamination, all Q0-Q3 pass |

**P9 Scope**: 30-chapter reliability certification.

**M3 Full Achievement**: After P9, dual genre proven at 30 chapters.

---

### P10 — Genesis & Reference Intelligence (V2-036 to V2-042)

(Deferred to post-M3, not blocking early milestones)

### P11 — Human Calibration & Learning (V2-043 to V2-048)

(Deferred to post-M3)

### P12 — 100-Chapter Reliability (V2-049 to V2-052)

(M5 target)

### P13 — Reader / Market Feedback (V2-053 to V2-056)

(M6-M7 target)

### P14 — 300+ Chapter Evolution (V2-057 to V2-060)

(M7 target)

---

## 3. Gate Model

**Four Types of Gates** (frequently confused, now formalized):

### 3.1 Task Dependency

**Definition**: Task A requires Task B's output to execute

**Example**:
```yaml
V2-010 (CanonCommitService):
  depends_on: [V2-009]  # Needs Canon Event Log to write commits
```

**Enforcement**: Task graph, build system

---

### 3.2 Phase Entry Gate

**Definition**: Conditions required to start executing tasks in Phase N

**Example**:
```yaml
P1_ENTRY_GATE:
  requires:
    - P0_EXIT_GATE: passed
    - M0: closed
  allows: [V2-005, V2-006, V2-007, V2-008]
  blocks: [V2-009+]
```

**Enforcement**: Project governance, manual approval

---

### 3.3 Milestone Close Gate

**Definition**: Evidence required to declare Milestone M complete

**Example**:
```yaml
M0_CLOSE_GATE:
  evidence_required:
    - CI: green
    - lockfile: committed
    - secrets: none detected
    - normative_index: complete
    - architecture_fitness: enforced
  verdict: READY | NOT_READY
```

**Enforcement**: Evidence checklist, cannot be overridden

---

### 3.4 Certification Gate

**Definition**: Evidence required for major advancement (M3, M5, M7)

**Example**:
```yaml
M3_CERTIFICATION_GATE:
  evidence_required:
    - dual_genre_30ch: completed
    - canon_errors: 0
    - genre_contamination: 0
    - Q0_Q3_hard_gates: all pass
    - promise_debt: no accumulation
    - continuity: maintained across 30 chapters
  verdict: PASS | FAIL
```

**Enforcement**: Formal certification report, external review

---

## 4. Control Plane Rules

### Rule 1: Single Source of Truth

```
implementation-backlog.yaml = SSOT for Task identity
PHASE_TASK_REGISTRY.md = SSOT for Phase identity
```

**Prohibited**: Convergence documents, ADR documents, or any other document redefining Task/Phase semantics.

### Rule 2: Reference Only

All documents may **reference** Task IDs and Phase IDs but must use exact definitions from this registry.

**Correct**:
```markdown
ADR-0025 affects V2-018 (Context Compiler, P5)
```

**Incorrect**:
```markdown
P5 = Context Intelligence  # Wrong, P5 = Context & Model Gateway
V2-018 = Context          # Incomplete, must include phase
```

### Rule 3: Phase Purity

Each Phase has a specific scope. **Do not introduce semantics from later phases into earlier phases.**

**Example Violations**:
- ❌ Genesis logic in P0 (belongs in P2 minimal bootstrap or P10 full)
- ❌ Workflow retry in P0 (belongs in P6/P8)
- ❌ Provider unknown in P0 (belongs in P5/P8)

### Rule 4: Validation Required

Before committing Task/Phase references, validate against:
1. `implementation-backlog.yaml` (Task existence)
2. `PHASE_TASK_REGISTRY.md` (Phase correctness)
3. Automated validators (cross-reference checks)

---

## 5. Validation Checklist

**Before freezing architecture baseline, verify**:

- [ ] All Phase references match Section 1 (P0-P14)
- [ ] All Task references match Section 2 (V2-001 to V2-060)
- [ ] All ADR owners exist in backlog
- [ ] All ADR owner phases match ADR blocking phases
- [ ] No P0 tasks contain narrative/workflow business logic
- [ ] Gate types clearly distinguished (dependency, entry, close, certification)
- [ ] No convergence document redefines Task/Phase semantics

---

## 6. Change Control

**This registry is NORMATIVE and FROZEN after convergence correction.**

**Changes require**:
- Formal ADR (if fundamental change)
- Version increment (MAJOR for incompatible changes)
- All dependent documents updated
- Validation suite re-run

**Current Version**: 1.0 (initial baseline)

---

END OF PHASE & TASK REGISTRY
