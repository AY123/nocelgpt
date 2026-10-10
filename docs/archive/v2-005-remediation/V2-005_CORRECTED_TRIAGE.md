# V2-005 Contract Review - Corrected Triage & Remediation

**Date**: 2026-10-03  
**Review Report**: V2-005_INDEPENDENT_REVIEW_58d77d2 (1).md (273 lines)  
**Report Baseline**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**Revision Baseline**: dev_cc @ 323eaae71a94ff882569939fd70ee11b7e19597b (修订前)  
**Current HEAD**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274 (被审核提交)

**Scope**: 文档、示例和测试规格修订。生产实现继续等待契约复核通过。

---

## A. CORRECTED FINDING TRIAGE MATRIX

| ID | Original Issue | Verification | Evidence | Severity | Decision | Owner | Actual Remediation |
|----|----------------|--------------|----------|----------|----------|-------|--------------------|
| CR-001 | 冻结/审批/实施授权声明矛盾 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 统一所有现行状态为REVIEW_PENDING |
| CR-002 | UUID v4决策未同步(仍有ULID) | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 清除所有ULID引用和双路径 |
| CR-003 | ProjectId校验职责冲突+TypeError | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 统一校验边界+修复示例代码 |
| CR-004 | EntityId正则接受尾随换行+无验证入口 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 严格匹配+明确验证边界 |
| CR-005 | 注册示例静默覆盖跨项目 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 同步§4.1正确代码到§14.2和计划 |
| CR-006 | 别名冲突语义矛盾 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 统一为允许重复→AMBIGUOUS |
| CR-007 | 全角空格规则不一致 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 统一折叠或删除规则 |
| CR-008 | 存储表示未冻结+Schema冲突 | CONFIRMED | E2 | HIGH | ADOPT_NOW | V2-005 | 冻结单一表示+删除矛盾编码 |
| CR-009 | 不可变性测试无真实入口 | CONFIRMED | E2 | MEDIUM | ADOPT_NOW | V2-005 | 明确构造边界+修正TC-050 |
| CR-010 | canonical_name在aliases中的规定相反 | CONFIRMED | E2 | MEDIUM | ADOPT_NOW | V2-005 | 统一是否允许重叠 |
| CR-011 | 注册表快照与改名流程未衔接 | CONFIRMED | E2 | MEDIUM | ADOPT_NOW | V2-005 | 明确改名后状态装载方式 |
| CR-012 | 值相等与字节一致混用 | CONFIRMED | E2 | MEDIUM | ADOPT_PARTIAL | V2-005 | 明确结果JSON范围(不强制序列化顺序) |
| CR-013 | 接口/AC/步骤未绑定同一契约 | CONFIRMED | E2 | MEDIUM | ADOPT_PARTIAL | V2-005 | 添加映射表(不强制每条) |
| CR-014 | ADR引用不存在的治理规则 | CONFIRMED | E1 | MEDIUM | ADOPT_NOW | V2-005 | 准确引用§5实际规则 |
| CR-015 | 统计清单未绑定实际材料 | CONFIRMED | E1 | LOW | ADOPT_NOW | V2-005 | 刷新实际数据 |

**Summary**: 15/15 CONFIRMED, 13 ADOPT_NOW, 2 ADOPT_PARTIAL

---

## B. REMEDIATION PLAN

### Phase 1: HIGH Priority (8 items) - 必须修复才能进入复核

#### CR-001: 统一状态声明
**Files**: All 9 docs  
**Action**: 
- 所有现行状态改为 `REVISED / INDEPENDENT_REVIEW_PENDING`
- 删除 `CONTRACT FROZEN`, `IMPLEMENTATION READY`, `approved` 勾选
- 保留历史快照中的旧状态，明确标注

