# ANovel V2 Platform Foundation, Security, Provenance & Observability Specification

> **中文名**：ANovel V2 平台基础、安全、溯源与可观测性规范  
> **Document ID**：SPEC-PLATFORM-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `CANONICAL_STATE_SPEC.md`
> - `CONTEXT_INTELLIGENCE_SPEC.md`
> - `PRODUCTION_WORKFLOW_SPEC.md`
> - `QUALITY_EVALUATION_REPAIR_SPEC.md`
> - `CORPUS_EVALUATION_LEARNING_SPEC.md`
>
> **Primary Goal**：为 ANovel V2 建立统一的横切平台能力，使核心叙事生产系统在 Secrets、Authorization、Artifact Integrity、Audit、Provenance、Observability、Cost、Backup/Restore、Incident Response、Private Corpus 和 Software Supply Chain 等方面具备生产级约束。

---

# 0. Normative Summary

ANovel V2 Platform Foundation MUST 满足：

1. **Secrets never enter source, artifacts, prompts, logs or corpus.**
2. **All privileged actions require explicit authorization.**
3. **Canon write, Publish, Retcon and Policy Promotion are high-privilege actions.**
4. **Every persistent artifact has provenance and integrity metadata.**
5. **Every production run is traceable end-to-end.**
6. **Trace, Metric and Log are correlated but semantically distinct.**
7. **Logs are structured and sanitized.**
8. **Private corpus content inherits source privacy and rights policy.**
9. **Backups are tested through restore, not merely created.**
10. **Incidents are classified, contained, audited and closed with corrective action.**
11. **Dependency and container supply chain are pinned/scanned.**
12. **CI enforces architecture fitness and security gates.**
13. **Observability must not create a second source of narrative truth.**
14. **Audit records are append-oriented and tamper-evident where practical.**
15. **Cost and usage are first-class operational signals.**
16. **PII collection is minimized.**
17. **Artifact retention and deletion are policy governed.**
18. **Production and experiment environments are separated.**
19. **Feature flags cannot bypass Constitution/Canon/Genre hard rules.**
20. **Security failure is fail-closed for privileged operations.**

---

# 1. Why This Layer Exists

前面的规范已经回答：

```text
What is the book?
What is true?
What should happen?
What should the model see?
How does production run?
What quality is acceptable?
How does the system learn?
```

平台层回答的是：

```text
Who may act?
What can be trusted?
What happened operationally?
Can we prove it?
Can we recover?
Can secrets leak?
Can dependencies be trusted?
```

如果缺少这一层，Narrative Architecture 再好也无法安全进入长期生产。

---

# 2. Platform Boundary

Platform Foundation 负责：

```text
Identity
Authorization
Secrets
Artifact Integrity
Audit
Provenance
Trace
Metrics
Logs
Cost
Backup
Restore
Incident
Data Retention
Private Corpus Controls
Dependency/Supply Chain
Environment Separation
Architecture Fitness
```

不负责：

```text
Genre semantics
Canon semantics
Narrative planning
Quality rubric
Market interpretation
```

---

# 3. Security Principle

默认：

> **Least Privilege + Explicit Authority + Fail Closed**

所有高风险动作必须：

```text
authenticated actor
authorized scope
bound artifact hash
audited action
```

---

# 4. Actor Model

Actor 类型：

```text
HUMAN_USER
HUMAN_ADMIN
SYSTEM_SERVICE
WORKFLOW_WORKER
AI_WORKER
CI_BOT
EXTERNAL_CONNECTOR
```

AI Worker 默认：

```text
no direct privileged authority
```

---

# 5. Privileged Actions

至少：

```text
CANON_COMMIT
RETCON_APPROVE
GENRE_HARD_RULE_CHANGE
POLICY_PROMOTION
PUBLISH_EXTERNAL
SECRET_ROTATION
CORPUS_EXPORT
DATA_DELETE
ROLE_ASSIGNMENT
BACKUP_RESTORE
```

---

# 6. Authorization Model

推荐：

```text
RBAC + resource scope + action scope
```

后期可升级 policy-based。

Authorization 决策必须考虑：

```text
actor
role
project
branch
resource
action
risk
environment
```

---

# 7. No AI Self-Authorization

AI Worker 可以：

```text
propose
diagnose
prepare
```

不能：

