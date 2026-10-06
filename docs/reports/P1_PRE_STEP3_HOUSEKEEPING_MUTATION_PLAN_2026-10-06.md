# P1-PRE-STEP3-HOUSEKEEPING-001: Mutation Plan
**Document ID**: P1-PRE-STEP3-HOUSEKEEPING-MUTATION-PLAN  
**Date**: 2026-10-06  
**Baseline**: work/h2-convergence-closure @ be6e475b

---

## EXECUTIVE SUMMARY

This plan defines the minimal, safe mutations required to:
1. Clarify current project status for AI agents
2. Commit untracked evidence files
3. Clean up root directory noise
4. Update stale status claims in README.md

**Total Proposed Changes**: 7 mutation groups  
**Risk Level**: LOW (no production code, contract, schema, or test changes)  
**Rollback**: All changes are reversible via git reset

---

## MUTATION APPROVAL LOGIC

### Auto-Approved Categories (Will Execute)
- Documentation updates (status clarity)
- Adding untracked evidence files (immutable preservation)
- Moving obvious duplicates to docs/
- .gitignore minor additions (if needed)

### Deferred Categories (Will NOT Execute)
- Branch deletion
- Stash cleanup
- Archive organization beyond root cleanup
- main branch operations

### Prohibited Categories (Will NEVER Execute)
- Production code changes
- Contract modifications
- Schema changes
- Test deletion or weakening
- Historical evidence modification
- Branch history rewrite

---

## MUTATION GROUP 1: Create PROJECT_STATUS.md

**ID**: MUT-001  
**Type**: CREATE_FILE  
**Risk**: LOW  
**Reversibility**: HIGH (git rm)

**Target**: `PROJECT_STATUS.md` (repository root)

**Rationale**: New AI agents require 6+ navigation hops to determine current project state. This creates a single-file SSOT.

**Content**: See detailed content below

**Evidence**: Authority Matrix Report identified this as critical gap

**Rollback**: `git rm PROJECT_STATUS.md`

---

## MUTATION GROUP 2: Update README.md Status Claims

**ID**: MUT-002  
**Type**: UPDATE_FILE  
**Risk**: LOW  
**Reversibility**: HIGH (git checkout)

**Target**: `README.md`

**Changes**:

### Change 2.1: Update Line 5 (Project Status Summary)

**Current**:
```markdown
当前为 **Plan v1.3.0**。P0 (Repository & Governance) 已验证完成，V2-001 through V2-004 CLOSED，G-P0 PASS。权威阶段状态见 [phase-gates.yaml](plan/machine/phase-gates.yaml)。
```

**Proposed**:
```markdown
当前为 **Plan v1.3.0**。P0 (Repository & Governance) 已验证完成，V2-001 through V2-004 CLOSED，V2-005 Step 2 VERIFIED (Pipeline 2915904387, 6/6 PASS)，G-P0 PASS。当前仓库：`https://gitlab.com/angyang/ainovel.git`。权威阶段状态见 [phase-gates.yaml](plan/machine/phase-gates.yaml)。
```

**Justification**: Adds V2-005 Step 2 completion and new repository URL

---

### Change 2.2: Insert Current Status Section (After Line 7)

**Location**: After line 7 (after "剩余任务见...")

**Insert**:
```markdown

**当前状态**: V2-005 Step 3 实施中 (ID Generation and Normalization)  
**当前分支**: `work/h2-convergence-closure`  
**Step 2 验证**: SHA `1aa31e7`, Pipeline 2915904387, 6/6 PASS, 565/565 PASS  
**详细状态**: 见 [PROJECT_STATUS.md](PROJECT_STATUS.md)
```

**Justification**: Provides immediate status visibility at README top

---

### Change 2.3: Update "当前实施边界" Section

**Current** (Line 63-67):
```markdown
## 当前实施边界

