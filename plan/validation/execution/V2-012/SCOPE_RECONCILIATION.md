# P2结项范围清单补正

原固定范围已包含P2/M2汇总及phase/milestone登记，但遗漏`plan/machine/ci-gates.yaml`这一处既有逻辑门禁的状态登记。最终同SHA run42774996789已经在POSTGRES_ENV执行atomic/CAS/same-different payload/rebuild全部控制；未实施新的检测，也不需要新增或重跑workflow。

本次仅将现有`CANON_CAS_IDEMPOTENCY`从NOT_IMPLEMENTED登记为VERIFIED，引用这次真实CI及逐断言测试。activation_phase、mode、allow_failure、四条checks及六个物理job完全保留。它不是第七个CI job，不能靠状态字段替代真实PG证据。

这是当前V2-012及已纳入范围的P2正常结项所需路径清单补正，属于操作者对现有任务授权的范围解释，不是新增用户原文授权或安全例外。保留旧scope.json/pin不改写；在变更该机器登记前建立新的固定scope-p2-closure.json，新增且仅新增该精确路径。代码、测试、依赖、安全批准、GitHub设置及后续任务不变。后续实际差异仍须以新固定pin审查并保留finding，不以无意义CI重跑补位。
