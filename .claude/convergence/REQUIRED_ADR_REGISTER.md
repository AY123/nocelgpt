# ANovel V2 Required ADR Register

**Document ID**: CONV-0007  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Track all Architecture Decision Records required for ANovel V2 implementation

---

## 0. ADR Governance

**When ADR Required** (per PROJECT_CONSTITUTION Section 17):
- New topriority Domain
- Authority model changes
- Canon write path changes
- Production state machine changes
- Genre hard rule semantics changes
- New long-term storage
- New Scheduler/Orchestrator
- Artifact lifecycle changes
- AI permission escalation
- Human authority boundary changes
- Constitution principle changes

**ADR Format**:
```markdown
# ADR-NNNN: Title

## Status
[PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED]

## Context
What is the issue we're trying to solve?

## Decision
What is the change we're proposing/have agreed to?

## Consequences
What becomes easier or more difficult?

## Alternatives Considered
What other options were evaluated?

## Migration
How do we transition from current state?

## Tests
How do we verify the decision is correctly implemented?
```

---

## 1. INITIAL ADR SET (from PROJECT_CONSTITUTION)

### ADR-0001: Modular Monolith First
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Architecture pattern for V2 initial phases  
**Decision**: Start with modular monolith, defer microservices until post-M5  
**Rationale**: Reduce operational complexity, enable rapid iteration  
**Owner**: V2-001 (P0)

### ADR-0002: Genre Intelligence is Foundational
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P1  
**Context**: Genre as afterthought caused V1 failures  
**Decision**: Genre as first-class domain, loaded before Canon operations  
**Rationale**: Prevent genre contamination (V1 LESSON-V1-001)  
**Owner**: V2-007 (P1)

### ADR-0003: Draft is not Canon
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Draft/Canon boundary enforcement  
**Decision**: Only CanonCommit can write Canon, no auto-promotion  
**Rationale**: Principle P-003, Invariant INV-004  
**Owner**: V2-009 (P3)

### ADR-0004: Canon Commit is the Only Write Boundary
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Single point of Canon modification  
**Decision**: All Canon writes through CanonCommitService only  
**Rationale**: Invariant INV-004, prevent Second Canon (RISK-C01)  
**Owner**: V2-009 (P3)

### ADR-0005: Canon Event Log + Snapshot
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P3  
**Context**: Canon persistence model  
**Decision**: Append-only event log + projection snapshots  
**Rationale**: V1 lesson (State as Projection works), enable replay  
**Owner**: V2-009 (P3)

### ADR-0006: Multi-source Genesis, Single Production Kernel
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P10  
**Context**: Multiple Genesis inputs (Idea/Reference/Hybrid/Corpus)  
**Decision**: All converge to GenesisSpec, then single kernel  
**Rationale**: Principle P-008, prevent divergent implementations  
**Owner**: V2-042 (P10)

### ADR-0007: Provider-independent Model Gateway
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P7  
**Context**: LLM provider abstraction  
**Decision**: Domain code never imports provider-specific modules  
**Rationale**: PROHIBIT-001, V1 lesson (real provider validation)  
**Owner**: V2-027 (P7)

### ADR-0008: Context Compiler Boundary
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P5  
**Context**: Worker input preparation  
**Decision**: Workers receive compiled Context, not raw DB access  
**Rationale**: Principle P-016, prevent context ad-hoc assembly  
**Owner**: V2-013 (P5)

### ADR-0009: Fail-Closed Production
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P3  
**Context**: Missing contracts, invalid states  
**Decision**: Production defaults to BLOCK on missing/invalid inputs  
**Rationale**: Principle P-005, V1 lesson (fail-open made contracts ineffective)  
**Owner**: V2-009 (P3)

### ADR-0010: Durable Workflow & Idempotency
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P8  
**Context**: Long-running production resilience  
**Decision**: Checkpoint/Resume/Retry with idempotency keys  
**Rationale**: External design lesson EXT-006, V1 resume failures  
**Owner**: V2-017 (P8)

### ADR-0011: Evidence Level & Judge Authority
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P6  
**Context**: AI evaluation authority boundaries  
**Decision**: E0-E1 deterministic > E2-E4 AI, Judge = T7 diagnostic only  
**Rationale**: Principle P-010, PROHIBIT-009  
**Owner**: V2-020 (P6)

