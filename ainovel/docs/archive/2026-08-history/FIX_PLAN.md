# Stage A 质量闭环修复计划

基于《小说创作核心能力核验报告》（2026-08-17），以下是已确认的真实问题及修复步骤。

## P0 问题（立即修复，预计3-5天）

### 1. Reader Simulation字段协议统一 ✅ 已确认
**问题**：
- 产物使用 `personas` + `would_continue`
- loop.py读取 `readers` + `will_continue`
- 导致 Production Card 的 `dropout_risk` / `continuation_rate` 为 null

**修复**：
- [ ] 统一schema为 `personas` + `would_continue`（已是多数产物使用的字段）
- [ ] 修复 loop.py:2252-2275 的字段读取
- [ ] 修复 Production Card 的 dropout 计算
- [ ] 添加schema一致性测试

**验收**：
- Production Card 有 Reader Simulation 数据时，`dropout_risk` 和 `continuation_rate` 不为 null
- 模拟器降级时明确标记 `degraded`，不当作0风险

---

### 2. Production Card 绝对质量阈值 ✅ 已确认
**问题**：
- `compute_recommendation()` 只检查：critical_deviations、quality_delta、dropout_risk
- 不检查绝对分数，例如 `hook < 75`、`retention < 75`

**修复**：
- [ ] 在 `production_card.py:compute_recommendation()` 添加绝对阈值检查
- [ ] 配置化阈值（不写死）
- [ ] 阈值建议：
  ```python
  QUALITY_THRESHOLDS = {
      "hook": 75,
      "retention": 75,
      "reward_density": 70,
      "payoff": 70,
      "character_consistency": 80,
      "world_consistency": 80,
      "reader_drop_risk_max": 30,
  }
  ```
- [ ] 当任一维度低于阈值，返回 `"hold"` 或 `"revise"`

**验收**：
- 低于阈值的章节不能得到 `recommend`
- 所有 action 都能追溯到明确 reason code

---

### 3. 真实初评-修改-终评闭环 ✅ 已确认
**问题**：
- loop.py:2352-2353 复用同一份 `_scores`
- `initial_quality_scores` == `final_quality_scores`
- `quality_delta` 为空

**修复**：
- [ ] 保存 Draft V0（生成后立即评审）
- [ ] 修订后生成 Draft V1
- [ ] 终评 V1（可选：pairwise V0 vs V1）
- [ ] 真实 delta 计算
- [ ] 净胜率低于65%时回滚到V0

**实施位置**：
- loop.py commercial/hygiene loop 之前：保存初始 qa_review 为 `initial_scores`
- loop.py 修订后：重新运行 final_review_model（如果启用）
- 修复 loop.py:2352 不再复用同一份 _scores

**验收**：
- 有修订的章节100%具备真实 V0/V1
- `quality_delta` 不为空
- Production Card 能显示真实改善/退化

---

### 4. 统一生产决策 ✅ 已确认
**问题**：
- final-TASK-00001.json 同时存在：
  - `comparison_report.summary.recommendation = "rollback"`
  - `editorial_verdict = "accept"`
  - `production_decision.action = "revise"`
  - `advance_to_next_chapter = false`

**修复**：
- [ ] 建立唯一 `ProductionDecisionEngine`
- [ ] 明确优先级：
  1. 硬红线（integrity fail、M7 redline）
  2. 契约冲突（critical_deviations > 0）
  3. Promise逾期
  4. 质量绝对阈值
  5. 质量退化
  6. 读者弃读风险
  7. 文体警告
  8. 人工审批
- [ ] 只允许输出一个决策：`publish` / `revise` / `hold` / `block`
- [ ] Comparison Report、Production Card、Final Chapter 不得各自独立决策

**验收**：
- 同一章所有产物的 `action` 完全一致
- 不再出现 `recommend` + `rollback` + `revise` 并存
- 每个 action 都能追溯到明确 reason code

---

### 5. Promise Delivery 状态更新接入 ✅ 部分确认（代码已有check_delivery调用）
**问题**：
- loop.py:2289-2320 已调用 `check_delivery()`
- 但报告称"未接入serial loop状态更新"

**需要验证**：
- [ ] 检查 `check_delivery()` 是否真正更新 ledger 状态
- [ ] 验证下一章是否重新投影 ledger（不重复注入已兑现承诺）
- [ ] 检查 `match_evidence()` 的准确性（50%阈值是否合理）

