# ADR-003 — Event Occurrence 与 Promise 时序语义

**状态**: ACCEPTED

**关联任务**: V2-007

**责任角色**: domain-maintainer

**决策权威**: ARCHITECTURE DECISION

**Machine ADR Status**: ACCEPTED

**日期**: 2026-10-14

**首次适用**: Plan v1.3.1

---

## 问题与依据

### 触发场景

V2-007 (Event Timeline Promise Core) 需要实现"同章多事件与插叙的时间顺序可区分"和"Promise 有承诺兑现窗口和生命周期"，但当前领域模型缺少必要的语义基础：

1. **Event 语义未定义**：
   - V2-061 已创建 `PlannedAction.occurred_event_ref: str | None`，但 Event 本身的语义、occurrence 定义、immutability 尚未建立
   - 无法区分"事件发生"与"章节叙述事件"
   - 无法表达插叙、回忆、未来预告的时间关系

2. **Promise 语义未定义**：
   - Promise 是小说叙事承诺（伏笔、读者预期、剧情承诺），不是 Character Goal
   - Promise 与 Event 的关系未明确（1:1, 1:N, N:1, N:N）
   - Fulfillment 判断标准不清晰

3. **时序模型缺失**：
   - 需要区分 story_time（小说世界时间）、narrative_time（章节呈现顺序）、system_time（系统记录时间）
   - 需要支持精确时间、时间区间、相对顺序
   - 需要支持插叙：事件在故事时间上发生于过去，但在叙述上晚于主线

4. **Canon 集成未明确**：
   - Event occurrence 的 authority 归属未定
   - Promise fulfillment 的 truth authority 未定
   - Idempotency 和 replay safety 未保证

### 现有规范

- **plan/03 §1**：要求 P1 实现 Event/Timeline/Promise，Event 身份与 occurrence 在 V2-007 决定
- **plan/03 §3**：Canon 唯一提交协议，不得引入第二真相存储
- **V2-061 Contract**: 明确 `PlannedAction.occurred_event_ref` 是引用，occurrence authority 属于 V2-007
- **ADR-002**: 建立了 BASE/DERIVED/CACHE 分类，为 ADR-003 提供了模式参考
- **历史归档**: plan/archive/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0 提供了设计参考（§28-35），但需要基于 P1 真实需求裁剪

### 需要决定的边界

1. Event 的身份、occurrence 语义、immutability
2. Promise 的身份、类型、生命周期
3. Event ↔ Promise 关系模型（基数、fulfillment 判断）
4. 时间模型（story_time 表达方式）
5. Timeline 语义（有序 Event 集合，支持插叙）
6. Hard invariants vs soft quality policies
7. Canon ownership 和 idempotency 保证

---

## 决定

### 核心原则

1. **Event 和 Promise 是叙事语义概念**，不是通用任务调度系统
2. **Event occurrence 属于 Canon truth authority**，immutable by default
3. **Promise 是叙事层承诺**，不是 Character Goal（Goal 已在 V2-061 定义）
4. **支持非线性叙事**：插叙、回忆、预告的时间关系可区分
5. **Idempotency 和 replay safety**：重放不产生重复 occurrence，重试不双重兑现
6. **Hard invariants 与 soft policies 分离**：兑现节奏评估属于 quality 层，不硬编码进 domain schema

---

### 决策 A：Event Occurrence 语义

#### Event 定义

```python
@dataclass(frozen=True)
class Event:
    """
    小说世界中已发生事实的权威表示。
    
    BASE fields (all persisted):
        event_id: 唯一稳定标识符 (UUID v4 format)
        project_id: 项目隔离边界
        event_type: 事件类型标识符
        story_time: 事件在小说世界中的发生时间
        participants: 参与实体列表
        occurrence_chapter: 事件首次被叙述的章节引用（可选）
        description: 人类可读描述
        created_at: Canon 提交时间（system_time）
        authority: 权威来源标识
        provenance: 结构化出处元数据
    
    Invariants:
        - event_id 必须 UUID v4 format
        - Event occurrence immutable（修正通过 Retcon，V2-007 不实现）
        - story_time 一旦确定不可修改（除非 Retcon）
        - participants 引用的 EntityId 必须存在于同一 project
    """
    event_id: EventId  # NewType("EventId", str)
    project_id: ProjectId
    event_type: str
    story_time: StoryTime
    participants: list[EntityId]
    occurrence_chapter: str | None
    description: str
    created_at: datetime
    authority: str
    provenance: dict[str, str]
```

