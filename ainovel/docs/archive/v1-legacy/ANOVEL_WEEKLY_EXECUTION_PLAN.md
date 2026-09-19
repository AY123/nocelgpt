# ANovel 周推进执行计划

> 版本：v1.0
> 
> 用途：供 AI 按周推进项目时直接执行、直接验收、直接回溯。
> 
> 依据：`docs/ANOVEL_FUTURE_PLAN.md`、`docs/ANOVEL_EXECUTION_TASKS.md`、`ROADMAP.md`、当前仓库代码与前述审核结论。
> 
> 原则：每周只推进一个主问题，其他事项尽量不动；凡未校准的信号，只能做诊断，不得做强决策。
>
> 当前进度快照（基于最新仓库事实）：
> - `W1-01` 的事实入口整理已完成到文档索引层，`docs/README.md` 已明确权威文档入口与优先级；根 `README.md` 是否同步仍需核对。
> - `W1-02` 的状态源职责已在 `ROADMAP.md` / 本计划 / `docs/ANOVEL_FUTURE_PLAN.md` 中明确。
> - `W1-03` 的能力矩阵已在 `ROADMAP.md` 中以能力/consumer/validation 方式部分建立，但周计划所要求的专用矩阵仍可继续补强。
> - `W1-04` 的短基线已完成独立冻结流程：`serial precheck`、`serial freeze`、`serial baseline-compare`、`quality-snapshot`、`baseline-freeze`、`baseline-compare report` 已落地并通过针对性测试；下一步重点转为固定样本与 30 章基线衔接。

---

## 1. 周推进总原则

### 1.1 只保留一条主线
每周只回答一个核心问题：
- 这周是在修事实入口，还是在修正文质量，还是在做 30 章基线，还是在做金样集校准。
- 不允许一周同时大修正文、重构流水线、再加新 Agent、再改商业逻辑。

### 1.2 每周必须产出四类结果
1. **可审计产物**：文档、manifest、评审记录、版本记录。
2. **可运行结果**：测试、短跑、真实模型或 replay 运行。
3. **可比较结果**：与上周基线可直接对照。
4. **可决策结论**：本周是否通过、是否回滚、是否进入下一周。

### 1.3 每周任务的完成定义
一个周任务只有同时满足以下条件才能标记 Done：
- 问题定义清楚；
- 有真实消费者；
- 实现完成；
- 测试通过；
- 真实模型路径或明确的确定性验证已运行；
- 质量相关任务有人工作品评估；
- artifact 与 provenance 完整；
- 已知限制已记录；
- 能明确指出下周要不要继续、继续什么。

### 1.4 每周禁止事项
- 不新增没有真实消费者的 Schema。
- 不新增未经消融验证的 Agent。
- 不把模拟读者分数当真实商业预测。
- 不让评价性信号阻塞 deterministic build。
- 不让 Reviewer 自动批准发布。
- 不以测试数量代替内容成熟度。

---

## 2. 12 周周推进节奏

### 第一阶段：第 1–4 周，项目事实与中文正文收口
目标：先把“项目是否真实、正文是否可读”做实。

### 第二阶段：第 5–8 周，30 章基线与质量真值
目标：先建立可验证的产品基线，再谈自动化改进。

### 第三阶段：第 9–12 周，自动修订与长弧规划
目标：验证自动修订净收益，并把单章能力推进到百章规划。

---

## 3. 第 1 周计划：事实恢复周

### 3.1 本周目标
统一项目事实入口，消除 README / ROADMAP / 当前代码状态之间的漂移。

### 3.2 本周主问题
“当前项目到底已经做到了什么？”

### 3.3 最新进度校正（依据当前仓库事实）
- `docs/README.md` 已明确文档入口与优先级，周推进入口没有漂移。
- `ROADMAP.md` 已记录 as-built / deferred 边界，属于事实账本而不是前向计划。
- `runtime/serialize/` 侧的基线链路已具备：`serial precheck`、`live baseline report`、`baseline freeze`、`quality snapshot`。
- 对应测试已通过，说明基线冻结能力不是纯文档，而是可运行产物。
- 但“2–3 章固定旧基线”的独立冻结动作仍应作为当前主推进项继续落实。

### 3.4 本周任务

| 任务 ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W1-01 | 恢复事实入口 | 重写根 `README.md`，只保留真实状态、仓库边界、运行方式、权威文档入口 | README 能让新成员快速理解项目现状 | 无 | 减少误读与重复建设 | 写成空泛介绍 | P0 |
| W1-02 | 整理状态源 | 明确 `ROADMAP.md` 是 as-built ledger，`docs/ANOVEL_FUTURE_PLAN.md` 是前向路线图，历史审核报告只作参考 | 所有状态文档职责清晰 | W1-01 | 防止事实源混乱 | 再次把历史文档当事实源 | P0 |
| W1-03 | 建能力矩阵 | 为核心能力补上“schema / consumer / tests / live proof / product proof / commercial proof”字段 | 每项能力能区分工程完成与产品完成 | 无 | 后续 AI 读取更可靠 | 过度维护导致文档膨胀 | P0 |
| W1-04 | 固定旧基线 | 冻结 2–3 章当前版本基线，保存 prompt / run / cost / state / quality 产物 | 可 Replay，可对比 | 现有运行入口 | 为后续改动建立参照 | 基线样本与比较报告仍可继续补强 | P0 |

### 3.4 本周出口标准
- README 已修正；
- 能力矩阵已建立；
- 历史文档角色明确；
- 旧基线已冻结并可重放；
- `serial baseline-compare` 与基线比较报告已可生成。

### 3.5 当前完成度校正
- `W1-04` 已从“单次冻结”推进到“冻结 + 比较报告”闭环；
- `W1-01`、`W1-02` 在文档层已基本完成，仍可在根 `README.md` 与能力矩阵中进一步对齐；
- `W1-03` 可继续补成更明确的能力矩阵模板，但不阻塞后续任务；
- `W2-01`~`W4-04` 仍处于待推进状态，当前不应跳过第 2 阶段直接进入 30 章扩写。

### 3.5 本周若失败，下一步
如果本周未完成，下一周不进入正文改造，优先补事实入口与基线。

---

## 4. 第 2 周计划：中文与长度周

### 4.1 本周目标
先解决正文最直观、最伤首订的硬问题：长度与语域。

### 4.2 本周主问题
“正文是否已经像中文商业网文，而不是像中英混合的技术草稿？”

### 4.3 最新完成度校正
- 长度口径已有统一入口：新增 `runtime.serialize.text_metrics.measure_text_length`，可给正文提供 `body_chars` / `nonspace_chars` / `paragraph_count` / `token_estimate`。
- 中文语域也已有基础检测入口：新增 `runtime.serialize.text_language.measure_text_language`，可识别长 ASCII 段、英文占优与中文字符占比。
- `quality_snapshot` 已把长度与语域信号写入 snapshot，且 `run_serial` 章节结果也开始保存该快照，周计划里的“长度口径统一 / 语域稳定”已接入章节生产链路。
- 已补齐 `serial precheck` / `serial freeze` / `serial baseline-compare` 的短跑验证入口与测试；并新增 `short_run_validation_report` 作为短跑验证汇总，`run_serial` 现在会在 2+ 章短跑中自动落盘验证报告，且新增 `serial validation-report` 可直接查看落盘结果。正文前后对比报告也已补齐，下一步是继续用正文前后对比样本验证检测是否真能帮助修正文，而不是直接跳到 30 章基线。

### 4.3 本周任务

| 任务 ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W2-01 | 统一长度口径 | 明确 `han_char_count` / `display_char_count` / `token_estimate` 的使用边界 | 同一正文在各模块长度结果一致 | W1-03 | 节奏与成本口径统一 | 破坏旧统计兼容性 | P0 |
| W2-02 | 锁定中文语域 | 在生成约束中明确简体中文、允许英文范围、禁止整段英文漂移 | 真实短跑中无无理由整段英文 | W1-04 | 提升正文可用率 | 过强约束导致机械化 | P0 |
| W2-03 | 章节角色分区 | 定义章节功能与长度区间的对应关系 | 能解释章节为何过长或过短 | W2-01 | 让长度管理服务内容节奏 | 角色定义过粗 | P1 |
| W2-04 | 跑 2–3 章短跑 | 对比旧基线与新约束效果 | 短跑长度、语域改善可见 | W2-01~03 | 快速发现方向是否正确 | 过早扩写 | P0 |

### 4.4 本周出口标准
- 长度统计统一；
- 中文语域稳定；
- 2–3 章短跑可比；
- 能明确指出是否需要进入角色声音修复。

---

## 5. 第 3 周计划：角色声音与 AI 味周

### 5.1 本周目标
解决“看起来像 AI 写的”和“角色说话像同一个人”的问题。

