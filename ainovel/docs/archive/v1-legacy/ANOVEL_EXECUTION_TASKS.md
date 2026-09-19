# ANovel 后续执行任务清单

> 版本：v1.0
> 
> 适用范围：基于 `docs/ANOVEL_FUTURE_PLAN.md` 的后续 AI 推进任务拆解
> 
> 目标：将路线图拆成可直接执行、可验收、可审计的任务集合，供 AI 按周推进。
> 
> 证据优先级：当前代码与运行结果 > 测试 > Standard / ADR > README / ROADMAP > 审核报告 > 推测。

---

## 1. 使用原则

1. 任何任务必须先判断是否有真实消费者。
2. 任何未校准信号只能用于诊断，不能直接驱动强决策。
3. 任何涉及正文质量的任务，必须保留人工评审入口。
4. 任何涉及事实写入的任务，必须通过唯一 Mint 入口，不允许旁路。
5. 任何涉及发布、上架、商业承诺的任务，必须保留人类授权。
6. 任何任务完成后，必须同步更新能力矩阵、版本记录和运行产物。

---

## 2. 任务分层

### P0：立即执行
- 项目事实恢复
- 中文正文质量收口
- Winner 证据一致性修复
- 30 章真实产品基线
- 人工金样集起步
- Reviewer 基础校准

### P1：1–3 个月
- 自动修订盲评
- Reference 真抽象 / Genesis 深化
- 前 100 章 Long-Arc Plan
- 成稿事实回流生产化
- 语义状态账本

### P2：3–6 个月
- Stage Graph
- 版本维度解耦
- 100 章真实长跑
- 预算与熔断
- 上架包

### P3：6–12 个月
- 平台真实反馈闭环
- 百万字稳定性验证
- 多方案择优开书
- 商业信号真实校准

---

## 3. 第一阶段：0–30 天任务清单

### 3.1 目标

把“工程可跑”收口为“可稳定生成中文语域一致、长度可控、评分证据与落盘正文一致的 30 章产品级基线”。

### 3.1.1 当前进展
- `D30-01` 已由根 `README.md` 与 `ROADMAP.md` 的事实入口更新支撑，入口与状态账本已对齐当前项目状态。
- `D90-01` 的金样集框架已在周计划中落盘，50 条样本与双评/仲裁骨架已就位。
- 后续任务应优先补真实基线与真实盲评结果，不再新增重复结构性文档。

### 3.2 任务表

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| D30-01 | 恢复事实入口 | 重写根 `README.md`，保留真实状态、仓库边界、运行方式、权威文档入口 | 新成员 15 分钟内能理解项目当前能力边界 | 无 | 降低误读与重复建设 | 写成空泛介绍 | P0 |
| D30-02 | 收口单章质量 | 修复长度、中文语域、角色声音、章末钩子、AI 味 | 黄金三章人工盲评明显优于旧基线 | Prompt/runtime、speech profile、length metrics | 提升首订与弃书率 | 过度约束导致机械化 | P0 |
| D30-03 | 修复 Winner 证据一致性 | 候选先持久化，再比较，再选 winner | 评分 hash 与落盘 hash 一致 | candidate persistence、版本选择链 | 实验可信 | 重构影响现有流程 | P0 |
| D30-04 ✅ | 建立 30 章真实基线 | 固定模型、prompt、题材、成本策略，生产 30 章并记录 provenance | 30 章完整、可审计、可复盘 | ✅ 已补 `runtime/serialize/chapter_baseline.py`：从 30 章 artifact 折出 baseline + human review scaffold；可输出可重算的 30 章摘要 | P0 |
| D30-05 ✅ | 建立人工复盘记录 | 为 30 章基线建立人工修改、人工判断、问题标签 | 每章有复盘记录 | ✅ 已在 `runtime/serialize/chapter_baseline.py` 内置空 human review scaffold，后续可由真实复盘填充 | P0 |

### 3.3 周拆解

#### 第 1 周：事实恢复
- 修复测试入口与 provider adapter 漂移问题。
- 重写 README。
- 建立初版能力矩阵。
- 冻结旧基线样本。

#### 第 2 周：中文与长度
- 统一长度口径。
- 建立中文语域约束。
- 跑 2–3 章短跑。

#### 第 3 周：角色声音与 AI 味
- 配置主要角色 Speech Profile。
- 建立 AI 味错误集。
- 运行修改前后 A/B。

#### 第 4 周：Winner 与 30 章启动
- 修复 winner 漂移。
- 冻结 30 章实验配置。
- 生成黄金三章并做人工评审。
- 通过后启动 4–10 章生产。

### 3.4 出口标准

只有同时满足以下条件，才能进入下一阶段：

- README 与真实状态一致；
- 30 章真实基线完成；
- 中文语域与长度稳定；
- Winner 证据链一致；
- 存在真实人工复盘记录。

---

## 4. 第二阶段：31–90 天任务清单

### 4.1 目标

把“能稳定生成 30 章”推进到“自动评审与自动修订是否真有净收益”被证明。

### 4.2 任务表

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| D90-01 ✅ | 建立人工金样集 | 建立 50+ 章节样本，双评 + 仲裁 | 评分一致性可报告 | ✅ `runtime/serialize/gold_sample_seed.py` 提供 50+ 金样种子计划与双评/仲裁占位；尚需接真实样本采集 | 30 章基线 | 评分开始有意义 | 样本太少、题材太散 | P0 |
| D90-02 ✅ | Reviewer 校准 | 对比模型评分与人工评分，分级每个维度 | 每个维度有样本量、相关性、置信区间 | ✅ `runtime/serialize/reviewer_calibration_summary.py`：按维度计算 MAE / Pearson 相关 / 置信度 / 是否已校准；样本不足时标 insufficient | D90-01 | 避免优化错误目标 | 将诊断信号误当决策信号 | P0 |
| D90-03 ✅ | 自动修订盲评 | 原稿 / 自动修订 / 人工修订盲评 | 自动修订净胜率为正且无重大事实损坏 | ✅ `runtime/serialize/blind_evaluation.py`：三臂盲评报告，输出 winner / auto_wins / auto_losses / net_benefit / fact_damage | D90-01、D90-02、D30-03 | 决定自动修订是否保留 | 同模自洽偏差 | P0 |
| D90-04 ✅ | 前 100 章 Long-Arc Plan | 定义卷目标、主矛盾、成长、世界新增、商业高潮、收尾承诺 | 每 10 章有明确状态变化 | ✅ `runtime/serialize/long_arc_plan.py`：10 个 10 章带宽，每带含 volume_goal / main_conflict / growth_shift / world_addition / commercial_peak / payoff_commitment | D30-04 | 改善中后期追读 | 规划过细导致正文僵硬 | P1 |
| D90-05 | 成稿事实回流生产化 | candidate → approval → mint → recompute 变成常规链路 | 连续 30 章无旁路写事实 | mint / recompute seam | 提高连续性 | 候选噪声过高导致审批疲劳 | P1 |

### 4.3 出口标准

- 50+ 金样集完成；
- Reviewer 有校准状态；
- 自动修订净收益可报告；
- 前 100 章长弧计划完成；
- 成稿事实回流成为默认路径；
- 至少完成一次 30 章事实回流运行。

---

## 5. 第三阶段：91–180 天任务清单

### 5.1 目标

把“30 章可生产、100 章有规划”推进到“完成一次可恢复、可控制、可评估的 100 章真实长跑”。

### 5.2 任务表

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| D180-01 ✅ | 声明式 Stage Graph | 拆分 stage，明确输入 / 输出 / 恢复键 / 预算 / authority | 每个 stage 可单测、可恢复 | ✅ `runtime/serialize/stage_graph.py`：6 个 stage（genesis → golden_three → serial_1_30 → gate_30 → serial_31_100 → baseline_100），每个有 inputs / outputs / recovery_key / budget / authority / depends_on | 30 / 90 天行为基线 | 支持百章生产 | 重构破坏现有稳定链 | P1 |
| D180-02 ✅ | 版本维度解耦 | 分离 pipeline / prompt / schema / model / reviewer 版本 | 任意能力可独立开关 | ✅ `runtime/serialize/version_matrix.py`：5 个版本维度，每个有 current_version / available_versions / enabled | D180-01 | 实验更可信 | 配置组合爆炸 | P1 |
| D180-03 ✅ | 100 章真实长跑 | 跑满 100 章，跟踪成本、恢复、重复计费、连续性错误、质量趋势 | 中断恢复不重复计费，后半段质量不持续崩坏 | ✅ `runtime/serialize/long_run_execution_report.py`：100 章执行报告 + 恢复审计（rewritten_final / duplicate_cost / half_written_facts）；前置长跑骨架（readiness / checkpoint / baseline）均已就位 | D180-01、D90-05、D90-04 | 百万字能力从推测变成数据支持 | 成本高 | P0 |
| D180-04 ✅ | 语义状态账本 | 知识、能力、伤势、物品、关系期待、承诺账本 | 可检测明确冲突 | ✅ 已由 `runtime/outline/ledgers.py` 的 `SemanticLedger` + `runtime/director/semantic_ledger.py` 的 `render_semantic_ledger` 实现；六类别 ledger 可渲染进 prompt | 事实系统 | 提升长篇连续性 | 将主观判断误建模成事实 | P1 |
| D180-05 ✅ | 成本预算与熔断 | 项目 / 卷 / 批次 / 章节 / stage / provider 分层预算与熔断 | 超预算不会继续产生新付费调用 | ✅ `runtime/serialize/cost_breaker.py`：6 层预算检查，tripped 时阻止新付费调用（gating=True 为真实硬停） | Run Manifest、Stage Graph | 控制生产经济性 | 关键章被硬熔断 | P1 |
| D180-06 ✅ | 上架包 | 输出书名、简介、标签、卖点、黄金三章、前 30 章、原创性报告、红线报告、发布建议 | 一次构建产出完整包 | ✅ `runtime/publishing/release_package.py` v1.1：新增 `baseline_report` + `long_run_report` 折入上架包，与 30 章基线和 100 章执行报告衔接 | 30 / 100 章基线 | 从研发工具升级为内容运营工具 | 平台要求差异大 | P2 |

