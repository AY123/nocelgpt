# V2-004 PREPARE Phase Complete
## Design Summary and IMPLEMENT Readiness

**Date:** 2026-09-25  
**Phase:** PREPARE → Ready for IMPLEMENT  
**Execution Packet:** ✅ CREATED

---

## PREPARE Phase Accomplishments

### 1. Repository Baseline Established ✅

```
Branch: dev_cc
HEAD: 73e029b353034727540047a8c08bf120cd2e80f1
Worktree: Clean (except expected V2-003.2 artifacts)
V2-004 Status: OPEN → ready for IN_PROGRESS
```

### 2. Execution Packet Created ✅

**Location:** `plan/validation/execution/V2-004/execution-packet.yaml`

**Key Bindings:**
- Task: V2-004
- Plan Version: 1.3.0
- Repository Revision: 73e029b353034727540047a8c08bf120cd2e80f1
- Action: IMPLEMENT
- Owner: delivery-maintainer

**Inputs (11 files with SHA256):**
- implementation-backlog.yaml
- ci-gates.yaml
- test-catalog.yaml
- Normative specs (4 files)
- Evidence schemas (2 files)
- PostgreSQL test
- uv.lock

**Scope:** P0 CI gates only, no weakening, typed evidence

### 3. GitLab Remote Verified ✅

```
Remote: https://gitlab.com/ayitnovel/ainovelos.git
Project: ayitnovel/ainovelos
Branch: dev_cc (will push here)
```

### 4. CI Design Completed ✅

**P0 Gates to Implement:**
1. **STATIC** - format/lint/typecheck (minimal, if tooling exists)
2. **UNIT** - tests/architecture + tests/contract
3. **SCHEMA_CONTRACT** - plan validation, governance
4. **ARCH_FITNESS** - architecture positive + negative fixtures
5. **SECRET_DEPENDENCY** - secret scan + dependency scan
6. **POSTGRES_ENV** - real PostgreSQL connection

**All gates:** `allow_failure: false`

**Future gates (must NOT implement):**
- CANON_CAS_IDEMPOTENCY (P2)
- DETERMINISTIC_E2E (P7)
- GENRE_SMOKE (P8)
- LIVE_PROVIDER (P10)

### 5. Test Design Completed ✅

**Will create:** `tests/contract/test_delivery_gates.py`

**Test coverage:**
- P0 gates exist and cannot allow_failure
- Future gates not falsely activated
- Secret negative fixture blocks
- Dependency negative fixture blocks
- Wrong revision CI evidence rejected
- Local forged CI rejected
- Failed/canceled pipeline rejected
- Current trusted CI positive path (if available)

---

## Implementation Plan

### Phase A: Local Implementation

**Files to create/modify:**

1. **`.gitlab-ci.yml`** - Main CI configuration
   - Variables, stages, before_script
   - STATIC job (if tooling available)
   - UNIT job
   - SCHEMA_CONTRACT job
   - ARCH_FITNESS job
   - SECRET_DEPENDENCY job
   - POSTGRES_ENV job (with service: postgres:17.0)
   - Artifact collection

2. **`tests/contract/test_delivery_gates.py`** - Contract tests
   - Validate ci-gates.yaml structure
   - Verify P0 gates have allow_failure: false
   - Verify future gates remain NOT_IMPLEMENTED
   - Negative fixture tests
   - Provenance verification tests (structure)

3. **Update `plan/machine/ci-gates.yaml`** (only status updates)
   - Change applicable gates from NOT_IMPLEMENTED to IMPLEMENTED
   - Add evidence_refs after CI execution

4. **Update `plan/machine/test-catalog.yaml`**
   - AT-V2-004 status: PLANNED → IMPLEMENTED

### Phase B: Local Validation

**Must execute before push:**
```bash
# Run new tests
pytest tests/contract/test_delivery_gates.py -v

# Run full test suite
pytest tests/architecture/ tests/contract/ -v

# Run plan validation
python -m plan.scripts.validate_plan --check

# Run governance tests
pytest tests/contract/test_plan_governance.py -v
```

**Expected:** All tests PASS, no regressions

### Phase C: Remote CI Execution

**After local validation:**
1. Commit implementation
2. Push to dev_cc
3. **Wait for GitLab pipeline execution**
4. **Verify pipeline ran on correct commit SHA**
5. Obtain pipeline/job/artifact provenance

### Phase D: Evidence Binding

**Only after real CI execution:**
1. Verify provenance (project, commit, pipeline, jobs, artifacts)
2. Create typed evidence records:
   - CODE evidence
   - TEST_RESULT evidence
   - **CI_RUN evidence** (only if CI executed)
