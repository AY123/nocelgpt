# ANovel V2 Hierarchical Planning & Narrative Contract Specification

> **中文名**：ANovel V2 分层规划与叙事契约规范  
> **Document ID**：SPEC-PLAN-0001  
> **Version**：1.0.0  
> **Status**：NORMATIVE / IMPLEMENTATION-READY BASELINE  
> **Authority**：ARCHITECTURE-SPEC  
> **Depends-On**：
> - `PROJECT_CONSTITUTION.md`
> - `GENRE_INTELLIGENCE_SPEC.md`
> - `NARRATIVE_DOMAIN_SPEC.md`
> - `CANONICAL_STATE_SPEC.md`
> - `MULTI_SOURCE_GENESIS_SPEC.md`
>
> **Primary Goal**：建立从 Series Vision 到 Scene Contract 的统一规划/契约体系，使 ANovel V2 能在长篇持续生产中同时具备长期方向、短期精确控制、可滚动重规划、可验证状态转移和 Reader Promise/Payoff 管理能力。

---

# 0. Normative Summary

ANovel V2 Planning & Contract Domain MUST 满足：

1. **Planning is hierarchical.**
2. **Far future is abstract; near future is concrete.**
3. **Plan is intention, Canon is history.**
4. **Plans are versioned and replaceable; Canon is not silently rewritten.**
5. **Production contracts are compiled, not handwritten runtime truth.**
6. **Every Chapter/Scene Contract binds a Canon parent and GenrePack version/hash.**
7. **Contracts declare required, forbidden and protected transitions.**
8. **Contract missing in Production means BLOCK.**
9. **Unknown required state is not treated as satisfied.**
10. **Reader Promise / Payoff / Hook scheduling are first-class planning objects.**
11. **Knowledge Boundaries are compiled into Scene Contracts.**
12. **Contracts constrain outcomes and state transitions, not prose wording.**
13. **Rolling replan affects future only.**
14. **Plan invalidation is explicit and dependency-aware.**
15. **Long-run plans MUST include engine durability and fatigue controls.**
16. **Scene is the smallest default narrative contract unit.**
17. **Chapter is the default commit aggregation unit in Phase 1.**
18. **A Contract cannot directly mutate Canon.**
19. **A Plan cannot override Genre Constitution or Canon.**
20. **Planning output is machine-readable and inspectable by humans and AI.**

---

# 1. Why Planning Is a Separate Domain

长篇小说不是：

```text
写下一章
→ 再问模型下一章写什么
```

这会产生：

- 主线漂移；
- Reader Promise 被遗忘；
- 每章局部有趣但整体不推进；
- 中后期重复发动机；
- 配角失踪；
- 伏笔失控；
- 升级通胀；
- 反派轮流送经验；
- 新地图替代真正结构发展。

因此 V2 需要正式的 Planning Domain。

---

# 2. Plan vs Contract

必须严格区分。

## Plan

回答：

> “我们希望未来发生什么？”

具有：

```text
flexible
versioned
replannable
future-facing
```

## Contract

回答：

> “当前这一生产单元允许/要求发生什么？”

具有：

```text
bounded
machine-readable
validation-oriented
frozen for execution
```

---

# 3. Hierarchical Planning Model

V2 采用：

```text
SeriesVision
↓
MacroArc
↓
VolumePlan
↓
ArcPlan
↓
ChapterPlan
↓
ScenePlan
↓
SceneContract
```

Chapter Contract 汇总 Scene Contracts。

---

# 4. SeriesVision

SeriesVision 是整本书最高层长期方向。

它至少包含：

```text
core premise
story question
core fantasy
reader promises
target ending state
protagonist transformation
world transformation
long-run narrative engines
major expansion phases
anti-failure constraints
```

它不是 300 章细纲。

---

# 5. SeriesVision Scope

正确：

```text
第 1 阶段：建立公司生存
第 2 阶段：进入行业竞争
第 3 阶段：资本/制度竞争
第 4 阶段：行业领导
```

错误：

```text
第 187 章董事会吵架
```

远未来细节必须保持抽象。

---

# 6. MacroArc

