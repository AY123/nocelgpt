# ANOVEL 样例包模板

> 版本：v1.0  
> 适用范围：ANOVEL 百万字长篇生产系统  
> 目标：统一样例包、金样包、评审包、训练包的结构，支持校准、回放、对比与归档  
> 原则：样例可追踪、标签可解释、来源可审计、用途可区分

---

## 1. 文档目的

ANOVEL 需要的不只是发布包，还需要样例包。

样例包用于：

- 金样集校准
- 章节评审训练
- 版本对比测试
- 模型行为观察
- 正负样本分析
- 爆款模板抽样
- 失败模式抽样

如果没有统一样例包，后续会出现：

- 样本结构不一致
- 标注语义混乱
- 评审结果难以对比
- 训练与校准混在一起
- 好样本与坏样本无法区分

因此，本模板定义 ANOVEL 的标准样例包结构。

---

# 2. 样例包定义

样例包是一个包含正文、元数据、标签、评分、说明、来源与用途的结构化样本集合。

它可以是：

1. 单章样例包
2. 连章样例包
3. 开篇样例包
4. 失败样例包
5. 金样集样例包
6. 训练样例包
7. 对照样例包

---

# 3. 样例包分层

ANOVEL 的样例包建议分为 4 类：

1. 正例样例包
2. 负例样例包
3. 边界样例包
4. 系统自产样例包

---

## 3.1 正例样例包
用于展示什么是“好”。

### 用途
- 评分校准
- 开篇模板提炼
- 爆款模式总结

### 特征
- 结构清晰
- 角色可信
- 节奏良好
- 钩子强
- 商业感强

---

## 3.2 负例样例包
用于展示什么是“坏”。

### 用途
- 风险识别
- 反例训练
- 失误模式总结

### 特征
- 设定冲突
- 人设崩坏
- 节奏拖沓
- AI 腔明显
- 留存弱

---

## 3.3 边界样例包
用于展示“临界状态”。

### 用途
- 评分校准
- 边界判断
- 争议样本分析

### 特征
- 好坏接近
- 评审分歧大
- 适合做仲裁样本

---

## 3.4 系统自产样例包
用于 ANOVEL 自己生产出来的章节、卷或发布包样本。

### 用途
- 版本比较
- 迭代回放
- 质量趋势观察

### 特征
- 有完整 provenance
- 可回放
- 可与真实结果对比

---

# 4. 样例包目录结构

建议统一使用如下目录结构：

```text
sample_pack/
├── sample_manifest.json
├── meta.json
├── body.txt
├── labels.json
├── human_scores.json
├── machine_scores.json
├── notes.md
├── provenance.json
└── assets/
    ├── cover.png
    └── excerpt.txt
```

---

# 5. 文件说明

---

## 5.1 `sample_manifest.json`

### 用途
样例包总清单文件。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "sample_type": "positive",
  "story_id": "STORY-001",
  "source_type": "human_curated",
  "version": "v1.0",
  "created_at": "2026-07-26T10:00:00Z",
  "files": [
    "meta.json",
    "body.txt",
    "labels.json",
    "human_scores.json",
    "machine_scores.json",
    "notes.md",
    "provenance.json"
  ]
}
```

---

## 5.2 `meta.json`

### 用途
记录样本基础元数据。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "title": "开篇强目标与危机并置",
  "genre": "玄幻",
  "subgenre": "升级流",
  "chapter_position": "opening",
  "source_type": "human_curated",
  "source_hint": "golden_three_chapter",
  "risk_flags": ["opening_slow", "ai_voice_risk"],
  "target_dimensions": ["opening_hook", "conflict_progression", "chapter_end_hook"]
}
```

### 说明
- `title` 应直接表达样本命题
- `source_hint` 用于说明来源性质
- `target_dimensions` 控制在 3–5 个核心维度

---

## 5.3 `body.txt`

### 用途
样本正文。

### 要求
- 保持原始正文结构
- 不要夹带额外解释
- 版本要明确
- 如为系统样本，需与 provenance 对应

---

## 5.4 `labels.json`

### 用途
定义样本标签和语义分类。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "primary_label": "positive",
  "secondary_labels": ["opening_hook", "conflict", "retention"],
  "difficulty": "medium",
  "boundary": false,
  "main_issue": null,
  "main_strength": "开篇目标明确，冲突迅速",
  "dimensions": {
    "opening_hook": true,
    "conflict_progression": true,
    "ending_hook": true,
    "continue_intent": true,
    "ai_voice_risk": false
  }
}
```

---

## 5.5 `human_scores.json`

### 用途
记录人工评分、双评、仲裁与最终裁定。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "reviewers": [
    {
      "reviewer_id": "R1",
      "scores": {
        "quality": 4,
        "commercial": 4,
        "retention": 5,
        "long_term": 4
      },
      "comment": "开篇抓力强，冲突明确"
    },
    {
      "reviewer_id": "R2",
      "scores": {
        "quality": 4,
        "commercial": 4,
        "retention": 4,
        "long_term": 4
      },
      "comment": "节奏稳定，钩子明确"
    }
  ],
  "final_decision": "positive",
  "arbitration": null
}
```

