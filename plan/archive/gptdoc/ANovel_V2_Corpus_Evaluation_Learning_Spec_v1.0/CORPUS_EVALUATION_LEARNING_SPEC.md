# ANovel V2 Corpus Intelligence, Evaluation Experiment & Learning Loop Specification

> **中文名**：ANovel V2 语料智能、评测实验与学习闭环规范  
> **Document ID**：SPEC-LEARNING-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `WEBNOVEL_MARKET_GENRE_RESEARCH.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
> - `CANONICAL_STATE_SPEC.md`
> - `MULTI_SOURCE_GENESIS_SPEC.md`
> - `PLANNING_CONTRACT_SPEC.md`
> - `CONTEXT_INTELLIGENCE_SPEC.md`
> - `PRODUCTION_WORKFLOW_SPEC.md`
> - `QUALITY_EVALUATION_REPAIR_SPEC.md`
>
> **Primary Goal**：建立 ANovel V2 从生产数据、失败案例、人工评价、实验结果和真实读者/市场信号中持续学习的正式机制，使系统能够基于证据改进 Prompt、ModelPolicy、QualityPolicy、GenrePack、PlanningPolicy 和 Reference Intelligence，而不污染 Canon、不突破人类授权边界、不把未经校准的 AI 指标误当成真实商业结果。

---

# 0. Normative Summary

ANovel V2 Learning System MUST 满足：

1. **Production Truth, Human Truth and Market Truth are distinct.**
2. **Corpus is governed data, not an untyped folder of text.**
3. **Every corpus item has provenance, rights metadata and lifecycle.**
4. **Failure examples are first-class training/evaluation assets.**
5. **Golden Set and Regression Set are distinct from ordinary corpus.**
6. **AI-provisional labels MUST NOT be promoted to Human Gold automatically.**
7. **Experiment Definition is immutable once started.**
8. **Baseline and Variant must be compared on the same eligible sample set.**
9. **Holdout data MUST remain untouched by tuning.**
10. **Promotion requires predefined gates, not post-hoc cherry-picking.**
11. **Rollback criteria are defined before release.**
12. **Reader/Market signals are contextual, delayed and noisy.**
13. **Real-world business metrics require cohort/exposure metadata.**
14. **Learning outputs are proposals to governed policy/configuration artifacts, not automatic Canon mutations.**
15. **Model/Prompt improvement MUST be measured against stable benchmarks.**
16. **Any policy/model promotion is versioned, attributable and reversible.**
17. **Learning loops MUST preserve failed experiments and negative evidence.**
18. **Corpus contamination, data leakage and benchmark leakage are hard governance failures.**
19. **The system MUST support longitudinal 10/30/100/300-chapter evaluation.**
20. **No self-improvement mechanism may silently rewrite Constitution, Genre hard rules or Canon.**

---

# 1. Why Learning Needs Its Own Domain

一个长期 AI 小说系统如果只有：

```text
Generate
→ Review
→ Repair
→ Commit
```

它只能“生产”。

真正长期有价值的系统还必须回答：

```text
什么失败最常见？
哪个 Prompt 真正更好？
哪个模型更适合 Planner / Writer / Reviewer？
哪种 GenrePack 最容易漂移？
哪些修复反而导致回归？
哪些 AI 商业评分和真实追读无关？
哪些 reader signals 值得进入未来规划？
```

所以 V2 必须建立独立的 Learning / Evaluation Domain。

---

# 2. Three Truth Layers

这是本规范最重要的分层。

## 2.1 Production Truth

回答：

> 系统实际发生了什么？

例如：

```text
哪个模型调用
哪个 Context
哪个 Contract
哪个 Candidate
哪个 Repair
哪个 Commit
哪个失败
哪个成本
```

来源：

```text
Workflow
Lineage
Canon
Telemetry
```

Production Truth 是可审计事实。

---

## 2.2 Human Truth

回答：

> 人类如何评价？

包括：

```text
专家判断
编辑判断
普通读者盲评
偏好选择
继续阅读意愿
类型识别
人物可信度
```

Human Truth 不是绝对客观，但它是真实人类反馈。

---

## 2.3 Market Truth

回答：

> 真实平台与读者行为发生了什么？

例如：

```text
曝光
点击
追读
留存
付费
订阅
月票
评论
完读
收入
```

Market Truth 受到大量外部因素影响，所以：

> Market Truth is real behavior, not pure writing quality.

---

# 3. Truth Separation Rule

禁止：

```text
AI Judge says 9.2
→ Human Truth = 9.2
```

禁止：

```text
Simulated Reader predicts high retention
→ Market Truth = high retention
```

禁止：

```text
low subscription
→ prose quality bad
```

必须保留每一层自己的 Authority。

---

# 4. Corpus Registry

所有进入 Learning 系统的材料必须登记到：

```text
CorpusRegistry
```

而不是：

```text
data/
misc/
examples/
old/
```

无治理堆积。

---

# 5. Corpus Item Types

建议：

```text
REFERENCE_WORK
GENERATED_CHAPTER
FAILED_CANDIDATE
REPAIRED_CANDIDATE
PUBLISHED_CHAPTER
HUMAN_REVIEW_SAMPLE
MARKET_SIGNAL_SAMPLE
GOLDEN_SAMPLE
REGRESSION_SAMPLE
BENCHMARK_SAMPLE
PROMPT_EXPERIMENT_SAMPLE
MODEL_EXPERIMENT_SAMPLE
GENRE_CERT_SAMPLE
```

---

# 6. CorpusItem

最低字段：

```text
corpus_item_id
item_type
content_ref
content_hash
project_id(optional)
genre_profile
source
rights
authority
labels
quality_refs
market_refs
created_at
lifecycle
```

---

# 7. Corpus Rights

每项必须明确：

```text
owned
licensed
public_metadata
user_provided
analysis_only
restricted
unknown
```

### Hard Rule

`unknown` 权限的原文：

```text
cannot be promoted into reusable training corpus
```

---

# 8. Corpus Lifecycle

```text
INGESTED
VALIDATED
CURATED
ACTIVE
QUARANTINED
DEPRECATED
RETIRED
```

---

# 9. Curated Corpus

用于研究/学习的 Corpus 不能只按“成功”筛选。

至少分：

```text
high_performing
normal
high_open_low_retention
long_sell
failed
abandoned
genre_drift
repair_heavy
retcon_heavy
```

---

# 10. Failure Corpus

失败不是垃圾。

需要长期保存：

```text
genre contamination
protagonist drift
knowledge leak
timeline conflict
promise debt
engine repetition
AI genericness
repair regression
context omission
workflow retry bug
originality risk
```

---

# 11. Why Failure Corpus Matters

如果系统只学习成功样本：

```text
cannot learn boundary
cannot learn false positive
cannot learn what not to do
```

高质量系统必须同时拥有：

```text
positive evidence
negative evidence
boundary evidence
```

---

# 12. Golden Set

Golden Set 是人工/专家高质量标注的稳定评测集。

必须区分：

```text
HUMAN_GOLD
EXPERT_GOLD
PLATFORM_FACT
AI_PROVISIONAL
```

只允许前 3 类进入真正 Golden authority。

---

# 13. Golden Set Governance

Golden Set 必须：

```text
versioned
rights-reviewed
balanced
split
immutable per version
provenance-linked
```

---

# 14. Dataset Splits

至少：

```text
TUNE
VALIDATION
HOLDOUT
```

### Rule

Holdout：

```text
MUST NOT be used for prompt/model/policy tuning
```

---

# 15. Regression Set

Regression Set 和 Golden Set 不同。

Regression Set 专门回答：

> 过去真实发生过的严重问题有没有回来？

例如：

```text
都市泄漏修仙
主角身份漂移
missing Contract
placeholder hash
retry duplicate commit
alias duplicate entity
knowledge leak
AI label masquerading as gold
```

---

# 16. V1 Regression Dataset

V1 所有确认问题 SHOULD 转换为：

```text
permanent regression cases
```

不能只写在复盘文档里。

---

# 17. Genre Certification Dataset

每个 GenrePack 拥有：

```text
positive cases
negative cases
cross-genre contamination cases
long-run cases
```

---

# 18. Benchmark Registry

所有 Benchmark：

```text
benchmark_id
version
task
dataset_version
metrics
promotion_use
```

---

# 19. Benchmark Classes

建议：

```text
GENESIS
GENRE
CANON
PLANNING
CONTEXT
WRITING
EXTRACTION
QUALITY
REPAIR
WORKFLOW
ORIGINALITY
COMMERCIAL_PROXY
LONG_RUN
```

---

# 20. ExperimentDefinition

实验必须在执行前冻结：

```text
experiment_id
hypothesis
baseline
variant
dataset
sample_selection
metrics
success_criteria
failure_criteria
statistical_plan
budget
```

---

# 21. Immutable Experiment Plan

实验开始后不允许偷偷改：

```text
success threshold
sample inclusion
primary metric
```

如果修改：

```text
new experiment version
```

---

# 22. Hypothesis

必须明确：

```text
what changes
why expected better
which metric should move
what must not regress
```

---

# 23. Baseline

Baseline 必须是：

```text
versioned known configuration
```

例如：

```text
WriterPrompt v1.3
ModelPolicy v2.0
QualityPolicy v1.1
```

---

# 24. Variant

Variant 只能改变计划中的变量。

避免：

```text
同时换 Prompt + Model + ContextPolicy + GenrePack
```

然后无法知道原因。

---

# 25. Single-variable Preference

不是所有实验都能单变量。

但 SHOULD 优先：

```text
one major intervention at a time
```

复杂组合实验需显式说明。

---

# 26. Sample Eligibility

Baseline 与 Variant 必须使用同一：

```text
eligible sample set
```

或使用严格 paired design。

---

# 27. Paired Experiment

对写作质量：

```text
same input
same Canon
same Contract
same Context semantics
different intervention
```

更适合 paired comparison。

---

# 28. Randomization

如有多个 Candidate：

```text
blind randomize presentation order
```

避免 position bias。

---

# 29. Blinding

Human/Judge 不知道：

```text
baseline / variant
model identity
prompt identity
```

在可行时必须盲评。

---

# 30. Experiment Metrics

必须分：

```text
primary
secondary
guardrail
```

---

# 31. Primary Metric

实验成功主要看什么。

例如：

```text
pairwise human preference
hard violation recall
repair regression
```

---

# 32. Guardrail Metric

不能因为提升一个指标破坏：

```text
cost
latency
Canon accuracy
Genre contamination
originality
```

---

# 33. No Metric Shopping

实验结束后不能：

```text
primary failed
but metric #17 improved
→ declare success
```

---

# 34. Statistical Plan

根据数据设计：

```text
paired
unpaired
categorical
ranking
continuous
```

选择适当统计方法。

---

# 35. Effect Size

必须同时报告：

```text
effect size
confidence interval
```

不要只报 p-value。

---

# 36. Sample Size

小样本：

```text
pilot
```

而不是 production proof。

---

# 37. Sequential Experiment

长期成本高时可以分阶段：

```text
pilot
→ confirmatory
→ holdout
→ production shadow
```

---

# 38. BenchmarkRun

每次跑 Benchmark 生成：

```text
BenchmarkRun
```

包括：

```text
config fingerprint
dataset
results
cost
latency
failures
```

---

# 39. Config Fingerprint

至少：

```text
code
prompt
model
context policy
quality policy
genre pack
schema
workflow
```

---

# 40. Prompt Benchmark

用于比较：

```text
PromptTemplate versions
```

必须保持其它条件尽量相同。

---

# 41. Model Benchmark

比较模型时：

```text
same ContextArtifact
same Prompt semantic task
same output schema
```

避免 Provider-specific Prompt 优化导致不公平比较。

---

# 42. Context Benchmark

可专门比较：

```text
Context retrieval policy
token budget
recent context depth
graph retrieval
```

---

# 43. Repair Benchmark

重点：

```text
finding resolution
new violation rate
pairwise preference
repair cost
```

---

# 44. Long-run Benchmark

单章 Benchmark 不足以证明长篇。

必须有：

```text
10 chapters
30 chapters
100 chapters
300 chapters
```

不同里程碑。

---

# 45. 10-Chapter Benchmark

关注：

```text
opening promise
genre stability
identity
basic workflow durability
```

---

# 46. 30-Chapter Benchmark

关注：

```text
arc completion
promise payoff
repair rate
drift
engine repetition
```

---

# 47. 100-Chapter Benchmark

关注：

```text
state growth
context retrieval
character memory
world expansion
cost
```

---

# 48. 300-Chapter Benchmark

关注：

```text
engine exhaustion
retcon rate
late-stage repetition
reader promise renewal
operational sustainability
```

---

# 49. ReaderSignal

真实读者信号必须结构化。

至少：

```text
signal_id
platform
cohort
content_ref
exposure
metric
value
window
captured_at
```

---

# 50. Reader Signal Types

例如：

```text
click_through
chapter_continue
day_retention
chapter_retention
comment_rate
favorite_rate
vote_rate
```

---

# 51. MarketSignal

付费/平台类：

```text
first_subscription
average_subscription
paid_follow
revenue
ranking
monthly_votes
conversion
```

---

# 52. Exposure Context

任何真实指标必须记录：

```text
impressions
traffic source
recommendation slot
time period
competition
```

否则不可直接比较。

---

# 53. Cohort

例如：

```text
new readers
returning readers
organic traffic
paid traffic
platform recommendation traffic
```

---

# 54. Signal Delay

真实市场反馈可能晚于生产数天/数周。

必须：

```text
event time
observation time
```

分开。

---

# 55. Reader Signal Is Not Canon

Reader/Market：

```text
may influence future planning
may calibrate Q6
```

不能：

```text
rewrite committed story facts
```

---

# 56. Calibration Loop

正式闭环：

```text
AI Proxy
↓
Human / Market Truth
↓
Compare
↓
Bias Analysis
↓
Calibration Update Proposal
↓
Validation
↓
Promotion Gate
```

---

# 57. Judge Calibration

分析：

```text
false positives
false negatives
genre bias
length bias
model-family bias
position bias
```

---

# 58. Commercial Proxy Calibration

Q6 预测与真实：

```text
retention
paid follow
subscription
```

比较：

```text
rank correlation
calibration curve
false confidence
```

---

# 59. No Automatic Proxy Promotion

即使某 Proxy 看起来相关：

```text
cannot automatically become hard gate
```

必须经过：

```text
human review
repeat experiments
holdout
```

---

# 60. LearningEvent

每次系统从证据提出改进：

```text
LearningEvent
```

例如：

```text
Prompt change proposal
Quality threshold change
Model route change
GenrePack soft rule change
Context policy change
```

---

# 61. LearningEvent Authority

LearningEvent：

```text
proposal
```

不是自动执行命令。

---

# 62. What Learning May Change

默认可提出修改：

```text
PromptTemplate
ModelPolicy
ContextPolicy
QualityPolicy
PlanningPolicy
RepairPolicy
Genre Soft Rules
ReferenceExtractionProfile
```

---

# 63. What Learning Cannot Auto-change

禁止自动：

```text
Project Constitution
Canon history
Genre hard semantics
Human authority rules
Security rules
Originality boundary
```

---

# 64. Policy Promotion

候选改进流程：

```text
Proposal
→ Benchmark
→ Validation
→ Holdout
→ Shadow
→ Promotion
```

---

# 65. Shadow Mode

新 Policy/Model 可在 Production 旁路运行：

```text
observe
do not control outcome
```

用于真实分布验证。

---

# 66. PromotionDecision

必须记录：

```text
candidate config
baseline config
evidence
primary metrics
guardrails
decision
approver
```

---

# 67. Promotion Status

```text
PROMOTE
REJECT
MORE_EVIDENCE
SHADOW_ONLY
```

---

# 68. Promotion Gates

例如：

```text
no hard violation recall regression
no originality regression
human pairwise preference non-inferior
cost within budget
latency within limit
```

---

# 69. Rollback Gate

发布前必须定义：

```text
what metric drop triggers rollback
```

---

# 70. Post-promotion Monitoring

新版本上线后：

```text
monitor drift
compare baseline window
watch hard failures
```

---

# 71. Rollback

Rollback：

```text
config rollback
```

不能：

```text
rewrite Canon produced earlier
```

---

# 72. Experiment Registry

所有实验长期可查询：

```text
hypothesis
status
result
cost
decision
```

避免团队重复做同样实验。

---

# 73. Negative Results

失败实验 MUST 保留。

否则会形成：

```text
publication bias
```

---

# 74. Benchmark Leakage

如果 Prompt/Model 已经反复针对某 Benchmark 调优：

```text
benchmark becomes contaminated
```

必须：

```text
rotate holdout
introduce fresh samples
```

---

# 75. Data Leakage

训练/参考/评测数据之间要标记：

```text
overlap
source family
derived from
```

防止“看过答案”。

---

# 76. Duplicate Detection

Corpus ingest 应进行：

```text
exact hash
near duplicate
semantic duplicate
```

避免样本重复放大。

---

# 77. Corpus Balance

需要监控：

```text
genre
chapter position
length
quality class
source
failure type
```

---

# 78. Genre Balance

不能整个 Golden Set 都是：

```text
玄幻
```

然后宣布 Urban Reviewer 准确。

---

# 79. Chapter Position Balance

样本要覆盖：

```text
opening
early
mid
late
ending
```

---

# 80. Failure Type Balance

尤其：

```text
knowledge leak
relationship drift
timeline
world law
genre
genericness
commercial fatigue
```

---

# 81. Human Review Sampling

不必人工评所有数据。

可以：

```text
stratified sampling
high-risk oversampling
disagreement sampling
```

---

# 82. Active Evaluation

优先人工评：

```text
AI disagreement
low confidence
high commercial importance
new genre
new model
```

---

# 83. Model Drift

Provider 模型升级：

```text
same model name
new behavior
```

也可能发生。

需要：

```text
periodic benchmark
```

---

# 84. Model Version Pinning

如果 Provider 提供版本：

```text
pin exact version
```

否则至少记录：

```text
observed model identifier
date
provider metadata
```

---

# 85. Prompt Drift

PromptTemplate：

```text
version
hash
```

必须进入 Benchmark/RunFingerprint。

---

# 86. Dataset Versioning

Dataset：

```text
dataset_id
version
hash
```

实验绑定 exact version。

---

# 87. Metric Versioning

Metric 定义变更：

```text
new metric version
```

避免历史图表混用。

---

# 88. Experiment Cost

实验不是免费。

记录：

```text
model cost
human cost
compute cost
elapsed time
```

---

# 89. ROI of Evaluation

后期可计算：

```text
quality gain / evaluation cost
```

用于优化评测深度。

---

# 90. Learning Priority

建议优先顺序：

```text
hard correctness
→ repair efficiency
→ genre fidelity
→ character quality
→ narrative quality
→ commercial proxy
→ market calibration
```

不要一开始就优化虚假的“爆款分”。

---

# 91. ReaderSignal to Planning

真实 ReaderSignal 可以进入：

```text
future replan evidence
```

但必须经过：

```text
confidence
minimum sample
cooldown
```

---

# 92. No Reactive Thrashing

不能因为：

```text
一章评论少
```

立即重写全书方向。

需要：

```text
signal window
trend confidence
```

---

# 93. MarketTrend vs ProjectSignal

区分：

```text
MarketTrendSnapshot
```

和：

```text
ProjectReaderSignal
```

前者是外部市场趋势，后者是本书真实反馈。

---

# 94. Learning and GenrePack

真实生产可以发现：

```text
某 Genre Hard Rule 缺失
某 Soft Rule 过严
```

但任何 Hard Rule 变更：

```text
ADR + certification
```

---

# 95. Learning and ContextPolicy

可实验：

```text
recent chapter depth
graph radius
token allocation
```

通过：

```text
Context Benchmark
```

决定。

---

# 96. Learning and Model Routing

可依据：

```text
quality
cost
latency
failure rate
```

调整 Role → Model。

---

# 97. Cost-aware Model Promotion

更贵模型只有在：

```text
meaningful quality gain
```

时才值得 promotion。

---

# 98. Multi-objective Promotion

不能只优化：

```text
quality
```

还考虑：

```text
cost
latency
reliability
```

---

# 99. Pareto Frontier

对不同 Model/Prompt 组合可维护：

```text
quality-cost-latency
```

Pareto 前沿。

---

# 100. Reproducibility

实验报告必须足够回答：

> 我能否在同样数据、版本和配置下重新跑一次？

随机模型不要求文本完全一致，但实验条件必须可重建。

---

# 101. Experiment Status

```text
DRAFT
FROZEN
RUNNING
COMPLETED
FAILED
INVALIDATED
ARCHIVED
```

---

# 102. Invalid Experiment

出现：

```text
holdout leakage
dataset corruption
wrong baseline
provider outage bias
```

实验标记：

```text
INVALIDATED
```

不能继续用于 Promotion。

---

# 103. Corpus Security

Corpus 中不得存：

```text
secrets
credentials
unnecessary personal data
```

---

# 104. Private User Content

用户上传参考小说/私人资料：

```text
rights and privacy policy inherited
```

不得自动进入公共/共享 Corpus。

---

# 105. Corpus Lineage

每项要知道：

```text
original source
transformations
derived profiles
used in which experiments
```

---

# 106. Evaluation Lineage

```text
Dataset
→ Experiment
→ BenchmarkRun
→ Result
→ PromotionDecision
```

---

# 107. Observability

Trace：

```text
corpus.ingest
corpus.curate
benchmark.run
experiment.run
human.evaluate
signal.ingest
calibration.run
promotion.evaluate
```

Metrics：

```text
dataset_size
label_authority_distribution
holdout_leakage
benchmark_cost
human_ai_agreement
market_proxy_correlation
promotion_success
rollback_rate
```

---

# 108. Error Codes

建议：

```text
LEARN-001 CORPUS_RIGHTS_UNKNOWN
LEARN-002 DATASET_DUPLICATE
LEARN-003 HOLDOUT_LEAKAGE
LEARN-004 EXPERIMENT_MUTATED_AFTER_START
LEARN-005 BASELINE_MISMATCH
LEARN-006 SAMPLE_IMBALANCE
LEARN-007 INSUFFICIENT_POWER
LEARN-008 BENCHMARK_CONTAMINATED
LEARN-009 PROMOTION_GUARDRAIL_FAIL
LEARN-010 MARKET_SIGNAL_CONTEXT_MISSING
LEARN-011 AI_LABEL_AUTHORITY_MISMATCH
LEARN-012 DATASET_VERSION_MISMATCH
LEARN-013 EXPERIMENT_INVALIDATED
LEARN-014 ROLLBACK_TRIGGERED
```

---

# 109. Architecture Fitness

CI / governance 检查：

```text
holdout not referenced by tuning config
AI_PROVISIONAL cannot become HUMAN_GOLD
private corpus cannot enter public corpus
LearningEvent cannot mutate Canon
PromotionDecision requires benchmark evidence
experiment config immutable after FROZEN
```

---

# 110. AI Coding Rules

实现 Learning Domain 时 AI MUST：

1. 不把 corpus 当普通文件夹；
2. 不自动把 AI 标签升级成人工标签；
3. 不用 Holdout 调 Prompt；
4. 不把失败实验删除；
5. 不从 ReaderSignal 直接修改 Canon；
6. 不自动改 Constitution/Genre hard rule；
7. 不在实验后改变 primary metric；
8. 不省略 baseline fingerprint；
9. 不把市场行为解释成单一文本质量因果；
10. Promotion 必须可 rollback。

---

# 111. Suggested Repository Layout

```text
src/anovel/learning/
  corpus/
  datasets/
  benchmark/
  experiments/
  human_eval/
  signals/
  calibration/
  promotion/
  rollback/

