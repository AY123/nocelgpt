# P0-02 评审系统现状诊断报告

**分析时间**: 2026-09-01  
**分析范围**: 评审系统架构、实现、调用链、问题根源  
**分析方法**: 代码追踪 + 架构分析 + 改进方案设计

---

## 一、评审系统架构全貌

### 1.1 调用链路图

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 入口层 (CLI & Serial Production)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  cli.py::run_serial()                                                     │
│       │                                                                   │
│       ├─ --reviewer=llm-quality → _make_reviewer() → LLMQualityJudge    │
│       ├─ --reviewer=panel → build_review_panel()                         │
│       └─ (默认) → reviewer=None                                           │
│              ↓                                                            │
│  serialize/loop.py::run_serial(reviewer=None)                             │
│       │                                                                   │
│       └─ ChapterProductionOrchestrator(                                   │
│              reviewer=ChapterReviewer()  ← **硬编码，忽略传入参数**        │
│          )                                                                │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 编排层 (ChapterProductionOrchestrator)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  runtime/chapter/orchestrator.py                                          │
│                                                                           │
│  @dataclass                                                               │
│  class ChapterProductionOrchestrator:                                     │
│      writer: DraftWriter                                                  │
│      reviewer: ChapterReviewer  ← **类型注解限制为ChapterReviewer**       │
│      reviser: RevisionEngine                                              │
│      finalizer: Finalizer                                                 │
│                                                                           │
│  硬编码实例化: serialize/loop.py:217                                       │
│      chapter_pipeline = ChapterProductionOrchestrator(                    │
│          reviewer=ChapterReviewer(),  ← **总是这个**                       │
│          ...                                                              │
│      )                                                                    │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 实现层 (三个Reviewer实现)                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│ ┌──────────────────┐  ┌─────────────────────┐  ┌───────────────────┐   │
│ │ ChapterReviewer  │  │ LLMQualityJudge     │  │ PlaceholderReviewer│  │
│ │ (chapter/)       │  │ (execution/         │  │ (execution/        │  │
│ │                  │  │  quality_center)    │  │  draft_review)     │  │
│ ├──────────────────┤  ├─────────────────────┤  ├───────────────────┤   │
│ │ 实现: 45行        │  │ 实现: 471行          │  │ 实现: 空           │  │
│ │ 逻辑: 固定0.7分   │  │ 逻辑: LLM 18维打分   │  │ 逻辑: 占位         │  │
│ │ 状态: ✅ 默认使用  │  │ 状态: ⚠️ CLI可用但   │  │ 状态: ✅ 协议定义  │  │
│ │                  │  │      serial未接入    │  │                   │  │
│ └──────────────────┘  └─────────────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 协议层次

```python
# 协议定义 (execution/draft_review.py)
class DraftReviewer(Protocol):
    reviewer_id: str
    def review(self, artifact: dict, package: dict, 
               grounding: dict | None = None) -> ReviewReport:
        ...

# 三个实现:
# 1. ChapterReviewer - 简单实现，固定分数
# 2. LLMQualityJudge - 完整实现，LLM调用
# 3. PlaceholderReviewer - 空实现，占位
```

---

## 二、问题根源分析

### 问题1: 硬编码导致参数传递中断 ⚠️

**位置**: `runtime/serialize/loop.py:217`

```python
def run_serial(*, reviewer=None, ...):
    # reviewer参数传入
    chapter_pipeline = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),  # ← 硬编码，忽略传入的reviewer
        reviser=RevisionEngine(),
        ...
    )
```

**影响**：
- CLI通过`--reviewer=llm-quality`传入的LLMQualityJudge被丢弃
- 外部调用传入的自定义reviewer无法生效
- 永远只使用ChapterReviewer

**严重度**: P0 - 阻止使用已实现的quality_center

---

### 问题2: 类型注解过于严格 ⚠️

**位置**: `runtime/chapter/orchestrator.py`

```python
@dataclass
class ChapterProductionOrchestrator:
    writer: DraftWriter
    reviewer: ChapterReviewer  # ← 应该是DraftReviewer协议
    reviser: RevisionEngine
```

**影响**：
- 类型检查会拒绝传入LLMQualityJudge
- 违反了面向接口编程原则
- 降低了可扩展性

**严重度**: P1 - 代码质量问题，但不影响运行时

---

