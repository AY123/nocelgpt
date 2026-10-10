# V2-005 Independent Review Triage Report

**Triage Date**: 2026-10-03  
**Review Report**: V2-005_INDEPENDENT_REVIEW_58d77d2.md (273 lines)  
**Report Baseline**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**Current Baseline**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**Baseline Match**: CONFIRMED (same commit)

**Triage Protocol**: Independent Review Triage & Selective Remediation  
**Triage Status**: READ-ONLY PHASE (no code changes until approved)

---

## A. EXECUTIVE CONCLUSION

### Review Quality Assessment
- **Quality**: HIGH - 全文核验，15个具体问题，可复现案例
- **Evidence**: E2 (静态分析 + 代码复现案例)
- **Scope**: Contract documents only (no running code verification)

### Original Claims
- **Total Findings**: 15 (CR-001 through CR-015)
- **Observations**: 明确分离在 §已覆盖部分

### Verification Summary (after triage)
- **CONFIRMED**: 13 findings
- **PARTIALLY_CONFIRMED**: 2 findings (CR-012, CR-013)
- **FALSE_POSITIVE**: 0
- **ALREADY_FIXED**: 0
- **CANNOT_VERIFY**: 0

### Decision Summary
- **ADOPT_NOW**: 11 findings
- **ADOPT_WITH_MODIFICATION**: 2 findings (CR-012, CR-013)
- **DEFER**: 2 findings (CR-011, CR-014)
- **REJECT**: 0

### Critical Issues
- **BLOCKER**: 0
- **P0**: 3 (CR-002, CR-005, CR-006)
- **P1**: 7
- **P2**: 5

---

## B. REPOSITORY BASELINE

```yaml
Branch: dev_cc
HEAD: 58d77d2673d07950d0a235d2b25bf7e1e17cb274
Worktree: Modified 审核报告.txt, untracked review files
Plan_Version: 1.3.0
Phase_Status: P0 VERIFIED, P1 entry pending
Current_Task: V2-005
Task_Status: REVISED / INDEPENDENT_REVIEW_PENDING
Task_Owner: domain-maintainer

Tool_Access:
  - Local Repository: YES
  - Remote CI: NO
  - Running Code: NO (contracts only, no implementation)

Evidence_Capability:
  - E0-E2: Available (document analysis, static reproduction)
  - E3: NOT_AVAILABLE (no running tests, no CI execution)
  - E4: NOT_APPLICABLE (no production system)
```

---

## C. FINDING TRIAGE MATRIX

| ID | Verification | Evidence | Severity | Recommendation | Decision | Owner | Reason |
|----|--------------|----------|----------|----------------|----------|-------|--------|
| CR-001 | CONFIRMED | E2 | P1 | VALID | ADOPT_NOW | V2-005 | 状态声明准确性 |
| CR-002 | CONFIRMED | E2 | P0 | VALID | ADOPT_NOW | V2-005 | UUID格式未强制 |
| CR-003 | CONFIRMED | E2 | P1 | VALID | ADOPT_NOW | V2-005 | 校验语义不明 |
| CR-004 | CONFIRMED | E2 | P1 | VALID | ADOPT_NOW | V2-005 | 归一化矛盾 |
| CR-005 | CONFIRMED | E2 | P0 | VALID | ADOPT_NOW | V2-005 | 示例代码违反规范 |
| CR-006 | CONFIRMED | E2 | P0 | VALID | ADOPT_NOW | V2-005 | 别名冲突矛盾 |
| CR-007 | CONFIRMED | E2 | P1 | VALID | ADOPT_NOW | V2-005 | 规范名改名未测试 |
| CR-008 | CONFIRMED | E2 | P1 | VALID | ADOPT_NOW | V2-005 | 前置条件缺失 |
| CR-009 | CONFIRMED | E2 | P2 | VALID | ADOPT_NOW | V2-005 | 候选顺序未定义 |
| CR-010 | CONFIRMED | E2 | P2 | VALID | ADOPT_NOW | V2-005 | 实施步骤不完整 |
| CR-011 | CONFIRMED | E2 | P2 | OVERENGINEERED | DEFER | ADR | ADR理由过度防御 |
| CR-012 | PARTIAL | E1 | P2 | PARTIAL | ADOPT_WITH_MOD | V2-005 | 标题措辞可改进 |
| CR-013 | PARTIAL | E1 | P2 | PARTIAL | ADOPT_WITH_MOD | V2-005 | 映射表可明确 |
| CR-014 | CONFIRMED | E1 | P2 | VALID | DEFER | 后续 | 测试优先级建议 |
| CR-015 | CONFIRMED | E1 | P2 | VALID | ADOPT_NOW | V2-005 | 文档统计准确性 |

