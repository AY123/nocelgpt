# ANovel V2 Genre Intelligence Architecture & Executable GenrePack Specification

> **中文名**：ANovel V2 Genre Intelligence 架构与可执行 GenrePack 规范  
> **Document ID**：SPEC-GENRE-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `V1_FORENSIC_LESSONS.md`
> - `REFERENCE_ARCHITECTURE_STUDY.md`
> - `WEBNOVEL_MARKET_GENRE_RESEARCH.md`
>
> **Primary Goal**：把“题材/类型”从文本标签升级为 ANovel V2 的基础领域能力，使 Genre 能真实约束世界规则、Canon 扩展、规划、生成、验证、修订、参考学习与商业评价。

---

# 0. Normative Summary

ANovel V2 的 Genre Intelligence 必须满足以下总原则：

1. **Genre is a foundational domain.**
2. **GenrePack is executable, versioned, inspectable and certifiable.**
3. **Platform taxonomy is metadata, not internal truth.**
4. **Genre / Mechanic / Tone / DomainPack / CastModel 必须正交分离。**
5. **Genre Hard Rules MUST be machine-enforceable.**
6. **Production MUST bind one resolved GenreProfile.**
7. **GenrePack MAY extend Canon but MUST NOT redefine Core Canon semantics.**
8. **Fusion MUST be explicit and conflict-resolved.**
9. **MarketTrendSnapshot MUST be versioned evidence, never permanent Genre truth.**
10. **Reference works may inform Genre inference, but Reference Evidence MUST NOT mutate Canon.**
11. **A GenrePack is not production-ready until certified.**
12. **Supporting a genre means proving long-run correctness, not merely shipping a YAML file.**

---

# 1. Problem Statement

ANovel V1 已经证明：

```text
genre = "都市"
```

不足以控制一部长篇小说。

问题包括：

- 都市写出修炼、灵气、法宝；
- Power System 被错误通用化；
- 玄幻先验污染其他题材；
- 关键词式 hard gate 误伤合法融合题材；
- Genre Prompt 与 Runtime State 没有统一 Authority；
- Genre 检测发现问题后不一定能阻止状态推进；
- 平台分类、商业套路、Mechanic、现实程度混在一起；
- Subgenre 差异没有进入 Canon/Planning/Quality。

因此 V2 必须建立一个正式的 Genre Domain。

---

# 2. Domain Boundary

Genre Intelligence Domain 负责：

```text
Genre Ontology
Genre Family
Subgenre
Reality Model
Setting Model
GenrePack
Genre Constitution
Fusion Policy
Narrative Engine
Progression Model
Conflict Pattern
Reader Promise
Canon Extension Declaration
DomainPack Compatibility
Market Mapping
MarketTrendSnapshot Consumption
Reference Genre Inference
Genre Certification
```

Genre Intelligence Domain **不负责**：

- Canon 具体事实；
- Writer Prompt 具体文本；
- 市场预测；
- ReaderSignal 真值；
- Character 当前情绪；
- 章节实际状态变化；
- 具体 LLM Provider。

---

# 3. Core Type System

## 3.1 PlatformCategory

表示外部平台分类。

示例：

```yaml
platform: qidian
channel: male
category: urban
subcategory: business_workplace
```

规则：

> PlatformCategory MUST NOT 直接作为内部 Genre Constitution。

---

## 3.2 GenreFamily

一级内部类型族。

初始 Registry：

```text
urban
fantasy
xianxia
historical
sci_fi
mystery
wuxia
game
infinite
realism
romance
```

新增 Family 必须 ADR。

---

## 3.3 Subgenre

一个 GenreFamily 内部真正影响 World/Engine/Canon 的细分。

例如：

```text
urban.business
urban.era
urban.entertainment
urban.supernatural

fantasy.eastern
fantasy.high_martial
fantasy.otherworld
fantasy.dynasty

xianxia.classical
xianxia.family
xianxia.realist_cultivation
xianxia.modern_cultivation
```

---

## 3.4 Mechanic

Mechanic 是故事机制，不是 Genre。

例：

```text
rebirth
transmigration
system
simulation
sign_in
beast_taming
family_growth
lord
farming
hidden_master
infinite_flow
```