MacroArc 表示大阶段。

例如：

```text
rise
survival
expansion
war
truth_revelation
succession
```

包含：

```text
entry_state
exit_state
reader_promise
engine
major conflict
irreversible change
scope expansion
```

---

# 7. VolumePlan

Volume 是中长期结构单元。

建议：

```text
goal
central conflict
reader promise
major payoff
character arcs
world expansion
progression target
open threads
closing transition
```

Volume 结束必须有：

```text
meaningful state change
```

不是只换标题。

---

# 8. ArcPlan

Arc 是最关键的可执行中程规划单元。

建议跨度：

```text
3–20 chapters
```

具体按 Genre 调整。

ArcPlan：

```text
arc_goal
entry_state
required_end_state
conflict_engine
character_intents
promise_open
promise_pay
progression
expected reversals
failure conditions
```

---

# 9. ChapterPlan

ChapterPlan 主要定义：

```text
chapter_function
reader_goal
required_progress
conflict
emotional_delta
information_gain
payoff
hook
scene_count
```

ChapterPlan 仍是 Plan，不是最终 Contract。

---

# 10. ScenePlan

ScenePlan：

```text
scene_function
participants
location
entry_state
goal
conflict
decision
required_transition
exit_state
knowledge boundary
```

---

# 11. Planning Resolution

计划越近越具体：

```text
100 chapters away → phase-level
30 chapters away → arc-level
5 chapters away → chapter-level
current chapter → scene-level
```

称为：

> **Rolling Resolution**

---

# 12. Freeze Horizon

定义：

```text
Plan Freeze Horizon
```

例如：

```text
current chapter
next 1 chapter
next 3 scenes
```

Freeze 内：

- 不因小信号随意重规划；
- 只有 Canon/Hard Constraint/重大风险可以打破。

避免 planning jitter。

---

# 13. Replan Horizon

Freeze 外：

```text
future plan
```

可以重新生成。

---

# 14. Rolling Replan

触发条件：

```text
Canon state changed
Major promise paid early
Character died
Progression changed
Reader signal
Market change
Reference evidence update
Arc failure
Engine fatigue
```

输出：

```text
PlanDiff
```

---

# 15. PlanDiff

必须明确：

```text
added
removed
modified
preserved
reason
affected_artifacts
```

不能只覆盖旧 plan。

---

# 16. Plan Invalidation

Plan 改变后：

```text
future ChapterPlan
future ScenePlan
future Contract
future ContextArtifact
```

可能 invalid。

必须显式标记。

---

# 17. Canon-triggered Replan

如果 Canon 与 Plan 冲突：

```text
Canon wins
Plan changes
```

禁止：

```text
edit Canon to fit Plan
```

---

# 18. Planning Inputs

规划只允许依赖：

```text
GenesisSpec
GenreProfile / GenrePack
CanonSnapshot
Open Promises
Current Arc/Volume
ReferenceEvidencePack(optional)
MarketTrendSnapshot(optional)
ReaderSignal(optional)
Planning Policy
```

---

# 19. Planning Authority

Plan authority：

```text
plan
```

不是：

```text
canon
```

---

# 20. Planning Workers

可以有：

```text
SeriesPlanner
ArcPlanner
ChapterPlanner
ScenePlanner
Replanner
```

但它们是 Worker。

不得拥有长期真值。

---

# 21. StoryContract

StoryContract 是整本书长期约束。

它来自：

```text
GenesisSpec
+
GenrePack
+
SeriesVision
```

包含：

```text
core promises
prohibited patterns
story question
ending constraints
core protagonist model
genre constraints
long-run engines
```

---

# 22. ArcContract

ArcContract：

```text
entry canon
required exit conditions
required progress
open promises
payoff obligations
forbidden regressions
character arc obligations
```

---

# 23. ChapterContract

ChapterContract 是 Chapter Production 的唯一正式约束。

它 MUST 由 compiler 生成。

不能：

```text
protagonist_name = "陈默"
```

这类硬编码。

---

# 24. ChapterContract Inputs

必须绑定：