### 5.2 最新推进状态
- 已新增 `SpeechProfile` 结构，并补了 `render_speech_profiles` / `merge_speech_profiles` / `coerce_speech_profile`，用于承载角色语气、句长、词汇层级与禁忌表达。
- 已新增匿名台词识别的最小规则测试入口 `identify_speaker`，并补了最小 `ab_cleaning_report` 结构、`ab_cleaning_flow` 样本流、`ab_cleaning_query` 查询入口与 `write_ab_cleaning_flow` 落盘入口，下一步继续做更完整的匿名台词识别与 A/B 清洗。

### 5.2 本周主问题
“正文是否已经具备最基本的角色差异与自然感？”

### 5.3 本周任务

| 任务 ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W3-01 | 配置 Speech Profile | 为至少 3 个主要角色建立语气、句长、用词层级、禁忌表达 | Speech Profile 真正进入 Prompt 消费路径 | W2-02 | 角色更有辨识度 | 口头禅堆砌 | P0 |
| W3-02 | 建 AI 味错误集 | 从真实输出中整理同义重复、抽象情绪、形容词堆叠等模式 | 可明确区分可检测项和主观项 | W2-04 | 为清洗提供依据 | 把风格误当错误 | P0 |
| W3-03 | 匿名台词识别测试 | 去掉角色名后人工判断说话者 | 识别率明显高于随机水平 | W3-01 | 验证角色声音区分 | 样本过少 | P0 |
| W3-04 | 运行 A/B 清洗 | 对比修改前后自然度、信息密度、角色声音 | AI 味评分改善且净推进不下降 | W3-02 | 直接改善正文可读性 | 统一短句化 | P1 |

### 5.4 本周出口标准
- 至少 3 个角色的声音可区分；
- AI 味错误集已形成；
- 清洗前后效果有人工证据；
- 可决定是否进入 winner 一致性修复。

---

## 6. 第 4 周计划：Winner 证据与黄金三章周

### 6.1 本周目标
保证“被评分的正文”就是“最终落盘的正文”，并开始黄金三章专项评审。

### 6.2 最新推进状态
- 已新增 `golden_three_review_pack`，可把前三章材料整理成一个可评审、可追溯的打包对象。
- 已新增 `golden_three_review_record`，可把评审人、备注和 pack 一起留档；已补查询入口，下一步可继续验证 Winner 漂移与黄金三章结论。

### 6.2 本周主问题
“被评审选中的正文，是否就是最终正文？”

### 6.3 最新推进状态
- 已新增 `30ch_launch_plan`，可将 30 章实验启动参数冻结成一个可追溯的启动计划，且已补落盘写入器与测试。
- 已新增 `30ch_launch_report` 与查询入口，且补了 `30ch_launch_link` / `30ch_run_attachment` 以关联 run manifest，并新增 `30ch_launch_bundle` / `30ch_launch_bridge` / `30ch_launch_summary` 做总查询与桥接汇总；另外补了 CLI 回归测试，确保入口不被破坏。已新增 `30ch_run_summary` 用于把启动摘要接到运行结果，且已补查询/落盘入口与 CLI 查询入口；又补了 `run_archive_bridge` 作为最小运行归档桥接层，并补了落盘写入器；再往上补了 `run_aggregate` 作为运行级汇总对象，并补了查询/落盘入口。（曾试作 `run_manifest_alias` / `run_overview` 两层，但二者只是 `run_aggregate` 的逐字节重复包装、未折叠任何新事实，且 `run-overview` CLI 因 `load_run_overview` 从未定义而必崩——已整体删除，运行级链路保留到 `run_aggregate` 为止。）下一步是继续寻找/补齐实际 serial run / manifest 的真实接点，开始第 5 周的 30 章实验启动。

### 6.3 最新推进状态
- 已新增 `winner_drift_report`，可对“被评分的正文”和“最终落盘正文”做 hash 一致性检查，且已补查询/落盘入口。
- 已新增第一版 `baseline_report`，可把黄金三章评审包与 Winner 漂移结果汇总为统一报告，并补了查询/落盘入口。

### 6.3 本周任务

| 任务 ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W4-01 | 修复 Winner 漂移 | 候选先持久化，再比较，再选 winner | 评分 hash 与落盘 hash 一致 | W1-04 | 质量实验可信 | 重构影响流程 | P0 |
| W4-02 | 冻结 30 章实验配置 | 锁定题材、模型、prompt、成本策略 | 可完整重建实验 | W4-01 | 避免多变量干扰 | 中途改目标 | P0 |
| W4-03 | 黄金三章人工评审 | 做前 300 字、第一章、第二章、第三章专项评审 | 至少 2 名人工评审一致或仲裁 | W2-04、W3-04 | 验证开篇是否成立 | 评审标准不一致 | P0 |
| W4-04 | 输出第一版基线报告 | 记录本轮短跑问题与可修复项 | 报告完整、可追溯 | W4-01~03 | 为后续 30 章基线做准备 | 结论空泛 | P1 |

### 6.4 本周出口标准
- Winner 证据一致；
- 黄金三章有人工结论；
- 实验配置冻结；
- 可进入第 5–8 周 30 章基线生产。

---

## 7. 第 5 周计划：30 章基线启动周

### 7.1 本周目标
先把 `M5` 的最小 `workflow-run` 骨架做出来：能启动、能落盘、能恢复、能留痕，但不扩展到完整 30 章流水线。

### 7.2 本周主问题
“我们是否已经拥有一个最小但真实可运行的 `workflow-run`？”

### 7.3 M5 最小骨架定义

`M5` 只做四件事：
1. **创建 run manifest**：记录 `run_id`、`story_id`、`status`、`cursor`、`input_hash`、`budget`、`created_at`、`updated_at`。
2. **单次启动**：从既有 serial 入口启动一次，不新增新的内容决策层，只包一层 run 级外壳。
3. **checkpoint / resume**：失败后可从 `cursor` 继续，已完成章节可重放或跳过，确保 run 可恢复。
4. **run 级审计**：把本次运行的结果、花费、失败章节、产物路径写回 derived，供后续基线比较。

### 7.4 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| M5-01 | 定义最小 run schema | 明确 workflow-run 的 manifest 字段、状态机和保存位置 | schema 可校验、字段不过度扩张 | 现有 serial / manifest 链路 | 先把 run 作为独立事实对象立住 | 过度设计 | P0 |
| M5-02 | 打通启动与恢复 | `start` / `resume` / `step` 三个入口形成闭环 | 可从中断点恢复，结果可重复 | 现有 `workflow_scheduler` | 最小运行骨架可用 | 与 serial 入口耦合过深 | P0 |
| M5-03 | 产出 run 级审计 | 保存 run manifest、batch audit、chapter final 关联信息 | 运行后可定位每次输出和失败原因 | M5-01、M5-02 | 便于后续 30 章基线复盘 | 审计字段杂糅 | P0 |
| M5-04 | 控制最小范围 | 不引入新 Agent、不新增质量策略、不改正文决策 | 仅 orchestration 层变更 | M5-01~03 | 降低风险，先验证骨架 | 想顺手补全功能 | P1 |

### 7.5 本周出口标准
- `workflow-run` 能以最小 manifest 形式创建并保存；
- `start` / `resume` / `step` 可以执行并恢复；
- run 级 audit 与 chapter final 关联可追溯；
- 没有新增正文决策层，没有新增 Agent。

### 7.6 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W5-01 | 启动 30 章实验 | 基于冻结配置开始连续生产 30 章 | 生成链路稳定运行 | W4-02 | 进入真实产品验证 | 中途漂移 | P0 |
| W5-02 | 建立章级记录 | 每章记录长度、成本、retries、QA、Review、Revision、Selection、state hash、facts | 每章 provenance 完整 | W5-01 | 后续可审计可回放 | 记录负担过高 | P0 |
| W5-03 | 第 10 章复盘点 | 在第 10 章检查主线推进、角色关系、重复结构、成本、事实噪声 | 可生成中途方向结论 | W5-01 | 及早止损 | 过早频繁改方向 | P0 |

### 7.7 本周出口标准
- 30 章生产已启动；
- 每章 provenance 可追踪；
- 第 10 章复盘机制已运行。

---

## 8. 第 6 周计划：30 章生产推进周

### 8.1 本周目标
继续推进到 20 章，验证中段连续性。

### 8.2 本周主问题
“正文能否在连续生成中保持语域、长度、角色与事实稳定？”

### 8.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W6-01 | 继续生产 11–20 章 | 保持冻结配置连续生产 | 连续生成不中断 | W5-03 | 观察中段稳定性 | 成本上升 | P0 |
| W6-02 | 检查事实候选噪声 | 记录候选数量、有效率、冲突率 | 噪声可被人工承受 | W6-01 | 为后续事实回流做准备 | 噪声过高 | P1 |
| W6-03 | 第 20 章复盘点 | 检查主线、人物关系、承诺兑现、重复结构 | 可判断是否继续 21–30 章 | W6-01 | 早期纠偏 | 复盘标准偏主观 | P0 |

