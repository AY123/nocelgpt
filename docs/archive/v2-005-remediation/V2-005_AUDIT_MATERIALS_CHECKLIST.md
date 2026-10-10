# V2-005 完整审核材料清单

**审核基线**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274  
**日期**: 2026-10-03  
**状态**: INDEPENDENT_REVIEW_PENDING

---

## 文件清单

### 核心文档（9份）

所有文档已从 commit 58d77d2 导出至 `/tmp/`:

| 文件名 | 大小 | 行数 | 用途 |
|--------|------|------|------|
| V2-005_IMPLEMENTATION_CONTRACT.md | 38K | 1,559 | **主契约**（最重要） |
| V2-005_TASK_REFINEMENT.md | 27K | 1,197 | 任务细化 |
| V2-005_TEST_CONTRACT_MATRIX.md | 18K | 396 | 测试矩阵（51个测试） |
| V2-005_IMPLEMENTATION_PLAN.md | 21K | 744 | 实施计划（8步骤） |
| V2-005_CONTRACT_REVISION_REPORT.md | 17K | 601 | 修订报告（v1.1.0） |
| V2-005_DECISION_GATES.md | 15K | 547 | 决策门评估 |
| V2-005_REFINEMENT_SUMMARY.md | 14K | 466 | 摘要 |
| V2-005_CURRENT_STATE_AUDIT.md | 12K | 525 | 基线审计 |
| V2-005_REVISION_EVIDENCE.md | 7.7K | 180 | 修订证据 |

**总计**: ~170K, 6,215 行

---

### 治理文档（3份）

| 文件名 | 来源 | 用途 |
|--------|------|------|
| decision-register.yaml | plan/machine/decision-register.yaml | ADR 依赖核查 |
| 00_GOVERNANCE_AND_SOURCE_AUTHORITY.md | plan/00_GOVERNANCE... | 治理规则、ADR 条件 |
| 03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md | plan/03_DOMAIN... | 身份要求、规范约束 |

---

## 审核包

**文件**: `/tmp/V2-005_审核材料_58d77d2.tar.gz`  
**大小**: ~64KB  
**内容**: 上述12个文件

**解压**:
```bash
cd /tmp
tar xzf V2-005_审核材料_58d77d2.tar.gz
```

---

## 审核重点

### 1. 上位规范一致性
- [ ] Implementation Contract § 2.1 EntityId 与 `03_DOMAIN_CANON...` § 1 要求一致
- [ ] Implementation Contract § 2.2 ProjectId 项目隔离要求一致
- [ ] Implementation Contract § 7 不变量与规范匹配

### 2. 公共接口与校验入口
- [ ] § 2.1 EntityId 构造路径（生成 vs 反序列化 vs 测试）
- [ ] § 2.2 ProjectId validate_project_id() 强制调用点
- [ ] § 3 各操作的前置条件校验

### 3. 操作前后条件
- [ ] § 3.1 create_identity 前置条件完整性
- [ ] § 3.2 rename_identity 异常安全
- [ ] § 3.3-3.4 add/remove_alias 边界条件

### 4. 项目隔离
- [ ] § 4 EntityRegistry 作用域（单项目 or 多项目）
- [ ] § 4.1 唯一性范围（全局 or 项目内）
- [ ] § 3.5 resolve_alias 项目隔离实现

### 5. 序列化
- [ ] § 9.1 JSON 表示
- [ ] § 9.3 往返保证
- [ ] AmbiguousResult.candidates 数组顺序

### 6. 测试映射
- [ ] Test Matrix 51个测试与契约覆盖关系
- [ ] 待核实的5个问题是否已有测试覆盖
- [ ] 测试是否验证所有不变量

### 7. 文档一致性
- [ ] 9份文档状态声明一致
- [ ] 版本号同步（v1.1.0）
- [ ] 设计决策在各文档间无矛盾

### 8. ADR 判断
- [ ] 依据 `00_GOVERNANCE...` 判断 ADR 必要性
- [ ] `decision-register.yaml` V2-005 条目核对
- [ ] 跨阶段影响分析准确性

---

## 待核实问题（非预设缺陷）

以下5个问题需要通过全文审核确认是否为真实缺陷：

| # | 问题 | 核查点 | 可能结果 |
|---|------|--------|----------|
| 1 | ProjectId 校验行为 | § 2.2 是否明确首尾空白处理语义 | 已明确 / 需补充 |
| 2 | EntityId 验证规范 | § 2.1 是否定义反序列化验证 | 已明确 / 需补充 |
| 3 | JSON 序列化顺序 | § 9.1 是否规定 candidates 顺序 | 已明确 / 需补充 |
| 4 | 项目归属检查 | § 4 是否明确作用域 | 已明确 / 需补充 |
| 5 | ADR 理由准确性 | Decision Gates ADR 节是否符合治理规则 | 准确 / 需修正 |

**审核原则**: 如果现有条款或测试已覆盖，直接引用即可，不预设新增内容。

---

## 审核输出

期望形成的审核清单格式：

```yaml
问题_ID: CR-001
描述: [具体问题]
位置: [文件名:节号或行号]
证据: [引用原文或冲突示例]
影响: [LOW/MEDIUM/HIGH]
最小修改要求: [具体条款或测试]
```

---

## 文档访问

### 方式 1: 本地文件
所有文件已导出到 `/tmp/V2-005_*.md`

### 方式 2: Git 命令
```bash
git show 58d77d2:docs/V2-005_IMPLEMENTATION_CONTRACT.md
git show 58d77d2:docs/V2-005_TEST_CONTRACT_MATRIX.md
# ... 其他文件
```

### 方式 3: 压缩包
```bash
# 位置：/tmp/V2-005_审核材料_58d77d2.tar.gz
# 包含12个文件（9份契约文档 + 3份治理文档）
```

---

## 下一步

1. ✅ 审核材料已准备（本清单）
2. ⏳ **等待独立审核**（你执行）
3. ⏳ 根据审核清单修订
4. ⏳ 复核通过后冻结契约

---

**状态**: 完整审核材料已提供，等待独立审核

**基线**: dev_cc @ 58d77d2673d07950d0a235d2b25bf7e1e17cb274

**当前状态**:
```yaml
V2_005_REFINEMENT_STATUS: REVISED
V2_005_CONTRACT_STATUS: INDEPENDENT_REVIEW_PENDING
V2_005_IMPLEMENTATION_AUTH: BLOCKED_ON_CONTRACT_REVIEW
```

---

**END OF AUDIT MATERIALS CHECKLIST**