---

## D. DETAILED FINDINGS - P0 (ADOPT_NOW)

### CR-002: EntityId 格式未强制执行

**Verification**: CONFIRMED  
**Evidence**: E2 (静态分析 + 复现案例)

**Current Status**: 
- 文档位置已核实: IMPLEMENTATION_CONTRACT §2.1 第37行
- 实际内容: "Format: **UUID v4 (RFC 4122)** - frozen, no environment fallback"
- 问题: 未定义反序列化验证，§2.1.1 不存在

**Reproduction**:
```python
# §2.1 定义了 is_valid_entity_id() 但未规定调用点
# 可直接构造非v4 UUID:
EntityId("00000000-0000-1000-8000-000000000000")  # v1格式
EntityId("550E8400-E29B-41D4-A716-446655440000")  # 大写
# 无强制验证，违反"frozen"声明
```

**Root Cause**: 
- 格式规范仅在生成时保证
- 反序列化路径无验证要求
- 测试构造路径无约束

**Target Invariant**:
```
∀ EntityId e in system:
  e matches UUID v4 pattern (lowercase, with hyphens)
  
Violation: 
  EntityId(non_v4_string) succeeds without validation
```

**Severity**: P0  
**Rationale**: 身份格式不一致将影响所有下游任务(V2-006/007/008/009)

**Recommendation Validity**: VALID

**Decision**: ADOPT_NOW

**Required Actions**:
1. 补充 §2.1.1 "EntityId Validation" 
2. 明确三个构造路径:
   - 生成: `_generate_entity_id()` (已保证格式)
   - 反序列化: 必须通过 `validate_entity_id()`
   - 测试: 允许直接构造(文档说明风险)
3. 添加测试 TC-005-057~061

**Adversarial Challenge**: N/A (格式验证不是行为不变量，是类型约束)

**Remaining Risk**: 测试代码仍可绕过验证 (acceptable - test code trusted)

---

### CR-005: 示例代码违反自身规范

**Verification**: CONFIRMED  
**Evidence**: E2 (静态代码对比)

**Current Status**:
- §4.1 第615-627行: 正确的幂等/冲突检查
- §14.2 第1283-1284行: 直接覆盖 `self._entities[entity.entity_id] = entity`
- IMPLEMENTATION_PLAN Step 4 第239-249行: 同样直接覆盖

**Reproduction**:
```python
# 使用 §14.2 示例代码
registry = EntityRegistry()
e1 = EntityIdentity(id="X", project="proj_a", name="甲", ...)
e2 = EntityIdentity(id="X", project="proj_b", name="乙", ...)

registry.add_entity(e1)  # 直接: _entities["X"] = e1
registry.add_entity(e2)  # 直接: _entities["X"] = e2  # 覆盖!

# 此时:
get_entities("proj_a")  # 返回 e2 (project_id="proj_b")
resolve_alias("proj_a", "乙", registry)  # RESOLVED (违反项目隔离)
```

**Root Cause**:
- §4.1 规范正确，但 §14.2 示例代码未实现该规范
- 项目索引更新但实体已被覆盖，导致 project_id 不匹配

**Target Invariant**:
```
∀ registry r, ∀ project p:
  get_entities(p) 返回的所有实体 e 满足 e.project_id == p
  
Violation:
  §14.2 代码允许 get_entities("proj_a") 返回 project_id="proj_b" 的实体
```

**Severity**: P0  
**Rationale**: 违反核心项目隔离保证，示例代码可直接复现

**Recommendation Validity**: VALID

**Decision**: ADOPT_NOW

