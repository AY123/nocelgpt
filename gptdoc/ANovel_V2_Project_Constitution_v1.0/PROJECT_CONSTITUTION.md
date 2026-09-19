# ANovel V2 Project Constitution & AI Engineering Charter

> **中文名**：ANovel V2 项目宪章与 AI 工程总纲  
> **Document ID**：GOV-0001  
> **Version**：1.0.0  
> **Status**：BASELINE / NORMATIVE  
> **Authority**：PROJECT-CONSTITUTION  
> **Applies To**：ANovel V2 全部产品、架构、代码、Schema、Prompt、Workflow、GenrePack、数据、测试、实验、AI Agent/Coding Agent  
> **Primary Format**：Markdown SSOT  
> **Machine Companion**：`project-constitution.yaml`  
> **Effective Date**：2026-09  
> **Change Rule**：重大变更必须通过 ADR + 宪章版本升级；任何 AI Agent 不得自行修改本文件的规范语义。

---

## 0. 文档目的

本文件是 ANovel V2 的最高级工程与产品规范。它不规定某个类、某张表或某个 Prompt 的实现细节；它规定所有实现不能突破的边界。

它回答十个根问题：

1. ANovel V2 最终要成为怎样的系统；
2. ANovel V2 明确不是什么；
3. 所有架构与代码必须遵守哪些基本原则；
4. 哪些信息拥有怎样的 Authority；
5. 谁可以改变 Canon，何时可以改变；
6. AI 在项目中可以做什么、不能自行做什么；
7. 哪些 V1 经验必须继承、哪些失败不得重演；
8. 新模块、Schema、Agent、Workflow、Genre 的准入标准；
9. 30/100/300 章与百万字目标如何验收；
10. 后续所有专项规范、ADR、实现计划共同服从什么上位规则。

### 0.1 为什么 V2 第一份正式资料必须是“宪章”

ANovel V1 已经证明：AI 可以极快地生成 Agent、Schema、Reviewer、Prompt、Derived Artifact、报告和代码，但**功能增长不会自动形成统一系统**。

V1 后期已经积累了很多正确工程经验——例如“无消费者即 stub”、State as Projection、唯一事实写入口、real-provider validation、replay/recovery、人类授权边界——但这些经验是逐步补出来的，且一度与早期的 Genre 偏置、多判断中心、fail-open、弱合同约束并存。

V2 必须把“后来才学会的纪律”提升为“第一天就不能违背的规则”。


# 1. Mission：项目使命

ANovel V2 的正式使命：

> **构建一个以 Genre Intelligence、Canonical Narrative State、Hierarchical Planning、Narrative Contract、Durable Workflow、Quality Calibration、Reference/Corpus Intelligence 和 Reader Signal 为核心的 AI 原生商业长篇小说生产操作系统，使 AI 能在受控创作自由度下，持续、稳定、可恢复、可验证地生产几十万至数百万字的高质量原创商业网文。**

最终系统必须支持四种开书方式：

- **Idea-Driven Genesis**：题材 + 核心创意 + 目标读者；
- **Reference-Guided Genesis**：一本/多本参考作品，抽象机制后原创；
- **Hybrid Genesis**：创意 + 正向/反向参考；
- **Corpus/Market-Driven Genesis**：版本化语料与市场证据驱动。

四种入口 **MUST** 汇聚为统一 `GenesisSpec`，之后进入同一个生产内核。

```text
Intent / Reference / Corpus / Market Evidence
                    ↓
              Genesis Compiler
                    ↓
               GenesisSpec
                    ↓
           Genre Constitution
                    ↓
               Story Bible
                    ↓
        Canonical Narrative State
                    ↓
          Hierarchical Planning
                    ↓
     Arc / Chapter / Scene Contract
                    ↓
            Context Compiler
                    ↓
       Generation / Review / Repair
                    ↓
         Validation & Commit Permit
                    ↓
              Canon Commit
                    ↓
         Canonical Narrative State N+1
                    ↓
        Human / Reader / Market Feedback
```


# 2. Non-Goals：明确不做什么

ANovel V2 **不是**：

