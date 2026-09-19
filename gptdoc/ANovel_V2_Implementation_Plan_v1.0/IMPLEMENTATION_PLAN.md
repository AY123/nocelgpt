# ANovel V2 Engineering Implementation Plan & Milestone Execution Baseline

> **中文名**：ANovel V2 工程实施计划与里程碑执行基线  
> **Document ID**：PLAN-IMPLEMENTATION-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / EXECUTION BASELINE  
> **Authority**：IMPLEMENTATION-BASELINE  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `V1_FORENSIC_LESSONS.md`
> - `REFERENCE_ARCHITECTURE_STUDY.md`
> - `WEBNOVEL_MARKET_GENRE_RESEARCH.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
> - `CANONICAL_STATE_SPEC.md`
> - `MULTI_SOURCE_GENESIS_SPEC.md`
> - `PLANNING_CONTRACT_SPEC.md`
> - `CONTEXT_INTELLIGENCE_SPEC.md`
> - `PRODUCTION_WORKFLOW_SPEC.md`
> - `QUALITY_EVALUATION_REPAIR_SPEC.md`
> - `CORPUS_EVALUATION_LEARNING_SPEC.md`
> - `PLATFORM_OBSERVABILITY_SECURITY_SPEC.md`
>
> **Primary Goal**：把 ANovel V2 已冻结的架构规范转换成可直接执行的工程计划，明确实现顺序、依赖、任务拆分、里程碑、CI Gate、认证标准和禁止事项，确保项目从 Greenfield Repository 开始以最小可验证内核逐步增长，而不是再次演化为 V1 式边界失控的大型实验集合。

---

# 0. Execution Principle

ANovel V2 的实施策略：

> **Greenfield Rewrite + Selective Migration**

即：

```text
Code starts from zero
Knowledge does not
Failure evidence does not
Regression cases do not
Research does not
```

V1 只作为：

```text
Evidence
Regression source
Failure corpus
Selective data migration source
```

而不是 V2 的代码基线。

---

# 1. Implementation North Star

V2 第一个真正成功的状态不是：

```text
100 modules
50 agents
full web UI
20 genres
```

而是：

> **同一个内核可以稳定生产两个强对比 Genre 的连续 30 章，并在 Retry / Resume / Repair / Canon Commit 下保持 0 Canon Fork 与 0 Cross-Genre Hard Contamination。**

第一阶段 Anchor Genres：

```text
GPK-U01 urban.business.realistic
GPK-X01 fantasy.eastern.progression
```

这两个 Genre 差异足够大，最适合验证架构是否真的 Genre-neutral。

---

# 2. Global Delivery Strategy

实施顺序必须遵循：

```text
Governance
↓
Domain Types
↓
Canon
↓
Genre Kernel
↓
Planning / Contract
↓
Context
↓
Model Gateway
↓
Single Chapter Workflow
↓
Q0–Q3
↓
Repair
↓
10-Chapter Run
↓
30-Chapter Certification
↓
Genesis / Reference Intelligence
↓
Human Calibration
↓
100-Chapter Run
↓
Reader/Market Learning
```

禁止倒置：

```text
先做 UI
先做多 Agent
先做 30 GenrePack
先做 ReaderSim
先做大知识图谱
```

---

# 3. Repository Baseline

建议新仓库结构：

```text
anovel-v2/
├─ docs/
│  ├─ 00-governance/
│  ├─ 01-research/
│  ├─ 02-domain/
│  ├─ 03-canon/
│  ├─ 04-genre/
│  ├─ 05-genesis/
│  ├─ 06-planning/
│  ├─ 07-context/
│  ├─ 08-workflow/
│  ├─ 09-quality/
│  ├─ 10-learning/
│  ├─ 11-platform/
│  └─ adr/
│
├─ specs/
│  ├─ schemas/
│  ├─ genres/
│  ├─ policies/
│  ├─ benchmarks/
│  └─ fixtures/
│
├─ src/anovel/
│  ├─ domain/
│  ├─ canon/
│  ├─ genre/
│  ├─ planning/
│  ├─ contracts/
│  ├─ context/
│  ├─ intelligence/
│  ├─ workflow/
│  ├─ quality/
│  ├─ repair/
│  ├─ learning/
│  └─ platform/
│
├─ tests/
│  ├─ unit/
│  ├─ contract/
│  ├─ architecture/
│  ├─ integration/
│  ├─ regression/
│  ├─ certification/
│  └─ live_provider/
│
├─ migrations/
├─ scripts/
├─ pyproject.toml
├─ uv.lock / poetry.lock / requirements.lock
└─ .gitlab-ci.yml
```

---

# 4. Technology Baseline

Phase 0 推荐：

```text
Python 3.12+
Pydantic v2 / dataclasses
PostgreSQL
SQLAlchemy 2.x
Alembic
pytest
JSON Schema Draft 2020-12
OpenTelemetry-compatible tracing
```

模型 Provider：

```text
Provider Adapter
```

而不是业务代码直接依赖具体厂商。

---

# 5. Dependency Policy

所有 Runtime Dependency：

```text
exactly pinned in lockfile
```

禁止 V1 风格：

```text
openai>=1.0
httpx>=0.23
```

Production Release 必须绑定：

```text
dependency_lock_hash
```

---

# 6. Phase Map

正式实施分为：

```text
P0 — Repository & Governance
P1 — Narrative Kernel
P2 — Canon Kernel
P3 — Genre Kernel
P4 — Planning & Contracts
P5 — Context & Model Gateway
P6 — Single-Chapter Production
P7 — Quality & Repair
P8 — Dual-Genre 10-Chapter Certification
P9 — 30-Chapter Certification
P10 — Genesis & Reference Intelligence
P11 — Human Calibration / Learning
P12 — 100-Chapter Reliability
P13 — Reader / Market Feedback
P14 — 300+ Chapter / Million-word Evolution
```

---

# 7. P0 — Repository & Governance

## Goal

建立一个从第一天就不能轻易破坏架构边界的 Greenfield repo。

## Deliverables

```text
PROJECT_CONSTITUTION
Architecture package boundaries
ADR mechanism
Schema registry
CI skeleton
Security scan
Dependency lock
Architecture fitness test harness
```

## Tasks

### P0-T01 Repository Bootstrap

- Python package
- formatter/linter/type checker
- pytest
- PostgreSQL test fixture
- migrations
- basic CI

### P0-T02 Normative Documentation Import

把已冻结文档放入：

```text
docs/
```

并形成：

```text
NORMATIVE_INDEX.md
```

### P0-T03 Architecture Fitness Harness

第一批规则：

```text
Writer cannot import Canon write API
Reference cannot import Canon write API
Provider SDK cannot enter domain package
Only CanonCommitService advances Canon Head
Only WorkflowStateService advances ProductionState
```

### P0-T04 Security Baseline

- secret scan
- dependency scan
- log sanitizer
- test fixture secret detection

## Exit Gate

```text
P0-GATE:
  CI green
  lockfile committed
  no secret
  normative index complete
  architecture fitness enforced
