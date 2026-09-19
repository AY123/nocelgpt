# ANovel V2 Narrative Domain Model & Semantic Ontology Specification

> **中文名**：ANovel V2 叙事领域模型与语义本体规范  
> **Document ID**：SPEC-DOMAIN-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `V1_FORENSIC_LESSONS.md`
> - `REFERENCE_ARCHITECTURE_STUDY.md`
> - `WEBNOVEL_MARKET_GENRE_RESEARCH.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
>
> **Primary Goal**：定义 ANovel V2 所有题材共用的叙事语义世界，使 Character、Relationship、Knowledge、Timeline、Event、Promise、Mystery、Faction、Object 等概念拥有稳定、机器可处理、可扩展、可验证的统一语义。

---

# 0. Normative Summary

ANovel V2 的 Narrative Domain MUST 满足：

1. **Narrative Domain is genre-neutral at the core.**
2. **Genre-specific concepts are extensions, not core duplication.**
3. **Entity identity is stable and independent from display name.**
4. **Facts have mutability classes.**
5. **Knowledge is explicit and scoped by knower.**
6. **Relationships are first-class entities, not text labels.**
7. **Events are immutable historical claims once committed.**
8. **State changes are represented as NarrativeDelta before Canon Commit.**
9. **Plans, beliefs, hypotheses and facts are separate semantic types.**
10. **Absence of evidence is not evidence of absence.**
11. **Unknown, uncertain and contradictory are distinct states.**
12. **All persistent narrative entities require provenance and authority.**
13. **Narrative semantics MUST NOT depend on a specific LLM provider.**
14. **Core Domain MUST NOT contain genre-specific names such as realm/company/equity.**
15. **Domain objects are authoritative data structures; AI Workers are interpreters/producers, not truth owners.**

---

# 1. Why Narrative Domain Comes Before Canon

V1 已经证明：

```text
有 Story Bible
有 Registry
有 State
```

并不自动意味着系统“理解小说世界”。

如果底层语义模型不稳定，后续会发生：

- Character 与人物卡、章节人物、State 人物重复建模；
- Relationship 只是字符串；
- Knowledge 藏在摘要中；
- Timeline 只有日期，没有事件关系；
- “受伤”被误写进 lifecycle status；
- 情绪、身份、职业、位置混在同一字段；
- Genre-specific 属性不断污染 Core Schema；
- AI 抽取字段与业务字段语义不一致。

因此 V2 顺序必须是：

```text
Narrative Ontology
↓
Canonical State
↓
Contracts
↓
Workflow
```

而不是反过来。

---

# 2. Domain Boundary

Narrative Domain 负责定义：

```text
Entity
Identity
Alias
Character
Relationship
Knowledge
Belief
Goal
Emotion
Location
Object
Faction
World
WorldLaw
Timeline
Event
Promise
Mystery
Resource
Status
NarrativeDelta
FactClaim
FactMutability
Evidence
Provenance
```

它不负责：

- 持久化策略；
- Canon Commit；
- Workflow；
- Provider；
- Prompt；
- Market Trend；
- Genre Certification；
- UI；
- Publishing。

这些属于其他 Domain。

---

# 3. Core Semantic Layers

V2 的叙事数据建议分五层。

## L1 Identity

回答：

> “这个东西是谁/是什么？”

例如：

```text
EntityId
EntityType
CanonicalName
Aliases
Lifecycle
```

---

## L2 State

回答：

> “它现在是什么状态？”

例如：

```text
location
occupation
wealth
emotion
relationship
knowledge
health
status
```

---

## L3 History

回答：

> “发生过什么？”

由：

```text
Event
```

表达。

---

## L4 Intention

回答：

> “未来想发生什么？”

例如：

```text
Goal
Plan
Promise
Contract
```

---

## L5 Interpretation

回答：

> “谁认为发生了什么？”

例如：

```text
Belief
Hypothesis
Suspicion
Rumor
Prediction
```

事实与解释必须分开。

---

# 4. Base Entity

所有核心叙事实体继承逻辑上的 `NarrativeEntity`。

最小字段：

```yaml
id:
entity_type:
canonical_name:
aliases:
lifecycle:
authority:
provenance:
created_at:
updated_at:
```

---

# 5. Entity Identity

## 5.1 Stable ID

实体身份必须使用稳定 ID。

例如：

```text
char_01H...
loc_01H...
faction_01H...
obj_01H...
```

Display Name 可以变化，ID 不变。

---

## 5.2 Canonical Name vs Alias

Character 例：

```yaml
id: char_chen_mo
canonical_name: 陈默
aliases:
  - 小陈
  - 陈总
  - 老陈