1. 单纯 Prompt 包装器；
2. 聊天式写作助手；
3. “一句话直接吐几十万字”的不可控生成器；
4. 用大量 Agent 相互调用替代架构设计的系统；
5. 以 GPT/Claude/DeepSeek 等模型名称为核心抽象的系统；
6. 参考小说改写器、洗稿器、情节复刻工具；
7. 以单一 AI Judge 分数作为绝对真值的系统；
8. 把“有 Schema”视为“有能力”的系统；
9. 把当年市场热点硬编码进永久领域模型的系统；
10. 为了“全自动”取消必要人类授权边界的系统；
11. 只面向单章文笔、不关心百章和百万字连续性的系统；
12. 用 LOC、Agent 数、Schema 数、测试数代替真实小说结果的系统。


# 3. Final Success Criteria：最终实现目标

## 3.1 30 章
- 0 个重大 Genre Hard Violation；
- 0 个主要角色身份漂移；
- 0 个重大时间线冲突；
- 0 个不可解释 Canon 状态分叉；
- Resume/Retry 不重复 Canon Commit；
- 每章拥有完整 Provenance。

## 3.2 100 章
- 核心人物、关系、知识边界、世界规则、Promise 稳定；
- 关键伏笔/承诺可追踪；
- 程序中断后可恢复；
- 前后 50 章质量趋势无系统性崩坏；
- 章节功能没有大规模重复。

## 3.3 300+ 章
- Narrative Engine 仍能扩展；
- 世界、人物、成长和冲突持续发生真实状态变化；
- 中后期不出现长期“原地打转”；
- 长弧与卷级承诺仍然可追踪和兑现。

## 3.4 百万字级
- 仍然是“同一本小说”；
- Canon、Genre、主线、人物和世界规则保持可解释连续性；
- 人工编辑与真实读者均有正向证据；
- AI 内部指标与真实市场信号之间存在可报告的校准关系。


# 4. Normative Language

本项目正式使用以下规范词：

- **MUST**：必须满足，否则是架构违规；
- **MUST NOT**：明确禁止；
- **SHOULD**：原则上应满足，偏离必须记录理由；
- **SHOULD NOT**：原则上不应做，偏离必须记录理由；
- **MAY**：可选。

所有 `P-*`、`INV-*`、`PROHIBIT-*` 条款均为可被 AI/CI 直接引用的规范条款。


# 5. Core Principles

## P-001 Canon over Model Memory
模型上下文、摘要、检索结果、Agent Memory 均不是小说事实源。Canonical Narrative State 才是项目事实真值。

## P-002 Genre is a Foundational Domain
Genre 不是字符串标签，也不是 Prompt 参数。GenrePack 必须影响 Reality Model、World Law、Allowed/Forbidden Elements、Progression、Canon Extension、Narrative Engine、Reader Promise 与 Quality Rubric。

## P-003 Draft is NOT Canon
Draft、Candidate、Rewrite、Reviewer 建议、Reference Evidence、AI 推断都不是 Canon。

## P-004 Canon Changes only through Canon Commit
所有 Canon 状态变化必须通过唯一 Canon Commit Boundary。任何旁路写 Canon 都是 P0 级架构违规。

## P-005 Production is Fail-Closed
Production Mode 下：缺 GenrePack、缺必要 Contract、缺有效父 Snapshot、Hard Invariant 失败、关键 Timeline Conflict、Commit Permit 缺失时必须 BLOCK。

## P-006 State owns truth; Worker owns computation
长期真值属于 Canon/State。Planner、Writer、Reviewer、Extractor、Repairer、Judge 是可替换 Worker，不得成为第二真值源。

## P-007 Agents are Workers, not Architecture
不能用“一个功能一个 Agent”代替领域建模。新 Worker 必须有 Domain、Input Contract、Output Contract、Consumer、Failure Semantics 和 Authority。

## P-008 Multiple Genesis Inputs, One Production Kernel
Idea/Reference/Hybrid/Corpus 只能在 Genesis 前分叉；后续必须汇聚到统一内核。

## P-009 Market Trend is not Genre Truth
`MarketTrendSnapshot` 是时间敏感证据；`GenrePack` 是相对稳定领域规则。市场变化不得静默修改 Genre 语义。

## P-010 AI Judge is not Ground Truth
未经真人/真实市场校准的 Judge 只能诊断、比较、排序，不能被表述成商业真值。

## P-011 Reference Evidence is not Project Canon
Reference/Corpus 只能拥有 Evidence Authority，不得直接写 Project Canon。

