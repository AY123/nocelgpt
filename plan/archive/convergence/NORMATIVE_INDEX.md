# ANovel V2 Normative Index & Truth Hierarchy

**Document ID**: CONV-0002  
**Version**: 1.0  
**Status**: NORMATIVE  
**Created**: 2026-09-19  
**Authority**: CONVERGENCE-BASELINE  
**Purpose**: Establish definitive truth hierarchy (T0-T7) and normative document index for ANovel V2

---

## 1. Truth Hierarchy Definition

Per PROJECT_CONSTITUTION.md Section 8, all conflicts resolve according to this hierarchy:

```
T0 — Project Constitution
     └─ Immutable principles, authority model, invariants

T1 — Approved ADR / Normative Architecture Specification  
     └─ Formal design decisions, domain specifications

T2 — Genre Constitution / Domain Policy
     └─ Genre rules, domain contracts, world models

T3 — Canonical Narrative State
     └─ Committed story facts (what happened)

T4 — Approved Plan / Arc / Chapter / Scene Contract
     └─ Future intentions (what should happen)

T5 — External Evidence (Reference / Corpus / Market)
     └─ Research, market data, competitive analysis

T6 — Generated Artifact / Draft / Candidate
     └─ AI proposals, design candidates, draft text

T7 — AI Analysis / Judge / Recommendation
     └─ Evaluation outputs, diagnostic scores
```

**Key Principle**: Lower tiers CANNOT override higher tiers.

**Conflict Resolution Rules**:
- Plan vs Canon conflict → Canon wins, Plan re-plans
- Reference vs Canon conflict → Canon wins
- Judge vs deterministic invariant → Invariant wins
- Market vs Genre Constitution → Cannot silently change Genre
- Draft vs Canon → Draft never becomes Canon without CanonCommit

---

## 2. T0 — Project Constitution

**Single Source of Truth**:

| Document | Path | Version | Status | Notes |
|----------|------|---------|--------|-------|
| PROJECT_CONSTITUTION.md | gptdoc/ANovel_V2_Project_Constitution_v1.0/ | 1.0.0 | **NORMATIVE** | Declares itself BASELINE/NORMATIVE; all other specs depend on this |

**Authority**: PROJECT-CONSTITUTION  
**Change Rule**: Major changes require ADR + constitution version upgrade; AI cannot autonomously modify  
**Scope**: 
- 20 Core Principles (P-001 to P-020)
- 12 V1 Lessons (LESSON-V1-001 to 012)
- 15 Core Invariants (INV-001 to 015)
- 14 Architecture Prohibitions (PROHIBIT-001 to 014)
- Truth Hierarchy T0-T7
- Authority Model
- AI Engineering Charter
- Human Authority Boundaries
- 30/100/300 chapter success criteria

**Depends On**: None (root document)  
**Depended By**: All specifications

---

## 3. T1 — Normative Architecture Specifications

### 3.1 Current Status

**All T1 documents are NORMATIVE_CANDIDATE pending final conflict resolution.**

After convergence is complete, these will be promoted to full NORMATIVE status.

### 3.2 Research Foundation Layer (T5 Input → T1 Baseline)

| Document | Doc ID | Version | Status | Authority | Supersedes |
|----------|--------|---------|--------|-----------|------------|
| V1_FORENSIC_LESSONS.md | RES-0001 | 1.0.0 | BASELINE/NORMATIVE-INPUT | RESEARCH-EVIDENCE | None (first forensic) |
| REFERENCE_ARCHITECTURE_STUDY.md | RES-0002 | 1.0.0 | BASELINE/RESEARCH-INPUT | RESEARCH-EVIDENCE | None |
| WEBNOVEL_MARKET_GENRE_RESEARCH.md | RES-0003 | 1.0.0 | BASELINE/RESEARCH-INPUT | RESEARCH-EVIDENCE | None |

**Notes**: 
- These provide T5 evidence but are elevated to normative input status for V2 architecture decisions
- V1_FORENSIC_LESSONS extracts 12 formal lessons (LESSON-V1-001 to 012) incorporated into Constitution
- REFERENCE_ARCHITECTURE identifies 8 external patterns (EXT-001 to 008) adopted as principles

### 3.3 Core Domain Specifications (Foundation Triad)

