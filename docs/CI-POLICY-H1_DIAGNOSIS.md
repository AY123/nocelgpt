# CI-POLICY-H1: EFFECTIVE CI CONFIGURATION DIAGNOSIS

**Date**: 2026-10-05  
**Type**: Infrastructure / CI Governance Investigation  
**Scope**: Effective CI configuration authority and missing gate runner diagnosis

---

## EXECUTIVE SUMMARY

⚠️ **CI-POLICY-H1 DIAGNOSIS: BLOCKER IDENTIFIED**

GitLab effective CI configuration diverges from repository `.gitlab-ci.yml`. External CI policy/compliance injection detected. Missing `scripts/ci/run_gate.py` required by effective pipeline but not present in repository or documented in any discovered governance source.

**Current Blocker**: `scripts/ci/run_gate.py` not found  
**Impact**: Step 2 CI verification blocked  
**Status**: Investigation complete, resolution path requires external policy clarification

---

## ISSUE SUMMARY

### Pipeline Failure
**Failed SHA**: `1aa31e7cdaff14e777210011c766badcd797b836`  
**Pipeline**: #2912198356  
**Result**: ❌ FAILED

**Failed Gates**:
- ❌ STATIC (scripts/ci/run_gate.py not found)
- ❌ SCHEMA_CONTRACT (scripts/ci/run_gate.py not found)
- ❌ SECRET_DEPENDENCY (scripts/ci/run_gate.py not found)
- ⏭️ UNIT (skipped)
- ⏭️ ARCH_FITNESS (skipped)
- ⏭️ POSTGRES_ENV (skipped)

**Tests Executed**: 0 (gate runner failed before tests)

### New Error Pattern
**Error Message** (all three failed gates):
```
uv run --locked python -B scripts/ci/run_gate.py <gate_name>

can't open file '.../scripts/ci/run_gate.py':
[Errno 2] No such file or directory
```

**Important**: `uv sync --locked` succeeded. Lock drift is resolved. New blocker is missing gate runner script.

---

## EFFECTIVE CI VS REPOSITORY DIVERGENCE

### Evidence of External CI Injection

#### Image Version
**Repository `.gitlab-ci.yml` (SHA 1aa31e7)**:
```yaml
image: python:3.12-bookworm
```

**Effective Pipeline Execution**:
```yaml
image: python:3.12.14-bookworm  # Specific patch version
```

**Divergence**: Tag specificity changed from `3.12` to `3.12.14`

---

#### Dependency Sync Strategy
**Repository `.gitlab-ci.yml` (SHA 1aa31e7, line 53)**:
```yaml
.base_job:
  before_script:
    - uv sync --frozen
```

**Effective Pipeline Execution**:
```bash
uv sync --locked
```

**Divergence**: Sync mode changed from `--frozen` (lenient) to `--locked` (strict)

**Impact**: This exposed real lock drift (resolved in CI-LOCK-H1), but indicates external policy override

---

#### Gate Execution Method
**Repository `.gitlab-ci.yml` (SHA 1aa31e7, lines 58-80)**:
```yaml
static:
  script:
    - echo "=== STATIC Gate ==="
    - uv run --directory . ruff format --check plan/scripts/ src/
    - uv run --directory . ruff check plan/scripts/ src/
    - uv run --directory . mypy plan/scripts/ src/ ...
```

**Direct tool invocation**: ruff, mypy called explicitly

**Effective Pipeline Execution**:
```bash
uv run --locked python -B scripts/ci/run_gate.py static
uv run --locked python -B scripts/ci/run_gate.py schema_contract
uv run --locked python -B scripts/ci/run_gate.py secret_dependency
```

**Divergence**: All gates now require `scripts/ci/run_gate.py` wrapper, which doesn't exist in repository

---

## REPOSITORY STATE VERIFICATION

### Missing File Confirmed
**Path**: `scripts/ci/run_gate.py`  
**SHA**: 1aa31e7cdaff14e777210011c766badcd797b836  
**Status**: ❌ **404 FILE NOT FOUND**

**Verification**:
```bash
ls scripts/ci/
# Output: directory 'scripts/ci/' does not exist

ls scripts/
# Output:
# check_architecture.py
# check_changes.py
# check_governance.py
# check_postgres.py
# task_execution.py
```

**Conclusion**: `run_gate.py` never existed in this repository at any commit on `work/h2-convergence-closure`

---