## P-012 Persistent Artifacts require Provenance
任何会影响长期结果的 Artifact 必须可追溯其 source、version、producer、parent hash、model/prompt/policy 等信息。

## P-013 No Consumer = Stub
继承 V1 最有价值的工程纪律：没有真实消费者的模块/Schema/Report 不得标记“能力完成”。

## P-014 Long-form Correctness before Feature Breadth
30 章认证前，不以新增 Agent、Persona、复杂 UI、海量 Genre、大规模 Corpus 为主。

## P-015 Real-model Validation is mandatory for Model Seams
真实模型才能暴露 provider、retry、replay、prompt communication、entity resolution 等问题。重大模型路径必须有 real-provider contract test。

## P-016 Context must be Compiled
Writer 不得随意读取整个项目；上下文必须由 Context Compiler 从 Genre、Canon、Contract、Knowledge、Relevant State、Approved Evidence 编译。

## P-017 Plan is Intention; Canon is History
未来计划可重算；已 Commit 的 Canon 不得静默修改。Retcon 必须显式。

## P-018 Repair before Rewrite
自动修订优先 Diagnosis → Patch → Regression，而不是发现一个问题就整章重写。

## P-019 Deterministic Facts outrank Semantic Preference
姓名、时间、版本、前置能力、Genre 禁止项、ID、父提交、Schema enum 等能确定性验证的内容，不交给 LLM 最终裁决。

## P-020 Reader/Market Signal eventually calibrates AI Metrics
最终优化目标必须从内部 AI 分数升级到人工盲评与真实点击、留存、追读、首订、追订、付费、弃书点等市场信号。


# 6. V1 Lessons：旧项目经验的制度化

## LESSON-V1-001 Genre 弱约束会造成类型污染
V1 `CLAUDE.md` 已明确承认早期设计隐含玄幻/奇幻范式，都市、历史、科幻等受到错误通用模型影响。

**V2 决策**：Genre 上升为基础 Domain；Hard Rule 可执行；Fusion 必须显式。

## LESSON-V1-002 Power System 不是通用 Progression
境界/修为只适用于部分题材。

**V2 决策**：统一 `ProgressionModel` 抽象，再由 Urban/Fantasy/Sci-fi/Historical 等扩展。

## LESSON-V1-003 关键词补丁不是 Genre Architecture
V1 后期通过 positive/negative keywords、题材专用 Prompt 补救，适合 Detection，不适合作为 Truth。

**V2 决策**：关键词 MAY 用于识别，MUST NOT 成为唯一 Genre 权威。

## LESSON-V1-004 Schema 存在不代表能力存在
V1 ROADMAP 已形成“consumer exists 才算能力”的正确纪律。

**V2 决策**：所有 Artifact 必须有 producer、consumer、lifecycle、authority、version policy。

## LESSON-V1-005 唯一事实写入口值得继承
V1 Mint、Candidate、Recompute、ID Ledger 的正确方向是：准备与写入分离、validate-then-write、显式 authority。

**V2 改良**：升级为 NarrativeDelta → ChangeSet → Commit Permit → Canon Commit。

## LESSON-V1-006 State as Projection 是正确方向
V1 `StoryState@N = fold(facts, events[1..N])` 是值得保留的核心经验。

**V2 改良**：Canon Event Log + Snapshot；Projection 可重建，不得成为第二真值。

## LESSON-V1-007 多 verdict 会制造多真值中心
历史 Artifact 曾同时存在 pass / rollback / revise / invalidated 等不同结论。

**V2 决策**：唯一 Production State Machine；其他评分只是 Evidence。

## LESSON-V1-008 Fail-open 会让 Contract 失效
缺 Contract 就跳过、找不到实体返回 None、continuity error 只 warning 等路径会使硬约束失真。

**V2 决策**：Production 默认 Fail-Closed；unsafe bypass 必须显式且不可直接发布。

## LESSON-V1-009 Real-provider Test 不可替代
V1 ROADMAP 已记录真实模型才发现的典型问题：
- live provider 未真正进入 serial generation；
- 5xx 错误被误判 permanent；
- timeout 被错误纳入 replay semantic key；
- extractor 看不到实体名字导致 phantom `new`；
- lifecycle enum 被模型误解为叙事情境。

