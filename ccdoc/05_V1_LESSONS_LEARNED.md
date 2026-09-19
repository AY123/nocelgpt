# 从 V1 提取的核心经验教训

**文档目的**: 总结 ANovel V1 的成功经验与失败教训，确保 V2 不重蹈覆辙  
**信息来源**: Project Constitution、ROADMAP.md、CLAUDE.md、审计报告  
**制定日期**: 2026-09-18  

---

## 一、V1 成功经验（必须继承）

### 1.1 State as Projection

**经验描述**:
```
StoryState@N = fold(facts, events[1..N])
```

状态是事实的投影，可重建，不是可变对象。

**为什么正确**:
- ✅ 任意时刻的状态可重新计算
- ✅ 不需要维护复杂的状态更新逻辑
- ✅ 便于调试和回溯
- ✅ 支持"如果当时这样会怎样"的假设分析

**V2 继承方式**:
- 保持 `runtime/memory/state.py` 的投影逻辑
- StoryState 永远是只读的
- 想改变状态 = 添加新事实，然后重新投影

**反面教训**: V1 初期曾尝试直接修改 State 对象，导致状态不一致，后来才改为投影模式。

---

### 1.2 No Consumer = Stub

**经验描述**:
> 没有真实消费者的模块/Schema/Report 不得标记"能力完成"

**为什么正确**:
- ✅ 防止堆积死代码
- ✅ 强制思考"这个模块真的有用吗？"
- ✅ 避免虚假进度感
- ✅ 保持代码库健康

**V1 教训**:
- 曾有 10+ 个 Schema 定义了但从未被使用
- 多个 Agent 实现了但从未被调用
- 报告系统生成了几十种报告，但没人读

**V2 执行纪律**:
```python
# ✅ 正确方式
def add_new_capability():
    # 1. 先有消费者
    consumer = implement_consumer()
    
    # 2. 再实现能力
    capability = implement_capability()
    
    # 3. 接线
    consumer.use(capability)
    
    # 4. 验证真的用上了
    assert capability.was_called()

# ❌ 错误方式
def add_new_capability():
    # 实现了一个能力
    capability = implement_capability()
    
    # 但没有消费者
    # 就标记"完成"
    mark_as_done()  # ❌ 这是 stub
```

---

### 1.3 Fail-Closed Production

**经验描述**:
> Production 模式默认阻断而非通过，缺关键信息、约束失败时必须 BLOCK

**为什么正确**:
- ✅ 防止错误蔓延（坏章节不生成后续章节）
- ✅ 早发现早修复
- ✅ 保护长期质量
- ✅ 避免浪费成本（不继续生成注定要删的内容）

**V1 教训**:
- 早期是 Fail-Open：缺 Contract 就跳过，找不到实体返回 None
- 结果积累了大量低质量章节
- 后期改为 Fail-Closed 后，问题在生成初期就被拦截

**V2 执行纪律**:
```python
# ✅ Fail-Closed（正确）
def produce_chapter(chapter_num):
    # 缺 GenrePack → BLOCK
    if not genre_pack:
        raise MissingGenrePackError("Production requires genre pack")
    
    # 约束违反 → BLOCK
    if genre_violations:
        raise GenreViolationError(violations)
    
    # BLOCKED 状态 → 不继续
    if decision.status == "BLOCKED":
        return None  # 不生成后续章节
    
    return draft

# ❌ Fail-Open（错误）
def produce_chapter(chapter_num):
    # 缺 GenrePack → 继续（❌）
    if not genre_pack:
        print("Warning: missing genre pack, continue anyway")
    
    # 约束违反 → 只是警告（❌）
    if genre_violations:
        print(f"Warning: {violations}, but continue")
    
    # BLOCKED 状态 → 仍然继续（❌）
    if decision.status == "BLOCKED":
        print("BLOCKED but continue next chapter")
    
    return draft  # 总是返回
```

---

### 1.4 Real-Provider Validation