#### Story Time 模型

支持三种时间表达：

```python
@dataclass(frozen=True)
class PreciseTime:
    """精确时间点（如已知具体日期时间）"""
    timestamp: str  # ISO 8601 format or story-world calendar
    precision: Literal["year", "month", "day", "hour", "minute"]

@dataclass(frozen=True)
class IntervalTime:
    """时间区间（如"春天"、"三个月内"）"""
    earliest: str
    latest: str
    description: str  # "spring 2013", "within 3 months"

@dataclass(frozen=True)
class RelativeTime:
    """相对时间（相对于另一事件或叙述点）"""
    anchor_event_id: EventId | None
    offset_description: str  # "3 days after X", "before story begins"
    relative_order: Literal["before", "after", "during", "concurrent"]

StoryTime = PreciseTime | IntervalTime | RelativeTime
```

#### 关键语义

1. **Occurrence vs Disclosure**：
   - **Occurrence**：事件在小说世界时间（story_time）发生
   - **Disclosure**：事件在叙述中被揭示（occurrence_chapter）
   - 插叙场景：Event.story_time = "10 years ago", occurrence_chapter = 80

2. **Immutability**：
   - Event 一旦提交到 Canon，默认 immutable
   - 修正通过 Retcon Event（V2-007 不实现，延期到后续任务）

3. **Authority**：
   - Event occurrence 的唯一 truth authority = Canon
   - PlannedAction.occurred_event_ref 是引用，不是 occurrence authority

---

### 决策 B：Promise 语义

#### Promise 定义

```python
@dataclass(frozen=True)
class Promise:
    """
    叙事层面对读者的承诺（伏笔、预期、剧情承诺）。
    
    BASE fields (all persisted):
        promise_id: 唯一稳定标识符 (UUID v4 format)
        project_id: 项目隔离边界
        promise_type: 承诺类型（枚举或扩展标识符）
        opened_at_chapter: 承诺建立的章节引用
        target_entities: 相关实体（可选）
        target_window: 期望兑现的时间窗口（story_time，可选）
        status: 承诺状态
        description: 人类可读承诺描述
        created_at: Canon 提交时间
        authority: 权威来源标识
        provenance: 结构化出处元数据
    
    Invariants:
        - promise_id 必须 UUID v4 format
        - status = FULFILLED 必须有至少一个 PromiseFulfillmentLink
        - target_entities 引用的 EntityId 必须存在于同一 project
    """
    promise_id: PromiseId  # NewType("PromiseId", str)
    project_id: ProjectId
    promise_type: str
    opened_at_chapter: str
    target_entities: list[EntityId]
    target_window: StoryTime | None
    status: PromiseStatus
    description: str
    created_at: datetime
    authority: str
    provenance: dict[str, str]
```

#### Promise Lifecycle

```python
class PromiseStatus(Enum):
    """
    Promise 生命周期状态。
    
    OPEN: 承诺已建立，尚未兑现
    FULFILLED: 承诺已完全兑现
    FAILED: 承诺明确失败（如角色死亡导致复仇承诺失败）
    ABANDONED: 承诺被放弃或不再相关
    """
    OPEN = "OPEN"
    FULFILLED = "FULFILLED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
```

**说明**：
- **不包含** `REINFORCED`, `DELAYED`, `PARTIAL`：这些属于 soft quality evaluation，不是 hard state
- **FULFILLED** 是确定性状态，由 PromiseFulfillmentLink 支撑
- **FAILED** 表示承诺明确无法兑现（非简单未兑现）
- **ABANDONED** 用于叙事方向改变、承诺不再相关的情况

#### Promise 与 Character Goal 的区分

| 维度 | Promise (V2-007) | Goal (V2-061) |
|------|------------------|---------------|
| 定义 | 叙事层面对读者的承诺 | 角色内心的目标 |
| 作用域 | 跨角色、全局叙事 | 单个角色 |
| 评估者 | 读者、叙事规划层 | 角色本身 |
| 示例 | "这段感情会发展" | 角色：我要追求她 |
| 权威 | V2-007 | V2-061 |
| 失败语义 | 叙事承诺破裂 | 角色目标未达成 |

