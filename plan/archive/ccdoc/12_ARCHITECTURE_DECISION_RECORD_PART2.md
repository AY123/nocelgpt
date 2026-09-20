# ANovel V2 架构决策记录：逐项评估与最终决策（第2部分）

**版本**: ADR v1.0  
**制定日期**: 2026-09-18  
**文档说明**: 第2部分 - 生产流程、质量系统、Prompt系统

---

## 4. 生产流程系统（Production Pipeline）

### 📊 现状分析

**当前项目（V1）**:
```python
# ainovel/AI-Novel-Runtime/runtime/serialize/loop.py
# 2907行的单体函数，包含所有生产逻辑
```

**问题**:
- ❌ 单体函数过长（2907行）
- ❌ 难以扩展（新增Stage需修改主流程）
- ❌ BLOCKED语义错误（不阻断后续章节）
- ❌ 成本追踪不完整

---

### ✅ 可借鉴（ADOPT）

#### 4.1 从网络项目借鉴

**借鉴1: Pipeline模式**

**来源**: 通用软件工程模式 + CreAgentive论文

```python
# ✅ 借鉴Pipeline模式
class ProductionPipeline:
    def __init__(self):
        self.stages: List[ProductionStage] = []
    
    def add_stage(self, stage: ProductionStage):
        self.stages.append(stage)
    
    def execute(self, context: ChapterContext) -> ChapterResult:
        for stage in self.stages:
            context = stage.process(context)
            if context.should_abort:
                break
        return context.result
```

**理由**: 
- 解耦各个生产步骤
- 新增Stage不需修改主流程
- 便于测试和维护

**借鉴2: Draft A/B/C工作流**

