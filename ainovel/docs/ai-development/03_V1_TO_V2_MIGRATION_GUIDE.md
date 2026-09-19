# 从V1到V2的迁移指南 - ANovel项目

**版本**: v1.0  
**制定日期**: 2026-09-18  
**适用于**: AI辅助代码迁移  
**状态**: 完整  

---

## 📋 文档目的

本文档帮助AI理解ANovel V1的设计，识别可保留和需重构的部分，提供清晰的迁移路径。

**核心目标**:
1. 让AI理解V1的架构和设计理念
2. 识别V1的优点（保留）和问题（重构）
3. 提供具体的迁移路径和代码示例
4. 避免常见的迁移陷阱

---

## 🎯 V1架构概览

### V1核心设计理念

ANovel V1有3个核心设计，这些设计是**正确的**，V2要**保留**：

#### 1. State as Projection（状态即投影）✅

**理念**: Canon是唯一真实，State是从Canon投影出来的

```python
# V1实现（保留这个理念）
class StoryState:
    """从Canon投影出来的状态"""
    
    def __init__(self, canon: Canon, chapter_num: int):
        self.canon = canon
        self.chapter_num = chapter_num
        
        # 从Canon投影
        self._characters = self._project_characters()
        self._events = self._project_events()
    
    def _project_characters(self):
        """从事实投影出角色状态"""
        # 查询Canon中所有角色相关的事实
        facts = self.canon.query(fact_type="CharacterAttribute")
        # 投影成角色字典
        return self._build_character_dict(facts)
```

**V2保留**: ✅ 继续使用State as Projection

---

#### 2. Canon Commit Boundary（唯一写入口）✅

**理念**: 所有事实修改必须通过Mint提交，保证SSOT

```python
# V1实现（保留这个理念）
class MintExecutor:
    """Mint是写入Canon的唯一入口"""
    
    def execute(self, facts: List[Fact]):
        """原子提交一批事实"""
        # 1. 验证
        self._validate_facts(facts)
        
        # 2. 事务提交
        with self.canon.transaction():
            for fact in facts:
                self.canon.add_fact(fact)
        
        # 3. 通知
        self._notify_listeners()
```

**V2保留**: ✅ 继续使用Mint作为唯一写入口

---

#### 3. Registry Pattern（注册表模式）✅

**理念**: 使用注册表管理配置和扩展点

```python
# V1实现（保留这个模式）
class FactRegistry:
    """事实类型注册表"""
    
    _fact_types = {}
    
    @classmethod
    def register(cls, fact_type: str, fact_class: Type[Fact]):
        cls._fact_types[fact_type] = fact_class
    
    @classmethod
    def get(cls, fact_type: str) -> Type[Fact]:
        return cls._fact_types[fact_type]
```

**V2保留**: ✅ 继续使用Registry Pattern

---

### V1目录结构

```
AI-Novel-Runtime/
└── runtime/
    ├── canon/          # Canon事实系统 ✅ 保留
    │   ├── fact.py
    │   └── canon.py
    │
    ├── memory/         # State管理 ✅ 保留
    │   └── state.py
    │
    ├── mint/           # Mint提交 ✅ 保留
    │   └── mint_executor.py
    │
    ├── production/     # 生产流程 ⚠️ 重构
    │   └── chapter_producer.py  # 2907行单体函数
    │
    ├── qa/             # 质量系统 ⚠️ 扩展
    │   └── quality_judge.py
    │
    └── outline/        # 大纲系统 ✅ 保留
        └── outline.py
```

---

## ✅ V1优点总结（保留部分）

### 1. Canon系统设计正确

**优点**:
- Fact类设计合理
- 事实类型清晰（CharacterAttribute, Event, etc.）
- 查询接口完善

**V2保留**:
```python
# V1的Fact类（保留）
@dataclass
class Fact:
    fact_id: str
    fact_type: str
    content: Dict
    source_chapter: int
    metadata: Dict = field(default_factory=dict)
```

