# 项目后续任务规划

**日期**: 2026-08-18  
**基于**: 2026-08-18复核报告 + P0任务完成状态

---

## 一、当前状态分析

### ✅ 已完成（高质量）
1. **P0-1**: 12个模块接入CLI ✅
2. **P0-2**: 未校准评分降级为advisory ✅
3. **P0-3**: Checkpoint完整性验证 ✅
4. **P0-4**: 测试集全绿（1814 passed）✅
5. **核心架构**: 模块完整性A-，确定性门禁A ✅

### ⚠️ 关键瓶颈（需要解决）
1. **校准样本不足**: 只有3个真实样本（需要30+）
2. **工作区未提交变更**: P0-2相关代码未提交
3. **最新HEAD回归测试**: C1/C3提交后未重新验证
4. **真实长序列验证**: 缺少5-30章真实模型验证
5. **自动修订盲评**: 单评审者+位置偏差

### 📋 待办任务（复核报告）
根据报告第九节"建议的验收顺序"：
1. 固化P0-2未提交变更 ← **已完成**（我们刚提交了4个commits）
2. 最新HEAD完整回归测试 ← **需要做**
3. 5章真实模型冒烟测试 ← **需要做**
4. 30章长序列基线验证 ← **需要做**
5. 收集30+真实人工样本 ← **需要做**（长期）
6. 重算W9校准摘要 ← **需要做**（样本收集后）
7. 多评审者盲评 ← **需要做**（样本收集后）

---

## 二、优先级重排

基于复核报告的核心观点：
> "项目目前的主要瓶颈已经不是'有没有模块'，而是'模块判断是否经过真实数据验证'"

### 原计划 vs 调整后

| 原计划 | 优先级 | 调整后 | 优先级 | 理由 |
|--------|--------|--------|--------|------|
| 阶段2深度集成 | P0 | → 推迟 | P2 | 模块已可达，深度集成不紧急 |
| 校准样本收集 | P1 | → 提升 | **P0** | 这是当前最大瓶颈 |
| 真实模型验证 | P2 | → 提升 | **P0** | 验证比添加功能更重要 |
| 最新HEAD测试 | - | → 新增 | **P0** | 确保当前代码稳定 |

---

## 三、后续任务规划

### Phase 1: 稳定当前基线（本周，P0）

#### 1.1 验证工作区状态 ✅
**状态**: 已完成
- 已提交4个commits（P0-1/P0-2/P0-3/文档）
- 工作区现在应该是干净的

**验证**:
```bash
git status
# 应该显示：nothing to commit, working tree clean
```

#### 1.2 最新HEAD完整回归测试 **← 立即执行**
**目标**: 验证C1/C3提交后的稳定性

**执行**:
```bash
# 完整测试集
python3 -m pytest tests/ -v --tb=short > test_results_2026_08_18.txt

# 关键指标
# - 总数应该 ≥ 1814
# - 失败应该 = 0
# - 跳过应该 ≤ 3
```

**预期**: 1814+ passed, 0 failed

#### 1.3 5章真实模型冒烟测试 **← 本周执行**
**目标**: 验证最新功能在真实LLM下的基本稳定性

**测试项目**:
```bash
# 方案A: 使用live-baseline-5ch fixture重新生成
python3 -m runtime.cli serial-run \
    --project tests/fixtures/live-baseline-5ch \
    --max-chapters 5 \
    --model sonnet-4 \
    --enable-final-quality-review \
    --enable-final-reader-simulation \
    --hygiene-model sonnet-4 \
    --hygiene-rounds 2

# 方案B: 创建新的测试项目
python3 -m runtime.cli genesis create \
    --project /tmp/smoke-test-2026-08-18 \
    --title "五章冒烟测试" \
    --genre xuanhuan

# 然后运行5章
python3 -m runtime.cli serial-run \
    --project /tmp/smoke-test-2026-08-18 \
    --max-chapters 5 \
    --model sonnet-4
```

**验证清单**:
- [ ] 5章全部成功生成
- [ ] 每章有draft_hash, final_hash, m7
- [ ] Checkpoint cp-010正确写入
- [ ] P0-3警告正常触发（如果有）
- [ ] P0-2 advisory警告出现（未校准评分）
- [ ] Production Card正常生成
- [ ] 无崩溃、无阻断

**预期时间**: 2-4小时（取决于模型速度）

---

### Phase 2: 真实数据验证（2-4周，P0）

#### 2.1 30章长序列基线验证 **← 第2周**
**目标**: 验证长篇稳定性

