# ProductionState 迁移指南

**版本**: 1.0  
**日期**: 2026-09-09  
**目标**: 从旧的状态字段迁移到统一的 ProductionState

---

## 🎯 为什么迁移？

### 问题：分散的状态决策

**旧系统**有多个状态决策源：
- `publish_readiness.recommendation`
- `commercial_verdict`
- `final_status`
- `production_decision`
- `m7_final.decision`

**问题**:
- ❌ 决策逻辑分散
- ❌ 容易不一致
- ❌ 难以维护
- ❌ 理解成本高

### 解决：统一的 ProductionState

**新系统**使用单一真相源：
- ✅ `production_state` - 唯一的状态字段
- ✅ ProductionState enum - 明确的状态定义
- ✅ 清晰的状态转换规则
- ✅ 统一的判断方法

---

## 📋 迁移策略

### 双轨制运行

**当前阶段 (2026-09-09)**:
- **新功能**: 使用 ProductionState ✅
- **现有功能**: 保留旧字段（标记为 advisory）
- **过渡期**: 两套系统并存

**未来阶段 (3-6个月后)**:
- 逐步迁移现有代码
- 最终移除旧字段

---

## 🔄 字段映射

### 旧字段 → 新字段

| 旧字段 | 旧值 | 新字段 | 新值 | 说明 |
|--------|------|--------|------|------|
| `final_status` | `"accepted"` | `production_state` | `"human_approved"` | 人工审核通过 |
| `final_status` | `"revised"` | `production_state` | `"needs_revision"` | 需要修改 |
| `final_status` | `"review"` | `production_state` | `"generated"` | 待审核 |
| `publish_readiness.recommendation` | `"publish"` | `production_state` | `"human_approved"` | 可以发布 |
| `publish_readiness.recommendation` | `"hold"` | `production_state` | `"needs_revision"` | 暂缓发布 |
| `publish_readiness.recommendation` | `"block"` | `production_state` | `"blocked"` | 阻止发布 |
| `commercial_verdict` | `"approved"` | `production_state` | `"human_approved"` | 商业审核通过 |
| `commercial_verdict` | `"rejected"` | `production_state` | `"blocked"` | 商业审核拒绝 |

---

## 💻 代码迁移示例

### 示例1: 判断是否可以发布

**旧代码** (分散判断):
```python
# 方式1: 使用 final_status
if chapter_data.get('final_status') == 'accepted':
    can_export = True

# 方式2: 使用 publish_readiness
publish_readiness = chapter_data.get('publish_readiness', {})
if publish_readiness.get('recommendation') == 'publish':
    can_export = True

# 方式3: 使用 commercial_verdict
if chapter_data.get('commercial_verdict') == 'approved':
    can_export = True
```

**新代码** (统一判断):
```python
from runtime.contract import ProductionState

# 统一方式
state = ProductionState(chapter_data.get('production_state', 'generated'))
can_export = state.can_export()
```

### 示例2: 判断是否可以继续下一章

**旧代码**:
```python
# 复杂的判断逻辑
if (chapter_data.get('final_status') == 'accepted' or
    chapter_data.get('publish_readiness', {}).get('recommendation') == 'publish' or
    chapter_data.get('commercial_verdict') == 'approved'):
    can_proceed = True
else:
    can_proceed = False
```

**新代码**:
```python
from runtime.contract import ProductionState

state = ProductionState(chapter_data.get('production_state', 'generated'))
can_proceed = state.can_proceed_next()
```

### 示例3: 设置章节状态

**旧代码**:
```python
# 需要设置多个字段
chapter_data['final_status'] = 'accepted'
chapter_data['publish_readiness'] = {
    'recommendation': 'publish',
    'timestamp': datetime.now().isoformat()
}
chapter_data['commercial_verdict'] = 'approved'
```

**新代码**:
```python
from runtime.contract import ProductionState

# 只设置一个字段
chapter_data['production_state'] = ProductionState.HUMAN_APPROVED.value
```

### 示例4: 状态转换验证

**旧代码**:
```python
# 没有转换验证，容易出错
chapter_data['final_status'] = 'accepted'  # 可能从任何状态转换
```

**新代码**:
```python
from runtime.contract import ProductionState, validate_state_transition

current = ProductionState(chapter_data['production_state'])
new = ProductionState.HUMAN_APPROVED

# 验证转换是否合法
if validate_state_transition(current, new, raise_on_invalid=False):
    chapter_data['production_state'] = new.value
else:
    raise ValueError(f"非法状态转换: {current} → {new}")
```

---

## 📖 ProductionState API

### 状态枚举

```python
from runtime.contract import ProductionState

ProductionState.GENERATED          # 已生成，待审核
ProductionState.NEEDS_REVISION     # 需要修改
ProductionState.BLOCKED            # 被阻塞
ProductionState.HUMAN_APPROVED     # 人工审核通过
ProductionState.PUBLISHED          # 已发布
ProductionState.INVALIDATED        # 已作废
```

### 判断方法

