# ANovel V2 Convergence Correction Report

**Document ID**: CONV-CORRECTION-0001  
**Version**: 1.0  
**Status**: IN PROGRESS  
**Date**: 2026-09-19  
**Purpose**: Correct control-plane issues in convergence deliverables before architecture baseline freeze

---

## Executive Summary

**Current Status**: CONVERGENCE_WITH_REMEDIATION  

**Gates**:
- ✅ **P0_ENTRY_GATE**: READY (0 blockers)
- ❌ **ARCHITECTURE_BASELINE_FREEZE_GATE**: PENDING (6 corrections required)

**Business Coding**: BLOCKED until baseline freeze  
**Narrative Kernel (P1)**: BLOCKED until M0 closed

---

## Issues Identified

### 1. ❌ CRITICAL: Phase/Task Semantic Remapping

**Problem**: Convergence documents redefined Phase semantics, conflicting with frozen IMPLEMENTATION_PLAN.md

**Evidence**:

| Source | Phase Definition | Correct (IMPLEMENTATION_PLAN) |
|--------|------------------|-------------------------------|
| ARCHITECTURE_READINESS_REPORT.md | P1 = Genre Foundation | P1 = Narrative Kernel |
| ARCHITECTURE_READINESS_REPORT.md | P2 = Domain Types | P2 = Canon Kernel |
| ARCHITECTURE_READINESS_REPORT.md | P3 = Canon Transaction | P3 = Genre Kernel |
| ARCHITECTURE_READINESS_REPORT.md | P4 = Planning | P4 = Planning & Contracts |
| ARCHITECTURE_READINESS_REPORT.md | P5 = Context | P5 = Context & Model Gateway |

**Correct Phase Map** (from IMPLEMENTATION_PLAN.md Section 6):
```
P0 — Repository & Governance
P1 — Narrative Kernel
P2 — Canon Kernel
P3 — Genre Kernel
P4 — Planning & Contracts
P5 — Context & Model Gateway
P6 — Single-Chapter Production
P7 — Quality & Repair
P8 — Dual-Genre 10-Chapter Certification
P9 — 30-Chapter Certification
P10 — Genesis & Reference Intelligence
P11 — Human Calibration & Learning
P12 — 100-Chapter Reliability
P13 — Reader / Market Feedback
P14 — 300+ Chapter / Million-word Evolution
```

**Impact**: AI agents receiving Task V2-008 will not know if it means:
- NarrativeDelta (correct, from backlog)
- Genre Foundation (incorrect, from readiness report)

**Remediation**: Update all convergence documents to reference frozen Phase definitions only.

---

### 2. ❌ CRITICAL: Task ID Registry Conflict

**Problem**: Convergence documents remapped Task IDs to different phases

**Evidence** (from implementation-backlog.yaml):

| Task ID | Correct Assignment | Incorrect (Readiness Report) |
|---------|-------------------|------------------------------|
| V2-005 | Character / Relationship (P1 Narrative) | Domain Types |
| V2-006 | Knowledge / Goal (P1 Narrative) | Domain Types |
| V2-007 | Event / Timeline / Promise (P1 Narrative) | Genre Foundation |
| V2-008 | NarrativeDelta (P1 Narrative) | Genre Foundation |
| V2-009 | Canon Event Log (P2 Canon) | Canon Transaction |
| V2-010 | CanonCommitService (P2 Canon) | Canon Transaction |
| V2-013 | GenreProfile and GenrePack loader (P3 Genre) | Context (incorrectly) |
| V2-018 | Context Compiler (P5 Context) | Not clearly mapped |
| V2-019 | Model Gateway (P5 Context) | Not clearly mapped |
| V2-020 | Single Chapter Workflow (P6 Production) | Not clearly mapped |

**Correct Task→Phase Mapping**:
```
V2-001 to V2-004: P0 Repository & Governance
V2-005 to V2-008: P1 Narrative Kernel
V2-009 to V2-012: P2 Canon Kernel
V2-013 to V2-016: P3 Genre Kernel
V2-017: P4 Contract Compiler
V2-018: P5 Context Compiler
V2-019: P5 Model Gateway
V2-020: P6 Single Chapter Workflow
V2-021 to V2-026: P7 Quality & Repair
V2-027 to V2-030: P8 Dual-Genre Certification
...
```

**Remediation**: Establish implementation-backlog.yaml as SSOT. Convergence documents may only reference, not redefine.

---

### 3. ❌ HIGH: ADR→Task Mapping Drift