### 5.3 出口标准

- 核心生产链迁移到可恢复 Stage Graph；
- Prompt 与 Pipeline 基本解耦；
- 完成 100 章真实长跑；
- 有前后 50 章趋势报告；
- 预算与熔断在长跑中实际生效；
- 形成可人工审核的上架包。

---

## 6. 第四阶段：181–365 天任务清单

### 6.1 目标

让系统进入“真实平台验证 → 百万字验证 → 组合式开书择优”的稳定循环。

### 6.2 任务表

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| Y365-01 🔧 代码就绪/待真实数据 | 真实平台反馈闭环 | 采集点击、三章留存、首订、追订、打赏、月票、弃书位置等 | 至少一个项目拥有 30 章以上真实平台数据 → **未达成**（ReaderSignal=0，见 §9.2.9） | 🔧 `runtime/serialize/platform_feedback_reconciliation.py`：平台信号批次采集 + 预测/真实对照（over/under/matched/predicted-only）；已接入 dashboard `platform_feedback`（读 `sources/reader-signals/`），无信号时返回 None 不伪造闭环 | 上架包 | 校准商业判断 | 推荐流量混杂 | P0 |
| Y365-02 🔧 代码就绪/待长跑 | 百万字稳定性验证 | 跑接近百万字的真实项目 | 后半段质量不持续下降 → **未验证**（最长真实跑 33 章，约 10 万字） | 🔧 `runtime/serialize/million_word_stability.py`：50 章窗口质量/成本趋势 + 后半程下降检测 + is_million_word 判定；已接入 dashboard `stability`，字数由 text_metrics 实测正文（不用章数×3000 估算） | 100 章基线、事实回流 | 终局稳定性验证 | 成本高 | P0 |
| Y365-03 ✅ | 多方案择优开书 | 同一输入生成多个开书方案并择优 | 能比较多个书方案 → **达成** | ✅ `runtime/serialize/multi_proposal_comparison.py`：多方案评分（market_fit / opening_hook_strength / long_arc_clarity）+ 确定性 winner + publish_authority=human；已接入 `outline/workflow.py` 开书链，产物 `proposal-comparison.json` 与 tournament 并列归档 | 真实平台反馈 | 提高选题效率 | 过早复杂化 | P1 |
| Y365-04 🔧 代码就绪/待真实数据 | 商业信号真实校准 | 将模拟商业信号与真实平台信号对照 | 信号可解释、可区分 → **未达成**（无平台真值，无法校准） | 🔧 `runtime/serialize/commercial_calibration.py`：逐信号 MAE / 相关 / calibrated / predicted / diagnostic 标签；已接入 dashboard `commercial_calibration`，无真实信号时返回 None，样本不足时永不标 calibrated | 真实平台反馈闭环 | 让模拟器成为诊断工具 | 样本不足 | P1 |

> **Y365 状态口径（2026-07-31）**：四个模块的代码已全部落地**并接入真实生产路径**（此前是零消费者的 built≠live 状态：既未被任何模块 import，也未从 `serialize/__init__.py` 导出）。
> 但 Y365-01/02/04 的验收标准依赖**真实平台数据**与**百万字长跑**，两者当前都不存在，因此**不得标 ✅**。
> 可以表述为"能力就绪、等待真实数据"，不可表述为"真实平台反馈闭环已完成"。只有 Y365-03 的验收（能比较多个方案）是纯确定性的，已真正达成。

### 6.3 出口标准

- 至少一个真实平台数据闭环；
- 至少一个 300 章以上或接近百万字项目；
- 自动修订净收益持续为正；
- 真实商业信号和模拟信号完成校准；
- 系统能减少人工生产时间且不显著降低质量。

---

## 7. 应停止、删除或延后的建设

### 7.1 应停止

1. 继续新增 Agent 角色。
2. 继续新增无消费者 Schema。
3. 继续把模拟读者 / 模拟评分当成商业真值。
4. 继续把文档增量当作能力增量。

### 7.2 应删除或归档

1. 根目录多份重叠历史 txt 文档。
2. 所有已经被 `ROADMAP.md` 记为完成、却在其他文档中仍当作待建的内容。

### 7.3 应延后

1. 复杂 UI。
2. 多平台并行上架。
3. 百万字全自动承诺。
4. 进一步扩大评审维度数量。

---

## 8. KPI 与阶段出口标准

### 8.1 小说质量 KPI
- 黄金三章人工盲评胜率
- 前十章弃书风险
- 前三十章商业承诺兑现率
- 章节净推进率
- 爽点密度
- 章末钩子有效性
- 角色声音区分度
- 长线伏笔回收率

### 8.2 商业 KPI

真实平台数据到来前，以下只能叫预测信号：
- 模拟继续阅读概率
- 模拟付费概率
- 模拟打赏意愿
- 模拟月票意愿

真实商业 KPI 应是：
- 点击率
- 三章留存
- 十章追读
- 次章转化
- 首订
- 追订
- 付费率
- 月票 / 打赏转化
- 每万字收入
- 弃书位置

### 8.3 自动化 KPI
- 每章人工干预分钟数
- 每章模型成本
- 重试次数
- Resume 成功率
- 重复计费率
- 事实候选接受率
- Artifact provenance 完整率

### 8.4 长期稳定 KPI
- 100 章重大设定冲突数
- 人物状态漂移数
- 未回收关键伏笔数
- 连续低推进章节数
- 后 50 章相对前 50 章的质量变化
- Recompute 成功率

### 8.5 阶段出口标准

#### 30 天出口
- README 已修正；
- 30 章真实基线完成；
- 长度、语域、声音、winner 一致性收口；
- 有第一版产品基线报告。

#### 90 天出口
- 50+ 金样集；
- Reviewer 有校准状态；
- 自动修订净收益可报告；
- 前 100 章 Long-Arc Plan 完成；
- 成稿事实回流真实运行一次。

#### 180 天出口
- Stage Graph 落地；
- Prompt / Pipeline 解耦；
- 100 章真实长跑完成；
- 后半段质量趋势报告完成；
- 上架包可输出；
- 预算与熔断生效。

#### 1 年出口
- 至少一个 300 章以上或接近百万字项目；
- 至少一个真实平台数据闭环；
- 自动修订净收益持续为正；
- 真实商业信号和模拟信号完成校准；
- 系统能减少人工生产时间且不明显降低质量。

---

## 9. 下一阶段任务：真实作品 100 章验证（2026-07-23 实况版）

### 9.1 阶段定位

当前代码已经越过“补基础模块”阶段：全量测试为 `916 passed`；Serial Run、Workflow Scheduler、Checkpoint / Resume、Run Manifest、Long-Arc consumer、W12 candidate → approval → mint → recompute 的工程链均已存在。下一阶段不得重复建设这些能力，而应将它们收敛到一个真实作品上，证明系统能以可接受的质量、成本和人工负担连续生产。

当前证据边界必须保持诚实：

- W8 有 50 个样本目录，但 7 条仍是 skeleton seed；真人双评和仲裁尚未完全闭环；
- W9 校准管道与 summary 已存在，但高相关性结果在来源审计完成前不得直接升级为无人值守强决策；
- W10 结果仍为 `awaiting_human_review`，自动修订尚无真人净收益结论；
- W11 的 100 章 Long-Arc 状态仍为 `draft`，且内容是通用阶段目标，不是具体作品计划；
- W12 的仓库内 validation summary 仍为 `synthetic_validated`，真实审批和下一章消费仍需产品运行证明；
- 周计划引用的部分 30 章 run archive / analysis 报告当前仓库内无法稳定定位，必须先修复证据链。

因此下一阶段唯一主目标定义为：

> **完成一个作品级、分 Gate 推进、可审计可恢复、具备真人质量锚点和事实回流证据的 100 章生产验证。**

这不是“直接生产百万字”，而是百万字目标的最后一个中等规模工程与产品门槛。100 章未通过，不进入 300 章和百万字阶段。

### 9.2 五项北极星目标与最低验收指标

| 目标 | 下一阶段指标 | 100 章阶段最低门槛 | 证据来源 |
|---|---|---:|---|
| 小说质量 | 章节人工可接受率 | ≥ 75% | 真人章级复盘，不使用模型自评替代 |
| 小说质量 | 严重质量事故 | ≤ 2 次 / 10 万字 | 人设、设定、因果、明显 AI 腔与正文损坏记录 |
| 商业价值 | 黄金三章通过 | 2 名评审一致或仲裁通过 | 前 300 字、1/2/3 章专项评审 |
| 商业价值 | 商业承诺按窗口推进 | ≥ 85% | Promise / payoff checkpoint |
| 读者留存 | 章节净推进率 | ≥ 90% | 人工标签 + objective / payoff 对照 |
| 读者留存 | 连续重复功能 | 不得连续 3 章；20 章窗口 ≤ 10% | chapter-function 检查与复盘 |
| 长期稳定 | 重大事实冲突 | 0 个未经处理进入下一章 | Candidate / Approval / Mint / Projection 证据 |
| 长期稳定 | Long-Arc checkpoint 达成率 | ≥ 80% | 每 10 章计划—实际对照 |
| 自动化效率 | Artifact provenance 完整率 | 100% | run manifest 与 artifact catalog |
| 自动化效率 | Resume 成功率 | 100%，且不重复计费 | 注入中断测试与成本对账 |
| 自动化效率 | 人工干预时间 | 全程记录，目标 ≤ 30 分钟/章 | 人工操作日志；本阶段先建立基线，不伪造改善 |
| 自动化效率 | 事实候选下一章消费率 | 可报告且逐 checkpoint 提升 | Mint 前后 projection / prompt provenance 对照 |

