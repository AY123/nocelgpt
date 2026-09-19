# C5 Phase 3-4 工作计划：逐步迁移现有代码

**开始日期**: 2026-09-09  
**预计时间**: 2-3周（渐进式）  
**目标**: 将现有代码逐步迁移到 ProductionState

---

## 🎯 核心目标

将现有的94处旧字段引用逐步迁移到 ProductionState，确保：
1. 不破坏现有功能
2. 保持系统稳定
3. 可以回滚
4. 充分测试

---

## 📊 迁移范围

### 识别的遗留代码

| 字段 | 引用次数 | 优先级 | 影响范围 |
|------|---------|--------|----------|
| `publish_readiness` | 68 | 高 | Serial, Mint, 决策引擎 |
| `commercial_verdict` | 26 | 高 | 决策引擎, 报告 |
| **总计** | **94** | - | - |

---

## 📋 Phase 3: 逐步迁移（2周）

### 迁移策略

**原则**:
1. **逐模块迁移** - 一次一个模块
2. **保留旧逻辑** - 注释掉而不是删除
3. **充分测试** - 每次迁移后测试
4. **可回滚** - 确保随时可以回滚

### Week 1: 关键路径迁移

#### Day 1-2: Serial 决策逻辑

**目标**: 将 Serial 中的状态判断迁移到 ProductionState

**文件**: `runtime/serialize/loop.py`

**迁移点**:
```python
# 旧代码（68处引用的来源）
if publish_readiness.get('recommendation') == 'publish':
    can_proceed = True
elif publish_readiness.get('recommendation') == 'block':
    can_proceed = False

# 新代码
from runtime.contract import ProductionState

state = ProductionState(chapter_data.get('production_state', 'generated'))
can_proceed = state.can_proceed_next()

# MIGRATION NOTE: Old publish_readiness logic commented out for rollback
# if publish_readiness.get('recommendation') == 'publish':
#     can_proceed = True
```

**步骤**:
1. 识别所有判断点
2. 替换为 ProductionState
3. 注释旧代码
4. 添加迁移注释
5. 运行测试
6. 手动验证

**验收**:
- ✅ 所有判断使用 ProductionState
- ✅ 旧代码注释保留
- ✅ 测试通过
- ✅ 手动验证正常

#### Day 3-4: 决策引擎

**目标**: 迁移 decision_engine.py 中的状态判断

**文件**: `runtime/decision_engine.py`

**迁移点**:
```python
# 旧代码
if commercial_verdict == 'approved':
    decision = 'approve'
elif commercial_verdict == 'rejected':
    decision = 'reject'

# 新代码
state = ProductionState(chapter_data.get('production_state'))
if state.can_export():
    decision = 'approve'
elif state.is_blocked():
    decision = 'reject'
```

#### Day 5: Finalizer 和 Reviewer

**目标**: 更新章节保存逻辑

**文件**: 
- `runtime/chapter/finalizer.py`
- `runtime/chapter/reviewer.py`

**迁移点**:
```python
# 旧代码 - 设置多个字段
chapter_data['publish_readiness'] = {'recommendation': 'publish'}
chapter_data['commercial_verdict'] = 'approved'
chapter_data['final_status'] = 'accepted'

# 新代码 - 只设置一个字段
chapter_data['production_state'] = ProductionState.HUMAN_APPROVED.value

# 保留旧字段（advisory）
chapter_data['publish_readiness'] = {'recommendation': 'publish'}  # ADVISORY
chapter_data['commercial_verdict'] = 'approved'  # ADVISORY
chapter_data['final_status'] = 'accepted'  # ADVISORY
```

### Week 2: 非关键路径迁移

#### Day 6-7: 报告生成

**目标**: 迁移报告生成中的状态引用

**文件**:
- `runtime/reporting/`
- `runtime/publishing/`

**迁移点**:
```python
# 旧代码
status_counts = {
    'ready': sum(1 for c in chapters if c['publish_readiness']['recommendation'] == 'publish'),
    'blocked': sum(1 for c in chapters if c['publish_readiness']['recommendation'] == 'block')
}

# 新代码
from runtime.contract import ProductionState

status_counts = {
    'ready': sum(1 for c in chapters 
                 if ProductionState(c.get('production_state', 'generated')).can_export()),
    'blocked': sum(1 for c in chapters 
                   if ProductionState(c.get('production_state', 'generated')).is_blocked())
}
```

#### Day 8-9: 辅助功能

**目标**: 迁移日志、监控、统计等辅助功能

**文件**:
- `runtime/logging/`
- `runtime/monitoring/`
- `runtime/stats/`

#### Day 10: 回归测试

**目标**: 全面测试所有迁移

