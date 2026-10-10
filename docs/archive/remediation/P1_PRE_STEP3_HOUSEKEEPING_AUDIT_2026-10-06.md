# P1-PRE-STEP3-HOUSEKEEPING-001: Repository Reality Audit
**Document ID**: P1-PRE-STEP3-HOUSEKEEPING-AUDIT  
**Date**: 2026-10-06  
**Status**: PHASE_A_COMPLETE / CLASSIFICATION_IN_PROGRESS  
**Baseline Branch**: work/h2-convergence-closure  
**Baseline SHA**: be6e475b77b5802cfcc73242f7273588288d06bf

---

## Executive Summary

Phase A (Read-Only Repository Reality Audit) has been completed. This report documents the current state of the ANovelOS repository after migration to the new canonical repository at `gitlab.com/angyang/ainovel.git`.

**Key Findings**:
- ✅ Canonical repository migration successful
- ✅ Step 2 exact-SHA verification complete (1aa31e7, Pipeline 2915904387)
- ✅ Active development continuation established (be6e475)
- ⚠️ Multiple stale repository references to old URL (ayitnovel/ainovelos)
- ⚠️ Root directory contains historical noise files
- ⚠️ 11 untracked evidence/report files in docs/
- ⚠️ Remote URL contains embedded PAT (security hygiene issue)
- ⚠️ No explicit PROJECT_STATUS.md or NEXT_STEPS.md for AI entrypoint

**Scope**: This audit covers repository structure, documentation authority, branch classification, and preparation for V2-005 Step 3 implementation.

---

## 1. Repository State Snapshot

### 1.1 Current Branch and HEAD
```
CURRENT_BRANCH: work/h2-convergence-closure
CURRENT_HEAD: be6e475b77b5802cfcc73242f7273588288d06bf
UPSTREAM: origin/work/h2-convergence-closure
STATUS: up to date
DIRTY: YES (11 untracked files in docs/)
```

### 1.2 Remote Configuration
```
REMOTE_NAME: origin
REMOTE_URL: https://oauth2:glpat-<REDACTED>@gitlab.com/angyang/ainovel.git
REMOTE_CREDENTIAL_EMBEDDED: YES
SECURITY_RISK: LOW (user confirmed non-confidential project)
```

**Canonical Repository**: https://gitlab.com/angyang/ainovel.git  
**Old Repository** (historical): https://gitlab.com/ayitnovel/ainovelos.git

### 1.3 Verification Evidence (Immutable)
```
STEP_2_EXACT_VERIFIED_SHA: 1aa31e7cdaff14e777210011c766badcd797b836
STEP_2_EXACT_PIPELINE: 2915904387
STEP_2_CI_RESULT: 6/6 PASS
STEP_2_TEST_RESULT: 565/565 PASS
STEP_2_STATE: IMPLEMENTED_CI_VERIFIED
STEP_3_MAY_BEGIN: YES
```

```
CONTINUATION_REVISION: be6e475b77b5802cfcc73242f7273588288d06bf
CONTINUATION_PARENT_1: 1aa31e7 (Step 2 exact SHA)
CONTINUATION_PARENT_2: 376565f (new repo initial commit)
CONTINUATION_FILE_DIFF_VS_1aa31e7: 0 files changed
```

### 1.4 Tracked Files Inventory
```
TOTAL_TRACKED_FILES: 1421
MARKDOWN_FILES: 310
PYTHON_CACHE_FILES: 727 (.pyc files)
CACHE_AND_SYSTEM_FILES: 826 (__pycache__, .DS_Store, etc.)
```

### 1.5 Directory Size Analysis
```
dist/            175M  (generated artifacts, cache, planning exports)
.venv/           150M  (Python virtual environment)
plan/             20M  (normative planning documents)
.mypy_cache/      12M  (type checker cache)
docs/            1.2M  (evidence and reports)
tests/           780K  (test suite)
scripts/          36K  (governance and CI scripts)
src/              16K  (production source code)
specs/           4.0K  (JSON schemas)
```