```

### Rule

Alias resolution MUST NOT mint a new entity if identity confidence is sufficient.

---

## 5.3 Name Change

正式改名不等于新实体。

需要：

```text
NameChangeEvent
```

而不是创建新 Character。

---

# 6. Entity Lifecycle

推荐通用 lifecycle：

```text
ACTIVE
INACTIVE
DEAD
DESTROYED
DISBANDED
LOST
UNKNOWN
```

不同 entity_type 可以限制可用值。

### Critical Rule

Lifecycle 只表达存在性/存续状态。

不能把：

```text
受伤
被追捕
心情低落
失业
```

写进 lifecycle。

这些属于其他 State。

---

# 7. Fact Mutability Model

V2 必须区分事实可变性。

## IMMUTABLE

原则上不可变化：

```text
birth_identity
biological_origin
historical_birth_date
entity_id
```

改变必须 Retcon。

---

## SLOW_MUTABLE

缓慢变化：

```text
personality
belief
relationship
reputation
loyalty
social_identity
```

需要事件与证据。

---

## DYNAMIC

频繁变化：

```text
location
money
emotion
inventory
current_goal
injury
knowledge
```

---

## DERIVED

由其他事实计算：

```text
age
current_status_summary
relationship_strength_bucket
```

不得人工当作独立事实写入。

---

# 8. FactClaim

所有可进入 Canon 的事实应能表示为 FactClaim。

核心：

```yaml
subject:
predicate:
object:
valid_from:
valid_to:
confidence:
authority:
evidence:
provenance:
mutability:
```

例：

```yaml
subject: char_chen_mo
predicate: located_at
object: loc_shanghai
valid_from: event_102
```

---

# 9. Unknown / Uncertain / Contradictory

必须区分：

## UNKNOWN

没有足够信息。

## UNCERTAIN

有候选信息，但置信度不足。

## CONTRADICTORY

存在互相冲突的高权威主张。

### Rule

`UNKNOWN` 不能被默认值偷偷填成事实。

---

# 10. Character

Character 是核心 Entity。

推荐 Core Character Model：

```text
Identity
Demographics
Role
Personality
Beliefs
Goals
Fears
Knowledge
Capabilities
Resources
Relationships
Emotion
Location
Health
Reputation
Lifecycle
```

但不是所有内容都直接存在 Character aggregate 内。

很多是独立 Entity/Projection。

---

# 11. Character Identity

建议包含：

```text
entity_id
canonical_name
aliases
birth_date
origin
gender
species
public_identity
secret_identity
```

### Rule

Secret Identity 必须具有可见性范围。

不能让所有角色自动知道。

---

# 12. Character Personality

不要只保存：

```text
冷静
聪明
善良
```

建议分为：

```text
stable_traits
values
boundaries
habits
decision_style
social_style
speech_markers
```

Personality 默认 `SLOW_MUTABLE`。

---

# 13. Character Goal

Goal 是一级对象。

结构：

```text
id
owner
description
priority
status
created_by
deadline
dependencies
conflicts_with
success_condition
failure_condition
```

状态：

```text
OPEN
ACTIVE
BLOCKED
ACHIEVED
FAILED
ABANDONED
SUPERSEDED
```

---

# 14. Belief

Belief 与 Fact 必须分开。

例如：

```text
事实：A 没有背叛。
角色 B 相信：A 背叛了。
```

系统必须同时容纳两者。

Belief：

```yaml
holder: char_b
proposition:
  subject: char_a
  predicate: betrayed
  object: char_b
