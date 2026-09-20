# ANovel V2 Context Compiler & Model Intelligence Boundary Specification

> **中文名**：ANovel V2 上下文编译器与模型智能边界规范  
> **Document ID**：SPEC-CONTEXT-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
> - `CANONICAL_STATE_SPEC.md`
> - `MULTI_SOURCE_GENESIS_SPEC.md`
> - `PLANNING_CONTRACT_SPEC.md`
>
> **Primary Goal**：定义 ANovel V2 中所有模型调用之前的统一 Context Compilation 机制，使模型上下文不再是临时拼接 Prompt，而是受 Authority、任务角色、Canon、Contract、Knowledge Boundary、Token Budget 和 Provenance 共同约束的正式生产 Artifact。

---

# 0. Normative Summary

ANovel V2 Context Intelligence MUST 满足：

1. **Context is compiled, not concatenated ad hoc.**
2. **Every model call that can affect production MUST bind a ContextArtifact.**
3. **ContextArtifact is immutable and hash-addressed once issued.**
4. **Authority priority is explicit.**
5. **Canon and Contract outrank Reference/Market/Model-generated notes.**
6. **Task role determines what context is visible.**
7. **Knowledge Boundary applies to character-grounded generation.**
8. **Raw reference text is excluded from production Writer by default.**
9. **Mandatory facts cannot be trimmed for token budget.**
10. **Token trimming must be deterministic enough to audit.**
11. **Context selection reasons are persisted.**
12. **Context omission decisions are inspectable.**
13. **Generation, review and repair of the same candidate SHOULD bind compatible Context lineage.**
14. **ContextArtifact does not become Canon.**
15. **Long-term memory is retrieved from authoritative/derived stores, not hidden model memory.**
16. **Provider-specific message formatting is infrastructure concern.**
17. **Prompt template, ContextArtifact and ModelPolicy are separate versioned assets.**
18. **Unknown or stale context is surfaced explicitly.**
19. **Context contamination across projects/branches is a hard failure.**
20. **Context compilation itself is observable and testable.**

---

# 1. Why Context Is a First-Class Artifact

V1 和大量 AI 写作工具容易走向：

```text
Story Bible
+ 最近几章
+ 人物卡
+ Prompt
+ 随手拼接若干检索结果
→ LLM
```

问题：

- 不知道模型实际看到了什么；
- 不知道哪些信息被裁掉；
- Reviewer 和 Writer 可能看到不同事实；
- Reference 原文可能意外进入正文；
- 旧 Plan / stale Snapshot 可能混入；
- Token 不够时随意删除关键事实；
- 同一任务重跑无法解释为什么结果不同；
- Provider 切换时上下文语义改变。

V2 必须把 Context 变成正式 Artifact。

---

# 2. ContextArtifact

`ContextArtifact` 是一次模型任务使用的完整语义上下文清单。

至少包含：

```text
context_id
project_id
branch_id
task_role
task_id
canon_head_hash
contract_hash
genre_pack_hash
planning_refs
items[]
token_budget
selection_policy_version
prompt_template_ref
model_policy_ref
context_hash
created_at
```

---

# 3. ContextItem

每个 ContextItem 必须声明：

```text
source_ref
source_type
authority
priority
mandatory
relevance
recency
risk
token_cost
inclusion_reason
content_hash
```

---

# 4. Context Authority Priority

默认优先级：

```text
T0 Project Constitution
T1 Genre Constitution / Hard Policy
T2 Current Canon
T3 Current Contract
T4 Current Active Plan
T5 Required Recent Narrative Context
T6 Derived Views / Summaries
T7 Approved Reference Evidence
T8 Market Evidence
T9 Diagnostic / Model Notes
```

### Rule

低 Authority 内容不能覆盖高 Authority。

---

# 5. Role-specific Context

不同 Worker 不应该看到相同全部信息。

---

## 5.1 Writer Context

Writer 主要需要：

