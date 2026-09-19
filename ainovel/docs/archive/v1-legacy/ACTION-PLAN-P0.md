# P0 问题处理行动计划

**制定日期**: 2026-08-27  
**目标**: 1周内修复所有P0问题，使项目进入稳定状态

---

## 问题清单

### P0-1: 架构守卫失败 - 3个orphan模块

**状态**: 🔴 FAILED  
**影响**: 破坏built=live原则，可能存在死代码

**失败模块**:
1. `runtime/chapter/quality_gate.py` - A.2质量门控
2. `runtime/genesis/authenticity.py` - 原创性检查增强
3. `runtime/signals/prediction_error.py` - 预测误差分析

---

### P0-2: Promise逾期阻断验证

**状态**: 🟡 SUSPECTED  
**影响**: 如果确认，会导致长篇生产停滞

**需验证**: Promise逾期是否真的会阻止`advance_to_next_chapter`

---

### P0-3: text_integrity大量误报

**状态**: 🟡 SUSPECTED  
**影响**: 35/36章标记为需review，可能是检测器过于严格

**需验证**: 抽样检查是真实问题还是误报

---

## 修复方案详细设计

### 方案1: 处理quality_gate.py

#### 步骤1: 检查模块用途和冗余性

```bash
# 查看quality_gate的设计意图
cat AI-Novel-Runtime/runtime/chapter/quality_gate.py | head -50

# 检查是否已被其他模块覆盖
grep -r "text_integrity\|prose_hygiene\|check_.*gate" AI-Novel-Runtime/runtime/chapter/
```

#### 步骤2A: 如果需要接入

```python
# 在 runtime/chapter/finalizer.py 中添加
from runtime.chapter.quality_gate import check_final_quality_gate

def finalize_chapter(...):
    # 现有代码...
    
    # 添加最终质量门控
    gate_result = check_final_quality_gate(
        chapter_draft=draft,
        text_integrity=integrity_result,
        promise_debt=promise_status,
        continuity=continuity_check
    )
    
    if gate_result.should_block:
        raise QualityGateError(gate_result.reasons)
    
    # 继续现有逻辑...
```

#### 步骤2B: 如果已冗余，移除

```bash
# 将模块移到deprecated/
mkdir -p AI-Novel-Runtime/runtime/deprecated
git mv AI-Novel-Runtime/runtime/chapter/quality_gate.py \
       AI-Novel-Runtime/runtime/deprecated/

# 在deprecated目录添加README
echo "quality_gate.py: 已被text_integrity + prose_hygiene覆盖，于2026-08-27废弃" \
  >> AI-Novel-Runtime/runtime/deprecated/README.md
```

**决策标准**:
- 如果`quality_gate`提供的检查已经在`text_integrity.py`和`prose_hygiene.py`中实现 → 移除
- 如果提供独特的门控逻辑 → 接入

---

### 方案2: 处理genesis/authenticity.py

#### 步骤1: 检查与M7的关系

```bash
# 查看authenticity的功能范围
cat AI-Novel-Runtime/runtime/genesis/authenticity.py | head -50

# 检查M7是否已覆盖
cat AI-Novel-Runtime/runtime/execution/m7.py | head -100
```

#### 步骤2A: 如果与M7互补，接入genesis

```python
# 在 runtime/genesis/generate_novel.py 中添加
from runtime.genesis.authenticity import check_genesis_originality

def generate_novel_from_references(...):
    # 生成设定
    brain = generate_brain(refs)
    outline = generate_outline(brain, refs)
    
    # 原创性检查
    auth_check = check_genesis_originality(
        brain=brain,
        outline=outline,
        references=refs
    )
    
    if auth_check.risk_level == "high":
        # 重新生成或警告
        pass
```

#### 步骤2B: 如果与M7重复，合并或移除

```bash
# 选项1: 合并到M7
# 将authenticity的独特检查移到m7.py

# 选项2: 移除
git mv AI-Novel-Runtime/runtime/genesis/authenticity.py \
       AI-Novel-Runtime/runtime/deprecated/
```

**决策标准**:
- `authenticity` 专注genesis阶段（设定/大纲） + `m7` 专注章节正文 → 接入
- 功能重叠 → 合并

---

### 方案3: 处理signals/prediction_error.py

#### 步骤1: 确认设计意图

```bash
# 查看prediction_error的功能
cat AI-Novel-Runtime/runtime/signals/prediction_error.py | head -50

# 检查是否依赖真实数据
grep -r "reader_signal\|platform_feedback" AI-Novel-Runtime/runtime/signals/
```

#### 步骤2: 根据数据依赖决策

如果**依赖真实平台数据**（很可能）：

```python
# 在 runtime/dashboard/novel_dashboard.py 中添加
from runtime.signals.prediction_error import compute_prediction_error

def generate_dashboard(...):
    # 现有代码...
    
    # 只在有真实数据时计算
    if has_real_signals():
        pred_error = compute_prediction_error(
            predicted=simulated_signals,
            actual=real_signals
        )
        dashboard["prediction_accuracy"] = pred_error
    else:
        dashboard["prediction_accuracy"] = "awaiting_real_data"
```

如果**不依赖真实数据**（仅计算器）：

```bash
# 接入到dashboard的对比视图
# 或移到serialize/目录（如果是离线分析工具）
```

**决策标准**:
- 如果是实时组件 → 接入dashboard，条件启用
- 如果是离线分析 → 移到serialize/
- 如果未来才需要 → 添加到KNOWN_UNREACHABLE allowlist，注释说明

---

### 方案4: 验证Promise逾期逻辑

#### 步骤1: 找到Promise逾期的决策点