### ADR-0012: Reference Evidence Firewall
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P10  
**Context**: Reference material cannot become Canon directly  
**Decision**: Reference = T5 evidence, requires Genesis → CanonCommit path  
**Rationale**: Principle P-011, Invariant INV-007, PROHIBIT-008  
**Owner**: V2-042 (P10)

### ADR-0013: Patch-first Repair
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P6  
**Context**: Quality issue remediation strategy  
**Decision**: Targeted patches preferred over full rewrite  
**Rationale**: Principle P-018, efficiency + provenance preservation  
**Owner**: V2-023 (P6)

### ADR-0014: Human Authority for Irreversible External Actions
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Publishing, R3 Retcon, external deployment  
**Decision**: Human approval required for irreversible external actions  
**Rationale**: Constitution Section 20, RISK-L03  
**Owner**: V2-002 (P0)

### ADR-0015: Provenance & Run Fingerprint
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P3  
**Context**: Artifact traceability  
**Decision**: All persistent artifacts have provenance envelope  
**Rationale**: Principle P-012, V1 lesson (placeholder hash)  
**Owner**: V2-009 (P3)

### ADR-0016: MarketTrendSnapshot separated from GenrePack
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P13  
**Context**: Market trends vs Genre truth  
**Decision**: Market = T5 time-bound evidence, Genre = T2 stable domain  
**Rationale**: Principle P-009  
**Owner**: V2-044 (P13)

### ADR-0017: Core Canon + Genre Extension
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P1  
**Context**: Genre-specific state fields  
**Decision**: Core Canon domain-neutral + Genre Extensions for specifics  
**Rationale**: Principle P-002, enable multi-genre  
**Owner**: V2-008 (P1)

### ADR-0018: Architecture Fitness Tests
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Automated boundary enforcement  
**Decision**: CI checks dependency direction, authority boundaries  
**Rationale**: V1 lesson (god package), preventARCHITECTURE violations  
**Owner**: V2-003 (P0)

### ADR-0019: Real-provider Contract Tests
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P7  
**Context**: Provider integration validation  
**Decision**: Real model tests for provider/prompt/replay/extraction  
**Rationale**: V1 lesson LESSON-V1-009 (mocks hide real issues)  
**Owner**: V2-029 (P7)

### ADR-0020: Markdown SSOT + Machine-readable Contracts
**Status**: RECOMMENDED (Constitution Section 17)  
**Priority**: P0  
**Context**: Documentation authority  
**Decision**: Markdown = SSOT, YAML/JSON/Schema = machine contracts  
**Rationale**: Constitution Section 16, DOCX = export only  
**Owner**: V2-002 (P0)

---

## 2. REQUIRED ADRs FROM CONFLICT RESOLUTION

### ADR-0021: Character Schema Composition Model
**Status**: REQUIRED  
**Priority**: M1 (blocks V2-006)  
**Source**: CONFLICT-003 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**: 
- `character.schema.json` allows `allOf` with potentially conflicting trait definitions
- Genre extensions may conflict with core traits
- Audit finding AR-04 confirms issue

**Decision Options**:
- **A**: Flatten schema (no allOf)
- **B**: Trait namespacing (core.cautious vs genre.reckless)
- **C**: Semantic conflict validation at commit time

**Recommendation**: Option C
- Keep flexible composition
- Add CharacterTraitValidator
- Define trait conflict rules per genre

**Consequences**:
- Positive: Flexible Genre extensions
- Negative: Runtime validation complexity
- Mitigation: Clear error messages for conflicts

**Tests**:
- TEST-DOMAIN-004: character_trait_uniqueness
- TEST-GENRE-003: genre_extension_no_core_conflict

**Owner**: V2-006 (P2)  
**Deadline**: Before M1

---

### ADR-0022: Promise Temporal Binding Model
**Status**: REQUIRED  
**Priority**: M1 (blocks V2-006)  
**Source**: CONFLICT-004 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- Promises lack temporal anchors in schema
- Risk of promise debt accumulation (RISK-L01)
- Planning spec assumes payoff tracking but schema doesn't enforce

