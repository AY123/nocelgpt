# ANovel V1 Forensic Lessons & V2 Selective Migration Decision Report

> **中文名**：ANovel V1 全生命周期法证复盘与 V2 选择性迁移决策报告  
> **Document ID**：RES-0001  
> **Version**：1.0.0  
> **Status**：BASELINE / NORMATIVE-INPUT  
> **Authority**：RESEARCH-EVIDENCE  
> **Depends-On**：`docs/00-governance/PROJECT_CONSTITUTION.md`  
> **Repository Audited**：`ayitnovel/ainovel`  
> **Audit Ref**：`main`  
> **Latest Commit Observed**：`334518d96e8f19daee27bb2eb545cfe258518a1c` (2026-09-13)  
> **Primary Use**：为 ANovel V2 架构、迁移、回归测试和 AI Coding Agent 提供“为什么这样设计”的内部证据。  
> **AI Reading Rule**：本报告是 V1 的证据与迁移建议，不是 V2 的实现规范；若与 Project Constitution 冲突，以 Constitution 为准。

---

# 0. Executive Conclusion

ANovel V1 不应被简单归类为“失败项目”，也不应被继续当作 V2 的代码底座。

更准确的结论是：

> **V1 是一个高价值、但边界失控的长期实验平台。它产出了大量正确的工程思想、失败样本、数据资产和领域认知；同时也积累了模块膨胀、题材弱约束、多决策中心、补丁式集成和真实生产链不闭合等结构性债务。**

因此 V2 的正确策略不是：

```text
V1 → 大规模重构 → 改名 V2
```

而是：

```text
V1
├─ 提取正确原则
├─ 提取失败案例
├─ 提取可复用数据
├─ 提取经过验证的协议思想
├─ 保留回归样本
└─ 冻结旧实现
          ↓
     Greenfield V2
          ↓
Selective Migration
```

## 0.1 总体裁决

| 类别 | 裁决 |
|---|---|
| V1 产品愿景 | **KEEP** |
| 商业长篇方向 | **KEEP** |
| Story Bible / Canon 思想 | **KEEP + REDESIGN** |
| State as Projection | **KEEP** |
| Mint / 唯一事实写入口 | **EXTRACT-CONCEPT** |
| ProductionState 单一状态源 | **KEEP-CONCEPT / REWRITE** |
| Real-provider validation | **KEEP** |
| Replay / Provenance / Manifest | **KEEP-CONCEPT** |
| Golden Set / Human Calibration 结构 | **MIGRATE-DATA + REDESIGN** |
| Genre 关键词/Prompt 补丁 | **ARCHIVE AS LESSON** |
| 当前 Genre Contract 实现 | **REWRITE** |
| 当前 ChapterContract 实现 | **REWRITE** |
| 当前 Contract Integration | **REWRITE** |
| 当前 serialize/ workflow 集群 | **REWRITE / SPLIT** |
| ReaderSim / Commercial 模拟 | **ARCHIVE-RESEARCH / LATER REBUILD** |
| 大量 Reviewer / Report / Experiment 模块 | **SELECTIVE ARCHIVE** |
| novel-dushi 旧生成正文 | **MIGRATE AS NEGATIVE REGRESSION DATA** |
| V1 历史文档 | **ARCHIVE / EVIDENCE ONLY** |
| V1 代码整体复制到 V2 | **PROHIBITED** |

最重要的一句话：

> **V2 应继承 V1 的认知，不继承 V1 的结构性混乱。**

---

# 1. Audit Scope & Method

## 1.1 Evidence Priority

本报告按以下优先级判断：

```text
Current main code
> Current persisted artifacts
> Current tests
> Current machine-readable metadata
> Current ROADMAP / README / CLAUDE.md
> Archived implementation reports
> Historical claims
```

任何“测试全部通过”“阶段完成”“成熟度 xx%”等历史结论，若与当前代码或真实 Artifact 冲突，以当前事实为准。

## 1.2 Repository Snapshot

当前观察到的 V1 仓库特征：

- 项目：`ayitnovel/ainovel`
- 默认分支：`main`
- 最新观察提交：`334518d9`
- 上一个大规模架构/归档提交：`272a7507`
- 最新提交将 `novel-dushi` 正式纳入版本库，参考小说原文被排除，旧生成结果被标记 INVALIDATED。
- 当前 `main` 搜索仍发现至少一处归档文档存在**明文、真实格式的 Anthropic API Key 值**；本报告刻意不记录该值。
- `main` 当前 GitLab Pipelines：**0**。
- `AI-Novel-Runtime/requirements.txt` 使用宽松依赖下界，无 lock：`pyyaml>=6.0`、`jsonschema>=4.0`、`openai>=1.0.0`、`httpx>=0.23.0`、`pytest>=8.0`。