**V2 决策**：Provider/Prompt/Replay/Entity Resolution 全部必须有最小真实模型验证。

## LESSON-V1-010 AI 评价必须分证据等级
ReaderSim、Commercial Judge、Quality Judge 在未校准前只能是 diagnostic/comparison。

## LESSON-V1-011 功能增长不能替代作品结果
模块数、Agent 数、报告数不能证明小说质量。

## LESSON-V1-012 Corpus/Reference 应影响规划，不应污染正文
Reference 通过抽象 EvidencePack 进入 Genesis/Planning，Writer 默认不读取连续参考原文。


# 7. External Design Lessons

以下只冻结“可迁移原则”，不把任何外部项目当成 V2 唯一模板。

- **EXT-001 Canon Commit Boundary**：Accepted/Committed 内容才推进长期状态。
- **EXT-002 Hierarchical Planning**：Series → Volume → Arc → Chapter → Scene，越远越抽象。
- **EXT-003 Transition Validation**：检查 State Before → Required Transition → Actual Transition。
- **EXT-004 Temporal/Graph Representation**：时间、关系、知识边界、因果不能全部依赖自然语言摘要。
- **EXT-005 Context Pack/Codex**：角色、地点、Lore、大纲、近期状态应结构化选择进入上下文。
- **EXT-006 Durable Workflow**：checkpoint、idempotency、retry、resume、side-effect boundary 是长篇生产必需品。
- **EXT-007 Policy-as-Code**：Genre Hard Rule、Commit Authorization、Security Rule 应逐步机器可执行。
- **EXT-008 Provenance First**：无法复盘的生成结果不应成为长期生产系统正式资产。


# 8. Truth Hierarchy

发生冲突时默认按以下顺序裁决：

```text
T0 Project Constitution
↓
T1 Approved ADR / Normative Architecture Specification
↓
T2 Genre Constitution / Domain Contract / Machine Policy
↓
T3 Canonical Narrative State / Canon Event Log
↓
T4 Approved Plan / Arc / Chapter / Scene Contract
↓
T5 External Evidence (Reference / Corpus / Market)
↓
T6 Generated Artifact / Draft / Candidate
↓
T7 AI Analysis / Judge / Recommendation
```

关键规则：

- 下级不得静默覆盖上级；
- Plan 与 Canon 冲突：Canon 优先，Plan 重规划；
- Reference 与 Canon 冲突：Canon 优先；
- Judge 与 deterministic invariant 冲突：Invariant 优先；
- Market 与 Genre Constitution 冲突：不得静默改变 Genre。


# 9. Authority Model

推荐 Authority 枚举：

| Authority | 含义 | 可直接改变 Canon |
|---|---|---:|
| constitution | 最高项目规则 | 否 |
| architecture | 已批准架构规则 | 否 |
| genre | Genre 规则 | 否 |
| canon | 已提交事实 | 已是事实 |
| contract | 当前生产约束 | 否 |
| plan | 未来意图 | 否 |
| human_approval | 人类授权动作 | 可触发 |
| reference | 参考证据 | 否 |
| corpus | 聚合语料证据 | 否 |
| market | 市场证据 | 否 |
| model | 模型输出 | 否 |
| diagnostic | 评分/分析 | 否 |
| draft | 候选文本 | 否 |

**原则：有信息 ≠ 有权限。**


# 10. Core Domain Registry

初始顶级领域：

1. `governance`
2. `genre_intelligence`
3. `genesis`
4. `reference_corpus_intelligence`
5. `narrative_domain`
6. `canon`
7. `planning`
8. `contracts`
9. `context`
10. `intelligence_workers`
11. `production_workflow`
12. `quality`
13. `repair`
14. `provenance_observability`
15. `publishing`
16. `reader_market_learning`

新增顶级 Domain **MUST** 通过 ADR。


# 11. Core Invariants