**经验描述**:
> 真实模型才能暴露 provider、retry、replay、prompt communication、entity resolution 等问题

**为什么正确**:
- ✅ 确定性测试只能验证逻辑一致性
- ✅ 只有真实 LLM 才能发现 Prompt 是否真的传达了意图
- ✅ 只有真实调用才能发现网络、重试、成本计算问题

**V1 发现的真实问题**（只有真实模型才暴露）:
1. **5xx 错误被误分类为永久失败**（不重试）
2. **Replay key 包含 timeout**（不同 timeout 不共享缓存）
3. **Extractor 只看 ID 不看名字**（导致已知角色被识别为 new）
4. **生成模型只在 `--commercial` 时才构建**（`--model-provider` 被忽略）

**V2 执行纪律**:
- 每个重要 LLM 路径必须有真实模型测试
- 不能只用 deterministic stub
- 测试套件包含：
  - ✅ 确定性测试（逻辑正确性）
  - ✅ 真实模型测试（通信正确性）

---

### 1.5 Canon Commit Boundary

**经验描述**:
> 所有 Canon 状态变化必须通过唯一 Canon Commit Boundary

**为什么正确**:
- ✅ 单一事实源（SSOT）
- ✅ 所有写入可审计
- ✅ 便于事务控制
- ✅ 防止旁路污染

**V1 教训**:
- 早期多个地方可以写事实（Planner、Writer、Reviewer 都能写）
- 导致事实冲突、来源不明
- 后来收敛为唯一 Mint 入口

**V2 执行纪律**:
```
任何想改变 Canon 的操作
    ↓
必须经过 Mint
    ↓
不能有旁路
```

```python
# ✅ 正确方式
def add_fact(fact):
    # 通过 Mint
    mint_executor.execute(fact)

# ❌ 错误方式
def add_fact(fact):
    # 直接写文件（❌）
    with open("facts/CHR-00001.yaml", "w") as f:
        f.write(fact)
```

---

### 1.6 Draft is NOT Canon

**经验描述**:
> Draft、Candidate、Rewrite、Reviewer 建议、Reference Evidence、AI 推断都不是 Canon

**为什么正确**:
- ✅ 防止未审核内容进入事实
- ✅ 保持 Canon 的权威性
- ✅ 支持多版本对比
- ✅ 可以安全地实验

**V1 教训**:
- 早期生成的 Draft 直接被当作 Canon
- 导致低质量内容污染事实库
- 后来引入 Candidate → Approval → Mint 流程

**V2 执行纪律**:
```
生成 Draft
    ↓
评审（可能多轮改写）
    ↓
人工审批
    ↓
提取 Fact Candidate
    ↓
Mint（才成为 Canon）
```

---

### 1.7 Evidence Level 明确

**经验描述**:
> 未经真人/真实市场校准的 Judge 只能诊断、比较、排序，不能表述成商业真值

**为什么正确**:
- ✅ 防止过度自信
- ✅ 明确告知用户这是"AI 猜的"还是"真实验证的"
- ✅ 避免错误决策
- ✅ 保留改进空间

**Evidence Level 分级**:
| Level | 证据类型 | 用途 | 可以 Gate 吗 |
|-------|----------|------|--------------|
| E0 | 确定性检查 | Hard Gate | ✅ 可以 |
| E1 | 结构化提取 | Candidate / Diagnosis | ❌ 不可以 |
| E2 | LLM 评价 | Ranking / Diagnostic | ❌ 不可以 |
| E3 | 人工金样集 | Calibration | ❌ 不可以（但可参考）|
| E4 | 真实市场数据 | Product Truth | ❌ 不可以（但是最终目标）|

**V1 教训**:
- Reader-sim、Commercial judge 未被校准
- 但一度被当作决策依据
- 导致优化方向错误

**V2 执行纪律**:
- 所有评分系统必须标注 Evidence Level
- E2 级别不能用于 Gate
- E3/E4 才能影响重大决策

---

## 二、V1 失败教训（不得重演）