因此，“本地测试很多”与“持续集成已经成为系统级防线”仍是两回事。

---

# 2. V1 Evolution：项目真实演进

## 2.1 Phase A — Engineering Kernel

这一阶段形成了 V1 最值得保留的工程纪律：

- Standard / Catalog / Schema-first；
- Task Package；
- Deterministic Build；
- Registry；
- Derived Artifact；
- Replay；
- Artifact Contract；
- Architecture Fitness；
- Model Protocol；
- Real Provider seam；
- Manifest；
- Facts / Derived 分离。

这一阶段的工程思想明显强于普通 AI 写作项目。

**裁决：大量 KEEP-CONCEPT。**

## 2.2 Phase B — Commercial Narrative Intelligence

随后系统快速加入：

- Quality Model；
- Narrative IR；
- Character Runtime；
- Commercial Loop；
- Reader Simulation；
- Market Positioning；
- Publishing OS；
- Novel Brain；
- Narrative Director；
- Promise / Retention；
- Long Arc；
- Corpus Intelligence；
- Human Calibration；
- Blind Evaluation；
- Million-word stability 等。

问题不在于这些能力“不该存在”。问题是：

> **上层能力增长速度超过了 Canon、Genre、Contract 和 Production Transaction 的成熟速度。**

系统变得“什么都有”，但底部仍可能回答不好：

- 主角是谁？
- 现在是哪年？
- 这是都市还是玄幻？
- 当前正文到底是否允许写入长期状态？
- Reviewer 的 pass 是否真的代表可继续生产？
- 下章到底基于哪个 previous-final？

这是 V1 最重要的结构性教训。

## 2.3 Phase C — Real Novel Failure Exposed the Architecture

`novel-dushi` 是 V1 最有价值的资产之一，不是因为它生成得好，而是因为它真实暴露了系统弱点。

Story Bible 明确规定主角为“陈默”，但旧 Chapter 1 persisted final 实际正文使用“林远”，同时同一 Artifact 中存在：

- `final_review.overall_verdict = pass`
- `publish_readiness = ready`
- comparison / recovery 建议 `rollback`
- editorial verdict `accept`
- pipeline decision `revise / hold_for_human_review`
- 最终 `production_state = invalidated`

这说明当时多个判断系统都“有自己的意见”，但没有一个真正从生成前到 Canon Commit 全链路封锁错误。

> **这不是单一模型失败，而是控制平面失败。**

---

# 3. What V1 Did Well — 必须保留的资产

## 3.1 “No Consumer = Stub”

V1 `ROADMAP.md` 早期明确形成：

> **a module with no consumer is a stub**

这是极其重要的工程纪律。它约束：Schema 不能只存在、Artifact 不能只落盘、新能力必须证明消费者。

### V2 Decision

**KEEP AS CONSTITUTIONAL PRINCIPLE**

迁移为：`P-013 Every New Module requires a Real Consumer`，并进入 Architecture Fitness。

---

## 3.2 State as Projection

V1 在 StoryState 上形成：

```text
StoryState@N = fold(facts, events[1..N])
```

它比“Agent 自己记住故事状态”成熟得多：可重建、可验证、可做 staleness、可 replay、不依赖单次模型上下文。

### V2 Decision

**KEEP-CONCEPT**，升级成：

```text
Canon Event Log
+
Canon Snapshot
+
Deterministic Projection
```

V1 `StoryState` 不直接搬代码。

---

## 3.3 Facts / Derived Separation

V1 已经理解：

- Prose 不是 Fact；
- Reader Simulation 不是 Fact；
- Market Snapshot 不是 Fact；
- Derived artifact 不应反向污染 Registry；
- 外部信号和小说内部事实不是同一种数据。

### V2 Decision

**KEEP / EXPAND**，扩展为 Authority Model：

```text
CANON
PLAN
CONTRACT
REFERENCE
MARKET
MODEL
DIAGNOSTIC
DRAFT
```

---

## 3.4 Mint as Unique Write Boundary

V1 Fact Candidate → Human Review → Mint → Recompute 的思想是重要资产。

值得保留的纪律：

- candidates 只准备；
- mint 才是唯一写入口；
- validate-before-write；
- conflicting 不自动解决；
- derived staleness；
- ID mint 单独治理；
- irreversible action 需要 Authority。

### V2 Decision

**EXTRACT-CONCEPT, DO NOT COPY IMPLEMENTATION**

V2 升级为：

```text
NarrativeDelta
→ ChangeSet
→ Validation
→ Commit Permit
→ Canon Commit
```

---

## 3.5 ProductionState as Single Decision Source

V1 后期已经认识到 `publish_readiness / commercial_verdict / production_decision` 不能同时当状态真值。

当前 `runtime/contract/production_state.py` 明确声明 ProductionState 是章节生产的唯一状态决策源，旧字段仅 advisory。

