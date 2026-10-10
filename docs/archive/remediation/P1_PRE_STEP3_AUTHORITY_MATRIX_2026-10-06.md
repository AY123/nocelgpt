# P1-PRE-STEP3-HOUSEKEEPING-001: Documentation Authority Matrix
**Document ID**: P1-PRE-STEP3-AUTHORITY-MATRIX  
**Date**: 2026-10-06  
**Baseline**: work/h2-convergence-closure @ be6e475b

---

## 1. Authority Classification Taxonomy

Documents are classified as:

- **NORMATIVE_ACTIVE**: Current binding specifications and contracts
- **OPERATIONAL_ACTIVE**: Current execution procedures and protocols
- **STATUS_ACTIVE**: Current project status and progress tracking
- **EVIDENCE_IMMUTABLE**: Historical evidence, must not be modified
- **HISTORICAL**: Superseded or completed work documentation
- **SUPERSEDED**: Replaced by newer versions
- **ARCHIVE_CANDIDATE**: Historical but may be moved to archive/
- **DUPLICATE**: Multiple copies of same content
- **AMBIGUOUS**: Authority status unclear, needs classification

---

## 2. Root Level Documents

| File | Classification | Authority | Notes |
|------|----------------|-----------|-------|
| README.md | NORMATIVE_ACTIVE | PRIMARY_ENTRYPOINT | ⚠️ Stale status (mentions V2-003, not V2-005) |
| AGENTS.md | OPERATIONAL_ACTIVE | AI_EXECUTION_ENTRY | Current and accurate |
| AT08_LEGITIMATE_CONTROL.md | EVIDENCE_IMMUTABLE | TEST_EVIDENCE | Should move to docs/ |
| V2-005_INDEPENDENT_REVIEW_58d77d2.md | DUPLICATE | HISTORICAL | Duplicate of docs/ version |
| V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md | DUPLICATE | HISTORICAL | Malformed filename |
| V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md | HISTORICAL | EVIDENCE | Contains old repo URLs (correct for historical context) |
| V2-005_REMEDIATION_PACKAGE_e300429.tar.gz | ARCHIVE_CANDIDATE | HISTORICAL | Compressed archive |
| V2-005_H1_REMEDIATION_PACKAGE.tar.gz | ARCHIVE_CANDIDATE | HISTORICAL | Compressed archive |
| 审核报告.txt | HISTORICAL | EVIDENCE | Chinese audit report |
| V2-003任务prompt.txt | HISTORICAL | EVIDENCE | V2-003 task prompt |

---

## 3. plan/ Directory Authority

### 3.1 Top-Level Planning Documents
| File | Classification | Authority | Current? |
|------|----------------|-----------|----------|
| plan/README.md | NORMATIVE_ACTIVE | PLANNING_INDEX | ✅ |
| plan/AI_EXECUTION_PROTOCOL.md | NORMATIVE_ACTIVE | AI_GOVERNANCE | ✅ |
| plan/PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md | NORMATIVE_ACTIVE | P0_SPEC | ✅ |
| plan/00_GOVERNANCE_AND_SOURCE_AUTHORITY.md | NORMATIVE_ACTIVE | GOVERNANCE | ✅ |
| plan/01_PRODUCT_SCOPE_AND_SUCCESS.md | NORMATIVE_ACTIVE | PRODUCT_SPEC | ✅ |
| plan/02_ARCHITECTURE_BASELINE.md | NORMATIVE_ACTIVE | ARCHITECTURE | ✅ |
| plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md | NORMATIVE_ACTIVE | DOMAIN_SPEC | ✅ |
| plan/04_GENRE_AND_STORY_FIXTURES.md | NORMATIVE_ACTIVE | GENRE_SPEC | ✅ |
| plan/05_PRODUCTION_CONTEXT_QUALITY_REPAIR.md | NORMATIVE_ACTIVE | QUALITY_SPEC | ✅ |
| plan/06_CERTIFICATION_AND_PRODUCT_EVALUATION.md | NORMATIVE_ACTIVE | CERT_SPEC | ✅ |
| plan/07_PLATFORM_SECURITY_AND_DELIVERY.md | NORMATIVE_ACTIVE | SECURITY_SPEC | ✅ |
| plan/08_ROADMAP_AND_GATES.md | NORMATIVE_ACTIVE | ROADMAP | ✅ |
| plan/09_TASK_EXECUTION_GUIDE.md | NORMATIVE_ACTIVE | EXECUTION_GUIDE | ✅ |
| plan/10_DECISIONS_AND_REMEDIATION.md | NORMATIVE_ACTIVE | DECISIONS | ✅ |