### 8.4 本周出口标准
- 已推进到 20 章；
- 中段连续性可评估；
- 可决定是否继续完成 30 章。

---

## 9. 第 7 周计划：30 章收口周

### 9.1 本周目标
完成 21–30 章，并输出第一版产品基线结论。

### 9.2 本周主问题
“这套系统是否能完成一个完整 30 章的产品级基线？”

### 9.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W7-01 | 完成 21–30 章 | 连续生产并保留 provenance | 30 章完整 | W6-03 | 形成产品基线 | 成本高 | P0 |
| W7-02 | 第 30 章完整复盘 | 检查商业承诺兑现、重复结构、可发布性 | 可输出 30 章复盘报告 | W7-01 | 判断是否进入金样集阶段 | 结论过于乐观 | P0 |
| W7-03 | 输出 30 章真实产品基线报告 | 汇总 30 章质量、成本、人工修改、问题分布 | 报告可审计 | W7-01、W7-02 | 后续路线有真实依据 | 指标失真 | P0 |

### 9.4 本周出口标准
- 30 章完成；
- 可发布性初判完成；
- 30 章产品基线报告输出。

---

## 10. 第 8 周计划：金样集启动周

### 10.1 本周目标
把“系统自己怎么看”切换成“人工真值怎么判断”。

### 10.2 本周主问题
“质量评分是否有人工锚点？”

### 10.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W8-01 | 建立金样集框架 | 定义样本类别、评分维度、仲裁规则 | 金样集结构明确 | W7-03 | 让质量系统有真值 | 分类过细 | P0 |
| W8-02 | 收集 50+ 样本 | 覆盖正例、反例、边界样本、系统自产样本；当前仅有 10 个 seed，需继续扩充到 50+ 并保留来源与授权信息 | 样本可追溯、有授权，且正/反/边界/系统自产分布可报告 | W8-01 | 形成校准基础 | 样本不平衡 | P0 |
| W8-03 | 双评与仲裁 | 每个样本至少两人评分，分歧进入仲裁 | 一致性可报告 | W8-02 | 评分可信度提升 | 人工成本高 | P0 |

### 10.4 本周出口标准
- 金样集开始形成且样本数达到 50+；
- 评分与仲裁流程清晰；
- 可以进入 Reviewer 校准。

### 10.5 当前执行说明
- `W8-01` 框架已就绪，`quality-golden-set/metadata/` 下的 schema、protocol、calibration template、reviewer calibration schema、crosswalk 等基础文件已存在。
- `W8-02` 当前仅完成 10 个 seed（`QGS-00001`~`QGS-00010`），其中已覆盖 positive / negative / boundary / ai_voice / padding / no_conflict / character_degradation / ending_failure 等基础类别。
- 接下来应优先补足到 50+ 样本，并在新增样本时补齐：`body.txt`、`meta.json`、`human_scores.json`、`labels.json`、`notes.md`，确保样本可审计、可追溯、可仲裁。
- 建议的扩充顺序是先补齐“分布缺口”再补齐“内容缺口”：按 `metadata/distribution.json` 的 100 条目标分布折算到 50 条里程碑，当前 10 条种子之后，新增 40 条建议配额为：`positive` +10、`negative` +8、`boundary` +4、`ai_voice` +5、`padding` +5、`no_conflict` +4、`character_degradation` +2、`ending_failure` +2。
- 为了满足 `metadata/crosswalk.json` 的覆盖要求，新增样本应至少触达这些维度组合：`opening_hook` / `conflict_progression` / `ending_hook` / `continue_intent` / `ai_voice_risk` / `continuity` / `information_density` / `payoff_delivery` / `character_motivation`。
- 新样本编号建议直接按 `QGS-00011` 到 `QGS-00050` 顺序递增。建议的 40 条分配为：`QGS-00011`~`QGS-00020` `positive`，`QGS-00021`~`QGS-00028` `negative`，`QGS-00029`~`QGS-00032` `boundary`，`QGS-00033`~`QGS-00037` `ai_voice`，`QGS-00038`~`QGS-00042` `padding`，`QGS-00043`~`QGS-00046` `no_conflict`，`QGS-00047`~`QGS-00048` `character_degradation`，`QGS-00049`~`QGS-00050` `ending_failure`。
- `W8-03` 的双评仲裁建议按以下最小流程执行：每条样本至少 2 名评分者独立评分；若主分类一致但分数差异超过阈值，则进入复核；若主分类不一致或出现边界争议，则进入仲裁；仲裁结果必须写回 `human_scores.json` 与 `notes.md`。
- 边界样本必须保留分歧证据，不能强行“消歧”成统一意见；正例必须展示清晰强项，负例必须展示清晰失败模式。
- `QGS-00001` 的现有结构可作为新增样本模板参考：`meta.json` 负责来源、风险与目标维度；`labels.json` 负责主问题/次问题/强项/是否边界；`human_scores.json` 负责双评数值、分歧说明与最终裁决。
- 建议新增样本统一采用相同骨架，以便后续批量审核与仲裁：`sample_id`、`title`、`genre`、`chapter_position`、`source_type`、`source_hint`、`risk_flags`、`revision_candidate`、`target_dimensions`、`body.txt`、`labels.json`、`human_scores.json`、`notes.md`。
- 参考 `QGS-00002` 的写法，`meta.json` 中 `title` 应直接表达该样本的评审命题，例如“开篇强目标与危机并置”；`target_dimensions` 应控制在 3–5 个核心维度，避免面面俱到导致样本失焦。
- 参考 `QGS-00002` 的 `notes.md`，每条样本都应写清“证据摘要 / 校准重点 / 风险说明”，这样后续双评和仲裁才有统一语义入口。
- 在未达到 50+ 之前，`W8-03` 仅可做流程演练，不应作为正式校准结论的依据。

### 10.6 50 条补样总表

| 范围 | 类别 | 条数 | 作用 |
|---|---|---:|---|
| `QGS-00001`~`QGS-00010` | seed / mixed | 10 | 当前已有种子，覆盖基础正负边界与失败模式 |
| `QGS-00011`~`QGS-00020` | positive | 10 | 高质量正例，提供回归基准 |
| `QGS-00021`~`QGS-00028` | negative | 8 | 明确失败模式，拉开质量差距 |
| `QGS-00029`~`QGS-00032` | boundary | 4 | 制造合理分歧，用于校准 |
| `QGS-00033`~`QGS-00037` | ai_voice | 5 | 专项识别 AI 腔 |
| `QGS-00038`~`QGS-00042` | padding | 5 | 专项识别注水拖沓 |
| `QGS-00043`~`QGS-00046` | no_conflict | 4 | 专项识别冲突不足 |
| `QGS-00047`~`QGS-00048` | character_degradation | 2 | 专项识别人设断裂/降智 |
| `QGS-00049`~`QGS-00050` | ending_failure | 2 | 专项识别断章失败 |

### 10.7 当前 W8 可判定状态
- **框架完成**：`W8-01` 已完成。
- **补样完成**：`W8-02` 已完成，当前样本数已达 50。
- **正式校准可启动**：`W8-03` 可进入正式双评与仲裁，不再只是演练。
- **进入第 9 周门槛**：已满足，样本数达到 50+，且分布与授权信息完整。

---

## 11. 第 9 周计划：Reviewer 校准周

### 11.1 本周目标
把“有评分器”变成“评分器能分辨什么是好，什么是坏”。

### 11.1.1 进入条件确认
- `W8-01` 框架已完成。
- `W8-02` 补样已完成，样本数达到 50。
- `W8-03` 可正式开始双评与仲裁。
- 因此现在可以进入第 9 周任务。

### 11.1.2 当前状态
- `W9-01` 已从“准备”推进到“真实回填 + 汇总”阶段。
- 已生成并接通校准包 `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-pack.json`，用于组织 50 条样本的校准输入。
- 已生成并接通校准报告骨架 `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-report.json`，用于落盘维度覆盖与后续评分结果。
- 已生成并接通校准队列 `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-queue.json`，逐条列出 50 条样本的校准顺序与运行约束。
- 已生成人工预审子集 `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-subset.json`，其中 `QGS-00001`、`QGS-00002`、`QGS-00003`、`QGS-00029`、`QGS-00033` 为 5 条优先试跑样本。
- `reviewer-calibration backfill` 已可将 5 条试跑样本写入正式回填结果；`reviewer-calibration backfill-all` 已可执行全量回填，当前真实回填结果为 43 条，另外 7 条属于 `README.txt` 明确标注的 skeleton seeds（仅保留结构，不含正文），因此结果状态应按 `complete_with_skeleton_seeds` 理解，而不是失败。
- `QGS-00001` 已存在可用的真实人工评分 `human_scores.json`，其余纳入批量回填路径的样本也已完成真实回填，不再停留在 synthetic 预览阶段。
- 已停用所有 `synthetic` 预览文件，正式路径仅保留 `w9-calibration-results.json` 作为真实回填容器。
- `reviewer-calibration summary --write` 已可输出并落盘 `w9-calibration-summary.json`，同时可生成 Markdown 版 `w9-calibration-summary.md`，汇总每维度样本量、相关性、误差、置信区间和边界样本表现。
- 现在 `W9-01` 的关键工作不是继续扩结构，而是执行回填、生成 summary，并据此把 12 个维度明确分成 `decision / diagnostic / unreliable` 三档，写入系统可直接读取的 `dimension_grading` 结构；骨架种子需要在后续样本补齐阶段单独处理，不能混作正式校准样本。
- 本周不再补样；本周只校准评分器。