---

## 2. Branch Classification

### 2.1 Active Development Branches
| Branch | HEAD | Classification | Purpose |
|--------|------|----------------|---------|
| work/h2-convergence-closure | be6e475 | ACTIVE_DEVELOPMENT | Current continuation after repo migration |
| verification/v2-005-step2-1aa31e7 | 1aa31e7 | VERIFICATION_EVIDENCE | Exact SHA verification for Step 2 |

### 2.2 Historical/Merged Branches (Local)
| Branch | HEAD | Status | Notes |
|--------|------|--------|-------|
| dev_cc | e300429 | HISTORICAL | Contract remediation branch, merged into continuation |
| main | 882d0cd | DIVERGED | ahead 36, behind 1 vs origin/main |
| work/h1-focused-remediation | c9345d1 | HISTORICAL | H1 remediation complete, merged |
| work/g-p0-* | various | GOVERNANCE | P0 closure and governance fixes |
| work/v2-002-superseding-revalidation | a752afa | HISTORICAL | V2-002 revalidation |
| work/v2-004-* | various | HISTORICAL | V2-004 evidence and revalidation |
| work/at08-enable-mr-pipeline | 9471543 | GOVERNANCE | MR pipeline configuration |
| work/p0-final-architecture-audit-h3 | 5b92bba | GOVERNANCE | P0 final audit |

### 2.3 Remote-Only Branches
| Branch | Purpose |
|--------|---------|
| origin/acceptance/v2-004 | V2-004 acceptance evidence |
| origin/codex/v2-004-enrollment-permission-probe-* | V2-004 permission probes |
| origin/dev_gpt | Historical development branch |

### 2.4 Git Stash
```
stash@{0}: WIP on dev_cc (6aee132)
stash@{1}: WIP on work/g-p0-h2-validator-self-test
```
**Classification**: HISTORICAL / INSPECTION_NEEDED

---

## 3. Root Directory File Noise

### 3.1 Historical Review/Evidence Files (Root Level)
These files appear to be temporary review artifacts that should be archived or removed:

| File | Size | Classification |
|------|------|----------------|
| V2-005_INDEPENDENT_REVIEW_58d77d2.md | 33K | DUPLICATE (exists in docs/) |
| V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md | 33K | DUPLICATE (missing .md extension) |
| V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md | 12K | HISTORICAL_EVIDENCE (contains old repo refs) |
| V2-005_REMEDIATION_PACKAGE_e300429.tar.gz | 54K | HISTORICAL_ARCHIVE |
| V2-005_H1_REMEDIATION_PACKAGE.tar.gz | 63K | HISTORICAL_ARCHIVE |
| 审核报告.txt | 27K | HISTORICAL (Chinese audit report) |
| V2-003任务prompt.txt | 11K | HISTORICAL (V2-003 task prompt) |
| AT08_LEGITIMATE_CONTROL.md | 349B | TEST_EVIDENCE (likely belongs in docs/) |

### 3.2 System/Cache Files (Ignored but Present)
```
.DS_Store              (macOS metadata)
.pytest_cache/         (test cache, 64K)
.mypy_cache/           (type cache, 12M)
.ruff_cache/           (linter cache, 156K)
```
**Status**: Properly ignored by .gitignore

### 3.3 Root Configuration Files (KEEP)
```
README.md              ✅ NORMATIVE_ACTIVE
AGENTS.md              ✅ OPERATIONAL_ACTIVE
pyproject.toml         ✅ BUILD_CONFIG
uv.lock                ✅ DEPENDENCY_LOCK
compose.yaml           ✅ TEST_INFRASTRUCTURE
.gitlab-ci.yml         ✅ CI_CONFIG
.gitignore             ✅ VCS_CONFIG
.gitleaks.toml         ✅ SECURITY_CONFIG
ruff.toml              ✅ LINT_CONFIG
security-policy.yaml   ✅ SECURITY_POLICY
.env.example           ✅ CONFIG_TEMPLATE
.python-version        ✅ RUNTIME_VERSION
```