---

### 决策 C：Event ↔ Promise Fulfillment 模型

采用 **独立建模 + Link 表达关系** 方案（Option C）。

#### Fulfillment Link 定义

```python
@dataclass(frozen=True)
class PromiseFulfillmentLink:
    """
    Promise 与 Event 之间的兑现关系链接。
    
    BASE fields (all persisted):
        link_id: 唯一标识符 (UUID v4 format)
        promise_id: 关联的 Promise
        event_id: 兑现承诺的 Event
        contribution_role: 此事件对承诺兑现的贡献角色
        created_at: 链接建立时间
        authority: 权威来源
        provenance: 出处元数据
    
    Invariants:
        - 同一 (promise_id, event_id) 对不可重复创建（idempotency）
        - promise_id 和 event_id 必须存在于同一 project
        - event_id 必须已提交到 Canon
    """
    link_id: str  # UUID v4
    promise_id: PromiseId
    event_id: EventId
    contribution_role: ContributionRole
    created_at: datetime
    authority: str
    provenance: dict[str, str]

class ContributionRole(Enum):
    """
    Event 对 Promise 兑现的贡献角色。
    
    PRIMARY: 主要兑现事件（如复仇成功）
    SUPPORTING: 支持性事件（如渐进式感情发展中的一次帮助）
    COMPLETE: 单一完整兑现（一个事件即完全兑现承诺）
    """
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"
    COMPLETE = "COMPLETE"
```

#### Fulfillment 判断逻辑

1. **Promise.status = FULFILLED** 的充要条件：
   - 存在至少一个 `PromiseFulfillmentLink` 其中 `contribution_role = COMPLETE`，或
   - 存在至少一个 `contribution_role = PRIMARY` 的 Link

2. **部分兑现**：
   - 多个 `contribution_role = SUPPORTING` 的 Link
   - Promise.status 仍为 OPEN，直到有 PRIMARY 或 COMPLETE Link

3. **Idempotency**：
   - 相同 `(promise_id, event_id)` 对不可重复创建 Link
   - 重试时返回已存在的 Link，不创建新记录

#### 支持的兑现模式

| 场景 | Event 数量 | Link 配置 | 说明 |
|------|-----------|----------|------|
| 简单兑现 | 1 | 1 COMPLETE | 一个事件完全兑现（如复仇成功） |
| 渐进兑现 | N | N-1 SUPPORTING + 1 PRIMARY | 多事件累计（如感情发展） |
| 一事多诺 | 1 | 多个 Promise 各有 Link | 高潮事件兑现多个承诺 |
| 多事一诺 | N | 指向同一 Promise | 复杂兑现（如多步骤复仇计划） |

---

### 决策 D：Timeline 语义

#### Timeline 定义

```python
@dataclass(frozen=True)
class Timeline:
    """
    有序 Event 集合，支持非线性叙事。
    
    BASE fields (all persisted):
        timeline_id: 唯一标识符
        project_id: 项目隔离边界
        name: Timeline 名称（如 "主线", "角色A回忆线"）
        events: Event ID 列表（按 story_time 排序）
        narrative_sequence: Event ID 列表（按 occurrence_chapter 排序，可选）
        created_at: 创建时间
        authority: 权威来源
    
    Invariants:
        - events 中的 Event 必须属于同一 project
        - events 列表按 story_time 可比较顺序排序
        - narrative_sequence（如存在）按 occurrence_chapter 排序
    """
    timeline_id: str  # UUID v4
    project_id: ProjectId
    name: str
    events: list[EventId]  # story_time order
    narrative_sequence: list[EventId] | None  # occurrence_chapter order
    created_at: datetime
    authority: str
```

#### Timeline 语义

1. **Story Order**：
   - `Timeline.events` 按小说世界时间（story_time）排序
   - 支持时间区间、相对时间的偏序关系

2. **Narrative Order**：
   - `Timeline.narrative_sequence` 按叙述顺序（occurrence_chapter）排序
   - 可选字段，用于明确追踪插叙、倒叙

3. **插叙支持**：
   - Event X: story_time="10 years ago", occurrence_chapter=80
   - Event Y: story_time="现在", occurrence_chapter=5
   - Story order: [X, Y]
   - Narrative order: [Y, X]

