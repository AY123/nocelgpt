# ANovel 战略重构路线图

**版本**: v1.0  
**制定日期**: 2026-09-18  
**实施周期**: 3-6 个月  
**决策点**: M3（3 个月后 Go/No-Go）  

---

## 一、重构策略总览

### 1.1 核心原则

**保留-重构-删除（40%-30%-30%）**:
- **保留 40%**: 工程基础扎实，可直接复用
- **重构 30%**: 思路正确但实现有问题，需要改造
- **删除 30%**: 未接线、未校准、重复的模块

**渐进式重构，保持测试绿色**:
- 每个阶段都有明确的验收标准
- 不允许测试长期红色
- 每 2 周一个可见成果

**从核心问题开始，由内向外**:
```
题材系统（P0）
  ↓
生产编排（P1）
  ↓
单章质量（P1）
  ↓
30 章基线（P1）
  ↓
商业验证（P2）
```

### 1.2 三大阶段

| 阶段 | 时间 | 核心目标 | 里程碑 |
|------|------|----------|--------|
| **Phase 1: 题材系统重构** | Month 1 | Genre 作为一等公民 | M1: 题材隔离证明 |
| **Phase 2: 生产流程优化** | Month 2 | 解耦编排，收口质量 | M2: 单章质量及格 |
| **Phase 3: 产品基线建立** | Month 3 | 30 章完整生产 | M3: 人工验证通过 |

---

## 二、Phase 1: 题材系统重构（Month 1）

### 目标

让 Genre 成为真正的领域模型，修复"都市写成奇幻"的架构缺陷。

### Week 1-2: Genre 核心重构

#### Day 1-2: 数据结构定义

**任务**:
```
1. 定义 GenreConfig（题材配置）
2. 定义 GenreConstraints（硬约束）
3. 定义 GenreProgressionModel（抽象基类）
4. 创建 GenreRegistry（注册表）
```

**产出**:
```
runtime/genre/
├── __init__.py
├── core.py              # 核心数据结构
├── constraints.py       # 约束定义
├── progression.py       # 进阶模型抽象
└── registry.py          # 注册表
```

**验收**:
- ✅ 所有数据结构有完整类型注解
- ✅ 每个类有 docstring 说明
- ✅ 单元测试覆盖基础功能

#### Day 3-4: 具体进阶模型实现

**任务**:
```
1. PowerProgressionModel（玄幻/奇幻）
2. WealthProgressionModel（都市）
3. TechProgressionModel（科幻）
```

**产出**:
```
runtime/genre/
├── progression/
│   ├── __init__.py
│   ├── power.py         # 力量进阶
│   ├── wealth.py        # 财富进阶
│   └── tech.py          # 科技进阶
```

**验收**:
- ✅ 每个模型有 8+ 等级定义
- ✅ validate_transition() 逻辑正确
- ✅ 单元测试覆盖晋级验证

#### Day 5: 都市题材完整配置

**任务**:
```
1. 定义都市约束（allowed/forbidden elements）
2. 创建都市关键词检测器
3. 注册都市题材到 GenreRegistry
```

**产出**:
```
runtime/genre/configs/
├── __init__.py
└── urban.py             # 都市题材完整配置
```

**验收**:
- ✅ 约束列表包含 20+ 正向关键词，10+ 负向关键词
- ✅ GenreRegistry.get("urban") 返回完整配置
- ✅ 关键词检测器单元测试通过

### Week 3: Genesis 流程题材感知改造

#### Day 1-2: 题材检测系统

**任务**:
```
1. 实现 KeywordDetector
2. 实现 GenreRegistry.detect_from_references()
3. 准备 10+ 测试用例
```

**测试用例**:
```python
# 都市题材
["我真没想重生啊", "主角重生回到2006年"] → "urban"
["重生之财源滚滚", "利用重生优势炒股"] → "urban"

# 玄幻题材
["斗破苍穹", "废材少年被退婚"] → "xuanhuan"
["武动乾坤", "符石炼体"] → "xuanhuan"

# 混淆案例
["重生之都市修仙"] → ?（需要人工确认）
```

**验收**:
- ✅ 题材检测准确率 > 90%（至少 10 个测试用例）
- ✅ 混淆案例能够识别并标记置信度低

#### Day 3: 题材感知的 Genesis

**任务**:
```
1. 修改 run_genesis() 支持题材检测
2. 题材配置注入到分析流程
3. 约束验证集成
```

