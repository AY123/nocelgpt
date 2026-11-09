# V2-010 本地实现

现有同一个 CanonCommitService 已扩展为受授权的有限事实章节提交。状态为 IMPLEMENTED；尚无本轮远程CI，不关闭 V2-010、V2-011/012 或 P2。

独立 ProtectedPermitIssuer 从已绑定策略执行实际测试检查，持久化完整 Permit；提交核对 actor/request/parent、候选与全部依赖、策略、issuer、授权/执行版本、有效期和撤销状态。普通提交没有调用方 ALLOW/PASS 签发入口。原文、Delta、四类依赖、Permit 和事实快照与 commit/event/receipt/HEAD 在同一 PostgreSQL 事务写入。取消、撤销、提交共用分支锁；已成功请求可恢复原收据，不受后来过期/撤销影响。

0002 增量迁移不改0001及已接受 root 字节。没有已接受正文覆盖/删除 API，数据库不可变约束仍生效。load_commit 校验并读回完整历史内容；load_baseline 返回对应 commit 的事实基线。review_submission 只展示正文/Delta/parent/version/阻断信息，不签发、不写入。

本轮依据现行02/05的P2边界，只提供显式绑定可销毁测试数据库的 TEST issuer。默认生产拒绝新 TEST Permit。数据库名是防误用护栏，可信管理 engine 不能给普通 Worker；actor 由可信应用入口提供，未实现网络认证。Q0–Q3、正式生产 issuer/P7、完整事件重建/V2-012、并发与响应丢失专项/V2-011、生产备份恢复仍不在本轮完成范围。没有付费模型调用或正文生产闭环。

## 实际本地验证

UNIT1099，真实PostgreSQL117（原服务1+V2-009的59+V2-010的57），架构244和新模型/收据契约85，均0失败/错误/skip；85是UNIT子集。STATIC及Secret/Dependency通过。当前54项安全发现仍OPEN，按既有精确有期批准消费，无新增批准或宽泛忽略。完整结果与源码hash见local-results/SUMMARY.json；完整ARCH_FITNESS动作差异和治理验证在交付pin绑定后另行记录，不以这些局部结果冒称已通过。

首轮PG的110通过/1失败保留为原记录：畸形Permit虽已拒绝，但异常类型不正确，修复后正式117项通过。新增回归覆盖bool/int伪造、未来签发时间、撤销后重建成功票据及历史过期证据读取。

五条原验收分别由test_v2_010.py的无授权/伪造/过期/撤销/错误绑定负控；两种engine的故障全回滚；完整证据新连接读回；历史正文UPDATE/DELETE拒绝；取消先胜和提交先胜控制覆盖。迁移/打包/现有服务测试保留并加强。

复现：锁定环境运行 scripts/ci/run_gate.py postgres_env --output-dir dist/validation/<new-dir>；本机Docker不可用时失败、不skip。只创建并清理本次临时数据库和Compose资源。不修改GitHub设置、不使用历史runner。

## 2026-10-22 最新交接

最小certifi修复已随 `e35177699d59c15eb22e9bf87bf3a3a88abf5b2f` 推送至GitHub main。本地UNIT1099/STATIC/安全扫描（54精确消费、51依赖0漏洞）通过。最终 [run39747798274](https://github.com/AY123/nocelgpt/actions/runs/39747798274) 已创建一次，但GitHub以账号付款/支出限额条件拒绝启动全部六个job（runner=0、步骤=0、artifact=0）。具体是付款问题还是限额未独立确定；没有代码测试失败证据，也没有当前候选的远程PASS。详见 [CI_BLOCKER.json](CI_BLOCKER.json)。V2-010继续IMPLEMENTED，P2未完成；停止自动重试，等待账户条件解除。旧3ac验收不与新lock结果拼接。

2026-11-09最终状态：V2-010已按16259d148ac33c5578b40d0221f7f70d7ca55dc4/run42632232950完成同SHA六门验收，详见[正式验收](closure-20261109/ACCEPTANCE_SUMMARY.md)。上述内容保留各原时点，不把旧结果重新标记。
