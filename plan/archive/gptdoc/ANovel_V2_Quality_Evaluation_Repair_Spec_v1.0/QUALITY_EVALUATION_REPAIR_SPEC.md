# ANovel V2 Quality Evaluation, Evidence Calibration & Repair Specification

> **中文名**：ANovel V2 质量评价、证据校准与修复规范  
> **Document ID**：SPEC-QUALITY-0001  
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
> - `PRODUCTION_WORKFLOW_SPEC.md`
>
> **Primary Goal**：建立 ANovel V2 的统一质量证据体系、提交门禁、语义评价、人工校准与修复协议，使“章节质量”不再依赖单一 LLM 主观评分，而是形成可验证、可诊断、可修复、可校准、可长期回归的质量闭环。

---

# 0. Normative Summary

ANovel V2 Quality System MUST 满足：

1. **Quality is multi-layered, not one score.**
2. **Deterministic truth and model judgment are separate evidence classes.**
3. **Hard gates are explicit and fail-closed.**
4. **A high LLM score cannot override a deterministic violation.**
5. **Reviewer output is evidence, not Canon authority.**
6. **The system MUST distinguish factual correctness from narrative preference.**
7. **Genre correctness, Canon correctness and transition correctness are independent gates.**
8. **Commercial prediction is diagnostic, not market truth.**
9. **Human evaluation is a distinct evidence level.**
10. **Reader/market outcomes are the strongest commercial calibration signal.**
11. **Repair is diagnosis-driven and patch-first by default.**
12. **Every repair produces a new candidate hash and requires revalidation.**
13. **Protected facts MUST survive repair.**
14. **Whole-chapter rewrite is reserved for structural failure.**
15. **Same-model generator/reviewer bias MUST be measurable and controlled.**
16. **Golden Set labels require provenance and authority.**
17. **Pairwise comparison is preferred to unsupported absolute scoring where appropriate.**
18. **Quality metrics MUST NOT be displayed as real business KPIs unless backed by real signals.**
19. **Quality evidence is versioned and linked to exact candidate/context/contract hashes.**
20. **Regression suites are first-class product assets.**

---

# 1. Why Quality Needs Its Own Architecture

AI 小说系统最常见的错误之一是：

```text
Writer
→ Reviewer
→ "8.8/10"
→ PASS
```

这无法回答：

- 主角是不是写错了？
- 角色是否知道了不该知道的信息？
- Genre 是否漂移？
- Realm/Equity/Timeline 是否非法变化？
- Contract 要求的状态变化是否真的发生？
- 章节是否有推进？
- 人物是否仍有独特性？
- 商业潜力评分是否只是 Judge 偏好？
- 修复后是否引入新错误？

因此 V2 必须建立分层质量模型。

---

# 2. Quality Ladder

V2 正式采用 Q0–Q8：

```text
Q0 Deterministic Integrity
Q1 Canon Consistency
Q2 Genre Fidelity
Q3 Transition Correctness
Q4 Narrative Quality
Q5 Character Quality
Q6 Commercial Proxy
Q7 Originality
Q8 Human / Reader / Market Truth
```

这些层的 Authority 不相同。

---

# 3. Q0 — Deterministic Integrity

Q0 处理可确定验证的问题。

例如：

```text
schema invalid
missing required artifact
hash mismatch
wrong project/branch
missing contract
stale contract
missing permit prerequisite
unregistered extension
invalid enum
duplicate entity id
invalid parent
```

### Authority

```text
HARD GATE
```

Q0 fail：

```text
NO COMMIT
```

---

# 4. Q1 — Canon Consistency

Q1 验证 Candidate / NarrativeDelta 是否与 Canon 冲突。

至少：

```text
identity
lifecycle
timeline
location
knowledge
relationship
capability
resource
promise
world law
```

### Example

Canon：

```text
char_A.lifecycle = DEAD
```

Candidate：

```text
char_A 在会议室发言
```

无合法 Retcon/复活机制：

```text
Q1 HARD FAIL
```

---

# 5. Q2 — Genre Fidelity

Q2 使用 Genre Constitution 和 GenrePack 验证：

```text
Reality Model
World Law
Forbidden Mechanics
Progression Rules
Genre Extensions
Fusion Policy
Period Constraints
```