---

## 5.6 `machine_scores.json`

### 用途
记录模型评分结果。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "model_scores": [
    {
      "model": "claude",
      "scores": {
        "quality": 4,
        "commercial": 4,
        "retention": 4,
        "long_term": 4
      }
    },
    {
      "model": "gpt-5.5",
      "scores": {
        "quality": 4,
        "commercial": 4,
        "retention": 5,
        "long_term": 3
      }
    }
  ],
  "consensus": {
    "quality": 4,
    "commercial": 4,
    "retention": 5,
    "long_term": 4
  }
}
```

---

## 5.7 `notes.md`

### 用途
记录样本说明、校准重点、风险说明、使用建议。

### 内容要求
- 样本用途
- 样本特征
- 评审重点
- 争议点
- 注意事项

### 示例结构
- 证据摘要
- 校准重点
- 风险说明
- 适用范围

---

## 5.8 `provenance.json`

### 用途
记录样本来源、版本、生成方式与引用链。

### 字段建议

```json
{
  "sample_id": "QGS-00001",
  "origin": "human_or_system",
  "source_refs": [
    "chapter_id",
    "story_id",
    "run_id"
  ],
  "generated_at": "2026-07-26T10:00:00Z",
  "generated_by": "human_or_model",
  "content_hash": "sha256:...",
  "version_hash": "sha256:..."
}
```

---

# 6. 样例包命名规范

建议统一采用以下规则：

- 样例 ID：`QGS-00001`
- 正例：`positive`
- 负例：`negative`
- 边界：`boundary`
- AI 味：`ai_voice`
- 注水：`padding`
- 无冲突：`no_conflict`
- 人设崩坏：`character_degradation`
- 结尾失败：`ending_failure`

---

# 7. 样例包标签体系

建议样例包至少支持以下标签维度：

1. `opening_hook`
2. `conflict_progression`
3. `ending_hook`
4. `continue_intent`
5. `ai_voice_risk`
6. `continuity`
7. `information_density`
8. `payoff_delivery`
9. `character_motivation`
10. `world_consistency`
11. `commercial_fit`
12. `retention_fit`

---

# 8. 样例包使用场景

---

## 8.1 金样集校准
用于人工双评、模型评分和维度校准。

## 8.2 章节评审训练
用于训练 reviewer 或检查 reviewer 是否稳定。

## 8.3 模型比较
用于 Claude、GPT-5.5、Kimi-k3 等模型差异对比。

## 8.4 结构抽样
用于总结开篇模式、冲突模式、钩子模式。

## 8.5 失败模式分析
用于识别重复、拖沓、AI 腔、设定冲突等问题。

---

# 9. 样例包生成流程

1. 确定样例目的
2. 选定样本类型
3. 汇总正文
4. 填写元数据
5. 标注标签
6. 进行人工评分
7. 进行模型评分
8. 写入 notes
9. 补充 provenance
10. 生成 manifest

---

# 10. 样例包质量要求

## 10.1 完整性
每个样例包必须至少包含：
- `meta.json`
- `body.txt`
- `labels.json`
- `human_scores.json`
- `notes.md`
- `provenance.json`

## 10.2 可解释性
标签和评分必须能解释为什么这样标。

## 10.3 可比较性
不同样例包之间必须能比较。

## 10.4 可回放性
样例包应可用于后续分析和模型测试。

## 10.5 可审计性
来源、版本和变更必须可追踪。

---

# 11. 常见错误

### 11.1 样例标签过宽
问题：什么都能装，结果没法比较。  
应对：标签必须尽量具体。

### 11.2 样例说明过长
问题：正文与说明混杂。  
应对：正文和说明分开。

### 11.3 人工分数与机器分数混淆
问题：不知道哪个是人打的，哪个是模型打的。  
应对：两个文件严格分离。

### 11.4 provenance 缺失
问题：样本来源不明。  
应对：必须补 provenance。

### 11.5 没有边界样本
问题：训练和校准都太容易。  
应对：必须保留边界样本。

---

# 12. 最小可执行版本

如果团队先做 MVP，建议至少实现：

1. `sample_manifest.json`
2. `meta.json`
3. `body.txt`
4. `labels.json`
5. `human_scores.json`
6. `notes.md`
7. `provenance.json`

---

# 13. 结论

ANOVEL 的样例包模板，是让系统可以稳定使用正负样本、边界样本和自生样本进行校准、评审和比较的基础。

没有样例包，评分和学习闭环就会漂；  
有了样例包，ANOVEL 才能把“什么是好、什么是坏、什么是临界”稳定记录下来。
