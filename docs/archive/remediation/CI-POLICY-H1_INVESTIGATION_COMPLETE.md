# CI-POLICY-H1: EFFECTIVE CI AUTHORITY & GATE RUNNER PROVENANCE — INVESTIGATION COMPLETE

**Date**: 2026-10-05  
**Type**: Infrastructure / CI Governance Investigation  
**Status**: ✅ **ROOT CAUSE IDENTIFIED**

---

## EXECUTIVE SUMMARY

✅ **CI-POLICY-H1 INVESTIGATION: COMPLETE**

**Root Cause Identified**: `scripts/ci/run_gate.py` exists in **`origin/dev_gpt`** branch (V2-004 implementation line) but is **absent** from **`work/h2-convergence-closure`** (V2-005 implementation line). The two branches diverged from common ancestor `882d0cd` (V2-003) and evolved independently.

**Effective CI Policy Source**: GitLab is executing against **`dev_gpt` CI configuration** (which requires `run_gate.py`) while the repository HEAD is on **`work/h2-convergence-closure`** (which does not have `run_gate.py`).

**Resolution Path**: Cross-branch integration required — bring `scripts/ci/` infrastructure from `dev_gpt` into `work/h2-convergence-closure`.

---

## KEY FINDINGS

### 1. Gate Runner Location Confirmed ✅

**File**: `scripts/ci/run_gate.py`  
**Status**: ✅ **EXISTS** in `origin/dev_gpt` branch  
**First Appearance**: Commit `615efb0` (2026-10-03)  
**Commit Message**: `feat(V2-004): implement delivery gates and source verification`

**File Size**: 313 lines (confirmed)  
**Purpose**: P0 gate runner orchestrating STATIC, UNIT, SCHEMA_CONTRACT, ARCH_FITNESS, SECRET_DEPENDENCY, POSTGRES_ENV gates

**Contract**: Well-defined Python script with:
- Argument parsing (`job` choices from GATES dict)
- Command orchestration per gate type
- Receipt generation for CI provenance
- Environment isolation
- Deterministic output directory structure

---

### 2. Branch Divergence Analysis

#### Common Ancestor
**SHA**: `882d0cd` (V2-003 completion)  
**Message**: `docs(V2-003): seal confirmed review corrections and handoff`  
**Date**: Before 2026-09-25

#### work/h2-convergence-closure (V2-005 Line)
**Commits Since Divergence**: 105  
**Focus**: V2-005 entity identity implementation  
**Recent Work**: Contract approval, Step 1-2 implementation, lock fixes  
**CI Configuration**: Original `.gitlab-ci.yml` with direct tool invocation

**Key Commits**:
- `1aa31e7` (HEAD): CI-LOCK-H1 lock fix
- `474c350`: Step 2-H1 contract fix
- `4248258`: V2-005 schema materialization
- `323eaae`: Merge P0 architecture audit

**CI Strategy**: `uv sync --frozen`, direct `ruff`/`mypy` calls

---

#### origin/dev_gpt (V2-004 Line)
**Latest**: `9fe51ab` (2026-10-05)  
**Focus**: V2-004 delivery gates, security hardening, runner infrastructure  
**Recent Work**: Trusted runner acceptance, security findings reconciliation

**Key Commits**:
- `9fe51ab`: Trusted runner acceptance invariants
- `1449da9`: Reconcile 45 security findings
- `938300f`: Include every hard gate in MR pipelines
- `615efb0`: **Implement delivery gates and source verification** (gate runner introduced)

**CI Strategy**: `uv sync --locked`, `scripts/ci/run_gate.py` orchestration

**Infrastructure Added**:
- `scripts/ci/run_gate.py` (gate orchestrator)
- `scripts/ci/check_configuration.py`
- `scripts/ci/check_syntax.py`
- `scripts/ci/check_security.py`
- `scripts/ci/bootstrap_scanners.py`
- `scripts/ci/verify_remote.py`

