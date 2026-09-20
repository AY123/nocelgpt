# ANovel V2 Durable Production Workflow, Retry, Resume & Execution Specification

> **中文名**：ANovel V2 持久化生产工作流、重试、恢复与执行规范  
> **Document ID**：SPEC-WORKFLOW-0001  
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
> - `CONTEXT_INTELLIGENCE_SPEC.md`
>
> **Primary Goal**：定义 ANovel V2 的唯一生产执行主干，使长篇小说在真实模型调用、失败重试、进程崩溃、人工暂停、预算不足、版本变化和 Canon Commit 等情况下仍然具备可恢复、可重放、可审计、无重复副作用的长期生产能力。

---

# 0. Normative Summary

ANovel V2 Production Workflow MUST 满足：

1. **There is one authoritative production workflow.**
2. **Workflow state is not Canon state.**
3. **Every workflow run is versioned and fingerprinted.**
4. **Every stage has an explicit StageContract.**
5. **Every external/non-deterministic action is a side-effect boundary.**
6. **Every irreversible side effect is idempotent.**
7. **Retry policy is explicit per stage.**
8. **Checkpoint is mandatory at durable boundaries.**
9. **Resume MUST continue from durable state, not from process memory.**
10. **Successful identical stages SHOULD NOT rebill or rerun unnecessarily.**
11. **Canon Commit is a dedicated workflow stage and uses Canon Domain semantics.**
12. **Publishing is a separate irreversible external action.**
13. **Budget reservation precedes expensive model calls where practical.**
14. **Stage outputs are immutable artifacts with hashes.**
15. **Downstream stages bind upstream artifact hashes.**
16. **Failure semantics distinguish retryable, repairable, blocked and terminal.**
17. **Kill/restart tests are mandatory before 30-chapter certification.**
18. **Workflow implementation may change; workflow semantics are stable.**
19. **Temporal/LangGraph/custom engine MUST NOT own narrative truth.**
20. **Production Mode is fail-closed.**

---

# 1. Why Durable Workflow Is a First-Class Domain

小说生产不是：

```python
for chapter in range(300):
    write_chapter()
```

真实生产一定会遇到：

- Provider 503；
- rate limit；
- timeout；
- invalid structured output；
- extraction failure；
- repair failure；
- human review pause；
- deployment/restart；
- process crash；
- budget exhaustion；
- stale Contract；
- Canon parent changed；
- model fallback；
- partial external side effect；
- duplicate retry；
- manual abort。

因此 V2 需要：

> **Durable Production Workflow**

而不是普通函数调用链。

---

# 2. Workflow Authority Boundary

Workflow 负责：

```text
orchestration
stage ordering
retry
resume
checkpoint
budget
timeouts
side-effect coordination
```

Workflow 不负责：

```text
Canon truth
Genre truth
Narrative semantics
Plan authority
Model evaluation truth
```

---

# 3. WorkflowRun

每次完整生产运行创建：

```text
WorkflowRun
```

最低字段：

```text
run_id
project_id
branch_id
workflow_version
run_type
status
input_refs
run_fingerprint
budget
started_at
updated_at
completed_at
```

---

# 4. Run Types

初始：

```text
GENESIS
PLAN
CHAPTER_PRODUCTION
SCENE_REPAIR
RETCON
REBUILD
CERTIFICATION
PUBLISH
```

---

# 5. WorkflowRun Status

统一状态：

```text
CREATED
READY
RUNNING
PAUSED
BLOCKED
WAITING_HUMAN
WAITING_EXTERNAL
SUCCEEDED
FAILED
ABORTED
CANCELLED
```

---

# 6. RunFingerprint

正式 Production Run MUST 生成：

```text
RunFingerprint
```

建议：

```text
sha256(
 constitution_version
 + code_commit
 + workflow_version
 + schema_set_hash
 + genre_pack_hash
 + canon_parent_hash
 + planning_hash
 + contract_hash
 + context_policy_hash
 + prompt_template_hashes
 + model_policy_hash
 + quality_policy_hash
 + feature_flags
)
```

目标不是保证随机模型输出完全相同。

目标是：

> 知道“这个结果是在什么条件下产生的”。

---

# 7. Stage

Workflow 由 Stage 构成。

