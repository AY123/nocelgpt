# 🔍 问题诊断与解决 - 2026-08-10

## 问题：51-60 章无法生产

### 症状
- `serial run` 执行后立即结束
- produced=0, skipped=0, planned=0
- 没有任何章节被规划或生产

### 根本原因
**Outline 只规划了前 30 章**：
- `first_30_chapters`: 30 章 ✅
- `chapters`: 0 章 ❌

这意味着：
- 1-30 章：从 outline 的 `first_30_chapters` 读取
- 31+ 章：outline 没有规划，导致无章节可生产

### 解决方案

**使用 Rolling Plan Continuation**：

```bash
python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --standard-root ../AI-Novel-Standard \
  --start-chapter 51 \
  --max-chapters 10 \
  --rolling-plan-continuation  # 关键参数！
  --model-provider deepseek \
  --model-id deepseek-chat
```

**Rolling Plan 机制**：
- `rolling-050.json` 包含 51-60 章的 active_goals
- `--rolling-plan-continuation` 告诉系统从 rolling plan 读取而不是 outline
- 系统会从 cp-050 检查点恢复状态

### 验证

✅ **Rolling Plans 存在**：
- rolling-010.json (10 goals)
- rolling-020.json (10 goals)
- rolling-030.json (10 goals)
- rolling-040.json (10 goals)
- rolling-050.json (10 goals) ← 包含 51-60 章

✅ **检查点存在**：
- cp-050.json ← 状态恢复点

### 经验教训

1. **Outline vs Rolling Plan**：
   - Outline：初始规划（通常只有前 30 章）
   - Rolling Plan：动态滚动规划（每 10 章更新）

2. **长序列生产策略**：
   - 1-30 章：使用 outline
   - 31+ 章：使用 rolling-plan-continuation

3. **M5 新功能验证**：
   - `--rolling-plan-continuation` 是 M5 刚实现的功能
   - 现在是首次实战使用

---

**状态**: 已使用正确参数重新启动 51-60 章生产
**后台任务**: 运行中
**预计完成**: 1-2 小时