**关键改动**:
```python
def run_genesis_v2(project_path, genre_override=None):
    # 1. 检测或指定题材
    genre_id = genre_override or GenreRegistry.detect_from_references(...)
    
    # 2. 加载题材配置
    genre_config = GenreRegistry.get(genre_id)
    
    # 3. 使用题材专用分析器
    analyzer = genre_config.reference_analyzer
    
    # 4. 使用题材专用 Prompt 模板
    template = genre_config.prompt_templates["outline"]
    
    # 5. 生成大纲（注入约束）
    outline = generate_outline(template, genre_config.constraints)
    
    # 6. 验证约束
    violations = GenreRegistry.validate_constraints(genre_id, outline)
    if violations:
        raise GenreViolationError(violations)
```

**验收**:
- ✅ 都市参考 → 生成都市大纲
- ✅ 玄幻参考 → 生成玄幻大纲
- ✅ 约束违反能够阻断 Genesis

#### Day 4-5: 玄幻题材完整配置

**任务**:
```
1. 定义玄幻约束
2. 创建玄幻关键词检测器
3. 注册玄幻题材
```

**产出**:
```
runtime/genre/configs/
└── xuanhuan.py          # 玄幻题材完整配置
```

**验收**:
- ✅ 玄幻约束与都市约束互斥
- ✅ GenreRegistry.get("xuanhuan") 返回完整配置

### Week 4: 题材隔离测试与验证

#### 题材隔离测试套件

**核心测试**:
```python
# tests/test_genre_isolation.py

def test_urban_cannot_generate_cultivation():
    """都市题材不能生成修炼内容（5 个测试用例）"""
    
    test_cases = [
        {
            "reference": "我真没想重生啊",
            "forbidden": ["灵气", "修炼", "境界", "突破"],
            "required": ["公司", "创业", "职场"]
        },
        {
            "reference": "重生之财源滚滚",
            "forbidden": ["丹药", "法宝", "宗门"],
            "required": ["股票", "投资", "商业"]
        },
        # ... 3 more cases
    ]
    
    for case in test_cases:
        outline = run_genesis_v2(case["reference"], genre_override="urban")
        
        # 验证禁止元素
        for forbidden in case["forbidden"]:
            assert forbidden not in outline, \
                f"都市大纲出现禁止元素: {forbidden}"
        
        # 验证必需元素
        for required in case["required"]:
            assert required in outline, \
                f"都市大纲缺少必需元素: {required}"

def test_xuanhuan_cannot_generate_modern_business():
    """玄幻题材不能生成现代商业内容（5 个测试用例）"""
    # 类似结构
```

**验收标准**:
- ✅ 都市题材 5 个测试用例全部通过
- ✅ 玄幻题材 5 个测试用例全部通过
- ✅ 题材检测准确率 > 90%

#### 集成测试

**端到端测试**:
```python
def test_urban_genesis_end_to_end():
    """都市题材端到端测试"""
    
    # 1. 准备参考
    references = ["我真没想重生啊"]
    
    # 2. 运行 Genesis
    outline = run_genesis_v2(references)
    
    # 3. 验证题材正确
    assert outline.genre == "urban"
    
    # 4. 验证进阶模型
    assert isinstance(outline.progression, WealthProgressionModel)
    assert "打工仔" in outline.progression.tiers
    assert "炼气期" not in outline.progression.tiers
    
    # 5. 验证约束
    violations = validate_genre_constraints("urban", outline.content)
    assert len(violations) == 0, f"发现约束违反: {violations}"
```

### M1 里程碑验收（Month 1 结束）

**必须通过的检查**:

✅ **数据结构**:
- [ ] GenreConfig、GenreConstraints、ProgressionModel 完整实现
- [ ] Power/Wealth/Tech 三个具体模型可用

✅ **注册表**:
- [ ] GenreRegistry 可注册、查询、检测
- [ ] 都市、玄幻两个完整配置已注册

✅ **检测准确率**:
- [ ] 题材检测准确率 > 90%（至少 10 个测试用例）

✅ **约束验证**:
- [ ] 都市题材 5 个测试用例：不生成修炼内容
- [ ] 玄幻题材 5 个测试用例：不生成现代商业

✅ **Prompt 模板**:
- [ ] 都市、玄幻各有专用 outline 模板
- [ ] 约束自动注入到 prompt

✅ **集成测试**:
- [ ] 都市参考 → 都市大纲（端到端测试通过）
- [ ] 玄幻参考 → 玄幻大纲（端到端测试通过）

