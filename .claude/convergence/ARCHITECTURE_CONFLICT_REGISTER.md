# ANovel V2 Architecture Conflict Register

**Document ID**: CONV-0005  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Log and resolve all architectural conflicts across V2 specifications

---

## 0. Conflict Resolution Protocol

**When same-tier (T1) conflicts exist**:
1. Log in this register with CONFLICT-ID
2. Identify all affected specifications
3. Analyze impact on implementation phases
4. Determine resolution approach (ADR required if fundamental)
5. Update specifications
6. Mark conflict as RESOLVED
7. Close with evidence of resolution

**Status Codes**:
- **OPEN** - Conflict identified, awaiting resolution
- **ANALYZING** - Under investigation
- **ADR_REQUIRED** - Needs formal Architecture Decision Record
- **RESOLVED** - Fixed, specifications updated
- **CLOSED** - Verified resolved, evidence attached

---

## 1. CRITICAL CONFLICTS (P0-Blocking)

### CONFLICT-001: Strategic Direction Misalignment

**Tier**: T6 vs User Directive + T1  
**Status**: **RESOLVED**  
**Priority**: P0

**Conflict**:
- **ccdoc/** (25 documents): Proposes "Strategic Refactor" of V1 (60-70% code retention)
- **User Directive + gptdoc + Constitution**: Greenfield V2 architecture with selective migration

**Sources**:
- ccdoc/README.md: "战略性重构"，"60-70% 代码可保留或重构"
- gptdoc/IMPLEMENTATION_PLAN.md: "Greenfield Rewrite + Selective Migration"
- PROJECT_CONSTITUTION.md Section 7: "V2 应继承 V1 的认知，不继承 V1 的结构性混乱"

**Impact**:
- Repository strategy (refactor branch vs new repo)
- Migration scope (code vs concepts)
- Timeline estimates (3-6 months refactor vs 12-18 months greenfield)

**Resolution**:
- **Decision**: Greenfield V2 (per user directive)
- **ccdoc Status**: Downgraded to DESIGN_CANDIDATE (T6) - valuable concepts only
- **Implementation**: CCDOC_ADOPTION_MATRIX.md documents ADOPT/ADAPT/DEFER/REJECT per element
- **Migration**: V1_REUSE_DECISION_MATRIX.md defines selective concept migration

**Evidence**:
- CCDOC_ADOPTION_MATRIX.md (CONV output): 12 ADOPT, 28 ADAPT, 15 DEFER, 8 REJECT, 3 HISTORICAL
- Strategic refactor approach explicitly rejected
- V1 code prohibited from wholesale copy (Constitution PROHIBIT-014)

**Closed**: 2026-09-19

---

## 2. HIGH-PRIORITY CONFLICTS (M1-Blocking)

### CONFLICT-002: "Evidence" Terminology Multi-Meaning

**Tier**: T1 (within gptdoc specs)  
**Status**: **RESOLVED**  
**Priority**: P0 (terminology baseline)

**Conflict**:
- **QUALITY_EVALUATION_REPAIR_SPEC**: "Evidence Level" (E1-E4) = confidence in quality evaluation
- **MULTI_SOURCE_GENESIS_SPEC**: "Evidence Pack" = reference material from source novels
- **CORPUS_EVALUATION_LEARNING_SPEC**: "Evidence" = experimental validation proof

**Sources**:
- gptdoc cross-reference analysis (AR-02 from architecture audit)
- QUALITY spec Section 38-42: Evidence Level definition
- GENESIS spec Section 42: EvidencePack definition

**Impact**:
- AI agents may confuse contexts
- Schema naming conflicts
- Documentation ambiguity
- Code variable naming

**Resolution**:
- **TERMINOLOGY_BASELINE.md** (CONV-0003) Section 1.1:
  - Quality: Keep "Evidence Level" as compound term OR rename to `QualityConfidenceLevel`
  - Genesis: Rename to `ReferencePack` (partially done)
  - Learning: Use `ExperimentalProof` or `ValidationEvidence`

**Implementation Gates**:
- P0 (V2-002): Terminology freeze
- P5 (V2-013): Context uses correct terms
- P6 (V2-020-026): Quality uses QualityConfidenceLevel
- P7 (V2-022, V2-026): Enforcement in schemas

**Status Change**: OPEN → RESOLVED (2026-09-19)

---

### CONFLICT-003: Character Schema Composition Issue

**Tier**: T1 (NARRATIVE_DOMAIN_SPEC schema defect)  
**Status**: **OPEN → ADR_REQUIRED**  
**Priority**: M1 (blocks V2-006)

**Conflict**:
- **character.schema.json**: Allows `allOf` with potentially conflicting trait definitions
- **Audit Finding**: AR-04 confirms trait uniqueness not enforced across composition layers

**Sources**:
- architecture-review-2026-09-18/ARCHITECTURE_AUDIT_REPORT.md AR-04
- gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/character.schema.json
- NARRATIVE_DOMAIN_SPEC.md Section 23

**Impact**:
- Characters could have contradictory traits (e.g., "cautious" + "reckless")
- Genre-specific character extensions might conflict with core traits
- Identity stability compromised

**Resolution Needed**:
- **Option A**: Flatten character schema (no allOf, single trait list with uniqueness)
- **Option B**: Trait namespacing (core.cautious vs genre.reckless)
- **Option C**: Trait conflict validation at commit time (allow schema, validate semantically)

**Recommendation**: Option C - Keep flexible schema, add semantic validator
- Rationale: Genre extensions need composition, but conflicts must be caught
- Implementation: V2-006 adds CharacterTraitValidator with conflict rules

**ADR Required**: ADR-0021 Character Schema Composition Model  
**Affected Phases**: P2 (V2-005, V2-006)  
**Acceptance**: Identity stability + trait uniqueness validation passes TEST-DOMAIN-004

---

### CONFLICT-004: Promise Schema Temporal Binding Gap

**Tier**: T1 (cross-spec gap)  
**Status**: **OPEN → ADR_REQUIRED**  
**Priority**: M1 (blocks V2-006)

**Conflict**:
- **NARRATIVE_DOMAIN_SPEC**: Promise entity defined but no temporal anchors required
- **PLANNING_CONTRACT_SPEC**: Promise scheduling and payoff expected but schema doesn't enforce

**Sources**:
- AR-05 from architecture audit
- NARRATIVE_DOMAIN Section 42: Promise definition
- PLANNING_CONTRACT Section 36-37: Reader Promise scheduling
- promise.schema.json: Missing temporal constraint fields

**Impact**:
- Promises may "float" without explicit payoff timing
- Payoff tracking ambiguous
- Promise debt accumulation risk (RISK-L01)

**Resolution Needed**:
- Add to promise.schema.json: `expected_payoff_chapter_range` or similar temporal binding
- Options:
  - **A**: Hard requirement (promise MUST specify expected payoff chapter)
  - **B**: Soft requirement (allow null for distant payoffs, require for near-term)
  - **C**: Two promise types (ImminentPromise requires timing, LongTermPromise optional)

**Recommendation**: Option B - Required for < 10 chapters, optional for distant
- Rationale: Allows flexibility for long arcs while enforcing near-term discipline

**ADR Required**: ADR-0022 Promise Temporal Binding Model  
**Affected Phases**: P2 (V2-006), P4 (V2-011, V2-012)  
**Acceptance**: Promise payoff tracking validated in TEST-DOMAIN-008

---

### CONFLICT-005: Event Identity vs Occurrence Confusion

**Tier**: T1 (NARRATIVE_DOMAIN_SPEC schema design)  
**Status**: **OPEN → ADR_REQUIRED**  
**Priority**: M1 (blocks V2-006)

**Conflict**:
- **event.schema.json**: Conflates event types (pattern) with event occurrences (instance)
- Example: "Character confronts antagonist" (type) vs "Zhang Wei confronted Li Ming in Ch5:S2" (occurrence)

**Sources**:
- AR-06 from architecture audit
- NARRATIVE_DOMAIN_SPEC event definitions
- event.schema.json

**Impact**:
- Event classification ambiguous
- Event querying/filtering unclear (search by type or instance?)
- Event reuse patterns unclear

**Resolution Needed**:
- **Option A**: Single event entity with type/instance fields
- **Option B**: Separate EventType and EventOccurrence schemas
- **Option C**: Event templates (type) and Event instances reference templates

**Recommendation**: Option C - EventTemplate + EventInstance pattern
- Rationale: Allows reusable event patterns + unique occurrences
- Implementation: event-template.schema.json + event-occurrence.schema.json

**ADR Required**: ADR-0023 Event Type vs Occurrence Model  
**Affected Phases**: P2 (V2-006)  
**Acceptance**: Event querying and pattern matching validated

---

## 3. MEDIUM-PRIORITY CONFLICTS (M3-Blocking)

### CONFLICT-006: Canon Extension Namespace Collision Risk

**Tier**: T1 (cross-spec concern)  
**Status**: **OPEN**  
**Priority**: M3 (blocks dual genre certification)

**Conflict**:
- **GENRE_INTELLIGENCE_SPEC** Section 27: Defines Canon Extensions for genre-specific state
- **CANONICAL_STATE_SPEC** Section 52: Extension registration but no namespace isolation
- **Risk**: Urban GenrePack "wealth" field could collide with Fantasy GenrePack "wealth" field (cultivation resource)

**Sources**:
- AR-08 from architecture audit
- GENRE_INTELLIGENCE_SPEC Section 27
- CANONICAL_STATE_SPEC Section 52

**Impact**:
- Dual genre projects (M3 milestone) may have field name collisions
- Genre switching contamination
- State reconstruction ambiguity

**Resolution Needed**:
- **Option A**: Mandatory namespace prefix (urban.wealth vs fantasy.wealth)
- **Option B**: GenrePack ID prefix (GPK-U01.wealth vs GPK-X01.wealth)
- **Option C**: Scoped extension objects (extensions.urban.wealth)

**Recommendation**: Option C - Scoped extension objects
- Rationale: Clean schema structure, clear ownership, explicit scope

**ADR Required**: ADR-0024 Canon Extension Namespace Model  
**Affected Phases**: P1 (V2-008), P3 (V2-009)  
**Acceptance**: Dual genre (urban + fantasy) 30-chapter run with 0 contamination

**Status**: ANALYZING

---

### CONFLICT-007: Context Token Budget Edge Case

**Tier**: T1 (CONTEXT_INTELLIGENCE_SPEC gap)  
**Status**: **OPEN**  
**Priority**: M2 (blocks V2-013)

**Conflict**:
- **CONTEXT_INTELLIGENCE_SPEC** Section 33: Defines token budget and mandatory items
- **context-policy.yaml** CTX-POL-001: "mandatory_items_never_trimmed"
- **Gap**: No behavior specified when mandatory items exceed token budget

**Sources**:
- AR-09 from architecture audit
- CONTEXT_INTELLIGENCE_SPEC Section 26, 33
- context-policy.yaml

**Impact**:
- Implementation may BLOCK silently
- Or FAIL without guidance
- Or EXPAND budget uncontrollably
- Or TRUNCATE mandatory items (violates policy)

**Resolution Needed**:
- **Option A**: BLOCK with error (refuse to compile context)
- **Option B**: EXPAND budget automatically (override token limit)
- **Option C**: FAIL with human decision required
- **Option D**: Hierarchical mandatory (must-have vs should-have)

**Recommendation**: Option A + Option D
- Primary: BLOCK with clear error message
- Future: Introduce mandatory priority levels (P0 vs P1 mandatory)

**ADR Required**: ADR-0025 Context Budget Overflow Handling  
**Affected Phases**: P5 (V2-013)  
**Acceptance**: TEST-CONTEXT-009 mandatory_overflow_blocks

**Status**: ANALYZING

---

## 4. INTEGRATION GAPS (Not conflicts, but undefined handoffs)

### GAP-001: Genesis→Planning Transformation

**Tier**: T1 cross-spec handoff  
**Status**: **OPEN**  
**Priority**: P4 (V2-011 interface)

**Gap**:
- **MULTI_SOURCE_GENESIS_SPEC** Section 78: Defines GenesisSpec output format
- **PLANNING_CONTRACT_SPEC** Section 14: Assumes SeriesVision input format
- **Missing**: Explicit transformation/adapter specification

**Sources**:
- gptdoc cross-reference analysis Section 5.3.1
- GENESIS Section 78
- PLANNING Section 14

**Impact**:
- P10 Genesis and P4 Planning implementations may have incompatible interfaces
- Requires runtime adapter or manual transformation

**Resolution**:
- **IMPLEMENTATION_PLAN** V2-009 includes "Genesis-to-Plan adapter" task
- Recommend: Formalize adapter contract in ADR

**ADR Recommended**: ADR-0026 Genesis-Planning Interface Contract  
**Affected Phases**: P4 (V2-011), P10 (V2-042)  
**Workaround**: P4 can use stub GenesisSpec until P10

**Status**: ACKNOWLEDGED (not blocking P4, adapter task exists)

---

### GAP-002: RepairPlan→Workflow Integration

**Tier**: T1 cross-spec handoff  
**Status**: **OPEN**  
**Priority**: P6 (V2-023, V2-024)

**Gap**:
- **QUALITY_EVALUATION_REPAIR_SPEC** Section 60-70: Defines RepairPlan artifact
- **PRODUCTION_WORKFLOW_SPEC** Section 46: Mentions repair loop but doesn't show RepairPlan as Stage input
- **Missing**: Formal RepairPlan → Workflow Stage binding

**Sources**:
- gptdoc cross-reference analysis Section 5.3.3
- QUALITY Section 60
- WORKFLOW Section 46

**Impact**:
- Repair implementation may be ad-hoc
- RepairPlan authority unclear
- Repair retry semantics undefined

**Resolution**:
- Recommend: Formalize RepairStage in workflow with RepairPlan input contract

**ADR Recommended**: ADR-0027 Repair Workflow Integration  
**Affected Phases**: P6 (V2-023, V2-024)  

**Status**: ACKNOWLEDGED (implementation detail, likely resolved during P6)

---

### GAP-003: Market Signal→Policy Promotion Path

**Tier**: T1 cross-spec handoff  
**Status**: **OPEN (Deferred to P13)**  
**Priority**: P13 (V2-044, V2-055)

**Gap**:
- **CORPUS_EVALUATION_LEARNING_SPEC** Section 80-85: Defines MarketSignal capture
- **CORPUS_EVALUATION_LEARNING_SPEC** Section 95-101: Defines Promotion Gate
- **Missing**: Signal aggregation algorithm, decision thresholds

**Sources**:
- gptdoc cross-reference analysis Section 5.3.4
- CORPUS_LEARNING Section 80-85, 95-101

**Impact**:
- P13 Learning implementation may lack concrete promotion criteria
- Market signal → policy deployment unclear

**Resolution**:
- **Status**: Intentionally abstract for later calibration
- Recommend: P13 tasks must define concrete thresholds during implementation

**ADR Recommended**: ADR-0028 Market Signal Aggregation and Promotion Thresholds  
**Affected Phases**: P13 (V2-044, V2-055)  

**Status**: DEFERRED (P13 is post-M5, not blocking early phases)

---

## 5. RESOLVED TERMINOLOGY CONFLICTS

### CONFLICT-008: "Authority" Dual Meaning

**Status**: **RESOLVED**  
**Resolution**: TERMINOLOGY_BASELINE.md Section 1.2
- Context Compiler: Use `SourcePrecedence`
- Document metadata: Keep `Authority` field (context distinguishes)

---

### CONFLICT-009: "Contract" Multi-Layer Usage

**Status**: **RESOLVED**  
**Resolution**: TERMINOLOGY_BASELINE.md Section 1.3
- Narrative: `ChapterContract`, `SceneContract`
- Technical: `StageContract` (or `ExecutionContract`)
- No rename needed if always qualified

---

## 6. NON-CONFLICTS (Clarifications)

### CLARIFICATION-001: "Commit" Ambiguity

**Status**: NOT A CONFLICT - Context always distinguishes
- CanonCommit: Narrative state change
- Git commit: Version control
- Workflow CommitStage: Production step

**Resolution**: Always use full term in ambiguous contexts

---

### CLARIFICATION-002: Workflow State vs Canon State

**Status**: NOT A CONFLICT - Explicitly separated
- BOUNDARY_SEPARATIONS_VERIFICATION.md confirms PASS
- WF-POL-002 policy enforces separation

---

### CLARIFICATION-003: Dual Genre Project Model

**Status**: NOT A CONFLICT - Implicitly supported
- GENRE_INTELLIGENCE_SPEC Section 15: One GenrePack active per project
- IMPLEMENTATION_PLAN M3: "Dual Genre Pack certification"
- **Interpretation**: Multiple GenrePacks can coexist, switching/isolation semantics clarified during V2-007/V2-008

---

## 7. CONFLICT SUMMARY TABLE

| ID | Conflict | Tier | Priority | Status | Blocking Phase | ADR Needed |
|----|----------|------|----------|--------|----------------|------------|
| C-001 | Strategic direction (ccdoc vs gptdoc) | T6 vs T1 | P0 | RESOLVED | None | No (decision made) |
| C-002 | "Evidence" multi-meaning | T1 | P0 | RESOLVED | None | No (terminology fix) |
| C-003 | Character schema composition | T1 | M1 | OPEN | P2 (V2-006) | Yes (ADR-0021) |
| C-004 | Promise temporal binding | T1 | M1 | OPEN | P2 (V2-006) | Yes (ADR-0022) |
| C-005 | Event type vs occurrence | T1 | M1 | OPEN | P2 (V2-006) | Yes (ADR-0023) |
| C-006 | Canon extension namespace | T1 | M3 | ANALYZING | P1 (V2-008) | Yes (ADR-0024) |
| C-007 | Context budget overflow | T1 | M2 | ANALYZING | P5 (V2-013) | Yes (ADR-0025) |
| GAP-001 | Genesis→Planning interface | T1 | P4 | OPEN | P4/P10 | Recommended (ADR-0026) |
| GAP-002 | RepairPlan→Workflow | T1 | P6 | OPEN | P6 | Recommended (ADR-0027) |
| GAP-003 | Market Signal→Promotion | T1 | P13 | DEFERRED | P13 | Recommended (ADR-0028) |

**Total**: 7 conflicts, 3 gaps, 3 clarifications

**Status Breakdown**:
- RESOLVED: 2 (C-001, C-002)
- OPEN: 5 (C-003, C-004, C-005, C-007, GAP-001, GAP-002)
- ANALYZING: 1 (C-006)
- DEFERRED: 1 (GAP-003)

**ADR Requirements**: 6 recommended, 0 completed

---

## 8. CONFLICT RESOLUTION GATES

**P0 (V2-002)**:
- ✅ C-001 RESOLVED (Strategic direction)
- ✅ C-002 RESOLVED (Evidence terminology)
- ⚠️ ADR register must be established (Task #14)

**M1 (V2-006)**:
- ❌ C-003 MUST RESOLVE (Character schema)
- ❌ C-004 MUST RESOLVE (Promise temporal)
- ❌ C-005 MUST RESOLVE (Event type/occurrence)
- Requires: ADR-0021, ADR-0022, ADR-0023

**M2 (V2-013)**:
- ❌ C-007 MUST RESOLVE (Context budget)
- Requires: ADR-0025

**M3 (V2-008)**:
- ⚠️ C-006 SHOULD RESOLVE (Canon extension namespace)
- Requires: ADR-0024

---

## 9. IMPLEMENTATION ACTIONS

**Immediate (P0)**:
1. ✅ Freeze TERMINOLOGY_BASELINE.md (resolves C-002)
2. ✅ Document strategic direction (resolves C-001)
3. ⏳ Create REQUIRED_ADR_REGISTER.md (Task #14)

**Before M1 (P2)**:
1. ⏳ Write ADR-0021 (Character schema composition)
2. ⏳ Write ADR-0022 (Promise temporal binding)
3. ⏳ Write ADR-0023 (Event type vs occurrence)
4. ⏳ Update NARRATIVE_DOMAIN_SPEC with decisions
5. ⏳ Update character.schema.json, promise.schema.json, event.schema.json

**Before M2 (P5)**:
1. ⏳ Write ADR-0025 (Context budget overflow)
2. ⏳ Update CONTEXT_INTELLIGENCE_SPEC
3. ⏳ Update context-policy.yaml

**Before M3 (P1-P3)**:
1. ⏳ Write ADR-0024 (Canon extension namespace)
2. ⏳ Update GENRE_INTELLIGENCE_SPEC Section 27
3. ⏳ Update CANONICAL_STATE_SPEC Section 52

---

## 10. CHANGE LOG

| Date | Change | Status |
|------|--------|--------|
| 2026-09-19 | Initial register created | - |
| 2026-09-19 | C-001 resolved (strategic direction) | CLOSED |
| 2026-09-19 | C-002 resolved (Evidence terminology) | CLOSED |
| 2026-09-19 | C-003 to C-007 logged | OPEN |
| 2026-09-19 | GAP-001 to GAP-003 logged | OPEN |

---

**Document Status**: NORMATIVE  
**Next Update**: After ADRs written and conflicts resolved  
**Owner**: Architecture convergence process

---

**END OF ARCHITECTURE CONFLICT REGISTER**