### 3.2 Machine-Readable Authority (plan/machine/)
| File | Classification | Authority | Purpose |
|------|----------------|-----------|---------|
| implementation-backlog.yaml | NORMATIVE_ACTIVE | TASK_REGISTRY | Task definitions and acceptance criteria |
| phase-gates.yaml | NORMATIVE_ACTIVE | PHASE_STATUS | Phase state and gates |
| test-catalog.yaml | NORMATIVE_ACTIVE | TEST_SPEC | Test requirements |
| ai-execution-policy.yaml | NORMATIVE_ACTIVE | AI_POLICY | AI execution constraints |
| ci-gates.yaml | NORMATIVE_ACTIVE | CI_SPEC | CI gate definitions |
| remediation-register.yaml | NORMATIVE_ACTIVE | REMEDIATION | Open remediation items |
| decision-register.yaml | NORMATIVE_ACTIVE | ADR_INDEX | Architecture decisions |
| source-register.yaml | NORMATIVE_ACTIVE | SOURCE_CATALOG | Source authority index |
| authority-policy.yaml | NORMATIVE_ACTIVE | AUTHORITY_RULES | Authority determination rules |
| governance-baseline.yaml | NORMATIVE_ACTIVE | GOVERNANCE | Governance policies |
| external-practice-register.yaml | NORMATIVE_ACTIVE | EXTERNAL_REFS | External practice references |
| foundational-reference-register.yaml | NORMATIVE_ACTIVE | FOUNDATION_REFS | Foundational references |
| milestones.yaml | NORMATIVE_ACTIVE | MILESTONES | Project milestones |
| review-triage-policy.yaml | NORMATIVE_ACTIVE | REVIEW_POLICY | Review triage rules |

**Status**: All machine files are CURRENT and AUTHORITATIVE

---

## 4. docs/ Directory Authority

### 4.1 V2-005 Contract and Implementation
| File | Classification | Authority | Version |
|------|----------------|-----------|---------|
| docs/V2-005_IMPLEMENTATION_CONTRACT.md | NORMATIVE_ACTIVE | BINDING_CONTRACT | v1.1.0 |
| docs/V2-005_IMPLEMENTATION_PLAN.md | OPERATIONAL_ACTIVE | IMPLEMENTATION | Current |
| docs/V2-005_IMPLEMENTATION_AUTHORIZATION_GATE.md | EVIDENCE_IMMUTABLE | AUTHORIZATION | Approval gate |

### 4.2 V2-005 Step Execution Reports (Untracked)
| File | Classification | Authority | Status |
|------|----------------|-----------|--------|
| docs/V2-005_STEP_1_REPORT.md | EVIDENCE_IMMUTABLE | STEP_1_EVIDENCE | ⚠️ Untracked |
| docs/V2-005_STEP_1_CI_FIX_REPORT.md | EVIDENCE_IMMUTABLE | STEP_1_CI_FIX | ⚠️ Untracked |
| docs/V2-005_STEP_2_REPORT.md | EVIDENCE_IMMUTABLE | STEP_2_EVIDENCE | ⚠️ Untracked |
| docs/V2-005_STEP_2_H1_FIX_REPORT.md | EVIDENCE_IMMUTABLE | STEP_2_HOTFIX | ⚠️ Untracked |
| docs/V2-005_POST_CI_EXECUTION_REPORT.md | EVIDENCE_IMMUTABLE | CI_EXECUTION | ⚠️ Untracked |
| docs/V2-005_AUTHORIZATION_EFFECTUATION_REPORT.md | EVIDENCE_IMMUTABLE | AUTHORIZATION | ⚠️ Untracked |
| docs/V2-005_AUTHORIZATION_FINAL_REPORT.md | EVIDENCE_IMMUTABLE | AUTHORIZATION | ⚠️ Untracked |

