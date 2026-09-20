# ANovel V2 External Reference Architecture & Competitive Design Study 2026

> **中文名**：ANovel V2 外部参考架构与竞争设计深度研究 2026  
> **Document ID**：RES-0002  
> **Version**：1.0.0  
> **Status**：BASELINE / RESEARCH INPUT  
> **Authority**：RESEARCH-EVIDENCE  
> **Depends-On**：`PROJECT_CONSTITUTION.md`, `V1_FORENSIC_LESSONS.md`  
> **Research Cutoff**：2026-09-18  
> **Primary Use**：把公开产品、开源实现、学术研究和成熟基础设施中的优秀设计，转换为 ANovel V2 可执行的架构决策输入。  
> **Rule**：本报告不建议 fork 任何单一项目。所有外部设计只能以“问题—证据—迁移原则”的方式进入 V2。

---

# 0. Executive Conclusion

截至 2026 年 9 月，公开网络中已经存在大量与 ANovel V2 部分重叠的产品、项目和研究，但没有找到一个公开系统完整覆盖：

```text
Commercial Chinese Web Novel
+
Genre Constitution
+
Reference / Corpus Guided Genesis
+
Canonical Narrative State
+
Long-form Hierarchical Planning
+
Transaction-style Canon Commit
+
Durable Workflow
+
Deterministic + Semantic Quality Gates
+
Human Calibration
+
Reader / Market Feedback
+
Hundreds-of-chapters / million-word production evidence
```

因此 ANovel V2 不应寻找“一个可直接复制的竞品”，而应采用：

> **Composite Reference Architecture**

即：

```text
Novel Studio AI
→ Canon acceptance boundary + Context Pack

NovelForge
→ Domain-oriented Chinese web-novel workflow + approval before state update

DOME
→ Dynamic hierarchical planning + temporal memory

ConWriter
→ Symbolic state + required transition + risk-aware local repair

MAGNET / ATLAS
→ Character-grounded intent + shared world state + graph verification

ConStory-Bench
→ Long-form consistency taxonomy + evidence-grounded checking

Novelcrafter
→ Codex + provider independence + author-oriented UX

Sudowrite
→ Story Bible dependency graph + Scene-first drafting

NovelAI
→ Context budget / activation / priority mechanics

Temporal / LangGraph
→ Durable workflow + checkpoint / replay / human-in-the-loop

OPA
→ Policy-as-Code

OpenLineage
→ Run / Job / Input / Output provenance

OpenTelemetry
→ Trace / Metric / Log observability
```

然后由 ANovel V2 自己补齐公开系统普遍缺失的：

```text
Genre Intelligence
Genre Canon Extensions
Commercial Web-Novel Narrative Engine
Reference Intelligence Firewall
Narrative Transaction
Canon Commit Permit
Evidence Authority Model
Genre Certification
30/100/300-Chapter Certification
Human + Reader + Market Calibration
```

---

# 1. Research Method

所有对象统一按照以下六个问题分析：

1. **Problem** — 它解决什么真实问题？
2. **Existing Solution** — 它怎么解决？
3. **Evidence** — 公开资料能证明到什么程度？
4. **Borrow** — ANovel V2 应借鉴什么？
5. **Do Not Borrow** — 哪些不应照搬？
6. **V2 Improvement / ADR** — V2 应如何进一步提升？

重要原则：

> “功能存在”不等于“生产能力已证明”。

学术实验、开源 MVP、商业写作工具的证据等级必须分开。

---

# 2. Reference Landscape

## 2.1 Three Reference Classes

### A. Commercial Authoring Products

- Novelcrafter
- Sudowrite
- NovelAI

优势：
- UX 成熟；
- 作者工作流清晰；
- Context/Story Bible/Codex 经验丰富；
- 实际用户使用。

不足：
- 主要定位 AI-assisted writing；
- Canon transaction / production state / durable autonomous production 通常不是核心；
- 商业网文长期自治生产不是其公开主目标。

### B. Open-source Long-form Writing Systems

- Novel Studio AI
- NovelForge

优势：
- 可以观察真实架构；
- 已开始引入 Canon、State、Approval、Context Pack；
- 更接近 ANovel V2 的工程问题。

