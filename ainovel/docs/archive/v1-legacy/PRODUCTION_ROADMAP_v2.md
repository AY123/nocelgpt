# ANovel 生产落实书 v2 — 从 Phase 7 到「参考小说→全自动完本」北极星

> 本文基于 2026-07-06 的仓库真实代码与最新 ROADMAP 撰写,非假设。凡涉及"当前已
> 落地到第几阶段"的快照事实,以 `ROADMAP.md`、项目 memory 索引与 `AI-Novel-Runtime/`
> 下的代码为准;本文与仓库冲突时,仓库赢。
>
> 撰写方法:先读仓库(README / ROADMAP / cli.py / execution/ / director/ /
> serialize/ / candidates/ / signals/ / outline/ / contracts/),再做差距分析。

---

## 0. 两个必须先讲的核实发现

**发现 A — README 与代码严重不一致(已在本轮同步修复)。**
`AI-Novel-Runtime/README.md` 曾停在 "Phase 4 complete / 300 pytest / 14 fitness",
只字未提 Phase 5/6/7。真实状态是 **Phase 7 完成、405 pytest 全绿 + 21 fitness +
19 conformance + 33 execution**。README 的 "Current Limits" 还把 recompute / ID
ledger / fact write-back 列为"未做",而 Phase 5 已全部交付。这是典型的快照腐烂,
本轮已同步 README。

**发现 B — Reference Intelligence / Auto Genesis / Multi-Agent 的骨架已存在。**
`runtime/outline/` 已有:参考小说摄入(`sources.py`,1–5 本,格式校验+hash)、
分析(`analyzer.py`)、**8 个稳定 Agent 角色**(`agents.py`:StructureAnalyst /
TropeAnalyst / **OriginalityGuard** / WorldBuilder / PlotArchitect /
CharacterDesigner / Critic / Synthesizer)、`derive_market_position` /
`propose_candidates` / `review_candidate`、以及 `run_outline_bootstrap`
(已接 CLI `outline bootstrap`)。**但它是确定性 mock(`mock-*-v1`),未接真实
LLM,不产 Novel Brain,不连正文生产链。** 因此这些不是"从零新建",而是
**"激活 + 接线 + 接真实模型"** —— 工作量与风险都远小于新建。这直接重排了路线图。

---

## 1. 总体判断

ANovel 已是一个**架构成熟、边界清晰、纪律极强**的生产系统骨架:build spine +
执行环 + 双轴 QA + facts/derived 分离 + ADR-009 人类授权(mint 是唯一 fact-writer,
带 `--confirm`)+ 完整可复现 / replay / 审计。从"单章可生产"到"多章连载可生产 +
事实可演化 + 导演可控制"这条主干已经打通(P14→P24→P5→P7)。

距离北极星「1–5 本参考小说 → 全自动百万字可上架完本 TOP 级」,**缺的不是地基,
而是三件事**:

1. **端到端串联**:参考理解 → 开书(含 Brain 生成)→ 长线规划 → 连载生产,目前是
   断成几段的能力孤岛。
2. **真实模型接入 + 编排**:几乎所有评价/生成层都是 seam + mock/deterministic,
   真实 LLM 是 drop-in 但未系统接入;且**没有 WorkflowScheduler** 来批量、可恢复、
   带审批点地跑几百章。
3. **人类授权的规模化**:mint 有单点 `--confirm`,但**没有 Approval Queue**把
   "几百章生产中的所有不可逆动作"组织成可批量审批的队列。

**一句话:地基世界级,缺的是"贯通 + 编排 + 规模化授权"。**

---

## 2. 当前能力与缺口(六分类)

### 2.1 已具备

| 能力 | 证据(模块) |
|---|---|
| 参考小说摄入 + 分析 + 多Agent大纲骨架(mock) | `outline/sources+analyzer+agents+workflow` |
| 单章正文生产(IR + Character Runtime + Brain风格 + prompt v6 导演目标) | `execution/`, `scene/`, `memory/`, prompt v6 |
| 多章连载链 + 状态折叠 + 运行清单 | `serialize/loop.py`, `run_manifest.py` |
| 双轴 QA + 质量v2 + 发布就绪 | `validator.py`, `quality-report.v2`, `publish-readiness` |
| 商业:读者仿真 + 商业优化环 + 市场定位/准入 | `execution/reader_sim+commercial`, `positioning/` |
| 事实演化闭环:候选→mint(唯一写手,`--confirm`)→recompute→ID Ledger | `candidates/`, `mint/executor.py`, `recompute/`, `idmint/` |
| 导演控制环(P7 完整):目标→生成→DirectorSession→跨章反哺→dashboard | `director/` |
| 上架包骨架:manuscript + IP bible 导出 | `export/` |
| 长篇记忆基础:StoryState 投影 + 伏笔追踪 + 长篇因果 gate | `memory/state+threads` |
| 真实信号 seam(未点火) | `signals/`(comparison-only, never-calibrates) |

### 2.2 半具备

- **参考理解 / 开书 / 多Agent**:骨架在,**是 mock,未接真实 LLM,未产 Brain,
  未接生产链**。
- **导演**:P7 已让它驱动生成 + 跨章反哺,但 compare/select 是薄适配器,
  **尚未真正跑多版本生成 + 择优**。
- **长线规划**:有 IR(单章)+ scene DSL + serial pacing(跨章节奏),但**没有
  "百万字级卷结构 + 100章方向 + 战力/升级体系"的长弧规划器**。
- **真实读者数据**:schema + reconcile 在,`calibrates:false` 结构性锁死,
  **seam 未点火**。

### 2.3 缺失

- **端到端 Genesis 编排**:参考 → Brain + Market Position + 角色库 + 事件库 +
  世界规则 + 前30章大纲,一条命令产出一个**可生产的新书项目**。
- **WorkflowScheduler**:可恢复、可批量、带审批点、失败回滚的几百章生产调度
  (ROADMAP 明确延期至今)。
- **Approval Queue**:把 mint/发布/定位修订等所有不可逆动作组织成可批量人工审批的
  队列 + 授权记录存储。
- **前100章长弧规划 + 战力/升级体系一致性检查**。
- **平台红线/敏感内容确定性 gate**(质量v2 提到 safety 拆分,但独立红线检查器待落地)。
- **成本预算与熔断**(run manifest 记录成本,但无预算上限/熔断)。

### 2.4 架构风险

1. **README 腐烂**(已确认并本轮修复)→ 否则新贡献者/新模型会误判进度。
2. **骨架-mock 长期不接线**会累积成第二种腐烂 —— outline mock 骨架就是候选;需明确
   "激活或删除"的触发条件(本落实书将其列入 P8 触发)。
3. **导演 compare/select 是薄适配器**:P8 多版本生成上马时,必须复用
   commercial/revision,**严禁长出第三个改写引擎**(已在 schema/注释钉死)。

### 2.5 产品化风险

- 真实 LLM 未系统接入 → 现在所有"质量/商业/留存"数字都来自 deterministic stub,
  **不代表真实产出质量**。项目历史已 3 次证明"只有真实模型跑才暴露真 bug"。
- 无编排 → 几百章靠人手敲 CLI,不可行。

### 2.6 商业化风险

- **原创性**:摄入侧有 OriginalityGuard 角色,但**真实 LLM 生成后的相似度检测**
  未落地 —— 上架前的法务生死线。
- **平台红线**:敏感内容确定性 gate 未确认 —— 一章违规可封书。
- **付费点/追订设计**:有商业环 + 定位,但**付费墙位置、黄金三章、卷级高潮**尚未
  成为生产**约束**(还只是评价信号)。

---

## 3. 核心建设模块清单

每个模块按字段说明。写入列严格遵守红线:AI 产候选,不直接写事实;facts 只由 mint 写。

### M1. Reference Novel Intelligence(激活 + 接真实模型)
- **目标**:从 1–5 本参考小说抽取题材/节奏/爽点/人设模式/商业模式/留存机制,产出
  **可复用的抽象特征**,严禁复制原文。
- **输入**:`sources/reference-novels/*`(已有摄入)。**输出**:`reference-analysis`
  (新 schema,derived)+ 喂 Market Snapshot/Brain 的特征包。
- **用 AI**:是。**角色**:复用 `agents.py` 的 StructureAnalyst/TropeAnalyst/
  **OriginalityGuard**,mock → 真实 LLM adapter(seam 已在)。
- **写入**:derived + sources(特征包),**永不 facts**。**审批**:否(纯分析);
  OriginalityGuard 结果进 Approval Queue 供人工确认。
