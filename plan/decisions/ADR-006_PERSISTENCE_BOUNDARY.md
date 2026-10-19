# ADR-006 — 根提交、短事务、控制版本与保留闭包

日期：2026-10-19。责任：canon-maintainer。适用 V2-009～012，后续 Workflow 消费相同取消/提交语义。由用户本轮 V2-009 授权内作设计决定；同操作者技术复核，不冒称外部审核或运行结果。

## 本轮最小边界

V2-009实现版本化SQL迁移、带作用域Repository，以及为原验收“根提交并发唯一、测试初始化无旁路”必需的 **root-only CanonCommitService**。同一服务后续扩展章节提交。不得另建seed/fixture/direct-fact写入API。迁移只建空表；受信任部署操作者可配置空project/branch与InitializerGrant，不能写事实、事件、HEAD或收据。

初始输入仅人工/测试的基础Entity、Relationship、WorldFact种子及原始UTF-8说明正文；所有关系端点与事实subject必须已在该批基础Entity登记。事件/Promise/角色派生类型的持久适配不在本轮隐式接受。InitializerGrant是数据库内scope、actor、version、enabled的受控管理记录；调用方authenticated actor须由可信应用入口提供，不从LLM字段或自报ALLOW取得。当前没有网络身份认证，数据库部署身份有管理权；不得把它宣称为对抗性安全隔离。无grant、actor不符、撤销/过期版本均拒绝。初始化授权不等于章节Permit；V2-010仍负责真实Permit验证、候选/检查/政策绑定及非root提交，V2-011负责一般CAS/幂等，V2-012负责投影重建。

## 数据与事务

PostgreSQL17；使用现有锁定SQLAlchemy/psycopg，不新增ORM模型框架或迁移依赖。SQL迁移随包发布、校验checksum、事务内执行且并发串行；未知版本/已应用文件checksum变化拒绝。生产与测试使用同迁移及服务，测试数据库必须明确、隔离、可销毁。

最小表：project、branch及初始化grant/control版本、request control、immutable artifacts、commit、event、receipt、初始实体及关系/事实作用域索引。所有从属关系包含project与branch复合键；HEAD、parent、event、receipt、artifact引用均不能跨作用域。根的parent为SQL NULL、sequence=0；partial unique index确保每branch只有一个root，不依赖NULL相等语义。每branch序号唯一；parent/HEAD必须指向本branch真实commit。后续非root路径未实现时明确拒绝。

原始正文、初始输入、初始化授权快照保存为完整bytes；commit引用它们，event和receipt与commit一致。一个根提交的事实集合是初始领域状态，不能用历史自由JSON声称生成了其他对象。Repository不向Worker暴露连接/写方法；生产import边界仅允许commit_service依赖内部repository。直接DB管理员不在该Python边界威胁模型内，部署不得把特权DSN分配给Worker。

服务在进入短事务前完成输入类型/作用域验证和规范字节计算。事务锁定唯一branch行；在同事务内检查当前grant版本、request执行版本、取消状态、空HEAD，写artifact/commit/event/receipt并CAS推进HEAD；任一步错误全部回滚。不在事务内调用模型、远程API或长评估。无无条件upsert覆盖旧内容，不提供已接受正文的update/delete API。

## 取消与权限撤销次序

request ID稳定标识一次意图，request control记录actor、执行版本和当时grant版本；重启attempt不改变它。commit、cancel、revoke锁同一branch行，采用数据库事务提交的先后次序；不是墙钟或UI返回顺序。

- 取消先成功：control版本递增并取消，持旧版本的提交拒绝，无新commit。
- 撤销先成功：grant版本递增/disabled，旧执行请求拒绝。
- 提交先成功：收据已持久化；取消返回ALREADY_COMMITTED及原收据，不能声称回滚。
- 相同request的成功收据在空HEAD/控制状态检查前查找；同payload返回原结果，不因HEAD已推进或后来撤销丢失已发生事实；异payload冲突。身份/scope仍须匹配。V2-009只验证root情形，不据此关闭V2-011。
- 未确定事务结果时报告未知；调用方用原request恢复，不新建ID或盲目重提。

## 早期恢复与保留责任

当前阶段只用可丢弃测试库验证，不存唯一有价值小说内容。所有root依赖内容存同库，读取时校验hash和版本，能定位原始正文、初始输入、授权记录、event和receipt。root没有模型、章节Delta或Permit，不伪造这些不存在的证据；未来首次非root提交须保留Delta、Permit/检查、政策/合约/Pack/模型指纹及不可重建输入，同一作用域引用，不能以短期缓存TTL删除。

首次有价值持久运行前，项目操作者负责把数据库及外部不可重建内容备份到测试库之外，并在隔离目标验证恢复及hash闭包；缺少该证据不得开展有价值持久运行。V2-028负责首次认证前的隔离恢复，V2-058负责正式自动化与长期演练。V2-009的读回/同库事务测试不声称数据库丢失恢复或生产备份已验收。已接受提交依赖内容不提供通用删除接口。

## 原验收映射

AT-V2-009-01：空库迁移、重复迁移checksum/版本验证，真实服务读写；02：跨project和branch外键实际拒绝，合法引用通过；03：两个真实独立连接竞争root只一条成功，事实初始化只有同一个service；04：本ADR在接口前接受，真实root取消/提交两种次序、权限version拒绝及完整bytes读回覆盖已实现部分。原四条断言、任务依赖和未来任务状态不改。

SQL约束/行锁依据：[PostgreSQL17 Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)、[Explicit Locking](https://www.postgresql.org/docs/17/explicit-locking.html)。它们支持数据库机制，不替代本项目真实测试。