### 4.3 CI Investigation Reports (Untracked)
| File | Classification | Authority | Status |
|------|----------------|-----------|--------|
| docs/CI-LOCK-H1_FIX_REPORT.md | EVIDENCE_IMMUTABLE | CI_REMEDIATION | ⚠️ Untracked |
| docs/CI-POLICY-H1_DIAGNOSIS.md | EVIDENCE_IMMUTABLE | CI_DIAGNOSIS | ⚠️ Untracked |
| docs/CI-POLICY-H1_INVESTIGATION_COMPLETE.md | EVIDENCE_IMMUTABLE | CI_INVESTIGATION | ⚠️ Untracked |
| docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md | EVIDENCE_IMMUTABLE | CI_REMEDIATION | ⚠️ Untracked |

**Recommendation**: Add all untracked evidence files to repository after content review

### 4.4 V2-005 Review and Audit Documents
| File | Classification | Authority |
|------|----------------|-----------|
| docs/V2-005_INDEPENDENT_REVIEW_TRIAGE.md | EVIDENCE_IMMUTABLE | REVIEW |
| docs/V2-005_CONTRACT_REVISION_REPORT.md | EVIDENCE_IMMUTABLE | REVISION |
| docs/V2-005_CORRECTED_TRIAGE.md | EVIDENCE_IMMUTABLE | TRIAGE |
| docs/V2-005_CURRENT_STATE_AUDIT.md | EVIDENCE_IMMUTABLE | AUDIT |
| docs/V2-005_DECISION_GATES.md | EVIDENCE_IMMUTABLE | DECISIONS |
| docs/V2-005_TASK_REFINEMENT.md | EVIDENCE_IMMUTABLE | REFINEMENT |
| docs/V2-005_AUDIT_MATERIALS_CHECKLIST.md | EVIDENCE_IMMUTABLE | CHECKLIST |
| docs/V2-005_CLARIFICATION_CHECKLIST.md | EVIDENCE_IMMUTABLE | CLARIFICATION |
| docs/V2-005_BF-01_REMEDIATION_REPORT.md | EVIDENCE_IMMUTABLE | BUGFIX |
| docs/V2-005_FINAL_REMEDIATION_REPORT.md | EVIDENCE_IMMUTABLE | REMEDIATION |
| docs/V2-005_APPROVAL_GATE_FINAL_REPORT.md | EVIDENCE_IMMUTABLE | APPROVAL |
| docs/V2-005_REVISION_EVIDENCE.md | EVIDENCE_IMMUTABLE | REVISION |
| docs/V2-005_REFINEMENT_SUMMARY.md | EVIDENCE_IMMUTABLE | SUMMARY |
| docs/V2-005_POST_CI_RATIFICATION.md | EVIDENCE_IMMUTABLE | RATIFICATION |

### 4.5 Historical Task Reports
| File | Classification | Authority |
|------|----------------|-----------|
| docs/V2-002_IMPLEMENTATION_REPORT.md | EVIDENCE_IMMUTABLE | V2-002 |
| docs/V2-003_IMPLEMENTATION_REPORT.md | EVIDENCE_IMMUTABLE | V2-003 |
| docs/V2-003.2_IMPLEMENTATION_REPORT.md | EVIDENCE_IMMUTABLE | V2-003.2 |
| docs/V2-003.2-H1_HOTFIX_REPORT.md | EVIDENCE_IMMUTABLE | V2-003.2_HOTFIX |
| docs/V2-004_BASELINE_PREPARE.md | EVIDENCE_IMMUTABLE | V2-004 |
| docs/V2-004_CONTEXT_RECONCILIATION_STATUS.md | EVIDENCE_IMMUTABLE | V2-004 |
| docs/V2-004_READY_FOR_FINAL_STEPS.md | EVIDENCE_IMMUTABLE | V2-004 |
| docs/V2-004_FOURTH_FIX_PROGRESS.md | EVIDENCE_IMMUTABLE | V2-004 |