一个 Stage 必须具有：

```text
stage_id
stage_type
stage_version
input_contract
output_contract
side_effect_class
retry_policy
timeout_policy
checkpoint_policy
budget_policy
authority
dependencies
```

---

# 8. StageContract

StageContract 是运行时执行契约。

至少：

```text
stage_id
input_artifact_refs
input_hashes
expected_output_types
idempotency_key
retry_policy
timeout
budget_reservation
side_effect_class
checkpoint_required
```

---

# 9. Stage Types

初始主链：

```text
LOAD_CANON
VALIDATE_PLAN
COMPILE_CONTRACT
COMPILE_CONTEXT
GENERATE_CANDIDATE
EXTRACT_DELTA
VALIDATE_DETERMINISTIC
VALIDATE_SEMANTIC
PLAN_REPAIR
APPLY_REPAIR
FINAL_VALIDATE
ISSUE_COMMIT_PERMIT
CANON_COMMIT
PROJECT_SNAPSHOT
FINALIZE_CHAPTER
PUBLISH_OPTIONAL
```

---

# 10. One Authoritative Workflow

禁止：

```text
SerialRunner
ProductionRunner
ChapterPipeline
ContractRunner
HookRunner
```

长期并行维护多套主执行链。

V2 必须有一个：

> **Authoritative Production Workflow**

不同模式通过 configuration/stage selection 实现。

---

# 11. StageGraph Must Drive Execution

如果系统存在 StageGraph：

```text
StageGraph
```

就必须真实驱动 Scheduler/Executor。

禁止出现：

```text
StageGraph only for docs/tests
Actual execution elsewhere
```

这正是 V1 需要避免的设计模型/运行路径分离。

---

# 12. Workflow Definition

WorkflowDefinition 是版本化 Artifact。

包含：

```text
workflow_id
version
stages
dependencies
transition_rules
failure_routes
```

---

# 13. Stage Input Binding

每个 Stage 输入必须绑定：

```text
artifact_id
artifact_hash
schema_version
```

禁止：

```text
read latest file from folder
```

这种隐式输入。

---

# 14. Stage Output

Stage 输出：

```text
StageArtifact
```

必须：

```text
immutable
versioned
hash-addressed
provenance-linked
```

---

# 15. Stage Completion

Stage 成功的含义不是：

> 函数 return 了。

而是：

```text
output artifact persisted
output hash verified
checkpoint persisted
side effect reconciled
```

---

# 16. Checkpoint

Checkpoint 记录：

```text
run_id
stage_id
attempt
status
input_hashes
output_refs
side_effect_receipts
budget_state
timestamp
```

---

# 17. Durable Boundary

以下后面 MUST checkpoint：

```text
expensive model call
external API side effect
Canon Commit
human wait
publish action
long-running batch
```

---

# 18. Resume

Resume 流程：

```text
Load WorkflowRun
↓
Load latest durable checkpoint
↓
Verify WorkflowDefinition/version
↓
Verify semantic inputs
↓
Verify completed stage artifacts
↓
Continue from first incomplete stage
```

---

# 19. Resume Must Not Trust Process Memory

任何：

```text
in-memory current_stage
local Python variable
agent memory
```

都不能成为恢复真值。

---

# 20. Stage Identity

同一 Stage 执行语义建议由：

```text
run_id
stage_id
stage_version
semantic_input_hash
```

共同确定。

---

# 21. Idempotency

对任何可能产生副作用的 Stage：

```text
idempotency_key
```

必须显式。

---

# 22. Model Call Idempotency

模型调用通常无法真正“撤销”。

策略：

```text
semantic request fingerprint
+
response cache / artifact reuse
```

如果同一语义请求已成功：

```text
reuse result
```

而不是重复扣费。

---

# 23. Semantic Request Fingerprint

进入：

```text
prompt_template
context_hash
model_id
sampling_semantics
tool_policy
output_schema
```

不进入：

```text
timeout
retry_count
trace_id
network route
```

---

# 24. Retry Taxonomy

失败分类：

```text
TRANSIENT
PERMANENT
SEMANTIC_INVALID
POLICY_BLOCKED
BUDGET_BLOCKED
CONCURRENCY_CONFLICT
HUMAN_REQUIRED
CANCELLED
```

---

