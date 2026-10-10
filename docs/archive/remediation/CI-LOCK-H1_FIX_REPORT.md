# CI-LOCK-H1: DEPENDENCY LOCK DRIFT FIX REPORT

**Date**: 2026-10-05  
**Type**: Infrastructure / CI Governance Fix  
**Scope**: pyproject.toml / uv.lock synchronization

---

## EXECUTIVE SUMMARY

✅ **CI-LOCK-H1 FIX: COMPLETE AND PUSHED**

Dependency lock drift between pyproject.toml and uv.lock has been resolved. The lockfile now includes pip-audit and 25 transitive dependencies as specified in pyproject.toml dev-dependencies. CI pipeline failure at SHA 474c350 is now unblocked.

**Lock Fix SHA**: `1aa31e7cdaff14e777210011c766badcd797b836`  
**Push Status**: ✅ SUCCESS  
**Local Test**: `uv sync --locked` ✅ PASS  
**Awaiting**: Exact-SHA CI retry for 1aa31e7

---

## ISSUE IDENTIFICATION

### Pipeline Failure
**Failed SHA**: `474c350dab010309535ccb2f87b28a727d49e1d0`  
**Pipeline**: #2912172835  
**Result**: ❌ FAILED

**Failed Gates**:
- ❌ STATIC (uv sync --locked failed)
- ❌ SCHEMA_CONTRACT (uv sync --locked failed)
- ❌ SECRET_DEPENDENCY (uv sync --locked failed)
- ⏭️ UNIT (skipped due to upstream failure)
- ⏭️ ARCH_FITNESS (skipped due to upstream failure)
- ⏭️ POSTGRES_ENV (skipped due to upstream failure)

**Tests Executed**: 0 (environment preparation failed)

### Root Cause
**Error Message**:
```
uv sync --locked

Resolved 51 packages

error: The lockfile at `uv.lock` needs to be updated,
but `--locked` was provided.

hint: To update the lockfile, run `uv lock`.
```

**Cause**: `pyproject.toml` specifies `pip-audit>=2.6,<3` in dev-dependencies, but `uv.lock` did not include pip-audit or its 25 transitive dependencies.

---

## CI CONFIGURATION DRIFT DETECTED

### Repository vs Effective Pipeline Divergence

**Repository .gitlab-ci.yml** (SHA 474c350):
```yaml
.base_job:
  image: python:3.12-bookworm
  before_script:
    - uv sync --frozen
```

**Effective GitLab Pipeline** (actual execution):
```yaml
image: python:3.12.14-bookworm  # Specific patch version
before_script:
  - uv sync --locked  # Stricter mode
```

**Observation**: Effective CI configuration differs from repository .gitlab-ci.yml, indicating:
- Project/group-level pipeline execution policy, OR
- Compliance policy injection, OR
- GitLab governance override

**Impact**: Previous pipelines with `--frozen` passed by ignoring lock drift. Stricter `--locked` mode exposed real inconsistency.

---

## LOCK DRIFT ANALYSIS

### pyproject.toml State
```toml
[project.optional-dependencies]
dev = [
    "pip-audit>=2.6,<3",  # Present
    "jsonschema>=4.18,<5",
    "mypy>=1.13,<2",
    "psycopg>=3.2,<4",
    "pytest>=8.0,<9",
    "pyyaml>=6.0,<7",
    "ruff>=0.9,<1",
    "sqlalchemy>=2.1.1,<3",
    "types-pyyaml>=6.0,<7",
]
```

### uv.lock State (before fix)
**Missing**:
- pip-audit (primary package)
- 25 transitive dependencies

**Present**:
- Only 8 of 9 specified dev dependencies
- No pip-audit dependency tree

**Conclusion**: `pyproject.toml ≠ uv.lock` dependency model

---

## RESOLUTION

### Fix Execution
**Tool**: uv 0.12.17 (project-specified version)  
**Command**: `uv lock`  
**Result**: ✅ Resolved 51 packages in 6.65s

### Added Packages (26 total)
**Primary**:
- pip-audit v2.10.1

**Transitive Dependencies** (25):
- pip-api v0.0.35
- cyclonedx-python-lib v11.12.0
- rich v15.0.0
- requests v2.34.2
- certifi v2026.7.22
- charset-normalizer v3.5.2
- idna v3.20
- urllib3 v2.8.0
- markdown-it-py v4.2.0
- mdurl v0.1.2
- pip-requirements-parser v32.0.1
- license-expression v30.4.4
- packageurl-python v0.17.6
- py-serializable v2.1.0
- sortedcontainers v2.4.0
- boolean-py v5.0
- cachecontrol v0.14.4
- defusedxml v0.7.1
- filelock v4.0.11
- msgpack v1.2.3
- pip v26.2.1
- platformdirs v4.12.3
- pyparsing v3.3.3
- tomli v2.4.1
- tomli-w v1.2.0

**Total Package Count**: 51 (unchanged, pip-audit tree added)

### No Unrelated Upgrades
**Verification**: Only pip-audit dependency tree was added. No existing dependencies were upgraded or modified beyond necessary version resolutions.

---

## VERIFICATION

### Local Testing ✅

**uv lock**:
```
Resolved 51 packages in 15ms
```

**uv sync --locked**:
```
✅ SUCCESS
Installed 26 packages:
- pip-audit 2.10.1
- [25 transitive dependencies]
```

