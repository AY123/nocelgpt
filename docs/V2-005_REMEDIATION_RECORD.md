# V2-005 Contract Remediation - Implementation Record

**Date**: 2026-10-03  
**Baseline**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**Status**: Partial implementation in progress

---

## Completed Fixes (HIGH Priority)

### ✅ CR-002: UUID v4 决策清理ULID残留
**Files Modified**:
- V2-005_IMPLEMENTATION_CONTRACT.md: Line 294, 1218, 1266
- V2-005_IMPLEMENTATION_PLAN.md: Lines 148-151 removed try/except
- V2-005_TASK_REFINEMENT.md: Line 957
- V2-005_CONTRACT_REVISION_REPORT.md: Line 49

**Changes**:
- 删除所有"Try ULID first", "Fallback to UUID"引用
- 统一为UUID v4 only
- 清除JSON Schema中的ULID描述

### ✅ CR-006: 别名冲突语义统一
**Files Modified**:
- V2-005_TASK_REFINEMENT.md: NS-5 section (line ~731)
- V2-005_TEST_CONTRACT_MATRIX.md: TC-005-038 (line 53)

**Changes**:
- 删除ConflictError要求
- 统一为: 允许跨实体重复别名 → 解析返回AMBIGUOUS
- 修改测试预期

### ✅ CR-007: 全角空格规则统一
**Files Modified**:
- V2-005_IMPLEMENTATION_CONTRACT.md: §3.6 normalization section
- V2-005_TEST_CONTRACT_MATRIX.md: TC-005-026

**Changes**:
- 明确: 全角空格删除(不是折叠)
- 统一所有代码和测试预期

### ✅ CR-008: 存储表示冻结
**Files Modified**:
- V2-005_IMPLEMENTATION_CONTRACT.md: §9.4

**Changes**:
- 删除"Store BOTH"双字段建议
- 冻结为: 仅存储原文，查询时计算normalized key
- 符合§13.1 closed schema

### ✅ CR-010: canonical_name/aliases重叠规定统一
**Files Modified**:
- V2-005_IMPLEMENTATION_CONTRACT.md: §2.3 aliases field, invariant 5

**Changes**:
- 统一为: 允许重叠(改名后旧名进入aliases)
- 删除"Does NOT include canonical_name"矛盾

### ✅ CR-011: 改名后注册表更新明确
**Files Modified**:
- V2-005_IMPLEMENTATION_CONTRACT.md: §4.2

**Changes**:
- 补充改名后状态更新示例
- 明确测试fixture直接赋值方式

---

## Remaining HIGH Priority (需要继续)

### ⏳ CR-001: 统一状态声明
**Status**: NOT STARTED
**Required**: 全部9份文档头部状态

### ⏳ CR-003: ProjectId校验语义
**Status**: Code is correct (no TypeError), need clarification in docs
**Required**: 补充首尾空白处理说明

### ⏳ CR-004: EntityId验证入口
**Status**: Pattern exists, need §2.1.1 validation entry point spec
**Required**: 补充验证边界规范

### ⏳ CR-005: 注册示例同步
**Status**: §4.1 correct, need sync to §14.2 and PLAN
**Required**: 同步正确代码到所有示例

---

## MEDIUM Priority (部分完成)

### ✅ CR-009: 构造边界明确 (PARTIAL)
**Status**: Immutability guarantees added, TC-005-050 needs fix

### ✅ CR-012: JSON范围明确 (PARTIAL)
**Status**: Need to add clarification on equality vs serialization

### ⏳ CR-013: 映射表
**Status**: NOT STARTED

### ⏳ CR-014: ADR引用修正
**Status**: NOT STARTED

---

## LOW Priority

### ⏳ CR-015: 统计刷新
**Status**: Current line counts retrieved, need to update docs

---

## Next Actions

由于时间和token限制，建议：

1. **提交当前进度** (6/15 completed)
2. **用户review已完成的修订**
3. **下一轮继续剩余9项**

或

**继续本轮完成所有15项**（需要较多编辑操作）

用户决定下一步行动。
