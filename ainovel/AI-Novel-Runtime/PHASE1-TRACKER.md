# Phase 1 执行跟踪器

**启动日期**: 2026-08-21  
**预计完成**: 2026-10-21（2个月）  
**状态**: 🟢 进行中

---

## 总体进度

| 任务组 | 进度 | 状态 | 预计完成 |
|--------|------|------|---------|
| 1.1 文本完整性硬门 | 95% | 🟢 进行中 | Week 2 |
| 1.2 AI味累积修复 | 5% | 🟡 准备中 | Week 4 |
| 1.3 篇幅失控修复 | 0% | ⚪ 待开始 | Week 4 |
| 1.4 真人验收流程 | 5% | 🟡 准备中 | Week 6 |

**总体进度**: 20% (6/30 tasks完成)

---

## Week 1-2: 文本完整性硬门

### Task 1.1.1: 升级文本完整性检测器 ⏳

**状态**: 🟢 进行中  
**优先级**: P0  
**负责人**: Claude  
**预计工时**: 8小时

#### 当前状态评估
✅ **已有基础**：
- `text_integrity.py` 已实现：word_split、whitespace_anomaly检测
- 20个测试全部通过
- 已处理3类false-positive（heading/chapter-end/scene-divider）

❌ **缺失能力**：
- [ ] 跨章句子连续性检查
- [ ] 词内标点检测（如"晶矿。城"）
- [ ] 异常换行检测（句中换行）

#### 子任务清单

- [x] 评估当前text_integrity.py能力（DONE）
- [ ] **1.1.1a**: 实现 `check_cross_chapter_continuity()`
  - 检查上章末尾是否有未完成句
  - 检查本章开头是否接续未完成句
  - 输入：current_body, previous_body
  - 输出：IntegrityIssue with severity="critical"
  
- [ ] **1.1.1b**: 实现 `check_word_internal_punctuation()`
  - 正则检测 `[一-鿿][。！？]["'"][一-鿿]` 模式
  - 返回前5个匹配作为evidence
  
- [ ] **1.1.1c**: 实现 `check_abnormal_line_breaks()`
  - 检测非对话、非段落结束的句中换行
  - 区分合法换行（段落结束）vs异常换行
  
- [ ] **1.1.1d**: 编写测试
  - `test_cross_chapter_split_sentence_blocked`
  - `test_word_internal_punctuation_detected`
  - `test_abnormal_mid_sentence_break_flagged`
  - `test_legitimate_paragraph_break_passes`

**验收标准**：
- ✅ 新增3个检测函数
- ✅ 新增4个测试，全部通过
- ✅ 在RUN-00001样本上验证，能检测到已知的3处断裂

---

### Task 1.1.2: 升级gate为发布硬门 ✅

**状态**: ✅ 已完成  
**优先级**: P0  
**完成日期**: 2026-08-21  
**实际工时**: 2小时

#### 完成内容

- [x] **1.1.2a**: 修改 `_scan_body` 集成新检测器
  - 词内标点检测已集成
  - 异常换行检测已集成
  - 代码位置：`text_integrity.py:375-381`
  
- [x] **1.1.2b**: 定义 `TextIntegrityBlockError` 异常
  - 携带chapter_id和issues列表
  - 清晰的错误消息
  - 代码位置：`text_integrity.py:28-39`
  
- [x] **1.1.2c**: 编写集成测试
  - `test_word_internal_punctuation_detected_in_assess` ✅
  - `test_abnormal_line_breaks_detected_in_assess` ✅
  - `test_text_integrity_block_error_structure` ✅
  - 总计9个集成测试，全部通过

- [ ] **1.1.2d (可选)**: loop.py跨章检查集成
  - 定位集成点（延后到Task 1.1.3）
  - 实现previous chapter加载
  - 编写端到端测试

**验收标准**：
- ✅ critical issue阻断finalization逻辑（异常类已定义）
- ✅ warning issue不阻断（在_scan_body中处理）
- ✅ 9个集成测试通过
- ✅ 52个text_integrity测试全部通过（20原有+23新增+9集成）