- **贡献**:①质量 ②商业 ③留存 ⑤自动化。**衔接**:升级 `outline/analyzer`,产物喂 M2。

### M2. Auto Project Genesis(新建,端到端编排)
- **目标**:一条命令 `genesis`,从参考特征 + 少量人工偏好,产出一个**可生产的新书项目**。
- **输入**:M1 特征包 + 人工偏好(题材/主角/爽点倾向)。**输出**:`novel-brain.yaml` +
  `market-position` + 角色/世界规则**候选**(经 mint)+ 事件库骨架 + 前30章 outline +
  前100章方向。
- **用 AI**:是。**角色**:WorldBuilder/PlotArchitect/CharacterDesigner/Synthesizer
  (已在 agents.py)。
- **写入**:Brain/position 写 sources;角色/事件**走 candidates→mint(`--confirm`)**,
  不直接写 facts。**审批**:是(开书不可逆,ADR-009 + 已有 `market-admission`
  authority=human)。
- **贡献**:①②③⑤ 全部。**衔接**:消费 M1,产物喂 serial 生产链。

### M3. Long-Arc Planner(百万字规划,新建)
- **目标**:卷结构 + 100章方向 + 战力/升级体系 + 商业节奏(付费墙/卷级高潮)。
- **输入**:Brain + market-position + 事件库。**输出**:`long-arc-plan`
  (新 schema,derived/projection)。
- **用 AI**:是(PlotArchitect)。**写入**:derived。**审批**:方向级修订=人类
  (复用 direction-review 的 `market_position_revision`)。
- **贡献**:①④(不崩长弧)②③(卷级高潮/付费节奏)。**衔接**:喂 IR 生成 +
  serial pacing 的 cadence。
- **当前行动建议**:`long-arc-plan` 已接到 director/mandate、chapter objective、version comparison / selection；下一步把它写进运行文档，保持 as-built 账本同步。

### M4. Multi-Version Generation + Director Selection(激活导演的 compare/select)
- **目标**:每章生成 N 个候选,导演择优。
- **输入**:章节目标 + brief。**输出**:多草稿 + version-comparison + version-selection
  (schema 已在)。
- **用 AI**:是。**关键红线**:**复用 `commercial.compare_simulations` +
  `revision.rewrite_once`,不新建改写引擎**(已钉死)。**写入**:derived。**审批**:
  内部择优自动(Commercial Loop 先例),发布仍人类。
- **贡献**:①③(择优提升质量/钩子)。**衔接**:director/ + serialize/loop。
- **当前行动建议**:先把 compare/select 的输入升级为可接收 `chapter-mandate` 与 `director-brief` 的双输入,避免导演只看短章局部。

### M5. WorkflowScheduler(新建,ROADMAP 长期延期项)
- **目标**:把 CLI 能力升级为**可恢复、可审计、可批量、带审批点、失败回滚**的流水线,
  能跑几百章。
- **输入**:生产计划 + serial-plan。**输出**:`workflow-run`(带 checkpoint/断点续跑)。
- **用 AI**:否(纯编排)。**写入**:derived。**审批**:在不可逆节点插入 Approval Queue。
- **贡献**:⑤(核心)④(可恢复审计)。**衔接**:调度 serial run + mint + publish,
  消费 run-manifest。
- **调度边界**:
+  - checkpoint 只记录运行点与输入快照，不记录事实；
+  - resume 只从 checkpoint 恢复编排状态，不重放已确认的不可逆动作；
+  - rollback 只回退未确认的批次和 derived 产物，不回滚 facts；
+  - publish/mint/position 修订等不可逆动作一律进入 Approval Queue 后执行。
- **当前行动建议**:Scheduler 先做成编排层，复用现有 serial/mint/publish，不新造执行语义。

### M6. Human Approval Queue(新建)
- **目标**:把散落的 `requires_human_approval` 标志(candidates/plan、
  outline/import_plan 已有)组织成**统一审批队列 + 授权记录存储**。
- **输入**:待审批动作(mint/publish/开书/定位修订)。**输出**:`approval-request` /
  `approval-record`(append-only,可审计)。
- **写入**:derived(审批请求与授权记录)。**贡献**:④(审计/回滚)⑤(规模化授权,
  ADR-009 落地)。
- **现状**:已落地统一审批模型与队列,`genesis`/`mint` 已接入;`publish` 入口当前
  仓库尚未形成可执行链路,待后续补齐。
- **衔接**:mint executor / publishing / genesis 的授权点统一走它。

### M7. Originality & Platform-Red-Line Gate(新建/补全)
- **目标**:生成后相似度检测(防洗稿)+ 平台敏感内容确定性 gate。
- **用 AI**:相似度=是(embedding/检索);红线=**确定性检查(可 gate,ADR-003 正确应用)**。
  **写入**:derived(报告)。**审批**:命中上报人类。
- **贡献**:③(不被封)②(可上架)。**衔接**:插在 publish-readiness 之前。

### M8. Cost Budget & Circuit Breaker(新建)
- **目标**:每书/每批预算上限 + 超支熔断。
- **输入**:run-manifest 成本折叠(已有数据)。**输出**:`budget-report` + 熔断信号。
  **写入**:derived。
- **贡献**:④⑤(成本可控)。**衔接**:WorkflowScheduler 的准入检查。

---

## 4. 阶段路线图

> 复用你的编号但按**真实现状**重排(Genesis 前置、Reference 是激活非新建)。每阶段
> 独立可提交、独立可回归 —— 沿用项目已验证的纪律。

| Phase | 目标 | 关键任务 | 产物 | 验收 | 风险 | 优先级 | 为何排这 |
|---|---|---|---|---|---|---|---|
| **7.5 文档 + 真实基线** | 消除 README 腐烂;建真实 LLM 端到端基线 | 更新 README 到 P7;跑一次真实 DeepSeek 全链 | 更新的 README;真实 run-manifest | README 与代码一致;一次真实多章跑通 | 低 | **P0** | 腐烂文档误导后续;真实基线是质量判断前提 |
| **8. Auto Project Genesis** | 一条命令从参考+偏好开书 | 激活 outline agents 接真实 LLM;新增 Brain 生成;角色/事件走 mint | `genesis` 命令;Brain+position+outline+事件库 | 给参考能产出可生产新书项目 | 中(原创性) | **P0** | 北极星入口;骨架已在,ROI 最高 |
| **9. Reference Intelligence 深化** | 参考特征质量达标 + 原创性 | agents mock→真实;M7 相似度检测 | `reference-analysis`;相似度报告 | 特征可复用且过原创检查 | 中(洗稿) | **P1** | 依赖 P8 LLM 接线;决定商业合法性 |
| **10. Long-Arc Planner** | 百万字规划不崩 | M3 卷结构+100章方向+战力体系 | `long-arc-plan` | 产出连贯长弧+付费节奏 | 中 | **P1** | 依赖 Brain(P8);连载生产地图 |
| **11. Multi-Agent Production Room** | 每章多版本+导演择优 | M4 激活 compare/select;复用现有环 | 多草稿+comparison+selection | 择优可复现;不新建引擎 | 中(重复引擎) | **P1** | 依赖 P7 导演(已完成)+真实模型 |
| **12. Human Approval Queue** | 规模化人类授权 | M6 统一审批队列+授权记录 | `approval-record` | 所有不可逆动作走队列 | 低 | **P1** | ADR-009 规模化前提;调度依赖它 |
| **13. WorkflowScheduler** | 几百章可恢复批量生产 | M5 checkpoint+续跑+回滚+审批点 | `workflow-run` | 断点续跑;失败回滚无残留 | 高 | **P2** | 依赖 P8/12;真实生产量才需要 |
| **14. Platform Launch Package** | 可直接上架 | 简介/标签/标题/发布节奏+M7 红线 | 上架包+风险报告 | 产出平台可用上架物料 | 中(红线) | **P2** | 依赖前30章正文可用 |
| **15. Long-Form Maintenance** | 百万字维护 | 战力/时间线一致性检查;recompute 规模化 | 一致性报告 | 长跑不崩设定/伏笔 | 中 | **P2** | 依赖长弧规划+真实长跑 |
| **16. Real Reader Feedback Calibration** | 点火真实信号 seam | 谨慎开启 calibration(仍 comparison-first) | 校准建议 | 真实数据产出调整建议(不自动改) | 高(过拟合) | **P3** | 需真实上架数据;最后一环 |

---

## 5. P0 / P1 / P2 / P3 优先级(含依赖)

