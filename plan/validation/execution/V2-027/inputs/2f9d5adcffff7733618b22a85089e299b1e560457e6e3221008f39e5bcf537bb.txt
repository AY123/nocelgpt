# ADR-010 — Model Gateway 的请求身份、费用责任与恢复

2026-11-16；V2-019，后续V2-027复用。用户指定首个Provider为OpenAI；本次授权包含实现与无付费验证，不包含未明确数值的真实调用。当前实现/验证同一操作者，Agent仅技术交叉检查。

## 决定

1. Gateway消费V2-018的角色安全model_bytes；不发送整个ContextArtifact或AUDIT_ONLY输入，不写Canon、不签Permit。逻辑请求绑定project/branch、run、logical_id、Context/model_hash、指令/模板、响应Schema及冻结的允许模型政策。attempt ID独立且每次发送唯一；重启/retry/fallback不创建新预算。已成功逻辑请求持久重放原响应，不自动重新生成，也不建立跨logical的创意生成缓存。
2. 首个适配器使用OpenAI Responses HTTPS协议，显式结构化输出，不启用tools、streaming、conversation、background、隐式fallback或SDK自动重试。Provider协议只在adapter内。原响应按普通严格JSON解析（拒绝重复key/非有限数），保留实际字节与raw hash，再校验响应Schema和业务成功状态。模型拒绝、incomplete、HTTP错误与无响应分开；HTTP200不自动等于有效输出。
3. 费用账本使用stdlib SQLite、短事务BEGIN IMMEDIATE与唯一约束，存放由操作者指定的专用文件；这不是Canon或小说事实库，不改变Canon Schema。发送前原子检查并持久reserve及attempt；发送前再记录DISPATCHED；网络不占事务。预算首次建立时冻结project/branch/run、USD整数微单位总额、尝试数、持久截止时间、inflight/UNKNOWN上限；相同run不能靠新实例或fallback重置。
4. 同一attempt费用责任互斥转换：reserved/inflight → settled estimate 或 UNKNOWN liability，不重复叠加同一责任。准入计入已估结费用+全部inflight预留+待核UNKNOWN责任。价格快照/来源/有效期及模型能力必须明确；采用未折扣输入价、输出上限与显式误差余量计算最坏预留。V018字节估算不当Provider tokens。若不能得到经核对的输入上界/窗口能力则阻断live；可用完整模型窗口作保守费用上界，但不能称实际输入usage或精确账单保证。
5. response_hash只来自收到的真实字节，无body则None，不生成空串hash。结果SUCCESS/FAILED/UNKNOWN与费用状态独立：HTTP/Schema失败仍可能计费，缺usage不记零。标准usage按冻结计价估结，标ESTIMATED而非已核对账单；异常usage、价格/模型不符保持待核责任，停止自动重试。响应仅保存白名单元数据，不存Authorization；凭据仅执行时注入，repr/日志/结果不包含key。
6. 重复logical_id换语义输入拒绝；同attempt并发/重复不能再次发送。restart遇DISPATCHED未完成则UNKNOWN并保留预留；只有可证明未发送的PREPARED attempt可取消释放。成功响应与估结同事务保存后再返回。人工/Provider证据reconcile幂等、带来源，不得无依据把UNKNOWN当0；后续观察到迟到结果仍校验原attempt身份。UNKNOWN后retry须显式接受可能重复费用，并受原总额/次数/截止时间约束。fallback仅在预先冻结的允许政策内显式新attempt，保留实际model，不更换标签伪装。
7. 响应JSON Schema由同一jsonschema实现验证，现有锁定4.26.0由dev移至runtime，不增新包/升级版本；锁文件按实际依赖图核对。类型/序列化继续用ANOVELOS-CJSON-1，凭据不进入数据类型。模型/价格/能力配置在model-policy.yaml，未配置live默认阻断，不从历史credential材料推断服务可用。
8. 本地真实HTTP server用于验证wire协议、断线、usage/预留/重放/恢复与隔离；它不是外部OpenAI证据。首个外部调用必须具备数值预算/次数/时长、有效模型能力与凭据，并保留实际响应/请求ID/usage/模型指纹。缺任一项仅阻断LIVE_CALL与最终V2-019/P5验收，不阻本地实现，不用mock PASS替代真实Provider。

## 原验收与本轮边界