### 4.6 Governance and H-Series Reports
| File | Classification | Authority |
|------|----------------|-----------|
| docs/00_GOVERNANCE_AND_SOURCE_AUTHORITY.md | NORMATIVE_ACTIVE | GOVERNANCE |
| docs/H1_REMEDIATION_PROGRESS_HISTORICAL_HEADER.md | HISTORICAL | H1 |
| docs/H1_CHANGE_SUMMARY.md | HISTORICAL | H1 |
| docs/H3_FINAL_CONVERGENCE_EVIDENCE.md | EVIDENCE_IMMUTABLE | H3 |
| docs/H3.1_MICRO_FIX_EVIDENCE.md | EVIDENCE_IMMUTABLE | H3.1 |

---

## 5. plan/validation/ Evidence Authority

### 5.1 Closure Evidence (G-P0)
```
plan/validation/closure/G-P0-38b0c57/
  ├── ci/*.yaml                    EVIDENCE_IMMUTABLE (CI results)
  └── evidence/                    EVIDENCE_IMMUTABLE
```

**Contains**: Historical CI pipeline results from old repository (ayitnovel/ainovelos)  
**Authority**: IMMUTABLE - accurate historical record  
**Action**: PRESERVE as-is (do not update URLs)

### 5.2 Execution Validation (V2-001 through V2-004)
```
plan/validation/execution/V2-001/   EVIDENCE_IMMUTABLE
plan/validation/execution/V2-002/   EVIDENCE_IMMUTABLE
plan/validation/execution/V2-003/   EVIDENCE_IMMUTABLE
plan/validation/execution/V2-004/   EVIDENCE_IMMUTABLE
```

**Contains**: Execution packets, CI artifacts, evidence binding  
**Authority**: IMMUTABLE  
**Old Repo References**: PRESERVE (historical accuracy)

### 5.3 V2-005 Validation (Expected but Absent)
```
plan/validation/execution/V2-005/   <DOES NOT EXIST YET>
```

**Expected After**: Step 3 completion  
**Should Contain**: Step 1, Step 2, Step 3 evidence binding

---

## 6. AI Canonical Entrypoints

### 6.1 Current Implicit Entrypoint Sequence
For a new AI agent entering the project:

1. **README.md** (root) → Project overview
   - Problem: Mentions "V2-003 已完成" but not V2-005 status
   - Problem: No explicit "current task" statement
   
2. **AGENTS.md** (root) → AI execution entry
   - Redirects to plan/README.md and AI_EXECUTION_PROTOCOL.md
   - Current and accurate
   
3. **plan/README.md** → Planning index
   - Points to machine/implementation-backlog.yaml for task status
   - Current
   
4. **plan/machine/implementation-backlog.yaml** → Task registry
   - V2-005 task defined
   - No explicit `state:` field (must infer from evidence)

5. **docs/V2-005_IMPLEMENTATION_CONTRACT.md** → Current contract
   - Version 1.1.0
   - Defines Step 1, 2, 3
   - No explicit "current step" marker