### 问题3: ChapterReviewer是简单实现 ✅ 已知问题

**位置**: `runtime/chapter/reviewer.py`

```python
def review(self, draft: ChapterDraft) -> ChapterReview:
    scores = {
        "structure": anchors["structure"] if cjk_chars >= min_chars else 0.5,
        "pacing": anchors["pacing"] if cjk_chars >= min_chars else 0.5,
        "readability": 0.8 if text else 0.0,
        "character_consistency": 0.7,  # ← 固定
        "setting_consistency": 0.7,    # ← 固定
        "emotion_progress": 0.7,       # ← 固定
        "hook_strength": 0.7 if text.endswith(...) else 0.6,  # ← 简单规则
        "commercial_pull": 0.7,        # ← 固定
        ...
    }
```

**影响**：
- 审核报告所称的"96/100章相同分数"
- 无法区分章节质量差异
- 只做了长度检查和简单规则

**严重度**: P0 - 这是审核报告的核心论断

---

### 问题4: LLMQualityJudge已实现但未接入 ⚠️

**现状**：
- ✅ 已实现：471行完整代码
- ✅ 已测试：有测试覆盖
- ✅ CLI可用：通过`--reviewer=llm-quality`调用
- ❌ Serial未接入：被硬编码的ChapterReviewer阻断

**位置**: `runtime/execution/quality_center.py`

```python
class LLMQualityJudge:
    """
    18维度评分:
    - V1: hook, conflict, reward_density, character_consistency,
          world_consistency, emotion, commercial, originality_risk
    - V2: retention, subscription, payoff, curiosity, promise_delivery,
          pacing, character_growth, serial_sustainability, 
          reader_drop_risk, safety_risk
    """
```

**严重度**: P0 - Built≠Live第8个实例

---

## 三、审核报告论断验证

### 报告论断1: "评审使用固定分数"

**验证结果**: ✅ **准确**

- ChapterReviewer确实使用固定0.7分数
- 代码证据：`reviewer.py:31-42`
- 这是审核报告的核心发现

### 报告论断2: "需要替换固定Reviewer"

**验证结果**: ⚠️ **部分准确，但方案不同**

审核报告建议：
- ❌ "删除chapter_reviewer.py，重建评审"
- ❌ "停止生产4周"

**实际情况**：
- ✅ LLMQualityJudge已实现471行
- ✅ 只需修复硬编码问题，不需要重建
- ✅ 可以并行改进，不需要停产

### 报告论断3: "质量评审系统不可信"

**验证结果**: ⚠️ **混淆了两个层次**

审核报告混淆：
- ChapterReviewer不可信 ✅（固定分数）
- 评审系统整体不可信 ❌（quality_center已实现）

**实际情况**：
- 系统**有能力**做真实评审（quality_center 471行）
- 只是**未接入**生产（硬编码问题）
- 不是"能力缺失"，是"接入问题"

---

## 四、为何LLMQualityJudge未被使用？

### 追踪调用链

1. **CLI层**：可以传入LLMQualityJudge ✅
   ```python
   # cli.py
   reviewer = _make_reviewer(args, gen_model)  # 可以是llm_quality_judge
   result = run_serial(..., reviewer=reviewer)
   ```

2. **Serial层**：接受reviewer参数 ✅
   ```python
   # serialize/loop.py
   def run_serial(*, reviewer=None, ...):
       # reviewer参数存在
   ```

3. **Orchestrator层**：**参数被忽略** ❌
   ```python
   # serialize/loop.py:217
   chapter_pipeline = ChapterProductionOrchestrator(
       reviewer=ChapterReviewer(),  # ← 硬编码！
   )
   ```

### 根本原因

**设计意图 vs 实际实现**：

设计意图（从协议定义看）：
- DraftReviewer协议允许多种实现
- run_serial接受reviewer参数
- 应该支持可插拔的评审器

实际实现：
- ChapterProductionOrchestrator硬编码ChapterReviewer
- 传入的reviewer参数被忽略
- **实现时未贯彻设计意图**

这是典型的"Built≠Live"问题第8个实例。

---

## 五、改进方案对比

### 方案A: 最小改动修复 ✅ 推荐

**改动点**：
1. `ChapterProductionOrchestrator`的`reviewer`字段改为可选参数
2. `serialize/loop.py`传递外部reviewer而不是硬编码
3. 默认值保持`ChapterReviewer()`，向后兼容
4. CLI添加`--quality-judge`标志

