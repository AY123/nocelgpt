# V2-012 工程验收

V2-012 CLOSED。代码`416c4510f8d505a1701a2b6e0c1f8181b90418ec`；GitHub [run42774996789](https://github.com/AY123/nocelgpt/actions/runs/42774996789)同SHA六门PASS：UNIT1124 + ARCH244 + PostgreSQL157 = **1525项，0失败/error/skip**。原服务1、V00959、V01057、V01114、V01226构成PG157；新增25项纯契约属于UNIT子集，不重复计数。只触发一个关键run，attempt1，无自动重试。

实际读取六个原始ZIP，核对GitHub digest、source/lock/driver身份、命令exit、全部声明产物hash与JUnit。原三断言全部成立：固定target从root+Delta逐章重放，原快照仅对比；纯投影故障保留已提交原收据、HEAD和全部字节；按真实ROOT-1/FACT_DELTA-1/schema1.0/CJSON1重建历史，不支持版本拒绝。

真实多章状态与revision显式验证，含UNKNOWN/RETRACTED/NO_CHANGE、旧目标、新连接、撤销后历史、双项目同名main交错隔离，以及缺事件/Delta、损坏字节、错误版本/编码、循环/跳过parent/序号缺口拒绝。EXISTING_METHODS_UNCHANGED核对原service/repository所有旧方法精确字节和AST保持，未增加第二写入口、迁移、缓存表、队列或Provider。

最初本地沙箱依赖审计未生成报告，正常本机环境重跑通过，旧失败保留；正式接受仅本次完整远端结果，不混本地或旧SHA。安全54项仍OPEN，批准范围和2027-01-06到期时间不变；54/54精确消费、0新增未匹配/未使用、51依赖0漏洞。实施和验证为同一操作者，不冒称独立人员审计。

## 边界

本轮重建的是已交付有限事实状态。STATE_SNAPSHOT属于不可变接受evidence，其缺损仍拒绝，不静默覆盖原历史。同库重建不是数据库丢失恢复、生产备份、全部Narrative对象持久化或小说生成/阅读质量认证。六项跨任务finding只作当前范围部分处置，后续消费者与恢复责任保留。

P2/M2仅根据009～012已接受证据、本run重新执行全部157项PG及原三条阶段退出断言汇总，详见P2汇总；不是产品或生产就绪。结项提交只改元数据和导航，CODE_MANIFEST证明业务/测试字节等于受测SHA，不另触发CI。