---

## 4. Untracked Files in docs/

The following 11 files are untracked (not committed):

```
docs/CI-LOCK-H1_FIX_REPORT.md
docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md
docs/CI-POLICY-H1_DIAGNOSIS.md
docs/CI-POLICY-H1_INVESTIGATION_COMPLETE.md
docs/V2-005_AUTHORIZATION_EFFECTUATION_REPORT.md
docs/V2-005_AUTHORIZATION_FINAL_REPORT.md
docs/V2-005_POST_CI_EXECUTION_REPORT.md
docs/V2-005_STEP_1_CI_FIX_REPORT.md
docs/V2-005_STEP_1_REPORT.md
docs/V2-005_STEP_2_H1_FIX_REPORT.md
docs/V2-005_STEP_2_REPORT.md
```

**Classification**: EVIDENCE_UNTRACKED  
**Rationale**: These appear to be evidence documents generated during V2-005 Step 1 and Step 2 implementation and CI remediation.

**Recommendation**: Add to repository as immutable evidence if they document actual work performed. Review for any stale status claims before committing.

---

## 5. Documentation Authority Findings

### 5.1 Current Authoritative Entry Points
Based on README.md and repository structure:

1. **README.md** - Project overview and quickstart
2. **AGENTS.md** - AI execution entry point
3. **plan/README.md** - Planning authority index
4. **plan/AI_EXECUTION_PROTOCOL.md** - AI governance
5. **docs/V2-005_IMPLEMENTATION_CONTRACT.md** - Current task contract (v1.1.0)
6. **plan/machine/implementation-backlog.yaml** - Task registry
7. **plan/machine/phase-gates.yaml** - Phase status

### 5.2 Missing AI Entrypoint Documents
**Finding**: No explicit `PROJECT_STATUS.md` or `NEXT_STEPS.md` at repository root.

**Impact**: A new AI agent must read README.md → AGENTS.md → plan/README.md → implementation-backlog.yaml to understand current state. This is a 4-hop navigation.

**Current Status Derivation Path**:
- README.md says "V2-001 through V2-004 CLOSED, G-P0 PASS"
- README.md says "当前实施边界: V2-003 已完成本地实施与验证"
- Untracked docs/ files reference V2-005 Step 1 and Step 2
- Must infer: currently at V2-005 Step 3

### 5.3 Stale Repository References

**Old Repository URL**: `https://gitlab.com/ayitnovel/ainovelos`  
**Found in**: 20+ locations

Sample findings:
```
V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md:
  - Pipeline URL references ayitnovel/ainovelos
  
plan/validation/closure/G-P0-38b0c57/ci/*.yaml:
  - pipeline_url: https://gitlab.com/ayitnovel/ainovelos/-/pipelines/...
  
plan/validation/execution/V2-004/remote-security/*.md:
  - Project: ayitnovel/ainovelos
```

**Classification**: HISTORICAL_VALID  
**Rationale**: These are immutable evidence files documenting actual historical CI runs. The old repository URLs are factually correct for those historical events.

**Required Action**: NONE (preserve historical accuracy)  
**Prohibited Action**: Mechanically replacing historical URLs with new repository

---

## 6. Contract and Task Status Verification

### 6.1 V2-005 Implementation Contract
```
FILE: docs/V2-005_IMPLEMENTATION_CONTRACT.md
VERSION: 1.1.0
DATE: 2026-10-03
STATUS: REVISED / INDEPENDENT_REVIEW_PENDING
AUTHORITY: Implementation Contract (Pending Approval)
```

**Contract Baseline**: dev_cc @ 323eaae7  
**Contract Defines**: EntityId, ProjectId, ResolutionResult, normalization rules  
**Step Breakdown**: 3 steps defined  
**Current Step**: STEP 3 - IMPLEMENT ID GENERATION AND NORMALIZATION

### 6.2 Task Status in implementation-backlog.yaml
```
task_id: V2-005
title: Core entity IDs and alias resolution
phase: P1
priority: P0
state: <NOT EXPLICITLY DEFINED IN YAML>
```