### Related Files Search
**Search**: Documentation mentioning `run_gate`, `CI policy`, `compliance`, or `pipeline policy`

**Found**:
- V2-005 governance documents (not CI-related)
- No `run_gate.py` specification
- No ADR documenting `scripts/ci/run_gate.py` contract
- No `.gitlab-ci.yml` changes adding gate runner requirement

**Git History Search**:
```bash
git log --all --oneline --grep="run_gate"
# Output: (empty)

git log --all --oneline -- .gitlab-ci.yml | head -20
# Latest CI changes: V2-004 gate hardening, no run_gate.py introduction
```

**Conclusion**: `run_gate.py` was never part of repository governance or CI evolution

---

## POSSIBLE SOURCES OF EXTERNAL CI INJECTION

### 1. GitLab Project-Level CI/CD Settings
**Location**: GitLab UI → Project Settings → CI/CD

**Possible Mechanisms**:
- Custom CI/CD configuration path (override `.gitlab-ci.yml`)
- CI/CD variables forcing different behavior
- Protected branch pipeline rules

**Probability**: Low (would typically show in UI, not silently inject)

---

### 2. GitLab Group-Level Compliance Pipeline
**Location**: GitLab UI → Group Settings → CI/CD → Compliance pipelines

**Mechanism**: Group-level compliance policies can inject required jobs or override existing jobs

**Indicators**:
- Systematic changes (image version, sync strategy, gate runner)
- Affects all projects in group
- Not visible in repository

**Probability**: **High** — explains consistent pattern across multiple divergences

---

### 3. GitLab Instance-Level Security/Compliance Policies
**Location**: GitLab Admin → Security & Compliance

**Mechanism**: Instance-wide policies enforced by GitLab administrators

**Indicators**:
- Organization-wide standardization
- Cannot be disabled at project level
- Requires admin access to view/modify

**Probability**: Medium — depends on GitLab instance governance structure

---

### 4. External CI Pipeline Include
**Location**: `.gitlab-ci.yml` could reference external YAML

**Check**:
```yaml
# Current .gitlab-ci.yml (SHA 1aa31e7) does NOT contain:
include:
  - project: ...
  - remote: ...
  - template: ...
```

**Conclusion**: No external includes found

**Probability**: None — not present in repository

---

## SSOT GOVERNANCE DRIFT

### Current Lock Strategy Conflict

**Multiple Authoritative Sources**:

1. **Repository `.gitlab-ci.yml`**: `uv sync --frozen`
2. **Effective GitLab Pipeline**: `uv sync --locked` (enforced)
3. **README.md** (if exists): Unknown (not checked this session)
4. **ADR-001** (if exists): Unknown (file not found at expected path)

**Impact**: Documented behavior vs actual behavior divergence confuses contributors

---

## WHAT WE DON'T KNOW

### Critical Unknowns

1. **Authority Source**: Who/what injected the effective CI changes?
2. **Policy Intent**: Is `run_gate.py` a new organizational standard?
3. **Specification**: What should `run_gate.py` do? What's its contract?
4. **Scope**: Is this specific to this project, group, or instance-wide?
5. **Deployment Status**: Is this a partial rollout? Misconfiguration?

**Cannot Proceed Without**:
- Access to GitLab project/group/instance settings
- Communication with GitLab administrators or CI governance team
- Official specification for `scripts/ci/run_gate.py` contract

---

## WHAT WE DO KNOW

### Confirmed Facts

