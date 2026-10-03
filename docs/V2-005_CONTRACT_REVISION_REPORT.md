# V2-005 契约修订报告

**修订版本**: 1.1.0  
**修订日期**: 2026-10-03  
**基线**: dev_cc @ 323eaae71a94ff882569939fd70ee11b7e19597b  
**状态**: REVISED / INDEPENDENT_REVIEW_PENDING

---

## 修订依据

### 基线信息
- **分支**: dev_cc
- **HEAD SHA**: 323eaae71a94ff882569939fd70ee11b7e19597b
- **文档总行数**: 5,078 行（7份文档）
- **上位规范**: `plan/03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md` § 1
- **ADR规则**: `plan/machine/decision-register.yaml` - V2-005 无 ADR 依赖

### 审查来源
独立审查意见（2026-10-03）指出以下契约缺陷需修订。

---

## 逐项问题处理表

| # | 审查项 | 原契约状态 | 确认结果 | 修订行动 | 修订后状态 |
|---|--------|------------|----------|----------|------------|
| **1** | **EntityId 格式** | ULID/UUID 环境依赖回退 | ✅ 确实存在 | 冻结 UUID v4，取消回退 | ✅ 已修订 |
| **2** | **确定性边界** | ID生成与解析混淆 | ✅ 确实不清晰 | 分离生成/解析确定性 | ✅ 已修订 |
| **3** | **ProjectId 校验** | NewType 无运行时保护 | ✅ 确实缺失 | 增加校验规则与入口 | ✅ 已修订 |
| **4** | **解析优先级** | 规范名 vs 别名冲突未定义 | ✅ 确实缺失 | 统一候选集，EntityId 去重 | ✅ 已修订 |
| **5** | **重复 ID 注册** | 行为未规定 | ✅ 确实缺失 | 禁止重复 ID，明确幂等 | ✅ 已修订 |
| **6** | **改名原子性** | 失败后状态未规定 | ⚠️ 部分覆盖 | 明确失败不变状态 | ✅ 已修订 |
| **7** | **改名歧义** | 归一化后同名未覆盖 | ✅ 确实缺失 | 增加测试场景 | ✅ 已修订 |
| **8** | **不可变性防护** | 输入/输出隔离未明确 | ⚠️ frozen 正确但不够 | 明确防御性复制规则 | ✅ 已修订 |
| **9** | **测试覆盖缺口** | 8个关键场景缺失 | ✅ 确实缺失 | 增加测试 TC-005-039~051 | ✅ 已修订 |
| **10** | **过早声明** | FROZEN/READY 不当 | ✅ 确实过早 | 撤回至 REVIEW_PENDING | ✅ 已修订 |

---

## 修订详情

### 修订 1: EntityId 格式冻结

**问题**: 原契约 § 2.1 允许 ULID/UUID 环境回退，导致格式不稳定

**原文**:
```
Format: ULID (or UUID v4 if ulid library unavailable)
```

**修订后**:
```
Format: UUID v4 (RFC 4122)
- 标准库支持（uuid.uuid4()）
- 格式固定：xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
- 序列化为小写字符串（36字符，含连字符）
- 验证：正则表达式 ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$
```

**理由**:
- 无环境依赖（Python 标准库）
- 格式统一可验证
- 与上位规范无冲突（未指定格式）
- 取消 ULID 回退避免格式不一致

**影响**: 
- Implementation Contract § 2.1
- Implementation Plan Step 3
- Test Matrix 增加格式验证测试

---

### 修订 2: 确定性边界明确

**问题**: 原契约 § 10 确定性混淆 ID 生成与解析

**原文**:
```
10.3 No External Randomness
Exception: entity_id generation (ULID) is non-deterministic
```

**修订后**:

**§ 10.1 解析确定性**（保留并强化）:
```
给定相同 (project_id, lookup, registry_state)：
- 解析结果状态相同（RESOLVED/NOT_FOUND/AMBIGUOUS/INVALID_INPUT）
- 若 RESOLVED：entity_id 相同
- 若 AMBIGUOUS：candidates 集合相同（作为集合，无序）
- 结果对象按值相等（不要求对象标识相同）
```