不足：
- 公开项目仍较早期；
- 没有百万字/商业平台验证；
- Genre Intelligence 仍明显不足。

### C. Research & Infrastructure

Research：
- DOME
- ConWriter
- MAGNET / ATLAS
- ConStory-Bench

Infrastructure：
- Temporal
- LangGraph
- OPA
- OpenLineage
- OpenTelemetry

这类参考对 V2 的价值最高，因为它们解决：

```text
planning
state
transition
verification
durability
policy
lineage
observability
```

而这些正是 V1 最薄弱的控制平面。

---

# 3. Novel Studio AI

**Type**：Open-source local-first long-form fiction workbench

公开设计的关键流程：

```text
Plan
→ Build Context Pack
→ Draft Chapter
→ Check Continuity
→ Revise Style
→ Accept Chapter
→ Extract Memory
→ Reuse Memory
```

项目公开说明中明确：Draft 不更新 canon；只有 accepted chapter 才写入 summary、character state、graph triples、timeline events、memory chunks。

## 3.1 Problem

解决 LLM 长篇写作常见问题：
- 忘记过去章节；
- 人物位置不可能；
- 物品所有权漂移；
- 死者复活；
- 风格漂移；
- 模型只依赖 chat history。

## 3.2 Existing Solution

### Story Bible / Style Bible
版本化管理长期设定。

### Hierarchical Outline

```text
Volume Outline
→ Five-chapter Arc Pack
→ Chapter Outline
→ Scene Beats
```

### Context Pack

生成前编译：
- Story Bible
- Style Bible
- volume outline
- arc pack
- chapter outline
- scene beats
- recent accepted summaries
- previous ending
- active character states
- graph triples
- retrieved memory
- recent timeline events
- forbidden contradictions
- fact priority

### Acceptance Boundary
Draft 与 Memory Update 分离。

### Structured State
- character states
- relation triples
- timeline
- memory chunks

### Hybrid Retrieval
关键词 + graph facts + state + timeline + vector retrieval。

## 3.3 Evidence

公开 README 显示：
- TypeScript / Next.js / SQLite；
- Zod structured output validation；
- tests 覆盖 continuity schema、memory extraction、relation validity windows、chapter acceptance gate、Context Pack、API key redaction；
- CI 执行 test/type/build。

但公开仓库规模仍小，不能推断它已经证明 100/300 章生产能力。

## 3.4 Borrow

### REF-NSA-001 — Accepted Chapter → Canon Update
应直接成为 V2 根规则。

### REF-NSA-002 — Context Pack as explicit artifact
V2 应进一步升级：

```text
ContextArtifact
{
  source_hashes
  authority
  token_budget
  inclusion_reason
  exclusions
  compiler_version
}
```

### REF-NSA-003 — Recent local continuity + long-term canon
Context 同时包含近端连续性与长期事实。

### REF-NSA-004 — Fact Priority / Forbidden Contradictions
V2 将其升级为机器可执行 Policy。

## 3.5 Do Not Borrow

1. SQLite + local vector search 可用于 MVP，但不能预设为百万字最终架构。
2. “Accept” 不应只是 UI Action；V2 必须拆分 Validation / Approval / Commit Permit / Canon Commit。
3. Memory Extraction 不能直接等价 Canon；Extractor 只能产生 NarrativeDelta Candidate。

## 3.6 V2 Improvement

```text
Draft
↓
NarrativeDelta Candidate
↓
Deterministic Validation
↓
Semantic Validation
↓
Human/Policy Approval
↓
Commit Permit
↓
Canon Transaction
↓
Canon N+1
```

**ADR Candidate**：`ADR-0021 Accepted content must cross an explicit Canon Commit Boundary.`

---

# 4. NovelForge

**Type**：Open-source Chinese web-novel desktop studio

公开工作流：

```text
Novel Bible
↓
Volume / Chapter / Scene Outline
↓
Scene Planning + Character Intent
↓
Draft Generation
↓
Review and Author Approval
↓
Canon Facts + Character State Update
↓
Next Scene
```

## 4.1 Problem