```text
approve its own R3 retcon
grant itself role
rotate secrets
publish externally by default
promote policy without gate
```

---

# 8. Secret Management

Secrets 包括：

```text
provider API key
database credential
platform publishing token
object storage credential
signing key
webhook secret
```

---

# 9. Secret Storage

禁止：

```text
source code
README
Markdown spec
YAML fixture
Prompt
ContextArtifact
Corpus
Run Manifest
Log
Error stack
```

允许：

```text
runtime secret manager
environment injection
orchestrator secret mount
```

---

# 10. Secret Rotation

每个 secret：

```text
secret_id
owner
scope
created_at
last_rotated_at
rotation_policy
status
```

---

# 11. Secret Leak Incident

任何确认 secret leak：

```text
P0
```

最低动作：

```text
revoke
rotate
scan history
identify exposure
audit usage
document incident
```

---

# 12. Secret Scanning

CI 必须有：

```text
secret scan
```

覆盖：

```text
working tree
generated artifacts
fixtures
archives
Git history where practical
```

---

# 13. Log Sanitization

日志必须通过：

```text
LogSanitizer
```

过滤：

```text
authorization headers
api keys
tokens
credentials
private corpus content
large candidate text
personal data
```

---

# 14. Structured Logs

统一字段：

```text
timestamp
level
service
environment
project_id
branch_id
run_id
stage_id
trace_id
span_id
event
error_code
```

敏感字段：

```text
redacted
```

---

# 15. Logging Levels

建议：

```text
ERROR
WARN
INFO
DEBUG
TRACE
```

Production 默认：

```text
INFO
```

不得为调试长期开启全文 Prompt/正文日志。

---

# 16. Audit Log

Audit 与普通 Log 不同。

Audit 记录：

```text
who
did what
to which resource
with what authority
when
result
bound hashes
```

---

# 17. Audit Events

至少：

```text
CANON_COMMIT
RETCON_REQUEST
RETCON_APPROVE
PUBLISH
POLICY_PROMOTION
ROLE_CHANGE
SECRET_ROTATE
CORPUS_EXPORT
DATA_DELETE
BACKUP_RESTORE
CONFIG_CHANGE
```

---

# 18. Audit Integrity

Audit SHOULD：

```text
append-oriented
immutable by ordinary users
retention protected
```

可使用：

```text
hash chaining
WORM storage
restricted table permissions
```

视阶段选择。

---

# 19. Artifact Integrity

所有关键 Artifact：

```text
content_hash
schema_version
producer
created_at
provenance
```

关键 Artifact 包括：

```text
GenesisSpec
GenrePack
Plan
Contract
ContextArtifact
Candidate
NarrativeDelta
ChangeSet
QualityReport
CommitPermit
CanonCommit
BenchmarkRun
PromotionDecision
```

---

# 20. Hash Semantics

Hash 应基于：

```text
canonical serialization
```

避免 JSON key 顺序导致无意义差异。

---

# 21. Immutable Artifact Rule

关键 Artifact 创建后：

```text
never overwrite in place
```

修改：

```text
new artifact version
```

---

# 22. Provenance

Provenance 回答：

```text
who produced this?
from what inputs?
with what version?
under what policy?
```

---

# 23. ProvenanceRecord

至少：

```text
artifact_id
artifact_type
producer_type
producer_ref
input_refs
input_hashes
code_version
schema_version
policy_versions
created_at
```

---

# 24. Run Lineage

完整 Chapter lineage：

```text
Genesis
→ Plan
→ Contract
→ Context
→ ModelRun
→ Candidate
→ Delta
→ Quality
→ Repair
→ Permit
→ CanonCommit
→ Publish
```

---

# 25. Lineage Rule

任意最终 Chapter 应能回答：

> 它由哪些输入和决策产生？

---

# 26. OpenLineage-style Mapping

可映射：

```text
Job
Run
Input
Output
Facet
```

但内部 Canon/Artifact ID 仍由 ANovel 自己定义。

---

# 27. Observability Pillars

正式采用：

```text
Traces
Metrics
Logs
```

三者不可互相替代。

---

# 28. Trace

Trace 回答：

> 一次请求/生产链发生了什么？

层级：

```text
WorkflowRun
└─ Chapter
   ├─ Plan
   ├─ Contract
   ├─ Context
   ├─ Model
   ├─ Extract
   ├─ Validate
   ├─ Repair
   └─ Commit
```