### V2 Decision

**KEEP-CONCEPT / REWRITE STATE MACHINE**

V2 从第一天就统一状态，而不是后期再加兼容层。

---

## 3.6 Real-provider Validation

V1 `ROADMAP.md` 记录多次真实模型才暴露的问题：

1. live provider 曾未真正接入 serial generation；
2. HTTP 503 曾被误判为 Permanent；
3. `timeout_seconds` 曾被错误包含在 replay semantic key；
4. Fact extractor 看不到 entity name/alias，导致 known entity 被识别为大量 `new`；
5. Character lifecycle `status` 被模型误用成“受伤/被追捕”等叙事情境。

### V2 Decision

**KEEP AS MANDATORY ENGINEERING PRACTICE**

任何 Model/Provider/Prompt seam：

```text
Unit/Fake
+
Replay
+
Real-provider Contract Test
```

---

## 3.7 Derived Artifact Staleness / Recompute

V1 已有 source pin、fact version、staleness detection、deterministic rebuild vs generative regeneration 分离。

### V2 Decision

**KEEP-CONCEPT**，扩展到 GenrePack、Canon Snapshot、Context Artifact、Contract、Plan、Prompt、ModelPolicy、Reference Evidence、Quality Policy。

---

## 3.8 Golden Set / Calibration Infrastructure

当前 `quality-golden-set`：target 100、current 50，覆盖 positive / negative / boundary / ai_voice / padding / no_conflict / character_degradation / ending_failure，并声明 double blind、human scores、reviewer independence、regression gate、copyright review。

`w8-w9-ai-flow-report.md` 也明确承认：AI 双评只用于流程闭环，**不是真值**；同一 temp=0 模型两个 persona 的相关性明显虚高。

### V2 Decision

**MIGRATE-DATA + REBUILD CALIBRATION**

不要把当前 AI 侧“trusted”结果当正式人类校准。

---

# 4. Structural Failures — 必须禁止重演

## 4.1 Genre Was Added Too Late

V1 当前存在 `genre_taxonomy.py`、`genre_contract.py`、genre markers、channel routing、cadence defaults、forbidden keywords、genre drift detection、special prompts。

这些是在系统复杂度已经很高之后补上的。

`CLAUDE.md` 曾明确承认：早期设计隐含玄幻/奇幻、`power_system` 被错误通用化、都市/历史/科幻支持不足、参考都市小说曾被误判，修复主要依赖关键词、专用 Prompt 和 Schema 变体。

### 问题

这类补丁只能挡住最明显的污染，不能完整表达：

- Reality Model；
- Power/Progression；
- World Law；
- Canon Extension；
- Hybrid Genre；
- Reader Promise；
- Domain-specific state；
- Subgenre；
- Trope/Mechanic 正交维度。

### V2 Decision

**CURRENT GENRE CODE = REWRITE**

只迁移题材知识、失败样本、关键词 detector、平台分类映射。

---

## 4.2 ChapterContract Is Project-specific

当前 `runtime/contract/chapter_contract.py` 仍硬编码：

```text
protagonist_name = "陈默"
```

从 Story Bible 构建时也继续硬编码“陈默”，尽管注释声称“从 Story Bible 顶层读取”。

`_simple_extract()` 又采用：

```text
"protagonist_name": "陈默" if "陈默" in draft_text else None
```

如果正文完全写成另一个主角名，extractor 可能返回 None；而 Contract hard comparison 只在 extracted_protagonist 有值时执行。预期主角未出现在前 1000 字目前只是 warning。

### V2 Decision

**FULL REWRITE**

V2 Contract 必须完全由 Canon/Story/Genre 编译；missing required extraction 本身即 failure；使用 entity roster / alias resolution；Contract 不得依赖模型“恰好抽到错误名字”才能发现问题。

---

## 4.3 Provenance Is Incomplete

当前 ChapterContract：

```text
previous_hash = f"placeholder-hash-{chapter_num}"
```

也就是说存在 provenance 字段，但没有真实上一章 final hash。

### V2 Decision

Chapter N 至少绑定：

- Canon parent hash；
- previous committed chapter hash；
- Story/Canon version；
- GenrePack hash；
- Arc plan hash；
- Context Artifact hash；
- Prompt hash；
- ModelPolicy hash。

---

## 4.4 Contract Integration Is Optional by Default

当前多处：

```text
enable_contract_integration: bool = False
```

包括 `create_integration`、`create_production_hook`、`SerialHookAdapter`、`wrap_serial_with_hooks`、`create_adapter`、`run_serial_with_contracts`。

测试甚至明确断言：

> “契约集成应该默认禁用”

### V2 Decision

**DO NOT MIGRATE THIS POLICY**

```text
Production = contracts mandatory
Experiment/Unsafe = explicit bypass
```

Unsafe 结果不得成为 Publishable Canon。

