# ADR-002 — Character 基础/派生/缓存状态与 Schema 一致策略

**状态**: PROPOSED / DRAFT

**关联任务**: V2-061

**责任角色**: domain-maintainer

**决策权威**: 待独立审核与正式批准

**Machine ADR Status**: REQUIRED

**日期**: 2026-10-10

**冻结 Contract 基线**: d35be3dbb9c6613ff76b70f164427caa84d8da11

---

## 问题与依据

V2-061 Character 领域模型包含多类状态字段：

1. **核心语义状态** — 必须持久化保存的权威领域真值
2. **纯派生投影** — 可从核心状态确定性计算、不依赖外部权威
3. **运行时评估缓存** — 依赖外部 Canon 上下文、非权威、可能过时

当前冻结 Contract (d35be3d) 明确区分了这三类，但未最终决定：

- 具体哪些 Character 字段属于哪一类？
- 序列化/反序列化时如何处理各类字段？
- `character.schema.json` 应包含哪些字段？
- 语义相等性检查是否包含缓存字段？
- 如何满足 Machine SSOT 要求"合法派生字段和非默认值往返不丢失"？

缺少此决策将导致：

- 不同实现序列化不同状态
- 派生状态被误当作权威真值持久化
- 过时的 CACHE 污染 Canon
- 往返测试失败或定义模糊
- Schema 与代码类型不一致

V2-061 必须在接口实现前冻结此决策。

---

## 决定

### 状态分类定义

#### BASE（基础权威状态）

- **定义**: 语义权威领域状态，不可从其他字段无损重构
- **序列化**: 必须持久化到语义 JSON payload
- **语义相等**: 参与 `==` 比较
- **往返要求**: 反序列化后 BASE 状态必须精确相等

#### DERIVED（派生状态）

- **定义**: 纯函数确定性投影，仅依赖本地 BASE 状态
- **序列化**: 不持久化；加载后从恢复的 BASE 重新计算
- **语义相等**: 不作为独立存储字段比较；重新计算结果必须语义等价
- **依赖边界**: 禁止依赖外部 Canon、数据库、Provider、当前时钟、全局上下文

#### CACHE（运行时评估缓存）

- **定义**: 需要外部 Canon 上下文的非权威评估结果
- **序列化**: **不持久化**到 V2-061 P1 语义 schema payload
- **语义相等**: **不参与** (`field(compare=False)` 强制)
- **重新生成**: 外部权威可用时可重新评估；Canon 变化时必须失效

---

### Character 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 重计算来源 | 权威 |
|------|------|--------|--------|------------|------|
| `entity_id` | BASE | Yes | Yes | — | V2-005 (identity) |
| `project_id` | BASE | Yes | Yes | — | V2-005 (membership) |
| `lifecycle` | BASE | Yes | Yes | — | V2-061 |
| `knowledge` | BASE | Yes | Yes | — | V2-061 |
| `goals` | BASE | Yes | Yes | — | V2-061 |
| `intents` | BASE | Yes | Yes | — | V2-061 |
| `planned_actions` | BASE | Yes | Yes | — | V2-061 |
| `created_at` | BASE | Yes | Yes | — | V2-061 |
| `updated_at` | BASE | Yes | Yes | — | V2-061 |
| `authority` | BASE | Yes | Yes | — | V2-061 |
| `provenance` | BASE | Yes | Yes | — | V2-061 |
| `active_goals` | DERIVED | No | Recomputed | Filter BASE `goals` | V2-061 |
| `knowledge_count` | DERIVED | No | Recomputed | `len(knowledge)` | V2-061 |

**说明**:
- `entity_id`, `project_id`: V2-061 持久化这些引用字段，但 identity/project membership 权威归 V2-005
- `created_at`, `updated_at`, `authority`, `provenance` 是系统元数据，但仍属 BASE 语义状态
- 如未来需区分"语义 BASE"与"系统元数据"，需明确定义，不在本 ADR 范围

