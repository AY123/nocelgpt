# ANovel V2 Multi-Source Genesis & Reference Intelligence Specification

> **中文名**：ANovel V2 多源开书与参考智能规范  
> **Document ID**：SPEC-GENESIS-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `V1_FORENSIC_LESSONS.md`
> - `REFERENCE_ARCHITECTURE_STUDY.md`
> - `WEBNOVEL_MARKET_GENRE_RESEARCH.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
> - `CANONICAL_STATE_SPEC.md`
>
> **Primary Goal**：把 Idea-Driven、Reference-Guided、Hybrid、Corpus/Market-Driven 四种开书方式统一为一个可审计、可解释、原创性受控的 Genesis Compiler，最终输出统一 `GenesisSpec` 并通过 `GenesisCommit` 建立初始 Canon。

---

# 0. Normative Summary

ANovel V2 Genesis MUST 满足：

1. **Multiple inputs, one production kernel.**
2. **All creation modes converge to one GenesisSpec.**
3. **Reference text is evidence, not story truth.**
4. **Reference learning transfers mechanisms, not content.**
5. **Raw reference text MUST NOT become production writer context by default.**
6. **Every extracted reference feature carries provenance and confidence.**
7. **Positive and negative references are separate evidence classes.**
8. **Dimension-specific references MUST be supported.**
9. **Multi-reference abstraction is preferred to one-book imitation.**
10. **Originality checking occurs before Genesis acceptance.**
11. **MarketTrendSnapshot influences candidate generation/ranking, never Canon.**
12. **Genesis candidate generation and selection are separate stages.**
13. **GenesisSpec is the only accepted output contract of Genesis.**
14. **GenesisSpec MUST resolve GenreProfile before production.**
15. **Initial Story/World/Character state becomes Canon only through GenesisCommit.**
16. **ReferenceEvidencePack MUST NOT write Canon directly.**
17. **Unknown or disputed reference inference is explicit, not silently filled.**
18. **Model outputs are proposals; deterministic policy and human authority govern irreversible decisions.**
19. **Every Genesis run is reproducible enough to audit via RunFingerprint and lineage.**
20. **Copyright/originality safeguards are architecture requirements, not post-processing.**

---

# 1. Why Genesis Is a First-Class Domain

普通 AI 小说产品经常采用：

```text
User Prompt
→ Model
→ Outline
→ Chapter 1
```

这种做法无法解决：

- 用户只给一句创意时，系统如何构建商业小说骨架；
- 用户给一本/多本参考小说时，系统到底“学什么”；
- 如何避免把参考内容直接复制进新项目；
- 如何用市场趋势而不让趋势成为硬编码；
- 如何比较多个开书方案；
- 如何让最终世界、人物、Reader Promise、Narrative Engine 形成一套统一项目契约；
- 如何保证开书设定进入 Canon 时有完整来源和版本。

因此 V2 Genesis 是正式 Domain。

---

# 2. Creation Modes

V2 定义四种入口，但只有一个下游。

## 2.1 IDEA_DRIVEN

输入：

```text
genre intent
core concept
target reader
tone
constraints
optional world/character ideas
```

系统完成：

```text
Genre Resolution
Market/Reference optional research
Concept Expansion
Narrative Engine Design
Character/World Design
Genesis Tournament
GenesisSpec
```

---

## 2.2 REFERENCE_GUIDED

输入：

```text
1..N reference works
+
allowed learning dimensions
+
originality constraints
```

系统：

```text
Ingest
→ Decompose
→ Abstract
→ Compare
→ Build Evidence
→ Originality Guard
→ Genesis
```

---

## 2.3 HYBRID

输入：

```text
Idea
+
Positive References
+
Negative References
+
Dimension References
+
User likes/dislikes
```

这是 V2 推荐的高控制模式。

---

## 2.4 CORPUS_MARKET_DRIVEN

输入：

```text
Curated Corpus
+
MarketTrendSnapshot
+
Target Platform
+
Target Reader
```

系统从多书/多信号中抽象：

```text
shared patterns
variant patterns
overcrowded patterns
failure patterns
white-space opportunities
```

再生成 Genesis candidates。

---

# 3. Single Kernel Principle

四种模式只能在 Genesis Compiler 之前分叉。

正确：

```text
Idea ──────────────┐
Reference ─────────┤
Hybrid ────────────┤
Corpus/Market ─────┘
        ↓