3. Update ci-gates.yaml with evidence_refs
4. Update V2-004 status to IMPLEMENTED (or VERIFIED if full evidence)

---

## Design Decisions

### STATIC Gate Implementation

**Decision:** Minimal or skip if no existing tooling

**Rationale:**
- pyproject.toml has no ruff/mypy/black dependencies
- V2-003 did not establish static analysis baseline
- Adding large tooling in V2-004 would expand scope
- Can implement as "check for Python syntax errors" minimally

**Recommendation:** Implement minimal Python syntax check, document as future enhancement

### Secret Scanning

**Tool:** Use `gitleaks` or similar in CI (to be determined based on GitLab runner)

**Fixtures:** Create harmless test secrets in `tests/fixtures/secrets/`
- Format: `ANOVELOS_TEST_FAKE_KEY=obviously_fake_value_for_testing`
- Must be obviously invalid
- Must trigger scanner
- Must not be real credentials

### Dependency Scanning

**Approach:** Check `uv.lock` integrity and known vulnerabilities

**Tool:** Use `pip-audit` or `safety` if available in CI

**Negative fixture:** Temporarily introduce known-vulnerable dummy package spec (not in uv.lock)

### PostgreSQL Service

**Configuration:**
```yaml
services:
  - name: postgres:17.0
    alias: postgres
variables:
  POSTGRES_DB: bootstrap_test
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: (generate in CI)
  ANOVELOS_TEST_DSN: postgresql://postgres:...@postgres:5432/bootstrap_test
```

**Test:** Run existing `tests/integration/test_postgres_environment.py` subset

### Artifacts

**Structure:**
```
dist/ci/
├── validation/
├── tests/
├── security/
├── postgres/
└── provenance/
```

**All in `.gitignore` (dist/ already ignored)**

---

## Risk Assessment

### Low Risk ✅

- Local test execution
- CI configuration syntax
- Existing PostgreSQL test reuse
- Locked dependency usage

### Medium Risk ⚠️

- GitLab runner availability (unknown until push)
- Secret scanner availability/configuration
- Dependency scanner network access
- PostgreSQL service startup timing

### Mitigations

- Test locally before push
- Use official GitLab images
- Implement retries for service startup
- Document scanner unavailability as NOT_VERIFIED if needed

---

## Constraints Acknowledged

### Must NOT Do

- ❌ Implement P2+ gates
- ❌ Weaken existing tests/gates/thresholds
- ❌ Use real secrets in fixtures
- ❌ Make destructive remote permission tests
- ❌ Claim VERIFIED without real CI evidence
- ❌ Use Markdown as evidence records
- ❌ Modify V2-001/002/003 architecture

### Must Do

- ✅ Use `uv sync --frozen`
- ✅ Set `allow_failure: false` for P0 gates
- ✅ Generate machine-verifiable artifacts
- ✅ Bind evidence to actual tested revision
- ✅ Verify provenance or mark NOT_VERIFIED
- ✅ Use typed evidence records

---

## V2-003.2 Transferred Gaps

### F-001: PREPARE E2E Integration

**Status:** Will address if feasible

**Approach:** Create PREPARE-specific execution fixture in V2-004 tests

**If infeasible:** Document as transferred gap with clear limitation

### F-002: Authorization Chain E2E

**Status:** Will address if feasible

**Approach:** Test full `apply_dispositions()` chain with AUTHORIZATION_REQUIRED

**If infeasible:** Document as transferred gap with clear limitation

---

## IMPLEMENT Phase Readiness

### Prerequisites ✅

- ✅ Repository baseline established
- ✅ Execution packet created and bound
- ✅ Normative specs read and understood
- ✅ CI design completed
- ✅ Test design completed
- ✅ Scope frozen in execution packet
- ✅ Stop conditions identified

### Next Steps

1. **Enter IMPLEMENT phase**
2. Create `.gitlab-ci.yml`
3. Create `tests/contract/test_delivery_gates.py`
4. Update ci-gates.yaml (status only)
5. Update test-catalog.yaml (status only)
6. Run local validation
7. Commit and push
8. Obtain real CI evidence
9. Bind typed evidence
10. Update V2-004 status

---

## Approval Request

**PREPARE phase complete. Ready to proceed to IMPLEMENT?**

**Scope:** As defined in execution packet
**Risk:** Medium (GitLab runner/scanner availability unknown)
**Estimated effort:** Full implementation session
**Breaking:** No existing functionality

**If approved, will proceed to IMPLEMENT phase with zero repository mutations until approval.**

---

**PREPARE Status:** ✅ COMPLETE  
**Execution Packet:** ✅ VALID  
**Ready for:** IMPLEMENT

