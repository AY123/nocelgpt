# V2-005 Contract Clarification Required

**Date**: 2026-10-03  
**Status**: SUPPLEMENTARY_REVISION_NEEDED  
**Baseline**: dev_cc @ 58d77d26

---

## Issues Requiring Clarification

基于实际运行测试与全文一致性核验需求，以下5项需要补充修订。

---

## 1. ProjectId 校验行为不明确

### 问题
当前实现：
```python
def validate_project_id(s: str) -> ProjectId:
    if not s or not s.strip():
        raise ValueError("...")
    stripped = s.strip()
    if any(ord(c) < 0x20 or c == '\x7f' for c in stripped):
        raise ValueError("...")
    return ProjectId(stripped)
```

**实际运行结果**:
| 输入 | 结果 | 问题 |
|------|------|------|
| `"project-a"` | `"project-a"` | ✓ |
| `"\tproject-a\n"` | `"project-a"` | 首尾制表符/换行被接受 |
| `"project\na"` | `ValueError` | 内部换行被拒绝 |
| `123` | `AttributeError` | 非字符串泄漏异常 |

**不明确之处**:
- 语义选择未定：先 strip 再检查 vs 先检查再 strip？
- 首尾控制字符是"被清理"还是"被禁止"？
- 非字符串输入应统一 ValueError 还是允许 AttributeError？

### 需要的契约条款

**选项 A**（建议）: 输入清理语义
```python
# 契约：首尾空白允许并清理，内部控制字符禁止
def validate_project_id(s: str) -> ProjectId:
    if not isinstance(s, str):
        raise ValueError("ProjectId must be string")
    stripped = s.strip()
    if not stripped:
        raise ValueError("ProjectId cannot be empty after stripping")
    if any(ord(c) < 0x20 or c == '\x7f' for c in stripped):
        raise ValueError("ProjectId cannot contain control characters")
    return ProjectId(stripped)

# 明确："\tproject-a\n" → "project-a" (合法)
# 明确："project\na" → ValueError (内部换行禁止)
```

**选项 B**: 严格输入语义
```python
# 契约：任何控制字符（包括首尾）禁止
def validate_project_id(s: str) -> ProjectId:
    if not isinstance(s, str):
        raise ValueError("ProjectId must be string")
    if any(ord(c) < 0x20 or c == '\x7f' for c in s):
        raise ValueError("ProjectId cannot contain control characters")
    stripped = s.strip()
    if not stripped:
        raise ValueError("ProjectId cannot be empty")
    return ProjectId(stripped)

# 明确："\tproject-a\n" → ValueError (首尾制表符禁止)
```

**需要明确**: 选择 A 或 B，写入 Implementation Contract § 2.2

### 需要的测试映射

| 测试 | 输入 | 预期 | 覆盖条款 |
|------|------|------|----------|
| TC-005-052 | `"\tproj\n"` | 清理或拒绝（按选项） | 首尾控制字符 |
| TC-005-053 | `"proj\na"` | ValueError | 内部控制字符 |
| TC-005-054 | `123` | ValueError | 非字符串输入 |
| TC-005-055 | `""` | ValueError | 空字符串 |
| TC-005-056 | `"   "` | ValueError | 纯空白 |

### 强制调用点

需要明确以下入口**必须**调用 `validate_project_id()`:
- ✅ 反序列化 (JSON → ProjectId)
- ❓ `create_identity()` - 是否在参数接收处调用？
- ❓ `EntityRegistry.add_entity()` - 是否验证？
- ❓ `resolve_alias()` - 是否验证？

**当前契约**说"create_identity 参数直接接受 ProjectId（调用方负责校验）"，但未禁止 `ProjectId("")` 直接构造绕过。

**建议**: 明确 ProjectId 构造路径：
1. 生产路径：必须通过 `validate_project_id()`
2. 测试路径：允许 `ProjectId("test")` 直接构造（信任测试代码）
3. 反序列化：强制 `validate_project_id()`

---

## 2. EntityId 验证与规范化未完整

### 问题

当前契约 § 2.1 定义生成：
```python
def _generate_entity_id() -> EntityId:
    return EntityId(str(uuid.uuid4()))
```

**未明确**:
- 反序列化时是否验证 UUID v4 格式？
- 非 v4 UUID (如 v1, v3, v5) 是否拒绝？
- 大写 UUID 是否接受并规范化？
- 无连字符形式是否接受？
- 规范化发生在唯一性比较前还是后？

**实际风险**:
```python
EntityId("550E8400-E29B-41D4-A716-446655440000")  # 大写
EntityId("550e8400e29b41d4a716446655440000")      # 无连字符
EntityId("...v1 UUID...")                        # 非 v4
```

这些是否合法？是否等价？

### 需要的契约条款