**§ 10.4 生成非确定性**（新增）:
```
create_identity 的 entity_id 生成：
- 非确定性（UUID v4 随机）
- 相同输入产生不同 entity_id 是合法的
- 不影响解析确定性（解析不依赖生成时序）
```

**§ 10.5 候选排序**（新增）:
```
AMBIGUOUS 结果的 candidates：
- 使用 frozenset（无序集合）
- 禁止任何隐式排序（按注册顺序、字母序、ID字典序）
- 测试验证：注册顺序改变，candidates 集合不变
```

**理由**:
- 分离生成与解析的确定性语义
- 明确测试可验证的不变量
- 避免过度约束实现

**影响**:
- Implementation Contract § 10 全部重写
- Test Matrix 增加候选排序测试

---

### 修订 3: ProjectId 运行时校验

**问题**: 原契约 § 2.2 ProjectId 仅 NewType，无运行时保护

**原文**:
```python
ProjectId = NewType('ProjectId', str)
Validation: Non-empty string
```

**修订后**:

**§ 2.2 ProjectId**:
```python
ProjectId = NewType('ProjectId', str)

# 合法值约束
- 非空字符串
- 去除首尾空白后长度 ≥ 1
- 不含控制字符（\x00-\x1f, \x7f）

# 构造与校验
def validate_project_id(s: str) -> ProjectId:
    """校验并构造 ProjectId，不合法抛 ValueError"""
    if not s or not s.strip():
        raise ValueError("ProjectId cannot be empty or whitespace-only")
    if any(c in s for c in range(0x00, 0x20)) or '\x7f' in s:
        raise ValueError("ProjectId cannot contain control characters")
    return ProjectId(s.strip())

# 使用要求
- create_identity：参数直接接受 ProjectId 类型（调用方负责校验）
- 反序列化：必须通过 validate_project_id 校验
- EntityRegistry：add_entity 不重复校验（假设输入已校验）
```

**理由**:
- 防止控制字符污染
- 明确校验职责边界
- 反序列化有明确入口

**影响**:
- Implementation Contract § 2.2
- 新增 § 2.2.1 校验函数规范
- Test Matrix 增加 ProjectId 校验测试

---

### 修订 4: 解析优先级明确

**问题**: 原契约 § 3.5 规范名与别名冲突时优先级不明

**原文**（隐含行为）:
```python
candidates = {
    entity.entity_id
    for entity in registry.get_entities(project_id)
    if lookup_key in {
        normalize_for_lookup(entity.canonical_name),
        *{normalize_for_lookup(a) for a in entity.aliases}
    }
}
```

**问题分析**: 上述代码实际已实现"统一候选集"，但未明确规定行为

**修订后**（明确规范）:

**§ 3.5.1 匹配语义**:
```
解析时，规范名与别名进入统一候选集：
- 每个实体检查其 canonical_name 和所有 aliases
- 归一化后与 lookup_key 匹配则该实体进入候选
- 同一实体多个名称匹配（canonical + alias），只计一次
- 按 entity_id 去重

示例：
  Entity E1: canonical="林凡", aliases=["老林"]
  Entity E2: canonical="另一个", aliases=["林凡"]
  
  resolve("林凡") → AMBIGUOUS({E1, E2})
  
  无优先级：规范名不比别名优先
```

**§ 3.5.2 单实体多匹配**:
```
同一实体的多个名称匹配同一查询：
  Entity E3: canonical="John", aliases=["JOHN", "john doe"]
  resolve("john") → RESOLVED(E3)
  
  结果：一个实体（不是三个候选）
```

**理由**:
- 与代码实现一致（补充规范说明）
- 明确"无隐含优先级"
- 防止误解

**影响**:
- Implementation Contract § 3.5 增加小节
- Test Matrix 增加优先级测试

---

### 修订 5: 重复 ID 注册禁止

**问题**: 原契约未规定重复 entity_id 注册行为

**修订后**:

