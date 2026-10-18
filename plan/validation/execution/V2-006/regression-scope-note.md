# V2-006 回归夹具的最小范围补充

实际首轮UNIT发现既有 TASK_START 单点反例夹具在开启V2-006后不再是合法前提：它只重置V2-005和P0，却保留V2-006的活动状态。原失败保留于dist/validation/v2006-local-20261018/governance-contract-probe.xml与unit.xml。

用户持续授权推进本任务内的普通必要修复。新固定scope只额外允许tests/contract/test_plan_governance.py；先记录范围再修复。仅在隔离数据副本中把非P0任务恢复OPEN，以建立缺前置门的合法基线，再执行原IN_PROGRESS单点突变。原测试保留，新增断言精确核对V2-005被TASK_START拒绝。真实项目状态、验证器、六门、业务验收、依赖与安全策略均不改。

旧scope/start-review及失败产物保留。属于同操作者技术复核，不声称独立人员审计。
