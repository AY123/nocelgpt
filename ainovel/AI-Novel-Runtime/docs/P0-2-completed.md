# P0-2: 未校准评分修复完成报告

**日期**: 2026-08-18  
**状态**: ✅ 完成  
**测试结果**: 1806 passed, 3 skipped, 0 failed

---

## 执行摘要

成功修复未校准评分被用于生产决策的问题。现在只有校准后的decision级维度可以触发hold，未校准维度仅产生advisory警告，符合ADR-003。

### 问题
- **校准状态**: `uncalibrated_insufficient_real_samples`（只有3个真实样本）
- **所有维度**: `diagnostic`级（仅供诊断），0个`decision`级
- **但代码在**: 使用这些未校准分数直接触发`hold`决策
- **违反ADR-003**: 评价性判断不应阻断生产

### 解决方案

实施了**方案A+部分B**：加载校准状态，未校准维度降级为advisory。

#### 核心修改

**1. 添加校准状态加载器** (`decision_engine.py`)
```python
def load_calibration_status(project_path: Path) -> Dict:
    """加载评审校准状态，返回可信维度列表"""
    # 读取 quality-golden-set/metadata/w9-calibration-summary.json
    # 返回 decision_dimensions, diagnostic_dimensions
```

**2. 修改决策引擎** (`decision_engine.py`)
```python
def decide(
    self,
    *,
    calibration_status: Optional[Dict] = None,  # 新增参数
    # ...
):
    # Priority 6: 质量阈值检查
    if final_quality_scores:
        decision_dims = calibration_status.get("decision_dimensions", [])
        
        for dim, min_score in QUALITY_THRESHOLDS.items():
            if score < min_score:
                if dim in decision_dims:
                    # 已校准：可以hold
                    return "hold", blocking_issues, warnings
                else:
                    # 未校准：仅advisory警告
                    warnings.append(f"{dim} ... (uncalibrated, advisory only)")
                    # 不return，继续检查
```

**3. 更新Production Card** (`production_card.py`)
```python
def compute_recommendation(self, project_path: Optional[str] = None) -> str:
    # 加载校准状态
    calibration_status = load_calibration_status(Path(project_path))
    
    action, blocking, warnings = engine.decide(
        calibration_status=calibration_status,
        # ...
    )
```

**4. 更新调用点**
- `align_production_decision()` 添加 `calibration_status` 参数
- 所有调用点传入校准状态

---

## 行为变化

### 修复前
```python
# 未校准评分 → 直接hold
final_quality_scores = {"hook": 60}  # 低于阈值75
action, _, _ = engine.decide(final_quality_scores=scores)
assert action == "hold"  # ❌ 错误的gate行为
```

### 修复后
```python
# 未校准评分 → 仅advisory
calibration_status = {"decision_dimensions": []}  # 未校准
action, _, warnings = engine.decide(
    final_quality_scores={"hook": 60},
    calibration_status=calibration_status
)
assert action == "publish"  # ✅ 不gate
assert "uncalibrated, advisory only" in warnings[0]  # ✅ 有警告

# 校准后的评分 → 可以hold
calibration_status = {"decision_dimensions": ["hook"]}  # 已校准
action, _, _ = engine.decide(
    final_quality_scores={"hook": 60},
    calibration_status=calibration_status
)
assert action == "hold"  # ✅ 校准后可gate
```

---

## 测试覆盖

### 新增测试 (8个)
`tests/test_p0_2_uncalibrated_scores.py`:
- ✅ 未校准评分仅advisory
- ✅ 校准后评分可触发hold
- ✅ 混合校准状态
- ✅ 无校准状态时的向后兼容
- ✅ 风险维度遵守校准状态
- ✅ 确定性gate不受影响
- ✅ 校准文件缺失处理
- ✅ 真实校准格式加载

### 更新测试 (6个)
- ✅ `test_decision_engine.py` - 添加校准状态
- ✅ `test_production_card_thresholds.py` - 模拟校准项目

### 完整测试集
- **1806 passed**, 3 skipped, 0 failed
- 包含所有P0-2新测试和回归测试

---

## 当前校准状态

根据 `quality-golden-set/metadata/w9-calibration-summary.json`:

```json
{
  "status": "uncalibrated_insufficient_real_samples",
  "real_sample_count": 3,
  "trusted_dimensions": [],
  "dimension_grading": {
    "decision": [],
    "diagnostic": [
      "ai_voice_risk", "chapter_goal", "character_motivation",
      "conflict_progression", "continue_intent", "continuity",
      "emotion_flow", "ending_hook", "information_density",
      "opening_hook", "paying_intent", "payoff_delivery"
    ]
  }
}
```

**影响**: 
- ✅ 当前所有质量评分都是advisory，不会gate生产
- ✅ 确定性红线（M7原创性、文本完整性）继续有效
- 🔄 等待校准完成（需要至少30个真实样本）后，decision级维度才能gate

---

## ADR-003 对齐