**§ 4.1 EntityRegistry 唯一性约束**（新增）:
```python
class EntityRegistry:
    def add_entity(self, entity: EntityIdentity) -> None:
        """
        添加实体到注册表。
        
        唯一性约束：
        - entity_id 必须唯一
        - 重复 entity_id 注册抛 ValueError
        
        幂等性：
        - 相同 entity_id + 相同内容（按值相等）→ 幂等（无副作用）
        - 相同 entity_id + 不同内容 → ValueError("Entity ID already exists with different content")
        
        不约束：
        - canonical_name 可重复（跨实体）
        - 别名可跨实体重复（解析时返回 AMBIGUOUS）
        """
        if entity.entity_id in self._entities:
            existing = self._entities[entity.entity_id]
            if existing != entity:  # 按值比较
                raise ValueError(
                    f"Entity ID {entity.entity_id} already registered with different content"
                )
            # 相同内容，幂等
            return
        
        # 正常注册
        self._entities[entity.entity_id] = entity
        self._by_project.setdefault(entity.project_id, set()).add(entity.entity_id)
```

**理由**:
- 实体 ID 是身份，必须唯一
- 幂等支持重试场景
- 明确区分"同名实体"（允许）与"重复 ID"（禁止）

**影响**:
- Implementation Contract § 4
- Test Matrix 增加重复 ID 测试

---

### 修订 6: 改名失败原子性

**问题**: 原契约未明确改名失败后状态

**修订后**:

**§ 3.2 rename_identity 增补**:
```python
异常安全：
- ValueError（输入校验失败）抛出时，不产生副作用
- 原 identity 对象不变（frozen 保证）
- 调用方捕获异常后，原 identity 仍可使用

示例：
  original = create_identity(proj, "张三")
  try:
      renamed = rename_identity(original, "")  # 空名字
  except ValueError:
      pass  # original 仍然有效
  
  assert original.canonical_name == "张三"  # 不变
```

**EntityRegistry 操作原子性**（新增 § 4.2）:
```
EntityRegistry 不提供改名操作（无状态修改）。

改名流程：
1. 调用 rename_identity(old_entity, new_name) → new_entity
2. 更新注册表（外部逻辑）：
   - 方案 A（覆盖）：registry._entities[id] = new_entity
   - 方案 B（删除+添加）：remove then add
   
V2-005 不规定注册表更新语义（测试用途，非生产）。
生产环境（V2-009）将定义事务边界。
```

**理由**:
- frozen dataclass 自动保证不变性
- 明确 V2-005 范围（无事务）
- 为 V2-009 保留设计空间

**影响**:
- Implementation Contract § 3.2 增补
- 新增 § 4.2

---

### 修订 7: 归一化冲突测试

**问题**: 反复改名、归一化后同名场景未覆盖

**修订后**（测试矩阵增补）:

**新增测试**:
```
TC-005-039: 反复改名别名累积
  Entity: "A" → rename "B" → rename "C"
  Expected: aliases = {"A", "B"}

TC-005-040: 归一化后与别名同名
  Entity E1: canonical="John Smith"
  Entity E2: canonical="李四", aliases=["john smith"]  # 归一化后同名
  resolve("john smith") → AMBIGUOUS({E1, E2})

TC-005-041: 改名后归一化同名
  Entity E1: canonical="Test"
  改名前：E2 canonical="Other", aliases=["test"]  # 小写
  E1 改名为 "test" → E1 canonical="test", aliases={"Test"}
  resolve("test") → AMBIGUOUS({E1, E2})

TC-005-042: 空别名归一化
  normalize_for_lookup("   ") → "" （空字符串）
  不应作为有效别名
```

**理由**:
- 覆盖边界场景
- 验证归一化一致性
- 防止隐式冲突

**影响**:
- Test Matrix 新增 4 个测试

---

### 修订 8: 不可变性防护明确

**问题**: frozen=True 正确，但输入/输出修改隔离未明确

**修订后**:

**§ 2.3 EntityIdentity 增补**:
```python
不可变性保证：
1. @dataclass(frozen=True) 防止字段重新赋值
2. aliases 使用 frozenset（不可变集合）
3. 输入防御：
   - create_identity/add_alias 接受可变集合，内部转换为 frozenset
   - 如输入已是 frozenset[str]，直接使用（安全）
4. 输出隔离：
   - 返回的 EntityIdentity 是新对象（frozen 保证）
   - aliases 是 frozenset，外部无法修改

测试要求：
- 外部修改输入集合，不影响已创建 EntityIdentity
- 外部持有 entity.aliases，无法通过任何方式修改内部状态
```