**V2增强**: 增加`validity_start`和`validity_end`字段

---

### 2. State管理设计正确

**优点**:
- State as Projection理念正确
- 投影逻辑清晰
- 时间感知（查询特定章节的状态）

**V2保留**: State的投影逻辑

**V2增强**: 支持Validity Interval

---

### 3. Mint系统设计正确

**优点**:
- 唯一写入口
- 事务支持
- 验证机制

**V2保留**: Mint作为唯一写入口

**V2修复**: 原子事务Bug（Decision 3.2）

---

### 4. Registry模式使用恰当

**优点**:
- FactRegistry管理事实类型
- 扩展性好

**V2保留**: Registry模式

**V2新增**: GenreRegistry（题材注册表）

---

### 5. 测试覆盖率高

**优点**:
- 405个测试
- 覆盖核心功能

**V2保留**: 所有测试，继续扩展

---

## ❌ V1问题总结（需重构部分）

### 问题1: 缺少Genre系统（最大问题）

**问题**: 题材只是字符串标签，无约束

```python
# V1做法（错误）
story_bible = StoryBible(
    genre="urban"  # 只是字符串，无任何约束
)

# 结果：都市小说生成修炼内容
```

**V2重构**: 实现Genre-First架构

```python
# V2做法（正确）
genre_config = GenreRegistry.get(GenreID.URBAN)
# 有完整的约束、进阶模型、Prompt模板

# 生成时自动验证约束
validator = GenreValidator(genre_config)
violations = validator.validate(chapter_text)
if violations:
    # 阻断生成
```

**迁移路径**:
1. 新建`runtime/genre/`模块
2. 实现GenreConfig, GenreConstraints, ProgressionModel
3. 修改Genesis流程，增加Genre检测
4. 所有生成都通过Genre验证

---

### 问题2: 缺少Validity Interval

**问题**: 无法区分"合法变化"vs"非法矛盾"

```python
# V1做法（问题）
# 章节5：陈阳是贫困大学生
fact1 = Fact(
    fact_type="CharacterAttribute",
    content={"character": "陈阳", "attribute": "财富", "value": "贫困"}
)

# 章节20：陈阳是富豪
fact2 = Fact(
    fact_type="CharacterAttribute",
    content={"character": "陈阳", "attribute": "财富", "value": "富豪"}
)

# V1会判定为矛盾，但这是合法的成长！
```

**V2重构**: 增加Validity Interval

```python
# V2做法（正确）
fact1 = Fact(
    fact_type="CharacterAttribute",
    content={"character": "陈阳", "attribute": "财富", "value": "贫困"},
    validity_start=5,
    validity_end=19  # 在第20章被supersede
)

fact2 = Fact(
    fact_type="CharacterAttribute",
    content={"character": "陈阳", "attribute": "财富", "value": "富豪"},
    validity_start=20,
    validity_end=None,  # 当前有效
    superseded_by=None,
    supersede_reason="财富增长（合法变化）"
)

# V2正确识别：这是合法变化，不是矛盾
```

**迁移路径**:
1. 扩展Fact数据结构（增加validity字段）
2. 修改矛盾检测逻辑（检查有效期重叠）
3. 更新State投影逻辑（只投影有效的事实）

---

### 问题3: 生产流程是单体函数

**问题**: `chapter_producer.py`有2907行，难以维护

```python
# V1做法（问题）
def produce_chapter(chapter_num, state):
    # 行1-200: 加载上下文
    # 行201-800: 生成初稿
    # 行801-1500: 质量检查
    # 行1501-2000: 修订
    # 行2001-2907: 提交
    
    # 2907行单体函数！
```

**V2重构**: Pipeline架构

