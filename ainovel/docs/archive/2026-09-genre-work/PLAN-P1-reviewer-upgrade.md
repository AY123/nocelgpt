# P1-01 评审系统升级方案

**方案版本**: v1.0  
**设计时间**: 2026-09-01  
**实施周期**: 2天  
**风险等级**: 低（向后兼容）

---

## 一、方案概述

### 1.1 目标

修复评审系统的硬编码问题，启用已实现的LLMQualityJudge能力。

**核心原则**：
- ✅ 向后兼容（默认行为不变）
- ✅ 最小改动（只修复阻塞点）
- ✅ 可选启用（通过CLI标志）
- ✅ 利用现有代码（quality_center 471行）

### 1.2 问题定位

**根本原因**：`runtime/serialize/loop.py:217`硬编码`ChapterReviewer()`

**影响**：
- CLI传入的`--reviewer=llm-quality`被忽略
- LLMQualityJudge无法在serial production中使用
- Built≠Live第8个实例

---

## 二、方案A：最小改动修复（推荐）

### 2.1 改动文件清单

| 文件 | 改动类型 | 行数 | 风险 |
|------|---------|------|------|
| `runtime/chapter/orchestrator.py` | 类型注解 | 1行 | 低 |
| `runtime/serialize/loop.py` | 参数传递 | 5行 | 低 |
| `runtime/cli.py` | CLI标志 | 10行 | 低 |
| `tests/test_reviewer_upgrade.py` | 新增测试 | 50行 | - |

**总改动**：约66行代码

### 2.2 详细改动方案

#### 改动1：修复类型注解

**文件**: `runtime/chapter/orchestrator.py`

**当前代码**：
```python
@dataclass
class ChapterProductionOrchestrator:
    writer: DraftWriter
    reviewer: ChapterReviewer  # ← 类型过于具体
    reviser: RevisionEngine
    finalizer: Finalizer
    beat_planner: BeatPlanner
```

**修改为**：
```python
from ..execution.draft_review import DraftReviewer

@dataclass
class ChapterProductionOrchestrator:
    writer: DraftWriter
    reviewer: DraftReviewer  # ← 改为协议类型
    reviser: RevisionEngine
    finalizer: Finalizer
    beat_planner: BeatPlanner
```

**改动理由**：
- DraftReviewer是协议，支持多种实现
- 符合面向接口编程原则
- 不影响运行时行为（Python运行时不强制类型）

---

#### 改动2：修复硬编码问题

**文件**: `runtime/serialize/loop.py`

**当前代码** (约第217行)：
```python
def run_serial(
    *,
    project_path: str | Path,
    standard_root: str | Path,
    schema_dir: str | Path,
    out_dir: str | Path,
    model=None,
    reviewer=None,  # ← 参数存在但未使用
    ...
):
    ...
    chapter_pipeline = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),  # ← 硬编码！
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
```

**修改为**：
```python
def run_serial(
    *,
    project_path: str | Path,
    standard_root: str | Path,
    schema_dir: str | Path,
    out_dir: str | Path,
    model=None,
    reviewer=None,
    ...
):
    ...
    # 默认使用ChapterReviewer（向后兼容）
    if reviewer is None:
        from ..chapter import ChapterReviewer
        reviewer = ChapterReviewer()
    
    chapter_pipeline = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=reviewer,  # ← 使用传入的reviewer
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
```

**改动理由**：
- 尊重传入的reviewer参数
- 默认值保证向后兼容
- 允许外部注入自定义reviewer

---

#### 改动3：添加CLI标志

**文件**: `runtime/cli.py`

**在run_serial命令添加参数**：

```python
# 在run_serial的argparse定义中添加
parser.add_argument(
    '--quality-judge',
    action='store_true',
    help='Use LLM quality judge instead of simple reviewer (requires live model)'
)

# 在run_serial的执行逻辑中
def cmd_run_serial(args):
    ...
    # 构建reviewer
    if args.quality_judge:
        from .execution.quality_center import llm_quality_judge
        model = _build_llm_model(args)  # 复用生成模型或独立构建
        reviewer = llm_quality_judge(model)
    else:
        reviewer = None  # 使用默认ChapterReviewer
    
    result = run_serial(
        project_path=args.project,
        reviewer=reviewer,
        ...
    )
```