**Problem**: ADR ownership mapped to incorrect Task IDs

**Evidence**:

| ADR | Current Owner | Correct Owner | Rationale |
|-----|---------------|---------------|-----------|
| ADR-0025 Context Overflow | V2-013 (GenrePack) | V2-018 (Context Compiler) | Context budget is P5, not P3 |
| ADR-0024 Extension Namespace | V2-008 (NarrativeDelta) | V2-013~016 (Genre) + V2-009~012 (Canon) | Extension namespace spans Genre+Canon |
| ADR-0007 Provider Gateway | V2-027 (Workflow) | V2-019 (Model Gateway) | Model Gateway is P5, not P8 |
| ADR-0010 Durable Workflow | V2-017 (Contract) | V2-020/027/028 (Workflow) | Workflow is P6/P8, not P4 |
| ADR-0022 Promise Temporal | V2-006 (Knowledge) | V2-007 (Event/Promise) + V2-017 (Contract) | Promise is V2-007, consumed by V2-017 |
| ADR-0023 Event Type/Occurrence | V2-006 (Knowledge) | V2-007 (Event/Timeline) | Event is V2-007, not V2-006 |

**Remediation**: Create automated ADR→Task cross-reference validator; correct all mappings.

---

### 4. ❌ HIGH: P0 Scope Creep

**Problem**: Business logic recommended for P0 implementation

**Evidence**:

1. **Genesis Bootstrap in V2-001**:
   - ARCHITECTURE_READINESS_REPORT.md recommends: "Create TEST_GENESIS_STUB mode in V2-001"
   - **Violation**: V2-001 should be pure repository bootstrap, no narrative semantics
   - **Correct**: Minimal Canon Bootstrap should be in V2-009/010 (P2 Canon Kernel)

2. **Provider UNKNOWN in V2-002**:
   - Report recommends: "Add UNKNOWN to workflow-policy.yaml in V2-002"
   - **Violation**: V2-002 is normative docs import, no workflow semantics
   - **Correct**: Provider UNKNOWN should be in V2-019 (Model Gateway) + V2-027 (Workflow Retry)

**P0 Correct Scope**:
```
V2-001: Repository skeleton (pyproject.toml, CI, tests/, migrations/)
V2-002: Normative docs import (docs/, NORMATIVE_INDEX.md)
V2-003: Architecture fitness harness (import rules, boundary checks)
V2-004: Security baseline (secret scan, dependency scan)
```

**Remediation**: Remove all narrative/workflow business logic from P0 recommendations.

---

### 5. ❌ MEDIUM: Readiness Verdict Logic Error

**Problem**: Report claims "READY (with conditions)" but Master Prompt requires binary READY/NOT_READY per gate

**Evidence**:
- ARCHITECTURE_READINESS_REPORT.md Section 1: "READY (with conditions)"
- Master Prompt Section 25: "最终只能输出：READY 或 NOT_READY"
- Report itself shows: 15/17 criteria PASS, 2 PARTIAL

**Logic Error**: "READY with conditions" is NOT_READY for that gate

**Correct Verdict Model**:
```yaml
P0_ENTRY_GATE:
  verdict: READY
  blockers: 0
  can_start: [V2-001, V2-002, V2-003, V2-004]
  cannot_start: [V2-005+]

ARCHITECTURE_BASELINE_FREEZE_GATE:
  verdict: PENDING
  blockers: 6
  blocking_issues:
    - Phase/Task remapping correction
    - ADR ownership correction
    - P0 scope correction
    - Gate model clarification
    - Task registry SSOT enforcement
    - Readiness verdict correction
  can_freeze: false
```

**Remediation**: Split single verdict into two independent gates with binary READY/PENDING.

---

### 6. ❌ MEDIUM: Gate Model Ambiguity

**Problem**: "Phase Gate vs Task Dependency" marked PARTIAL but not clearly separated

**Missing Definitions**:

| Concept | Definition | Example |
|---------|-----------|---------|
| task_dependencies | Task A requires Task B output | V2-010 depends on V2-009 (Canon Event Log) |
| phase_entry_gate | Conditions to start Phase N | P1 entry requires: P0-GATE passed, M0 closed |
| milestone_close_gate | Evidence to declare Milestone complete | M0 close requires: CI green, lockfile committed, no secrets, normative index valid, architecture fitness enforced |
| certification_gate | Evidence for advancement | M3 certification: dual genre 30ch, 0 contamination, all Q0-Q3 pass |

**Current Confusion**: Implementation Plan has both but doesn't explicitly separate them