**执行**:
```bash
# 创建30章基线项目
python3 -m runtime.cli genesis create \
    --project /tmp/baseline-30ch-2026-08 \
    --title "三十章基线验证" \
    --genre dushi

# 生成outline
python3 -m runtime.cli outline plan \
    --project /tmp/baseline-30ch-2026-08 \
    --chapters 30

# 运行30章
python3 -m runtime.cli serial-run \
    --project /tmp/baseline-30ch-2026-08 \
    --max-chapters 30 \
    --model sonnet-4 \
    --enable-final-quality-review \
    --hygiene-model sonnet-4 \
    --hygiene-rounds 2
```

**验证清单**:
- [ ] 30章全部成功
- [ ] Checkpoints cp-010, cp-020, cp-030完整
- [ ] P0-3完整性验证正常工作
- [ ] State hash无异常重复
- [ ] Event ID无异常重复
- [ ] 无内存泄漏
- [ ] 平均每章时间稳定

**预期时间**: 1-2天运行 + 1天分析

#### 2.2 收集真实人工评审样本 **← 第3-4周，关键**
**目标**: 收集≥30个真实样本用于校准

**方案A: 从30章基线中抽样**
```bash
# 从30章中选择10-15章进行人工评审
# 标准：覆盖不同章节位置（开头/中间/结尾）

# 抽样脚本
python3 scripts/sample_chapters_for_review.py \
    --project /tmp/baseline-30ch-2026-08 \
    --count 15 \
    --strategy stratified  # 分层抽样
```

**方案B: 混合多个项目**
- 从5章冒烟测试选5章
- 从30章基线选15章
- 从历史项目选10章
- 共30章

**人工评审流程**:
1. 导出章节文本（去除ID）
2. 随机打乱顺序
3. 邀请2-3位评审者
4. 使用标准化评分表（12个维度）
5. 盲评（不告知章节来源）
6. 记录评分理由
7. 计算评审者间一致性（ICC）

**评分维度**（与W9对齐）:
- opening_hook, chapter_goal, conflict_progression
- character_motivation, emotion_flow
- information_density, payoff_delivery
- ending_hook, continuity, ai_voice_risk
- paying_intent, continue_intent

**预期时间**: 2-3周（评审者时间）

#### 2.3 重算W9校准摘要
**前提**: 完成2.2，收集≥30真实样本

**执行**:
```bash
# 重新计算校准
python3 -m runtime.cli reviewer-calibration summary \
    --project /tmp/baseline-30ch-2026-08 \
    --write

# 检查结果
cat quality-golden-set/metadata/w9-calibration-summary.json | \
    jq '{status, real_sample_count, decision_dimensions, diagnostic_dimensions}'
```

**成功标准**:
- real_sample_count ≥ 30
- 至少2-3个维度升级为decision级
- 相关系数 > 0.7且置信区间窄

---

### Phase 3: 质量能力升级（4-6周，P1）

#### 3.1 启用校准后的质量门禁
**前提**: Phase 2完成，有decision级维度

**执行**:
```bash
# 使用质量门禁运行
python3 -m runtime.cli serial-run \
    --project PROJECT \
    --enable-quality-gate  # 新增参数
    --quality-gate-dimensions hook,retention  # 指定decision级维度
```

**配合修改**:
- decision_engine.py: 从calibration_status读取decision_dimensions
- 当前已实现：decision维度可以hold，diagnostic维度advisory

#### 3.2 多评审者W10盲评
**目标**: 重新验证自动修订效果

**改进**:
- 至少3位评审者
- 随机换位（A/B位置随机）
- 完整reason codes
- 加入人工修订第三臂

**预期**: 如果自动修订净收益仍为负，继续restrict

---

### Phase 4: 功能扩展（8-12周，P2）

#### 4.1 阶段2深度集成（有选择性）
**调整策略**: 不是全部12个模块，而是按需集成

**优先集成**（基于真实需求）:
1. **商业宪法系统** - 如果有实际constitution文件
2. **修订任务构建器** - 改进hygiene质量
3. **Promise债务追踪** - 改进长篇一致性

**暂缓集成**:
- Hook增强评估 - 现有hook已足够
- 人物弧验证 - checkpoint已有基本检查
- 世界一致性 - 除非有明确问题

#### 4.2 性能优化
- 减少LLM调用次数
- 优化prompt长度
- 并行化stage A/B

#### 4.3 Dashboard增强
- Checkpoint质量报告
- 校准状态可视化
- Production Card汇总

---

## 四、任务优先级矩阵

