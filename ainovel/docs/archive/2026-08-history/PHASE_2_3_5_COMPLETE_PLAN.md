# Phase 2/3/5 完整实现方案

**日期**: 2026-08-15  
**目标**: 完善阶段 A，实现真实的最终稿复评

---

## 实现策略

### 关键考虑

1. **成本影响**: 每次真实复评需要额外 LLM 调用
2. **时间影响**: 增加 20-40 秒生产时间
3. **配置化**: 必须可选，默认使用简化版本
4. **实用性**: 仅对关键章节或高风险情况启用

---

## Phase 2: 最终稿 Quality Center 复评

### 实现位置

在 Production Card 生成之前，添加可选的最终稿复评。

### 配置参数

```python
# 新增 CLI 参数
--enable-final-quality-review    # 启用最终稿质量复评
--final-review-threshold         # 触发条件（默认: 总是）
  - always: 所有章节
  - contract-warning: 契约有警告时
  - quality-drop: 初稿质量低于阈值时
  - critical-only: 仅关键章节（1, 10, 20, ...）
```

### 实现代码

```python
# In loop.py, before Production Card generation

final_quality_scores = _scores  # 默认复用初稿
quality_delta = {}

if enable_final_quality_review and review_model:
    # 判断是否需要复评
    should_review = False
    
    if final_review_threshold == "always":
        should_review = True
    elif final_review_threshold == "contract-warning":
        should_review = final_contract_validation.get("requires_revision", False)
    elif final_review_threshold == "quality-drop":
        initial_avg = sum(_scores.values()) / len(_scores) if _scores else 0
        should_review = initial_avg < 75
    elif final_review_threshold == "critical-only":
        should_review = spec.index in [1, 10, 20, 30, 50, 100]
    
    if should_review:
        # 构造最终稿 artifact
        final_artifact = {
            "chapter_index": spec.index,
            "body": chapter_draft.get("body", ""),
            "content_hash": chapter_draft.get("content_hash"),
            "word_count": len(chapter_draft.get("body", "")),
        }
        
        # 调用 Quality Center
        from ..execution.quality_center import LLMQualityJudge
        
        judge = LLMQualityJudge(
            review_model,
            reviewer_id="final-draft-judge",
            threshold=80
        )
        
        final_report = judge.review(
            artifact=final_artifact,
            package=package,
            grounding=grounding
        )
        
        # 提取最终评分
        final_quality_scores = final_report.scores or _scores
        
        # 计算质量变化
        if _scores and final_quality_scores:
            for dim in final_quality_scores:
                initial_val = _scores.get(dim, 0)
                final_val = final_quality_scores[dim]
                quality_delta[dim] = {
                    "initial": initial_val,
                    "final": final_val,
                    "delta": final_val - initial_val
                }
        
        # 记录到 ChapterRun
        run.final_quality_review = final_report.to_dict()
```

### 成本估算

| 配置 | 每章成本 | 100 章成本 | 说明 |
|-----|---------|-----------|------|
| always | +$0.10 | +$10 | 所有章节复评 |
| contract-warning | +$0.02 | +$2 | 仅警告时 (~20%) |
| quality-drop | +$0.03 | +$3 | 仅低质量时 (~30%) |
| critical-only | +$0.01 | +$1 | 仅关键章节 (~10%) |

---

## Phase 3: 最终稿 Reader Simulator 复评

### 实现位置

仅在商业模式启用时，在最终稿确定后重新模拟读者反应。

### 配置参数

```python
--enable-final-reader-simulation  # 启用最终稿读者模拟
--final-reader-threshold          # 触发条件
  - always
  - commercial-revised: 经过商业修订的章节
  - dropout-risk: 初稿有弃书风险时
```

### 实现代码

```python
# In loop.py, after commercial optimization (if enabled)

final_reader_response = None
dropout_risk = None
continuation_rate = None

if enable_final_reader_simulation and reader_model and commercial_mode:
    should_simulate = False
    
    if final_reader_threshold == "always":
        should_simulate = True
    elif final_reader_threshold == "commercial-revised":
        should_simulate = commercial_revision_session is not None
    elif final_reader_threshold == "dropout-risk":
        initial_dropout = (initial_reader_response or {}).get("dropout_risk", 0)
        should_simulate = initial_dropout > 0.2
    
    if should_simulate:
        from ..execution.reader_simulator import simulate_readers
        
        final_reader_response = simulate_readers(
            chapter=chapter_draft,
            reader_model=reader_model,
            reader_roles=commercial_config.get("reader_roles"),
            project_path=project_path
        )
        
        # 提取关键指标
        readers = final_reader_response.get("readers", [])
        dropouts = [r for r in readers if not r.get("will_continue")]
        dropout_risk = len(dropouts) / len(readers) if readers else 0
        continuation_rate = 1.0 - dropout_risk
        
        # 检测新增弃书
        initial_dropouts = (initial_reader_response or {}).get("dropout_count", 0)
        final_dropouts = len(dropouts)
        
        if final_dropouts > initial_dropouts:
            import logging
            logging.warning(
                f"Ch{spec.index} Final draft introduced new dropout risks: "
                f"{initial_dropouts} → {final_dropouts}"
            )
```

