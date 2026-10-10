# Repository AI Context Hygiene Inventory

**Task**: REPO-AI-CONTEXT-HYGIENE-003  
**Date**: 2026-10-09  
**Baseline SHA**: c69a3427985ea6adbaf7425dac71b1e8e28239b5

---

## Authority Conflicts Identified

### CRITICAL: Duplicate ADR-002 Assignment

**Machine Authority** (plan/machine/decision-register.yaml):
```yaml
id: ADR-002
related_tasks: [V2-061]
```

**Stale Authority** (docs/decision-register.yaml):
```yaml
id: ADR-002
related_tasks: [V2-006]  # WRONG - V2-006 is CLOSED
```

**Risk**: AI thinks Character Knowledge belongs to V2-006 instead of V2-061

**Action**: DELETE docs/decision-register.yaml (no current references, superseded by machine authority)

---

## Duplicate Normative Authority

### docs/00_GOVERNANCE_AND_SOURCE_AUTHORITY.md vs plan/00_GOVERNANCE_AND_SOURCE_AUTHORITY.md

**Status**: Files are IDENTICAL (diff shows no differences)

**Risk**: Future drift if both maintained

**Action**: KEEP plan/ version (canonical), POINTER in docs/

### docs/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md vs plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md

**Status**: Files are IDENTICAL

**Risk**: Future drift

**Action**: KEEP plan/ version (canonical), POINTER in docs/

---

## Historical/Intermediate Documents (docs/)

### High Confidence Archive Candidates

**H-series progress/remediation** (29 files):
- docs/H1_REMEDIATION_PROGRESS.md
- docs/H1_CHANGE_SUMMARY.md
- docs/H2_REMEDIATION_EVIDENCE.md
- docs/H3_FINAL_CONVERGENCE_EVIDENCE.md
- docs/H3.1_MICRO_FIX_EVIDENCE.md
- docs/V2-003.2-H1_HOTFIX_REPORT.md
- docs/V2-003.2-H2_VERIFICATION_CLOSURE.md
- docs/V2-005_H1_REMEDIATION_PACKAGE.tar.gz
- docs/V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md
- docs/CI-POLICY-H1_DIAGNOSIS.md
- docs/CI-POLICY-H1_INVESTIGATION_COMPLETE.md
- docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md
- docs/CI-LOCK-H1_FIX_REPORT.md
- ... (total 29 H1/H2/H3 files)

**Status**: Intermediate remediation/diagnostic artifacts

**Machine References**: None found