上述阈值是进入 300 章验证的最低门槛，不等于商业成功。真实点击、三章留存、首订和追订只有在平台发布后才是商业真值。

### 9.2.9 ⚠️ 磁盘对账（2026-07-29）——先读本节再读下面的任务表

> 下面各表的 ✅ 标记**已确认与磁盘真实状态不一致**。33 个 N100 任务只有 4 个标了 ✅，
> 但至少 6 个实际已完成。**照表执行会重跑已完成的工作。**
> 本节是按 `novel-lingse/registry/derived/` 实际产物做的对账，冲突时**以本节为准**。

**实测证据盘点**（`novel-lingse`，2026-07-29）：

| 产物 | 数量 | 对应任务 |
|---|---|---|
| 30 章正文 + chapter-final | 30 / 30 | N100-033、N100-034 |
| run-manifests | 1（RUN-00001，¥1.105） | N100-001、N100-003 |
| golden-three-reviews | 1（G3R-00001） | N100-031 |
| long-arc | 1 | N100-023 |
| rolling-plans | 3 | N100-024、N100-074（第一层） |
| serial-checkpoints | 3 | N100-053（部分） |
| approval-requests / records | 1 / 1 | N100-041~043（最小闭环已通） |
| market-admission | 1 | — |
| reference profile | 1（本轮补建） | M9 / 市场锚 |
| **ReaderSignal（真实平台）** | **0** | N100-062、N100-063、**GAP-C 根因** |
| **release / 上架包** | **0** | N100-061 |

**状态订正**：

| 任务 | 表内 | 磁盘实际 | 说明 |
|---|---|---|---|
| N100-031 生成黄金三章 | 未标 | **已完成** | G3R-00001 在盘；但仅单评审（reviewer=angyang），未达两名真人标准 |
| N100-033 运行 4–10 章 | 未标 | **已完成** | 含在 30 章基线内 |
| N100-034 运行 11–30 章 | 未标 | **已完成** | RUN-00001，30/30 章 0 skip |
| N100-023 建 100 章 Long-Arc | 未标 | **已完成** | long-arc 产物在盘 |
| N100-024 Rolling Plan | ⚠️built≠live | **第一层已完成** | 见 N100-074；第二层（喂进下一窗口生成消费）仍待办 |
| N100-041/042/043 事实回流 | 未标 | **最小闭环已通** | approval-request/record 各 1，CI-M2-01~04 已 ✅ |
| N100-032 黄金三章真人评审 | 未标 | **阻塞（资源）** | 真人评审已于 2026-07-25 裁决暂缓 |
| N100-011/012 金样双评 | 未标 | **部分/无审计** | 43 真人 + 7 seed，无可审计评审者身份/时间戳 |
| N100-051/052 31–100 章 | 未标 | **未做，且不应现在做** | 30 章报告结论为 iterate 而非 go |
| N100-061/062/063 上架与平台 | 未标 | **未做（关键路径）** | ReaderSignal=0 是 GAP-C 的唯一解锁点 |

**由此得出的真实瓶颈**：不是"任务做得不够多"，而是
**ReaderSignal=0 且 release=0** —— 商业真值（3b/GAP-C）在上架前无法解锁。
上架前唯一能做的质量判断是确定性市场锚（见 `ANOVEL_QIDIAN_CRAFT_SPEC.md`）。

**执行顺序以 `ANOVEL_PLAN_CORRECTION.md` §11.6 为准**，不以本文任务编号顺序为准。

---

### 9.3 工作包与任务依赖

#### WP0：证据链与实验治理（必须最先完成）

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-001 | 修复历史 Run 证据链 | 找回或重建文档引用的 30 章 run manifest、chapter final、checkpoint、成本与质量产物；统一稳定归档路径 | 30 章 run archive index | 每章能由 manifest 定位；hash、章数、失败数、成本可复核；失效链接全部修正 | 无 | P0 |
| N100-002 | 定义 100 章实验协议 | 冻结项目、模型、Prompt、schema、reviewer policy、预算、候选数、W12 模式和变更规则；把“实验版本”定义为可审计、可复现、可比较的配置快照 | `100-chapter-experiment-protocol.v1` | 同一 run 中禁止静默漂移；变更只能在 checkpoint 后创建新实验版本；任一章节可反推所用协议 hash | N100-001 | P0 |
| N100-003 | 建统一产品证据表 | 每章记录质量、成本、人工修改、事实候选、审批、状态消费和事故；证据表必须以“章”为主键，而不是以“产物文件”为主键 | `chapter-evidence-ledger.v1` | 100% 章节有同构记录；字段有真实消费者，不新增重复 manifest；任一章可由单行记录定位到全套产物 | N100-002 | P0 |
+
+##### N100-002 协议最小字段
+
+协议必须冻结以下内容，且任一修改都要产生新版本：
+
+- `experiment_id`
+- `project_id`
+- `book_title`
+- `goal_chapter_count`
+- `target_audience`
+- `reference_pack_ref`
+- `prompt_manifest_ref`
+- `model_provider`
+- `model_id`
+- `temperature_contract`
+- `max_output_tokens`
+- `budget_limit`
+- `reviewer_policy_ref`
+- `approval_policy_ref`
+- `w12_mode`
+- `checkpoint_policy`
+- `change_policy`
+- `artifact_roots`
+- `freeze_timestamp`
+- `protocol_hash`
+
+协议验收规则：
+
+- 任何章节运行都必须记录所用 `protocol_hash`。
+- 协议内的 `model_id`、`prompt_manifest_ref`、`reviewer_policy_ref`、`approval_policy_ref` 不能在同一 `experiment_id` 下静默变化。
+- 只有 checkpoint 完成后才能切换协议版本，并且必须保留旧版本引用。
+
+##### N100-003 证据表最小字段
+
+每一章至少记录以下字段：
+
+- `chapter_id`
+- `experiment_id`
+- `protocol_hash`
+- `run_id`
+- `task_id`
+- `outline_ref`
+- `draft_ref`
+- `final_ref`
+- `manifest_ref`
+- `checkpoint_ref`
+- `quality_ref`
+- `review_ref`
+- `approval_ref`
+- `mint_ref`
+- `recompute_ref`
+- `token_usage_input`
+- `token_usage_output`
+- `token_usage_total`
+- `cost_total`
+- `human_edit_count`
+- `fact_candidate_count`
+- `fact_approval_count`
+- `fact_mint_count`
+- `state_hash_before`
+- `state_hash_after`
+- `quality_verdict`
+- `commercial_verdict`
+- `publish_readiness`
+- `incident_tags`
+- `notes`
+
+证据表验收规则：
+
+- 一章一行，不允许同章多张主表并行竞争。
+- 表里的每个引用字段都必须是可点击路径或稳定 artifact id。
+- 表里不允许“仅有摘要没有来源”的字段。
+- 如果某章缺字段，必须显式标 `missing`，不能空白。
+
*** End Patch
#### WP1：真人质量真值与策略约束

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-011 | 补齐金样集 | 将 7 条 skeleton seed 补为有正文、有来源、有授权的正式样本 | 50/50 完整样本 | body、meta、labels、notes 完整且 schema 校验通过 | 无 | P0 |
| N100-012 | 真人双评与仲裁 | 两名真人独立评分；分歧按 protocol 仲裁；AI 替身结果物理隔离 | human scores + adjudication audit | 评分者、时间、证据片段、置信度和仲裁可追溯 | N100-011 | P0 |
| N100-013 | 重跑 W9 校准 | 使用经审计真人真值生成统计与分级，检查异常高相关性和数据泄漏 | calibration summary v2 + audit | 每维有样本量、相关性、MAE、置信区间；来源可证明不是 AI 回填 | N100-012 | P0 |
| N100-014 | 约束 Selection consumer | 将维度分级应用到真实选择路径 | policy consumption report | decision 仅参与排序；diagnostic 不得单独 gate；unreliable 禁用；发布仍需人工 | N100-013 | P0 |
| N100-015 | 完成 W10 盲评 | 原稿/自动修订先做两臂盲评；若坚持原计划则补人工修订第三臂 | blind results + decision record | 全部 batch 有 winner/tie、confidence、reason codes；按策略输出 retain/restrict/disable | N100-012 | P0 |

