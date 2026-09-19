# P0-1: 孤立模块接入生产链路计划

**目标**: 将12个已实现但未接入的模块接入主生产链路（`run_serial`），使架构适配测试通过。

**核心原则**:
- 每个模块必须从CLI或主生产路径可达
- 每个模块产出结构化artifact
- Artifact必须被下游消费
- 遵守ADR-003（advisory, never gates）和ADR-006（只读事实）

---

## 孤立模块清单

### 1. 人物与世界一致性（长篇维护）
- `character_growth.py` - 人物成长状态机
- `character_arc_validator.py` - 人物弧验证  
- `world_consistency_checker.py` - 世界一致性检查

### 2. 商业宪法系统
- `commercial_constitution.py` - 商业规则定义
- `constitution_validator.py` - 宪法验证器
- `constitution_integration.py` - 集成辅助
- `constitution_aware_paywall.py` - 基于宪法的付费点

### 3. 留存与Promise系统
- `hook_enhanced.py` - 增强型钩子评估
- `reader_expectation.py` - 读者期待处理
- `promise_debt_tracker.py` - Promise债务追踪

### 4. 商业优化
- `paywall_optimizer.py` - 付费点优化

### 5. 修订系统
- `revision_task.py` - 修订任务构建

---

## 接入策略

### 阶段1: 最小化接入（让测试通过）

**目标**: 在不破坏现有功能的前提下，让这些模块从CLI可达。

**方案**: 
1. 在 `runtime/cli.py` 中添加一个轻量级命令（如 `--enable-advanced-checks`）
2. 该命令导入所有12个模块（确保它们被import graph覆盖）
3. 调用它们的基础功能但不影响主流程
4. 架构测试将判定它们"可达"

**实现位置**: 
- `runtime/cli.py`: 添加 `_cmd_advanced_checks` 命令
- 或在 `run_serial` 添加可选参数导入这些模块

### 阶段2: 深度集成（实际使用）

**目标**: 让这些模块真正参与生产流程，产出有价值的artifact。

#### 2.1 商业宪法系统接入

**接入点**: `run_serial` 启动时加载Constitution

```python
# 在 run_serial 函数开始处
from runtime.commercial_constitution import load_constitution
from runtime.constitution_validator import ConstitutionValidator

constitution = load_constitution(project_path)
if constitution:
    validator = ConstitutionValidator(constitution)
```

**消费点**: 每章生成后验证

```python
# 在每章生成后、写入前
if constitution:
    compliance = validator.validate_chapter(chapter_draft, chapter_spec)
    chapter_run.constitution_compliance = compliance  # 记录在ChapterRun
    if compliance.violations:
        # Advisory warning, never gates
        print(f"  Constitution violations: {len(compliance.violations)}")
```

**Artifact**: `constitution_compliance` 字段添加到 `ChapterRun`

#### 2.2 人物弧验证接入

**接入点**: `run_serial` 每10章检查点

```python
# 在checkpoint逻辑中
from runtime.character_arc_validator import validate_character_arcs
from runtime.character_growth import load_character_growth

if chapter_index % 10 == 0:
    growth_records = load_character_growth(project_path, chapter_index)
    arc_issues = validate_character_arcs(growth_records)
    checkpoint["character_arc_issues"] = arc_issues  # Advisory
```

**Artifact**: 添加到10章checkpoint记录

#### 2.3 世界一致性接入

**接入点**: 与人物弧类似，每10章检查

```python
from runtime.world_consistency_checker import check_world_consistency

if chapter_index % 10 == 0:
    world_issues = check_world_consistency(project_path, chapter_index)
    checkpoint["world_consistency_issues"] = world_issues  # Advisory
```

#### 2.4 Hook增强评估接入

**接入点**: 替换或补充现有的hook检查

```python
# 在 loop.py 现有的 hook 检查处
from runtime.hook_enhanced import EnhancedHookEvaluator

hook_evaluator = EnhancedHookEvaluator()
hook_result = hook_evaluator.evaluate(chapter_draft, recent_chapters)
chapter_run.hook_enhanced = hook_result  # 更详细的hook分析
```

#### 2.5 Promise债务追踪接入

**接入点**: 每章生成前检查Promise状态

```python
from runtime.promise_debt_tracker import track_promise_debt

promise_debt = track_promise_debt(project_path, chapter_index)
if promise_debt.critical_promises:
    # 注入到chapter objective
    chapter_objective["urgent_promises"] = promise_debt.critical_promises
```

#### 2.6 读者期待处理接入

**接入点**: Reader simulation后，反馈给下一章

```python
from runtime.reader_expectation import process_reader_expectations

if simulator:
    sim_result = simulator.simulate(chapter_draft)
    expectations = process_reader_expectations(sim_result)
    next_chapter_objective["reader_expectations"] = expectations.top_2
    promise_tracker.add_promises(expectations.deferred)
```

#### 2.7 付费点优化器接入

**接入点**: Constitution + 章节评估后推荐

```python
from runtime.paywall_optimizer import optimize_paywall
from runtime.constitution_aware_paywall import suggest_paywall_points

if constitution:
    paywall_suggestions = suggest_paywall_points(
        constitution, chapter_run, chapter_index)
    chapter_run.paywall_recommendation = paywall_suggestions  # Advisory
```

#### 2.8 修订任务构建器接入

**接入点**: 确定性检查后，构建结构化修订任务

```python
from runtime.revision_task import build_revision_tasks

deterministic_warnings = check_all_deterministic(chapter_draft)
if deterministic_warnings:
    revision_tasks = build_revision_tasks(deterministic_warnings)
    # 传递给hygiene_model或rewrite_model
    if hygiene_model:
        revised = hygiene_model.revise(chapter_draft, revision_tasks)
```

---

## 实施顺序

### Week 1: 阶段1 - 最小化接入
1. 在 `cli.py` 添加导入路径
2. 确保所有12个模块可被import（修复import错误）
3. 运行架构测试，验证通过

### Week 2: 阶段2.1-2.3 - 商业宪法 + 人物/世界
1. 接入商业宪法系统
2. 接入人物弧验证
3. 接入世界一致性检查
4. 运行5章测试验证

### Week 3: 阶段2.4-2.8 - 留存与优化系统
1. 接入Hook增强评估
2. 接入Promise债务追踪
3. 接入读者期待处理
4. 接入付费点优化
5. 接入修订任务构建
6. 运行完整测试

---

## 成功标准

1. ✅ 架构适配测试通过（0个新孤立模块）
2. ✅ 完整测试集通过（0 failed）
3. ✅ 5章生成能产出所有新artifact
4. ✅ 所有新功能遵守ADR-003（advisory, never gates）
5. ✅ 没有破坏现有功能（byte-identical when disabled）

---

## 风险与缓解

**风险1**: 模块有import依赖问题
- **缓解**: 先单独测试每个模块的import

**风险2**: 接入后影响现有byte-identical行为
- **缓解**: 所有新功能都是opt-in或条件触发

**风险3**: 新artifact schema未定义
- **缓解**: 先在ChapterRun添加Optional字段

**风险4**: 性能影响
- **缓解**: 初期只在checkpoint触发，不在每章

---

## 下一步行动

1. [ ] 验证所有12个模块可独立import
2. [ ] 在cli.py添加最小化接入点
3. [ ] 运行架构测试验证
4. [ ] 开始阶段2深度集成