**Evidence References**: Need to check plan/validation/**

**Action**: ARCHIVE to docs/archive/remediation/ (preserve for history)

---

### Binary Packages

**Files**:
1. docs/V2-005_H1_REMEDIATION_PACKAGE.tar.gz
2. docs/V2-005_REMEDIATION_PACKAGE_e300429.tar.gz
3. docs/V2-005_审核材料_58d77d2.tar.gz

**Git Grep**: Referenced in 5 housekeeping audit files (themselves historical)

**Purpose**: Historical delivery artifacts for V2-005 remediation cycles

**Action**: ARCHIVE to docs/archive/packages/ (Git history preserved)

---

### V2-001 through V2-004 Progress Documents

**Files**: 20+ implementation reports, status updates, preparation docs

**Examples**:
- docs/V2-001_IMPLEMENTATION_REPORT.md
- docs/V2-002_IMPLEMENTATION_REPORT.md
- docs/V2-003.2-H1_HOTFIX_REPORT.md
- docs/V2-004_FOURTH_FIX_PROGRESS.md
- docs/V2-004_STATUS_CURRENT.md

**Status**: Historical progress (tasks now CLOSED)

**Machine References**: None (backlog references V2-00X_IMPLEMENTATION_CONTRACT.md only)

**Action**: ARCHIVE to docs/archive/v2-001-004/ (preserve history)

---

### V2-005 Intermediate Audit/Review Docs

**Files**: 15+ audit materials, checklists, independent reviews

**Examples**:
- docs/V2-005_AUDIT_MATERIALS_CHECKLIST.md
- docs/V2-005_INDEPENDENT_REVIEW_58d77d2.md
- docs/V2-005_INDEPENDENT_REVIEW_TRIAGE.md
- docs/V2-005_CURRENT_STATE_AUDIT.md

**Status**: Intermediate V2-005 remediation cycle artifacts

**Final Authority**: docs/reports/V2-005_FINAL_CLOSURE_REPORT.md

**Action**: ARCHIVE to docs/archive/v2-005-remediation/ (preserve provenance)

---

### docs/reports/ Intermediate Audits

**Files**: 36 report files

**HIGH CONFIDENCE ARCHIVE** (superseded by later reports):
- REPOSITORY_HYGIENE_AUDIT_2026-10-02.md (pre-P1)
- P1_PRESTART_HOUSEKEEPING_AUDIT_2026-10-03.md
- CODE_HYGIENE_INDEPENDENT_REVIEW_2026-10-03.md
- P1_PRE_STEP3_HOUSEKEEPING_AUDIT_2026-10-06.md
- P1_PRE_STEP3_HOUSEKEEPING_MUTATION_PLAN_2026-10-06.md (plan, not final)

**KEEP** (current authority):
- V2-005_FINAL_CLOSURE_REPORT.md (final V2-005 evidence)
- V2-005_FINAL_RATIFICATION.md (ratification)
- V2-006_IMPLEMENTATION_AUTHORIZATION.md (authorization)
- POST_V2_005_PRE_V2_006_REPOSITORY_REVIEW_2026-10-06.md (transition review)
- H3_SSOT_RECONCILIATION_FINAL_REPORT.md (recent SSOT closure)

---

## Files to KEEP Intentionally

### Current Authority & Contracts

**KEEP**:
- docs/V2-061_IMPLEMENTATION_CONTRACT.md (current task contract)
- docs/GOVERNANCE_TEST_HARNESS_DEBT.md (current debt record)
- docs/reports/V2-005_FINAL_CLOSURE_REPORT.md (closure evidence)
- docs/reports/V2-005_FINAL_RATIFICATION.md (ratification)
- docs/reports/V2-006_IMPLEMENTATION_AUTHORIZATION.md (authorization)
- docs/reports/H3_SSOT_RECONCILIATION_FINAL_REPORT.md (recent closure)

### Implementation Reports (Current Backlog References)

**KEEP** (referenced by plan/machine/implementation-backlog.yaml):
- docs/V2-00X_IMPLEMENTATION_CONTRACT.md (for X = 1, 2, 3, 4)

**Note**: Even though tasks are CLOSED, contracts remain normative references

---

## Reference Integrity Check

### docs/decision-register.yaml References

```bash
git grep "docs/decision-register.yaml"
```

**Result**: No references found

**Safe to DELETE**: YES

### Binary Package References

```bash
git grep "V2-005_.*\.tar\.gz"
```

**Result**: Referenced in 5 archived housekeeping reports

**Safe to ARCHIVE**: YES (references are themselves historical)

---

## Files Intentionally NOT Moved (Evidence/Validation)

### plan/validation/**

**Status**: HIGH RISK EVIDENCE VAULT

**Action**: NO CHANGES (preserve revision-bound evidence)

**Rationale**: Contains execution packets, closure evidence, hash bindings

### plan/archive/**

**Status**: Already explicitly archived

**Action**: NO CHANGES

**Rationale**: Clear archive区，不需要进一步清理

---

## Proposed Actions Summary

| Action | Count | Examples |
|--------|-------|----------|
| DELETE | 1 | docs/decision-register.yaml |
| POINTER REPLACEMENT | 2 | docs/00_GOVERNANCE*.md, docs/03_DOMAIN*.md |
| ARCHIVE | ~60 | H1/H2/H3 reports, binary packages, V2-001-004 progress, V2-005 audits |
| KEEP | ~15 | Current contracts, final reports, ratifications |

---

## AI Context Policy Updates Required

### AGENTS.md Updates

**Add**:
- Default active context list (plan/machine/*, current contracts)
- Default excluded context (plan/archive/, docs/archive/, plan/validation/)
- Authority hierarchy (plan/machine > docs/)

### plan/README.md Updates

**Verify**:
- Current status reflects P0 VERIFIED, P1 ACTIVE
- No stale V2-001-004 implementation guidance

---

## Validation Baseline

**Before Changes**:
- validate_plan --check: FAIL (64 findings - expected)
- validate_plan --self-test: PASS (32 cases)
- Task count: 61
- P0 status: VERIFIED
- v2.005-complete: 42e824b64fc27a808ffc523dd2b25f78b9b8b5e8
- v2.006-complete: 0b629433d9bd957742db4c609a8ca09473fd685b

**Expected After Changes**:
- No new validator regressions
- No broken references
- Same task count (61)
- Same immutable tags
