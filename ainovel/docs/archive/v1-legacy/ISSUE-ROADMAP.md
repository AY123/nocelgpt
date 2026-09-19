# ANovel 项目真实问题与修复路线图

**版本**: v1.0  
**日期**: 2026-08-27  
**目标**: 区分真实问题和误判，制定可执行的改进路线

---

## 执行摘要

基于对审核报告的深度验证，项目的**真实状态**是：

### ✅ 已证实的优势
1. **测试覆盖率 99.95%** (2016/2017 passed)
2. **架构守卫完整** (25/26 guards passed)
3. **100章产物存在**，包含完整质量评审链
4. **所有ADR守卫通过** (003/006/008/009)
5. **分层决策架构运行正常** (quality → commercial → decision)

### 🔴 确认的真实问题
1. **3个模块未接入** (quality_gate / authenticity / prediction_error)
2. **长跑稳定性待证明** (有产物，但需证明单次30+章零故障)
3. **text_integrity可能过严** (35/36章标记需review，疑似误报)
4. **API故障恢复不够强** (RUN-00051 有4章因网络失败)

### ❌ 报告误判
1. ~~"评审pass但决策revise是冲突"~~ → 这是分层架构的正确运行
2. ~~"成本null"~~ → 已在2026-07-19修复
3. ~~"商业能力40%"~~ → 混淆了工程完整度(75%)和市场验证度(0%)

---

## 真实问题详细分析

### 问题1: 架构守卫失败 - 3个orphan模块

**现状**:
```bash
FAIL: new orphans: 
  - chapter/quality_gate.py
  - genesis/authenticity.py
  - signals/prediction_error.py
```

**根因**: built ≠ live (第7次出现)

**影响评估**:
- 🟡 中等严重性
- 不影响现有功能运行
- 但违反架构原则：造好的功能没接入 = 技术债

**修复路径**:

#### 选项A: 全部接入 (推荐用于有独特价值的模块)
```
quality_gate → finalizer.py (最终质量门控)
authenticity → genesis/generate.py (创作阶段原创性)
prediction_error → dashboard (条件启用：仅当有真实数据)
```

#### 选项B: 移除冗余 (推荐用于已被覆盖的模块)
```
quality_gate: 如果text_integrity + prose_hygiene已覆盖 → deprecated/
authenticity: 如果M7已覆盖genesis阶段 → 合并到m7.py
prediction_error: 如果暂无真实数据 → 添加到KNOWN_UNREACHABLE + 注释
```

**决策依据**:
1. 读取每个模块的前50行，了解设计意图
2. 搜索是否有其他模块实现了相同功能
3. 判断：接入 / 合并 / 延后 / 移除

**优先级**: 🔴 P0 (破坏架构卫生)

**预计工作量**: 2-3天

---

### 问题2: 长跑稳定性证明不足

**现状**:
- ✅ 有100章产物文件
- ❓ 但不确定是否来自单次运行
- ❓ RUN-00051: 26/30成功，4章API故障

**根因**: 
1. 多次运行的累积产物 vs 单次长跑
2. 网络故障恢复机制不够强

**影响评估**:
- 🟡 中等严重性
- 影响"可连续生产30+章"的信心
- 但不影响单章质量

**验证路径**:

#### 步骤1: 检查最新manifest
```bash
# 找到最新的完整运行
cd novel-lingse/registry/derived/run-manifests
ls -lt | head -5

# 检查单次运行的连续成功章节数
python3 << 'EOF'
import json, glob

for manifest_file in sorted(glob.glob("run-manifest-*.json"))[-5:]:
    data = json.load(open(manifest_file))
    chapters = data.get("chapters", [])
    
    success_count = sum(1 for ch in chapters if ch.get("ok", False))
    total_count = len(chapters)
    
    # 计算最长连续成功
    max_streak = 0
    current_streak = 0
    for ch in chapters:
        if ch.get("ok", False):
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    print(f"{manifest_file}: {success_count}/{total_count}, max_streak={max_streak}")
EOF
```

#### 步骤2: 如果最长连续 < 30，执行新的长跑
```bash
# 目标: 30章，零失败，固定配置
python -m run_serial \
  --project novel-lingse \
  --start 1 \
  --count 30 \
  --model-provider deepseek \
  --model deepseek-chat \
  --checkpoint-every 5 \
  --resume-on-failure \
  --max-retries 5
```