V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。`scripts/check_architecture.py` 扫描完整 `src/anovel` Python 源码...
```

**Proposed**: Expand section with V2-004 and V2-005 status

```markdown
## 当前实施边界

V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。`scripts/check_architecture.py` 扫描完整 `src/anovel` Python 源码，检查导入边界和当前 P0 硬门禁政策；`scripts/check_changes.py` 比较固定 Git 基线与实际 index/worktree，审查任务范围和可识别的验收弱化。代码存在与验证完成分别记录。

V2-004 (Secret/依赖 CI、远端来源与保护权限) 已完成并验证。远端 CI、架构检查器和权限边界均已实现。正式任务关闭需要代码、测试、真实 CI 和验收记录，本地 PASS 与 CI PASS 分别记录。

**V2-005 当前进度**:
- **Step 1** (Entity Identity Module Structure): ✅ COMPLETE
- **Step 2** (Core Entity Types Implementation): ✅ VERIFIED
  - Exact SHA: `1aa31e7cdaff14e777210011c766badcd797b836`
  - Pipeline: 2915904387 (6/6 PASS, 565/565 PASS)
  - Contract: docs/V2-005_IMPLEMENTATION_CONTRACT.md v1.1.0
- **Step 3** (ID Generation and Normalization): 🔄 IN PROGRESS
  - Branch: `work/h2-convergence-closure`
  - Continuation SHA: `be6e475b77b5802cfcc73242f7273588288d06bf`