**Decision Options**:
- **A**: Hard requirement (all promises specify expected payoff)
- **B**: Soft requirement (< 10 chapters required, distant optional)
- **C**: Two promise types (Imminent vs LongTerm)

**Recommendation**: Option B
- Required for promises within 10 chapters
- Optional for long-arc promises
- Add `expected_payoff_chapter_range` to schema

**Consequences**:
- Positive: Prevent near-term promise floating
- Positive: Allow flexibility for long arcs
- Negative: Validation complexity
- Mitigation: Clear policy in planning-policy.yaml

**Tests**:
- TEST-DOMAIN-008: promise_payoff_tracking
- TEST-PLAN-006: imminent_promise_has_timing

**Owner**: V2-006 (P2), V2-011 (P4)  
**Deadline**: Before M1

---

### ADR-0023: Event Type vs Occurrence Model
**Status**: REQUIRED  
**Priority**: M1 (blocks V2-006)  
**Source**: CONFLICT-005 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- `event.schema.json` conflates event patterns with instances
- Querying ambiguous (by type or by occurrence?)
- Audit finding AR-06

**Decision Options**:
- **A**: Single entity with type/instance fields
- **B**: Separate EventType and EventOccurrence schemas
- **C**: EventTemplate + EventInstance pattern

**Recommendation**: Option C
- EventTemplate: Reusable patterns ("confrontation", "revelation")
- EventInstance: Specific occurrences with participants, time, location
- EventInstance references EventTemplate (optional)

**Consequences**:
- Positive: Clear separation, reusable patterns
- Positive: Better querying ("all confrontations" vs "Ch5 confrontation")
- Negative: Two schemas instead of one
- Mitigation: Make template reference optional (not all events need templates)

**Tests**:
- TEST-DOMAIN-011: event_template_reusable
- TEST-DOMAIN-012: event_instance_unique

**Owner**: V2-006 (P2)  
**Deadline**: Before M1

---

### ADR-0024: Canon Extension Namespace Model
**Status**: REQUIRED  
**Priority**: M3 (blocks dual genre certification)  
**Source**: CONFLICT-006 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- Genre extensions may have naming collisions (urban.wealth vs fantasy.wealth)
- Dual genre certification (M3) at risk
- Audit finding AR-08

**Decision Options**:
- **A**: Mandatory prefix (urban.wealth vs fantasy.wealth)
- **B**: GenrePack ID prefix (GPK-U01.wealth vs GPK-X01.wealth)
- **C**: Scoped extension objects (extensions.urban.wealth)

**Recommendation**: Option C
- Scoped objects: `{ extensions: { urban: { wealth: ... }, fantasy: { realm: ... } } }`
- Clear ownership, explicit scope
- No string manipulation needed

**Consequences**:
- Positive: Clean schema, clear boundaries
- Positive: Easy to detect cross-genre access
- Negative: Deeper nesting in Canon state
- Mitigation: Context Compiler flattens for Worker consumption

**Tests**:
- TEST-GENRE-008: extension_namespace_no_collision
- TEST-M3-001: dual_genre_30ch_zero_contamination

**Owner**: V2-008 (P1), V2-009 (P3)  
**Deadline**: Before M3

---

### ADR-0025: Context Budget Overflow Handling
**Status**: REQUIRED  
**Priority**: M2 (blocks V2-013)  
**Source**: CONFLICT-007 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- Mandatory context items may exceed token budget
- context-policy.yaml says "mandatory_items_never_trimmed" but no overflow behavior
- Audit finding AR-09

**Decision Options**:
- **A**: BLOCK with error (refuse compilation)
- **B**: EXPAND budget automatically (override limit)
- **C**: FAIL with human decision required
- **D**: Hierarchical mandatory (P0 vs P1 mandatory)

**Recommendation**: Option A + Option D (future)
- Phase 1: BLOCK with clear error message
- Phase 2: Introduce mandatory priority levels
  - CRITICAL: Character identity, genre rules (never trim)
  - REQUIRED: Recent events, active contracts (trim last if必须)
  - PREFERRED: Background context (trim first)