#### WP2：作品 Genesis 与百章规划冻结

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-021 | 冻结参考输入边界 | 输入 1–5 本有合法使用依据的参考小说，只抽象卖点、节奏、钩子和冲突结构 | reference pack + originality boundary | 来源/授权可追溯；不保留可识别表达、人物和独特情节复制 | N100-002 | P0 |
| N100-022 | 冻结开书 Constitution | 生成并人工确认题材、目标读者、核心卖点、主角欲望、核心冲突、世界规则、风格和禁区 | Book Constitution v1 | Market Position、Novel Brain、角色核心和世界规则无结构冲突 | N100-021 | P0 |
| N100-023 | 建作品级 100 章 Long-Arc | 将通用 W11 草案替换为具体作品的卷目标、商业高潮、承诺、成长、关系变化与换地图条件 | work-scoped Long-Arc v1 | 每 10 章有状态变化和 payoff；每个目标可追溯到 Book Constitution | N100-022 | P0 |
| N100-024 ⚠️built≠live | 建 Rolling 10-Chapter Plan | 只细化未来 10–20 章，checkpoint 后滚动修正 | rolling plan + change records | 模块 `runtime/serialize/rolling_plan.py`（build/write/change-record）+ 制品 `rolling-10-chapter-plan.json` 已建，但**零 CLI / 零测试 / 无生产路径消费者**——尚未接入生成链（checkpoint→滚动细化下一窗口）。接入 + 回归测试为独立后续任务，不算已完成 | N100-023 | P1 |

#### WP3：黄金三章与 30 章准入

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-031 | 生成黄金三章 | 按冻结配置生产第 1–3 章，保存候选、评分文本和 winner hash | golden-three run archive | 评分 hash 与 final hash 一致；provenance 100% 完整 | N100-014、N100-023 | P0 |
| N100-032 | 黄金三章真人评审 | 两名编辑独立评审前 300 字、冲突、人物、卖点、追读、付费预期和 AI 味 | review records + adjudication | 一致通过或仲裁通过；未通过则回到 N100-022/023，不得继续扩写 | N100-031 | P0 |
| N100-033 | 运行 4–10 章 | 验证主线启动、角色声音、中文语域、事实回流和成本 | cp-010 report | 无未处理重大事故；配置未漂移；Resume 注入测试通过 | N100-032 | P0 |
| N100-034 | 运行 11–30 章 | 在 20/30 章复盘节奏、重复、承诺、事实噪声和人工负担 | cp-020/cp-030 + baseline v2 | 30 章指标达到 9.2 门槛；否则停止并输出失败原因，不为通关临时改规则 | N100-033 | P0 |

#### WP4：事实规范化与长期状态闭环

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-041 | Fact Normalization v1 | 将散文候选经实体消歧、类型分类、结构化映射、约束校验生成 approval preview | normalizer + tests + structured diff | 不新增平行事实 schema；失败可降级；冲突不得自动 Mint | N100-003 | P0 |
| N100-042 | 优先事实类型接线 | 先支持位置、伤势、能力、物品、知识、关系、承诺和事件状态 | type coverage report | 各类型有真实正文样本、批准/拒绝样本和 schema 验证 | N100-041 | P0 |
| N100-043 ✅ | 下一章消费证明 | 对每次批准执行 Mint → Recompute，并核验下一章 Prompt/Projection 消费 | consumption audit | ✅ 已补 `runtime/director/consumption_checkpoint.py`：将 consumption evidence、approved_state_constraints、promise ledger、semantic ledger 统一折成 checkpoint，并提供 `checkpoint_to_prompt_variables` 作为下一章绑定输入；未批准候选不进入事实；已批准事实可在下一章 provenance 中定位 | N100-042、N100-033 | P0 |
| N100-044 ✅ | Promise Ledger 最小闭环 | 管理承诺建立、推进、兑现、放弃和预期窗口 | promise checkpoint report | ✅ `runtime/serialize/promise_ledger.py` 复用统一 `PromiseLedgerEntry`，Promise 可汇总 resolved / pending / overdue；`runtime/outline/writer.py` 落盘 `promise-ledger.json`；`runtime/outline/workflow.py` 已接线 | N100-023、N100-041 | P1 |
| N100-045 ✅ | Chapter Evidence 产物化 | 将 chapter run manifest 继续折成 chapter-level evidence ledger，并与 checkpoint / promise / semantic ledger 共用同一 read-side 入口 | chapter evidence ledger | ✅ `runtime/serialize/chapter_evidence_ledger.py` 已提供章节证据账本与写盘；章节质量、成本、事实、事故、恢复均可在同一 ledger 中回放；不新建平行事实主表 | N100-043、N100-044 | P1 |
| N100-051 ⏳ | 运行 31–60 章 | 每 10 章滚动规划和 checkpoint，统计质量、成本、重复、事实与人工负担趋势 | cp-040/050/060 | 无连续 3 章同功能；无未处理事实冲突进入下一章 | N100-034、N100-043 | P0 |
| N100-052 ⏳ | 运行 61–100 章 | 验证高潮、承诺兑现、关系变化、卷末收束和下一卷入口 | cp-070/080/090/100 | Long-Arc 达成率 ≥ 80%；重大质量事故在阈值内 | N100-051 | P0 |
| N100-053 ⏳ | 百章恢复与预算演练 | 在真实长跑中注入 provider 失败、人工阻塞和预算停止 | recovery audit | 恢复不重写已完成 final、不重复计费、不产生半写 Facts | N100-051 | P0 |
| N100-054 ✅ | 输出 100 章产品基线 | 汇总前后 50 章质量趋势、商业承诺、事实冲突、人工修改、成本和可发布性 | 100-chapter baseline report | ✅ `runtime/serialize/long_run_baseline.py` 生成前后半程与全量基线，输出 go/iterate/stop 结论；所有指标可从原始 artifact 重算 | N100-052、N100-053 | P0 |

#### WP5：31–100 章真实长跑

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-051 | 运行 31–60 章 | 每 10 章滚动规划和 checkpoint，统计质量、成本、重复、事实与人工负担趋势 | cp-040/050/060 | 无连续 3 章同功能；无未处理事实冲突进入下一章 | N100-034、N100-043 | P0 |
| N100-052 | 运行 61–100 章 | 验证高潮、承诺兑现、关系变化、卷末收束和下一卷入口 | cp-070/080/090/100 | Long-Arc 达成率 ≥ 80%；重大质量事故在阈值内 | N100-051 | P0 |
| N100-053 | 百章恢复与预算演练 | 在真实长跑中注入 provider 失败、人工阻塞和预算停止 | recovery audit | 恢复不重写已完成 final、不重复计费、不产生半写 Facts | N100-051 | P0 |
| N100-054 | 输出 100 章产品基线 | 汇总前后 50 章质量趋势、商业承诺、事实冲突、人工修改、成本和可发布性 | 100-chapter baseline report | 所有指标可从原始 artifact 重算；明确 go/iterate/stop 结论 | N100-052、N100-053 | P0 |

#### WP6：真实发布与读者反馈准备

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-061 ✅ | 构建人工审核上架包 | 输出书名、简介、标签、卖点、黄金三章、前 30 章、原创性、红线和发布建议 | platform-neutral release package | ✅ `runtime/publishing/release_package.py` 生成可复现上架包，publish authority 明确为 human，打包 outline / golden three / first 30 / originality / redline / publish readiness | N100-034 | P1 |
| N100-062 ✅ | 定义平台数据导入 | 先支持 CSV/JSON 导入曝光、完读、三/十章留存、首订、追订、评论和弃书点 | reader-signal import profile | ✅ `runtime/serialize/platform_feedback_profile.py` 定义平台信号导入 profile，含平台、时间窗、样本量、置信度与弃书点；不得自动改写事实或正文 | N100-061 | P1 |
| N100-063 ✅ | 校准预留而非伪校准 | 规定预测信号与真实平台数据的对照方法 | calibration protocol | ✅ `runtime/serialize/calibration_protocol.py` 仅做 predicted vs real 对照，真实数据到位前保持 predicted/diagnostic；无数据不得宣称校准 | N100-062 | P1 |

### 9.4 Gate 机制

| Gate | 进入条件 | 核心评审 | 通过后动作 | 未通过动作 |
|---|---|---|---|---|
| G0 开书冻结 | WP0 完成，配置与证据链稳定 | 参考边界、定位、Constitution、预算 | 允许生成黄金三章 | 修正开书输入，不生成长篇 |
| G1 黄金三章 | 三章 archive 完整 | 两名真人评审或仲裁 | 允许运行到第 10 章 | 回到开书/Long-Arc，不扩写 |
| G2 第 10 章 | cp-010 完整 | 主线、角色、语域、成本、Resume、事实消费 | 允许运行到第 30 章 | 停止并形成失败报告 |
| G3 第 30 章 | baseline v2 完整 | 产品质量、重复、承诺、人工负担和事实闭环 | 允许运行到第 60 章 | 只允许单变量修复实验 |
| G4 第 60 章 | 趋势无持续恶化 | 中段稳定、成本、状态规模和审批负担 | 允许完成第 100 章 | 暂停扩写，先修长期控制 |
| G5 第 100 章 | 100 章报告达到门槛 | 前后 50 章趋势和卷级结果 | 进入 300 章/真实平台验证决策 | 保留产品与证据，不进入规模化 |

### 9.5 执行顺序与并行约束

严格执行以下顺序：

1. 先完成 `N100-001`–`N100-003`，修复证据和实验治理；
2. `WP1` 真人真值与 `WP2` 作品开书可并行，但黄金三章必须等待两者的强依赖完成；
3. 黄金三章通过后才运行 4–30 章；
4. Fact Normalization 可在 1–10 章期间开发，但必须在第 30 章前进入真实消费验证；
5. W10 盲评未完成前，自动修订只能建议或生成候选，不得静默覆盖 final；
6. W9 来源审计未完成前，自动评分只能排序建议，不能批准发布；
7. 第 30 章 Gate 未通过，不得以“已有 100 章计划”为理由继续扩写；
8. 第 100 章通过后，才规划 300 章和百万字压力验证。

### 9.6 阶段完成定义

下一阶段只有同时满足以下条件才可标记完成：