**Implementation Order**: Genre → Domain → Canon

| Document | Doc ID | Version | Status | Depends On | Defines |
|----------|--------|---------|--------|------------|---------|
| GENRE_INTELLIGENCE_SPEC.md | SPEC-GENRE-0001 | 1.0.0 | NORMATIVE_CANDIDATE | CONSTITUTION + 3 research | GenrePack, Genre Rules, Canon Extensions, Reality Models |
| NARRATIVE_DOMAIN_SPEC.md | SPEC-DOMAIN-0001 | 1.0.0 | NORMATIVE_CANDIDATE | CONSTITUTION + research + GENRE | Character, Relationship, Event, Knowledge, Promise, Mystery, NarrativeDelta |
| CANONICAL_STATE_SPEC.md | SPEC-CANON-0001 | 1.0.0 | NORMATIVE_CANDIDATE | CONSTITUTION + research + GENRE + DOMAIN | Canon Commit boundary, Event Log, Snapshot, Retcon, Branch |

**Implementation Phases**:
- P1: Genre foundation (V2-007, V2-008)
- P2: Domain types (V2-005, V2-006)  
- P3: Canon transaction (V2-009)

**Known Defects** (from gptdoc analysis):
- AR-04: Character schema composition issue (V2-006)
- AR-05: Promise temporal binding gap (V2-006)
- AR-06: Event identity vs occurrence confusion (V2-006)
- AR-08: Canon extension namespace collision risk (V2-008)

### 3.4 Production Pipeline Specifications

**Implementation Order**: Genesis → Planning → Context → Workflow → Quality → Learning

| Document | Doc ID | Version | Phase | Defines |
|----------|--------|---------|-------|---------|
| MULTI_SOURCE_GENESIS_SPEC.md | SPEC-GENESIS-0001 | 1.0.0 | P10 (deferred) | GenesisSpec, Reference Intelligence, Originality Guard |
| PLANNING_CONTRACT_SPEC.md | SPEC-PLAN-0001 | 1.0.0 | P4 | SeriesVision, ArcPlan, ChapterContract, SceneContract, Required/Forbidden Transitions |
| CONTEXT_INTELLIGENCE_SPEC.md | SPEC-CONTEXT-0001 | 1.0.0 | P5 | ContextArtifact, Context Compiler, Authority Priority, Mandatory Facts |
| PRODUCTION_WORKFLOW_SPEC.md | SPEC-WORKFLOW-0001 | 1.0.0 | P8 | WorkflowRun, Stage, Checkpoint, Retry, Idempotency, Resume |
| QUALITY_EVALUATION_REPAIR_SPEC.md | SPEC-QUALITY-0001 | 1.0.0 | P6 | Q0-Q8 layers, E1-E4 evidence, RepairPlan, Golden Set, Calibration |
| CORPUS_EVALUATION_LEARNING_SPEC.md | SPEC-LEARNING-0001 | 1.0.0 | P13 (deferred) | Corpus Registry, Experiment, Baseline, Promotion Gate, Reader/Market Signal |

**Implementation Phases**:
- P4: Planning/Contract (V2-011, V2-012)
- P5: Context Intelligence (V2-013, V2-014, V2-015)
- P6: Quality/Repair (V2-020 to V2-026)
- P8: Production Workflow (V2-017, V2-018, V2-019)
- P10: Genesis (deferred, minimal bootstrap in P3)
- P13: Learning (deferred)

**Known Gaps**:
- AR-09: Context token budget edge case (V2-013)
- AR-10: Workflow schema completeness (V2-017)
- Genesis→Planning handoff transformation not fully specified
- RepairPlan→Workflow integration needs clarification

### 3.5 Platform Foundation Specification

| Document | Doc ID | Version | Phase | Defines |
|----------|--------|---------|-------|---------|
| PLATFORM_OBSERVABILITY_SECURITY_SPEC.md | SPEC-PLATFORM-0001 | 1.0.0 | P0/P9 | Secrets, Authorization, Audit, Provenance, OpenTelemetry, Artifact Integrity |

**Implementation**: P0 (security baseline) + P9 (observability)

### 3.6 Execution Baseline

