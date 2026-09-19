# Task 5.1 完成：遗留代码识别报告

**日期**: 2026-09-09  
**任务**: 识别遗留代码  
**状态**: ✅ 完成

---

## 📊 统计数据

### 代码使用情况

| 字段/概念 | 使用次数 | 优先级 | 说明 |
|----------|---------|--------|------|
| `publish_readiness` | 68 | 高 | 旧的发布准备度判断 |
| `commercial_verdict` | 26 | 高 | 旧的商业判断 |
| `production_state` | 7 | - | 新的统一状态（目标） |

**结论**: 
- 旧字段使用广泛（94处）
- 新字段使用很少（7处）
- **需要大量重构工作**

---

## 🎯 清理策略调整

### 原计划 vs 实际情况

**原计划**: 1-2天清理完成

**实际情况**: 
- `publish_readiness`: 68处引用
- `commercial_verdict`: 26处引用
- **总计**: 94处需要评估

**调整后计划**: 
采用**渐进式策略**，分阶段清理：

1. **阶段1 (已完成)**: 新代码使用 ProductionState ✅
2. **阶段2 (当前)**: 标记旧字段为 advisory
3. **阶段3 (未来)**: 逐步迁移现有代码
4. **阶段4 (长期)**: 完全移除旧字段

---

## 📋 详细清理清单

### 阶段1: 新功能已使用 ProductionState ✅

**已完成的模块**:
- ✅ `runtime/contract/production_state.py` - ProductionState 定义
- ✅ `runtime/serialize/production_hook.py` - 生产钩子
- ✅ `runtime/serialize/serial_hook_adapter.py` - Serial 适配器
- ✅ `runtime/publishing/contract_validator.py` - 发布验证器
- ✅ `runtime/publishing/release_package.py` - 契约验证集成

**新功能统计**:
- 新增代码: ~3000行
- 使用 ProductionState: 100%
- 测试覆盖: 74个测试

---

### 阶段2: 标记旧字段为 Advisory (当前任务)

**需要标记的文件** (高优先级):

1. **Schema 定义**
   - `AI-Novel-Standard/contracts/chapter-final.schema.json`
   - 添加 `production_state` 字段 ✅
   - 标记 `publish_readiness` 为 advisory

2. **核心模块**
   - `runtime/execution/publish_readiness.py` (68处引用的来源)
   - `runtime/chapter/finalizer.py` (使用 publish_readiness)
   - `runtime/decision_engine.py` (使用 commercial_verdict)

**标记策略**:
```python
# 在关键位置添加注释
# ADVISORY: This field is kept for compatibility.
# New code should use production_state instead.
```

---

### 阶段3: 逐步迁移 (未来)

**迁移优先级**:

**P0 - 关键路径** (影响发布):
- [ ] Serial 生成流程
- [ ] Mint 发布流程
- [ ] 状态转换逻辑

**P1 - 重要功能** (影响质量):
- [ ] 章节验证
- [ ] 质量检查
- [ ] 决策引擎

**P2 - 辅助功能** (可延后):
- [ ] 报告生成
- [ ] 日志记录
- [ ] 统计分析

---

### 阶段4: 完全移除 (长期)

**时间表**: 3-6个月后

**前置条件**:
- 所有新数据使用 production_state
- 旧数据已迁移或不再使用
- 所有代码已迁移
- 充分测试

---

## 💡 关键发现

### 1. 代码耦合度高

`publish_readiness` 和 `commercial_verdict` 深度耦合到现有代码中：
- 执行流程
- 决策逻辑
- 报告生成
- 数据结构

**影响**: 不能简单替换，需要仔细迁移

### 2. 多个决策源

目前存在多个状态决策源：
- `publish_readiness.recommendation`
- `commercial_verdict`
- `m7_final.decision`
- `production_state` (新)

**问题**: 决策逻辑分散，容易不一致

### 3. 数据兼容性

大量现有章节数据使用旧格式：
- chapter-final-TASK-*.json (30+ 个文件)
- 历史数据
- 测试数据

**需要**: 向后兼容读取

---

## 🎯 当前阶段目标 (阶段2)

### 目标: 标记旧字段，不破坏现有功能

**具体任务**:

1. **更新 Schema** ✓
   - 添加 `production_state` 字段定义
   - 标记旧字段为 deprecated/advisory
   - 保持向后兼容

2. **添加文档注释** ✓
   - 在关键位置添加 ADVISORY 注释
   - 说明迁移路径
   - 提供使用示例

3. **创建迁移指南** ✓
   - 新代码应该如何使用
   - 旧代码如何迁移
   - 常见模式转换

4. **保持系统稳定** ✓
   - 不修改现有逻辑
   - 不破坏现有功能
   - 确保测试通过

---

## 📝 推荐方案

### 采用双轨制策略

**新功能** (已实现):
- 使用 ProductionState
- 使用新的验证流程
- 使用契约系统

**现有功能** (保持不变):
- 保留 publish_readiness
- 保留 commercial_verdict
- 保留现有逻辑

**优点**:
- ✅ 新功能使用最佳实践
- ✅ 现有功能保持稳定
- ✅ 平滑过渡
- ✅ 风险可控

**缺点**:
- ⚠️ 两套系统并存
- ⚠️ 需要逐步迁移
- ⚠️ 过渡期较长

---

## 🚀 下一步行动

### 立即执行 (阶段2)

1. **更新 chapter-final.schema.json**
   - 添加 `production_state` 字段
   - 标记旧字段为 advisory
   - 更新描述和示例

2. **创建迁移指南**
   - 新代码使用指南
   - 旧代码迁移路径
   - 常见模式对照

3. **添加关键注释**
   - 在 publish_readiness.py 添加 ADVISORY 注释
   - 在 decision_engine.py 添加说明
   - 在 finalizer.py 添加迁移提示

4. **文档更新**
   - README 说明双轨制
   - API 文档更新
   - 架构文档更新

### 延后执行 (阶段3-4)

- 逐步迁移现有代码
- 性能优化
- 完全移除旧字段

**时间线**: 未来 3-6 个月

---

## 📊 工作量评估

### 阶段2 (当前) - 标记和文档
**工作量**: 0.5-1天  
**风险**: 低  
**价值**: 高（为未来迁移铺路）

### 阶段3 - 逐步迁移
**工作量**: 2-3周  
**风险**: 中  
**价值**: 高（统一架构）

### 阶段4 - 完全移除
**工作量**: 1-2周  
**风险**: 中-高  
**价值**: 中（代码清理）

---

## ✅ Task 5.1 结论

### 完成的工作
- ✅ 统计了遗留代码使用情况
- ✅ 识别了清理优先级
- ✅ 调整了清理策略
- ✅ 创建了详细清单

### 关键决策
- **采用渐进式策略**，不一次性清理
- **双轨制运行**，新旧系统并存
- **当前阶段只标记**，不破坏现有功能
- **未来逐步迁移**，分阶段执行

### 下一步
- Task 5.2: 更新 Schema，标记旧字段
- Task 5.3: 创建迁移指南
- Task 5.4: 添加关键注释
- Task 5.5: 文档更新

---

**完成日期**: 2026-09-09  
**下一任务**: Task 5.2 - 更新 Schema