---

## 4.5 Missing Contract Can Pass

当前：

```text
if not contract:
    return True, {"message": "无契约，跳过验证"}
```

这是典型 fail-open。

### V2 Decision

`Production` 下：`Missing Contract = BLOCKED`。

---

## 4.6 Continuity Error Can Be Logged Without Blocking State Advance

当前 `contract_integration.py` 能产生 continuity errors，但存在只 `logger.warning(...)` 的路径，随后 state 仍可能推进。

### Deep Lesson

> **Detection != Enforcement**

Validator 写得再好，如果没有绑定 State Transition / Commit Permit，就不是硬约束。

### V2 Decision

所有 hard validation 必须绑定：

```text
Gate
→ State Transition
→ Commit Permit
```

---

## 4.7 Multiple Decision Centers

`novel-dushi` 旧 final artifact 是最清晰证据：同一章 QA pass、publish ready、rollback、editorial accept、pipeline revise、production invalidated 同时存在。

### V2 Decision

统一：

```text
Evidence
   ↓
Policy
   ↓
ProductionState
   ↓
Commit Permit
```

Reviewer/Commercial/ReaderSim 不拥有状态写权。

---

## 4.8 `serialize/` Became a God Package

当前 `AI-Novel-Runtime/runtime/serialize/` 约 90 个文件，包含：serialization、baseline、A/B、calibration、blind evaluation、contracts、checkpoint、cost、experiments、golden sample、30-chapter launch、long arc、million-word stability、platform feedback、quality、reviewer calibration、scheduler、stage graph、winner drift、run manifest 等。

这已经不是“serialize”。

### V2 Decision

**NO CODE COPY**

按 Bounded Context 重建：

```text
workflow/
experiments/
evaluation/
calibration/
provenance/
production/
artifact_io/
```

---

## 4.9 StageGraph Does Not Own Runtime

`build_default_stage_graph()` 当前搜索只出现在 `stage_graph.py` 及其测试，没有成为 WorkflowScheduler 的真正执行来源。

这代表“架构模型”和“真实执行路径”分离。

### V2 Decision

如果建设 StageGraph，它必须成为执行来源；否则不建设。

---

## 4.10 Module Shadowing / Naming Collision

当前同时存在：

```text
runtime/dashboard.py
runtime/dashboard/
```

历史上也曾出现类似 `serialize.py` vs `serialize/`。

### V2 Decision

Architecture Fitness：`foo.py + foo/ = CI FAIL`。

---

## 4.11 Prompt / Prompts Fragmentation

当前 `runtime/` 同时存在 `prompt/` 与 `prompts/`，再加各子域内部 Prompt 逻辑。

### V2 Decision

Prompt 是版本化 Production Asset；Domain 只引用 Prompt ID/version。

---

## 4.12 Tests Are Numerous but CI Is Not Institutionalized

历史文档多次报告 1000–2000+ tests 通过，但当前 GitLab `main` pipeline count = 0。

### V2 Decision

Day 1 建 CI：

```text
lint
unit
contract
architecture-fitness
schema
secret-scan
deterministic-integration
real-provider scheduled/manual
```

---

## 4.13 Dependencies Are Not Locked

当前 requirements 使用 `>=` 下界，对强调 replay / reproducibility / long-term production 的系统不足。

### V2 Decision

采用 `pyproject.toml + lock file`，区分 runtime/test/dev/provider extras。

---

## 4.14 Security Governance Failed Once

最新 commit message 称已把归档文档中的 Anthropic key 替换成环境变量，但当前 `main` 仍可搜索到至少一处真实格式的 credential 值。

### V2 Decision

**P0 SECURITY LESSON**：rotate、remove from HEAD、scan history、secret scanning in CI、pre-commit scan、archive 同样扫描、fixture secret 必须明显 fake。

---

# 5. Genre Forensics

## 5.1 Current Genre Taxonomy Has Useful Knowledge

`genre_taxonomy.py` 已积累：

- 起点男频/女频映射；
- 一级/二级分类；
- pacing defaults；
- discriminant markers；
- genre degradation concept；
- authored coined term extraction；
- must / forbid rules。

它自身也承认：pacing 是 C-grade experience，并非真实平台测量；markers 是 proxy，不是 genre truth。

### V2 Decision

**MIGRATE KNOWLEDGE, NOT MODULE**

转化为：Genre Knowledge Base、Platform Taxonomy Mapping、Market Evidence、Certification Fixtures，而不是复制 Python dict。

## 5.2 Current Genre Contract Is Too Keyword-centric

`genre_contract.py` 的 hard gate 主要依赖禁用关键词，例如都市禁止修炼/灵气，玄幻禁止股票/互联网。

### False Positive

都市异能、都市修仙、现代修真等合法融合可能被误判。

### False Negative