- **P0(立即)**:7.5 文档+真实基线 → 8 Genesis。文档腐烂阻碍一切;Genesis 是北极星
  入口且骨架已在(激活 ROI 最高)。依赖:真实 LLM adapter(seam 已在)。
- **P1(紧跟)**:9 Reference深化 · 10 Long-Arc · 11 Multi-Agent · 12 Approval Queue。
  构成"开书→规划→多版本生产→可授权"的最小可上架闭环。全部依赖 P8 的 LLM 接线;
  11 依赖已完成的 P7 导演;13 依赖 12。
- **P2(中期)**:13 Scheduler · 14 Launch Package · 15 Maintenance。真实生产量 +
  上架需求出现后才有消费者(避免建 stub)。
- **P3(长期)**:16 真实读者校准。必须先有真实上架数据。

**依赖链**:文档→Genesis→(Reference深化‖Long-Arc‖Approval)→Multi-Agent→
Scheduler→Launch→Maintenance→Calibration。

---

## 6. M5 总体架构设计与实施拆分

### 6.1 M5 的定义

`M5` 定义为**正文生产闭环阶段**:系统从"能编排任务"升级为"能稳定产出高质量、可连载、可商业化的正文"。

M5 的核心不是继续强化编排,而是把章节生产本身做成可审计、可恢复、可迭代的生产线。它只负责正文生产链路,不再接管 M4 的调度/准入/预算/批次审计。

### 6.2 M5 的总体目标

M5 必须同时满足五个目标:

1. 小说质量高:结构完整、人物可信、设定稳定、节奏优秀、章末钩子强。
2. 商业价值高:题材卖点明确、付费点清晰、平台适配强、转化导向明确。
3. 读者留存强:开篇抓人、每章有推进、连载动机持续、追更意愿强。
4. 长期维护好:百万字级别不崩设定、不崩人设、不崩节奏、不丢伏笔。
5. 自动化生产强:从大纲到正文、从正文到评审、从评审到修订、从修订到定稿,形成可审计/可恢复/可扩展流水线。

### 6.3 M5 模块树

#### A. Chapter Production Orchestrator
章节生产调度器,负责章节级生成/评审/修订循环与失败重试,记录章节级状态。

#### B. Chapter Intent Builder
把章节目标、角色状态、事件目标、商业目标、节奏目标、钩子目标折叠成章节意图。

#### C. Scene / Beat Planner
把章节意图拆成场景、情节点、信息点、情绪点、冲突点和章末钩子。

#### D. Draft Writer
在场景与约束基础上生成正文草稿。

#### E. Chapter Reviewer
对草稿进行结构、节奏、人物、设定、可读性、商业性评审。

#### F. Revision Engine
根据评审意见做局部修订,保持事实与设定稳定。

#### G. Continuity Guard
持续检查角色漂移、设定冲突、因果断裂、伏笔遗漏和情绪节奏断裂。

#### H. Commercial Hook Optimizer
优化开篇吸引点、每章推进点、章末悬念、付费点和升级/反转节奏。

### 6.4 M5 数据对象

- `ChapterIntent`
- `BeatPlan`
- `ChapterDraft`
- `ChapterReview`
- `ChapterRevision`
- `ChapterFinal`

### 6.5 M5 生产流程

1. 章节输入装配
2. 章节意图构建
3. 场景/节拍规划
4. 草稿生成
5. 第一轮评审
6. 修订
7. 第二轮评审
8. 定稿输出

### 6.6 M5 实施拆分

| 子阶段 | 目标 | 交付 | 验收 |
|---|---|---|---|
| M5.1 | 章节生产骨架 | Chapter Production Orchestrator + Intent/Beat/Draft/Review/Revision/Final | 能从章节目标生成初稿、评审、修订并输出定稿 |
| M5.2 | 章节质量控制 | 多维评分、结构完整性、节奏、钩子、可读性、商业性检测 | 每章都有结构化质量报告，能判定可发布/需修订/不可发布 |
| M5.3 | 连续性与设定稳定 | 角色状态跟踪、设定一致性、因果链、伏笔追踪 | 能发现角色漂移、设定冲突与伏笔遗漏 |
| M5.4 | 商业留存优化 | 开篇钩子、章末钩子、留存动机、升级/打脸/反转节奏 | 每章输出商业可读性评估 |
| M5.5 | 自动修订闭环 | reviewer 驱动修订、修订历史、再评审、质量门 | 初稿不一定好,但最终稿稳定过线 |

### 6.7 M5 验收标准

M5 完成时,系统应能稳定满足:

- 持续产出完整章节
- 每章有明确目标
- 正文有结构
- 节奏可控
- 人设稳定
- 设定稳定
- 钩子清晰
- 修订闭环可用
- 结果可审计
- 长篇连载不崩

### 6.8 M5 与 M4 的边界

- M4: 解决任务怎么跑、怎么恢复、怎么准入、怎么审计、怎么控预算。
- M5: 解决章节怎么写好、怎么稳定产出正文、怎么控制作品质量、怎么提升留存和商业性。

### 6.9 当前代码落点(已实现,用于补充说明)

M5 的第一轮代码提交已经把章节生产闭环的骨架接起来了,对应以下落点:

- `runtime/chapter/orchestrator.py`: 统一串起意图构建、节拍规划、草稿生成、评审、修订、候选版本比较与最终定稿。
- `runtime/chapter/reviser.py`: 提供基于评审结果的修订引擎,并可生成多种候选版本供导演选择。
- `runtime/chapter/finalizer.py`: 汇总最终章节输出,生成最终 hash、质量摘要、连续性备注与商业备注。
- `runtime/chapter/types.py` 与 `contracts/chapter/chapter-final.schema.json`: 扩展章节定稿的数据结构与契约字段,支持比较结果、最终策略、最终状态等信息。
- `runtime/director/compare.py` 与 `contracts/version-comparison.schema.json`: 为多版本章节候选提供统一比较与择优报告,服务于 M5 的多版本生产闭环。
- `runtime/dashboard/report.py` 与相关测试: 将章节生产/比较信息纳入仪表盘报告与回归测试,确保流水线结果可观测、可审计。

这轮提交的文档补充仅用于解释代码已经实现到哪一步,不改变 M5 的目标边界;M5 仍然只负责"章节怎么写好",不接管 M4 的调度、准入、预算与批次审计。

## 7. 多 Agent 设计(Production Room)

复用 `outline/agents.py` 已有 8 角色 + 导演,分三层。**上下文隔离靠"每个 Agent 只吃
结构化产物,不共享自由文本记忆"**:

```
┌─ Genesis 层(开书时跑一次)──────────────────────────┐
│ StructureAnalyst / TropeAnalyst / OriginalityGuard   │ ← 只读参考,产结构化特征
│ WorldBuilder / PlotArchitect / CharacterDesigner     │ ← 产 Brain/世界/人设候选
│ Synthesizer                                          │ ← 合并为 outline + 长弧
└──────────────────────────────────────────────────────┘
              ↓ 产物(schema化)喂给
┌─ Chapter 层(每章跑)────────────────────────────────┐
│ Director(已完成)= 定目标→brief                      │ ← 唯一决策者
│ Drafter ×N(多版本正文)                              │
│ QualityReviewer / ReaderSimulator / CommercialLoop   │ ← 评价,永不 gate
│ Director.compare/select = 汇总择优(复用现有环)      │
└──────────────────────────────────────────────────────┘
              ↓ 不可逆动作
┌─ Authority 层 ───────────────────────────────────────┐
│ FactCandidate→Mint(--confirm)/ Publish / Approval Q  │ ← 只有这里能对外/写事实
└──────────────────────────────────────────────────────┘
```

**污染防治(关键)**:每个 Agent 的输入是**上游产物的 schema 化投影**
(objective/brief/IR/character-runtime),不是"整本书的对话历史"。这正是项目
`state_digest` + 投影架构的用途 —— **Agent 之间通过 derived artifact 通信,不通过
共享 context**。Director 是唯一汇总者(DirectorSession 记录决策链)。

---

## 7. 关键数据流

