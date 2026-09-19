# 30章重跑验证 - 执行指南

**创建日期**: 2026-08-21  
**Phase**: Week 3-4  
**目标**: 验证Phase 1三大修复的实际效果

---

## 🚀 快速开始

### 步骤1: 准备环境

```bash
cd /Users/angyang/Documents/xiaoshuo/AINovel/AI-Novel-Runtime
bash scripts/prepare_30chapter_rerun.sh
```

这个脚本会：
- ✅ 检查环境和依赖
- ✅ 运行Phase 1测试（132个测试）
- ✅ 备份现有章节
- ✅ 生成运行配置

---

### 步骤2: 检查模型配置

查看`.env`文件中的模型配置：

```bash
cat /Users/angyang/Documents/xiaoshuo/AINovel/.env | grep MODEL
```

**确认模型优先级**: 1号模型 > 2号模型 > 3号模型

当前配置示例：
```
CC_VIBE_ANTHROPIC_MODEL=claude-fable-5  # 1号模型
CC_VIBE_OPENAI_MODEL=gpt-5.6-sol        # 2号模型
# MOONSHOT 或其他作为3号模型
```

---

### 步骤3: 启动30章生成

**方法A: 使用准备好的脚本** (推荐新手)
```bash
cd AI-Novel-Runtime
python3 scripts/run_30chapter_rerun.py
```

**方法B: 手动运行serial loop** (推荐有经验者)
```bash
cd AI-Novel-Runtime

# 设置环境变量
export ANES_PROJECT=novel-lingse
export ANES_CHAPTERS=1-30
export ANES_BUDGET_LIMIT=5.0

# 运行
python3 -m runtime.cli run-serial \
  --project novel-lingse \
  --chapters 1-30 \
  --budget-limit 5.0 \
  --enable-phase1-features
```

---

## 📊 监控进度

### 实时监控

**终端1 - 查看日志**:
```bash
tail -f AI-Novel-Runtime/runtime.log
```

**终端2 - 查看进度**:
```bash
watch -n 10 'ls novel-lingse/registry/chapters/ | wc -l'
```

### 关键指标

| 指标 | 监控方式 | 目标 |
|------|---------|------|
| **章节进度** | `ls chapters/ \| wc -l` | 30章 |
| **成本** | 日志中的cost累计 | <¥5 |
| **耗时** | 开始时间→当前时间 | 2-3天 |
| **文本硬伤** | grep "integrity.*fail" | 0次 |
| **AI味** | grep "ai_taste.*warning" | <40% |
| **超长** | grep "truncated" | <5次 |

---

## 🔍 Phase 1功能验证清单

### 验证点1: 文本完整性

**检查方式**:
```bash
# 检查跨章断裂
grep "cross_chapter.*critical" runtime.log

# 检查词内标点
grep "word_internal_punctuation.*critical" runtime.log

# 检查异常换行
grep "abnormal.*break" runtime.log
```

**目标**: 0次critical issues

---

### 验证点2: AI味修复

**检查方式**:
```bash
# 统计AI味warning
grep "ai_taste.*warning" runtime.log | wc -l

# 检查量化指令是否生效
grep "第.*句.*约第.*字" runtime.log | head -5

# 检查模板检测
grep "template.*overuse" runtime.log | head -5
```

**目标**:
- AI味warning率<40%
- 量化指令在hygiene循环中使用
- 模板检测正常工作

---

### 验证点3: 篇幅控制

**检查方式**:
```bash
# 统计截断次数
grep "truncated.*true" runtime.log | wc -l

# 检查多轮收紧
grep "attempt.*2\|attempt.*3" runtime.log | wc -l

# 检查篇幅分布
python3 << 'EOF'
import json
from pathlib import Path

chapters_dir = Path("novel-lingse/registry/chapters")
lengths = []

for ch in sorted(chapters_dir.glob("*.json")):
    with open(ch) as f:
        data = json.load(f)
        word_count = len(data.get("body", ""))
        lengths.append(word_count)
        
print(f"章节数: {len(lengths)}")
print(f"平均长度: {sum(lengths)/len(lengths):.0f}")
print(f"超长(>4000): {sum(1 for l in lengths if l > 4000)}")
EOF
```

