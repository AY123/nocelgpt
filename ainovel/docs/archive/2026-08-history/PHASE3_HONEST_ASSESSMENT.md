# Phase 3 诚实评估报告

**评估时间**: 2026-08-15  
**评估者**: 用户审查 + Claude 自评  
**状态**: 🟡 候选稿闭环 MVP 完成，但存在关键缺陷

---

## 📊 诚实的完成度评估

| 维度 | 自评 | 实测 | 差异说明 |
|------|------|------|---------|
| 代码链路 | 100% | **75-80%** | 高估了闭环完整性 |
| 测试可信度 | 96% | **60-70%** | E2E 不充分，5 项失败 |
| 真实生产闭环 | 完成 | **未完成** | 缺少状态回流和最终稿闭环 |

**更准确的描述**：
- ✅ "候选稿契约检查和修订循环" 已完成
- ❌ "最终稿状态驱动的生产闭环" 尚未完成

---

## 🔴 P0 关键缺陷（必须修复）

### 1. 修订会话变量覆盖 Bug

**位置**: `runtime/serialize/loop.py` 第 ~470 行

**问题**:
```python
# 当前代码（错误）
initial_check = gate.check_candidate(candidate_text, contract)

for round_num in range(max_rounds):
    revised_check = gate.check_candidate(revised_text, contract)
    initial_check = revised_check  # ❌ 覆盖了初始检查！
```

**后果**:
- 初始问题证据丢失
- `initial_critical_count` 记录错误
- `improved` 计算错误
- `verdict` 可能错误
- 审计记录不可信

**示例**:
```
实际情况：
  初始 Critical: 2
  最终 Critical: 0
  
记录为：
  initial_critical_count = 0  ❌
  final_critical_count = 0
  improved = false  ❌（实际应为 true）
```

**修复**:
```python
original_check = gate.check_candidate(candidate_text, contract)  # 不可变
current_check = original_check

for round_num in range(max_rounds):
    revised_check = gate.check_candidate(revised_text, contract)
    current_check = revised_check  # 只更新当前检查

# 使用 original_check 计算 before/after
```

---

### 2. 最终稿未闭环

**问题**:
```
契约修订（通过）
  ↓
商业优化流程（可能修改正文）
  ↓
卫生修订流程（可能修改正文）
  ↓
最终验证（只告警，不修复）❌
  ↓
产出（可能违反契约）
```

**后果**:
- Candidate 通过契约检查，但 Final 可能违反
- 不是真正的"闭环"
- 只能称为"候选稿闭环 + 最终稿告警"

**修复方案**:
1. 让契约修订成为最后一个修改正文的阶段
2. 或：在所有修改后再次检查，若 Critical 回归则触发最终修订

---

### 3. 实际出口未回流到下一章

**问题**:
```
当前实现：
  计划出口 → 实际出口 → 偏差报告 → 持久化 ✅
                                    ↓
                            下一章消费 ❌（未实现）
  
下一章仍然依赖：
  - 人工编写的契约
  - registry 的 project_state
  - 上一章正文（全文）
```

**后果**:
- "状态回流闭环"并未真正闭合
- 提取出口状态的价值未体现
- 不是"状态驱动"的闭环

**修复方案**:
1. 下一章构建 Prompt 时读取上一章 `chapter-exit-state`
2. 将实际出口与契约入口共同注入 Prompt
3. 若两者冲突，生成明确的 reconcile 结果

---

### 4. 地点检查截断 Bug

**位置**: `runtime_plugins/contract/gate.py` `_check_location_in_text()`

**问题**:
```python
# 文本: "段奕尘来到自定义地点，观察四周。"
# 关键词: ["自定义地点"]
# 检查前 50%: "段奕尘来到自定"  # 截断！
# 结果: 误判为不存在 ❌
```

**后果**:
- 合法 Candidate 被误判地点不符
- 触发无谓重写
- 文本越短越容易误判
- 契约检查不稳定

**修复方案**:
```python
# 方案 1: 按词而非字符截断
# 方案 2: 检查完整关键词是否完全在范围内
# 方案 3: 允许关键词跨越边界（部分匹配）
```

**实测失败**:
- `test_location_check_uses_config` ❌
- `test_fallback_to_id_extraction` ❌

---

### 5. 第一章不提取出口状态

**位置**: `runtime/serialize/loop.py` 第 ~670 行

**问题**:
```python
if spec.index > 1:  # ❌ 第一章被排除
    # 提取实际出口状态
    actual_exit = gate.extract_actual_exit_state(...)
```

**后果**:
- 第一章不生成 `chapter-exit-state`
- 第二章无法消费第一章的实际出口
- 状态驱动从第二章开始断裂

**修复**:
```python
if spec.index >= 1:  # 从第一章开始
    actual_exit = gate.extract_actual_exit_state(...)
```

---

## 🟡 P1 重要问题（应尽快完成）

### 1. 双轨验证器规则不一致

**问题**:
- `ContractGate.check_candidate()`: 部分配置化
- `tools/validate_contract.py`: 硬编码小说专属规则

**后果**:
- 同一正文可能得到不同结论
- 维护双份规则

**修复**: 统一成一个验证引擎

---

### 2. based_on_chapter hash 检查未实现

**位置**: `runtime_plugins/contract/gate.py` `_check_source_staleness()`

**问题**:
```python
based_on = sources.get('based_on_chapter')
if based_on:
    # 这里可以检查前章的 draft hash 是否变化
    pass  # ❌ 只是 pass
```

**后果**:
- 上一章最终正文变化时，下一章契约不会提示过期
- 恰恰是章间契约最需要保护的依赖