| 任务 | 紧急度 | 重要度 | 优先级 | 预计时间 |
|------|--------|--------|--------|---------|
| 最新HEAD回归测试 | 高 | 高 | **P0** | 1h |
| 5章真实模型冒烟 | 高 | 高 | **P0** | 4h |
| 30章长序列验证 | 高 | 高 | **P0** | 2天 |
| 收集30+真实样本 | 中 | 极高 | **P0** | 3周 |
| 重算W9校准摘要 | 低 | 极高 | **P0** | 1h（样本后） |
| 多评审者W10盲评 | 低 | 高 | P1 | 2周 |
| 启用质量门禁 | 低 | 高 | P1 | 1天 |
| 阶段2深度集成 | 低 | 中 | P2 | 2-3周 |
| 性能优化 | 低 | 中 | P2 | 1-2周 |
| Dashboard增强 | 低 | 低 | P3 | 按需 |

---

## 五、立即行动清单（本周）

### Day 1（今天）
- [x] P0-1/P0-2/P0-3提交 ✅ **已完成**
- [ ] 验证git status干净
- [ ] 运行最新HEAD完整回归测试
- [ ] 分析测试结果

### Day 2
- [ ] 准备5章冒烟测试环境
- [ ] 执行5章真实模型测试
- [ ] 验证所有P0修复在真实场景下工作

### Day 3-4
- [ ] 分析5章测试结果
- [ ] 修复发现的任何问题
- [ ] 准备30章基线验证

### Day 5
- [ ] 启动30章长序列运行
- [ ] 设计人工评审流程
- [ ] 准备评审材料和评分表

---

## 六、关键决策点

### 决策1: 阶段2深度集成的范围
**问题**: 是否全部12个模块都深度集成？

**建议**: **否**，按需集成
- 商业宪法：如果有实际constitution文件
- 修订任务：如果hygiene效果不佳
- Promise追踪：如果长篇一致性有问题
- 其他模块：保持可达但不强制使用

**理由**: 复核报告明确指出"模块判断是否经过真实数据验证"才是瓶颈，盲目添加功能反而分散精力。

### 决策2: 质量门禁的启用时机
**问题**: 何时启用LLM质量评分作为门禁？

**建议**: **严格等待校准完成**
- 必须≥30真实样本
- 必须有≥2个decision级维度
- 必须验证误差和置信区间
- 在启用前运行pilot测试

**当前策略**: 继续advisory only（P0-2已正确实现）

### 决策3: 自动修订的未来
**问题**: 自动修订净收益为负，是否删除？

**建议**: **保持opt-in，不删除**
- 当前盲评有明显位置偏差
- 只有1位评审者
- 需要多评审者重新评估
- 可能特定类型问题（如错别字）仍有价值

**当前策略**: 继续restrict（不默认启用）

---

## 七、成功标准

### Phase 1（本周）
- [x] P0修复已提交 ✅
- [ ] 最新HEAD测试 ≥1814 passed, 0 failed
- [ ] 5章冒烟测试全部成功
- [ ] 无阻断、无崩溃

### Phase 2（2-4周）
- [ ] 30章长序列全部成功
- [ ] 收集≥30真实人工样本
- [ ] W9校准状态升级（≥2个decision维度）
- [ ] 评审者间一致性ICC > 0.7

### Phase 3（4-6周）
- [ ] 质量门禁可安全启用
- [ ] 多评审者盲评完成
- [ ] 自动修订策略明确（继续/改进/删除）

### Phase 4（8-12周）
- [ ] 按需集成2-3个高价值模块
- [ ] 性能优化（每章平均时间降低20%）
- [ ] Dashboard可视化校准状态

---

## 八、风险与缓解

### 风险1: 人工评审者难找
**影响**: 无法收集30个样本

**缓解**:
- 降低要求到20个样本（最低限度）
- 分多批收集（每批5-10个）
- 简化评审流程（30分钟/章→20分钟/章）

### 风险2: 校准后仍无decision维度
**影响**: 质量门禁无法启用

**缓解**:
- 这是可接受的结果
- 继续advisory only
- 投入精力改进评分模型

### 风险3: 30章长序列失败
**影响**: 核心稳定性存疑

**缓解**:
- 优先修复导致失败的bug
- 降级到15章基线
- 分段运行（3次10章）

---

## 九、总结

### 核心观点
1. **P0任务已高质量完成** ✅
2. **当前瓶颈是真实数据验证，不是功能开发**
3. **阶段2深度集成应该推迟到Phase 4**
4. **立即优先级是：测试→验证→校准→门禁**

### 行动方针
```
短期（1周）: 测试验证基线稳定性
中期（4周）: 收集真实样本，完成校准
长期（12周）: 按需扩展功能，持续优化
```

### 最终目标
不是"有多少模块"，而是"能稳定可信地生产高质量小说"。

---

**下一步**: 立即执行最新HEAD完整回归测试
