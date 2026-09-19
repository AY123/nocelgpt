# ANOVEL 基线测试记录模板

> 版本：v1.0  
> 适用范围：ANOVEL 黄金三章测试、前 10 章测试、30 章基线验证  
> 目标：统一记录真人测试、评分、弃读原因、卖点理解和是否进入下一阶段的结论  
> 原则：记录统一、结果可追踪、结论可回退、方便与后续基线比较

---

## 1. 文档目的

ANOVEL 的前置测试不能只口头讨论“通过 / 不通过”，必须形成统一记录。

本模板用于：

- 黄金三章真人测试记录
- 前 10 章真人测试记录
- 30 章基线复盘记录
- 测试样本汇总
- 测试结论归档

---

# 2. 适用对象

本模板适用于以下三类测试记录：

1. **黄金三章测试记录**
2. **前 10 章测试记录**
3. **30 章基线测试记录**

三者记录结构尽量统一，便于后续比较。

---

# 3. 基本信息区

每次测试都应先记录以下基础信息：

```json
{
  "test_id": "TEST-001",
  "story_id": "STORY-001",
  "test_type": "golden_three_chapters",
  "version": "v1.0",
  "test_date": "2026-07-26T10:00:00Z",
  "test_conducted_by": "human_or_system",
  "content_scope": "CH-001 to CH-003",
  "target_reader": "男频玄幻核心读者"
}
```

---

# 4. 测试样本信息

建议记录被测试内容的基本信息：

```json
{
  "title_direction": "废土工坊崛起",
  "description_version": "v1.0",
  "tags": ["废土", "经营", "升级", "势力流"],
  "chapter_ids": ["CH-001", "CH-002", "CH-003"],
  "model_versions": {
    "planner": "claude_xxx",
    "draft": "kimi_k3_xxx",
    "polish": "gpt_5_5_xxx"
  }
}
```

---

# 5. 真人读者信息区

记录参与测试的读者类型和数量：

```json
{
  "reader_count": 5,
  "reader_profiles": [
    "核心题材读者",
    "平台常读读者",
    "对节奏敏感的读者",
    "对商业卖点敏感的读者",
    "外部对照读者"
  ]
}
```

### 说明
- 不需要公开真实身份
- 重点是读者类型，而不是个人信息
- 可根据实际情况记录为匿名编号

---

# 6. 评分与反馈表

下面是建议的统一记录维度。

## 6.1 黄金三章测试记录

```json
{
  "open_hook_score": 4,
  "selling_point_clarity_score": 4,
  "main_goal_clarity_score": 4,
  "continue_reading_willingness": true,
  "continue_reading_reason": "主角目标明确，开篇冲突足够",
  "drop_risk_score": 2,
  "payoff_expectation_score": 4,
  "key_positive_feedback": [
    "开局有冲突",
    "卖点能看懂",
    "人物目标清晰"
  ],
  "key_negative_feedback": [
    "第二章节奏稍缓"
  ]
}
```

---

## 6.2 前 10 章测试记录

```json
{
  "continue_to_ch10": true,
  "continue_to_next_volume": true,
  "selling_point_payoff": true,
  "rhythm_fatigue": false,
  "repetition_risk": false,
  "main_goal_continuity": true,
  "chapter_fatigue_points": ["CH-007"],
  "favorite_chapters": ["CH-003", "CH-005", "CH-009"],
  "weak_chapters": ["CH-007"],
  "main_drop_reason": "中段信息密度略低"
}
```

---

## 6.3 30 章基线记录

```json
{
  "first_volume_closed": true,
  "long_term_trajectory": "stable",
  "quality_trend": "slightly_down_after_ch20",
  "retention_trend": "stable",
  "commercial_trend": "promising",
  "fact_flow_completeness": true,
  "revision_cost": "medium",
  "model_cost": "medium",
  "human_cost": "medium",
  "continue_to_100ch": true
}
```

---

# 7. 测试问题模板

每次测试建议记录以下问题答案。

## 7.1 黄金三章
- 你愿意继续看吗？
- 你觉得这本书卖什么？
- 你知道主角现在要做什么吗？
- 哪一段最吸引你？
- 哪一段最容易让你停下来？

## 7.2 前 10 章
- 你愿意连续追到第 10 章吗？
- 卖点是否兑现？
- 主角目标是否持续清晰？
- 有没有重复、拖沓、空转？
- 你愿意继续等更新吗？

## 7.3 30 章基线
- 第一卷是否闭环？
- 这本书是否还有继续写下去的基础？
- 事实回流是否完整？
- 中后期是否有明显疲劳？
- 是否值得进入 100 章长跑？

---

# 8. 结论记录模板

测试结束后，必须写清楚结论：

```json
{
  "result": "pass_or_fail",
  "decision": "enter_next_stage_or_revise",
  "main_reasons": [
    "开篇抓力足够",
    "卖点理解清晰",
    "中段无明显疲劳"
  ],
  "required_fixes": [
    "压缩第 2 章过渡段",
    "加强第 7 章钩子"
  ],
  "next_step": "30_ch_baseline_or_rewrite_opening"
}
```

---

# 9. 记录原则

### 9.1 记录要统一
不同测试必须使用相同的核心字段。

### 9.2 记录要可比较
黄金三章、前 10 章、30 章都要能横向比较。

### 9.3 记录要可回退
如果测试未通过，要能回到上一个阶段修正。

### 9.4 记录要可追踪
每次测试都应保留版本号、测试日期和样本信息。

---

# 10. 与其他文档的关系

本模板建议与以下文档配套使用：

- `docs/ANOVEL_GOLDEN_THREE_CHAPTERS_TEST_SPEC.md`
- `docs/ANOVEL_TEN_CHAPTER_TEST_SPEC.md`
- `docs/ANOVEL_30_CH_BASELINE_SPEC.md`
- `docs/ANOVEL_SCORING_SYSTEM.md`
- `docs/ANOVEL_REALITY_CHECKLIST.md`

其中：
- `TEST_SPEC` 负责定义怎么测
- `SCORING_SYSTEM` 负责定义怎么打分
- `REALITY_CHECKLIST` 负责定义什么时候算真实验证
- 本模板负责记录结果

---

# 11. 最小可执行版本

如果团队先做 MVP，建议至少保留以下字段：

- test_id
- test_type
- story_id
- chapter_ids
- reader_count
- continue_reading_willingness
- selling_point_clarity
- drop_risk
- result
- decision
- required_fixes

---

# 12. 结论

ANOVEL 的基线测试记录模板，是把真人验证和 30 章基线从“讨论”变成“可归档证据”的关键工具。

没有统一记录，就没有办法比较不同版本、不同开篇和不同模型路线是否真的更好。

因此，这份模板是前置验证体系中的基础配套件。
