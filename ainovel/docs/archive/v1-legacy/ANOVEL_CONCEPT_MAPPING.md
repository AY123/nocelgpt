# ANOVEL 概念映射表

> 版本：v1.0  
> 适用范围：ANOVEL 百万字长篇生产系统与现有仓库实现  
> 目标：将 ANOVEL 文档中的概念逐项映射到仓库中已存在的合同、模块、数据结构与运行边界，避免形成第二套设计源  
> 原则：概念可映射、实现不分叉、权威不重复、字段不另起炉灶

---

## 1. 文档目的

ANOVEL 新增文档的价值，不在于再造一套平行体系，而在于把作品生产治理层的概念，映射到仓库中已有的工程事实、合同和运行边界上。

本表用于回答三个问题：

1. ANOVEL 文档中的概念对应仓库里的什么实现
2. 哪些概念只是术语统称，不能当作新合同
3. 哪些概念已经与现有实现重叠，需要严格对齐

---

# 2. 映射原则

### 2.1 概念可以新增，权威不能新增
ANOVEL 文档可以引入新的治理语言，但不能另起一套实现权威。

### 2.2 文档统称不等于实现合同
例如 `ReviewReport`、`ReleasePackage`、`ChapterObjective` 可以作为文档统称，但实现层必须映射到已有对象。

### 2.3 现有实现优先
若仓库已有对应模块或合同，则 ANOVEL 文档只能解释、整理、收口，不能重新定义。

### 2.4 字段不平行分叉
凡已有 schema / contract / registry / derived artifact 的概念，ANOVEL 不应创建并行字段体系。

### 2.5 映射必须明确
每个重要概念都应明确：
- 统称是什么
- 对应实现是什么
- 是否重叠
- 是否需要修正文档表述

---

# 3. 概念映射总表

| ANOVEL 概念 | 现有仓库/合同中的对应物 | 关系判断 |
|---|---|---|
| `ANOVEL_PRODUCTION_ARCHITECTURE` 总架构 | `ROADMAP.md` 中的工程分层、生产链路、阶段冻结 | 方向一致，但 ANOVEL 更偏作品生产层 |
| `ANOVEL_MODEL_ROLE_SPEC` 模型角色职责 | `Model` 协议、真实 LLM adapter、execution loop 中的生成/评审分离 | 可映射，但不能写死模型名 |
| `ANOVEL_SCORING_SYSTEM` 评分体系 | `quality-report v2`、`reader-simulation v2`、`publish-readiness`、`review-report` | 部分重叠，需要明确量纲和权威来源 |
| `ANOVEL_OPENING_TEMPLATE` 开书模板 | `market-position`、`chapter-ir`、`director objective/brief`、开篇章节目标 | 可映射到开书前规划与章节目标层 |
| `ANOVEL_TEAM_EXECUTION_PLAN` 团队执行 | `WorkflowScheduler`、`serial run`、`execution pipeline`、`review loop` | 可映射到运行组织方式 |
| `ANOVEL_FACT_FLOW_SPEC` 事实流转 | `facts registry`、`FactCandidate`、`mint`、`state recompute` | 高度对应，需严格对齐现有事实写入规则 |
| `ANOVEL_REVIEW_GUIDE` 评审指南 | `quality-report`、`review-report`、`publisher review`、`draft reviewer` | 可映射，属于评审策略层 |
| `ANOVEL_REVIEW_SCORECARD_TEMPLATE` 打分卡模板 | `quality-report`、`review-report` 的字段结构和评审面板 | 可映射，为评审输出模板 |
| `ANOVEL_RELEASE_PROCESS` 发布流程 | `production-card`、`review-report`、`release/distribution` | 与现有发布/分发边界高度相关 |
| `ANOVEL_RELEASE_PACKAGE_SPEC` 发布包规范 | `release package`、`production card`、`publish-readiness`、`artifact bundle` | 可映射，属于发布交付包层 |
| `ANOVEL_DATA_SCHEMA_SPEC` 数据结构规范 | IDL / schema-first / contracts / registry contracts | 必须映射，不能另起一套字段体系 |
| `ANOVEL_LEARNING_LOOP_SPEC` 学习闭环规范 | `reader-signal`、`market snapshot`、`quality trend`、`strategy updates` | 可映射到反馈与策略更新层 |
| `ANOVEL_SAMPLE_PACK_TEMPLATE` 样例包模板 | gold sample / eval sample / fixture packs / comparison packs | 可映射为校准和评审样本 |
| `ANOVEL_GLOSSARY` 术语表 | 现有 ADR / contracts / README 中的术语 | 需统一术语，不可双定义 |
| `ANOVEL_DEPLOYMENT_CHECKLIST` 部署检查 | build gate / conformance / release checks / regression suite | 可映射到上线前检查层 |
| `ANOVEL_IMPLEMENTATION_ROADMAP` 实施路线图 | `ROADMAP.md` 的阶段推进 + ANOVEL 的阶段计划 | 可作为前向实施版，不冲突 |
| `ANOVEL_30_CH_BASELINE_SPEC` 30 章基线 | 30 章 run / baseline freeze / production sample | 与现有长篇验证思路一致 |
| `ANOVEL_100_CH_RUN_SPEC` 100 章长跑 | `serial run`、`checkpoint/resume`、`trend monitoring` | 高度对应，是长跑验证层 |
| `ANOVEL_PLATFORM_FEEDBACK_SPEC` 平台反馈规范 | `reader-signal`、平台数据导入、商业反馈分析 | 可映射到市场真实反馈 |
| `ANOVEL_MONITORING_DASHBOARD_SPEC` 监控面板规范 | `dashboard`、`trend board`、`health`、`alert` | 与现有监控读面高度对应 |
| `ANOVEL_REALITY_CHECKLIST` 现实校验清单 | `ROADMAP.md` 的 deferral / built / proof / audit mindset | 很一致，属于治理校验层 |
| `ANOVEL_FINAL_INTEGRATION_PLAN` 最终集成计划 | 整个工程核 + 内容生产层 + 商业层的总收口 | 可作为总整合叙事，但不能替代现有合同 |

