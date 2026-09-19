# ANOVEL 发布包规范

> 版本：v1.0  
> 适用范围：ANOVEL 百万字长篇生产系统  
> 目标：统一作品级发布包、上架包与审查包的内容结构、字段与生成规则  
> 原则：内容完整、版本唯一、可审查、可回放、可撤销

---

## 1. 文档目的

ANOVEL 的最终交付，不只是章节正文本身，而是一个完整的、可审查的发布包。

这个发布包用于：

- 上架前人工审核
- 平台提交
- 作品版本冻结
- 读者测试前校验
- 作品级发布决策
- 后续回滚与比较

发布包是 ANOVEL 把“作品”作为一个整体产品交出去的标准载体。

---

## 2. 发布包定义

发布包是一个包含作品关键信息、正文摘要、风险说明、原创性报告和版本信息的标准化交付集合。

它不是单个文件，而是一组结构化产物。

---

# 3. 发布包分层

ANOVEL 的发布包分为 3 个层级：

1. 章节发布包
2. 卷发布包
3. 作品发布包

---

## 3.1 章节发布包
用于单章审查和单章发布。

### 包含内容
- 章节正文
- 章节目标
- 评审结果
- 修订记录
- 事实回流记录
- 版本号
- provenance

---

## 3.2 卷发布包
用于一个卷或一组章节的整体审查。

### 包含内容
- 卷摘要
- 卷内章节列表
- 卷级目标
- 卷级钩子
- 卷级评分
- 卷级风险提示
- 卷内事实汇总

---

## 3.3 作品发布包
用于整部作品或一个较大阶段版本的发布。

### 包含内容
- 书名方向
- 简介
- 标签
- 卖点
- 黄金三章
- 前 30 章摘要
- 长弧摘要
- 角色卡
- 世界设定
- 原创性报告
- 风险报告
- 发布建议
- 版本号
- provenance

---

# 4. 作品发布包结构

推荐的作品发布包目录如下：

```text
release_pack/
├── package_manifest.json
├── title_direction.md
├── description.md
├── tags.md
├── selling_points.md
├── golden_three_chapters/
│   ├── CH-001.md
│   ├── CH-002.md
│   └── CH-003.md
├── chapter_summary_1_30.md
├── long_arc_summary.md
├── character_cards.md
├── world_rules.md
├── quality_report.md
├── commercial_report.md
├── retention_report.md
├── long_term_report.md
├── originality_report.md
├── risk_report.md
├── release_recommendation.md
└── provenance.json
```

---

# 5. 发布包核心文件说明

---

## 5.1 `package_manifest.json`

### 用途
发布包清单文件，描述当前包的版本、范围和结构。

### 字段建议

```json
{
  "release_id": "REL-001",
  "story_id": "STORY-001",
  "version": "v1.0",
  "scope": "story",
  "generated_at": "2026-07-26T18:00:00Z",
  "generated_by": "system_or_human",
  "artifact_list": [
    "title_direction.md",
    "description.md",
    "tags.md",
    "selling_points.md",
    "golden_three_chapters/CH-001.md",
    "golden_three_chapters/CH-002.md",
    "golden_three_chapters/CH-003.md",
    "chapter_summary_1_30.md",
    "long_arc_summary.md",
    "character_cards.md",
    "world_rules.md",
    "quality_report.md",
    "commercial_report.md",
    "retention_report.md",
    "long_term_report.md",
    "originality_report.md",
    "risk_report.md",
    "release_recommendation.md",
    "provenance.json"
  ]
}
```

---

## 5.2 `title_direction.md`

### 用途
记录书名方向和命名策略。

### 内容要求
- 题材风格
- 读者预期
- 命名方向
- 备选书名
- 风险提示

### 示例内容
- 书名应该体现“废土”“工坊”“崛起”“势力”等关键词
- 避免太泛、太文艺、太难传播

---

## 5.3 `description.md`

### 用途
记录作品简介。

### 内容要求
- 主角处境
- 核心卖点
- 初始冲突
- 第一阶段目标
- 追读理由

### 简介原则
- 一句话看懂卖什么
- 不要堆世界观
- 不要先讲设定
- 要让人想点开

---

## 5.4 `tags.md`

### 用途
记录平台标签与题材标签。

### 内容要求
- 主标签
- 次标签
- 商业标签
- 情绪标签
- 风险标签

### 示例
- 废土
- 经营
- 升级
- 势力流
- 热血
- 生存

---

## 5.5 `selling_points.md`

### 用途
总结本书的核心卖点。

### 内容要求
- 1–3 条核心卖点
- 每条卖点的持续性
- 每条卖点对应的剧情承载方式

### 示例
- 废土捡到神级工坊
- 从拾荒者到据点主
- 工坊升级驱动长期成长

---

## 5.6 `golden_three_chapters/`

### 用途
放置黄金三章。

### 要求
- 必须是最终定稿版本
- 必须能体现开篇钩子
- 必须能体现卖点
- 必须有清晰章末悬念

### 说明
黄金三章不是样章，而是发布级正文。

---

## 5.7 `chapter_summary_1_30.md`

### 用途
概述前 30 章的主要内容与阶段变化。

### 内容要求
- 每 5 章或每 10 章一段摘要
- 关键事件
- 主角成长
- 据点变化
- 敌人变化
- 钩子变化

### 作用
帮助审查者快速判断第一卷是否成立。