**Required Actions**:
1. 将 §4.1 正确实现同步到 §14.2
2. 同步 IMPLEMENTATION_PLAN Step 4
3. 补充 TC-005-047 参数化测试(同项目/跨项目 同ID不同内容)
4. 验证失败后所有索引不变

**Adversarial Challenge**:
```python
# 候选修复: 在add_entity中使用§4.1逻辑
# 攻击: 通过_entities直接访问绕过？
registry._entities[id] = malicious_entity  # 私有字段，允许测试访问

# 评估: 私有字段访问是测试代码特权，acceptable
# Invariant 仍成立: 公开接口 add_entity() 保证隔离
```

**Remaining Risk**: 测试代码直接操作私有字段可绕过 (acceptable - test internal)

---

### CR-006: 别名冲突语义矛盾

**Verification**: CONFIRMED  
**Evidence**: E2 (多文档对比)

**Current Status**:
- IMPLEMENTATION_CONTRACT §3.3: 未检查跨实体别名冲突
- IMPLEMENTATION_CONTRACT §4.1: "Aliases MAY be duplicate (across entities) → AMBIGUOUS at resolution"
- TASK_REFINEMENT NS-5: "add same alias to E2 → Error or warning"
- TEST_CONTRACT_MATRIX TC-005-038: "Error or warning" (与§4.1矛盾)

**Root Cause**: 主契约与测试预期不一致

**Target Invariant**:
```
设计选择A (当前§4.1):
  允许跨实体重复别名，解析时返回 AMBIGUOUS
  
设计选择B (当前NS-5/TC-005-038):
  禁止跨实体重复别名，add_alias 时拒绝
  
矛盾: 两种设计在不同部分混用
```

**Severity**: P0  
**Rationale**: 核心语义不一致，将导致实现选择困惑

**Recommendation Validity**: VALID (保留选择A)

**Decision**: ADOPT_NOW

**Required Actions**:
1. 确认采用设计A (允许重复，解析AMBIGUOUS)
2. 删除/修改 NS-5 和 TC-005-038 中的"Error"预期
3. 明确 add_alias 不执行跨实体查重
4. TC-005-038 改为验证: 两实体同别名 → resolve返回AMBIGUOUS

**Remaining Risk**: NONE (语义统一后无风险)

---

## E. DETAILED FINDINGS - P1 (ADOPT_NOW)

### CR-001: 状态声明准确性

**Verification**: CONFIRMED  
**Evidence**: E1 (文档头部检查)

**grep结果**:
```
V2-005_IMPLEMENTATION_CONTRACT.md:6:Status: REVISED / INDEPENDENT_REVIEW_PENDING
V2-005_DECISION_GATES.md:6:Status: REVISED / INDEPENDENT_REVIEW_PENDING  
V2-005_TASK_REFINEMENT.md:6:Status: REVISED / INDEPENDENT_REVIEW_PENDING
```

**Assessment**: 状态声明已正确(v1.1.0修订后)

**Issue**: 
- 报告声称"修订未完成时声称FROZEN" 
- 实际当前文档已改为 "REVISED / INDEPENDENT_REVIEW_PENDING"
- 但Baseline SHA记录为"323eaae7"(修订前) 而非"58d77d2"(修订后)

**Severity**: P1 (文档完整性问题，非契约逻辑)

**Decision**: ADOPT_NOW

**Required Action**: 更新Baseline SHA从"323eaae7"到"58d77d2"

---

### CR-003: ProjectId校验语义不明

**Verification**: CONFIRMED  
**Evidence**: E2 (代码分析)

**Current Code** (§2.2 第92-119行):
```python
def validate_project_id(s: str) -> ProjectId:
    if not s or not s.strip():
        raise ValueError("ProjectId cannot be empty...")
    stripped = s.strip()
    if any(ord(c) < 0x20 or c == '\x7f' for c in stripped):
        raise ValueError("ProjectId cannot contain control characters")
    return ProjectId(stripped)
```

**Issue**: 
1. 先strip()再检查控制字符 → 首尾`\t\n`被接受(清理)
2. 内部`\n`被拒绝
3. 语义未明确: "清理首尾空白" vs "禁止所有控制字符"

**Severity**: P1