4. **不要求完整约束求解**：
   - V2-007 不实现 temporal constraint solver
   - 支持人工/planning 层指定顺序
   - 冲突检测属于 quality 层，不阻塞提交

---

### 决策 E：Hard Invariants

以下为 **必须由 domain 层强制执行** 的 hard invariants：

1. **Identity Uniqueness**：
   - `Event.event_id` 全局唯一
   - `Promise.promise_id` 全局唯一
   - `PromiseFulfillmentLink` 的 `(promise_id, event_id)` 对唯一

2. **Occurrence Immutability**：
   - Event 提交后，`event_id`, `story_time`, `event_type`, `participants` 不可修改
   - 修正通过 Retcon Event（V2-007 不实现）

3. **Fulfillment Evidence**：
   - `Promise.status = FULFILLED` 必须有至少一个 PromiseFulfillmentLink
   - Link 指向的 Event 必须已提交到 Canon

4. **Project Isolation**：
   - Event, Promise, Link 不可跨 project 引用
   - 所有 EntityId 引用必须属于同一 project

5. **Terminal State Protection**：
   - `Promise.status = FULFILLED/FAILED/ABANDONED` 不可回退到 OPEN
   - State transition 单向：OPEN → {FULFILLED | FAILED | ABANDONED}

6. **Reference Integrity**：
   - `PlannedAction.occurred_event_ref` 指向的 Event 必须存在
   - `PromiseFulfillmentLink.event_id` 指向的 Event 必须存在
   - `PromiseFulfillmentLink.promise_id` 指向的 Promise 必须存在

---

### 决策 F：Soft Quality Policies（不在 V2-007 硬编码）

以下评估属于 **quality/planning 层**，不作为 domain invariant：

1. **Promise 兑现节奏**：
   - "Promise 应在 N 章内兑现"
   - "高潮章节应兑现多个 Promise"
   - 由 planning/quality 层评估打分，不阻塞提交

2. **Event 频率评估**：
   - "章节应包含合理数量事件"
   - 属于 pacing 评估，不是 hard constraint

3. **Promise 类型平衡**：
   - "不同类型 Promise 应均衡分布"
   - 属于叙事质量评估

4. **Fulfillment 合理性**：
   - "SUPPORTING Event 是否真正支持 Promise"
   - 由 intelligence/quality 层评估，V2-007 只记录 Link

---

### 决策 G：Canon Ownership 与 Idempotency

#### Canon Authority

1. **Event Occurrence**：
   - 唯一 truth authority: Canon (V2-009/V2-010)
   - 通过 CanonCommitService 提交
   - Event 是 immutable fact

2. **Promise State**：
   - 唯一 truth authority: Canon
   - Promise 状态变更通过 Canon Commit

3. **Fulfillment Link**：
   - 通过 Canon Commit 建立
   - Link 建立后 immutable（不可修改 contribution_role）

#### Idempotency 保证

1. **Event Commit Idempotency**：
   - 使用稳定 idempotent key（由 workflow 层提供）
   - 相同 key + 相同 payload → 返回原 receipt
   - 相同 key + 不同 payload → 报冲突

2. **Promise Fulfillment Idempotency**：
   - `(promise_id, event_id)` 对作为 natural key
   - 重复创建相同 Link → 返回已存在 Link，不创建新记录

3. **Replay Safety**：
   - Event 重放不产生重复 occurrence（由 idempotent key 保证）
   - Promise fulfillment 重试不双重兑现（由 Link uniqueness 保证）

4. **Deterministic Derived State**：
   - `Promise.status = FULFILLED` 可从 Link 集合确定性推导
   - Timeline 顺序可从 Event.story_time 确定性重建

---

## 拒绝的备选方案

### Option A：Promise 直接绑定单个 Event

```text
Promise.fulfillment_event_ref → EventId
```

**拒绝理由**：
- 无法表达渐进式兑现（多事件累计）
- 无法表达一事件兑现多承诺
- Promise 必须预知具体事件，缺乏灵活性
- 不符合真实小说叙事模式

---

### Option B：Promise 绑定 Outcome Condition

```text
Promise.outcome_condition: StructuredCondition
Event.outcomes: StructuredOutcome
自动匹配评估 fulfillment
```

