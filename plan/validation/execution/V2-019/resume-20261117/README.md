# V2-019 恢复收口（2026-11-17）

本轮按[用户原话](authorization.txt)收口已有差异、scope/review 绑定和公开价格/能力核对。V2-019 保持 IN_PROGRESS / IMPLEMENT；付费调用未获授权，V2-020 保持 OPEN / PREPARE。实施与验证为同一操作者，Agent 技术交叉检查不等于独立人员审核。

## 差异与固定绑定

恢复起点为 `cefeaaf4a1889fdaf9c19a55de6621a1e1daa3c9`，当时 `main`、工作区干净，GitHub main 为同一 SHA。[DIFF_ATTRIBUTION.json](DIFF_ATTRIBUTION.json)逐项绑定实现审查 `6ab1474` 至恢复起点的 25 个文件：V2-019 上下文协调 2 个、V2-020 离线准备 18 个、其资料/报告同步 5 个。Gateway 源码、原测试、CI、治理与最低验收未变。

原 opening 至恢复起点的 6 个 REVIEW finding 保留对账：4 个测试 finding 的内容与原处置完全一致；2 个 backlog finding 因全文件 hash 变化重新核对，新增差异仅为 V2-020 准备包引用。没有删减验收或放宽门禁。原 scope、implementation-review、LOCAL_RESULTS 及本地实现报告未覆盖。

- Scope pin：`9f80d0ad7433ff00f19701f8ce53504f9ff90ecd` / [scope.json](scope.json)。opening 为恢复起点，allowed_paths 与原表严格相同，例外为空；V2-020 路径没有加入。
- Review pin：`ae047be144fd08c005355f7e090eb450ad6fc149` / [review.json](review.json)。真实新差异扫描为零 finding 后固定空 dispositions，仅适用于恢复窗口，不替代历史审查。

当前执行包绑定上述双 pin；实际 index/worktree 差异在命令前后检查。已提交的 V2-020 内容属于恢复起点，继续修改它仍会越界；新基线不授予实施 V2-020 的权限。

## 官方资料与政策

2026-11-17 已重新获取官方[价格页](https://developers.openai.com/api/docs/pricing)、[gpt-6-luna 模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)及[输入计数接口](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count)。公开原页快照、获取时间与 hash 见[来源核对](provider-source-verification.json)，原始文件位于新的 `dist/recovery/v2019-20261117-01/official-docs/`，未修改历史 dist/validation。

目录仍声明模型支持 Responses、结构化输出及 reasoning none；窗口 1,050,000、最大输出 128,000。标准普通输入/输出分别为每百万 token 0.10/0.50 美元。账户实际访问、计数/Schema 行为及真实费用尚未验证。

本轮 model-policy 仅改变 `id` 和 `price_expires_at`，不降低费率/预留，不扩大窗口/输出，不更换模型。应用窗口仍为 16384、输出 1024；输入保守上界仍按每百万 0.25 美元、输出 0.50 美元，误差余量 1000 微美元，每 attempt 预留 5608 微美元。模型仍只是原协议探针候选，不代表写作选型或文学质量判断。

新政策标识为 `openai-protocol-probe-20261117`，有效期至 `2026-11-18T03:49:58.347947Z`（北京时间 11:49:58）。24 小时是本地复核间隔，不是厂商保价保证；实际调用前若到期或条件变化必须再核对。

## 本轮验证与后续

[RESULTS.json](RESULTS.json)绑定本轮真实结果和源文件 hash：

- Gateway 既有专项 124 项通过，0 failure / error / skip；包含本地 HTTP、成功路径、预算拒绝、UNKNOWN、恢复与隔离。
- 规划检查、32 项校验器自测、39 项治理回归、36 项 AI 执行回归及 13 项历史负例探针通过；五项聚合治理命令均退出 0。
- 显式架构检查 42 个文件、0 finding；write-views 通过，规范 manifest/生成视图字节未变。
- 当前政策解析及保守预留核对通过，离线探针请求重建通过。LIVE_CALL 检查因与绑定的 IMPLEMENT 动作不符而 BLOCKED；未派发命令。预算与 UNKNOWN 控制另由上述已有正反例验证。

2216 项、0 skip 仍是原实现的历史本地结果，本轮没有声称重新运行全量，也没有新增远程 CI、真实 Provider 或 P5 验收。

当前 `paid_calls_allowed=false`、`model_cost_cap=0`。用户尚需明确真实调用总额、尝试次数、时长/停止条件；安全凭据入口和账户模型能力也待核实。现有本地任务入口不会派发 LIVE_CALL 子命令，未来须核定适用授权/派发路径，不能直接绕过入口执行付费探针。进入真实调用前还要重查政策和冻结新请求，不能复用旧政策的运行快照。真实接缝稳定后再做最终精确源码六门 CI 与 V2-019/P5 验收；V2-020 正式实施继续等待其前置门禁与授权。
