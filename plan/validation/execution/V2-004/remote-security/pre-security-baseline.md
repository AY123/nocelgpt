---
type: BASELINE_SNAPSHOT
phase: PRE_SECURITY_HARDENING
captured: 2026-09-28T12:45:00+08:00
purpose: Record initial state before AT-07/08 GitLab security configuration
---

# Pre-Security Baseline Snapshot

## Repository State

**Project**: ayitnovel/ainovelos  
**GitLab URL**: https://gitlab.com/ayitnovel/ainovelos  
**Baseline Commit**: `eb6da67bfdaf377882c9d8331e44470d1020fce8`  
**Pipeline**: #37 (ID: 2888110854)  
**Pipeline Status**: ✅ SUCCESS (6/6 P0 jobs PASS)  
**Commit Subject**: fix(V2-004): reconcile active execution context after truth-state restore  
**Commit Author**: 昂扬 <angyang@chinaums.com>  
**Commit Date**: 2026-09-28 12:26:51 +0800  

## Branch State

**Current Branch**: `dev_cc`  
- Tracking: `origin/dev_cc`  
- HEAD: `eb6da67`  
- Status: Clean working tree

**Main Branch**: `main`  
- HEAD: `882d0cd`  
- Subject: docs(V2-003): seal confirmed review corrections and handoff

## GitLab Protection Status (Pre-Hardening)

### Branch Protection

**main**:  
- Status: **PROTECTED** ✅  
- Protection details: (to be queried via GitLab API)

**dev_cc**:  
- Status: **NOT PROTECTED** ⚠️  
- Current risk: Direct push allowed, no merge gate

### Project-Level Merge Checks

**Pipelines must succeed**:  
- Status: **DISABLED** ⚠️  
- Current behavior: MRs can be merged without CI success

### Current Identity

**Git User**: 昂扬  
**Git Email**: angyang@chinaums.com  
**GitLab Role**: Owner  
**Access Level**: 50 (group_access.access_level = 50)

## P0 CI Baseline (6 Gates)

All gates passing at commit `eb6da67`:

1. **STATIC**: ✅ PASS  
2. **SCHEMA_CONTRACT**: ✅ PASS (0 errors, all constraints satisfied)  
3. **UNIT**: ✅ PASS (330 passed, 0 failed)  
4. **ARCH_FITNESS**: ✅ PASS  
5. **POSTGRES_ENV**: ✅ PASS  
6. **SECRET_DEPENDENCY**: ✅ PASS  

**test_plan_governance.py**: 15 passed  

## Truth-State Verification

V2-001: CLOSED ✅  
V2-002: CLOSED ✅  
V2-003: CLOSED ✅  
V2-004: **IMPLEMENTED** ⚠️ (waiting for AT-07/08 verification)  

AT-V2-004: IMPLEMENTED  
AT-V2-004-07: **BLOCKED** (needs GitLab restricted identity)  
AT-V2-004-08: **BLOCKED** (needs protected branch + mandatory pipeline)  

## Critical Observations

1. **No MR rules in .gitlab-ci.yml**: Must verify CI attaches to MRs before enabling merge checks
2. **dev_cc unprotected**: Real development happens here; must be protected for AT-08
3. **No merge gate**: Current identity can directly push to dev_cc and bypass any review
4. **Pipeline #37 is authentic**: No validator weakening, no fake closures, no test deletions

## Next Steps (As Per AT-07/08 Plan)

1. ✅ Baseline recorded (this document)
2. ⏳ Create Developer-level implementation identity
3. ⏳ Protect dev_cc branch (No one can push, Maintainers can merge)
4. ⏳ Verify CI runs on MR (prerequisite for step 5)
5. ⏳ Enable "Pipelines must succeed"
6. ⏳ Execute AT-07 verification (boundary testing)
7. ⏳ Execute AT-08 self-weakening attack test
8. ⏳ Execute AT-08 legitimate control MR
9. ⏳ Collect evidence and close AT-07/08

## Evidence Requirements

For each GitLab operation test, capture:
- HTTP status codes / API responses
- Git push rejection messages
- MR state and merge blocking reasons
- Identity/role information at time of operation
- GitLab audit log entries (if accessible)

---

**Baseline Integrity**: This snapshot represents the last known-good state before security hardening.  
Any GitLab configuration changes after this point are part of AT-07/08 implementation.