---

# 29. Span

每个 Span：

```text
trace_id
span_id
parent_span_id
operation
start
end
status
attributes
```

---

# 30. Trace Attributes

建议：

```text
project_id
branch_id
run_id
chapter_id
stage_id
model_role
provider
model
genre_pack
workflow_version
quality_policy_version
```

禁止放：

```text
secret
full private text
```

---

# 31. Metrics

Metrics 回答：

> 系统整体表现如何？

---

# 32. Core Operational Metrics

至少：

```text
workflow_success_rate
stage_failure_rate
stage_latency
retry_rate
resume_rate
checkpoint_failure
commit_conflict
publish_failure
```

---

# 33. Model Metrics

```text
model_call_total
provider_error_rate
latency
input_tokens
output_tokens
cost
fallback_rate
structured_output_failure
```

---

# 34. Narrative Production Metrics

仅作为 operational/quality signals：

```text
repair_rate
hard_violation_rate
genre_drift
canon_conflict
promise_debt
context_compile_failure
```

---

# 35. Metric Label Discipline

避免高基数 label：

```text
full prompt
full chapter text
user freeform title
```

否则监控系统爆炸。

---

# 36. Cost Monitoring

每个 ModelRun：

```text
token usage
provider
model
currency
estimated cost
actual cost
```

聚合：

```text
per chapter
per genre
per stage
per model
per workflow
```

---

# 37. Cost Anomaly

例如：

```text
Chapter cost > baseline * threshold
```

触发：

```text
WARN / BLOCK depending policy
```

---

# 38. Budget vs Cost

Budget：

```text
what may be spent
```

Cost：

```text
what was spent
```

必须分离。

---

# 39. Availability / SLO

Phase 1 不需要过度复杂 SLA。

但建议定义内部 SLO：

```text
workflow recoverability
commit integrity
backup restore
secret exposure = zero tolerance
```

---

# 40. Service Health

关键组件：

```text
database
object store
model providers
workflow executor
queue
telemetry collector
```

---

# 41. Environment Separation

至少：

```text
DEV
TEST
STAGING
PRODUCTION
```

Production secret/data 不得默认复制到 DEV。

---

# 42. Experiment Isolation

Experiment 可以读取：

```text
approved corpus copy
```

不能随意写：

```text
production Canon
```

---

# 43. Production Database Access

开发/AI Agent 默认：

```text
no direct production DB mutation
```

通过 Service/API。

---

# 44. Private Corpus

用户上传小说、草稿、资料可能是私有内容。

必须：

```text
source owner
access scope
reuse policy
retention
export policy
```

---

# 45. Private Corpus Inheritance

派生：

```text
BookNarrativeProfile
ReferenceEvidencePack
Embedding
Summary
```

默认继承 source privacy。

不能因为“抽象过”就自动公开。

---

# 46. PII Minimization

ANovel 核心通常不需要大量个人信息。

只收集：

```text
necessary account/operational data
```

避免：

```text
unneeded personal profile
```

---

# 47. Content Retention

不同类型：

```text
workflow logs
model artifacts
candidate drafts
published chapters
private references
audit logs
backups
```

各自 retention policy。

---

# 48. Deletion Semantics

删除要区分：

```text
logical deactivation
artifact retention
legal deletion
backup expiry
```

---

# 49. Backup

至少备份：

```text
Canon Store
Artifact metadata
Workflow state
Policy/config registry
Corpus metadata
Audit
```

---

# 50. Backup Policy

定义：

```text
frequency
retention
encryption
location
restore owner
```

---

# 51. Restore Test

最重要原则：

> Backup not tested by restore is not a reliable backup.

必须定期：

```text
restore into isolated environment
verify hashes
rebuild Canon snapshots
verify workflow metadata
```

---

# 52. Disaster Recovery

灾难场景：

```text
primary DB lost
object storage corruption
bad migration
secret compromise
deployment rollback
```

---

# 53. Recovery Priority

优先：

```text
Canon integrity
Audit
Workflow resumability
Artifacts
Derived projections
```

Projection 可重建，Canon 不可丢。

---

# 54. RPO / RTO

Phase 1 可先定义内部目标：

```text
RPO
RTO
```

不必承诺外部 SLA。

---

# 55. Migration Safety

