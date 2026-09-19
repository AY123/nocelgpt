# P0-1 阶段2：深度集成实施计划

**日期**: 2026-08-18  
**目标**: 将12个模块深度集成到生产流程，产出实际artifact

---

## 实施策略

### 原则
1. **渐进式**: 一次集成1-2个模块，测试后再继续
2. **Opt-in**: 所有新功能通过CLI参数启用，默认关闭
3. **Advisory**: 严格遵守ADR-003，新功能不能gate生产
4. **向后兼容**: 不启用时保持byte-identical

### 优先级排序

#### 高优先级（立即集成）
1. **商业宪法系统** - 作品级规则，影响所有章节
2. **修订任务构建器** - 改进hygiene修订质量
3. **Hook增强评估** - 改进留存检测

#### 中优先级（短期集成）
4. **Promise债务追踪** - 改进narrative coherence
5. **读者期待处理** - 闭环reader simulation
6. **付费点优化器** - 商业决策支持

#### 低优先级（中期集成）
7. **人物弧验证** - checkpoint质量检查
8. **世界一致性检查** - checkpoint质量检查
9. **人物成长状态机** - 长篇维护

---

## 阶段2.1: 商业宪法系统（Week 1）

### 模块
- `commercial_constitution.py` - 定义
- `constitution_validator.py` - 验证器
- `constitution_integration.py` - 集成辅助

### 集成方案

#### 1. 添加CLI参数
```python
# runtime/cli.py
parser.add_argument(
    "--constitution",
    type=str,
    help="Path to commercial constitution file (enables constitution validation)"
)
```

#### 2. 在run_serial开始加载
```python
# runtime/serialize/loop.py, 函数开始处
constitution = None
if constitution_path:
    from ..commercial_constitution import CommercialConstitution
    try:
        constitution = CommercialConstitution.load_from_file(constitution_path)
        print(f"  📜 Constitution loaded: {constitution.work_type}")
    except Exception as e:
        print(f"  ⚠️  Constitution loading failed: {e}")
```

#### 3. 每章验证（advisory）
```python
# 在chapter完成后、写入前
if constitution:
    from ..constitution_validator import ConstitutionValidator
    validator = ConstitutionValidator(constitution)
    
    compliance = validator.validate_chapter(
        chapter_text=chapter_draft["body"],
        chapter_index=spec.index,
        metadata={
            "hook_score": end_hook,
            "ai_voice_risk": ai_taste,
        }
    )
    
    # 记录到ChapterRun（新字段）
    chapter_run.constitution_compliance = compliance.to_dict()
    
    if compliance.violations:
        print(f"  📋 Constitution: {len(compliance.violations)} issues (advisory)")
```

#### 4. ChapterRun扩展
```python
# runtime/serialize/loop.py, ChapterRun dataclass
@dataclass
class ChapterRun:
    # ... 现有字段
    constitution_compliance: Optional[Dict] = None  # P0-1阶段2新增
```

### 测试
```bash
# 创建示例constitution
python3 -m runtime.commercial_constitution --create-example > test_constitution.json

# 运行5章测试
python3 -m runtime.cli serial-run \
    --project tests/fixtures/live-baseline-5ch \
    --max-chapters 5 \
    --constitution test_constitution.json

# 验证artifact
cat tests/fixtures/live-baseline-5ch/registry/derived/chapter-run/run-TASK-00001.json | jq .constitution_compliance
```

---

## 阶段2.2: 修订任务构建器（Week 1）

### 模块
- `revision_task.py`

### 集成方案

#### 1. 在hygiene检查后构建任务
```python
# runtime/serialize/loop.py, hygiene检查处
if hygiene_model and hygiene_rounds > 0:
    # 现有的确定性检查
    deterministic_warnings = check_all_deterministic(chapter_draft)
    
    if deterministic_warnings:
        # P0-1阶段2: 构建结构化修订任务
        from ..revision_task import build_revision_tasks
        revision_tasks = build_revision_tasks(deterministic_warnings)
        
        # 传递给hygiene轮次
        for task in revision_tasks:
            print(f"    🔧 Revision: {task.priority} - {task.description}")
        
        # hygiene_model使用结构化任务
        # （需要修改hygiene调用以接受tasks参数）
```