解决：
- 长篇不是独立 Prompt；
- 需要持续 world/character/context；
- 人物“知道什么”；
- Revision 后状态如何更新；
- 多模型任务路由。

## 4.2 Existing Solution

公开能力包括：
- Novel Bible；
- volume → chapter → scene planning；
- scene planning；
- character intent；
- writing；
- review；
- fact extraction；
- state update；
- approval before continuity changes；
- revision-aware history；
- Ollama / DeepSeek per-step routing；
- OS credential store；
- Markdown / EPUB export。

## 4.3 Borrow

### REF-NF-001 — Character Intent before prose
SceneContract 不只应该有“发生什么”，还应该有：

```text
character_goal
character_belief
knowledge_boundary
emotional_state
decision_pressure
relationship_intent
```

### REF-NF-002 — Fact Extraction and State Update are explicit pipeline stages
V2 强化为：Extraction produces proposal, not truth.

### REF-NF-003 — Revision-aware history
小说生产一定会改章、重写 Scene、插入章节、修改事实，因此需要：

```text
Revision
→ Impact Analysis
→ Dependent Plan Invalidation
→ Revalidation
```

### REF-NF-004 — Task-specific Model Routing
Planner / Writer / Extractor / Reviewer 使用不同 ModelPolicy。

## 4.4 Do Not Borrow

1. Author approval 不能是唯一 integrity mechanism，V2 必须有机器 hard gate。
2. Character Agents 不拥有 persistent truth；Character Intent 是计算，Character State 才是真值。
3. Desktop workflow 不是 Production OS 架构；Runtime 应 headless-first。

## 4.5 V2 Improvement

新增：

```text
CharacterKnowledgeState
CharacterIntentArtifact
CharacterDecisionProposal
```

这些都不能直接写 Canon。

**ADR Candidate**：`ADR-0022 Character reasoning is stateless computation over authoritative Character State.`

---

# 5. DOME — Dynamic Hierarchical Outlining with Memory Enhancement

**Source**：NAACL 2025 Long Paper

DOME 针对：rigid outline、缺 macro-level planning、长篇 uncertainty、contextual conflict。

## 5.1 Existing Solution

### Dynamic Hierarchical Outline (DHO)
大纲不是一次冻结，而是在生成过程中动态调整。

### Memory Enhancement Module
基于 temporal knowledge graph 存储/访问生成内容。

### Temporal Conflict Analyzer
利用 temporal KG 评估一致性。

## 5.2 Borrow

### REF-DOME-001 — Planning must be hierarchical

```text
Series Vision
→ Macro Arc
→ Volume
→ Arc
→ Chapter
→ Scene
```

### REF-DOME-002 — Future planning is mutable

```text
Canon = history
Plan = intention
```

Plan 可重算，Canon 不静默修改。

### REF-DOME-003 — Temporal memory must be explicit
至少表示：Event、valid_from、valid_to、occurred_at、known_by、caused_by。

## 5.3 Do Not Borrow

1. 学术 story length 不等于百万字商业网文。
2. Temporal KG 不应该成为所有事实唯一模型。
3. Dynamic planning 不能用来偷偷改过去。

## 5.4 V2 Improvement

```text
Committed Canon
+
Open Promises
+
Arc Goal
+
Risk / Fatigue
+
Reader Evidence
→ Rolling Plan
```

每次 replan 输出 PlanDiff、Rationale、ImpactedContracts、InvalidatedArtifacts。

**ADR Candidate**：`ADR-0023 Future plans are versioned, dynamically replannable projections over immutable committed history.`

---

# 6. ConWriter

**Type**：2026 long-form generation research

核心：

```text
Static Story Requirements
+
Dynamic Narrative Memory
+
Symbolic Story State
+
Required Transition
+
Risk Signal
↓
Scene Generation
↓
Transition Check
↓
Localized Repair
```

## 6.1 Why It Matters

传统 Reviewer 问“这一章有没有问题？”；ConWriter 更接近问“State N 到 Scene S 是否完成合法且要求的状态转移？”

## 6.2 Borrow

### REF-CW-001 — State transition is first-class
建立 RequiredTransition / ForbiddenTransition / ActualNarrativeDelta。

### REF-CW-002 — Scene-level production
Chapter 是 aggregate，Scene 是更细生产/修复单元。