P1 (Narrative Kernel) 将实现核心叙事模型。优先保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。
```

**Justification**: Updates stale "V2-003 is current" claim to accurate V2-005 Step 3 status

**Rollback**: `git checkout HEAD -- README.md`

---

## MUTATION GROUP 3: Add Untracked Evidence Files

**ID**: MUT-003  
**Type**: ADD_FILES  
**Risk**: VERY_LOW  
**Reversibility**: HIGH (git rm)

**Targets**: 11 untracked files in docs/

**Files**:
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

**Action**: `git add docs/CI-*.md docs/V2-005_*.md`

**Rationale**: These are evidence files documenting actual work performed. They should be in repository as immutable evidence.

**Pre-Check Required**: 
- Verify no secrets in files (grep for glpat-, password=, etc.)
- Verify content is evidence/report, not temporary scratch

**Classification**: EVIDENCE_IMMUTABLE

**Rollback**: `git rm --cached docs/CI-*.md docs/V2-005_*.md`

---

## MUTATION GROUP 4: Move Root Evidence to docs/

**ID**: MUT-004  
**Type**: MOVE_FILES  
**Risk**: LOW  
**Reversibility**: HIGH (git mv back)

**Targets**:

### 4.1 AT08_LEGITIMATE_CONTROL.md
```
SOURCE: ./AT08_LEGITIMATE_CONTROL.md
TARGET: docs/AT08_LEGITIMATE_CONTROL.md
COMMAND: git mv AT08_LEGITIMATE_CONTROL.md docs/
RATIONALE: Test evidence file, belongs in docs/
SIZE: 349 bytes
```

### 4.2 审核报告.txt
```
SOURCE: ./审核报告.txt
TARGET: docs/审核报告_历史.txt
COMMAND: git mv 审核报告.txt docs/审核报告_历史.txt
RATIONALE: Historical audit report (Chinese), belongs in docs/
SIZE: 27KB
NOTE: Rename to indicate historical nature
```

### 4.3 V2-003任务prompt.txt
```
SOURCE: ./V2-003任务prompt.txt
TARGET: docs/V2-003_TASK_PROMPT.txt
COMMAND: git mv V2-003任务prompt.txt docs/V2-003_TASK_PROMPT.txt
RATIONALE: Historical task prompt, belongs in docs/
SIZE: 11KB
NOTE: Rename to ASCII filename for portability
```

**Rollback**: `git mv docs/<file> ./`

---

## MUTATION GROUP 5: Archive Root Review Documents

**ID**: MUT-005  
**Type**: MOVE_FILES  
**Risk**: LOW  
**Reversibility**: HIGH

**Targets**:

### 5.1 Duplicate Review File (Malformed Name)
```
SOURCE: ./V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md
ACTION: DELETE (after confirming duplicate)
RATIONALE: Duplicate with malformed filename
COMMAND: rm "V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md"
PRE-CHECK: diff with V2-005_INDEPENDENT_REVIEW_58d77d2.md
```

### 5.2 Move Review Documents to docs/
```
SOURCE: ./V2-005_INDEPENDENT_REVIEW_58d77d2.md
TARGET: docs/V2-005_INDEPENDENT_REVIEW_58d77d2.md
COMMAND: git mv V2-005_INDEPENDENT_REVIEW_58d77d2.md docs/
RATIONALE: Review evidence, belongs in docs/
SIZE: 33KB
```

```
SOURCE: ./V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md
TARGET: docs/V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md
COMMAND: git mv V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md docs/
RATIONALE: Historical review evidence
SIZE: 12KB
NOTE: Contains old repository URLs (correct for historical context)
```

**Rollback**: `git mv docs/<file> ./`

---

## MUTATION GROUP 6: Archive Root Compressed Packages

**ID**: MUT-006  
**Type**: MOVE_FILES  
**Risk**: LOW  
**Reversibility**: HIGH

**Targets**:

### 6.1 Check for Duplicates in docs/
```
BEFORE MOVING: Check if these already exist in docs/
- docs/V2-005_REMEDIATION_PACKAGE_e300429.tar.gz
- docs/V2-005_审核材料_58d77d2.tar.gz
```

### 6.2 Move Archives
```
SOURCE: ./V2-005_REMEDIATION_PACKAGE_e300429.tar.gz
TARGET: docs/V2-005_REMEDIATION_PACKAGE_e300429.tar.gz
COMMAND: git mv V2-005_REMEDIATION_PACKAGE_e300429.tar.gz docs/
SIZE: 54KB
PRE-CHECK: Check if already exists in docs/
```

```
SOURCE: ./V2-005_H1_REMEDIATION_PACKAGE.tar.gz
TARGET: docs/V2-005_H1_REMEDIATION_PACKAGE.tar.gz
COMMAND: git mv V2-005_H1_REMEDIATION_PACKAGE.tar.gz docs/
SIZE: 63KB
```

**Alternative**: If duplicates exist in docs/, delete root versions instead of moving

**Rollback**: `git mv docs/<file> ./` or restore from git

---

## MUTATION GROUP 7: Update .gitignore (if needed)

**ID**: MUT-007  
**Type**: UPDATE_FILE  
**Risk**: VERY_LOW  
**Reversibility**: HIGH

**Target**: `.gitignore`

**Current Assessment**: Coverage is adequate ✅

**Proposed Addition** (optional, for completeness):
```gitignore
# Python type checker and linters (already present but explicit)
.mypy_cache/
.ruff_cache/

# Coverage reports
.coverage
htmlcov/
```

**Status**: DEFER (current coverage sufficient, caches already ignored)

**Action**: NO CHANGE

---

## PROHIBITED MUTATIONS (Will NOT Execute)

### PROHIBITED-1: Branch Deletion
```
❌ git branch -D <branch>
❌ git push --delete origin <branch>
```
**Rationale**: Deferred to post-housekeeping, requires explicit approval

### PROHIBITED-2: Stash Cleanup
```
❌ git stash drop
```
**Rationale**: Requires inspection, deferred

### PROHIBITED-3: Main Branch Operations
```
❌ git push -f origin main
❌ Modify main history
```
**Rationale**: Task constraints explicitly prohibit

### PROHIBITED-4: Historical Evidence Modification
```
❌ Modify plan/validation/ URLs
❌ Update pipeline IDs in evidence
❌ Change historical CI status claims
```
**Rationale**: Would falsify historical record

### PROHIBITED-5: Production Changes
```
❌ Modify src/
❌ Modify tests/
❌ Modify schemas/
❌ Modify contracts/
```
**Rationale**: Out of scope for housekeeping

---

## VERIFICATION PLAN

After each mutation group:

```bash
# Check working directory state
git status

