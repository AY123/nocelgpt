# ANOVEL 评审打分卡模板

> 版本：v1.0  
> 适用范围：ANOVEL 百万字长篇生产系统  
> 目标：把章节评审、版本比较、修订决策统一成可直接使用的标准打分卡  
> 原则：维度明确、分数统一、问题可追踪、决策可执行

---

## 1. 文档目的

ANOVEL 的评分体系已经定义了质量、商业、留存、长篇稳定四大类指标。  
但要真正落地，必须有一份可以直接使用的评审打分卡，让 reviewer、模型、编辑和人工审校都能按同一标准打分。

本模板用于：

- 单章评审
- 卷级评审
- 作品基线评审
- 自动修订前后比较
- 模型版本比较
- 人工金样集校准

---

## 2. 打分卡设计原则

### 2.1 统一 0–5 分制
所有维度都使用 0–5 分，便于比较。

### 2.2 维度尽量少而精
每个大类控制在 4–6 个核心维度。

### 2.3 每个分数必须可解释
不能只写分数，要写原因和问题。

### 2.4 分数要能指导动作
每份打分卡都应能得出明确决策：
- 保留
- 修订
- 回炉
- 发布
- 拒绝

### 2.5 评审与建议分离
先给分，再写问题，再给建议。

---

# 3. 打分卡总结构

建议每次评审都输出以下 6 个部分：

1. 基本信息
2. 分项评分
3. 问题列表
4. 修订建议
5. 决策意见
6. provenance

---

# 4. 基本信息模板

```json
{
  "story_id": "STORY-001",
  "chapter_id": "CH-001",
  "review_id": "REV-001",
  "review_version": "v1.0",
  "reviewer": "claude_or_gpt_or_human",
  "review_date": "2026-07-26T10:00:00Z",
  "scope": "chapter"
}
```

---

# 5. 分项评分模板

---

## 5.1 质量评分卡

### 维度
1. 结构完整度
2. 人物可信度
3. 设定稳定性
4. 正文可读性
5. 节奏优秀度

### 模板

```json
{
  "quality": {
    "structure": {
      "score": 4,
      "reason": "本章有明确任务推进，冲突完整，结尾有钩子",
      "issues": ["中段过渡略慢"]
    },
    "character": {
      "score": 4,
      "reason": "主角行为符合既定动机，配角声音较稳定",
      "issues": []
    },
    "world_consistency": {
      "score": 5,
      "reason": "没有与既有设定冲突",
      "issues": []
    },
    "prose": {
      "score": 4,
      "reason": "语句自然，AI 腔不重",
      "issues": ["个别句子略显总结化"]
    },
    "rhythm": {
      "score": 4,
      "reason": "推进节奏稳定，未出现明显拖沓",
      "issues": ["中段信息密度可再提高"]
    }
  }
}
```

---

## 5.2 商业评分卡

### 维度
1. 题材定位清晰度
2. 核心卖点强度
3. 付费点明确度
4. 平台竞争力

### 模板

```json
{
  "commercial": {
    "positioning": {
      "score": 5,
      "reason": "题材方向明确，读者心智清晰",
      "issues": []
    },
    "selling_point": {
      "score": 4,
      "reason": "工坊卖点已露出，但还可更强",
      "issues": ["核心卖点可更集中"]
    },
    "payoff": {
      "score": 4,
      "reason": "本章有小爽点，但付费驱动力一般",
      "issues": []
    },
    "platform_fit": {
      "score": 4,
      "reason": "符合起点男频主流阅读预期",
      "issues": []
    }
  }
}
```

---

## 5.3 留存评分卡

### 维度
1. 开篇吸引力
2. 章末钩子强度
3. 追读动机持续性
4. 弃书风险

### 模板

```json
{
  "retention": {
    "opening": {
      "score": 5,
      "reason": "前段迅速建立压力和目标",
      "issues": []
    },
    "ending_hook": {
      "score": 5,
      "reason": "结尾悬念明确，能驱动继续阅读",
      "issues": []
    },
    "continue_intent": {
      "score": 4,
      "reason": "读者知道下一章要看什么",
      "issues": []
    },
    "drop_risk": {
      "score": 4,
      "reason": "弃书风险较低，但中段仍需注意节奏",
      "issues": []
    }
  }
}
```

---

## 5.4 长篇稳定评分卡

### 维度
1. 设定稳定性
2. 人设稳定性
3. 节奏稳定性
4. 伏笔管理
5. 状态回流能力

### 模板