Mechanic 可以跨 Genre。

---

## 3.5 Tone

Tone 是阅读情绪风格。

例：

```text
light
warm
satirical
dark
tragic
epic
suspenseful
absurd
```

---

## 3.6 CastModel

例：

```text
single_protagonist
dual_protagonist
ensemble
family
faction
multi_generation
```

---

## 3.7 DomainPack

DomainPack 提供专业领域知识与状态扩展。

例如：

```text
business
finance
law
medicine
entertainment
AI
semiconductor
military
education
esports
```

原则：

> DomainPack SHOULD NOT 被误建成 GenreFamily。

---

# 4. Multi-axis GenreProfile

生产项目不能只有一个 genre 字符串。

必须解析成 `GenreProfile`：

```yaml
genre_profile:
  family: urban
  subgenre: urban.business

  reality_model: realistic
  setting_model: contemporary

  mechanics:
    - rebirth

  tone:
    - realistic
    - humorous

  cast_model: ensemble

  domain_packs:
    - business
    - finance

  narrative_engines:
    - entrepreneurship
    - market_competition

  progression_engines:
    - wealth
    - company_scale
    - social_status

  reader_promises:
    - upward_mobility
    - strategic_business_victory
```

GenreProfile 是 Project-level resolved result。

---

# 5. Genre Resolution

Genre Resolution 输入：

```text
User Intent
Reference Evidence
Platform Target
Market Snapshot
Project Constraints
```

输出：

```text
ResolvedGenreProfile
```

规则：

1. 用户显式意图优先于市场趋势；
2. Genre Constitution 优先于 Reference Evidence；
3. MarketTrendSnapshot 只能建议，不可覆盖用户明确要求；
4. Reference Genre 推断必须标明 confidence；
5. 若关键维度冲突，必须进入 unresolved 状态；
6. Production 不允许 unresolved GenreProfile。

---

# 6. GenrePack Definition

`GenrePack` 是 V2 的核心可执行类型包。

每个 Pack 至少包含：

```text
identity
metadata
platform_mapping
constitution
reality_model
setting_constraints
world_laws
narrative_engines
progression_engines
conflict_patterns
reader_promises
payoff_patterns
hook_patterns
cast_models
mechanics_compatibility
domain_pack_compatibility
canon_extensions
quality_rubric
reference_profile
certification_profile
```

---

# 7. GenrePack Lifecycle

状态：

```text
DRAFT
RESEARCHED
IMPLEMENTED
CERTIFIED_10
CERTIFIED_30
PRODUCTION_READY
DEPRECATED
RETIRED
```

禁止：

```text
DRAFT → PRODUCTION_READY
```

必须经过：

```text
schema validation
unit rules
negative contamination tests
cross-genre tests
10-chapter run
30-chapter certification
```

---

# 8. Genre Constitution

Genre Constitution 是 GenrePack 中最高 Authority 的题材规则。

它必须区分：

```text
HARD
SOFT
ADVISORY
```

---

## 8.1 HARD

违反即：

```text
BLOCKED
```

示例：

### realistic urban

```yaml
supernatural:
  cultivation: forbidden
  magic: forbidden
  unexplained_psychic_power: forbidden
```

### xianxia

```yaml
realm_transition:
  requires_valid_path: true
```

---

## 8.2 SOFT

违反不自动阻止 Commit，但进入修订/人工复核。

例如：

```text
expected payoff rhythm
hook density
genre vocabulary presence
tone drift
```

---

## 8.3 ADVISORY

只用于：

```text
planning suggestions
market hints
style hints
```

不得影响 Commit。

---

# 9. Rule Representation

Hard Rule 不允许只存在自然语言 Prompt。

至少要有结构化 Policy。

示例：

```yaml
rule:
  id: GEN-U-BIZ-001
  severity: hard
  target: world.supernatural.cultivation
  operator: equals
  expected: false
  on_violation: block
```

复杂语义规则可以：

```text
structured trigger
+
semantic evaluator
```

但 semantic result 的 Authority 必须明确。

---

# 10. Reality Model

建议初始枚举：

