# ANovel V2 Canonical Narrative State & Narrative Transaction Specification

> **中文名**：ANovel V2 规范叙事状态与叙事事务规范  
> **Document ID**：SPEC-CANON-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `V1_FORENSIC_LESSONS.md`
> - `REFERENCE_ARCHITECTURE_STUDY.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
>
> **Primary Goal**：定义 ANovel V2 中唯一权威的 Canon 模型、状态提交边界、事务语义、重试/并发/回滚/重建/Retcon 机制，保证长篇生产在数十到数百章节后仍然只有一套可追踪、可恢复、可验证的小说事实真值。

---

# 0. Constitutional Summary

本规范建立以下不可违背的 Canon 原则：

1. **Draft is not Canon.**
2. **NarrativeDelta is proposal, not truth.**
3. **Canon changes only through Canon Commit.**
4. **Every Canon Commit has exactly one valid parent head.**
5. **Production is fail-closed before commit.**
6. **Commit is atomic.**
7. **Retry must be idempotent.**
8. **Committed history is append-only by default.**
9. **Snapshots are projections, not alternate truth.**
10. **Canon must be reconstructable from committed history.**
11. **A validation report cannot mutate Canon.**
12. **A model cannot approve its own irreversible state mutation.**
13. **Retcon is explicit, versioned and auditable.**
14. **Workflow state is not Canon state.**
15. **Reference, Market, Plan, Judge and Draft have zero direct Canon write authority.**
16. **Every production project has one authoritative Canon Head.**
17. **Branching is explicit and isolated.**
18. **Concurrent commits require optimistic concurrency / fencing semantics.**
19. **Accepted text hash must equal evaluated/committed text hash.**
20. **Canon lineage is cryptographically fingerprinted where practical.**

---

# 1. Why Canon Needs Its Own Domain

V1 已经证明：

```text
Story Bible 存在
+
Registry 存在
+
Review 存在
```

并不能保证长期一致性。

真正的问题是：

```text
Who owns truth?
Who is allowed to change truth?
When does a candidate become truth?
How do retries avoid duplicate truth?
How do edits change downstream truth?
How do we recover after crash?
```

因此 Canon 必须是独立 Domain，而不是：

```text
a folder of yaml files
or
a model memory
or
a registry helper
```

---

# 2. Core Canon Objects

V2 Canon Domain 至少包含：

```text
CanonHead
CanonEvent
CanonSnapshot
NarrativeDelta
ChangeSet
CommitPermit
CanonTransaction
CanonCommit
CanonProjection
CanonBranch
RetconRequest
RetconCommit
InvalidationRecord
```

---

# 3. CanonHead

`CanonHead` 表示某个项目/分支当前唯一权威最新提交。

最小字段：

```text
project_id
branch_id
head_commit_id
head_sequence
head_hash
snapshot_id
updated_at
```

规则：

> 一个 project + branch 只能有一个 active Canon Head。

---

# 4. CanonEvent

CanonEvent 是已提交历史中的不可变事件。

可以包含：

```text
entity_created
fact_set
fact_ended
relationship_changed
knowledge_changed
goal_changed
promise_changed
resource_transferred
location_changed
world_changed
genre_extension_changed
```

CanonEvent 一旦提交：

> 默认 append-only。

---

# 5. CanonCommit

CanonCommit 是一次原子 Canon 变更的正式记录。

结构：

```text
commit_id
project_id
branch_id
parent_commit_id
sequence
source_artifact_id
source_text_hash
change_set_hash
permit_id
events[]
commit_hash
created_at
```

### Critical

Commit 不是：

```text
“保存最新 state”
```

而是：

```text
“追加一组已经被授权的事实变化”
```

---

# 6. Canon Snapshot

Snapshot 是 Canon Head 的加速投影。

它包含：

```text
entities
active facts
relationships
knowledge
promises
timeline projection
genre extensions
```

但：

> Snapshot 不是第二套真值。

它必须能从 Canon history 重建。

---

# 7. Snapshot Rule

允许：

```text
cache
materialized view
read model
```

但必须满足：

```text
snapshot.head_commit_id == canon_head.head_commit_id
```

若不一致：

```text
STALE
```

不得偷偷当最新 Canon。

---

# 8. Canon Transaction

一次生产提交必须遵循：

```text
BEGIN
↓
Load Canon Head N
↓
Bind Parent Commit
↓
Compile Contract
↓
Generate Candidate
↓
Extract NarrativeDelta
↓
Validate Delta
↓
Build ChangeSet
↓
Obtain CommitPermit
↓
Compare Current Head == Expected Parent
↓
Append Canon Commit
↓
Project Snapshot N+1
↓
Move Canon Head
↓
COMMIT
```

任何一步失败：

```text
ROLLBACK
Canon remains N
```

---

# 9. NarrativeDelta vs ChangeSet

## NarrativeDelta

来自正文/模型抽取的候选变化。

特点：

```text
may be uncertain
may conflict
may be incomplete
may contain unsupported operations
```

## ChangeSet

经过：

```text
entity resolution
schema validation
genre validation
canon validation
temporal validation
knowledge validation
transition validation
```

之后形成的可提交结构。

### Rule

`NarrativeDelta != ChangeSet`

---

# 10. ChangeSet

ChangeSet 必须：

```text
reference expected_parent_commit
reference source_artifact
contain typed operations
contain deterministic validation summary
contain semantic validation evidence
declare risk level
```

ChangeSet 不能自行提交自己。

---

# 11. CommitPermit

CommitPermit 是 Canon Commit 的必要前置凭据。

它证明：

```text
which ChangeSet
which parent
which source text
which policy version
which validations
which human approvals
which genre pack
```

已满足提交要求。

### Rule

没有 CommitPermit：

```text
NO COMMIT
```

---

# 12. Permit Binding

Permit 必须绑定：

```text
change_set_hash
source_text_hash
expected_parent_hash
genre_pack_hash
contract_hash
policy_hash
```

任何一个变化：

```text
Permit invalid
```

必须重新验证。

---

# 13. Text Hash Integrity

V1 的历史问题之一：

> 被评价的正文与最终落盘正文可以产生语义不一致。

V2 必须确保：

```text
generated_text_hash
evaluated_text_hash
approved_text_hash
committed_source_text_hash
```

在单一接受路径上完全一致。

如果不同：

```text
CANON-TEXT-HASH-MISMATCH
→ BLOCK
```

---

# 14. Parent Binding

任何 Commit 必须声明：

```text
expected_parent_commit_id
expected_parent_hash
expected_parent_sequence
```

提交前重新读取 CanonHead。

如果 Head 已变化：

```text
CONCURRENCY_CONFLICT
```

当前 transaction 不得继续。

---

# 15. Optimistic Concurrency

Phase 1 推荐：

```text
Compare-And-Swap
```

语义：

```text
UPDATE canon_head
SET head = new
WHERE head = expected_parent
```

affected rows = 1：

```text
success
```

否则：

```text
conflict
```

---

# 16. Fencing

如果未来存在：

```text
multiple workers
leases
distributed execution
```

则使用：

```text
lease_owner
lease_epoch
```

提交必须满足：

```text
owner == current_owner
epoch == current_epoch
```

旧 Worker 即使恢复运行，也不能提交旧结果。

---

# 17. Idempotency

每个 irreversible Canon Commit 必须有：

```text
idempotency_key
```

建议：

```text
hash(
 project_id
 + branch_id
 + source_artifact_id
 + expected_parent
 + change_set_hash
)
```

同 key 重试：

```text
return existing commit
```

不得重复追加事件。

---

# 18. Retry Semantics

允许重试：

```text
generation
extraction
semantic review
projection rebuild
```

必须谨慎：

```text
commit
publish
external side effect
```

Commit 重试必须完全 idempotent。

---

# 19. Crash Recovery

如果进程在：

```text
append commit
```

后、

```text
update snapshot
```

前崩溃：

系统必须能：

```text
read CanonHead
rebuild snapshot
```

恢复。

### Rule

Snapshot failure MUST NOT invalidate already successful Canon Commit.

---

# 20. Commit Atomicity

推荐逻辑：

```text
DB transaction:
  insert commit
  insert events
  CAS update canon_head