数据库 migration：

```text
versioned
reviewed
tested on realistic snapshot
rollback/forward-fix plan
```

---

# 56. Destructive Migration

删除/改语义字段：

```text
requires explicit migration review
```

尤其 Canon 表。

---

# 57. Data Integrity Check

定期检查：

```text
Canon hash chain
Snapshot rebuild
Artifact hash
Foreign keys
Orphan lineage
```

---

# 58. Incident Management

Incident：

```text
P0
P1
P2
P3
```

---

# 59. P0 Examples

```text
Canon corruption
secret leak
cross-project data leak
unauthorized publish
lost production data
private corpus exposure
```

---

# 60. P1 Examples

```text
repeated duplicate billing
workflow unable to resume
systematic genre gate bypass
backup failure
```

---

# 61. Incident Lifecycle

```text
DETECTED
TRIAGED
CONTAINED
MITIGATED
RECOVERED
POSTMORTEM
CLOSED
```

---

# 62. Incident Record

至少：

```text
incident_id
severity
detected_at
affected_scope
timeline
root_cause
containment
recovery
corrective_actions
owners
```

---

# 63. Postmortem

重点：

```text
what happened
why controls failed
what prevents recurrence
```

不是追责文档。

---

# 64. Security Incident Evidence

保护：

```text
logs
audit
hashes
access records
```

避免事故期间清理关键证据。

---

# 65. Dependency Management

所有 Runtime dependency：

```text
pinned / lockfile
```

禁止生产：

```text
unbounded latest
```

---

# 66. Supply Chain

至少：

```text
dependency scan
vulnerability scan
license awareness
container image digest
SBOM where practical
```

---

# 67. CI Security Gates

至少：

```text
secret scan
dependency scan
schema validation
architecture fitness
tests
migration check
```

---

# 68. SBOM

Phase 1 可以生成：

```text
SPDX/CycloneDX
```

后期进入 release artifact。

---

# 69. Container / Runtime Image

如果容器化：

```text
pin base image digest
minimal image
non-root where possible
read-only fs where practical
```

---

# 70. Feature Flags

Feature Flag 可以：

```text
enable experimental evaluator
route model
turn on shadow mode
```

不能：

```text
disable Canon validation in production
bypass hard Genre rule
skip authorization
```

---

# 71. Unsafe Mode

如果存在开发 Unsafe Mode：

```text
DEV/TEST only
```

Production 必须硬禁。

---

# 72. Authorization Audit

任何授权拒绝/允许都可审计。

尤其：

```text
Canon
Retcon
Publish
Corpus export
Policy promotion
```

---

# 73. API Boundary

内部服务/API：

```text
typed request
auth
validation
rate limits where needed
```

---

# 74. Input Validation

所有外部输入：

```text
schema
size
type
encoding
```

验证。

---

# 75. File Upload

Reference/corpus upload 需检查：

```text
file type
size
malware scan where practical
archive bomb
content hash
```

---

# 76. Path Safety

不得：

```text
user-controlled arbitrary filesystem path
```

直接进入 Runtime。

---

# 77. Prompt Injection Boundary

外部参考文本可能包含：

```text
instructions
malicious content
```

Reference 内容必须作为：

```text
data
```

而不是 system instruction。

---

# 78. Prompt Instruction Authority

优先：

```text
system policy
project constitution
role prompt
contract/context data
external content
```

外部内容不能升级为 instruction。

---

# 79. Tool Authorization

未来 Model Tool Use：

```text
allowlist by role
scope
budget
```

Writer 不应拥有：

```text
publish tool
secret tool
canon write tool
```

---

# 80. Egress Control

高敏环境可限制：

```text
which provider receives private corpus
```

ModelPolicy 必须支持：

```text
data residency / provider allowlist
```

---

# 81. Provider Data Policy

每个 Provider route 记录：

```text
allowed data classes
private content allowed?
retention policy known?
```

---

# 82. Provenance vs Audit

Provenance：

> Artifact 从哪里来？

Audit：

> 谁做了什么高权限动作？

两者不可混为一表。

---

# 83. Observability vs Business Analytics

Telemetry：

```text
system health
```

Reader/Market analytics：

```text
product behavior
```

分离存储和语义。

---

# 84. Trace Sampling

Production 可：

```text
sample low-risk traces
```

但：

