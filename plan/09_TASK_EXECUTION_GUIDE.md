# 任务执行与关闭证据

## 1. 开始任务

读取 backlog 中 task、对应现行规范、验收场景和必需 ADR。确认前置 Phase Gate 与依赖任务已 VERIFIED/CLOSED。若该任务仍需细化（PLANNED），先把输入、测试场景、产物路径、范围、负责人和待决项补齐，才转 IN_PROGRESS。

前四任务已提供执行级要求，可以开始；并不意味着它们已实现。后续任务具备明确目标和验收映射，具体接口设计在最晚决策点前细化。

`normative_specs` 指向本包现行规则；`design_references` 指向对应领域的原始详细设计快照，便于查阅候选字段和研究背景。参考快照中的旧阶段、证据语义、缺陷 Schema 和完成状态不恢复为现行规则。任务产物与目标测试路径相对项目根目录；规范、参考和验收记录引用相对 plan 目录。

## 2. 状态机

```text
OPEN → IN_PROGRESS → IMPLEMENTED → VERIFIED → CLOSED
```

IMPLEMENTED 表示代码/配置已存在；VERIFIED 需对应测试与 CI；CLOSED 还需验收记录与未关闭缺陷的明确处置。发现回归可以重开，历史证据不删除。

`evidence.code`、`tests`、`ci`、`acceptance` 在 VERIFIED/CLOSED 时都必须有可定位引用，绑定同一变更/提交。生产测试失败不能仅修改状态字段。填写 [验收模板](templates/TASK_ACCEPTANCE_RECORD.yaml)。

## 3. 计划测试与已执行测试

[test-catalog.yaml](machine/test-catalog.yaml) 记录每个任务的计划场景、断言和未来测试路径。当前状态 PLANNED，所有未来代码路径都明确是 expected outputs，不要求本资料包中已经存在。

文件存在校验只应用于现行规范、来源与已提交证据；不能为了路径校验通过创建空测试文件。业务实现完成后，需把测试状态和运行证据更新为真实结果。

## 4. 常用命令

在项目根目录运行：

```bash
python3 plan/scripts/validate_plan.py --check
python3 plan/scripts/validate_plan.py --write-views
python3 plan/scripts/validate_plan.py --self-test
```

`--check` 不修正不一致；检查后输出范围明确的 JSON。`--write-views` 仅从机器源重新生成只读表；不能自动关闭任何任务。`--self-test` 在内存/临时环境注入任务错位、循环、空 CLOSED、缺失证据等反例，确认验证器确实拒绝。

本脚本只验证实施资料，不替代后续 pytest、PostgreSQL、CI 或真实 Provider 测试。源版本变化后重新检查；包内结果不适用于未记录的新版本。

## 5. 工作纪律

优先完成当前关键链及必要防线，不新增没有消费者的模块或 Schema。不从 archive 直接抄入已知缺陷实现。不把外部研究结论当本系统收益证明。用户新决策进入机器源/正文及影响登记，避免依靠聊天隐式维护版本。