COMMIT
```

Snapshot 可：

```text
same transaction
or
post-commit projection
```

取决于实现。

但 Canon Head 更新必须和 Commit 写入一致。

---

# 21. Canon Event Log

Event Log 需要：

```text
ordered sequence
immutable commit reference
typed event payload
schema version
```

建议 sequence：

```text
monotonic per branch
```

---

# 22. Canon Reconstruction

给定：

```text
initial state
+
commit log
+
schema versions
+
projectors
```

必须可以重建：

```text
Snapshot@N
```

这是长期审计能力的核心。

---

# 23. Projection

Projection 可以有多个：

```text
CharacterView
TimelineView
RelationshipGraph
PromiseLedger
SceneRelevantState
```

它们都属于：

```text
DERIVED
```

不得成为平行 Canon。

---

# 24. Canon Fact Authority

只有：

```text
CanonCommit
```

产生 Canon Authority。

以下均不能：

```text
Draft
Reviewer
ReferenceEvidence
MarketSignal
Plan
ContextArtifact
AI Extraction
```

---

# 25. Contract Relationship

Contract 约束：

```text
what may happen next
```

Canon 表达：

```text
what has happened
```

Contract 可以：

```text
compiled from canon
```

但不能反向自动写 Canon。

---

# 26. Plan Relationship

Plan 是：

```text
future intention
```

Canon 是：

```text
committed history
```

如果 Canon 导致 Plan 过时：

```text
invalidate / replan
```

不能改 Canon 去迎合旧 Plan。

---

# 27. Branching

V2 支持显式 Branch。

用途：

```text
alternative plot experiment
repair experiment
A/B narrative
retcon preview
```

每个 Branch：

```text
own CanonHead
own commit chain
shared ancestor
```

---

# 28. Branch Isolation

Branch 不得自动影响 main Canon。

合并前必须：

```text
compare
validate
resolve
commit
```

不存在 Git 式自动文本 merge。

---

# 29. Merge Semantics

Narrative Branch merge 是语义合并。

需要检查：

```text
entity conflicts
timeline conflicts
knowledge conflicts
relationship conflicts
world law
genre
promise
```

如果冲突：

```text
BLOCK
```

---

# 30. Retcon

Retcon 不是直接编辑历史文件。

流程：

```text
RetconRequest
↓
Impact Analysis
↓
Human Approval
↓
Retcon ChangeSet
↓
Rebuild affected projections/plans
↓
Retcon Commit
```

---

# 31. Retcon Types

建议：

```text
CORRECTION
CONTINUITY_REPAIR
AUTHORIAL_CHANGE
WORLD_RULE_CHANGE
IDENTITY_CORRECTION
```

不同类型风险不同。

---

# 32. Retcon Severity

## R1

小事实修正：

```text
拼写
颜色
轻微日期
```

## R2

状态修正：

```text
关系
资源
位置
```

## R3

重大：

```text
身份
死亡
核心历史
世界规则
Genre
```

R3 默认要求 Human Authority。

---

# 33. Retcon Impact Graph

修改旧事实后必须分析：

```text
dependent events
plans
contracts
promises
knowledge
context artifacts
published chapters
```

不能只改一个字段。

---

# 34. Published Canon

一旦章节对外发布：

```text
publication_state = external
```

Retcon 风险更高。

必须记录：

```text
published impact
reader-visible inconsistency
migration strategy
```

---

# 35. Invalidation

以下 Artifact 在 Canon 改变后可能 stale：

```text
Plan
Arc
ChapterContract
SceneContract
ContextArtifact
ReviewEvidence
DerivedSummary
CharacterView
```

系统必须有：

```text
invalidation graph
```

---

# 36. Canon vs Story Bible

Story Bible 在 V2 不是唯一 Canon Store。

它应成为：

```text
Human-readable projection / authored constitution
```

其中：

```text
stable authored constraints
```

可以拥有高 Authority。

但运行中事实仍通过 Canon Commit。

---

# 37. Initial Canon

新项目 Genesis 后，需要：

```text
GenesisCommit
```

用于建立：

```text
initial characters
world
relationships
initial knowledge
initial promises
initial genre extensions
```

这样没有“无历史的隐藏初始状态”。

---

# 38. Genesis Commit

GenesisCommit 也必须：

```text
versioned
hashed
validated
```

以后才能准确回答：

> 这个小说最初是什么设定？

---

# 39. Entity Creation

新实体必须通过：

```text
CREATE_ENTITY
```

并完成：

```text
identity resolution
duplicate check
schema validation
```

---

# 40. Entity Deletion

Canon 不推荐物理删除 Narrative Entity。

使用：

```text
lifecycle
invalidation
superseded_by
```

保持历史。

---

# 41. Fact Ending

动态事实：

```text
located_at = A
```

变成：

```text
located_at = B
```

应逻辑表示：

```text
end old validity
set new fact
```

而不是覆写历史。

---

# 42. Time-valid Facts

支持：

```text
valid_from
valid_to
```

例如：

```text
employee_of
owns_object
located_at
```

这样 Timeline 查询才可靠。

---

# 43. Knowledge Commit

Knowledge 变化也是 Canon。

如果 Character 得知秘密：

```text
ADD_KNOWLEDGE
```

必须有：

```text
source event
acquired time
```

---

# 44. False Belief

错误认知也可以进入 Canon：

```text
character believes X
```

但不能将 X 本身提交为事实。

---

# 45. Promise Canon

Promise 也是 Canon 中的叙事义务。

打开：

```text
OPEN_PROMISE
```

兑现：

```text
PAY_PROMISE
```

长期系统必须跟踪未还 Promise Debt。

---

# 46. Genre Extension Commit

Genre-specific 状态变化：

```text
realm
equity
territory
family_generation
```

也通过统一 ChangeSet。

GenrePack 不能拥有独立提交路径。

---

# 47. Canon Extension Registry

每个 extension 必须注册：

```text
schema
owner
ops
validators
projector
```

未注册 extension：

```text
BLOCK
```

---

# 48. Semantic Validation Stack

ChangeSet 提交前：

```text
Schema
Identity
Authority
Genre
Mutability
Timeline
Knowledge
Relationship
Capability
Transition
Risk
Semantic Review
Human Gate(if required)
```

---

# 49. Hard vs Soft Validation

Hard：

```text
schema invalid
wrong parent
identity contradiction
immutable mutation
genre hard violation
illegal progression
knowledge hard leak
unregistered extension
```

Soft：

```text
tone drift
payoff weak
motivation questionable
```

Soft 默认不直接改变 Canon 权限，除非 Policy 指定。

---

# 50. CommitPolicy

建议统一接口：

```text
evaluate(change_set, canon, contract, evidence)
→ CommitDecision
```

结果：

```text
ALLOW
DENY
REPAIR_REQUIRED
HUMAN_REVIEW
```

---

# 51. CommitPermit Content

Permit 至少：

```text
permit_id
change_set_hash
source_text_hash
expected_parent_hash
contract_hash
genre_pack_hash
policy_hash
validation_results
human_approval_refs
expires_at(optional)
```

---

# 52. Permit Expiration

如果 Canon Head 改变：

```text
Permit automatically invalid
```

即使 expires_at 未到。

---

# 53. Human Approval

Human Approval 也是 Artifact。

必须：

```text
who
what
scope
approved_hash
approved_at
```

不能只存：

```text
approved = true
```

---

# 54. Model Approval Prohibition

同一 Model 可以：

```text
generate
review
```

但不能拥有：

```text
irreversible commit authority
```

Commit authority 来自：

```text
deterministic policy
+
explicit approval policy
```

---

# 55. Canon Hash Chain

建议：

```text
commit_hash = sha256(
 parent_hash
 + change_set_hash
 + source_text_hash
 + permit_hash
 + sequence
)
```

目的：

```text
detect accidental mutation
ensure lineage
```

不是区块链。

---

# 56. Snapshot Hash

Snapshot 也可：

```text
snapshot_hash
```

用于：

```text
staleness
context provenance
rebuild verification
```

---

# 57. Source Artifact Binding

每个 Commit 必须能追溯：

```text
chapter
scene
revision
```

以及 source text。

---

# 58. Scene vs Chapter Commit

Phase 1 推荐：

```text
Chapter-level Canon Commit
```

Scene 产生 Delta，但聚合到章节。

原因：

```text
simpler transaction boundary
```

未来可支持：

```text
scene commit
```

用于复杂长章。

---

# 59. Chapter Aggregation

多个 SceneDelta：

```text
Scene 1
Scene 2
Scene 3
```

聚合时必须检查内部：

```text
order
conflict
duplicate mutation
temporal consistency
```

---

# 60. Candidate Rejection

失败 Candidate：

```text
never touches Canon
```

可以存：

```text
experiment artifact
```

但 authority = draft/diagnostic。

---

# 61. Repair

Repair 输入：

```text
Candidate Text
Validation Findings
Protected Facts
```

输出：

```text
new Candidate
new hash
new Delta
```

必须重新完整验证。

不能继承旧 Permit。

---

# 62. Rollback

Canonical transaction 未提交前：

```text
rollback = discard proposal
```

Commit 后不能“数据库 rollback 历史”。

应该：

```text
compensating / retcon commit
```

---

# 63. Undo Semantics

UI “撤销”必须区分：

```text
uncommitted undo
vs
committed retcon
```

绝不能用同一个动作隐藏语义。

---

# 64. Canon Store Boundary

只有 Canon Repository/Commit Service 可以执行：

```text
append_commit
advance_head
```

其他模块：

```text
read-only
```

---

# 65. Architecture Fitness

CI 必须检查：

```text
Writer cannot import Canon write repository
Reviewer cannot import Canon write repository
Reference module cannot import Canon write repository
Market module cannot import Canon write repository
Only CanonCommitService may advance head
```

---

# 66. Workflow Integration

Workflow 可以：

```text
request commit
wait commit
observe commit
```

但不能：

```text
own canon state
```

Workflow retry 不能重建另一套 Canon。

---

# 67. Storage Independence

本规范不强制：

```text
PostgreSQL
SQLite
EventStore
```

但实现必须满足语义。

Phase 1 推荐：

```text
PostgreSQL
```

原因：

- CAS；
- transaction；
- constraints；
- JSONB extension；
- mature tooling。

---

# 68. Suggested Tables

仅作为实现建议：

```text
canon_heads
canon_commits
canon_events
canon_snapshots
commit_permits
change_sets
retcon_requests
artifact_lineage
```

---

# 69. CanonHead Schema Constraints

数据库级：

```text
UNIQUE(project_id, branch_id)
UNIQUE(commit_id)
UNIQUE(branch_id, sequence)
```

---

# 70. Append-only Protection

生产数据库可考虑：

```text
deny UPDATE/DELETE
```

对 committed events。

修改通过新 Commit。

---

# 71. Schema Versioning

CanonEvent 必须：

```text
schema_version
```

Projector 必须支持：

```text
old version migration
```

---

# 72. Canon Migration

软件 Schema 升级与小说 Retcon 是两回事。

## Schema Migration

```text
representation changes
meaning same
```

## Retcon

```text
story meaning changes
```

必须完全区分。

---

# 73. Canon Rebuild Test

CI 至少定期验证：

```text
snapshot stored
==
snapshot rebuilt from log
```

---

# 74. Long-run Integrity Test

30/100/300 章：

随机抽：

```text
head
snapshot
events
```

验证 hash/sequence/parent。

---

# 75. Cross-project Isolation

任何 Canon key 必须包含：

```text
project_id
```

禁止 ID 冲突导致跨小说污染。

---

# 76. Cross-branch Isolation

同样：

```text
branch_id
```

必须参与：

```text
head
sequence
idempotency
snapshot
```

---

# 77. GenrePack Upgrade

项目升级 GenrePack：

```text
old pack
→ migration proposal
→ validation
→ human approval if major
→ Canon/Project config commit
```

不能 runtime 热替换。

---

# 78. Market Changes

MarketTrendSnapshot 更新：

```text
does not mutate Canon
```

最多：

```text
future planning evidence
```

---

# 79. Reference Changes

新增参考小说：

```text
does not mutate existing Canon
```

除非人类明确触发：

```text
Replan Future
```

---

# 80. Publish Boundary

`Canon Commit` 与 `Publish` 分开。

```text
Committed
≠
Published
```

Publish 是外部副作用。

---

# 81. Production State vs Canon State

Production State：

```text
GENERATED
VALIDATING
APPROVED
COMMITTED
PUBLISHED
```

Canon State：

```text
story facts
```

两者不得混淆。

---

# 82. Error Codes

建议：

```text
CANON-001 PARENT_MISMATCH
CANON-002 DUPLICATE_COMMIT
CANON-003 PERMIT_MISSING
CANON-004 PERMIT_STALE
CANON-005 TEXT_HASH_MISMATCH
CANON-006 CHANGESET_HASH_MISMATCH
CANON-007 IMMUTABLE_FACT_MUTATION
CANON-008 UNREGISTERED_EXTENSION
CANON-009 SNAPSHOT_STALE
CANON-010 REBUILD_MISMATCH
CANON-011 FENCING_REJECTED
CANON-012 BRANCH_CONFLICT
CANON-013 RETCON_APPROVAL_REQUIRED
CANON-014 AUTHORITY_VIOLATION
```

---

# 83. Observability

Trace：

```text
canon.load_head
canon.validate_changeset
canon.issue_permit
canon.commit
canon.project_snapshot
canon.rebuild
canon.retcon
```

Metrics：

```text
canon_commit_total
canon_commit_conflict_total
canon_commit_retry_total
canon_rebuild_failure_total
canon_retcon_total
canon_snapshot_stale_total
```

---

# 84. Audit Log

每次 Commit 记录：

```text
actor
workflow_run
chapter
scene
model calls
validation
human approval
policy version
```

---

# 85. Privacy / Sensitive Metadata

如果未来连接真实作者/平台账号：

Canon 不应存：

```text
API key
credentials
payment secret
```

这些属于 Security Infrastructure。

---

# 86. AI Coding Rules

AI 实现 Canon 相关代码时 MUST：

1. 不允许第二 Canon Store；
2. 不允许 Writer/Reviewer 直接 write；
3. 不允许 missing contract/permit 继续；
4. 不允许 placeholder parent/hash；
5. commit 必须 idempotent；
6. retry 必须安全；
7. snapshot 必须可重建；
8. committed events 不原地 edit；
9. unknown 不转为默认事实；
10. Retcon 必须显式；
11. branch 必须隔离；
12. test 必须覆盖 crash/retry/concurrency。

---

# 87. Required Tests

最低：

```text
TEST-CANON-001 draft cannot mutate canon
TEST-CANON-002 missing permit blocks
TEST-CANON-003 stale parent blocks
TEST-CANON-004 retry returns same commit
TEST-CANON-005 concurrent commit only one wins
TEST-CANON-006 snapshot rebuild equals stored
TEST-CANON-007 wrong text hash blocks
TEST-CANON-008 immutable fact mutation blocks
TEST-CANON-009 failed validation leaves head unchanged
TEST-CANON-010 branch isolation
TEST-CANON-011 retcon creates new commit
TEST-CANON-012 writer module cannot import write API
```

---

# 88. V1 Regression Mapping

直接覆盖 V1 教训：

```text
REG-V1-CHAR-001
→ identity validation before commit