```text
project_id
chapter_id
canon_parent
genre_pack
story_contract
arc_contract
chapter_plan
```

---

# 25. ChapterContract Core

至少：

```text
chapter_function
reader_goal
required_transitions
forbidden_transitions
protected_facts
required_entities
knowledge_constraints
progression_constraints
promise_obligations
payoff_obligations
hook_requirement
tone_constraints
scene_contract_refs
```

---

# 26. SceneContract

SceneContract 是默认最小执行单位。

包含：

```text
scene_id
parent_chapter_id
entry_state_ref
participants
location
scene_goal
conflict
required_transition
forbidden_transition
protected_facts
knowledge_boundary
capability_constraints
resource_constraints
exit_expectation
```

---

# 27. Contract Compilation

正确：

```text
Canon
+
Plan
+
Genre
+
Story Rules
↓
Contract Compiler
↓
Frozen Contract Artifact
```

不是：

```text
manual hardcoded Python object
```

---

# 28. Contract Freeze

开始生成后：

```text
Contract frozen
```

如果 Canon/Plan 改变：

```text
old Contract stale
```

必须重新 compile。

---

# 29. Contract Hash

每个 Contract：

```text
contract_hash
```

绑定：

```text
canon_parent_hash
plan_hash
genre_pack_hash
compiler_version
```

---

# 30. RequiredTransition

表示当前单元必须完成的状态变化。

例如：

```yaml
subject: company_01
path: lifecycle
from: PLANNED
to: ACTIVE
```

---

# 31. ForbiddenTransition

表示不允许出现：

```yaml
subject: protagonist
path: cultivation.realm
any_change: true
```

---

# 32. ProtectedFact

当前生产单元不得破坏：

```text
identity
timeline
world law
relationship status
knowledge boundary
```

---

# 33. Allowed Extra Transition

创作不能被 Contract 锁死。

允许：

```text
allowed_extra
```

只要：

```text
Genre legal
Canon legal
Risk acceptable
```

---

# 34. Review-required Extra

某些意外变化：

```text
new important character
major relationship change
unexpected resource gain
```

可以：

```text
HUMAN_REVIEW / REPAIR
```

---

# 35. Character Intent

SceneContract SHOULD 包含参与角色：

```text
goal
belief
knowledge
fear
decision pressure
relationship intent
```

这样人物行为不是只跟 Plot。

---

# 36. Knowledge Boundary

SceneContract 必须编译：

```text
who knows what
who suspects what
what remains secret
```

---

# 37. Capability Boundary

角色只能使用：

```text
Canon-confirmed capability
+
available resource
+
legal context
```

---

# 38. Reader Goal

每章应声明：

> 希望读者在本章结束时产生什么阅读心理？

例如：

```text
satisfaction
curiosity
fear
anticipation
emotional attachment
```

Reader Goal 是 planning target，不是硬真值。

---

# 39. Reader Promise Scheduling

Promise 必须跨层调度。

例如：

```text
Book Promise
→ Volume reinforcement
→ Arc setup
→ Chapter payoff
```

---

# 40. Promise Debt

计划系统维护：

```text
open
age
reinforcement count
target payoff window
```

过期：

```text
promise_debt_risk
```

---

# 41. Payoff Scheduling

不能随机“每三章一个爽点”。

Payoff 与：

```text
Promise
Conflict
State Change
```

绑定。

---

# 42. Payoff Classes

例如：

```text
micro
chapter
arc
volume
series
```

---

# 43. Payoff Dependency

大 Payoff 前必须有：

```text
setup
investment
delay
tension
```

否则：

```text
unearned payoff
```

---

# 44. Hook Scheduling

Hook 是：

```text
transition to next reading action
```

而不是必须 cliffhanger。

类型：

```text
question
opportunity
threat
reveal
decision
emotional residue
```

---

# 45. Hook Fatigue

Plan 应检测：

```text
same hook type repeated
constant cliffhanger
false urgency
```

---

# 46. Chapter Function Taxonomy

建议 Registry：

```text
setup
escalation
confrontation
payoff
recovery
reveal
transition
relationship
exploration
decision
```