### Example

`urban.business.realistic`

出现：

```text
灵气复苏
```

若无 Fusion Policy：

```text
Q2 HARD FAIL
```

---

# 6. Q3 — Transition Correctness

Q3 比较：

```text
RequiredTransition
ForbiddenTransition
ProtectedFacts
```

与：

```text
ActualNarrativeDelta
```

核心问题：

> 这一 Scene/Chapter 是否真的完成了 Contract 要求？

### Authority

对明确机器可验证的 Transition：

```text
HARD GATE
```

---

# 7. Q4 — Narrative Quality

Q4 关注：

```text
scene purpose
causal progression
narrative density
conflict quality
pacing
information flow
setup/payoff
hook quality
clarity
emotional residue
```

Q4 大部分属于：

```text
semantic evaluative evidence
```

默认不能覆盖 Q0–Q3。

---

# 8. Q5 — Character Quality

Q5 关注：

```text
motivation
decision plausibility
voice differentiation
relationship dynamics
character specificity
agency
emotional continuity
opponent adaptation
supporting cast usefulness
```

关键：

> Character Consistency 与 Character Quality 不同。

人物没有事实矛盾，不代表人物写得好。

---

# 9. Q6 — Commercial Proxy

Q6 可以评估：

```text
reader promise clarity
continuation intent
payoff strength
hook effectiveness
early conversion hypothesis
retention hypothesis
fatigue risk
subscription motivation hypothesis
```

### Critical

必须明确命名：

```text
Commercial Proxy
```

而不是：

```text
Commercial Truth
```

---

# 10. Q7 — Originality

Q7 结合 Genesis Originality Firewall：

```text
lexical overlap
semantic overlap
event sequence similarity
character function mapping
relationship graph similarity
world signature similarity
progression similarity
signature scene collision
```

如果 Reference 模式存在：

```text
Q7 becomes mandatory
```

---

# 11. Q8 — Human / Reader / Market Truth

Q8 包含：

```text
Human Blind Review
Editor Review
Real Reader Retention
Subscription
Paid Follow
Votes
Comments
Completion
Revenue
```

它是商业质量校准的最高现实层。

### Rule

Q8 数据必须带：

```text
population
sample size
period
platform
exposure
confidence
```

---

# 12. Evidence Levels

建议正式定义：

## E0 — Deterministic Evidence

例如：

```text
schema
hash
state
timeline
contract
numeric transition
```

最强机器证据。

## E1 — Structured Verified Evidence

例如：

```text
reference metadata
platform fact
human-approved fact
```

## E2 — Model Evaluation Evidence

例如：

```text
review
pairwise judgment
semantic diagnosis
```

## E3 — Simulated Reader / Commercial Evidence

例如：

```text
synthetic reader
pay intent prediction
retention prediction
```

## E4 — Human / Real Market Evidence

例如：

```text
blind human score
real retention
subscription
```

---

# 13. Evidence Authority

默认：

```text
E0 hard facts
> E1 verified evidence
> E2 model evaluation
> E3 simulation
```

商业校准：

```text
E4 real signal
```

可以用于反校准 E2/E3。

---

# 14. EvidenceRecord

所有质量判断输出：

```text
EvidenceRecord
```

至少：

```text
evidence_id
quality_layer
evidence_level
subject_hash
context_hash
contract_hash
producer
finding
severity
confidence
rationale
provenance
```

---

# 15. Severity

统一：

```text
INFO
WARN
REPAIR
HARD_FAIL
```

---

# 16. Finding Status

```text
OPEN
CONFIRMED
DISMISSED
REPAIRED
REGRESSION
WAIVED
```

---

# 17. Waiver

Hard Gate 不应轻易 waiver。

允许 waiver 的规则必须显式：

```text
waivable = true
required_authority = human
```

Genre/Canon 核心 hard violation 默认：

```text
not waivable
```

---

# 18. QualityDecision

最终质量决策不是一个分数。

输出：

```text
PASS
REPAIR_REQUIRED
HUMAN_REVIEW
BLOCKED
```

---

# 19. Hard Gate Precedence

如果：

```text
Q0/Q1/Q2/Q3 HARD_FAIL
```

即使：