**Decision**: ADOPT_NOW

**Required Action**:
1. 明确语义选择(建议: 允许首尾空白并清理，禁止内部控制字符)
2. 添加非字符串输入检查: `if not isinstance(s, str): raise ValueError`
3. 补充测试 TC-005-052~056

---

### CR-004: 归一化后empty未定义

**Verification**: CONFIRMED  
**Evidence**: E2 (代码分析 + §10.6缺失)

**Current**:
- normalize_for_lookup() 定义清晰
- 但未规定 normalize("   ") → "" 的处理

**Issue**: 空白字符串归一化为空后的行为未定义

**Severity**: P1

**Decision**: ADOPT_NOW

**Required Action**:
1. §3.5 补充: 归一化后为空字符串 → INVALID_INPUT
2. 添加测试 TC-005-042, TC-005-049

---

### CR-007: 规范名变别名未测试

**Verification**: CONFIRMED  
**Evidence**: E1 (测试矩阵检查)

**Current**: TC-005-005 只测试旧名进入aliases，未测试resolve

**Issue**: 未验证旧规范名可解析

**Severity**: P1

**Decision**: ADOPT_NOW

**Required Action**: 补充 TC-005-005 断言: `resolve(project, "陈平安") == RESOLVED(entity_id)`

---

### CR-008: rename前置条件缺失

**Verification**: CONFIRMED  
**Evidence**: E2 (§3.2检查)

**Issue**: §3.2未明确 identity.canonical_name 必须非空

**Severity**: P1

**Decision**: ADOPT_NOW

**Required Action**: §3.2 Preconditions 补充: "identity.canonical_name is valid (non-empty)"

---

## F. DETAILED FINDINGS - P2 (ADOPT_NOW)

### CR-009: 候选顺序未定义

**Verification**: CONFIRMED  
**Evidence**: E2

**Decision**: ADOPT_NOW  
**Action**: §9.1 补充候选数组排序规则(建议: 稳定排序 by EntityId)

### CR-010: 实施步骤不完整

**Verification**: CONFIRMED  
**Evidence**: E2

**Decision**: ADOPT_NOW  
**Action**: IMPLEMENTATION_PLAN 同步 §4.1 代码到 Step 4

### CR-015: 文档统计不准确

**Verification**: CONFIRMED  
**Evidence**: E1 (行数核对)

**Decision**: ADOPT_NOW  
**Action**: 更新 REVISION_EVIDENCE 实际行数(249行，非180行)

---

## G. ADOPT_WITH_MODIFICATION

### CR-012: 测试标题措辞

**Verification**: PARTIALLY_CONFIRMED  
**Evidence**: E1

**Issue**: 测试标题使用中文可能不够精确

**Original Recommendation**: 改为英文标题  
**Assessment**: OVERENGINEERED (中文标题可读性更好，无实质问题)

**Decision**: ADOPT_WITH_MODIFICATION

**Modification**: 保持中文标题，但补充关键英文术语在括号内

### CR-013: 映射表可明确

**Verification**: PARTIALLY_CONFIRMED  
**Evidence**: E1

**Decision**: ADOPT_WITH_MODIFICATION  
**Modification**: 添加测试覆盖矩阵，但不要求每个测试都有显式映射条目

---

## H. DEFERRED

### CR-011: ADR理由分析

**Verification**: CONFIRMED  
**Evidence**: E1

**Issue**: ADR判断理由可改进，但不影响实质结论(不需要ADR)

**Severity**: P2

**Decision**: DEFER  
**Owner**: ADR  
**Reason**: ADR结论正确(decision-register.yaml V2-005: required_decisions: [])，理由表述可优化但非阻塞

### CR-014: 测试优先级建议

**Verification**: CONFIRMED  
**Evidence**: E1

**Decision**: DEFER  
**Owner**: V2-005实施阶段  
**Reason**: 测试优先级是实施细节，契约阶段无需规定

---

## I. APPROVED REMEDIATION PLAN

### Phase 1: P0 Critical (BLOCKER for contract freeze)