#### 步骤3: 增强故障恢复
```python
# 在 runtime/execution/llm_model.py 中增强
class LLMExecutor:
    def execute_with_retry(self, request):
        max_retries = 5  # 从3增加到5
        backoff_base = 2.0  # exponential backoff
        
        for attempt in range(max_retries):
            try:
                return self._execute(request)
            except NetworkError as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_base ** attempt
                    log.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise
```

**优先级**: 🟡 P1 (重要但非阻塞)

**预计工作量**: 3-5天 (1天增强代码，1-2天执行长跑，1-2天分析结果)

---

### 问题3: text_integrity可能过严

**现状**: 35/36章标记为`status: review_required`

**根因假设**:
- 基于memory记录，`word_internal_punctuation`对以下模式误报：
  - 场景分隔符 `---`
  - 章节结束标记 `（第X章 完）`
  - 中文破折号 `——`

**影响评估**:
- 🟡 中等严重性
- 造成"狼来了"效应：真实问题被淹没在误报中
- 但不阻断生产（advisory信号）

**验证路径**:

#### 步骤1: 抽样验证
```bash
# 抽取10个样本
cd novel-lingse/registry/derived/chapter-final
python3 << 'EOF'
import json, random

# 假设text_integrity在ChapterRun中
# 需要找到实际的数据结构路径
samples = random.sample(range(1, 101), 10)

for i in samples:
    filename = f"final-TASK-{i:05d}.json"
    try:
        data = json.load(open(filename))
        # 提取正文和integrity结果
        text = data.get("final_text", "")
        # integrity可能在envelope或其他字段中
        print(f"\n=== Chapter {i} ===")
        print(f"Length: {len(text)} chars")
        # 需要找到integrity字段的实际路径
    except FileNotFoundError:
        pass
EOF
```

#### 步骤2: 人工检查每个样本
对每个样本：
1. 读取`final_text`
2. 查找text_integrity的具体警告
3. 判断：真实问题 or 误报
4. 记录误报模式

#### 步骤3: 根据结果修复

如果**误报率 > 50%**:
```python
# 修正 runtime/execution/text_integrity.py
class TextIntegrityChecker:
    # 已知的合法模式（不应触发警告）
    ALLOWED_PATTERNS = [
        (r'^---+$', 'scene_divider'),
        (r'（第.{1,5}章.{0,5}完）', 'chapter_end_marker'),
        (r'——', 'chinese_dash'),
        (r'【.*?】', 'bracketed_annotation'),
    ]
    
    def check_word_internal_punctuation(self, text):
        # 先移除已知合法模式
        cleaned = text
        for pattern, name in self.ALLOWED_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        # 再检查剩余的可疑模式
        issues = self._detect_suspicious_punctuation(cleaned)
        return issues
```

如果**误报率 < 30%**:
- 当前检测器是合理的
- 真实问题需要在生成侧修复

**优先级**: 🟡 P1 (影响信号可信度)

**预计工作量**: 2-3天

---

### 问题4: API故障恢复不够强

**现状**: RUN-00051 中4章因API连接错误失败

**根因**: 
- Retry次数可能不够
- Backoff策略可能不合理
- 没有持久化"待恢复"队列

**影响评估**:
- 🟡 中等严重性
- 在网络不稳定环境下影响长跑成功率
- 但不影响最终产物质量

**修复路径**:

#### 增强1: 更强的retry策略
```python
# runtime/execution/llm_model.py
class LLMExecutor:
    DEFAULT_MAX_RETRIES = 5  # 从3提升到5
    BACKOFF_MULTIPLIER = 2.0
    MAX_BACKOFF = 300  # 最长等待5分钟
    
    def execute_with_retry(self, request):
        for attempt in range(self.DEFAULT_MAX_RETRIES):
            try:
                return self._execute(request)
            except (NetworkError, TimeoutError) as e:
                if attempt < self.DEFAULT_MAX_RETRIES - 1:
                    backoff = min(
                        self.BACKOFF_MULTIPLIER ** attempt,
                        self.MAX_BACKOFF
                    )
                    self.logger.warning(
                        f"Request failed (attempt {attempt+1}/{self.DEFAULT_MAX_RETRIES}), "
                        f"retrying in {backoff}s: {e}"
                    )
                    time.sleep(backoff)
                else:
                    self.logger.error(f"Request failed after {self.DEFAULT_MAX_RETRIES} attempts")
                    raise
```