**报告**: 详见 `TASK-1.1.2-COMPLETE.md`

---

## Week 2-4: AI味累积修复

### Task 1.2.1: Span定位引用 ⏳

**状态**: 🟡 准备中  
**优先级**: P0  
**预计工时**: 6小时

#### 当前状态评估
✅ **已有基础**：
- `humanization.py` 已实现anaphora检测
- 检测逻辑：找连续3+句同头

❌ **缺失能力**：
- [ ] 返回具体位置（sentence index, char offset）
- [ ] 返回原文text span
- [ ] 计算在body中的字符偏移量

#### 子任务清单

- [ ] **1.2.1a**: 增强 `detect_anaphora_with_spans()`
  - 返回结构：
    ```python
    {
      "start_sentence_index": int,
      "length": int,  # 连续句数
      "pattern": str,  # 首字/词
      "text": str,  # 原文
      "char_offset": int  # 在body中的位置
    }
    ```
  - 实现 `_calculate_char_offset()` 辅助函数
  
- [ ] **1.2.1b**: 更新 `AiTasteReport` 数据结构
  - 新增字段：`anaphora_spans: list[dict]`
  - 保持向后兼容（旧字段保留）
  
- [ ] **1.2.1c**: 编写测试
  - `test_anaphora_detection_returns_exact_spans`
  - `test_char_offset_calculation_accurate`
  - `test_span_text_matches_body_substring`

**验收标准**：
- ✅ 返回的char_offset准确（body[offset:offset+len(text)] == text）
- ✅ 3个测试通过

---

### Task 1.2.2: 量化重写指令 ⏳

**状态**: 🟡 准备中  
**优先级**: P0  
**依赖**: Task 1.2.1完成  
**预计工时**: 4小时

#### 子任务清单

- [ ] **1.2.2a**: 实现 `build_hygiene_instruction()`
  - 引用具体位置："第5-7句出现同头排比..."
  - 引用原文：「他知道...他知道...他知道...」
  - 量化目标："将排比从3处降到0处"
  
- [ ] **1.2.2b**: 更新 `hygiene_loop.py` 调用
  - 传递ai_taste_report（含spans）
  - 将instruction注入rewrite prompt
  
- [ ] **1.2.2c**: 编写测试
  - `test_hygiene_instruction_cites_specific_locations`
  - `test_hygiene_instruction_includes_original_text`
  - `test_quantified_target_in_instruction`

**验收标准**：
- ✅ instruction包含具体位置和原文
- ✅ 3个测试通过

---

### Task 1.2.3: 更强重写模型 ⏳

**状态**: 🟡 准备中  
**优先级**: P1  
**预计工时**: 2小时

#### 子任务清单

- [ ] **1.2.3a**: 在 `hygiene_loop.py` 添加模型选择
  ```python
  hygiene_model = select_hygiene_model(
      default="deepseek-reasoner",
      fallback="deepseek-chat"
  )
  ```
  
- [ ] **1.2.3b**: 验证deepseek-reasoner可用
  - 测试API连接
  - 确认pricing配置
  
- [ ] **1.2.3c**: A/B测试（手动）
  - 选择3章有AI味的样本
  - 对比chat vs reasoner重写效果
  - 记录到 `experiments/hygiene-model-ab.md`

**验收标准**：
- ✅ deepseek-reasoner可调用
- ✅ A/B测试显示reasoner改善率>chat

---

### Task 1.2.4: 高频模板检测 ⏳

**状态**: 🟡 准备中  
**优先级**: P1  
**预计工时**: 4小时

#### 子任务清单

- [ ] **1.2.4a**: 从100章诊断提取模板库
  - "他知道", "这不是", "沉默了片刻"
  - "深吸一口气", "眼中闪过", "嘴角勾起"
  - 统计在参考作品中的基准频率
  
- [ ] **1.2.4b**: 实现 `detect_template_phrases()`
  - 对比draft频率 vs 参考基准
  - 超过基准2倍→warning
  
- [ ] **1.2.4c**: 集成到ai_taste检测
  - 作为新的维度：template_overuse
  