**§ 2.1.1 EntityId 验证** (新增):
```python
import re
import uuid

ENTITY_ID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)

def validate_entity_id(s: str) -> EntityId:
    """
    验证并规范化 EntityId（用于反序列化）。
    
    接受:
    - 标准小写 UUID v4 (带连字符)
    - 大写形式（规范化为小写）
    
    拒绝:
    - 非 UUID 格式
    - 非 v4 版本
    - 无连字符形式
    - 空字符串
    """
    if not isinstance(s, str):
        raise ValueError("EntityId must be string")
    
    # 规范化为小写
    normalized = s.lower()
    
    # 验证 UUID v4 格式
    if not ENTITY_ID_PATTERN.match(normalized):
        raise ValueError(
            f"EntityId must be valid UUID v4 format: {s}"
        )
    
    return EntityId(normalized)

# 使用：反序列化必须通过此函数
# 生成：通过 _generate_entity_id()（已保证格式）
# 测试：允许 EntityId("...") 直接构造
```

**唯一性比较** (§ 4.1 补充):
```python
# EntityRegistry 比较前不规范化（假设输入已规范）
# 若需要防御：可在 add_entity 入口规范化
```

### 需要的测试映射

| 测试 | 输入 | 预期 | 覆盖条款 |
|------|------|------|----------|
| TC-005-057 | 大写 UUID v4 | 规范化为小写 | 大小写规范化 |
| TC-005-058 | UUID v1 | ValueError | 版本检查 |
| TC-005-059 | 无连字符 UUID | ValueError | 格式检查 |
| TC-005-060 | 非 UUID 字符串 | ValueError | 格式检查 |
| TC-005-061 | 空字符串 | ValueError | 非空检查 |

---

## 3. JSON 序列化顺序未定义

### 问题

`AmbiguousResult.candidates` 使用 `frozenset` (正确的领域选择)。

**未明确**:
- JSON 序列化时 candidates 数组顺序？
- 相同候选集的两次序列化是否字节一致？
- 测试验证"集合相等"还是"JSON 相等"？

**示例**:
```python
result = AmbiguousResult(
    status=ResolutionStatus.AMBIGUOUS,
    candidates=frozenset([id1, id2, id3])
)

json1 = serialize(result)  # {"candidates": [id1, id2, id3]}
json2 = serialize(result)  # {"candidates": [id3, id1, id2]} ?
```

字节一致吗？

### 需要的契约条款

**§ 9.1.1 AMBIGUOUS 序列化顺序** (补充):

**选项 A** (建议): 稳定排序
```python
# 序列化时按 EntityId 字典序排序
{
  "status": "ambiguous",
  "candidates": sorted(list(candidates))  # 字典序
}

# 保证：相同候选 → 字节一致的 JSON
```

**选项 B**: 无序保证
```python
# 序列化时顺序未定义
{
  "status": "ambiguous",
  "candidates": list(candidates)  # 任意顺序
}

# 反序列化：转换为 frozenset
# 相等性：按集合比较，不按数组顺序
```

**建议**: 选择 A（稳定排序），理由：
- 便于人工检查
- 便于快照测试
- 便于日志对比
- 不影响领域语义（反序列化仍转 frozenset）

### 需要的测试映射

| 测试 | 验证 | 覆盖条款 |
|------|------|----------|
| TC-005-062 | 相同候选集两次序列化 → JSON 字节一致 | 序列化稳定性 |
| TC-005-063 | 反序列化 JSON → frozenset (顺序无关) | 反序列化正确性 |

---

## 4. 项目归属检查不完整

### 问题

当前契约强调"项目隔离"，但操作层面未完整覆盖。

**已明确**:
- ✅ `resolve_alias(project_id, ...)` - 查询隔离
- ✅ `create_identity(project_id, ...)` - 创建时绑定

**未明确**:
- `EntityRegistry.add_entity()` - 是否验证 entity.project_id 合法？
- `rename_identity()` - 无法改变 project_id (frozen 保证，但未测试)
- 唯一性作用域 - entity_id 全局唯一 or 项目内唯一？

**关键问题**: EntityRegistry 是"单项目实例"还是"多项目共享"？

### 需要的契约条款

**§ 4 EntityRegistry 作用域** (补充):

**选项 A**: 多项目共享注册表
```python
# 一个 EntityRegistry 存储多个项目的实体
# entity_id 全局唯一（跨项目）
# project_id 用于查询隔离

registry = EntityRegistry()  # 全局单例
registry.add_entity(entity_in_proj_a)
registry.add_entity(entity_in_proj_b)

# 唯一性：entity_id 跨项目唯一
# 隔离：通过 get_entities(project_id) 实现
```

**选项 B**: 单项目注册表
```python
# 每个项目独立 EntityRegistry
# entity_id 项目内唯一（不同项目可重复）

registry_a = EntityRegistry(project_id="proj_a")
registry_b = EntityRegistry(project_id="proj_b")

# 唯一性：entity_id 项目内唯一
# 隔离：通过独立实例实现
```

