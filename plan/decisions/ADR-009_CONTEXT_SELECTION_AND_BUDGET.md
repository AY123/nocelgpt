# ADR-009 — 角色化上下文、必需项与显式预算

2026-11-15；V2-018。用户已授权先准备本ADR再实现Context Compiler。由同一实施/验证操作者在任务范围内接受设计，Agent只做技术交叉检查，不称独立人员审核。

## 决定

1. 只消费已冻结、可恢复的V2-017 CompiledContract和显式候选来源。FrozenContextInputs完整保存Contract/request/sources及规范hash，标AUDIT_ONLY；它不是Writer输入。ContextArtifact另存角色安全的逐项投影、source/hash/必需性/纳入排除原因与绑定。model_bytes仅输出选中的模型内容，不嵌套完整Contract/fixture/Canon/未来章或审查记录。
2. WRITER消费当前章节或显式scene的创作意图、原四操作约束、Pack世界机制、必要旧事实和知识边界。计划明确标意图，不能当成已发生事实。读者延迟揭示事实不进入当前Writer；CHARACTER必须指定实际角色，只消费其有观察来源的知识、自己的Belief/目标/意图，不把作者真相/他人知识升级为该角色知识。角色本来已经获知的秘密允许早于读者揭示时点，不倒抹其知识。REVIEWER可读当前审查事实，仍无Canon写权。必需性不能覆盖可见性：必要事实不可见时返回VISIBILITY_REQUIRED_CONFLICT，不静默丢弃，不改源知识。此处角色标签是可信调用方输入，不是身份认证系统或文学语义证明。
3. 必需集合由正式合约推导：当前硬约束及前值、保护/禁止/知识/揭示引用、被采用意图及其已知/误信依据、相应实体/机制、本章起点与完整的冻结前章实际末段。外部来源不能将其降为optional或覆盖权威项。原文末段保持Unicode/BOM/换行，绑定原始全文hash、commit/candidate/span及UNKNOWN结束语义；第一章明确无前章。必需项不可被摘要/检索或相关度排序挤出。角色感知与写作约束分开，CHARACTER不接收作者未来转移计划。
4. 先校验scope/role/parent/版本/时间可用性，再安装完整必需集合，再按显式priority与稳定ID逐项试装optional。不压缩/截断必需项。预算包含最终model_bytes的完整JSON结构及显式framing_reserve。V2-018使用UTF8_BYTES_ESTIMATE_V1（每UTF8字节一个本地估算单位），明确ESTIMATE_NOT_PROVIDER_TOKENS；不是任意模型的精确token数或已证明上界，也不是实际usage/费用。V2-019负责实际Provider tokenizer/窗口兼容性及调用预算。本地预算超限返回诊断，没有可执行Artifact；不自动换模型或调用生成模型。
5. 候选ContextSource显式绑定project/branch/parent、来源版本、原UTF8内容hash、roles、available_from、相关fact_ids与可选actor。错scope/旧parent拒绝；未来/不适用角色可选项排除并留脱敏原因，若调用者要求其必需则阻断。原始参考正文不可直达Writer/角色；REFERENCE_SIGNAL仅允许可信上游批准的抽象信号。原AUTHOR_REVIEW_ONLY完整保留blob及其base64不得靠更改role标签洗成Writer候选；已识别的整包转发必须拒绝。自由文本分类和来源声明不能证明全文无泄漏，本轮不伪称实现语义DLP/embedding/外部检索服务。
6. 角色输出与审计恢复输入分离。排除清单/诊断不复制被排除资料原值或任意来源文本，只用稳定hash与原因。已有章节的真实正文是已接受的叙事证据，显式知识映射仍不得因正文可见而自动learn。本轮不做正文语义知识抽取；结束状态UNKNOWN继续保留。若已冻结末段含不适合某角色的全文，CHARACTER不获得该作者接续片段；Writer完整保留适用的实际末段，不能谎称语义上消除了原正文已有泄漏。
7. 仅提供可选的进程内ContextCache；key含完整FrozenContextInputs hash（含request角色/actor/scene/budget、scope/parent/Contract/Pack/knowledge/continuity及所有候选来源）和编译/计数政策。每次取出验证内容/绑定，Reviewer/Writer/A/B角色不能跨用途复用。缓存是可丢弃投影，不是Canon或唯一历史证据；完整FrozenContextInputs可在无缓存、无模型/网络情况下重编译。共享进程Owner恶意改代码/内存不在本权限声明内。
8. Python封闭不可变类型与ANOVELOS-CJSON-1序列化为唯一运行契约，不复制一份会漂移的手写Schema。新增仅context模块及测试/现有PG门禁追加；不改Canon/Contract/Genre规则、不加依赖/表/Writer/Gateway/Permit路径。本轮的无模型ContextArtifact是工程能力，不代表自动写作、阅读质量、生产放行或外部备份。

## 原验收保持

AT-V2-018-01～05及任务五条最低验收原文不变。验证低相关旧必需事实、预算恰好/溢出与序列化开销、scope/未来知识/误信、BOM/CRLF中文真实末段、完整Writer导出及Reviewer/A/B缓存隔离、冻结输入离线重放；两本已实际采用的开发fixture和真实PG读视图验证接缝。全部就绪后仅一次关键同SHA六门CI，不用资料PASS代替运行证据。