### 2.1 Genre 弱约束造成类型污染

**失败描述**:
Genre 只是字符串标签，没有实际约束力，导致都市小说生成修炼内容。

**根本原因**:
```python
# ❌ V1 错误方式
genre = "都市"  # 只是个字符串
prompt = UNIVERSAL_TEMPLATE.format(genre=genre)
# 模型可以忽略这个标签
```

**后果**:
- 都市题材出现"灵气复苏"、"修炼境界"
- 玄幻题材出现"公司"、"股票"
- 类型不纯，读者困惑

**V2 纠正方式**:
- Genre 是一等公民领域模型（GenreConfig）
- 包含硬约束（allowed/forbidden elements）
- 约束可执行、可验证
- 违反约束 = 阻断生成

---

### 2.2 Power System 不是通用 Progression

**失败描述**:
强制所有题材使用 `power_level` / `cultivation_stage`，但都市小说不应该有"境界"。

**根本原因**:
设计时隐含假设了玄幻/奇幻范式，把修炼体系当作通用模型。

**后果**:
- 都市小说角色有"炼气期"、"筑基期"（荒谬）
- 无法表达都市题材的真正进阶（财富/地位）

**V2 纠正方式**:
- 引入 `ProgressionModel` 抽象基类
- PowerProgressionModel（玄幻）
- WealthProgressionModel（都市）
- TechProgressionModel（科幻）
- 各有各的语义

---

### 2.3 关键词补丁不是 Genre Architecture

**失败描述**:
通过 positive/negative keywords、题材专用 Prompt 补救，但这只是检测，不是架构。

**根本原因**:
Genre 没有在架构层面得到支持，只能打补丁。

**后果**:
- 关键词检测不准确（《我真没想重生啊》被误判为奇幻）
- Prompt 补丁越来越长，维护困难
- 治标不治本

**V2 纠正方式**:
- Genre-First 架构
- 在 Genesis 阶段就锁定题材
- 题材约束贯穿整个流程
- 关键词只用于检测，约束才是真正的防线

---

### 2.4 功能增长不能替代作品结果

**失败描述**:
一度追求模块数、Agent 数、Schema 数、测试数，但忽略了真实小说质量。

**根本原因**:
工程导向压倒了产品导向。

**后果**:
- 724 个 Python 文件，898 个 JSON 文件
- 但缺少 30 章人工验证基线
- 缺少真实读者反馈
- 无法证明商业价值

**V2 纠正方式**:
- 从工程导向转向作品导向
- 不再追求模块数量
- 追求证明：
  - ✅ 前 3 章真的抓人（人工盲评 > 7 分）
  - ✅ 30 章真的完整（0 重大缺陷）
  - ✅ 自动修订真的有用（A/B 胜率 > 50%）

---

### 2.5 多 Verdict 制造多真值中心

**失败描述**:
历史 Artifact 曾同时存在 pass / rollback / revise / invalidated 等不同结论。

**根本原因**:
多个评审者都有"最终决定权"。

**后果**:
- 不知道该听谁的
- 冲突时无法裁决
- 状态混乱

**V2 纠正方式**:
- 唯一 Production State Machine
- 其他评分只是 Evidence，不是 Verdict
- 最终决定权在生产决策阶段

---

### 2.6 Fail-Open 让 Contract 失效

**失败描述**:
缺 Contract 就跳过、找不到实体返回 None、continuity error 只 warning。

**根本原因**:
为了"不卡住"而放松约束。

**后果**:
- 错误积累
- 后期修复成本高
- 质量不可控

**V2 纠正方式**:
- Production 默认 Fail-Closed
- unsafe bypass 必须显式且不可直接发布
- 宁可早期卡住，不要后期崩溃

---

### 2.7 AI 评价未分证据等级

**失败描述**:
ReaderSim、Commercial Judge、Quality Judge 在未校准前被当作决策依据。

**根本原因**:
没有明确标注"这是 AI 猜的，还是真实验证的"。