# Verify no unintended changes
git diff --check

# Verify only intended files modified
git diff --stat

# Run existing validation
.venv/bin/python -B plan/scripts/validate_plan.py --check --output-dir dist/validation/housekeeping
.venv/bin/python -B -m pytest -q tests/contract
```

After all mutations:

```bash
# Verify repository state
git status --short | wc -l  # Should be 0 if all changes committed

# Verify CI gates still pass (local)
.venv/bin/python -B scripts/check_governance.py --output-dir dist/validation/housekeeping-post
.venv/bin/python -B -m pytest -q

# Verify no production behavior changed
git diff be6e475..HEAD -- src/ tests/ specs/  # Should show 0 changes
```

---

## COMMIT PLAN

### Commit 1: Add Untracked Evidence Files
```bash
git add docs/CI-*.md docs/V2-005_STEP_*.md docs/V2-005_*AUTHORIZATION*.md docs/V2-005_POST_CI*.md
git commit -m "docs(V2-005): add Step 1-2 and CI remediation evidence

Add untracked evidence files documenting V2-005 Step 1-2 implementation
and CI remediation process:
- Step 1 and Step 2 execution reports
- CI investigation and remediation reports
- Authorization gate reports

These files document actual work performed and CI verification.

Evidence binding:
- Step 2 exact SHA: 1aa31e7
- Step 2 Pipeline: 2915904387 (6/6 PASS, 565/565 PASS)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Commit 2: Organize Root Directory Evidence
```bash
git mv AT08_LEGITIMATE_CONTROL.md docs/
git mv 审核报告.txt docs/审核报告_历史.txt
git mv V2-003任务prompt.txt docs/V2-003_TASK_PROMPT.txt
git mv V2-005_INDEPENDENT_REVIEW_58d77d2.md docs/
git mv V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md docs/
git mv V2-005_REMEDIATION_PACKAGE_e300429.tar.gz docs/
git mv V2-005_H1_REMEDIATION_PACKAGE.tar.gz docs/
rm "V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md"

git commit -m "chore(housekeeping): organize root directory evidence files

Move historical evidence and review documents from repository root to docs/:
- Test evidence (AT08)
- Historical audit reports
- V2-003 task prompt
- V2-005 review documents
- Remediation packages

Remove duplicate file with malformed name.

No content changes, organization only.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Commit 3: Update Project Status Documentation
```bash
# Create PROJECT_STATUS.md
# Update README.md

git add PROJECT_STATUS.md README.md
git commit -m "docs(status): update project status for V2-005 Step 3

Create PROJECT_STATUS.md with current state summary for AI agents.

Update README.md:
- Add V2-005 Step 2 verification status
- Add current repository URL
- Expand '当前实施边界' section with V2-004 and V2-005 progress
- Add explicit Step 3 work-in-progress marker

Current state:
- Task: V2-005 Step 3 (ID Generation and Normalization)
- Branch: work/h2-convergence-closure
- Step 2 verified: SHA 1aa31e7, Pipeline 2915904387 (6/6 PASS)

No production code changes.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## ROLLBACK PROCEDURES

### Full Rollback (Before Push)
```bash
# Reset all housekeeping commits
git reset --hard be6e475b77b5802cfcc73242f7273588288d06bf

# Verify restoration
git status
git log --oneline -1
```

### Partial Rollback (Specific Commit)
```bash
# Revert a specific commit
git revert <commit-sha>

# Or reset to before specific commit
git reset --hard <commit-before-housekeeping>
```