- **INV-001**：正式 Production MUST 绑定版本化 GenrePack。
- **INV-002**：Genre Hard Violation MUST 阻止 Canon Commit。
- **INV-003**：Canon Commit MUST 引用有效 parent snapshot/head。
- **INV-004**：Canon 只能通过唯一 Commit Boundary 写入。
- **INV-005**：被评价/验证正文的 hash MUST 对应最终被接受正文。
- **INV-006**：Retry/Resume MUST NOT 重复不可逆 side effect。
- **INV-007**：ReferenceEvidencePack MUST NOT 直接写 Canon。
- **INV-008**：Model MUST NOT 同时充当 proposal + approver + irreversible authority。
- **INV-009**：Canon SHOULD 可由 Event Log + reducer 重建。
- **INV-010**：Production Run MUST 有 RunFingerprint。
- **INV-011**：Market Snapshot MUST 带 platform/channel/time/source/confidence。
- **INV-012**：AI Evaluation MUST 标注 Evidence Level。
- **INV-013**：Persisted Artifact MUST 有生命周期。
- **INV-014**：Production-ready GenrePack MUST 有跨类型污染负向测试。
- **INV-015**：unsafe bypass 输出 MUST 标记 non-production，不得直接发布。


# 12. Architecture Prohibitions

- **PROHIBIT-001**：禁止 provider-specific Domain（如 `GPTStoryPlanner` 作为领域类型）。
- **PROHIBIT-002**：禁止第二 Canon Store。
- **PROHIBIT-003**：禁止 Draft/Writer/Reviewer 直接写 Canon。
- **PROHIBIT-004**：禁止关键 Hard Constraint 只存在于 Prompt。
- **PROHIBIT-005**：禁止“一个功能一个 Agent”。
- **PROHIBIT-006**：禁止无 consumer 的 Schema 标记 Done。
- **PROHIBIT-007**：禁止把 2026 热点硬编码为永久 Domain Rule。
- **PROHIBIT-008**：禁止连续参考小说原文直接进入正式 Writer Context。
- **PROHIBIT-009**：禁止单一 AI Judge 拥有 Commit Authority。
- **PROHIBIT-010**：禁止 Silent Retcon。
- **PROHIBIT-011**：禁止 Hidden Mutable Agent Memory 成为真值。
- **PROHIBIT-012**：禁止未版本化 Prompt/Schema/Policy 进入 Production。
- **PROHIBIT-013**：禁止同一能力长期存在两套 Scheduler/Workflow/State Machine。
- **PROHIBIT-014**：禁止用 LOC/Agent/Schema/Test 数量冒充产品成功。


# 13. Production State Machine

建议基础状态：

```text
PLANNED
→ CONTEXT_READY
→ GENERATED
→ VALIDATING
→ NEEDS_REPAIR | BLOCKED | VALIDATED
→ APPROVAL_PENDING
→ APPROVED
→ COMMITTING
→ COMMITTED
→ PUBLISH_READY
→ PUBLISHED
```

旁路：

```text
INVALIDATED
SUPERSEDED
ABORTED
```

必须牢记：

- `Judge score high` ≠ `APPROVED`
- `GENERATED` ≠ `COMMITTED`
- `COMMITTED` ≠ `PUBLISHED`
- `PUBLISH_READY` 是资格，不是自动外部动作


# 14. Canon Transaction Model

```text
BEGIN NARRATIVE TRANSACTION

Load Canon Snapshot N
Load Genre / Story / Arc / Chapter / Scene Contracts
Compile Context
Generate Candidate
Extract Proposed NarrativeDelta
Validate:
  - Genre
  - Canon
  - Timeline
  - Character Knowledge
  - Required Transition
  - Forbidden Transition
Repair if allowed
Revalidate
Obtain Commit Permit
Append Canon Event(s)
Build Snapshot N+1

COMMIT
```

任何阶段失败：

```text
ROLLBACK CANDIDATE
CANON UNCHANGED
```


# 15. AI Engineering Charter

## 15.1 AI MAY
AI 可以分析、设计、生成代码、生成测试、写 ADR Draft、重构、执行评审、分析实验、编写迁移和文档。

## 15.2 AI MUST
重大任务开始前：

1. 读取 `PROJECT_CONSTITUTION.md`；
2. 读取任务相关 Normative Specs；
3. 检查当前代码；
4. 明确受影响 Domain；
5. 明确受影响 Principles / Invariants；
6. 明确是否触及 Canon / Human Authority；
7. 给出实现计划；
8. 实现；
9. 运行测试；
10. 运行 Architecture Fitness；
11. 更新规范/ADR；
12. 报告剩余风险。

## 15.3 AI MUST NOT autonomously
AI 不得自行：