**Remediation**: Add explicit Gate Model section to corrected documentation.

---

## Remediation Plan

### Phase 1: Control Plane Fixes (Immediate)

**Task**: Fix 6 convergence documents

1. **ARCHITECTURE_READINESS_REPORT.md**
   - Split verdict into P0_ENTRY_GATE (READY) and BASELINE_FREEZE_GATE (PENDING)
   - Correct all Phase references (P1=Narrative, P2=Canon, P3=Genre)
   - Correct all Task references (V2-005~008=Narrative, not Genre)
   - Remove Genesis/Provider from P0 recommendations
   - Move to V2-009/010 and V2-019/027 respectively

2. **REQUIRED_ADR_REGISTER.md**
   - Correct ADR-0025 owner: V2-013 → V2-018
   - Correct ADR-0024 owner: V2-008 → V2-013~016 + V2-009~012
   - Correct ADR-0007 owner: V2-027 → V2-019
   - Correct ADR-0010 owner: V2-017 → V2-020/027/028
   - Correct ADR-0022 owner: V2-006 → V2-007 + V2-017
   - Correct ADR-0023 owner: V2-006 → V2-007

3. **NORMATIVE_INDEX.md**
   - Update Section 3.3 "Implementation Phases" to match frozen Phase Map
   - Correct Phase→Spec mapping

4. **ARCHITECTURE_CONFLICT_REGISTER.md**
   - Update ADR owner references
   - Correct Phase blocking references

5. **ARTIFACT_LIFECYCLE_REGISTER.md**
   - Update Phase gate references

6. **Create New**: **PHASE_TASK_REGISTRY.md**
   - Formalize Phase Map (P0-P14)
   - Formalize Task Map (V2-001 to V2-060)
   - Formalize Gate Model (task deps, phase entry, milestone close, certification)
   - Establish implementation-backlog.yaml as SSOT

### Phase 2: Validation (Next)

**Task**: Create automated validators

1. **Task-ADR Cross-Reference Validator**
   - Verify all ADR owners exist in backlog
   - Verify ADR owner Phase matches ADR blocking Phase
   - Generate warnings for drift

2. **Phase-Task Consistency Validator**
   - Verify all Phase references match PHASE_TASK_REGISTRY.md
   - Verify all Task references match implementation-backlog.yaml
   - Block commits with invalid references

3. **Gate Model Validator**
   - Verify Phase entry gates reference correct evidence
   - Verify Milestone close gates have test backing
   - Verify no circular dependencies

### Phase 3: Baseline Freeze (After Correction)

Once 6 documents corrected and validators green:

```yaml
ARCHITECTURE_BASELINE_FREEZE_GATE:
  verdict: READY
  blockers: 0
  frozen_artifacts:
    - NORMATIVE_INDEX.md
    - TERMINOLOGY_BASELINE.md
    - AUTHORITY_MATRIX.md
    - PHASE_TASK_REGISTRY.md
    - implementation-backlog.yaml
    - All 15 gptdoc specifications
    - All policy YAML files
```

Then proceed to create:
```
PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md
```

---

## Success Criteria

**Correction Complete When**:

1. ✅ All 6 convergence documents corrected
2. ✅ Phase references match frozen Phase Map
3. ✅ Task references match implementation-backlog.yaml
4. ✅ ADR owners corrected and validated
5. ✅ P0 scope pure (no Genesis/Workflow logic)
6. ✅ Readiness verdict split into two gates
7. ✅ Gate model explicitly defined
8. ✅ 3 validators created and green
9. ✅ PHASE_TASK_REGISTRY.md created
10. ✅ User approves baseline freeze

**Then**:
```
PRE-ARCHITECTURE CONVERGENCE: CLOSED
ARCHITECTURE_BASELINE: FROZEN
P0 EXECUTION: APPROVED
```

---

## Timeline

**Estimated Effort**: 2-3 hours (systematic corrections, not new analysis)

**Deliverables**:
- 6 corrected convergence documents
- 1 new registry document (PHASE_TASK_REGISTRY.md)
- 3 validation scripts
- Updated ARCHITECTURE_READINESS_REPORT.md with split verdict

---

## Current Status

- [x] Issues identified and documented
- [ ] Corrections in progress
- [ ] Validators created
- [ ] User approval
- [ ] Baseline frozen

---

**Next Action**: Begin systematic correction of 6 documents, starting with ARCHITECTURE_READINESS_REPORT.md

---

END OF CORRECTION REPORT