**拒绝理由**：
- `outcome_condition` 结构化复杂，容易退化为自由文本
- 自动匹配需要复杂推理引擎，超出 P1 范围
- `fulfillment_degree: 0.0~1.0` 评分属于 soft policy，不应是 hard state
- 过度设计，不符合"保持简单"原则

---

### Option C（被接受）：独立建模 + Link

**接受理由**：
- Event 和 Promise 独立建模，各有清晰语义
- Link 表达 N:N 关系，灵活支持所有兑现模式
- Contribution_role 语义明确（3 个枚举值）
- 支持插叙：Event.story_time 独立于 occurrence_chapter
- 符合 Canon 架构：Event 是 fact，Link 是 relationship
- 实现简单，可测试

---

### 历史归档方案的裁剪

**历史归档建议**（plan/archive/gptdoc NARRATIVE_DOMAIN_SPEC.md §28-35）：

```text
Event 字段: id, event_type, occurred_at, participants, location,
           preconditions, actions, outcomes, causes, effects, evidence, authority

Promise Lifecycle: OPEN | REINFORCED | DELAYED | PARTIAL | PAID | BROKEN | 
                   ABANDONED | SUPERSEDED
```

**本 ADR 裁剪**：
- **Event 字段减少**：去除 `preconditions`, `causes`, `effects`（属于高级因果推理，延期到后续任务）
- **Promise Lifecycle 简化**：去除 `REINFORCED`, `DELAYED`, `PARTIAL`（属于 soft policy，不是 hard state）
- **不实现 Mystery/Clue 系统**（延期到 P3/P4 planning 模块）
- **不实现 Temporal Constraint Solver**（V2-007 只要求"可区分"，不要求自动求解）

**裁剪理由**：
- V2-007 目标：同章多事件与插叙的时间顺序可区分 + Promise 有兑现窗口和生命周期
- 不预先实现 P10/P11 高级推理能力
- 保持 P1 domain model 简单、可验证

---

## 影响与验证

### 对 V2-061 的影响

1. **PlannedAction.occurred_event_ref 语义明确**：
   - 该字段指向 V2-007 定义的 Event.event_id
   - V2-061 不拥有 occurrence authority，只持有引用
   - Occurrence 判断必须查询 V2-007 Event 是否存在

2. **兼容性**：
   - V2-061 无需修改（occurred_event_ref 已是 str | None）
   - V2-007 实现后，该引用可被验证

### 对 V2-005/V2-006 的影响

1. **Entity 引用**：
   - Event.participants: list[EntityId] 使用 V2-005 EntityId
   - Promise.target_entities: list[EntityId] 使用 V2-005 EntityId
   - 必须遵守 project isolation

2. **无 Schema 变更**：
   - V2-005/V2-006 domain model 不需修改

### 对 Canon (V2-009/V2-010) 的影响

1. **Canon Commit 协议扩展**：
   - 需支持 Event 类型提交
   - 需支持 Promise 类型提交
   - 需支持 PromiseFulfillmentLink 类型提交

2. **Idempotency Key**：
   - Event 使用 workflow 层提供的稳定 key
   - Link 使用 `(promise_id, event_id)` 作为 natural key

### Schema 影响

**新增 Schema 文件**：
- `specs/schemas/event.schema.json`
- `specs/schemas/promise.schema.json`
- `specs/schemas/promise-fulfillment-link.schema.json`
- `specs/schemas/timeline.schema.json`

**Schema 设计原则**：
- 仅包含 BASE 字段（遵循 ADR-002 原则）
- `additionalProperties: false`
- UUID v4 format validation for all IDs

### 代码影响

**新增模块**：
- `src/anovel/domain/event.py`
- `src/anovel/domain/promise.py`
- `src/anovel/domain/timeline.py`

**新增测试**：
- `tests/contract/test_v2_007_event.py`
- `tests/contract/test_v2_007_promise.py`
- `tests/contract/test_v2_007_fulfillment.py`
- `tests/contract/test_v2_007_timeline.py`

### 数据库影响（V2-009 实现时）

**预期新表**（Schema 设计属于 V2-009）：
- `events`
- `promises`
- `promise_fulfillment_links`
- `timelines`
- `timeline_events` (junction table)

**不在 ADR-003 范围**：
- 具体 column types
- Indexes
- Migration scripts

