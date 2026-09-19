# ANOVEL 数据结构规范

> 版本：v1.0  
> 适用范围：ANOVEL 百万字长篇生产系统  
> 目标：统一 ANOVEL 的核心对象、字段、状态、版本与 provenance，保证架构、评分、事实流转、发布流程都能落到一致的数据结构上  
> 原则：结构统一、字段明确、状态可追踪、版本可比较、事实可回放

---

## 1. 文档目的

ANOVEL 前面的架构、模型分工、评分体系、开书模板、团队执行、事实流转、评审和发布流程，最终都必须落到统一的数据结构上。

如果没有统一数据结构，系统会出现以下问题：

- 文档写得很完整，但实现各做各的
- 不同模块的字段名不一致
- 事实、评审、版本、发布无法串起来
- 运行结果不能回放
- 评分和正文无法一一对应

因此，本规范的目标是：

1. 统一核心对象定义
2. 统一字段与状态
3. 统一 provenance 记录
4. 统一版本管理方式
5. 统一模块间数据交互标准

---

## 2. 设计原则

### 2.1 结构优先
所有核心对象都必须有明确结构，不允许只靠自然语言描述。

### 2.2 版本化
任何关键对象一旦进入系统，必须可版本化、可比较、可追踪。

### 2.3 可审计
每个对象都要保留来源、生成时间、生成者、版本和引用链。

### 2.4 可回放
同一输入在同一版本下应尽可能回放出一致结果。

### 2.5 可扩展
字段设计要支持后续扩展，但不能过度抽象。

### 2.6 不混层
事实、评审、运行、发布、长弧等不同层级对象不能混在一个结构里。

---

## 3. 核心对象总览

ANOVEL 的核心数据对象建议分为 12 类：

1. `PositioningSpec`
2. `StorySpec`
3. `ArcPlan`
4. `VolumePlan`
5. `CharacterProfile`
6. `WorldRuleSet`
7. `ChapterObjective`
8. `ChapterDraft`
9. `ReviewReport`
10. `FactCandidate`
11. `FactRecord`
12. `ReleasePackage`

---

# 4. 核心对象定义

---

## 4.1 `PositioningSpec`

### 用途
描述一本书的题材定位、商业定位和目标受众。

### 字段建议

```json
{
  "story_id": "STORY-001",
  "genre": "玄幻",
  "subgenre": "升级流",
  "platform": "起点中文网",
  "target_reader": {
    "gender": "男",
    "age_range": "18-35",
    "preferences": ["升级", "热血", "爽感"]
  },
  "core_selling_points": ["强金手指", "势力成长", "高压冲突"],
  "risk_flags": ["开篇慢热", "卖点发散"]
}
```

### 说明
- `story_id` 必须唯一
- `genre` 和 `subgenre` 要明确
- `core_selling_points` 不能太多，建议 2–5 个

---

## 4.2 `StorySpec`

### 用途
描述整本书的基础设定与战略目标。

### 字段建议

```json
{
  "story_id": "STORY-001",
  "title_direction": "待定",
  "logline": "主角在废土中捡到一座神级工坊，并借此建立势力",
  "core_conflict": "资源匮乏与势力压迫",
  "core_goal": "从拾荒者成长为据点主",
  "primary_antagonist_type": "地方势力",
  "commercial_goal": "形成起点式长篇商业竞争力"
}
```

---

## 4.3 `ArcPlan`

### 用途
描述长弧规划，通常覆盖 30 章、100 章或更长范围。

### 字段建议

```json
{
  "story_id": "STORY-001",
  "arc_version": "v1.0",
  "chapter_range": "1-100",
  "milestones": [
    {
      "chapter_range": "1-30",
      "goal": "第一卷闭环"
    },
    {
      "chapter_range": "31-60",
      "goal": "区域扩张"
    }
  ],
  "climax_points": [
    "CH-030",
    "CH-060",
    "CH-100"
  ],
  "map_transition_points": [
    "CH-030",
    "CH-070"
  ]
}
```

### 说明
- `milestones` 是阶段目标
- `climax_points` 是关键高潮点
- `map_transition_points` 是地图或舞台转换点

---

## 4.4 `VolumePlan`

### 用途
描述卷级结构。

### 字段建议

```json
{
  "volume_id": "VOL-001",
  "story_id": "STORY-001",
  "chapter_range": "1-30",
  "volume_goal": "建立第一据点",
  "volume_hook": "工坊升级引来更强势力关注",
  "volume_end_state": "主角具备初步自保能力"
}
```

---