**目标**:
- 截断次数<5次
- 超长章节<5/30

---

## 📈 中期检查点

### Checkpoint 1: 前10章（Day 1）

**检查内容**:
- ✅ 10章全部生成成功
- ✅ 无文本硬伤
- ✅ AI味指标正常
- ✅ 成本在预算内（约¥1.5）

**如果有问题**: 暂停，分析日志，调整配置

---

### Checkpoint 2: 前20章（Day 2）

**检查内容**:
- ✅ 20章全部生成成功
- ✅ AI味是否恶化？（对比前10章）
- ✅ 篇幅控制是否生效？
- ✅ 成本在预算内（约¥3）

---

### Checkpoint 3: 全部30章（Day 3）

**完整验证**:
- ✅ 30章全部生成成功
- ✅ 生成质量报告
- ✅ 对比RUN-00001基线

---

## 📋 质量报告生成

### 自动生成报告

完成后会自动生成：
```
AI-Novel-Runtime/30chapter_rerun_report_YYYYMMDD.json
```

### 手动生成详细报告

```bash
python3 << 'EOF'
# 分析30章质量
from pathlib import Path
import json

chapters_dir = Path("novel-lingse/registry/chapters")

report = {
    "text_integrity": {"breaks": 0, "punctuation": 0},
    "ai_taste": {"warnings": 0, "templates": 0},
    "length": {"over_length": 0, "truncated": 0},
}

for ch in sorted(chapters_dir.glob("*.json")):
    with open(ch) as f:
        data = json.load(f)
        
        # 分析逻辑...
        
print(json.dumps(report, indent=2))
EOF
```

---

## ⚠️ 常见问题

### Q1: 生成中断了怎么办？

**A**: 重新运行，serial loop会从上次中断处继续

```bash
# 检查已完成的章节
ls novel-lingse/registry/chapters/ | tail -1

# 从下一章继续
python3 -m runtime.cli run-serial \
  --project novel-lingse \
  --chapters 15-30  # 假设完成到第14章
```

---

### Q2: 成本超预算了怎么办？

**A**: 
1. 检查是否有异常retry
2. 考虑降级使用更便宜的模型
3. 调整budget_limit继续

---

### Q3: AI味还是很严重怎么办？

**A**:
1. 检查量化指令是否正常工作（日志中搜索"第.*句"）
2. 检查hygiene循环是否执行（日志中搜索"hygiene"）
3. 可能需要Task 1.2.3（升级到更强模型）

---

### Q4: 篇幅还是超长怎么办？

**A**:
1. 检查多轮收紧是否生效（日志中搜索"attempt"）
2. 检查硬截断是否执行（日志中搜索"truncated"）
3. 考虑降低tolerance参数（从0.2降到0.1）

---

## ✅ 验收标准

### 必须达成（Hard Gate）

- [ ] 30章全部生成成功
- [ ] 0处跨章断裂
- [ ] 0处词内标点
- [ ] AI味warning率<40%且不恶化
- [ ] 超长章节<5/30 (<17%)

### 期望达成（Soft Goal）

- [ ] AI味warning率<30%
- [ ] Hygiene改善率≥80%
- [ ] 平均篇幅在目标±15%内
- [ ] 成本<¥4

### 如果不通过

**Plan B**:
- 分析具体问题
- 调整参数重跑部分章节
- 或升级模型（Task 1.2.3）

---

## 📅 时间线

| Day | 任务 | 产出 |
|-----|------|------|
| **Day 1** | 生成前10章 | 10章 + Checkpoint 1报告 |
| **Day 2** | 生成第11-20章 | 20章 + Checkpoint 2报告 |
| **Day 3** | 生成第21-30章 | 30章 + 完整质量报告 |
| **Day 4** | 分析报告 | 验收决策 |

---

## 🎯 下一步

**30章重跑成功后**:
→ Week 5-6: 真人双盲评审（黄金三章+前10章）

**30章重跑不完全成功**:
→ 分析问题，调整参数，重跑部分章节

---

**准备就绪！随时可以启动30章重跑。** 🚀

需要立即启动吗？还是先休息，明天再开始？
