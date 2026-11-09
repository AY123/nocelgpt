# V2-011 — 连续章节的安全重试

开工：main@993ccacde90815cd5e6d31930f3ab62581c69958；V2-010已完成工程验收。消费已接受ADR-006及03现行契约，原AT-V2-011三条断言不变。同操作者实施和技术交叉检查，不声明外部独立审核。

目的：连续小说生产在网络断开、Worker重启或竞争保存时，不重复入章、不覆盖已接受正文，也不从错误前文续写。本文不证明生成小说或阅读质量。

## 复用决定

已有唯一CanonCommitService和Repository在同一branch行锁内：核对scope/actor/request purpose/parent；优先查询原收据并比较payload hash；只有未提交请求才核对当前权限/Permit/HEAD，原子写正文、Delta、事件、收据并CAS推进HEAD。稳定request ID与候选hash分离，不引入attempt ID。

审查决定：任务原产物`src/anovel/canon/idempotency.py`改为已有`src/anovel/canon/repository.py`，复用已有实现而不为文件名拆建第二套框架；任务身份、阶段、依赖、验收、安全门禁不变。只有真实测试揭示缺陷时才修改该实现。保留V2-009/010原测试。

## 本轮验证

- 同键同载荷：不同连接同时提交，原收据完全一致，正文/Delta/事件/收据/sequence无重复。
- 同键异载荷：成功后变更正文、候选版本、依赖或Delta均冲突；相同键两个有效候选并发也只能一个入章。
- 同parent不同request：提前签发两份合法Permit，两个独立PostgreSQL后端在branch锁前同步，恰好一个成功、另一个CanonConflict，无失败候选残留。采用有超时的barrier和数据库lock/statement timeout，不用顺序执行冒充并发。
- 响应丢失：唯一服务完成真实事务后，在调用边界丢弃结果并抛TimeoutError；释放原连接池，用新Engine/Service恢复原ticket和receipt，不重建请求ID；随后使用原receipt作为parent提交第二章，历史正文与事实基线均正确。
- 未提交事务失败后：回滚不得留下半章，原稳定请求可重试成功；重试不允许wrong actor/scope/parent绕过身份检查。

只用现有隔离TEST issuer和可销毁PostgreSQL；不改生产Permit边界、不调用模型、不接生产数据库、不实现V2-012。扩展原mandatory PostgreSQL命令包含V2-011，保留其全部原测试和6门硬失败。实现阶段不运行远程CI；完成本地测试及差异检查后才考虑一次关键验收。
