# 论文阅读笔记

**阅读计划**: 本周完成4篇核心论文  
**总时间**: ~7.5小时  
**状态**: 🟡 待开始  

---

## 📖 阅读清单与时间分配

### 必读（P0，4篇）

| # | 论文 | 时间 | 重点章节 | 状态 |
|---|------|------|---------|------|
| 1 | FactTrack | 2h | Section 3 (Validity Interval) | 🟡 待读 |
| 2 | SCORE | 2h | Section 4-5 (RAG + 结果) | 🟡 待读 |
| 3 | ConStory-Bench | 2h | Section 3-4 (错误分类) | 🟡 待读 |
| 4 | DHO | 1.5h | Section 3 (动态调整) | 🟡 待读 |

---

## 1. FactTrack - Time-Aware World State Tracking

**论文链接**: https://arxiv.org/html/2407.16347v1  
**发表时间**: 2024年7月  
**阅读日期**: ________  
**阅读时长**: ____小时  
**状态**: 🟡 待读  

### 基本信息
- **作者**: 
- **机构**: 
- **发表于**: 

### 核心贡献

**Validity Interval（有效性区间）**:
- 为每个事实追踪有效性区间（validity_start, validity_end）
- 区分"合法变化"vs"非法矛盾"
- 支持角色成长、剧情转折等合法演化

### 关键概念

1. **Validity Interval（有效性区间）**
   - 定义: （待填写）
   - 作用: （待填写）
   - 示例: （待填写）

2. **Fact Superseding（事实替代）**
   - 定义: （待填写）
   - 作用: （待填写）

3. **Timeline Structure（时间线结构）**
   - 定义: （待填写）
   - 优势: （待填写）

### 技术细节

（阅读Section 3后填写）

### 对ANovel的启示

**直接应用**:
- [ ] Fact数据结构增加validity_start/end字段
- [ ] 矛盾检测改为检查有效期重叠
- [ ] 合法变化vs非法矛盾自动区分

**实施位置**:
- `AI-Novel-Runtime/runtime/canon/fact.py`
- `AI-Novel-Runtime/runtime/qa/deterministic/contradiction_checker.py`

**预期收益**:
- 角色成长不再被判定为矛盾
- 剧情转折更自然
- 降低误报率

### 关键引用

（记录关键图表和公式）

---

## 2. SCORE - Story Coherence and Retrieval Enhancement

**论文链接**: https://arxiv.org/html/2503.23512v1  
**发表时间**: 2025年3月  
**阅读日期**: ________  
**阅读时长**: ____小时  
**状态**: 🟡 待读  

### 基本信息
- **作者**: 
- **机构**: 
- **发表于**: 

### 核心贡献

**Temporal RAG（时间对齐的RAG）**:
- 检索时考虑时间有效性
- 时间衰减权重（最近的章节权重更高）
- 上下文注入到生成Prompt

**量化结果**:
- ✅ 连贯性提升 23.6%
- ✅ 幻觉减少 41.8%
- ✅ 情感一致性 89.7%

### 关键概念

1. **Temporally-aligned RAG Pipeline**
   - 定义: （待填写）
   - 工作原理: （待填写）

2. **Time Decay Weight（时间衰减权重）**
   - 公式: （待填写）
   - 参数: （待填写）

3. **Emotional Consistency Tracking**
   - 方法: （待填写）
   - 准确率: 89.7%

### 技术细节

（阅读Section 4后填写）

### 对ANovel的启示

**直接应用**:
- [ ] 实现TemporalRAG类
- [ ] 向量化事实内容
- [ ] 时间窗口检索（优先最近3章）
- [ ] 情感一致性检查

**实施位置**:
- `AI-Novel-Runtime/runtime/memory/temporal_rag.py`
- `AI-Novel-Runtime/runtime/qa/deterministic/emotional_checker.py`

**预期收益**:
- 连贯性提升 >20%
- 幻觉减少 >35%
- 情感一致性 >85%

### 关键引用

（记录关键数据和图表）

---

## 3. ConStory-Bench - Consistency Bugs in Long Story

