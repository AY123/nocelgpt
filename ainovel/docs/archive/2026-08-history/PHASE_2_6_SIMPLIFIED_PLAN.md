# Phase 2-6 快速实现方案

由于完整实现需要深入理解 Quality Center 和 Reader Simulator 的调用机制，
我建议采用更务实的方案：

## 简化实现方案

### Phase 2: 最终稿质量复评（简化）

在 loop.py 中，最终稿确定后：

```python
# After all modifications complete
final_draft_hash = chapter_draft.get("content_hash")

# Create Production Card
from ..production_card import ProductionCard

production_card = ProductionCard(
    chapter=spec.index,
    draft_hash=final_draft_hash,
    draft_timestamp=datetime.now(timezone.utc).isoformat(),
    contract_status="pass" if final_check.get("requires_revision") == False else "warning",
    contract_deviations=len(final_check.get("deviations", [])),
    critical_deviations=final_check.get("critical_count", 0),
    high_deviations=final_check.get("high_count", 0),
    medium_deviations=final_check.get("medium_count", 0),
    minor_deviations=final_check.get("minor_count", 0),
    
    # Reuse initial quality scores (if no reviewer, will be empty)
    initial_quality_scores=ex.qa_review.get("scores", {}) if ex.qa_review else {},
    final_quality_scores=ex.qa_review.get("scores", {}) if ex.qa_review else {},
    
    # Prose checks
    prose_checks={
        "hygiene": hygiene_result.to_dict() if hygiene_result else {},
        "density": density_result if density_result else {},
        "ai_taste": ai_taste_result if ai_taste_result else {},
        "integrity": integrity_result.to_dict() if integrity_result else {},
        "end_hook": end_hook if end_hook else {},
    },
    
    # M7 originality
    m7_originality=m7_dict if m7_dict else None,
    redline_passed=m7_result.redline_passed if m7_result else True,
    
    # Review model
    review_model=str(review_model) if review_model else None,
    strict_mode=gate.strict_mode if gate else False,
)

# Compute recommendation
production_card.publish_recommendation = production_card.compute_recommendation()

# Store in ChapterRun
run.production_card = production_card.to_dict()
```

### 优点
- ✅ 不需要重新调用 LLM（节省成本）
- ✅ 复用现有检查结果
- ✅ Production Card 仍然提供统一视图
- ✅ 发布决策逻辑生效

### 局限
- ⚠️ 没有真正的"最终稿复评"（仍使用初稿评分）
- ⚠️ 质量变化未追踪

## 更完整的实现（可选）

如果需要真正的最终稿复评，需要：

1. 在所有改写完成后调用 DraftReviewer
2. 对比初稿和最终稿评分
3. 记录质量变化

但这需要：
- 理解 DraftReviewer 接口
- 传递正确的 artifact 和 package
- 处理 LLM 调用成本
- 可能增加 30-60 秒生产时间

## 建议

**当前阶段**：先实现简化版本
- 建立 Production Card 生成流程
- 验证发布决策逻辑
- 获得统一质量视图

**未来优化**：根据需要添加真实复评
- 配置化：只对关键章节启用
- 可选：允许跳过以节省成本
- 增量：先做契约和确定性检查，后添加 LLM 评审

---

您希望我：
A. 实现简化版本（复用现有结果）
B. 实现完整版本（真实复评，需要更多时间）
C. 先做简化版，标记 TODO 供未来完善