```
参考小说(sources/reference-novels/)
  │  [Reference Intelligence: agents+真实LLM] ── OriginalityGuard →→ Approval Queue
  ▼
reference-analysis(derived)+ 人工偏好
  │  [Auto Project Genesis]
  ├─► novel-brain.yaml (sources)          ← 授权:人类确认开书
  ├─► market-position (sources) ─[positioning admit]─ market-admission(human)
  ├─► 角色/世界规则/事件 ─[candidates→mint --confirm]─► registry/facts/**  ← 唯一写事实处
  └─► 前30章 outline + long-arc-plan (derived)
  ▼
[serialize/loop 每章]  StoryState=fold(facts,events)  ← 投影,非可变
  ├─ Director: objective + brief (v6 prompt)
  ├─ Drafter ×N → version-comparison → selection
  ├─ Quality/Reader/Commercial(advisory,never gate)
  ├─ 确定性 gate:draft-QA + 红线 + 因果 → 可 gate
  ├─ DirectorSession(骑信封,审计)
  └─ 跨章反哺:objective(N+1)=fold(chapter N 信号)
  ▼
publish-readiness(human authority)→ Platform Launch Package → [人工发布]
  ▼
真实读者信号(signals/, comparison-only)→(P3)校准建议(不自动改)
  ▲
run-manifest 全程记录:prompt/model/cost/hash/version(可复现可审计)
```

---

## 8. 风险与架构红线(逐条守住)

| 红线 | 现状落地 | 后续要求 |
|---|---|---|
| 1. AI 不直接写事实 | ✅ mint 是唯一写手 | Genesis 角色/事件必须走 candidates→mint |
| 2. facts 人工授权 | ✅ `--confirm` + guard #16 | 接入 Approval Queue 规模化 |
| 3. 不自动发布 | ✅ publish authority=human | Launch Package 只暂存不发布 |
| 4. 预测不 gate | ✅ 双轴 QA + gating const false | 新评价模块继承此约束 |
| 5. 参考不抄袭 | 🟡 OriginalityGuard 角色在(mock) | **P1 必须补真实相似度检测**(最高商业风险) |
| 6. schema-first | ✅ Standard 是契约源 | 新产物先建 schema |
| 7. 调用可追溯 | ✅ produced_by.llm + replay | 新增预算维度 |
| 8. 不可逆有 approval record | 🟡 有标志,无统一存储 | **P1 建 approval-record schema** |
| 9. 可重放/审计/回滚/版本演化 | ✅ 全套 | Scheduler 补断点续跑/回滚 |

**新增确定性 gate(合规,ADR-003 正确应用)**:平台红线检查器(M7)—— banned terms/
敏感线,可 gate 构建。这不违反"预测不 gate",而是"确定性可 gate"的正确使用。

---

## 9. 商业网文专业要求(不能只讲工程)

把网文商业规律**变成生产约束**,而非事后评价。落地方式如右列:

| 商业要素 | 现状 | 变成生产约束的方式 |
|---|---|---|
| 开篇黄金三章 | 有 IR + 导演目标 | 前 3 章 objective 强制 `cliffhanger_type` + 高钩子密度;红线:开篇跳出风险 |
| 前 10 章追读 | reader-sim 有 continue_prob | long-arc-plan 规定前 10 章每章必留悬念;跨章反哺监控追读掉落 |
| 前 30 章商业承诺 | positioning admit 有此检查 | Genesis 必须产出 30 章内兑现的 `commercial_promise` |
| 首订/追订/打赏/月票 | commercial 6 persona | 付费墙位置写入 long-arc-plan;付费点章 objective 强化 payoff |
| 爽点密度 | 无显式度量 | IR beat 增加"爽点标记";pacing 检查爽点间隔 |
| 情绪曲线 | scene pacing 已有 valence | 已有;serial pacing 监控卷级节奏 |
| 章末钩子 | 导演 `cliffhanger_type` | 已是 objective 字段;红线:钩子缺失告警 |
| 人物关系张力 | character-runtime 有 tension | 已投影;长弧规划维护关系演进 |
| 主线推进 | IR + 事件因果 | 已有;long-arc 保证每卷主线净推进 |
| 卷级高潮 | serial pacing cadence | 已有 cadence_chapters;Genesis 设定卷高潮章 |
| 免费→付费转化 | 无 | long-arc-plan 标注付费墙章 + 转化钩子设计 |
| 长期升级路径 | 无战力体系 | M3 战力/升级体系一致性检查(P1) |
| 防套路化/原创性 | OriginalityGuard(mock) | M7 真实相似度检测(P1);Brain `forbidden_style` |
| 平台红线/敏感 | quality v2 safety 拆分 | M7 确定性红线 gate(可 gate,P2) |

---

## 10. 验收标准

| # | 验收项 | 达标定义 |
|---|---|---|
| 1 | 参考→新书项目 | `genesis` 给 1–5 本参考+偏好,产出含 Brain+position+角色库+事件库+outline 的可生产项目,通过 gate |
| 2 | 前30章 outline | long-arc-plan + 前30章 outline schema 校验通过,含卷结构+付费节奏 |
| 3 | 前10–20章可上架正文 | 真实 LLM 产出,过确定性 gate + 红线 + 原创检查,publish-readiness=可发布 |
| 4 | 百万字长线规划 | long-arc-plan 覆盖 100+ 章方向+战力体系,一致性检查无崩 |
| 5 | 多Agent评审修订 | 每章多版本+导演择优+修订,DirectorSession 可复现 |
| 6 | 上架包 | 产出简介/标签/标题/章节/IP bible/发布节奏+红线报告 |
| 7 | facts+continuity | mint 全程只加不改;伏笔回收率/因果/时间线检查通过 |
| 8 | 调用+成本记录 | run-manifest 记录每次 prompt/model/cost/hash;预算不超限 |
| 9 | 真实数据反馈 | 接入真实信号,产出调整**建议**(comparison-only,不自动改生成) |

**北极星综合验收**:一条 `genesis + workflow run` 能在预算内、带人工审批点、可断点
续跑地产出 ≥20 章可上架正文 + 百万字规划 + 上架包,全程可复现可审计。**先达此
"垂直切片",再扩章数。**

---

## 11. 最近 30 天建议推进任务

**Week 1 — P0 清障 + 真实基线**
1. ✅ 更新 `README.md` 到 Phase 7(本轮已完成,消除腐烂)。
2. 接一次真实 DeepSeek 跑现有 serial v6 全链,产出真实 run-manifest,**建立质量/成本
   基线**(项目历史证明:只有真实跑暴露真 bug)。
3. 决策:outline mock 骨架 —— 明确"接真实模型"的触发已到,列入 P8。

**Week 2–3 — P0 Genesis 垂直切片**
4. 把 `outline/agents.py` 的 mock 换成真实 LLM adapter(seam 已在,drop-in)。
5. 新增 **Novel Brain 生成**(Genesis 产 `novel-brain.yaml`)—— 当前 Brain 是人工授的,
   这是最大断点。
6. 打通 `genesis` 命令:参考 → Brain + position + outline + 角色/事件候选
   (走 mint `--confirm`)。
7. 验收:给 1 本参考,产出一个能跑 serial 的新书项目。

**Week 4 — P1 起步 + 合规**
8. `approval-record` schema + 把 candidates/outline 已有的 `requires_human_approval`
   标志接入统一队列(M6 最小版)。
9. **原创性相似度检测最小版**(M7 上半)—— 生成正文 vs 参考的相似度报告,进
   Approval Queue。**这是上架法务生死线,不能拖到 P2。**

**30 天目标**:从"能生产单本已授权项目的章节"推进到"**给参考小说 → 自动开出一本
新书 → 产出前几章正文 → 关键动作有审批记录 → 有原创性报告**" —— 即北极星的
**最小垂直切片**。

---

## 12. v2.1 战略重排 —— Novel → Architecture(质量优先)

> 2026-07-06 追加。核心令:**项目已过"造编译器"阶段,后续约 70% 资源投入小说质量
> 系统。所有工程设计必须回答"它让小说更好了吗",否则不开发。** 本节把这一战略令
> 落成可执行的重排,并用真实代码校准了原始诊断。

### 12.1 用代码校准四大短板(避免重复造轮子)

原始诊断点名"叙事智能/角色/留存/商业评审"四大短板。核实代码后,**只有一个是真绿地,
另三个是深化/激活** —— 这决定钱怎么花:

| 短板 | 代码真相 | 结论 |
|---|---|---|
| ①叙事智能:不会规划故事(为什么是现在/冲突升级/心理变化) | 只有单章 `scene/ir.py` + 跨章 pacing 曲线;**确无跨章叙事规划器** | ✅ **真绿地,第一优先** |
| ②角色只是数据库 | 已有 goal/pressure/secret/fear/desire/relationship_tension/growth_stage/next_likely_action;缺 emotion/belief/value/memory/decision_policy | 🟡 **深化,非新建** |
| ③留存只是点评 | 已有 continue_probability/pay_probability/drop_point/drop_reason(6+6 persona);缺全书章级留存曲线 | 🟡 **深化(且见 12.3 红线)** |
| ④商业评审太弱,应结构化 | Quality v2 **已有 18 维**(hook/retention/subscription/emotion/commercial/pacing/...);缺"接真实 LLM 评分+成为裁判" | 🟡 **激活,非新建** |