**Go/No-Go**:
- ✅ 如果通过 → 进入 Phase 2
- ❌ 如果失败 → 延长 Phase 1，修复问题后再验收

---

## 三、Phase 2: 生产流程优化（Month 2）

### 目标

解耦生产编排，收口单章质量硬伤。

### Week 5-6: Production Pipeline 重构

#### 当前问题

`serialize/loop.py` 2907 行，高度耦合：
```python
# ❌ 当前方式
def produce_chapter(chapter_num):
    # 生成
    draft = generate(...)
    
    # 检查 1
    if quality_check(draft):
        ...
    
    # 检查 2
    if genre_check(draft):
        ...
    
    # 检查 3
    if contract_check(draft):
        ...
    
    # ... 每新增检查器都要修改主流程
```

#### 解决方案：Pipeline 模式

**核心设计**:
```python
# ✅ 新方式
class ProductionStage(ABC):
    @abstractmethod
    def execute(self, ctx: ChapterContext) -> ChapterContext:
        """执行阶段"""
        pass
    
    @abstractmethod
    def should_block(self, ctx: ChapterContext) -> bool:
        """是否阻断后续生产"""
        return False

class ProductionPipeline:
    def __init__(self, stages: List[ProductionStage]):
        self.stages = stages
    
    def run(self, ctx: ChapterContext) -> ChapterContext:
        for stage in self.stages:
            ctx = stage.execute(ctx)
            if stage.should_block(ctx):
                ctx.should_continue = False
                return ctx
        return ctx

# 使用
pipeline = ProductionPipeline([
    LoadContextStage(),
    GenerateDraftStage(),
    GenreValidationStage(),      # 题材硬约束（必须阻断）
    QualityGateStage(),           # 质量门禁（确定性检查阻断）
    CommercialOptimizationStage(), # 可选优化（不阻断）
    DecisionStage(),              # 生产决策
    PersistStage()                # 持久化
])
```

**Day 1-2**: Stage 抽象与核心 Stages
**Day 3-4**: 迁移现有检查器到 Stage
**Day 5**: Pipeline 集成测试

**验收**:
- ✅ 主流程从 2907 行降低到 < 500 行
- ✅ 新增 Stage 不需要修改主流程
- ✅ BLOCKED 状态真正阻断后续章节

### Week 7-8: 单章质量硬伤修复

#### 当前问题

根据审计报告，单章存在 4 大硬伤：
1. **AI 味道重**：明显的 AI 腔调
2. **长度失控**：目标 3000-5000 字，实际经常超标
3. **角色同声**：所有角色说话风格一样
4. **钩子弱**：前 3 章不够抓人

#### 修复方案

**1. AI 味道检测与改写**

```python
# AI 味道特征
AI_TASTE_PATTERNS = [
    r"如同.*一般",
    r"仿佛.*般",
    r"不禁.*起来",
    r"内心深处",
    r"波澜起伏",
    r"若有所思",
    # ... 更多模式
]

def detect_ai_taste(text: str) -> List[AiTasteViolation]:
    violations = []
    for pattern in AI_TASTE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            violations.append({
                "pattern": pattern,
                "matches": matches,
                "severity": "high"
            })
    return violations

def rewrite_ai_taste(text: str, violations: List) -> str:
    # 针对性改写
    pass
```

**2. 长度控制**

```python
def enforce_length_constraint(draft: str, target: int = 4000, tolerance: int = 500) -> str:
    word_count = len(draft)
    
    if word_count < target - tolerance:
        # 扩展
        return expand_draft(draft, target_words=target)
    elif word_count > target + tolerance:
        # 压缩
        return compress_draft(draft, target_words=target)
    else:
        return draft
```

**3. 角色声音差异化**

```python
class CharacterVoiceProfile:
    character_id: str
    speaking_style: str      # 简洁/啰嗦/文雅/粗俗
    vocabulary_level: str    # 文言/书面/口语/方言
    emotion_tendency: str    # 冷静/激动/幽默/严肃
    
def inject_voice_profile(dialogue: str, character: Character) -> str:
    profile = get_voice_profile(character)
    # 根据 profile 调整对话风格
    pass
```

**4. 钩子强化（前 3 章）**

```python
HOOK_STRATEGIES = {
    1: "identity_crisis",     # 身份危机（重生/穿越）
    2: "conflict_escalation", # 冲突升级
    3: "reveal_power"         # 展现金手指
}

def enhance_chapter_hook(chapter_num: int, draft: str) -> str:
    if chapter_num > 3:
        return draft  # 只强化前 3 章
    
    strategy = HOOK_STRATEGIES[chapter_num]
    return apply_hook_strategy(draft, strategy)
```