```text
Genre Constitution
Scene/Chapter Contract
Relevant Canon
Character Knowledge Boundary
Current Location / World Rules
Recent Local Context
Open Promise relevant to scene
Style/Tone policy
Allowed abstract reference evidence
```

默认不需要：

```text
full market report
full reference text
all historical chapters
all diagnostics
all alternate plans
```

---

## 5.2 Planner Context

Planner 需要：

```text
GenesisSpec
SeriesVision
Canon
Open Promises
Current Arc/Volume
Engine state
Fatigue signals
Reader/Market evidence(optional)
Reference Evidence(optional)
```

Planner 可以看到比 Writer 更广的未来与市场信息。

---

## 5.3 Reviewer Context

Reviewer 应看到：

```text
same accepted Canon parent
same Contract
same GenrePack
candidate text
validation criteria
```

### Critical

Reviewer SHOULD NOT secretly use a newer Canon than Writer.

否则：

```text
reviewing against future state
```

---

## 5.4 Extractor Context

Extractor 需要：

```text
candidate text
entity roster
aliases
ontology
current Canon relevant subset
extension schemas
```

特别需要：

```text
entity canonical names + aliases
```

避免 V1 大量 phantom new entities。

---

## 5.5 Repairer Context

Repairer 需要：

```text
original candidate
validation findings
protected facts
allowed patch scope
Contract
relevant Canon
```

不应默认获得全新自由写作 Prompt。

---

## 5.6 Judge Context

Judge 只获得：

```text
task-appropriate evidence
```

并标记：

```text
evaluation authority = diagnostic
```

---

# 6. Context Compiler

统一接口：

```text
compile_context(ContextRequest)
→ ContextArtifact
```

ContextRequest：

```text
project
branch
task_role
task_id
canon_parent
contract
plan
token_budget
policy
```

---

# 7. Compilation Pipeline

建议：

```text
Load fixed authorities
↓
Resolve project/branch scope
↓
Load Canon parent
↓
Load frozen Contract
↓
Select required Plan
↓
Resolve task entities
↓
Retrieve relevant state
↓
Apply knowledge boundary
↓
Select recent narrative context
↓
Inject allowed evidence
↓
Apply authority ranking
↓
Apply token budget
↓
Validate mandatory coverage
↓
Hash
↓
Issue ContextArtifact
```

---

# 8. Mandatory Context

不能因为 Token Budget 被裁掉：

```text
Genre hard rules
Contract required transitions
Contract forbidden transitions
Protected facts
Required entity identity
Critical world law
Character knowledge boundary
Canon parent identity/hash
```

---

# 9. Optional Context

可以根据预算裁剪：

```text
older summaries
low-relevance lore
secondary reference patterns
market notes
non-critical style examples
```

---

# 10. Token Budget

ContextBudget 至少分配：

```text
system_policy
genre
contract
canon
recent_context
character_state
reference_evidence
style
response_reserve
```

不能：

```text
用满输入 token，导致输出空间不足
```

---

# 11. Reserved Output Tokens

必须预留：

```text
response_reserve
```

不同 Role 不同。

例如 Writer > Reviewer > Extractor。

---

# 12. Token Budget Policy

示例：

```yaml
writer:
  mandatory_min_ratio: 0.35
  canon_max_ratio: 0.25
  recent_context_max_ratio: 0.20
  reference_max_ratio: 0.05
  output_reserve_ratio: 0.25
```

比例是 Policy，不是硬编码 Domain。

---

# 13. Context Selection Score

可使用：

```text
authority
+
mandatory
+
task relevance
+
entity relevance
+
recency
+
risk
+
promise relevance
```

综合排序。

### Important

Selection score 是检索策略，不是 narrative truth。

---

# 14. Relevance

Relevance 可以来自：

```text
exact entity match
graph proximity
current contract reference
semantic retrieval
recent activity
open promise link
```

---

# 15. Recent Context

Writer 通常需要：

```text
previous scene ending
previous chapter ending
recent accepted chapter summaries
```

而不是完整前 100 章。

---