| 类型 | 示例 | 可否gate | 修复前 | 修复后 |
|------|------|---------|--------|--------|
| 确定性红线 | M7原创性、文本完整性 | ✅ 可block | ✅ 正确 | ✅ 正确 |
| 未校准评分 | LLM质量分（无真实样本） | ❌ 仅advisory | ❌ 错误hold | ✅ advisory |
| 校准后评分 | decision级维度（≥30样本） | ✅ 可hold | N/A | ✅ 可hold |
| 人工决策 | 人工审批rejected | ✅ 可block | ✅ 正确 | ✅ 正确 |

**结论**: 修复后完全符合ADR-003（评价性判断不阻断构建，只有硬红线可gate）

---

## 文件变更

### 修改文件
1. `runtime/decision_engine.py` 
   - 添加 `load_calibration_status()`
   - 修改 `decide()` 添加校准状态参数
   - 修改 Priority 6 质量阈值检查逻辑
   - 修改 `align_production_decision()` 添加参数

2. `runtime/production_card.py`
   - 修改 `compute_recommendation()` 加载并传入校准状态

3. `tests/test_decision_engine.py`
   - 更新2个测试添加校准状态

4. `tests/test_production_card_thresholds.py`
   - 更新4个测试，创建模拟校准项目

### 新增文件
5. `tests/test_p0_2_uncalibrated_scores.py` - 8个新测试
6. `docs/P0-2-uncalibrated-scores-fix.md` - 修复方案文档
7. `docs/P0-2-completed.md` - 本报告

---

## 向后兼容性

- ✅ **calibration_status参数可选**: 不传入时，所有评分视为未校准（advisory only）
- ✅ **字节完全兼容**: 确定性生产路径（无质量评分）保持byte-identical
- ✅ **渐进式激活**: 校准完成后，逐个维度升级为decision级
- ✅ **现有测试通过**: 1806个测试全绿

---

## 下一步行动

### 短期（P0完成后）
1. ✅ 通知用户校准状态影响
2. 📋 准备校准计划（至少30个真实样本）
3. 📋 更新文档说明当前所有质量分数为advisory

### 中期（校准完成）
1. 收集至少30个真实章节样本
2. 人工盲评打分
3. 重新计算校准摘要
4. 部分维度升级为decision级
5. 验证decision级维度可正确gate

### 长期（生产优化）
1. 建立定期校准流程
2. 为不同题材/平台建立分层校准
3. 引入分位数阈值替代固定阈值
4. 真实平台数据闭环

---

## 技术细节

### 校准状态结构
```python
{
    "status": str,  # "uncalibrated_..." | "calibrated" | "unknown"
    "trusted_dimensions": List[str],  # 向后兼容
    "decision_dimensions": List[str],  # 可gate的维度
    "diagnostic_dimensions": List[str]  # 仅advisory的维度
}
```

### 决策优先级（Priority 6）
1. 检查维度是否在 `decision_dimensions`
2. 是 → 可以触发hold，带"calibrated"标记
3. 否 → 仅advisory警告，带"uncalibrated, advisory only"标记

### 加载逻辑
```
project_path/
  └─ quality-golden-set/
      └─ metadata/
          └─ w9-calibration-summary.json  ← 读取这里
```

如果文件不存在或JSON无效：
```python
{
    "status": "unknown",
    "decision_dimensions": [],  # 空 = 所有维度advisory
    ...
}
```

---

## 对核验报告的响应

**报告原文**（P0-2）:
> 未校准评分被用于生产决策
> 
> 影响：好章节可能被错误hold，差章节可能被错误放行。
> 
> 处理：
> - 校准前所有LLM分数只允许advisory
> - 确定性红线可以Block
> - 人工校准后的维度才能进入强决策

**响应状态**:
- ✅ 未校准分数降级为advisory
- ✅ 确定性红线继续block
- ✅ 校准后维度可以hold
- ✅ 符合ADR-003
- ✅ 完整测试通过

---

## 提交信息

```
fix: P0-2 uncalibrated scores are advisory only

Uncalibrated LLM quality scores now produce advisory warnings only,
cannot trigger hold/block. Only calibrated decision-level dimensions
can gate production (ADR-003).

Changes:
- Add load_calibration_status() to read w9-calibration-summary.json
- Modify ProductionDecisionEngine.decide() to check calibration status
- Update ProductionCard.compute_recommendation() to load calibration
- Update align_production_decision() to accept calibration_status
- Add 8 new tests for calibration behavior
- Update 6 existing tests to provide calibration status

Current state: all dimensions are diagnostic (advisory only).
After calibration (≥30 real samples), decision dimensions can gate.

Test results: 1806 passed, 0 failed
Fixes: P0-2 from 2026-08-18 capability audit
```

---

## 参考文档

- 修复方案: `docs/P0-2-uncalibrated-scores-fix.md`
- 核验报告: 用户提供的 2026-08-18 核验报告
- 校准状态: `quality-golden-set/metadata/w9-calibration-summary.json`
- ADR-003: 评价性判断永不阻断构建/生产