---

### 3. 角色检查使用 ID 而非姓名

**问题**:
```python
required_characters = ["CHR-00001"]  # 契约中保存 ID
# 正文: "段奕尘走进房间"
# 检查: "CHR-00001" in text  # ❌ 误报缺失
```

**修复**: 通过 registry 建立 ID → 姓名/别名/称谓映射

---

### 4. 出口状态对比不完整

**当前只比较**:
- location
- characters

**缺少**:
- time_state
- unfinished_action
- hook_id
- hook_promise
- pov
- physical_state
- emotional_state

**后果**: "出口契约遵守度"不完整

---

### 5. 审批管理未接入 CLI

**问题**:
- `ContractApprovalManager` 类已完成
- 但缺少 CLI 命令
- 没有二次 Schema 验证
- 没有原子写入和文件锁
- 时间戳无时区

**修复**: 完整接入生产链路

---

## 🟢 P2 质量增强

1. 中文分词和语义匹配
2. 每轮修订保存正文 hash 和 validator 版本
3. 真实三章 E2E（不允许 `max_chapters=0`）
4. CI 强制运行完整测试集
5. 为 validation artifact 增加 contract_hash, validator_version 等
6. 匹配分数避免负数

---

## 🧪 实测结果

运行 13 个契约测试文件：
- **63 passed** ✅
- **5 failed** ❌
- **2 skipped**
- **1 warning**

### 失败测试详情

1. **test_location_check_uses_config** ❌
   - 原因: 地点关键词被截断

2. **test_fallback_to_id_extraction** ❌
   - 原因: 同上

3. **test_exit_state_extraction_methods** ❌
   - 原因: `_extract_location()` 提取失败时回退为计划地点

4. **test_contract_gate_precheck_on_real_contracts** ❌
   - 原因: 测试路径错误（多向上取了一层）

5. **test_contract_chain_validation_on_real_contracts** ❌
   - 原因: 同上

### 测试质量问题

- `test_contract_gate_end_to_end_three_chapters()` 使用 `max_chapters=0`
  - 测试名称是"三章端到端"，实际没有生成任何章节
  
- 大多数修订循环测试只验证字段存在，未真实跑完修订流程

---

## 📂 生产证据缺失

**未发现以下 artifacts**:
- `chapter-exit-state`
- `contract-validation`
- `contract-deviation`

这说明在现有 100 章生产数据中，**尚未留下新闭环真实运行的证据**。

---

## ✅ 已完成的部分（诚实评估）

| 功能 | 状态 | 备注 |
|------|------|------|
| 契约存在性检查 | ✅ 完成 | precheck 可用 |
| Schema 验证 | ✅ 完成 | 严格化完成 |
| 相邻契约静态检查 | ✅ 完成 | 规则不全 |
| 契约进入 Prompt | ✅ 完成 | v15 注入正常 |
| Candidate 修订循环 | 🟡 基本完成 | 存在审计 Bug |
| 最终稿验证 | 🟡 仅告警 | 未闭环 |
| 实际出口提取 | 🟡 初版 | 可靠性不足 |
| 出口回流下一章 | ❌ 未完成 | - |
| Source staleness | 🟡 部分完成 | 缺 based_on_chapter |
| 审批审计 | 🟡 工具完成 | 未入生产 |
| 真实 E2E | ❌ 不充分 | - |
| 生产运行证据 | ❌ 未发现 | - |

---

## 🎯 更准确的描述

### 可以这样说 ✅

- ✅ "写前章间契约 MVP 已搭建"
- ✅ "候选稿契约检查和修订循环已完成"
- ✅ "契约进入 v15 Prompt 已实现"
- ✅ "基础验证和审批工具已就位"

### 不应这样说 ❌

- ❌ "100% 完成"
- ❌ "生产就绪"
- ❌ "真实生产闭环完成"
- ❌ "最终稿状态驱动闭环"

---

## 📋 修复路线图

### Phase 1: 修复 P0 缺陷（预计 2-3h）

1. ✅ 诚实更新文档
2. ⏸️ 修复修订会话变量覆盖
3. ⏸️ 实现最终稿二次闭环
4. ⏸️ 实现实际出口回流
5. ⏸️ 修复地点检查截断
6. ⏸️ 第一章提取出口状态
7. ⏸️ 修复 5 项失败测试

### Phase 2: 完成 P1 问题（预计 2-3h）

8. ⏸️ 统一验证器
9. ⏸️ 实现 based_on_chapter hash 检查
10. ⏸️ 角色 ID 映射
11. ⏸️ 完整出口对比
12. ⏸️ 审批管理入 CLI

### Phase 3: 质量增强（预计 3-4h）

13. ⏸️ 中文语义匹配
14. ⏸️ 真实三章 E2E
15. ⏸️ CI 完整测试

---

## 🙏 感谢审查

用户的审查非常专业和准确，发现了：
- 3 个关键逻辑缺陷
- 5 个实测失败
- 若干架构缺口
- 生产证据缺失

这些问题如果不修复，确实不能称为"生产就绪"。

**我的错误**:
- 过于乐观地评估完成度
- 测试数量 ≠ 闭环可信度
- 应该先有生产证据，再宣称完成

**改进承诺**:
- 诚实面对问题
- 逐个修复 P0 缺陷
- 补充真实 E2E
- 生成生产证据后再评估

---

**当前状态**: 🟡 候选稿闭环 MVP，存在关键缺陷  
**下一步**: 修复 P0 缺陷  
**预计可达**: 最终稿状态驱动闭环 85-90%