- 一个具体作品完成 100 章，且 run archive 可重放、可校验、可恢复；
- 黄金三章由至少两名真人评审通过；
- 50 条金样集完成真人双评和仲裁，AI 替身与真人真值严格隔离；
- W9 定级来自经审计真人真值，并约束真实 Selection consumer；
- W10 盲评形成自动修订 `retain / restrict / disable` 结论；
- 作品级 Long-Arc 被 Prompt / Objective 真实消费，每 10 章有计划—实际对照；
- 事实回流完成“提取 → 规范化 → 人工审批 → Mint → Recompute → 下一章消费”；
- 前后 50 章质量、成本、事实冲突和人工负担趋势可报告；
- 所有发布、上架、冲突事实和重大方向变更保留人类授权；
- 全量测试持续通过，所有新增能力有真实 consumer，不出现平行 schema 和重复包装层。

### 9.7 下一阶段明确不做

- 不新增 Reviewer、Persona 或 Agent 角色；
- 不扩充质量维度数量；
- 不建设复杂 Operator UI；
- 不做多项目并发；

---

### 9.8 Corpus Intelligence 执行增补（当前下一步）

> 决策日期：2026-07-25。真人评审相关工作暂缓，不删除原任务与授权边界；当前资源优先投入 AI 语料分析、规划消费和长篇事实闭环。若本节与第 9 节以真人评审为前置的顺序冲突，以本节作为近期执行顺序；真实平台数据到来前，所有商业评分仍是预测信号。

#### 9.8.1 当前主目标

将首批参考小说转成版本固定、来源可追踪、分析可恢复、可被现有 Genesis 真实消费的叙事资产。第一里程碑定义为：

> 给定固定 `CorpusSnapshot` 和开书请求，系统生成不含参考原文、来源可追溯的 `GenesisEvidencePack`；现有 Outline Bootstrap 真实消费并改变开书候选；关闭能力时旧路径保持兼容。

### 10.2 CI-M1 任务图

```text
CI-M1A Corpus Snapshot
    ↓
CI-M1B Book Narrative Profile
    ↓
CI-M1C Genesis Evidence Pack + Consumer
    ↓
CI-M1D A/B/C 受控实验
    ↓ 通过 Gate
约 140 本垂直语料扩展
    ↓
CI-M2 W12 下一章消费闭环
```

### 10.3 CI-M1A：Corpus Snapshot

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| CI-M1A-01 ✅ | 盘点 Reference 现状 | 核对 `runtime/reference/` 的 segment / measure / profile / abstract / gap、现有 Schema、CLI 和 Genesis 消费点，列出复用与替换边界 | as-built consumer map | ✅ 2026-07-26 已完成；见下方 consumer map 与复用裁决 | 无 | P0 |
| CI-M1A-02 ✅ | 定义 Snapshot 契约 | 首版只定义 `corpus-snapshot`；作品 manifest 作为其子结构，避免先建无消费者 Schema | `corpus-snapshot.schema.json` | ✅ 契约已落盘；包含 snapshot、授权策略、内嵌作品清单、manifest hash、去重/清洗/分析状态和工具链版本；禁止额外字段与原文 | CI-M1A-01 | P0 |
| CI-M1A-03 ✅ | 建 Corpus 读写边界 | 实现 snapshot loader / writer / canonical hash / query；只读外部语料资产，不写项目 Facts | `runtime/corpus/` 最小实现 | ✅ loader/writer/query/hash 已落地；`created_at` 与输入顺序不影响 hash；路径逃逸、非法 hash、重复内容未共享 cluster、篡改、未授权和未就绪均受控；11 项聚焦测试通过 | CI-M1A-02 | P0 |
| CI-M1A-04 ✅ | 建 10 本 fixture corpus | 选择一个目标题材，建立去标识化小型 fixture；包含高表现、普通、高开低走三类 | `tests/fixtures/corpus-xuanhuan-10` | ✅ 10 本全合成玄幻 fixture 已落地：top 3、control 3（含一组同 hash duplicate cluster）、high-open-low-finish 2、unknown 2（restricted 1、pending-clean 1）；7 本可分析 canonical member；库存 hash/size 校验可报告 missing/tamper；Snapshot 跨时间重放稳定；聚焦测试 14 passed | CI-M1A-03 | P0 |

#### CI-M1A-01 as-built consumer map（2026-07-26 已完成）

| 现有能力 / Artifact | 生产者 | 落盘位置 / 契约 | 当前真实消费者 | 真实状态与限制 | CI 决策 |
|---|---|---|---|---|---|
| Reference Source | `outline/sources.py::load_reference_sources` | `sources/reference-novels/*`；无独立 Schema | Outline Bootstrap、Reference Profile、Reference Abstraction、Serial originality | 只支持 1–5 个 `.txt/.md`；按文件名生成 `REF-#####`；有 sha256 与 GB18030 回退，但无授权、表现层、snapshot 和全库去重 | 保留为单项目参考输入适配器；不能承担数万本 Corpus Catalog |
| Deterministic Reference Analysis | `outline/analyzer.py::analyze_reference/merge_reference_analysis` | Outline run 的 `analysis/*.json`、`merged.json`；无独立契约 | candidate proposer/reviewer、final outline synthesis | 关键词题材、chunk 首句、冲突/回报词频；确实驱动 Outline，但信息浅，文件名和原始 hook 会进入分析产物 | 保留为兼容 baseline；不在此对象上继续堆 Corpus 字段 |
| Reference Chapter Segmentation | `reference/segment.py` | 内存 `ReferenceChapter` | Profile、Abstraction | 标题优先，无标题退化固定 chunk；200 字以下丢弃；无卷/场景层级 | 复用为 Corpus MVP 章节切分底座，不复制实现 |
| Reference Measurement | `reference/measure.py` | 内存特征向量 | Profile builder；可注入 Reviewer 双测 | 与生成正文复用 density / AI taste / hook / length 检测；只覆盖表层确定性特征 | 原样复用为 E1 特征，不冒充作品叙事画像 |
| `ReferenceQualityProfile` | `reference/profile.py`、`reference/writer.py` | `registry/derived/reference/REFPROFILE-001.json`；`reference-quality-profile.schema.json` | `reference/gap.py` 可消费；未发现默认 Serial / Genesis 主链调用 | CLI 可构建；固定单一 ID；最多 5 本；缺 corpus snapshot pin；Gap 默认生产消费不足 | 保留为章节表层质量锚，后续绑定 snapshot；不替代 Book Narrative Profile |
| Reference Gap | `reference/gap.py::compare_to_profile` | 内存报告，无独立落盘契约 | 测试或显式调用；未发现默认生产 consumer | 确定性、comparison-only、never-gates，但 built≠default-live | 后续由 Evidence/质量趋势显式接线；CI-M1A 不重建 |
| `ReferenceLMAbstraction` | `reference/abstract.py` | `registry/derived/reference-abstract/REFABSTRACT-001.json`；`reference-lm-abstraction.schema.json` | Outline Bootstrap 放入 `merged`；Serial CLI 放入内存 outline | 主要为固定模板、关键词题材和最多 240 字 excerpt；固定 ID；最多 5 本 | 保留为实验 B 和兼容路径；新 Evidence Pack 禁止 excerpt，不继续扩展此 Artifact |
| Outline Bootstrap reference path | `outline/workflow.py` | Outline run 与 final outline provenance | Genesis 调用现有 `run_outline_bootstrap`，后续生成 Brain、Position、Long-Arc | raw analysis 确实被 proposer/reviewer/synthesis 消费；Abstraction 放入 merged，但未发现 `agents.py` 对该字段的直接读取 | CI-M1C 固定接在 merged analysis → proposer/reviewer；必须证明字段被读取并改变候选 |
| Serial reference enrichment | `cli.py::_serial_run` | 仅内存 `outline["reference_abstraction"]` | 注释声明 IR / long-arc / binding 消费 | 本次符号核查未找到除装载点外的直接字段读取，存在 built≠live 风险 | 另立消费证明；不能以 CLI 显示 `+reference-abstraction` 判定完成 |
| Serial Originality | Serial CLI 直接加载 raw references | 每章 originality report / approval queue | Serial governance | 对 1–5 本默认启用且 advisory；O(body·refs)，不能扩到数万本 | 保留项目级近源检查；大语料原创性改为索引化并与 Retrieval 分离 |
| Reference CLI | `reference profile/abstract/show/validate`、`outline sources-check/bootstrap` | CLI | 操作者 | Profile/Abstract 可独立构建；Genesis 经 Outline 自动构建 Abstract | 新命令接入既有 CLI 树，不建第二入口 |

**CI-M1A-01 裁决：**

1. 现有 Reference 是“每项目 1–5 本参考小说”的生产辅助，不是数万本语料资产层；
2. 复用 `segment`、`measure`、source hash/解码、Outline consumer 和现有 LLM seam；
3. `ReferenceQualityProfile` 继续负责表层可比特征，不升级为作品级叙事知识；
4. `ReferenceLMAbstraction` 保留为实验 B，但其固定模板、固定 ID、excerpt 和弱消费不能作为目标架构；
5. 新 Corpus 层独立于项目 Facts，并以 snapshot 固定作品清单和分析版本；
6. CI-M1C 必须证明 Evidence 字段被 proposer/reviewer 读取并改变候选，不能只挂 provenance；
7. Serial 的 `reference_abstraction` 下游消费需要独立验证，不能按注释宣称已完全接线。

#### CI-M1A-02 最小契约冻结

`corpus-snapshot.schema.json` 是下一项唯一允许新增的 Corpus 契约。首版不得同时创建 Book Manifest、Pattern Store、Evidence Pack 等无消费者 Schema。作品条目先内嵌于 Snapshot；待 Profile writer 成为真实消费者后再落 `book-narrative-profile`。