# 16. Long-term Context

Long-term 使用：

```text
Canon Views
Promise Ledger
Relationship State
Character Knowledge
World Rules
```

不依赖全文。

---

# 17. Context Window Is Not Memory

模型长 Context：

```text
does not equal
```

长期 Memory。

即使模型支持百万 token，也不应把整个小说全文当 Canon。

---

# 18. Derived Summary

Summary 是：

```text
DERIVED
```

如果与 Canon 冲突：

```text
Canon wins
```

Summary 必须有：

```text
source range
source hash
head hash
```

---

# 19. Summary Staleness

如果 Canon Head 改变且影响其来源：

```text
summary = stale
```

不能继续注入。

---

# 20. Knowledge Boundary Projection

对每个 Scene participant 编译：

```text
known
believed
suspected
unknown
secret_to_them
```

Writer 可以看到完整控制信息，但必须明确：

```text
character may not know X
```

或者采用 role-separated generation。

---

# 21. Character-grounded Subcontext

可为每个角色生成：

```text
CharacterPerspectiveContext
```

用于 Character Reasoner。

它只包含该角色合理可知内容。

---

# 22. Writer Global vs Character Perspective

Writer 是全知生产 Worker，可以知道：

```text
秘密真相
```

但 Contract 必须约束：

> 不能让当前角色泄漏不该知道的信息。

---

# 23. Reference Evidence Injection

允许 Writer 使用：

```text
abstract pattern
```

例如：

```text
本场景节奏目标：短冲突 → 信息反转 → 状态变化
```

不允许：

```text
参考书原句/原场景连续细节
```

---

# 24. Reference Injection Levels

建议：

```text
NONE
ABSTRACT_ONLY
DIMENSION_ONLY
ANALYSIS_ONLY
```

Writer 默认：

```text
ABSTRACT_ONLY
```

---

# 25. Market Evidence Injection

Writer 通常：

```text
NONE
```

Planner/Genesis：

```text
may use
```

避免 Writer 直接“为了市场”破坏当前小说。

---

# 26. Style Context

Style 可以来自：

```text
Project Style Spec
Genre tone
approved style constraints
```

不能默认来自某在世作者大段原文。

---

# 27. Style Parameters

建议抽象：

```text
POV
tense
sentence rhythm
dialogue density
description density
interiority
register
humor level
```

---

# 28. Prompt Template vs Context

必须分离：

```text
PromptTemplate
ContextArtifact
ModelPolicy
```

三者独立 version/hash。

---

# 29. PromptTemplate

Prompt 负责：

```text
task instruction
output format
role
behavior
```

Context 负责：

```text
facts
constraints
state
evidence
```

---

# 30. ModelPolicy

ModelPolicy 负责：

```text
role → model/provider
sampling
max output
tool policy
fallback
budget
```

Domain 不知道 provider。

---

# 31. Provider Adapter

Provider 层把统一：

```text
Prompt + Context + ModelPolicy
```

转换为：

```text
OpenAI messages
Claude messages
other provider payload
```

---

# 32. Context Hash

建议：

```text
sha256(
 task_role
 + canon_head_hash
 + contract_hash
 + selected_item_hashes
 + selection_policy_version
 + prompt_template_hash
)
```

ModelPolicy hash 单独记录。

---

# 33. Why ModelPolicy Not Always Inside Context Hash

同一 Context 可用于：

```text
GPT
Claude
Kimi
```

比较。

因此：

```text
context_hash
```

描述语义输入，

```text
run_fingerprint
```

再包含 ModelPolicy。

---

# 34. Context Inspection

Production 工具必须支持：

```text
show me exactly what the model saw
```

至少显示：

```text
item list
authority
token estimate
inclusion reason
omitted items
hashes
```

---

# 35. Omission Report

ContextArtifact SHOULD 存：

```text
omitted_items
omission_reason
```

例如：

```text
token budget
low relevance
stale
authority conflict
forbidden for role
```

---

# 36. Context Conflict

