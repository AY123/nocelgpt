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