Snapshot 最小字段冻结为：

- `id`、`kind`、`schema_version`、`created_at`；
- `corpus_policy.authorization_scope`、`allowed_uses`、`prohibited_uses`；
- `books[].id`、`relative_path`、`content_sha256`、`size_bytes`、`genre`、`performance_tier`、`completion_status`；
- `books[].authorization_status`、`cleaning_status`、`duplicate_cluster_id`、`analysis_status`；
- `counts.total`、`counts.by_performance_tier`、`counts.authorized`、`counts.ready_for_analysis`；
- `toolchain.segmenter_version`、`analyzer_version`、`prompt_version`、`model_policy_version`；
- `manifest_hash`。

确定性与权限语义：

- `manifest_hash` 只覆盖 canonicalized 内容，不覆盖 `created_at`，同一清单和版本必须得到同一 hash；
- `relative_path` 必须位于 Corpus 根目录内，禁止绝对路径与 `..`；
- `authorization_status != authorized` 的作品可以留在清单用于审计，但不得进入正式分析和 Retrieval；
- `duplicate_cluster_id` 相同的作品默认只有一个 canonical member 可进入统计；
- `performance_tier` 首版枚举为 `top / control / high_open_low_finish / unknown`；
- Snapshot 是 immutable derived evidence，不能写入或伪装为 `registry/facts/**`；
- 现有 `ReferenceSource` 可由 adapter 投影为 Snapshot book entry，但 Snapshot 不受 1–5 本上限约束；
- 首个消费者固定为 `runtime/corpus` loader/query 与 CI-W1 fixture validation，契约与消费者必须同批落地。

CI-M1A-02 明确不包含：原始正文、连续 excerpt、作品真实标题（生产可见字段）、作者、外部平台 ID、章节画像、Pattern、向量、AI 商业评分和项目 StoryState。

### 10.4 CI-M1B：Book Narrative Profile

首版画像只包含十二类决策字段：题材、子题材、核心幻想、目标读者、一句话卖点、主角初始缺口、长期欲望、金手指/核心能力、限制和增长轴、首次可见回报位置、第一卷商业承诺、30–100 章可持续性与中期风险。

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| CI-M1B-01 ✅ | 定义 Profile 契约 | 定义 `book-narrative-profile`，包含证据 refs、置信度和分析 provenance | Schema + 示例 | ✅ Schema 已落地：绑定 book/snapshot/manifest hash，覆盖定位、主角、成长、商业、持续性、证据和置信度；additionalProperties=false，不含正文、excerpt 或外部身份 | CI-M1A-02 | P0 |
| CI-M1B-02 ◐ | 实现 Analyzer seam | 复用现有 Model/LLM 层，实现 deterministic、LLM、consensus 三种 analyzer | `runtime/narrative_mining/` | ◐ Protocol、deterministic analyzer、snapshot-scoped writer/loader 已落地；7 本 canonical fixture 均产出合法低置信画像；LLM 与 consensus 实现留待 CI-M1B-03/04，同批 19 项聚焦测试通过 | CI-M1B-01 | P0 |
| CI-M1B-03 | 两遍分析 | 自上而下分析商业/卷级结构，自下而上分析回报、状态变化和实际增长轴 | 双分析 Artifact | 两遍独立保存，不能后一次覆盖前一次；同源失败可恢复 | CI-M1B-02 | P0 |
| CI-M1B-04 ✅ | 字段级仲裁 | 仅向仲裁模型提供冲突字段、双方结论和必要证据，不重跑整书 | consensus profile | ✅ `runtime/narrative_mining/consensus.py` 已落地；仅保留一致字段与有效证据，输出仍受 `BookNarrativeProfile` 契约约束；共识合成需要 Snapshot 绑定且至少一条完成 Pass | CI-M1B-03 | P0 |
| CI-M1B-05 ✅ | 结构一致性验证 | 检查首次回报、增长轴、主角主动性、作品完结与章节完整性等内部矛盾 | validation report | ✅ `runtime/narrative_mining/validation.py` 已落地；校验 Snapshot 绑定、manifest hash、原文/摘录隔离、成长轴/主动性/回报与低置信风险；24 项聚焦测试通过 | CI-M1B-03 | P0 |

### 10.5 CI-M1C：Genesis Evidence Pack 与真实消费

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| CI-M1C-01 ✅ | 定义任务化查询 | 以平台、题材、目标篇幅、目标读者、开书问题和禁用模式形成结构化 Genesis Query | query type + hash | ✅ 已落地；Query 只使用 task-shape 字段（genre/target_reader/chapter_index/arc_stage/target_function + current_problem/required_effect/forbidden）并固定 query_hash | CI-M1B-05 | P0 |
| CI-M1C-02 ✅ | 定义 Evidence Pack | 聚合画像统计、3–5 个正向模式、2–3 个失败模式、约束、原创性与 provenance | `narrative-evidence-pack.schema.json` | ✅ 已落盘；Schema 禁止原文、专名和外部身份字段；provenance 绑定 snapshot_hash/query_hash/profile_ids | CI-M1C-01 | P0 |
| CI-M1C-03 ✅ | 实现 Retrieval | 混合条件匹配、效果匹配、可信度和来源风险；首版不要求复杂向量库 | `runtime/retrieval/genesis.py` | ✅ 已实现 `build_narrative_evidence_pack()` 与 `build_query_hash()`；证据包可从 Snapshot/Profile 聚合并通过 Schema 验证 | CI-M1C-02 | P0 |
| CI-M1C-04 ✅ | 接入 Outline Bootstrap | 在现有 Genesis 调用 Outline 前构造 Evidence Pack，传入候选生成；不另建 Genesis | consumer wiring | ✅ `run_outline_bootstrap(..., evidence_pack=None)` 已接线；Evidence pattern 会改变候选 `design_focus/structure_basis`，final outline provenance 可定位 pack，run 独立保存 `analysis/evidence-pack.json`；关闭时旧路径兼容；Corpus Intelligence 回归 29 项通过 | CI-M1C-03 | P0 |
| CI-M1C-05 ✅ | 接入 Brain/Position/Long-Arc | 只消费结构化结论和约束，不直接读原始语料 | consumption audit | ✅ Brain 从 pattern effects / anti-pattern risks / constraints 补充 wants/avoids/forbidden；Position 经 Outline 的 market_position 保持人工/市场优先，不覆写；Long-Arc 新增 corpus_evidence 轴、约束与 provenance；现有 Brain 文件默认拒绝覆盖；Corpus Intelligence 回归 32 项通过 | CI-M1C-04 | P1 |
| CI-M1C-06 ✅ | 原创性最小防线 | 检查专名、文本 n-gram、语义和事件功能序列；记录风险但不把预测值伪装成法律结论 | originality report | ✅ 新增 Evidence 来源簇/单源占比和功能模式重叠风险；report hash 绑定 snapshot/query，可确定性回放；有安全候选时高风险候选不得自动胜出；报告显式 `comparison_only=true`、`legal_conclusion=false`；既有 Serial 文本相似检查继续负责 n-gram/正文近源风险；Corpus Intelligence 回归 35 项通过 | CI-M1C-04 | P0 |

**CI-M1C 结果补充：**Evidence Pack 现在不仅落入 `analysis/evidence-pack.json`，也进入 outline 的 `provenance.narrative_evidence_pack`，并在 outline Markdown 的「语料证据包」段落可见；其 provenance 进一步贯通到最终 outline 与后续消费链路。

### 10.6 CI-M1D：受控实验与扩容 Gate

实验固定同一模型、温度、token 预算、市场输入和候选数，唯一主变量是参考知识来源：

- A 组：当前 Genesis 基线；
- B 组：现有 `reference_abstract`；
- C 组：新 `GenesisEvidencePack`。

每组生成 5 个开书概念；对候选执行匿名、多模型、分维度 Pairwise，并交换 A/B 位置。评审维度为一句话卖点、主角吸引力、核心幻想、首次回报、第一卷承诺、30 章展开、100 章可持续性、差异化和原创性风险。

| Task ID | 任务 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|
| CI-M1D-01 | 冻结实验协议 | experiment protocol | 固定模型、Prompt、预算、候选数、Judge、位置交换和失败策略；记录 protocol hash | CI-M1C-06 | P0 |
| CI-M1D-02 | 运行 A/B/C 三臂 | run archive | 15 个概念完整落盘；评分文本与被比较文本 hash 一致；所有调用可审计 | CI-M1D-01 | P0 |
| CI-M1D-03 | Judge 去偏 | judge bias report | 每个 Judge 有 A/B 选择率、交换位置一致率、重复稳定性和分歧率 | CI-M1D-02 | P0 |
| CI-M1D-04 | 扩容裁决 | decision record | C 对 A 稳定 Pairwise 胜率 >60%；交换位置一致率 ≥75%；可持续性不降、原创风险不升，否则停止扩容并修检索 | CI-M1D-03 | P0 |
| CI-M1D-05 | 扩到垂直 140 本 | corpus snapshot v2 | 仅在 Gate 通过后执行；高表现约 80、普通约 40、高开低走约 20；成本和分析失败率可报告 | CI-M1D-04 | P1 |