**论文链接**: http://acl.ldc.upenn.edu/2026.findings-acl.410/  
**发表时间**: 2026年  
**阅读日期**: ________  
**阅读时长**: ____小时  
**状态**: 🟡 待读  

### 基本信息
- **作者**: 
- **机构**: 
- **发表于**: ACL 2026 Findings

### 核心贡献

**5大类19种错误类型体系**:

1. **Factual（事实错误，3种）**
   - entity_attribute_change
   - entity_relation_change
   - entity_disappearance

2. **Temporal（时间错误，4种）**
   - timeline_contradiction
   - event_order_wrong
   - duration_inconsistency
   - season_weather_conflict

3. **Character（角色错误，5种）**
   - personality_drift
   - knowledge_inconsistency
   - goal_change
   - ability_inconsistency
   - speech_pattern_change

4. **World（世界观错误，4种）**
   - rule_violation
   - setting_change
   - power_system_inconsistent
   - technology_level_jump

5. **Plot（剧情错误，5种）**
   - causal_contradiction
   - unresolved_plot_thread
   - premature_resolution
   - impossible_coincidence
   - motivation_missing

**ConStory-Checker（自动检测器）**:
- 为每种错误类型实现检测器
- 提供文本证据
- 返回严重程度

### 关键发现

（阅读Section 3后填写）

1. **错误倾向于出现在叙事中段**
2. **错误倾向于出现在高token熵的文本段**
3. **某些错误类型倾向于共现**

### 对ANovel的启示

**直接应用**:
- [ ] 实现19个错误检测器
- [ ] 每个检测器返回证据
- [ ] 中段章节加强检查
- [ ] Token熵检测

**实施位置**:
- `AI-Novel-Runtime/runtime/qa/deterministic/constory_checker.py`
- 每种错误一个Checker类

**预期收益**:
- 错误检测准确率 >80%
- 误报率 <10%
- 覆盖所有主要错误类型

### 关键引用

（记录错误分类体系图表）

---

## 4. DHO - Dynamic Hierarchical Outlining

**论文链接**: https://arxiv.org/html/2412.13575v1  
**发表时间**: 2024年12月  
**阅读日期**: ________  
**阅读时长**: ____小时  
**状态**: 🟡 待读  

### 基本信息
- **作者**: 
- **机构**: 
- **发表于**: 

### 核心贡献

**Dynamic Hierarchical Outline（动态分层大纲）**:
- 大纲不是固定的，而是动态调整
- 融合规划与写作阶段
- 适应生成过程中的变化

**MEM（Memory-Enhancement Module）**:
- 基于时间知识图谱的记忆增强
- 事件-实体关系图
- 时间索引检索

### 关键概念

1. **Dynamic Outline Adjustment**
   - 定义: （待填写）
   - 触发条件: （待填写）
   - 调整策略: （待填写）

2. **Temporal Knowledge Graph**
   - 结构: （待填写）
   - 检索方法: （待填写）

### 对ANovel的启示

**考虑应用**（M3后）:
- ⚠️ 动态大纲调整（M3前静态大纲）
- ⚠️ 时间知识图谱（M4后考虑）

**实施位置**:
- （M4后再定）

**预期收益**:
- 大纲更灵活
- 记忆检索更强

### 关键引用

（记录动态调整机制图表）

---

## 📊 阅读计划

### 本周计划

**周一**: FactTrack（2小时）
**周二**: SCORE（2小时）
**周三**: ConStory-Bench（2小时）
**周四**: DHO（1.5小时）
**周五**: 总结整理

### 阅读方法

1. **第一遍**：快速浏览全文，理解核心贡献
2. **第二遍**：精读关键章节，记录技术细节
3. **第三遍**：思考对ANovel的启示，设计应用方案

### 输出物

- [ ] 4篇论文笔记完成
- [ ] 关键技术总结文档
- [ ] ANovel应用设计草案

---

## 🔗 相关资源

### 辅助阅读

- **预架构包**: D04-D09
- **架构决策**: 12_PART1-3
- **可执行指南**: 11_FINAL_EXECUTABLE_GUIDE.md

### 讨论问题

（阅读过程中记录疑问）

---

**最后更新**: 2026-09-18  
**下次更新**: 阅读第一篇论文后