类型漂移可以不用敏感词表达。

### Wrong Abstraction

“公司”“手机”等词本身并不能决定世界规则是否合法。

### V2 Decision

Genre hard gate 基于：

```text
Genre Constitution
+
World Law
+
Fusion Policy
+
Capability/Entity State
```

关键词只作为辅助 detector。

---

# 6. Canon & State Forensics

## 6.1 Story Bible Is Valuable but Not Enough

V1 Story Bible 已能记录 protagonist、chapter events、date、location、required beats、irreversible changes、hooks、world、characters、narrative rules。

方向正确，但 `novel-dushi` 证明：

```text
Bible says 陈默
Draft writes 林远
QA still says pass
```

### V2 Decision

Story Bible 不再只是文件，必须编译成：

```text
Canon
Contracts
Context
Validation Rules
```

## 6.2 V1 State Models Are Split

V1 同时有 narrative state、production state、pipeline state、registry facts、chapter final、run manifest、derived state 等。

V2 严格分四类：

```text
Canonical Narrative State   # 小说事实
Production State            # 工件生产生命周期
Workflow State              # 运行/阶段状态
Derived Projection          # 可重建读模型
```

任何字段必须归属其中一个。

---

# 7. LLM Infrastructure Forensics

## 7.1 Model Gateway Concept Is Correct

V1 已有 provider factory、Claude / OpenAI-compatible、retry、replay、model protocol、cost/token metadata。

### V2 Decision

**SELECTIVE REIMPLEMENTATION**，Provider Layer 完全属于 Infrastructure。

## 7.2 Replay Needs Semantic Request Identity

V1 已真实发现 `timeout_seconds` 不应进入 semantic replay key。

V2 Request fingerprint 分类：

```text
Semantic:
  prompt
  model
  sampling
  max output
  tool policy

Operational:
  timeout
  retry count
  request id
  telemetry
```

---

# 8. Quality / Evaluation Forensics

## 8.1 Deterministic vs Evaluative Split Is Correct

V1 已坚持 deterministic 可以 gate、evaluative advisory、reader/commercial simulation comparison-only。

### V2 Decision

升级为 Evidence E0–E4。

## 8.2 Judge Bias Is a Fundamental Risk

V1 已发现：AI Judge 可能偏爱 AI 文本；same-model persona 高度一致；`ai_voice_risk` 自动对齐弱；AI/Human correlation 可虚高。

### V2 Decision

Judge 最终用途：triage / ranking / diagnosis / candidate comparison，不是“真理评分器”。

## 8.3 Golden Set Should Survive

迁移：sample、labels、taxonomy、blind-review metadata、governance、calibration schema ideas。

不得直接迁移成真值：AI persona consensus、AI-only trusted labels、来源不清的模板化 human scores。

---

# 9. Commercial / Reader Simulation Forensics

V1 Commercial Loop、Reader Persona、Market Positioning 有研究价值，但不应成为 V2 第一阶段核心。

原因：

1. 真实 reader signal 仍不足；
2. simulated pay intent 不是商业真值；
3. Judge/Simulation 存在同源偏差；
4. Canon/Genre 不稳时，上层商业优化只会优化错误作品。

### V2 Decision

**ARCHIVE AS RESEARCH / REBUILD AFTER 30-CHAPTER + HUMAN CALIBRATION**。

---

# 10. Workflow / Scheduler Forensics

## 10.1 Valuable Pieces

V1 有 checkpoints、run manifest、cost breaker、workflow scheduler、stage graph、resume tests、long-run artifacts，说明已经理解“长篇不是一个 while-loop”。

## 10.2 Orchestration Is Fragmented

Scheduler / serial / hooks / wrapper 路径重叠，Contract 通过额外 adapter/wrapper 接入，Experiment 与 Production 大量混在 `serialize/`。

### V2 Decision

**FULL REWRITE OF ORCHESTRATION**。

V2 只有一个 Workflow Engine。每 Stage 声明：input/output contract、side effect、idempotency key、retry、checkpoint、authority、budget、timeout、recovery。

---

# 11. Repository Hygiene Forensics

V1 同一仓库混合：source、standard、experiments、generated artifacts、novel projects、reports、quality output、历史完成文档。

仓库体积不是当前最大问题，**认知噪音才是**。

### V2 Decision

代码仓只保留：source、normative docs、schemas、small curated fixtures、canonical regression evidence。

大体积 raw runs、full manuscripts、reference texts、bulk corpus、replay blobs 放 Artifact/Data Storage。

---

# 12. Selective Migration Matrix