confidence: 0.8
source: rumor_x
```

---

# 15. Knowledge

Knowledge 是 ANovel V2 的关键核心能力。

每个角色拥有自己的 Knowledge State。

结构：

```text
knower
proposition
knowledge_level
source
acquired_at
validity
confidence
```

Knowledge Level：

```text
KNOWN
BELIEVED
SUSPECTED
HEARD
UNKNOWN
FALSELY_BELIEVED
```

---

# 16. Knowledge Boundary

生成 Scene 时必须知道：

> 每个参与角色知道什么、不知道什么。

这直接防止：

- 剧透式角色知识；
- 未知情角色突然引用秘密；
- 悬疑失效；
- 阴谋逻辑崩坏。

### Hard Rule Candidate

Character MUST NOT act using facts outside its knowledge boundary unless:

```text
intuition
guess
inference
external_source
```

被显式表示。

---

# 17. Emotion

Emotion 是 Dynamic State。

建议不用单一字符串。

结构：

```text
primary_emotion
intensity
target
cause
mask
duration
```

例如：

```yaml
primary_emotion: fear
intensity: 0.7
target: faction_black_gate
cause: event_220
mask: calm
```

---

# 18. Relationship

Relationship MUST 是 first-class entity。

不是：

```text
"陈默和李雪关系很好"
```

而是：

```yaml
id: rel_001
party_a: char_chen_mo
party_b: char_li_xue
relationship_types:
  - friend
  - business_partner