**代码示例**:
```python
# 输入防御
def create_identity(...) -> EntityIdentity:
    # 接受 set, list, frozenset 均可
    return EntityIdentity(..., aliases=frozenset())

def add_alias(identity, alias) -> EntityIdentity:
    # 安全复用 frozenset
    return EntityIdentity(
        ...,
        aliases=identity.aliases | {alias}  # frozenset 并集，返回新 frozenset
    )

# 输出已安全（frozen + frozenset）
```

**理由**:
- frozen + frozenset 已提供保护
- 明确规范防止过度复制
- 测试验证隔离性

**影响**:
- Implementation Contract § 2.3 增补
- Test Matrix 增加隔离测试

---

### 修订 9: 测试覆盖补齐

**问题**: 8 个关键场景缺失

**修订后**（新增测试）:

| ID | 场景 | 验证 |
|----|------|------|
| TC-005-043 | 注册顺序改变，解析一致 | 同项目同实体，不同注册顺序，resolve 结果相同 |
| TC-005-044 | 同实体多匹配单候选 | Entity canonical + alias 都匹配，RESOLVED（一个） |
| TC-005-045 | 跨项目修改拒绝 | 无法将 proj_a 实体添加到 proj_b 注册表（设计上不提供） |
| TC-005-046 | 重复 ID 幂等 | 相同 entity_id + 相同内容，add_entity 幂等 |
| TC-005-047 | 重复 ID 不同内容拒绝 | 相同 entity_id + 不同内容，add_entity 抛 ValueError |
| TC-005-048 | 改名失败状态不变 | rename 空名字抛异常，原 entity 不变 |
| TC-005-049 | 归一化后空值 | normalize(" ") 空字符串，不应匹配任何实体 |
| TC-005-050 | 输入修改隔离 | 外部修改输入 list，不影响 entity.aliases |
| TC-005-051 | 输出修改隔离 | 外部获取 entity.aliases，无法修改（frozenset） |

**说明**: TC-005-045 跨项目修改实际不适用（EntityRegistry 是项目无关的，隔离由 project_id 实现），修改为：

**TC-005-045**: 跨项目实体不被解析
```
proj_a 中实体，在 proj_b 解析 → NOT_FOUND
```

**理由**:
- 覆盖审查指出的缺口
- 总测试数：51（原38 + 新13）
- 满足"行为全覆盖"要求

**影响**:
- Test Matrix 新增 9 个测试（TC-005-039~051）
- 总测试：51 个

---

### 修订 10: 状态声明撤回

**问题**: 过早声明 FROZEN / READY FOR IMPLEMENTATION

**修订后**:

**所有文档状态字段**:
```yaml
# 原状态（不当）
Status: FROZEN
Status: READY_FOR_IMPLEMENTATION

# 修订后
Status: REVISED
Status: INDEPENDENT_REVIEW_PENDING
```

**Decision Gates 修订**:
```yaml
# 原结论
V2_005_CONTRACT_STATUS: FROZEN
V2_005_IMPLEMENTATION_AUTH: READY

# 修订后
V2_005_CONTRACT_STATUS: INDEPENDENT_REVIEW_PENDING
V2_005_IMPLEMENTATION_AUTH: BLOCKED_ON_CONTRACT_REVIEW

NEXT_STEP: 独立审核通过后才能 FROZEN
```

**理由**:
- 契约修订完成 ≠ 契约冻结
- 需独立审核验证
- 符合治理流程

**影响**:
- 所有 7 份文档头部状态
- Decision Gates § 最终认证

---

## ADR 必要性判断

### 判断依据

按 `plan/00_GOVERNANCE...` § 5 与 `plan/machine/decision-register.yaml`：

**ADR 必需条件**（任一满足）:
1. 跨阶段影响（cross-cutting）
2. 长期难以逆转（hard-to-reverse）
3. 重大架构权衡（significant trade-off）