**代码改动**：
```python
# runtime/chapter/orchestrator.py
from ..execution.draft_review import DraftReviewer

@dataclass
class ChapterProductionOrchestrator:
    writer: DraftWriter
    reviewer: DraftReviewer  # 改为协议类型
    reviser: RevisionEngine
    ...

# runtime/serialize/loop.py
def run_serial(*, reviewer=None, ...):
    if reviewer is None:
        reviewer = ChapterReviewer()  # 默认向后兼容
    
    chapter_pipeline = ChapterProductionOrchestrator(
        reviewer=reviewer,  # 传递外部reviewer
        ...
    )
```

**工作量**: 2天
- 1天：代码修改 + 单元测试
- 1天：集成测试 + 回归验证

**优势**：
- ✅ 不破坏现有行为（默认仍是ChapterReviewer）
- ✅ 立即启用quality_center能力
- ✅ 向后兼容（所有现有测试通过）
- ✅ 可选择性启用（--quality-judge）

**风险**：
- ⚠️ 需要验证所有调用路径
- ⚠️ 类型检查可能需要调整

---

### 方案B: 两层评审架构 ⭐ 理想

**架构**：
```
快速筛选层 (ChapterReviewer)
    ↓ (确定性检查，永不调用LLM)
    ├─ 长度不足 → 拒绝
    ├─ 格式错误 → 拒绝
    └─ 基础通过 → 进入深度评审
         ↓
深度评审层 (LLMQualityJudge, 可选)
    ↓ (LLM调用，按需启用)
    ├─ 18维度打分
    ├─ 修订建议
    └─ 对比选优
```

**实现**：
```python
class TwoTierReviewer:
    def __init__(self, fast_reviewer, deep_reviewer=None):
        self.fast = fast_reviewer
        self.deep = deep_reviewer
    
    def review(self, artifact, package, grounding=None):
        # 第一层：快速筛选
        fast_result = self.fast.review(artifact, package)
        if fast_result.overall_verdict == "revise":
            return fast_result  # 快速拒绝
        
        # 第二层：深度评审（可选）
        if self.deep is not None:
            return self.deep.review(artifact, package, grounding)
        
        return fast_result
```

**工作量**: 1周
- 2天：TwoTierReviewer实现
- 2天：配置策略（何时启用深度评审）
- 3天：测试 + 成本优化验证

**优势**：
- ✅ 性能优化（快速拒绝明显问题，不浪费LLM调用）
- ✅ 成本优化（只对候选章节深度评审）
- ✅ 灵活配置（可按章节重要性调整）
- ✅ 清晰分层（确定性 vs 评价性）

**适用场景**：
- 大批量生产（>100章）
- 成本敏感
- 需要快速迭代

---

### 方案C: 完全重写 ❌ 不推荐

审核报告建议的方案：
- 删除所有现有reviewer
- 重新设计评审系统
- 4周开发周期

**为何不推荐**：
- ❌ LLMQualityJudge已实现471行，重写是浪费
- ❌ 破坏现有测试和向后兼容性
- ❌ 需要大量回归测试
- ❌ 时间成本过高（4周 vs 2天）
- ❌ 与"继续生产"冲突

---

## 六、推荐的执行计划

### Phase 1: 快速修复（本周，2天）

**目标**: 启用LLMQualityJudge

**任务**：
1. ✅ 修改ChapterProductionOrchestrator接受DraftReviewer协议
2. ✅ 修改serialize/loop.py传递reviewer参数
3. ✅ 添加CLI标志`--quality-judge`
4. ✅ 回归测试确保默认行为不变

**验收**：
```bash
# 默认行为（确定性，快速）
python -m runtime.cli run-serial --project novel-lingse

# 启用质量判断（LLM，准确）
python -m runtime.cli run-serial --project novel-lingse --quality-judge
```

---

### Phase 2: 验证效果（1周后）

**目标**: 确认LLMQualityJudge输出可用

**任务**：
1. ✅ 用LLMQualityJudge重新评审抽样的10章
2. ✅ 对比ChapterReviewer vs LLMQualityJudge的评分差异
3. ✅ 验证18个维度是否能区分章节质量
4. ✅ 建立30-50条金样集用于校准

**验收**：
- 不同质量的章节得分显著不同
- 评分与人工判断相关性 > 0.6
- 无假绿灯（高分但质量差）