若两个 ContextItem 冲突：

```text
authority priority
```

先裁决。

若同 Authority 冲突：

```text
BLOCK / unresolved
```

不能两个都塞给模型“让它自己判断”。

---

# 37. Stale Context

以下变化使 Context stale：

```text
Canon parent changed
Contract changed
GenrePack changed
Plan dependency changed
critical source invalidated
```

---

# 38. Context Reuse

Context 可缓存，如果：

```text
all semantic inputs identical
```

---

# 39. Cache Key

基于：

```text
ContextRequest semantic identity
source hashes
selection policy
```

Operational：

```text
timeout
retry count
trace id
```

不进入 semantic key。

---

# 40. Context Artifact Lifecycle

```text
REQUESTED
COMPILED
VALIDATED
USED
STALE
INVALIDATED
ARCHIVED
```

---

# 41. Context Validation

编译完成后：

```text
schema
project isolation
branch isolation
parent hash
contract hash
genre hash
mandatory coverage
knowledge boundary
forbidden source
token budget
staleness
```

---

# 42. Project Isolation

任何 ContextItem 必须带：

```text
project_id
```

错误项目：

```text
HARD FAIL
```

---

# 43. Branch Isolation

Canon branch 不同：

```text
context cannot cross
```

除非显式 comparison task。

---

# 44. Raw Reference Leak Detection

Context validator 扫描：

```text
reference title
character names
long verbatim spans
source IDs
```

在 Writer Context 中出现：

```text
BLOCK / review
```

---

# 45. Secret / Sensitive Data

Context 不应包含：

```text
API keys
credentials
private user secrets
```

Provider auth 由基础设施注入。

---

# 46. Recent Chapter Source

Recent narrative context 必须来自：

```text
committed exact body
or
trusted derived summary bound to commit
```

不能来自失败 Draft。

---

# 47. Failed Candidate Isolation

失败 Candidate 可以给：

```text
Repairer
Evaluator
```

但不能作为下一章 Canon context。

---

# 48. Accepted Text Identity

Writer/Reviewer/Extractor/Commit 链必须绑定：

```text
candidate_text_hash
```

避免阶段之间文本漂移。

---

# 49. Review Context Compatibility

ReviewContext SHOULD 记录：

```text
writer_context_hash
```

Reviewer 可以增加：

```text
evaluation rubric
```

但基础事实来源应保持兼容。

---

# 50. Repair Context Compatibility

Repairer 必须知道：

```text
original context hash
candidate hash
findings hash
allowed patch scope
```

---

# 51. Context and NarrativeDelta

Extractor Context 必须包含：

```text
ontology
entity aliases
current state
```

以便产生高质量 Delta。

---

# 52. Entity Resolution Context

对 active scene entities：

```text
canonical_name
aliases
entity_id
type
current role
```

全部提供。

---

# 53. Avoid Full Registry Dump

不要把全部实体都塞给模型。

优先：

```text
direct participants
one-hop relations
contract-mentioned
recently active
high-risk identity
```

---

# 54. Graph Retrieval

Relationship/Knowledge/Faction 适合：

```text
graph neighborhood
```

结合 semantic retrieval。

---

# 55. Retrieval Layers

建议：

```text
L0 exact mandatory
L1 entity graph
L2 recent chronology
L3 semantic memory
L4 optional evidence
```

---

# 56. Retrieval Determinism

同一 frozen state + same policy：

```text
selection should be substantially repeatable
```

完全依赖随机 embedding top-k 不够。

---

# 57. Retrieval Tie-break

建议稳定：

```text
authority
mandatory
relevance
recency
stable id
```

---

# 58. Context Budget Failure

如果 mandatory items 已超过模型限制：

```text
CONTEXT_TOO_LARGE
```

不能静默删 hard facts。

解决：

```text
use larger model
split task
reduce contract scope
```

---

# 59. Context Compression

允许对低 Authority 内容：

```text
summarize
compress
```

必须保留：

```text
source refs
summary hash
```

