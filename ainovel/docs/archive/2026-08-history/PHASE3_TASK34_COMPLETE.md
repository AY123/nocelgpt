# Phase 3 Task 3.4 Complete ✅

**Task**: CLI集成（CLI Integration）  
**Date**: 2026-08-14  
**Status**: ✅ Complete

---

## 实施内容

### 1. 添加 CLI 参数

**文件**: `AI-Novel-Runtime/runtime/cli.py`

**位置**: `cli.py:3042-3058` (在 `--w12-extract` 之后)

**新增参数**:

#### `--enable-contract-gate`
```bash
--enable-contract-gate
```
- **类型**: `action="store_true"` (flag)
- **默认值**: `False`
- **说明**: 启用 Contract Gate（Phase 3）。仅在 `--prompt-version 15.0.0` 时生效。
- **行为**: 
  - Precheck: 验证章节契约，跳过无效章节
  - Validation: 生成后验证，advisory only

#### `--contracts-dir PATH`
```bash
--contracts-dir /path/to/contracts
```
- **类型**: `metavar="PATH"`
- **默认值**: `None` (使用 `PROJECT/contracts`)
- **说明**: 契约文件目录（`chapter_N_contract.json`）
- **仅在**: `--enable-contract-gate` 启用时使用

#### `--strict-contract-mode`
```bash
--strict-contract-mode
```
- **类型**: `action="store_true"` (flag)
- **默认值**: `False`
- **说明**: 严格模式 - precheck 失败抛异常而非跳过章节
- **警告**: 可能中止 serial 运行
- **仅在**: `--enable-contract-gate` 启用时有意义

---

### 2. 参数传递到 run_serial

**位置**: `cli.py:2191-2223`

**新增行**:
```python
contracts_dir=getattr(args, "contracts_dir", None),
enable_contract_gate=getattr(args, "enable_contract_gate", False),
strict_contract_mode=getattr(args, "strict_contract_mode", False),
```

**模式对齐**:
- 使用 `getattr(args, ...)` 模式，与其他可选参数一致
- 提供明确的默认值（`None` / `False`）

---

### 3. 输出显示增强

**位置**: `cli.py:2240-2252`

**新增输出**:
```python
if c.contract_validation:
    if c.contract_validation.get("error"):
        line += f"  contract=error"
    elif c.contract_validation.get("valid") is False:
        issue_count = len(c.contract_validation.get("issues", []))
        line += f"  contract=invalid({issue_count})"
    elif c.contract_validation.get("valid") is True:
        line += f"  contract=ok"
```

**示例输出**:
```
  [ok ] ch  5 EVT-00005 stage=done  draft=a3f8...  contract=ok
  [ok ] ch  6 EVT-00006 stage=done  draft=b2e1...  contract=invalid(2)
  [SKIP] ch  7 EVT-00007 stage=contract-check-failed  (Contract Gate precheck failed: ...)
```

---

### 4. 测试覆盖

**文件**: `tests/test_contract_gate_cli.py`

**测试用例**:
1. ✅ `test_cli_help_shows_contract_gate_options` - 帮助文本包含新参数
2. ✅ `test_cli_accepts_contract_gate_flags` - 参数定义存在
3. ✅ `test_contract_gate_cli_integration_wiring` - 参数传递到 run_serial

**测试结果**: 3 passed in 0.31s

---

## 使用示例

### 基础用法
```bash
python runtime/cli.py serial run \
    --project . \
    --standard-root ../AI-Novel-Standard \
    --prompt-version 15.0.0 \
    --enable-contract-gate
```

### 指定契约目录
```bash
python runtime/cli.py serial run \
    --project . \
    --standard-root ../AI-Novel-Standard \
    --prompt-version 15.0.0 \
    --enable-contract-gate \
    --contracts-dir ./my-contracts
```

### 严格模式
```bash
python runtime/cli.py serial run \
    --project . \
    --standard-root ../AI-Novel-Standard \
    --prompt-version 15.0.0 \
    --enable-contract-gate \
    --strict-contract-mode
```