---

# 4. 必须特别注意的重叠点

---

## 4.1 `ReviewReport`
ANOVEL 文档里用 `ReviewReport`，仓库里已经存在 `quality-report`、`review-report`、`publish-readiness` 等概念。

### 建议
- 文档层可把 `ReviewReport` 作为统称
- 实现层分别映射到：
  - `quality-report`
  - `review-report`
  - `publish-readiness`
- 不应再定义一套平行的发布评审字段体系

---

## 4.2 `PositioningSpec`
ANOVEL 的 `PositioningSpec` 与仓库已有的 `market-position` 基本同义。

### 建议
- 文档层保留“定位”统称
- 实现层明确用 `market-position`
- 不要再新增另一套字段体系

---

## 4.3 `ChapterObjective`
ANOVEL 的 `ChapterObjective` 与现有的 `chapter-ir`、`director objective`、`chapter mandate` 存在交叉。

### 建议
- ANOVEL 用它做“章节目标”的统称
- 实现层映射到 `chapter-ir` 和 `director objective`
- 不要再写两套平行结构

---

## 4.4 `FactRecord`
ANOVEL 的 `FactRecord` 与仓库现有 `facts registry`、`mint`、`state recompute` 是同一条链路。

### 建议
- 文档层把它作为“事实正式记录”统称
- 实现层继续沿用现有事实注册、Mint、重算机制
- 不允许文档再定义一套新的事实写入口

---

## 4.5 `ReleasePackage`
ANOVEL 的 `ReleasePackage` 与现有的 `production-card`、`review-report`、`publish-readiness`、`release/distribution` 存在交叉。

### 建议
- 把 `ReleasePackage` 作为“作品级发布包总称”
- 实现层拆到现有发布、审查、卡片、准备度对象中
- 不要新建完全平行的导出系统

---

# 5. 安全定位

为了避免“第二套系统”，ANOVEL 文档建议明确定位成三层：

## 5.1 术语层
用于说明“这个概念是什么”。

例如：
- 事实
- 定位
- 章节目标
- 发布包
- 评分体系

---

## 5.2 策略层
用于说明“这个概念为什么重要”。

例如：
- 先真人验证
- 先 30 章
- 再 100 章
- 高订阅要定义清楚
- 模型要基准驱动

---

## 5.3 映射层
用于说明“这个概念在仓库里对应什么实现”。

例如：
- `PositioningSpec` → `market-position`
- `FactRecord` → `facts registry + mint`
- `ReleasePackage` → `production-card + review-report + publish-readiness`

---

# 6. 实施约束

## 6.1 不要把 ANOVEL 当成第二套 schema 源
ANOVEL 文档可以提供治理术语，但不能绕开现有合同重新发明字段。

## 6.2 不要把文档术语直接当代码对象名
文档中的概念命名可以偏治理视角，但实现层必须与仓库既有命名统一。

## 6.3 不要重复定义已经冻结的合同
已有冻结 schema、contract、registry 的内容，应优先沿用，不要重新写一套。

## 6.4 不要把映射表当作实现本身
映射表只是治理层说明，不是代码实现替代。

---

# 7. 建议的文档维护方式

### 7.1 先有映射，再写规范
凡是新增 ANOVEL 术语，都应该先说明对应实现是什么。

### 7.2 有现有实现时只做统称
已有实现的概念，文档只做统称，不重新定义字段和存储结构。

### 7.3 任何新增字段都必须解释是否已有对应物
如果没有对应物，必须说明为什么需要新增；如果有对应物，必须说明为何不直接复用。

---

# 8. 结论

ANOVEL 概念映射表的核心作用不是“把名词对应起来”，而是确保文档体系与现有工程体系共存时，不产生第二套权威源。

只要遵守以下原则，ANOVEL 就是治理层补充，而不是实现层分叉：

- 概念可以新增
- 权威不能新增
- 术语可以统一
- 合同不能重复
- 映射必须明确

这能保证 ANOVEL 的文档体系真正服务于项目质量提升，而不是把项目带入更多维护复杂度。