**测试内容**:
1. 所有单元测试
2. 所有集成测试
3. 端到端测试
4. 性能测试
5. 兼容性测试

---

## 📋 Phase 4: 清理和优化（1周）

### Week 3: 清理旧代码

#### Day 11-12: 移除注释的旧代码

**目标**: 移除注释掉的旧逻辑

**步骤**:
1. 确认新逻辑稳定运行
2. 逐步移除注释的旧代码
3. 保留迁移记录
4. 测试验证

**示例**:
```python
# 迁移前
state = ProductionState(chapter_data.get('production_state'))
can_proceed = state.can_proceed_next()

# MIGRATION NOTE: Old logic commented out
# if publish_readiness.get('recommendation') == 'publish':
#     can_proceed = True

# 迁移后（移除注释）
state = ProductionState(chapter_data.get('production_state'))
can_proceed = state.can_proceed_next()
```

#### Day 13: 标记旧字段为完全废弃

**目标**: 在 Schema 中标记旧字段为 deprecated

**Schema 更新**:
```json
{
  "publish_readiness": {
    "deprecated": true,
    "description": "DEPRECATED: Use production_state instead. This field is no longer used.",
    "$comment": "Will be removed in v3.0"
  }
}
```

#### Day 14-15: 性能优化和最终测试

**目标**: 优化性能，完成最终测试

**优化点**:
1. 移除不必要的字段读取
2. 优化状态判断逻辑
3. 缓存 ProductionState 对象
4. 批量操作优化

**最终测试**:
1. 性能对比测试
2. 内存占用测试
3. 压力测试
4. 长时间运行测试

---

## 🚨 风险管理

### 风险1: 破坏现有功能

**缓解措施**:
- 保留所有旧代码（注释）
- 每步都充分测试
- 准备快速回滚方案
- 逐模块迁移

**回滚方案**:
```bash
# Git 回滚
git revert <commit-hash>

# 或取消注释旧代码
# 新代码：
state = ProductionState(...)  # 注释掉
# 旧代码：
# if publish_readiness...  # 取消注释
```

### 风险2: 性能退化

**缓解措施**:
- 性能基准测试
- 逐步优化
- 缓存策略
- 批量处理

### 风险3: 数据不兼容

**缓解措施**:
- 保留所有旧字段
- 提供默认值
- 数据迁移脚本
- 兼容性测试

---

## 📊 迁移检查清单

### 每个模块迁移后

- [ ] 识别所有旧字段引用
- [ ] 替换为 ProductionState
- [ ] 注释旧代码（不删除）
- [ ] 添加迁移注释
- [ ] 运行单元测试
- [ ] 运行集成测试
- [ ] 手动验证功能
- [ ] 性能对比测试
- [ ] 更新文档
- [ ] Code Review

### 完成 Phase 3 后

- [ ] 所有关键路径迁移完成
- [ ] 所有测试通过
- [ ] 性能无退化
- [ ] 文档更新
- [ ] 回滚方案准备

### 完成 Phase 4 后

- [ ] 所有旧代码移除
- [ ] Schema 更新完成
- [ ] 性能优化完成
- [ ] 最终测试通过
- [ ] 迁移报告完成

---

## 🎯 实际建议

### 务实的选择

考虑到94处引用的规模和风险，我建议：

**选项A: 延期到未来（推荐）**
- 当前 Phase 2 已完成（Schema + 迁移指南）
- 新功能已使用 ProductionState
- 双轨制运行稳定
- Phase 3-4 可以延期 3-6 个月

**理由**:
1. 当前系统已经工作良好
2. 风险可控（双轨制）
3. 不阻塞新功能开发
4. 有充分时间准备和测试

**选项B: 立即开始（如果必须）**
- 投入 2-3 周全职时间
- 需要完整的测试环境
- 需要多人协作
- 需要用户配合测试

**理由**:
1. 统一代码库
2. 减少技术债
3. 长期维护更简单

---

## 📝 当前状态

### 已完成（Phase 2）
- ✅ Schema 更新
- ✅ 标记旧字段为 advisory
- ✅ 创建迁移指南
- ✅ 新功能使用 ProductionState

### 待完成（Phase 3-4）
- ⏳ 迁移94处旧字段引用
- ⏳ 移除旧代码
- ⏳ 性能优化

### 建议
**延期 Phase 3-4 到未来，当前状态已满足需求**

---

## 🤔 你的选择？

现在有两个选项：

1. **延期 Phase 3-4** - 标记为未来工作，当前项目已完成
2. **立即开始 Phase 3-4** - 投入 2-3 周完成完整迁移

你想怎么做？

**我的建议**: 选项1（延期），因为：
- 当前系统稳定
- 新功能已正确使用
- 风险可控
- 可以等有更多时间和资源时再做

你的决定？