### REF-CW-003 — Uncertainty-aware validation
主角身份、死亡、能力升级、时间跳跃、永久关系变化、世界规则变化、重大资产变化等高风险 Delta 使用更强验证。

### REF-CW-004 — Localized repair
优先局部修复而不是整章重写。

## 6.3 Do Not Borrow

1. Symbolic representation 不覆盖所有 narrative nuance。
2. Risk signal 只是选择验证强度，不是真值。
3. Contract 只控制边界，不应把文学性变成状态机填空。

## 6.4 V2 Improvement

建议建立 Narrative Transition DSL，例如：

```yaml
required:
  - entity: protagonist.company
    from: null
    to: registered

forbidden:
  - entity: protagonist.power.realm
    any_change: true

risk:
  irreversible: high
```

**ADR Candidate**：`ADR-0024 Narrative generation is validated as explicit state transition, not only text quality.`

---

# 7. MAGNET / ATLAS

**Type**：2026 research

MAGNET 使用 persona-grounded character agents、shared world state、evolving story goals；ATLAS 把 scene 变成 world graph 并跨场景检测 hallucination。

公开论文在 100-page 实验设置中报告，相比 single-model 和 IBSEN baseline 减少了 hallucination / annotation，但这仍是研究结果，不是百万字商业证明。

## 7.1 Borrow

### REF-MA-001 — Characters need goal + belief + knowledge

```text
goal
belief
fear
knowledge
relationship
emotion
resources
decision options
```

### REF-MA-002 — Shared World State
角色行动必须作用于共同世界，而不是各 Agent 私有世界。

### REF-MA-003 — Graph verification
关系、所有权、位置、事件边特别适合 Graph 表达。

## 7.2 Do Not Borrow

1. 不采用永久 Agent-per-character。
2. 多 Agent 讨论会显著放大成本和不可预测性。
3. LLM editor evaluation 不是商业真值。

## 7.3 V2 Improvement

```text
Character State = truth
Character Reasoner = ephemeral worker
```

仅当前 Scene 重要角色进入 reasoning context。

**ADR Candidate**：`ADR-0025 Characters are authoritative state entities; character agents are ephemeral reasoning views.`

---

# 8. ConStory-Bench

**Type**：ACL Findings 2026 benchmark

公开信息：2,000 prompts、4 task scenarios、5 大 consistency error categories、19 个细分类；ConStory-Checker 的判断要求明确文本证据。

## 8.1 Core Value

Long-form consistency 必须独立 Benchmark，不能只看 fluency / plot quality。

## 8.2 Borrow

V2 建 `ANovel Consistency Benchmark`，至少覆盖：

### Characterization
identity / traits / knowledge / capability / relationship

### Factual
name / object / quantity / location / ownership

### Narrative Style
POV / tense / voice

### Timeline & Plot
chronology / causality / open thread / promise

### Worldbuilding
world law / technology / power / social institution / geography

并增加 ANovel 特有：

### Genre
authorized reality / fusion / progression

### Commercial
promise debt / payoff repetition / engine exhaustion

## 8.3 Do Not Borrow

Benchmark checker 不能直接成为唯一 production gate；确定事实优先 deterministic check。

**ADR Candidate**：`ADR-0026 Long-form consistency has a first-class regression benchmark independent of prose quality.`

---

# 9. Novelcrafter

**Type**：commercial writing platform

最值得研究：Codex、planning views、cross-book shared Codex、flexible prompting、provider independence、local model support。

## 9.1 Borrow

### REF-NC-001 — Codex UX
Canon 不能只有数据库表；人物、地点、Lore、概念要对人可浏览、可解释、可修改。

### REF-NC-002 — Series-level knowledge
预留：Universe Canon / Series Canon / Book Canon。

### REF-NC-003 — Provider Independence
Domain 不知道 OpenAI/Claude/DeepSeek。

## 9.2 Do Not Borrow

Novelcrafter 是 writer-centric productivity tool；Codex 不等于 Canon Transaction，不能替代 machine-enforced production control。

**ADR Candidate**：`ADR-0027 Narrative knowledge supports scoped canon while keeping provider-independent intelligence.`