### 11.2 本周主问题
“哪些评分维度真的可信？”

### 11.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W9-01 | 校准 Reviewer | 对比自动评分与人工评分，分级每个维度 | 每个维度有样本量、相关性、置信区间 | W8-03 | 避免错误优化 | 把诊断信号当决策信号 | P0 |
| W9-02 | 标注 decision / diagnostic / unreliable | 给每个维度定级 | 系统界面可显示校准状态 | W9-01 | 让后续决策分层 | 标注过度保守 | P0 |
| W9-03 | 去掉未校准强决策 | 未校准维度不得驱动自动 Selection | 自动决策只用可信维度 | W9-01~02 | 降低误判风险 | 过度依赖少数维度 | P0 |

### 11.4 本周出口标准
- Reviewer 有分级；
- 未校准维度退出强决策；
- 可以进入自动修订盲评。

---

## 12. 第 10 周计划：自动修订盲评周

### 12.1 本周目标
验证自动修订是否真的改善作品，而不是只改善分数。

### 12.1.1 进入条件确认
- `W9` 已完成预览级流程验证，但正式人工评分结果仍待真实输入。
- `W10-01` 已完成盲评样本准备的骨架搭建，候选池、批次、输入模板、结果模板均已落盘。
- `W10-02` 已具备执行条件，接下来只需填充批次级盲评结果；结构性文件已齐备，不再新增模板。
- 盲评执行日志 `AI-Novel-Runtime/quality-golden-set/metadata/w10-blind-review-execution-log.json` 已落盘，可直接记录 batch 级结果。
- 当前 `W10` 进入“只填值、不加结构”的阶段，后续工作应集中在 batch 结果回填和最终汇总。
- 单批次回填模板 `AI-Novel-Runtime/quality-golden-set/metadata/w10-blind-review-result-template.json` 已落盘，可直接用于写入任意 batch 的真实或测试结果。

### 12.2 本周主问题
“自动修订到底值不值得继续做？”

### 12.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W10-01 | 准备盲评样本 | 选至少 30 个问题章节，准备原稿 / 自动修订 / 人工修订 | 样本可盲评 | W9-03 | 形成比较基线 | 样本挑选偏差 | P0 |
| W10-02 | 执行盲评 | 隐去来源，人工排序 | 自动修订净胜率可计算 | W10-01 | 判断自动修订收益 | 评审者疲劳 | P0 |
| W10-03 | 限定保留策略 | 只保留稳定提高质量的修订类型 | 无净收益策略降级 | W10-02 | 避免噪音放大 | 过度删除风格 | P1 |

### 12.3.1 当前执行说明
- `W10-01` 已完成样本池与候选集结构，当前不再扩池，下一步进入真实批次结果回填。
- `W10-02` 的盲评结构已定义，`w10_blind_review_triple_structure.json` 作为三版本比较模板。
- 当前执行重点从“搭结构”切换为“填结果”：优先回填 `W10-B01`，然后按 batch 继续推进。

### 12.4 本周出口标准
- 自动修订净收益有证据；
- 无净收益策略已降级；
- 可以进入长弧规划。

### 12.5 当前执行状态
- 结构性模板已完成，`W10` 当前处于真实批次结果回填阶段。
- 先回填 `W10-B01`，再按 batch 继续，避免继续扩建模板。

---

## 13. 第 11 周计划：Long-Arc 规划周

### 13.1 本周目标
把单章质量推进到百章叙事规划。

### 13.1.1 进入条件确认
- `W10` 的盲评结构已冻结，当前仅剩 batch 结果回填。
- `W11-01` 已启动，长弧计划、mandate/objective、重复功能检查骨架均已落盘。

### 13.2 本周主问题
“前 100 章的成长、冲突、高潮、付费点是否有明确规划？”

### 13.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W11-01 | 定义前 100 章 Long-Arc | 定义卷结构、阶段目标、商业高潮、换地图条件 | 每 10 章有可追溯目标 | W7-03、W9-03 | 中后期不容易疲劳 | 规划过细 | P0 |
| W11-02 | 写入 Mandate / Objective | 将长弧约束注入现有生成链路 | 章级目标受长弧约束 | W11-01 | 让规划真正生效 | 约束过多导致僵硬 | P1 |
| W11-03 | 检查章节功能重复 | 检测连续重复、周期重复、换名字但同功能 | 可识别重复风险 | W11-01 | 防止中后期原地打转 | 误报 | P1 |

### 13.4 本周出口标准
- 前 100 章长弧完成；
- 可以进入事实回流的生产化阶段。

---

## 14. 第 12 周计划：事实回流周

### 14.1 本周目标
让成稿事实回流成为默认生产路径。

### 14.1.1 进入条件确认
- `W12` 的候选提取、审批、Mint、语义账本骨架均已落盘。
- `W12-01` 已进入可执行状态，后续可直接接入正文证据。
- `W12` synthetic 冲突测试、仲裁日志、resolved state 与 next-chapter projection 已验证，说明回流链路可跑通。

### 14.2 本周主问题
“正文中的新事实，能否稳定回流并在下一章被正确消费？”

### 14.3 本周任务

| Task ID | 目标 | 具体任务 | 验收标准 | 依赖关系 | 预期收益 | 风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| W12-01 | 启动候选提取 | Final 后自动提取 candidate facts | 每条候选能定位正文证据 | W7-03 | 让事实可演化 | 候选噪声过高 | P0 |
| W12-02 | 批量审批 | 分类队列：additive / new / conflicting / unverifiable | 每条事实写入有 Approval Record | W12-01 | 降低手工混乱 | 审批负担高 | P0 |
| W12-03 | Mint / Recompute | 批准后通过唯一 Mint 入口写入并重算投影 | 下一章读取更新后的状态 | W12-02 | 长篇连续性增强 | 半写状态 | P0 |
| W12-04 | 语义状态账本 | 建知识、能力、伤势、物品、关系期待、承诺账本 | 可检出明确冲突 | W12-03 | 让长篇状态更稳 | 主观判断误事实化 | P1 |

### 14.4 本周出口标准
- 连续事实回流运行；
- 写事实无旁路；
- 新状态可被下一章消费。

---

## 15. 两周推进清单：真实 30 章生产闭环

### 15.1 两周阶段目标
把项目从“工程链路已具备”推进到“真实 30 章连续生产 + 人工真值闭环 + W12 真实接入”的可验收阶段。

### 15.2 第一周：完成真实 30 章连续生产主链路

#### 必须做
1. **冻结 30 章实验配置**
   - 锁定模型、Prompt、预算、约束与运行参数
   - 生成最终版 `run manifest`
   - 中途不得更改实验配置

2. **启动真实 serial run**
   - 从第 1 章连续跑到第 10 章
   - 不是 synthetic replay，不是 fixture smoke，不是预览式短跑
   - 必须走真实正文生产链路

3. **每章强制落盘**
   - 原始正文
   - 修订正文
   - 事实候选
   - 质量快照
   - 成本、重试、失败原因
   - run state 与 provenance

4. **完成第 10 章复盘**
   - 记录问题类型
   - 记录修复动作
   - 记录后续策略是否需要调整
   - 复盘必须形成明确结论，不得仅保留日志

#### 可延后
- W8 / W9 的人工真值补齐
- W10 的盲评完整结论
- W12 的真实 serial run 深度统计

#### 第一周验收产物
- 1–10 章真实正文
- 第 10 章复盘报告
- 每章 provenance 完整
- 第一版 30 章运行汇总表

### 15.3 第二周：完成 11–30 章生产并输出 30 章产品基线

#### 必须做
1. **继续生产 11–20 章**
   - 保持第一周冻结配置
   - 继续记录每章产物
   - 禁止为“通关”临时改规则

2. **完成第 20 章复盘**
   - 检查事实噪声
   - 检查角色声音漂移
   - 检查长度与中文语域稳定性
   - 检查修订成本是否上升

3. **完成 21–30 章**
   - 形成完整 30 章正文集
   - 保留完整 run archive
   - 每章都能追溯到输入、输出和修订过程

4. **完成第 30 章复盘**
   - 总结全流程问题
   - 明确哪些策略有效、哪些无效
   - 记录是否需要下一轮实验