- 修改 Constitution 语义；
- 删除 Hard Invariant；
- 新增顶级 Domain；
- 建第二 Canon；
- 绕过 Commit；
- 把 diagnostic 升级成 truth；
- 把热门题材写死进核心；
- 复制第二套 State/Workflow；
- 删除失败测试换 CI 通过；
- 把 unsafe 输出升级 Production；
- 将参考原文大段注入 Writer。


# 16. Documentation Governance

## 16.1 权威格式
- Normative Docs：**Markdown**
- Machine Contracts：**YAML / JSON / JSON Schema / OpenAPI**
- Human Export：**DOCX / PDF**

DOCX/PDF 是导出物，不是权威源。

## 16.2 推荐结构

```text
docs/
├── 00-governance/
│   ├── PROJECT_CONSTITUTION.md
│   ├── DOCUMENTATION_STANDARD.md
│   ├── GLOSSARY.md
│   └── ADR_INDEX.md
├── 01-product/
├── 02-research/
├── 03-architecture/
├── 04-genre/
├── 05-genesis/
├── 06-domain/
├── 07-production/
├── 08-engineering/
└── adr/

specs/
├── constitution/
├── genres/
├── schemas/
├── workflows/
├── quality/
└── model-policies/
```

每份 Normative 文档 SHOULD 包含：
`Document ID / Version / Status / Authority / Depends-On / Supersedes / Updated / Normative or Informative`。


# 17. ADR Governance

以下变化 MUST 建 ADR：

- 新顶级 Domain；
- Authority 变化；
- Canon Write Path 变化；
- Production State Machine 变化；
- Genre Hard Rule 语义变化；
- 新长期存储；
- 新 Scheduler/Orchestrator；
- Artifact 生命周期变化；
- AI 权限提升；
- 人类不可逆授权边界改变；
- Constitution 原则改变。

初始 ADR 建议：

1. ADR-0001 Modular Monolith First
2. ADR-0002 Genre Intelligence is Foundational
3. ADR-0003 Draft is not Canon
4. ADR-0004 Canon Commit is the Only Write Boundary
5. ADR-0005 Canon Event Log + Snapshot
6. ADR-0006 Multi-source Genesis, Single Production Kernel
7. ADR-0007 Provider-independent Model Gateway
8. ADR-0008 Context Compiler Boundary
9. ADR-0009 Fail-Closed Production
10. ADR-0010 Durable Workflow & Idempotency
11. ADR-0011 Evidence Level & Judge Authority
12. ADR-0012 Reference Evidence Firewall
13. ADR-0013 Patch-first Repair
14. ADR-0014 Human Authority for Irreversible External Actions
15. ADR-0015 Provenance & Run Fingerprint
16. ADR-0016 MarketTrendSnapshot separated from GenrePack
17. ADR-0017 Core Canon + Genre Extension
18. ADR-0018 Architecture Fitness Tests
19. ADR-0019 Real-provider Contract Tests
20. ADR-0020 Markdown SSOT + Machine-readable Contracts


# 18. Testing Philosophy

V2 测试分五层：

## T0 Unit
Reducer、Parser、Validator 等纯逻辑。

## T1 Contract
Schema、Protocol、Version Compatibility、Artifact。

## T2 Architecture Fitness
例如：
- Domain 不 import 具体 provider；
- Writer 不 import Canon write API；
- Reference 模块不 import Canon Commit；
- 只有 Commit Service 可 append Canon Event；
- 禁止第二 State Store；
- Genre Hard Rule 必须存在机器表达。

## T3 Real-model Contract Test
验证 provider、prompt、replay、retry、structured output、entity resolution。

## T4 Production Certification
10/30/100/300 章真实生产。


# 19. Evidence Model

| Level | Evidence | 用途 |
|---|---|---|
| E0 | Deterministic | Hard Gate |
| E1 | Structured Extraction | Candidate / Diagnosis |
| E2 | LLM / Multi-model Evaluation | Ranking / Diagnostic |
| E3 | Human Gold / Blind Review | Calibration / Decision Support |
| E4 | Real Reader / Market | Product & Commercial Truth |

**Evidence 不得向上伪装。**


# 20. Human Authority Boundary

以下动作默认需要 Human Authority，除非未来 ADR 明确改变：