---

# 10. Sudowrite

Story Bible 的公开依赖关系：

```text
Braindump → Synopsis
Genre → Synopsis / Outline / Scenes / Draft
Synopsis → Characters / Worldbuilding / Outline / Scenes
Characters → Outline / Scenes / Draft
Worldbuilding → Outline / Scenes / Draft
Outline → Scenes
Scenes → Draft
```

## 10.1 Borrow

### REF-SW-001 — Explicit dependency graph
每个 Artifact 知道 depends_on / produces / invalidated_by。

### REF-SW-002 — Scene as generation unit
Scene 是 prose generation 的直接上游。

### REF-SW-003 — Human editable layers
AI 生成层仍然可以手工修改。

## 10.2 Do Not Borrow

1. Genre 在 Sudowrite 中主要仍是 generation context，V2 要升级为 machine-enforced Constitution。
2. Story Bible 在写作工具中可以更灵活，但 V2 Production Mode 关键 Canon 不可缺失。
3. Chapter length 不应该只由 Scene 数量推导。

**ADR Candidate**：`ADR-0028 Narrative artifacts form an explicit dependency DAG with automatic invalidation.`

---

# 11. NovelAI

NovelAI 最值得借鉴的是 Context Management：activation key、insertion order、search range、token budget、reserved tokens、trimming、placement、cascading activation、phrase bias。

## 11.1 Borrow

### REF-NAI-001 — Context Budget is architecture
Context Compiler 处理 priority / authority / relevance / token reservation / distance / recency / risk / mandatory facts。

### REF-NAI-002 — Activation
不是所有 Character/Lore 永远进入 Context，只加入当前 Scene 相关信息。

### REF-NAI-003 — Context inspection
调试必须能看到模型实际收到的上下文。

## 11.2 Do Not Borrow

1. Keyword activation 不足以覆盖语义相关性。
2. Phrase Bias 不是 Genre enforcement。
3. Lorebook 不是 Canon transaction。

## 11.3 V2 Improvement

```yaml
items:
  - source_id:
    authority:
    priority:
    token_budget:
    inclusion_reason:
    hash:
```

**ADR Candidate**：`ADR-0029 Model context is a compiled, inspectable, versioned artifact with explicit token budget and authority.`

---

# 12. Temporal — Durable Execution

小说生产到百章/百万字后必然遇到 API failure、process restart、rate limit、manual pause、human review、partial success、retry、deployment。

Temporal 的核心思想：

```text
Workflow
→ durable deterministic control flow

Activity
→ external/non-deterministic side effect

Event History
→ replay state recovery
```

## 12.1 Borrow

### REF-TMP-001 — Workflow / Side-effect separation

```text
Workflow Decision
≠ Model API Call
≠ Canon Commit
≠ Publishing
```

### REF-TMP-002 — Event History
Production Run 可重建。

### REF-TMP-003 — Idempotency
任何 side effect 都必须考虑重试。

### REF-TMP-004 — Human wait is durable
人工审批等待不依赖进程内存。

## 12.2 Do Not Borrow

Phase 1 不必立刻部署 Temporal Service；应先借 execution semantics，再根据真实需求选 engine。

**ADR Candidate**：`ADR-0030 Workflow core follows durable-execution semantics even if initial implementation is in-process.`

---

# 13. LangGraph

LangGraph 提供 state graph、checkpoint、persistence、human-in-the-loop、fault tolerance、time travel、store、pending writes。

特别重要：节点在 checkpoint 边界失败后可能重新执行，因此 side effect 必须 idempotent。

## 13.1 Borrow

### REF-LG-001 — Checkpoint and long-term store are different
对应 V2：Workflow State != Canonical Narrative State。

### REF-LG-002 — Pending writes
已成功节点的结果应尽可能避免重复执行。

### REF-LG-003 — Human interrupt / resume
适合人工审批与长期暂停。

## 13.2 Do Not Borrow

绝不把 LangGraph State 当 Novel Canon。

## 13.3 V2 Engine Decision

Phase 1 可自研最小 deterministic workflow，或用 LangGraph prototype；M5 后根据 operational complexity、replay、human wait、scale 决定 Temporal/LangGraph/custom。