| Document | Doc ID | Version | Status | Authority | Defines |
|----------|--------|---------|--------|-----------|---------|
| IMPLEMENTATION_PLAN.md | PLAN-IMPLEMENTATION-0001 | 1.0.0 | NORMATIVE/EXECUTION-BASELINE | IMPLEMENTATION-BASELINE | P0-P14 phases, M0-M7 milestones, V2-001 to V2-060 tasks |

**Dependencies**: All normative specs  
**Scope**: Task graph, CI gates, certification criteria, phase gates

---

## 4. T2 — Genre Constitution / Domain Policy

**Defined In**: GENRE_INTELLIGENCE_SPEC.md (T1) provides the specification  
**Instances**: Individual GenrePacks are T2 artifacts

**Initial Anchor Genres**:

| GenrePack | ID | Version | Status | Definition |
|-----------|----|---------|----- --|------------|
| urban.business.realistic | GPK-U01 | TBD | PLANNED | Urban realism with business/career progression |
| fantasy.eastern.progression | GPK-X01 | TBD | PLANNED | Eastern fantasy with cultivation progression |

**Authority**: GENRE  
**Can Block**: CanonCommit (if Genre Hard Rule violated)  
**Cannot**: Override Constitution, change Canon retroactively without Retcon

**Implementation Phase**: P1 (V2-007, V2-008)  
**Certification**: M3 (dual genre 30-chapter certification)

**Policy Files**:
- `genre-ontology.yaml` - Genre taxonomy and classification
- `example-urban-business-realistic.genre-pack.yaml` - Urban anchor example
- Genre-specific validation rules in each GenrePack

---

## 5. T3 — Canonical Narrative State

**Defined In**: CANONICAL_STATE_SPEC.md (T1) provides the specification  
**Instances**: Per-project Canon Event Log + Canon Snapshots are T3 artifacts

**Authority**: CANON  
**Truth Status**: What has definitively happened in the story  
**Write Boundary**: CanonCommit only (INV-004)  
**Mutation Rules**: Immutable facts cannot change without explicit Retcon

**Key Concepts**:
- Canon HEAD: Current canonical state
- Canon Event Log: Append-only history of all commits
- Canon Snapshot: Projection of state at any commit
- Retcon: Explicit past modification with invalidation cascade

**Implementation Phase**: P3 (V2-009, V2-010)  
**Certification**: M1 (narrative kernel), M2 (single chapter transaction)

**Policy File**: `canon-commit-policy.yaml`

---

## 6. T4 — Approved Plan / Contract

**Defined In**: PLANNING_CONTRACT_SPEC.md (T1) provides the specification  
**Instances**: Per-project SeriesVision, ArcPlan, ChapterContract, SceneContract are T4 artifacts

**Authority**: CONTRACT  
**Truth Status**: What is intended to happen (not what happened)  
**Relationship to Canon**: Plan conflict with Canon → Plan must re-plan (not Canon change)

**Key Concepts**:
- SeriesVision: Overall series direction
- ArcPlan: Multi-chapter narrative arc structure
- ChapterContract: Per-chapter semantic requirements
- SceneContract: Per-scene commitments
- RequiredTransition: Must occur for contract satisfaction
- ForbiddenTransition: Must not occur (Genre or plan constraint)

**Implementation Phase**: P4 (V2-011, V2-012)  
**Certification**: M2 (chapter contract enforcement)

**Policy File**: `planning-policy.yaml`

---

## 7. T5 — External Evidence

**Categories**:

### 7.1 Reference Evidence (Genesis input)
- **Defined In**: MULTI_SOURCE_GENESIS_SPEC.md
- **Authority**: REFERENCE (read-only, never writes Canon directly)
- **Artifacts**: ReferenceEvidencePack
- **Use**: Genesis phase input, mechanism learning
- **Prohibition**: PROHIBIT-008 (continuous reference text cannot enter Writer context directly)

### 7.2 Market Evidence
- **Defined In**: WEBNOVEL_MARKET_GENRE_RESEARCH.md (research), CORPUS_EVALUATION_LEARNING_SPEC.md (operational)
- **Authority**: MARKET (read-only metadata)
- **Artifacts**: MarketTrendSnapshot
- **Use**: Genre design, corpus evaluation
- **Prohibition**: P-009 (cannot silently modify Genre Constitution)