**如果确认缺失，修复**：
- [ ] 每章完成后：check_delivery() → 生成状态更新候选 → 人工审批（高置信自动确认）→ Mint写入
- [ ] 下一章重新投影 ledger
- [ ] 状态扩展：`open` / `partially_delivered` / `delivered` / `broken` / `overdue`

---

### 6. 修复集成测试 ✅ 待验证
**问题**：
- 报告称 Stage A CLI 集成测试失败（Python路径、review_model断言）

**修复**：
- [ ] 验证测试路径：`python3 -m runtime.cli`
- [ ] 更新过期断言（`review_model` → `final_review_model`）
- [ ] 添加 Reader Simulation schema 契约测试
- [ ] 添加 Production Decision 一致性测试

---

## P1 问题（建立真实质量闭环，预计1-2周）

### 7. 确定性警告转化为修订任务
**问题**：
- AI味、节奏、密度、钩子等 warning 只进入报表，不驱动修订

**修复**：
- [ ] 将 warning 转换为结构化 Revision Task（精确 span、问题类型、修改边界）
- [ ] 例如第1章自动生成：
  - 打散连续"他"开头句式
  - 降低比喻密度（5.5 → 1.59以下）
  - 增加中段局面反转
  - 增强章末钩子（从"重复目标"到"新危机"）

---

### 8. 升级人物成长模型
**问题**：
- 当前仅根据"出场次数"判断成长阶段（7次 → transformed）

**修复**：
- [ ] 从"出场次数"升级为状态机
- [ ] 跟踪：欲望、错误信念、恐惧、价值、行动策略、关系、能力、已付代价、不可逆选择
- [ ] 只有发生有证据的状态转移时，才推进成长阶段

---

### 9. 升级章末钩子评估
**问题**：
- 当前只检测"是否存在钩子"，不区分钩子类型和质量

**修复**：
- [ ] 区分钩子类型：新信息、新威胁、身份揭示、决策悬停、爽点前置、情感破裂、规则反转、目标升级、倒计时、付费断点
- [ ] 检测：是否重复本章问题、是否延迟兑现、是否假悬念、连续三章是否使用同一种钩子

---

### 10. Reader Simulation 期待反馈给下一章
**问题**：
- 当前期待只记录在 Production Card，未转化为下一章硬目标

**修复**：
- [ ] 对 Persona 期待做：聚类、去重、区分"必须满足"和"不可全满足"
- [ ] 选择1-2个进入下一章 objective
- [ ] 其余进入中期 Promise

---

## P2 问题（补齐商业竞争力，预计2-4周）

### 11. 建立作品级 Commercial Constitution
**修复**：
- [ ] 在生成章节前冻结：目标平台、目标人群、题材、一句话卖点、三个差异化标签、主爽点引擎、主情绪引擎、核心付费驱动力、前三章承诺、免费期末尾承诺、每卷商业峰值、明确不写什么
- [ ] 每章商业评分都相对此 Constitution

---

### 12. 重构 Paywall Optimizer
**问题**：
- 当前使用固定章号（玄幻6-12章）

**修复**：
- [ ] 从固定章号改为事件驱动：核心能力首次完整兑现、首个阶段胜利、主要关系建立、新威胁显性化、高价值信息只揭开一半、下一章有明确兑现预期、读者已投入足够时间、免费区没有过度欠债
- [ ] 输出多个候选并进行匿名 A/B 评审

---

### 13. 引入平台反馈校准
**修复**：
- [ ] 支持录入：点击率、首章读完率、1→2章留存、3章留存、10章留存、付费转化、追订率、章节评论情绪、催更率、弃书位置
- [ ] 通过 Platform Feedback Reconciliation 更新：阈值、Persona权重、Hook类型效果、题材商业参数、Paywall策略
- [ ] 在没有真实数据前，所有 predicted retention/pay conversion 必须标注：`comparison_only=true`

---

## P3 问题（构建百万字稳定性，预计1-2个月）

### 14. 建立多时间尺度规划
**修复**：
- [ ] 同时维护：章（场景与即时目标）、5章（短周期兑现）、10章（阶段波形）、30章（小卷）、100章（大卷）、全书（终局承诺）
- [ ] 每层计划都定义：建立什么、升级什么、兑现什么、改变什么、留下什么、禁止重复什么

---