---

# 60. Mandatory Facts Never Summarized Away

关键：

```text
identity
numeric state
timeline
knowledge
world law
required transition
```

优先结构化原值，而不是 prose summary。

---

# 61. Structured Before Prose

Context 尽量：

```text
structured facts
then concise prose
```

避免长篇自然语言压埋约束。

---

# 62. Context Sections

建议统一：

```text
1. Task
2. Hard Rules
3. Contract
4. Canon Facts
5. Character Perspectives
6. Recent Narrative
7. Style
8. Optional Evidence
9. Output Requirements
```

---

# 63. Context Ordering

高 Authority / Hard Constraints 放前。

但不同 Provider 的 attention 特性由 adapter/policy 调整。

---

# 64. Context Envelope

统一内部表示：

```text
ContextEnvelope
```

Provider Adapter 再决定具体消息结构。

---

# 65. Role Registry

至少：

```text
PLANNER
WRITER
EXTRACTOR
REVIEWER
REPAIRER
JUDGE
SUMMARIZER
REFERENCE_ANALYST
```

---

# 66. Role Capability

每个 Role 声明：

```text
allowed_sources
forbidden_sources
required_sources
authority_limit
can_propose_delta
can_write_canon = false
```

---

# 67. Writer Role

```text
can_propose_text: true
can_propose_delta: false
can_commit: false
```

---

# 68. Extractor Role

```text
can_propose_delta: true
can_commit: false
```

---

# 69. Reviewer Role

```text
can_produce_evidence: true
can_commit: false
```

---

# 70. Repairer Role

```text
can_modify_candidate: true
can_commit: false
```

---

# 71. Planner Role

```text
can_propose_plan: true
can_mutate_canon: false
```

---

# 72. Model Gateway

Model Gateway 根据：

```text
Role
ModelPolicy
CostPolicy
Availability
```

选择 Provider。

Domain 只认识：

```text
role
capabilities
```

---

# 73. Model Capability Registry

例如：

```text
structured_output
long_context
tool_use
reasoning
cost_class
latency_class
```

而不是在业务代码写：

```text
if model == "claude"
```

---

# 74. Fallback

Provider fallback 允许：

```text
same role
compatible capability
```

但必须记录：

```text
actual model
fallback reason
```

---

# 75. Fallback Semantic Risk

换模型可能改变结果。

因此：

```text
fallback run
```

是新 Run，不是假装原模型成功。

---

# 76. Context Provenance

ContextArtifact 必须记录：

```text
compiler_version
selection_policy
source hashes
generated_at
request id
```

---

# 77. Context Lineage

后续：

```text
Draft
Review
Delta
Repair
```

都引用 ContextArtifact。

---

# 78. Observability

Trace：

```text
context.request
context.retrieve
context.rank
context.trim
context.validate
context.issue
```

Metrics：

```text
context_tokens
mandatory_token_ratio
context_compile_latency
stale_context_reject
raw_reference_leak
knowledge_boundary_items
cache_hit
```

---

# 79. Context Quality Diagnostics

可以分析：

```text
too much irrelevant context
missing important fact
duplicated facts
conflicting facts
over-compressed context
```

---

# 80. Context Drift

如果相同类型任务的 Context 结构不断变化：

```text
context_drift
```

应监控。

---

# 81. AI Coding Rules

实现 Context 时 AI MUST：

1. 不让业务模块自己拼 Prompt；
2. 不从文件系统随意 glob 全部资料；
3. 不让 Writer 看到 raw reference；
4. 不把 stale summary 当 Canon；
5. 不裁掉 mandatory facts；
6. 不把 ModelPolicy 混进 Genre/Domain；
7. 不让 Provider Adapter决定 narrative authority；
8. ContextArtifact 必须 hash/version；
9. 每个 item 有 source 和 inclusion reason；
10. 项目/分支混入立即失败。

---

# 82. Suggested Repository Layout