### 验收影响

**AT-V2-007 必须验证**：
1. 同章多事件时间顺序可区分
2. 插叙场景：story_time ≠ occurrence_chapter
3. Promise 创建、兑现、状态转换
4. PromiseFulfillmentLink 唯一性
5. Event occurrence idempotency
6. Project isolation

### 迁移要求

**P1 无需迁移**：
- 当前无生产数据
- V2-007 是新增能力，不影响已有 V2-005/V2-006/V2-061 数据

---

## 生效与替代

### 生效条件

1. **ADR-003 状态 = ACCEPTED**
2. **登记到 plan/machine/decision-register.yaml**
3. **V2-007 实现前置条件满足**

### 不替代其他 ADR

ADR-003 是独立决策，不替代 ADR-001/ADR-002。

### Machine 登记更新

```yaml
- id: ADR-003
  title: Event occurrence 与 Promise 时序
  status: ACCEPTED
  owner_role: domain-maintainer
  related_tasks:
  - V2-007
  decision_due_task: V2-007
  timing: before_interface_implementation
  decision_record: plan/decisions/ADR-003_EVENT_PROMISE_TEMPORAL_SEMANTICS.md
  verification_refs: []
```

### V2-007 Implementation Constraints

V2-007 实现必须：
1. 严格遵循 ADR-003 定义的 Event/Promise/Link/Timeline 语义
2. 实现所有 hard invariants 验证
3. 不硬编码 soft quality policies
4. 通过 Canon Commit 提交 Event/Promise
5. 保证 idempotency 和 replay safety
6. 支持插叙场景测试（story_time vs occurrence_chapter）

---

## 后果

### 积极后果

1. **领域模型清晰**：
   - Event/Promise 语义明确，不与 Goal 混淆
   - 时间模型支持非线性叙事

2. **架构边界明确**：
   - Event occurrence authority = Canon
   - Promise ≠ Character Goal（层次清晰）
   - Hard invariants vs soft policies 分离

3. **实现可行**：
   - 模型简单，P1 可实现
   - 不预先实现 P10 高级能力
   - 测试可验证

4. **未来扩展友好**：
   - Retcon Event 可在后续任务实现
   - Causality graph 可作为 Event 扩展
   - Mystery/Clue 可作为 Promise 特殊类型
   - Temporal constraint solver 可在 planning 层实现

### 消极后果

1. **需要额外 Link 表**：
   - PromiseFulfillmentLink 增加存储复杂度
   - 可接受：换取灵活性和清晰语义

2. **StoryTime 多态复杂性**：
   - PreciseTime | IntervalTime | RelativeTime 需要 union type 处理
   - 可接受：符合真实小说叙事需求

### 风险

1. **如未来需要 Retcon**：
   - ADR-003 明确 Event immutable by default
   - Retcon 通过独立 ADR 定义
   - 不阻塞当前决策

2. **如需要完整 temporal reasoning**：
   - ADR-003 支持基础时间顺序表达
   - 高级约束求解属于 planning 层
   - 不阻塞 V2-007 验收

---

## 验证要求

### 单元测试

```python
def test_event_immutability():
    """Event 是 frozen dataclass，不可修改"""
    event = Event(...)
    with pytest.raises(FrozenInstanceError):
        event.story_time = ...

def test_promise_fulfillment_requires_link():
    """Promise.status=FULFILLED 必须有 Link"""
    promise = Promise(..., status=PromiseStatus.FULFILLED)
    links = get_fulfillment_links(promise.promise_id)
    assert len(links) > 0
    assert any(link.contribution_role in [ContributionRole.PRIMARY, ContributionRole.COMPLETE] 
               for link in links)

def test_fulfillment_link_idempotency():
    """相同 (promise_id, event_id) 不可重复创建"""
    link1 = create_link(promise_id="p1", event_id="e1")
    link2 = create_link(promise_id="p1", event_id="e1")  # 重复
    assert link1.link_id == link2.link_id  # 返回相同 Link

def test_project_isolation():
    """Event/Promise 不可跨 project 引用"""
    event = Event(project_id="proj1", participants=[EntityId("entity_from_proj2")])
    with pytest.raises(ValueError):
        validate_project_isolation(event)

def test_story_time_vs_occurrence_chapter():
    """插叙：story_time 早于主线，occurrence_chapter 晚于主线"""
    flashback = Event(
        event_id="e1",
        story_time=PreciseTime(timestamp="2010-01-01", precision="day"),
        occurrence_chapter="ch80"
    )
    mainline = Event(
        event_id="e2",
        story_time=PreciseTime(timestamp="2020-01-01", precision="day"),
        occurrence_chapter="ch05"
    )
    
    # Story order
    story_order = sort_by_story_time([flashback, mainline])
    assert story_order == [flashback, mainline]
    
    # Narrative order
    narrative_order = sort_by_occurrence_chapter([flashback, mainline])
    assert narrative_order == [mainline, flashback]
```