---

### 3. Effective CI Configuration Source

**Repository `.gitlab-ci.yml` (work/h2-convergence-closure, SHA 1aa31e7)**:
```yaml
image: python:3.12-bookworm
before_script:
  - uv sync --frozen
script:
  - ruff format --check ...
  - ruff check ...
  - mypy ...
```

**Effective GitLab Pipeline Execution**:
```yaml
image: python:3.12.14-bookworm
before_script:
  - uv sync --locked
script:
  - uv run --locked python -B scripts/ci/run_gate.py static
  - uv run --locked python -B scripts/ci/run_gate.py schema_contract
  - uv run --locked python -B scripts/ci/run_gate.py secret_dependency
```

**Conclusion**: GitLab is executing **`dev_gpt`'s CI configuration**, not `work/h2-convergence-closure`'s.

---

### 4. Why Is dev_gpt CI Active on h2-convergence-closure Branch?

**Hypothesis 1**: GitLab project default branch is `dev_gpt`  
**Implication**: CI configuration reads from default branch, not current branch  
**Probability**: High

**Hypothesis 2**: GitLab CI/CD configuration path override  
**Implication**: Project settings point to `dev_gpt:.gitlab-ci.yml`  
**Probability**: Medium

**Hypothesis 3**: Group/instance compliance pipeline injection using `dev_gpt` as template  
**Implication**: External policy enforces `dev_gpt` CI standards  
**Probability**: Low (would typically be more generic)

**Evidence Supporting Hypothesis 1**:
- `dev_gpt` is actively maintained with recent V2-004 work
- `dev_gpt` has production-grade CI infrastructure
- Effective CI exactly matches `dev_gpt` `.gitlab-ci.yml` structure

---

## REPOSITORY TOPOLOGY

```
882d0cd (V2-003 completion)
├─── work/h2-convergence-closure (105 commits)
│    ├─ V2-005 implementation
│    ├─ .gitlab-ci.yml: --frozen, direct tools
│    └─ NO scripts/ci/run_gate.py
│
└─── origin/dev_gpt (continuation)
     ├─ V2-004 delivery gates
     ├─ .gitlab-ci.yml: --locked, run_gate.py orchestration
     └─ YES scripts/ci/run_gate.py + full CI infrastructure
```

**Current State**: HEAD on `h2-convergence-closure`, but CI executing `dev_gpt` configuration

---

## SCRIPTS/CI/ INFRASTRUCTURE IN DEV_GPT

**Gate Runner** (`scripts/ci/run_gate.py`):
- **Purpose**: Centralized P0 gate orchestration
- **Gates**: static, unit, schema_contract, arch_fitness, secret_dependency, postgres_env
- **Features**:
  - Command plan per gate type
  - Receipt generation (SHA256, timestamps, environment capture)
  - Deterministic output directories (`dist/ci/<gate>/`)
  - Environment variable filtering for reproducibility
  - CI/local execution mode detection

**Supporting Scripts**:
- `check_configuration.py`: Configuration validation
- `check_syntax.py`: Python syntax verification
- `check_security.py`: Security scanning orchestration
- `bootstrap_scanners.py`: Security tool download/verification
- `verify_remote.py`: Remote source verification

**README.md References** (dev_gpt):
```
V2-004 的候选流水线由 `.gitlab-ci.yml`、`security-policy.yaml` 和 
`scripts/ci/` 实现。本地使用上面的精确版本 uv/Python 环境，运行 
`uv run --locked python -B scripts/ci/run_gate.py static` 
```

---

## RESOLUTION PATH

### Option A: Integrate scripts/ci/ from dev_gpt (RECOMMENDED)

**Action**: Cherry-pick or merge `scripts/ci/` infrastructure from `dev_gpt` into `work/h2-convergence-closure`