```text
src/anovel/context/
  request/
  compiler/
  retrieval/
  ranking/
  budget/
  validation/
  artifact/

src/anovel/intelligence/
  roles/
  gateway/
  policies/

specs/context/
  schemas/
  policies/
```

---

# 83. Minimum APIs

```text
compile_context(request) -> ContextArtifact
validate_context(artifact) -> ValidationResult
inspect_context(context_id) -> ContextInspection
mark_context_stale(trigger) -> InvalidationSet

select_model(role, policy) -> ModelRoute
execute_model(role, context, prompt, model_policy) -> ModelRun
```

---

# 84. Required Tests

```text
TEST-CTX-001 mandatory_facts_never_trimmed
TEST-CTX-002 stale_canon_blocks_context
TEST-CTX-003 stale_contract_blocks_context
TEST-CTX-004 raw_reference_absent_from_writer
TEST-CTX-005 project_isolation
TEST-CTX-006 branch_isolation
TEST-CTX-007 knowledge_boundary_present
TEST-CTX-008 extractor_has_alias_roster
TEST-CTX-009 failed_draft_not_used_as_recent_context
TEST-CTX-010 same_semantic_inputs_same_context_hash
TEST-CTX-011 context_too_large_blocks
TEST-CTX-012 reviewer_binds_writer_parent
TEST-CTX-013 fallback_records_actual_model
```

---

# 85. V1 Regression Mapping

```text
V1 extractor only saw IDs
→ entity alias roster mandatory

V1 prompt ad-hoc composition
→ Context Compiler

V1 reference/market/domain artifacts mixed
→ role-specific allowed sources

V1 replay ambiguity
→ Context hash + Run fingerprint separation

V1 stale derived artifacts
→ context source staleness validation
```

---

# 86. Definition of Done

Context Intelligence v1.0 完成必须证明：

1. Writer Context 可由 Contract + Canon 自动编译；
2. 同一 ContextArtifact 可被 inspect；
3. Mandatory facts 不会因 token budget 消失；
4. Raw Reference 默认无法进入 Writer；
5. Knowledge Boundary 对 Scene participants 正确；
6. Extractor 获得 names + aliases；
7. Stale Canon/Contract Context 自动拒绝；
8. ContextHash 稳定；
9. Provider 切换不改变 Context authority；
10. Writer/Reviewer/Repairer lineage 可追踪；
11. 30 章运行没有跨项目/跨分支污染；
12. CI 有 Context regression suite。

---

# 87. Formal ADRs

建议接受：

## ADR-CONTEXT-001
Context is a compiled immutable artifact.

## ADR-CONTEXT-002
Every production model call binds a ContextArtifact.

## ADR-CONTEXT-003
Context authority priority is explicit.

## ADR-CONTEXT-004
Mandatory hard facts cannot be trimmed.

## ADR-CONTEXT-005
Role-specific context visibility is enforced.

## ADR-CONTEXT-006
Raw reference text is excluded from Writer context by default.

## ADR-CONTEXT-007
PromptTemplate, ContextArtifact and ModelPolicy are separately versioned.

## ADR-CONTEXT-008
Workflow/model provider does not own narrative authority.

## ADR-CONTEXT-009
Context selection and omission are inspectable.

## ADR-CONTEXT-010
Context lineage is preserved across generation, review and repair.

---

# 88. Next Document

下一份正式规范应为：

# `PRODUCTION_WORKFLOW_SPEC.md`

因为现在已经定义：

```text
Genesis
→ Canon
→ Plan
→ Contract
→ Context
```

下一步必须定义：

> 这些步骤如何在真实系统里长期、可恢复、可重试、可追踪地运行？

下一份将冻结：

```text
WorkflowRun
Stage
StageContract
Checkpoint
Retry
Idempotency
Budget Reservation
Resume
Failure Semantics
Kill/Restart
Model Call Boundary
Commit Stage
Publish Boundary
Run Fingerprint
```

之后再进入：

```text
QUALITY_EVALUATION_REPAIR_SPEC.md
```

**END OF SPEC**