### After Push (If Needed)
```bash
# Create revert commits (preserves history)
git revert <housekeeping-commit-1>
git revert <housekeeping-commit-2>
git revert <housekeeping-commit-3>
git push origin work/h2-convergence-closure
```

---

## RISK ASSESSMENT MATRIX

| Mutation Group | Risk Level | Impact | Reversibility | Approval |
|----------------|-----------|---------|---------------|----------|
| MUT-001: Create STATUS | VERY_LOW | High value | Easy (git rm) | ✅ AUTO |
| MUT-002: Update README | LOW | High value | Easy (checkout) | ✅ AUTO |
| MUT-003: Add evidence | VERY_LOW | Medium value | Easy (git rm) | ✅ AUTO |
| MUT-004: Move evidence | LOW | Low impact | Easy (git mv back) | ✅ AUTO |
| MUT-005: Archive reviews | LOW | Low impact | Easy (git mv back) | ✅ AUTO |
| MUT-006: Archive packages | LOW | Low impact | Easy (restore) | ✅ AUTO |
| MUT-007: Update .gitignore | VERY_LOW | Low impact | Easy (checkout) | ⏸️ DEFER |

**Overall Risk**: LOW  
**Production Impact**: NONE (documentation only)  
**Evidence Impact**: POSITIVE (adds evidence, does not modify existing)  
**Reversibility**: HIGH (all changes easily reversible)

---

## EXECUTION SEQUENCE

1. ✅ **Pre-flight checks**
   - Verify baseline SHA: be6e475
   - Verify clean working directory (except known untracked files)
   - Verify .venv activated

2. ✅ **MUT-003**: Add untracked evidence files
   - Pre-check: Scan for secrets
   - Execute: git add
   - Verify: git status
   - Commit: Evidence addition

3. ✅ **MUT-004, MUT-005, MUT-006**: Organize root directory
   - Pre-check: Verify files exist
   - Execute: git mv commands
   - Execute: rm duplicate
   - Verify: Files in correct locations
   - Commit: Organization

4. ✅ **MUT-001**: Create PROJECT_STATUS.md
   - Execute: Create file
   - Verify: Content complete

5. ✅ **MUT-002**: Update README.md
   - Execute: Apply changes
   - Verify: Diff shows only intended changes

6. ✅ **Commit**: Status documentation
   - Commit: Status update
   - Verify: git log

7. ✅ **Validation**
   - Run: contract tests
   - Run: governance checks
   - Verify: 6/6 gates still pass (if local env available)

8. ✅ **Final verification**
   - Review: All commits
   - Check: No production changes
   - Confirm: Evidence preserved

---

## SUCCESS CRITERIA

Housekeeping mutations are successful if ALL of the following are true:

```
✅ PROJECT_STATUS.md created and contains accurate current state
✅ README.md updated with V2-005 Step 2 completion
✅ 11 untracked evidence files added to repository
✅ Root directory cleaned (evidence moved to docs/)
✅ No production code modified (src/, tests/, specs/)
✅ No contracts modified (docs/V2-005_IMPLEMENTATION_CONTRACT.md unchanged)
✅ No schemas modified (specs/*.json unchanged)
✅ No historical evidence modified (plan/validation/ unchanged)
✅ No test weakening (test count unchanged)
✅ Local validation passes (if environment available)
✅ All changes committed with clear messages
✅ Git history clean (no merge conflicts)
```

**Failure Condition**: If ANY success criterion fails, STOP and rollback.

---

## POST-EXECUTION DELIVERABLES

After successful execution:

1. ✅ Three new commits on work/h2-convergence-closure
2. ✅ PROJECT_STATUS.md at repository root
3. ✅ Updated README.md
4. ✅ Clean root directory (evidence in docs/)
5. ✅ 11 evidence files tracked in docs/
6. ✅ Validation report in dist/validation/housekeeping-post/
7. ✅ This mutation plan execution report (to be created)

---

**END OF MUTATION PLAN**

Status: READY FOR EXECUTION