Genesis Compiler
        ↓
GenesisSpec
        ↓
Genre
Canon
Planning
Production
```

禁止：

```text
IdeaPipeline
ReferencePipeline
CorpusPipeline
HybridPipeline
```

长期独立维护。

---

# 4. Genesis Intake

统一输入对象：

```text
GenesisIntake
```

包含：

```text
mode
user_intent
target_platform
target_reader
genre_hints
hard_constraints
soft_preferences
references
corpus_refs
market_snapshot_ref
originality_policy
budget
```

---

# 5. User Intent Authority

用户明确要求：

```text
genre
prohibited content
era
core character
ending preference
commercial direction
```

属于高 Authority。

Market/Reference 只能建议，不得覆盖。

例如：

```text
User: 现实都市商战，禁止超自然
```

即使参考书包含修仙：

> Reference evidence 不得引入 supernatural。

---

# 6. Reference Ingestion

Reference 输入必须有：

```text
reference_id
source_type
ownership/license/provenance
title
author(optional)
language
format
content_hash
scope
allowed_use
```

---

# 7. Reference Use Policy

Reference 必须声明：

```text
analysis_only
pattern_learning
style_analysis
negative_example
dimension_specific
```

禁止默认：

```text
verbatim_generation_source
```

---

# 8. Copyright / Rights Boundary

Reference-Guided 模式必须坚持：

> **Mechanism Transfer, not Content Transfer.**

系统允许学习：

```text
narrative engine
progression engine
reader promise
pacing
hook
payoff
character function
relationship dynamics
arc expansion
failure pattern
genre structure
```

系统不应直接复刻：

```text
连续原文
独特角色组合
标志性场景
相同事件序列
独特世界设定组合
关系图的一一映射
高度识别性表达
```

---

# 9. Reference Decomposition

每本参考作品生成：

```text
BookNarrativeProfile
```

必须尽量抽象为机制，不保存可复制情节作为核心输出。

---

# 10. BookNarrativeProfile

建议字段：

```text
market_position
genre_profile
core_fantasy
reader_promises
premise_pattern
narrative_engines
progression_engines
conflict_engines
opening_pattern
hook_patterns
payoff_patterns
pacing_profile
character_functions
relationship_patterns
cast_model
world_model
arc_expansion
volume_structure
long_run_engine
fatigue_patterns
failure_patterns
style_signals
originality_risks
evidence
confidence
```

---

# 11. Character Function Abstraction

不要输出：

```text
角色 A = 某原作主角
角色 B = 某原作女主
```

而是：

```text
ambitious outsider
institutional gatekeeper
mentor with conflicting agenda
competitor who adapts
social anchor
```

---

# 12. Event Abstraction

错误：

```text
主角在拍卖会上被嘲笑，然后买到神秘戒指
```

正确抽象：

```text
Public Undervaluation
→ Hidden Opportunity
→ Acquisition
→ Delayed Value Reveal
→ Social Status Reversal
```

---

# 13. Progression Abstraction

错误：

```text
练气 → 筑基 → 金丹
```

可抽象：

```text
entry tier
→ first qualitative threshold
→ institutional recognition
→ resource access increase
→ higher-order conflict
```

在同 Genre 内也可保留合法领域语义，但不能把某参考书独有命名复制为新项目默认命名。

---

# 14. Opening Pattern

参考抽取：

```text
initial pressure
core anomaly/opportunity
first decision
first promise
first irreversible change
first payoff
```

而不是复制前三章剧情。

---

# 15. Narrative Engine Profile

每本参考书至少识别：

```text
engine trigger
state consumed
state changed
conflict generated
payoff generated
escalation path
repeatability
exhaustion risk
```

---

# 16. Long-run Engine

特别分析：

```text
为什么它能写到 100/300+ 章？
```

包括：

```text
scope expansion
new state space
new relationship network
new institutions
new geography
new responsibility
new cost
```

---

# 17. Failure Pattern Extraction

Reference 不只学习成功。

也分析：

```text
mid-book fatigue
repetitive payoff
opponent stupidity
world reset
progression inflation
relationship stagnation
promise debt
generic voice
```

---

# 18. Positive References

Positive Reference 表示：

> 希望学习某些机制。

必须声明：

```text
desired_dimensions
```

例如：

```text
opening_hook
business_progression
ensemble
pacing
```

---

# 19. Negative References

Negative Reference 表示：

> 明确不希望复制/重现的模式。

抽取：

```text
avoid_patterns
failure_modes
tone_to_avoid
mechanics_to_avoid
```

Negative Evidence 进入 Genesis constraint。

---

# 20. Dimension-specific Reference

同一项目可：

```text
Book A → opening
Book B → character dynamics
Book C → business engine
Book D → pacing
Book E → long-arc expansion
```

这样比：

> “模仿某一本书”

更安全、更有效。

---

# 21. Multi-reference Cross Mining

N 本参考不直接拼接。

必须经过：

```text
Common Pattern Mining
Variant Pattern Mining
Contradiction Analysis
Outlier Detection
Failure Comparison
```

---

# 22. Shared Pattern

如果多个高质量参考都表现出：

```text
early promise
rapid first state change
adaptive opponent
```

可以形成：

```text
shared_evidence
```

但仍不是永久 Genre rule。

---

# 23. Variant Pattern

不同成功作品可能使用不同策略。

V2 不应强行平均。

应该记录：

```text
Pattern A succeeds under conditions X
Pattern B succeeds under conditions Y
```

---

# 24. Contradiction Handling

参考书之间冲突时：

```text
do not silently merge
```

输出：

```text
conflicting_patterns
conditions
confidence
recommended choices
```

---

# 25. ReferenceEvidencePack

经过抽象、对比、去内容化后，生成：

```text
ReferenceEvidencePack
```

这是 Reference Intelligence 对 Genesis 的正式输出。

---

# 26. ReferenceEvidencePack Authority

Authority：

```text
reference
```

它可以：

```text
suggest Genesis
rank candidates
warn originality risk
```

不能：

```text
write Canon
override Genre Constitution
become Writer raw context
```

---

# 27. Evidence Item

每条 evidence：

```text
id
dimension
pattern
confidence
source_refs
evidence_level
transferability
originality_risk
notes
```

---

# 28. Originality Firewall

Originality Firewall 是 Genesis 前置必经边界。

至少检查：

```text
lexical similarity
semantic similarity
event sequence similarity
plot skeleton similarity
character function mapping
relationship graph similarity
world signature similarity
signature scene similarity
progression sequence similarity
```

---

# 29. Originality Is Multi-dimensional

不能只用文本相似度。

例如：

> 名字都变了，但角色关系、事件顺序和成长路径一模一样

仍然高风险。

---

# 30. Originality Distance

建议输出：

```text
lexical_distance
semantic_distance
event_distance
character_graph_distance
world_distance
progression_distance
overall_risk
```

不是简单一个 0–100 分。

---

# 31. Signature Pattern Guard

如果某参考作品具有非常独特：

```text
scene
artifact
relationship configuration
world mechanism
```

应标记：

```text
signature_pattern
```

Genesis MUST avoid near-isomorphic reuse。

---

# 32. Originality Policy

最低政策：

```text
no_verbatim_copy
no_signature_scene_reuse
no_one_to_one_character_mapping
no_near_identical_event_sequence
no_reference_name_leakage
```

---

# 33. Writer Reference Firewall

Production Writer 默认只能看到：

```text
GenesisSpec
GenrePack
Canon
Plan
Contract
Abstract Reference Evidence when explicitly needed
```

不得默认看到：

```text
reference full text
original character names
chapter sequence
verbatim excerpts
```

---

# 34. MarketTrendSnapshot Integration

MarketSnapshot 可用于：

```text
candidate generation
candidate diversification
opportunity identification
saturation warning
```

但不得：

```text
force current trend
```

---

# 35. Trend Staleness

MarketSnapshot 必须检查：

```text
period
captured_at
staleness
platform
channel
```

过期数据降权。

---

# 36. Corpus Intelligence

Corpus 不应只是向量库。

它需要存：

```text
BookNarrativeProfile
performance evidence
quality evidence
failure evidence
genre axes
```

---

# 37. Corpus Segmentation

Corpus 应区分：

```text
high_performing
normal
high_open_low_retention
long_sell
failed
abandoned
```

避免只学习成功样本。

---

# 38. Failure Corpus

失败作品可以回答：

```text
什么模式会导致：
开篇强但后继无力？
30章后疲劳？
升级通胀？
订阅断崖？
```

这是非常有价值的反向知识。

---

# 39. Genesis Candidate

Genesis 不应只生成一个方案。

输出多个：

```text
GenesisCandidate
```

每个包括：

```text
premise
genre profile
core fantasy
reader promise
narrative engines
progression engines
character architecture
world model
commercial thesis
originality report
risk report
```

---

# 40. Genesis Tournament

多个 Candidate 进入：

```text
Tournament
```

不是让一个 Judge 直接选“最高分”。

---

# 41. Candidate Evaluation Dimensions

至少：

```text
genre coherence
premise strength
reader promise clarity
engine durability
progression depth
character potential
world specificity
commercial fit
originality
reference distance
implementation feasibility
long-run expansion
```

---

# 42. Evidence Level

Candidate Ranking 主要是：

```text
E2 model evaluation
+
E0 structural checks
+
E1 evidence
```

不能冒充 E4 市场真值。

---

# 43. Diversity Constraint

Tournament 应防止所有 Candidate 同质化。

例如：

```text
minimum structural distance
different engine composition
different protagonist architecture
different world logic
```

---

# 44. Human Selection

Phase 1 推荐：

```text
AI shortlist
→ human choose / modify
```

未来可以测试自动选择，但不可把未经市场校准的 Judge 当最终商业真值。

---

# 45. GenesisSpec

最终唯一正式输出：

```text
GenesisSpec
```

它必须是后续所有 Domain 的统一输入。

---

# 46. GenesisSpec Required Fields

至少：

```text
project_identity
target_market
target_reader
genre_profile
core_fantasy
reader_promises
premise
story_question
protagonist_model
cast_model
world_model
narrative_engines
progression_engines
conflict_engines
relationship_engine
commercial_engine
tone_style
pacing_model
originality_policy
reference_evidence_refs
forbidden_patterns
long_run_expansion
initial_canon_plan
```

---

# 47. GenesisSpec Does Not Contain Raw References

禁止：

```text
full reference chapter
reference prose blocks
reference character name mapping
```

---

# 48. Project Identity

GenesisSpec 需要：

```text
working_title
project_id
language
target_length
target_chapter_range
platform_target
```

---

# 49. Target Market

例如：

```text
platform: qidian
channel: male
reader_segment:
```

只是策略，不是 Canon。

---

# 50. Core Fantasy

回答：

> 读者通过主角体验什么根本欲望？

例如：

```text
upward mobility
second chance
mastery
legacy
freedom
discovery
```

---

# 51. Story Question

项目级 Story Question：

```text
这本书最终要回答什么？
```

它用于防止 300 章后主线消失。

---

# 52. Protagonist Model

支持：

```text
person
family
faction
ensemble
multi_generation
```

不能默认永远 single protagonist。

---

# 53. Commercial Engine

它不是“保证赚钱”。

它描述：

```text
reader continuation logic
promise/payoff cycle
retention hypothesis
subscription hypothesis
```

Authority：

```text
plan/evidence
```

---

# 54. Long-run Expansion Plan

至少说明：

```text
scope expansion
relationship expansion
world expansion
responsibility expansion
cost expansion
```

---

# 55. Forbidden Patterns

来自：

```text
user dislike
negative references
genre constitution
originality firewall
V1 regression
```

统一进入：

```text
forbidden_patterns
```

---

# 56. Genesis Validation

GenesisSpec 提交前：

```text
Schema
Genre Resolution
Fusion
Originality
Reference Leakage
World Logic
Engine Durability
Progression
Reader Promise
Long-run Expansion
Constraint
```

---

# 57. GenesisCommit

GenesisSpec 通过后：

```text
GenesisCommit
```

创建初始 Canon。

包括：

```text
World
Initial Characters
Initial Relationships
Initial Knowledge
Initial Factions
Initial Promises
Initial Genre Extensions
```

---

# 58. GenesisCommit Is Canon Commit

它不能是特殊旁路。

使用同一：

```text
ChangeSet
CommitPermit
CanonCommit
```

只是：

```text
parent = genesis root
```

---

# 59. Genesis Provenance

必须记录：

```text
intake hash
reference pack hashes
market snapshot
candidate set
selected candidate
selection rationale
originality report
genre pack
model policy
prompt version
code version
```

---

# 60. Genesis Re-run

如果用户修改需求：

```text
before production:
  can regenerate Genesis