5. **输出 30 章产品基线报告**
   - 正文质量
   - 中文语域
   - 长度分布
   - 角色声音
   - AI 味风险
   - 事实冲突率
   - 修订率
   - 成本与耗时
   - 人工介入量

#### 可延后
- 自动修订策略大改
- 进一步扩展新 schema
- 新一轮长弧规划

#### 第二周验收产物
- 11–30 章真实正文
- 第 20 / 30 章复盘报告
- 完整 30 章 run archive
- 30 章产品基线报告 v1

### 15.4 同步推进的辅助工作

#### A. W8 / W9 人工真值补齐
- 清掉 7 条 skeleton seed
- 完成正式双评
- 完成分歧仲裁
- 重新生成校准 summary

#### B. W10 盲评结论
- 对比原稿 / 自动修订 / 人工修订
- 计算自动修订净收益
- 明确保留、降级或限制启用策略

#### C. W12 接入真实 serial run
- 不再只依赖 synthetic fixture
- 统计候选有效率、冲突率、审批成本
- 确认下一章是否消费更新后的状态

### 15.5 最推荐的执行顺序
1. 冻结 30 章配置
2. 跑 1–10 章并完成第 10 章复盘
3. 跑 11–20 章并完成第 20 章复盘
4. 跑 21–30 章并完成第 30 章复盘
5. 输出 30 章产品基线报告
6. 补 W8 / W9 真值
7. 做 W10 盲评结论
8. 验证 W12 真实接入

### 15.6 最终判断标准
当且仅当以下四项都成立，才能说项目已从工程阶段进入产品验证阶段：
- 30 章真实连续生产完成
- 10 / 20 / 30 章复盘完成
- 人工真值闭环基本补齐
- W12 在真实 serial run 中有可量化收益

#### 完成度快照（2026-07-22 更新）
| 判据 | 状态 | 证据 |
|---|---|---|
| 30 章真实连续生产完成 | ✅ 完成 | RUN-00025（33/33 done，0 skip），`genesis-pilot/analysis/v10-baseline-report.md`（索引见 `docs/RUN-00025-EVIDENCE-INDEX.md`） |
| 10 / 20 / 30 章复盘完成 | ✅ 完成 | serial-checkpoints `genesis-pilot/registry/derived/serial-checkpoints/cp-0{10,20,30}.json`（核心字段折自 run-scoped manifest，hash 校验一致）+ 三段复盘报告 `genesis-pilot/analysis/checkpoint-reviews-run00025.md` |
| 人工真值闭环基本补齐 | 🟡 进行中（管道已验证） | 金样集 43 样本有正文+真值 + 7 空 seed；W9 校准 summary 已生成。**W8-03→W9 管道已用 AI 替身端到端跑通**（`metadata/w8-w9-ai-flow-report.md`）：AI 双评+仲裁→喂真实校准代码→43 样本每维相关性/MAE/定级。硬红线守住：只写 `ai_scores.json`/`w9-ai-calibration-results.json`，未碰 human_scores.json 与真实校准产物。诚实结论：AI 双评同源 temp=0，自我一致 95%、相关性虚高，**不是真值**——判据仍需真人评分。副产物：ai_voice_risk 即便虚高环境仍最弱(corr 0.53)，真人校准应重点关注。**官方 backfill→定级闭环也已跑通**（`metadata/w9-backfill-closure-report.md`，沙箱）：把 AI consensus 落到 human_scores 位置，官方 CLI `reviewer-calibration backfill-all`+`summary --write` 自动产出 12 维定级——证明「真值一旦落盘，定级零手工自动产出」。live 43 真值文件与真实校准产物一个未碰 |
| W12 在真实 serial run 中有可量化收益 | ✅ 成立 | 接入完成（`--w12-extract`，第 8 个 built≠live 修复）：serial loop 每章 stage-only（ADR-009）、never-gates（ADR-003）。**全 33 章双模式汇总已跑**（`genesis-pilot/analysis/w12-run00025-report.md`）：确定性 223 候选全 consistent（**有效率 0%**，实体在场探测器，下限基线）；**LLM(deepseek) 649 候选 = 391 new + 178 additive + 80 conflicting，有效率 87.7%、冲突率 12.3%**，提取出确定性拿不到的语义事实（能力/伤情/记忆/物品）。判据要的"可量化收益"成立。**候选审批 mint 链路也已 AI 模拟走通**（`genesis-pilot/analysis/w12-mint-walkthrough-report.md`，沙箱）：全 33 章 stage→审批(actor=AI-SIM)→mint(validate-then-write)→recompute，22 receipts、66 事实落地、沙箱 facts 41→95、conflicting 79 全部按 ADR-009 拒绝。核心发现：87.7% 语义有效率 vs **实际仅 ~10% 可 mint**——三层 frozen schema 契约挡住（conflicting 不 mint / new 仅 CHR-ITM 按名建 / additive 仅 physical_facts.* 直过，abilities 是实体引用数组）。下一工程缺口=散文值→schema 结构值规范化层 |

**checkpoint 能力（本轮落地）**：`runtime/serialize/checkpoints.py` — writer（loop.py，共享 `build_checkpoint` builder）→ reader（`load_serial_checkpoints`）→ 引用端（`run_aggregate.checkpoints`）三段贯通；`backfill_checkpoints` 从不可变 run-manifest 折历史运行的 checkpoint（可用 snapshot 归档在 draft_hash 匹配时补 m7/quality）。只读投影（ADR-008），不铸事实、不 gate。

**W12 serial 接入（本轮落地）**：`--w12-extract` 让 `run_serial` 每章生产后调 `run_w12_fact_reflow`（此前 CLI-only）。传内存 draft，不重读可变的 `drafts/`（规避 task_id-keyed 产物被后续 run 覆盖的陷阱）。结果记在 `ChapterRun.w12`。stage-only、never-gates、never-mints；W12 异常降级为 `w12.error` 不中断 serial。

**结论**：四项判据中 **3 项已成立**——30 章生产、10/20/30 复盘、W12 可量化收益（LLM 全 33 章有效率 87.7%）。第 4 项人工真值闭环仍需**真人评分**才能成立（AI 双评同源虚高，不是真值）。

**两条剩余真人动作现已全部用 AI 替身端到端走通（沙箱，不碰 live）**：
- W12 候选审批 mint：全 33 章 stage→审批→mint→recompute 跑通，66 事实落地，暴露"87.7% 有效率 vs ~10% 可 mint"的散文→schema 规范化缺口。
- W8/W9 校准定级：官方 `reviewer-calibration backfill-all`+`summary` 从真值自动产出 12 维定级。

**结果：两条流程的工程管道都已验证闭合，真人动作一旦执行即可零额外工程产出结果。剩余的纯属真人判断（真实审批、真实评分），非工程缺口。**

### 15.7 仓库实况审计与推进结论（2026-07-23）

> 本节以当前工作树中的代码、测试和可定位产物重新核验。判定规则是：代码存在不等于产品完成；测试通过不等于真人结论；文档提到但仓库内无法定位的运行产物，不作为本次审计的独立完成证据。

#### 15.7.1 审计摘要

- **工程健康度：高。** 在 `AI-Novel-Runtime` 执行全量测试，结果为 `916 passed in 71.80s`。
- **计划工程项完成度：约 85%。** W1–W7 的基础设施、30 章 orchestration、checkpoint、provenance、质量快照与 W12 serial 接线均有代码和测试支撑；W8–W12 的结构性链路大部分也已落地。
- **产品验收完成度：约 65%。** 当前主要缺口不是继续新增模块，而是真人评审、真人授权、真实运行归档入库，以及自动修订净收益结论。
- **最终规划状态：尚未完成。** 12 周计划不能按“全部 Done”关闭，当前应进入“验收收口冲刺”，而不是开启下一轮架构扩建。

#### 15.7.2 分周真实完成度