specs/learning/
  schemas/
  policies/
  benchmarks/
  datasets/
```

---

# 112. Minimum APIs

```text
register_corpus_item(item) -> CorpusItem
curate_dataset(query, policy) -> DatasetVersion

create_experiment(definition) -> Experiment
freeze_experiment(experiment_id)
run_experiment(experiment_id) -> ExperimentResult

run_benchmark(benchmark_id, config) -> BenchmarkRun
ingest_human_evaluation(eval) -> HumanTruthRecord
ingest_reader_signal(signal) -> ReaderSignal
ingest_market_signal(signal) -> MarketSignal

calibrate_proxy(proxy, truth_dataset) -> CalibrationReport
propose_learning_change(evidence) -> LearningEvent
evaluate_promotion(change, evidence) -> PromotionDecision
rollback_config(version) -> RollbackReceipt
```

---

# 113. Required Tests

```text
TEST-LEARN-001 ai_label_cannot_be_human_gold
TEST-LEARN-002 holdout_cannot_be_tuning_input
TEST-LEARN-003 frozen_experiment_is_immutable
TEST-LEARN-004 baseline_and_variant_share_eligible_samples
TEST-LEARN-005 failed_experiment_is_preserved
TEST-LEARN-006 private_reference_not_added_to_public_corpus
TEST-LEARN-007 reader_signal_cannot_mutate_canon
TEST-LEARN-008 promotion_requires_guardrails
TEST-LEARN-009 rollback_restores_previous_policy
TEST-LEARN-010 market_signal_requires_exposure_context
TEST-LEARN-011 benchmark_dataset_version_pinned
TEST-LEARN-012 corpus_duplicate_detected
TEST-LEARN-013 genre_balance_reported
TEST-LEARN-014 promotion_blocked_on_hard_regression
TEST-LEARN-015 learning_event_is_proposal_only
```

---

# 114. Definition of Done

Learning v1.0 完成必须证明：

1. Corpus Registry 可登记多种来源；
2. Rights unknown 的原文不会进入可复用训练 Corpus；
3. Golden / Regression / Benchmark Dataset 分离；
4. Tune / Validation / Holdout 分离；
5. 一个 Prompt/Model 实验可冻结、运行、复现；
6. Pairwise Human Evaluation 可进入 Human Truth；
7. ReaderSignal / MarketSignal 可带 cohort/exposure；
8. Commercial Proxy 可与真实信号校准；
9. Promotion 有 primary/guardrail gates；
10. Promotion 后可 rollback；
11. LearningEvent 不可直接改 Canon；
12. 30/100 章 Benchmark 可形成 longitudinal report。

---

# 115. Formal ADRs

建议接受：

## ADR-LEARN-001
Production Truth, Human Truth and Market Truth are separate authorities.

## ADR-LEARN-002
Corpus is a governed registry with provenance, rights and lifecycle.

## ADR-LEARN-003
Failure Corpus is a first-class evaluation asset.

## ADR-LEARN-004
Golden, Regression and ordinary corpus datasets are distinct.

## ADR-LEARN-005
Holdout data is immutable with respect to tuning.

## ADR-LEARN-006
Experiment definitions are frozen before execution.

## ADR-LEARN-007
Promotion requires predefined primary and guardrail gates.

## ADR-LEARN-008
Learning outputs are governed change proposals, never direct Canon mutations.

## ADR-LEARN-009
Reader/Market signals require contextual metadata and cannot be treated as pure writing quality.

## ADR-LEARN-010
Every promoted configuration is reversible.

---

# 116. Next Document

下一份正式规范应为：

# `PLATFORM_OBSERVABILITY_SECURITY_SPEC.md`

原因：

核心创作、生产、质量、学习闭环已经形成。

下一步必须把横切基础设施正式冻结：

```text
Security
Secrets
Authorization
Audit
Provenance
OpenTelemetry
OpenLineage-style Run Lineage
Artifact Integrity
PII / Private Corpus
Cost Monitoring
Incident Handling
Backup / Restore
```

完成后，再生成：

```text
IMPLEMENTATION_PLAN.md
```

把所有规范转换为 Phase / Milestone / Sprint / Task / DoD 的实施计划。

**END OF SPEC**