**改动理由**：
- 显式的CLI标志，用户可控
- 默认不启用，避免成本意外
- 复用现有的model构建逻辑

---

### 2.3 测试方案

#### 测试1：向后兼容性测试

```python
# tests/test_reviewer_upgrade.py

def test_default_reviewer_unchanged():
    """默认行为：不传reviewer，应使用ChapterReviewer"""
    from runtime.chapter import ChapterReviewer
    from runtime.serialize.loop import run_serial
    
    result = run_serial(
        project_path="test_project",
        reviewer=None,  # 显式传None
        ...
    )
    
    # 验证使用了ChapterReviewer
    assert isinstance(pipeline.reviewer, ChapterReviewer)
```

#### 测试2：LLMQualityJudge接入测试

```python
def test_llm_quality_judge_injection():
    """传入LLMQualityJudge，应被使用"""
    from runtime.execution.quality_center import LLMQualityJudge
    from runtime.serialize.loop import run_serial
    from tests.fixtures import MockModel
    
    mock_model = MockModel()
    reviewer = LLMQualityJudge(model=mock_model)
    
    result = run_serial(
        project_path="test_project",
        reviewer=reviewer,
        ...
    )
    
    # 验证使用了传入的reviewer
    assert isinstance(pipeline.reviewer, LLMQualityJudge)
```

#### 测试3：CLI标志测试

```bash
# 命令行测试

# 默认行为（确定性，ChapterReviewer）
python -m runtime.cli run-serial --project novel-lingse

# 启用质量判断（LLM，LLMQualityJudge）
python -m runtime.cli run-serial --project novel-lingse --quality-judge \
    --model-provider deepseek-chat
```

---

### 2.4 部署计划

#### Day 1：代码改动 + 单元测试

**上午**（3小时）：
1. ✅ 修改`orchestrator.py`类型注解
2. ✅ 修改`serialize/loop.py`参数传递
3. ✅ 编写单元测试

**下午**（3小时）：
1. ✅ 修改`cli.py`添加标志
2. ✅ 运行现有测试套件（确保无回归）
3. ✅ 本地验证

#### Day 2：集成测试 + 验证

**上午**（3小时）：
1. ✅ 集成测试：默认行为
2. ✅ 集成测试：LLMQualityJudge接入
3. ✅ CLI测试：两种模式

**下午**（3小时）：
1. ✅ 真实运行：生成1章（默认模式）
2. ✅ 真实运行：生成1章（quality-judge模式）
3. ✅ 对比评审结果
4. ✅ 文档更新

---

### 2.5 风险控制

#### 风险1：类型检查失败

**可能性**: 低  
**影响**: 中等（CI失败但不影响运行）

**缓解措施**：
- 确保DraftReviewer协议定义完整
- 添加`TYPE_CHECKING`导入避免循环依赖
- 如果类型检查工具过于严格，添加`# type: ignore`注释

#### 风险2：现有测试失败

**可能性**: 低  
**影响**: 高（阻塞合并）

**缓解措施**：
- 默认值保持ChapterReviewer（向后兼容）
- 先在分支运行完整测试套件
- 有失败立即回滚

#### 风险3：LLMQualityJudge运行时错误

**可能性**: 中等  
**影响**: 高（用户启用后失败）

**缓解措施**：
- 添加try-catch，LLM失败时降级到ChapterReviewer
- 记录详细错误日志
- 文档说明`--quality-judge`需要live model

---

### 2.6 回滚方案

如果改动导致问题，回滚步骤：

```bash
# 1. Git回滚
git revert <commit-hash>

# 2. 或手动恢复
# 将serialize/loop.py:217改回
reviewer=ChapterReviewer()

# 3. 重新运行测试
python -m pytest tests/ -q
```

**回滚时间**: < 10分钟

---

## 三、方案B：两层评审架构（可选）

### 3.1 概述

在方案A的基础上，增加两层评审架构，优化性能和成本。