```text
realistic
heightened_realism
hidden_supernatural
open_supernatural
full_fantasy
science_speculative
```

Reality Model 影响：

- allowed events；
- validation；
- world laws；
- DomainPack；
- Reference inference；
- Writer context。

---

# 11. Setting Model

初始：

```text
contemporary
era
campus
workplace
alternate_world
dynasty
future
multiverse
```

`era` 必须关联 `PeriodConstraintProfile`。

---

# 12. Period Constraint Profile

年代/历史/特定时代题材需要：

```text
technology
price
salary
policy
institution
media
transport
communication
culture
fashion
terminology
```

示例：

```yaml
period:
  start_year: 2013
  hard:
    prohibit_technology_after_year: true
```

### Important

Period Constraint 是 Genre/Setting 的规则层。

实际 2013 某项价格是多少，则属于 external evidence / domain knowledge。

---

# 13. Narrative Engine Contract

Narrative Engine 回答：

> 为什么下一章还能继续发生故事？

每个 Engine 必须声明：

```text
inputs
state_consumed
state_changed
conflict_created
payoff_produced
escalation_path
exhaustion_risk
```

例如：

```yaml
engine:
  id: entrepreneurship
  consumes:
    - opportunity
    - capital
    - team
  mutates:
    - company
    - market_position
    - cash
    - reputation
  creates_conflict:
    - competition
    - financing
    - execution_risk
```

---

# 14. Engine Durability

V2 必须评估 Engine 是否能支持长篇。

一个 Engine 不应该只问：

> 能否产生下一章？

还要问：

```text
Can it generate new states after:
10 chapters?
30 chapters?
100 chapters?
300 chapters?
```

建议记录：

```text
scope_expansion
state_space_growth
repetition_risk
dependency_on_new_map
dependency_on_stronger_enemy
```

---

# 15. Progression Engine Contract

Progression 是任何可持续成长维度。

例：

### Urban

```text
wealth
career
company_scale
network
reputation
status
knowledge
```

### Fantasy

```text
realm
skill
artifact
resource
faction_power
```

### Mystery

```text
knowledge
access
trust
world_truth
```

每个 Progression Engine 应声明：

```text
state path
legal transitions
preconditions
cost
evidence
cap
anti-inflation policy
```

---

# 16. Progression Anti-inflation

V2 必须防止：

```text
每次升级只是数字更大
```

Progression 应尽量满足：

```text
quantitative increase
+
qualitative capability change
+
new responsibility/cost
+
new conflict space
```

否则标记：

```text
progression_flattening_risk
```

---

# 17. Reader Promise Contract

Reader Promise 是项目长期商业承诺。

结构：

```yaml
promise:
  id: upward_mobility
  established_by: chapter_3
  reinforcement_window: 5
  payoff_window: 15
  renewal_policy: rolling
```

Promise lifecycle：

```text
open
reinforced
delayed
partially_paid
paid
renewed
abandoned
violated
```

---

# 18. Payoff Pattern

Payoff 不是简单“爽点”。

完整结构：

```text
Expectation
→ Tension
→ Delay
→ Resolution
→ Social Confirmation
→ State Change
→ New Promise
```

一个 payoff SHOULD 改变：

```text
resource
status
relationship
knowledge
world_state
future_option
```

如果没有真实状态变化，标记：

```text
cosmetic_payoff
```

---

# 19. Hook Model

Hook 分：

```text
book
volume
arc
chapter
scene
```

Type：

```text
question
threat
reveal
opportunity
promise
decision
reversal
emotion
```

Hook Quality 不是密度越高越好。

必须监控：

```text
hook_repetition
false_promise
hook_fatigue
```

---

# 20. Canon Extension Model

Core Canon 固定负责：

```text
Character
Relationship
Timeline
Location
Knowledge
Object
Event
Promise
```

GenrePack 只能声明 Extension：

```text
Company
Realm
Sect
Family
Territory
...
```

禁止：

> GenrePack 重新定义 Character / Timeline 的基础语义。

---

# 21. Canon Extension Declaration

示例：