trust: 0.7
affection: 0.4
dependency: 0.3
public_status: partner
private_status: complicated
valid_from:
valid_to:
```

---

# 19. Relationship Multi-dimensionality

关系至少可以包含：

```text
trust
affection
loyalty
fear
debt
dependency
authority
hostility
intimacy
```

不同 GenrePack 可以增加 extension。

---

# 20. Relationship Event

Relationship 状态变化必须尽量由 Event 驱动：

```text
betrayal
rescue
confession
promotion
marriage
conflict
alliance
breakup
```

而不是 Writer 直接设置：

```text
trust = 0.9
```

---

# 21. Faction

Faction 适用于：

```text
company
sect
family
gang
government
army
guild
organization
```

Core Faction：

```text
identity
type
members
leadership
goals
resources
territory
relations
reputation
lifecycle
```

Genre-specific 能力通过 Extension。

---

# 22. Membership

Membership SHOULD 是独立关系。

```text
entity
faction
role
rank
joined_at
left_at
visibility
```

这样才能处理：

- 卧底；
- 双重身份；
- 临时顾问；
- 外门/内门；
- 股东但非员工。

---

# 23. Location

Location 不是字符串。

建议：

```text
id
name
location_type
parent_location
coordinates(optional)
access_rules
ownership
known_by
lifecycle
```

支持层级：

```text
国家
→ 城市
→ 区
→ 建筑
→ 房间
```

---

# 24. Object

Object 表示长期有叙事意义的物品。

字段：

```text
identity
object_type
owner
holder
location
condition
properties
access_rules
lifecycle
```

必须区分：

```text
owner
holder
```

例如偷来的物品：

```text
owner != holder
```

---

# 25. Resource

Resource 可以是：

```text
money
spiritual_stone
food
ammo
influence
attention
data
```

Core Domain 只定义资源抽象。

GenrePack / DomainPack 定义：

- 单位；
-约束；
- 流转；
- 合法区间。

---

# 26. World

World 是项目级叙事环境。

Core World：

```text
identity
scope
reality_model
time_model
geography_model
institution_model
law_model
culture_model
technology_model
supernatural_model
```

具体语义由 GenrePack 填充。

---

# 27. WorldLaw

WorldLaw 表示不可随意违反的世界规则。

例如：

```text
死亡是否可逆
魔法是否存在
时间旅行规则
重生机制
修炼规则
法律制度
技术可用性
```

WorldLaw：

```text
id
scope
rule_type
severity
conditions
exceptions
version
```

---

# 28. Event

Event 是“发生过的事情”的核心表示。

最低字段：

```text
id
event_type
occurred_at
participants
location
preconditions
actions
outcomes
causes
effects
evidence
authority
```

---

# 29. Event Immutability

Canon Event 一旦 committed：

> 默认不可修改。

修正方式：

```text
Retcon / Correction Event
```

而不是覆写历史。

---

# 30. Event Time

必须区分：

```text
story_time
recorded_at
committed_at
```

story_time 是小说世界时间。

recorded_at 是系统抽取时间。

committed_at 是 Canon 提交时间。

---

# 31. Event Causality

事件可以声明：

```text
caused_by
enables
blocks
resolves
reveals
```

这对：

- Plot continuity；
- Mystery；
- Promise；
- Arc；

非常重要。

---

# 32. Timeline

Timeline 不是一个日期列表。

它是：

```text
ordered Event set
+
temporal constraints
```

支持：

```text
before
after
during
overlaps
same_time
```

---

# 33. Temporal Uncertainty

某些事件时间可能不精确：

```text
around spring 2013
```

需要：

```text
precision
earliest
latest
```

而不是强行填精确 timestamp。

---

# 34. Promise

Promise 是作者/文本对读者的叙事承诺。

不是角色 Goal。

例如：

```text
这个秘密以后会揭示
这段感情会发展
这个仇会解决
主角会建立公司
```

Promise：

```text
id
promise_type
opened_at
status
target_window
related_entities
payoff_condition
evidence
```

---

# 35. Promise Lifecycle

```text
OPEN
REINFORCED
DELAYED
PARTIAL
PAID
BROKEN
ABANDONED
SUPERSEDED
```

Promise Debt 可以由此派生。

---

# 36. Mystery

Mystery 是被隐藏/未知的命题集合。

结构：

```text
question
truth
known_by
suspected_by
clues
red_herrings
reveal_state
```

关键：

> `truth` 与角色知识分离。

---

# 37. Clue

Clue 可以：

```text
support
contradict
mislead
partially_reveal
```

Mystery 系统必须支持：

```text
reader knows
character does not know
```

和反过来。

---

# 38. Status

Status 不应成为万能字段。

必须命名具体状态类型：

```text
health_status
employment_status
production_status
relationship_status
legal_status
social_status
```

禁止：

```text
status: "受伤并且被追杀"
```

---

# 39. NarrativeDelta

NarrativeDelta 是 V2 最重要的中间语义对象之一。

它表示：

> 一个 Candidate Scene/Chapter 声称改变了什么。

结构：

```text
created_entities
updated_facts
ended_facts
events
relationship_changes
knowledge_changes
promise_changes
world_changes
genre_extension_changes
uncertain_claims
conflicts
```

---

# 40. NarrativeDelta Is Not Canon

NarrativeDelta 只是 Proposal。

流程：

```text
Text
↓
Extraction
↓
NarrativeDelta Candidate
↓
Validation
↓
ChangeSet
↓
Commit Permit
↓
Canon Commit
```

---

# 41. Delta Operation Types

建议：

```text
CREATE_ENTITY
SET_FACT
END_FACT
ADD_RELATIONSHIP
UPDATE_RELATIONSHIP
ADD_KNOWLEDGE
UPDATE_BELIEF
CREATE_EVENT
OPEN_PROMISE
PAY_PROMISE
UPDATE_GOAL
MOVE_ENTITY
TRANSFER_OBJECT
CHANGE_RESOURCE
```

Genre Extension 可以注册新 op。

---

# 42. Required Transition vs Actual Delta

Planning/Contract 声明：

```text
RequiredTransition
ForbiddenTransition
```

生成后得到：

```text
ActualNarrativeDelta
```

Validation：

```text
required satisfied?
forbidden absent?
extra changes allowed?
```

---

# 43. Extra Change Policy

Writer 可能自然产生 Contract 未明确要求的合理变化。

不能全部禁止。

分：

```text
allowed_extra
review_required_extra
forbidden_extra
```

由：

```text
Genre
Canon
Contract
Risk Policy
```

决定。

---

# 44. Semantic Authority

每个 Domain artifact 必须声明 Authority：

```text
canon
contract
plan
reference
market
model
diagnostic
draft
human_approval
```

Domain 模型只定义字段。

谁有权写入由 Canon Spec 决定。

---

# 45. Evidence

Evidence 结构建议：

```text
source_type
source_ref
span
hash
producer
confidence
evidence_level
```

用于：

- Fact；
- Reference inference；
- Market inference；
- AI extraction。

---

# 46. Provenance

任何 persistent entity/fact/event：

```text
created_by
source_artifact
source_hash
schema_version
producer_version
created_at
```

Production 中再由 Lineage 扩展。

---

# 47. Entity Scope

V2 后期可能支持：

```text
universe
series
book
volume
```

因此 Entity SHOULD 支持 scope。

例如一个世界级组织可以跨多本书。

Phase 1 可只实现：

```text
book
```

但 schema 预留 scope。

---

# 48. Core vs Extension

Core Domain 绝不能出现：

```text
realm
equity
box_office
pet_evolution
```

这些是 Extension。

Core 只提供抽象：

```text
Resource
Capability
Faction
ProgressionDimension
```

GenrePack 扩展具体结构。

---

# 49. Capability

Capability 表示角色/实体可执行能力。

Core：

```text
id
owner
capability_type
level(optional)
preconditions
cost
limitations
source
```

Genre-specific：

```text
spell
martial_skill
business_skill
legal_authority
medical_procedure
```

---

# 50. Capability Prerequisite

生成前可检查：

```text
character has capability?
required resource?
knowledge?
location?
status?
```

避免：

> 角色突然会一个从未拥有的能力。

---

# 51. Resource Transfer

任何重要资源变化 SHOULD 可追踪来源与去向。

例如：

```text
money
artifact
share
spiritual stone
territory
```

可表达：

```text
source
target
amount
cause_event
```

---

# 52. Character Knowledge Example

```yaml
knower: char_li_xue
proposition:
  subject: char_chen_mo
  predicate: owns_company
  object: company_01