**ADR Candidate**：`ADR-0031 Workflow persistence and narrative persistence are separate stores and authorities.`

---

# 14. OPA — Policy as Code

OPA 核心思想：Policy decision 与 enforcement 解耦，结构化输入产生 decision。

## 14.1 Why It Matters

适合：

```text
Genre Constitution
Commit Authorization
Publish Eligibility
Architecture Guard
Unsafe Mode
Human Authority
Reference Boundary
```

## 14.2 Borrow

V2 设计统一 Policy Interface：

```text
input:
  genre
  canon
  delta
  contract
  evidence

output:
  allow
  deny_reasons
  warnings
  obligations
```

早期可 Python/YAML，后期可替换 OPA/Rego。

## 14.3 Do Not Borrow

“人物行为是否符合心理动机”等语义判断不应强写成 Rego；Policy-as-Code 只负责结构化、可确定规则。

**ADR Candidate**：`ADR-0032 Deterministic narrative and production rules use a Policy-as-Code interface decoupled from enforcement.`

---

# 15. OpenLineage

OpenLineage 定义 Job / Run / Dataset / Facet，并用 RunEvent 记录 START / RUNNING / COMPLETE / ABORT / FAIL。

## 15.1 Borrow

Narrative Production 映射：

```text
Job
= GenerateScene / Review / Extract / Commit

Run
= specific execution

Input Dataset
= CanonSnapshot / Contract / ContextArtifact / Prompt

Output Dataset
= Draft / ReviewEvidence / ChangeSet / CanonSnapshot
```

Custom Facet 可记录 model / token / cost / genre / chapter / evidence_level / authority。

## 15.2 Do Not Borrow

不需要先部署 OpenLineage backend；先吸收 schema 与 mental model。

**ADR Candidate**：`ADR-0033 Every production stage emits lineage linking versioned inputs, execution and outputs.`

---

# 16. OpenTelemetry

OpenTelemetry 基本 Signals：Traces / Metrics / Logs / Baggage。

V2 长跑必须回答：Chapter 187 为什么失败？哪个 model call 最贵？哪个 validation 最慢？哪个 GenrePack 违规最多？哪个 repair loop 重复？

## 16.1 Borrow

### Trace

```text
Novel Run
└─ Chapter
   └─ Scene
      ├─ Context Compile
      ├─ Generate
      ├─ Extract
      ├─ Validate
      └─ Repair
```

### Metrics
model cost / latency / retries / token / repair rate / hard violation / commit success / drift frequency。

### Logs
必须携带 run_id / chapter_id / scene_id / stage / trace_id / artifact_id。

**ADR Candidate**：`ADR-0034 Production workflow is natively observable through structured traces, metrics and logs.`

---

# 17. Cross-reference Synthesis

## 17.1 Pattern A — Explicit Narrative State
来源：Novel Studio AI / NovelForge / DOME / ConWriter / MAGNET / ConStory-Bench。

结论：长篇一致性不能依赖模型上下文长度；Canonical Narrative State 是一级架构对象。

## 17.2 Pattern B — Plan Hierarchically
来源：DOME / Sudowrite / Novel Studio AI / NovelForge。

```text
Series → Volume → Arc → Chapter → Scene
```

## 17.3 Pattern C — Draft Is Provisional
来源：Novel Studio AI / NovelForge + V1 failure evidence。

## 17.4 Pattern D — Context Must Be Selected
来源：Novel Studio AI Context Pack / NovelAI Lorebook / Novelcrafter Codex / Sudowrite Story Bible。

结论：Context Compiler 是正式生产边界。

## 17.5 Pattern E — Transition > Text Review
来源：ConWriter / ATLAS / ConStory-Bench。

```text
State N
→ expected delta
→ text
→ extracted delta
→ validate transition
```

## 17.6 Pattern F — Durable Orchestration
来源：Temporal / LangGraph。

长篇生产是 durable workflow，不是 while-loop。

## 17.7 Pattern G — Rule/Policy Separate from Model
来源：OPA + deterministic rule systems。

Hard rule 不应只存在于 Prompt。

