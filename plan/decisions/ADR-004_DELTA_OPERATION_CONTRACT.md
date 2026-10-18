# ADR-004 — 有限事实变化提议与 reducer 前置条件

日期：2026-10-18。任务：V2-008，后续消费者 V2-010/017。责任：domain-maintainer。依据用户“先准备 ADR-004，再实现 NarrativeDelta 有限变化语言”的授权，由同一 Codex 操作者决定并做技术复核，不声称独立人员审核。本文不是实现、CI 或 P1 验收证据；生效状态由机器决策登记及 ADR_DECISION 记录。

## 问题与范围

现行 03 契约要求操作名/版本、作用域、路径、类型化载荷、前值、正文证据、reducer、重复含义和授权明确。AT-V2-008 三条断言保持原文，不借历史自由字典或“提取到什么就提交什么”绕过它们。V2-006 的 WorldFact/Proposition 已有稳定身份和非 null 标量，V2-007 已有叙述锚点和明确 occurrence。

本轮只实现**既有 WorldFact 的候选值变化**。不增加实体/事实创建、任意属性写入、事件/Promise/知识更新、Genre 插件注册或通用补丁框架。未来消费者确需其他操作时显式登记其版本、载荷、条件和测试，不让本轮格式自动接受它们。

## 决定

1. **只注册四个操作，版本均为1.0。** 四个 frozen 类型及闭集解析分派为 SET_FACT、MARK_UNKNOWN、RETRACT_FACT、NO_CHANGE。无默认操作、未知版本回退或运行时可插拔 reducer。目标是已登记 WorldFact.id，路径枚举仅 `proposition.value`。subject/predicate/身份不由该操作改写，任意JSON pointer、未登记目标或扩展操作拒绝。
2. **值类型取自 baseline 原始 seed，不接受操作自报类型。** ScalarKind 为 STRING / BOOLEAN / NUMBER；NUMBER 接受有限 int/float，bool 独立，沿用 Proposition 的数值比较语义。null、容器、非有限浮点和类型强转拒绝。UNKNOWN 或 RETRACTED 不会清除 seed 类型约束。
3. **事实状态与操作分别建模。** FactState 是 KNOWN(value) / UNKNOWN / RETRACTED。KNOWN 必须有非 null 标量；后两者的 JSON 不带 value，连 value=null 也拒绝。NO_CHANGE 是操作，不是事实状态。撤销保留目标、原始 seed 与来源的 tombstone，不删除记录；不把“已撤销”表述为该事件从未发生。
4. **只读基线与前值都明确。** FactSnapshot 保留 immutable seed_fact:WorldFact、严格非负整数 revision 和当前 FactState。初始快照从 seed 得到 KNOWN；类型始终从 seed 推导。FactBaseline 是 project/branch/parent_ref 和唯一目标快照 tuple；parent_ref 是调用方给定的基线引用，不冒充已认证 Canon HEAD 或 ADR-005 尚未决定的规范哈希。提议必须匹配外部 baseline 的 project/branch/parent_ref。每个 Precondition 同时匹配 fact revision、状态和值，bool 不与数字相等；即使值回到旧值，旧 revision 也不能通过。
5. **每个操作都携带正文与授权引用。** ProseEvidence 含同项目 source_id、NarrativePosition 和非空 evidence_ref；OperationMeta 含稳定 op ID、target_id、path、Precondition、ProseEvidence、authorization_ref。NarrativeDelta 显式绑定 source_id，所有操作的来源必须一致。preview 还必须接收调用方外部传入的 source_id 与 authorization_refs，逐条核对；缺失或未被允许的引用失败。这里仅验证结构和引用适用性，不认证正文语义、真实身份、审批或 Permit，不从自报 Owner/ALLOW 推断权限。
6. **reducer 是纯预演。** `preview_delta` 只读取冻结 baseline，返回不可变 PreviewResult（候选 baseline 与 before/after 变化记录），不调用 KnowledgeState 修改、Timeline、Promise、数据库、Canon 或文件写入。一个 Delta 不允许空操作、重复 op ID 或重复 target/path，避免同批覆盖及顺序隐含。所有操作以冻结父基线为前值；任一项失败不返回部分候选、不改变输入。跨场景候选 overlay 和真实提交由后续任务消费，不能把此预演当作 Canon 写路径。