knowledge_level: suspected
confidence: 0.55
source:
  type: observation
  ref: event_120
```

---

# 53. Mystery Example

```yaml
id: mystery_001
question: 谁泄露了融资方案？
truth:
  subject: char_zhang
  predicate: leaked
  object: doc_financing_plan
reader_visibility: hidden
clues:
  - clue_01
  - clue_02
red_herrings:
  - clue_fake_01
status: OPEN
```

---

# 54. Relationship Example

```yaml
id: rel_chen_li
party_a: char_chen_mo
party_b: char_li_xue
types:
  - business_partner
trust: 0.72
affection: 0.31
hostility: 0.0
valid_from: event_033
```

---

# 55. Event Example

```yaml
id: evt_company_registered
event_type: company_registered
story_time:
  date: 2013-03-22
participants:
  - char_chen_mo
location: loc_market_supervision_office
preconditions:
  - company_name_approved
outcomes:
  - company_01.lifecycle = ACTIVE
```

---

# 56. Knowledge Leakage Validation

Scene Validation SHOULD 检查：

```text
dialogue claims
decisions
reactions
```

是否使用超出角色 knowledge boundary 的信息。

如果是：

```text
hard error
or
semantic review
```

取决于证据是否明确。

---

# 57. Character Consistency Validation

至少：

```text
identity
lifecycle
location
knowledge
capability
relationship
goal
```

不能把所有一致性压成：

```text
character_consistency_score = 0.82
```

---

# 58. World Consistency Validation

至少：

```text
WorldLaw
RealityModel
Technology
Institution
Geography
Genre Extension
```

---

# 59. Narrative Risk Classification

变化按风险：

## R0 Low
- temporary emotion；
- decorative object。

## R1 Medium
- location；
- small resource；
- temporary relationship tension。

## R2 High
- new character；
- capability；
- major money；
- relationship status；
- job/faction role。

## R3 Critical
- death；
- protagonist identity；
- world law；
- irreversible power transition；
- secret truth；
- major retcon。

风险影响：

```text
validation depth
human review
repair policy
```

---

# 60. Domain Validation Philosophy

验证顺序：

```text
Schema
↓
Identity
↓
Authority
↓
Temporal
↓
Knowledge
↓
Relationship
↓
World/Genre
↓
Transition
↓
Semantic
```

先验证确定性，再验证语义。

---

# 61. Narrative Domain Error Codes

建议：

```text
ND-IDENTITY-001 duplicate entity
ND-IDENTITY-002 unresolved alias
ND-LIFECYCLE-001 invalid transition
ND-KNOWLEDGE-001 knowledge leak
ND-TIME-001 temporal contradiction
ND-REL-001 invalid relationship transition
ND-WORLD-001 world law violation
ND-CAP-001 missing capability
ND-DELTA-001 untyped mutation
ND-DELTA-002 unsupported extension
ND-AUTH-001 authority violation
ND-FACT-001 immutable fact mutation
```

---

# 62. DomainPack Integration

DomainPack 可以添加：

```text
schemas
validators
knowledge base
transition rules
```

不能：

- 重写 Core Entity ID；
- 重写 Event 语义；
- 建第二 Timeline；
- 绕过 NarrativeDelta。

---

# 63. Genre Extension Integration

GenrePack 声明：

```text
canon_extensions
```

Narrative Domain 提供 Extension Host。

例如：

```text
Character.extensions["cultivation"]
Faction.extensions["company"]
```

但推荐最终存储可分表/typed aggregate，不要求物理 JSON blob。

---

# 64. Avoid God Object

禁止：

```text
Character {
  300 fields
}
```

应该使用：

```text
CharacterIdentity
CharacterPsychology
CharacterKnowledge
CharacterResources
CharacterCapabilities
CharacterRelationships
```

通过 Entity ID 聚合。

---

# 65. Read Model

为了 Context Compiler，可以构建：

```text
CharacterView
WorldView
SceneRelevantState
```

它们是 Derived Projection，不是 Canon Truth。

---

# 66. Serialization

机器数据 MUST：

- schema version；
- stable IDs；
- explicit null/unknown semantics；
- no hidden defaults；
- deterministic serialization where hashes matter。

---

# 67. Null Semantics

必须区分：

```text
missing
null
unknown
not_applicable
redacted
```

不能全部变成 JSON null。

至少逻辑层必须可区分。

---

# 68. AI Extraction Contract

Extractor 输出：

```text
NarrativeDelta Candidate
+
Evidence
+
Confidence
+
Unresolved
```

不能输出：

```text
CanonicalState N+1
```

---

# 69. Extractor Failure

若关键信息抽取不到：

```text
UNKNOWN
```

不是：

```text
no change
```

这是 V1 主角漂移漏检的直接教训。

---

# 70. Human Correction

人类可以纠正：

```text
entity resolution
fact extraction
relationship interpretation
```

但 Human correction 进入 Canon 前仍应通过：

```text
ChangeSet / Commit
```

---

# 71. Retcon Preparation

本规范不定义 Retcon 工作流，但 Domain 必须支持：

```text
supersedes
corrects
invalidates
```

方便后续 Canon Spec 使用。

---

# 72. Narrative Ontology Registry

所有 predicate / event_type / relationship_type SHOULD 注册。

避免无限自由文本：

```text
"friend"
"best_friend"
"好友"
"铁哥们"
```

全部成为不同 schema 值。

---

# 73. Registry Versioning

Ontology Registry 单独版本化：

```text
narrative_ontology_version
```

变化：

### Patch
alias / wording

### Minor
new predicate/event type

### Major
semantic change / removed meaning

---

# 74. Minimal Phase-1 Ontology

第一阶段只实现：

```text
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
WorldLaw
NarrativeDelta
```

Mystery/Belief/Emotion 可以 Schema 先定义、Runtime 后实现。

---

# 75. AI Coding Rules

实现 Narrative Domain 时 AI MUST：

1. 不把数据库模型当领域模型；
2. 不加入具体 Genre 名词；
3. 不加入 Provider；
4. 不让 Extractor 写 Canon；
5. 不用字符串 status 承载多个含义；
6. 所有 Entity 使用稳定 ID；
7. Alias resolution 不静默 mint；
8. Unknown 不等于 no-change；
9. Event committed 后不原地改历史；
10. Extension 不得建平行 Core Domain。

---

# 76. Suggested Repository Layout

```text
src/anovel/domain/
  identity/
  character/
  relationship/
  knowledge/
  world/
  event/
  timeline/
  promise/
  mystery/
  delta/
  extensions/