## 17.8 Pattern H — Provenance & Observability
来源：OpenLineage / OpenTelemetry / Temporal Event History。

每章必须可解释、可追踪、可恢复。

---

# 18. What the Public Landscape Still Does Not Solve Well

## GAP-001 — Commercial Chinese Web-Novel Genre Intelligence
公开产品通常有 genre tag/text；公开研究偏 general story consistency。缺少“都市商战、家族修仙、高武、华娱、历史、无限流”等对应的 world law、state extension、progression、reader promise、commercial pattern、fusion rule。

**V2**：Genre Ontology / GenrePack / Constitution / Canon Extension / Certification。

## GAP-002 — Reference-guided Original Creation
公开工具缺少完整：

```text
Raw Reference
→ Narrative Decomposition
→ Pattern Abstraction
→ Evidence Pack
→ Originality Firewall
→ GenesisSpec
```

## GAP-003 — Canon Transaction
现有项目常做到 accepted → update memory；V2 要升级为 Candidate Delta → Validation → Commit Permit → Atomic Canon Commit。

## GAP-004 — Evidence Authority
事实、预测、judge score、simulation、market evidence 必须分权威等级。

## GAP-005 — Commercial Truth
没有公开系统证明内部 AI 分数与真实起点追读/订阅/付费长期稳定相关；V2 必须自己做 ReaderSignal calibration。

## GAP-006 — Million-word Certification
公开研究多是千字/万字/百页；商业产品不公开百万字连续自治 benchmark。因此百万字只能靠 V2 自己证明。

---

# 19. Recommended V2 Composite Architecture

```text
L0 Product / Market
↓
L1 Genre Intelligence
↓
L2 Genesis & Evidence
↓
L3 Narrative Domain & Canon
↓
L4 Planning & Contracts
↓
L5 Context & Intelligence
↓
L6 Production Workflow
↓
L7 Validation / Repair / Canon Commit
↓
L8 Evaluation / Corpus / Calibration
↓
L9 Publishing / Reader / Market Learning
```

横切：

```text
Provenance
Security
Policy
Observability
Versioning
Architecture Governance
```

---

# 20. Technology Adoption Policy

V2 不应该因为外部工具成熟就全量引入。

## Phase A — Borrow Semantics
先在 Spec 中建立 durable execution semantics、Policy interface、Lineage schema、Trace model。

## Phase B — Internal Minimal Implementation
证明 1 chapter → 10 chapter → 30 chapter。

## Phase C — Adopt Infrastructure When Proven Necessary
根据真实瓶颈选择 Temporal / LangGraph / OPA / OpenLineage backend / OTel collector。

原则：**避免提前基础设施膨胀。**

---

# 21. Reference Architecture Decisions

建议进入 ADR backlog：

1. ADR-0021 Canon Commit Boundary
2. ADR-0022 Stateless Character Reasoning
3. ADR-0023 Dynamic Versioned Planning
4. ADR-0024 Transition-oriented Generation
5. ADR-0025 Character State over Character Agents
6. ADR-0026 Long-form Consistency Benchmark
7. ADR-0027 Scoped Canon + Provider Independence
8. ADR-0028 Artifact Dependency DAG
9. ADR-0029 Compiled Context Artifact
10. ADR-0030 Durable Execution Semantics
11. ADR-0031 Workflow State != Narrative State
12. ADR-0032 Policy-as-Code Interface
13. ADR-0033 Narrative Lineage
14. ADR-0034 Native Observability

这些 ADR 目前只是候选，后续专项 Spec 完成时逐条批准。

---

# 22. Comparative Matrix