```yaml
canon_extensions:
  - id: company
    schema_ref: schemas/company.schema.json
    authority: canon
    mutable: true

  - id: equity
    schema_ref: schemas/equity.schema.json
    authority: canon
    mutable: true
```

每个 Extension 必须声明：

```text
owner domain
schema
lifecycle
mutation rules
projection rules
validation rules
```

---

# 22. DomainPack Interface

GenrePack 与 DomainPack：

```text
GenrePack
→ defines narrative/world constraints

DomainPack
→ supplies professional knowledge/state
```

示例：

```yaml
genre_pack: urban.business.realistic

domain_packs:
  required:
    - business
  optional:
    - finance
    - internet_startup
```

---

# 23. Fusion Policy

混合类型必须显式声明。

结构：

```yaml
fusion:
  primary:
    genre: xianxia
    authority: world_law

  secondary:
    genre: urban_social_logic

  overlays:
    - satire

  conflict_resolution:
    supernatural: primary_wins
    social_institutions: merged
```

---

# 24. Fusion Conflict Resolution

冲突必须有 Policy。

示例：

```text
Primary World Law
> Secondary World Flavor
> Mechanic
> Tone
> Market Trend
```

如果两个 GenrePack 在 hard rule 上无法合并：

```text
FusionResolution = incompatible
```

Production BLOCK。

---

# 25. Mechanics Compatibility

每个 GenrePack 可声明：

```text
allowed
conditional
forbidden
```

例如：

```yaml
mechanics:
  rebirth: allowed
  system: conditional
  cultivation: forbidden
```

`conditional` 必须指定要求。

---

# 26. MarketTrendSnapshot Contract

MarketTrendSnapshot 是：

```text
time-bounded
platform-specific
channel-specific
evidence-ranked
```

结构：

```yaml
platform: qidian
channel: male
period: 2026-Q3

signals:
  - family_xianxia
  - urban_rebirth
```

它可参与：

- Genesis candidate generation；
- Genre candidate ranking；
- Corpus sampling；
- Market Positioning。

不得：

- 修改 Canon；
- 修改 Constitution；
- 自动改 GenreFamily。

---

# 27. Reference Genre Profile

Reference Intelligence 对每本书生成：

```text
ReferenceGenreProfile
```

包括：

```text
platform mapping
genre axes
reality model
narrative engines
progression engines
reader promises
mechanics
tone
cast
domain signals
fusion signals
confidence
evidence spans
```

重要：

> Reference Profile 是 inference，不是 truth。

---

# 28. Genre Inference Confidence

每个推断字段：

```yaml
value: urban.business
confidence: 0.91
evidence:
  - source: chapter_1
  - source: metadata
```

关键冲突：

```text
confidence < threshold
→ unresolved
```

不能偷偷 fallback。

---

# 29. Genre Certification

一个 GenrePack 进入 `PRODUCTION_READY` 前至少通过：

```text
C0 Schema
C1 Unit Policy
C2 Negative Contamination
C3 Cross-Genre Isolation
C4 Reference Mode
C5 10-Chapter Run
C6 30-Chapter Run
C7 Resume/Retry
C8 Human Spot Review
```

---

# 30. Certification Metrics

至少记录：

```text
hard_violation_count
soft_violation_rate
genre_drift_rate
cross_genre_contamination
canon_extension_error
repair_rate
human_genre_fidelity
engine_repetition_rate
progression_violation
```

---

# 31. Wave 1 Certification

## GPK-U01 — urban.business.realistic

目标：

```text
0 unauthorized supernatural
0 impossible equity transition
0 impossible money transition
0 unexplained company scale jump
0 timeline/period hard error
```

## GPK-X01 — fantasy.eastern.progression

目标：

```text
0 illegal realm jump
0 ability without prerequisite
0 world-law violation
0 urban business contamination
```

---

# 32. Wave 2 Certification

## GPK-U02 — urban.rebirth.era

额外：

```text
future knowledge decay
timeline divergence
period constraints
```

## GPK-X02 — fantasy.high_martial

额外：

```text
modern institution consistency
rank/social treatment
official organization presence
```

---

# 33. Wave 3 Certification

## GPK-A01 — xianxia.family