**含义:不是建 4 个新系统,而是 1 个真绿地 + 3 个深化/激活。** 90% 力气花在"让骨架接
真实模型 + 加心理/决策深度",而非重造。

### 12.2 质量系统的层次(三大脑 + 一裁判 + 生成侧三件套)

```
                    ┌──────────────────────────────┐
                    │   Novel Quality Engine(18维,真实LLM)         │ ← 最高裁判
                    │   裁"改稿+发布",不裁 build(守 ADR-003)       │
                    └───────────────┬────────────────┘
        ┌───────────────────┼────────────────────┐
 ┌──────▼───────┐   ┌───────▼────────┐   ┌───────▼────────┐
 │ Narrative Intel   │   │ Character Intel   │   │ Reader/Commercial │
 │ (绿地:跨章规划)   │   │ (深化:心理+决策) │   │ Intel(深化:曲线) │
 │ why-now/升级/心理弧│  │ +emotion/belief/  │   │ 相对留存曲线+     │
 │                    │   │ decision_policy   │   │ 弃书热点定位      │
 │                    │   │ +Speech Profile   │   │                   │
 └───────────────┘   └────────────────┘   └────────────────┘
 ── 生成侧(每章正文更像人写)──────────────────────────────────
 Author Persona(Novel Brain 深化,300万字风格不乱)
 Humanization Engine(每章写完立即去 AI 味,不最后统一润色)
 AI Trace Judge(只做 Advisor,永不 Gate)
```

**"最高裁判"的正确落位**:Novel Quality Engine 驱动 **revision loop + publish-readiness**
(改稿轴 / 发布轴),**不驱动 deterministic build gate**(构建轴)。这正是 P4.1 的
`Build Gate ≠ Publish Readiness` 设计。质量说了算,但不卡死流水线。

### 12.3 一条不可破的红线:相对留存,不做伪精确绝对预测

原始诉求要"第3章弃书率=18%"这类**绝对预测**。但 reader-simulation 的 schema 写死了
`comparison_only: true` / `gating: false`(const)—— 它的数字**只在"改写前 vs 后"的相对
比较里有意义,永不作为绝对真理**。理由:读者反应是不可证伪的预测。

**若破此线的后果**:系统会为了刷低"18%"这个幻觉数去改稿 —— **为假指标牺牲真质量**。
这与原始诊断里"AI Trace Judge 千万不要 Gate"是同一个道理。

**正确落地**(既满足商业诉求,又不破红线):
- ✅ 章级**相对留存曲线**(每章相对基线的 retention delta)
- ✅ **弃书热点定位**(drop_point + drop_reason 聚合成"哪几段是掉读高危")—— 诊断,非绝对预测
- ⏳ 绝对百分比 → 只在接入**真实平台数据**后校准(P3 signals 点火),且**仍是建议不是 gate**

### 12.4 质量优先重排后的阶段序(接续第 4 节路线图)

依赖现实:**质量系统需要一本活的书作为改进对象**。故策略是
**"薄 Genesis 解锁 → 70% 力气砸三大脑 → 三大脑回喂 Genesis"**。

| 阶段 | 名称 | 性质 | 优先级 | 服务的质量维 | 为何这个位置 |
|---|---|---|---|---|---|
| **8** | Minimal Genesis + 真实模型基线 | 解锁(薄) | **P0** | — | 没有活书,三大脑无作用对象;顺带建立真实质量基线 |
| **9** | Narrative Intelligence(跨章规划器) | **绿地** | **P0** | hook/conflict/pacing/serial_sustainability | 唯一真绿地,防流水账核心 |
| **10** | Character Intelligence(心理+决策+Speech) | 深化 | **P1** | character_consistency/growth/emotion | AI 最易翻车处 |
| **11** | Novel Quality Engine(18维接真实LLM,当改稿裁判) | 激活 | **P1** | 全部18维 | 让质量真正说了算(改稿+发布轴) |
| **12** | Reader/Commercial Intelligence(相对留存曲线+热点) | 深化 | **P1** | retention/subscription/reader_drop_risk | 商业价值,守 12.3 红线 |
| **13** | Author Persona(Novel Brain 深化) | 深化 | **P2** | 全书风格一致 | 300万字风格不乱 |
| **14** | Humanization Engine(每章即时去AI味) | 绿地 | **P2** | 正文可读性 | 不最后统一润色 |
| **14b** | AI Trace Judge(仅 Advisor) | 绿地 | **P2** | — | 只诊断,永不 gate |
| **15+** | Scheduler / Launch / 真实数据校准 | 保持 v2 位置 | **P2/P3** | — | 真实生产量出现才有消费者 |

### 12.5 资源分配(70/20/10 变成准入约束)

| 方向 | 比例 | 对应阶段 | 硬约束 |
|---|---|---|---|
| **小说质量系统** | **70%** | 9·10·11·12·13·14·14b | 每模块必须声明服务哪几维质量,否则不批 |
| **自动化生产** | **20%** | 8·15 Scheduler·Launch | 只在有真实生产量时深投 |
| **工程能力** | **10%** | 真实模型适配/多模型调度/可观测/性能 | 除必要维护,不再扩基础设施 |

### 12.6 三条锋利裁决(Chief Architect 定调)

1. **同意 Novel → Architecture 翻转**,并变成准入约束:PR 若答不出"让哪几维质量更好",不批。
2. **纠正执行误区**:四短板只有"跨章叙事规划器"是绿地,另三个是激活/深化,别当新建做。
   **且最紧急的第一件事是接真实模型** —— 现所有质量数字来自 deterministic stub,
   **你还没看过系统真实的小说质量**。
3. **守住最值钱的纪律**:Quality Engine 裁改稿/发布,不裁 build;绝对留存率、AI Trace
   只做 Advisor。**一旦让评价性判断 gate 构建、或去刷幻觉指标,就是为假数据牺牲真质量。**

### 12.7 成熟度自评(对齐战略视角)

| 维度 | 评级 | 说明 |
|---|---|---|
| 工程能力(编译器/流水线/契约/QA/replay/多Agent) | ★★★★★ | 世界优秀,可作优秀开源工程 |
| 小说生产能力(世界观/大纲/refine/review/连续性) | ★★★☆☆ | 中等偏上,距 TOP 级稳定生产有大空间 |
| 商业价值 | ★★☆☆☆ | 最缺 Narrative + Commercial + Reader 三大智能,非缺模型 |

**结论**:工程地基世界级,后续价值几乎全在小说质量。本重排即为此服务。

---

## 13. Phase 9 详细设计:Narrative Intelligence — 跨章叙事规划器

> 2026-07-06 追加。这是 v2.1(§12)确认的**唯一真绿地**,也是防流水账的核心。本节
> 是 schema-first 详细设计,尚未落代码。设计前已核实现有层次(chapter-objective /
> chapter-ir / scene-plan)以避免造重复层。
>
> **触发条件(2026-07-08 更新)**:Phase 9 须坐在 chapter-objective 之上,但 §14.3.1
> Activation Sprint 之前 objective 根本没上线(整栈跑在 prompt v1)。**A.1–A.4 已完成
> (栈激活+真实 before/after 验证)**,chapter-objective/ir/scene-plan/character-runtime
> 现已 0→12 进入真实生产路径,Phase 9 的前置真空已填平,可以开工。

### 13.1 定位:它填哪个真空,不碰哪些已有层

现有生产层的 lowering 链:
```
outline(粗意图)→ chapter-objective(导演:这章要什么)
             → chapter-ir(单章:五个叙事操作)→ scene-plan(节拍)→ draft
```

| 层 | 已有?回答什么 | 时间尺度 |
|---|---|---|
| outline | ✅ 粗略卷/章意图 | 全书(静态) |
| **chapter-mandate(新)** | ❌ **为什么是现在 / 冲突升到哪 / 心理弧走到哪 / 净推进什么** | **跨章(N 依赖 N-1)** |
| chapter-objective(导演) | ✅ 这章要什么(retention/payoff/cliffhanger) | 单章 |
| chapter-ir | ✅ 五个叙事操作(turn/emotion/info/question/hook) | 单章内 |
| scene-plan | ✅ 节拍骨架 | 章内 |

