# CI-POLICY-H1-R1: PROJECT CI CONFIGURATION REMEDIATION

**Date**: 2026-10-05  
**Type**: Infrastructure / GitLab Project Settings Fix  
**Status**: ⏳ **REQUIRES MANUAL GITLAB OPERATION**

---

## EXECUTIVE SUMMARY

⚠️ **CI-POLICY-H1-R1: MANUAL GITLAB CONFIGURATION REQUIRED**

**Root Cause Confirmed**: GitLab project-level `ci_config_path` is set to V2-004 Trusted CI, causing all branches (including `dev_cc`/`work/h2-convergence-closure`) to execute `dev_gpt`'s CI configuration instead of their own `.gitlab-ci.yml`.

**Resolution**: Restore GitLab project CI configuration file to default (`.gitlab-ci.yml` or empty).

**Critical**: This is **NOT fixable via code**. Requires GitLab project settings modification by maintainer with appropriate permissions.

---

## ROOT CAUSE VERIFIED

### Current GitLab Project Configuration

**Setting**: Settings → CI/CD → General pipelines → CI/CD configuration file  
**Current Value**:
```
plan/validation/execution/V2-004/enrollment-20261005/trusted-ci.yml
@ayitnovel/ainovelos:acceptance/v2-004
```

**Effect**: This project-level setting overrides ALL branches' `.gitlab-ci.yml`, routing all pipelines through V2-004 Trusted CI configuration.

---

## INCORRECT CI ROUTING DIAGRAM

```
Code Relationship (CORRECT):
dev_cc (V2-005)  ━━━━━━━━ Independent
dev_gpt (V2-004) ━━━━━━━━ Independent

Current CI Routing (INCORRECT):
dev_cc push
    ↓
GitLab Project-level ci_config_path
    ↓
plan/.../trusted-ci.yml@acceptance/v2-004
    ↓
include: 9fe51ab (dev_gpt HEAD)
    ↓
Requires: scripts/ci/run_gate.py ❌
          uv sync --locked
          python:3.12.14-bookworm

Expected (dev_cc should use its own CI):
dev_cc push
    ↓
work/h2-convergence-closure:.gitlab-ci.yml
    ↓
uv sync --frozen
ruff, mypy (direct invocation)
NO scripts/ci/run_gate.py ✓
```

---

## WHY workflow:rules CANNOT FIX THIS

**Common Misconception**: Add `workflow:rules` to `trusted-ci.yml` to skip non-acceptance branches

**Why This Fails**:
- `ci_config_path` is the **top-level entry point** for ALL pipelines
- Once set at project level, GitLab reads CI configuration from that location
- `workflow:rules` can prevent pipeline creation, but **cannot** redirect back to branch's `.gitlab-ci.yml`
- If workflow rules exclude a branch, pipeline simply doesn't run (vs. falling back to branch CI)

**GitLab Documentation**:
> "The path to the CI/CD configuration file for the project. This file is used for ALL pipelines unless overridden."

