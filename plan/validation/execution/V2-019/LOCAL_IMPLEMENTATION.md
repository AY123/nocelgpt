# V2-019 — OpenAI Model Gateway 本地实现

2026-11-16。任务 IN_PROGRESS；ADR-010 已接受。Provider 为用户选择的 OpenAI，尚无真实 Provider 成功/费用证据。实施、验证为同一操作者；Agent技术交叉检查不冒称独立人员验收。

已实现从 V2-018 角色安全 Context 到结构化 Provider 输出的工程接缝，为后续 Writer 提供调用能力；本任务不实现 Writer、自动小说工作流或文学质量判断。

## 已交付行为

- `GatewayRequest`冻结project/branch/run/logical、Context及model projection hash、指令/模板、响应Schema和允许模型政策。logical ID语义冲突拒绝；同一成功logical从SQLite重放原响应，不建立跨logical创意缓存。
- `ModelGateway.submit`先在持久SQLite中原子预留预算，再标记DISPATCHED，持有单次精确绑定的DispatchPermit才进入OpenAI adapter。无预算零HTTP；网络不占数据库事务。
- `BudgetLimit`首次冻结总微美元、attempt数、截止时间、并行/UNKNOWN上限。spent、inflight和UNKNOWN责任共同准入；retry/fallback不重置额度。UNKNOWN重试需要显式风险决定；不自动重试。异常费用或模型/服务价级冻结run。
- Responses使用`store=false`、非流式、无工具/会话/后台、`truncation=disabled`和`service_tier=default`。先调用input_tokens计数，实际输入数+最大输出不能超过应用窗口；V018字节预算不冒称Provider tokens。预算按应用窗口输入上界保守预留。
- 原HTTP body和raw hash、header request ID、实际model、usage、逻辑/attempt/model fingerprint分别留存。无收到body则没有response hash；count响应独立，不能冒充生成响应。refusal/incomplete/HTTP错误/不合Schema/UNKNOWN分开；Schema由runtime jsonschema真实校验，禁止外部引用检索。
- 成功与结算同事务持久化后返回；missing/malformed usage不记零。ESTIMATED是冻结价的保守费用估算，不是Provider核对账单。中断的DISPATCHED恢复为UNKNOWN；只有明确未发送的PREPARED可取消。reconcile带authority/evidence引用且幂等，不自动关闭费用。
- 真实HTTP本地fixture覆盖断线、滴流、重定向、refusal、usage缺失、反射凭据、晚响应及价格到期。客户端超时后远端仍可能执行，所以保留责任；超时worker不能保存迟到结果或继续下一POST。

SQLite仅记录模型请求与费用责任，不是第二Canon，也不改变正式小说持久化。现有Canon/Contract/Context代码未改。jsonschema4.26.0从已锁定dev移动至runtime；51个锁定包版本不变，无SDK/第三方新包。

## 当前模型政策与探针

`model-policy.yaml`是严格ModelPolicy DTO，以JSON写法保存为合法YAML，避免为生产引入PyYAML。当前`gpt-6-luna`仅为低成本协议探针提案，不代表长篇写作选型或文学质量结论。

官方模型目录给出1.05M context/128K output；本项目仅允许16384应用窗口、1024输出，发送前实际计数。标准输出0.50美元/百万token；输入用公开普通/缓存写入价格中的0.25美元/百万token上界而不是声称实际单价，另预留1000微美元误差。每attempt保守预留5608微美元（0.005608美元）。价格/能力来源及实际页面hash见`provider-source-verification.json`；政策2026-11-17T00:00Z到期，调用前需核对现行价格/账户能力。

`probe/prepare_request.py`生成的dist请求快照使用已采用都市测试书，经现有Contract/Context编译得到角色安全上下文。只读view是明确未入库的component fixture，不声称真实Canon根提交；原书Owner审定不等于本次Provider输出/阅读质量认可。探针要求100～200字场景JSON，仅验证网关，不进入Canon。

## 本地验证与下一步

完整本地结果及源文件hash由`LOCAL_RESULTS.json`保存。新增Gateway专项属于POSTGRES_ENV中集成套件子集；不能把它重复加到总测试数，不能称其全部为PostgreSQL或外部OpenAI。仅生产依赖隔离安装、真实Schema校验及默认CLI dry-run也已验证。

`run_gateway_probe.py`默认验证请求/预算/精确policy并输出dry-run，不读key、不创建ledger、不联网。显式`--execute-live`才会单次提交，凭据从OPENAI_API_KEY或`--prompt-key`隐藏输入；无任何SDK或自动fallback/retry。该flag不是Owner授权凭证，Agent还须通过本任务LIVE_CALL入口。结果0600独占创建，控制台只输出脱敏摘要；保持同一ledger/run，不把UNKNOWN当未发生后重发。

当前真实调用为0、远程CI为0；V019/P5/M4均未因本地PASS而关闭。待一个明确数值预算及API key入口/账户模型能力就绪后，做受控真实Provider探针；本地与真实Provider都收稳后才使用一次关键修订CI。建议预算上限0.05美元、最多3次显式生成attempt（每次最多1次计数请求），从实际建立run起180秒；这是提案，未获Owner批准，不得据此调用。

暂存扫描发现新运行快照的38个source_key和1个cache_key（均为Context派生SHA256）被generic-api-key识别；未提交、未扩例外，完整快照保存在dist/validation/v2019-probe-20261116/，仓库仅保留可复现准备脚本。业务DTO/缓存identity/扫描规则均未改变。