REG-V1-CONTRACT-001
→ no contract => no permit

REG-V1-CONTRACT-002
→ placeholder hash impossible

REG-V1-CONTINUITY-001
→ hard failure => no permit

REG-V1-STATE-001
→ evidence does not directly mutate head

REG-V1-WINNER-001
→ text hash binding

REG-V1-RETRY-001
→ idempotent commit
```

---

# 89. Definition of Done

Canonical State v1.0 只有满足以下才能完成：

1. Genesis 可建立 initial Canon；
2. 一章正文经过 Delta → ChangeSet → Permit → Commit；
3. Draft 删除/失败不会改 Canon；
4. Commit retry 不重复；
5. 两个并发 commit 只有一个成功；
6. Snapshot 可完全重建；
7. wrong parent/hash 被硬拒绝；
8. Retcon 不覆写历史；
9. Genre Extension 使用同一提交路径；
10. Workflow 与 Canon State 完全分离；
11. CI 有 Architecture Fitness；
12. 能连续运行至少 30 章无 Canon fork。

---

# 90. Formal ADRs

建议接受：

## ADR-CANON-001
Canon changes only through explicit Canon Commit.

## ADR-CANON-002
Canon uses append-only commits/events plus rebuildable snapshots.

## ADR-CANON-003
NarrativeDelta must be validated into ChangeSet before commit.

## ADR-CANON-004
CommitPermit binds parent, source text, policy and ChangeSet hashes.

## ADR-CANON-005
Canon commits use optimistic concurrency and idempotency.

## ADR-CANON-006
Workflow State and Canon State are separate authorities.

## ADR-CANON-007
Committed history is immutable; story changes use Retcon commits.

## ADR-CANON-008
Genre extensions share the same Canon commit boundary.

## ADR-CANON-009
Snapshots are derived projections and may never become alternate truth.

## ADR-CANON-010
Branches are explicit isolated Canon histories.

---

# 91. Next Document

下一份规范应为：

# `MULTI_SOURCE_GENESIS_SPEC.md`

原因：

Genre、Narrative Domain、Canon 三块地基已经形成。

下一步应该定义：

```text
Idea Input
Reference Input
Hybrid Input
Corpus / Market Input
↓
Genesis Intake
↓
Reference Intelligence
↓
Evidence Pack
↓
Originality Guard
↓
Genesis Tournament
↓
GenesisSpec
↓
Genesis Commit
```

这一份将把“给一个想法”和“给一本到多本参考小说自动学习后原创”正式统一为一个 Genesis Compiler。

**END OF SPEC**