## 4.5 `CharacterProfile`

### 用途
描述单个角色的基本设定、声音风格、成长轨迹和关系状态。

### 字段建议

```json
{
  "character_id": "CHR-001",
  "story_id": "STORY-001",
  "name": "陆沉",
  "role": "protagonist",
  "traits": ["冷静", "韧性强", "目标感强"],
  "motivation": "活下去并保护妹妹",
  "voice_style": {
    "sentence_length": "short_to_medium",
    "tone": "calm",
    "taboos": ["夸张喊叫", "空泛鸡汤"]
  },
  "growth_path": [
    "拾荒者",
    "工坊拥有者",
    "据点主",
    "区域势力核心"
  ],
  "relationship_state": [
    {
      "target_character_id": "CHR-002",
      "relation": "sibling",
      "status": "protective"
    }
  ]
}
```

---

## 4.6 `WorldRuleSet`

### 用途
描述世界规则、力量体系、资源规则和边界条件。

### 字段建议

```json
{
  "world_id": "WORLD-001",
  "story_id": "STORY-001",
  "setting_summary": "废土世界，旧文明崩坏后资源稀缺，城邦割据",
  "rules": [
    "资源稀缺",
    "高风险区域存在污染与变异生物",
    "旧文明技术可被修复但稀少"
  ],
  "power_system": [
    "体能强化",
    "机械改造",
    "工坊制造",
    "装备升级",
    "势力扩张"
  ],
  "constraints": [
    "高级技术必须有能源源核支撑",
    "工坊升级依赖稀有材料"
  ]
}
```

---

## 4.7 `ChapterObjective`

### 用途
描述一章的写作目标、冲突、钩子和事实消费要求。

### 字段建议

```json
{
  "chapter_id": "CH-001",
  "story_id": "STORY-001",
  "chapter_role": "opening_hook",
  "goal": "立住主角生存压力并引出工坊",
  "conflict": "资源不足与外部压迫",
  "info_gain": "发现异常地下入口",
  "hook": "工坊权限提示出现",
  "facts_to_consume": ["FACT-001", "FACT-002"],
  "length_target": 2500
}
```

---

## 4.8 `ChapterDraft`

### 用途
描述某一章的正文草稿及其来源信息。

### 字段建议

```json
{
  "chapter_id": "CH-001",
  "story_id": "STORY-001",
  "draft_version": "v1",
  "model_used": "kimi-k3",
  "prompt_version": "p1.0",
  "content": "……正文……",
  "content_hash": "sha256:...",
  "word_count": 2480,
  "provenance": {
    "generated_at": "2026-07-26T10:00:00Z",
    "generated_from": {
      "objective_id": "OBJ-001",
      "state_hash": "sha256:..."
    }
  }
}
```

---

## 4.9 `ReviewReport`

### 用途
记录章节或版本的评审结果。

### 字段建议

```json
{
  "chapter_id": "CH-001",
  "story_id": "STORY-001",
  "review_version": "v1.0",
  "reviewer": "claude",
  "scores": {
    "structure": 4,
    "character": 4,
    "world_consistency": 5,
    "prose": 4,
    "rhythm": 4,
    "commercial": 4,
    "retention": 5,
    "long_term": 4
  },
  "issues": [
    "中段稍缓",
    "章末钩子可再加强"
  ],
  "recommendation": "revise",
  "provenance": {
    "reviewed_at": "2026-07-26T11:00:00Z"
  }
}
```

---

## 4.10 `FactCandidate`

### 用途
表示正文中提取出的、可能进入长期状态的事实候选。

### 字段建议

```json
{
  "fact_id": "FACT-001",
  "story_id": "STORY-001",
  "fact_type": "character_state",
  "source_chapter": "CH-001",
  "source_span": "L120-L145",
  "value": {
    "subject": "CHR-001",
    "predicate": "injured",
    "severity": "medium"
  },
  "confidence": 0.92,
  "status": "candidate"
}
```

---

## 4.11 `FactRecord`

### 用途
表示经过审批并 mint 后进入长期账本的事实。

### 字段建议

```json
{
  "fact_id": "FACT-001",
  "story_id": "STORY-001",
  "fact_type": "character_state",
  "source_chapter": "CH-001",
  "status": "minted",
  "value": {
    "subject": "CHR-001",
    "predicate": "injured",
    "severity": "medium"
  },
  "approval": {
    "decision": "approved",
    "reviewer": "human_or_system",
    "reason": "明确可验证"
  },
  "provenance": {
    "minted_at": "2026-07-26T12:00:00Z"
  }
}
```