| 周次 | 审计状态 | 估算完成度 | 已确认事实 | 未满足的退出条件 |
|---|---|---:|---|---|
| W1 事实恢复 | ✅ 完成 | 100% | 根 `README.md` 已成为事实入口；`ROADMAP.md` 与前向规划职责已区分；能力矩阵、baseline freeze/compare 与测试存在 | 无阻塞项；后续仅需随事实同步维护 |
| W2 中文与长度 | ✅ 工程完成 | 95% | 长度、语域、质量快照、短跑验证均已接入并有测试 | 缺少本轮审计可直接定位的真人正文前后对比结论，不影响工程出口但影响产品证据强度 |
| W3 角色声音与 AI 味 | 🟡 部分完成 | 70% | Speech Profile、匿名台词识别、A/B cleaning 结构与测试存在 | 尚无“至少 3 个角色匿名识别率明显高于随机”及真人 A/B 净收益报告 |
| W4 Winner 与黄金三章 | 🟡 工程完成、人工未闭环 | 75% | winner drift、golden-three pack/record、baseline report 及测试存在 | 至少 2 名真人评审与仲裁证据未在本次审计中确认 |
| W5–W7 30 章基线 | 🟡 能力完成、证据未纳入版本控制 | 85% | workflow manifest、scheduler start/resume/step、run aggregate、checkpoint、serial 生产与相关测试均存在；`RUN-00025` 及四份报告经二次核实**真实存在**于 `genesis-pilot/`（manifest 33/33 done、0 skip、`final_state_hash sha256:147514d4`、token total 236117；`v10-baseline-snapshot/` 1514 文件、`run-00025-snapshot/` 1235 文件） | 上述产物整目录被 `.gitignore:7` 忽略，git 未跟踪任一文件（`git ls-files genesis-pilot`=0），fresh clone 拿不到；真缺口不是“丢失/重跑”，而是**未纳入版本控制**——需决定归档策略（白名单 `git add -f` 精选 manifest+四报告+checkpoint，或建已跟踪 `evidence/` 目录），而非重新运行 |
| W8 金样集 | 🟡 样本框架完成 | 80% | `QGS-00001`–`QGS-00050` 目录存在；43 条正文样本具备评分结构，7 条仍是 skeleton seed | 必须补齐 7 条 skeleton；确认评分者身份、独立性、授权和仲裁记录后，才能把 W8-03 判为真人真值完成 |
| W9 Reviewer 校准 | 🟡 代码缺陷已修、待真人真值 | 75% | 校准代码、policy、summary 和测试存在；当前 summary 为 43 样本、12 维分级 | **CLOSE-06 已修自我指涉根因**：`reviewer_calibration_cli.build_real_reviewer_output` 原第 21 行把 `human_scores.editor_a` 照抄为 reviewer 侧（对比侧又是 `mean(editor_a,editor_b)`），r≈0.99–1.0 是数学必然。已改为读独立的 `ai_scores.consensus_scores`（LLM 判官,不派生自人类分,附 `reviewer_source` 溯源字段）；重跑 backfill+summary 后相关性回落到真实量级 r=0.53–0.92、MAE=0.31–0.74，`ai_voice_risk`(0.528) 已按 <0.6 门槛从 trusted 剔除；4 个 decision 维实测均 ≥0.847，静态分级与实测自洽。新增防回归测试 `test_reviewer_side_is_independent_of_human_ground_truth`。**剩余待办**：`ai_scores` 仍是 AI 判官非真人真值（同源 temp=0 双评仍有虚高风险），真人双评(CLOSE-05)落盘后需再跑一次；在真人真值到位前，`decision` 维度不得升级为无人值守硬门控 |
| W10 自动修订盲评 | 🔴 未完成 | 45% | 30 个候选、自动修订产物、blind package、批次与结果 schema 已齐备 | `w10-blind-review-comparison-results.json` 仍为 `awaiting_human_review`，10 个批次 winner/confidence 均为空；且目前只有原稿/自动修订双臂，未达到原计划三臂真人盲评 |
| W11 Long-Arc | 🟢 绑定作品 + 真实消费已验证 | 90% | 100 章分段计划、mandate/objective、重复检查结构存在。**CLOSE-12** 把规划投影器 `long_arc/plan.py::build_long_arc_plan` 绑定到《蚀梦纪元》（fold 作者 5 层 power tiers + 3 级 conflict ladder，ADR-008 纯投影，重生成 `LONGARC-001.json` 已归档，4 测试）。**CLOSE-13 已用真实 DeepSeek 3 章 A/B 验证消费（¥0.18）**：生成 live 路径是 `arc/projection.py::project_long_arc`（读同一 outline），long-arc 臂 prompt 3/3 章携带作者坐标（战力段位/冲突层级/卷目标，~10.8K vs 基线 ~5.2K）、draft hash 全变、state_hash 不变（坐标不覆盖事实）、纯正文零元词汇泄漏（无机械化回归）。报告 `genesis-pilot/analysis/close13-longarc-consumption.md`（已归档） | built=live/输出改变/无回归三判据成立。主题定向强度在 n=3 下不确定（逐词计数噪声，同 beat-enrichment 方法学教训），留待更大样本；但"是否被消费"答案明确=是。**剩余**：可选的大样本主题定向量化 |
| W12 事实回流 | 🟢 工程接通 + 规范化层 + 真实 live 验证 | 90% | `run_serial(..., w12_extract=True)` 已接入候选回流（stage-only、never-mint、降级不阻断）。**CLOSE-14** 补散文→schema 规范化层（`normalize.py`，纯形状：标量→数组/标量叶→字符串/能力名→活实体 id，绝不发明事实，11 测试）。**CLOSE-15 已用真实 deepseek-v4-pro 对 TASK-00001 跑通 W12 抽取**，报告 `genesis-pilot/analysis/close15-w12-live-report.md`（已归档）：修复 2 个真实运行暴露的 built≠live 缺陷——① draft envelope 未 unwrap（抽取器读顶层 body 拿空→0 候选）② w12 命令 `--model-id` 默认空串致 DeepSeek 400 被静默吞→0 候选；修复后抽出 10 候选，**真实可 mint 率 2/10（20%）**，量级吻合关闭 W12 时的 ~10% 判断。5 项回归测试（含 unwrap 固化）。**CLOSE-15 跟进：加抽取提示 schema 字段约束**（`declared_fields_by_type` + prompt 注入合法字段 + `_coerce_field` 近似名纠正/无匹配丢弃）：真实重跑 8 候选字段名全 schema 合法（发明字段这层清零，制约前占 6/8 阻断），并修复第 3 个 built≠live 陷阱（长 prompt 超 60s 默认 timeout→静默吞异常→伪 0 候选；w12 默认 timeout 提到 120 + `last_error` 告警）。4 项 extract-constraint 测试 | 诚实结论：字段约束已见效（清除发明字段），但可 mint 率天花板下沉到**引用型字段需先 mint 目标实体**（abilities/possessions 要 MAG/ITM-##### 引用，散文值不过）——这是「散文语义→结构化实体图」建模，非提示/形状层可解。**剩余**：引用型字段的先建实体建模（下一杠杆）+ 人工审批真实 mint（可选）|

#### 15.7.3 关键证据与风险校正

1. **测试事实已确认**：全量 `916` 项测试通过，可证明当前工程回归基线健康。
2. **30 章产物真实存在，缺的是版本控制（原“可能丢失”结论已撤销）**：二次核实确认 `RUN-00025` 及 `analysis/v10-baseline-report.md`、`checkpoint-reviews-run00025.md`、`w12-run00025-report.md`、`w12-mint-walkthrough-report.md` **真实充实地存在**于 `genesis-pilot/`（manifest 33/33、`final_state_hash sha256:147514d4`、快照 1514+1235 文件）。首轮审计判为“无法定位/可能丢失”是**搜索路径错误**——只搜了仓库根 `analysis/`，未进 `genesis-pilot/`。真问题：`genesis-pilot/` 整目录被 `.gitignore:7` 忽略、git 零跟踪，fresh clone 复核不到。因此不应重跑或撤销完成标记，而应决定归档策略把关键证据纳入版本控制。
3. **W9 高相关性是自我指涉，不是可信度**：`w9-calibration-results.json` 的 reviewer 侧分数经核实 96% 是 `human_mean` 的取整（80.8% = floor、15% = round），r≈1.0 / MAE≈0 是拿“人类分取整”对比“人类分自己”的数学必然，无校准意义。真正独立的 AI 判官 vs 人类为 r=0.53–0.92。重做时 reviewer 侧必须独立于人类分；并区分真人独立评分、AI 替身评分（`w9-ai-calibration-results.json`，脚本已自带“NOT a real calibration”免责）、沙箱回填三类来源，物理隔离。
4. **W10 是当前最明确的硬阻塞**：结果文件明确为 `awaiting_human_review`，因此自动修订是否值得保留尚无证据，不能据现有 advisory 或自动分数下结论。
5. **W11 仍是通用草案而非作品级百章生产计划**：当前结构证明能力存在，但不足以证明具体作品的百章目标、高潮和地图切换已冻结。
6. **W12 的下一工程缺口应收敛为规范化层**：候选提取与审批/Mint 边界已建立，下一步不应再加平行 schema，而应将散文事实规范化为现有 frozen schema 可接受的结构值，并保持人类审批权。

### 15.8 下一步任务规划：验收收口冲刺

#### P0-A：修复证据链（预计 0.5–1 天）

