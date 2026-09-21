# ANovelOS

面向中文网文的自动创作与可靠生产项目。最终目标是提升作品的阅读竞争力；工程通过、真人阅读结果与市场成绩分别验证，不承诺爆款。

当前为 **规划 v1.2 / P0 待实施**。60 个任务仍为 OPEN，尚未取得 P0 工程、真实 CI、数据库或章节认证证据。

## 从这里开始

1. [正式规划入口](plan/README.md)与[短执行协议](AGENTS.md)。
2. [P0 执行方案](plan/PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md)：V2-001～004。
3. [任务清单](plan/machine/implementation-backlog.yaml)、[阶段门禁](plan/machine/phase-gates.yaml)、[整改义务](plan/machine/remediation-register.yaml)。
4. [两份评估报告的核实与采纳](plan/changes/2026-09-21_REVIEW_ADOPTION.md)。

`plan/machine/` 是现行机器资料，`plan/generated/` 是生成视图。`gptdoc/`、`ccdoc/`、历史审核和 `plan/archive/` 是设计或证据输入，不是平行执行规范。

## 校验规划

需要 Python、PyYAML、jsonschema。依赖的精确版本与 uv.lock 随 V2-001 锁定；现在不把已有本机环境称为可复现工程环境。

```bash
python3 -B plan/scripts/validate_plan.py --check
python3 -B plan/scripts/validate_plan.py --self-test
python3 -B plan/scripts/test_governance.py
```

明确修改机器源后，用 `python3 -B plan/scripts/validate_plan.py --write-views` 更新生成视图与内容清单，再检查。规则基线不会被此命令自动重建。

## 当前实施边界

先补强资料治理，再完成真实仓库骨架、架构检查、Secret/依赖 CI 与 PostgreSQL 基础环境。P0 的准备工作可以并行筹备，正式任务关闭仍需要代码、测试、真实 CI 和验收记录。

G-P0 未验证前不开始 Narrative Kernel。优先保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。