**Consequences**:
- Positive: Clear failure mode, no silent truncation
- Positive: Forces explicit budget planning
- Negative: May block valid compilations initially
- Mitigation: Dashboard shows budget usage, helps tuning

**Tests**:
- TEST-CONTEXT-009: mandatory_overflow_blocks
- TEST-CONTEXT-010: budget_advisory_accurate

**Owner**: V2-013 (P5)  
**Deadline**: Before M2

---

## 3. RECOMMENDED ADRs FROM GAPS

### ADR-0026: Genesis-Planning Interface Contract
**Status**: RECOMMENDED  
**Priority**: P4/P10  
**Source**: GAP-001 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- GenesisSpec output format (P10) differs from SeriesVision input (P4)
- Explicit transformation not specified
- May require adapter

**Decision Options**:
- **A**: GenesisSpec directly produces SeriesVision format
- **B**: Adapter service translates GenesisSpec → SeriesVision
- **C**: SeriesVision accepts GenesisSpec as-is (no transformation)

**Recommendation**: Option B (adapter)
- Genesis focuses on startup concerns
- Planning focuses on production concerns
- Adapter bridges domains cleanly

**Owner**: V2-011 (P4), V2-042 (P10)  
**Deadline**: Before P10 implementation

---

### ADR-0027: Repair Workflow Integration
**Status**: RECOMMENDED  
**Priority**: P6  
**Source**: GAP-002 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- RepairPlan artifact defined (QUALITY spec)
- Workflow repair loop mentioned but RepairPlan consumption unclear
- Need formal integration

**Decision Options**:
- **A**: RepairStage explicitly consumes RepairPlan
- **B**: Repair loop is meta-workflow (outside main workflow)
- **C**: Repair inlined in quality stage (no separate stage)

**Recommendation**: Option A
- Explicit RepairStage in workflow
- Takes RepairPlan as input
- Outputs patched Draft
- Re-enters validation

**Owner**: V2-023 (P6), V2-024 (P6)  
**Deadline**: Before P6 complete

---

### ADR-0028: Market Signal Aggregation and Promotion Thresholds
**Status**: RECOMMENDED  
**Priority**: P13  
**Source**: GAP-003 (ARCHITECTURE_CONFLICT_REGISTER)

**Context**:
- MarketSignal capture defined
- Promotion Gate exists
- Aggregation algorithm and thresholds not specified

**Decision Options**:
- **A**: Fixed thresholds (e.g., retention > 60%)
- **B**: Statistical significance tests
- **C**: A/B test winner selection
- **D**: Human judgment after signal review

**Recommendation**: Option D initially, evolve to C
- P13 initial: Human reviews signals, approves promotions
- P14: Statistical A/B testing automated

**Owner**: V2-044 (P13), V2-055 (P13)  
**Deadline**: Before P13 complete

---

## 4. ADR STATUS SUMMARY