```text
Q4 = 9.5
Q6 = 9.8
```

仍然：

```text
BLOCKED / REPAIR_REQUIRED
```

---

# 20. No Weighted Average Override

禁止：

```text
total_score =
0.1 * canon +
0.9 * prose

if total_score > 8:
  pass
```

因为致命错误不能被平均掉。

---

# 21. Semantic Rubrics

Q4–Q6 可以使用 Rubric。

Rubric 必须：

```text
versioned
dimensioned
anchored
```

例如 Narrative Density：

```text
LOW
MEDIUM
HIGH
```

配合标准定义，而不是自由打分。

---

# 22. Absolute Score Limitations

LLM 对：

```text
8.7 vs 8.9
```

通常没有可靠标尺。

因此：

- 用等级；
- 用 pairwise；
- 用 diagnosis；
- 用 calibrated threshold；

通常比小数分数更可靠。

---

# 23. Pairwise Evaluation

适用于：

```text
Candidate A vs B
Original vs Repair
Prompt version A vs B
Model A vs B
```

Judge 回答：

```text
A
B
TIE
UNCERTAIN
```

并输出维度级理由。

---

# 24. Blind Evaluation

Judge 不应知道：

```text
哪个是新模型
哪个是系统当前方案
哪个是 baseline
```

避免 status bias。

---

# 25. Judge Independence

推荐：

```text
Generator != Primary Judge
```

至少在关键校准任务中。

可以使用：

```text
different model family
human blind review
```

---

# 26. Same-family Bias

若 Writer、Reviewer、Repairer 全部使用同模型族：

必须记录：

```text
evaluation_dependency_risk
```

---

# 27. Multi-model Consensus

多模型结果不应简单：

```text
majority vote = truth
```

应保留：

```text
agreement
disagreement
confidence
dimension-specific split
```

---

# 28. Reviewer Role

Reviewer：

```text
produces evidence
```

不能：

```text
advance Canon
change ProductionState directly
issue CommitPermit by itself
```

---

# 29. Quality Aggregator

统一组件：

```text
QualityAggregator
```

输入：

```text
Q0..Q7 evidence
policy
risk
```

输出：

```text
QualityDecision
```

---

# 30. Quality Policy

QualityPolicy 定义：

```text
which checks required
which are hard
repair thresholds
human review thresholds
max repair loops
commercial diagnostic usage
```

---

# 31. Policy by Production Mode

例如：

```text
EXPERIMENT
STAGING
PRODUCTION
CERTIFICATION
```

Production 最严格。

---

# 32. Deterministic Validators

优先实现：

```text
schema
hash
identity
timeline
lifecycle
resource arithmetic
capability prerequisite
knowledge boundary
genre hard rules
contract transitions
```

---

# 33. Semantic Evaluators

适合：

```text
motivation
pacing
scene purpose
voice
emotional impact
payoff quality
genericness
```

---

# 34. Hybrid Validator

某些问题：

```text
deterministic trigger
+
semantic interpretation
```

例如：

> 是否出现新的重要人物但没有注册？

NER/LLM 可以发现候选，Domain validator 决定是否合法。

---

# 35. Diagnosis First

Semantic Reviewer 首先输出：

```text
Finding
```

而不是先给总分。

Finding 应包含：

```text
where
what
why
risk
repairability
evidence
```

---

# 36. Finding Location

尽量定位：

```text
scene
paragraph
span
entity
transition
```

这样 Repair 才能 patch-first。

---

# 37. Repairability

每个 Finding：

```text
LOCAL
SCENE
CHAPTER_STRUCTURE
PLAN_LEVEL
CANON_LEVEL
NOT_REPAIRABLE_IN_TEXT
```

---

# 38. RepairPlan

RepairPlan 输入：

```text
candidate hash
findings
protected facts
allowed delta
contract
canon parent
```

输出：

```text
patch targets
repair instructions
must preserve
must change
must not introduce
validation rerun
```

---

# 39. Patch-first Principle

默认顺序：

```text
local sentence patch
↓
paragraph patch
↓
scene patch
↓
chapter structural rewrite
```

不要一有错误就整章重写。

---

# 40. Why Patch-first

整章重写可能：

