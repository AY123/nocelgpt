---
type: ACCEPTANCE_TEST_EVIDENCE
test_ids: AT-V2-004-07, AT-V2-004-08
status: VERIFIED
completed: 2026-09-28T17:41:00+08:00
---

# AT-07/08 Complete Evidence Package

## Executive Summary

✅ **AT-V2-004-07**: GitLab权限隔离验证 - **PASS**  
✅ **AT-V2-004-08**: 远程保护与自削弱防御验证 - **PASS**  

**Key Finding**: GitLab role-based access control + protected branches + mandatory pipeline checks provide multi-layer defense against self-weakening attacks.

---

## AT-07: Permission Boundary Verification

### Test Identity
- **Username**: TomAy47287015
- **Role**: Developer (inherited from ayitnovel group)
- **Access Level**: 30
- **Project**: ayitnovel/ainovelos (ID: 86656946)

### Positive Tests (Authorized Operations)

| Test | Operation | Result | Evidence |
|------|-----------|--------|----------|
| 1 | Read user via API | ✅ PASS | HTTP 200, user ID 2897322 |
| 2 | Read project via API | ✅ PASS | HTTP 200, project ID 86656946 |
| 3 | Verify membership | ✅ PASS | access_level=30 confirmed |
| 4 | Clone repository | ✅ PASS | Successful clone via HTTPS OAuth2 |
| 5 | Push to feature branch | ✅ PASS | Branch work/at07-boundary-test created, commit 18a1c7c |

### Negative Tests (Unauthorized Operations - Should Fail)

| Test | Operation | Result | Evidence |
|------|-----------|--------|----------|
| 6 | Create protected branch | ✅ REJECTED | HTTP 403 Forbidden |
| 7 | Modify project merge checks | ✅ REJECTED | HTTP 403 Forbidden |
| 8 | Direct push to protected main | ✅ REJECTED | Git pre-receive hook declined |

**AT-07 Conclusion**: Developer identity has clear operational boundaries enforced by GitLab RBAC.

---

## AT-08: Remote Protection & Self-Weakening Defense

### Phase 1: Protection Configuration

**dev_cc Branch Protection** (Applied: 2026-09-28T15:47:00):
- Push access: **No one** (access_level=0)
- Merge access: **Maintainers** (access_level=40)
- Allow force push: **false**
- Evidence: GitLab API response, branch now appears in protected branches list

**Pipelines Must Succeed** (Enabled: 2026-09-28T15:47:30):
- Setting: `only_allow_merge_if_pipeline_succeeds=true`
- Effect: MR cannot be merged without successful pipeline
- Evidence: GitLab project settings API

### Phase 2: MR Pipeline Support

**Implementation**: `.gitlab-ci.yml` workflow.rules added  
**Commits**: 931069e, 9471543  
**Branch**: work/at08-enable-mr-pipeline  
**MR**: !2 (merged to dev_cc, merge commit 7a4d2d0)

**Verification**:
- Branch pipeline: #2888486768 (source=push, 6/6 PASS)
- MR pipeline: #2888503623 (source=merge_request_event, 6/6 PASS)
- Duplicate suppression: #2888520064 (only MR pipeline, no duplicate branch pipeline)

### Phase 3: Developer Boundary Re-verification

**Test**: Direct push to protected dev_cc  
**Commit**: 3b6467f (local only, never reached remote)  
**Result**: ✅ REJECTED  
**Evidence**: 
```
remote: GitLab: You are not allowed to push code to protected branches on this project.
! [remote rejected] dev_cc -> dev_cc (pre-receive hook declined)
```

### Phase 4: Adversarial Self-Weakening Attack (Negative Test)

**MR**: !3 (work/at08-weakening-attack → dev_cc)  
**Web URL**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/3  
**Commits**: 85fcaec, b8206b9  
**Modification**: Added `_weakened_validator_bypass()` to `plan/scripts/validate_plan.py`

**Attack Intent**: Weaken governance validator to bypass phase state validation

**Defense Layers**:

1. **Layer 1: CI Gates**
   - Pipeline: #2888811314
   - Status: **FAILED**
   - STATIC: failed
   - SCHEMA_CONTRACT: failed
   - Other gates: skipped (fast-fail)
   - **Result**: ❌ Malicious code rejected by quality gates

2. **Layer 2: Role-Based Access Control**
   - Developer `can_merge`: **false**
   - **Result**: ❌ Even if CI passed, Developer cannot self-merge

3. **Layer 3: Pipeline Gate**
   - `detailed_merge_status`: `ci_must_pass`
   - **Result**: ❌ Failed pipeline blocks merge button

**Evidence**: All three layers independently blocked the attack.

### Phase 5: Legitimate Control Case (Positive Test)

**MR**: !4 (work/at08-legitimate-control → dev_cc)  
**Web URL**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/4  
**Commit**: e4cfaa8  
**Change**: Added AT08_LEGITIMATE_CONTROL.md (documentation, non-functional)