| 操作 | 载荷与前提 | 纯 reducer 结果 | 重复含义 |
|---|---|---|---|
| SET_FACT | 必需 value，符合 seed 类型；前值匹配；非 RETRACTED | 当前状态变 KNOWN(value)，revision+1 | 同值应显式 NO_CHANGE；对结果重放因旧 revision 拒绝 |
| MARK_UNKNOWN | 禁止 value；前值匹配；当前 KNOWN | 当前状态变 UNKNOWN，revision+1；seed 不丢失 | 已 UNKNOWN 应 NO_CHANGE；旧 revision 拒绝 |
| RETRACT_FACT | 禁止 value；前值匹配；非 RETRACTED | 当前状态变 RETRACTED，revision+1；保留 tombstone | 重复撤销拒绝，应 NO_CHANGE |
| NO_CHANGE | 禁止 value；仍需全部前值、证据、作用域和引用检查 | 返回完全相同的快照、状态与 revision | 可重复预演，不产生额外变化 |

RETRACTED 本轮为终态，除 NO_CHANGE 外不能再改；恢复/更正需未来明确操作。UNKNOWN 可通过合格 SET_FACT 恢复已知。对同一个原 baseline 重复预演同一 Delta 可确定性得到相同结果；不提供跨进程幂等收据、全局单次提交或相同 ID 载荷哈希服务。V2-010 仍须在唯一 CanonCommitService 内认证授权、重验条件和原子提交，并实现提交幂等。

## 最小接口与 JSON 边界

- FactPath、ScalarKind、FactStatus；FactState.known/unknown/retracted 及严格 to_dict/from_dict。
- FactSnapshot(seed_fact, revision=0, *, state=None)：省略 state 仅为可信构造的初始 KNOWN 便利；JSON 必须显式包含 state。
- FactBaseline(project, branch, parent_ref, facts:tuple)，from_world_facts、get、to_dict/from_dict；固定 kind=FACT_BASELINE/schema_version=1.0。
- Precondition(revision,state)，from_snapshot；ProseEvidence(source_id,position,evidence_ref)；OperationMeta(id,target_id,path,expected,evidence,authorization_ref)。
- SetFact(meta,value)、MarkUnknown(meta)、RetractFact(meta)、NoChange(meta)，operation_from_dict；JSON 展平 op/version 与 meta 字段，只有 SET_FACT 包含 value。
- NarrativeDelta(id,branch,parent_ref,source_id,operations:tuple)，project 从 id 推导；JSON 固定 kind=NARRATIVE_DELTA/schema_version=1.0。
- preview_delta(baseline,delta,*,source_id,authorization_refs:frozenset[str])；PreviewResult(delta_id,candidate,changes:tuple[FactChange(operation_id,before,after)])。

复用标准库 frozen/slots dataclass 与既有 EntityId、WorldFact、NarrativePosition，不新增依赖。JSON Schema 在各叶子封闭，oneOf 区分四种操作/三种事实状态，并复用本地 `$defs`；输入缺字段、额外字段、错类型或版本拒绝，导出不暴露可变容器。Schema 只校验结构，目标登记、seed 类型、引用、前值及跨对象一致性仍须领域入口验证。Python 严格 revision 整数与 JSON Schema 数学整数的既有边界保持明确。

## 验收与后续责任

正例必须实际改变候选值，并证明原 baseline 与人物认知不变；UNKNOWN、RETRACTED、NO_CHANGE 三种结果可分别观察。反例包括缺 path/value/evidence、未注册操作/目标/路径、错类型与 bool/number、跨项目、旧 parent/revision/状态/值、错来源/授权引用、重复目标、终态修改和批次后项失败。完整非默认 JSON 往返与 Schema 对账都要通过。UNCERTAIN/CONTRADICTORY 不偷换为 UNKNOWN，也不在本轮凭自由字典获准写入。

本地测试通过不等于真实 CI、Canon 提交、P1 完成或章节产品闭环。V2-010/017 消费本语言时补齐相应真实权限、持久性、候选/正文绑定和消费者验收；不以该 ADR 提前放行后续任务。
