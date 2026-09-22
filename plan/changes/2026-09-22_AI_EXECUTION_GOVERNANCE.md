# v1.3.0：全 AI 开发执行措施落地

日期：2026-09-22。来源：用户明确项目将由 AI 持续搭建推进，要求将上一轮六项措施生成相关文件，并要求继续完成。本变更据此完善执行规划和本地校验；没有启动业务开发、真实 Provider、远端配置或工程任务验收。

## 1. 范围与权威

Plan Version 从 1.2.2 升为 1.3.0。P0—P14、两个 Anchor、60 个任务的身份/阶段/依赖、最低治理基线与生产权限边界保持不变。全部任务 OPEN、阶段 NOT_VERIFIED、真实 CI 门禁 NOT_IMPLEMENTED。新增内容不是第 16 份总体架构研究，也不增加 Agent 平台。

上一轮口头评估只指出风险，尚不能供后续 AI 稳定执行；本轮将它们接入现行入口、机器任务、测试场景及可执行检查。现有 76 项整改责任不凭本轮资料工作关闭，也不把同一措施另建成平行任务链。

## 2. 六项措施与实现范围

| 措施 | 文件/责任 | 本轮实际范围 | P0 尚须实施 |
|---|---|---|---|
| 执行包 | AI_EXECUTION_PROTOCOL、Schema、模板、V2-002 | 非 OPEN 引用要求、结构/身份/输入快照检查 | 实际开工与工具入口强制消费 |
| 改动归属 | allowed_paths、V2-003 | 已声明路径/产物的有限检查 | 真实 diff、新增未跟踪文件、依赖和语义范围核对 |
| 禁止偷偷降标 | 协议、V2-003/004 | 保留最低基线与登记对应检查 | 受保护旧版本对比、测试删改/skip/阈值与 CI 保护 |
| 决策与未知 | action、claims、ADR、V2-002 | 按声明动作检查未决 ADR/未知阻断、来源 hash 与预算字段 | 真实动作拦截、来源真实性及授权核验 |
| 可信验收 | 07、P0 方案、V2-004 | 明确当前提交、真实来源与最小权限验收责任 | 实际 CI、有效权限与错误/越权负例 |
| 交接恢复 | handoff、AI_HANDOFF_RECORD、V2-002 | 最低交接字段、版本/输入过期、检查产物 hash | 实际工作区/副作用结果/会话恢复核对 |

六项责任由 [ai-execution-policy.yaml](../machine/ai-execution-policy.yaml) 映射现有任务和场景。`IMPLEMENTED_LOCAL` 仅指本地声明检查代码存在，不是工程 VERIFIED。P0 能力状态不能在责任任务尚未实现时改为 IMPLEMENTED/VERIFIED。

## 3. 执行语义

- 正式包只能落在 `validation/`，避免包内 manifest hash 与清单自身循环；模板不可作为记录。OPEN 有包时只允许 PREPARE。
- 输入覆盖任务现行规范以及 backlog、场景、ADR 和执行政策四份机器源。活动记录必须匹配当前版本/manifest/来源字节；历史已验证记录保留可恢复快照，不为新要求重写旧记录。
- PREPARE 允许调查、拟定 ADR；IMPLEMENT、LIVE_CALL、CERTIFY 按各自时点检查。准备标签不授权真实实现或付费调用；现场拦截仍待 P0。
- FACT/ASSUMPTION/UNKNOWN 分开，决定走 ADR。来源/hash 仅证明记录和字节可核对，不认证语义正确性。未决项明确阻断动作，不能靠模型自信消除。
- last_check 的 PASS 必须有产物；FAIL/UNKNOWN 因执行器丢失等没有产物时必须解释缺失，不强迫伪造日志。模板不能当运行产物。
- 已有授权范围内的常规工作自动推进；冻结范围、最低要求、权限或预算变化依现行授权与变更规则处理，不要求每一步另行批准。

## 4. 验收与复现

新增 10 个 P0 场景：AT-V2-002-13～16、AT-V2-003-04～06、AT-V2-004-06～08，总数由 236 增为 246，全部仍 PLANNED。原场景与最低义务未删除。

现有治理正例补充合格执行包；专项回归覆盖准备正例、动作决策、合法 live/certification 声明、旧输入、缺包/错任务、模板路径、越界声明、假成功、未知记录、历史包和虚报工程状态。合成记录只存在隔离临时目录，不成为真实任务证据。

```sh
python3 -B plan/scripts/validate_plan.py --check --output-dir dist/validation/ai-governance-1.3.0
python3 -B plan/scripts/validate_plan.py --self-test --output-dir dist/validation/ai-governance-1.3.0
python3 -B plan/scripts/test_governance.py --output-dir dist/validation/ai-governance-1.3.0
python3 -B plan/scripts/test_ai_execution.py --output-dir dist/validation/ai-governance-1.3.0
```

本轮结果保存至 `plan/validation/ai-governance-1.3.0/`，绑定实际工作区 manifest；旧验证文件保持原样。资料检查不认证 HEAD 已提交内容、真实 CI、数据库、模型、工作区动作监控或阅读效果。真实读者证据仍须 E3/E4，不由 AI 模拟替代。
