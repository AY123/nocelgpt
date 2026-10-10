HISTORICAL — SUPERSEDED — NON-NORMATIVE

**Applicable baseline**: Historical V2-005 remediation phase  
**Superseded by**: H2/H3/H3.1 convergence evidence  
**Warning**: This document must not be used as current implementation, contract approval, authorization, or task status.

---

# V2-005 Contract Remediation - Status Report

**Date**: 2026-10-03  
**Original Baseline**: 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**Current Commit**: [pending - see below]  
**Status**: PARTIAL_REMEDIATION_COMPLETE (6/15 items)

---

## Progress Summary

**Completed**: 6/15 (40%)  
**Remaining**: 9/15 (60%)

### Completed Items (6)

| ID | Issue | Severity | Files Modified | Status |
|----|-------|----------|----------------|--------|
| CR-002 | UUID v4清理ULID残留 | HIGH | 5 files | ✅ DONE |
| CR-006 | 别名冲突语义统一 | HIGH | 2 files | ✅ DONE |
| CR-007 | 全角空格规则统一 | HIGH | 2 files | ✅ DONE |
| CR-008 | 存储表示冻结 | HIGH | 1 file | ✅ DONE |
| CR-010 | canonical_name/aliases统一 | MEDIUM | 1 file | ✅ DONE |
| CR-011 | 改名后注册表更新 | MEDIUM | 1 file | ✅ DONE |

### Remaining Items (9)

**HIGH Priority (3)**:
- CR-001: 状态声明统一 (所有9份文档)
- CR-003: ProjectId校验语义明确
- CR-004: EntityId验证入口规范
- CR-005: 注册示例代码同步

**MEDIUM/LOW Priority (5)**:
- CR-009: 构造边界明确
- CR-012: JSON范围说明
- CR-013: 映射表补充
- CR-014: ADR引用修正
- CR-015: 统计数据刷新

---

## Key Changes Made

### 1. ULID完全移除 (CR-002)
**Before**: Try ULID, fallback to UUID  
**After**: UUID v4 only (standard library)

**Files**:
- IMPLEMENTATION_CONTRACT: 移除ULID描述
- IMPLEMENTATION_PLAN: 删除try/except分支
- TASK_REFINEMENT: 删除fallback说明
- CONTRACT_REVISION_REPORT: 更新格式描述
- JSON Schema描述: 改为UUID v4

### 2. 别名冲突统一为允许 (CR-006)
**Before**: NS-5要求Error, TC-005-038预期Error/Warning  
**After**: 允许重复 → resolve返回AMBIGUOUS

**Rationale**: 符合§4.1主契约设计

### 3. 全角空格统一删除 (CR-007)
**Before**: 文档说"strip", 示例显示删除  
**After**: 明确删除(不折叠), 统一所有代码和测试

### 4. 存储表示冻结为原文 (CR-008)
**Before**: §9.4建议存储双字段(raw + normalized)  
**After**: 仅存储原文，查询时计算normalized key

**Rationale**: 符合§13.1 closed schema

### 5. 允许canonical_name在aliases (CR-010)
**Before**: §2.3说"Does NOT include", Invariant说"MAY exist"  
**After**: 统一为"MAY exist after rename"

### 6. 改名后状态更新示例 (CR-011)
**Before**: Option A/B但未明确流程  
**After**: 补充完整示例代码

---

## Remaining Work Breakdown

### Phase 1: Critical HIGH items (估计2-3小时)

**CR-001: 状态声明统一** (9 files)
- 所有文档头部改为 `REVISED / INDEPENDENT_REVIEW_PENDING`
- 删除 `CONTRACT FROZEN`, `READY` 声明
- 估计: 15-20处修改

**CR-005: 注册示例同步** (2 files)
- 同步§4.1正确代码到§14.2
- 同步到IMPLEMENTATION_PLAN Step 4
- 估计: 2处代码块替换

**CR-003/004: 验证边界明确** (2 files)
- ProjectId: 补充首尾空白语义说明
- EntityId: 补充§2.1.1验证入口规范
- 估计: 2个新小节

### Phase 2: MEDIUM/LOW items (估计1-2小时)

**CR-009**: TC-005-050测试修正  
**CR-012**: §9.1补充相等语义说明  
**CR-013**: 测试矩阵添加AC映射表  
**CR-014**: DECISION_GATES ADR分析修正  
**CR-015**: 更新REVISION_EVIDENCE行数

---

## Options for Next Step

### Option A: 继续完成剩余9项 (推荐)
- **优点**: 一次性完成所有修订，契约进入复核状态
- **缺点**: 需要继续2-4小时工作
- **建议**: 适合集中处理

### Option B: 提交当前进度，下一轮继续
- **优点**: 当前6项已有价值，可以审查
- **缺点**: 仍有3个HIGH未修复，不能冻结契约
- **建议**: 仅在需要中断时选择

### Option C: 仅完成HIGH，延后MEDIUM/LOW
- **优点**: 快速解决阻塞项
- **缺点**: 仍需第三轮处理低优先级
- **建议**: 适合时间紧迫时

---

## Recommendation

**推荐 Option A**: 继续完成剩余9项

**理由**:
1. 已完成6项，建立了修订模式
2. 剩余3个HIGH必须修复才能解除冻结阻塞
3. MEDIUM/LOW项工作量不大，可顺手完成
4. 一次性完成避免多次context切换

**预计总时长**: 再需2-4小时（已用约1小时）

---

## Current Commit

等待用户决定是否继续。如果继续，当前进度将作为中间提交。

**Files changed**: 8 documents  
**Lines changed**: ~50-70 lines  
**Core fixes**: UUID统一, 别名语义, 存储表示, 规范名重叠

---

**Status**: AWAITING_USER_DECISION

**Options**:
- A: Continue all 15 items
- B: Review current 6, continue later  
- C: Finish 3 HIGH only

用户选择？