#### 2. 修改hygiene调用（可选）
```python
# 如果hygiene支持结构化任务
revised = hygiene_model.revise(
    text=chapter_draft["body"],
    tasks=revision_tasks,  # 结构化任务
    fallback_prompt=deterministic_warnings  # 向后兼容
)
```

### 测试
```bash
# 运行带hygiene的5章
python3 -m runtime.cli serial-run \
    --project tests/fixtures/live-baseline-5ch \
    --max-chapters 5 \
    --hygiene-model sonnet-4 \
    --hygiene-rounds 2
```

---

## 阶段2.3: Hook增强评估（Week 1）

### 模块
- `hook_enhanced.py`

### 集成方案

#### 1. 添加CLI参数
```python
parser.add_argument(
    "--enhanced-hook",
    action="store_true",
    help="Use enhanced hook evaluation (more detailed metrics)"
)
```

#### 2. 在end_hook评估处增强
```python
# runtime/serialize/loop.py, end_hook评估处
if enable_enhanced_hook:
    from ..hook_enhanced import EnhancedHookEvaluator
    
    evaluator = EnhancedHookEvaluator()
    hook_result = evaluator.evaluate(
        chapter_text=chapter_draft["body"],
        recent_chapters=get_recent_n_chapters(state, n=3)
    )
    
    # 记录到ChapterRun
    chapter_run.hook_enhanced = hook_result.to_dict()
    
    print(f"  🪝 Hook enhanced: {hook_result.overall_score:.1f} "
          f"({hook_result.dominant_type})")
```

#### 3. ChapterRun扩展
```python
@dataclass
class ChapterRun:
    # ... 现有字段
    hook_enhanced: Optional[Dict] = None  # 增强hook评估
```

---

## 阶段2.4-2.6: 留存系统（Week 2）

### Promise债务追踪

#### 集成点：每章开始前
```python
# 在章节生成前
if enable_promise_tracking:
    from ..promise_debt_tracker import track_promise_debt
    
    debt = track_promise_debt(project_path, spec.index)
    
    if debt.critical_promises:
        # 注入到章节prompt的extra_vars
        extra_vars["urgent_promises"] = debt.critical_promises[:3]
        print(f"  ⏰ Urgent promises: {len(debt.critical_promises)}")
```

### 读者期待处理

#### 集成点：Reader simulation后
```python
# 在reader simulation后
if simulator:
    sim_result = simulator.simulate(chapter_draft)
    
    if enable_reader_expectations:
        from ..reader_expectation import process_reader_expectations
        
        expectations = process_reader_expectations(sim_result)
        
        # 反馈给下一章（通过state或临时文件）
        state.pending_reader_expectations = expectations.top_2
        
        # 记录到ChapterRun
        chapter_run.reader_expectations = expectations.to_dict()
```

### 付费点优化器

#### 集成点：章节完成后
```python
# 在章节评估后
if constitution and enable_paywall_optimizer:
    from ..paywall_optimizer import optimize_paywall
    from ..constitution_aware_paywall import suggest_paywall_points
    
    suggestions = suggest_paywall_points(
        constitution=constitution,
        chapter_run=chapter_run,
        chapter_index=spec.index
    )
    
    chapter_run.paywall_recommendation = suggestions.to_dict()
    
    if suggestions.recommended_position:
        print(f"  💰 Paywall suggestion: ch{suggestions.recommended_position}")
```

---

## 阶段2.7-2.9: Checkpoint质量检查（Week 2-3）

### 人物弧验证