| V1 Asset | Decision | V2 Action |
|---|---|---|
| Product vision | KEEP | 写入 Product Charter |
| Commercial long-form goal | KEEP | 最终 DoD |
| AI multi-model concept | KEEP | Model Gateway |
| Standard / schema-first | KEEP | 新 Schema Registry |
| Catalog concept | KEEP | 重做 typed registry |
| Story Bible | EXTRACT-CONCEPT | 编译为 Canon/Contracts |
| Registry facts | EXTRACT-CONCEPT | Canon Event + Snapshot |
| StoryState projection | KEEP-CONCEPT | Canon projector |
| Mint unique writer | KEEP-CONCEPT | Canon Commit Service |
| Fact Candidate | KEEP-CONCEPT | NarrativeDelta candidate |
| Recompute/staleness | KEEP-CONCEPT | generalized invalidation |
| ID ledger | SELECTIVE | Entity ID service if needed |
| ProductionState | KEEP-CONCEPT | new state machine |
| ChapterContract | REWRITE | generic compiled contract |
| ContractIntegration | REWRITE | mandatory production gate |
| Genre taxonomy knowledge | MIGRATE-KNOWLEDGE | data, not Python dict |
| Genre marker tests | MIGRATE-AS-DIAGNOSTIC | smoke detector |
| Genre keyword contract | ARCHIVE/REWRITE | Constitution policy |
| Outline pipeline | EXTRACT-CONCEPT | hierarchical planning |
| Long Arc | EXTRACT-CONCEPT | Series/Volume/Arc planner |
| Narrative IR | EXTRACT-CONCEPT | Scene/Beat plan only if consumed |
| Character Runtime | EXTRACT-CONCEPT | Canon character projections |
| Promise ledger | EXTRACT-CONCEPT | Canon/plan promise system |
| Progression | EXTRACT-CONCEPT | Genre-specific progression |
| Reference/Corpus | EXTRACT-CONCEPT | Evidence architecture |
| Novel Brain | EXTRACT-CONCEPT | GenesisSpec/Story Constitution |
| Director | ARCHIVE-CONCEPT | planning policy, no new agent initially |
| Reader Simulation | ARCHIVE-RESEARCH | rebuild after calibration |
| Commercial Loop | ARCHIVE-RESEARCH | rebuild after reader signal |
| Market Positioning | KEEP-CONCEPT | Genesis evidence layer |
| Publishing OS | REWRITE LATER | after correctness |
| Dashboard | REWRITE LATER | read model only |
| LLM factory/retry/replay | SELECTIVE REIMPLEMENT | infrastructure |
| Run Manifest | KEEP-CONCEPT | RunRecord/Lineage |
| Golden Set | MIGRATE-DATA | sanitize + provenance |
| Calibration pipeline | KEEP-CONCEPT | human-first rebuild |
| serialize/ package | DO NOT MIGRATE | split domains |
| historical docs | ARCHIVE | evidence only |
| novel-dushi Story Bible | MIGRATE AS FIXTURE | regression baseline |
| novel-dushi invalidated finals | MIGRATE AS NEGATIVE DATA | never production seed |
| old reference novels | DO NOT COPY INTO CODE REPO | legal/evidence storage |
| old tests | SELECTIVE PORT | invariants, not implementation |
| old secrets/history | PURGE | security incident closure |

---

# 13. V1 → V2 Regression Dataset

V1 的错误必须变成永久测试。

建议建立 `tests/regression/v1/`：

## REG-V1-GENRE-001
都市现实商业项目出现未经授权修炼/魔法体系 → **Genre Constitution HARD FAIL**。

## REG-V1-CHAR-001
Canon 主角“陈默”，正文主角“林远” → **Identity Contract FAIL**；即使 extractor 返回 unknown 也不得通过。

## REG-V1-TIME-001
Canon/Story 时间与正文年份漂移 → **Timeline FAIL**。

## REG-V1-CONTRACT-001
Production 缺 ChapterContract → **BLOCKED**，禁止“跳过验证”。

## REG-V1-CONTRACT-002
previous hash 是 placeholder → **Contract compilation FAIL**。

## REG-V1-CONTINUITY-001
hard continuity errors → **state must not advance**。

## REG-V1-STATE-001
QA pass + commercial rollback + pipeline revise → 所有 signal 只进入 Policy；唯一 ProductionState 决策。

## REG-V1-WINNER-001
评分文本 hash 与落盘文本 hash 不同 → **Commit blocked**。

## REG-V1-RETRY-001
同一 commit stage retry → **no duplicate Canon event**。

## REG-V1-REPLAY-001
仅 timeout 不同 → **same semantic request fingerprint**。

## REG-V1-ENTITY-001
Known character 用 alias/中文名出现 → **must not mint duplicate**。

## REG-V1-ENUM-001
“受伤/被追捕”等叙事情境被抽到 lifecycle status → **reject/unverifiable, not retcon**。

## REG-V1-SECRET-001
docs/archive 出现 credential pattern → **CI fail**。

## REG-V1-ARCH-001
`foo.py` 与 `foo/` 同时存在 → **Architecture Fitness fail**。