```text
Canon Commit / Incident / Error
```

应保留完整关联记录。

---

# 85. Log Retention

不同级别：

```text
DEBUG short
INFO medium
AUDIT long
```

具体周期由部署环境决定。

---

# 86. Privacy-safe Telemetry

优先存：

```text
hash
id
count
duration
```

而不是全文内容。

---

# 87. Artifact Store

大文本 Artifact 可进：

```text
object storage
```

Metadata 在 DB。

---

# 88. Artifact Addressing

推荐：

```text
artifact_id
content_hash
storage_ref
```

---

# 89. Object Immutability

关键 artifact bucket：

```text
versioned / write-once semantics where practical
```

---

# 90. Orphan Cleanup

只有确认：

```text
not referenced
retention expired
not audit-protected
```

才能删除。

---

# 91. Architecture Fitness

CI 必须自动验证架构铁律。

例如：

```text
Writer cannot import Canon write API
Reference module cannot import Canon write API
Market module cannot mutate Canon
Only Workflow owns production transitions
Only Canon service advances head
Hard rules cannot be disabled by feature flag
```

---

# 92. Fitness Test Classification

```text
IMPORT_RULE
DEPENDENCY_RULE
SCHEMA_RULE
STATE_WRITER_RULE
AUTHORITY_RULE
SECURITY_RULE
```

---

# 93. Fitness Failure

Production branch：

```text
CI BLOCK
```

不能 warning-only。

---

# 94. Release Manifest

每个 Release：

```text
code commit
schema versions
workflow version
policy versions
dependency lock hash
image digest
SBOM ref
migration ref
```

---

# 95. Production Deployment

最低：

```text
health check
migration gate
secret check
config validation
smoke test
```

---

# 96. Rollback

Deployment rollback：

```text
code/config rollback
```

不能随意 rollback Canon data。

---

# 97. Database Rollback Caution

如果新版本已经写入新 Canon：

```text
cannot blindly restore old database
```

必须使用：

```text
forward fix / compatibility
```

避免丢历史。

---

# 98. Observability Dashboard

建议至少：

```text
Run Health
Provider Health
Cost
Quality Gate
Canon Integrity
Retry/Resume
Backup/Restore
Security Events
```

---

# 99. Alerting

告警：

```text
P0 security
Canon integrity
sustained provider failure
cost anomaly
backup failure
restore test failure
workflow blocked spike
```

---

# 100. Alert Fatigue

避免所有 WARN 发通知。

使用：

```text
severity
rate
duration
impact
```

---

# 101. Cost Alert

例如：

```text
per chapter cost x2 baseline
```

需检查：

```text
repair loop
context bloat
provider change
```

---

# 102. Context Token Alert

监控：

```text
mandatory ratio
trimming
context too large
```

---

# 103. Canon Integrity Alert

任何：

```text
snapshot rebuild mismatch
hash chain mismatch
head parent anomaly
```

均高优先级。

---

# 104. Backup Alert

```text
backup missed
restore validation failed
```

至少 P1。

---

# 105. Private Corpus Access Alert

异常：

```text
bulk export
cross-project access
forbidden provider route
```

触发安全事件。

---

# 106. Operational Runbook

需要：

```text
provider outage
DB issue
workflow stuck
Canon conflict
secret leak
backup failure
publish failure
```

Runbook。

---

# 107. Security Runbook

Secret Leak：

```text
revoke
rotate
scan
contain
audit
postmortem
```

Cross-project leak：

```text
stop service
revoke access
scope exposure
notify owners
restore isolation
```

---

# 108. Backup Runbook

```text
verify backup
restore isolated
validate Canon
validate Workflow
promote recovery
```

---

# 109. Data Classification

建议：

```text
PUBLIC
INTERNAL
PRIVATE
SECRET
```

---

# 110. Example Classification

```text
public market metadata → PUBLIC
internal benchmark → INTERNAL
user manuscript → PRIVATE
API key → SECRET
```

---

# 111. Data Handling by Class

每个 class 定义：

```text
storage
logging
provider routing
export
retention
```

---

# 112. Encryption

Production SHOULD：

```text
TLS in transit
encryption at rest
```

尤其：

```text
private corpus
secrets
backups
```

---

# 113. Key Management

加密 key 与 data store 分离管理。

---

# 114. Time Synchronization