1. ✅ **CI-LOCK-H1 Succeeded**: `uv sync --locked` now works (verified by Pipeline #2912198356)
2. ✅ **Step 2-H1 Code Correct**: ResolutionResult types align with frozen contract
3. ✅ **Lock Consistency**: pip-audit and dependencies properly added to uv.lock
4. ❌ **Missing File**: `scripts/ci/run_gate.py` required but absent
5. ❌ **External Injection**: Effective CI diverges from repository `.gitlab-ci.yml`
6. ❌ **No Specification**: No discovered documentation for gate runner contract

---

## RESOLUTION PATHS (DECISION REQUIRED)

### Path A: Create Minimal Gate Runner (Not Recommended)
**Action**: Create `scripts/ci/run_gate.py` that delegates to existing tools

**Risks**:
- Guessing at undefined contract
- Adapting repository to unknown external policy
- May not match actual policy requirements
- Could mask deeper misconfiguration

**When Appropriate**: Only if confirmed that gate runner is official requirement and specification is provided

---

### Path B: Investigate External Policy Source (Recommended)
**Action**: Access GitLab settings to identify CI injection source

**Steps**:
1. Check GitLab project CI/CD settings for overrides
2. Check group-level compliance pipelines
3. Contact GitLab administrators for instance-level policies
4. Request official `run_gate.py` specification if it's required

**Benefits**:
- Addresses root cause
- Clarifies authoritative CI contract
- Avoids guessing at requirements
- Maintains SSOT principle

---

### Path C: Revert to Repository-Controlled CI
**Action**: Disable external CI injection, use only `.gitlab-ci.yml`

**Feasibility**: Depends on external policy authority (may not be possible)

**When Appropriate**: If external injection was misconfiguration or test deployment

---

## RECOMMENDED IMMEDIATE ACTIONS

1. **Access GitLab UI**: Check project/group CI/CD settings for compliance pipeline injection
2. **Contact Administrators**: Request clarification on effective CI policy source
3. **Request Specification**: If `run_gate.py` is official, obtain contract/requirements
4. **Document Findings**: Update this diagnosis with external policy source once identified
5. **Hold Implementation**: Do NOT proceed to V2-005 Step 3 until CI is unblocked

---

## CURRENT PROJECT STATE

```
Step 1: ✅ VERIFIED

Step 2-H1 Code: ✅ ACCEPTED
Step 2 Contract Conformance: ✅ PASS

CI-LOCK-H1 Lock Repair: ✅ ACCEPTED
CI-LOCK-H1 uv sync --locked: ✅ REMOTE VERIFIED

CI-POLICY-H1: ⚠️ BLOCKER IDENTIFIED
Missing: scripts/ci/run_gate.py (external policy requirement)

Step 2 Exact-SHA CI: ❌ FAILED_PRETEST
Blocker: Missing gate runner required by effective CI policy

Step 2 State: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED
Step 3: 🔒 BLOCKED
```

---

## GOVERNANCE PRINCIPLES VIOLATED

1. **SSOT Drift**: Repository `.gitlab-ci.yml` no longer reflects actual CI behavior
2. **Fail-Closed**: External changes introduced without repository knowledge
3. **Explicit Contract**: Gate runner required but not specified in repository governance
4. **No Speculative Fix**: Cannot guess at `run_gate.py` implementation without specification

---

## NEXT STEPS

**Immediate** (External):
- Access GitLab project settings
- Identify effective CI policy source
- Obtain `run_gate.py` specification (if required)

**After Clarification**:
- If misconfiguration: Disable external injection, retry CI
- If official policy: Implement `run_gate.py` per specification
- If rollout issue: Wait for complete deployment

**Not Recommended**:
- Blindly create `run_gate.py` without specification
- Proceed to Step 3 while CI is blocked
- Weaken gates to bypass gate runner requirement

---

## EVIDENCE FILES

**Committed to Repository**:
- ❌ None (CI-POLICY-H1 is diagnostic only, no code changes)

**Local Reports** (not pushed):
- docs/CI-LOCK-H1_FIX_REPORT.md
- docs/CI-POLICY-H1_DIAGNOSIS.md (this file)
- docs/V2-005_STEP_2_H1_FIX_REPORT.md
- [7 other local V2-005 reports]

**Remote Evidence**:
- Pipeline #2912198356 (FAILED, gate runner not found)
- SHA 1aa31e7 (lock fixed, gate runner missing)

---

## SUMMARY

**Operation**: CI-POLICY-H1 Effective CI Configuration Diagnosis  
**Result**: ⚠️ BLOCKER IDENTIFIED  
**Root Cause**: External CI policy injection requiring `scripts/ci/run_gate.py`  
**Missing File**: scripts/ci/run_gate.py (no specification found)  
**Resolution**: Requires external policy clarification

**CI-LOCK-H1**: ✅ COMPLETE (lock drift resolved)  
**Step 2**: ✅ CODE + CONTRACT VERIFIED / ❌ CI BLOCKED  
**Step 3**: 🔒 BLOCKED (CI must pass before proceeding)

**Critical Path**: Identify external CI policy source → Obtain gate runner specification → Implement or disable policy → Retry CI → Proceed to Step 3

---

**END OF CI-POLICY-H1 DIAGNOSIS**

**Status**: External policy investigation required  
**Date**: 2026-10-05  
**Blocked SHA**: 1aa31e7cdaff14e777210011c766badcd797b836  
**Blocker**: scripts/ci/run_gate.py not found