after Canon production:
  cannot silently replace Genesis
```

需要：

```text
Project Reconstitution / Retcon / Branch
```

---

# 61. Reference Update After Production

后续加参考书：

```text
Reference Evidence Update
```

可以影响：

```text
future plan
```

不能自动改：

```text
committed Canon
```

---

# 62. Genesis and Planning Boundary

Genesis 负责：

```text
what kind of book is this?
why does it work?
what are the enduring engines?
```

Planning 负责：

```text
what happens next?
```

不要让 Genesis 生成 300 章固定细纲。

---

# 63. Genesis Far-future Abstraction

Genesis 可以提供：

```text
Series Vision
Major Phase
End-state
Long Arc Skeleton
```

但未来细节保持抽象。

---

# 64. Market-Driven Generation Risk

纯市场驱动容易：

```text
trend chasing
homogenization
late entry
genericness
```

因此必须加入：

```text
originality
authorial distinction
novel combination
```

---

# 65. Novelty Budget

可以定义：

```text
stable genre base
+
novelty dimensions
```

例如：

```text
Genre familiar
World logic novel
Cast architecture novel
```

防止所有维度同时陌生导致 Reader Promise 不清。

---

# 66. Reference Weight

不建议简单数字混合全文。

可以在 Evidence 层表达：

```text
importance
dimension scope
confidence
```

例如：

```yaml
source: book_a
dimension: opening
importance: high
```

---

# 67. Positive/Negative Conflict

如果用户：

```text
Positive: 喜欢 A 的节奏
Negative: 讨厌 A 的人物
```

系统必须按 dimension 分离。

---

# 68. Reference Identity Firewall

Writer Context 需要去除：

```text
reference title
reference author
reference character names
reference unique terms
```

除非用于分析任务，不用于正文生产。

---

# 69. Reference Raw Storage

原文建议：

```text
external governed storage
```

而不是长期进入代码仓库。

需要：

```text
content hash
rights metadata
access policy
```

---

# 70. Evidence Retention

可长期保留：

```text
abstract profile
evidence span references
hash
```

原文是否保留取决于授权。

---

# 71. Multi-language References

Reference Intelligence SHOULD 支持：

```text
Chinese
English
translated
```

但抽象后统一：

```text
semantic ontology
```

避免翻译表面词影响机制分析。

---

# 72. Style Analysis

风格可以学习：

```text
sentence length distribution
dialogue ratio
POV
register
rhythm
description density
```

但禁止：

```text
直接模仿在世作者高度识别性的独特风格
```

应转成高层写作参数，而不是“像某作者写”。

---

# 73. Originality and Style

允许：

```text
concise dialogue-heavy
fast-paced
low exposition
```

不应：

```text
复刻某作者独特措辞和句法习惯
```

---

# 74. ReferenceEvidencePack Schema Rules

每条 pattern 必须：

```text
dimension
abstraction_level
source_count
confidence
transferability
originality_risk
```

---

# 75. Source Count

单书 pattern：

```text
source_count = 1
```

应比：

```text
multi-source shared pattern
```

更谨慎。

---

# 76. Anti-copy Transform Test

Genesis Candidate 应能回答：

> 如果隐藏参考书名，我是否仍能解释这个项目为什么是一个独立成立的原创概念？

如果不能：

```text
REJECT
```

---

# 77. Character Mapping Test

检查是否存在：

```text
Reference A protagonist → Candidate protagonist
Reference A mentor → Candidate mentor
Reference A rival → Candidate rival
```

一一对应。

过高：

```text
originality risk
```

---

# 78. Event Sequence Test

如果 Candidate 主要事件序列与参考高度同构：

```text
REJECT / REBUILD
```

---

# 79. World Signature Test

如果：

```text
unique institution
unique resource
unique artifact
unique cultural mechanism
```

组合高度相同：

```text
risk
```

---

# 80. Corpus Bias

Corpus 可能偏向：

```text
某年代
某平台
某题材
某性别频道
```

必须记录：

```text
coverage
imbalance
```

---

# 81. Market Signal Bias

榜单只是：

```text
observed successful subset
```

不代表全部读者。

MarketSnapshot 必须：

```text
platform/time/channel scoped
```

---

# 82. Genesis Error Codes

建议：

```text
GENESIS-001 INVALID_INTAKE
GENESIS-002 UNRESOLVED_GENRE
GENESIS-003 REFERENCE_RIGHTS_UNKNOWN
GENESIS-004 REFERENCE_PARSE_FAILED
GENESIS-005 EVIDENCE_CONFLICT
GENESIS-006 ORIGINALITY_RISK_HIGH
GENESIS-007 SIGNATURE_PATTERN_COLLISION
GENESIS-008 CANDIDATE_ENGINE_WEAK
GENESIS-009 LONG_RUN_EXPANSION_WEAK
GENESIS-010 RAW_REFERENCE_LEAK
GENESIS-011 MARKET_SNAPSHOT_STALE
GENESIS-012 GENESIS_SPEC_INVALID
```

---

# 83. Genesis State Machine

```text
INTAKE
→ INGESTING
→ PROFILING
→ ABSTRACTING
→ EVIDENCE_READY
→ CANDIDATES_GENERATED
→ ORIGINALITY_CHECK
→ TOURNAMENT
→ SELECTED
→ VALIDATED
→ COMMIT_READY
→ COMMITTED
```

失败：

```text
BLOCKED
REJECTED
NEEDS_USER_DECISION
```

---

# 84. Workflow Durability

Reference profiling 可能很重。

必须支持：

```text
checkpoint
resume
dedup
content hash cache
```

避免同一本书重复分析。

---

# 85. Reference Cache Key

基于：

```text
content_hash
profile_schema_version
analysis_policy_version
model_policy_version
```

Operational timeout 不进入 semantic identity。

---

# 86. Cost Governance

大文本 Reference 分析必须：

```text
chunk
hierarchical summarize
cache
reuse
```

但摘要不能成为唯一 evidence。

关键 pattern 需要可追溯 source span。

---

# 87. Privacy

私人参考文档：

```text
must not be published
must not enter public corpus
```

权限必须继承 source policy。

---

# 88. AI Coding Rules

实现 Genesis 时 AI MUST：

1. 不建立四套生产 Kernel；
2. 不让 raw references 直接进入 Writer；
3. 不让 ReferenceEvidence 写 Canon；
4. 不把单书 pattern 升格 Genre Rule；
5. 不用一个总分代替 originality dimensions；
6. 不忽略 negative references；
7. 不把 market trend 当 user intent；
8. 不自动选择高风险相似 Candidate；
9. GenesisCommit 使用 Canon 标准提交路径；
10. 每个 persistent evidence 有 provenance/hash。

---

# 89. Suggested Repository Layout

```text
src/anovel/genesis/
  intake/
  references/
  profiling/
  abstraction/
  evidence/
  originality/
  tournament/
  compiler/