```text
fix A
break B
change voice
alter facts
create new delta
invalidate previous good parts
```

局部 patch 风险更小。

---

# 41. Protected Facts

Repair 必须保护：

```text
Canon facts
RequiredTransitions already satisfied
Character knowledge
Genre rules
Critical wording when approved
```

---

# 42. Allowed Delta

RepairPlan 应声明：

```text
what semantic changes are permitted
```

例如：

```text
dialogue wording only
motivation explanation only
scene pacing only
```

---

# 43. Repair Candidate

Repair 后：

```text
new candidate_id
new text_hash
```

旧 Candidate 仍保留。

---

# 44. Full Revalidation

任何 Repair 后：

```text
Q0–Q7
```

至少重新跑受影响层。

对不确定 dependency：

```text
full rerun
```

---

# 45. Repair Gain

记录：

```text
resolved_findings
remaining_findings
new_findings
pairwise_preference
cost
```

---

# 46. Repair Regression

如果修复引入新 Hard Fail：

```text
REGRESSION
```

优先回滚 repair candidate。

---

# 47. Repair Loop

建议：

```text
MAX_REPAIR_LOOPS = policy
```

超过：

```text
HUMAN_REVIEW
or
REGENERATE
```

---

# 48. Regenerate vs Repair

选择依据：

```text
finding scope
structural damage
repair cost
contract satisfaction
```

---

# 49. Whole-chapter Rewrite Conditions

例如：

```text
chapter goal not achieved
multiple scenes structurally wrong
narrative engine absent
protagonist agency fundamentally missing
large-scale causality broken
```

才进入：

```text
WHOLE_CHAPTER_REWRITE
```

---

# 50. Rewrite Is New Generation

整章 Rewrite：

```text
new candidate
new context binding if needed
new delta
new evaluation
```

旧 Permit 无效。

---

# 51. Quality Context

所有 Judge/Reviewer 必须绑定：

```text
candidate hash
Canon parent
Contract
GenrePack
Rubric
Context
```

---

# 52. Reviewer Information Leakage

评测商业潜力时不要告诉 Judge：

```text
这是当前系统最喜欢的版本
```

否则产生 anchoring。

---

# 53. Golden Set

Golden Set 是长期 Quality 校准资产。

应包含：

```text
positive
negative
boundary
genre violations
AI voice
padding
no conflict
character degradation
ending failure
continuity failure
knowledge leak
```

---

# 54. Golden Set Item

每个样本：

```text
sample_id
text
task
labels
label_authority
human_evaluations
source_rights
provenance
```

---

# 55. Golden Label Authority

严格区分：

```text
HUMAN_GOLD
EXPERT_GOLD
PLATFORM_FACT
AI_PROVISIONAL
```

AI-only label 不得伪装成人工 Gold。

---

# 56. Double-blind Human Review

重要校准：

- reviewer 不知道样本来源；
- reviewer 不知道模型版本；
- reviewer 独立评分；
- 后处理再计算 agreement。

---

# 57. Human Evaluation Dimensions

建议：

```text
genre fidelity
character credibility
narrative engagement
clarity
novelty
continuation intent
overall preference
```

---

# 58. Human Evaluation Is Not Perfect

人工也会：

```text
disagree
have taste bias
```

因此记录：

```text
reviewer id pseudonym
experience
confidence
```

---

# 59. Inter-rater Agreement

统计：

```text
agreement
Krippendorff alpha / kappa where suitable
```

只有任务适合时使用。

---

# 60. Calibration

目标：

> 让 AI 评价与人工/市场更接近。

不是：

> 让 AI 自己证明自己准确。

---

# 61. Calibration Dataset Split

必须区分：

```text
train/tune
validation
holdout
```

避免拿同一 Golden Set 反复调 Prompt 后再宣布高准确率。

---

# 62. Judge Calibration Metrics

根据任务选择：

```text
accuracy
precision/recall
rank correlation
pairwise agreement
false-negative rate
hard violation recall
```

---

# 63. Hard Violation Recall

Genre/Canon hard violation：

> False Negative 比 False Positive 更危险。

所以单独监控：

```text
hard_violation_recall
```

---

# 64. Commercial Proxy Calibration

Q6 应与未来真实：

```text
retention
paid follow
subscription
```