```python
# V2做法（正确）
class ProductionPipeline:
    """生产管道"""
    
    def __init__(self):
        self.stages = [
            LoadContextStage(),
            GenerateDraftStage(),       # Draft A/B/C
            GenreValidationStage(),     # 题材验证
            QualityGateStage(),         # 质量检查
            DecisionStage(),            # 决策
            PersistStage()              # 持久化
        ]
    
    def execute(self, chapter_num):
        context = {}
        for stage in self.stages:
            context = stage.execute(context)
            if context.get("status") == "BLOCKED":
                break
        return context

# 每个Stage只有200-300行，清晰可维护
```

**迁移路径**:
1. 新建`runtime/production/pipeline.py`
2. 拆分2907行函数为7个Stage
3. 每个Stage独立测试
4. 逐步替换旧的produce_chapter

---

### 问题4: 质量系统未校准

**问题**: 评分系统直接用于决策，但未校准

```python
# V1做法（问题）
score = quality_judge.evaluate(chapter_text)
if score < 7.0:
    # 直接阻断，但评分可能不准
    return "BLOCKED"
```

**V2重构**: 双轨质量系统

```python
# V2做法（正确）
# 轨道1：Deterministic（决策用）
gate_result = deterministic_gate.check(chapter_text)
if gate_result.has_critical_violations():
    return "BLOCKED"  # 明确的错误，可以阻断

# 轨道2：Evaluative（趋势用）
score = evaluative_judge.evaluate(chapter_text)
log_score(score)  # 只记录趋势，不做决策
```

**迁移路径**:
1. 保留V1的quality_judge（作为Evaluative）
2. 新建Deterministic Gate（ConStory-Checker等）
3. 决策只用Deterministic结果
4. M4后校准Evaluative，再用于辅助决策

---

### 问题5: Mint有事务Bug

**问题**: 事务不完整，可能导致部分提交

```python
# V1做法（有Bug）
def execute(self, facts):
    # 问题：验证失败后，部分事实可能已经写入
    for fact in facts:
        self._validate_fact(fact)  # 可能抛异常
        self.canon.add_fact(fact)  # 已经写入
```

**V2修复**: 完整的原子事务

```python
# V2做法（正确）
def execute(self, facts):
    # 1. 先全部验证（不写入）
    for fact in facts:
        self._validate_fact(fact)
    
    # 2. 验证通过后，原子提交
    with self.canon.transaction():
        for fact in facts:
            self.canon.add_fact(fact)
    
    # 要么全部成功，要么全部回滚
```

**迁移路径**:
1. 修改MintExecutor.execute方法
2. 增加State Guards（防御性检查）
3. 添加回归测试（防止再次出现）

---

## 🔄 迁移路径图

### 总体策略：渐进式迁移

```
V1 (main分支)
  ↓
V2-refactor分支（当前）
  ↓
M1: Genre系统（新建）
  ↓
M1: Validity Interval（扩展V1）
  ↓
M2: Pipeline（重构V1）
  ↓
M2: 质量系统（扩展V1）
  ↓
M3: 集成测试
  ↓
Go/No-Go决策
```

---

### 迁移优先级

#### P0（M1，必须迁移）

1. **Genre系统**（新建）
   - 位置：`runtime/genre/`
   - 状态：V1无，V2新建
   - 工作量：6周

2. **Validity Interval**（扩展）
   - 位置：`runtime/canon/fact.py`
   - 状态：扩展Fact类
   - 工作量：2周

3. **修复Mint Bug**（修复）
   - 位置：`runtime/mint/mint_executor.py`
   - 状态：修复事务
   - 工作量：1周

#### P1（M2，重要迁移）

4. **Pipeline架构**（重构）
   - 位置：`runtime/production/`
   - 状态：拆分2907行
   - 工作量：3周

5. **质量系统**（扩展）
   - 位置：`runtime/qa/`
   - 状态：增加Deterministic
   - 工作量：3周

#### P2（M3，优化迁移）

6. **Snapshot**（新建）
   - 位置：`runtime/memory/snapshot.py`
   - 状态：V1无，V2新建
   - 工作量：1周

---

## 📝 具体迁移示例

### 示例1: 迁移Fact类（扩展）

#### V1代码（保留）