### 15. 建立 Long-Run Health Dashboard
**修复**：
- [ ] 每10/30/50章统计：人设偏移、世界规则冲突、开放Promise数、Promise逾期数、平均兑现周期、同类钩子连续次数、爽点类型多样性、连续低潮章数、角色缺席时长、能力膨胀速度、反派梯度、地图利用率、对话角色辨识度、AI味趋势、章节质量趋势、商业疲劳风险

---

### 16. 修复 Million Word Stability 指标方向
**问题**：
- 当前风险项没有反向计分，可能把高风险计为高质量

**修复**：
- [ ] 质量均值必须：对风险项反向计分、排除degraded数据、区分数据缺失和稳定、无有效数据时输出unknown（不能输出stable=true）、不仅看均值，还要看方差、连续退化、最差窗口和恢复能力

---

### 17. 建立伏笔图谱
**修复**：
- [ ] 每个伏笔记录：来源章节、相关角色、相关世界规则、表层问题、深层问题、最早可兑现章、最迟应兑现章、预计兑现方式、已提供证据、已发生误导、当前状态、回收证据、回收质量、是否产生新承诺

---

## 实施顺序

**第一阶段（立即修复，3-5天）**：
1. Reader Simulation字段协议统一
2. Production Card绝对质量阈值
3. 真实初评-修改-终评闭环
4. 统一生产决策
5. 验证Promise Delivery状态更新
6. 修复集成测试

**第二阶段（质量闭环，1-2周）**：
7. 确定性警告转化为修订任务
8. Reader Simulation期待反馈给下一章
9. 升级章末钩子评估
10. 升级人物成长模型

**第三阶段（商业校准，2-4周）**：
11. 建立作品级Commercial Constitution
12. 重构Paywall Optimizer
13. 引入平台反馈校准

**第四阶段（百万字治理，1-2个月）**：
14. Promise语义状态机
15. 人物弧状态机
16. 作品专属长弧计划
17. 多窗口节奏与商业疲劳检测
18. 修复百万字稳定性模型

---

## 验收标准

### 单章质量门槛（P0完成后）
| 指标 | 建议门槛 |
|------|---------|
| Hook | ≥ 78 |
| Conflict | ≥ 75 |
| Reward Density | ≥ 72 |
| Character Consistency | ≥ 85 |
| World Consistency | ≥ 88 |
| Emotion | ≥ 75 |
| Retention | ≥ 78 |
| Payoff | ≥ 72 |
| Curiosity | ≥ 78 |
| Pacing | ≥ 75 |
| Reader Drop Risk | ≤ 25 |
| 高严重度事实冲突 | 0 |
| 关键Promise漏兑 | 0 |
| 评审degraded | 0 |

**注意**：这些是启动门槛，后续必须根据人工金样和真实读者数据校准。

---

## 风险提示

1. **LLM自评高分虚假安全感**：大部分章节评分80-95区间，Reader Simulation普遍100%继续阅读。若没有人工金样校准和真实平台反馈，这类高分可能只是模型偏好。

2. **承诺被提到≠承诺被兑现**：字符串命中会把"提及承诺"误当"完成承诺"。在长篇中造成严重后果。

3. **系统擅长发现问题，但没有确保问题被修掉**：当前大量能力是 `gating=false`、advisory。需要明确的人类或策略决策层。

4. **百万字能力被100章模板和均值报表高估**：100章成功生成证明的是吞吐能力，不等于人设不崩、设定不崩、伏笔不丢、节奏不重复、商业卖点不疲劳。

---

## 当前能力评分总结（基于核验报告）

| 核心目标 | 当前评分 | P0完成后预估 | 全部完成预估 |
|---------|---------|-------------|-------------|
| 小说质量高 | 72/100 | 78/100 | 85/100 |
| 商业价值高 | 61/100 | 65/100 | 80/100 |
| 读者留存强 | 68/100 | 73/100 | 82/100 |
| 长期维护好 | 64/100 | 68/100 | 84/100 |
| 工程可审计性 | 88/100 | 92/100 | 95/100 |
| **综合成熟度** | **69/100** | **75/100** | **85/100** |

---

## 结论

**当前项目的优势是"工程治理和审计能力强"，短板是"质量结果闭环与商业校准不足"。**

下一阶段不应继续增加更多评分Agent或报表，而应优先解决：
1. 字段协议
2. 决策一致性
3. Promise状态闭环
4. 真实修订净收益
5. 平台数据校准

完成P0和P1后，项目综合成熟度预计可从当前约69分提升到80-84分；完成平台反馈校准和百万字状态治理后，才有条件向"稳定商业生产系统"迈进。