- Formal Retcon；
- 外部发布；
- 平台上架；
- Major Genre Change；
- Story Constitution Change；
- 高风险 Canon Conflict Resolution；
- Copyright/Reference Boundary Exception；
- 从 diagnostic signal 自动学习并修改 Production Policy。

内部 Candidate Selection 和受控 Repair MAY 自动化，但必须受 Genre/Canon/Contract Gate 约束。


# 21. Security & Secret Governance

V2 Day 1 必须建立：

- secret scanning；
- `.env` / secret manager；
- 禁止 API Key 进入 docs/archive/test fixture；
- Git history secret scan；
- dependency lock；
- audit log；
- least privilege；
- external-content provenance。

真实 Secret 进入 Git 视为 **P0 Security Incident**，不是普通文档错误。


# 22. Copyright / Originality Governance

Reference-Guided Creation 的原则：

> **Mechanism Transfer, not Content Transfer**

系统可以学习：
- Narrative Function；
- Progression；
- Payoff；
- Pacing；
- Character Dynamics；
- Long Arc；
- Reader Promise。

系统必须防止：
- 连续原文复制；
- 标志性情节序列复刻；
- 角色一一映射；
- 高相似世界组合；
- 高相似关系图；
- 识别性强表达。

后续 Originality Firewall SHOULD 覆盖 lexical / semantic / event sequence / character function / relationship graph / structural similarity。


# 23. Versioning & Run Fingerprint

至少独立版本化：

- constitution_version
- architecture_version
- genre_pack_version
- schema_version
- workflow_version
- prompt_version
- context_policy_version
- model_policy_version
- quality_policy_version
- reference_policy_version
- market_snapshot_version

Production Run SHOULD 形成稳定 Fingerprint：

```text
sha256(
  constitution_version
  + code_commit
  + architecture_version
  + genre_pack_hash
  + schema_set_hash
  + canon_parent_hash
  + contract_hash
  + context_policy_hash
  + prompt_hash
  + model_policy_hash
  + sampling_policy
  + workflow_hash
  + quality_policy_hash
)
```

其目标不是强求随机模型字节级复现，而是准确知道“结果在什么条件下产生”。


# 24. Definition of Done Hierarchy

## Code DoD
测试、lint/type、无架构违规、错误语义明确、文档同步、无 secret、无 hidden truth state。

## Module DoD
producer/consumer、contract、lifecycle、authority、observability、error/retry、tests 完整。

## Domain DoD
边界清晰、依赖方向固定、无 duplicate truth、API 和 invariant 明确。

## Genre DoD
完整 GenrePack、Hard/Soft Rule、Canon Extension、Quality Rubric、负向污染测试、30 章认证。

## Production DoD
fail-closed、resumable、idempotent、traceable、无 duplicate commit、成本可见。

## Product DoD
以真实小说和读者结果衡量，不以工程数量衡量。


# 25. Milestone Gates

- **M0 Constitution**：本宪章批准；
- **M1 Narrative Kernel**：Genre + Canon + Contract + Transaction；
- **M2 Single Chapter**：一章事务闭环正确；
- **M3 Dual Genre**：Urban/Fantasy 同内核隔离；
- **M4 10 Chapters**：连续状态稳定；
- **M5 30-Chapter Certification**：第一生产门槛；
- **M6 Human Calibration**：Gold Set + Blind Review；
- **M7 100 Chapters**：Durable Long Run；
- **M8 Multi-source Genesis**：Idea/Reference/Hybrid/Corpus；
- **M9 Real Reader Signal**：真实平台闭环；
- **M10 300+ / Million-word**：长期商业生产验证。

M3 之前默认冻结：
- 复杂 Reader Simulator；
- 多平台自动发布；
- 30+ Genre；
- 大规模 UI；
- 大规模 Corpus；
- 大量 Reviewer Persona；
- 自动 Retcon；
- “一键百万字”承诺。

第一阶段只证明：
1. Genre 不串；
2. Canon 不乱；
3. Draft 不污染事实；
4. Transaction 正确；
5. Retry 不重复 Commit；
6. Real Model 可通过统一 Worker Seam。


# 26. Change Management

版本变更：

- **PATCH**：措辞、链接、非语义澄清；
- **MINOR**：新增不改变既有权威关系的原则；
- **MAJOR**：Authority、Canon、Human Boundary、Hard Invariant、Fail-Closed、Reference→Canon、Judge Authority 等根规则改变。