## REG-V1-ARCH-002
StageGraph 有定义但没有真实执行消费者 → **capability not production-ready**。

---

# 14. Data Migration Plan

## 14.1 Must Migrate

### Failure Fixtures
- genre drift；
- protagonist drift；
- time drift；
- conflicting verdict；
- stale derived；
- replay semantic key bug；
- entity alias duplicate；
- lifecycle enum extraction bug。

### Golden Set
前提：版权来源可追溯、human/AI 分数严格分开、provenance 完整、无 secret。

### Genre Knowledge
Python dict 转为 research evidence / taxonomy mapping / candidate GenrePack material。

## 14.2 May Migrate

- Corpus snapshot metadata；
- Book narrative profiles；
- Reference evidence templates；
- long-arc experiment datasets；
- promise / character arc fixtures。

逐项验证。

## 14.3 Must Not Migrate as Production State

- invalidated chapter finals；
- old mutable state caches；
- archived temporary run outputs；
- old run manifests as live state；
- historical pass verdict；
- AI-only human-score substitutes；
- placeholder hashes；
- hardcoded novel-specific contracts。

---

# 15. Code Migration Rules

任何 V1 代码进入 V2 前必须回答：

1. 它解决的 Domain 问题是什么？
2. 该 Domain 在 V2 是否仍存在？
3. 是否依赖 V1 路径结构？
4. 是否依赖 V1 Registry？
5. 是否依赖 V1 Artifact shape？
6. 是否依赖具体 Provider？
7. 是否存在 hidden mutable state？
8. 是否具备真实 consumer？
9. 是否通过 V2 Invariants？
10. 为什么“重写”成本高于“迁移”？

默认策略：

> **Concept first, code last.**

---

# 16. V2 Rules Derived Directly from V1

- **RULE-F-001** Genre 必须在 Genesis 之前建立，而不是正文后检查。
- **RULE-F-002** Contract 必须由 Canon/Plan 编译，不允许手写具体小说名。
- **RULE-F-003** Missing required extraction = failure/unknown，不是“跳过”。
- **RULE-F-004** Detection 若声称 hard，就必须真实影响 State/Commit。
- **RULE-F-005** 所有 irreversible side effect 都需要 idempotency key。
- **RULE-F-006** Plan / Canon / Production / Workflow 四类状态严格分离。
- **RULE-F-007** 所有评价必须声明 evidence level 和 authority。
- **RULE-F-008** AI 商业预测不能命名为真实商业结果。
- **RULE-F-009** 阶段完成报告不能替代代码/Artifact 证据。
- **RULE-F-010** 系统必须用真实长跑证明自己，不用模块数量证明。

---

# 17. Recommended V1 Freeze Policy

V2 正式启动后，V1 应进入：

```text
MAINTENANCE / EVIDENCE MODE
```

允许：安全修复、数据损坏修复、导出迁移资产、补 forensic evidence、维持旧实验可读性。

默认禁止：新增大型 Agent、新主架构、多 Genre 扩张、大规模 Workflow 重构、把 V1 继续改造成 V2。

原因：

> 每继续向 V1 增加一个长期能力，都提高 V2 的迁移认知成本。

---

# 18. Security Closure Required Before V2 Migration

V2 正式使用 V1 历史资料前，先完成：

1. 轮换泄露的 Anthropic Key；
2. 删除当前 HEAD 明文；
3. 扫描 Git history；
4. 扫描所有 archive；
5. 扫描 zip/generated docs；
6. 建 secret scanner；
7. 建 fake-secret fixture conventions；
8. 记录 incident closed evidence。

不得因为仓库 private 就降低处置级别。

---

# 19. CI Baseline Required on Day 1 of V2

```text
stages:
  - static
  - unit
  - contract
  - architecture
  - security
  - deterministic-integration
```

Real-provider：`manual / scheduled`。

必须输出：test report、schema report、architecture report、secret scan、dependency lock check。

---

# 20. Recommended New-repo Import Order

V2 新仓库不要复制 V1 tree：

```text
1. PROJECT_CONSTITUTION
2. ADR framework
3. Documentation standard
4. V1 forensic regression fixtures
5. Genre / Canon normative specs
6. Schema contracts
7. Minimal domain code
8. Canon transaction
9. Single-chapter pipeline
10. Real-provider seam
```

最后才迁 Golden Set、Corpus、commercial experiments、UI/reporting。

---

# 21. Migration Scorecard

