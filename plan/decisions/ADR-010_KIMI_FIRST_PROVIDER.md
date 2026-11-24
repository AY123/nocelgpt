# ADR-010 补充决定 · 首个真实验收 Provider

2026-11-22。Owner 选择 Kimi 作为 V2-019 首个真实验收 Provider。本决定更新首个适配协议和探针对象。逻辑请求身份、账本、恢复、保留用量及真实验收要求沿用 [ADR-010](ADR-010_PROVIDER_BUDGET_AND_REQUEST_IDENTITY.md)。

- 本切片支持 Moonshot 中国站 `https://api.moonshot.cn/v1/chat/completions` 和 `kimi-k3.1-pro`。推理强度冻结为 `high`，使用单轮非流式结构化输出。只有本地回环夹具可使用测试端点。OpenAI 既有适配器、策略字节及账本重放继续兼容。 [接口](https://platform.kimi.com/docs/api/chat) · [模型参数](https://platform.kimi.com/docs/api/models-overview)
- 复用同一 `ModelGateway`、单次派发凭证、原始响应哈希和本地 JSON Schema 校验。保留实际模型、截断、HTTP 错误、用量缺失及无真实响应的 `UNKNOWN`。模型的推理 token 属于总输出用量，正文只从最终内容提取。缓存本次固定在 `implicit` 的 `5m` 档，缓存命中和写入已计入总输入用量。 [用量与缓存](https://platform.kimi.com/docs/api/chat)
- 现有账本以微美元计量。真实 Kimi 策略以文档模型窗口 1,048,576 作为最坏输入预留基数，并保留输出上限 1024。发送前用同一模型及消息调用 Token 估算，估算值加最大输出超过 16,384 即停止。估算接口的请求只含模型及消息，不能用它替代 Schema 等额外输入的预留或真实账单。真实策略的供方计价、汇率上界及短期有效期仍须有独立证据。 [Token 估算](https://platform.kimi.com/docs/api/estimate)
- 首探针沿用独占授权、私有账本、真实控制终端隐藏凭据和精确输入绑定。`.env` 中的公开配置用于选择候选。探针凭据由 `--prompt-key` 获取。需要明确证据证明计数调用可在现行预留规则下准入，疑似计费或未知时拒绝。仍为单次尝试、每次 POST 最多 30 秒、总时限最多 120 秒。真实请求、可信 CI、Canon、Permit 和 V2-020/V2-027 仍按各自授权和门禁执行。

此次可以实施并验证本地回环。待账户、政策、计数费用和数值授权具备后，单独固定真实探针许可。五条 V2-019 验收场景和 G-P5 的真实取证维持现行要求。