```python
# V1: runtime/canon/fact.py
@dataclass
class Fact:
    """事实
    
    Attributes:
        fact_id: 唯一标识
        fact_type: 事实类型
        content: 事实内容
        source_chapter: 来源章节
    """
    fact_id: str
    fact_type: str
    content: Dict
    source_chapter: int
    metadata: Dict = field(default_factory=dict)
```

#### V2代码（扩展）

```python
# V2: runtime/canon/fact.py（扩展V1）
@dataclass
class Fact:
    """事实（V2扩展：增加Validity Interval）
    
    Attributes:
        fact_id: 唯一标识
        fact_type: 事实类型
        content: 事实内容
        source_chapter: 来源章节
        validity_start: 有效期起始章节（新增）
        validity_end: 有效期结束章节（新增）
        superseded_by: 被哪个事实替代（新增）
        supersede_reason: 替代原因（新增）
    """
    fact_id: str
    fact_type: str
    content: Dict
    source_chapter: int
    metadata: Dict = field(default_factory=dict)
    
    # ✅ V2新增字段
    validity_start: int = field(default=None)
    validity_end: Optional[int] = field(default=None)
    superseded_by: Optional[str] = field(default=None)
    supersede_reason: str = field(default="")
    
    def __post_init__(self):
        # 向后兼容：V1事实没有validity字段
        if self.validity_start is None:
            self.validity_start = self.source_chapter
    
    def is_valid_at(self, chapter_num: int) -> bool:
        """检查事实在指定章节是否有效（V2新增）"""
        if chapter_num < self.validity_start:
            return False
        if self.validity_end is not None and chapter_num > self.validity_end:
            return False
        return True
```

#### 迁移步骤

1. **兼容性**: 新增字段有默认值，V1代码仍可运行
2. **测试**: 添加`test_is_valid_at`测试
3. **逐步迁移**: 新事实使用validity字段，旧事实自动兼容

---

### 示例2: 迁移produce_chapter（重构）

#### V1代码（2907行单体，需拆分）

```python
# V1: runtime/production/chapter_producer.py
def produce_chapter(chapter_num: int, state: StoryState) -> Dict:
    """生产章节（2907行单体函数）"""
    
    # === 部分1: 加载上下文（200行）===
    outline = load_outline()
    task_package = outline.get_chapter(chapter_num)
    context = {
        "chapter_num": chapter_num,
        "task_package": task_package,
        "state": state
    }
    
    # === 部分2: 生成初稿（600行）===
    prompt = build_prompt(context)
    draft_text = llm.generate(prompt)
    
    # === 部分3: 质量检查（700行）===
    quality_result = quality_judge.evaluate(draft_text)
    if quality_result.score < 7.0:
        # 修订逻辑（500行）
        ...
    
    # === 部分4: 提交（700行）===
    facts = extract_facts(draft_text)
    mint.execute(facts)
    
    # ... 总共2907行
    
    return result
```

#### V2代码（Pipeline，每个Stage 200-300行）

```python
# V2: runtime/production/pipeline.py
class ProductionPipeline:
    """生产管道（拆分为多个Stage）"""
    
    def __init__(self):
        self.stages = [
            LoadContextStage(),      # ~200行
            GenerateDraftStage(),    # ~300行
            GenreValidationStage(),  # ~200行
            QualityGateStage(),      # ~300行
            DecisionStage(),         # ~150行
            PersistStage()           # ~200行
        ]
    
    def execute(self, chapter_num: int, state: StoryState) -> ProductionResult:
        """执行生产管道"""
        context = ProductionContext(
            chapter_num=chapter_num,
            state=state
        )
        
        for stage in self.stages:
            context = stage.execute(context)
            
            # 检查是否需要提前终止
            if context.status == StageStatus.BLOCKED:
                logger.warning(f"Pipeline blocked at {stage.name}")
                break
        
        return ProductionResult(
            status=context.status,
            chapter_text=context.get("chapter_text"),
            metadata=context.metadata
        )

# V2: runtime/production/stages/load_context_stage.py
class LoadContextStage(PipelineStage):
    """加载上下文Stage（~200行）"""
    
    def execute(self, context: ProductionContext) -> ProductionContext:
        """加载生产所需的上下文"""
        outline = self._load_outline()
        task_package = outline.get_chapter(context.chapter_num)
        
        context.set("outline", outline)
        context.set("task_package", task_package)
        context.set_status(StageStatus.SUCCESS)
        
        return context
```

