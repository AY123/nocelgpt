# 30章Phase 1验证运行 - 监控指南

**启动时间**: 2026-08-25 17:17  
**进程ID**: 11798  
**模型**: claude-fable-5 (CC-Vibe Anthropic)  
**API**: https://claudecode.top  
**日志文件**: `30chapter_phase1_claude_20260825_171744.log`

---

## 📊 运行配置

```bash
--max-chapters 30
--model-provider claude
--model-id claude-fable-5
--prompt-version 10.0.0
--long-arc --vary-openings --mandate --speech
--hygiene-model claude:claude-fable-5
--hygiene-rounds 2
--budget-limit 10.0
```

---

## 🔍 监控命令

### 实时进度监控

```bash
# 查看实时日志
tail -f /Users/angyang/Documents/xiaoshuo/AINovel/30chapter_phase1_claude_20260825_171744.log

# 监控生成进度
watch -n 10 'ls /Users/angyang/Documents/xiaoshuo/AINovel/novel-lingse/registry/derived/drafts/ | wc -l'

# 检查进程状态
ps -p 11798 -o pid,stat,%cpu,%mem,etime
```

### 快速检查

```bash
cd /Users/angyang/Documents/xiaoshuo/AINovel

# 查看当前进度
echo "已生成章节: $(ls novel-lingse/registry/derived/drafts/ | wc -l)/30"

# 查看最近日志
tail -20 30chapter_phase1_claude_20260825_171744.log

# 检查最新生成的章节
ls -lt novel-lingse/registry/derived/drafts/ | head -5
```

---

## 📈 预期时间线

| 检查点 | 时间 | 章节数 |
|--------|------|--------|
| **Checkpoint 1** | +24小时 | 前10章 |
| **Checkpoint 2** | +48小时 | 前20章 |
| **Checkpoint 3** | +72小时 | 全30章 |

---

## ✅ 验收标准

运行成功需要满足：

- [ ] **30章全部生成** (0 skip)
- [ ] **跨章断裂 = 0**
- [ ] **AI味不恶化** (<40%)
- [ ] **超长章节 <5/30**
- [ ] **模板检测正常工作**
- [ ] **成本 <¥10**

---

## 🚨 故障处理

### 如果进程停止

```bash
# 检查进程是否运行
ps -p 11798

# 查看日志末尾错误
tail -50 30chapter_phase1_claude_20260825_171744.log

# 从中断处继续（假设完成到第15章）
cd AI-Novel-Runtime
python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --start-chapter 16 \
  --max-chapters 30 \
  --model-provider claude \
  --model-id claude-fable-5 \
  [其他参数相同]
```

### 如果预算超限

运行会自动在达到¥10时停止。可以：
1. 检查已生成章节数
2. 调整预算继续

---

## 📋 关键检查点

### 24小时后（第1个检查点）

```bash
# 检查进度
ls novel-lingse/registry/derived/drafts/ | wc -l

# 检查质量指标
grep "ai_taste.*warning" 30chapter_phase1_claude_20260825_171744.log | wc -l
grep "length_enforced.*True" 30chapter_phase1_claude_20260825_171744.log | wc -l
grep "模板表达过度使用" 30chapter_phase1_claude_20260825_171744.log | head -5
```

### 48小时后（第2个检查点）

```bash
# 检查是否有AI味恶化趋势
grep "ai_taste" 30chapter_phase1_claude_20260825_171744.log | tail -10

# 检查超长章节数量
grep "length_enforced" 30chapter_phase1_claude_20260825_171744.log | wc -l
```

### 72小时后（最终检查）

```bash
# 生成质量报告
python3 -m runtime.cli report quality \
  --project ../novel-lingse \
  --run RUN-00050

# 对比baseline (RUN-00001)
python3 -m runtime.cli report compare \
  --baseline RUN-00001 \
  --current RUN-00050
```

---

## 📞 完成后分析

运行完成后执行：

```bash
cd AI-Novel-Runtime

# 1. 查看运行摘要
tail -50 ../30chapter_phase1_claude_20260825_171744.log

# 2. 检查生成的章节
ls ../novel-lingse/registry/derived/drafts/ | wc -l

# 3. 查看运行manifest
cat ../novel-lingse/registry/derived/run-manifests/RUN-00050.json

# 4. 生成分析报告
python3 scripts/analyze_phase1_run.py RUN-00050
```

---

## 🎯 Phase 1验证目标

对比 RUN-00001 (Baseline):

| 指标 | Baseline | Phase 1目标 |
|------|----------|-------------|
| 跨章断裂 | 3处 | 0处 |
| AI味恶化 | 40%→70% | <40%持平 |
| 超长章节 | 18/30 (60%) | <5/30 (<17%) |
| 模板检测 | 未检测 | 实时修复 |

---

**监控指南创建时间**: 2026-08-25 17:20  
**运行状态**: ✅ 进行中  
**预计完成**: 2026-08-28