| ADR | Title | Status | Priority | Owner | Deadline |
|-----|-------|--------|----------|-------|----------|
| ADR-0001 | Modular Monolith First | RECOMMENDED | P0 | V2-001 | M0 |
| ADR-0002 | Genre is Foundational | RECOMMENDED | P1 | V2-007 | M1 |
| ADR-0003 | Draft is not Canon | RECOMMENDED | P0 | V2-009 | M1 |
| ADR-0004 | Canon Commit Only Boundary | RECOMMENDED | P0 | V2-009 | M1 |
| ADR-0005 | Event Log + Snapshot | RECOMMENDED | P3 | V2-009 | M1 |
| ADR-0006 | Multi-source Genesis | RECOMMENDED | P10 | V2-042 | M6 |
| ADR-0007 | Provider Gateway | RECOMMENDED | P7 | V2-027 | M4 |
| ADR-0008 | Context Compiler | RECOMMENDED | P5 | V2-013 | M2 |
| ADR-0009 | Fail-Closed Production | RECOMMENDED | P3 | V2-009 | M1 |
| ADR-0010 | Durable Workflow | RECOMMENDED | P8 | V2-017 | M4 |
| ADR-0011 | Evidence Level Authority | RECOMMENDED | P6 | V2-020 | M3 |
| ADR-0012 | Reference Firewall | RECOMMENDED | P10 | V2-042 | M6 |
| ADR-0013 | Patch-first Repair | RECOMMENDED | P6 | V2-023 | M3 |
| ADR-0014 | Human Authority | RECOMMENDED | P0 | V2-002 | M0 |
| ADR-0015 | Provenance & Fingerprint | RECOMMENDED | P3 | V2-009 | M1 |
| ADR-0016 | Market vs Genre Separation | RECOMMENDED | P13 | V2-044 | M7 |
| ADR-0017 | Core + Extension Model | RECOMMENDED | P1 | V2-008 | M1 |
| ADR-0018 | Architecture Fitness | RECOMMENDED | P0 | V2-003 | M0 |
| ADR-0019 | Real-provider Tests | RECOMMENDED | P7 | V2-029 | M4 |
| ADR-0020 | Markdown SSOT | RECOMMENDED | P0 | V2-002 | M0 |
| **ADR-0021** | **Character Schema** | **REQUIRED** | **M1** | **V2-006** | **Before M1** |
| **ADR-0022** | **Promise Temporal** | **REQUIRED** | **M1** | **V2-006** | **Before M1** |
| **ADR-0023** | **Event Type/Occurrence** | **REQUIRED** | **M1** | **V2-006** | **Before M1** |
| **ADR-0024** | **Extension Namespace** | **REQUIRED** | **M3** | **V2-008** | **Before M3** |
| **ADR-0025** | **Context Overflow** | **REQUIRED** | **M2** | **V2-013** | **Before M2** |
| ADR-0026 | Genesis-Planning Interface | RECOMMENDED | P4/P10 | V2-011/042 | Before P10 |
| ADR-0027 | Repair Integration | RECOMMENDED | P6 | V2-023 | Before P6 |
| ADR-0028 | Market Signal Promotion | RECOMMENDED | P13 | V2-044 | Before P13 |

**Total**: 28 ADRs (20 recommended from Constitution, 5 required from conflicts, 3 recommended from gaps)

---

## 5. BLOCKING ANALYSIS

**M0 (P0) Blockers**: None (ADRs 1, 3, 4, 14, 18, 20 are recommendations, not blockers)

**M1 Blockers**:
- ❌ ADR-0021: Character schema composition
- ❌ ADR-0022: Promise temporal binding
- ❌ ADR-0023: Event type vs occurrence
- **Status**: 3 REQUIRED ADRs must be written before M1

**M2 Blockers**:
- ❌ ADR-0025: Context budget overflow
- **Status**: 1 REQUIRED ADR must be written before M2

**M3 Blockers**:
- ❌ ADR-0024: Canon extension namespace
- **Status**: 1 REQUIRED ADR must be written before M3 dual genre certification

---

## 6. ADR WORKFLOW

**Creation Process**:
1. Identify need (conflict, gap, major decision)
2. Log in this register with REQUIRED/RECOMMENDED status
3. Research options
4. Write ADR with format above
5. Review with stakeholders
6. Status → PROPOSED
7. Decision approved → ACCEPTED
8. Implementation → Update specs + code
9. Verification → Tests pass
10. ADR → IMPLEMENTED

**ADR Location**: `/Users/angyang/Documents/AI/ANovelOS/docs/adr/`

**ADR Index**: Maintained in `docs/00-governance/ADR_INDEX.md`

---

## 7. IMPLEMENTATION TRACKING

**P0 (V2-002)**: 
- Create ADR directory structure
- Initialize ADR-0001 through ADR-0020 (Constitution recommendations)
- Establish ADR review process

**P2 (V2-006)**:
- Write ADR-0021, ADR-0022, ADR-0023
- Update NARRATIVE_DOMAIN_SPEC with decisions
- Update schemas

**P5 (V2-013)**:
- Write ADR-0025
- Update CONTEXT_INTELLIGENCE_SPEC

**P1/P3 (V2-008/009)**:
- Write ADR-0024
- Update GENRE_INTELLIGENCE_SPEC and CANONICAL_STATE_SPEC

---

**Document Status**: NORMATIVE  
**Next Update**: As conflicts resolved and ADRs written  
**Owner**: Architecture convergence → Implementation teams

---

**END OF REQUIRED ADR REGISTER**
