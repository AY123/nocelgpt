# Narrative、Canon 与 Artifact 契约

## 1. 领域最小集合

P1 实现稳定实体 ID、带作用域的别名、Character/Relationship/Knowledge、Event/Timeline/Promise 和 NarrativeDelta。名字不作为主键。项目内同名、角色改名、别名歧义必须有独立结果；不能随意合并实体。

世界事实、角色 Belief、角色 Knowledge、读者已揭示信息、作者计划分开。记录“甲说乙破产”不等于提交“乙已破产”；计划中的未来事件不属于当前事实。UNKNOWN、UNCERTAIN、CONTRADICTORY、NO_CHANGE、删除/撤销使用不同类型。

Character 基础/派生 Schema 的封闭策略须在 V2-006 决定并验证；Promise 时序、Event 身份与 occurrence 在 V2-007 决定。合法叶子字段必须通过，错误实体类型、错误生命周期和跨书引用必须失败。

## 2. 变化语言

NarrativeDelta/ChangeSet 的每种操作必须明确：操作名/版本、主体和作用域、字段路径或专用载荷、前值条件、目标值类型、正文证据位置、reducer、重复应用含义和授权。

未知操作、未注册扩展、类型不匹配、跨项目引用、过期前值不得提交。null 不同时代表未知/删除/无变化。实体一般以生命周期/tombstone 表达退出，禁止用通用 DELETE 绕过历史保留。

先定义所需有限操作；不用自由字典把验证责任推回 Prompt。Genre 扩展通过注册并验证的接口参与，Core 不包含 cultivation_level 或公司财务专属字段。

## 3. 唯一提交协议

1. 调用方提交 project/branch、parent、稳定逻辑幂等键、候选/ChangeSet 和 Permit 引用。
2. 检查主体授权、所有 Artifact 作用域、政策版本、输入绑定、必跑检查完整性及 Permit 有效性。
3. 在短数据库事务中复核状态，通过 CAS 更新 HEAD，写 Canon 事件/提交/收据及必要的可靠投影触发记录。
4. 同键同载荷返回原收据；同键不同载荷报冲突。相同键查询优先恢复已成功提交，不能因 HEAD 已推进就丢失成功收据。
5. 失败不产生半提交；非权威异步投影失败可重建，不声称权威事务已回滚。

模型调用、全文抽取和长时间评估不持有数据库事务。CAS、唯一约束和幂等不是相互替代关系。

逻辑请求 ID 在重试/重启间稳定，execution attempt ID 每次可不同，不能把变化的 attempt ID 纳入稳定幂等身份。键与载荷哈希分开存储，以便检测同键异载荷。

## 4. 根提交与章内候选状态

P2 用人工/测试初始输入经 CanonCommitService 创建唯一 root；空父提交的语义、并发唯一性、测试权限必须显式。完整自动开书到 P10 实现。

章内场景可读取 `frozen parent + validated candidate overlay`，不得把前一候选场景写入正式 Canon。后续场景失败后 overlay 随候选失效。最终章级正文、Delta、校验和 Commit 必须绑定同一候选版本。

## 5. 权限

| 操作 | 唯一负责者 | 模型/人类输入边界 |
|---|---|---|
| 推进 Canon HEAD | CanonCommitService | 人工也通过同一服务，不直接 SQL 改事实 |
| 更新生产状态 | Workflow 状态服务 | Worker 只返回结果，不自报已接受 |
| 签发 Permit | 受保护 PermitIssuer | 模型返回的 ALLOW 无签发权 |
| 提议计划/正文/修复 | 对应 Worker 或操作者 | 均为候选，提交前验证 |
| Retcon / Pack 升级 | 经授权的操作提议及服务 | 明确范围、影响、记录和重验证 |
| 发布作品 | 后期显式发布流程 | Writer/Reviewer 不持发布能力；首期不自动发布 |

文档权威层级和数据类别不是统一数值枚举。Context、Draft、Reference、CheckRecord 不因套用了某个 T 编码就获得写权限。

## 6. Artifact 身份、哈希与血缘

持久对象包含：artifact_id/type、schema_id/version、明确 scope、producer/version、input refs/hashes、content_hash、created_at 和适用政策。scope 显式区分 project/branch 与全局只读目录；全局 Pack 绑定到项目时仍记录版本/hash。

正文原始 UTF-8 字节 hash 与结构化规范化 hash 分开。结构化哈希的精确算法、数字/时间/Unicode/列表语义和测试向量在 P2 首次实现前通过 ADR 确定；不得使用“语义需要的精度”等不能唯一决定字节的规则。

内容身份不能代替来源授权。即使相同内容可复用，也必须独立核查 issuer、作用域、输入和政策是否适用。修复/合约/Pack/父提交改变会使相关派生证据失效。

## 7. 保留与重建

已接受章节保留源正文、ChangeSet、提交收据、历史 Permit/检查结果、绑定的合约/Pack/政策/模型指纹及可核验的必要输入，或保留可独立核验的等价证据包。执行许可过期/已使用与删除历史证据是两件事。

缓存可按保留策略删除；被接受提交依赖的不可重建证据不能按通用短期缓存期限删除。只有 hash 而无可恢复内容，不满足完整追溯要求。项目删除走独立授权与记录，不在本包中执行。

Snapshot 是投影。重建必须绑定事件/reducer/Schema 版本，并验证重建后与历史摘要一致。软件 Schema Migration 与故事 Retcon 分开记录；升级不能偷偷重写故事历史。