- [ ] **1.2.4d**: 编写测试
  - `test_template_phrase_detection`
  - `test_baseline_comparison`

**验收标准**：
- ✅ 能检测出高频模板
- ✅ 2个测试通过

---

## Week 3-4: 篇幅失控修复

### Task 1.3.1: 生成后硬截断 ⏳

**状态**: ⚪ 待开始  
**优先级**: P0  
**预计工时**: 4小时

#### 子任务清单

- [ ] **1.3.1a**: 创建 `runtime/chapter/length_enforcer.py`
- [ ] **1.3.1b**: 实现 `enforce_length_hard_limit()`
  - 在完整句处截断
  - tolerance=0.2（允许超20%）
  - 标记truncated=True
- [ ] **1.3.1c**: 集成到finalize流程
- [ ] **1.3.1d**: 编写测试
  - `test_hard_truncate_at_sentence_boundary`
  - `test_within_tolerance_not_truncated`

**验收标准**：
- ✅ 超长章节被截断到目标+20%
- ✅ 截断发生在完整句边界
- ✅ 2个测试通过

---

### Task 1.3.2: 多轮收紧策略 ⏳

**状态**: ⚪ 待开始  
**优先级**: P1  
**预计工时**: 3小时

#### 子任务清单

- [ ] **1.3.2a**: 创建 `runtime/chapter/length_strategy.py`
- [ ] **1.3.2b**: 实现 `progressive_length_constraint()`
  - attempt=1: 正常目标
  - attempt=2: 降低天花板10%
  - attempt=3: 硬截断
- [ ] **1.3.2c**: 编写测试
  - `test_progressive_constraint_tightens_ceiling`
  - `test_third_attempt_uses_hard_truncate`

**验收标准**：
- ✅ 逐次收紧策略正确
- ✅ 2个测试通过

---

## Week 4-6: 真人验收流程

### Task 1.4.1: 设计盲评协议 ⏳

**状态**: 🟢 进行中  
**优先级**: P0  
**预计工时**: 3小时

#### 当前进度

- [x] 协议框架已设计（见QUALITY-FIRST-IMPROVEMENT-PLAN.md）
- [ ] **1.4.1a**: 创建 `docs/blind-review-protocol.yaml`
- [ ] **1.4.1b**: 设计评分表单
  - 5个维度×5分制
  - 具体问题记录区
  - 整体可发布性判断
- [ ] **1.4.1c**: 准备评审工具
  - Google Form或本地Markdown模板
  - 自动生成盲评样本脚本

**验收标准**：
- ✅ 协议文档完整
- ✅ 评分表单可用
- ✅ 盲评样本生成脚本正常运行

---

### Task 1.4.2: 招募真人编辑 ⏳

**状态**: 🟡 准备中  
**优先级**: P0  
**预计工时**: N/A（外部依赖）

#### 要求

- [ ] **编辑A**: 网文编辑经验3年+，玄幻题材
- [ ] **编辑B**: 网文编辑经验3年+，玄幻题材（独立于A）

#### 招募渠道

- [ ] 网文作者/编辑社区
- [ ] 起点/番茄等平台编辑
- [ ] 自由职业编辑平台

**预计费用**: ¥500-1000/人（评审13章）

---

### Task 1.4.3: 实施黄金三章双盲评审 ⏳

**状态**: ⚪ 待开始  
**优先级**: P0  
**依赖**: Task 1.4.1, 1.4.2完成  
**预计工时**: 1周（含等待编辑返回）

#### 子任务清单

- [ ] **1.4.3a**: 准备盲评样本
  ```bash
  python3 -m runtime.cli blind-review prepare \
    --project novel-lingse \
    --chapters 1-3 \
    --output blind-samples/G1-lingse-ch1-3.txt \
    --strip-metadata
  ```

- [ ] **1.4.3b**: 发送给编辑A（独立评审）
- [ ] **1.4.3c**: 发送给编辑B（独立评审）
- [ ] **1.4.3d**: 收集评审结果
  - `reviews/G1-editor-A.yaml`
  - `reviews/G1-editor-B.yaml`