**来源**: [HZ-KMNO项目](https://github.com/HZ-KMNO/web-novel-writing-guidance-skill)

```python
# ✅ 借鉴Draft A/B/C
def produce_chapter(chapter_num):
    # Draft A: 快速初稿（60s）
    draft_a = generate_draft_a(chapter_num)
    if is_good_enough(draft_a):
        return draft_a, "draft_a"
    
    # Draft B: 改进版（120s）
    draft_b = generate_draft_b(chapter_num, base=draft_a)
    if is_good_enough(draft_b):
        return draft_b, "draft_b"
    
    # Draft C: 精修版（180s）
    draft_c = generate_draft_c(chapter_num, base=draft_b)
    return draft_c, "draft_c"
```

**理由**:
- HZ-KMNO项目验证（中文网文专用）
- 提升单章质量15-25%
- 成本可控（平均$0.020/章）

**借鉴3: 成本追踪与预算控制**

**来源**: [CreAgentive论文](https://arxiv.org/html/2509.26461) - $1/100章

```python
# ✅ 借鉴成本控制
COST_TARGETS = {
    "per_chapter": 0.01,      # 目标$0.01/章
    "per_30_chapters": 0.30,  # M3目标
    "per_100_chapters": 1.00  # M6目标
}

def produce_with_budget(chapter_num, budget_remaining):
    if budget_remaining < COST_TARGETS["per_chapter"]:
        raise BudgetExceededError()
    
    draft, cost = generate_chapter(chapter_num)
    log_cost(chapter_num, cost)
    
    return draft, budget_remaining - cost
```

**理由**: CreAgentive论文量化证明可实现

#### 4.2 客观补充建议

**补充1: 异步生产模式**

```python
# 建议增加
class AsyncProductionPipeline:
    """异步生产（支持批量并行）"""
    
    async def produce_batch(self, chapter_nums: List[int]):
        """批量生产（提升吞吐）"""
        tasks = [self.produce_chapter(num) for num in chapter_nums]
        results = await asyncio.gather(*tasks)
        return results
```

**理由**: 提升吞吐量（100章场景）

**补充2: 生产监控与可观测性**

```python
# 建议增加
class ProductionMetrics:
    """生产指标监控"""
    
    def record_stage_duration(self, stage_name, duration):
        pass
    
    def record_chapter_cost(self, chapter_num, cost):
        pass
    
    def get_bottleneck_stages(self) -> List[str]:
        """识别瓶颈阶段"""
        pass
```

**理由**: 便于性能优化

---

### ❌ 不应借鉴（REJECT）

#### 4.3 从当前项目拒绝

**拒绝1: 2907行单体函数**

```python
# ❌ V1做法（拒绝）
def serialize_loop_v1():
    # 2907行代码
    # 包含Genesis/Planning/Writing/QA/Decision...
    pass
```

**理由**: 不可维护，难以测试

**拒绝2: BLOCKED不阻断**

```python
# ❌ V1做法（拒绝）
if decision.status == "BLOCKED":
    print("BLOCKED but continue next chapter")
    # 仍然继续生成后续章节
```

**理由**: 导致错误蔓延

#### 4.4 从网络项目拒绝

**拒绝1: 过度复杂的多智能体争论**

**来源**: InkOS的10-agent pipeline

```python
# ❌ 拒绝过度复杂的多智能体
agents = [Agent1(), Agent2(), ..., Agent10()]  # 10个智能体
for agent in agents:
    agent.argue_about_plot_holes()  # 多轮争论
```

**理由**: 
- M3前优先简单可靠
- 成本过高
- 增加不确定性

---

### 🔄 V2改良方案（IMPROVE）

#### 4.5 改良方案

**改良1: Pipeline架构**

```python
# V2设计
class ProductionPipeline:
    """生产管道（插件化）"""
    
    def __init__(self):
        self.stages: List[ProductionStage] = [
            LoadContextStage(),
            GenerateDraftStage(),
            GenreValidationStage(),
            QualityGateStage(),
            DecisionStage(),
            PersistStage()
        ]
    
    def execute(self, chapter_num: int) -> ChapterResult:
        context = ChapterContext(chapter_num)
        
        for stage in self.stages:
            try:
                context = stage.process(context)
                
                # 检查是否应中止
                if context.should_abort:
                    logger.info(f"Pipeline aborted at {stage.name}")
                    break
                
            except StageError as e:
                context.errors.append(e)
                if stage.is_critical:
                    break
        
        return context.to_result()

class ProductionStage(ABC):
    """生产阶段抽象基类"""
    
    name: str
    is_critical: bool = False
    
    @abstractmethod
    def process(self, context: ChapterContext) -> ChapterContext:
        pass

class GenerateDraftStage(ProductionStage):
    """生成草稿阶段"""
    
    name = "GenerateDraft"
    
    def process(self, context: ChapterContext) -> ChapterContext:
        # Draft A/B/C工作流
        draft_workflow = DraftABCWorkflow()
        
        draft, cost, version = draft_workflow.produce_chapter(
            context.chapter_num,
            context.task_package
        )
        
        context.draft = draft
        context.cost += cost
        context.draft_version = version
        
        return context

class GenreValidationStage(ProductionStage):
    """题材验证阶段"""
    
    name = "GenreValidation"
    is_critical = True  # 违反题材约束 = 中止
    
    def process(self, context: ChapterContext) -> ChapterContext:
        violations = GenreRegistry.validate_constraints(
            context.genre_id,
            context.draft
        )
        
        critical_violations = [v for v in violations if v.severity == "critical"]
        
        if critical_violations:
            context.should_abort = True
            context.errors.append(GenreViolationError(critical_violations))
        
        context.genre_violations = violations
        return context

class QualityGateStage(ProductionStage):
    """质量门禁阶段"""
    
    name = "QualityGate"
    
    def process(self, context: ChapterContext) -> ChapterContext:
        # 确定性检查
        issues = []
        
        # 长度检查
        if not (3500 <= len(context.draft) <= 4500):
            issues.append(Issue("length_out_of_range", "high"))
        
        # AI味检查
        ai_taste_score = detect_ai_taste(context.draft)
        if ai_taste_score > 0.3:
            issues.append(Issue("ai_taste_detected", "medium"))
        
        # 一致性检查（ConStory-Checker）
        consistency_errors = consistency_checker.check_chapter(
            context.draft,
            context.chapter_num,
            context.story_state
        )
        
        issues.extend(consistency_errors)
        
        context.quality_issues = issues
        return context

class DecisionStage(ProductionStage):
    """决策阶段"""
    
    name = "Decision"
    
    def process(self, context: ChapterContext) -> ChapterContext:
        # 决策逻辑
        decision = self._make_decision(context)
        
        if decision.status == "BLOCKED":
            context.should_abort = True  # 关键：阻断后续章节
            context.decision = decision
            return context
        
        context.decision = decision
        return context
    
    def _make_decision(self, context):
        # 如果有critical错误 -> BLOCKED
        critical_errors = [
            e for e in context.errors 
            if getattr(e, 'severity', '') == 'critical'
        ]
        
        if critical_errors:
            return Decision(
                status="BLOCKED",
                reason=f"Critical errors: {critical_errors}"
            )
        
        # 如果有critical质量问题 -> BLOCKED
        critical_quality = [
            i for i in context.quality_issues 
            if i.severity == "critical"
        ]
        
        if critical_quality:
            return Decision(
                status="BLOCKED",
                reason=f"Critical quality issues: {critical_quality}"
            )
        
        # 否则 -> APPROVED
        return Decision(status="APPROVED")

class PersistStage(ProductionStage):
    """持久化阶段"""
    
    name = "Persist"
    
    def process(self, context: ChapterContext) -> ChapterContext:
        if context.decision.status == "APPROVED":
            # 提取事实
            facts = extract_facts_from_chapter(
                context.draft,
                context.chapter_num,
                context.genre_config
            )
            
            # Mint（原子提交）
            mint_result = mint_executor.execute(facts)
            
            context.mint_result = mint_result
            context.snapshot_id = mint_result.snapshot_id
        
        return context
```

**改良2: Draft A/B/C集成**

```python
class DraftABCWorkflow:
    """三稿制工作流"""
    
    def produce_chapter(self, chapter_num, task_package):
        # Draft A: 快速初稿
        draft_a, cost_a = self._generate_draft_a(chapter_num, task_package)
        
        issues_a = self._detect_issues(draft_a, level="critical")
        
        if len(issues_a) == 0 and self._is_good_enough(draft_a):
            return draft_a, cost_a, "draft_a"
        
        # Draft B: 改进版
        draft_b, cost_b = self._generate_draft_b(
            chapter_num,
            task_package,
            base_draft=draft_a,
            issues=issues_a
        )
        
        issues_b = self._detect_issues(draft_b, level="high")
        
        if len(issues_b) == 0:
            return draft_b, cost_a + cost_b, "draft_b"
        
        # Draft C: 精修版
        draft_c, cost_c = self._generate_draft_c(
            chapter_num,
            task_package,
            base_draft=draft_b,
            issues=issues_b
        )
        
        return draft_c, cost_a + cost_b + cost_c, "draft_c"
    
    def _generate_draft_a(self, chapter_num, task_package):
        """Draft A: 关注剧情推进"""
        prompt = f"""
你是快速写作专家，生成第{chapter_num}章。

【任务】
{task_package.to_prompt()}

【要求】
- 重点：剧情推进
- 速度：快速生成
- 长度：{task_package.target_length}字（±500）

开始：
"""
        draft = llm.generate(prompt, temperature=0.8, timeout=60)
        return draft, llm.get_last_cost()
    
    def _generate_draft_b(self, chapter_num, task_package, base_draft, issues):
        """Draft B: 修复明显问题"""
        prompt = f"""
你是资深编辑，改进第{chapter_num}章。

【初稿】
{base_draft}

【问题】
{self._format_issues(issues)}

【改进要求】
- 修复所有问题
- 优化语言
- 长度保持

输出改进版本：
"""
        draft = llm.generate(prompt, temperature=0.7, timeout=120)
        return draft, llm.get_last_cost()
    
    def _generate_draft_c(self, chapter_num, task_package, base_draft, issues):
        """Draft C: 精修细节"""
        prompt = f"""
你是网文大神，精修第{chapter_num}章。

【当前版本】
{base_draft}

【仍需优化】
{self._format_issues(issues)}

【精修要求】
- 修复细节
- 优化流畅度、情感、节奏、钩子
- 达到起点出版水准

输出最终版本：
"""
        draft = llm.generate(prompt, temperature=0.6, timeout=180)
        return draft, llm.get_last_cost()
    
    def _is_good_enough(self, draft):
        """判断是否足够好"""
        # 长度合格
        if not (3500 <= len(draft) <= 4500):
            return False
        
        # 无AI味
        if detect_ai_taste_score(draft) > 0.3:
            return False
        
        return True
```

**改良3: 成本追踪与预算控制**

```python
class CostTracker:
    """成本追踪器"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.chapter_costs: Dict[int, float] = {}
        self.stage_costs: Dict[str, float] = {}
    
    def record_cost(self, chapter_num: int, stage: str, cost: float):
        """记录成本"""
        self.total_cost += cost
        
        if chapter_num not in self.chapter_costs:
            self.chapter_costs[chapter_num] = 0.0
        self.chapter_costs[chapter_num] += cost
        
        if stage not in self.stage_costs:
            self.stage_costs[stage] = 0.0
        self.stage_costs[stage] += cost
    
    def check_budget(self, target: str) -> bool:
        """检查预算"""
        if target == "30_chapters":
            return self.total_cost <= 0.30
        elif target == "100_chapters":
            return self.total_cost <= 1.00
        return True
    
    def get_report(self) -> Dict:
        """生成成本报告"""
        return {
            "total_cost": self.total_cost,
            "average_per_chapter": self.total_cost / len(self.chapter_costs),
            "by_chapter": self.chapter_costs,
            "by_stage": self.stage_costs,
            "budget_status": {
                "30_chapters": self.check_budget("30_chapters"),
                "100_chapters": self.check_budget("100_chapters")
            }
        }

class ProductionPipeline:
    """增加成本追踪"""
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        # ...
    
    def execute(self, chapter_num):
        context = ChapterContext(chapter_num)
        
        for stage in self.stages:
            start_cost = context.cost
            context = stage.process(context)
            stage_cost = context.cost - start_cost
            
            # 记录成本
            self.cost_tracker.record_cost(
                chapter_num,
                stage.name,
                stage_cost
            )
        
        return context.to_result()
```

**改良4: BLOCKED语义修复**

```python
def produce_30_chapters():
    """生产30章（正确处理BLOCKED）"""
    
    produced_chapters = []
    
    for chapter_num in range(1, 31):
        result = pipeline.execute(chapter_num)
        
        if result.decision.status == "BLOCKED":
            logger.critical(f"Chapter {chapter_num} BLOCKED, stopping production")
            
            # 关键：不继续生成后续章节
            break
        
        produced_chapters.append(result)
    
    return produced_chapters
```

---

### ⭐ 最终架构决策（DECISION）

#### Decision 4.1: Pipeline架构（必须采纳）

**决策**: ✅ **采纳** Pipeline模式

**理由**:
- 解耦生产步骤
- 主流程从2907行降低到<500行
- 新增Stage不需修改主流程

**实施**:
- M2 Week 7-8: Pipeline基础架构
- M2 Week 8: 实现7个核心Stage

**验收标准**:
- ✅ 主流程代码量<500行
- ✅ 新增Stage不修改主流程
- ✅ 单元测试覆盖所有Stage

---

#### Decision 4.2: Draft A/B/C（采纳）

**决策**: ✅ **采纳** Draft A/B/C工作流

**理由**:
- HZ-KMNO项目验证（中文网文专用）
- 提升质量15-25%
- 成本可控

**实施**:
- M2 Week 9-10: 实现三稿制
- GenerateDraftStage集成

**验收标准**:
- ✅ Draft B质量 > Draft A（人工盲评）
- ✅ Draft C质量 > Draft B
- ✅ 平均成本<$0.025/章

---

#### Decision 4.3: 成本追踪（必须采纳）

**决策**: ✅ **采纳** 成本追踪与预算控制

**理由**: CreAgentive论文验证（$1/100章可实现）

**实施**:
- M1 设计：成本目标定义
- M2 Week 8: CostTracker实现
- M2 Week 9-14: 所有Stage集成

**验收标准**:
- ✅ 30章成本<$0.75（考虑Draft A/B/C）
- ✅ 100章成本<$2.50（M6目标，留有余量）

---

#### Decision 4.4: BLOCKED语义修复（必须修复）

**决策**: ✅ **必须修复** BLOCKED不阻断Bug

**理由**: V1 P0 Bug，导致错误蔓延

**实施**:
- M2 Week 8: DecisionStage实现
- 集成测试验证

**验收标准**:
- ✅ BLOCKED状态不生成后续章节
- ✅ 集成测试通过（3个场景）

---

#### Decision 4.5: 异步生产（暂不采纳）

**决策**: ⚠️ **暂不采纳** 异步批量生产

**理由**: M3前优先同步流程，M6后考虑（100章场景）

---

#### Decision 4.6: 多智能体争论（不采纳）

**决策**: ❌ **不采纳** 10-agent争论机制

**理由**: 过度复杂，成本过高，M3前不需要

---

## 5. 质量系统

### 📊 现状分析

**当前项目（V1）**:
```python
# ainovel/AI-Novel-Runtime/runtime/qa/
# 多个评分系统（Reader-sim, Commercial, Quality）
# 但未经校准
```

**优点**:
- ✅ 双轴质量系统（Deterministic + Evaluative）
- ✅ 18维度Quality v2

**问题**:
- ❌ 评分系统未校准（无金样集）
- ❌ 缺少系统化的错误分类（19种类型）
- ❌ AI味检测只用正则表达式

---

### ✅ 可借鉴（ADOPT）

#### 5.1 从当前项目借鉴

**借鉴1: 双轴质量系统**

```python
# ✅ V1设计（保持）
Deterministic Gate（确定性检查，可阻断）
  +
Evaluative Trend（评分诊断，不阻断）
```

**理由**: ADR-003明确定义，正确的架构

#### 5.2 从网络项目借鉴

**借鉴1: 错误分类体系（19种类型）**

**来源**: [ConStory-Bench论文](http://acl.ldc.upenn.edu/2026.findings-acl.410/)

```python
# ✅ 借鉴19种错误类型
ERROR_TAXONOMY = {
    "factual": [
        "entity_attribute_change",
        "entity_relation_change",
        "entity_disappearance"
    ],
    "temporal": [
        "timeline_contradiction",
        "event_order_wrong",
        "duration_inconsistency",
        "season_weather_conflict"
    ],
    "character": [
        "personality_drift",
        "knowledge_inconsistency",
        "goal_change",
        "ability_inconsistency",
        "speech_pattern_change"
    ],
    "world": [
        "rule_violation",
        "setting_change",
        "power_system_inconsistent",
        "technology_level_jump"
    ],
    "plot": [
        "causal_contradiction",
        "unresolved_plot_thread",
        "premature_resolution",
        "impossible_coincidence",
        "motivation_missing"
    ]
}
```

**理由**: 学术研究支撑，最系统的错误分类

**借鉴2: Perplexity质量门禁**

**来源**: [Claude Book - HackerNoon](https://hackernoon.com/claude-book-a-multi-agent-framework-for-writing-novels-with-claude-code)

```python
# ✅ 借鉴Perplexity检测
class PerplexityGate:
    def calculate_perplexity(self, text):
        # 使用GPT-2计算困惑度
        perplexity = model.calculate(text)
        return perplexity
    
    def detect_ai_taste(self, text):
        perplexity = self.calculate_perplexity(text)
        
        # AI生成文本通常有特定困惑度范围
        if 20 < perplexity < 40:
            return {"has_ai_taste": True, "confidence": 0.8}
        
        return {"has_ai_taste": False}
```

**理由**: 比正则表达式更准确

**借鉴3: 情感一致性检查**

**来源**: [SCORE论文](https://arxiv.org/html/2503.23512v1) - 89.7%情感一致性

```python
# ✅ 借鉴情感一致性
class EmotionalConsistencyChecker:
    EMOTIONS = [
        "neutral", "happy", "sad", "angry", "fearful"
    ]
    
    VALID_TRANSITIONS = {
        "neutral": ["happy", "sad", "angry"],
        "happy": ["neutral", "excited"],
        # ...
    }
    
    def check_emotion_transition(self, char_id, current_emotion, chapter_num):
        last_emotion = get_last_emotion(char_id, chapter_num - 1)
        
        if current_emotion not in self.VALID_TRANSITIONS[last_emotion]:
            # 检查是否有重大事件解释
            events = get_major_events_between(chapter_num - 1, chapter_num)
            
            if not has_justifying_event(events, last_emotion, current_emotion):
                return {"valid": False, "reason": "Abrupt emotion jump"}
        
        return {"valid": True}
```

**理由**: SCORE论文量化证明（89.7%一致性）

#### 5.3 客观补充建议

**补充1: Token熵检测**

**来源**: ConStory-Bench论文发现

```python
# 建议增加
def detect_high_entropy_segments(chapter_text):
    """检测高token熵的文本段（更易出错）"""
    segments = split_into_segments(chapter_text, size=100)
    
    high_entropy_segments = []
    for seg in segments:
        entropy = calculate_token_entropy(seg)
        if entropy > THRESHOLD:
            high_entropy_segments.append({
                "segment": seg,
                "entropy": entropy,
                "risk": "high"
            })
    
    return high_entropy_segments
```

**理由**: ConStory-Bench发现高熵区更易出错

**补充2: 中段加强检查**

```python
# 建议增加
class MiddleChapterGuard:
    """中段章节需要更严格检查"""
    
    def get_check_intensity(self, chapter_num, total_chapters):
        ratio = chapter_num / total_chapters
        
        if 0.3 < ratio < 0.7:
            return "high"  # 中段，高强度
        return "normal"
```

**理由**: ConStory-Bench发现错误倾向于出现在中段

---

### ❌ 不应借鉴（REJECT）

#### 5.4 从当前项目拒绝

**拒绝1: 未校准的评分系统**

```python
# ❌ V1做法（拒绝直接使用）
reader_sim_score = reader_sim.evaluate(chapter)  # 未校准
commercial_score = commercial.evaluate(chapter)  # 未校准

# 直接用于决策（❌）
if reader_sim_score < 0.7:
    decision = "BLOCKED"
```

**理由**: 
- 未经金样集校准
- 不能用于阻断决策
- 只能用于诊断

**正确做法**: 标注为E2级（诊断级），不参与阻断决策

---

### 🔄 V2改良方案（IMPROVE）

#### 5.5 改良方案

**改良1: ConStory-Checker实现**

```python
class ConsistencyChecker:
    """19种错误类型检测器"""
    
    def __init__(self):
        self.checkers = {
            "factual": [
                EntityAttributeChecker(),
                EntityRelationChecker(),
                EntityDisappearanceChecker()
            ],
            "temporal": [
                TimelineChecker(),
                EventOrderChecker(),
                DurationChecker(),
                SeasonWeatherChecker()
            ],
            "character": [
                PersonalityChecker(),
                KnowledgeChecker(),
                GoalChecker(),
                AbilityChecker(),
                SpeechPatternChecker()
            ],
            "world": [
                WorldRuleChecker(),
                SettingChecker(),
                PowerSystemChecker(),
                TechnologyLevelChecker()
            ],
            "plot": [
                CausalChecker(),
                PlotThreadChecker(),
                ResolutionChecker(),
                CoincidenceChecker(),
                MotivationChecker()
            ]
        }
    
    def check_chapter(self, chapter, chapter_num, story_state):
        all_errors = []
        
        for category, checkers in self.checkers.items():
            for checker in checkers:
                errors = checker.check(chapter, chapter_num, story_state)
                
                for error in errors:
                    error["category"] = category
                    error["subtype"] = checker.error_type
                    error["severity"] = checker.severity
                    error["evidence"] = checker.get_evidence(chapter, error)
                
                all_errors.extend(errors)
        
        return self._categorize_by_severity(all_errors)

# 示例检查器
class PersonalityChecker:
    error_type = "personality_drift"
    severity = "high"
    
    def check(self, chapter, chapter_num, story_state):
        errors = []
        
        # 提取角色行为
        char_behaviors = extract_character_behaviors(chapter)
        
        for char_id, behaviors in char_behaviors.items():
            # 获取历史人设
            historical_personality = story_state.get_character_personality(char_id)
            
            if not historical_personality:
                continue
            
            # 检查是否一致
            for behavior in behaviors:
                if not is_consistent_with_personality(behavior, historical_personality):
                    errors.append({
                        "character": char_id,
                        "behavior": behavior,
                        "expected_personality": historical_personality,
                        "chapter": chapter_num
                    })
        
        return errors
    
    def get_evidence(self, chapter, error):
        # 提取相关句子作为证据
        return extract_sentences_about_character(
            chapter,
            error["character"]
        )[:2]
```

**改良2: AI味多维检测**

```python
class AITasteDetector:
    """AI味多维检测（正则+Perplexity）"""
    
    def __init__(self):
        self.regex_detector = RegexAITasteDetector()
        self.perplexity_detector = PerplexityGate()
    
    def detect(self, text):
        # 方法1: 正则模式检测
        regex_result = self.regex_detector.detect(text)
        
        # 方法2: Perplexity检测
        perplexity_result = self.perplexity_detector.detect_ai_taste(text)
        
        # 综合判断
        if regex_result["has_ai_taste"] and perplexity_result["has_ai_taste"]:
            return {
                "has_ai_taste": True,
                "confidence": 0.9,
                "methods": ["regex", "perplexity"]
            }
        elif regex_result["has_ai_taste"] or perplexity_result["has_ai_taste"]:
            return {
                "has_ai_taste": True,
                "confidence": 0.7,
                "methods": ["regex" if regex_result["has_ai_taste"] else "perplexity"]
            }
        
        return {"has_ai_taste": False}

class RegexAITasteDetector:
    """正则模式检测"""
    
    AI_PATTERNS = [
        r"如同.{1,5}一般",
        r"仿佛.{1,5}般",
        r"不禁.{1,5}起来",
        r"内心深处",
        r"心中暗想",
        # ... 更多模式
    ]
    
    def detect(self, text):
        pattern_count = 0
        for pattern in self.AI_PATTERNS:
            if re.search(pattern, text):
                pattern_count += 1
        
        # 如果匹配3个以上模式 -> AI味
        if pattern_count >= 3:
            return {"has_ai_taste": True, "pattern_count": pattern_count}
        
        return {"has_ai_taste": False}
```

**改良3: 情感一致性集成**

```python
class QualityGateStage(ProductionStage):
    """质量门禁（增加情感检查）"""
    
    def __init__(self):
        super().__init__()
        self.consistency_checker = ConsistencyChecker()
        self.ai_taste_detector = AITasteDetector()
        self.emotional_checker = EmotionalConsistencyChecker()
    
    def process(self, context):
        issues = []
        
        # 1. 确定性检查
        issues.extend(check_length(context.draft))
        issues.extend(check_format(context.draft))
        
        # 2. AI味检测（改良）
        ai_taste = self.ai_taste_detector.detect(context.draft)
        if ai_taste["has_ai_taste"]:
            issues.append(Issue(
                "ai_taste_detected",
                "medium",
                confidence=ai_taste["confidence"]
            ))
        
        # 3. 一致性检查（19种类型）
        consistency_errors = self.consistency_checker.check_chapter(
            context.draft,
            context.chapter_num,
            context.story_state
        )
        issues.extend(consistency_errors["critical"])
        issues.extend(consistency_errors["high"])
        
        # 4. 情感一致性（新增）
        emotions = extract_emotions_from_chapter(context.draft)
        for char_id, emotion in emotions.items():
            result = self.emotional_checker.check_emotion_transition(
                char_id,
                emotion,
                context.chapter_num
            )
            
            if not result["valid"]:
                issues.append(Issue(
                    "emotion_inconsistency",
                    "high",
                    character=char_id,
                    reason=result["reason"]
                ))
        
        # 5. Token熵检测（新增）
        high_entropy_segs = detect_high_entropy_segments(context.draft)
        if high_entropy_segs:
            issues.append(Issue(
                "high_entropy_segments",
                "low",
                segments=high_entropy_segs
            ))
        
        context.quality_issues = issues
        return context
```

---

### ⭐ 最终架构决策（DECISION）

#### Decision 5.1: 双轴质量系统（保持）

**决策**: ✅ **保持** Deterministic Gate + Evaluative Trend

**理由**: ADR-003定义，正确的架构

---

#### Decision 5.2: ConStory-Checker（必须采纳）

**决策**: ✅ **采纳** 19种错误类型检测器

**理由**: ConStory-Bench论文支撑，最系统的分类

**实施**:
- M1 Week 3: 定义19种类型
- M2 Week 10-11: 实现19个Checker
- M2 Week 12: 集成到QualityGateStage

**验收标准**:
- ✅ 19种类型全覆盖
- ✅ 检测准确率>80%（人工验证100样本）
- ✅ 误报率<10%

---

#### Decision 5.3: Perplexity检测（采纳）

**决策**: ✅ **采纳** Perplexity作为AI味检测补充

**理由**: Claude Book文章验证，比正则更准确

**实施**:
- M2 Week 11: 实现PerplexityGate
- 与正则检测结合（双重验证）

**验收标准**:
- ✅ 检测准确率>85%
- ✅ 与正则检测互补

---

#### Decision 5.4: 情感一致性（采纳）

**决策**: ✅ **采纳** 情感一致性检查

**理由**: SCORE论文量化证明（89.7%）

**实施**:
- M2 Week 11: EmotionalConsistencyChecker
- 集成到QualityGateStage

**验收标准**:
- ✅ 情感一致性>85%
- ✅ 覆盖常见情感转换

---

#### Decision 5.5: Token熵检测（采纳）

**决策**: ✅ **采纳** Token熵检测

**理由**: ConStory-Bench发现高熵区易错

**实施**: M2 Week 12，作为诊断信息（不阻断）

---

#### Decision 5.6: 中段加强检查（采纳）

**决策**: ✅ **采纳** 中段加强检查

**理由**: ConStory-Bench发现中段易错

**实施**: M2 Week 12，动态调整检查强度

---

#### Decision 5.7: 评分系统校准（M4后）

**决策**: ⚠️ **M3前不校准**，M4阶段建立金样集

**理由**:
- M3前优先确定性检查
- 金样集需要30章基线后建立
- Reader-sim/Commercial保持E2级（诊断）

---

## 📄 文档状态

**当前**: 第2部分完成  
**下一步**: 生成第3部分（Prompt系统、评分系统、总结）

---

**制定人**: Claude Opus 4.8  
**文档版本**: ADR v1.0 Part 2/3