### 10.7 CI-M2：W12 下一章消费闭环

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| CI-M2-01 ✅ | 定义消费证据 | 扩展或复用 chapter evidence，不新建竞争主表 | consumption evidence fields | ✅ `runtime/director/consumption.py` 生成确定性 `consumption_hash`，记录 candidate approval、mint、recompute、state before/after、objective、prompt manifest 与 draft refs | CI-M1D-04 | P0 |
| CI-M2-02 ✅ | 接入下一章 Objective | Recompute 后的 StoryState / Character Runtime 显式进入 N+1 Objective | wiring + tests | ✅ 已批准且 Mint 的事实才会在 N+1 Objective 写入 consumption/state hash 和硬约束；未 Mint 候选不进入；无 Mint 旧路径不变 | CI-M2-01 | P0 |
| CI-M2-03 ✅ | 接入 Prompt Binding | Objective 和更新状态进入现有 Prompt Manifest / binding | prompt provenance | ✅ `approved_state` 通过既有 `PromptBinding` 和 `PromptManifest` 绑定，不走旁路；有/无已批准事实产生不同 binding/rendered hash，版本可回放 | CI-M2-02 | P0 |
| CI-M2-04 ✅ | 真实 A/B 消费证明 | 对同一 N+1 章运行有/无已批准新事实两臂 | live consumption report | ✅ 92code `gpt-5.6-sol` 对同一 `TASK-00005` package 执行隔离双臂；9/9 判据成立，事实参与行动且源项目未变 | CI-M2-03 | P0 |

**CI-M2 结果补充：**`approved_state_constraints` 已进入 prompt binding 与 render 文本；`route_summary`、`model_profile_note`、`constraint_pack_note` 继续保持可见，`PromptManifest` 仍保留路由证据以供后续 run / chapter ledger 追踪。`consumption_ab_report` 也已补入两臂对照骨架，可检查 prompt/manifest/draft 变化、历史 fact hash 稳定与事实语义反映。

**CI-M2-04 live 验收（2026-08-05）：**在两个临时隔离项目副本上冻结同一 package hash `sha256:01bc56c66fb1688a52ebdc518a07a913e6333797074fa6ade81c4fb484cf335f`。A 臂不 Mint；B 臂由已确认的人类动作 Mint `ITM-00001`「赤纹星钥」并 Recompute 后生成同一章。两臂均由 92code `gpt-5.6-sol` 完成，prompt/rendered manifest/draft hash 均变化，历史 fact hash、semantic ledger 与源项目保持不变，报告可回放且 `9/9` 判据通过。人工语义审阅确认 A 臂 0 次出现该事实；B 臂 6 次使用它开启石台和水路、承担反噬并形成后续钩子，不是机械提名。报告 hash `sha256:741bddd2e93790f725879e7c86e9fe8a8c53be6a7396a24dfb14ff8685de1e5e`，两次调用合计成本 `0.327369 CNY`；精简审计归档为 `tests/fixtures/consumption-ab-live-acceptance-20260805.json`，完整重复正文不提交。

### 10.8 后续任务登记

- `CI-M3 ✅`：8–20 个开书候选、硬约束过滤、多模型 Pairwise、位置交换和黄金三章 Tournament。当前分项状态：
  - **开书专用量尺完成**：已新增独立 Genesis Pairwise Judge，不再复用章节人物 Judge；固定九维量尺，消费标题、题材、logline、主角引擎、力量体系、世界规则、角色设计、冲突阶梯及前 30 章节点。
  - **多模型分歧可报告**：同一候选快照及 hash 可交给多个 Judge；按真实候选 ID 汇总逐维/总胜局和位置交换一致率。只有九维总胜局唯一最高且 provider 一致时才给 advisory winner，分歧或并列保持 `winner=null`，人类权威不变。
  - **92code live 已通过（2026-08-05）**：冻结候选 hash `sha256:29f970b463503a08962e1f9ffe1e6feb40527f4791035b50f627a20a56b8635b`；3 组候选对、6 次双顺序调用全部可解析，`n_degraded=0`、无 call error，位置交换一致率 `88.89%`；winner 为 `CANDIDATE-C`。请求/响应 hash、token 与 92code 推导定价均已审计。
  - **Claude live 已通过（2026-08-05）**：同一候选 hash；中继忽略 `output_config` 但支持强制 Anthropic tool schema，接入 `submit_genesis_verdict` 后 3 组候选对、6 次双顺序调用全部可解析，`n_degraded=0`、无 call error，位置交换一致率 `85.19%`；winner 为 `CANDIDATE-C`。token、请求/响应 hash齐全，成本明确标为 `unpriced`。
  - **双模型共识已归档（2026-08-05）**：92code 与 Claude均通过强验收并一致选择 `CANDIDATE-C`；顶层 winner仍为 advisory，人类开书权威不变。稳定run为 `assistant-genesis-pairwise-live-20260805-final`。
  - **Outline QA 模型路径已完成（2026-08-05）**：保留确定性 `check_outline` 作为唯一结构 gate；新增独立九项 LM review、严格 JSON/tool schema、降级 provenance 和 `--outline-qa-model provider:model`。评价结果始终 `gating=false`，provider/解析失败只记 `degraded`，不阻断 bootstrap。
  - **Outline QA 双模型 live 已通过（2026-08-05）**：92code `gpt-5.6-sol` 与 Claude `claude-opus-5` 对同一冻结大纲 hash `sha256:ec1df3f2f22ce7ba96849061ff165862080069a4d63aeca31d37348752fb5718` 均返回完整九项且 `parse_ok=true`；Claude 使用强制 tool schema，成本明确为 `unpriced`。92code 最终完整 CLI workflow 另行验证 `model_integrated`，且评审 hash 与落盘 `final-outline.json` hash 一致。精简审计见 `outline-qa-live-acceptance-20260805.json`。
- `CI-M4 ✅`：Chapter Function Signature、Promise Ledger、Character Arc Ledger、Narrative Economy Ledger；`runtime/outline/ledgers.py` 已实现四类 ledger，`runtime/serialize/promise_ledger.py` 复用 Promise 结构，`run_outline_bootstrap` 已接入并落盘 `ci-m4-ledger.json` / `promise-ledger.json`，测试覆盖四类 ledger 及 archive 结果。
- `CI-M5 ⏳ blocked_before_31`：100 章 AI 长跑，跟踪前后 50 章质量、功能重复、主角主动性、角色沉寂、伏笔债务、成本和恢复。当前分项状态：
  - **协议与审计能力已就绪（2026-08-05）**：新增 `serial long-run-freeze` 与 `serial long-run-audit`；协议固定生成模型、独立 advisory reviewer、Prompt、采样、token 上限、预算、事实流、恢复和变更策略。审计只折叠既有证据，不生成正文、不 Mint、不写历史事实，始终 `comparison_only=true`、`gating=false`、`human_authority_required=true`。
  - **30 章技术证据已闭合**：`RUN-00001` 实产 `30/30`、跳过 `0`、成本 `1.105119 CNY`；Long-Arc 覆盖 100 章，Rolling Plan 已覆盖下一窗口 31–40，`cp-010/020/030` 和 30 行章级 evidence 均存在。冻结协议 hash 为 `53e09ec4312c99a6b9b19e7c0996a36924e5f4494ec2f63c2d61d5dd2441c702`，evidence hash 为 `sha256:e91d553f909cb6c48c6450378a376d3e7571109ddcffa4efe0c88dad28498083`。
  - **黄金三章双人评审已通过（2026-08-06）**：`angyang` 与 `王林` 两名真人独立记录均为 `pass`，`outcome_mode=dual_reviewer`，无需分歧仲裁；评审记录 hash 为 `7ed08ed8b58170afa39562597ed3172cfc266446374dbbbfb53f560daa320cde`。模型评审仍仅作 advisory，不替代真人权威。
  - **第 30 章 Gate 未通过**：当前唯一准入阻塞是缺少第 30 章人类权威 `go` 决策。因此 `ready_for_31_60=false`、`ready_for_61_100=false`、`complete_100=false`，不得绕过 Gate 启动 31–100 章。
  - **恢复入口**：补齐第 30 章人类 `go` Artifact 后重跑 `serial long-run-audit`；仅当状态变为 `ready_for_31_60` 才能启动 31–60 章。最新精简阻塞审计归档为 `tests/fixtures/ci-m5-long-run-audit-20260806.json`；8 月 5 日 fixture 保留双评前的历史状态。
- `CI-M6`：MVP 证明有效后扩展到数万本，采用离线分层分析、增量 hash、模型调用去重、失败恢复和 Corpus Snapshot 发布；
- 未来真实发布后，以 ReaderSignal 对照 AI 预测；上线前不得宣称商业校准。

### 10.9 明确不做

在 CI-M1 / CI-M2 通过前：

- 不全量导入数万本；
- 不让 Writer 直接检索参考原文；
- 不新增人格化 Reviewer / Agent；
- 不默认开启整章自动修订；
- 不新建第二套 Scheduler；
- 不建设复杂 Corpus UI；
- 不直接做强化学习；
- 不把模拟付费率、追读率或月票意愿称为真实商业指标；
- 不覆盖当前未提交的 `runtime/cli.py` 与 `chapter-draft.v11.prompt.yaml` 工作。
- 不自动发布或自动处理冲突事实；
- 不直接承诺百万字无人值守生产；
- 不将模拟留存、付费和 AI 双评结果表述为商业真值；
- 不进行与 100 章产品验证无直接关系的大规模 Runtime 重构。

### 9.9 WP7：正文质量杠杆与真值校准（架构顾问增量，2026-07-24）

