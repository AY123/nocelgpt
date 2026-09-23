# V2-002 审核后续变更依据

2026-09-23，用户在两份审核的事实复核与修复建议后要求继续。本次仅处理 V2-002 的本地入口边界缺陷、状态语义和提交后证据，不开始其他任务。

可信比较基线为 a3ea77304f0c68967f21532adf3852bec3ea0a4d。首次 IMPLEMENT 入口实际 PASS；仓库只有用户审核报告的既有修改，其 hash 已保存在 preflight.json。原始 PREPARE 和开工 revision 保留，不为后续修复虚构第二次开工。

- detached HEAD：Git symbolic-ref 的退出码 1 表示正常脱离分支；将 branch 记录为 null，继续绑定完整 HEAD。其他 Git 错误继续失败，恢复仍比较全部上下文。新增合法 check/run/resume、分支与 detached 切换、detached 提交变更的正反例。
- checkpoint：先读取一次字节并计算 hash，再校验 JSON 与对象类型；无效 JSON、数组、null、标量及缺字段对象产生可保存的 BLOCKED 记录，子命令不得执行。保留现有有效 checkpoint 兼容行为。
- AI-EXEC-01：其 p0_required 同时要求本地入口和 CI。保留 IMPLEMENTED_LOCAL，但整体 p0_enforcement_status 改为 NOT_IMPLEMENTED 并说明 V2-004 剩余责任；不改 owner/scenario 映射或枚举，不降低 p0_required。AI-EXEC-04/06 不变。
- 新增 12 个契约测试用例；原有测试函数、验收场景、阈值、扫描排除、最低基线、门禁、任务身份/阶段/依赖保持。V2-001 只随共享输入刷新活动包，不重新实施或认证。

提交后结果绑定实际修复提交，旧工作区记录不改写。CODE / TEST_RESULT 仅证明所列本地源字节和命令结果；CI 与最终验收仍缺失，V2-002 保持 IMPLEMENTED，G-P0/M0 不推进。实施与验证由同一操作者完成，不声称独立审核。

证据绑定首次检查真实 FAIL：三个 backlog 证据指针漏写 Schema 必需的 status（证据文件本身均为实际 PASS）。已补充 status: PASS，不改 Schema；失败产物保存在 binding-first-check-failed.json，随后重新检查。