# 25. TRANSIENT

例：

```text
503
timeout
rate limit
temporary network failure
```

可以重试。

---

# 26. PERMANENT

例：

```text
invalid API key
unsupported model
schema permanently incompatible
```

不自动无限重试。

---

# 27. SEMANTIC_INVALID

例：

```text
model output parses
but violates output contract
```

可：

```text
retry with repair instruction
or
alternate model
or
block
```

取决于 StagePolicy。

---

# 28. POLICY_BLOCKED

例：

```text
Genre hard violation
missing Contract
stale Canon
```

不能靠重试“碰碰运气”。

必须先解决上游。

---

# 29. CONCURRENCY_CONFLICT

例如：

```text
Canon Head changed
```

当前 downstream artifacts 可能全部 stale。

需要：

```text
rebase / replan / recompile
```

---

# 30. RetryPolicy

每 Stage：

```text
max_attempts
backoff
retryable_classes
fallback_policy
```

---

# 31. Retry Budget

重试本身也消耗：

```text
money
time
tokens
```

因此必须有：

```text
retry_budget
```

---

# 32. Timeout

区分：

```text
request timeout
stage timeout
workflow deadline
human wait timeout(optional)
```

---

# 33. Heartbeat

长 Stage：

```text
reference profiling
large corpus analysis
long human process
```

可以 heartbeat。

---

# 34. Lease

如果分布式 Worker：

```text
lease_owner
lease_until
lease_epoch
```

---

# 35. Fencing Token

任何不可逆 side effect：

```text
current lease epoch
```

必须匹配。

旧 Worker 恢复：

```text
fencing rejected
```

---

# 36. Budget Domain

Workflow 必须管理：

```text
token budget
money budget
time budget
retry budget
```

---

# 37. Budget Reservation

昂贵 Stage 前：

```text
reserve estimated cost
```

完成后：

```text
reconcile actual
```

---

# 38. Budget Exhaustion

预算不足：

```text
BUDGET_BLOCKED
```

不能自动：

```text
switch to random cheap model
```

除非 ModelPolicy 明确允许。

---

# 39. Cost Receipt

每个 model call 输出：

```text
input tokens
output tokens
provider reported usage
estimated cost
actual cost
currency
```

---

# 40. Model Call Boundary

Model Gateway 调用是 Side Effect Stage。

必须保存：

```text
semantic request fingerprint
actual provider
actual model
request artifact
response artifact
usage
latency
retry history
```

---

# 41. Model Fallback

Fallback：

```text
preferred model unavailable
→ compatible fallback
```

必须：

```text
new attempt
actual model logged
```

不能伪装成原模型运行。

---

# 42. Candidate Generation Stage

输入：

```text
ContextArtifact
PromptTemplate
ModelPolicy
```

输出：

```text
CandidateArtifact
```

包含：

```text
text
text_hash
model_run_ref
context_hash
contract_hash
```

---

# 43. Candidate Artifact

Candidate：

```text
authority = draft
```

不得自动推进 Canon。

---

# 44. Extraction Stage

输入：

```text
CandidateArtifact
Extractor Context
Ontology
```

输出：

```text
NarrativeDelta Candidate
```

---

# 45. Validation Stages

建议分：

```text
Q0 Deterministic
Q1 Canon
Q2 Genre
Q3 Transition
Q4+ Semantic
```

Quality 细节由下一份规范定义。

---

# 46. Repair Route

如果：

```text
repairable
```

则：

```text
Diagnosis
→ RepairPlan
→ Patch
→ New Candidate Hash
→ Re-extract
→ Re-validate
```

---

# 47. Repair Loop Limit

必须：

```text
max repair iterations
```

避免无限循环。

---

# 48. Repair Gain

每轮 repair 应记录：

```text
before findings
after findings
new violations
```

---

# 49. Final Validation

在 CommitPermit 前：

```text
all hard gates pass
candidate hash final
delta final
change set final
```

---

# 50. CommitPermit Stage

输入：

```text
Final Candidate
ChangeSet
Validation Evidence
Contract
Canon Parent
GenrePack
```

输出：

```text
CommitPermit
```

---

# 51. Canon Commit Stage

这是不可逆 Canon side effect。

必须：

```text
idempotent
CAS/fencing protected
```

