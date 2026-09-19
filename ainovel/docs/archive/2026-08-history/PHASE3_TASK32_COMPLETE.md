# Phase 3 Task 3.2 Complete ✅

**Task**: 修改run_serial集成Contract Gate  
**Date**: 2026-08-14  
**Status**: ✅ Complete

---

## 实施内容

### 1. 修改 `run_serial` 函数签名

**文件**: `AI-Novel-Runtime/runtime/serialize/loop.py`

新增参数：
```python
contracts_dir: Optional[str | Path] = None,
enable_contract_gate: bool = False,
strict_contract_mode: bool = False,
```

**语义**：
- `contracts_dir`: 契约文件目录，默认为 `project_path/contracts`
- `enable_contract_gate`: 是否启用Contract Gate检查，默认False
- `strict_contract_mode`: 严格模式（契约失败抛异常），默认False（跳过章节）

---

### 2. 集成 Precheck 逻辑

**位置**: `loop.py:622-679` (在章节循环内，budget检查之后)

**触发条件**:
```python
if enable_contract_gate and prompt_version == "15.0.0":
```

**执行流程**:
1. 动态加载 `runtime_plugins.contract` 模块
2. 初始化 `ContractGate` 实例
3. 调用 `gate.precheck(spec.index)` 验证契约
4. 契约失败时：
   - **严格模式**: 抛出异常，终止serial
   - **非严格模式**: 跳过此章节，继续运行

**ADR-003 遵守**: 
- 非严格模式下，契约失败**跳过**章节而不是杀死serial
- 契约检查是 **可选** 的（enable_contract_gate=False时完全不触发）

---

### 3. 更新文档字符串

**新增段落**:
```
With the v15 template ("15.0.0", Phase 3 Contract Gate) each chapter is
verified against an AUTHORED CONTRACT before generation begins. When
`enable_contract_gate` is True and prompt_version is "15.0.0", the precheck
verifies the chapter has a valid, approved contract file (chapter_N_contract.json)
before building the task package. Chapters without valid contracts are SKIPPED
(ADR-003: orchestration never kills the serial). In strict_contract_mode, a
contract failure raises; in non-strict (default), it skips and continues.
When contracts_dir is absent, defaults to project_path/contracts.
```

---

### 4. 测试覆盖

**文件**: `tests/test_contract_gate_integration.py`

**测试用例**:
1. ✅ `test_contract_gate_disabled_by_default` - 默认不启用
2. ✅ `test_contract_gate_only_on_v15` - 仅v15触发
3. ✅ `test_contract_gate_parameters_accepted` - 参数接受测试
4. ✅ `test_contract_gate_integration_wiring` - 结构化测试（签名/文档）

**测试结果**: 4 passed in 0.17s

---

## 架构决策

### ✅ 遵循 ADR-003
- Precheck是**可选gate**（enable_contract_gate控制）
- 非严格模式下**跳过**而非终止serial
- 与现有的budget breaker、M7 gate对齐

### ✅ 向后兼容
- `enable_contract_gate=False`（默认）：完全不触发，行为与之前byte-identical
- v1-v14版本：不受影响
- 新增参数都有合理默认值

### ✅ 延迟导入
- `runtime_plugins.contract` 只在需要时导入
- 避免未安装Contract Gate时的导入错误

---

## 集成点验证

| 验收标准 | 状态 | 验证方式 |
|---------|------|---------|
| 新增参数可用 | ✅ | 签名测试通过 |
| 默认不启用 | ✅ | enable_contract_gate=False测试通过 |
| 仅v15触发 | ✅ | 版本条件测试通过 |
| 文档完整 | ✅ | docstring包含v15说明 |
| 非侵入式 | ✅ | 所有现有测试未受影响 |

---

## 后续工作

### Task 3.3: 生成后验证 (待实施)
- 在章节生成后调用 `gate.validate()`
- 保存验证报告到derived artifacts
- 失败时记录警告（不阻止）

### Task 3.4: CLI集成 (待实施)
- 添加 `--enable-contract-gate` CLI参数
- 添加 `--contracts-dir` CLI参数
- 添加 `--strict-contract-mode` CLI参数

### Task 3.5: 端到端测试 (待实施)
- 使用真实Contract Gate模块的集成测试
- 边界条件测试

---

## 提交信息

```
feat: Phase 3 Task 3.2 - Contract Gate集成到run_serial

集成点:
- 新增3个参数: contracts_dir, enable_contract_gate, strict_contract_mode
- v15 prompt + enable_contract_gate触发precheck
- 非严格模式跳过失败章节（ADR-003）
- 向后兼容（默认关闭）

测试:
- 4个集成测试全部通过
- 签名、文档、参数验证完整

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

**Task 3.2 完成时间**: 2小时  
**预计 vs 实际**: 预计2小时 / 实际2小时 ✅  
**下一步**: Task 3.3 生成后验证