specs/genesis/
  schemas/
  policies/
  examples/

tests/genesis/
  reference/
  originality/
  tournament/
  regression/
```

---

# 90. Minimal API Surface

```text
normalize_genesis_intake(input) -> GenesisIntake

ingest_reference(ref) -> ReferenceSnapshot
profile_reference(snapshot) -> BookNarrativeProfile
abstract_reference(profiles) -> ReferenceEvidencePack

evaluate_originality(candidate, refs) -> OriginalityReport

generate_genesis_candidates(intake, evidence) -> list[GenesisCandidate]
evaluate_candidates(candidates) -> TournamentReport
select_candidate(report, policy) -> GenesisCandidate

compile_genesis_spec(candidate) -> GenesisSpec
validate_genesis_spec(spec) -> ValidationResult

build_genesis_changeset(spec) -> ChangeSet
commit_genesis(changeset, permit) -> CanonCommit
```

---

# 91. Required Tests

至少：

```text
TEST-GEN-001 idea-only creates valid GenesisSpec
TEST-GEN-002 reference raw text not present in Writer artifact
TEST-GEN-003 reference evidence cannot mutate Canon
TEST-GEN-004 negative reference produces forbidden patterns
TEST-GEN-005 dimension-specific reference isolation
TEST-GEN-006 multi-reference common pattern extraction
TEST-GEN-007 conflicting references remain explicit
TEST-GEN-008 high event similarity rejects candidate
TEST-GEN-009 one-to-one character mapping rejects candidate
TEST-GEN-010 market snapshot cannot override user genre
TEST-GEN-011 stale market signal downgraded
TEST-GEN-012 GenesisCommit uses canonical commit service
```

---

# 92. Definition of Done

Genesis v1.0 完成必须证明：

1. 一个纯创意可以生成合法 GenesisSpec；
2. 一到多本参考书可以生成 ReferenceEvidencePack；
3. Reference 原文默认不进入 Writer；
4. Positive/Negative/Dimension Reference 都有效；
5. 多参考能抽象 shared/variant patterns；
6. Originality Firewall 能拒绝明显情节/角色映射复制；
7. Tournament 能生成至少 3 个结构不同 Candidate；
8. GenreProfile 完整解析；
9. GenesisSpec 可进入 Planning/Canon；
10. GenesisCommit 使用标准 Canon Transaction；
11. Reference/Market 无 Canon Authority；
12. 全流程具备 Provenance。

---

# 93. Formal ADRs

建议接受：

## ADR-GENESIS-001
All Genesis modes converge into one GenesisSpec.

## ADR-GENESIS-002
Reference Intelligence transfers mechanisms, not content.

## ADR-GENESIS-003
Raw reference text is isolated from production Writer by default.

## ADR-GENESIS-004
BookNarrativeProfile is the canonical abstraction of a reference work.

## ADR-GENESIS-005
ReferenceEvidencePack is evidence-only authority.

## ADR-GENESIS-006
Originality is multi-dimensional and checked before candidate acceptance.

## ADR-GENESIS-007
Genesis produces multiple candidates before selection.

## ADR-GENESIS-008
MarketTrendSnapshot is advisory evidence, not user-intent authority.

## ADR-GENESIS-009
GenesisSpec is the sole downstream contract of Genesis.

## ADR-GENESIS-010
Initial project state enters Canon through normal Canon Commit semantics.

---

# 94. Next Document

下一份规范应为：

# `PLANNING_CONTRACT_SPEC.md`

因为：

```text
Genre
Narrative Domain
Canon
Genesis
```

已经回答：

> 这是什么书？
> 这个世界是什么？
> 什么是真实？
> 项目如何诞生？

下一步必须回答：

> 如何把百万字目标逐层分解成下一章、下一场景，同时允许未来动态调整又不破坏 Canon？

下一份将冻结：

```text
SeriesVision
MacroArc
VolumePlan
ArcPlan
ChapterContract
SceneContract
RequiredTransition
ForbiddenTransition
ReaderPromise Scheduling
Payoff Scheduling
Rolling Replan
PlanDiff
Plan Invalidation
```

**END OF SPEC**
