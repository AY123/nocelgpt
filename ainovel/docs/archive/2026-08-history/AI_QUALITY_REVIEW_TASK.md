# 🔍 AI 质量评审任务 - 2026-08-11

## 任务概述

**目标**: 补充 100 章的详细质量评分  
**方法**: 使用 refine 命令 + llm-quality reviewer  
**模型**: DeepSeek (成本低)  
**预计时间**: 3-4 小时  
**预计成本**: ¥2-3 CNY

---

## 评审内容

### 18 维度质量评分
1. character_consistency - 角色一致性
2. commercial - 商业价值
3. conflict - 冲突设计
4. emotion - 情感表达
5. foreshadowing - 伏笔设置
6. genre_contract - 类型契约
7. immersion - 沉浸感
8. logic - 逻辑性
9. mandate - 任务推进
10. originality - 原创性
11. pacing - 节奏控制
12. plot_coherence - 情节连贯性
13. prose_quality - 文笔质量
14. reader_experience - 阅读体验
15. scene_vividness - 场景生动性
16. setup_payoff - 铺垫与回报
17. speech - 对话质量
18. tension - 张力

---

## 执行方案

### 方案：批量运行（后台执行）
```bash
# 循环评审所有章节
for i in {1..100}; do
  python3 -m runtime.cli refine \
    --package TASK-$(printf "%05d" $i).json \
    --standard-root ../AI-Novel-Standard \
    --project . \
    --model-provider deepseek \
    --model-id deepseek-chat \
    --prompt-version v12 \
    --reviewer llm-quality \
    --max-rounds 1
done
```

---

## 启动状态

**启动时间**: 2026-08-11 01:40  
**状态**: 准备启动