**后果**:
- 优化方向错误
- 信心过度
- 浪费资源

**V2 纠正方式**:
- 所有 AI 评分标注 Evidence Level
- 未校准 = E2 级（诊断级）
- 不参与生产决策

---

### 2.8 Corpus/Reference 应影响规划，不应污染正文

**失败描述**:
Reference 通过抽象 EvidencePack 进入 Genesis/Planning，但 Writer 默认不读取连续参考原文。

**为什么这样做**:
- 防止洗稿
- 防止过度相似
- 保持原创性

**V1 教训**:
早期 Writer 可以读参考原文，导致生成内容与参考小说过于相似。

**V2 继承**:
- Reference 只用于 Genesis/Planning 阶段
- Writer 只看 EvidencePack（抽象的机制/套路）
- 不看原文

---

## 三、核心原则总结

### 必须遵守的 20 条原则

根据 Project Constitution，以下原则不能违背：

1. **P-001**: Canon over Model Memory
2. **P-002**: Genre is a Foundational Domain
3. **P-003**: Draft is NOT Canon
4. **P-004**: Canon Changes only through Canon Commit
5. **P-005**: Production is Fail-Closed
6. **P-006**: State owns truth; Worker owns computation
7. **P-007**: Agents are Workers, not Architecture
8. **P-008**: Multiple Genesis Inputs, One Production Kernel
9. **P-009**: Market Trend is not Genre Truth
10. **P-010**: AI Judge is not Ground Truth
11. **P-011**: Reference Evidence is not Project Canon
12. **P-012**: Persistent Artifacts require Provenance
13. **P-013**: No Consumer = Stub
14. **P-014**: Long-form Correctness before Feature Breadth
15. **P-015**: Real-model Validation is mandatory
16. **P-016**: Context must be Compiled
17. **P-017**: Plan is Intention; Canon is History
18. **P-018**: Repair before Rewrite
19. **P-019**: Deterministic Facts outrank Semantic Preference
20. **P-020**: Reader/Market Signal eventually calibrates AI Metrics

---

## 四、实施检查清单

### 在实施任何新功能前，问自己：

- [ ] 这个功能有真实消费者吗？（P-013）
- [ ] 它是否违反 Genre 约束？（P-002）
- [ ] 它是否试图绕过 Canon Commit？（P-004）
- [ ] 它是否在 Production 模式下 Fail-Open？（P-005）
- [ ] 它是否把 AI 评价当作 Ground Truth？（P-010）
- [ ] 它是否经过真实模型验证？（P-015）
- [ ] 它是否追求模块数量而非作品质量？（P-014）

### 如果任何一项为"是"：

**停止实施，重新设计。**

---

## 五、致未来维护者

如果你正在读这份文档，说明你正在考虑修改或扩展系统。

**请记住**：

1. **V1 的失败不是因为技术不够好，而是因为优先级错了。**
   - 不要再追求"更多模块"
   - 追求"更好的作品"

2. **V1 的成功经验是血泪换来的。**
   - State as Projection（重构过多次才稳定）
   - No Consumer = Stub（堆积了大量死代码后才学会）
   - Fail-Closed（早期 Fail-Open 造成质量灾难）

3. **Genre 系统是 V2 的核心改进。**
   - 这是 V1 最大的架构缺陷
   - 必须在第一天就做对

4. **30 章基线是第一个关键里程碑。**
   - 在证明 30 章稳定前，不要谈 100 章
   - 在证明单题材稳定前，不要扩展到全题材

5. **人工验证不能跳过。**
   - AI 评分只是诊断
   - 真实读者才是真相
   - 金样集是校准的前提

**最后，请遵守 Project Constitution 的 20 条原则。**

它们是 V1 失败和成功的总结，是 V2 的护栏。

---

**制定人**: Claude Opus 4.8  
**基于**: Project Constitution、V1 审计报告、ROADMAP 经验总结  
**状态**: 核心经验教训总结完成