---

## Phase 5: 商业优化质量非退化

### 实现位置

在商业循环中，增加质量非退化检查。

### 实现逻辑

```python
# In commercial loop (runtime/execution/commercial_loop.py or loop.py)

def accept_commercial_revision(
    original_draft,
    revised_draft,
    original_reader_response,
    revised_reader_response,
    enable_quality_guard=True
):
    # 现有检查
    commercial_improved = check_commercial_improvement(...)
    no_new_dropouts = check_no_new_dropouts(...)
    acceptable_subscription_loss = check_subscription_loss(...)
    
    # 新增：质量非退化检查
    quality_maintained = True
    contract_maintained = True
    hygiene_maintained = True
    
    if enable_quality_guard:
        # 1. 质量非退化（允许 5 分容差）
        if original_quality_scores and revised_quality_scores:
            key_dimensions = [
                "character_consistency",
                "world_consistency",
                "prose_quality"
            ]
            
            for dim in key_dimensions:
                original_val = original_quality_scores.get(dim, 0)
                revised_val = revised_quality_scores.get(dim, 0)
                
                if revised_val < original_val - 5:  # 下降超过 5 分
                    quality_maintained = False
                    logging.warning(
                        f"Commercial revision degraded {dim}: "
                        f"{original_val} → {revised_val}"
                    )
        
        # 2. 契约非退化
        original_contract = check_contract(original_draft)
        revised_contract = check_contract(revised_draft)
        
        if revised_contract["critical_count"] > original_contract["critical_count"]:
            contract_maintained = False
        if revised_contract["high_count"] > original_contract["high_count"]:
            contract_maintained = False
        
        # 3. 正文卫生维护
        original_hygiene = check_hygiene(original_draft)
        revised_hygiene = check_hygiene(revised_draft)
        
        original_issues = original_hygiene.get("issue_count", 0)
        revised_issues = revised_hygiene.get("issue_count", 0)
        
        if revised_issues > original_issues:
            hygiene_maintained = False
    
    # 综合判断
    accept = (
        commercial_improved
        and no_new_dropouts
        and acceptable_subscription_loss
        and quality_maintained
        and contract_maintained
        and hygiene_maintained
    )
    
    return {
        "accept": accept,
        "commercial_improved": commercial_improved,
        "no_new_dropouts": no_new_dropouts,
        "quality_maintained": quality_maintained,
        "contract_maintained": contract_maintained,
        "hygiene_maintained": hygiene_maintained,
    }
```

---

## 配置建议

### 开发/测试环境

```bash
# 简化版本（当前默认）
--no-enable-final-quality-review
--no-enable-final-reader-simulation
```

成本：$0  
时间：0 秒

### 生产环境（标准）

```bash
# 仅关键章节和风险情况
--enable-final-quality-review --final-review-threshold=contract-warning
--enable-final-reader-simulation --final-reader-threshold=commercial-revised
--enable-commercial-quality-guard
```

成本：约 +$2-3 / 100 章  
时间：约 +5-10 秒 / 章（触发时）

### 生产环境（严格）

```bash
# 所有章节完整复评
--enable-final-quality-review --final-review-threshold=always
--enable-final-reader-simulation --final-reader-threshold=always
--enable-commercial-quality-guard
```

成本：约 +$15-20 / 100 章  
时间：约 +30-40 秒 / 章

---

## 实施优先级

### 建议顺序

1. **Phase 5 (最高)**: 商业优化质量非退化
   - 成本：$0（不需要额外 LLM）
   - 时间：<1 秒
   - 价值：防止商业修订破坏质量

2. **Phase 2 (中等)**: 最终稿质量复评
   - 成本：可配置
   - 时间：可配置
   - 价值：质量变化追踪

3. **Phase 3 (较低)**: 最终稿读者模拟
   - 成本：可配置
   - 时间：可配置
   - 价值：商业模式专用

---

## 您的选择

我建议从 **Phase 5** 开始，因为：
- ✅ 零成本
- ✅ 立即生效
- ✅ 防止质量退化
- ✅ 实用价值高

然后根据需要添加 Phase 2/3。

您希望我：
**A**. 实现 Phase 5（商业质量非退化）  
**B**. 实现 Phase 2（最终稿质量复评）  
**C**. 实现全部（5 → 2 → 3）  
**D**. 其他建议

---

*方案设计: Claude Opus 4.8*  
*日期: 2026-08-15*
