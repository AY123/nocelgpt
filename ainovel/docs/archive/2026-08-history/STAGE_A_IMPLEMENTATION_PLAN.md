# 阶段 A 实现方案：最终稿质量闭环

**日期**: 2026-08-15  
**目标**: 确保所有评估和发布结论都绑定最终稿

---

## 当前状态分析

### 已有的质量检查

1. **初稿阶段** (ex.qa_review)
   - 位置: Chapter execution 完成后
   - 覆盖: 初始生成的正文
   - 问题: 后续可能经过多次改写

2. **最终稿阶段**
   - 契约最终复验 ✅ (已有)
   - M7 原创性检查 ✅ (已有)
   - 正文卫生检查 ✅ (已有)
   - 钩子检查 ✅ (已有)
   - **质量中心复评** ❌ (缺失)
   - **读者模拟复评** ❌ (缺失)

---

## 任务 1: 最终稿 Quality Center 复评

### 实现位置

在 `runtime/serialize/loop.py` 的最终稿完成后，M7 检查之前或之后。

### 实现逻辑

```python
# After all modifications (contract revision, commercial revision, hygiene)
final_draft = chapter_draft
final_hash = final_draft.get("content_hash")

# Run Quality Center on FINAL draft
if review_model:  # Only if LLM reviewer is enabled
    from ..execution.quality_center import review_chapter_quality
    
    final_quality_review = review_chapter_quality(
        chapter=final_draft,
        review_model=review_model,
        project_path=project_path,
        prev_chapter_body=prev_text
    )
    
    # Compare to initial quality
    initial_scores = ex.qa_review.get("scores", {}) if ex.qa_review else {}
    final_scores = final_quality_review.get("scores", {})
    
    quality_delta = {}
    for dimension in final_scores:
        initial = initial_scores.get(dimension, 0)
        final = final_scores[dimension]
        quality_delta[dimension] = {
            "initial": initial,
            "final": final,
            "delta": final - initial
        }
```

### 关键点

- 只在启用 LLM reviewer 时运行（避免无谓成本）
- 绑定 final_hash
- 对比初稿和最终稿质量变化
- 记录到 ChapterRun

---

## 任务 2: 最终稿 Reader Simulator 复评

### 实现位置

在商业优化完成后（如果启用），或最终稿确定后。

### 实现逻辑

```python
# Run Reader Simulator on FINAL draft (if commercial mode enabled)
if commercial_optimization_enabled and reader_model:
    from ..execution.reader_simulator import simulate_readers
    
    final_reader_response = simulate_readers(
        chapter=final_draft,
        reader_model=reader_model,
        reader_roles=commercial_config.get("reader_roles"),
        project_path=project_path
    )
    
    # Check for new drop risks
    new_dropouts = [
        r for r in final_reader_response.get("readers", [])
        if not r.get("will_continue")
    ]
    
    if new_dropouts:
        # Warning: final draft introduced new dropout risks
        pass
```

### 关键点

- 只在商业模式启用时运行
- 检测最终稿是否引入新的弃书风险
- 记录到 ChapterRun

---

## 任务 3: Production Card 数据结构

### 定义

```python
@dataclass
class ProductionCard:
    """统一的章节发布质量卡片"""
    
    # 基本信息
    chapter: int
    draft_hash: str
    draft_timestamp: str
    
    # 契约状态
    contract_status: str  # "pass" | "warning" | "invalid"
    contract_deviations: int
    critical_deviations: int
    high_deviations: int
    
    # 质量评分（最终稿）
    final_quality_scores: dict  # {dimension: score}
    quality_delta: dict  # {dimension: {initial, final, delta}}
    
    # 读者响应（最终稿）
    reader_simulation: dict
    dropout_risk: float
    continuation_rate: float
    
    # 确定性检查
    prose_checks: dict
    m7_originality: dict
    
    # 发布建议
    publish_recommendation: str  # "recommend" | "hold" | "block"
    redline_passed: bool
    human_decision: str  # "pending" | "approved" | "rejected"
    human_decision_by: Optional[str]
    human_decision_at: Optional[str]
    
    # 审计
    generated_at: str
    review_model: str
    
    def to_dict(self):
        return asdict(self)
```

