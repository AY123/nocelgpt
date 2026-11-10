# V2-012 — 已提交故事状态的只读重建

开工main@76daba5，依赖V2-010 CLOSED；实际009/010/011原始验收保留。消费现行03/07/AI协议及已接受ADR-006，字节身份沿用ADR-005。原三条AT-V2-012不变，同操作者实施与技术交叉检查，不冒称独立人员审核。

## 实现决定

- 复用唯一CanonCommitService，增加明确只读`rebuild_snapshot(project, branch, commit_id)`；Repository只提供固定target真实祖先事件及完整历史证据读取。纯`projection.py`不接Engine、不import内部Repository、不写Canon或新事实库。
- 从固定target沿parent找root，校验scope、无循环/缺失、根sequence0及每步sequence连续、event/reducer/schema/encoding版本一致。只读取target祖先，后续HEAD变化不改变历史目标。
- root从已验证RootSeed初始化。章节按`FACT_DELTA-1`及schema1.0逐条重放现有有限Delta；授权引用来自已验证的历史Permit政策，不重新要求当前Permit未过期/未撤销。禁止用`load_baseline()`或保存快照作为reducer输入。
- 每章在重绑parent之前对比重新计算的canonical snapshot摘要与原STATE_SNAPSHOT字节身份；通过后把baseline重绑到该章commit，供下一章重放。输出最终baseline、原收据、每步版本及摘要，不保留额外整书正文副本。
- 当前只实现真实历史存在的ROOT-1/FACT_DELTA-1、schema1.0、ANOVELOS-CJSON-1。未知版本明确拒绝，不回退“最新”。不虚构v2以制造兼容测试；未来版本须保留v1语义和固定向量。
- 重建在提交完成后的独立只读入口。完整历史验证后，纯投影失败携带原target收据，明确已经提交；源历史缺失/损坏仍为完整性拒绝，不能伪造有效收据或返回部分成功。

STATE_SNAPSHOT目前纳入不可变commit evidence/envelope，不是可任意删除的缓存。本任务独立计算派生状态并验证历史摘要；原接受证据缺失/损坏须停止，不静默覆盖。对缓存/派生输出的重建不等于数据库丢失恢复，首次有价值数据的隔离备份前提保留。

## 验证与范围

真实可销毁PostgreSQL通过原唯一服务构造root和多章：SET→UNKNOWN→SET→RETRACTED→NO_CHANGE，覆盖每个历史点摘要、NO_CHANGE revision不变、两个项目同名branch隔离、当前权限撤销后的历史重建和新连接重建。投影故障后原正文/Delta/事件/收据/HEAD及同键重试保持正确，故障移除可再重建。缺事件/Delta、错误scope/parent/sequence、未知版本、损坏字节、摘要不符都拒绝。

保留原009/010/011所有测试；PG门禁仅追加012。六门继续mandatory，关键交付只运行一次最终CI。无模型、生产数据、事件总线、后台队列、新迁移或可变投影表。P2/M2只有009～012全部真实验收且原退出断言有完整证据后才可汇总；小说生成、真人阅读与生产备份不随工程汇总完成。