**Result**: Lock file now consistent with pyproject.toml

---

## COMMIT DETAILS

**Commit SHA**: `1aa31e7cdaff14e777210011c766badcd797b836`  
**Author**: 昂扬 <angyang@chinaums.com>  
**Message**: `fix(ci): update uv.lock to match pyproject.toml dev dependencies`

**Changes**:
```
1 file changed, 341 insertions(+)
M uv.lock
```

---

## PUSH RESULTS

**Push Target**: `origin/work/h2-convergence-closure`  
**Push Result**: ✅ SUCCESS

**Push Output**:
```
To https://gitlab.com/ayitnovel/ainovelos.git
   474c350..1aa31e7  work/h2-convergence-closure -> work/h2-convergence-closure
```

**Post-Push Verification**:
```
Local HEAD:  1aa31e7cdaff14e777210011c766badcd797b836 ✓
Remote HEAD: 1aa31e7cdaff14e777210011c766badcd797b836 ✓
```

---

## SSOT GOVERNANCE NOTE

### Current Lock Strategy Inconsistency

**ADR/Policy** (assumed authoritative based on effective CI):
- Requires: `uv sync --locked`

**Repository Documentation**:
- `.gitlab-ci.yml`: Documents `uv sync --frozen`
- `security-policy.yaml`: May also reference `--frozen`

**Effective CI**: Uses `uv sync --locked` (stricter)

**Recommendation**: Separate governance task to:
1. Confirm authoritative lock strategy (prefer `--locked` if ADR mandates it)
2. Update `.gitlab-ci.yml` documentation to match effective policy
3. Investigate and document CI configuration source (project/group policy)

**Rationale**: `--frozen` masks lock drift by working around it. `--locked` enforces lock correctness, which caught this real issue.

---

## IMPACT ON STEP 2

### Before CI-LOCK-H1
```
Step 2-H1 Code: ACCEPTED
Step 2 Contract Conformance: PASS
Step 2 Exact-SHA CI: FAILED_PRETEST (environment)
STEP_2_STATE: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED
STEP_3_MAY_BEGIN: NO
```

### After CI-LOCK-H1
```
Step 2-H1 Code: ACCEPTED
Step 2 Contract Conformance: PASS
Step 2 CI-LOCK-H1: COMPLETE
Step 2 Exact-SHA CI: PENDING_RETRY
STEP_2_STATE: IMPLEMENTED_CONTRACT_VERIFIED_AWAITING_CI
STEP_3_MAY_BEGIN: NO (awaiting CI)
```

---

## EXACT-SHA CI STATUS

**Required Pipeline SHA**: `1aa31e7cdaff14e777210011c766badcd797b836`  
**Pipeline Status**: ⏳ PENDING (awaiting trigger)

**Expected Results** (6 gates):
1. ✅ STATIC — expected PASS (lock fixed)
2. ✅ SCHEMA_CONTRACT — expected PASS (lock fixed)
3. ✅ UNIT — expected PASS (565/565)
4. ✅ ARCH_FITNESS — expected PASS (222/222)
5. ✅ POSTGRES_ENV — expected PASS
6. ✅ SECRET_DEPENDENCY — expected PASS (lock fixed)

**Expected Tests**: 565/565 PASS (unit 343, arch 222)

---

## STEP 2 FINAL ACCEPTANCE (AFTER CI SUCCESS)

**After CI-LOCK-H1 CI SUCCESS**:
```
V2-005 IMPLEMENTATION STEP 2: PASS
STEP_2_STATE: IMPLEMENTED_CI_VERIFIED
STEP_3_MAY_BEGIN: YES

NEXT_STEP: V2-005 IMPLEMENTATION — STEP 3: IMPLEMENT ID GENERATION AND NORMALIZATION
```

---

## LESSONS LEARNED

1. **Strict Lock Enforcement Value**: `--locked` caught real drift that `--frozen` masked

2. **CI Configuration Transparency**: Effective pipeline diverged from repository documentation without clear audit trail

3. **Lock Drift Detection**: Dev dependency addition in pyproject.toml without corresponding lock update went undetected in previous --frozen pipelines

4. **Governance Layer Separation**: Infrastructure fix (CI-LOCK-H1) correctly separated from domain implementation (V2-005 Step 2-H1)

---

## SUMMARY

**Operation**: CI-LOCK-H1 Dependency Lock Drift Fix  
**Result**: ✅ COMPLETE AND PUSHED  
**Lock Fix SHA**: 1aa31e7cdaff14e777210011c766badcd797b836  
**Push Status**: SUCCESS  
**Local Test**: uv sync --locked PASS  
**CI Status**: PENDING  

**Issue**: pyproject.toml / uv.lock inconsistency  
**Fix**: Added pip-audit 2.10.1 + 25 dependencies  
**Impact**: Unblocked Step 2 CI verification  

**Step 2 State**: IMPLEMENTED_CONTRACT_VERIFIED_AWAITING_CI  
**Next** (after CI): STEP 3 — ID GENERATION AND NORMALIZATION

---

**END OF CI-LOCK-H1 FIX REPORT**

**Status**: Lock drift resolved, awaiting exact-SHA CI  
**Date**: 2026-10-05  
**CI-LOCK-H1 SHA**: 1aa31e7cdaff14e777210011c766badcd797b836  
**Step 2-H1 SHA**: 474c350dab010309535ccb2f87b28a727d49e1d0