一个 Chapter 可多个 function，但需主函数。

---

# 47. Scene Function Taxonomy

例如：

```text
information
conflict
decision
payoff
relationship
discovery
transition
setup
```

---

# 48. Narrative Density

Planning SHOULD 避免：

```text
scene exists only to fill length
```

Scene 至少改变：

```text
state
knowledge
relationship
emotion
goal
resource
reader understanding
```

---

# 49. Progression Scheduling

Progression Engine 进入 Plan。

例如：

```text
Current
→ obstacle
→ prerequisite
→ cost
→ transition
→ consequence
```

---

# 50. Anti-inflation

Plan 不允许连续：

```text
stronger enemy
→ stronger enemy
→ stronger enemy
```

必须扩展：

```text
responsibility
complexity
tradeoff
social consequence
```

---

# 51. Conflict Engine Rotation

长期应监控：

```text
business competition
institutional pressure
internal conflict
relationship
resource scarcity
```

避免只重复一种 conflict。

---

# 52. Opponent Adaptation

重要 Opponent 需要：

```text
observe
learn
adapt
counter
```

Plan 必须记住 previous encounters。

---

# 53. Long-run Engine Durability

ArcPlanner 应评估：

```text
engine_repetition
scope expansion
state diversity
new decision space
```

---

# 54. Fatigue Signals

例如：

```text
same conflict pattern
same payoff
same scene sequence
same opponent archetype
same hook
```

触发 replan。

---

# 55. Plan Evaluation

Plan 可以由 AI Judge 比较，但：

```text
plan score != truth
```

用于：

```text
ranking
diagnosis
```

---

# 56. Plan Acceptance

Phase 1 推荐：

```text
auto structural validation
+
human optional review
```

Production 不需要每章人工批准计划，但 high-risk replan 可要求。

---

# 57. Contract Validation

Contract 编译后先检查：

```text
schema
parent hash
genre compatibility
canon existence
entity references
transition legality
knowledge
capability
promise feasibility
```

---

# 58. Missing Contract

Production：

```text
missing ChapterContract
→ BLOCK
```

绝不能：

```text
skip validation
```

---

# 59. Stale Contract

如果：

```text
canon parent changed
plan changed
genre pack changed
```

则：

```text
STALE_CONTRACT
```

不得用于生成/提交。

---

# 60. Contract and Context

Context Compiler 以后必须使用：

```text
frozen Contract
```

而不是自由读取当前最新 Plan。

保证 generation/review 基于同一 contract。

---

# 61. Contract and Canon Commit

CommitPermit 绑定：

```text
contract_hash
```

保证：

```text
generated under Contract A
```

不能：

```text
commit under Contract B
```

---

# 62. Chapter Contract Aggregation

ChapterContract 汇总所有 SceneContract：

```text
order
shared protected facts
chapter-level payoff
chapter hook
final required state
```

---

# 63. Scene Reorder

如果 Scene 顺序改变：

```text
contract hash changes
```

必须重新检查：

```text
knowledge
timeline
state transitions
```

---

# 64. Dynamic Scene Count

ChapterPlan 可以估计：

```text
scene_count
```

但 Scene 数不是硬规则。

如果生成过程中需要新增 Scene：

```text
PlanDiff
→ Contract recompile
```

---

# 65. Intra-chapter Repair

修某 Scene：

```text
revalidate downstream Scene Contracts
```

因为 entry state 可能变化。

---

# 66. Chapter Boundary

Phase 1：

```text
Chapter = default Canon Commit boundary
```

Scene Contract 是生成/验证边界。

---

# 67. Arc Completion

Arc 结束必须验证：

```text
required end state
promise payoff
progression
character arc
```

---

# 68. Volume Completion

Volume 结束：

```text
major payoff
state reset?
new scope?
new question?
```

不能只写总结。

---

# 69. Story Question Tracking

SeriesVision 的 Story Question 应：

```text
reinforced
complicated
partially answered
finally answered
```

---

# 70. Ending Constraint

如果 GenesisSpec 有：

```text
ending requirement
```

Planning 不能完全偏离。

---

# 71. Planning Branch