**适用场景**：
- 大批量生产（>100章）
- 成本敏感
- 需要快速迭代

### 3.2 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│ TwoTierReviewer                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  快速筛选层 (ChapterReviewer)                                 │
│    ├─ 长度检查：< min_chars → reject                         │
│    ├─ 格式检查：text_integrity → reject                      │
│    └─ 基础规则：humanization/density → pass to deep          │
│         ↓                                                    │
│  深度评审层 (LLMQualityJudge, 可选)                           │
│    ├─ 18维度打分                                             │
│    ├─ 修订建议                                               │
│    └─ 对比选优                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 实现代码

**新增文件**: `runtime/chapter/two_tier_reviewer.py`

```python
"""two_tier_reviewer.py — 两层评审架构

第一层（快速筛选）：确定性检查，零成本，快速拒绝明显问题
第二层（深度评审）：LLM调用，按需启用，准确评分
"""
from dataclasses import dataclass
from typing import Optional

from ..execution.draft_review import DraftReviewer, ReviewReport
from .reviewer import ChapterReviewer


@dataclass
class TwoTierReviewer:
    """两层评审：快速筛选 + 深度评审（可选）"""
    
    fast_reviewer: DraftReviewer
    deep_reviewer: Optional[DraftReviewer] = None
    reviewer_id: str = "two-tier-reviewer-v1"
    
    # 配置：何时启用深度评审
    deep_review_policy: str = "always"  # always | important | sample
    sample_rate: float = 0.2  # sample模式下的比例
    
    def review(self, artifact: dict, package: dict, 
               grounding: dict | None = None) -> ReviewReport:
        """
        两层评审流程：
        1. 快速筛选：确定性检查
        2. 深度评审：LLM打分（按策略）
        """
        # 第一层：快速筛选
        fast_result = self.fast_reviewer.review(artifact, package, grounding)
        
        # 如果快速筛选拒绝，直接返回
        if self._should_reject_fast(fast_result):
            return fast_result
        
        # 第二层：深度评审（按策略）
        if self._should_deep_review(artifact, package):
            if self.deep_reviewer is not None:
                return self.deep_reviewer.review(artifact, package, grounding)
        
        # 深度评审未启用或不需要，返回快速结果
        return fast_result
    
    def _should_reject_fast(self, result: ReviewReport) -> bool:
        """快速筛选是否拒绝"""
        # ChapterReviewer的verdict逻辑：长度不足或空文本
        # 这里可以扩展其他确定性拒绝条件
        for finding in result.findings:
            if finding.severity == "error":
                return True
        return False
    
    def _should_deep_review(self, artifact: dict, package: dict) -> bool:
        """是否需要深度评审"""
        chapter_id = artifact.get("chapter_id", "")
        
        if self.deep_review_policy == "always":
            return True
        
        if self.deep_review_policy == "important":
            # 重要章节：前10章、高潮章节等
            chapter_no = int(chapter_id.split("-")[-1]) if "-" in chapter_id else 0
            return chapter_no <= 10 or chapter_no % 10 == 0
        
        if self.deep_review_policy == "sample":
            # 随机抽样
            import random
            return random.random() < self.sample_rate
        
        return False
```

### 3.4 CLI集成

```python
# runtime/cli.py

parser.add_argument(
    '--quality-judge',
    action='store_true',
    help='Use LLM quality judge instead of simple reviewer'
)

parser.add_argument(
    '--two-tier',
    action='store_true',
    help='Use two-tier reviewer (fast + deep)'
)

parser.add_argument(
    '--deep-policy',
    choices=['always', 'important', 'sample'],
    default='important',
    help='When to use deep review in two-tier mode'
)

# 构建reviewer
if args.two_tier:
    from .chapter.two_tier_reviewer import TwoTierReviewer
    from .chapter import ChapterReviewer
    
    fast = ChapterReviewer()
    deep = None
    if args.quality_judge:
        from .execution.quality_center import llm_quality_judge
        model = _build_llm_model(args)
        deep = llm_quality_judge(model)
    
    reviewer = TwoTierReviewer(
        fast_reviewer=fast,
        deep_reviewer=deep,
        deep_review_policy=args.deep_policy
    )
elif args.quality_judge:
    # 单层LLM
    from .execution.quality_center import llm_quality_judge
    model = _build_llm_model(args)
    reviewer = llm_quality_judge(model)
else:
    # 默认
    reviewer = None
```

