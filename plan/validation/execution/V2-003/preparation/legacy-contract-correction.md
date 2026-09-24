# V2-003 必要契约测试路径补充

完整真实回归 `raw/011_precommit_tests.json`：235 passed、1 failed；单独复跑同一4项参数用例：3 passed、1 failed。失败为 `tests/contract/test_plan_governance.py::test_existing_rules_reject_single_mutations` 把 V2-002 标 CLOSED 后只期待 `TASK_EVIDENCE`。

实际 `validate_plan.py` 的该诊断专指证据 revision 数量不等于1。V2-002 的 CODE/TEST_RESULT 已在上次交付绑定同一 revision，因此当下正确结果是 `TASK_SCHEMA` 指出 ci/acceptance 空值及 `TASK_TEST`；任务仍然被拒绝关闭。`git diff --quiet c6f26c6 -- plan/scripts/validate_plan.py tests/contract/test_plan_governance.py` 返回0，确认校验器与该测试均未在 V2-003 改动。原失败完整保留，不改校验器制造旧诊断。

依据用户“有问题或补充的直接修正后启动”及本任务完成正反回归的既有授权，补充这一个支持测试路径，以校正旧负例的诊断并额外断言缺 CI 与缺验收分别被拒绝；不删除/skip 测试，不减少断言、不改变实际拒绝要求。本项属于既有任务必要集成修正，不开启 V2-004。原 scope v1/v2 及失败均保留；v3 仅增一个 allowed_path，无其他范围、保护、身份、依赖、权限或规则例外改变。先单独提交 v3 固定新范围，再修改测试；精确代码变化仍须技术复核与真实复验。
