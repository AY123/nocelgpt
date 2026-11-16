# V2-018 Context Compiler 本地交付

ADR009先于接口实现接受。新增context模块，从V2-017冻结合约纯编译角色化ContextArtifact，不改Canon/Contract/Genre规则、数据库Schema或依赖。四个源文件：封闭不可变模型、纯投影/必需选择、可丢弃的有界内存缓存和包入口。完整FrozenContextInputs标AUDIT_ONLY，供离线恢复；model_bytes仅包含当前角色安全内容，不携带整份作者输入或未来章节。

Writer保留当前章/场景意图、约束/前值、必要旧事实、真实前章完整末段/接续和Pack机制。可见保护/禁止事实以及已登记扩展的单位、币种、归属和资源/境界代价有有限依赖闭包；不从数量猜单位，不靠高相关检索挤出必要内容。隐秘must_not_know等以ID级约束保留；真正必要值若不可见则阻断。Character仅持其实际观察/误信/目标/意图，不能从作者真相或他人知识自动learn。矛盾观察明确CONTRADICTORY，与KNOWN/Belief分开；错误选择合法。

先scope/角色/时点授权，再装完整mandatory，最后按priority和稳定ID整项试装optional。计数覆盖实际model JSON+显式framing reserve；UTF8_BYTES_ESTIMATE_V1明确不是Provider真实tokens或任意模型的已证上界，V2-019仍须实际兼容性与费用预算。超预算返回诊断，无可执行Artifact；不截断必需项、不自动换模型。完整作者输入的原始/base64/重格式/包装JSON不能靠改visibility洗入Writer。显式来源规则不是语义DLP，不能声称检测了任意自由文本的秘密或幻觉。

每项纳入/排除保留source/hash、分类、原因和计数；排除/诊断不复制被拒绝资料原值。缓存key绑定完整输入、role/actor/scene、project/branch/parent/Contract/Pack/knowledge与预算政策；Reviewer或角色A缓存不转给Writer/B。缓存可删，完整冻结输入离线可恢复。Writer前章正文不自动成为Character知识；未实现正文语义提取/文学质量或身份认证。

完整本地1611 UNIT+244 ARCH+237 PG=2092项，0失败/error/skip；新53契约+6PG为子集。STATIC/五治理、安全54/54精确消费、51依赖0漏洞通过，命令/日志/哈希/JUnit见LOCAL_RESULTS。双实际Owner已采用故事输入沿用V2-017原决定，不请求新凭据或伪造人工审定。PG验证真实Canon读输入、接续和既有candidate协议兼容及拒绝后Canon不变。

技术交叉检查中接受了实体显示名/别名、结构化作者整包识别、矛盾知识及扩展依赖闭包修正。对‘hidden protected必须公开真值’建议作MODIFY：ID guard足够时保留guard，不提前公开秘密。原null整包子串误拒已修，合法annulled和JSON null摘要可用；早期测试夹具/字段/预算假设错误及失败XML原样保留，不冒称首轮全绿。所有旧测试、原五AT和六门保留，PG仅追加新测试文件。

当前只完成本地实现，尚待不可变candidate及同SHA远程六门验收，不据此关闭V2-018/P5。没有Provider/Writer/付费调用、生产Permit、自动小说生产、阅读质量或外部备份。下一任务V2-019仍独立实施。
