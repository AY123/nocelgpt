# ANovel V2 Source Authority Inventory

**Document ID**: CONV-0001  
**Version**: 0.1 (DRAFT - IN PROGRESS)  
**Status**: BUILDING  
**Created**: 2026-09-19  
**Purpose**: Catalog all architecture materials and establish authority relationships for ANovel V2 pre-architecture convergence

---

## 1. Inventory Scope

This inventory covers all materials in `/Users/angyang/Documents/AI/ANovelOS/` including:

- **ainovel/** - V1 legacy system (code, tests, production evidence)
- **ccdoc/** - Strategic refactor design candidate (25 files, 22,403 lines)
- **gptdoc/** - Primary normative candidate specifications (15 packages, 136 files)
- **architecture-review-2026-09-18/** - gptdoc architecture audit
- **ccdoc-review-2026-09-19/** - ccdoc architecture audit  
- **project-analysis-2026-09-18/** - V1 forensic analysis
- **planning-integration-2026-09-18/** - Planning integration materials
- **ANovel_V2_PreArchitecture_Pack_2026/** - Pre-architecture knowledge pack (10 DOCX)

---

## 2. Authority Classification Schema

Materials are classified as:

- **NORMATIVE** - Approved baseline, binding authority
- **NORMATIVE_CANDIDATE** - Proposed for normative status, pending convergence
- **ADR_CANDIDATE** - Design decisions requiring formal ADR
- **RESEARCH** - Evidence, market data, competitive analysis
- **EVIDENCE** - Runtime evidence, test results, production data
- **REVIEW** - Audit reports, analysis, findings
- **LEGACY** - V1 code/docs, migration source only
- **HISTORICAL** - Archived, reference only
- **REJECTED** - Explicitly superseded or rejected

---

## 3. Material Catalog

### 3.1 gptdoc/ - Primary Normative Candidate

**Classification**: NORMATIVE_CANDIDATE  
**Authority Level**: T1 (pending final convergence)  
**Status**: Comprehensive specification suite, subject to conflict resolution

| Package | Document | Status | Notes |
|---------|----------|--------|-------|
| ANovel_V2_Project_Constitution_v1.0 | PROJECT_CONSTITUTION.md | NORMATIVE_CANDIDATE (T0) | Declares itself BASELINE/NORMATIVE; establishes Truth Hierarchy T0-T7 |
| ANovel_V2_V1_Forensic_Lessons_v1.0 | V1_FORENSIC_LESSONS.md | RESEARCH/EVIDENCE | V1 failure analysis, migration decisions |
| ANovel_V2_Implementation_Plan_v1.0 | IMPLEMENTATION_PLAN.md | NORMATIVE_CANDIDATE | Execution baseline, P0-P14 phases |
| ANovel_V2_Reference_Architecture_Study_v1.0 | REFERENCE_ARCHITECTURE_STUDY.md | RESEARCH | External design lessons |
| ANovel_V2_WebNovel_Market_Genre_Research_2026_v1.0 | WEBNOVEL_MARKET_GENRE_RESEARCH.md | RESEARCH | Market evidence (T5) |
| ANovel_V2_Genre_Intelligence_Spec_v1.0 | GENRE_INTELLIGENCE_SPEC.md | NORMATIVE_CANDIDATE (T2) | Genre domain spec |
| ANovel_V2_Narrative_Domain_Spec_v1.0 | NARRATIVE_DOMAIN_SPEC.md | NORMATIVE_CANDIDATE (T2) | Core narrative types |
| ANovel_V2_Canonical_State_Spec_v1.0 | CANONICAL_STATE_SPEC.md | NORMATIVE_CANDIDATE (T3) | Canon boundary spec |
| ANovel_V2_Multi_Source_Genesis_Spec_v1.0 | MULTI_SOURCE_GENESIS_SPEC.md | NORMATIVE_CANDIDATE | Genesis spec (deferred P10) |
| ANovel_V2_Planning_Contract_Spec_v1.0 | PLANNING_CONTRACT_SPEC.md | NORMATIVE_CANDIDATE (T4) | Planning domain |
| ANovel_V2_Context_Intelligence_Spec_v1.0 | CONTEXT_INTELLIGENCE_SPEC.md | NORMATIVE_CANDIDATE | Context compilation |
| ANovel_V2_Production_Workflow_Spec_v1.0 | PRODUCTION_WORKFLOW_SPEC.md | NORMATIVE_CANDIDATE | Workflow orchestration |
| ANovel_V2_Quality_Evaluation_Repair_Spec_v1.0 | QUALITY_EVALUATION_REPAIR_SPEC.md | NORMATIVE_CANDIDATE | Quality/Repair domain |
| ANovel_V2_Corpus_Evaluation_Learning_Spec_v1.0 | CORPUS_EVALUATION_LEARNING_SPEC.md | NORMATIVE_CANDIDATE | Learning (deferred) |
| ANovel_V2_Platform_Observability_Security_Spec_v1.0 | PLATFORM_OBSERVABILITY_SECURITY_SPEC.md | NORMATIVE_CANDIDATE | Platform/Security |
| architecture-review-2026-09-18 | ARCHITECTURE_AUDIT_REPORT.md | REVIEW | Independent audit of gptdoc |

**Audit Status**: architecture-review-2026-09-18/ARCHITECTURE_AUDIT_REPORT.md found:
- **Verdict**: "Conditional P0 entry - NOT fully implementation-ready"
- 12/12 contract probes exposed gaps or type errors
- Schema meta-validation passed, but domain semantics validation incomplete
- **Key Findings**: Same-name enum conflicts, operation algebra incomplete, Genesis bootstrap dependency unclear

**Supersedes Relationships**: None explicitly declared (first normative attempt for V2)

---

### 3.2 ccdoc/ - Strategic Refactor Design Candidate

**Classification**: DESIGN_CANDIDATE  
**Authority Level**: Reference only, individual concepts subject to ADOPT/ADAPT/DEFER/REJECT  
**Status**: Strategic refactor proposal for V1, conflicts with greenfield approach

| Document | Lines | Classification | Notes |
|----------|-------|----------------|-------|
| README.md | 541 | CANDIDATE_INDEX | Claims "v1.0", "前期准备阶段完成" |
| 00_PROJECT_REFACTOR_ASSESSMENT.md | 315 | RESEARCH/CANDIDATE | V1 refactor ROI analysis |
| 01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md | 919 | DESIGN_CANDIDATE | Genre-First architecture |
| 02_STRATEGIC_REFACTOR_ROADMAP.md | 804 | CANDIDATE_PLAN | 3-month refactor roadmap |
| 03_KEEP_REFACTOR_DELETE_CHECKLIST.md | 533 | MIGRATION_CANDIDATE | 40%-30%-30% strategy |
| 04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md | 759 | DESIGN_CANDIDATE | Urban/Fantasy templates |
| 05_V1_LESSONS_LEARNED.md | 517 | RESEARCH | V1 lessons (overlaps with gptdoc) |
| 11_FINAL_EXECUTABLE_GUIDE.md | ? | CANDIDATE | Claims "FINAL" status |
| 12_ARCHITECTURE_DECISION_RECORD_*.md | 3 parts | ADR_CANDIDATE | ADR format but not formal |
| 13-21 (Data/Stack/Arch/LLM/QA/DB/API/Ops/Test) | ~10K lines | DESIGN_CANDIDATE | Detailed design proposals |

**Audit Status**: ccdoc-review-2026-09-19/CCDOC_ARCHITECTURE_AUDIT_REPORT.md found:
- **Verdict**: "Design candidate library, not unified implementation baseline"
- 24 findings: 8 blocking, 15 high-priority, 1 general
- **Strategic Conflict**: Proposes V1 strategic refactor vs. user's greenfield directive
- **Known Issues**: Genre keywords as hard facts, Canon commit boundary not enforced in API layer, Draft/Accepted/Published state mixing, Workflow retry lacks idempotency/unknown semantics

**Relationship to gptdoc**: Predates gptdoc; many concepts absorbed and refined in gptdoc

---

### 3.3 ainovel/ - V1 Legacy System

**Classification**: LEGACY/EVIDENCE  
**Authority Level**: None (code), T5 (evidence), Regression source  
**Status**: Frozen baseline, selective migration only

**Key V1 Documents**:
- `ROADMAP.md` - V1 phase history, as-built evidence
- `CLAUDE.md` - V1 architecture admission of genre failures
- `AI-Novel-Standard/` - Schema/ADR attempts
- `AI-Novel-Runtime/` - 59K lines Python runtime
- `tests/` - 43K lines tests (2122 passed / 15 failed in offline run)
- `novel-dushi/` - Failed urban production (60 errors)
- `novel-lingse/` - Successful fantasy production (0 errors)

**Forensic Evidence** (from project-analysis):
- **F01 P0**: Git-tracked docs contain API keys (security incident)
- **F02 P0**: Mint lacks atomic commit (partial commit possible)
- **F03 P1**: BLOCKED doesn't actually block progression
- **F04 P1**: Resume cursor inconsistent with completion stats
- Real provider validation exists but no CI pipeline
- State as Projection concept valid but not full Event Sourcing

**Migration Verdict** (from gptdoc/V1_FORENSIC_LESSONS.md):
- KEEP: Vision, Canon concept, State as Projection, Real-provider validation, Provenance
- EXTRACT_CONCEPT: Mint/unique write boundary, Golden Set structure
- REWRITE: Genre Contract, Chapter Contract, Workflow, Serialization
- ARCHIVE: ReaderSim (rebuild later), Most reviewer/report modules
- PROHIBITED: V1 code wholesale copy to V2

---

### 3.4 Architecture Reviews

#### architecture-review-2026-09-18/ (gptdoc audit)

**Classification**: REVIEW/NORMATIVE-INPUT  
**Date**: 2026-09-18 ~ 2026-09-19  
**Auditor**: Independent technical audit  
**Scope**: All 15 gptdoc packages (136 files, 121 manifest-verified)

**Key Findings**:
- Overall direction: PASS
- P0 readiness: CONDITIONAL (not fully implementation-ready)
- 12 contract probes exposed schema/domain semantic gaps
- Recommendations feed into P0 tasks V2-001 through V2-004

**Authority**: T1 input for conflict resolution

#### ccdoc-review-2026-09-19/ (ccdoc audit)

**Classification**: REVIEW  
**Date**: 2026-09-19  
**Auditor**: Independent technical audit  
**Scope**: All 25 ccdoc files (22,403 lines)

**Key Findings**:
- 24 findings across Genre/Core/Delivery/Product
- Strategic misalignment: refactor vs. greenfield
- Useful concepts but not unified baseline

**Authority**: Guidance for ADOPT/ADAPT/DEFER/REJECT matrix

---

### 3.5 ANovel_V2_PreArchitecture_Pack_2026/

**Classification**: RESEARCH/INFORMATIVE (DOCX export format)  
**Authority Level**: T5 (External format, not machine-readable SSOT)  
**Status**: Knowledge pack, not normative source

Contains 10 DOCX files (D00-D09):
- D00: Master Index
- D01: Product Charter
- D02: V1 Lessons & Migration
- D03: Market Research
- D04: Reference Architecture
- D05: Genre Intelligence (v0.1)
- D06: Genesis/Corpus (v0.1)
- D07: Narrative Domain/Canon (v0.1)
- D08: Workflow/Quality/Repair (v0.1)
- D09: Engineering Roadmap

**Note**: Per PROJECT_CONSTITUTION.md Section 16.1, "DOCX/PDF are export artifacts, not authoritative sources." Normative content should be in gptdoc/ Markdown.

---

### 3.6 project-analysis-2026-09-18/

**Classification**: EVIDENCE/REVIEW  
**Contains**:
- PROJECT_DEEP_ANALYSIS.md - V1 forensic analysis
- reproduction-results.json - Verified failure reproduction
- pytest-results.log - Test execution evidence
- Various validation logs

**Authority**: T5 (Evidence) for V1 failures and regression requirements

---

### 3.7 planning-integration-2026-09-18/

**Classification**: PLANNING_CANDIDATE  
**Status**: Directory exists but contents not yet examined  
**Authority**: TBD pending content review

---

## 4. Authority Hierarchy Mapping

Based on PROJECT_CONSTITUTION.md Truth Hierarchy:

```
T0 Project Constitution
   ↓ gptdoc/ANovel_V2_Project_Constitution_v1.0/PROJECT_CONSTITUTION.md
   
T1 Approved ADR / Normative Architecture Specification
   ↓ gptdoc/* specs (CANDIDATES pending conflict resolution)
   ↓ architecture-review findings (INPUT to convergence)
   
T2 Genre Constitution / Domain Policy
   ↓ gptdoc/Genre_Intelligence_Spec
   ↓ gptdoc/Narrative_Domain_Spec
   
T3 Canonical Narrative State
   ↓ gptdoc/Canonical_State_Spec
   
T4 Approved Plan / Contract
   ↓ gptdoc/Planning_Contract_Spec
   
T5 External Evidence
   ↓ gptdoc/Market_Research
   ↓ gptdoc/Reference_Architecture_Study
   ↓ project-analysis evidence
   ↓ V1 runtime evidence
   
T6 Generated Artifact / Draft / Candidate
   ↓ ccdoc/* (design candidates)
   ↓ PreArchitecture_Pack DOCX (exports)
   
T7 AI Analysis / Judge / Recommendation
   ↓ Review reports (recommendations)
```

---

## 5. Supersedes Relationships

**EXPLICIT SUPERSEDES**: None declared

**IMPLICIT CONFLICTS** (require resolution):
1. **Strategic Direction**: ccdoc proposes V1 refactor; gptdoc + user directive = greenfield
2. **Genre Authority**: ccdoc keywords vs. gptdoc GenrePack domain
3. **Canon Boundary**: ccdoc API design vs. gptdoc transaction model
4. **Workflow Semantics**: ccdoc retry vs. gptdoc idempotency/unknown

**CONVERGENCE REQUIRED**: Task #8 (Architecture Conflict Register)

---

## 6. Version and Status Summary

| Material | Version | Status Claimed | Actual Status |
|----------|---------|----------------|---------------|
| PROJECT_CONSTITUTION.md | 1.0.0 | BASELINE/NORMATIVE | NORMATIVE_CANDIDATE (T0) |
| gptdoc specs (most) | 1.0.0 | Various | NORMATIVE_CANDIDATE pending convergence |
| gptdoc genesis/genre/domain v0.1 | 0.1 | Draft | NORMATIVE_CANDIDATE |
| ccdoc | v1.0 | "前期准备阶段完成" | DESIGN_CANDIDATE only |
| architecture-review | - | Independent audit | REVIEW/NORMATIVE-INPUT |
| ccdoc-review | - | Independent audit | REVIEW |
| project-analysis | - | Evidence | EVIDENCE |
| ainovel V1 | - | Production system | LEGACY/EVIDENCE |

**WARNING**: Version numbers and "FINAL" labels in filenames do NOT establish authority. Authority must be determined through explicit Supersedes chains and convergence process.

---

## 7. Next Steps

This inventory feeds into:

1. **Task #2** - Establish Truth Hierarchy and Normative Index
2. **Task #3** - Unify Core Terminology Baseline
3. **Task #8** - Identify Architecture Conflicts
4. **Task #6** - Analyze ccdoc Adoption Matrix
5. **Task #7** - Validate gptdoc Conformance and Defects
6. **Task #4** - Perform V1 Forensic Reuse Analysis

**Status**: DRAFT - Requires deep reading of all materials to complete classification and conflict identification.

---

## 8. Open Questions

1. What materials exist in planning-integration-2026-09-18/?
2. Are there additional V1 ADRs or architecture decisions beyond what's in ainovel/AI-Novel-Standard/adr/?
3. What is the relationship between PreArchitecture_Pack DOCX and gptdoc Markdown?
4. Has user explicitly frozen/approved any specific document as T0?
5. What is the authority relationship between architecture-review REMEDIATION_REGISTER and gptdoc Implementation Plan tasks?

---

**Document Status**: DRAFT IN PROGRESS  
**Completion**: ~40% (catalog structure established, needs deep material analysis)  
**Next Action**: Continue with parallel material analysis using Agent tool