---

## 5.8 `long_arc_summary.md`

### 用途
概述 100 章或更长的长弧规划。

### 内容要求
- 阶段目标
- 卷结构
- 高潮点
- 地图切换点
- 核心伏笔
- 中后期扩展方式

### 作用
证明这本书不是只能写前几章。

---

## 5.9 `character_cards.md`

### 用途
记录主要角色卡。

### 内容要求
- 角色名
- 角色定位
- 性格
- 动机
- 说话风格
- 成长路径
- 关系状态

### 作用
证明人物有长期稳定基础。

---

## 5.10 `world_rules.md`

### 用途
记录世界规则和力量体系。

### 内容要求
- 世界背景
- 资源规则
- 力量体系
- 约束条件
- 禁忌规则

### 作用
证明设定自洽、可长期维护。

---

## 5.11 `quality_report.md`

### 用途
记录质量评分结果。

### 内容要求
- 结构评分
- 人物评分
- 设定评分
- 可读性评分
- 节奏评分
- 总分
- 问题列表

---

## 5.12 `commercial_report.md`

### 用途
记录商业价值判断。

### 内容要求
- 题材定位
- 卖点强度
- 付费点
- 平台适配度
- 竞争力判断

---

## 5.13 `retention_report.md`

### 用途
记录留存判断。

### 内容要求
- 开篇吸引力
- 章末钩子
- 追读动机
- 弃书风险

---

## 5.14 `long_term_report.md`

### 用途
记录长篇稳定性判断。

### 内容要求
- 设定稳定性
- 人设稳定性
- 节奏稳定性
- 伏笔管理
- 状态回流能力

---

## 5.15 `originality_report.md`

### 用途
记录原创性与风险控制结果。

### 内容要求
- 参考来源说明
- 模式抽象说明
- 重复风险
- 模仿风险
- 原创性结论

---

## 5.16 `risk_report.md`

### 用途
记录发布风险。

### 内容要求
- 内容风险
- 商业风险
- 留存风险
- 长篇风险
- 事实风险
- 发布建议

---

## 5.17 `release_recommendation.md`

### 用途
给出最终发布建议。

### 建议类型
- `publish`
- `revise`
- `hold`
- `reject`

---

## 5.18 `provenance.json`

### 用途
记录发布包来源与版本信息。

### 字段建议

```json
{
  "release_id": "REL-001",
  "story_id": "STORY-001",
  "version": "v1.0",
  "generated_at": "2026-07-26T18:00:00Z",
  "generated_by": "system_or_human",
  "source_artifacts": [
    "chapter_drafts",
    "review_reports",
    "fact_records",
    "arc_plans"
  ],
  "source_hashes": {},
  "build_hash": "sha256:..."
}
```

---

# 6. 发布包生成流程

---

## 6.1 输入
- 作品正文
- 章节评审
- 卷级评审
- 长弧规划
- 事实账本
- 角色账本
- 世界账本
- 风险信息

---

## 6.2 步骤
1. 汇总章节结果
2. 汇总卷级结果
3. 汇总作品级结果
4. 生成黄金三章
5. 生成前 30 章摘要
6. 生成长弧摘要
7. 生成角色卡与世界规则
8. 生成评分报告
9. 生成原创性与风险报告
10. 生成发布建议
11. 写入 provenance

---

## 6.3 输出
- 完整发布包目录
- 版本号
- 发布建议
- 可审查、可回放、可追踪的交付物

---

# 7. 发布包质量要求

## 7.1 完整性
所有必需文件必须存在。

## 7.2 一致性
正文、摘要、评分、事实、角色、世界规则之间必须一致。

## 7.3 唯一性
每个发布包必须有唯一版本号和唯一 hash。

## 7.4 可审查性
审查者应能通过发布包快速判断是否值得上线。

## 7.5 可回放性
后续应能通过 provenance 回放生成过程。

---

# 8. 常见错误

### 8.1 只有正文没有摘要
问题：审查效率低。  
应对：必须生成摘要和报告。

### 8.2 只有评分没有版本
问题：无法追踪。  
应对：必须有 release_id 和 version。

### 8.3 发布包和草稿混用
问题：未定稿内容进入发布结构。  
应对：草稿、候选、定稿、发布要分离。

### 8.4 事实与发布包不一致
问题：发布包里说的和账本里不是一回事。  
应对：发布前必须做一致性检查。

### 8.5 没有风险报告
问题：审查者不知道问题在哪。  
应对：风险报告必须独立存在。

---

# 9. 最小可执行版本

如果团队先做 MVP，建议至少实现：

1. `package_manifest.json`
2. `title_direction.md`
3. `description.md`
4. `tags.md`
5. `selling_points.md`
6. `golden_three_chapters/`
7. `chapter_summary_1_30.md`
8. `long_arc_summary.md`
9. `character_cards.md`
10. `world_rules.md`
11. `quality_report.md`
12. `commercial_report.md`
13. `retention_report.md`
14. `long_term_report.md`
15. `originality_report.md`
16. `risk_report.md`
17. `release_recommendation.md`
18. `provenance.json`

---

# 10. 结论

ANOVEL 的发布包规范，是把一部长篇小说从“写出来”推进到“能被审查、能被发布、能被比较、能被回滚”的关键一步。

它保证系统输出的不只是正文，而是一个完整、清晰、可维护的作品交付单元。