---

# 52. Commit Uncertain Result

最危险场景：

```text
request sent
DB commit may have succeeded
client timed out
```

恢复时：

```text
query idempotency key
```

判断是否已成功。

绝不能盲重试 append。

---

# 53. Post-Commit Projection

Commit 后：

```text
Snapshot
Derived Views
Promise Ledger
Character View
```

可异步重建。

---

# 54. Projection Failure

如果 projection 失败：

```text
Canon remains committed
projection retry
```

不得撤销 Canon。

---

# 55. Chapter Finalization

ChapterFinal Artifact 应绑定：

```text
committed Canon commit
final text hash
validation refs
model lineage
```

---

# 56. Production State

章节生产状态建议：

```text
PLANNED
CONTEXT_READY
GENERATED
VALIDATING
NEEDS_REPAIR
VALIDATED
APPROVAL_PENDING
APPROVED
COMMITTING
COMMITTED
PUBLISH_READY
PUBLISHED
BLOCKED
INVALIDATED
ABORTED
```

---

# 57. Production State Authority

只有：

```text
Workflow Policy / State Machine
```

能改变 ProductionState。

Reviewer 只能提供 Evidence。

---

# 58. Human Wait

某些 Stage：

```text
R3 Retcon
high-risk originality
external publish
```

可能进入：

```text
WAITING_HUMAN
```

必须 durable。

---

# 59. Human Decision Artifact

记录：

```text
decision
scope
approved hash
actor
timestamp
```

---

# 60. Human Resume

收到 decision 后：

```text
validate decision artifact
resume exact stage
```

---

# 61. Manual Pause

用户可以：

```text
pause after current durable boundary
```

不是强杀事务中间状态。

---

# 62. Cancellation

Cancellation：

```text
stop future stages
preserve completed artifacts
do not undo committed Canon
```

---

# 63. Abort

ABORT 表示异常终止。

之后可：

```text
resume
or
new run
```

---

# 64. Workflow Version Change

运行中 WorkflowDefinition 升级：

```text
do not silently switch
```

选项：

```text
finish old
migrate run
restart from safe boundary
```

---

# 65. Run Migration

必须显式：

```text
from_version
to_version
mapping
safe_stage
```

---

# 66. Schema Upgrade During Run

同理：

```text
stage artifact schema
```

变化必须有 compatibility policy。

---

# 67. Artifact Immutability

Stage output 不原地覆盖。

新 attempt：

```text
new artifact id
```

---

# 68. Winner Selection

多 Candidate 时：

```text
candidate A
candidate B
candidate C
```

winner selection 只是 Stage。

必须保存：

```text
all candidate refs
ranking evidence
selected hash
```

---

# 69. Evaluated Winner Integrity

最终 selected candidate hash 必须和：

```text
reviewed
repaired
committed
```

一致。

---

# 70. Publish Boundary

Publish 与 Canon Commit 完全分离。

```text
COMMITTED
→ PUBLISH_READY
→ Human/Policy Gate
→ External Publish
```

---

# 71. Publish Idempotency

外部平台发布同样需要：

```text
idempotency / external receipt
```

---

# 72. Publish Receipt

记录：

```text
platform
external_id
published_hash
published_at
response
```

---

# 73. Published Hash

必须：

```text
published_hash == approved_publish_artifact_hash
```

---

# 74. External Edit

如果发布平台人工修改：

```text
external divergence
```

必须检测/同步策略。

---

# 75. Run Lineage

每次 WorkflowRun：

```text
inputs
stages
outputs
model calls
commits
publication
```

形成完整 lineage。

---

# 76. Stage Lineage

类似：

```text
Input Artifact(s)
→ Stage Run
→ Output Artifact(s)
```

---

# 77. Observability

Trace 层级：

```text
WorkflowRun
└─ Chapter
   ├─ Compile Contract
   ├─ Compile Context
   ├─ Generate
   ├─ Extract
   ├─ Validate
   ├─ Repair
   └─ Commit
```

---

# 78. Metrics

至少：

```text
workflow_run_total
workflow_failure_rate
stage_retry_total
stage_latency
model_cost
model_retry
repair_iterations
commit_conflict
resume_total
checkpoint_recovery
budget_blocked
```

---