```text
lineage
generation
succession
lifespan
family continuity
```

## GPK-A02 — xianxia.realist_cultivation

```text
resource scarcity
realm legality
social hierarchy
cost of progression
```

---

# 34. Genre Quality Rubric

Genre quality 分：

### Structural
- World Law Fidelity
- Reality Fidelity
- Progression Fidelity
- Engine Fidelity

### Reader-facing
- Reader Promise Delivery
- Payoff Fit
- Tone Fit
- Genre Recognition

### Long-run
- Drift
- Repetition
- Inflation
- Engine Exhaustion

---

# 35. Deterministic vs Semantic Split

## Deterministic candidates

```text
illegal realm
forbidden mechanic
timeline year
schema violation
missing required canon extension
invalid parent
period technology hard violation
```

## Semantic

```text
does chapter still feel like urban business?
is business conflict convincing?
is xianxia atmosphere distinct?
is payoff satisfying?
```

Semantic 默认不能直接拥有 Hard Authority，除非被明确校准。

---

# 36. Genre Drift

Genre Drift 不是：

> 某几个关键词少了。

它应综合：

```text
world law
engine
progression
reader promise
domain state
tone
cast behavior
```

关键词只能作为低成本 smoke detector。

---

# 37. Anti-Genericness

GenrePack SHOULD 提供：

```text
generic_failure_patterns
```

例如 urban business：

```text
vague_business_success
random_money_growth
stupid_competitor
generic_boardroom
```

fantasy：

```text
generic_realm_naming
map_reset
crowd_shock_loop
resource_without_cost
```

用于 Quality Diagnosis。

---

# 38. AI Coding Rules for Genre Domain

AI 实现 Genre 相关任务时 MUST：

1. 读取本规范；
2. 不新增平行 genre truth；
3. 不用 Prompt 字符串替代 hard policy；
4. 不把 current market trend 写进 core enum；
5. 不把 mechanic 当 family；
6. 不在 Domain 层依赖 LLM Provider；
7. 不让 Reference Profile 直接生成 Canon mutation；
8. 新 GenrePack 必须有 certification fixture；
9. 新 Canon Extension 必须声明 owner/schema/lifecycle；
10. 不允许 unknown genre 静默 fallback 为某个默认 Genre。

---

# 39. Repository Layout

建议：

```text
docs/04-genre/
  GENRE_INTELLIGENCE_SPEC.md

specs/genres/
  ontology/
    genre-ontology.yaml

  packs/
    urban/
    fantasy/
    xianxia/

  schemas/
    genre-pack.schema.json
    genre-constitution.schema.json
    market-trend-snapshot.schema.json
    genre-certification.schema.json

tests/genre/
  certification/
  contamination/
  cross-genre/
```

---

# 40. Initial Package Naming

建议 ID：

```text
GPK-U01 urban.business.realistic
GPK-U02 urban.rebirth.era

GPK-X01 fantasy.eastern.progression
GPK-X02 fantasy.high_martial

GPK-A01 xianxia.family
GPK-A02 xianxia.realist_cultivation
```

---

# 41. Versioning

GenrePack 采用 Semantic Versioning：

### Patch

- 文案澄清；
- advisory keyword；
- non-semantic metadata。

### Minor

- 新 soft rule；
- 新 optional DomainPack；
- 新 quality dimension。

### Major

- Hard rule 改变；
- Canon Extension 语义改变；
- Reality Model 改变；
- Fusion precedence 改变；
- Progression legal transitions 改变。

---

# 42. Project Pinning

项目创建后必须 pin：

```text
genre_pack_id
genre_pack_version
genre_pack_hash
```

GenrePack 升级时：

```text
existing project
≠
automatic upgrade
```

必须显式 migration/revalidation。

---

# 43. Deprecation

Deprecated GenrePack：

- 新项目不能选择；
- 老项目仍可继续；
- 提供 migration guidance；
- 不允许静默替换。

---

# 44. Architecture Decisions to Accept

建议本规范正式接受：

## ADR-GENRE-001
Genre Intelligence is a foundational domain.

## ADR-GENRE-002
Internal genre representation is multi-axis.