#### 迁移步骤

1. **保留V1**: 保留`produce_chapter`函数（作为备份）
2. **逐步拆分**: 
   - Week 1: 实现Pipeline框架
   - Week 2: 实现前3个Stage
   - Week 3: 实现后3个Stage
3. **并行运行**: V2 Pipeline和V1 produce_chapter并行，对比结果
4. **切换**: 验证通过后，切换到V2 Pipeline
5. **删除V1**: 确认稳定后，删除V1代码

---

### 示例3: 新建Genre系统（从零开始）

#### V1状态（无）

V1没有Genre系统，直接新建

#### V2代码（新建）

```python
# V2: runtime/genre/config.py（全新模块）
@dataclass
class GenreConfig:
    """题材配置（V2新建）"""
    genre_id: GenreID
    genre_name: str
    constraints: GenreConstraints
    progression_model: Type[ProgressionModel]
    prompt_templates: Dict[str, str]

# V2: runtime/genre/registry.py（全新模块）
class GenreRegistry(Singleton):
    """题材注册表（V2新建）"""
    
    def register(self, config: GenreConfig):
        """注册题材配置"""
        self._configs[config.genre_id] = config

# 注册都市题材
urban_config = GenreConfig(
    genre_id=GenreID.URBAN,
    genre_name="都市",
    constraints=UrbanConstraints(),
    progression_model=WealthProgressionModel,
    prompt_templates={
        "outline": URBAN_OUTLINE_PROMPT,
        "chapter": URBAN_CHAPTER_PROMPT
    }
)
GenreRegistry().register(urban_config)
```

#### 迁移步骤

1. **新建目录**: `runtime/genre/`
2. **实现核心类**: GenreConfig, GenreConstraints, ProgressionModel
3. **实现Registry**: GenreRegistry
4. **定义配置**: UrbanConfig, XuanhuanConfig
5. **集成Genesis**: Genesis流程增加Genre检测
6. **集成生产**: 生产流程增加Genre验证

---

## ⚠️ 常见迁移陷阱

### 陷阱1: 破坏V1的核心设计

```python
# ❌ 错误：破坏State as Projection
# 不要让State可修改
class StoryState:
    def set_character_age(self, age):
        self.characters["protagonist"].age = age  # ❌ 错误！

# ✅ 正确：保持State as Projection
# State是只读的，修改必须通过Mint
def update_character_age(age):
    fact = Fact(...)  # 创建事实
    mint.execute([fact])  # 通过Mint提交
    state = state.rebuild()  # 重新投影
```

---

### 陷阱2: 一次性大规模重写

```python
# ❌ 错误：一次性重写所有代码
# 删除V1的2907行，重写Pipeline
# 风险：可能破坏现有功能

# ✅ 正确：渐进式迁移
# 1. 保留V1代码
# 2. 并行实现V2
# 3. 对比验证
# 4. 逐步切换
# 5. 确认稳定后删除V1
```

---

### 陷阱3: 忽略向后兼容

```python
# ❌ 错误：修改Fact类，破坏现有数据
@dataclass
class Fact:
    fact_id: str
    validity_start: int  # 必需字段，旧数据无此字段

# ✅ 正确：保持向后兼容
@dataclass
class Fact:
    fact_id: str
    validity_start: int = field(default=None)  # 可选，有默认值
    
    def __post_init__(self):
        if self.validity_start is None:
            self.validity_start = self.source_chapter  # 自动填充
```

---

### 陷阱4: 没有迁移测试