Audit/trace 依赖：

```text
consistent UTC timestamps
```

UI 再本地化。

---

# 115. IDs

关键对象：

```text
UUID/ULID
```

避免可预测自增暴露资源规模。

---

# 116. Clock vs Story Time

平台时间：

```text
system timestamp
```

小说时间：

```text
story_time
```

严格分离。

---

# 117. Test Data

测试中禁止使用真实 production secrets/private content。

---

# 118. Synthetic Fixtures

优先：

```text
synthetic novels
synthetic users
synthetic tokens
```

---

# 119. Production Copy for Test

若必须：

```text
sanitize
scope
approve
expire
```

---

# 120. Model Provider Outage

Workflow：

```text
TRANSIENT
```

可：

```text
retry
fallback if policy allows
pause
```

不能自动降低 narrative hard gate。

---

# 121. Provider Compromise

如果 provider route 被禁止：

```text
disable route
invalidate credentials
block private data egress
```

---

# 122. External Publishing Connector

必须独立权限：

```text
PUBLISH_EXTERNAL
```

Writer/Reviewer 无权直接调用。

---

# 123. Publish Audit

记录：

```text
platform
artifact hash
actor
approval
external receipt
```

---

# 124. Data Export

Corpus/Project export：

```text
authorized
audited
scoped
```

---

# 125. Data Import

导入历史项目：

```text
schema validate
rights metadata
provenance
quarantine if unknown
```

---

# 126. Backup Scope

最小恢复集：

```text
Canon
Workflow
Artifact Metadata
Policies
Audit
Corpus Metadata
```

大文本对象存储也需要对应策略。

---

# 127. Restore Integrity

恢复后：

```text
Canon rebuild
hash validation
artifact existence
lineage consistency
```

---

# 128. Platform Error Codes

建议：

```text
PLAT-SEC-001 UNAUTHORIZED
PLAT-SEC-002 SECRET_DETECTED
PLAT-SEC-003 PRIVATE_DATA_ROUTE_BLOCKED
PLAT-SEC-004 CROSS_PROJECT_ACCESS
PLAT-AUD-001 AUDIT_WRITE_FAILED
PLAT-ART-001 HASH_MISMATCH
PLAT-ART-002 ORPHAN_ARTIFACT
PLAT-OBS-001 TRACE_CONTEXT_MISSING
PLAT-COST-001 BUDGET_ANOMALY
PLAT-BKP-001 BACKUP_FAILED
PLAT-BKP-002 RESTORE_VALIDATION_FAILED
PLAT-SUP-001 VULNERABLE_DEPENDENCY
PLAT-SUP-002 UNPINNED_RUNTIME_DEPENDENCY
PLAT-INC-001 P0_INCIDENT
```

---

# 129. Required CI Gates

最低：

```text
Unit
Contract
Schema
Architecture Fitness
Secret Scan
Dependency Scan
Migration Validation
Security Static Checks
Real Provider Contract Test (controlled)
```

---

# 130. Branch Protection

Main/Release：

```text
CI required
review required
no direct force push
```

具体由 Repo Governance 决定。

---

# 131. Release Gate

Release 前：

```text
all hard CI gates pass
migration ready
release manifest created
backup verified
rollback/forward plan ready
```

---

# 132. AI Coding Rules

AI 实现 Platform Foundation 时 MUST：

1. 不把 Secrets 写入代码/文档/fixture；
2. 不让 AI Worker 自动获得高权限；
3. 不把全文正文作为普通日志字段；
4. 不用 telemetry 作为 Canon；
5. 不让 feature flag 关闭 hard rule；
6. 不创建平行 Audit/Provenance 真值；
7. 不删除失败/incident evidence；
8. 不使用 unpinned runtime dependency；
9. 不把 private corpus 路由给未授权 provider；
10. 不宣称“有 backup”而没有 restore test。

---

# 133. Suggested Repository Layout

```text
src/anovel/platform/
  security/
  authorization/
  secrets/
  audit/
  provenance/
  observability/
  cost/
  backup/
  incident/
  retention/
  supply_chain/

specs/platform/
  schemas/
  policies/
  runbooks/

tests/platform/
  security/
  integrity/
  backup/
  architecture_fitness/
```

---

# 134. Minimum APIs