## ADR-GENRE-003
GenrePack is executable and versioned.

## ADR-GENRE-004
Genre hard rules are machine-enforceable and fail-closed.

## ADR-GENRE-005
Mechanic, Tone, DomainPack and CastModel are orthogonal dimensions.

## ADR-GENRE-006
GenrePack may extend Canon but not redefine Core Canon.

## ADR-GENRE-007
Genre Fusion is explicit and policy governed.

## ADR-GENRE-008
MarketTrendSnapshot is evidence, not Genre truth.

## ADR-GENRE-009
Reference Genre inference carries confidence and evidence.

## ADR-GENRE-010
Production-ready Genre requires certification.

---

# 45. Implementation Sequence

不要一次实现所有字段。

## Phase G0 — Kernel

实现：

```text
GenreFamily
GenreProfile
GenrePack loader
Genre Constitution
Hard Rule engine interface
Pack version/hash
```

## Phase G1 — Canon Integration

```text
Canon Extension registry
DomainPack compatibility
```

## Phase G2 — Engine Contracts

```text
NarrativeEngine
ProgressionEngine
ReaderPromise
```

## Phase G3 — Fusion

```text
Primary/Secondary/Overlay
Conflict Resolution
```

## Phase G4 — Certification

```text
urban.business.realistic
fantasy.eastern.progression
```

## Phase G5 — Reference/Market Integration

```text
ReferenceGenreProfile
MarketTrendSnapshot
```

---

# 46. Minimum API Surface

建议：

```text
resolve_genre_profile(input) -> GenreProfile
load_genre_pack(id, version) -> GenrePack
validate_genre_pack(pack) -> ValidationResult
compile_genre_policy(pack, project) -> GenrePolicy
validate_content(policy, context, delta) -> GenreValidation
resolve_fusion(packs) -> ResolvedGenrePack
get_canon_extensions(pack) -> ExtensionDeclarations
run_genre_certification(pack) -> CertificationReport
```

---

# 47. Failure Semantics

必须明确：

```text
UNKNOWN_GENRE
UNRESOLVED_GENRE
PACK_NOT_FOUND
PACK_VERSION_MISMATCH
PACK_SCHEMA_INVALID
FUSION_CONFLICT
HARD_GENRE_VIOLATION
CANON_EXTENSION_MISSING
MECHANIC_INCOMPATIBLE
CERTIFICATION_REQUIRED
```

Production：

> 默认 BLOCK。

---

# 48. Observability

Genre 相关 trace：

```text
genre.resolve
genre.load
genre.compile_policy
genre.validate
genre.fusion
genre.certify
```

Metrics：

```text
genre_hard_violation_total
genre_soft_violation_total
genre_drift_rate
genre_repair_rate
cross_genre_contamination_total
```

---

# 49. Security / Integrity

GenrePack：

- 必须 hash；
- schema validated；
- immutable version artifact；
- production project pin hash；
- 禁止运行时 silent edit。

---

# 50. Definition of Done

Genre Intelligence v1.0 的完成，不是：

```text
schemas created
```

而是：

1. Urban Business Pack 能生产 30 章；
2. Eastern Fantasy Pack 能生产 30 章；
3. 两者 0 cross-contamination hard failure；
4. Pack 可版本化；
5. Hard Rules 真正阻止 Commit；
6. Canon Extensions 真正被 Runtime 消费；
7. Reference/Market 不拥有 Canon Authority；
8. CI 中存在 certification suite；
9. AI Coding Agent 可以仅凭本规范和 schema 实现/审查。

---

# 51. Next Normative Document

完成 Genre Intelligence 后，下一份应为：

```text
NARRATIVE_DOMAIN_SPEC.md
```

原因：

> GenrePack 已经定义“不同类型需要哪些事实”，下一步必须定义“这些事实到底以什么通用 Narrative Domain Model 表达”。

下一份应冻结：

```text
Character
Relationship
Knowledge
World
Location
Object
Faction
Event
Timeline
Promise
Mystery
NarrativeDelta
Fact Mutability
Entity Identity
Authority
```

然后再进入：

```text
CANONICAL_STATE_SPEC.md
```

**END OF SPEC**
