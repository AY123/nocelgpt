# ADR-002 — Character 类型与封闭序列化边界

日期：2026-10-18。关联任务：V2-006。责任：domain-maintainer。决定由同一 Codex 实施操作者依据用户“开始”V2-006的授权作出；生效状态读取机器决策登记及正式 ADR_DECISION，不声称独立人员审核。本文不是实现、CI或产品验收证据。

## 问题与依据

现行 Entity 是不可变的项目作用域身份，JSON Schema 已封闭。直接用 allOf 继承该封闭 Schema 会拒绝 Character 的合法派生字段；只继承 Entity 的解析/导出又会丢字段。现行规范要求身份、类型与生命周期正确，误信、事实和计划分离。AR-03还要求 identity 字段正例；CA-06本阶段只验证领域/JSON往返，JSONB/API映射仍属后续责任。

依据：`03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md`、`05_PRODUCTION_CONTEXT_QUALITY_REPAIR.md`、AT-V2-006的四条断言，以及已交付的 Entity。历史领域设计只作参考，未整体采用其字段；FND-003不引入角色Agent或图数据库，EXT-005的后续合约/正文消费者不在本任务实现。

## 决定

1. **本内存领域边界复用标准库 frozen/slots dataclass 和显式解析。** 不新增依赖。现行技术方向中的 Pydantic v2 在未来外部API/持久化边界消费时再评估；本阶段以共享正反例校验代码与 JSON Schema 一致，不形成两套各自演进的契约。
2. **Character 继承 Entity 的身份行为，显式实现完整解析/导出。** 版本 `1.0`，类型固定 `CHARACTER`，生命周期限定 ACTIVE / INACTIVE / DEAD / UNKNOWN；受伤、失业、DESTROYED、DISBANDED不属于人物生命周期。保留封闭的 CharacterIdentity（species / gender / origin，缺省为明确的UNKNOWN）和 description。不增加公司财务或修炼专属字段。
3. **Schema在叶子封闭。** `character.schema.json`显式声明身份及派生字段，各层拒绝未知字段。复用可组合的 `$defs`，不以 allOf 引用已封闭的 Entity；对账测试比较身份字段约束。完整非默认数据、EntityRegistry改名后的派生字段均须保留。Entity自身的封闭边界保持不变。
4. **Relationship是独立值对象。** 稳定ID、固定 `RELATIONSHIP` 类型、party_a / party_b EntityId、非空关系类型集合及 trust（有限数，范围[-1,1]）；所有身份必须属于同项目。不从人名推断或合并身份，不引入关系事件/reducer。
5. **事实、来源、认知与计划分别建模。** knowledge.py 提供不可变 Proposition、WorldFact、Observation、Belief、Goal、Intent；查询和修改只作用于本内存投影，不是Canon提交。命题值为严格JSON标量（不以null兼任未知），布尔不得与数值混淆，数值拒绝NaN/Infinity。Goal/Intent有独立类型、owner及目标/判断依据/计划选择/预期代价，不能被事实接口接受。
6. **世界事实不自动成为人物知识。** KnowledgeState按人物显式记录取得。KNOWN必须消费已登记的Observation：同项目、匹配fact_id、人物确在witnesses中、有非空证据引用。不存在/错人物/错命题/跨项目来源均拒绝；传闻以BELIEVED或SUSPECTED的Belief保留，不得用自报 `reliable=true` 晋级。角色可以基于自己的误信作出计划，不强迫其使用作者知道的真相。
7. **知识边界验证的范围是显式结构与关联，不是假装验证自然语言。** Observation是应用方提供的结构化观察证据；P1不认证它在真实正文中的语义真伪。正文Q1检查与合约消费者留给V2-023/V2-017，事件发生与转移留给V2-007/008。读者已知、未来计划、传闻不能借事实/知识解析入口变成已发生事实或确定知识。
8. **完整投影可做严格JSON往返。** knowledge.schema.json封闭定义角色、事实、观察、信念、取得记录、目标与意图。恢复依次验证引用和知识边界；不能仅因JSON里写KNOWN就接受。外部不能通过导出数据或嵌套容器修改原状态。未知版本、额外字段、重复ID和跨书引用均拒绝，失败不留下部分修改。

## 取舍与验收

不引入Pydantic、数据库、Provider、常驻角色Agent或通用实体框架；不改现有Entity的类型与查找语义。代价是需要维护显式解析和Schema，但共享样本同时验证两者，所有声明字段有非默认往返测试。若将来引入边界框架，应在真实消费者任务里迁移并保留本次回归。

四组验收：人物派生字段/关系与认知非默认往返；错误类型/生命周期/引用拒绝；东库真实钥匙与西库误信并存、有效观察后才知情；救人目标和去西库取钥匙的计划不改变客观位置。所有测试先本地运行，不冒称远程CI、数据库往返或小说生产完成。