# 79. Structured Logs

每条日志至少：

```text
run_id
stage_id
attempt
project_id
branch_id
chapter_id(optional)
trace_id
```

---

# 80. Failure Record

每个失败保存：

```text
failure_class
error_code
message
stage
input hashes
provider status
retryable
```

---

# 81. No Silent Failure

禁止：

```text
catch Exception:
    log warning
    continue
```

在 Production 主链。

---

# 82. Dead-letter / Quarantine

无法自动恢复的 Stage：

```text
BLOCKED
```

保留完整证据。

---

# 83. Workflow Storage

建议 PostgreSQL 持久化：

```text
workflow_runs
stage_runs
checkpoints
stage_artifacts
model_runs
budget_ledger
side_effect_receipts
```

---

# 84. Queue

Phase 1 可：

```text
single process / DB-backed queue
```

不必一开始上复杂分布式队列。

---

# 85. Engine Choice

Phase 1：

```text
custom minimal durable semantics
or
LangGraph prototype
```

后续根据：

```text
human waits
distributed scale
operational burden
```

评估 Temporal。

---

# 86. Engine Independence

无论使用何种 engine：

```text
WorkflowDefinition
StageContract
Artifact
Canon
```

不得被框架私有状态绑死。

---

# 87. Kill Test

必须测试：

```text
kill before model
kill during model
kill after model response
kill before commit
kill after commit before checkpoint
kill during projection
```

---

# 88. Resume Acceptance

每种 Kill Case：

```text
no duplicate commit
no duplicate publish
no lost accepted artifact
no hidden state fork
```

---

# 89. 10-Chapter Durability Test

至少随机终止：

```text
3–5 times
```

验证恢复。

---

# 90. 30-Chapter Durability Test

必须加入：

```text
provider transient failures
rate limit
budget pause
manual pause
worker restart
commit conflict
```

---

# 91. Workflow Security

Stage input 不允许：

```text
untrusted arbitrary path execution
secret in artifact
```

---

# 92. Secret Handling

Provider key：

```text
runtime secret injection
```

不得进入：

```text
Workflow Artifact
Context Artifact
Run Manifest
Log
```

---

# 93. Audit

需要回答：

> Chapter 187 为什么最后变成这个版本？

系统应能列出：

```text
Run
Contract
Context
Model call
Candidate
Review
Repair
Delta
ChangeSet
Permit
Commit
```

---

# 94. Workflow Error Codes

建议：

```text
WF-001 STAGE_INPUT_STALE
WF-002 STAGE_OUTPUT_INVALID
WF-003 RETRY_EXHAUSTED
WF-004 BUDGET_EXHAUSTED
WF-005 CHECKPOINT_CORRUPT
WF-006 RESUME_VERSION_MISMATCH
WF-007 SIDE_EFFECT_UNKNOWN
WF-008 IDEMPOTENCY_CONFLICT
WF-009 LEASE_LOST
WF-010 FENCING_REJECTED
WF-011 HUMAN_REQUIRED
WF-012 CANON_PARENT_CHANGED
WF-013 WORKFLOW_CANCELLED
WF-014 ARTIFACT_HASH_MISMATCH
WF-015 MODEL_FALLBACK_USED
```

---

# 95. Architecture Fitness

CI 检查：

```text
only Workflow Executor can advance production stage
only CanonCommitService can advance Canon
Publisher cannot write Canon
Model Gateway cannot mutate Workflow DB except through Stage API
StageGraph must have runtime consumer
```

---

# 96. AI Coding Rules

AI 实现 Workflow 时 MUST：

1. 不创建第二主 Scheduler；
2. 不依赖进程内状态做恢复；
3. 不让 Retry 重复不可逆副作用；
4. 不用 timeout 作为 semantic request identity；
5. 不把 Projection failure 当 Canon rollback；
6. 不让 Reviewer 自己改 ProductionState；
7. 不让 missing Checkpoint 静默继续；
8. 不覆盖旧 Artifact；
9. 不把 Secret 写入 Run artifact；
10. 不把 Workflow framework state 当 Canon。

---

# 97. Suggested Repository Layout