```json
{
  "long_term": {
    "world_stability": {
      "score": 5,
      "reason": "本章未引入新的设定冲突",
      "issues": []
    },
    "character_stability": {
      "score": 4,
      "reason": "角色行为稳定，但后续要关注情绪线",
      "issues": []
    },
    "rhythm_stability": {
      "score": 4,
      "reason": "节奏尚可，未出现结构疲劳",
      "issues": ["若连续多章同模式，可能疲劳"]
    },
    "foreshadowing": {
      "score": 4,
      "reason": "伏笔有埋设，但回收路径需保持清晰",
      "issues": []
    },
    "state_reflow": {
      "score": 5,
      "reason": "本章新增事实可回流且已记录",
      "issues": []
    }
  }
}
```

---

# 6. 总分计算模板

建议按以下权重汇总：

```text
Total = 质量×0.30 + 商业×0.25 + 留存×0.25 + 长篇稳定×0.20
```

### 模板

```json
{
  "summary": {
    "quality_score": 85,
    "commercial_score": 82,
    "retention_score": 90,
    "long_term_score": 84,
    "total_score": 85
  }
}
```

---

# 7. 问题列表模板

每次评审必须写明问题列表，不能只给分。

### 模板

```json
{
  "issues": [
    {
      "type": "rhythm",
      "severity": "medium",
      "description": "中段信息密度略低",
      "suggestion": "压缩过渡段，增强冲突推进"
    },
    {
      "type": "commercial",
      "severity": "low",
      "description": "核心卖点还可以更聚焦",
      "suggestion": "把工坊能力展示得更直接"
    }
  ]
}
```

---

# 8. 决策模板

评审结果必须落到明确决策。

### 决策类型
- `publish`
- `revise`
- `hold`
- `reject`

### 模板

```json
{
  "decision": "revise",
  "decision_reason": "整体合格，但中段节奏和卖点聚焦仍可优化",
  "required_actions": [
    "压缩过渡段",
    "加强核心卖点展示",
    "增强章末钩子"
  ]
}
```

---

# 9. 不同场景的打分卡变体

---

## 9.1 单章打分卡
重点看：
- 结构
- 人物
- 节奏
- 钩子
- 事实回流

---

## 9.2 卷级打分卡
重点看：
- 卷结构是否完整
- 卷末钩子是否成立
- 卷内成长是否持续
- 是否形成阶段闭环

---

## 9.3 作品级打分卡
重点看：
- 30 章基线
- 长弧可持续性
- 商业定位
- 留存潜力
- 长篇稳定性

---

## 9.4 模型版本对比打分卡
重点看：
- 哪个版本更自然
- 哪个版本更稳定
- 哪个版本更有商业感
- 哪个版本更适合继续生产

---

# 10. 评审记录模板

建议每次评审都落一份完整记录：

```json
{
  "review_id": "REV-001",
  "story_id": "STORY-001",
  "chapter_id": "CH-001",
  "review_version": "v1.0",
  "reviewer": "claude",
  "scores": {
    "quality": 85,
    "commercial": 82,
    "retention": 90,
    "long_term": 84,
    "total": 85
  },
  "issues": [],
  "decision": "revise",
  "provenance": {
    "input_hash": "sha256:...",
    "output_hash": "sha256:...",
    "reviewed_at": "2026-07-26T10:00:00Z"
  }
}
```

---

# 11. 常见打分错误

### 11.1 只给总分不给细分
问题：不知道哪里好，哪里差。  
应对：必须分项评分。

### 11.2 只写意见不给建议
问题：无法执行。  
应对：每个问题都要给建议。

### 11.3 分数漂移
问题：不同评审人标准不一致。  
应对：必须有金样集校准。

### 11.4 模型自评自举
问题：生成和评审混在一起。  
应对：严格分离 reviewer 与 generator。

### 11.5 分数和内容不一致
问题：分数高但正文明显有问题。  
应对：要求评论必须能解释分数。

---

# 12. 最小可执行版本

如果团队先做 MVP，建议至少落地以下字段：

- 章节 ID
- 评审 ID
- 质量分
- 商业分
- 留存分
- 长篇稳定分
- 总分
- 问题列表
- 决策
- provenance

---

# 13. 结论

ANOVEL 的评审打分卡模板，是把所有抽象评分体系变成实际工作流的一步。

有了这份模板，团队就能对同一章、同一卷、同一版本，使用同一套语言说清楚：
- 好在哪里
- 坏在哪里
- 改什么
- 是否值得继续

这才是 ANOVEL 真正可执行的评审系统。
