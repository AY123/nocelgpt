# P0 修复生产验证指南

**目标**: 在真实生产环境中验证 P0-2 和 P0-3 修复的效果

**创建日期**: 2026-08-15  
**状态**: 准备就绪

---

## 📋 概述

本指南提供了两种验证方式：

1. **快速验证**: 使用验证脚本检查现有运行结果
2. **完整试运行**: 运行 2-3 章，观察完整数据流

---

## 🚀 方式 1: 快速验证（推荐）

### 适用场景
- 已有运行结果（run-manifest.json）
- 想快速检查 P0 修复是否生效
- 不想重新运行章节

### 使用步骤

#### 1. 定位运行清单文件

运行清单通常位于以下位置之一：
```bash
# 选项 A: registry/derived/run-manifests/
registry/derived/run-manifests/RUN-00025.json

# 选项 B: out/ 目录
out/run-manifest.json
```

#### 2. 运行验证脚本

```bash
cd AI-Novel-Runtime
python3 scripts/verify_p0_fixes.py <path-to-run-manifest.json>
```

**示例**:
```bash
# 验证最新的 baseline run
python3 scripts/verify_p0_fixes.py ../registry/derived/run-manifests/RUN-00025.json

# 验证 out/ 目录的运行
python3 scripts/verify_p0_fixes.py out/run-manifest.json
```

#### 3. 解读输出

验证脚本会检查以下内容：

**P0-2 验证**:
```
🔍 P0-2: 最终稿契约闭环验证
============================================================

📊 统计:
  总章节数: 33
  有最终验证: 15/33

📋 详情:
  第 1 章: ✅ 通过
  第 2 章: ✅ 通过
  第 5 章: ❌ 失败 (2 关键问题)
  ...

✅ P0-2 修复生效: final_contract_validation 被正确记录
```

**P0-3 验证**:
```
🔗 P0-3: 实际出口回流到下一章
============================================================

📊 统计:
  实际出口文件: 33

📋 详情:
  第 1 章:
    地点: 森林深处
    人物: 主角, NPC
    钩子: 悬念A, 伏笔B

✅ P0-3 修复生效: 实际出口状态被正确提取
```

---

## 🏃 方式 2: 完整试运行（可选）

### 适用场景
- 想从头运行 2-3 章
- 观察完整的契约闭环流程
- 对比启用/禁用修复的效果

### 使用步骤

#### 1. 准备试运行脚本

```bash
cd AI-Novel-Runtime
python3 scripts/p0_production_trial.py --help
```

#### 2. 运行试运行（Dry-run 模式）

```bash
# 模拟运行，不调用真实 LLM
python3 scripts/p0_production_trial.py --chapters 3 --dry-run
```

#### 3. 运行试运行（真实模式）

**注意**: 需要配置 LLM 模型和 API key

```bash
# 真实运行 3 章
python3 scripts/p0_production_trial.py --chapters 3
```

#### 4. 查看结果

试运行会：
1. 创建临时项目
2. 运行指定章节数
3. 自动分析结果
4. 保留项目目录供检查

---

## 🔍 验证要点

### P0-2: 最终稿契约闭环验证

**期望行为**:
- `ChapterRun` 有 `final_contract_validation` 字段
- 当商业/卫生修改草稿后，该字段被填充
- 验证失败时，记录关键问题数量

**验证方法**:
```python
# 检查 run-manifest.json
chapter_run = manifest['chapters'][0]
if chapter_run.get('final_contract_validation'):
    print("✅ P0-2 生效")
    print(f"验证结果: {chapter_run['final_contract_validation']}")
else:
    print("⚠️  final_contract_validation 未填充")
    print("可能原因: 草稿未变化（hash 相同）")
```

**注意事项**:
- 如果草稿在契约修订后未被修改（商业/卫生跳过或未改变 hash），`final_contract_validation` 可能为 `None`
- 这是预期行为，不是 bug

### P0-3: 实际出口回流

**期望行为**:
- 每章生成后，`chapter-exit-state/exit-TASK-N.json` 被创建
- 下一章加载该文件，渲染为 `actual_entry_state`
- `actual_entry_state` 被注入到 prompt

**验证方法**:
```bash
# 检查实际出口文件
ls registry/derived/chapter-exit-state/

# 输出示例:
# exit-TASK-00001.json
# exit-TASK-00002.json
# exit-TASK-00003.json

# 查看实际出口内容
cat registry/derived/chapter-exit-state/exit-TASK-00001.json
```

**文件格式**:
```json
{
  "chapter": 1,
  "location": "森林深处",
  "present_characters": ["主角", "NPC"],
  "active_hooks": ["悬念A", "伏笔B"],
  "emotional_state": "紧张",
  "plot_threads": ["主线", "支线1"],
  "final_text_hash": "hash-xxx"
}
```

### 完整闭环验证

**期望行为**:
```
第 1 章:
  ✅ 生成 → 修订 → 商业/卫生
  ✅ P0-2: 最终契约验证
  ✅ P0-5: 提取实际出口 → exit-TASK-00001.json

第 2 章:
  ✅ P0-3: 加载 exit-TASK-00001.json
  ✅ P0-3: 渲染 actual_entry_state
  ✅ P0-3: 注入到 prompt
  ✅ 模型基于实际状态生成
```