可以对未来做：

```text
Plan Branch A
Plan Branch B
```

用于 Tournament。

但不创建 Canon Branch，除非真的生成/提交。

---

# 72. Plan Tournament

重要 Arc 可生成 3–5 方案：

```text
different conflict
different payoff
different relationship path
```

比较后选。

---

# 73. Planning Reference Evidence

ReferenceEvidence 可以：

```text
suggest structure
```

不能：

```text
copy chapter sequence
```

---

# 74. Market Signal in Planning

Reader/Market Signal 可改变：

```text
future pacing
promise emphasis
```

但不能：

```text
rewrite committed events
```

---

# 75. Reader Signal Safety

早期真实 reader signal 可能噪声大。

需要：

```text
minimum sample
confidence
lag
```

后续 Quality/Market Spec 再定义。

---

# 76. Plan Storage

Plan 应保存：

```text
version
parent_plan
created_from_canon
reason
status
```

---

# 77. Plan Status

```text
DRAFT
ACTIVE
FROZEN
SUPERSEDED
INVALIDATED
COMPLETED
```

---

# 78. Plan Dependency DAG

Artifact：

```text
SeriesVision
→ MacroArc
→ Volume
→ Arc
→ ChapterPlan
→ ScenePlan
→ Contract
→ ContextArtifact
```

上游变化自动 invalid 下游。

---

# 79. Dependency Hash

每个 Artifact：

```text
input_hashes
```

避免 stale artifact。

---

# 80. Planning Error Codes

建议：

```text
PLAN-001 STALE_CANON
PLAN-002 MISSING_PARENT_PLAN
PLAN-003 GENRE_CONFLICT
PLAN-004 ENGINE_EXHAUSTION
PLAN-005 PROMISE_DEBT
PLAN-006 PROGRESSION_INVALID
PLAN-007 KNOWLEDGE_BOUNDARY_INVALID
PLAN-008 NO_LONG_RUN_PATH
PLAN-009 PLAN_JITTER
PLAN-010 DEPENDENCY_STALE

CONTRACT-001 MISSING_CONTRACT
CONTRACT-002 STALE_CONTRACT
CONTRACT-003 INVALID_PARENT
CONTRACT-004 REQUIRED_TRANSITION_MISSING
CONTRACT-005 FORBIDDEN_TRANSITION_PRESENT
CONTRACT-006 PROTECTED_FACT_CHANGED
CONTRACT-007 KNOWLEDGE_VIOLATION
CONTRACT-008 CAPABILITY_VIOLATION
CONTRACT-009 HASH_MISMATCH
```

---

# 81. Planning Observability

Trace：

```text
plan.series
plan.volume
plan.arc
plan.chapter
plan.scene
plan.replan
contract.compile
contract.validate
```

Metrics：

```text
replan_rate
plan_invalidation_rate
promise_debt
engine_repetition
contract_failure
unexpected_transition
```

---

# 82. AI Coding Rules

实现 Planning/Contract 时 AI MUST：

1. 不硬编码具体小说人物/地点；
2. Contract 必须 compiler 生成；
3. 不允许 missing contract pass；
4. Contract 必须绑定 Canon Parent；
5. Plan 是 future，不能写 Canon；
6. Replan 只改 future；
7. Knowledge Boundary 必须来自 Canon；
8. RequiredTransition 必须机器可读；
9. Hook/Payoff 不当 deterministic truth；
10. 下游 artifact stale 必须显式 invalid。

---

# 83. Repository Layout

建议：

```text
src/anovel/planning/
  series/
  volume/
  arc/
  chapter/
  scene/
  replan/

src/anovel/contracts/
  compiler/
  validation/
  transition/

specs/planning/
  schemas/
  policies/
```

---

# 84. Minimum APIs

```text
build_series_vision(genesis_spec) -> SeriesVision

plan_volume(canon, series_vision) -> VolumePlan
plan_arc(canon, volume_plan) -> ArcPlan
plan_chapter(canon, arc_plan) -> ChapterPlan
plan_scene(canon, chapter_plan) -> list[ScenePlan]

compile_story_contract(...) -> StoryContract
compile_arc_contract(...) -> ArcContract
compile_chapter_contract(...) -> ChapterContract
compile_scene_contract(...) -> SceneContract

replan_future(trigger, canon, active_plan) -> PlanDiff
invalidate_dependents(plan_diff) -> InvalidationSet
```