```bash
# 查找Promise检查逻辑
grep -r "promise.*overdue\|overdue.*promise" AI-Novel-Runtime/runtime/

# 查找advance_to_next_chapter决策
grep -r "advance_to_next_chapter" AI-Novel-Runtime/runtime/chapter/
```

#### 步骤2: 检查是否阻断

```python
# 预期的正确逻辑（ADR-003）
def decide_advance(chapter_result):
    blockers = []
    
    # 确定性红线可以阻断
    if chapter_result.text_integrity.has_critical_errors:
        blockers.append("text_integrity_failed")
    
    # Promise逾期应该是警告，不阻断
    if chapter_result.promise_status.overdue_count > 0:
        warnings.append("promises_overdue")  # ✅ 不放入blockers
    
    return len(blockers) == 0  # 只有blockers才阻止advance
```

#### 步骤3: 如果发现阻断，修复

```python
# 错误模式（如果存在）
if promise_status.overdue_count > 0:
    return {"advance_to_next_chapter": False}  # ❌ 不应该

# 正确模式
if promise_status.overdue_count > 0:
    warnings.append("promise_debt_high")
    # 但仍然 advance_to_next_chapter = True（如果没有其他blockers）
```

---

### 方案5: 验证text_integrity误报

#### 步骤1: 抽样10个章节

```bash
# 找到被标记为needs_review的章节
cd novel-lingse/registry/derived/chapter-final
grep -l '"status": "review_required"' *.json | head -10 > /tmp/sample.txt

# 或者更精确地找
python3 << 'EOF'
import json, glob
samples = []
for f in sorted(glob.glob("final-TASK-*.json"))[:50]:
    data = json.load(open(f))
    # 需要找到text_integrity字段的实际路径
    # 可能在chapter_run或其他envelope字段中
    if "text_integrity" in str(data):
        samples.append(f)
        if len(samples) >= 10:
            break
print("\n".join(samples))
EOF
```

#### 步骤2: 人工检查样本

对每个样本：
1. 读取正文 (`final_text`)
2. 查看text_integrity的具体警告
3. 判断：真实问题 vs 误报

**常见误报模式**（基于memory）：
- `---` 场景分隔符 → 被误判为word_internal_punctuation
- `（第X章 完）` 模型标记 → 被误判为whitespace_anomaly
- 中文破折号 `——` → 可能触发某些规则

#### 步骤3: 根据结果决策

如果**多数是误报**：
```python
# 修正text_integrity.py的检测器
def check_word_internal_punctuation(text):
    # 排除已知的合法模式
    ALLOWED_PATTERNS = [
        r'^---+$',  # 场景分隔符
        r'（第.{1,5}章.{0,5}完）',  # 章节结束标记
        r'——',  # 中文破折号（不是word-internal）
    ]
    
    for pattern in ALLOWED_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    
    # 然后再检查真正的word-internal punctuation
```

如果**多数是真实问题**：
- 修正生成侧（prompt、模型配置）
- 或添加后处理清理

---

## 执行时间表

### Day 1 (周一)
- [ ] 早上: 检查3个orphan模块的用途和冗余性
- [ ] 下午: 决策每个模块的处理方式（接入/移除/allowlist）
- [ ] 晚上: 实现第一个模块的处理

### Day 2 (周二)
- [ ] 早上: 实现剩余2个模块的处理
- [ ] 下午: 运行架构测试，确认通过
- [ ] 晚上: 提交修复，运行全量测试

### Day 3 (周三)
- [ ] 早上: 验证Promise逾期逻辑
- [ ] 下午: 如果有问题，修复并测试
- [ ] 晚上: 文档更新（ADR-003实践）

### Day 4 (周四)
- [ ] 全天: text_integrity抽样验证
  - 抽取10个样本
  - 人工检查每个
  - 统计误报率

### Day 5 (周五)
- [ ] 早上: 根据抽样结果修复检测器或生成器
- [ ] 下午: 回归测试
- [ ] 晚上: 更新文档，准备P0完成报告

---

## 验收标准

### P0-1: 架构守卫
- [ ] `pytest tests/test_fitness.py::test_architecture_fitness` 通过
- [ ] 3个模块都有明确归属（已接入/已移除/已allowlist+注释）

### P0-2: Promise逻辑
- [ ] 确认Promise逾期是advisory，不阻断
- [ ] 或者证明当前行为是正确的（有文档说明）

### P0-3: text_integrity
- [ ] 抽样10个，误报率 < 30%
- [ ] 如果误报率高，已修复并重新测试

### 整体
- [ ] 全量测试通过率 ≥ 99.9%
- [ ] 文档更新完成
- [ ] P0完成报告已提交

---

## 风险和应急方案

### 风险1: 模块接入引入新bug

**应急**:
- 每个接入都要有单元测试
- 先在test分支验证
- 保留回滚能力

### 风险2: text_integrity修复破坏现有检测

**应急**:
- 保存当前检测器版本
- 新版本应该是现有逻辑 + 例外规则
- A/B测试：旧版本 vs 新版本

### 风险3: Promise逻辑牵涉复杂状态机

**应急**:
- 如果修复风险大，暂时添加文档说明当前行为
- 标记为P1，下个迭代修复
- P0优先保证不破坏现有功能

---

## 沟通计划

### 每日standup
- 完成了什么
- 遇到什么阻塞
- 今天计划

### Day 5 完成报告

包含：
1. 3个模块的最终处理方式
2. Promise逻辑验证结果
3. text_integrity误报率统计
4. 架构测试通过截图
5. 遗留P1问题列表

---

## 参考资料

- ADR-003: 评估性判断永不阻断
- ADR-009: 不可逆操作需人工批准
- Memory: [built≠live instances](built-live-pattern.md)
- CLAUDE.md: Schema-First守门规则
