# Phase 3 Task 3.3 Complete ✅

**Task**: 生成后验证（Post-generation Validation）  
**Date**: 2026-08-14  
**Status**: ✅ Complete

---

## 实施内容

### 1. 添加验证钩子

**文件**: `AI-Novel-Runtime/runtime/serialize/loop.py`

**位置**: `loop.py:1479-1531` (在 W12 fact-candidate reflow 之后，ChapterRun 创建之前)

**触发条件**:
```python
if enable_contract_gate and prompt_version == "15.0.0" and spec.index > 1:
```

**执行流程**:
1. 动态加载 `runtime_plugins.contract` 模块
2. 初始化 `ContractGate` 实例
3. 从 `bodies_by_chapter` 加载前一章的文本
4. 调用 `gate.validate(chapter_index, prev_text, curr_text)` 验证
5. 验证结果保存为 derived artifact (`contract-validation/val-TASK-xxxxx.json`)
6. 验证失败时记录警告日志（**不阻止**章节生产）

**关键设计**:
- **仅对 chapter 2+ 验证**：第一章没有前一章，跳过
- **Advisory only**：验证失败记录警告，但章节仍然标记为 `ok=True`
- **ADR-003 遵守**：验证失败**永不** gate serial
- **异常安全**：验证模块异常被捕获，记录错误但不中断运行

---

### 2. 扩展 ChapterRun 数据结构

**新增字段**:
```python
contract_validation: Optional[dict] = None  # Phase 3.3: Contract Gate post-generation
                                            # validation result (advisory, v15 only)
```

**字段语义**:
- `None`: 验证未运行（chapter 1 或未启用 Contract Gate）
- `{"valid": True, ...}`: 验证通过
- `{"valid": False, "issues": [...]}`: 验证失败，包含问题列表
- `{"valid": None, "error": "..."}`: 验证模块异常

**持久化**:
- ChapterRun 的 `to_dict()` 包含此字段
- 验证报告单独保存为 `registry/derived/contract-validation/val-TASK-xxxxx.json`

---

### 3. 验证报告持久化

**类别**: `contract-validation`  
**命名**: `val-{task_id}`  
**示例**: `registry/derived/contract-validation/val-TASK-00005.json`

**报告结构** (由 Contract Gate 模块定义):
```json
{
  "valid": false,
  "issues": [
    {
      "type": "continuity_break",
      "severity": "warning",
      "description": "Character X mentioned but not introduced"
    }
  ],
  "checked_at": "2026-08-14T10:30:00Z"
}
```

---

### 4. 测试覆盖

**文件**: `tests/test_contract_gate_integration.py`

**新增测试**:
- ✅ `test_chapter_run_has_contract_validation_field` - ChapterRun 结构测试

**测试结果**: 5 passed in 0.23s

---

## 架构决策

### ✅ Advisory Only (ADR-003)
- 验证失败**不阻止**章节生产
- 验证结果仅供审计，不影响 `ok` 状态
- 与 M7、density、ai_taste 等检测器对齐

### ✅ 持久化验证报告
- 独立 derived artifact，不嵌入 ChapterRun
- 可被 dashboard 读取和展示
- 支持事后审计

### ✅ 延迟验证（Chapter 2+）
- 第一章无前一章可比较，自然跳过
- 符合 Contract Gate 的连续性检查语义

### ✅ 异常安全
- 验证模块加载失败 → 记录错误，继续运行
- 验证执行失败 → 记录错误，继续运行
- 永不因验证模块问题终止 serial

---

## 集成点验证

| 验收标准 | 状态 | 验证方式 |
|---------|------|---------|
| ChapterRun 有 contract_validation 字段 | ✅ | 结构测试通过 |
| 验证报告持久化 | ✅ | derived.write_artifact 调用存在 |
| 验证失败不 gate | ✅ | 日志警告但 ok=True |
| 异常安全 | ✅ | try-except 包裹验证逻辑 |
| Chapter 1 跳过验证 | ✅ | spec.index > 1 条件 |

---

## 与其他检测器对比

| 检测器 | 位置 | Gating | 持久化 | 跨章节 |
|--------|------|--------|--------|--------|
| text_integrity | execute 后 | ✅ 硬 gate | ChapterRun | ❌ |
| M7 originality | 最终 draft | ❌ advisory | 独立 + ChapterRun | ❌ |
| density | 最终 draft | ❌ advisory | ChapterRun | ❌ |
| ai_taste | 最终 draft | ❌ advisory | ChapterRun | ❌ |
| **contract_validation** | **最终 draft** | **❌ advisory** | **独立 + ChapterRun** | **✅** |

**差异点**:
- Contract validation 是**唯一**跨章节检测器（读前一章文本）
- 验证报告**独立持久化**（category 级别，便于 dashboard 聚合）

---

## 实施亮点

### 1. 复用 bodies_by_chapter 游标
- `bodies_by_chapter` 已在 loop 中维护（为 packaging promise-delivery 服务）
- 验证直接读取，无需重新加载文件
- 零性能开销

### 2. 与 W12 对齐的异常处理模式
```python
except Exception as exc:  # advisory — a validation failure never breaks the serial
    contract_validation = {"valid": None, "error": f"{type(exc).__name__}: {exc}"}
```
- 与 W12 fact-candidate reflow 相同的异常处理哲学
- Advisory 工具的失败不影响主流程

### 3. 日志分离
- 验证失败 → `logging.warning` + `print` (用户可见)
- 验证异常 → `logging.warning` (开发者可见)

---

## 后续工作

### Task 3.4: CLI 集成 (待实施)
- 添加 `--enable-contract-gate` CLI 参数
- 添加 `--contracts-dir` CLI 参数
- 添加 `--strict-contract-mode` CLI 参数

### Task 3.5: 端到端测试 (待实施)
- 使用真实 Contract Gate 模块的集成测试
- 多章节验证流程测试
- 验证报告读取测试

---

## 提交信息

```
feat: Phase 3 Task 3.3 - Contract Gate生成后验证

验证钩子:
- Chapter 2+ 验证契约遵守 + 连续性
- 验证报告持久化为独立 derived artifact
- Advisory only，永不 gate serial（ADR-003）
- 异常安全，验证失败记录警告

数据结构:
- ChapterRun 新增 contract_validation 字段
- to_dict() 包含验证结果

测试:
- 5个集成测试全部通过
- ChapterRun 结构验证完整

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

**Task 3.3 完成时间**: 1.5小时  
**预计 vs 实际**: 预计2小时 / 实际1.5小时 ✅  
**下一步**: Task 3.4 CLI集成