**当前契约倾向**: 选项 A（多项目共享）  
**理由**: `get_entities(project_id)` 接受参数，而非构造时绑定

**需要明确**:
1. EntityRegistry 作用域（A or B）
2. 唯一性作用域（全局 or 项目内）
3. add_entity 是否验证 project_id 非空

### 需要的测试映射

| 测试 | 验证 | 覆盖条款 |
|------|------|----------|
| TC-005-064 | 不同项目相同 entity_id → 唯一性冲突 or 允许？ | 唯一性作用域 |
| TC-005-065 | rename 不改变 project_id | 项目归属不可变 |
| TC-005-066 | add_entity 验证 project_id 非空 | 输入校验 |

---

## 5. ADR 判断理由需修正

### 问题

当前理由：
> "跨阶段影响：无，局限于 domain.identity"

**矛盾**:
- 文档明确列出下游依赖：V2-006, V2-007, V2-008, V2-009
- EntityId 将被所有后续 Narrative 能力使用
- 这是 P1 的**基础身份契约**，非局部模块

**正确判断**:
- EntityId 格式确实跨阶段共享
- 但不需要 ADR 的理由是：**标准技术选择 + 未进入持久化**
- `required_decisions: []` 是治理已明确授权的依据

### 需要的修正

**ADR 必要性判断** (修订):

| 标准 | V2-005 分析 | 结论 |
|------|-------------|------|
| 跨阶段影响 | ✅ 是（P1~P2 共享身份） | 触发条件 |
| 难以逆转 | ✅ 易逆转（V2-009 前） | 豁免理由 |
| 重大权衡 | ❌ 标准选择（UUID）| 豁免理由 |
| 治理授权 | ✅ `required_decisions: []` | 明确豁免 |

**结论**: 不需要 ADR

**理由**（修正后）:
1. **触发条件满足**: EntityId 确实跨阶段（P1-P2）
2. **豁免理由 1**: 技术标准选择（UUID v4），无争议方案
3. **豁免理由 2**: V2-009 持久化前易逆转，影响范围可控
4. **治理明确**: `decision-register.yaml` V2-005 条目 `required_decisions: []` 已授权无 ADR 实施
5. **文档充分**: 设计理由记录在细化文档，满足可追溯性

**不应简单声称"局限于模块"，应承认跨阶段影响但有豁免理由。**

---

## 补充修订清单

| # | 问题 | 需要行动 | 优先级 |
|---|------|----------|--------|
| 1 | ProjectId 校验语义 | 选择 A/B，补充 § 2.2，+5 测试 | 高 |
| 2 | EntityId 验证规范 | 补充 § 2.1.1，+5 测试 | 高 |
| 3 | JSON 序列化顺序 | 选择 A/B，补充 § 9.1.1，+2 测试 | 中 |
| 4 | 项目归属检查 | 明确作用域，补充 § 4，+3 测试 | 高 |
| 5 | ADR 理由修正 | 修订 Decision Gates ADR 节 | 低 |

**总计**: +15 测试（51 → 66）

---

## 全文一致性核验缺失材料

当前无法完成全文审核的原因：
- ✅ 修订摘要已提供
- ✅ 提交 SHA 已记录 (58d77d26)
- ❌ **9份完整文档未上传**（无法访问 Git 仓库）
- ❌ **治理条款引用未完整**（需核对上位规范）

**需要的材料**:
1. 完整文档（9份，~6,215 行）
   - 方式 A: 上传文本文件
   - 方式 B: 提供可访问的 Git 仓库/分支快照
   - 方式 C: 使用文档分享服务（如 GitLab snippet）

2. 引用的治理条款全文
   - `plan/00_GOVERNANCE...` § 5 (ADR 规则)
   - `plan/03_DOMAIN_CANON...` § 1 (身份要求)
   - `plan/machine/decision-register.yaml` V2-005 条目

---

## 建议下一步

**选项 1** (建议): 先补5项澄清，再全文审核
1. 根据本清单补充修订（聚焦5个问题）
2. 提交修订后提供完整文档
3. 进行正式独立审核

**选项 2**: 先提供当前完整文档，审核后批量修订
1. 上传/共享 58d77d26 的9份文档
2. 完成全文一致性核验
3. 形成完整修订清单
4. 一次性修订

---

## 当前状态

```yaml
V2_005_REFINEMENT_STATUS: REVISED
V2_005_CONTRACT_STATUS: INDEPENDENT_REVIEW_PENDING
V2_005_IMPLEMENTATION_AUTH: BLOCKED_ON_CONTRACT_REVIEW

阻塞原因:
  - 5项契约条款需要澄清
  - 完整文档未提供（无法全文核验）
  - 测试映射不完整（需 +15 测试）

解除阻塞:
  - 补充5项澄清 + 提供完整文档
  - 或：提供完整文档 + 接受批量修订清单
```

---

**END OF CLARIFICATION CHECKLIST**