| Task ID | 任务 | 交付物 | 验收标准 |
|---|---|---|---|
| CLOSE-01 | 决定并执行 `genesis-pilot/` 证据的版本控制策略（产物已确认存在，勿重跑）：白名单 `git add -f` 精选 `RUN-00025.json` manifest + 四份报告 + checkpoint，或建已跟踪的 `evidence/` 目录放精选产物 | 纳入版本控制的 run archive 索引 | fresh clone 可定位 33 章 manifest、hash 可复核、四份报告文档链接有效；不整目录提交 2700+ 快照文件 |
| CLOSE-02 | 确认 `genesis-pilot/analysis/` 内第 10/20/30 章复盘与 30 章基线报告随 CLOSE-01 一并纳入版本控制 | 三份 checkpoint 结论 + baseline report（已跟踪） | 报告中的章数、hash、成本、失败数与 manifest 一致（当前已一致：33/33、`sha256:147514d4`、token 236117） |
| CLOSE-03 | 修正文档中所有“RUN-00025 无法定位/可能丢失”的错误陈述（本轮已改），并核对是否有其它引用仍指向仓库根 `analysis/` 的过期路径 | 修正后的文档引用 | 全文无“丢失/需重跑”表述；产物真实存在的结论保留，完成标记基于已核实证据而非历史文字 |

#### P0-B：完成人工真值闭环（预计 2–4 个评审人日）

| Task ID | 任务 | 交付物 | 验收标准 |
|---|---|---|---|
| CLOSE-04 | 补齐 7 条 skeleton seed 的正文、来源与授权 | 完整 50 条金样集 | 50/50 样本均非空且 metadata、labels、notes 完整 |
| CLOSE-05 | 两名真人独立完成 50 条评分，并对分歧仲裁 | 可追溯的 human scores 与仲裁记录 | 评分者身份/时间/独立性可审计；不得混入 AI 替身结果 |
| CLOSE-06 | 重做 W9 calibration，修复**自我指涉根因**：现 `w9-calibration-results.json` 的 reviewer 侧 96% 是 `human_mean` 取整（80.8% floor + 15% round），必须换成**独立于人类分**的 reviewer 输出（真实自动 reviewer 或真 AI 判官），再与真人真值比对 | 新 summary + calibration audit | reviewer 侧可证明不派生自 human_mean；AI 与真人结果物理隔离；每维样本量、相关性、MAE、区间与定级可解释；预期 r 回落到有意义量级（对照独立 AI-vs-human 为 0.53–0.92） |
| CLOSE-07 | 将 W9 policy 应用于真实 selection consumer | policy 验证报告 | 仅经确认的 decision 信号可参与选择；diagnostic 不得单独 gate；unreliable 禁用 |

#### P0-C：完成 W10 真人盲评（预计 2–3 个评审人日）

| Task ID | 任务 | 交付物 | 验收标准 |
|---|---|---|---|
| CLOSE-08 ✅ | 先执行 B01 小批次，检查盲法、疲劳与理由码 | B01 3 样本试评记录（`packet-QGS-00001~00003`）| ✅ 试评完成，无来源泄漏，理由码可用。**遗留发现**：小批次未识别出后续暴露的强位置偏好（见 CLOSE-09） |
| CLOSE-09 ✅ | 完成剩余批次真人盲评 | 22/22 packet 填满 winner/confidence/reason/notes（评审者 ayit）| ✅ 全部 22 个可运行候选完成真人盲评；每个 packet 含 winner、confidence、reviewer、timestamp。⚠️ **单评审者 + 91%（20/22）偏 B 位**——存在强位置偏好，结果不作为质量标准（详见决策记录） |
| CLOSE-10 ✅ | 汇总自动修订净胜率与回归率 | `genesis-pilot/analysis/w10-decision-record.md` + `w10-blind-review-comparison-results.json`（status=aggregated）| ✅ 揭盲聚合：original 14 / auto 8 / tie 0，净胜率 **−27%**，回归率 0。脚本确定性给 `disable`；**人类治理判断收敛为 restrict**（负净胜率被位置偏差污染，不足以硬禁用，但明确否定"默认全开"）；自动修订保持 opt-in（`--hygiene`），不进默认链路 |
| CLOSE-11 ✅（记录偏差）| 按接受的计划偏差，正式修订计划为"两臂验证" | 两臂结果（原稿 vs 自动修订）| ✅ 人工修订臂不存在、不伪造；正式为两臂验证并记录偏差。**方针**：本次单评测不作为标准、不复评；质量真值迭代交给后续真实写作的生产信号（ReaderSignal） |

#### P1-D：把 W11/W12 从通用能力推进到作品级验证（预计 2–4 天，不含模型运行时间）

| Task ID | 任务 | 交付物 | 验收标准 |
|---|---|---|---|
| CLOSE-12 ✅ | 将 Long-Arc 草案绑定到目标作品和冻结 run | 作品级 `LONGARC-001.json`（《蚀梦纪元》）| ✅ 已落地：投影器 fold 作者 power_system(5层)+conflict_ladder(3级)进 band goals 与 power 轴（ADR-008 纯投影），每 10 章有作品级具体目标 + 换地图条件 + provenance 溯源；`git add -f` 归档；4 项绑定测试 + 向后兼容回退 |
| CLOSE-13 ✅ | 做 3 章受控验证，确认 mandate/objective 真正改变生产结果 | `genesis-pilot/analysis/close13-longarc-consumption.md`（真实 DeepSeek A/B，¥0.18）| ✅ 三判据成立：long-arc 臂 prompt 3/3 章带作者坐标（~10.8K vs 5.2K）、draft hash 全变、state_hash 不变、纯正文零元词汇泄漏（无回归）。主题定向强度 n=3 下不确定，不宣称 |
| CLOSE-14 ✅ | 实现散文事实到 frozen schema 的规范化层 | `runtime/candidates/normalize.py` + 11 测试 | ✅ 已落地：schema 驱动纯形状转换，插 extract→reconcile 之间，不绕过 schema、不发明事实/不自动 mint 冲突、失败留原值不阻断 serial；证真实收益（`abilities='梦蚀之眼'` 被 schema 拒 → `['MAG-00001']` 过 gate） |
| CLOSE-15 ✅ | 在真实 serial run 做 W12 对照验证 | `genesis-pilot/analysis/close15-w12-live-report.md`（真实 deepseek-v4-pro）| ✅ 首个真实 CLI live run：TASK-00001 抽 10 候选（new5/additive4/conflicting1），真实可 mint 率 2/10（20%，吻合 ~10% 判断）；修复 2 个 built≠live（envelope 未 unwrap、model-id 空串→400 静默吞）。诚实结论：剩余瓶颈是语义（发明字段/能力需先建实体）非形状。下一章消费率/多章对照留待可选扩展 |

### 15.9 推荐执行顺序与完成门槛

严格按以下顺序收口，避免继续堆结构：

1. `CLOSE-01`–`CLOSE-03`：先让 30 章产品基线重新可审计；
2. `CLOSE-04`–`CLOSE-07`：完成真正的人类质量锚点；
3. `CLOSE-08`–`CLOSE-11`：用盲评决定自动修订去留；
4. `CLOSE-12`–`CLOSE-13`：冻结作品级百章规划并验证真实消费；
5. `CLOSE-14`–`CLOSE-15`：收口 W12 规范化与真实收益；
6. 更新 `README.md`、`ROADMAP.md`、能力矩阵与本计划，形成最终冻结版本。

项目规划只有同时满足以下条件才可标记完成（勾选状态截至 2026-07-24）：

- ✅ 30 章 run archive 在稳定路径可重放、可校验，10/20/30 章复盘与基线报告引用有效（CLOSE-01~03，RUN-00025 已 `git add -f` 归档）；
- ⚠️ 部分：50 条样本中 **43 真人评 + 7 skeleton seed**，AI 替身结果与真人结果严格隔离（`ai_scores.json` 显式标注 NOT human ground truth）；**未达标点**：差 7 条非空真人样本，且 43 份 `human_scores.json` 无可审计的评审者身份/时间戳（CLOSE-04/05）；
- ✅ 部分：W9 独立 reviewer 定级 r 落在预期区间（未塌成 human_mean 派生，CLOSE-06）；policy 约束真实 selection consumer 待确认（CLOSE-07）；
- ✅ W10 真人盲评完成，自动修订策略已有结论：脚本 `disable` → 人类治理收敛为 **restrict**（22/22，净胜率 −27%，带位置偏差 caveat，不作为质量标准；CLOSE-08~11）；
- ✅ 作品级 100 章 Long-Arc 已冻结并在真实生成路径被消费（CLOSE-12~13）；
- ⚠️ 部分：W12 完成"提取→人工审批→Mint→Recompute"，但 **"下一章消费"环未闭合**（CLOSE-15 显式将其留作可选扩展）；
- ⏳ 待办：README/ROADMAP/能力矩阵最终冻结版本（15.9 步骤 6）；全量测试保持通过、限制与人工授权边界已记录。

在这些门槛满足前，禁止把项目状态描述为“12 周规划全部完成”；准确表述应为：**工程主链路基本完成，产品与人工验收正在收口——W10 盲评已收口（带位置偏差 caveat，不作质量标准）；剩余缺口为金样真人样本补齐+可审计化（门槛②）、W12 下一章消费闭环（门槛⑥）、文档冻结（步骤 6）。质量真值的最终校准依赖后续真实写作的生产信号。**

## 16. 当前下一周期：Corpus Intelligence MVP