---

### Phase 3: 两层架构（可选，2周后）

**目标**: 成本优化 + 性能优化

**任务**：
1. ✅ 实现TwoTierReviewer
2. ✅ 配置策略（前10章深度评审，后续抽样）
3. ✅ 成本对比实验
4. ✅ 性能对比实验

**验收**：
- 成本降低 > 50%（相比全章节深度评审）
- 质量无显著下降
- 吞吐量提升 > 2x

---

## 七、关键决策点

### 决策1: 是否立即启用LLMQualityJudge？

**推荐**: ✅ **是，通过可选标志启用**

理由：
- quality_center已实现且测试通过
- 只需修复硬编码问题（2天工作量）
- 不影响默认行为（向后兼容）
- 可以立即验证效果

**不推荐**: ❌ "等4周重建评审系统"

理由：
- 已有实现可用，重建是浪费
- 与"继续生产"目标冲突
- 时间成本过高

---

### 决策2: 是否替换ChapterReviewer？

**推荐**: ⚠️ **不，保留作为快速筛选层**

理由：
- ChapterReviewer确定性、快速、无成本
- 可以快速拒绝明显问题（长度不足等）
- 作为第一层筛选有价值

**改进**: ✅ **增强ChapterReviewer的确定性检查**

建议增加：
- 格式完整性检查
- 文本完整性检查（已有text_integrity）
- 基础规则检查（已有humanization, density）

---

### 决策3: 默认使用哪个Reviewer？

**推荐**: ✅ **默认ChapterReviewer，可选LLMQualityJudge**

理由：
- 向后兼容（现有测试通过）
- 确定性（可重现）
- 零成本（不调用API）

**何时使用LLMQualityJudge**：
- 关键章节（前10章、高潮章节）
- 需要对比选优时
- 人工验证前的预评估
- 金样集建立

---

## 八、对审核报告建议的回应

### 审核报告P0-02："替换固定分Reviewer"

**审核报告建议**：
- 删除chapter_reviewer.py
- 重新设计评审系统
- 4周开发周期
- 停止生产

**我的评估**：⚠️ **目标正确，方案过度**

**推荐方案**：
- ✅ 保留ChapterReviewer作为快速筛选
- ✅ 启用LLMQualityJudge作为深度评审
- ✅ 2天修复硬编码问题
- ✅ 不停止生产，并行改进

**差异对比**：

| 维度 | 审核报告方案 | 推荐方案 | 优势 |
|------|------------|---------|------|
| 开发周期 | 4周 | 2天 | 20x快 |
| 利用现有代码 | ❌ 删除重建 | ✅ 利用quality_center | 复用471行代码 |
| 向后兼容 | ❌ 破坏现有测试 | ✅ 完全兼容 | 零风险 |
| 生产影响 | ❌ 停产4周 | ✅ 继续生产 | 不阻塞 |
| 架构清晰度 | ⚠️ 单一评审 | ✅ 两层架构 | 更灵活 |

---

## 九、总结与建议

### 核心结论

1. **评审系统不是"能力缺失"，是"接入问题"**
   - LLMQualityJudge已实现471行
   - 被硬编码阻断，未接入生产
   - 这是Built≠Live第8个实例

2. **ChapterReviewer不是"需要删除"，是"需要定位"**
   - 固定分数确实是问题
   - 但作为快速筛选层有价值
   - 应该保留并增强，不是删除

3. **改进不需要"停产4周"，只需"修复2天"**
   - 硬编码是代码层面的简单bug
   - 不需要架构性重构
   - 可以并行改进

### 立即行动

**P0（本周）**：
1. 修复硬编码问题（2天）
2. 启用LLMQualityJudge通过CLI标志
3. 回归测试确保向后兼容

**P1（2周）**：
1. 用LLMQualityJudge重新评审抽样10章
2. 对比评分差异
3. 建立30-50条金样集

**P2（可选，1个月）**：
1. 实现两层评审架构
2. 成本优化验证
3. 性能优化验证

### 不推荐的行动

❌ 删除chapter_reviewer.py  
❌ 停产4周重建评审系统  
❌ 在没有验证的情况下默认启用LLMQualityJudge

---

**报告完成时间**: 2026-09-01  
**下一步**: 继续Task #4（评审系统升级方案设计）并生成具体的代码改动方案