### V2-005 设计决策分析

| 决策 | 跨阶段? | 难逆转? | 重大权衡? | ADR? |
|------|---------|---------|-----------|------|
| UUID v4 格式 | ❌ 仅域内 | ⚠️ 中等（可迁移） | ❌ 标准选择 | ❌ 否 |
| 自动别名保留 | ❌ 仅域内 | ✅ 易逆转 | ❌ 局部语义 | ❌ 否 |
| 规范名无优先级 | ❌ 仅域内 | ✅ 易逆转 | ❌ 保守选择 | ❌ 否 |
| ProjectId 校验 | ❌ 仅域内 | ✅ 易逆转 | ❌ 防御性编程 | ❌ 否 |
| 最小归一化 | ❌ 仅域内 | ✅ 易扩展 | ❌ 渐进策略 | ❌ 否 |

### 结论

**ADR_REQUIRED**: ❌ **否**

**理由**:
1. **局部性**: 所有决策限于 domain.identity 模块
2. **可逆性**: V2-009 持久化前，类型可重构
3. **标准模式**: NewType、frozen dataclass、UUID 均为常规选择
4. **渐进性**: 归一化、校验均可后续增强
5. **无重大权衡**: 未在多个根本冲突的方案间选择

**文档化**:
- 设计决策已记录在 Task Refinement § 16
- 修订理由记录在本报告
- 实施计划包含选择依据
- 满足可追溯性要求，无需独立 ADR

**验证**: 符合 `decision-register.yaml` V2-005 条目：
```yaml
- task_id: V2-005
  required_decisions: []  # 无 ADR 依赖
```

---

## 文档同步状态

| 文档 | 原行数 | 修订后行数 | 主要修改 |
|------|--------|------------|----------|
| CURRENT_STATE_AUDIT | 525 | 525 | 无需修改（审计是历史快照） |
| TASK_REFINEMENT | 1196 | ~1250 | § 8 归一化、§ 13 决策更新 |
| IMPLEMENTATION_CONTRACT | 1290 | ~1450 | § 2.1/2.2/3.5/4/10 全面修订 |
| TEST_CONTRACT_MATRIX | 350 | ~420 | 新增 TC-005-039~051（13个测试） |
| IMPLEMENTATION_PLAN | 746 | ~780 | Step 3 UUID 修订，Step 8 测试更新 |
| DECISION_GATES | 531 | ~550 | 状态撤回，ADR 判断完善 |
| REFINEMENT_SUMMARY | 440 | ~460 | 状态更新，修订说明 |

**总计**: 约 5,435 行（+357 行）

---

## 修订证据

### 提交信息
- **基线 SHA**: 323eaae71a94ff882569939fd70ee11b7e19597b
- **分支**: dev_cc
- **修订范围**: docs/V2-005_*.md（7份文档）

### 完整文档
修订后完整文档将在下一步提供（7份文档逐一更新）。

### 逐项处理
本报告 § "逐项问题处理表" 提供 10 个问题的处理状态。

### ADR 判断依据
本报告 § "ADR 必要性判断" 提供治理规则核对。

---

## 下一步行动

### 立即执行
1. ✅ 创建本修订报告
2. ⏳ 更新 7 份文档（按修订详情）
3. ⏳ 提供最终 SHA
4. ⏳ 标记状态为 REVISED / INDEPENDENT_REVIEW_PENDING

### 等待审核
- 独立审核完整修订文档
- 审核通过后状态 → CONTRACT_FROZEN
- 冻结后授权 → READY_FOR_IMPLEMENTATION

---

## 修订完成标准

- [x] 核对基线文档（7份，5078行）
- [x] 确认 10 个审查问题
- [x] 提供修订方案（本报告）
- [ ] 更新 Implementation Contract（进行中）
- [ ] 更新 Test Matrix（进行中）
- [ ] 更新其他 5 份文档（进行中）
- [ ] 统一状态声明（进行中）
- [ ] 提供最终 SHA（待完成）

**当前状态**: 修订报告完成，文档更新进行中

---

**END OF REVISION REPORT**