**Pipeline**: #2888922730  
**Status**: **SUCCESS**  
**Jobs**: 6/6 PASS
- STATIC: success
- SCHEMA_CONTRACT: success
- UNIT: success
- ARCH_FITNESS: success
- POSTGRES_ENV: success
- SECRET_DEPENDENCY: success

**Merge Permissions (Developer)**:
- `can_merge`: **false**
- `detailed_merge_status`: `mergeable`
- `merge_status`: `can_be_merged`
- **Result**: ✅ CI passes, but Developer still cannot self-merge

**Governance Approval**:
- Owner reviewed green pipeline
- Owner executed merge (merge commit 3ddd1d4)
- **Result**: ✅ Legitimate change merged through proper governance channel

---

## Multi-Layer Defense Summary

| Attack Vector | Defense Layer 1 (CI) | Defense Layer 2 (RBAC) | Defense Layer 3 (Pipeline Gate) | Outcome |
|---------------|----------------------|------------------------|----------------------------------|---------|
| Self-weakening validator | ❌ STATIC/SCHEMA fail | ❌ Developer can't merge | ❌ ci_must_pass blocks | ✅ BLOCKED |
| Legitimate change | ✅ All gates pass | ❌ Developer can't merge | ✅ Pipeline success | ✅ Requires governance approval |

**Key Insight**: Even if an attacker bypasses Layer 1 (CI gates), Layer 2 (RBAC) independently prevents self-merge.

---

## Evidence Artifacts

### GitLab Resources
- **Protected Branches**: https://gitlab.com/ayitnovel/ainovelos/-/settings/repository#js-protected-branches-settings
- **Merge Request Settings**: https://gitlab.com/ayitnovel/ainovelos/-/settings/merge_requests
- **MR !1**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/1 (initial test, no pipeline)
- **MR !2**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/2 (MR pipeline enablement, merged)
- **MR !3**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/3 (adversarial attack, blocked)
- **MR !4**: https://gitlab.com/ayitnovel/ainovelos/-/merge_requests/4 (legitimate control, merged)

### Pipelines
- **#2888486768**: Branch pipeline, work/at08-enable-mr-pipeline, 6/6 PASS
- **#2888503623**: MR pipeline (!2), merge_request_event, 6/6 PASS
- **#2888520064**: MR pipeline (!2 update), no duplicate, 6/6 PASS
- **#2888811314**: MR pipeline (!3 adversarial), FAILED (static + schema_contract)
- **#2888922730**: MR pipeline (!4 legitimate), 6/6 PASS

### Local Files
- `plan/acceptance/AT-V2-004/pre-security-baseline.md`: Pre-hardening snapshot
- `plan/acceptance/AT-V2-004/at07-test-log.md`: AT-07 detailed test log
- `plan/acceptance/AT-V2-004/mr-pipeline-implementation-report.md`: MR pipeline verification
- `plan/acceptance/AT-V2-004/at07-08-evidence.md`: This document

---

## Acceptance Criteria Verification

### AT-V2-004-07 Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Developer can clone, read, push feature branches | ✅ PASS | Tests 1-5 all successful |
| Developer cannot modify protected branch settings | ✅ PASS | HTTP 403 on API call |
| Developer cannot modify project merge checks | ✅ PASS | HTTP 403 on API call |
| Developer cannot direct push to protected branches | ✅ PASS | Git pre-receive hook rejection |

### AT-V2-004-08 Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| dev_cc protected with proper access levels | ✅ PASS | GitLab API confirms protection |
| "Pipelines must succeed" enabled | ✅ PASS | Project setting enabled |
| MR pipelines trigger correctly | ✅ PASS | 3/3 MR pipelines used merge_request_event source |
| Self-weakening attack blocked | ✅ PASS | MR !3 blocked by 3 independent layers |
| Legitimate flow works with governance | ✅ PASS | MR !4 green pipeline, Owner merged |
| No same-commit self-weakening bypass | ✅ PASS | Developer cannot merge own changes to protected branch |

---

## Final Status

**AT-V2-004-07**: ✅ **VERIFIED**  
**AT-V2-004-08**: ✅ **VERIFIED**  
**V2-004**: IMPLEMENTED → **VERIFIED** (ready for closure)  
**P0**: NOT_VERIFIED → Ready for final phase decision  

**Next Steps**:
1. Update V2-004 status to CLOSED
2. Create P0 PHASE_DECISION
3. Create M0 MILESTONE_DECISION
4. Verify G-P0 satisfied
5. Proceed to V2-005

---

**Evidence compiled**: 2026-09-28T17:41:00+08:00  
**Verified by**: Claude Opus 4.8 + 昂扬 (Owner)  
**Test environment**: GitLab.com, ayitnovel/ainovelos, commit 3ddd1d4 (dev_cc HEAD)