### 7.3 Reader Signal (when available)
- **Defined In**: CORPUS_EVALUATION_LEARNING_SPEC.md section 80-90
- **Authority**: MARKET (E4 evidence level)
- **Use**: Human calibration, policy promotion
- **Phase**: P13 (deferred)

### 7.4 V1 Evidence
- **Classification**: LEGACY/EVIDENCE
- **Sources**: 
  - ainovel/ code and tests
  - project-analysis-2026-09-18/ (forensic findings)
  - V1_REUSE_DECISION_MATRIX.md (convergence output)
  - V1_REGRESSION_ASSET_REGISTER.md (convergence output)
- **Use**: Regression requirements, failure patterns, negative test cases
- **Authority**: EVIDENCE (informs architecture, doesn't dictate)

---

## 8. T6 — Generated Artifact / Draft / Candidate

**Status**: NOT Canon, NOT truth

**Categories**:

### 8.1 Design Candidates
- **ccdoc/** materials (25 files)
- **Classification**: DESIGN_CANDIDATE
- **Authority**: T6 (reference only)
- **Disposition**: Per CCDOC_ADOPTION_MATRIX.md (ADOPT/ADAPT/DEFER/REJECT decisions)
- **Key Principle**: CONSTITUTION P-003 "Draft is NOT Canon"

### 8.2 AI-Generated Proposals
- **NarrativeDelta**: Extracted story changes (from Writer output)
- **Draft Text**: Generated chapter text before validation
- **ChangeSet**: Prepared Canon changes before commit
- **Classification**: CANDIDATE / PROPOSAL
- **Authority**: None until validated and committed
- **Defined In**: NARRATIVE_DOMAIN_SPEC.md section 56-60

### 8.3 Export Artifacts
- **ANovel_V2_PreArchitecture_Pack_2026/** (DOCX files)
- **Classification**: INFORMATIVE (export format)
- **Authority**: None (per CONSTITUTION section 16.1: "DOCX/PDF are export artifacts, not authoritative sources")
- **Use**: Human-readable summaries only

---

## 9. T7 — AI Analysis / Judge / Recommendation

**Status**: Evaluation evidence, NOT truth

**Categories**:

### 9.1 Quality Evaluation Outputs
- **Defined In**: QUALITY_EVALUATION_REPAIR_SPEC.md
- **Evidence Levels**: E1 (deterministic) to E4 (real reader)
- **Use**: Diagnosis, repair guidance, ranking
- **Cannot**: Override Canon, auto-deploy without calibration
- **Key Principle**: CONSTITUTION P-010 "AI Judge is not Ground Truth"

### 9.2 Audit/Review Reports
- **Examples**:
  - architecture-review-2026-09-18/ARCHITECTURE_AUDIT_REPORT.md
  - ccdoc-review-2026-09-19/CCDOC_ARCHITECTURE_AUDIT_REPORT.md
- **Classification**: REVIEW (T7 with normative input weight)
- **Authority**: RECOMMENDATION (findings inform convergence decisions)
- **Use**: Conflict identification, defect detection, adoption guidance

### 9.3 Diagnostic Artifacts
- **RepairPlan**: Proposed fixes (not executed fixes)
- **QualityReport**: Evaluation results
- **Judge Scores**: Comparative rankings
- **Authority**: DIAGNOSTIC (cannot trigger Canon changes directly)

---

## 10. Normative Document Dependency Graph

```
PROJECT_CONSTITUTION (T0)
├─ V1_FORENSIC_LESSONS (T5→T1 input)
├─ REFERENCE_ARCHITECTURE_STUDY (T5→T1 input)
├─ WEBNOVEL_MARKET_GENRE_RESEARCH (T5→T1 input)
│
├─ GENRE_INTELLIGENCE_SPEC (T1→T2)
│  └─ GenrePack instances (T2)
│
├─ NARRATIVE_DOMAIN_SPEC (T1)
│  ├─ depends on: GENRE
│  └─ defines: Core narrative types
│
├─ CANONICAL_STATE_SPEC (T1→T3)
│  ├─ depends on: GENRE, DOMAIN
│  └─ Canon instances (T3)
│
├─ PLANNING_CONTRACT_SPEC (T1→T4)
│  ├─ depends on: GENRE, DOMAIN, CANON
│  └─ Plan/Contract instances (T4)
│
├─ CONTEXT_INTELLIGENCE_SPEC (T1)
│  ├─ depends on: GENRE, DOMAIN, CANON, PLANNING
│  └─ uses: Authority Priority (T0-T5 ordering)
│
├─ PRODUCTION_WORKFLOW_SPEC (T1)
│  ├─ depends on: CONTEXT, PLANNING, CANON
│  └─ wraps: CanonCommit in Workflow Stage
│
├─ QUALITY_EVALUATION_REPAIR_SPEC (T1)
│  ├─ depends on: all above
│  └─ produces: T7 evaluations (evidence, not truth)
│
├─ MULTI_SOURCE_GENESIS_SPEC (T1)
│  ├─ depends on: GENRE, DOMAIN, CANON
│  └─ consumes: T5 Reference Evidence
│
├─ CORPUS_EVALUATION_LEARNING_SPEC (T1)
│  ├─ depends on: all above
│  └─ consumes: T5 Market/Reader Signal
│
├─ PLATFORM_OBSERVABILITY_SECURITY_SPEC (T1)
│  └─ cross-cutting platform concerns
│
└─ IMPLEMENTATION_PLAN (T1 execution baseline)
   └─ depends on: ALL normative specs
```

---

## 11. Supersedes Relationships

### 11.1 Explicit Supersedes

**NONE** explicitly declared in current materials.

All gptdoc specifications are first-generation V2 normative candidates with no prior V2 specifications to supersede.

### 11.2 Implicit Supersession

| Superseded Material | Superseded By | Relationship |
|---------------------|---------------|--------------|
| ccdoc/ strategic refactor approach | gptdoc/ + user greenfield directive | Strategic direction change |
| V1 architecture/code | gptdoc/ specs + V1_FORENSIC_LESSONS | Greenfield rewrite with selective concept migration |
| ccdoc keyword-based Genre | GENRE_INTELLIGENCE_SPEC domain-based Genre | Architecture upgrade (per CCDOC_ADOPTION_MATRIX) |
| V1 multiple verdict centers | CANONICAL_STATE single ProductionState | Architectural correction (LESSON-V1-007) |

### 11.3 Future Supersession

When specifications are revised:
- Must update `Supersedes:` field in document header
- Must increment version per CONSTITUTION Section 26 (PATCH/MINOR/MAJOR rules)
- MAJOR changes require ADR

---

## 12. Authority Boundary Matrix (Quick Reference)

| Entity | Can Read | Can Propose | Can Validate | Can Block | Can Write Canon | Can Retcon |
|--------|----------|-------------|--------------|-----------|-----------------|------------|
| Constitution | - | - | All | All | No (principles, not narrative) | No |
| GenrePack | All T3-T7 | - | NarrativeDelta | CanonCommit | No | No |
| Canon HEAD | - | - | - | - | Is Truth | Via R3 Retcon |
| ChapterContract | Canon, Context | - | Draft | Stage completion | No | No |
| Context Compiler | T0-T5 sources | Context | - | Missing mandatory | No | No |
| Writer (AI) | Context | Draft, NarrativeDelta | - | - | No | No |
| Quality Judge | Draft | QualityReport | - | Via Q0-Q3 hard gates | No | No |
| Repair Worker | Draft, QualityReport | RepairPlan | - | - | No | No |
| Reference Material | - | Evidence | - | - | No | No |
| Market Signal | - | Trend data | - | - | No | No |
| CanonCommit Service | All | - | Full pre-commit | - | YES (only path) | No |
| Human Authority | All | Override | Override | Override | Via approval | YES (R3) |

**Critical Invariant** (INV-004): Canon writes ONLY through CanonCommit boundary.

---

## 13. Version Baseline

**As of 2026-09-19 convergence**:

| Document | Version | Status |
|----------|---------|--------|
| PROJECT_CONSTITUTION | 1.0.0 | NORMATIVE_CANDIDATE (T0) |
| All gptdoc specs | 1.0.0 | NORMATIVE_CANDIDATE (T1) |
| Genesis/Genre/Domain specs (subset) | 0.1 | NORMATIVE_CANDIDATE (acknowledged draft) |
| ccdoc | "v1.0" claimed | DESIGN_CANDIDATE (T6) |
| Architecture audits | - | REVIEW (T7 with weight) |

**Post-Convergence**: All NORMATIVE_CANDIDATE specs promoted to NORMATIVE status after:
1. Terminology conflicts resolved (Task #3)
2. Architecture conflicts resolved (Task #8)
3. Schema defects addressed or deferred with mitigation (AR-04, AR-05, AR-06)
4. Readiness Report approves (Task #15)

---

## 14. Change Control

### 14.1 Constitution Changes (T0)
- **PATCH**: Wording clarification, link fixes, non-semantic
- **MINOR**: New principle that doesn't conflict with existing
- **MAJOR**: Authority change, invariant change, prohibition change
- **Process**: MAJOR requires ADR + governance approval
- **Prohibition**: AI cannot autonomously modify (CONSTITUTION Section 15.3)

### 14.2 Normative Spec Changes (T1)
- **PATCH**: Example updates, clarifications, typo fixes
- **MINOR**: New optional capabilities, backward-compatible additions
- **MAJOR**: Breaking changes to contracts, schemas, authority boundaries
- **Process**: MAJOR requires ADR
- **Tracking**: Update `Supersedes:` field, maintain ADR index

### 14.3 Genre/Policy Changes (T2)
- **GenrePack version**: Semantic versioning
- **World Rule changes**: Require human authority (per canon-commit-policy.yaml)
- **Prohibition**: Market trends cannot silently modify Genre Constitution (P-009)

### 14.4 Canon Changes (T3)
- **CanonCommit**: Append-only event log
- **Retcon**: R1 (soft), R2 (medium), R3 (hard) with explicit authority and invalidation cascade
- **Prohibition**: Silent retcon forbidden (PROHIBIT-010)

---

## 15. Convergence Status

**Completed**:
- ✅ Source Authority Inventory (Task #1)
- ✅ V1 Forensic Reuse Analysis (Task #4)
- ✅ V1 Regression Asset Register (Task #5)
- ✅ ccdoc Adoption Matrix (Task #6)
- ✅ gptdoc Conformance Analysis (Task #7)
- ✅ **This Normative Index** (Task #2)

**Remaining for Full Convergence**:
- Task #3: Terminology Baseline (unify conflicting terms)
- Task #8: Architecture Conflicts (requires Tasks #2, #3)
- Task #9: Authority Matrix (detailed)
- Task #10: Data Ownership Matrix
- Task #11: Artifact Lifecycle Register
- Task #12: Boundary Separations Verification
- Task #13: Architecture Risk Register
- Task #14: Required ADR Register
- Task #15: Architecture Readiness Report (final gate)

---

## 16. Usage Guidelines

### 16.1 For AI Agents

When implementing V2:
1. **Read PROJECT_CONSTITUTION first** (T0)
2. **Check this Normative Index** to understand authority hierarchy
3. **Resolve conflicts by tier**: Lower tier cannot override higher tier
4. **Validate against invariants**: INV-001 through INV-015
5. **Check prohibitions**: PROHIBIT-001 through PROHIBIT-014
6. **Follow dependency order**: Genre → Domain → Canon → Planning → Context → Workflow
7. **Respect authority boundaries**: Draft ≠ Canon, Judge ≠ Truth, Reference ≠ Canon

### 16.2 For Conflict Resolution

When documents conflict:
1. Identify tier of each document (T0-T7)
2. Higher tier wins by default
3. Same-tier conflicts → log in ARCHITECTURE_CONFLICT_REGISTER (Task #8)
4. Cannot proceed until same-tier conflicts resolved via ADR

### 16.3 For Verification

Architecture fitness tests should verify:
- No code bypasses CanonCommit boundary (INV-004)
- Writer doesn't import Canon write API (Architecture Fitness)
- GenrePack can block commits (T2 authority)
- Draft never auto-becomes Canon (P-003, PROHIBIT-003)
- AI Judge doesn't have Commit Authority (PROHIBIT-009)

---

**Document Status**: NORMATIVE  
**Next Update**: After Task #8 (Architecture Conflicts) resolves any same-tier conflicts  
**Maintenance**: Update when new specs added, supersession occurs, or major version changes

---

**END OF NORMATIVE INDEX**