```python
# ❌ 错误：没有测试，直接迁移

# ✅ 正确：编写迁移测试
def test_v1_to_v2_fact_migration():
    """测试V1事实可以在V2中使用"""
    # V1格式的事实
    v1_fact = Fact(
        fact_id="test",
        fact_type="CharacterAttribute",
        content={},
        source_chapter=5
        # 没有validity字段
    )
    
    # V2应该能处理
    assert v1_fact.is_valid_at(5) == True
    assert v1_fact.validity_start == 5  # 自动填充
```

---

## ✅ 迁移检查清单

### 开始迁移前

- [ ] 阅读V1代码，理解核心设计
- [ ] 识别可保留的部分（State/Canon/Mint）
- [ ] 识别需重构的部分（Production/QA）
- [ ] 制定迁移计划（分阶段，可回退）
- [ ] 创建v2-refactor分支

### 迁移过程中

- [ ] 保留V1代码（不删除）
- [ ] V2代码独立测试
- [ ] V1和V2并行运行（对比结果）
- [ ] 保持向后兼容（旧数据可用）
- [ ] 每个阶段提交Git

### 迁移完成后

- [ ] 所有V1测试在V2中通过
- [ ] V2新增测试覆盖新功能
- [ ] 性能不低于V1
- [ ] 文档更新
- [ ] 删除V1代码（确认稳定后）

---

## 📊 迁移进度跟踪

### M1阶段迁移

| 模块 | V1状态 | V2目标 | 迁移方式 | 进度 |
|------|--------|--------|----------|------|
| Genre系统 | 无 | 新建 | 从零开始 | 0% |
| Validity Interval | 无 | 扩展Fact | 扩展V1 | 0% |
| Mint事务 | 有Bug | 修复 | 修复V1 | 0% |
| State Guards | 无 | 新增 | 扩展V1 | 0% |

### M2阶段迁移

| 模块 | V1状态 | V2目标 | 迁移方式 | 进度 |
|------|--------|--------|----------|------|
| Pipeline | 2907行单体 | 7个Stage | 重构V1 | 0% |
| Draft A/B/C | 无 | 新增 | 新建 | 0% |
| ConStory-Checker | 无 | 新增 | 新建 | 0% |
| Temporal RAG | 无 | 新增 | 新建 | 0% |

---

## 🔗 相关文档

### 必读
1. [AI辅助开发指南](./01_AI_ASSISTED_DEVELOPMENT_GUIDE.md)
2. [代码规范与模板](./02_CODE_STANDARDS_AND_TEMPLATES.md)
3. [架构决策记录](../architecture-decisions/12_ARCHITECTURE_DECISION_RECORD_PART1.md)

### 实施指南（即将生成）
1. Genre系统完整实施手册
2. Validity Interval实施手册
3. Pipeline架构实施手册

---

## 💡 AI迁移提示词模板

### 模板1: 扩展现有类

```
请扩展V1的{类名}，增加{新功能}：

1. 查阅V1代码：
   - 位置：{文件路径}
   - 理解当前实现

2. V2扩展要求：
   - 保持V1的所有功能（向后兼容）
   - 增加{新字段列表}
   - 增加{新方法列表}
   - 新字段必须有默认值（兼容旧数据）

3. 输出：
   - V2完整代码
   - 迁移说明（如何处理旧数据）
   - 测试代码（验证兼容性）
```

### 模板2: 重构大函数

```
请将V1的{函数名}（{行数}行）重构为Pipeline：

1. 分析V1代码：
   - 位置：{文件路径}
   - 识别逻辑分段

2. 拆分为Stage：
   - Stage 1: {功能}（约{行数}行）
   - Stage 2: {功能}（约{行数}行）
   - ...

3. 输出：
   - Pipeline框架代码
   - 各Stage实现代码
   - 迁移测试（V1结果 == V2结果）
```

---

**制定人**: Claude Opus 4.8  
**文档版本**: v1.0  
**最后更新**: 2026-09-18  
**状态**: ✅ 完整