| System | Best Idea | V2 Borrow | Main Limitation |
|---|---|---|---|
| Novel Studio AI | accepted chapter updates canon | Canon boundary + Context Pack | early-stage / no commercial proof |
| NovelForge | approval before state change | character intent + revision-aware state | author-centric / early |
| DOME | dynamic hierarchical outline | rolling planning + temporal memory | research-scale |
| ConWriter | transition-constrained scenes | NarrativeDelta + localized repair | symbolic simplification risk |
| MAGNET | persona-grounded action | character goal/knowledge reasoning | agent cost / authority risk |
| ATLAS | graph verification | relationship/world graph checks | graph not full narrative truth |
| ConStory-Bench | consistency taxonomy | regression benchmark | evaluation, not production control |
| Novelcrafter | Codex + provider choice | human knowledge UX + model gateway | assistive, not autonomous OS |
| Sudowrite | Story Bible dependency chain | artifact DAG + scene-first | weak machine hard constraints |
| NovelAI | context placement/budget | Context Compiler mechanics | context != canon |
| Temporal | durable workflow | replay/idempotency/human wait | infra complexity |
| LangGraph | checkpoint/store separation | workflow persistence pattern | must not own canon |
| OPA | policy decision separation | Genre/Commit policy interface | semantic judgments unsuitable |
| OpenLineage | run/input/output lineage | Narrative provenance schema | data-tooling overhead |
| OpenTelemetry | traces/metrics/logs | production observability | not narrative model |

---

# 23. Final Competitive Positioning

公开市场主要是：

- AI-assisted Writing Studio
- Generative Story Tool
- Stateful Long-form Workbench
- Long-form Consistency Research Framework

ANovel V2 应定位为：

> **AI-native Commercial Web-Novel Production Operating System**

核心差异：

```text
not just assist
not just generate
not just remember
not just evaluate

but:

Design
→ Govern
→ Produce
→ Validate
→ Commit
→ Recover
→ Learn
```

---

# 24. Strongest Architectural Recommendation

综合 V1 与外部研究，V2 主干应固定为：

```text
Genre Constitution
       ↓
GenesisSpec
       ↓
Canonical Narrative State N
       ↓
Hierarchical Plan
       ↓
Chapter Contract
       ↓
Scene Contract
       ↓
Context Compiler
       ↓
Creative Worker
       ↓
NarrativeDelta
       ↓
Deterministic Policy
       ↓
Semantic Validation
       ↓
Localized Repair
       ↓
Commit Permit
       ↓
Canon Commit
       ↓
Canonical Narrative State N+1
```

所有复杂 AI 能力围绕这条主干生长，而不是 Agent A → B → C → D。

---

# 25. What Not to Build Yet

M5 前不优先：
- persona swarm；
- 每角色长期 Agent；
- 复杂 Reader Simulator；
- 全网实时趋势预测；
- 大型图数据库；
- Temporal 集群；
- OPA 集群；
- 多平台自动发布；
- 30+ GenrePack；
- 高级可视化 graph studio。

先证明：Canon / Genre / Transition / Workflow / 30 chapters。

---

# 26. Source Registry

本报告优先使用官方/原始资料：

- Novel Studio AI — https://github.com/YfengJ/novel-studio-ai
- NovelForge — https://github.com/hzhang092/novel-agent
- DOME — https://aclanthology.org/2025.naacl-long.63/
- ConWriter — https://arxiv.org/abs/2608.05169
- MAGNET / ATLAS — https://arxiv.org/abs/2607.00918
- ConStory-Bench — https://aclanthology.org/volumes/2026.findings-acl/
- Novelcrafter — https://www.novelcrafter.com/
- Sudowrite docs — https://docs.sudowrite.com/
- NovelAI docs — https://docs.novelai.net/
- Temporal — https://docs.temporal.io/ and https://learn.temporal.io/
- LangGraph — https://langchain-ai.github.io/langgraph/
- Open Policy Agent — https://www.openpolicyagent.org/docs
- OpenLineage — https://openlineage.io/docs/
- OpenTelemetry — https://opentelemetry.io/docs/

---

# 27. Next Document

下一份正式资料应为：

```text
WEBNOVEL_MARKET_GENRE_RESEARCH.md
```

本报告回答：**“系统架构应该向谁学习？”**

下一份回答：**“系统到底需要理解什么样的商业网文？”**

重点研究：
- 起点分类；
- 2025–2026 榜单与热点；
- 玄幻 / 都市 / 仙侠；
- 二级类型与融合类型；
- Narrative Engine；
- Progression Engine；
- Reader Promise；
- Payoff；
- 长篇发动机；
- 爆款与失败模式；
- GenrePack 应具备的机器能力。

然后才进入：`GENRE_INTELLIGENCE_SPEC.md`。

**END OF REPORT**