---

## 📊 预期结果

### 成功标准

| 指标 | 期望值 | 说明 |
|-----|--------|------|
| **P0-2 覆盖率** | > 50% | 至少一半章节有最终验证记录 |
| **P0-3 文件生成** | 100% | 每章都有实际出口文件 |
| **契约偏差记录** | > 0 | 至少有一些偏差被记录 |
| **最终验证失败** | < 10% | 大部分章节应该通过最终验证 |

### 异常情况处理

#### 情况 1: `final_contract_validation` 全部为 None

**可能原因**:
- Contract Gate 未启用
- prompt_version < 15.0.0
- 商业/卫生流程未运行
- 草稿 hash 未变化（最常见）

**解决方法**:
1. 检查运行参数：`enable_contract_gate=True`
2. 检查 prompt 版本：`prompt_version="15.0.0"`
3. 启用商业/卫生流程：`--simulator` 或 `--hygiene-model`

#### 情况 2: 实际出口文件缺失

**可能原因**:
- P0-5 未修复（已修复，不应该发生）
- 章节 index < 1（第 0 章不提取）
- Contract Gate 未启用

**解决方法**:
1. 确认 P0-5 修复已应用
2. 检查章节 index >= 1
3. 启用 Contract Gate

#### 情况 3: 实际出口存在但未被下一章使用

**验证方法**:
- 查看 prompt 日志或 LLM 请求
- 检查 extra_vars 是否包含 `actual_entry_state`
- 查看 binding.py 是否正确绑定

**注意**: 文件层面的验证无法直接确认是否被模型使用

---

## 🎯 对比测试（可选）

### 目标
对比启用/禁用 `actual_entry_state` 的生成质量差异

### 方法

#### 1. 运行基准版本（禁用 P0-3）

修改 `loop.py`，临时注释掉 P0-3 的代码：
```python
# P0-3: 临时禁用
# if _at_least(major, 15) and enable_contract_gate and spec.index > 1:
#     ...
#     extra_vars["actual_entry_state"] = actual_entry_context
```

运行 3 章，保存结果为 `baseline-without-p0-3/`

#### 2. 运行修复版本（启用 P0-3）

恢复 P0-3 代码，运行相同的 3 章，保存结果为 `baseline-with-p0-3/`

#### 3. 对比分析

对比以下指标：
- 状态连续性（地点/人物/钩子是否连贯）
- 契约违反次数
- 生成质量评分

---

## 📝 报告模板

### 验证报告

```markdown
# P0 修复生产验证报告

**验证日期**: YYYY-MM-DD
**验证人**: [姓名]
**运行版本**: [git commit hash]

## 验证结果

### P0-2: 最终稿契约闭环验证
- 总章节: X
- 有最终验证: X/X
- 验证失败: X/X
- 状态: ✅/⚠️/❌

### P0-3: 实际出口回流
- 实际出口文件: X
- 文件完整性: ✅/⚠️/❌
- 状态: ✅/⚠️/❌

### 契约闭环完整性
- 第 1 章 → 第 2 章: ✅/⚠️/❌
- 偏差记录: X 个
- 状态: ✅/⚠️/❌

## 问题和建议

[描述发现的问题和改进建议]

## 结论

✅/⚠️/❌ P0 修复生效/部分生效/未生效
```

---

## 🛠️ 故障排查

### 常见问题

#### Q1: 验证脚本报错 "文件不存在"

**解决**:
```bash
# 确认文件路径
ls registry/derived/run-manifests/

# 使用绝对路径
python3 scripts/verify_p0_fixes.py $(pwd)/registry/derived/run-manifests/RUN-00025.json
```

#### Q2: 验证脚本报告 "无最终验证记录"

**解决**: 这可能是预期行为，见 "异常情况处理"

#### Q3: 试运行脚本无法找到模块

**解决**:
```bash
# 确保在正确的目录
cd AI-Novel-Runtime

# 确保 Python 路径正确
export PYTHONPATH=$(pwd):$PYTHONPATH
```

---

## 📚 相关文档

- `P0-2-fix-report.md` - P0-2 详细修复报告
- `P0-3-fix-report.md` - P0-3 详细修复报告
- `P0-e2e-validation-report.md` - 端到端验证报告
- `COMPLETE_SESSION_SUMMARY.md` - 完整会话总结

---

## ✅ 检查清单

验证前准备:
- [ ] 确认 P0-2 和 P0-3 修复已应用（git log）
- [ ] 确认有可用的 run-manifest.json
- [ ] 确认 Contract Gate 已启用
- [ ] 确认 prompt_version >= 15.0.0

验证步骤:
- [ ] 运行验证脚本
- [ ] 检查 P0-2 结果
- [ ] 检查 P0-3 结果
- [ ] 检查契约闭环
- [ ] 记录验证报告

可选步骤:
- [ ] 运行完整试运行
- [ ] 对比测试（有/无 P0-3）
- [ ] Dashboard 可视化

---

**状态**: ✅ 准备就绪，可以开始验证

**建议**: 先使用快速验证方式（方式 1），确认修复生效后再考虑完整试运行