**验收**:
- ✅ AI 味道检测准确率 > 80%
- ✅ 章节长度 95% 落在 3000-5000 字区间
- ✅ 同一章节中不同角色对话可区分
- ✅ 前 3 章钩子强度提升（人工评估）

### M2 里程碑验收（Month 2 结束）

✅ **Pipeline 重构**:
- [ ] ProductionStage 抽象完成
- [ ] Genre/Quality/Decision 三大 Stage 实现
- [ ] 主流程代码量降低 > 80%

✅ **BLOCKED 语义修复**:
- [ ] BLOCKED 状态真正阻断后续章节
- [ ] 集成测试验证阻断行为

✅ **单章质量**:
- [ ] AI 味道检测器上线
- [ ] 长度控制有效率 > 95%
- [ ] 角色声音差异化可检测
- [ ] 前 3 章钩子强化完成

**Go/No-Go**:
- ✅ 如果通过 → 进入 Phase 3
- ❌ 如果失败 → 延长 Phase 2

---

## 四、Phase 3: 30 章基线建立（Month 3）

### 目标

冻结配置，跑满 30 章，建立第一个可验证的产品基线。

### Week 9-10: 完整生产运行

#### 冻结配置

**锁定以下配置**:
```yaml
# baseline-config.yaml
baseline_name: "v1.0-30ch-baseline"
locked_at: "2026-12-18"

genre: "urban"  # 先验证都市
prompt_version: "urban_outline_v1"
model: "deepseek-v3"
quality_gate: "deterministic_only"  # 只用确定性检查
commercial_optimization: false      # 暂时关闭

target_chapters: 30
chapter_length: 4000  # ±500
```

#### 生产运行

**Day 1-3**: 都市重生 30 章
```bash
# 准备参考
references: ["我真没想重生啊", "重生之财源滚滚"]

# 运行生产
python -m runtime.cli genesis --genre urban --references refs.txt
python -m runtime.cli serial run --chapters 30 --config baseline-config.yaml

# 生成产物
├── registry/facts/          # 事实库
├── registry/derived/        # 衍生物
│   ├── drafts/ch001.yaml   # 草稿
│   ├── drafts/ch002.yaml
│   └── ...
└── production-manifest.json # 生产清单
```

**Day 4-5**: 玄幻废材流 30 章
```bash
references: ["斗破苍穹", "武动乾坤"]

python -m runtime.cli genesis --genre xuanhuan --references refs.txt
python -m runtime.cli serial run --chapters 30 --config baseline-config.yaml
```

**验收**:
- ✅ 都市 30 章完整生产（无中断）
- ✅ 玄幻 30 章完整生产（无中断）
- ✅ 每章都有完整 Provenance
- ✅ 题材隔离测试通过（都市无修炼，玄幻无商业）

### Week 11-12: 人工盲评验证

#### 黄金三章盲评（抓人度）

**评估维度**:
- 开局吸引力（1-10 分）
- 冲突设置（1-10 分）
- 钩子强度（1-10 分）
- 愿意继续读（是/否）

**评估员**:
- 3 名真实网文读者
- 盲评（不知道是 AI 生成）

**通过标准**:
- 平均分 > 7/10
- "愿意继续读" > 60%

#### 前十章留存度

**评估维度**:
- 情节推进（1-10 分）
- 角色吸引力（1-10 分）
- 冲突升级（1-10 分）
- 愿意追更（是/否）

**通过标准**:
- 平均分 > 6/10
- "愿意追更" > 50%

#### 30 章完整性复盘

**人工检查清单**:
- [ ] 0 个重大题材违规（都市出现修炼）
- [ ] 0 个主要角色身份漂移
- [ ] 0 个重大时间线冲突
- [ ] 0 个不可解释的设定崩坏
- [ ] 主线连贯（有开始、发展、阶段性高潮）
- [ ] 角色成长可追踪（财富/地位晋级合理）

### M3 里程碑验收（Month 3 结束）- Go/No-Go 决策点

**关键指标**:

✅ **生产完整性**:
- [ ] 都市重生 30 章完整生产
- [ ] 玄幻废材流 30 章完整生产
- [ ] 题材隔离测试通过（0 题材污染）

✅ **人工盲评**:
- [ ] 前 3 章盲评 > 7/10 分
- [ ] 前 10 章留存度 > 6/10 分
- [ ] 30 章完整性复盘通过（0 重大缺陷）