做 correlation / ranking validation。

在无真实数据前：

```text
Q6 = hypothesis
```

---

# 65. Reader Simulation

Synthetic Reader 可以用于：

```text
diagnosis
scenario testing
candidate comparison
```

不能作为：

```text
真实用户行为替代
```

---

# 66. Market Truth

真实市场数据必须记录：

```text
exposure
traffic source
chapter number
cohort
date
platform
```

不能只拿“订阅低”反推文字差。

---

# 67. Causal Humility

Reader metrics 受到：

```text
cover
title
traffic
competition
timing
price
platform policy
```

影响。

因此市场数据用于校准时必须保留 context。

---

# 68. Quality Metrics Storage

每个 metric：

```text
metric_id
definition
version
population
aggregation
```

禁止后续同名换算法。

---

# 69. Quality Score Naming

如果不是 calibrated metric：

不要叫：

```text
quality_score
commercial_score
success_probability
```

推荐：

```text
model_judgment_score
proxy_score
diagnostic_signal
```

---

# 70. Genericness Risk

V2 特别需要：

```text
generic dialogue
generic reaction
generic setting
template transition
repeated rhetorical structure
LLM summary voice
```

---

# 71. AI Voice Detection

AI Voice Checker 只能：

```text
diagnostic
```

除非经过强人工校准。

---

# 72. Repetition

跨章检测：

```text
phrase repetition
scene pattern repetition
hook repetition
conflict repetition
payoff repetition
reaction repetition
```

---

# 73. Long-run Quality

单章好不代表长篇好。

必须计算：

```text
drift
fatigue
promise debt
engine repetition
character flattening
progression inflation
```

---

# 74. 10-Chapter Review

重点：

```text
early promise
genre stability
character identity
engine viability
```

---

# 75. 30-Chapter Review

重点：

```text
arc completion
promise payoff
variation
relationship growth
repair rate
genre drift
```

---

# 76. 100-Chapter Review

重点：

```text
long-arc durability
state complexity
character memory
world expansion
fatigue
cost
```

---

# 77. 300-Chapter Review

重点：

```text
engine exhaustion
late-stage repetition
retcon rate
canon size
context quality
reader promise renewal
```

---

# 78. Quality Gate before Commit

推荐：

```text
Q0 PASS
Q1 PASS
Q2 PASS
Q3 PASS
Q4 no structural blocker
Q5 no critical character blocker
Q7 no high originality block
```

Q6：

```text
diagnostic by default
```

---

# 79. Human Gate

触发：

```text
R3 change
high originality risk
ambiguous hard conflict
repeated repair failure
retcon
publication policy
```

---

# 80. Commit Permit Integration

QualityAggregator 输出：

```text
QualityDecision
```

如果满足 CommitPolicy：

```text
CommitPermit may be issued
```

Reviewer 不能直接发 Permit。

---

# 81. Quality Artifact Immutability

每次 Review：

```text
new EvaluationArtifact
```

不要覆盖旧评价。

---

# 82. Evaluation Reproducibility

至少记录：

```text
rubric version
model
context hash
prompt hash
candidate hash
sampling
```

---

# 83. Pairwise Artifact

记录：

```text
candidate_a
candidate_b
blind labels
winner
confidence
dimension findings
judge
```

---

# 84. Quality Lineage

完整：

```text
Candidate
→ Evidence
→ Diagnosis
→ RepairPlan
→ Repaired Candidate
→ Evidence
→ QualityDecision
→ CommitPermit
```

---

# 85. Quality Error Codes

建议：

```text
QUAL-001 HARD_GATE_FAIL
QUAL-002 CANON_CONFLICT
QUAL-003 GENRE_VIOLATION
QUAL-004 REQUIRED_TRANSITION_MISSING
QUAL-005 KNOWLEDGE_LEAK
QUAL-006 CHARACTER_CRITICAL
QUAL-007 NARRATIVE_STRUCTURAL_FAILURE
QUAL-008 ORIGINALITY_BLOCK
QUAL-009 JUDGE_DISAGREEMENT
QUAL-010 CALIBRATION_INSUFFICIENT
QUAL-011 REPAIR_REGRESSION
QUAL-012 REPAIR_EXHAUSTED
QUAL-013 GOLD_LABEL_UNVERIFIED
QUAL-014 MARKET_SIGNAL_UNCALIBRATED
```