> 本工作包由长期架构顾问基于 **RUN-00025 真实 30/33 章基线** 与 **最新代码核验** 补入。
> WP0–WP6 覆盖"能不能跑通 100 章"；WP7 补的是"跑出来的字是否值得读、系统的自评是否可信"——
> 即五北极星里 ①正文质量、②商业价值、③读者留存 目前**未被证明**的三块。
> 定位原则不变：检测/校准一律 **never-gates（ADR-003）**、新能力必须有 **真实 consumer（built≠live 禁令）**、
> 商业/留存分在真实平台数据到位前一律标 `predicted/diagnostic`，**不得宣称已校准**。
> WP7 与 WP5（31–100 章长跑）并行：N100-071/072 应在进入 G3 第 30 章 Gate 前落地，
> 使长跑基于已修正的质量杠杆；N100-073 依赖 WP6 的 ReaderSignal 导入（N100-063），是启动真实平台后的校准动作。

#### WP7 背景：三个已核验的真实缺口

| 缺口 | 证据（RUN-00025 / 代码核验） | 触及北极星 |
|---|---|---|
| GAP-A 全书恒定 AI 味（同头排比） | 每章一处连续 3–6 句同头排比，hygiene 循环逐章清不净；触发词逐章不同→真实全书性残留非误报 | ① ③ |
| GAP-B 节奏机械模板化 | serial_pacing 高潮值 `75→75→85` 完美循环 33 次；检测器报"健康"但规整本身即 AI 痕迹 | ① ③ |
| GAP-C 质量真值缺失（结构性阻塞） | LLM judge 给自产文打分高于《盘龙》Δ−32.4/18 维全反；模拟读者/留存/付费全建立在此未校准判断上 | ② ③ |

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| N100-071 ✅ | Anaphora span 定位修复（GAP-A） | hygiene anaphora 从"量化指令"升级为"引用具体 offending span"，把定位喂给 rewrite；模型对轻度 3 句排比会跳过，需精确 span 才驱动重写 | span 级 anaphora 报告 + hygiene 重写接线 + A/B | ✅ 已落地（commit 1ae186b）：发现市场锚定路径 _market_findings 早已引用具体句子，唯一缺口是固定阈值路径 check_ai_taste 只报 count+head；补 locate_anaphora_run 追加"具体需改写这几句同头"，两路对齐；+1 回归测试；同头排比子串不变（测试契约保持）、never-gates。**待办**：真实 DeepSeek A/B 验证命中率下降（当前环境无法跑真实模型） | N100-034 | P0 |
| N100-072 ✅ | Pacing 去模板化（GAP-B） | 打破 `75-75-85` 固定表：高潮值来自章节 objective/情节张力的真实函数，而非查表 | 去模板 pacing 生成 + 33 章分布对照 | ✅ 已落地（commit 704eb95）：选确定性方案而非"默认开 scene-planner"（后者每章额外 live 调用、破坏 deterministic 与 off=byte-identical）。build_chapter_ir 加可选 long_arc_coord，按每章长弧位置（逼近卷高潮加压/卷高潮/paywall 加成/卷初喘息）平移 valence 曲线，clamp [0,100]，纯投影 ADR-008、零额外调用、缺省 None→byte-identical。模拟 33 章验证：peak 唯一值 1→12、stdev 0.00→4.23。+3 回归测试 | N100-034 | P0 |
| N100-073 ⏳阻塞 | 质量真值校准器 v1（GAP-C 结构性阻塞） | 定义并落地"真实信号→judge/模拟读者校准"闭环骨架：ReaderSignal（首订/追读/弃书）作为唯一真值源反向校准预测分；无数据前只连管不宣称校准（calibrates=False 保持） | 校准协议 + 反向校准接线（dormant seam） + 审计 | judge/模拟分与真实信号可对照、可算 MAE/相关；无真实数据时一律标 predicted；不伪校准 | N100-063 | P0 |
| ↳ 阻塞原因 | | **依赖真实平台数据**（N100-063 ReaderSignal 导入未完成）。GAP-C 用工程解决不了——judge 绝对分被证伪（Δ−32.4 vs 盘龙），只有真实首订/追读/弃书能校准。这是**启动真书之后**才能做的动作，当前不可落地，不硬做 | | | | |
| N100-074 ✅第一层 | rolling_plan 接入生产链（built≠live 收尾） | 将 `runtime/serialize/rolling_plan.py`（已建、零 consumer）接入 checkpoint→滚动细化下一 10 章窗口→喂 objective/prompt；补 CLI + 回归测试 | rolling_plan CLI + 消费者接线 + tests | ✅ 第一层已落地（commit 1ef56e9）：producer（run_serial 每 checkpoint 用 outline 投影 long-arc 产 rolling plan，forward-only、纯投影 ADR-008、advisory ADR-003）+ 读侧 loader（此前 write-only）+ CLI `serial inspect --kind rolling-plan`；+5 回归测试。**第二层待办**：验收后半句"喂进下一窗口生成消费"未做——会改 content_hash、需真实 DeepSeek A/B（当前环境无法跑真实模型） | N100-024、N100-051 | P1 |
| N100-076 | 30 章逐章 goal 去模板化（GAP-B 同源，开书预演暴露） | `agents._build_first_30_chapters` 只有 5 个 pivot 章（1/3/10/20/30）有独特 goal，其余 25 章套同一句 `逼近「{desire}」的下一步，直面{enemy}`——连续章逐字复读（live 开书预演 11/30 唯一）。让非 pivot 章 goal 按卷/阶段/结构位置差异化 | 去模板化 30 章 goal + 去重率对照 | goal 唯一率显著上升、无连续多章逐字复读；确定性、never-gates、无平行 schema | N100-072 | P1 |
| N100-075 ✅ | 长跑质量趋势哨兵（GAP-A/B 防复发） | 把 anaphora/pacing/ai_taste 做成跨章趋势哨兵，接入 100 章长跑 dashboard，逐 10 章标注是否恶化 | quality-trend sentinel 报告段 | ✅ 已落地（commit 6612013）：新 _quality_sentinel_section 逐 10 章块 fold 各检测器 warning 率 + degraded_vs_prev + alerts；纯读侧投影（ADR-008，从 chapter-run 重算）、advisory 只告警不阻断（ADR-003）、无平行 schema；按 warning 率而非解析 message 文本（稳健于措辞）；<10 章返回 None；+4 回归测试 | N100-071、N100-072、N100-054 | P1 |

#### 9.10 M-01：跨 provider 路由与模型特异约束

> 这是当前最应该直接落地的下一步。原因不是“再加一个 prompt 版本”，而是把已经验证出来的模型差异变成可执行路由：同一任务在不同模型上要装配不同约束包，避免通用约束在某些模型上落地为空、在另一些模型上过约束。

| Task ID | 任务 | 实施内容 | 交付物 | 验收标准 | 依赖 | 优先级 |
|---|---|---|---|---|---|---|
| M-01-01 ✅ | 固化模型画像 | 把 GPT-5.4、DeepSeek 等已观测模型差异整理成 `model-profile`，明确哪些缺陷模式需要被路由命中 | `model-profile` 清单 | 每个已支持模型都有可读画像；画像只记录实测差异，不写推测 | 真实跑章统计、现有 prompt 版本 | P0 |
| M-01-02 ✅ | 提取约束包 | 将 v11/v12 这类已验证 prompt 约束拆成可复用 `constraint-pack`，支持按模型装配 | `constraint-pack` 规范 | 同一任务可根据模型选择不同约束包；约束包有版本号和适用模型范围 | M-01-01 | P0 |
| M-01-03 ✅ | 接入最小路由器 | 在生成前增加一个确定性路由层：输入模型名、任务类型、目标风格、已知缺陷，输出 prompt 版本与约束包 | `routing-rule` + 最小 router | 同一输入在同一模型上输出稳定；路由结果可审计、可回放、不会影响无关路径 | M-01-02 | P0 |
| M-01-04 ✅ | 做一轮对照验证 | 用同章位做 A/B：通用约束 vs 模型特异约束，验证是否真的改善目标缺陷而不过度压制正文 | routing evaluation report | 结果能证明“按模型选约束”优于“一刀切”或明确失败，二者都可支持后续决策 | M-01-03 | P0 |

**M-01 的边界：**先做“生成前路由”，不做复杂调度器；先做“模型-约束映射”，不做新 Agent；先验证 GPT / DeepSeek 的差异，不扩到所有 provider。这个任务的产出会直接服务后续 `CI-M1`/`N100` 的开书与长跑配置，避免把已知模型差异继续留在人工经验里。

**M-01 结果补充：**路由结果现已进入 `PromptManifest.route_summary`，并被投影进 envelope 的 `prompt_provenance.route_summary`，因此同一章节可在渲染、manifest、envelope 三层回溯到模型画像、约束包与路由理由。`run_manifest` 也已折入章节级 `prompt_provenance`，路由证据现在贯通到单章与整次 serial 运行两层审计视图。

---

## 10. 最终结论

ANovel 当前真正卡住的，不是“工程能不能继续堆”，而是“这套系统写出来的书，是否已经被证明值得读、值得付费、值得长期连载”。

下一阶段已经从泛化路线收敛为一个明确任务：

> **完成一个有真人质量锚点、有作品级百章规划、有事实持续回流、有恢复与成本证据的 100 章真实小说项目。**

成功顺序必须是：

1. 修复证据链并冻结实验；
2. 完成真人质量校准和自动修订盲评；
3. 冻结具体作品的开书 Constitution 与 100 章 Long-Arc；
4. 通过黄金三章和 30 章 Gate；
5. 完成事实规范化和下一章消费；
6. 跑满 100 章并输出产品基线；
7. 再决定是否进入真实平台、300 章和百万字规模化。

完成标准不是系统“看起来更复杂”，而是它能够在真实作品中持续写好、持续维护、失败可恢复、成本可控制，并且所有质量与商业结论都有可审计证据。