```text
authorize(actor, action, resource) -> AuthorizationDecision
record_audit(event) -> AuditReceipt
record_provenance(record) -> ProvenanceReceipt

start_trace(operation, attrs) -> TraceContext
record_metric(metric, value, labels)
write_log(event)

verify_artifact_integrity(artifact) -> IntegrityResult
create_backup(scope) -> BackupRecord
validate_restore(backup) -> RestoreValidation

declare_incident(event) -> IncidentRecord
close_incident(incident, evidence) -> IncidentClosure
```

---

# 135. Required Tests

```text
TEST-PLAT-001 secret_never_logged
TEST-PLAT-002 writer_cannot_publish
TEST-PLAT-003 ai_worker_cannot_self_authorize
TEST-PLAT-004 cross_project_access_denied
TEST-PLAT-005 private_corpus_route_policy_enforced
TEST-PLAT-006 artifact_hash_mismatch_detected
TEST-PLAT-007 audit_append_preserved
TEST-PLAT-008 canon_trace_lineage_complete
TEST-PLAT-009 feature_flag_cannot_disable_hard_gate
TEST-PLAT-010 backup_restore_rebuilds_canon
TEST-PLAT-011 restore_detects_missing_artifact
TEST-PLAT-012 unpinned_dependency_blocks_release
TEST-PLAT-013 secret_scan_blocks_ci
TEST-PLAT-014 publish_receipt_audited
TEST-PLAT-015 production_secret_absent_from_test_fixture
```

---

# 136. V1 Regression Mapping

```text
historical secret/API exposure risk
→ secret scan + log sanitization + P0 procedure

weak provenance
→ artifact provenance + run lineage

missing/weak CI
→ hard CI gates

unlocked dependencies
→ pinning + supply chain gate

mixed source/generated/experiment files
→ governed data classification + corpus registry + artifact store

hidden production truth
→ trace + audit + lineage
```

---

# 137. Definition of Done

Platform Foundation v1.0 完成必须证明：

1. Secret scan 可阻止 CI；
2. Production log 不含 secret/private full text；
3. Canon/Publish/Retcon 权限独立；
4. AI Worker 无法自授权；
5. 每个最终 Chapter 可追溯完整 lineage；
6. Artifact hash corruption 可检测；
7. Cross-project/private corpus access 可阻止；
8. Backup 可以真实 restore；
9. Restore 后 Canon Snapshot 可重建；
10. Dependency 锁定与扫描进入 CI；
11. P0/P1 Incident 有 Runbook；
12. Release Manifest 可重建生产配置。

---

# 138. Formal ADRs

建议接受：

## ADR-PLATFORM-001
Secrets are injected at runtime and never stored in narrative artifacts.

## ADR-PLATFORM-002
Privileged operations require explicit authorization and audit.

## ADR-PLATFORM-003
Every persistent production artifact carries provenance and integrity metadata.

## ADR-PLATFORM-004
ANovel uses correlated traces, metrics and structured logs.

## ADR-PLATFORM-005
Private corpus privacy and rights propagate to derived artifacts.

## ADR-PLATFORM-006
Backup correctness is proven through restore validation.

## ADR-PLATFORM-007
CI enforces architecture fitness, security and supply-chain gates.

## ADR-PLATFORM-008
Feature flags cannot bypass constitutional or hard narrative controls.

## ADR-PLATFORM-009
Production and experiment environments are logically separated.

## ADR-PLATFORM-010
Release artifacts include a complete configuration and dependency manifest.

---

# 139. Architecture Documentation Phase Closure

到此为止，ANovel V2 前期核心架构规范已覆盖：

```text
Governance
Research
Genre
Narrative Domain
Canon
Genesis
Planning
Context
Workflow
Quality
Learning
Platform Foundation
```

下一步不应继续无限增加“概念型规范”。

应该进入：

# `IMPLEMENTATION_PLAN.md`

把全部 normative specs 转换成：

```text
Phase
Milestone
Sprint
Task
Dependency
Owner Role
Artifact
Acceptance Criteria
DoD
CI Gate
Certification Gate
```

并明确第一阶段只实现：

```text
Genre Kernel
Narrative Core
Canon
Chapter Workflow
Context Compiler
Q0-Q3
Patch Repair
Urban Business Pack
Eastern Fantasy Pack
30-Chapter Certification
```

而不是一次实现所有愿景。

**END OF SPEC**