---

# 86. Quality Observability

Trace：

```text
quality.q0
quality.q1
quality.q2
quality.q3
quality.q4
quality.q5
quality.q6
quality.q7
quality.aggregate
quality.repair
quality.calibrate
```

Metrics：

```text
hard_failure_rate
repair_rate
repair_gain
repair_regression_rate
judge_disagreement
human_ai_agreement
genre_drift
canon_conflict
originality_block
commercial_proxy_correlation
```

---

# 87. Cost Governance

质量系统可能比 Writer 更贵。

因此记录：

```text
quality_cost_per_chapter
review_cost
repair_cost
human_cost
```

并分析：

```text
marginal quality gain
```

---

# 88. Adaptive Validation

低风险 Scene：

```text
lighter semantic review
```

高风险：

```text
deeper review
multiple judges
human gate
```

但 Q0–Q3 必须按 Policy 保持强约束。

---

# 89. Risk-weighted Review

输入：

```text
Narrative Risk R0-R3
```

决定：

```text
review depth
judge count
human requirement
```

---

# 90. Quality Policy Versioning

任何：

```text
threshold
rubric
judge ensemble
hard gate
```

变化都产生新 `quality_policy_version`。

---

# 91. Quality Regression Gate

Model/Prompt/Policy 修改后，必须跑：

```text
Golden Set
V1 Regression Set
Genre Certification Set
```

---

# 92. Release Blocking

如果新版本造成：

```text
hard violation recall下降
major human preference regression
cross-genre contamination
```

则：

```text
BLOCK RELEASE
```

---

# 93. Statistical Discipline

实验比较需明确：

```text
paired vs unpaired
sample size
confidence interval
effect size
multiple testing
```

避免只报：

```text
p < 0.05
```

---

# 94. Small Sample Warning

8、10、20 个样本可以做：

```text
pilot
```

不能轻易宣布：

```text
production superiority proven
```

---

# 95. Ceiling Effect

如果 baseline 已经：

```text
9.0/10
```

Judge 可能无辨别力。

需要：

```text
harder samples
pairwise
objective metrics
human review
```

---

# 96. Judge Saturation Detection

监控：

```text
score variance
tie rate
pairwise inconsistency
```

判断 evaluator 是否失灵。

---

# 97. Model Change Calibration

换 Judge Model：

```text
must recalibrate
```

因为不同 Judge 标尺不同。

---

# 98. Human Calibration Governance

Human Review 数据：

```text
immutable
versioned
consent/rights
blind protocol
```

---

# 99. Golden Set Governance

必须：

```text
double-blind where applicable
copyright reviewed
balanced categories
holdout reserved
AI provisional labels separated
```

---

# 100. Quality Security

Evaluation artifacts 不存：

```text
provider secret
personal identifiers unnecessary for task
```

---

# 101. AI Coding Rules

实现 Quality 时 AI MUST：

1. 不设计一个总分决定一切；
2. 不让 Semantic Judge 覆盖 deterministic hard fail；
3. 不让 Reviewer 改 Canon；
4. 不把 Q6 命名为真实商业结果；
5. 不把 AI label 冒充 human gold；
6. Repair 后必须新 hash；
7. Repair 后必须 revalidate；
8. 不默认整章重写；
9. Pairwise 测试必须 blind；
10. 任何 calibration 报告必须说明样本规模与来源。

---

# 102. Suggested Repository Layout

```text
src/anovel/quality/
  deterministic/
  canon/
  genre/
  transition/
  narrative/
  character/
  commercial/
  originality/
  aggregation/
  repair/
  calibration/

specs/quality/
  schemas/
  rubrics/
  policies/

tests/quality/
  golden/
  regression/
  calibration/
```

---

# 103. Minimum APIs