```text
src/anovel/workflow/
  definitions/
  engine/
  scheduler/
  stages/
  checkpoint/
  retry/
  budget/
  recovery/
  state/
  lineage/

src/anovel/infrastructure/
  model_gateway/
  persistence/
  telemetry/
```

---

# 98. Minimum APIs

```text
create_run(definition, inputs) -> WorkflowRun
execute_run(run_id) -> WorkflowResult
pause_run(run_id)
resume_run(run_id)
cancel_run(run_id)

execute_stage(run_id, stage_id) -> StageResult
load_checkpoint(run_id) -> Checkpoint
reconcile_side_effect(stage_run) -> SideEffectStatus

reserve_budget(stage) -> BudgetReservation
reconcile_budget(reservation, actual) -> BudgetReceipt
```

---

# 99. Required Tests

```text
TEST-WF-001 restart_after_successful_model_call_reuses_artifact
TEST-WF-002 timeout_does_not_change_semantic_model_key
TEST-WF-003 retry_does_not_duplicate_commit
TEST-WF-004 retry_does_not_duplicate_publish
TEST-WF-005 crash_after_commit_recovers_projection
TEST-WF-006 stale_contract_blocks_stage
TEST-WF-007 canon_parent_change_blocks_commit
TEST-WF-008 budget_exhaustion_blocks_expensive_stage
TEST-WF-009 fallback_records_actual_model
TEST-WF-010 manual_pause_is_durable
TEST-WF-011 worker_lease_loss_fenced
TEST-WF-012 stage_graph_drives_execution
TEST-WF-013 checkpoint_corruption_blocks_resume
TEST-WF-014 production_state_has_single_writer
TEST-WF-015 failed_candidate_never_becomes_next_context
```

---

# 100. V1 Regression Mapping

```text
V1 fake-model green / live-provider failure
→ real provider stage tests

V1 retry/replay ambiguity
→ semantic request fingerprint

V1 StageGraph not runtime
→ StageGraph drives execution

V1 multiple orchestration paths
→ one authoritative workflow

V1 warning then continue
→ explicit failure classes / fail-closed

V1 placeholder provenance
→ artifact hash + checkpoint + lineage
```

---

# 101. Definition of Done

Production Workflow v1.0 完成必须证明：

1. 一章完整链路可执行；
2. 任意 Stage 失败后状态可解释；
3. model call 成功后进程崩溃不会重复计费（可缓存条件下）；
4. commit 成功后崩溃不会重复 Commit；
5. publish 不会重复；
6. stale Contract/Canon 会阻止后续；
7. WorkflowState 与 CanonState 完全分离；
8. StageGraph 是真实执行图；
9. 预算和 retry 可追踪；
10. 手动 Pause/Resume 有 durable semantics；
11. 10 章随机 kill/restart 通过；
12. 30 章多故障注入通过。

---

# 102. Formal ADRs

建议接受：

## ADR-WF-001
ANovel has one authoritative production workflow.

## ADR-WF-002
Workflow state is separate from Canon state.

## ADR-WF-003
Every stage is governed by a StageContract.

## ADR-WF-004
External and irreversible side effects are idempotent boundaries.

## ADR-WF-005
Resume relies on durable checkpoints, not process memory.

## ADR-WF-006
Semantic model request identity excludes operational parameters.

## ADR-WF-007
Canon Commit is a dedicated idempotent workflow stage.

## ADR-WF-008
Publishing is separate from Canon Commit.

## ADR-WF-009
Stage artifacts are immutable and hash-addressed.

## ADR-WF-010
Workflow engine implementation may vary, but execution semantics remain stable.

---

# 103. Next Document

下一份规范应为：

# `QUALITY_EVALUATION_REPAIR_SPEC.md`

现在已经有：

```text
Genesis
→ Canon
→ Planning
→ Contract
→ Context
→ Durable Workflow
```

下一步必须正式定义：

> “什么样的章节允许 Commit？”

下一份将冻结：

```text
Q0 Deterministic
Q1 Canon
Q2 Genre
Q3 Transition
Q4 Narrative
Q5 Character
Q6 Commercial Proxy
Q7 Originality
Q8 Human / Reader Truth

Evidence Level
Judge Independence
Pairwise Evaluation
Diagnosis
RepairPlan
Patch-first Repair
Regression Validation
Human Calibration
Golden Set
```

**END OF SPEC**