### Contract 测试

```python
def test_v2_061_occurred_event_ref_integration():
    """PlannedAction.occurred_event_ref 指向 V2-007 Event"""
    event = Event(event_id="evt_123", ...)
    commit_to_canon(event)
    
    planned_action = PlannedAction(
        ...,
        occurred_event_ref="evt_123"
    )
    
    # 验证引用存在
    assert get_event(planned_action.occurred_event_ref) == event
    
def test_gradual_promise_fulfillment():
    """渐进式兑现：多 SUPPORTING + 1 PRIMARY"""
    promise = Promise(promise_id="p1", status=PromiseStatus.OPEN)
    
    # 第一个支持事件
    event1 = Event(event_id="e1", ...)
    link1 = PromiseFulfillmentLink(
        promise_id="p1",
        event_id="e1",
        contribution_role=ContributionRole.SUPPORTING
    )
    # Promise 仍为 OPEN
    assert promise.status == PromiseStatus.OPEN
    
    # 第二个支持事件
    event2 = Event(event_id="e2", ...)
    link2 = PromiseFulfillmentLink(
        promise_id="p1",
        event_id="e2",
        contribution_role=ContributionRole.SUPPORTING
    )
    
    # 最终主要兑现事件
    event3 = Event(event_id="e3", ...)
    link3 = PromiseFulfillmentLink(
        promise_id="p1",
        event_id="e3",
        contribution_role=ContributionRole.PRIMARY
    )
    
    # 现在 Promise 应为 FULFILLED
    promise_updated = update_promise_status(promise.promise_id)
    assert promise_updated.status == PromiseStatus.FULFILLED
```

### AT-V2-007 验收场景

1. **AC-1：同章多事件时间顺序**
   - 给定：一章包含 3 个事件
   - 当：事件有明确 story_time
   - 则：可通过 Timeline 查询 story_time 顺序

2. **AC-2：插叙场景**
   - 给定：回忆章节（第 80 章）
   - 当：描述 10 年前事件
   - 则：Event.story_time = "10 years ago", occurrence_chapter = 80
   - 则：Story order ≠ narrative order

3. **AC-3：Promise 生命周期**
   - 给定：新建 Promise（status=OPEN）
   - 当：关联事件发生并创建 PRIMARY Link
   - 则：Promise.status → FULFILLED
   - 则：不可回退到 OPEN

4. **AC-4：Promise 与 Goal 区分**
   - 给定：角色有 Goal "revenge"
   - 则：Character.goals 包含该 Goal（V2-061）
   - 给定：叙事有 Promise "复仇会成功"
   - 则：独立创建 Promise 对象（V2-007）
   - 则：两者不混淆

---

## 批准前提条件

1. **语义完整性**：Event/Promise/Link/Timeline 语义明确且无歧义
2. **权威边界清晰**：V2-005/V2-006/V2-061/V2-007/Canon 边界明确
3. **Hard/Soft 分离**：Hard invariants 与 soft policies 明确区分
4. **P1 范围合理**：不预先实现 P10 高级能力
5. **V2-007 可实现**：实现约束明确，验收可测试
6. **无语义冲突**：与 ADR-001/ADR-002 及现有 Contract 无冲突

**当前状态**: ACCEPTED — 2026-10-14

---

## 参考

- plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md §1, §3
- V2-061 Implementation Contract (occurred_event_ref authority boundary)
- ADR-002 (BASE/DERIVED/CACHE 分类原则)
- plan/archive/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/NARRATIVE_DOMAIN_SPEC.md (§28-35, 历史设计参考)
- V2-007 Task Definition (plan/machine/implementation-backlog.yaml)