✅ **技术指标**:
- [ ] 每章有完整 Provenance
- [ ] 生产可中断、可恢复
- [ ] BLOCKED 状态正确阻断

**决策**:

✅ **如果 M3 通过**:
→ 进入 Phase 4-6（Month 4-6）
- 建立人工金样集（50+ 样本）
- 校准评分系统（与金样集对齐）
- 验证自动修订净收益（A/B 测试）
- 100 章长线规划

❌ **如果 M3 不通过**:
→ 回到问题定位
- 分析失败原因（题材？质量？流程？）
- 针对性修复
- 重新验证
- **不继续扩张**（不做 100 章、不做新题材）

---

## 五、Phase 4-6: 商业验证（Month 4-6）

### 仅在 M3 通过后执行

### Month 4: 金样集与评分校准

**目标**: 建立人工金样集，校准 AI 评分系统

**Week 13-14**: 金样集建立
- 50+ 章节样本
- 双盲评分（2 名评估员）
- 一致性检查与仲裁

**Week 15-16**: 评分系统校准
- AI 评分 vs 人工评分对齐
- 计算相关性系数
- 调整评分模型

**验收**:
- ✅ AI 评分与人工评分相关性 > 0.7
- ✅ 评分系统从"诊断级"升级为"参考级"

### Month 5: 自动修订净收益验证

**目标**: 证明自动修订真的改善质量

**A/B 测试设计**:
- **Group A**: 原稿
- **Group B**: 自动修订
- **Group C**: 人工修订（对照组）

**评估方式**: 盲评（评估员不知道哪个是哪个）

**通过标准**:
- 自动修订胜率 > 50%（vs 原稿）
- 自动修订接近人工修订（差距 < 20%）

### Month 6: 100 章长线规划

**目标**: 验证长篇连续性

**Long-arc Plan**:
- 每 10 章一个小高潮
- 每 30 章一个阶段性目标
- 100 章整体弧线

**验收**:
- ✅ 100 章无系统性重复
- ✅ 角色成长可追踪
- ✅ 无重大设定崩坏

---

## 六、风险缓解措施

### 范围蔓延风险

**症状**: 重构过程中忍不住添加新功能

**缓解**:
- 严格遵守"保留-重构-删除"清单
- M3 前禁止添加新模块
- Code Review 拒绝 scope creep

### 测试回归风险

**症状**: 重构破坏现有测试

**缓解**:
- 每个 Stage 保持测试绿色
- 回归测试自动运行
- 红色测试必须当天修复

### 完美主义陷阱

**症状**: 重构永远"还差一点"

**缓解**:
- 3 个月硬截止
- M3 是 Go/No-Go 决策点，不是"再给一个月"
- 60 分 > 0 分，先跑起来再优化

### 团队疲劳

**症状**: 长期重构没有正反馈

**缓解**:
- 每 2 周一个可见成果
- 里程碑庆祝
- 透明进度跟踪

---

## 七、进度跟踪

### 每周检查点

**每周五下午**:
- 本周完成情况
- 下周任务分配
- 风险识别与缓解

### 每月里程碑

**Month 1 结束**: M1 验收会议（Go/No-Go）
**Month 2 结束**: M2 验收会议（Go/No-Go）
**Month 3 结束**: M3 验收会议（重大 Go/No-Go 决策点）

### 进度仪表盘

```
Week 1:  ████░░░░░░░░ 33% - Genre 核心重构进行中
Week 2:  ████████░░░░ 67% - 进阶模型实现完成
Week 3:  ████████████ 100% - Genesis 改造完成
Week 4:  ████████████ M1 - 题材隔离验证通过 ✅

Week 5:  ████░░░░░░░░ 33% - Pipeline 重构进行中
...
```

---

## 八、成功标准总结

### M1（1 个月）

- ✅ 题材检测准确率 > 90%
- ✅ 都市不生成修炼（5 个测试用例）
- ✅ 玄幻不生成商业（5 个测试用例）

### M2（2 个月）

- ✅ Pipeline 解耦完成
- ✅ BLOCKED 正确阻断
- ✅ 单章质量硬伤修复

### M3（3 个月）- 关键决策点

- ✅ 30 章完整生产（都市 + 玄幻）
- ✅ 前 3 章盲评 > 7/10
- ✅ 30 章完整性复盘通过

**M3 通过 = 继续投入**
**M3 不通过 = 暂停扩张，重新诊断**

---

**制定人**: Claude Opus 4.8  
**下一步**: 生成详细的保留-重构-删除清单