```

---

# 8. P1 — Narrative Kernel

## Goal

实现与 Genre 无关的最小 Narrative Domain。

## Implement

```text
EntityId
NarrativeEntity
Character
Relationship
Knowledge
Goal
Location
Faction
Object
Event
Timeline
Promise
FactClaim
FactMutability
NarrativeDelta
```

## Do NOT Implement Yet

```text
realm
equity
box_office
reader simulation
```

这些属于 extension。

## Critical Tests

```text
alias resolution
unknown != no_change
knowledge boundary
event immutability semantics
fact mutability
relationship first-class
```

## Exit Gate

能够表示一个纯现实测试故事：

```text
人物
关系
地点
事件
知识变化
Promise
Delta
```

且不需要 Genre-specific field。

---

# 9. P2 — Canon Kernel

## Goal

建立唯一可信 Narrative Truth。

## Implement

```text
CanonHead
CanonCommit
CanonEvent
CanonSnapshot
ChangeSet
CommitPermit
CanonCommitService
SnapshotProjector
Idempotency
CAS
Retcon skeleton
```

## Database Tables

最低：

```text
canon_heads
canon_commits
canon_events
canon_snapshots
change_sets
commit_permits
```

## Critical Tests

```text
draft cannot write canon
missing permit blocks
stale parent blocks
retry returns same commit
two concurrent commits only one wins
snapshot rebuild equals stored
wrong text hash blocks
```

## Exit Gate

用 synthetic chapter 完成：

```text
Delta
→ ChangeSet
→ Permit
→ Commit
→ Snapshot N+1
```

并通过 kill-after-commit recovery。

---

# 10. P3 — Genre Kernel

## Goal

让 Runtime 真正具备 Genre boundary。

## Implement

```text
GenreFamily
GenreProfile
GenrePack Loader
Genre Constitution
Hard Rule Engine
Genre Extension Registry
GenrePack hash/version
Fusion skeleton
```

## First Packs

只实现：

```text
urban.business.realistic
fantasy.eastern.progression
```

## Urban Extensions

```text
Company
Equity
Cash
Market
Product
Career
Reputation
```

## Fantasy Extensions

```text
Realm
Technique
Resource
Artifact
Faction Power
```

## Critical Cross-Genre Tests

Urban：

```text
cultivation → hard fail
magic → hard fail
illegal money transition → hard fail
```

Fantasy：

```text
illegal realm jump → hard fail
ability without prerequisite → hard fail
```

## Exit Gate

两个 GenrePack 使用同一 Canon/Narrative Kernel。

---

# 11. P4 — Planning & Contracts

## Goal

把未来意图转换成可验证执行契约。

## Implement

```text
SeriesVision
ArcPlan
ChapterPlan
ScenePlan
StoryContract
ArcContract
ChapterContract
SceneContract
ContractCompiler
PlanDiff
Invalidation
```

## Hard Requirement

禁止任何：

```text
protagonist_name = "..."
```

项目特定硬编码。

## Tests

```text
missing contract blocks
stale contract blocks
required transition
forbidden transition
protected fact
knowledge boundary
contract hash
```

## Exit Gate

当前 Scene Contract 可从：

```text
Canon + Genre + Plan
```

自动编译。

---

# 12. P5 — Context & Model Gateway

## Goal

让所有模型调用共享统一、可审计的 Context semantics。

## Implement

```text
ContextRequest
ContextItem
ContextArtifact
ContextCompiler
ContextBudget
RoleRegistry
ModelPolicy
ModelGateway
ProviderAdapter
```

## Required Roles

```text
PLANNER
WRITER
EXTRACTOR
REVIEWER
REPAIRER
```

## Critical Tests

```text
mandatory facts never trimmed
raw reference absent from writer
extractor gets aliases
stale contract context blocked
branch/project isolation
```

## Live Provider Test

至少两个 Provider/Model route 中有一个真实调用测试。

目的：

```text
detect real wiring/provider failure
```

而不是只 Mock。

---

# 13. P6 — Single-Chapter Production

## Goal

第一次完成真实生产闭环。

## Workflow

```text
LOAD_CANON
→ COMPILE_CONTRACT
→ COMPILE_CONTEXT
→ GENERATE
→ EXTRACT_DELTA
→ Q0-Q3
→ COMMIT_PERMIT
→ CANON_COMMIT
→ PROJECT
```

## Stage Engine

Phase 1 只实现最小 durable engine：

```text
DB-backed state
checkpoint
retry
idempotency
resume
```

不要立即引入复杂集群。

## Required Failure Tests

```text
provider 503
timeout
process restart
crash before commit
crash after commit
stale parent
```

## Exit Gate

连续自动生产：

```text
3 chapters
```

0 Canon fork。

---

# 14. P7 — Quality & Patch Repair

## Goal

把“生成即接受”升级为可诊断质量闭环。

## First Scope

实现：

```text
Q0
Q1
Q2
Q3
Q4 basic
Q5 basic
Patch-first Repair
QualityAggregator
```

暂不把 Q6 商业预测作为 Gate。

## Repair

必须：

```text
Diagnosis
→ RepairPlan
→ Patch
→ New Candidate
→ Re-extract
→ Revalidate
```

## Exit Gate

至少建立 20 个 synthetic / regression defects，并验证 Repair 不破坏 Protected Facts。

---

# 15. P8 — Dual-Genre 10-Chapter Certification

## Goal

首次验证架构，而不是单个功能。

运行两个项目：

```text
Urban Business — 10 chapters
Eastern Fantasy — 10 chapters
```

## Required

```text
same kernel
same workflow
same canon
same context compiler
same quality stack
different GenrePack
```

## Metrics

```text
hard violation count
genre contamination
canon conflict
repair rate
workflow retry
cost/chapter
context size
```

## Pass Conditions

至少：

```text
0 unauthorized cross-genre hard contamination
0 duplicate commit
0 Canon fork
0 stale contract commit
0 unrecoverable workflow crash
```

---

# 16. P9 — 30-Chapter Certification

## Goal

证明系统不只会写 3–10 章。

每个 Anchor Genre：

```text
30 chapters
```

## Fault Injection

必须插入：

```text
provider transient failure
manual pause
worker restart
budget pause
stale contract
repair loop
commit conflict
```

## Narrative Evaluation

检查：

```text
genre drift
promise debt
engine repetition
character flattening
progression inflation
```

## Certification Status

通过后：

```text
GPK-U01 = CERTIFIED_30
GPK-X01 = CERTIFIED_30
```

满足更高 Gate 后才：

```text
PRODUCTION_READY
```

---

# 17. P10 — Genesis & Reference Intelligence

## Goal

在生产内核已稳定后，再实现复杂开书能力。

## Implement

```text
GenesisIntake
BookNarrativeProfile
ReferenceEvidencePack
OriginalityReport
GenesisCandidate
GenesisTournament
GenesisSpec
GenesisCommit
```

## Modes

```text
IDEA_DRIVEN
REFERENCE_GUIDED
HYBRID
CORPUS_MARKET_DRIVEN
```

全部输出同一：

```text
GenesisSpec
```

## Critical Safety

```text
raw reference not in Writer
reference evidence cannot write Canon
signature pattern collision check
```

---

# 18. P11 — Human Calibration & Learning

## Goal

从 AI 自评进入真实校准。

## Implement

```text
CorpusRegistry
GoldenSet
RegressionSet
BenchmarkRegistry
ExperimentDefinition
Pairwise Human Evaluation
CalibrationReport
PromotionDecision
LearningEvent
```

## First Benchmark

比较：

```text
Writer Prompt A vs B
or
Model A vs B
```

使用：

```text
blind pairwise
```

而不是绝对 9.x 分。

---

# 19. P12 — 100-Chapter Reliability

## Goal

验证长篇 memory/state/context/engine durability。

运行至少：

```text
1 Anchor Genre × 100 chapters
```

优先：

```text
urban.business.realistic
```

或两者中更稳定者。

## Measure

```text
Canon size growth
context retrieval quality
relationship continuity
knowledge leakage
promise debt
repair rate
cost trend
engine fatigue
```

## Exit Gate

不能依赖手工频繁修状态才能继续。

---

# 20. P13 — Reader / Market Feedback

## Goal

引入真实 Q8 signal。

## Implement

```text
ReaderSignal
MarketSignal
cohort
exposure
calibration
future planning input
```

## Strict Rule

真实市场数据：

```text
may calibrate
may replan future
cannot mutate past Canon
```

---

# 21. P14 — 300+ Chapter / Million-word Evolution

只有在 P12/P13 成功后进入。

研究：

```text
300 chapters
multi-volume
late-stage planning
large Canon
cost control
engine renewal
retcon management
reader signal feedback
```

百万字是：

```text
certification target
```

不是 Day-1 feature。

---

# 22. Sprint Strategy

建议每个 Phase 拆：

```text
S0 Contract/Schema
S1 Core implementation
S2 Integration
S3 Regression
S4 Certification
```

对关键 Phase 不允许：

```text
Implementation done
tests later
```

---

# 23. Task Template

所有 Task 使用统一格式：

```text
Task ID
Goal
Inputs
Normative Specs
Files/Modules
Dependencies
Implementation Rules
Acceptance Criteria
Tests
Artifacts
Out of Scope
Risks
DoD
```

---

# 24. AI Agent Execution Template

给 Claude/GPT/Codex 的每个 Task 前置：

```text
1. Read PROJECT_CONSTITUTION.md.
2. Read task-relevant normative specs.
3. Identify affected ADRs and invariants.
4. Inspect existing implementation before editing.
5. Do not create new authority boundaries without ADR.
6. Production paths are fail-closed.
7. Draft/Reference/Judge cannot write Canon.
8. Every persistent artifact needs producer, consumer, lifecycle, authority, provenance.
9. Run required tests and architecture fitness.
10. Report conflicts instead of silently violating the specs.
```

---

# 25. Priority Classification

```text
P0 = blocks architectural correctness
P1 = required for milestone
P2 = valuable after milestone
P3 = defer
```

---

# 26. P0 Engineering Issues

From Day 1：

```text
secret leakage
second Canon path
missing Contract pass
direct Writer Canon write
stale parent commit
duplicate commit retry
cross-project state leak
unversioned schema/policy
```

任何一个出现：

```text
STOP FEATURE WORK
```

先 closure。

---

# 27. CI Pipeline Baseline

建议：

```text
Stage 1 — Static
Stage 2 — Unit
Stage 3 — Contract/Schema
Stage 4 — Architecture Fitness
Stage 5 — Security
Stage 6 — PostgreSQL Integration
Stage 7 — Deterministic E2E
Stage 8 — Genre Certification Smoke
Stage 9 — Live Provider (controlled)
```

---

# 28. CI Hard Gates

Production branch：

```text
allow_failure: false
```

至少覆盖：

```text
schema validation
architecture fitness
secret scan
unit tests
contract tests
PostgreSQL integration
Canon concurrency/idempotency
```

---

# 29. Live Provider CI

真实 Provider Test 不建议每个 commit 全量执行。

可：

```text
scheduled
manual protected
nightly
release gate
```

但不能永远没有。

---

# 30. Database Strategy

建议：

```text
PostgreSQL from early phase
```

不要先设计：

```text
in-memory truth
then later migrate
```

Canon/Workflow concurrency 太关键。

---

# 31. Migration Discipline

每个 Migration：

```text
forward
test
rollback/forward-fix guidance
real PostgreSQL gate
```

不能只 SQLite。

---

# 32. Domain Package Rules

严格层级：

```text
domain
↓
application/use cases
↓
infrastructure
```

Domain 不依赖：

```text
Provider SDK
FastAPI
SQLAlchemy model
Workflow engine
```

---

# 33. Provider Abstraction

业务代码依赖：

```text
ModelRole
ModelCapability
ModelGateway
```

不依赖：

```text
OpenAIClient
AnthropicClient
```

---

# 34. Workflow Engine Choice

P6 前：

```text
不决定大型 distributed workflow framework
```

先实现语义。

如果未来满足：

```text
multiple workers
long human waits
large scale
complex recovery
```

再评估 Temporal。

---

# 35. Avoid Premature Agent Architecture

P0–P9 禁止：

```text
persistent agent per character
agent swarm
agent society
```

Character Reasoning 是：

```text
stateless worker over authoritative Character State
```

---

# 36. Avoid Premature Knowledge Graph

Phase 1：

```text
relational + typed relationships
```

足够。

图数据库等到：

```text
real query bottleneck
```

再 ADR。

---

# 37. UI Timing

P0–P8：

```text
CLI / API / internal debug UI
```

即可。

大型 Author Studio UI：

```text
after stable production kernel
```

---

# 38. Minimum Debug UI

值得早做：

```text
Canon Inspector
Contract Inspector
Context Inspector
Workflow Run Inspector
Quality Findings
Lineage Viewer
```

不是漂亮，而是可调试。

---

# 39. Observability From Day 1

不能等 Production 后再补。

最少：

```text
run_id
stage_id
trace_id
model usage
cost
error code
```

---

# 40. Security From Day 1

最低：

```text
secret scan
log sanitizer
env secret injection
dependency lock
```

---

# 41. Documentation Rule

每实现一个 Domain：

```text
normative spec
code
tests
examples
migration
```

保持同步。

---

# 42. ADR Gate

必须 ADR 的变化：

```text
new top-level domain
new Canon store
new workflow engine
new authority boundary
new Genre hard semantics
new persistent memory system
```

---

# 43. Definition of Production-Ready

一个模块“可运行”不等于 Production Ready。

必须有：

```text
schema
tests
consumer
provenance
observability
failure semantics
migration
security
```

---

# 44. Definition of Genre Support

“有 GenrePack 文件”不算支持。

至少：

```text
certification
cross-contamination test
10-chapter run
30-chapter run
```

---

# 45. Definition of Model Support

“API 调通”不算支持。

至少：

```text
structured output
failure classification
retry
usage/cost
fallback semantics
live-provider test
```

---

# 46. Definition of Repair Support

“可以叫模型改一下”不算 Repair。

必须：

```text
Diagnosis
RepairPlan
ProtectedFacts
AllowedDelta
NewHash
Revalidation
Regression detection
```

---

# 47. Definition of Learning Support

“模型自我反思”不算学习。

必须：

```text
dataset
experiment
baseline
variant
evidence
promotion
rollback
```

---

# 48. Milestone M0 — Constitution & Repo

Pass：

```text
repo bootstrapped
CI green
normative docs imported
secret scan
lockfile
architecture rules
```

---

# 49. Milestone M1 — Narrative Kernel

Pass：

```text
core domain implemented
stable entity ID
alias resolution
knowledge boundary
NarrativeDelta
```

---

# 50. Milestone M2 — Canon Kernel

Pass：

```text
atomic commit
CAS
idempotency
snapshot rebuild
retcon skeleton
```

---

# 51. Milestone M3 — Dual Genre Kernel

Pass：

```text
Urban + Fantasy
same core
hard contamination blocked
```

---

# 52. Milestone M4 — Single Chapter End-to-End

Pass：

```text
Plan
Contract
Context
Writer
Extractor
Q0-Q3
Commit
```

---

# 53. Milestone M5 — Repair

Pass：

```text
diagnosis
patch-first
revalidation
```

---

# 54. Milestone M6 — 10-Chapter Certification

Pass：

```text
2 genres × 10 chapters
fault injection
0 Canon fork
```

---

# 55. Milestone M7 — 30-Chapter Certification

Pass：

```text
2 genres × 30 chapters
genre stability
workflow durability
```

---

# 56. Milestone M8 — Multi-source Genesis

Pass：

```text
Idea
Reference
Hybrid
Corpus
→ GenesisSpec
```

---

# 57. Milestone M9 — Human Calibration

Pass：

```text
GoldenSet
blind pairwise
holdout
promotion gate
```

---

# 58. Milestone M10 — 100-Chapter Reliability

Pass：

```text
100 chapter continuous production
```

---

# 59. Milestone M11 — Real Reader Signal

Pass：

```text
ReaderSignal
MarketSignal
Q6 calibration
```

---

# 60. Milestone M12 — 300+ Chapter Reliability

Pass：

```text
late-stage durability
```

---

# 61. Release Strategy

版本建议：

```text
v0.1 narrative kernel
v0.2 canon kernel
v0.3 genre kernel
v0.4 single chapter
v0.5 repair
v0.6 10ch
v0.7 30ch
v0.8 genesis/reference
v0.9 calibration
v1.0 100ch certified
```

---

# 62. Main Branch Policy

建议：

```text
main always releasable enough for current milestone
```

不要长期堆积：

```text
half-integrated architecture
```

---

# 63. Feature Branch Rule

每个 Task：

```text
small enough to review
```

避免“一次提交 100 个模块”。

---

# 64. Test Pyramid

建议：

```text
many unit
many contract
strong integration
small but mandatory E2E
controlled live-provider
```

---

# 65. Regression Pyramid

永久 Regression 包含：

```text
V1 failures
new production failures
security incidents
certification failures
```

---

# 66. V1 Assets to Migrate First

优先迁移：

```text
failure cases
golden metadata governance
real-provider failure scenarios
state/contract/canon lessons
genre contamination examples
```

不是迁移：

```text
runtime/serialize god package
duplicate orchestration
hardcoded character logic
```

---

# 67. V1 Code Migration Rule

默认：

```text
do not copy
```

只有满足：

```text
clear boundary
tests
no legacy coupling
matches V2 semantics
```

才允许 selective port。

---

# 68. Data Migration

可以迁移：

```text
curated Golden Set metadata
approved reference metadata
regression fixtures
```

必须：

```text
new schema validation
new provenance
```

---

# 69. Security P0 Before Migration

任何历史资料中疑似 secret：

```text
do not migrate until sanitized
```

---

# 70. Implementation Risk Register

最高风险：

```text
RISK-01 architecture overbuilding
RISK-02 semantic schema too generic
RISK-03 LLM judge over-authority
RISK-04 GenrePack becoming prompt pack
RISK-05 Canon duplicated in projections
RISK-06 workflow framework owning truth
RISK-07 too many genres too early
RISK-08 insufficient real-provider testing
RISK-09 weak human calibration
RISK-10 reference copyright leakage
```

---

# 71. Anti-overengineering Rules

P0–P9 不做：

```text
microservices
Kafka
Kubernetes requirement
graph database requirement
multi-region
agent swarm
real-time trend scraping
30 genre packs
complex WYSIWYG editor
```

除非有真实瓶颈。

---

# 72. Performance Strategy

先测：

```text
correctness
latency
cost
```

不提前优化。

---

# 73. Cost Targets

早期记录：

```text
cost per chapter
cost by stage
repair cost
quality cost
```

先基线化，不武断设商业 KPI。

---

# 74. Quality Targets

早期硬指标优先：

```text
0 duplicate commit
0 stale commit
0 cross-project leak
0 cross-genre hard contamination
0 missing contract pass
```

语义质量后续人工校准。

---

# 75. 30-Chapter Certification Report

每个 Anchor Genre 输出：

```text
run fingerprint
genre pack
model policy
total chapters
hard violations
repairs
failures
retries
cost
human sample review
drift
promise debt
engine repetition
```

---

# 76. Certification Failure

任何重大失败：

```text
do not hide
```

进入：

```text
Failure Corpus
Regression Set
Next Sprint
```

---

# 77. Production Readiness Gate

P9 后仍不自动宣布商业 Production。

至少还需要：

```text
security
backup restore
human calibration
real provider stability
operational runbook
```

---

# 78. Sprint Closure Template

每 Sprint 必须报告：

```text
completed tasks
changed files
tests
CI
known risks
deferred work
architecture deviations
new regression cases
```

---

# 79. Milestone Closure Template

必须：

```text
Acceptance Criteria
Evidence
Run IDs
Test Results
Open Risks
Go / No-Go
```

---

# 80. No Self-certification by Code Generator

实现 Agent 不能只凭：

```text
"I completed everything"
```

宣告关闭。

必须有：

```text
CI evidence
artifact evidence
runtime evidence
```

---

# 81. Evidence-based Closure

Task 状态：

```text
OPEN
IN_PROGRESS
IMPLEMENTED
VERIFIED
CLOSED
```

`IMPLEMENTED != CLOSED`

---

# 82. Close Criteria

只有：

```text
code
tests
CI
acceptance evidence
```

全部通过才能：

```text
CLOSED
```

---

# 83. First 20 Engineering Tasks

建议启动顺序：

```text
V2-001 Repository bootstrap
V2-002 Normative docs index
V2-003 Architecture fitness harness
V2-004 Secret/dependency CI
V2-005 Core Entity IDs & aliases
V2-006 Character/Relationship/Knowledge
V2-007 Event/Timeline/Promise
V2-008 NarrativeDelta
V2-009 Canon tables & repository
V2-010 CanonCommitService
V2-011 Idempotency/CAS
V2-012 Snapshot rebuild
V2-013 GenreProfile/Pack loader
V2-014 Genre hard policy engine
V2-015 Urban Business extension
V2-016 Eastern Fantasy extension
V2-017 Contract Compiler
V2-018 Context Compiler
V2-019 Model Gateway
V2-020 Single Chapter Workflow
```

---

# 84. Tasks 21–40

```text
V2-021 Extractor
V2-022 Q0 validators
V2-023 Q1 Canon validators
V2-024 Q2 Genre validators
V2-025 Q3 Transition validators
V2-026 CommitPermit integration
V2-027 Workflow retry/checkpoint
V2-028 Kill/restart harness
V2-029 QualityAggregator
V2-030 Diagnosis
V2-031 Patch Repairer
V2-032 Repair regression
V2-033 3-chapter smoke
V2-034 Urban 10ch certification
V2-035 Fantasy 10ch certification
V2-036 Fault injection
V2-037 Context inspector
V2-038 Canon inspector
V2-039 Lineage inspector
V2-040 30ch certification runner
```

---

# 85. Tasks 41–60

```text
V2-041 Idea Genesis
V2-042 Reference ingestion
V2-043 BookNarrativeProfile
V2-044 ReferenceEvidencePack
V2-045 Originality firewall
V2-046 Genesis Tournament
V2-047 GenesisSpec
V2-048 GenesisCommit
V2-049 Corpus Registry
V2-050 GoldenSet migration
V2-051 RegressionSet migration
V2-052 ExperimentDefinition
V2-053 Benchmark runner
V2-054 Pairwise evaluator
V2-055 Human evaluation ingest
V2-056 Calibration
V2-057 Promotion gate
V2-058 Backup/restore
V2-059 Release manifest
V2-060 100ch runner
```

---

# 86. Critical Path

真正 Critical Path：

```text
V2-005
→ V2-008
→ V2-009
→ V2-010
→ V2-013
→ V2-017
→ V2-018
→ V2-019
→ V2-020
→ V2-021
→ V2-022..025
→ V2-026
→ V2-033
→ V2-034/035
→ V2-040
```

任何不在这条链的功能，早期都要质疑是否应该先做。

---

# 87. Recommended Team/Agent Roles

即使全程 AI 搭建，也建议职责分离：

```text
Architecture Agent
Implementation Agent
Test/CI Agent
Security Agent
Reviewer Agent
Benchmark Agent
```

可以由同一模型承担不同 Session，但角色职责要分离。

---

# 88. AI Handoff Contract

Task 交给另一个 AI 时，必须附：

```text
Task Spec
Relevant Normative Docs
Current Commit SHA
Affected Modules
Acceptance Criteria
Tests
Out of Scope
```

---

# 89. Context Size for Coding Agents

不要每次把全部 14 份规范塞进 Prompt。

通过：

```text
Normative Index
Task-to-Spec Mapping
```

只给任务相关文档。

---

# 90. Task-to-Spec Mapping Example

`V2-010 CanonCommitService`：

```text
PROJECT_CONSTITUTION
NARRATIVE_DOMAIN_SPEC
CANONICAL_STATE_SPEC
PLATFORM_OBSERVABILITY_SECURITY_SPEC
```

`V2-018 ContextCompiler`：

```text
CONTEXT_INTELLIGENCE_SPEC
PLANNING_CONTRACT_SPEC
CANONICAL_STATE_SPEC
GENRE_INTELLIGENCE_SPEC
```

---

# 91. Documentation Linter

后期可实现：

```text
Task references valid ADR/spec
schema refs exist
version refs exist
```

---

# 92. Schema Registry

所有 JSON Schema：

```text
stable ID
version
owner
consumer
```

必须登记。

---

# 93. Policy Registry

同理：

```text
GenrePolicy
ContextPolicy
QualityPolicy
WorkflowPolicy
PlatformPolicy
```

---

# 94. Runtime Config

Runtime Config 只能选择：

```text
registered versions
```

不能 arbitrary JSON bypass。

---

# 95. Release Reproducibility

Release 必须能重建：

```text
code
dependencies
schemas
policies
workflow
genre packs
```

---

# 96. P0/P1 Bug Handling

一旦出现：

```text
Canon corruption
security leak
duplicate commit
cross-project leak
hard gate bypass
```

立即：

```text
freeze feature work
fix
add regression
verify
```

---

# 97. Architecture Drift Review

每 2–3 Milestone 做一次：

```text
Architecture Review
```

检查：

```text
new duplicate authority?
god package?
consumerless artifact?
hidden bypass?
```

---

# 98. God Package Threshold

不是用文件数硬判断。

但当一个 package 同时负责：

```text
workflow
quality
serialization
experiments
publishing
calibration
```

必须拆界。

---

# 99. Consumer Rule

每个新 persistent artifact 必须回答：

```text
Who produces it?
Who consumes it?
Who owns it?
When stale?
When deleted?
```

回答不了：

```text
do not add
```

---

# 100. Exit From Architecture Phase

到本计划完成为止：

> **ANovel V2 Architecture Preparation Phase is CLOSED.**

下一步不再继续无止境写前置规范。

正确动作：

```text
Create V2 Repository
Import Normative Specs
Start V2-001
```

---

# 101. Final Implementation Recommendation

第一批实际编码必须严格收敛：

```text
M0 Repo/Governance
M1 Narrative Kernel
M2 Canon
M3 Dual Genre
M4 Single Chapter E2E
M5 Repair
M6 10ch
M7 30ch
```

在 M7 以前：

> 不追求“系统功能很多”。

只追求：

> **核心链路可信、可恢复、可验证、双 Genre 不串、30 章不崩。**

这是 V2 与 V1 最大的工程策略区别。

---

# 102. Immediate Next Action

实施阶段的第一份执行文档应是：

# `PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md`

它应该只做：

```text
repo skeleton
dependency lock
normative docs import
architecture fitness
security gates
PostgreSQL test harness
CI baseline
```

并生成首批 Task：

```text
V2-001
V2-002
V2-003
V2-004
```

完成 P0 并获得绿色 CI 后，再进入 Narrative Kernel。

**END OF IMPLEMENTATION PLAN**
