# 合约、上下文、模型、工作流与质量修复

## 1. Planning 与 Contract

SeriesVision → ArcPlan → ChapterPlan → Chapter/SceneContract。计划表达意图；Contract 绑定项目/分支、Canon parent、GenrePack、编译器/政策版本与要求。必需转移、禁止转移、保护事实、知识边界使用与 Delta 一致的类型语义。

硬要求和创作偏好分开。计划与 Canon 冲突时重规划；不能修改 Canon 来使计划通过。P10 前人工 SeriesVision/Story Fixture 是合法输入，不强制依赖尚未实现的 GenesisSpec 编译器。

## 2. Context Compiler

先选必需事实/约束/知识边界，再分配可选摘要与检索内容。检索结果保留来源、作用域和版本；top-k 不代替必需集合。

预算不足时先移除可选项；必需集合仍超预算则返回可诊断错误或显式换用兼容配置，不静默截断。记录 inclusion/exclusion 原因、token 计数方法、Canonical parent、Contract/Pack hash 与角色。

所有项目数据查询、缓存、embedding 索引、blob、日志展示都有作用域。参考分析仅提供经批准的抽象信号；原始长篇参考不进入 Writer。不得把模型上下文中的其他任务内容当项目事实。

## 3. Model Gateway

分离 logical_request、attempt、provider request ID 和候选响应。记录模型实际标识、参数、模板版本、输入 hash、开始/结束、结果状态、usage 与费用状态。

结果状态至少区分成功、已知失败和 UNKNOWN。超时不证明未执行；无法确认远端结果时不能承诺绝不重复收费。先查询/恢复可识别结果；决定重试时记录可能重复的费用与预算影响。

缓存按语义输入、作用域和模型政策隔离。Provider fallback 是可见的政策动作，需重新记录实际模型和适用校验，不能以同一个 model label 掩盖切换。

首个真实调用前配置总费用/尝试次数/运行时长上限；无凭证时 live gate 为 BLOCKED，不能转 Mock 然后报真实测试通过。

## 4. 单章闭环

```text
load frozen parent / plan
→ compile contract
→ compile context
→ generate candidate
→ extract NarrativeDelta
→ execute required checks
→ diagnose / bounded patch / re-extract / revalidate
→ issue protected CommitPermit
→ CanonCommitService
→ durable receipt / accepted chapter
```

Draft saved、validated、accepted、published 是不同状态。首期只完成到 accepted/export；不自动发表。ERROR/UNKNOWN/缺检查/未经授权 SKIP 不能发 Permit。

每个阶段声明输入、输出、重试类别、稳定请求身份、幂等范围、失败状态和恢复方法。进程在模型返回后、抽取后、Permit 后、提交后任一时点退出，恢复都不能造成第二次权威提交或伪成功。

## 5. Q0–Q3 最小生产门禁

| 层 | 负责检查 | 示例拒绝条件 |
|---|---|---|
| Q0 | 结构、完整性、输入绑定、必要 Artifact | 错 hash、缺检查、作用域缺失 |
| Q1 | Canon 一致性、前值、生命周期与知识范围 | 死者无解释复活、跨书关系、角色凭空知情 |
| Q2 | 已冻结的 Genre/扩展世界规则 | 实际发生的非法超自然能力、扩展未注册 |
| Q3 | 合约要求/禁止转移与实际变化 | 必需转移遗漏、保护事实被改写 |

每次运行有独立 CheckExecution 记录，包含 check ID/version、状态、输入 hash、结果 refs。没有 Findings 不表示执行过检查。抽取合法也不等于正文没有遗漏违规，需正文与 Delta 覆盖校验及已知遗漏样本。

语义检查可以使用模型辅助，但来源、置信和未知结果必须显式。没有验证依据的模型 PASS 不能满足硬门禁要求；确定的硬失败不能被平均分抵消。

Q4 文学质量、Q5 角色质量、Q6 商业代理指标按阶段补充，不必首期实现。Q7 原创在 Reference 模式启用时必须有适用政策；Q8 是人工/读者/市场校准层。未实现层标 NOT_IMPLEMENTED，不填空数组冒充 PASS。

## 6. Permit

签发者核验 required check 集合、状态、候选/ChangeSet/parent/Contract/Pack/政策绑定、issuer 权限和有效期。CanonCommitService 在提交时再次验证，防止旧证据配新候选、未经授权对象或 HEAD 竞争。

P2 的测试 Permit 只存在于隔离测试配置/凭证，生产拒绝该来源。P7 集成正式签发。绕过 Gate 的开关不得进入生产配置。

## 7. Repair 与停止条件

RepairPlan 必须指出错误证据、修改范围、保护区域、预期影响及重验集合。补丁改变正文即产生新候选 hash，重新抽取受影响内容并验证完整提交前提。

区分表达缺陷、事实缺陷、不可满足合约和规划失败。后两者升级为合约/计划修订提议，不无限修改句子。达到预算/轮次/时间上限、重复无改进或引入新硬失败时停止自动尝试并保留诊断。

有限重写可作为明确政策动作；不得删除失败尝试以改善成功率。对未改区域及已有正确事实执行回归，验证修复没有制造新污染。
