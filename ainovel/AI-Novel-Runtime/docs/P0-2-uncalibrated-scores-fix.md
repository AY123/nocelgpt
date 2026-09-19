# P0-2: 未校准评分用于生产决策 - 修复方案

**日期**: 2026-08-18  
**问题**: 未校准的LLM评分被用于生产决策（hold/block判断）

---

## 问题诊断

### 当前校准状态
```json
{
  "status": "uncalibrated_insufficient_real_samples",
  "real_sample_count": 3,
  "trusted_dimensions": [],
  "dimension_grading": {
    "decision": [],
    "diagnostic": [所有12个维度],
    "unreliable": []
  }
}
```

### 问题代码位置

**1. decision_engine.py:102-106**
```python
for dim, min_score in QUALITY_THRESHOLDS.items():
    score = final_quality_scores.get(dim)
    if score is not None and score < min_score:
        warnings.append(f"{dim} score {score:.0f} below threshold {min_score}")
        return "hold", blocking_issues, warnings  # ❌ 直接hold
```

**2. production_card.py:13-22**
```python
QUALITY_THRESHOLDS = {
    "hook": 75,
    "retention": 75,
    "reward_density": 70,
    # ... 固定阈值，未考虑校准状态
}
```

### 核心矛盾

1. **校准报告明确说明**: 只有3个真实样本，所有维度都是`diagnostic`（仅供诊断/复盘，不能单独决定选择）
2. **决策引擎却在使用**: 这些未校准分数直接触发`hold`决策
3. **违反ADR-003**: 评价性判断不应阻断构建/生产，只有硬红线可以gate

---

## 修复方案

### 方案A: 加载校准状态，动态降级（推荐）

**原则**:
- 未校准维度的分数只能用于advisory警告
- 只有校准后的`decision`级维度可触发hold
- 确定性红线继续可以block

**实现**:

1. **加载校准摘要**
```python
def load_calibration_status(project_path: Path) -> dict:
    """加载校准状态，返回trusted_dimensions列表"""
    golden_set = project_path / "quality-golden-set"
    summary_path = golden_set / "metadata" / "w9-calibration-summary.json"
    if not summary_path.exists():
        return {"status": "unknown", "trusted_dimensions": []}
    
    with open(summary_path) as f:
        data = json.load(f)
    return {
        "status": data.get("status", "unknown"),
        "trusted_dimensions": data.get("trusted_dimensions", []),
        "decision_dimensions": data.get("dimension_grading", {}).get("decision", [])
    }
```

2. **修改决策引擎**
```python
def decide(
    self,
    *,
    final_quality_scores: Optional[Dict[str, float]] = None,
    calibration_status: Optional[Dict] = None,  # 新增参数
    # ... 其他参数
) -> Tuple[str, List[str], List[str]]:
    
    # Priority 6: 质量阈值检查 - 只对已校准维度有效
    if final_quality_scores:
        trusted_dims = []
        if calibration_status:
            # 优先使用decision级维度，其次是trusted_dimensions
            trusted_dims = (calibration_status.get("decision_dimensions", []) or
                          calibration_status.get("trusted_dimensions", []))
        
        for dim, min_score in QUALITY_THRESHOLDS.items():
            score = final_quality_scores.get(dim)
            if score is not None and score < min_score:
                if dim in trusted_dims:
                    # 已校准维度：可以hold
                    warnings.append(f"{dim} score {score:.0f} below threshold {min_score} (calibrated)")
                    return "hold", blocking_issues, warnings
                else:
                    # 未校准维度：仅警告
                    warnings.append(f"{dim} score {score:.0f} below threshold {min_score} (uncalibrated, advisory only)")
                    # 不return，继续检查
```

3. **Production Card调用时传入校准状态**
```python
def compute_recommendation(self) -> str:
    from .decision_engine import ProductionDecisionEngine
    from pathlib import Path
    
    engine = ProductionDecisionEngine()
    
    # 加载校准状态
    calibration_status = None
    if hasattr(self, 'project_path'):
        calibration_status = load_calibration_status(Path(self.project_path))
    
    action, blocking_issues, warnings = engine.decide(
        # ... 其他参数
        final_quality_scores=self.final_quality_scores,
        calibration_status=calibration_status,
        # ...
    )
```

### 方案B: 完全移除质量阈值gate（最保守）

**原则**: 严格遵守ADR-003，评价性分数永不gate

**实现**:
```python
# 在 decision_engine.py 中注释掉或删除 Priority 6
# Priority 6: 质量分数只产生warnings，永不return hold
if final_quality_scores:
    for dim, min_score in QUALITY_THRESHOLDS.items():
        score = final_quality_scores.get(dim)
        if score is not None and score < min_score:
            warnings.append(f"{dim} score {score:.0f} below threshold {min_score} (advisory)")
            # 不return - 质量分数仅供参考
```

### 方案C: 添加bypass标志（兼容性最好）

**原则**: 添加`--strict-quality-gate`标志，默认关闭

**实现**:
```python
# CLI参数
parser.add_argument("--strict-quality-gate", action="store_true",
                   help="Enable quality score gating (requires calibrated reviewer)")

# 决策引擎
def decide(self, *, enable_quality_gate: bool = False, ...):
    # Priority 6: 质量阈值（仅在启用且已校准时有效）
    if enable_quality_gate and final_quality_scores and calibration_status:
        trusted_dims = calibration_status.get("decision_dimensions", [])
        if trusted_dims:  # 只有存在decision级维度时才gate
            # ... 原有逻辑
```

---

## 推荐方案: A + 部分B

**实施步骤**:

1. ✅ **立即**: 实现方案A的校准状态加载
2. ✅ **立即**: 未校准维度降级为advisory
3. ✅ **短期**: 等待校准完成（至少30个真实样本）
4. ✅ **中期**: 校准后，decision级维度才能触发hold

**ADR-003对齐**:
- 确定性红线（M7原创性、文本完整性）继续block ✅
- 评价性分数（LLM质量评分）仅advisory，直到校准完成 ✅
- 人工决策可block ✅

---

## 测试计划

1. **单元测试**: 决策引擎在不同校准状态下的行为
```python
def test_uncalibrated_scores_are_advisory():
    engine = ProductionDecisionEngine()
    
    # 未校准状态
    calibration_status = {"trusted_dimensions": []}
    
    # 低分应该只产生warning，不hold
    action, blocking, warnings = engine.decide(
        final_quality_scores={"hook": 60},  # 低于阈值75
        calibration_status=calibration_status
    )
    
    assert action != "hold", "未校准分数不应触发hold"
    assert any("uncalibrated" in w for w in warnings)
```

2. **集成测试**: 5章运行，验证未校准状态不阻断
3. **回归测试**: 确保deterministic gates仍然有效

---

## 文档更新

需要更新：
- `production_card.py` docstring说明阈值适用条件
- `decision_engine.py` 每个priority的gating条件
- ADR-003文档：明确质量分数的advisory边界

---

## 预期效果

**修复前**:
- 未校准LLM评分 → 直接触发hold
- 好章节可能被错误hold
- 违反ADR-003（评价性判断阻断生产）

**修复后**:
- 未校准评分 → 仅advisory警告
- 只有确定性红线和人工决策可block/hold
- 校准完成后，decision级维度才能gate
- 符合ADR-003

---

## 下一步行动

1. [ ] 实现 `load_calibration_status()` 
2. [ ] 修改 `ProductionDecisionEngine.decide()` 添加校准状态参数
3. [ ] 更新所有调用点传入校准状态
4. [ ] 添加单元测试
5. [ ] 运行5章集成测试
6. [ ] 更新文档