---

## 架构决策

### ✅ 与现有参数对齐
- 使用相同的 `getattr(args, ...)` 模式
- 遵循相同的命名约定（kebab-case CLI → snake_case 代码）
- flag 参数使用 `action="store_true"`

### ✅ 帮助文本完整
- 每个参数都有详细的 `help` 说明
- 说明了触发条件（v15.0.0）
- 说明了行为（skip vs raise）
- 引用了 ADR-003

### ✅ 输出友好
- 验证结果简洁显示（`contract=ok` / `contract=invalid(N)`）
- 与 M7、W12 等其他检测器输出对齐
- 错误情况明确标记

---

## 集成点验证

| 验收标准 | 状态 | 验证方式 |
|---------|------|---------|
| 参数可用 | ✅ | 帮助文本测试通过 |
| 参数传递 | ✅ | 源码检查测试通过 |
| 输出显示 | ✅ | 代码审查 + 手工验证 |
| 默认值正确 | ✅ | `action="store_true"` 默认 False |

---

## 与其他可选功能对比

| 功能 | CLI 参数 | 依赖 prompt 版本 | 输出标记 |
|------|---------|-----------------|---------|
| W12 fact-extract | `--w12-extract` | ❌ | `w12=Ncand/status` |
| M7 originality | `--no-originality` | ❌ | `m7=rec/level` |
| Psych beats | `--psych-beats` | v5+ | (无单独标记) |
| Hygiene | `--hygiene-model` | ❌ | `hygiene=verdict` |
| **Contract Gate** | **`--enable-contract-gate`** | **v15.0.0** | **`contract=ok/invalid(N)`** |

**差异点**:
- Contract Gate 是**唯一**与 prompt 版本强绑定的可选功能
- 双阶段检测（precheck + validation）在输出中都可见

---

## 文档更新

### Help 文本
```
--enable-contract-gate
    enable Contract Gate (Phase 3): verify each chapter against its authored
    contract before generation (precheck) and after production (validation).
    Only activates with --prompt-version 15.0.0. Precheck skips chapters
    without valid contracts (ADR-003: never kills the serial). Post-generation
    validation is advisory only, never gates.

--contracts-dir PATH
    directory containing chapter contract files (chapter_N_contract.json).
    Defaults to PROJECT/contracts. Only used when --enable-contract-gate is set.

--strict-contract-mode
    strict Contract Gate mode: precheck failures raise exceptions instead of
    skipping chapters. Use with caution — can abort the serial mid-run.
    Only meaningful with --enable-contract-gate.
```

---

## 后续工作

### Task 3.5: 端到端测试 (待实施)
- 使用真实 Contract Gate 模块的完整测试
- 多章节运行验证
- 验证报告读取测试
- 与 v15 prompt 模板联合测试

### Phase 3 Complete Checklist
- [x] Task 3.1: 创建 v15 prompt 模板 ✅
- [x] Task 3.2: 修改 run_serial 集成 precheck ✅
- [x] Task 3.3: 生成后验证 ✅
- [x] Task 3.4: CLI 集成 ✅
- [ ] Task 3.5: 端到端测试

---

## 提交信息

```
feat: Phase 3 Task 3.4 - Contract Gate CLI集成

CLI参数:
- --enable-contract-gate: 启用Contract Gate
- --contracts-dir: 指定契约目录
- --strict-contract-mode: 严格模式

参数传递:
- 使用getattr模式传递到run_serial
- 与w12/psych-beats等可选功能对齐

输出显示:
- contract=ok/invalid(N)/error
- 与M7/W12输出格式对齐

测试:
- 3个CLI集成测试全部通过
- 帮助文本、参数定义、传递wiring验证完整

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

**Task 3.4 完成时间**: 1小时  
**预计 vs 实际**: 预计1小时 / 实际1小时 ✅  
**下一步**: Task 3.5 端到端测试（可选）