| Area | V1 Concept Value | V1 Code Reuse Value | V2 Priority |
|---|---:|---:|---:|
| Canon / Facts | 10/10 | 4/10 | P0 |
| StoryState projection | 9/10 | 5/10 | P0 |
| ProductionState | 9/10 | 5/10 | P0 |
| Genre | 8/10 knowledge | 3/10 | P0 |
| Contracts | 9/10 concept | 2/10 | P0 |
| Genesis | 8/10 | 4/10 | P1 |
| Reference Intelligence | 8/10 | 4/10 | P1 |
| Corpus Intelligence | 8/10 | 5/10 | P2 |
| LLM gateway/replay | 9/10 | 6/10 | P0/P1 |
| Workflow | 8/10 concept | 2/10 | P1 |
| Quality deterministic | 9/10 | 5/10 | P1 |
| AI Judge | 6/10 | 3/10 | P2 |
| Golden Set | 9/10 | data-centric | P2 |
| ReaderSim | 6/10 research | 2/10 | P3 |
| Commercial Loop | 7/10 research | 2/10 | P3 |
| Publishing | 7/10 concept | 2/10 | P3 |
| Dashboard | 5/10 | 1/10 | P3 |
| Historical reports | evidence only | 0/10 | archive |
| Invalidated manuscripts | regression value 10/10 | not production | P0 fixture |

---

# 22. Final V1 Lessons

1. **AI 最容易写正文，最难维护长期真值。** Canon 比 Writer 更重要。
2. **Genre 不是标签。** 它是世界规则、状态模型、叙事发动机和商业承诺。
3. **有验证器不等于有约束。** 如果不能阻止 Commit，它只是报告。
4. **Draft 不能成为事实。** 只有 Commit 后的结果才能推进世界。
5. **AI Judge 不等于读者。** AI 评分需要人工和真实市场校准。
6. **模块数量不等于能力。** 没有 consumer 的模块就是 stub。
7. **Fake-model green 不等于 production green。** 真实 Provider 必须测试。
8. **长篇是一种 Durable Workflow。** Retry、Resume、Replay、Idempotency 从第一天设计。
9. **失败正文是高价值资产。** 应成为 Regression Dataset，而不是删除。
10. **V2 必须从“系统正确”开始，再追求“系统丰富”。** 先 1 章正确，再 10、30、100，再商业闭环。

---

# 23. Formal Migration Decision

本报告正式裁决：

> **ANovel V2 SHALL be a Greenfield implementation.**

并采用：

> **Selective Concept/Data Migration from V1.**

V1 不作为 V2 的代码分支起点。V2 不做：

```text
git checkout -b v2
```

然后继续扩。

---

# 24. Evidence Index

关键证据路径：

```text
README.md
ROADMAP.md
CLAUDE.md
AI-Novel-Runtime/requirements.txt
AI-Novel-Runtime/runtime/genre_taxonomy.py
AI-Novel-Runtime/runtime/genre_contract.py
AI-Novel-Runtime/runtime/contract/chapter_contract.py
AI-Novel-Runtime/runtime/contract/story_state.py
AI-Novel-Runtime/runtime/contract/production_state.py
AI-Novel-Runtime/runtime/serialize/contract_integration.py
AI-Novel-Runtime/runtime/serialize/production_hook.py
AI-Novel-Runtime/runtime/serialize/serial_hook_adapter.py
AI-Novel-Runtime/runtime/serialize/serial_with_contracts.py
AI-Novel-Runtime/runtime/serialize/stage_graph.py
AI-Novel-Runtime/runtime/serialize/workflow_scheduler.py
AI-Novel-Runtime/runtime/dashboard.py
AI-Novel-Runtime/runtime/dashboard/
AI-Novel-Runtime/quality-golden-set/metadata/index.json
AI-Novel-Runtime/quality-golden-set/metadata/w8-w9-ai-flow-report.md
novel-dushi/registry/story-bible/BIBLE-00001.yaml
novel-dushi/registry/derived/chapter-final/final-TASK-00001.json
docs/archive/2026-09-genre-work/P0关键问题最终修复报告.md
```

关键 commits：`334518d9`、`272a7507`、`60fdadae`、`6fa717cf`、`7f7cef26`。

---

# 25. Next Document Trigger

本报告之后，下一份正式资料应为：

```text
REFERENCE_ARCHITECTURE_STUDY.md
```

它不是“竞品列表”，而是逐项建立：

```text
Problem
Existing Solution
Evidence
What to Borrow
What NOT to Borrow
V2 Improvement
Architecture Decision
```

覆盖 Novel Studio AI、NovelForge、DOME、ConWriter、MAGNET/ATLAS、ConStory-Bench、Novelcrafter、Sudowrite、NovelAI，以及 Durable Workflow / Policy-as-Code / Provenance / Observability。

---

# 26. Closing Statement

ANovel V1 最有价值的成果，不是仓库里有多少文件，而是它已经用真实失败证明：

> **长篇 AI 小说生产的真正难点是 Genre、Canon、State、Contract、Workflow、Evaluation 和 Market Truth 的长期闭环。**

V2 不需要再次付同样的学费。

**END OF REPORT**