> 决策日期：2026-07-25。真人评审任务暂缓，保留原证据缺口但不作为本周期工程阻塞。当前只推进一个主问题：让优秀小说语料以版本化抽象证据进入现有 Genesis，并在受控实验中证明净收益。详细任务以 `docs/ANOVEL_EXECUTION_TASKS.md` 第 10 节为准。

### 16.1 周次安排

| 周次 | 唯一主目标 | 关键任务 | 必须交付 | 出口标准 |
|---|---|---|---|---|
| CI-W1 ✅ | 冻结语料边界 | 盘点 `runtime/reference/`；定义 `CorpusSnapshot`；实现 canonical hash、loader/writer；建 10 本 fixture | snapshot schema、runtime consumer、fixture、测试 | ✅ 2026-07-26 完成：10 本合成玄幻 fixture、7 本 canonical 可分析；授权/清洗/重复筛选和 missing/tamper inventory findings 已验证；14 项聚焦测试通过；Corpus 不写 Facts |
| CI-W2 ✅ | 产出作品叙事画像 | 定义 `BookNarrativeProfile`；实现 deterministic / LLM / consensus analyzer；两遍分析和字段仲裁 | profile schema、analyzers、validation、分析产物 | ✅ 已落地（commit 9728188）：`runtime/narrative_mining/`（book_profile + llm_analyzer + consensus + validation）；`book-narrative-profile` / `book-profile-analysis-pass` schema；3 测试（含无密钥可运行的 consensus/validation）通过 |
| CI-W3 ✅ | 让 Genesis 真实消费 | 定义任务化 Query 和 `GenesisEvidencePack`；实现 retrieval；接入 Outline Bootstrap 和 provenance | evidence schema、retrieval consumer、Genesis 接线、原创性报告 | ✅ 已落地（commit 9728188）：`runtime/retrieval/`（genesis + originality）；`narrative-evidence-pack` schema（无连续原文/专名）；接入 outline/agents+workflow；3 测试（evidence pack / outline 消费改变候选 / 原创性 guard）通过 |
| CI-W4 ⏳阻塞 | 受控实验与裁决 | 冻结 A/B/C 协议；每组 5 个概念；匿名多模型 Pairwise；A/B 位置交换；Judge 偏差统计 | run archive、bias report、decision record | C 对 A 胜率 >60%，位置交换一致率 ≥75%，可持续性不降、原创风险不升 |
| ↳ CI-W4 阻塞原因 | | **胜率判据依赖 LLM judge，即 GAP-C 未校准真值**：judge 给自产文打分高于《盘龙》Δ−32.4、四方模型对比中检测器无法分辨质量优劣（人读才见差异）。现在做 CI-W4 会得到用不可信判官算出的胜率（Gate 或显示"C 胜 A 65%"却对真实订阅无预测力）。应在第一本书上架、拿到真实首订/追读数据校准判官后再做，否则是伪裁决。 | | | |
| CI-W5 ✅ | W12 下一章消费 | 建消费证据；Mint/Recompute 状态进入 N+1 Objective 和 Prompt；真实有/无事实 A/B | consumption audit、live report、回归测试 | ✅ 真实双臂 6/6 成立（commit 8dc9003 + 08f9aa7）：CI-M2-04 用 novel-lingse 副本 new mint ITM-00001「三棱晶刺」→recompute→v11 双臂第6章。6 判据全成立：prompt/manifest/draft hash 变化、历史 fact hash 不变（41/41）、正文写入"三棱晶刺"、可重放。真实运行逼出并修掉 3 个 built≠live（serial 未接消费证据 / approved_state 只注入 ID+hash 无语义 / v10 模板无槽）。报告归档 `novel-lingse/analysis/ci-m2-04-ab-report.json` |

### 16.1.1 当前进度（2026-07-28 对齐代码）

CI-M1/M2 五个周次中 **4 个已完成**（W1 语料快照 / W2 叙事画像 / W3 Genesis 消费 / W5 下一章消费），全套测试通过。**唯一未做的是 CI-W4 受控实验**，且它被 **GAP-C 阻塞**：其核心出口"C 对 A Pairwise 胜率 >60%"只能由 LLM judge 裁决，而 judge 判别力已被反复证伪（给自产文打分高于《盘龙》Δ−32.4；四方模型对比中检测器无法分辨质量优劣）。

**下一步不推荐硬做 CI-W4**（会产出用不可信判官算的伪胜率）。真正该做的是**产品动作**：用四方对比选定的模型（kimi-k3 / gpt-5.5，正文对比数据已备齐）重跑第一本书 → 上架 → 拿真实首订/追读数据。这份真实真值才能校准判官、让 CI-W4 的裁决有意义、让"从好书学配方"闭环可验证。见 `docs/N100-FIRST-BOOK-LAUNCH-PLAN.md`。

### 16.2 CI-W1 立即执行顺序（已完成，保留为历史执行记录）

1. 读取并画出现有 Reference 生产者—消费者图；
2. 明确复用 `segment/measure/profile/abstract/gap`，禁止平行重建；
3. 只定义首个有消费者的 `corpus-snapshot` 契约；
4. 实现 `runtime/corpus/` 最小 loader、writer、query 和 canonical hash；
5. 建立一个目标题材的 10 本去标识化 fixture corpus；
6. 增加 Schema、hash、重复、授权边界和 non-fact-writer 测试；
7. 输出 CI-W1 运行报告，确认是否进入 CI-W2。

### 16.3 每周统一验收

每周必须回答：

1. 新 Artifact 的真实消费者是谁；
2. 本周能力是否改变了实际生产决策；
3. 输入、模型、Prompt、Corpus Snapshot 和输出能否回放；
4. 是否向 Writer 泄露连续原文、真实专名或单本作品完整结构；
5. 是否产生无消费者 Schema、重复模块或旁路事实写入；
6. 本周成本、失败率和恢复结果是什么；
7. 是否达到周出口，还是应该停止扩容并修正。

### 16.4 阶段 Gate

CI-M1 只有在以下条件同时成立后才能扩到约 140 本或进入数万本扩容：

- Snapshot manifest 可复核；
- Profile 有证据、置信度和版本；
- Genesis 记录 snapshot/query/retrieval provenance；
- 无 Evidence 路径保持兼容；
- C 组对 A 组 Pairwise 胜率高于 60%；
- 位置交换一致率不低于 75%；
- 100 章可持续性不下降；
- 原创性风险不增加；
- 所有新增模块有消费者。

任何一项未满足，都不得以“已有数万本储备”为理由提前全量处理。

### 16.5 本周期明确不做

- 不补真人评审作为工程 Gate；
- 不直接全量导入数万本；
- 不让 Writer 检索原始小说正文；
- 不新增 Reviewer / Persona / Agent 数量；
- 不恢复默认整章自动修订；
- 不做强化学习和复杂 Corpus UI；
- 不重建 Scheduler、Replay、Manifest、Long-Arc 或 Mint；
- 不覆盖当前工作区已有的 `runtime/cli.py` 与 `chapter-draft.v11.prompt.yaml` 修改。

---

## 17. 每周例行制度

### 17.1 周一：计划与事实检查
- 上周产物是否完成；
- 测试是否全绿；
- 当前能力矩阵是否更新；
- 本周只选一个主问题；
- 明确本周不做什么。

### 17.2 周中：真实模型短跑
任何 Prompt、Model、Pipeline 改动，都至少跑：
- 正常样本；
- 边界样本；
- 失败恢复样本。

### 17.3 周五：质量评审
输出：
- 本周正文或规划对比；
- 成本变化；
- AI Pairwise、位置偏差与分歧结果；
- 新发现；
- 是否达到退出标准；
- 是否需要回滚。

### 17.4 每月：产品冻结
每月形成一个可重放版本：
- Pipeline；
- Prompt；
- Model Config；
- Reviewer；
- Book Project；
- Golden Set；
- Run Report。

---

## 18. 任务状态字段建议

每个周任务在看板中至少包含以下字段：

| 字段 | 说明 |
|---|---|
| Task ID | 唯一编号 |
| Goal | 要解决的真实问题 |
| Quality Impact | 对小说质量的影响 |
| Commercial Impact | 对商业价值的影响 |
| Evidence Level Before | 实施前证据等级 |
| Target Evidence Level | 目标证据等级 |
| Dependency | 前置任务 |
| Artifact | 交付产物 |
| Acceptance | 验收标准 |
| Risk | 主要风险 |
| Status | Pending / Doing / Blocked / Done |
| Proof | 测试、运行报告或人工评估链接 |

---

## 19. 最终结论

这份周推进计划的目的，不是把项目做得更像“有很多任务”，而是让 AI 每周都能回答三个问题：

1. 这周到底在解决什么真实问题；
2. 这周做出的改变是否真的改善了正文或系统；
3. 这周是否应该继续、转向还是回滚。

如果某周不能回答这三个问题，那么那一周就不算完成。
