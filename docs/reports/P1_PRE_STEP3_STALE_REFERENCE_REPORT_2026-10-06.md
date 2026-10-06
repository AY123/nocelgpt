# P1-PRE-STEP3-HOUSEKEEPING-001: Stale Reference Report
**Document ID**: P1-PRE-STEP3-STALE-REFERENCE-REPORT  
**Date**: 2026-10-06  
**Baseline**: work/h2-convergence-closure @ be6e475b

---

## 1. Stale Repository URL References

### 1.1 Old Repository URL
```
OLD: https://gitlab.com/ayitnovel/ainovelos
NEW: https://gitlab.com/angyang/ainovel
```

### 1.2 Reference Classification Matrix

| File | Reference Count | Classification | Action |
|------|----------------|----------------|---------|
| V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md | 3 | HISTORICAL_VALID | PRESERVE |
| plan/validation/closure/G-P0-38b0c57/ci/*.yaml | 6 | HISTORICAL_VALID | PRESERVE |
| plan/validation/execution/V2-004/remote-security/*.md | 5+ | HISTORICAL_VALID | PRESERVE |
| plan/validation/execution/V2-004/closure/ci/*.yaml | 2 | HISTORICAL_VALID | PRESERVE |
| plan/validation/execution/V2-001/closure/ci/*.yaml | 1 | HISTORICAL_VALID | PRESERVE |
| plan/validation/execution/V2-004/ci/*.yaml | 1 | HISTORICAL_VALID | PRESERVE |

**Total Old Repository References**: 20+

### 1.3 Reference Analysis

**Example from V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md**:
```markdown
| 仓库 | https://gitlab.com/ayitnovel/ainovelos |
- [H1→H2 比较](https://gitlab.com/ayitnovel/ainovelos/-/compare/...)
- [H2 提交](https://gitlab.com/ayitnovel/ainovelos/-/commit/e00b035...)
[Pipeline 2910274247](https://gitlab.com/ayitnovel/ainovelos/-/pipelines/2910274247)
```

**Analysis**: These URLs point to actual historical pipelines that ran in the old repository. The URLs are factually correct.

**Example from plan/validation/closure/G-P0-38b0c57/ci/ci-static.yaml**:
```yaml
pipeline_url: https://gitlab.com/ayitnovel/ainovelos/-/pipelines/2906152868
```

**Analysis**: This is immutable evidence of an actual CI run. The URL is historically accurate.

---

## 2. Reference Type Classification

### 2.1 HISTORICAL_VALID References (DO NOT MODIFY)

These references document actual events that occurred in the old repository:

**Category**: CI Pipeline Evidence
```
Files: plan/validation/*/ci/*.yaml
Pattern: pipeline_url: https://gitlab.com/ayitnovel/ainovelos/-/pipelines/NNNN
Count: 15+
Rationale: These pipelines actually ran in ayitnovel/ainovelos
Action: PRESERVE - modifying would falsify historical record
```

**Category**: Historical Review Documents
```
Files: V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md, docs/*REPORT.md
Pattern: Links to commits, comparisons, pipelines in ayitnovel/ainovelos
Count: 5+
Rationale: These documents reviewed work performed in old repository
Action: PRESERVE - accurate historical documentation
```

**Category**: Security Baseline Documentation
```
Files: plan/validation/execution/V2-004/remote-security/*.md
Pattern: "Project: ayitnovel/ainovelos (ID: 86656946)"
Count: 3+
Rationale: Documents actual security state of old repository
Action: PRESERVE - factual security audit evidence
```

### 2.2 ACTIVE_STALE References (REQUIRES UPDATE)

**Finding**: NONE DETECTED

No active operational documents (README, CI config, scripts) contain stale repository references.

**Verified Clean**:
- ✅ README.md - no repository URLs
- ✅ .gitlab-ci.yml - no hardcoded URLs
- ✅ AGENTS.md - no repository URLs
- ✅ scripts/*.py - no hardcoded repository URLs (spot check)

### 2.3 AMBIGUOUS References (REQUIRES REVIEW)

**Finding**: NONE DETECTED

All repository references clearly belong to historical evidence context.

---

## 3. Branch Reference Audit

### 3.1 Active Branch References in Documents

**Search Pattern**: References to branch names in active documentation

**Finding**: README.md contains generic references
```markdown
Line 12: [P0 执行方案](plan/PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md)：V2-001～004
```

No explicit branch name references in active docs. ✅ GOOD

### 3.2 Historical Branch References

Found in evidence files:
- "dev_cc @ 323eaae7" (V2-005 contract baseline)
- Various work/* branches in validation evidence

**Classification**: HISTORICAL_VALID  
**Action**: PRESERVE

---

## 4. CI State References

### 4.1 Historical CI Block References

**Pattern**: "CI_BLOCKED", "stuck_pending_no_matching_runners"

| File | Line | Content | Classification |
|------|------|---------|----------------|
| docs/CI-POLICY-H1_INVESTIGATION_COMPLETE.md | 282 | "IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED" | HISTORICAL_VALID |
| docs/CI-POLICY-H1_DIAGNOSIS.md | 333 | "IMPLEMENTED_CONTRACT_VERIFIED_CI_BLOCKED" | HISTORICAL_VALID |
| docs/CI-LOCK-H1_FIX_REPORT.md | 243 | "STEP_2_STATE: ...CI_BLOCKED" | HISTORICAL_VALID |
| docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md | 336 | "Step 2 State: ...CI_BLOCKED" | HISTORICAL_VALID |

**Analysis**: These files document the historical CI blockage that necessitated repository migration. They correctly describe the state at that time.

**Also Found**: Resolution evidence
```
docs/V2-005_STEP_2_H1_FIX_REPORT.md:227: "STEP_2_STATE: IMPLEMENTED_CI_VERIFIED"
docs/CI-POLICY-H1-R1_REMEDIATION_PLAN.md:314: "STEP_2_STATE = IMPLEMENTED_CI_VERIFIED"
```

**Interpretation**: The document set correctly shows the progression CI_BLOCKED → CI_VERIFIED.

**Action**: PRESERVE both states (shows problem resolution timeline)

### 4.2 Active CI Status References

**README.md Current Claims**:
```markdown
Line 5: "V2-001 through V2-004 CLOSED, G-P0 PASS"
Line 65: "V2-003 已完成本地实施与验证"
```

**Assessment**:
- ⚠️ STALE - Does not mention V2-005 Step 2 completion
- ⚠️ INCOMPLETE - No mention of new repository migration
- ⚠️ OUTDATED - "当前实施边界" claims V2-003, but we're at V2-005 Step 3

**Action Required**: UPDATE README.md

---

## 5. Pipeline ID References

### 5.1 Historical Pipeline IDs (Old Repository)

Sample of documented pipelines from ayitnovel/ainovelos:

```
2910274247  (V2-005 H2 delta closure)
2906152868  (G-P0 closure)
2888946804  (V2-004 closure)
2885351752  (V2-001/V2-004 CI)
... (15+ more in validation evidence)
```

**Classification**: EVIDENCE_IMMUTABLE  
**Action**: PRESERVE (accurate historical record)

### 5.2 Current Pipeline IDs (New Repository)

Documented in task handoff:

```
2915891016  (work/h2-convergence-closure, be6e475, 6/6 PASS)
2915904387  (verification/v2-005-step2-1aa31e7, 1aa31e7, 6/6 PASS, EXACT SHA)
```

**Classification**: CURRENT_EVIDENCE  
**Location**: Currently only in task handoff, NOT in repository docs  
**Action Required**: Add to evidence documentation

---

## 6. Commit SHA References

### 6.1 Verified Milestone SHAs

| SHA | Description | Referenced In |
|-----|-------------|---------------|
| 1aa31e7cdaff14e777210011c766badcd797b836 | Step 2 exact verified | Task handoff, verification branch |
| be6e475b77b5802cfcc73242f7273588288d06bf | Continuation post-migration | Current HEAD |
| 376565f52604811fb45159c18111ebd2cd779b08 | New repo initial commit | Merge parent |
| e300429 | Contract remediation (dev_cc) | Contract baseline |
| 323eaae7 | Contract baseline | V2-005 contract doc |

**Status**: All SHAs correctly documented in appropriate contexts

### 6.2 SHA Reference Accuracy

No incorrect or stale SHA references detected. ✅

---

## 7. Test Count References

### 7.1 Historical Test Counts

Found in evidence documents:
- "565 tests" (various V2-005 documents)
- "343 UNIT tests"
- "222 ARCH_FITNESS tests"

**Verification**: Still accurate as of be6e475 per Pipeline 2915904387

**Status**: ✅ ACCURATE

### 7.2 Stale Test Count References

**Finding**: NONE DETECTED

---

## 8. Documentation Cross-Reference Audit

### 8.1 Internal Plan References

README.md references:
```markdown
✅ [phase-gates.yaml](plan/machine/phase-gates.yaml) - EXISTS
✅ [implementation-backlog.yaml](plan/machine/implementation-backlog.yaml) - EXISTS
✅ [remediation-register.yaml](plan/machine/remediation-register.yaml) - EXISTS
✅ [ai-execution-policy.yaml](plan/machine/ai-execution-policy.yaml) - EXISTS
✅ [plan/README.md](plan/README.md) - EXISTS
✅ [AGENTS.md](AGENTS.md) - EXISTS
```

**Status**: All cross-references valid ✅

### 8.2 External References

Found in docs/V2-004/remote-security/*.md:
- GitLab documentation URLs
- RFC references
- External practice references

**Status**: Not verified (external), assume valid

---

## 9. Stale Status Claims

### 9.1 README.md Staleness

**Current Claims**:
```
Line 5: "V2-001 through V2-004 CLOSED, G-P0 PASS"
```

**Reality**: V2-005 Step 2 is also CLOSED (CI_VERIFIED)

**Staleness**: ⚠️ OUTDATED by ~1 task

**Proposed Update**:
```
"V2-001 through V2-004 CLOSED, V2-005 Step 2 VERIFIED, G-P0 PASS"
```

---

**Current Claims**:
```
Line 65: "V2-003 已完成本地实施与验证"
```

**Reality**: V2-003, V2-004, and V2-005 Step 1-2 all completed

**Staleness**: ⚠️ OUTDATED by 2+ tasks

**Proposed Update**:
```
"V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。
V2-004 (CI/Security) 已完成远端 CI 与权限验证。
V2-005 Step 1-2 (Entity Identity Core Types) 已完成契约验证与 CI 验证（Pipeline 2915904387, 6/6 PASS）。
当前任务：V2-005 Step 3 - ID Generation and Normalization。"
```

### 9.2 Active Doc Staleness Summary

| Document | Stale Claims | Severity | Action |
|----------|--------------|----------|--------|
| README.md | V2-005 not mentioned | MEDIUM | UPDATE |
| README.md | Current boundary = V2-003 | MEDIUM | UPDATE |
| AGENTS.md | None detected | - | KEEP |
| .gitlab-ci.yml | None detected | - | KEEP |

---

## 10. Reference Correction Plan

### 10.1 DO NOT MODIFY (Historical Evidence)

**Files**: 20+ files containing old repository URLs
**Rationale**: Accurate historical record
**Examples**:
- plan/validation/*/ci/*.yaml
- plan/validation/execution/V2-004/remote-security/*.md
- V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md

**Action**: PRESERVE with explicit note in housekeeping report

### 10.2 MUST UPDATE (Active Status)

**File**: README.md

**Line 5 - Current**:
```markdown
当前为 **Plan v1.3.0**。P0 (Repository & Governance) 已验证完成，V2-001 through V2-004 CLOSED，G-P0 PASS。
```

**Line 5 - Proposed**:
```markdown
当前为 **Plan v1.3.0**。P0 (Repository & Governance) 已验证完成，V2-001 through V2-004 CLOSED，V2-005 Step 2 VERIFIED (Pipeline 2915904387, 6/6 PASS, 565/565 PASS)，G-P0 PASS。当前仓库：gitlab.com/angyang/ainovel。
```

**Section "当前实施边界" - Current**:
```markdown
V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。
```

**Section "当前实施边界" - Proposed**:
```markdown
## 当前实施边界

V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。`scripts/check_architecture.py` 扫描完整 `src/anovel` Python 源码，检查导入边界和当前 P0 硬门禁政策；`scripts/check_changes.py` 比较固定 Git 基线与实际 index/worktree，审查任务范围和可识别的验收弱化。

V2-004 (Secret/依赖 CI、远端来源与保护权限) 已完成并验证。远端 CI、架构检查器和权限边界均已实现。

V2-005 Step 1-2 已完成：
- Step 1: Entity identity module structure established
- Step 2: Core entity identity types implemented (EntityId, ProjectId, ResolutionResult)
- Exact SHA 1aa31e7 verified via Pipeline 2915904387 (6/6 PASS, 565/565 PASS)
- Contract: docs/V2-005_IMPLEMENTATION_CONTRACT.md v1.1.0

**当前任务**: V2-005 Step 3 - Implement ID Generation and Normalization
- Branch: work/h2-convergence-closure
- Continuation SHA: be6e475b77b5802cfcc73242f7273588288d06bf

P1 (Narrative Kernel) 将实现核心叙事模型。优先保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。
```

### 10.3 SHOULD ADD (New Evidence)

**Recommendation**: Add untracked evidence files to docs/ with current pipeline references

---

## 11. Stale Reference Statistics

```
TOTAL_OLD_REPO_REFS: 20+
  HISTORICAL_VALID: 20+ (100%)
  ACTIVE_STALE: 0 (0%)

STALE_STATUS_CLAIMS: 2
  README.md task status: 1
  README.md current boundary: 1

STALE_BRANCH_REFS: 0
STALE_CI_CONFIG: 0
STALE_PIPELINE_IDS: 0
STALE_TEST_COUNTS: 0
STALE_SHA_REFS: 0

BROKEN_INTERNAL_LINKS: 0
```

---

## 12. Reference Update Priority

### Priority 1: MUST UPDATE
1. README.md line 5 - project status summary
2. README.md section "当前实施边界" - current task boundary

### Priority 2: SHOULD ADD
3. Add untracked evidence files to repository
4. Create PROJECT_STATUS.md with current state

### Priority 3: OPTIONAL
5. Add explicit repository migration note to README
6. Document new repository in plan/validation/

### Priority 4: PROHIBITED
7. ❌ Do NOT modify historical evidence repository URLs
8. ❌ Do NOT change pipeline IDs in evidence
9. ❌ Do NOT update commit SHAs in historical docs

---

## 13. Verification After Updates

After applying updates, verify:

```bash
# Check no historical evidence was modified
git diff HEAD -- plan/validation/

# Should show ZERO changes
```

```bash
# Check only intended active docs were updated
git diff HEAD -- README.md

# Should show ONLY status updates
```

---

**END OF STALE REFERENCE REPORT**

Next: Security Hygiene Report