```python
state = ProductionState.HUMAN_APPROVED

# 是否可以导出（发布）
state.can_export()  # True for HUMAN_APPROVED, PUBLISHED

# 是否可以继续下一章
state.can_proceed_next()  # True for HUMAN_APPROVED, PUBLISHED

# 是否可以修改
state.can_revise()  # True for GENERATED, NEEDS_REVISION

# 是否可以发布
state.can_publish()  # True for HUMAN_APPROVED

# 是否是终态
state.is_terminal()  # True for PUBLISHED, INVALIDATED

# 是否被阻塞
state.is_blocked()  # True for BLOCKED

# 是否需要关注
state.needs_attention()  # True for NEEDS_REVISION, BLOCKED, INVALIDATED
```

### 状态转换

```python
from runtime.contract import ProductionState, validate_state_transition

current = ProductionState.GENERATED
new = ProductionState.HUMAN_APPROVED

# 检查是否可以转换
if current.can_transition_to(new):
    print("可以转换")

# 获取所有可能的下一个状态
next_states = current.next_states()
# [NEEDS_REVISION, BLOCKED, HUMAN_APPROVED, INVALIDATED]

# 验证转换（抛出异常）
validate_state_transition(current, new, raise_on_invalid=True)
```

---

## 🔧 新代码开发指南

### 1. 创建章节时

```python
from runtime.contract import ProductionState

chapter_final = {
    'chapter_id': 'TASK-00001',
    'final_text': '...',
    'production_state': ProductionState.GENERATED.value,  # 初始状态
    # 旧字段保留但不使用
    'final_status': None,  # ADVISORY
    'production_decision': None,  # ADVISORY
}
```

### 2. 更新状态时

```python
from runtime.contract import ProductionState

# 只更新 production_state
chapter_data['production_state'] = ProductionState.HUMAN_APPROVED.value
```

### 3. 读取状态时

```python
from runtime.contract import ProductionState

# 读取并使用 ProductionState
state_str = chapter_data.get('production_state', 'generated')
state = ProductionState(state_str)

# 进行判断
if state.can_export():
    export_chapter(chapter_data)
```

### 4. 在 Serial 生成中

```python
from runtime.serialize.production_hook import create_production_hook

# 创建钩子
hook = create_production_hook(
    project_path=project_path,
    enable_contract_integration=True
)

# 生成前验证
can_proceed, errors = hook.before_generate(ctx)

# 生成后验证并设置状态
passed, state = hook.validate_and_save_chapter(...)
```

### 5. 在 Mint 发布中

```python
from runtime.publishing.contract_validator import validate_chapter_contracts_for_release

# 发布前验证
result = validate_chapter_contracts_for_release(
    project_path=project_path,
    chapter_list=[1, 2, 3, ...]
)

if result['passed']:
    # 所有章节都是 HUMAN_APPROVED 或 PUBLISHED
    release_package(...)
```

---

## ⚠️ 注意事项

### 1. 旧数据兼容性

```python
# 读取章节时，提供默认值
state_str = chapter_data.get('production_state', 'generated')
state = ProductionState(state_str)
```

### 2. 保留旧字段

```python
# 保留旧字段以保持兼容性，但不使用
chapter_data['production_state'] = 'human_approved'  # 使用
chapter_data['final_status'] = 'accepted'  # 保留，不使用
```

### 3. 不要混用

```python
# ❌ 错误：混用新旧字段
if state.can_export() and chapter_data['final_status'] == 'accepted':
    ...

# ✅ 正确：只使用新字段
if state.can_export():
    ...
```

---

## 📊 迁移检查清单

### 新功能开发
- [ ] 使用 `ProductionState` enum
- [ ] 使用 `production_state` 字段
- [ ] 使用状态判断方法（`can_export()` 等）
- [ ] 保留旧字段但不使用
- [ ] 添加测试

### 现有代码迁移
- [ ] 识别旧字段使用
- [ ] 替换为 `ProductionState`
- [ ] 更新判断逻辑
- [ ] 回归测试
- [ ] 性能测试

### Schema 更新
- [x] 添加 `production_state` 字段
- [x] 标记旧字段为 advisory
- [ ] 更新文档
- [ ] 更新示例

---

## 🆘 常见问题

### Q1: 旧数据会破坏吗？
**A**: 不会。旧字段保留，向后兼容。

### Q2: 必须立即迁移吗？
**A**: 不必。新代码使用新字段，旧代码继续工作。

### Q3: 如何判断使用哪个字段？
**A**: 新代码使用 `production_state`，旧代码保持不变。

### Q4: 状态转换规则是什么？
**A**: 见 `ProductionState.can_transition_to()` 方法。

### Q5: 如何测试？
**A**: 使用 `ProductionState` 的测试套件（21个测试）。

---

## 📚 参考资料

### 核心文件
- `runtime/contract/production_state.py` - ProductionState 定义
- `contracts/chapter/chapter-final.schema.json` - Schema 定义
- `tests/test_production_state.py` - 测试示例

### 相关文档
- C2 阶段完成报告
- ProductionState 设计文档
- 契约系统文档

---

**文档版本**: 1.0  
**最后更新**: 2026-09-09  
**作者**: AI-Novel Team