AT-V2-019-01～05及最低断言保留。测试包括先reserve再发送、无预算零请求、UNKNOWN无body无假hash、已知错误与待核费用分离、同logical冲突/成功重放、并发不能双花、重启/fallback不重置额度、重复结算不重复计费，以及角色安全正文/Schema输入绑定。六门mandatory不改，远程CI仅关键交付运行；不因本任务启用付费CI或自动小说生成。

官方协议依据：OpenAI [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[模型目录](https://developers.openai.com/api/docs/models)、[计价](https://developers.openai.com/api/docs/pricing)。已实际获取页面；账户模型权限、最终模型选择、精确能力及live数值授权在调用前另核对，不从网页推断账户访问或文学质量。

## 2026-11-17 补充：仅限首次能力探针的授权派发

用户授权实现 V2-019 固定探针入口、安全凭据与本地正反例，仍未授予实际数值预算或真实调用权限。当前单人 Owner 模式提供可复查的本地授权边界，不冒称独立审批或对抗同写权限者的隔离。原任意 LIVE_CALL 子命令与 CERTIFY 的通用拒绝保留；只新增固定类型的 V2-019 首次能力探针派发，直接探针 CLI 也必须消费相同授权校验。

首次能力调查区分三类事实：公开资料支持的协议/窗口/政策；尚未观测的账户访问与本次 count/generation/Schema 兼容性；经 Owner 单独批准的一次有界调查。账户的真实兼容性在该调查中仍为待测项，不预先标为 FACT，也不用于最终验收。仅此明确目的可在实际兼容性未知时取得证据；预算、授权、价格、计数费用依据、输入与安全运行条件未知仍阻断。未来普通章节调用、自动重试、fallback、认证及 V2-020 不消费该许可。

执行包通过可空 `probe_authorization` 绑定固定 Git grant 的 revision/ref/SHA256。正式 grant 必须包含 Owner 数值授权原话来源/hash、源码库存指纹、scope/review pins、请求/预算/政策原字节与内容 hash、project/branch/run/logical/attempt/model 身份、私有根与精确账本/结果/claim 路径、有效期及停止条件。CLI 不可选择另一 grant 或任意子命令。只有 task/action、原文来源、固定内容和现行输入一致，且活动包 `paid_calls_allowed=true`、数值预算不小于本次需求并不超过授权时，才可能派发。当前包继续 false/0、授权绑定为空。

窄入口固定为 `FIRST_CAPABILITY_PROBE`：WRITER 安全上下文、`gateway-protocol-probe-v1`、单一政策及闭合 `{text:string}` JSON Schema；真实模式仅当前 gpt-6-luna、直连标准 Responses、应用窗口不超过16384及输出不超过1024。最多1个attempt、并行1、UNKNOWN上限1，最多1次计数POST及合格后1次生成POST，单POST不超过30秒、总期限不超过120秒。禁止自动重试/fallback，任一失败、UNKNOWN、费用PENDING或成功均结束本次探针。LOOPBACK_FIXTURE 授权仅允许明确 test_mode 的本地回环HTTP，不读取真实凭据，不构成外部Provider证据。

当前账本预留公式未单列计数费用。此窄入口仅接受有固定来源证据、经明确核对的 `VERIFIED_ZERO_COST` 计数政策；未知或非零计数费用均拒绝，非零支持须另行设计真实预留/责任，不能借 margin 推断覆盖。本轮没有为真实账户声明计数免费，也没有创建真实数值 grant。

派发前在授权固定的私有目录原子独占创建0600 claim并fsync，早于任何凭据读取或网络，失败/中断也不删除。结果独占创建；账本、WAL、SHM、journal、claim及结果必须同一当前用户所有的0700规范目录，文件0600、无符号链接/硬链接别名，使用umask077。只从真实控制TTY隐藏输入凭据，不能关闭回显或无TTY就拒绝，不回退stdin或环境凭据。交互后重新核对源码、执行包、输入、pins和期限，直接消费已验证DTO。重复授权、换输出、已有attempt或UNKNOWN不能重发；恢复仅核对原账本。

本地验证必须同时覆盖合格精确授权的完整回环HTTP正例和缺失/过期/错hash/越权/超额/任意命令/CERTIFY/重复派发/无TTY/非私有目录等负例。实现角色与验证角色可由同一操作者承担并如实标注。即使本地检查通过，真实调用、账户能力和最终六门CI/工程验收仍分别未完成。