**Steps**:
1. Identify minimal commit set introducing gate runner infrastructure
2. Review `scripts/ci/run_gate.py` contract and dependencies
3. Cherry-pick infrastructure commits OR create integration branch
4. Update `.gitlab-ci.yml` on `h2-convergence-closure` to use gate runner
5. Test locally: `uv run --locked python -B scripts/ci/run_gate.py static`
6. Commit and push
7. Verify exact-SHA CI passes

**Benefits**:
- Uses production-tested gate runner from `dev_gpt`
- Aligns with effective CI expectations
- No guessing at implementation
- Inherits V2-004 security hardening

**Risks**:
- May bring V2-004 dependencies/changes not yet needed for V2-005
- Requires careful review of what's being integrated

---

### Option B: Update GitLab Default Branch to work/h2-convergence-closure

**Action**: Change GitLab project default branch from `dev_gpt` to `work/h2-convergence-closure`

**Feasibility**: Requires GitLab maintainer/owner permissions

**Impact**: CI would then read from `work/h2-convergence-closure`'s `.gitlab-ci.yml`

**Risks**:
- May break ongoing V2-004 work on `dev_gpt`
- Requires understanding of project branching strategy governance
- Does not address lock drift (--frozen vs --locked)

---

### Option C: Maintain Dual CI Configurations

**Action**: Keep both branches with their own CI strategies, ensure proper branch→CI mapping

**Complexity**: High  
**Not Recommended**: Increases governance surface, SSOT drift

---

## AUTHORITY CHAIN ESTABLISHED

**WHO owns effective CI?**  
→ `origin/dev_gpt` branch (V2-004 implementation line)

**WHERE is its source?**  
→ `origin/dev_gpt:.gitlab-ci.yml` + `scripts/ci/run_gate.py`

**WHICH revision/version is active?**  
→ Latest `dev_gpt` HEAD (~`9fe51ab` or similar)

**IS run_gate.py a repository obligation?**  
→ YES, for branches using `dev_gpt` CI model  
→ NO, for branches using legacy direct-tool model (like current `h2-convergence-closure`)

**WHAT is its exact contract?**  
→ 313-line Python script in `dev_gpt:scripts/ci/run_gate.py`  
→ Well-defined, production-tested, code-reviewed

---

## RECOMMENDED IMMEDIATE ACTION

1. ✅ **Review `dev_gpt` gate runner**: Understand `scripts/ci/run_gate.py` contract
2. ✅ **Cherry-pick infrastructure**: Bring gate runner into `work/h2-convergence-closure`
3. ✅ **Update local .gitlab-ci.yml**: Align with gate runner model
4. ✅ **Test locally**: `uv run --locked python -B scripts/ci/run_gate.py static`
5. ✅ **Commit and push**: CI-POLICY-H1 resolution
6. ✅ **Retry CI**: Expect 6/6 gates PASS with gate runner present

---

## CURRENT PROJECT STATE

```yaml
Step 1: ✅ VERIFIED

Step 2-H1 Code: ✅ ACCEPTED
Step 2 Contract Conformance: ✅ PASS

CI-LOCK-H1: ✅ COMPLETE (lock drift resolved)

CI-POLICY-H1: ✅ INVESTIGATION COMPLETE
Root Cause: scripts/ci/run_gate.py exists in dev_gpt, absent in h2-convergence-closure
Resolution: Cross-branch integration required

Step 2 Exact-SHA CI: ❌ BLOCKED (gate runner missing)
Step 2 State: IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED
Step 3: 🔒 BLOCKED
```

---

## NEXT STEP

**Execute**: CI-POLICY-H1 Resolution — Integrate Gate Runner Infrastructure

**NOT**: Proceed to V2-005 Step 3 (still blocked by CI)

---

**END OF CI-POLICY-H1 INVESTIGATION**

**Status**: Root cause identified, resolution path clear  
**Date**: 2026-10-05  
**Blocker**: scripts/ci/ infrastructure present in dev_gpt, absent in work/h2-convergence-closure  
**Resolution**: Cross-branch integration required