**关键判断**:planner 的独特价值是**跨章**——回答"为什么是现在、冲突升级到哪、心理弧
走到哪",这是当前所有层都不覆盖、导致流水账的真空。所以 `chapter-mandate` 坐在
**objective 之上**,是"连载张力弧"投影到单章的**强制令**;它**约束** objective,不替代。
这与项目 compiler lowering 架构同构——**新增更高的 IR 层,不是并列层**。

### 13.2 核心契约:`narrative-mandate.schema.json`(四个防流水账硬字段)

```jsonc
{
  "kind": "narrative_mandate",
  "authority": "human",   // const,ADR-009(方向级修订人类授权)
  "gating": false,        // const,ADR-003(评价性,永不 gate build)
  "chapter_no": 42,
  "task_id": "TASK-00042",

  // ① why-now:为什么主角现在必须行动,不能等(防"温水章")
  "why_now": {
    "trigger": "对手在今夜宴会公开羞辱,拖到明日则家族彻底出局",
    "cost_of_delay": "high",   // enum: none|low|medium|high (none=流水账信号)
    "clock": "宴会结束前"       // 可选:时间压力锚
  },

  // ② escalation:冲突相对上一章是否升级(跨章张力阶梯)
  "escalation": {
    "from_level": 5, "to_level": 6,   // 0-10 阶梯,fold 自上一章 mandate
    "kind": "stakes_raise",           // enum: stakes_raise|new_antagonist|
                                       //   reversal|betrayal|time_pressure|
                                       //   power_reveal|flat (flat=预警)
    "vs_previous": "对手从个人刁难升级为动用家族势力"
  },

  // ③ inner_shift:主角心理/信念是否变化(防"扁平主角")
  "inner_shift": {
    "dimension": "belief",   // enum: belief|goal|fear|value|relationship|resolve
    "from": "隐忍待时", "to": "决定主动出击",
    "cause": "得知妹妹被牵连"   // 变化的因,不能凭空
  },

  // ④ net_advance:这章净推进了什么主线(防"原地打转")
  "net_advance": {
    "main_line": "主角首次公开展示锋芒,进入家族权力视野",
    "irreversible": true,    // 是否产生不可逆的故事状态变化
    "advances_thread": "OUTLINE thread ref 或事件线"
  },

  "provenance": { "derived_from": ["..."], "source_version": 1 },
  "content_hash": "sha256:..."
}
```

### 13.3 关键设计决策(每个对齐项目纪律)

1. **escalation/inner_shift 是跨章 fold,不是可变状态(ADR-008)。**
   `escalation.from_level` = 上一章 mandate 的 `to_level`;`inner_shift.from` = 上一章
   的 `to`。是折叠,非读写可变字段——同 StoryState / character_runtime 的投影纪律。
   第 N 章 mandate 由 `long-arc-plan`(P10)+ 前 N-1 章 mandate + StoryState 折出。

2. **两个流水账探测器是确定性检查,advisory 告警(不 gate build)。**
   - `cost_of_delay: none` → "本章无时间压力,疑似温水章"
   - `escalation.kind: flat` 连续 ≥2 章 → "张力停滞"
   - `net_advance.irreversible: false` 连续 ≥3 章 → "原地打转"
   确定性可算,但按 ADR-003 只作 advisory(叙事质量判断,非构建正确性)。**这是把
   "防流水账"变成可度量约束的核心。**

3. **mandate 约束 objective,不替代。** 生成侧顺序变为
   `mandate(为什么/升到哪)→ objective(要什么)→ IR(怎么做)`。导演的
   `build_chapter_objective` 增 `mandate=` 入参:escalation/inner_shift 成为 objective
   的硬约束(cliffhanger/payoff 必须与 escalation.kind 一致)。**复用导演,不新建决策者。**

4. **prompt v7 = v6 + `narrative_mandate` 槽。** 沿用 v5→v6 的三处接线纪律(模板槽 +
   loop fold + binding allowlist);v6 逐字节冻结。正文 prompt 显式告诉模型"这章为什么
   必须现在发生、冲突升到哪、主角内心移动到哪"——直接攻击流水账。

5. **服务的质量维(准入约束)**:hook / conflict / pacing / serial_sustainability /
   character_growth。mandate 让这些维度在**生成前**被规划,而非事后评分。

### 13.4 落地拆解(每步独立可提交、可回归)

| 子步 | 交付 | 验收 |
|---|---|---|
| 9.1 | ✅ `narrative-mandate.schema.json` + `director/mandate.py`(project+validate+render) | schema 校验通过,带 gating/authority const |
| 9.2 | ✅ 跨章 fold:mandate(N) 折自 mandate(N-1)+ 大纲 beat(`first_30_chapters`) | 确定性;同输入同 hash;第1章降级(无前章) |
| 9.3 | ✅ 三个流水账探测器(温水章/张力停滞/原地打转,`mandate_check.py`) | advisory 告警,永不 gate;确定性可复现;顶格 level 强制 kind=flat 使停滞探测器仍触发 |
| 9.4 | ✅ **prompt v8**(非 v7,v7 已被 speech 占用)+ loop 接线(mandate→objective 约束);CLI `--mandate` | v6/v7 逐字节冻结;v8 正文体现 why-now/升级/心理移动 |
| 9.5 | ✅ dashboard 折 mandate → "张力弧健康度"(升级阶梯/温水章/不可逆推进 + 跨章停滞判定) | 只读折叠,空项目降级 |
| 9.6 | ✅ 真实 DeepSeek 12 章 v7-vs-v8 干净对比(¥0.675) | **章末钩子 warning 5→1(人工读证实真实改善)、AI 味 6→4、字数 CV 33.3%→25.1%;pacing 8→8 正交不变;温水章 10/12 忠实暴露大纲 beat 弱** |

**Phase 9 COMPLETE(2026-07-08)。** 唯一变量对比(无 speech profile → speech 两臂中立)证实 mandate 层可测地改善章末钩子(§14 发现3 的系统解)与 AI 味,收紧字数,且未回退其他维度。比 A.4 混合结果更决定性。**下一步的真实靶子来自 9.6 的诚实暴露：温水章 10/12 说明收益上限受大纲 beat 质量约束——richer beats 是 genesis 侧的增量方向。**

### 13.5 与原始诊断的精确对应

| 诊断原话 | mandate 字段 |
|---|---|
| 主角为什么现在必须这样做?为什么不能等一天? | `why_now.trigger` + `cost_of_delay` + `clock` |
| 冲突是不是升级? | `escalation.from_level→to_level` + `kind`(flat=预警) |
| 角色心理有没有变化? | `inner_shift.dimension/from/to/cause` |
| 这一章真正推动了什么? | `net_advance.main_line` + `irreversible` |
| 容易流水账 | 三个确定性探测器 advisory 告警 |

---

## 14. 真实基线实测与优先级修正(2026-07-06)

> 本节基于对仓库中**真实模型产出的正文**的直接评估,不是理论推断。数据来源:
> `novel-pilot/registry/derived/drafts/` 里三个模型对同一章(TASK-00001,第1章)的
> 真实产出:DeepSeek(serial 实产,3728字)、Claude(manual,1534字)、
> GPT(manual,1589字)。**方法论限制**:三者均为单章、无 mandate、无多章连载,
> 故本节只能诊断**单章正文质量**,不能诊断长篇崩坏(需真跑几十章,即 Phase 8 Genesis
> 的前提)。

### 14.1 实测发现(比理论更值钱的三条)

**发现 1 — 流水账的根因是「单章信息密度」,不只是跨章规划。**
DeepSeek 版 3728 字里,前 1/3 是「暮色如铁锈/寒风如刀/记不清逃亡多少天」这类**零信息
增量**的氛围句。Claude 用「针脚是自己缝的、靴底塞干草」两个细节就交代了「独自长途
逃亡」,DeepSeek 用三段抒情还没说清。→ §13 mandate 的 `information_gain` 反注水方向
正确,但真实数据显示**单章内信息密度问题比跨章规划更早暴露、更致命**。

**发现 2 — 三个模型的角色声音几乎无差异(实测全翻车)。**
三版的马伦都是「坚定、温柔、压低声音」,埃德里克都是「警惕、摸向腰间的剑」。**没有
一个模型让两个角色说话方式真正不同。** → 这不是「深化」问题,是**现在就翻车**的问题;
Character Speech Profile 的必要性被实测确认。

**发现 3 — 章末钩子只有 DeepSeek 有,且模板化(信鸽/猫头鹰警告)。**
Claude/GPT 收在情绪上,无追读钩子。→ 说明章末钩子现在**不是生产约束**,全凭模型自由
发挥;应进 objective 硬约束。