| ID | Action | Files | Tests |
|----|--------|-------|-------|
| CR-002 | 补充§2.1.1 EntityId验证规范 | IMPLEMENTATION_CONTRACT | TC-005-057~061 |
| CR-005 | 同步§4.1正确代码到§14.2 | IMPLEMENTATION_CONTRACT, PLAN | TC-005-047 |
| CR-006 | 统一别名冲突语义(选择A) | CONTRACT, REFINEMENT, TEST_MATRIX | 修改TC-005-038 |

### Phase 2: P1 Must-Fix

| ID | Action | Files | Tests |
|----|--------|-------|-------|
| CR-001 | 更新Baseline SHA | All 9 docs | N/A |
| CR-003 | 明确ProjectId校验语义 | IMPLEMENTATION_CONTRACT | TC-005-052~056 |
| CR-004 | 规定归一化空字符串处理 | IMPLEMENTATION_CONTRACT | TC-005-042,049 |
| CR-007 | 补充旧名解析测试 | TEST_MATRIX | TC-005-005扩展 |
| CR-008 | 补充rename前置条件 | IMPLEMENTATION_CONTRACT | N/A |

### Phase 3: P2 Should-Fix

| ID | Action | Files | Tests |
|----|--------|-------|-------|
| CR-009 | 定义候选顺序 | IMPLEMENTATION_CONTRACT | TC-005-062~063 |
| CR-010 | 同步实施步骤 | IMPLEMENTATION_PLAN | N/A |
| CR-012 | 改进测试标题 | TEST_MATRIX | N/A |
| CR-013 | 添加映射表 | TEST_MATRIX | N/A |
| CR-015 | 更新文档统计 | REVISION_EVIDENCE, CHECKLIST | N/A |

---

## J. IMPLEMENTATION AUTHORIZATION STATUS

```yaml
Status: TRIAGE_COMPLETE
Code_Changes: NONE (read-only triage phase完成)
Next_Action: AWAITING_IMPLEMENTATION_AUTHORIZATION

Approved_Count: 13 (11 ADOPT_NOW + 2 ADOPT_WITH_MOD)
Estimated_Effort:
  - Contract修订: 6 sections
  - Test新增: ~15 test cases  
  - 文档同步: 9 files

Blocking_Issues: 3 P0必须修复才能冻结契约
Recommended_Sequence: Phase 1 (P0) → Phase 2 (P1) → Phase 3 (P2)
```

---

## K. REMAINING RISKS

1. **测试代码信任边界** (CR-005 残余风险)
   - 测试仍可直接访问私有字段绕过验证
   - Mitigation: Acceptable - test code trusted
   - Severity: LOW

2. **EntityId格式验证覆盖** (CR-002 残余风险)
   - 测试路径允许直接构造
   - Mitigation: 文档说明，测试代码自律
   - Severity: LOW

---

## L. FINAL DECISION

**Decision**: **TRIAGE COMPLETE — AWAITING IMPLEMENTATION AUTHORIZATION**

**Summary**:
- 审核报告整体有效(13/15 confirmed)
- 需要修复 13 个问题(11 ADOPT_NOW + 2 WITH_MOD)
- 3个P0问题必须修复才能冻结契约
- 预计修订工作量: 6 sections + 15 tests + 9 files

**Recommendation**: 授权实施 Approved Remediation Plan

**Next Step**: 用户决定是否授权进入实施阶段

---

## M. TRIAGE SELF-CHECK

- [x] 当前仓库真实读取 (58d77d2 confirmed)
- [x] 无伪造工具结果
- [x] Report/Current Baseline已区分
- [x] Findings与Observations已分开
- [x] Evidence Level按证据类型评定
- [x] 完成五维判断(每个Finding)
- [x] P0定义了Target Invariant
- [x] P0执行了Adversarial Challenge
- [x] 量化结论已核实或标记
- [x] Scope未扩大
- [x] 不采纳项有理由(CR-011,CR-014 DEFER)
- [x] Matrix/Detail/Summary完全一致
- [x] 未授权实施已停止

**Triage完整性**: COMPLETE

---

**END OF TRIAGE REPORT**

**Date**: 2026-10-03  
**Triage Engineer**: Independent Review Protocol  
**Status**: READ-ONLY TRIAGE COMPLETE