**Reference**: [GitLab CI/CD Configuration Paths](https://docs.gitlab.com/ee/ci/pipelines/settings.html#specify-a-custom-cicd-configuration-file)

---

## REMEDIATION REQUIRED

### Immediate Action (Manual)

**Location**: GitLab Project → Settings → CI/CD → General pipelines → CI/CD configuration file

**Current Value**:
```
plan/validation/execution/V2-004/enrollment-20261005/trusted-ci.yml@ayitnovel/ainovelos:acceptance/v2-004
```

**Required Change**:
```
.gitlab-ci.yml
```
OR
```
(empty/clear the field)
```

**Effect**:
- All branches will use their own `.gitlab-ci.yml` at repository root
- `dev_cc`/`work/h2-convergence-closure` will use `uv sync --frozen` + direct tool invocation
- No more `scripts/ci/run_gate.py` requirement for dev_cc

---

### Verification Steps (After Configuration Change)

1. ✅ **Confirm Configuration Change**
   - Re-read GitLab project settings
   - Verify `ci_config_path` is now `.gitlab-ci.yml` or empty

2. ✅ **DO NOT Modify dev_cc Code**
   - No new commits
   - No cherry-picks from dev_gpt
   - Keep HEAD at `1aa31e7cdaff14e777210011c766badcd797b836`

3. ✅ **Retry Pipeline for Exact SHA**
   - Branch: `work/h2-convergence-closure`
   - SHA: `1aa31e7cdaff14e777210011c766badcd797b836`
   - Trigger: Manual retry or new push

4. ✅ **Verify Job Trace Shows dev_cc CI**
   - Image: `python:3.12-bookworm` (not `3.12.14`)
   - Sync: `uv sync --frozen` (not `--locked`)
   - Gates: Direct `ruff`/`mypy` calls
   - **NO** `scripts/ci/run_gate.py` references

5. ✅ **Confirm 6/6 Gates PASS**
   - STATIC: PASS (ruff, mypy)
   - SCHEMA_CONTRACT: PASS
   - UNIT: PASS (565/565)
   - ARCH_FITNESS: PASS (222/222)
   - POSTGRES_ENV: PASS
   - SECRET_DEPENDENCY: PASS (pip-audit)

6. ✅ **Only After Full CI SUCCESS**
   - Update Step 2 state: `IMPLEMENTED_CI_VERIFIED`
   - Unblock Step 3: `STEP_3_MAY_BEGIN = YES`

---

## IMPACT ON acceptance/v2-004

**Governance Issue**: Clearing `ci_config_path` also affects `acceptance/v2-004` branch

**Short-Term**: `acceptance/v2-004` will no longer automatically use V2-004 Trusted CI

**Long-Term Solution Required**: CI Dispatcher (see below)

---

## LONG-TERM ARCHITECTURE: CI DISPATCHER

**Problem**: Manual switching of `ci_config_path` is not scalable

**Solution**: Create a lightweight CI dispatcher at project level

### Proposed Dispatcher Configuration

**File**: `.gitlab-ci-dispatcher.yml` (at project level)

```yaml
# GitLab Project CI Dispatcher
# Routes branches to appropriate CI configurations

include:
  # V2-004 Trusted CI (for acceptance branch only)
  - project: ayitnovel/ainovelos
    ref: acceptance/v2-004
    file: plan/validation/execution/V2-004/enrollment-20261005/trusted-ci.yml
    rules:
      - if: '$CI_COMMIT_REF_NAME == "acceptance/v2-004"'

  # Branch-specific CI (for all other branches)
  - project: '$CI_PROJECT_PATH'
    ref: '$CI_COMMIT_REF_NAME'
    file: '.gitlab-ci.yml'
    rules:
      - if: '$CI_COMMIT_REF_NAME != "acceptance/v2-004"'
```

**GitLab Support**:
- ✅ `include:rules` supported
- ✅ `$CI_PROJECT_PATH` available pre-pipeline
- ✅ `$CI_COMMIT_REF_NAME` available pre-pipeline
- ✅ Dynamic `ref:` resolution supported

**Reference**: [GitLab include:rules](https://docs.gitlab.com/ee/ci/yaml/includes.html#use-rules-with-include)

**Effect**:
```
GitLab Project ci_config_path: .gitlab-ci-dispatcher.yml
    ↓
    ├── acceptance/v2-004
    │       ↓
    │   V2-004 Trusted CI (9fe51ab)
    │       ↓
    │   scripts/ci/run_gate.py
    │
    └── dev_cc / work/*
            ↓
        Branch's own .gitlab-ci.yml
            ↓
        uv sync --frozen, direct tools
```

**Implementation Note**: Dispatcher is **future enhancement**, not required for immediate fix

---

## CRITICAL BOUNDARIES MAINTAINED

### What We Are NOT Doing ✅

❌ **NOT** copying `dev_gpt`'s `scripts/ci/run_gate.py` to `dev_cc`  
❌ **NOT** cherry-picking V2-004 infrastructure to `dev_cc`  
❌ **NOT** merging `dev_gpt` into `dev_cc`  
❌ **NOT** making `dev_cc` compatible with `dev_gpt` CI expectations  
❌ **NOT** modifying `dev_cc` code to pass V2-004 Trusted CI

### What We ARE Doing ✅

✅ **Restoring** GitLab project CI configuration to default  
✅ **Allowing** `dev_cc` to use its own `.gitlab-ci.yml`  
✅ **Maintaining** independence between `dev_cc` and `dev_gpt` code lines  
✅ **Preserving** V2-004 Trusted CI for `acceptance/v2-004` (future dispatcher)

---

## CORRECT BOUNDARIES

```yaml
dev_cc Work Line:
  Purpose: V2-005 implementation
  CI: .gitlab-ci.yml (uv sync --frozen, direct tools)
  Dependencies: NONE on dev_gpt
  Should NOT: Import dev_gpt infrastructure

dev_gpt Work Line:
  Purpose: V2-004 Trusted Execution
  CI: scripts/ci/run_gate.py orchestration
  Dependencies: Independent
  Should NOT: Be forced onto dev_cc

acceptance/v2-004:
  Purpose: V2-004 formal acceptance
  CI: V2-004 Trusted CI (appropriate for this context)
  Should: Continue using trusted configuration
```

---

## EXECUTION SEQUENCE: CI-POLICY-H1-R1

### Phase 1: Record Current State ✅
**Current `ci_config_path`**:
```
plan/validation/execution/V2-004/enrollment-20261005/trusted-ci.yml@ayitnovel/ainovelos:acceptance/v2-004
```

### Phase 2: Modify GitLab Project Settings (MANUAL REQUIRED) ⏳
**Action**: Human operator with GitLab maintainer permissions must:
1. Navigate to: GitLab Project → Settings → CI/CD → General pipelines
2. Locate: "CI/CD configuration file"
3. Change from:
   ```
   plan/validation/execution/V2-004/enrollment-20261005/trusted-ci.yml@ayitnovel/ainovelos:acceptance/v2-004
   ```
4. Change to:
   ```
   .gitlab-ci.yml
   ```
   (or clear field to use default)
5. Save settings

### Phase 3: Verify Configuration Change ⏳
**Action**: Re-read GitLab project settings via API/UI
**Expected**: `ci_config_path` is now `.gitlab-ci.yml` or empty

### Phase 4: Do NOT Modify dev_cc Code ✅
**No commits to**: `work/h2-convergence-closure`  
**No cherry-picks from**: `dev_gpt`  
**Keep HEAD at**: `1aa31e7cdaff14e777210011c766badcd797b836`

### Phase 5: Retry Pipeline for Exact SHA ⏳
**Branch**: `work/h2-convergence-closure`  
**SHA**: `1aa31e7cdaff14e777210011c766badcd797b836`  
**Action**: Manual pipeline retry OR new push (no-op commit)

### Phase 6: Verify Job Trace ⏳
**Must See**:
- `uv sync --frozen` (not `--locked`)
- Direct `ruff format --check` calls
- Direct `mypy` calls
- Image: `python:3.12-bookworm`

**Must NOT See**:
- `scripts/ci/run_gate.py`
- `python:3.12.14-bookworm`
- `uv sync --locked`

### Phase 7: Confirm CI Success ⏳
**Required**: 6/6 gates PASS, 565/565 tests PASS

### Phase 8: Unblock Step 3 ⏳
**After CI SUCCESS**:
```
STEP_2_STATE = IMPLEMENTED_CI_VERIFIED
STEP_3_MAY_BEGIN = YES
```

---

## CURRENT PROJECT STATE

```yaml
CI-POLICY-H1 Investigation: ✅ COMPLETE
Root Cause: ✅ VERIFIED (project-level ci_config_path misdirection)
dev_gpt Code Dependency: ✅ NONE (CI-only coupling)
Project CI Scope Error: ✅ VERIFIED

CI-POLICY-H1-R1 Remediation: ⏳ REQUIRES MANUAL GITLAB OPERATION
Blocked By: GitLab project settings access required

Step 2-H1 Code: ✅ ACCEPTED
Step 2 Contract: ✅ PASS
CI-LOCK-H1: ✅ COMPLETE

Step 2 Exact-SHA CI: ❌ BLOCKED (awaiting GitLab config fix)
Step 2 State: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED
Step 3: 🔒 BLOCKED (awaiting Step 2 CI verification)
```

---

## WHY I CANNOT FIX THIS

**I Am**: Code-level AI assistant  
**I Can**: Read files, write code, commit, push, analyze repository  
**I Cannot**: Modify GitLab project settings, access GitLab UI, call GitLab API for settings changes

**This Issue**: Requires GitLab project-level configuration change  
**Required Permission**: Maintainer or Owner role on GitLab project  
**Resolution**: Human operator must execute Phase 2 (modify GitLab settings)

---

## NEXT STEPS

**Immediate** (Human Required):
1. ⏳ Modify GitLab project `ci_config_path` to `.gitlab-ci.yml`
2. ⏳ Retry pipeline for SHA `1aa31e7`
3. ⏳ Verify job trace shows dev_cc's own CI
4. ⏳ Confirm 6/6 gates PASS

**After CI Success**:
5. ✅ Update Step 2 state: `IMPLEMENTED_CI_VERIFIED`
6. ✅ Proceed to V2-005 Step 3

**Future Enhancement**:
7. 🔮 Implement CI dispatcher for branch-specific routing
8. 🔮 Restore V2-004 Trusted CI for `acceptance/v2-004` via dispatcher

---

## SUMMARY

**Operation**: CI-POLICY-H1-R1 Project CI Configuration Remediation  
**Status**: ⏳ REQUIRES MANUAL GITLAB OPERATION  
**Root Cause**: Project-level `ci_config_path` routes all branches to V2-004 Trusted CI  
**Resolution**: Restore `ci_config_path` to `.gitlab-ci.yml` (requires GitLab maintainer)  

**Critical Principle Maintained**:  
❌ Do NOT copy `dev_gpt` code to `dev_cc`  
✅ Fix CI routing configuration instead

**Blocked**: Step 2 CI verification, Step 3 implementation  
**Awaiting**: Human operator to modify GitLab project settings

---

**END OF CI-POLICY-H1-R1 REMEDIATION PLAN**

**Status**: Manual GitLab configuration required  
**Date**: 2026-10-05  
**Blocker**: Project-level ci_config_path setting  
**Resolution**: Restore to `.gitlab-ci.yml` via GitLab Settings → CI/CD