MAJOR 修改 MUST 有 ADR 与迁移说明。


# 27. AI Task Preamble Standard

未来给 AI Coding Agent 的重大任务建议统一附带：

```text
You are implementing ANovel V2.

Before editing:
1. Read docs/00-governance/PROJECT_CONSTITUTION.md.
2. Read task-relevant normative specs.
3. Identify affected Principles, Invariants, Authorities and ADRs.
4. Inspect current implementation before proposing changes.
5. Do not create a new top-level domain, canon store, workflow engine or authority boundary without an accepted ADR.
6. Production paths are fail-closed.
7. Draft/Reference/AI evaluation cannot write Canon directly.
8. Every persistent artifact needs a producer, consumer, lifecycle, authority and provenance.
9. Run tests and architecture fitness checks before completion.
10. Report conflicts with the Constitution instead of silently violating them.
```


# 28. Glossary

- **Canon**：正式接受并提交的小说事实与事件历史。
- **Canon Snapshot**：某一 Canon Head 下可重建的当前叙事状态。
- **NarrativeDelta**：候选正文声称发生的状态变化。
- **ChangeSet**：准备提交到 Canon 的结构化变化。
- **Commit Permit**：证明 ChangeSet 已满足必要验证与授权的凭据。
- **GenrePack**：将题材转成机器规则、扩展、机制和评价标准的版本化领域包。
- **Genre Constitution**：GenrePack 最高优先级的允许/禁止/世界规则。
- **GenesisSpec**：多入口开书归一后的正式创生输入。
- **ReferenceEvidencePack**：从参考作品抽象得到的可迁移证据，不是 Canon。
- **MarketTrendSnapshot**：特定平台、频道、时间段的市场证据快照。
- **Context Artifact**：Context Compiler 为某次模型调用生成的版本化上下文。
- **Worker**：可替换的规划/生成/抽取/评价/修复执行者，不拥有长期真值。
- **ProductionState**：章节/Artifact 在生产生命周期中的唯一权威状态。
- **Evidence Level**：描述证据距离真实真值的等级。


# 29. Source & Rationale Notes

本宪章吸收的内部证据包括：

- 当前 AINovel `ROADMAP.md` 中已验证有效的：
  - no consumer = stub；
  - state as projection；
  - schema-first；
  - unique fact writer / mint boundary；
  - replay/recovery；
  - derived recompute；
  - real-provider validation；
  - human authority；
  - reader-signal comparison-only。
- 当前 `CLAUDE.md` 对 V1 题材架构失误的明确诊断：
  - 隐含玄幻/奇幻偏向；
  - Genre 隔离不足；
  - power_system 错误通用化；
  - 都市等类型支持不足；
  - 跨题材测试不足。
- 前期 V1 深度审计发现：
  - 人物/时间/类型漂移；
  - hard constraint fail-open；
  - Contract 非强制；
  - placeholder provenance；
  - 多 verdict 冲突；
  - CI/repro/security 风险。
- 外部长篇 AI 项目与研究中值得抽象的设计：
  - Accepted Chapter → Canon Update；
  - Hierarchical Planning；
  - State Transition Validation；
  - Temporal/Graph Memory；
  - Context Pack；
  - Durable Workflow；
  - Long-form Consistency Benchmark。

具体外部项目逐项证据、不应借鉴项与引用来源，在后续 `REFERENCE_ARCHITECTURE_STUDY.md` 单独维护。


# 30. Final Constitutional Test

以后任何新功能都必须回答：

> **它是否让系统更稳定地生产一部长篇、类型正确、事实一致、人物可信、剧情持续推进、可恢复、可验证，并最终让真实读者愿意继续阅读和付费的原创商业小说？**

如果不能证明：

> **默认不进入当前优先级。**

---

# 31. Baseline Declaration

自 v1.0.0 被采纳后：

1. 本文件应成为 V2 新仓库第一批文件；
2. 所有 Normative Spec 必须声明对本宪章的依赖；
3. 重大冲突以本宪章为上位裁决；
4. AI Agent 不得把自身推断提升为更高 Authority；
5. V1 代码/Schema/Prompt/模块只能作为迁移候选，不自动继承权威；
6. V2 采用：**代码可以重写，认知不能清零**。

**END OF BASELINE**