**Finding**: The implementation-backlog.yaml does not contain explicit `state:` or `status:` fields for V2-005.

**State Derivation**: Must be inferred from:
- Evidence files in docs/
- CI Pipeline results
- Git commit history

### 6.3 README.md Current State Claims
```
Line 5: "V2-001 through V2-004 CLOSED, G-P0 PASS"
Line 65: "V2-003 已完成本地实施与验证"
```

**Finding**: README does not mention V2-005 current state.  
**Impact**: Stale status information for new AI agents.

---

## 7. CI and Pipeline Status References

### 7.1 GitLab CI Configuration
```
FILE: .gitlab-ci.yml
VERSION: 1.0.0
GATES: STATIC, UNIT, SCHEMA_CONTRACT, ARCH_FITNESS, SECRET_DEPENDENCY, POSTGRES_ENV
DEPENDENCIES: uv.lock (uv sync --frozen)
```

**Status**: ✅ CI configuration is current and verified working in new repository

### 7.2 Historical CI Block References

**Found in untracked docs/**:
```
docs/CI-POLICY-H1_INVESTIGATION_COMPLETE.md:
  "Step 2 State: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED"
  
docs/CI-POLICY-H1_DIAGNOSIS.md:
  "Step 2 State: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED"
  
docs/CI-LOCK-H1_FIX_REPORT.md:
  "STEP_2_STATE: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED"
```

**Also found**:
```
docs/V2-005_STEP_2_H1_FIX_REPORT.md:
  "STEP_2_STATE: IMPLEMENTED_CI_VERIFIED"
  
docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md:
  "STEP_2_STATE = IMPLEMENTED_CI_VERIFIED"
```

**Classification**: HISTORICAL_SEQUENCE  
**Interpretation**: These documents show the progression from CI_BLOCKED → CI_VERIFIED after repository migration.

**Current Authoritative Status**:
- Step 2: IMPLEMENTED_CI_VERIFIED (Pipeline 2915904387, 6/6 PASS, 565/565 PASS)
- Step 3: READY_TO_BEGIN

---

## 8. Security and Credential Hygiene

### 8.1 Remote URL Credential Embedding
```
FINDING: Remote URL contains embedded GitLab PAT
LOCATION: .git/config remote.origin.url
FORMAT: https://oauth2:glpat-<TOKEN>@gitlab.com/angyang/ainovel.git
ACTIVE: YES
CREDENTIAL_STATUS: User confirmed non-confidential project
OWNER_ACTION: User declined revocation
```

**Risk Level**: LOW (user explicit decision)  
**Recommendation**: Document this as intentional deviation from standard practice.

### 8.2 .gitignore Coverage
```
✅ __pycache__/
✅ *.py[cod]
✅ .venv/
✅ .pytest_cache/
✅ .env (with !.env.example)
✅ *.pem, *.key
✅ *credential*, *secret*.json
✅ .DS_Store
✅ node_modules/
✅ dist/
```

**Status**: Adequate coverage for standard Python project.

### 8.3 No Active Secrets Found
No credential files found in tracked repository content during this audit.

---

## 9. Duplicate and Archive Candidates

### 9.1 Root-Level Duplicates
```
V2-005_INDEPENDENT_REVIEW_58d77d2.md (root)
→ DUPLICATE of file in docs/ (if exists)

V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md (root)
→ DUPLICATE with malformed filename
```

### 9.2 Compressed Archives in Root
```
V2-005_REMEDIATION_PACKAGE_e300429.tar.gz (55K, root)
V2-005_H1_REMEDIATION_PACKAGE.tar.gz (63K, root)
docs/V2-005_REMEDIATION_PACKAGE_e300429.tar.gz (exists?)
docs/V2-005_审核材料_58d77d2.tar.gz (exists in docs/)
```

**Finding**: Potential duplicate archives between root and docs/.

### 9.3 Planning Distribution Archives
```
dist/planning/ANovelOS_Implementation_Plan_v1.2.2.zip
dist/planning/ANovelOS_Implementation_Plan_v1.3.0.zip
```

**Classification**: GENERATED_DISTRIBUTION  
**Status**: Intentional versioned exports, KEEP

---

## 10. AI Context Clarity Assessment

**Question**: Can a new AI agent quickly answer these questions?

| Question | Answer Location | Hops | Clear? |
|----------|----------------|------|--------|
| What is this project? | README.md line 3 | 1 | ✅ YES |
| Current canonical repo? | README.md (implicit) | 1 | ⚠️ INDIRECT |
| Current development branch? | <none> | ? | ❌ NO |
| Current HEAD? | <requires git command> | - | ❌ NO |
| Current phase/task? | README.md + backlog | 3 | ⚠️ INDIRECT |
| Step 2 verified? | <untracked docs> | ? | ❌ NO |
| Next step is Step 3? | <untracked docs> | ? | ❌ NO |
| Which docs are normative? | AGENTS.md + plan/README | 2 | ⚠️ PARTIAL |
| Which are historical? | <implicit from archive/> | ? | ⚠️ PARTIAL |
| What is prohibited? | AI_EXECUTION_PROTOCOL.md | 2 | ✅ YES |

**Assessment**: AI entrypoint clarity is PARTIAL but IMPROVABLE.

**Gap**: No single-file current status summary at repository root.

---

## 11. Phase A Summary Statistics

```
FILES_SCANNED: 1421 tracked + ~3800 in dist/ + 11 untracked
BRANCHES_SCANNED: 17 local + 10 remote-only = 27 total
DOCS_CLASSIFIED: 310 markdown files scanned
STALE_REPO_REFERENCES: 20+ (all in historical evidence)
SECURITY_FINDINGS: 1 (embedded PAT, user-accepted)
DELETE_CANDIDATES: 8 root-level files (review needed)
ARCHIVE_CANDIDATES: 2-4 tar.gz files (deduplication needed)
UNTRACKED_EVIDENCE: 11 files in docs/
```

---

## 12. Phase A Completion Status

```
✅ Repository state snapshot complete
✅ Remote configuration audited
✅ Branch classification complete
✅ File inventory complete
✅ Documentation authority scan complete
✅ Stale reference identification complete
✅ Security hygiene audit complete
✅ Duplicate/archive candidate identification complete
✅ AI entrypoint clarity assessment complete
```

**PHASE A**: COMPLETE  
**NEXT PHASE**: Phase B - Documentation Authority Matrix (detailed classification)

---

## 13. Preliminary Recommendations (Subject to Phase B-L)

### 13.1 High Priority
1. Add untracked docs/ evidence files to repository (after review)
2. Create `PROJECT_STATUS.md` at root with current state summary
3. Update README.md to reflect V2-005 Step 2 completion
4. Archive or remove root-level duplicate/historical files

### 13.2 Medium Priority
5. Classify and document branch retention policy
6. Review and potentially remove old stashes
7. Create explicit "next steps" section in status doc

### 13.3 Low Priority / Defer
8. Branch cleanup (after classification review)
9. Historical evidence organization (no semantic changes)

### 13.4 No Action Required
10. Stale repository URLs in historical evidence (preserve as-is)
11. Embedded PAT in remote URL (user decision)
12. Cache directories (properly ignored)

---

## 14. Stop Conditions Check

```
❌ SSOT conflicts: NONE detected
❌ Production code modification required: NO
❌ Contract modification required: NO
❌ Schema/migration issues: NONE
❌ Branch history rewrite needed: NO
❌ Active credential requiring revocation: NO (user decision)
❌ Evidence identity inconsistency: NONE
✅ Current HEAD matches expected: YES (be6e475)
⚠️ Uncommitted modifications: YES (11 untracked files, expected)
❌ Remote concurrent updates: NONE detected
```

**STATUS**: No stop conditions triggered. Safe to proceed to Phase B.

---

**END OF PHASE A AUDIT REPORT**

Next: Phase B - Documentation Authority Matrix
