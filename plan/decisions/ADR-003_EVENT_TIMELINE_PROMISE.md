# ADR-003 — Event 发生、双时间顺序与 Promise 兑现

日期：2026-10-18。关联任务：V2-007。责任：domain-maintainer。决定由同一 Codex 实施操作者依据用户“先准备 ADR-003，再实现事件、时间线与 Promise”的授权作出。生效状态读取机器决策登记及 ADR_DECISION；本文不证明实现、远程 CI 或产品验收完成。

## 问题与依据

现行契约要求稳定事件身份、发生状态、同章多事件和插叙顺序，以及 Promise 的兑现窗口和生命周期。V2-005 已提供项目作用域 EntityId；V2-006 已将世界事实、观察、误信、目标和 Intent 分开。不能因出现一个事件名、时间或计划就推断事情已发生，也不能把世界时间与读者获知的顺序合并。

依据是 `03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md`、`04_GENRE_AND_STORY_FIXTURES.md` 与 AT-V2-007-01/02/03。历史领域设计仅作参考；不整套引入其事件模板、因果求解器和八态 Promise 工作流。

## 决定

1. **沿用不可变值对象与显式封闭 JSON 边界。** 使用标准库 frozen/slots dataclass，无新依赖。Event 与 Promise 均有稳定 EntityId、固定 kind 和 schema_version=1.0，未知版本、字段、类型和跨项目引用拒绝。所有声明字段完整往返，导出对象不能修改原值。Schema 用本地 `$defs`，Promise Schema 复用同样的事件定义，并以对账测试防止漂移。
2. **事件身份、类型和发生状态分开。** Event 的 event_type 是分类，不是去重身份。Occurrence 限定 OCCURRED / NOT_OCCURRED / UNKNOWN，必须显式提供，不从 description、时间、参与人或 evidence_ref 推导。每个事件声明均有非空来源引用。已有 Intent 仍是计划，不能被事件入口消费；不另建通用 EventPlan 框架。
3. **每个事件有主要叙述锚点与独立故事时刻。** NarrativePosition=(chapter,order)，二者为严格正整数，支持同章多事件。它是读者接触该事件声明的主要锚点，不枚举重复提及。StoryTime 是无隐含单位的逻辑整数时钟，可为负值：UNKNOWN 无界；EXACT 两界相等；RANGE earliest<latest。范围表示“可能发生于该区间的某个时刻”，不是事件持续时间。已发生但时刻未知与是否发生未知是不同状态。
4. **只报告证据支持的时序。** TemporalRelation 为 BEFORE / AFTER / SAME_TIME / UNKNOWN。两确切时刻相等才报告 SAME_TIME；重叠的可能时刻范围不证明同时。非 OCCURRED 的声明不形成发生关系。Timeline 按 EntityId 登记事件，重复 ID、重复主要叙述锚点、错项目均拒绝且不留下部分修改。narration_order 包含全部声明；story_order 只排序 OCCURRED，并且仅在这些事件可确定严格全序时返回。未知、重叠或同时造成不唯一顺序时明确拒绝，不用 ID 或录入顺序伪造先后。
5. **Promise 是文本向读者作出的承诺，不是人物 Goal。** 内容、opened_at、来源及关联实体明确记录。PromiseWindow 用 NarrativePosition 的 inclusive 起止位置；已知窗口 start<=end 且不能早于承诺建立。未知窗口显式 UNKNOWN，不用 null 暗示无限期限。查询返回 EARLY / IN_WINDOW / LATE / UNKNOWN。插叙事件的世界时刻可以早于开篇，但其读者锚点仍决定兑现位置。
6. **生命周期仅保留 OPEN / PAID / BROKEN / ABANDONED。** 初建只能 OPEN。pay_off / break_promise 必须消费同项目 Timeline 中已登记且 OCCURRED 的事件，叙述位置不能早于 opened_at；abandon 必须有明确说明引用。三种终态不可再转移。转换返回新的不可变投影，调用方采用返回值；本阶段不声称实现全局单次提交或 Canon 状态机。晚兑现可 PAID 且报告 LATE；时间流逝不自动改变状态，也不自行判定文学兑现质量。
7. **终态恢复需要同样的有效依据。** JSON 保存完整 resolution_event 快照及独立 resolution_evidence_ref。PAID/BROKEN 的 from_dict 必须给出 Timeline，核对完整事件内容与登记值相等后重放转换；只匹配同 ID 不够。OPEN 无 resolution；ABANDONED 有说明但无事件。缺上下文、伪造发生状态、同 ID 换内容、错项目或回溯兑现均拒绝。
8. **本任务只验证结构、引用和时序，不认证自然语言真伪。** evidence_ref 是显式应用方引用，并非凭其存在就证明正文确实发生或兑现。事件与 Promise 操作不会创建 WorldFact、传播人物知识或执行 Intent。正文语义、因果链、读者/市场验证留给真实消费者任务。

## 取舍与验收

不增加数据库、Provider、Agent、Canon 写路径、NarrativeDelta/reducer、通用状态引擎或时序约束求解器。两界比较、同项目和引用一致性由领域解析器执行；标准 JSON Schema 负责封闭结构和局部类型，不假称其可完成所有跨字段/外部引用验证。Python 严格整数拒绝 bool/float，JSON Schema 的数学整数语义可能接受 1.0；实际入口仍以领域解析校验。

三组原验收断言保持不变：同章事件/插叙双顺序；兑现窗口和生命周期；稳定身份、来源及未知不等于发生。测试还需覆盖未知时刻、范围重叠、跨项目/伪造终态、完整非默认 JSON 往返，以及事件/Promise 不改变人物认知的边界。本地通过不代替同 SHA 的真实 CI 或 V2-007 验收。