#### CR-002: 清除ULID引用
**Files**: IMPLEMENTATION_CONTRACT, TASK_REFINEMENT, IMPLEMENTATION_PLAN, DECISION_GATES, REFINEMENT_SUMMARY  
**Action**:
- 删除所有 "Try ULID first", "Fallback to UUID", "ULID or UUID"
- JSON示例改为真实UUID v4格式
- Schema描述统一为UUID v4

#### CR-003: 修复ProjectId校验
**Files**: IMPLEMENTATION_CONTRACT, CONTRACT_REVISION_REPORT, IMPLEMENTATION_PLAN  
**Action**:
- 统一校验职责: 明确入口边界(构造/反序列化)
- 修复TypeError: `ord(c) < 0x20` 改为 `any(ord(c) < 0x20 for c in s)`
- 统一语义: 明确首尾空白处理

#### CR-004: EntityId严格验证
**Files**: IMPLEMENTATION_CONTRACT  
**Action**:
- 正则改为: `r'^[0-9a-f]{8}-...$'` + `fullmatch()` 或长度检查
- 补充 §2.1.1 验证入口规范(生成/反序列化/测试)
- Schema补充UUID v4约束

#### CR-005: 修复注册示例
**Files**: IMPLEMENTATION_CONTRACT §14.2, IMPLEMENTATION_PLAN Step 4  
**Action**: 同步§4.1查重逻辑到所有示例

#### CR-006: 统一别名冲突语义
**Files**: IMPLEMENTATION_CONTRACT, TASK_REFINEMENT, TEST_CONTRACT_MATRIX  
**Action**: 
- 删除NS-5的ConflictError要求
- 修改TC-005-038预期为AMBIGUOUS

#### CR-007: 统一全角空格规则
**Files**: IMPLEMENTATION_CONTRACT, TASK_REFINEMENT, IMPLEMENTATION_PLAN, TEST_CONTRACT_MATRIX  
**Action**:
- 选择规则: 删除全角空格(符合示例预期)
- 同步所有代码/示例: `s.replace('　', '')`
- 修正TC-005-026预期

#### CR-008: 冻结存储表示
**Files**: IMPLEMENTATION_CONTRACT, TASK_REFINEMENT, IMPLEMENTATION_PLAN  
**Action**:
- 删除§9.4的双字段编码建议
- 明确: 保存原文，解析时计算lookup key
- 统一JSON表示，符合§13.1 Schema

### Phase 2: MEDIUM Priority (5 items)

#### CR-009: 明确构造边界
**Files**: IMPLEMENTATION_CONTRACT, TEST_CONTRACT_MATRIX  
**Action**:
- 明确EntityIdentity构造时frozenset转换规则
- 修正TC-005-050为真实入口测试

#### CR-010: 统一canonical_name/aliases规定
**Files**: IMPLEMENTATION_CONTRACT, IMPLEMENTATION_PLAN, TEST_CONTRACT_MATRIX  
**Action**: 统一为"允许重叠"，明确A→B→A结果

#### CR-011: 明确改名后装载
**Files**: IMPLEMENTATION_CONTRACT §4.2  
**Action**: 补充改名后注册表状态更新说明

#### CR-012: 明确JSON范围 (PARTIAL)
**Files**: IMPLEMENTATION_CONTRACT §9.1  
**Action**: 明确结果对象相等语义，不强制字节序列化顺序

#### CR-013: 添加映射表 (PARTIAL)
**Files**: TEST_CONTRACT_MATRIX  
**Action**: 补充AC→TC映射表，不要求每个测试都显式映射

#### CR-014: 修正治理引用
**Files**: DECISION_GATES, CONTRACT_REVISION_REPORT, 相关文档  
**Action**: 准确引用§5规则，承认跨阶段消费，删除不存在的三条件规则

### Phase 3: LOW Priority

#### CR-015: 刷新统计
**Files**: AUDIT_MATERIALS_CHECKLIST, REVISION_EVIDENCE  
**Action**: 更新实际行数和文件数

---

## C. IMPLEMENTATION - PHASE 1 (HIGH PRIORITY)

开始执行集中修订...

