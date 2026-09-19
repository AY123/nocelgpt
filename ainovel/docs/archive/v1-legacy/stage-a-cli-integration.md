# 阶段 A CLI 参数集成完成报告

**完成时间**: 2026-08-17  
**任务**: CLI 参数集成（1-2 小时）  
**状态**: ✅ 100% 完成

## 概述

阶段 A（最终稿质量闭环）的所有 Phase (1-6) 已在 `runtime/serialize/loop.py` 中实现完成。本次任务将这些功能通过 CLI 参数暴露，使用户可以通过命令行启用/配置这些特性。

## 完成的工作

### 1. 新增 CLI 参数

在 `serial run` 命令中添加了 4 个新参数：

#### Phase 2: 最终稿质量复评
- `--enable-final-quality-review`: 启用最终稿质量复评
  - 在所有修改（revision + commercial + hygiene）后重新运行 Quality Center
  - 提供真实的质量变化追踪（初稿 → 最终稿）
  - Advisory only, never gates (ADR-003)
  - 增加 LLM 成本但提供准确的质量 delta

- `--final-review-threshold {always,contract-warning,quality-drop,critical-only}`: 控制哪些章节被复评
  - `always`: 所有章节（默认）
  - `contract-warning`: 仅有契约偏差的章节
  - `quality-drop`: 初始评分 < 75 的章节
  - `critical-only`: 里程碑章节（1, 10, 20, 30, 50, 100）

#### Phase 3: 最终稿读者模拟
- `--enable-final-reader-simulation`: 启用最终稿读者模拟
  - 在商业优化后重新运行读者模拟
  - 检测修改引入的新弃书风险
  - 仅在 `--commercial` 启用时运行
  - Advisory only, never gates (ADR-003)

- `--final-reader-threshold {always,commercial-revised,dropout-risk}`: 控制哪些章节被重新模拟
  - `always`: 所有章节
  - `commercial-revised`: 仅商业优化有变更的章节（默认）
  - `dropout-risk`: 仅初始模拟显示风险的章节

### 2. 代码修改

#### `runtime/serialize/loop.py`
- 在 `run_serial` 函数签名中添加 4 个新参数：
  - `enable_final_quality_review: bool = False`
  - `final_review_threshold: str = "always"`
  - `enable_final_reader_simulation: bool = False`
  - `final_reader_threshold: str = "commercial-revised"`
- 移除了 TODO 注释（Line 2095, 2172）
- 参数现在直接用于条件判断，不再硬编码

#### `runtime/cli.py`
- 在 `_add_serial_command` 函数中添加 4 个新参数定义（Line 3125+）
- 在 `_cmd_serial_run` 函数中将参数传递给 `run_serial`（Line 2223+）
- 参数通过 `getattr(args, ...)` 安全读取，有默认值

### 3. 测试覆盖

创建了新的测试文件 `tests/test_stage_a_cli_integration.py`，包含 3 个测试：

1. `test_stage_a_cli_help_includes_new_parameters`: 验证 CLI 帮助信息包含新参数
2. `test_run_serial_function_signature_includes_stage_a_params`: 验证函数签名正确
3. `test_stage_a_parameters_used_in_loop`: 验证参数在代码中实际使用

**测试结果**: 27 passed (包括所有 Production Card 和 Publishing 测试)

## 使用示例

### 基础用法（默认关闭）
```bash
python3 -m runtime.cli serial run \
  --project ./my-novel \
  --standard-root ../AI-Novel-Standard \
  --model-provider deepseek \
  --model-id deepseek-v4-pro \
  --max-chapters 5
```

### 启用最终稿质量复评
```bash
python3 -m runtime.cli serial run \
  --project ./my-novel \
  --standard-root ../AI-Novel-Standard \
  --model-provider deepseek \
  --model-id deepseek-v4-pro \
  --reviewer llm-quality \
  --enable-final-quality-review \
  --final-review-threshold contract-warning \
  --max-chapters 5
```

### 启用最终稿读者模拟
```bash
python3 -m runtime.cli serial run \
  --project ./my-novel \
  --standard-root ../AI-Novel-Standard \
  --model-provider deepseek \
  --model-id deepseek-v4-pro \
  --commercial \
  --enable-final-reader-simulation \
  --final-reader-threshold commercial-revised \
  --max-chapters 5
```

### 同时启用两者（完整 Stage A）
```bash
python3 -m runtime.cli serial run \
  --project ./my-novel \
  --standard-root ../AI-Novel-Standard \
  --model-provider deepseek \
  --model-id deepseek-v4-pro \
  --reviewer llm-quality \
  --commercial \
  --enable-final-quality-review \
  --final-review-threshold always \
  --enable-final-reader-simulation \
  --final-reader-threshold always \
  --max-chapters 5
```

## 架构遵循

本次集成严格遵循项目架构原则：

- **ADR-003**: 所有质量检查都是 advisory，never gates
- **ADR-007**: 未触碰任何 frozen schema
- **Schema-First**: 守门测试全部通过（28 passed）
- **参数传递**: 使用 `getattr` 安全读取，保持向后兼容

## Production Card 集成状态

Production Card 已在 `serialize/loop.py` 中完整集成：
- ✅ Phase 1: 数据结构（Line 150, 2237-2304）
- ✅ Phase 2: 最终稿质量复评（Line 2087-2163，现在可通过 CLI 启用）
- ✅ Phase 3: 最终稿读者模拟（Line 2165-2236，现在可通过 CLI 启用）
- ✅ Phase 4: Production Card 生成（Line 2252-2299）
- ✅ Phase 5: 商业质量非退化（通过 commercial_session 集成）
- ✅ Phase 6: 集成测试（全部通过）

## 成本考虑

启用这些功能会增加 LLM 调用成本：

- `--enable-final-quality-review`: 每章 +1 LLM 调用（质量评判）
- `--enable-final-reader-simulation`: 每章 +N LLM 调用（N 个读者角色）

建议：
- 生产环境使用 `--final-review-threshold contract-warning` 减少成本
- 使用 `--budget-limit` 控制总成本
- 使用 `--per-chapter-budget` 控制单章成本

## 下一步选择

CLI 参数集成已完成。现在可以选择：

**B. 阶段 B: Promise Ledger 重构**
- 重构承诺追踪系统
- 预计时间：4-6 小时

**C. 真实验证: 30 章基线测试**
- 使用新参数运行完整的 30 章基线
- 验证 Production Card 在真实场景中的表现
- 收集质量 delta 数据

## 验证清单

- [x] CLI 参数定义正确
- [x] 参数传递到 `run_serial`
- [x] 函数签名包含新参数
- [x] TODO 注释已移除
- [x] 帮助信息清晰明确
- [x] 所有测试通过（27/27）
- [x] Schema conformance 测试通过（28/28）
- [x] 向后兼容（默认值不改变现有行为）
- [x] 文档完整

## 提交信息

```
feat: Stage A CLI 参数集成 - 最终稿质量复评和读者模拟

添加 4 个新 CLI 参数以启用阶段 A Phase 2/3 功能：

- --enable-final-quality-review: 启用最终稿质量复评
- --final-review-threshold: 控制复评阈值
- --enable-final-reader-simulation: 启用最终稿读者模拟
- --final-reader-threshold: 控制模拟阈值

所有功能 advisory only (ADR-003)，默认关闭保持向后兼容。

测试: 27 passed (新增 3 个集成测试)
守门: 28 passed (schema-conformance)
```