```text
run_quality(candidate, context, contract, policy) -> QualityReport

run_q0(...) -> Evidence[]
run_q1(...) -> Evidence[]
run_q2(...) -> Evidence[]
run_q3(...) -> Evidence[]
run_semantic_review(...) -> Evidence[]

aggregate_quality(evidence, policy) -> QualityDecision

diagnose(candidate, evidence) -> DiagnosisReport
build_repair_plan(diagnosis, contract, canon) -> RepairPlan
apply_repair(candidate, repair_plan) -> CandidateArtifact

compare_pairwise(a, b, rubric) -> PairwiseEvaluation
calibrate_judge(golden_set, judge_policy) -> CalibrationReport
```

---

# 104. Required Tests

```text
TEST-QUAL-001 hard_fail_cannot_be_averaged_away
TEST-QUAL-002 reviewer_cannot_write_canon
TEST-QUAL-003 q6_is_diagnostic_by_default
TEST-QUAL-004 repair_creates_new_hash
TEST-QUAL-005 repair_reruns_required_gates
TEST-QUAL-006 protected_fact_survives_repair
TEST-QUAL-007 repair_regression_detected
TEST-QUAL-008 same_model_bias_recorded
TEST-QUAL-009 blind_pairwise_hides_candidate_identity
TEST-QUAL-010 ai_label_not_human_gold
TEST-QUAL-011 originality_block_prevents_commit
TEST-QUAL-012 judge_disagreement_preserved
TEST-QUAL-013 golden_holdout_not_used_for_tuning
TEST-QUAL-014 hard_violation_recall_release_gate
TEST-QUAL-015 commercial_proxy_never_labeled_market_truth
```

---

# 105. V1 Regression Mapping

直接对应 V1：

```text
QA pass but wrong protagonist
→ Q1 identity hard gate outranks reviewer

commercial pass vs rollback conflict
→ evidence aggregation with single QualityDecision

same-model double reviewer high agreement
→ judge independence / bias recording

AI voice calibration weak
→ human calibration + holdout

whole chapter rewrite instability
→ patch-first repair

soft warning then continue
→ explicit severity and hard gate policy
```

---

# 106. Definition of Done

Quality v1.0 只有满足以下才算完成：

1. Q0–Q7 有独立可执行入口；
2. Q0–Q3 hard gate 真正阻止 Commit；
3. Semantic Judge 无 Canon write authority；
4. RepairPlan 能局部修改 Candidate；
5. Repair 后重新抽取 Delta 并 revalidate；
6. Golden Set 有明确 human/AI label authority；
7. 至少一个 blind pairwise calibration 流程；
8. V1 Regression Set 全部纳入；
9. Genre Certification 与 Quality Gate 联通；
10. Q6 明确标记为 Proxy；
11. 30 章实验统计 repair rate / hard failures / drift；
12. CI 有质量回归门禁。

---

# 107. Formal ADRs

建议接受：

## ADR-QUALITY-001
Quality is a multi-layer evidence system, not a scalar score.

## ADR-QUALITY-002
Q0–Q3 deterministic/domain violations outrank semantic scores.

## ADR-QUALITY-003
Reviewer output is evidence and has no Canon authority.

## ADR-QUALITY-004
Commercial evaluation is proxy until calibrated against real signals.

## ADR-QUALITY-005
Repair is diagnosis-driven and patch-first.

## ADR-QUALITY-006
Every repair creates a new candidate and requires revalidation.

## ADR-QUALITY-007
Golden labels explicitly distinguish human/expert/platform/AI authority.

## ADR-QUALITY-008
Blind pairwise evaluation is preferred for relative quality comparison.

## ADR-QUALITY-009
Judge bias and disagreement are first-class metrics.

## ADR-QUALITY-010
Release quality is governed by regression and calibration evidence.

---

# 108. Next Document

下一份正式规范应为：

# `CORPUS_EVALUATION_LEARNING_SPEC.md`

因为现在已经形成完整生产闭环：

```text
Generate
→ Validate
→ Diagnose
→ Repair
→ Final Validate
→ Commit
```

下一步要解决：

> 系统如何从长期生产、失败样本、人工评价和真实市场反馈中学习，而不污染 Canon、不过拟合某一个 Judge？

下一份将冻结：

```text
Corpus Registry
Golden Set
Failure Corpus
Evaluation Dataset
Experiment Definition
Baseline
Holdout
Model/Prompt Benchmark
Learning Loop
ReaderSignal
MarketSignal
Calibration
Promotion Gate
Rollback
```

**END OF SPEC**