### 3.5 使用示例

```bash
# 模式1：默认（快速，确定性）
python -m runtime.cli run-serial --project novel-lingse

# 模式2：全LLM（准确，成本高）
python -m runtime.cli run-serial --project novel-lingse --quality-judge

# 模式3：两层-重要章节（平衡）
python -m runtime.cli run-serial --project novel-lingse \
    --two-tier --quality-judge --deep-policy important

# 模式4：两层-抽样（成本优化）
python -m runtime.cli run-serial --project novel-lingse \
    --two-tier --quality-judge --deep-policy sample
```

### 3.6 成本对比

假设100章生产：

| 模式 | LLM调用次数 | 相对成本 | 评审准确性 |
|------|-----------|---------|-----------|
| 默认 | 0 | 0 | 低（固定分数） |
| 全LLM | 100 | 100% | 高 |
| 两层-重要 | ~20 | 20% | 高（重要章节） |
| 两层-抽样20% | 20 | 20% | 中等 |

---

## 四、实施建议

### 4.1 推荐路径

**Phase 1（本周）**：实施方案A
- 目标：修复硬编码，启用LLMQualityJudge
- 工作量：2天
- 风险：低

**Phase 2（2周后，可选）**：实施方案B
- 前提：Phase 1验证通过 + 有成本优化需求
- 目标：两层架构，成本优化
- 工作量：3天

### 4.2 验收标准

**Phase 1验收**：
- ✅ 默认行为不变（现有测试全通过）
- ✅ `--quality-judge`可用且输出18维度评分
- ✅ 评分能区分不同质量章节
- ✅ 无性能回归

**Phase 2验收**：
- ✅ 两层模式成本降低>50%
- ✅ 重要章节评审准确性不下降
- ✅ 快速筛选召回率>90%

### 4.3 文档更新

需要更新的文档：
1. ✅ README.md：添加`--quality-judge`说明
2. ✅ CLAUDE.md：更新评审系统说明
3. ✅ 内部文档：评审系统架构图

---

## 五、FAQ

### Q1: 为什么不直接替换ChapterReviewer为默认？

**A**: 向后兼容和成本控制
- 现有测试依赖确定性行为
- LLM调用有成本
- 用户应显式选择

### Q2: LLMQualityJudge失败怎么办？

**A**: 降级策略
```python
try:
    return deep_reviewer.review(artifact, package, grounding)
except Exception as e:
    logger.warning(f"Deep review failed: {e}, fallback to fast")
    return fast_result
```

### Q3: 如何校准LLMQualityJudge？

**A**: 需要金样集
- 建立30-50条人工评分样本
- 计算相关性和MAE
- 调整prompt或使用多模型panel

### Q4: 两层架构会影响性能吗？

**A**: 轻微影响，可忽略
- 快速层是确定性逻辑，<1ms
- 深度层是按需调用，不影响快速路径
- 整体延迟由LLM决定（如果启用）

---

## 六、总结

### 核心优势

1. **最小改动**：只修复阻塞点，不重构
2. **向后兼容**：默认行为完全不变
3. **利用现有**：quality_center 471行代码复用
4. **风险可控**：2天工作量，低风险
5. **灵活扩展**：两层架构可选，按需启用

### 与审核报告对比

| 维度 | 审核报告方案 | 本方案 |
|------|------------|--------|
| 周期 | 4周 | 2天 |
| 风险 | 高（重构） | 低（修复） |
| 复用 | 无（删除重建） | 高（471行） |
| 兼容 | 破坏 | 保持 |
| 成本 | 停产损失 | 无损失 |

### 下一步

1. ✅ 审批本方案
2. ✅ 执行Phase 1改动（2天）
3. ✅ 验证效果
4. ⚠️ 可选：Phase 2两层架构（按需）

---

**方案设计**: Kiro  
**审批状态**: 待审批  
**实施时间**: 审批后立即开始