### 生成位置

在所有检查完成后，发布前。

---

## 任务 4: 商业优化质量非退化条件

### 当前条件（已有）

```python
# In commercial loop
if (relative_improvement 
    and no_new_dropouts 
    and acceptable_subscription_loss):
    accept_revision = True
```

### 增强条件

```python
# Enhanced acceptance criteria
accept_revision = (
    relative_improvement
    and no_new_dropouts
    and acceptable_subscription_loss
    and quality_not_degraded  # 新增
    and contract_not_degraded  # 新增
    and prose_hygiene_maintained  # 新增
)

# 具体判断
quality_not_degraded = all([
    revised_scores.get("character_consistency", 0) >= 
        original_scores.get("character_consistency", 0) - 5,  # 允许 5 分容差
    revised_scores.get("world_consistency", 0) >= 
        original_scores.get("world_consistency", 0) - 5,
    revised_scores.get("prose_quality", 0) >= 
        original_scores.get("prose_quality", 0) - 5
])

contract_not_degraded = (
    revised_critical_count <= original_critical_count
    and revised_high_count <= original_high_count
)

prose_hygiene_maintained = (
    revised_hygiene_issues <= original_hygiene_issues
)
```

---

## 实施计划

### Phase 1: 数据结构（30 分钟）

1. 创建 `ProductionCard` 类
2. 添加到 `ChapterRun.to_dict()`
3. 序列化和反序列化

### Phase 2: 最终稿质量复评（1 小时）

1. 在 loop.py 添加最终稿 Quality Center 调用
2. 对比初稿和最终稿评分
3. 记录质量变化

### Phase 3: 最终稿读者模拟（30 分钟）

1. 在商业优化后添加最终读者模拟
2. 检测新增弃书风险
3. 记录到 Production Card

### Phase 4: Production Card 生成（1 小时）

1. 聚合所有最终检查结果
2. 生成统一发布建议
3. 持久化到章节审计

### Phase 5: 商业优化增强（1 小时）

1. 添加质量非退化条件
2. 添加契约非退化条件
3. 添加正文卫生维护条件
4. 更新接受规则

### Phase 6: 测试（1 小时）

1. 单元测试 Production Card
2. 集成测试最终稿复评
3. 测试商业优化新条件

---

## 预期成果

### 验收标准

1. ✅ 最终稿必须重新运行 Quality Center
2. ✅ 最终稿必须重新运行 Reader Simulator（如果启用商业模式）
3. ✅ 所有最终评估绑定同一个 draft_hash
4. ✅ Production Card 包含所有关键指标
5. ✅ 商业优化不能在质量维度明显退化
6. ✅ hold/block 必须进入人工决策队列

### 数据示例

```json
{
  "production_card": {
    "chapter": 1,
    "draft_hash": "abc123",
    "contract_status": "pass",
    "critical_deviations": 0,
    "final_quality_scores": {
      "character_consistency": 85,
      "world_consistency": 88,
      "pacing": 78
    },
    "quality_delta": {
      "character_consistency": {"initial": 82, "final": 85, "delta": +3},
      "pacing": {"initial": 80, "final": 78, "delta": -2}
    },
    "reader_simulation": {
      "continuation_rate": 0.92,
      "dropout_risk": 0.08
    },
    "publish_recommendation": "recommend",
    "redline_passed": true,
    "human_decision": "pending"
  }
}
```

---

## 风险与缓解

### 风险 1: 增加生产成本

**缓解**:
- 只在 LLM reviewer 启用时运行
- 可配置是否执行最终复评
- 默认保持向后兼容

### 风险 2: 增加生产时间

**缓解**:
- 最终复评是最后一步，不影响主流程
- 可选择性跳过部分评审
- 仅对关键章节启用完整复评

### 风险 3: 评分不稳定

**缓解**:
- 使用质量变化而非绝对分数
- 设置合理容差（如 ±5 分）
- 记录初稿和最终稿评分用于分析

---

## 下一步

请确认是否开始实现，或需要调整方案。

我建议从 **Phase 1 和 Phase 2** 开始，先实现基础的最终稿质量复评和数据结构。

---

*方案设计: Claude Opus 4.8*  
*日期: 2026-08-15*