specs/domain/
  narrative-ontology.yaml
  schemas/
```

---

# 77. Minimum Public Interfaces

建议：

```text
resolve_entity(ref) -> EntityResolution
validate_entity(entity) -> ValidationResult

build_fact_claim(...) -> FactClaim
validate_fact_transition(old, new) -> ValidationResult

extract_narrative_delta(text, context) -> DeltaCandidate
validate_delta(delta, canon, contract) -> DeltaValidation

project_character_view(canon, character_id) -> CharacterView
project_scene_state(canon, scene_contract) -> SceneRelevantState
```

---

# 78. Definition of Done

Narrative Domain v1.0 不是“Schema 写完”。

必须证明：

1. 同一人物多 alias 不产生重复实体；
2. 死亡人物不能无事件恢复 ACTIVE；
3. 一个角色无法使用自己不知道的秘密；
4. Capability 必须存在才能使用；
5. Location/Relationship/Goal 可以形成合法变化历史；
6. Event 可以构成 Timeline；
7. NarrativeDelta 能表达一章发生的主要变化；
8. Unknown extraction 不会被误当“无变化”；
9. Genre Extension 可以挂接但不污染 Core；
10. 所有对象能被下一份 Canon Spec 消费。

---

# 79. Formal Architecture Decisions

建议接受：

## ADR-DOMAIN-001
Core Narrative Domain is genre-neutral.

## ADR-DOMAIN-002
Stable Entity ID is authoritative over names and aliases.

## ADR-DOMAIN-003
Knowledge and belief are explicit, per-holder state.

## ADR-DOMAIN-004
Relationship is a first-class entity.

## ADR-DOMAIN-005
Committed Event history is immutable by default.

## ADR-DOMAIN-006
NarrativeDelta is the only semantic proposal format for prose-induced state change.

## ADR-DOMAIN-007
Unknown is distinct from no-change.

## ADR-DOMAIN-008
Genre/Domain extensions cannot redefine Core Domain semantics.

## ADR-DOMAIN-009
Facts have explicit mutability classes.

## ADR-DOMAIN-010
AI extraction produces proposals with evidence, never authoritative state.

---

# 80. Next Document

下一份正式规范应为：

# `CANONICAL_STATE_SPEC.md`

它将在本 Narrative Domain 之上定义：

```text
Canon Event Log
Canon Snapshot
Canon Head
ChangeSet
Commit Permit
Canon Transaction
Projection
Snapshot/Rebuild
Concurrency
Idempotency
Retcon
Invalidation
Versioning
Hash Chain
Provenance
```

Narrative Domain 回答：

> “小说世界有哪些语义对象？”

Canonical State 回答：

> “哪些对象是真的？怎么变成真的？怎么保证永远只有一套真相？”

**END OF SPEC**