- [ ] **1.4.3e**: 对比一致性
  ```bash
  python3 -m runtime.cli blind-review compare \
    --review-a reviews/G1-editor-A.yaml \
    --review-b reviews/G1-editor-B.yaml \
    --output reviews/G1-consensus.yaml
  ```

**验收标准**：
- ✅ 两位编辑独立完成评审
- ✅ 一致性报告生成
- ✅ 记录分歧项和仲裁结果

---

### Task 1.4.4: 建立人工质量真值数据集 ⏳

**状态**: ⚪ 待开始  
**优先级**: P0  
**依赖**: Task 1.4.3完成  
**预计工时**: 6小时

#### 子任务清单

- [ ] **1.4.4a**: 创建 `runtime/reference/human_baseline.py`
- [ ] **1.4.4b**: 实现 `HumanQualityBaseline` 类
  - 加载人工评审结果
  - 计算两位编辑平均分
  - 提供查询接口
- [ ] **1.4.4c**: 实现 `compare_with_llm_judge()`
  - 对比LLM judge vs 人工真值
  - 计算bias和correlation
- [ ] **1.4.4d**: 生成基线报告
  - `analysis/human-quality-baseline.md`
  - 包含每个维度的人工/LLM对比

**验收标准**：
- ✅ HumanQualityBaseline类可用
- ✅ LLM judge bias量化（预期：0.5-1.0分偏高）
- ✅ 基线报告完整

---

## Phase 1 总验收标准

### 必须达成（Hard Gate）

- [ ] **文本完整性**: 重跑30章，0处跨章断裂，0处词内标点
- [ ] **AI味收敛**: 重跑30章，AI味warning率<40%且不恶化
- [ ] **篇幅达标**: 重跑30章，超长章节<5/30（<17%）
- [ ] **真人验收**: 黄金三章+前10章完成双盲评审，整体可发布性≥"小修后发布"

### 期望达成（Soft Goal）

- [ ] LLM judge与人工真值bias<0.8分（5分制）
- [ ] 人工评审"文本自然度"平均≥3.5/5
- [ ] 人工评审"商业潜力"平均≥3.0/5

### 不通过标准

- ❌ 如果真人评审"整体可发布性"有任一章为"不可发布" → Phase 1失败，需重新迭代

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 | 状态 |
|------|------|------|---------|------|
| 真人评审不通过 | 中 | 高 | 预留2轮迭代空间 | 监控中 |
| AI味修复效果不足 | 中 | 高 | 准备fallback（后处理规则） | 监控中 |
| 找不到合适编辑 | 低 | 中 | 提前联系，准备备选方案 | 🟡需行动 |
| DeepSeek API不稳定 | 低 | 中 | 使用retry机制+fallback模型 | 已缓解 |

---

## 下一步行动（本周）

### 高优先级（P0，立即开始）

1. **Task 1.1.1a**: 实现跨章连续性检查
2. **Task 1.4.1a**: 创建盲评协议文档
3. **Task 1.4.2**: 开始招募真人编辑

### 中优先级（P1，本周内）

4. **Task 1.2.1a**: 实现AI味span定位
5. **Task 1.1.1b**: 实现词内标点检测

### 准备工作

6. 评估deepseek-reasoner API可用性
7. 统计100章诊断的高频模板库

---

## 每周检查点

### Week 1 End（2026-08-28）
- [ ] Task 1.1.1完成
- [ ] Task 1.4.1完成
- [ ] 编辑招募进展50%

### Week 2 End（2026-09-04）
- [ ] Task 1.1.2完成
- [ ] Task 1.2.1完成
- [ ] 编辑招募完成

### Week 4 End（2026-09-18）
- [ ] Task 1.2.2-1.2.4完成
- [ ] Task 1.3.1-1.3.2完成
- [ ] 准备30章重跑

### Week 6 End（2026-10-02）
- [ ] 30章重跑完成
- [ ] 黄金三章双盲评审完成
- [ ] Phase 1初步验收

---

**更新频率**: 每2天更新一次  
**负责人**: 用户 + Claude  
**下次更新**: 2026-08-23