**发现 4 — AI 味是肉眼可见的真实问题,非理论风险。**
DeepSeek 版形容词堆砌、心理独白冗长,AI 味明显重于 Claude/GPT。→ Humanization Engine
是实测痛点,不是「以后再说」。

### 14.2 优先级修正:痛点在单章,不在跨章

§12.4 原把 Narrative Intelligence(跨章规划器)排第一。**真实正文修正这个顺序**:
读者在第 1–3 章就死于「注水 / 角色同声 / AI 味」这些**单章就暴露**的伤,根本活不到
第 42 章去体验「跨章冲突没升级」。故跨章规划器的收益要跑到几十章才显现,当前看不到。

| 痛点 | 原优先级 | 实测修正 | 理由 |
|---|---|---|---|
| Character Speech Profile | Phase 10 内 | **提到 P1 最前** | 三模型全翻车,最确定的痛点 |
| 信息密度检查器(反注水) | Phase 9 内(跨章) | **提前为单章检查** | 单章就能测,第1章即暴露 |
| Humanization Engine | Phase 14(P2) | **提前到 P1** | 真实输出 AI 味肉眼可见 |
| 章末钩子硬约束 | 隐含在 objective | **显式进 objective 约束** | 现在全凭自由发挥 |
| 跨章叙事规划器(mandate 全量) | Phase 9(P0) | **拆分**:单章探测器先行,跨章 fold(escalation ladder)推到有真实长跑后 | 跨章收益需几十章才显现 |
| 留存相对比较 | P1 | 不变 | 实测确认:可相对排序,不可绝对打分 |

### 14.3 修正后的近期落地序(取代 §12.4 的前几阶段)

1. **P0-a 单章质量三件套(实测最痛,先做)**:Character Speech Profile + 单章信息密度
   检查器 + Humanization Engine。三者都在单章生效、纯确定性/可 advisory、不需长书即可
   验证。
   - ✅ **Character Speech Profile**（§15，S.1–S.6 COMPLETE，含真实 DeepSeek A/B 验证）。
   - ✅ **单章信息密度检查器**（`runtime/execution/density.py`，2026-07-06）:确定性
     三指标（对白占比 / 比喻密度 / 开篇信息偏斜），复用 `ReviewReport`(evaluative,
     never gates)、骑 envelope、只读 body 不改 draft/state hash;是 `check_pacing`
     的孪生。serial loop 每章记录 `ChapterRun.density`。429 pytest + 22 fitness 全绿。
   - ✅ **Humanization Engine v1（检测器）**（`runtime/execution/humanization.py`，
     2026-07-06）:确定性三信号（连续同头排比 / 破折号插入语密度 / 句长变异系数），
     从真实 DeepSeek 正文提取模式;复用 `ReviewReport`(evaluative, never gates)、骑
     envelope、只读 body 不改 hash;pacing/density 的第三个孪生。serial loop 每章记录
     `ChapterRun.ai_taste`。检测器优先——矫正(接 revise_until 去 AI 味改写)与预防(进
     prompt 约束)两半留后续增量。439 pytest + 22 fitness 全绿。
   - **→ P0-a 单章质量三件套 COMPLETE**（Speech Profile + 信息密度 + AI 味检测）。
   - ✅ **检测→矫正闭环**（`runtime/execution/prose_hygiene.py`，2026-07-06）:density+
     ai_taste 的 warning 驱动定向改写、确定性重检、keep-best;薄适配复用 rewrite_once
     (非第二个改写引擎)、opt-in、never gates。CLI `serial run --hygiene`。真实 DeepSeek
     A/B 验证:排比 warning 1→0、字数保持。§14.5「系统约束让任何模型合格」的落地终局。
   - ✅ **章末钩子检测器**（`runtime/execution/hook_check.py`，2026-07-06）:§14 发现3 的
     检测半——确定性分析结尾段（疑问/悬置/转折/闭合四信号），可对照 objective 的
     `cliffhanger_type`（声明未兑现→警告）;pacing/density/humanization 的第四个孪生。
     serial 每章记录 `ChapterRun.end_hook`。461 pytest + 22 fitness 全绿。
2. **P0-b Minimal Genesis**:开出能跑长书的项目(长篇崩坏诊断的前提)。
3. **P1 Narrative Intelligence(拆分版)**:先 mandate 的单章探测器(cost_of_delay /
   information_gain / 章末钩子),跨章 escalation ladder 待真实长跑后。
4. 其余(Quality Engine 接真实 LLM、Reader 相对曲线、Author Persona)顺序不变。

### 14.3.1 Activation Sprint(A.1–A.5,2026-07-08 COMPLETE)——「栈已激活」里程碑

**诊断(来自 G.8 真实跑)**:12 章验收书跑在 prompt **v1.0**——最原始档。硬证据:
director / chapter-objective / chapter-ir / scene-plan / character-runtime 全部 **0 产物**。
即整个 Phase 4-7 栈(P1-P24 大半)"建完+单测过,但从未碰过真实的书"。这是项目第一
原理("无消费者的模块即桩")在**整栈**尺度上的暴露。故 Phase 9 之前**先激活,不重建**。

- ✅ **A.1 outline auto-supply**(commit f81135c):genesis 写 outline 到 registry,serial
  从不加载——`load_project_outline` + CLI 自动加载 + `--no-outline` 逃生门。
- ✅ **A.2 默认 prompt v1→v6**(commit 492770d):serial CLI `--prompt-version` 默认翻到
  6.0.0;`--speech` 升 v7(opt-in)。函数默认仍 1.0.0,全部测试显式传版→字节一致。
- ✅ **A.3 章长约束**(commit f00d4b5):dead 字段 `target_wordcount_per_chapter` 终于接
  进生成(run.py 追加长度指令到 style 变量,无新 prompt 版);新增 `length_check.py`
  第 4 个孪生探测器,ChapterRun.length 持久化。
- ✅ **A.4 before/after 真实对比**(2026-07-08):genesis-pilot 12 章**双跑**——v1.0.0
  `--no-outline`(激活 OFF,复刻 G.8 基线,¥0.230)对 v6.0.0 默认+outline+target3000
  (激活 ON,¥0.323,live_calls=12)。持久化的 chapter-run(含 4+1 探测器)聚合成
  `genesis-pilot/analysis/A4-comparison.md`。**关键读数**:

  | 指标 | v1(OFF) | v6(ON) | 结论 |
  |---|---|---|---|
  | chapter-ir/scene-plan/character-runtime/objective/director-brief | **0 / 0 / 0 / 0 / 0** | **12 / 12 / 12 / 12 / 12** | **栈首次进入真实生产路径=激活成功** |
  | pacing 读数(real/12) | 0(全 null) | 12 | 情绪曲线上线 |
  | 字数 CV | 35.7%(μ4209,2521–7191) | 29.2%(μ4920,3283–8666) | target 收紧了离散度 |
  | length 警告(ran/12) | 0(无 target 跳过) | **7** | target 生效但**弱约束,模型仍超篇幅**(均值 4920≠3000) |
  | ai_taste 警告 | 4 | 4 | v6 化**未改善** AI 味 |
  | pacing_peak 序列 | 全 null | **75/75/85 机械循环** | 确定性 scene-plan 模板,非真实逐章变化;P21 LLM 富化未见效 |

  **答 v2.1 之问("激活是否让小说更好?")**:*配线*层面完全成功(整栈 0→12,pacing
  null→real,CV 收紧);*质量*层面部分成功且诚实暴露三个真实短板——① 章长弱约束仍超,
  ② AI 味不因升版改善,③ 情绪峰值是模板循环非真实变化。这些是 Phase 9 及后续增量的
  真实靶子,而非凭空猜测。
- ✅ **A.5 记录**:本节即里程碑记录;Phase 9 触发条件更新为"A.1–A.4 完成后"(见 §13)。

### 14.4 诚实的方法论说明

本次**未新跑 DeepSeek**,而是评估仓库已有的真实产出。原因:demo/pilot 项目只有 1–2
个事件,新跑也只能出 1 章,信息量不增;现有三模型第 1 章已足够暴露单章质量短板。
**要诊断长篇崩坏(设定/人设/伏笔跨百万字漂移),需要一个有几十事件的真实项目 ——
这正是 Phase 8 Genesis 要解决的**,当前无长书可跑。这反过来印证排序:单章三件套现在
就能修且实测最痛;长篇诊断要等 Genesis。

---

### 14.5 模型问题 vs 系统问题(战略决策:要不要为质量全程换 Claude?)