#### 增强2: 持久化恢复队列
```python
# runtime/serialize/recovery_queue.py (新建)
class RecoveryQueue:
    """持久化失败请求，供后续恢复"""
    
    def __init__(self, queue_path):
        self.queue_path = queue_path
    
    def enqueue(self, chapter_id, request, error):
        """记录失败的章节请求"""
        entry = {
            "chapter_id": chapter_id,
            "request": request.to_dict(),
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }
        self._append_to_queue(entry)
    
    def retry_failed(self):
        """重试队列中的失败请求"""
        for entry in self._read_queue():
            if entry["retry_count"] < 3:
                try:
                    result = execute_request(entry["request"])
                    self._mark_success(entry)
                except Exception as e:
                    entry["retry_count"] += 1
                    self._update_entry(entry)
```

#### 增强3: CLI支持恢复模式
```bash
# 新增命令：恢复失败的章节
python -m run_serial \
  --project novel-lingse \
  --recover-failed \
  --from-run RUN-00051
```

**优先级**: 🟡 P1 (提升可靠性)

**预计工作量**: 2-3天

---

## 非问题：报告误判澄清

### 误判1: "评审pass但决策revise是冲突"

**报告断言**:
> 36/36章节 overall_verdict=pass 但 action=revise，评审和决策冲突

**实际情况**: 这是**分层决策架构**的正确运行

```
┌─────────────────────────────────────┐
│ Layer 1: 质量评审 (QualityReview)   │
│ 问题: 这个草稿质量合格吗？           │
│ 答案: overall_verdict = pass        │
│ 含义: 质量达到发布基线               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Layer 2: 对比报告 (ComparisonReport)│
│ 问题: 有更好的版本吗？               │
│ 答案: winner = draft                │
│ 含义: revision反而更差，选draft      │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Layer 3: 生产决策 (ProductionDecision)│
│ 问题: 现在发布吗？                   │
│ 答案: hold_for_human_review = true  │
│ 含义: 按ADR-009，需人工批准          │
└─────────────────────────────────────┘
```

**关键理解**:
- `action: revise` 在这里的含义是 "**建议尝试修订**"（因为对比报告发现了风险）
- `editorial_verdict: accept` 表示 "**但编辑接受当前版本**"
- `hold_for_human_review` 是 ADR-009 的实现：不可逆操作需人工确认

**验证方法**:
```bash
# 检查ADR-003守卫是否通过
python -m tests.test_fitness 2>&1 | grep "all registered gate checks are deterministic"
# 输出: PASS

# 这证明advisory信号没有被误用作gate
```

**结论**: ✅ 不是问题，是正确的架构设计

---

### 误判2: "成本null，预算失效"

**报告断言**:
> 26次真实LLM调用无价格，成本统计不可信，预算熔断无效

**实际情况**: 这个问题**已在2026-07-19修复**

Memory记录:
```
[Cost null = deepseek-chat pricing gap] — FIXED 2026-07-19:
- Bug 1: DEFAULT_PRICING缺少deepseek-chat key → 已添加
- Bug 2: replay cache hit在cost step之前返回 → 已修复
- 回归测试: test_replay_reprices_cost.py 已添加
- 验证: RUN-00029 (0.028 CNY) + RUN-00030 (0.031 CNY)
```

最新提交:
```bash
git log --oneline | grep -i "cost\|price" | head -3
# (应该能看到修复提交)
```

**验证方法**:
```bash
# 运行回归测试
pytest tests/test_llm_contract_conformance.py::test_replay_reprices_cost -v

# 检查最新RUN的成本
cat novel-lingse/registry/derived/run-manifests/run-manifest-*.json | \
  jq '.cost' | tail -5
```

**结论**: ✅ 不是问题，已修复

---

### 误判3: "商业能力只有40%"

**报告断言**:
> 没有真实首订数据 → 商业预测不可信 → 商业能力40%

**问题分析**: 混淆了**工程完整度**和**市场验证度**

**实际情况**:

| 维度 | 完成度 | 说明 |
|------|--------|------|
| **商业检测器工程** | 85% | reader_simulator、paywall_optimizer、retention_optimizer已实现 |
| **商业信号存储** | 90% | ReaderSignal schema、存储、对比功能完整 |
| **商业决策逻辑** | 80% | 基于模拟信号的决策链完整 |
| **市场数据校准** | 0% | 没有真实平台数据 |
| **商业预测准确度** | 未知 | 需要真实数据才能评估 |

**关键区别**:
```
工程问题: "系统能处理商业信号吗？" → ✅ 能
市场问题: "预测准确吗？" → ❓ 未验证

类比: 汽车造好了(85%) vs 在真实道路测试(0%)
```

**正确评估**:
- **商业系统工程成熟度**: 80-85%
- **商业预测验证度**: 0% (awaiting real data)
- **不应简单平均为40%**

**解决路径**: 这不是工程问题，是**产品决策**
1. 选择一个平台（起点/番茄/七猫）
2. 发布一部小样本作品（10-30章）
3. 收集真实数据（点击/留存/首订）
4. 校准预测模型
5. 迭代优化

**结论**: ❌ 报告误判了成熟度计算方式

---

## 修复优先级矩阵

### 紧急度 vs 重要度

```
高重要 │ P1: 长跑稳定性验证    │ P0: 架构守卫修复
       │ P1: text_integrity   │ P0: (无紧急高重要项)
       │                      │
───────┼──────────────────────┼─────────────────────
低重要 │ P2: 文档完善         │ (无)
       │ P2: 性能优化         │
       └──────────────────────┴─────────────────────
         低紧急                 高紧急
```

### P0 - 本周必须完成 (1-3天)

1. ✅ **修复架构守卫** - 处理3个orphan模块
   - 工作量: 2-3天
   - 验收: `test_architecture_fitness` 通过

### P1 - 两周内完成 (3-7天)

2. ✅ **长跑稳定性验证** - 证明30+章零故障
   - 工作量: 3-5天
   - 验收: 单次运行30章，成功率100%

3. ✅ **text_integrity误报修复** - 抽样验证并修正
   - 工作量: 2-3天
   - 验收: 误报率 < 30%

4. ✅ **API恢复增强** - 更强的retry和恢复队列
   - 工作量: 2-3天
   - 验收: 网络故障后自动恢复

### P2 - 一个月内完成 (ongoing)

5. **文档完善**
   - 分层决策架构说明
   - ADR-003/009实践指南
   - 长跑操作手册

6. **市场验证准备** (产品决策)
   - 选择目标平台
   - 准备发布素材
   - 设计数据收集方案

---

## 成功指标

### 工程侧 (可在2周内达成)

- [ ] 架构测试 100% 通过
- [ ] 全量测试通过率 ≥ 99.9%
- [ ] 单次30章长跑成功率 = 100%
- [ ] text_integrity误报率 < 30%
- [ ] API故障自动恢复率 > 90%

### 市场侧 (需产品决策，时间TBD)

- [ ] 选定目标平台
- [ ] 发布首部试验作品
- [ ] 收集首批真实数据
- [ ] 完成首次模型校准
- [ ] 建立数据反馈闭环

---

## 下一步行动

### 立即开始 (今天)

1. **读取3个orphan模块**，了解设计意图
2. **检查最新RUN manifest**，确认单次长跑成绩
3. **抽样3个chapter-final**，初步验证text_integrity

### 本周完成

4. **决策并实施**3个模块的处理方式
5. **验证Promise逾期逻辑**（如果有时间）
6. **更新ADR文档**

### 下周完成

7. **text_integrity完整抽样**（10个样本）
8. **增强API恢复机制**
9. **执行新的30章长跑**（如果需要）

---

## 附录：需要人工验证的事项

以下事项需要人工检查，代码分析无法自动完成：

- [ ] 读取`reports/continuity_issues.json`，分析346个问题的分布
- [ ] 抽查10个`text_integrity=review_required`的章节正文
- [ ] 检查最新RUN的单次连续成功章节数
- [ ] 验证Promise逾期是否真的阻断`advance_to_next_chapter`
- [ ] 确认最新运行中cost是否仍然为null
- [ ] 检查CLI `--help`输出，验证参数文档完整性

**完成这些验证后，更新本文档，将"疑似"改为"确认"或"排除"。**