---

# 85. Required Tests

```text
TEST-PLAN-001 far_future_is_abstract
TEST-PLAN-002 current_scene_is_concrete
TEST-PLAN-003 canon_change_invalidates_future_contract
TEST-PLAN-004 replan_does_not_mutate_canon
TEST-PLAN-005 freeze_horizon_prevents_jitter
TEST-PLAN-006 promise_debt_detected
TEST-PLAN-007 engine_repetition_detected
TEST-PLAN-008 plan_diff_preserves_history

TEST-CONTRACT-001 no_hardcoded_project_data
TEST-CONTRACT-002 missing_contract_blocks
TEST-CONTRACT-003 stale_contract_blocks
TEST-CONTRACT-004 required_transition_validated
TEST-CONTRACT-005 forbidden_transition_blocks
TEST-CONTRACT-006 protected_fact_blocks_change
TEST-CONTRACT-007 knowledge_boundary_enforced
TEST-CONTRACT-008 capability_required
TEST-CONTRACT-009 contract_hash_bound_to_commit
```

---

# 86. V1 Regression Mapping

```text
V1 protagonist hardcode
→ compiled entity refs

V1 missing contract skip
→ production block

V1 placeholder previous hash
→ canon parent hash mandatory

V1 continuity warning
→ required/forbidden transition hard enforcement

V1 static future planning
→ rolling replan + freeze horizon
```

---

# 87. Definition of Done

Planning & Contract v1.0 完成必须证明：

1. GenesisSpec 可生成 SeriesVision；
2. Series → Volume → Arc → Chapter → Scene 全链路存在；
3. 当前 Scene Contract 可从 Canon 动态编译；
4. Contract 无任何具体项目硬编码；
5. Canon 改变后 stale Contract 自动拒绝；
6. Required/Forbidden Transition 可以验证 ActualDelta；
7. Knowledge Boundary 可阻止信息泄漏；
8. Promise/Payoff 能跨 Arc 调度；
9. Future Plan 可 replan 且不改 Canon；
10. 30 章运行中 Plan/Contract 不出现 fork；
11. CommitPermit 能绑定 Contract hash；
12. CI 有 contract regression suite。

---

# 88. Formal ADRs

建议接受：

## ADR-PLAN-001
Planning is hierarchical and rolling-resolution.

## ADR-PLAN-002
Far future remains abstract; near future is concrete.

## ADR-PLAN-003
Plans are versioned intentions and may be replanned.

## ADR-PLAN-004
Contracts are compiled artifacts, never project-specific hardcoded runtime objects.

## ADR-PLAN-005
SceneContract is the default smallest execution contract.

## ADR-PLAN-006
Chapter is the default Phase-1 Canon aggregation boundary.

## ADR-PLAN-007
Required/Forbidden/Protected transitions are first-class contract semantics.

## ADR-PLAN-008
Knowledge and capability boundaries are compiled into SceneContract.

## ADR-PLAN-009
Reader Promise and Payoff scheduling are first-class planning concerns.

## ADR-PLAN-010
Plan changes explicitly invalidate dependent artifacts.

---

# 89. Next Document

下一份正式规范应为：

# `CONTEXT_INTELLIGENCE_SPEC.md`

原因：

现在已经定义：

```text
what this book is
what is true
what should happen next
```

下一步要回答：

> 在具体生成这一 Scene/Chapter 时，模型到底应该看到哪些信息？

下一份将冻结：

```text
Context Compiler
ContextArtifact
Token Budget
Authority Priority
Mandatory Facts
Relevant Canon
Recent Context
Knowledge Boundary
Reference Evidence Injection
Context Hash
Context Debugging
Model Role Interface
```

之后再进入：

```text
PRODUCTION_WORKFLOW_SPEC.md
```

**END OF SPEC**