---

### CharacterKnowledge 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 重计算来源 | 权威 |
|------|------|--------|--------|------------|------|
| `knower` | BASE | Yes | Yes | — | V2-061 |
| `proposition` | BASE | Yes | Yes | — | V2-061 |
| `knowledge_level` | BASE | Yes | Yes | — | V2-061 |
| `acquisition_source` | BASE | Yes | Yes | — | V2-061 |
| `source_character` | BASE | Yes | Yes | — | V2-061 |
| `source_ref` | BASE | Yes | Yes | — | V2-061 |
| `basis_ref` | BASE | Yes | Yes | — | V2-061 |
| `acquired_at` | BASE | Yes | Yes | — | V2-061 |
| `story_time_ref` | BASE | Yes | Yes | — | V2-061 |
| `confidence` | BASE | Yes | Yes | — | V2-061 |
| `aligns_with_fact` | **CACHE** | **No** | **No** | Canon (V2-005/006/007) | 外部评估 |

**关键决策**:

```python
aligns_with_fact: bool | None = field(default=None, compare=False)
```

- 不持久化到语义 JSON payload
- 反序列化后 `aligns_with_fact = None`
- 需要时通过外部 Canon 上下文重新评估
- 不影响 `CharacterKnowledge` 语义相等性

---

### Proposition 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 权威 |
|------|------|--------|--------|------|
| `proposition_id` | BASE | Yes | Yes | V2-061 |
| `project_id` | BASE | Yes | Yes | V2-061 |
| `subject` | BASE | Yes | Yes | V2-061 |
| `predicate` | BASE | Yes | Yes | V2-061 |
| `object` | BASE | Yes | Yes | V2-061 |
| `context` | BASE | Yes | Yes | V2-061 |

**Context 不可变性要求**:

- 类型签名: `context: Mapping[str, Any] | None`
- 输入可能是 JSON object
- 领域构造时必须规范化/**递归深度冻结**为不可变表示
- 推荐: 递归冻结结构（注意 `MappingProxyType` 仅浅冻结，需递归处理嵌套）
- **存储的 `Proposition.context` 禁止是可变 dict**
- 避免创建后修改导致 PropositionId 碰撞不变式失效

**碰撞不变式**:

```python
same PropositionId + different BASE payload → REJECT
```

---

### Goal 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 权威 |
|------|------|--------|--------|------|
| `goal_id` | BASE | Yes | Yes | V2-061 |
| `character` | BASE | Yes | Yes | V2-061 |
| `description` | BASE | Yes | Yes | V2-061 |
| `target_state` | BASE | Yes | Yes | V2-061 |
| `status` | BASE | Yes | Yes | V2-061 |
| `priority` | BASE | Yes | Yes | V2-061 |
| `formed_at` | BASE | Yes | Yes | V2-061 |
| `resolved_at` | BASE | Yes | Yes | V2-061 |

**`target_state` 规范化**:

- 如接受结构化 mapping，需定义不可变性/规范化要求
- 避免不稳定的语义相等性
- 不扩展为目标推理引擎

---

### Intent 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 权威 |
|------|------|--------|--------|------|
| `intent_id` | BASE | Yes | Yes | V2-061 |
| `character` | BASE | Yes | Yes | V2-061 |
| `goal_ref` | BASE | Yes | Yes | V2-061 |
| `description` | BASE | Yes | Yes | V2-061 |
| `formed_at` | BASE | Yes | Yes | V2-061 |
| `abandoned_at` | BASE | Yes | Yes | V2-061 |

---

### PlannedAction 字段分类

| 字段 | 分类 | 持久化 | 相等性 | 权威 |
|------|------|--------|--------|------|
| `action_id` | BASE | Yes | Yes | V2-061 |
| `character` | BASE | Yes | Yes | V2-061 |
| `action_description` | BASE | Yes | Yes | V2-061 |
| `intent_ref` | BASE | Yes | Yes | V2-061 |
| `planned_for` | BASE | Yes | Yes | V2-061 |
| `status` | BASE | Yes | Yes | V2-061 |
| `occurred_event_ref` | BASE | Yes | Yes | V2-061 |
| `created_at` | BASE | Yes | Yes | V2-061 |
| `cancelled_at` | BASE | Yes | Yes | V2-061 |

**重要不变式**:

```python
occurred_event_ref is a reference/link, NOT occurrence authority
```

- `occurred_event_ref` 是引用字段
- 不能从其推断客观发生真值
- V2-007 拥有唯一发生权威
- ADR-002 不将此引用转化为派生客观真值

---

## Schema 表示

**Machine 工件**: `specs/schemas/character.schema.json`

**结构**:

- 单一 schema 文件
- 通过 `$defs` 嵌入: `Proposition`, `CharacterKnowledge`, `Goal`, `Intent`, `PlannedAction`
- **仅包含 BASE 字段作为持久化语义属性**

**排除**:

- DERIVED 字段（如 `active_goals`, `knowledge_count`）
- CACHE 字段（如 `aligns_with_fact`）

**`aligns_with_fact` 处理**:

在推荐决策下:

```text
aligns_with_fact 不是合法的持久化语义 JSON 属性
```

**Schema 验证偏好**:

```json
"additionalProperties": false
```

（与项目 schema 约定一致时）

**禁止创建**:

```text
knowledge.schema.json
```

除非有独立的 Machine SSOT 变更。

---

## 序列化/反序列化

### BASE 字段

```python
# 序列化
json_payload = {
    "entity_id": char.entity_id,
    "project_id": char.project_id,
    "lifecycle": char.lifecycle,
    "knowledge": serialize_knowledge_dict(char.knowledge),  # BASE only
    "goals": [serialize_goal(g) for g in char.goals],
    # ... other BASE fields
}

# 反序列化
char = Character(
    entity_id=data["entity_id"],
    project_id=data["project_id"],
    lifecycle=data["lifecycle"],
    knowledge=deserialize_knowledge_dict(data["knowledge"]),
    goals=[deserialize_goal(g) for g in data["goals"]],
    # ... other BASE fields
)
```

### CharacterKnowledge 序列化

```python
# 序列化（不包含 aligns_with_fact）
knowledge_payload = {
    "knower": ck.knower,
    "proposition": serialize_proposition(ck.proposition),
    "knowledge_level": ck.knowledge_level,
    "acquisition_source": ck.acquisition_source,
    "source_character": ck.source_character,
    "source_ref": ck.source_ref,
    "basis_ref": ck.basis_ref,
    "acquired_at": ck.acquired_at,
    "story_time_ref": ck.story_time_ref,
    "confidence": ck.confidence,
    # aligns_with_fact NOT included
}

# 反序列化
ck = CharacterKnowledge(
    knower=data["knower"],
    proposition=deserialize_proposition(data["proposition"]),
    knowledge_level=data["knowledge_level"],
    acquisition_source=data["acquisition_source"],
    source_character=data.get("source_character"),
    source_ref=data.get("source_ref"),
    basis_ref=data.get("basis_ref"),
    acquired_at=data.get("acquired_at"),
    story_time_ref=data.get("story_time_ref"),
    confidence=data.get("confidence"),
    # aligns_with_fact defaults to None
)
```

### DERIVED 字段

```python
# 不序列化
# 加载后重新计算

@property
def active_goals(self) -> list[Goal]:
    return [g for g in self.goals if g.status == "ACTIVE"]

@property
def knowledge_count(self) -> int:
    return len(self.knowledge)
```

### CACHE 字段

```python
# 不序列化到语义 payload
# 反序列化后设为 None
# 需要时通过外部 Canon 重新评估

def evaluate_truth_alignment(
    ck: CharacterKnowledge,
    canon: Canon
) -> bool | None:
    """Runtime evaluation using external Canon context."""
    # Implementation queries V2-005/V2-006/V2-007
    ...
```

---

## 语义相等性

### BASE 字段相等

```python
char1.entity_id == char2.entity_id
char1.project_id == char2.project_id
char1.lifecycle == char2.lifecycle
char1.knowledge == char2.knowledge  # dict 精确相等
char1.goals == char2.goals  # list 精确相等
# ... other BASE fields
```

### DERIVED 字段相等

```python
# 不作为存储字段独立比较
# 重新计算结果必须等价
char1.active_goals == char2.active_goals  # 从 BASE 重算
```

### CACHE 字段相等

```python
# 不参与语义相等性检查
# field(compare=False) 强制排除

# 以下断言必须成立
ck1 = CharacterKnowledge(..., aligns_with_fact=True)
payload = serialize(ck1)
ck2 = deserialize(payload)  # aligns_with_fact=None

assert ck1 == ck2  # PASS (compare=False 排除 aligns_with_fact)
```

---

## 往返语义

### Machine SSOT 合规性

**Machine 要求**: 合法派生字段和非默认值往返不丢失

**适用域明确**:

本 ADR 定义三类状态及其对 Machine SSOT 的映射:

#### 持久化 BASE 义务

合法 persisted BASE 字段及其合法非默认值:

→ 精确语义往返保留

**Machine SSOT 要求适用**: BASE 字段必须往返不丢失

#### DERIVED 义务

合法 DERIVED 视图:

→ 不持久化
→ 从恢复的 BASE 重新计算
→ 语义结果必须等价

**Machine SSOT 要求适用**: 恢复的 BASE 必须产生等价的 DERIVED 结果

#### CACHE

运行时 CACHE:

→ 不是合法持久化语义字段
→ 不是权威持久化状态
→ reset/重新评估不是持久化状态丢失

**Machine SSOT 要求不适用**: CACHE 明确不是合法持久化语义字段

**说明**: 这明确了适用域；它不修改或弱化 Machine SSOT。

### 往返验证

```python
# 往返必须保留 BASE 状态精确性
char1 = Character(...)
char1.knowledge[prop_id].aligns_with_fact = True  # CACHE

serialized = to_json(char1)

# 持久化语义 payload 不包含 aligns_with_fact
assert "aligns_with_fact" not in serialized["knowledge"][prop_id]

char2 = from_json(serialized)

# BASE 状态精确相等
assert char1.entity_id == char2.entity_id
assert char1.project_id == char2.project_id
assert char1.lifecycle == char2.lifecycle
assert char1.knowledge == char2.knowledge  # BASE: 精确 dict 相等
assert char1.goals == char2.goals
assert char1.intents == char2.intents
assert char1.planned_actions == char2.planned_actions

# DERIVED 重新计算后等价
assert char1.active_goals == char2.active_goals
assert char1.knowledge_count == char2.knowledge_count

# CACHE 不是语义往返的一部分
# aligns_with_fact 反序列化后为 None
assert char2.knowledge[prop_id].aligns_with_fact is None

# 但语义相等性仍然通过（compare=False）
assert char1 == char2  # PASS
```

---

## 失效语义

### 必须拒绝的持久化 Payload

```text
- 未知语义字段
- 跨项目引用
- 非法 lifecycle 字面值
- 非法嵌套身份
- PropositionId 碰撞（相同 ID + 不同 BASE payload）
- 缺失必需 BASE 字段
```

### CACHE 字段出现在持久化 JSON 中

**决策**: **REJECT**

**理由**: 防止意外的 CACHE 权威化

**语义**: 进入 semantic persisted payload 的 `aligns_with_fact` 字段**必须 REJECT**

任何包含 `aligns_with_fact` 的持久化语义 JSON payload 在反序列化时必须被拒绝，不得静默剥离或忽略。

**实现边界**: 在 semantic payload deserialization 边界强制执行

---

## Proposition Context 不可变性

**问题**: `dict | None` 类型本身可变

```python
@dataclass(frozen=True)
class Proposition:
    context: dict | None = None

# frozen=True 不足够
prop.context["x"] = 1  # 仍可修改内部 dict
```

**决策**:

1. **类型签名**: `context: Mapping[str, Any] | None`
2. **领域存储**: 必须是不可变/冻结表示
3. **输入规范化**: 
   - 输入可能来自 JSON object
   - 领域构造必须在存储前规范化/**递归深度冻结**
4. **推荐实现**: 递归冻结结构
   - **重要**: `MappingProxyType` 仅浅冻结，对嵌套结构不足够
   - 必须递归处理嵌套 mapping/list 以确保完全不可变
5. **不变式**: 存储的 `Proposition.context` 禁止是可变 dict

**边界**: 不为此建立重框架；最小收口即可

---

## 备选方案考虑

### Option A — 仅持久化 BASE（推荐）

```text
BASE: 持久化
DERIVED: 重新计算
CACHE: 仅运行时
```

**优点**:
- 单一权威
- 往返正确性明确
- 防止过时 CACHE 污染
- 实现简单
- AI 实现清晰

**缺点**:
- CACHE 重新评估成本（可接受，非高频操作）

**决策**: **ACCEPT（P1 推荐）**

### Option B — 持久化 BASE + CACHE

```text
BASE: 持久化
DERIVED: 重新计算
CACHE: 持久化（带版本绑定）
```

**优点**:
- 更快的评估重用

**缺点**:
- 过时真值对齐风险
- 需要 Canon 修订版本绑定
- Schema/状态复杂性增加
- 需要 CACHE 失效逻辑
- 多权威风险

**决策**: **DEFER（P1 拒绝，可能的未来扩展需明确 ADR 变更）**

### Option C — 持久化所有派生值

```text
BASE + DERIVED + CACHE: 全部持久化
```

**缺点**:
- 多权威
- 状态漂移
- Schema 重复
- 重新计算冲突
- 不满足单一权威原则

**决策**: **REJECT**

---

## 决策标准

评估选项依据:

1. **单一权威**: 每个语义真值仅有一个权威来源
2. **往返正确性**: BASE 精确保留，DERIVED 等价重算
3. **叙事正确性**: 支持反神视角、信念与现实分离
4. **项目隔离**: 无跨项目泄漏
5. **实现简单性**: AI 实现清晰，复杂度可控
6. **未来兼容性**: V2-007/V2-008 集成路径清晰
7. **长篇小说可靠性**: 多 POV、复杂角色认知状态稳定

**产品正确性优于理论灵活性**。

---

## 任务边界

### V2-061 权威

- Character 当前认知/意图/生命周期领域状态
- `aligns_with_fact` is a V2-061 runtime CACHE field and is not persisted in the semantic payload; evaluation requires external Canon context

### 外部权威

- **V2-005**: 实体身份/命名/别名/entity_type
- **V2-006**: 实体间关系拓扑
- **V2-007**: 客观事件发生与生命周期变更事件
- **V2-008**: 转换/delta 历史表示
- **Canon**: 接受的提交状态/历史

ADR-002 不吸收其他任务的权威。

---

## 后果

### 积极

- BASE/DERIVED/CACHE 边界明确
- 序列化/反序列化确定性
- 防止过时 CACHE 成为权威
- Schema 与代码类型一致
- 往返验证可测试
- 实现路径清晰

### 消极

- CACHE 重新评估成本（可接受）
- 需要外部 Canon 上下文评估 `aligns_with_fact`

### 风险

- 如未来需持久化 CACHE，需明确 ADR 变更定义版本绑定

---

## 验证要求

### 单元测试

```python
def test_cache_not_serialized():
    ck = CharacterKnowledge(..., aligns_with_fact=True)
    payload = serialize(ck)
    assert "aligns_with_fact" not in payload

def test_cache_not_in_equality():
    ck1 = CharacterKnowledge(..., aligns_with_fact=True)
    ck2 = CharacterKnowledge(..., aligns_with_fact=False)
    assert ck1 == ck2  # compare=False

def test_roundtrip_base_preservation():
    char1 = Character(...)
    serialized = to_json(char1)
    char2 = from_json(serialized)
    assert char1 == char2  # BASE 精确相等

def test_derived_recomputation():
    char = Character(goals=[...])
    serialized = to_json(char)
    char2 = from_json(serialized)
    assert char.active_goals == char2.active_goals

def test_proposition_collision_reject():
    # Same PropositionId + different BASE payload must be rejected
    prop1 = Proposition(
        proposition_id=PropositionId("prop-123"),
        project_id=ProjectId("project-1"),
        subject=EntityId("entity-A"),
        predicate="is_alive",
        object=None,
        context=None
    )
    prop2 = Proposition(
        proposition_id=PropositionId("prop-123"),
        project_id=ProjectId("project-1"),
        subject=EntityId("entity-B"),  # Different subject
        predicate="is_dead",  # Different predicate
        object=None,
        context=None
    )
    # System must reject: same PropositionId + different BASE payload

def test_proposition_context_immutable():
    context = {"key": "value"}
    prop = Proposition(
        proposition_id=PropositionId("prop-456"),
        project_id=ProjectId("project-1"),
        subject=EntityId("entity-C"),
        predicate="owns",
        object="artifact-X",
        context=context
    )
    with pytest.raises(TypeError):
        prop.context["key"] = "modified"
```

### Schema 验证

```bash
# character.schema.json 不包含 aligns_with_fact
jsonschema validate --schema character.schema.json invalid_with_cache.json
# 应失败
```

### 对抗性检查

```python
# CACHE True → 序列化 → 不在语义 JSON 中
# 反序列化相同 BASE → CACHE None → 语义相等仍 PASS
# 不同 BASE → 相等 FAIL
# 相同 PropositionId + 不同 BASE payload → 碰撞 REJECT
# 持久化 CACHE 字段 → 按 ADR 决策处理（REJECT）
# V2-007 发生真值 → 不从 PlannedAction BASE 单独推断
```

---

## 批准前提条件

1. **独立审核**: ADR-002 内容通过独立审核
2. **Contract 对齐**: 与冻结 Contract d35be3d 无语义冲突
3. **分类完整**: BASE/DERIVED/CACHE 分类明确且无歧义
4. **权威边界**: V2-005/V2-006/V2-007/V2-008 边界清晰
5. **Machine 接受映射**: BASE/DERIVED/CACHE 对 Machine SSOT 的映射明确
6. **无未解决语义冲突**: 无内部矛盾或与其他已接受决策冲突

**当前状态**: PROPOSED / DRAFT — 不具备批准权威

**注**: Schema/code/test conformance 属于 V2-061 implementation verification，不是 ADR-002 ratification 前提条件。ADR-002 在 interface implementation 前批准，implementation 验证 conformance。

---

## 批准输出 / 原子治理更新

批准后需执行的原子治理更新（尚未执行）:

1. **ADR 状态**: PROPOSED / DRAFT → ACCEPTED
2. **创建批准证据**: 生成正式决策证据文档
3. **decision_register.yaml**: `decision_record: null` → 批准证据路径
4. **验证引用**: 按当前治理要求添加适用的 verification_refs

---

## 参考

- V2-061 Implementation Contract (d35be3d)
- ADR-001 决策记录格式
- Machine SSOT 要求: 合法派生字段和非默认值往返不丢失
- V2-005 EntityIdentity 实现
- V2-006 Relationship 实现