6. **Untracked docs/** → Evidence files
   - Step 2 completion evidence exists but untracked
   - Not discoverable via git ls-files

**Total Navigation Hops**: 6+ to understand "currently at Step 3"

### 6.2 Recommended Minimal Entrypoint Set

**Proposal**: Create 3 new summary documents at root:

1. **PROJECT_STATUS.md** (NEW)
   - One-page current state summary
   - Current phase, task, step
   - Last verified SHA and Pipeline
   - Next action

2. **README.md** (UPDATE)
   - Add explicit V2-005 Step 2 completion
   - Add "Current Status: See PROJECT_STATUS.md"

3. **AGENTS.md** (KEEP AS-IS)
   - Already provides AI execution entry

**Result**: 1-2 hops to current status instead of 6+

---

## 7. Authority Conflicts and Ambiguities

### 7.1 V2-005 State Ambiguity

**Source 1**: README.md line 65
```
"V2-003 已完成本地实施与验证"
```
Implies: Currently past V2-003, but no V2-005 mention

**Source 2**: Untracked docs/V2-005_STEP_2_REPORT.md
```
"STEP_2_STATE: IMPLEMENTED_CI_VERIFIED"
"Next Step: STEP 3"
```
Implies: Step 2 complete, Step 3 ready

**Source 3**: plan/machine/implementation-backlog.yaml
```
task_id: V2-005
<no state: field>
```
Implies: State must be inferred from external evidence

**Resolution Required**: 
- Update README.md to reflect V2-005 Step 2 completion
- Add untracked evidence files to repository
- OR create explicit status document

### 7.2 Repository URL Authority

**Active Repository**: gitlab.com/angyang/ainovel  
**Historical Repository**: gitlab.com/ayitnovel/ainovelos

**Conflict**: 20+ references to old repository in evidence files

**Resolution**: NO CONFLICT - historical references are correct for historical evidence

---

## 8. Duplicate Content Analysis

### 8.1 Root vs docs/ Duplicates

**V2-005_INDEPENDENT_REVIEW_58d77d2.md**:
- Root: 33KB
- docs/: <check if exists>
- Action: Keep one authoritative copy, archive or remove duplicate

**V2-005_REMEDIATION_PACKAGE_e300429.tar.gz**:
- Root: 55KB
- docs/: <check if exists>
- Action: Move to docs/ or archive/

### 8.2 Duplicate Filename Issues

**V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md**:
- Missing .md extension
- Duplicate of proper filename
- Action: DELETE (after confirming identical content)

---

## 9. SSOT (Single Source of Truth) Analysis

### 9.1 Current Task Status SSOT

**Question**: What is the authoritative source for "V2-005 is at Step 3"?

**Current Answer**: Distributed across multiple sources
- README.md (stale, doesn't mention V2-005)
- Untracked docs/ (accurate but untracked)
- Git commit history (implicit)
- CI Pipeline results (external)

**Proposed SSOT**: PROJECT_STATUS.md at root

### 9.2 Contract SSOT

**Authoritative Source**: docs/V2-005_IMPLEMENTATION_CONTRACT.md v1.1.0  
**Status**: ✅ CLEAR SSOT

### 9.3 Task Definition SSOT

**Authoritative Source**: plan/machine/implementation-backlog.yaml  
**Status**: ✅ CLEAR SSOT

### 9.4 CI Configuration SSOT

**Authoritative Source**: .gitlab-ci.yml  
**Status**: ✅ CLEAR SSOT

---

## 10. Authority Matrix Summary

### 10.1 Document Count by Classification

```
NORMATIVE_ACTIVE: 30 files
OPERATIONAL_ACTIVE: 3 files
STATUS_ACTIVE: 0 files (⚠️ GAP)
EVIDENCE_IMMUTABLE: 40+ files
HISTORICAL: 15 files
DUPLICATE: 3 files
ARCHIVE_CANDIDATE: 4 files
```

### 10.2 Authority Health Assessment

| Aspect | Status | Issue |
|--------|--------|-------|
| Contract Authority | ✅ CLEAR | V2-005 contract v1.1.0 is authoritative |
| Task Definition | ✅ CLEAR | implementation-backlog.yaml is authoritative |
| CI Configuration | ✅ CLEAR | .gitlab-ci.yml is authoritative |
| Current Status | ⚠️ AMBIGUOUS | No single status document |
| Next Steps | ⚠️ IMPLICIT | Must infer from evidence |
| Phase State | ✅ CLEAR | phase-gates.yaml |
| Evidence Chain | ⚠️ PARTIAL | 11 untracked evidence files |
| Historical Preservation | ✅ GOOD | Clear archive/ separation |

**Overall Authority Health**: GOOD with GAPS in status clarity

---

## 11. Recommendations

### 11.1 Immediate Actions

1. **Create PROJECT_STATUS.md** at repository root
   - Current phase, task, step
   - Last verified SHA
   - Next action
   - Evidence references

2. **Update README.md**
   - Line 5: Add "V2-005 Step 2 VERIFIED"
   - Line 65: Update "当前实施边界" to V2-005

3. **Add untracked evidence to repository**
   - Review content of 11 untracked docs/ files
   - Commit as immutable evidence
   - Do not modify historical claims

4. **Move root duplicates to docs/**
   - AT08_LEGITIMATE_CONTROL.md → docs/
   - Archive tar.gz files appropriately

### 11.2 Defer to Post-Housekeeping

5. Create plan/validation/execution/V2-005/ structure
6. Archive root-level review documents
7. Establish formal document lifecycle policy

---

**END OF AUTHORITY MATRIX REPORT**

Next: Stale Reference Report