对同一章三模型产出的逐项对照,把短板分成两类 —— 这直接决定"是否该为质量全程换
更强模型"这个战略决策:

| 短板 | DeepSeek | Claude | GPT | 归类 |
|---|---|---|---|---|
| 信息密度/注水 | 差(前1/3氛围句) | 好(针脚/靴底细节) | 好 | **模型能力差异** |
| AI味/文风 | 重(形容词堆砌) | 轻 | 轻 | **模型能力差异** |
| 角色声音区分 | 无 | **也无** | **也无** | **系统缺输入** |
| 章末钩子 | 有(模板化) | **无** | **无** | **系统缺约束** |

**结论一(换模型能解决的一半)**:信息密度、AI味,Claude/GPT 明显更好 —— 同 prompt、
同设定,Claude 用一半字数交代更多信息。DeepSeek 基础写作能力确实弱于 Claude。
**但成本现实**:百万字连载,Claude API 成本是 DeepSeek 的十几到几十倍。现实策略是
**混合**:关键章(黄金三章/卷级高潮/付费点)用 Claude,过渡章用 DeepSeek —— 需要
多模型调度(§12.5 的 10% 工程投入项)。

**结论二(换模型也解决不了的一半,更致命)**:角色声音同质化 + 章末钩子缺失,
**Claude 和 GPT 同样翻车**。给 Claude 再强的模型,它也不知道马伦(铁匠女儿)和埃德里克
(流亡贵族)该怎么说话不同 —— 因为 **Speech Profile 这个输入压根不存在**;它也不留
钩子,因为系统没把"章末必须留钩子"作为硬约束喂进去。

**战略裁决**:一个 AI 网文**生产系统**的价值,不在于用最强模型,而在于用**系统约束**
(Speech Profile / 钩子约束 / 信息密度检查)让**任何模型**都产出商业合格稿。否则就只是
套壳调 API,护城河为零。→ **不要为质量全程换 Claude**(治标不治本 + 成本爆炸);
**先做系统约束三件套**,让便宜的 DeepSeek 也能写出区分度和钩子,再用多模型调度把
Claude 留给关键章。这强化(而非推翻)§14.2 的优先级修正。

---

## 15. 详细设计:Character Speech Profile(§14 实测最优先项)

> 2026-07-06 追加。§14 实测:三个模型(DeepSeek/Claude/GPT)对同一章**全部**角色同声
> —— 换模型解决不了,因为系统从没告诉任何模型"这两人语言该怎么不同"。Speech Profile
> 是这个问题的直接解药,也是"换 Claude 也解决不了的那一半"的系统解。本节是 schema-first
> 详细设计,尚未落代码。设计前已核实:Character 事实 schema 无任何语言字段;
> character_runtime 是动机层投影(goal/pressure/fear/desire);二者与 Speech Profile 正交。

### 15.1 定位:表达层规格,与动机层正交,不重复

| 层 | 已有?回答什么 | 性质 |
|---|---|---|
| Character 事实 | ✅ 能力/外貌/归属(**无语言字段**) | fact(声明式) |
| character_runtime | ✅ goal/pressure/fear/desire(**为什么这么做**) | projection(fold) |
| **Speech Profile(新)** | ❌ **怎么说话:用词/句长/习惯/禁忌/思维** | **authored source(像 Novel Brain)** |

**关键架构判断**:Speech Profile 是**作者授权的静态输入**(像 Novel Brain /
market-position),**不是 fact,不是 projection**。理由:角色说话方式是作者设定的创作
意图,不从事件折叠而来,也不是能力/归属那种客观事实。故住 `sources/`,与 Novel Brain
同类。

### 15.2 核心契约:`character-speech-profile.schema.json`

```jsonc
{
  "kind": "character_speech_profile",
  "authority": "human",   // const,作者授权(ADR-009 同 Brain)
  "gating": false,        // const,advisory 永不 gate(ADR-003)
  "schema_version": "1.0",
  "profiles": [
    {
      "character_id": "CHR-00002",   // 指向 Character 事实
      "name": "马伦·霍尔特",
      "vocabulary": {                 // ① 词汇域
        "register": "colloquial",     // enum: crude|colloquial|neutral|formal|archaic
        "signature_words": ["废铁", "打铁", "该还的债"],
        "avoids": ["华丽辞藻", "书面成语"]
      },
      "sentence": {                   // ② 句式
        "length": "short",            // enum: terse|short|medium|long|winding
        "style": "直接、少修饰"
      },
      "verbal_habits": ["说话压低声音", "习惯用反问", "不叫敬称"],  // ③ 语言习惯
      "taboo": ["不会主动示弱", "不用贵族腔"],                     // ④ 禁忌(防串味)
      "thinking_pattern": "务实、先算代价、警惕陌生人",           // ⑤ 思维模式
      "emotion_default": "沉静克制"                              // ⑥ 情绪默认态
    }
  ]
}
```

字段全覆盖原始诉求:Vocabulary / Sentence Length / Emotion / Habit / Taboo /
Thinking Pattern。

### 15.3 关键设计决策

1. **住 `sources/character-speech-profiles.yaml`,是 authored source(非 fact/projection)。**
   镜像 `brain/loader.py`:absent→None,pristine 全注释→当 absent,CLI `speech check`
   风格不 false-fail 新项目。**决策(已定):先做纯人工授权版**(作者手写),独立可用不
   阻塞;等 P8 Genesis 接真实模型后,由 CharacterDesigner agent 自动生成候选再人工确认,
   是自然增量。

2. **接入走 prompt v7,不改 v6。** 最初想附加到 render_character_runtime,但那会改变 v6
   渲染输出、破坏 v6 冻结。故走 v7(§13 已规划):v7 = v6 + `speech_profiles` 变量槽。
   沿用 v5→v6 的三处接线纪律(模板槽 + loop fold + binding allowlist)。**v6 逐字节冻结;
   无 profile 时 v7 退化为 v6 行为。**

3. **静态,不参与 fold。** 角色说话方式不随章节变,故不 fold;仅在渲染时按出场 lead 的
   `character_id` 匹配注入。degradation:某角色无 profile → 该 lead 不注入语言块,其余照常。

4. **服务的质量维**:character_consistency(角色不串味)+ 间接提升 emotion / dialogue 真实感。

### 15.4 落地拆解(独立可提交、可回归)

| 子步 | 交付 | 验收 |
|---|---|---|
| S.1 | `character-speech-profile.schema.json`(Standard)+ sources 位置 | schema 校验通过,带 gating/authority const |
| S.2 | `runtime/speech/loader.py`(load/validate,镜像 brain)+ CLI `speech check` | absent→None;pristine→absent;不 false-fail |
| S.3 | prompt v7 = v6 + `speech_profiles` 槽 + render 函数 | v6 逐字节冻结;无 profile 时 v7 退化为 v6 |
| S.4 | serial loop 接线(按出场角色匹配 profile)+ binding allowlist | 有 profile 的角色语言块进 prompt;degradation 干净 |
| S.5 | fitness guard:`speech/` 不写 facts、不 import model | 只读 authored source |
| S.6 ✅ | 真实 DeepSeek 验证:同章有/无 Speech Profile,角色声音是否真区分 | **通过**(2026-07-06):novel-pilot 同章同模型 deepseek-chat,无画像时二人同声(复现 §14);有画像时声音明显区分——埃德里克「承蒙相救,在下——」/ 马伦「得了,少废话」,禁忌各自守住。发现:画像的语言会带动全文语言(中文画像→中文正文),需在画像/Brain 里锁定目标语言。 |

### 15.5 为什么这是实测最优先(回扣基线)

- §14 实测:三模型**全部**角色同声 → 换模型解决不了,只有系统输入能解决。
- Speech Profile 是"换 Claude 也解决不了的那一半"的直接解药。
- 纯确定性(loader + render),S.1–S.5 **不耗 API**;仅 S.6 验证需真实模型。
- 架构最干净:authored source(Brain 先例)、v7(已规划)、不碰 fact/projection 边界。

---

## 附:与项目既有规范文件的关系

- 本文是**面向北极星的生产推进书**(战略路线)。
- `docs/AI_DEVELOPMENT_PROMPT.md` 是**逐任务的规范提示词**(战术执行)。
- `ROADMAP.md` 是**已落地里程碑 + 有意延期的权威记录**(事实底账)。

三者叠用:用 ROADMAP 确认现状 → 用本文选下一阶段 → 用 AI_DEVELOPMENT_PROMPT 执行
具体子任务。本文的快照事实(阶段/测试数/模块)以 ROADMAP 与代码为准,冲突时仓库赢。