---

## 4.12 `ReleasePackage`

### 用途
表示作品级或上架级发布包。

### 字段建议

```json
{
  "release_id": "REL-001",
  "story_id": "STORY-001",
  "version": "v1.0",
  "scope": "story",
  "artifacts": {
    "title_direction": "……",
    "description": "……",
    "tags": ["废土", "经营", "升级"],
    "golden_three_chapters": ["CH-001", "CH-002", "CH-003"],
    "chapter_summary_1_30": "……",
    "long_arc_summary": "……",
    "originality_report": "……",
    "risk_report": "……"
  },
  "decision": "publish",
  "provenance": {
    "assembled_at": "2026-07-26T18:00:00Z"
  }
}
```

---

# 5. 通用字段规范

---

## 5.1 标识字段

### 必须唯一
以下字段必须全局唯一：
- `story_id`
- `chapter_id`
- `character_id`
- `fact_id`
- `release_id`
- `volume_id`

### 建议格式
- `STORY-001`
- `CH-001`
- `CHR-001`
- `FACT-001`
- `REL-001`
- `VOL-001`

---

## 5.2 状态字段

### 常见状态建议
- `draft`
- `candidate`
- `approved`
- `rejected`
- `deferred`
- `minted`
- `frozen`
- `published`

---

## 5.3 provenance 字段

所有关键对象都应保留 provenance，至少包括：

- `generated_at`
- `generated_by`
- `version`
- `source_refs`
- `input_hash`
- `output_hash`

---

## 5.4 hash 字段

建议所有关键输出都保留：
- `content_hash`
- `state_hash`
- `artifact_hash`

用于：
- 回放
- 比对
- 去重
- 审计

---

# 6. 对象间关系

ANOVEL 的对象之间应形成明确引用链。

### 建议关系

```text
PositioningSpec -> StorySpec -> ArcPlan -> VolumePlan -> ChapterObjective -> ChapterDraft -> ReviewReport -> FactCandidate -> FactRecord -> ReleasePackage
```

### 说明
- 定位决定故事
- 故事决定长弧
- 长弧决定卷
- 卷决定章节目标
- 章节目标决定正文
- 正文生成评审
- 评审触发事实提取
- 事实审批后入账
- 作品最终进入发布包

---

# 7. 数据流约束

## 7.1 不允许跳层
不能绕过 `ChapterObjective` 直接生成发布包。  
不能绕过评审直接 mint 事实。  
不能绕过事实回流直接进入下一章。

## 7.2 不允许混层
不能把评审结果写进事实记录当事实。  
不能把草稿内容写进发布包当最终结果。

## 7.3 不允许丢 provenance
所有关键对象必须可追溯到来源和版本。

---

# 8. 版本管理

## 8.1 版本类型
建议至少区分：

- `spec_version`
- `prompt_version`
- `review_version`
- `arc_version`
- `story_version`
- `release_version`

## 8.2 版本原则
- 结构变更要升版本
- 评分规则变更要升版本
- 发布包生成规则变更要升版本
- 不同版本不得混用而不留痕

---

# 9. 最小可落地版本

如果团队先做 MVP，建议至少落地以下对象：

1. `PositioningSpec`
2. `StorySpec`
3. `ArcPlan`
4. `CharacterProfile`
5. `ChapterObjective`
6. `ChapterDraft`
7. `ReviewReport`
8. `FactCandidate`
9. `FactRecord`
10. `ReleasePackage`

---

# 10. 常见数据结构错误

### 10.1 字段过多但不稳定
问题：字段设计太复杂，团队无法长期维护。  
应对：先做最小可用结构，再逐步扩展。

### 10.2 版本不区分
问题：不同阶段输出混在同一结构里。  
应对：明确 version 字段。

### 10.3 provenance 缺失
问题：不知道对象从哪来。  
应对：所有关键对象都必须记录 provenance。

### 10.4 事实与评审混写
问题：把主观评分写进事实账本。  
应对：严格分层。

### 10.5 发布包与草稿混用
问题：未定稿内容直接进入发布结构。  
应对：草稿、候选、定稿、发布要分离。

---

# 11. 结论

ANOVEL 的数据结构规范，是把前面所有文档真正落到工程上的基础。

如果没有统一数据结构：

- 架构无法落地
- 评分无法比较
- 事实无法回流
- 发布无法追踪
- 百万字无法稳定维护

如果有了统一数据结构，ANOVEL 才真正具备成为中文网文百万字生产系统的工程基础。