#### 集成点：每10章checkpoint
```python
# runtime/serialize/loop.py, checkpoint写入处
if c.spec.index in CHECKPOINT_INDICES and c.spec.index % 10 == 0:
    if enable_character_arc_validation:
        from ..character_arc_validator import validate_character_arcs
        from ..character_growth import load_character_growth
        
        growth = load_character_growth(project_path, c.spec.index)
        arc_issues = validate_character_arcs(growth)
        
        # 添加到checkpoint
        checkpoint["character_arc_issues"] = arc_issues
        
        if arc_issues:
            print(f"  👤 Character arc: {len(arc_issues)} issues (advisory)")
```

### 世界一致性检查

#### 集成点：每10章checkpoint
```python
if c.spec.index in CHECKPOINT_INDICES:
    if enable_world_consistency:
        from ..world_consistency_checker import check_world_consistency
        
        world_issues = check_world_consistency(project_path, c.spec.index)
        checkpoint["world_consistency_issues"] = world_issues
        
        if world_issues:
            print(f"  🌍 World consistency: {len(world_issues)} issues (advisory)")
```

---

## 实施时间表

### Week 1（高优先级）
- ✅ Day 1-2: 商业宪法系统集成
- ✅ Day 3: 修订任务构建器集成
- ✅ Day 4: Hook增强评估集成
- ✅ Day 5: 5章集成测试

### Week 2（中优先级）
- Day 1-2: Promise债务追踪
- Day 3: 读者期待处理
- Day 4: 付费点优化器
- Day 5: 5章测试 + 30章压力测试

### Week 3（低优先级）
- Day 1-2: 人物弧验证（checkpoint）
- Day 3: 世界一致性检查（checkpoint）
- Day 4: 人物成长状态机
- Day 5: 完整100章测试

---

## CLI参数总览

```bash
python3 -m runtime.cli serial-run \
    --project PROJECT_PATH \
    --max-chapters 30 \
    \
    # P0-1阶段2新增参数
    --constitution path/to/constitution.json \
    --enhanced-hook \
    --enable-promise-tracking \
    --enable-reader-expectations \
    --enable-paywall-optimizer \
    --enable-character-arc-validation \
    --enable-world-consistency \
    \
    # 现有参数
    --model sonnet \
    --hygiene-model sonnet \
    --hygiene-rounds 2
```

---

## 成功标准

### 功能验证
- ✅ 所有12个模块产出artifact
- ✅ Artifact写入ChapterRun或checkpoint
- ✅ 不启用时保持byte-identical
- ✅ 启用时不影响章节生成成功率

### 测试标准
- ✅ 5章测试：所有新artifact正确生成
- ✅ 30章测试：无性能退化
- ✅ 100章测试：长篇稳定性验证
- ✅ 单元测试：1814+ passed

### 质量标准
- ✅ 所有新功能遵守ADR-003（advisory）
- ✅ 代码review通过
- ✅ 文档完整

---

## 风险与缓解

### 风险1: ChapterRun字段膨胀
- **影响**: ChapterRun过大，序列化慢
- **缓解**: 新字段都Optional，只在启用时写入
- **监控**: 测量ChapterRun JSON大小

### 风险2: 性能影响
- **影响**: 每章增加多个检查，运行变慢
- **缓解**: 
  - Constitution验证轻量级（不调用LLM）
  - Checkpoint检查只在10章倍数触发
  - Promise追踪使用缓存
- **监控**: 单章平均时间

### 风险3: 模块接口不匹配
- **影响**: 调用失败，生成中断
- **缓解**: 
  - Try-except包裹所有新调用
  - 失败降级为警告，不中断生成
- **示例**:
```python
try:
    compliance = validator.validate_chapter(...)
    chapter_run.constitution_compliance = compliance.to_dict()
except Exception as e:
    print(f"  ⚠️  Constitution validation error: {e}")
    chapter_run.constitution_compliance = None
```

---

## 下一步行动

1. [ ] 实施阶段2.1（商业宪法）
2. [ ] 实施阶段2.2（修订任务）
3. [ ] 实施阶段2.3（Hook增强）
4. [ ] 运行5章集成测试
5. [ ] 根据结果调整剩余集成计划
