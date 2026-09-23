# ANovelOS

面向中文网文的自动创作与可靠生产项目。最终目标是提升作品的阅读竞争力；工程通过、真人阅读结果与市场成绩分别验证，不承诺爆款。

当前为 **Plan v1.3.0 / V2-001 IMPLEMENTED / V2-002 IMPLEMENTED**。最小 Python 包、锁定安装与真实 PostgreSQL 基础测试已实现；本轮接入资料治理工程命令。其余 58 个任务仍 OPEN。远端 CI、P0 退出和章节生产未验证。

## 从这里开始

1. [正式规划入口](plan/README.md)与[短执行协议](AGENTS.md)。
2. [P0 执行方案](plan/PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md)：V2-001～004。
3. [任务清单](plan/machine/implementation-backlog.yaml)、[阶段门禁](plan/machine/phase-gates.yaml)、[整改义务](plan/machine/remediation-register.yaml)。
4. [AI 开发执行协议](plan/AI_EXECUTION_PROTOCOL.md)、[六项执行约束](plan/machine/ai-execution-policy.yaml)及[本轮落地记录](plan/changes/2026-09-22_AI_EXECUTION_GOVERNANCE.md)。

`plan/machine/` 是现行机器资料，`plan/generated/` 是生成视图。原 `gptdoc/`、`ccdoc/`、历史审核与矩阵已统一保留在 `plan/archive/`，根目录重复副本已清除；历史内容不是平行执行规范。

仓库清理已完成，逐文件去向、hash 和恢复依据见[资料迁移清单](docs/repository-layout-migration.md)。独有原始文档和日志已补充归档，工具配置保留。`dist/planning/` 是可再生成的分发目录，旧版本包不覆盖当前 `plan/`。V2-001 的实际状态和交接见[执行包](plan/validation/execution/V2-001/execution-packet.yaml)，版本选择见 [ADR-001](plan/decisions/ADR-001_RUNTIME_AND_LOCKING.md)。

## 安装和测试

基线是 Python **3.12.14**、uv **0.12.17**、PostgreSQL **17.11** 的 digest 固定镜像。测试需要运行中的 Docker 和支持 `up --wait` 的 Compose v2+；本轮使用 Docker 29.4.0 / Compose 5.1.2。初次安装需要访问 PyPI 和 Python 分发源，数据库镜像首次拉取需要网络。

若尚未安装 uv，可在仓库根目录执行以下本地安装；已有精确版本也可以直接使用。以下命令不修改系统 Python：

```bash
python3 -m pip install --target dist/tools/uv-bootstrap --index-url https://pypi.org/simple uv==0.12.17
export PATH="$PWD/dist/tools/uv-bootstrap/bin:$PATH"
export UV_CACHE_DIR="$PWD/dist/cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/dist/tools/python"
uv python install 3.12.14 --no-bin
uv sync --locked
uv run --locked python -c 'import anovel; print(anovel.__version__)'
uv run --locked python -m pytest --collect-only -q
uv run --locked python -m pytest -q -s
```

`uv.lock` 是唯一应用/测试依赖锁文件。普通安装使用 `--locked`，不得自动更新后宣称可重复；首次依赖变化才显式 `uv lock` 并审查 diff。P0 当前只安装实际测试/治理依赖，不预装 Web、Agent、Pydantic 或 Alembic 运行框架。

测试自动生成一次性数据库凭证和唯一 `anovel-v2001-...` Compose project，使用回环随机端口与 tmpfs，完成后删除本次项目的容器、网络和卷。测试忽略项目 `.env`，不需要手工建库或提供生产配置；Docker 不可用会失败，不跳过。正常/异常退出清理均有真实测试。若进程被 SIGKILL 或宿主断电，使用输出中的确切 project name 恢复清理；不要执行全局 prune：

```bash
ANOVELOS_TEST_DB=bootstrap_test ANOVELOS_TEST_USER=bootstrap_test ANOVELOS_TEST_PASSWORD=cleanup-only \
docker compose --env-file /dev/null -f compose.yaml -p <输出中的项目名> down --volumes --remove-orphans
```

`.env.example` 仅是测试配置字段示例，自动测试不读取它。独立探针 `uv run --locked python scripts/check_postgres.py` 要求显式 `ANOVELOS_TEST_DSN`，缺失返回 2，连接失败返回 1；不会自行选择数据库或创建业务表。格式为 `postgresql+psycopg://<测试用户>:<一次性密码>@127.0.0.1:<映射端口>/<测试库>`。不得配置生产库。

## 校验规划

PyYAML 和 JSON Schema Draft 2020-12 校验库已由 `uv.lock` 锁定。运行以下命令前激活 `.venv`，使 `python3` 来自已锁定环境。输出到独立目录，保留历史验证记录：

```bash
source .venv/bin/activate
python3 -B plan/scripts/validate_plan.py --check --output-dir dist/validation/local
python3 -B plan/scripts/validate_plan.py --self-test --output-dir dist/validation/local
python3 -B plan/scripts/test_governance.py --output-dir dist/validation/local
python3 -B plan/scripts/test_ai_execution.py --output-dir dist/validation/local
```

明确修改机器源后，用 `python3 -B plan/scripts/validate_plan.py --write-views` 更新生成视图与内容清单，再检查。规则基线不会被此命令自动重建。

## 当前实施边界

本次仅实施 V2-002，复用 V2-001 的锁定环境。架构检查、实际差异归属与防验收弱化属于 V2-003；Secret/依赖 CI、远端来源与保护权限属于 V2-004，均未开始。正式任务关闭需要代码、测试、真实 CI 和验收记录。本地 PASS 与 CI PASS 分别记录。

G-P0 未验证前不开始 Narrative Kernel。优先保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。

## 资料治理与本地任务入口

现行规范索引直接来自任务表的 `normative_specs`，检查器解析真实路径后拒绝 archive 别名与符号链接。`design_references` 继续作为历史参考。以下工程命令复用全部既有校验器和回归，输出规范—任务索引、实际仓库上下文配置清单及原始结果；输出目录每次使用新名称，不覆盖旧记录：

```bash
python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-1
python3 -B -m pytest -q tests/contract
```

正式动作前使用已绑定的任务专属执行包。`check` 实际读取仓库和输入；`run` 在检查通过后才启动 `--` 后的命令，保留子命令退出码；`resume` 重新核对上一份 PASS 的实际结束状态和当前输入。下面仅展示 V2-002 的本地命令，不创建或推进其他任务：

```bash
python3 -B scripts/task_execution.py check --task V2-002 --action IMPLEMENT --output dist/validation/start-1.json
python3 -B scripts/task_execution.py run --task V2-002 --action IMPLEMENT --output dist/validation/run-1.json -- python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-2
python3 -B scripts/task_execution.py resume --task V2-002 --action IMPLEMENT --checkpoint dist/validation/run-1.json --output dist/validation/resume-1.json
```

报告须输出至 plan 外：仓库内使用 Git 已忽略且未跟踪的目录（如 `dist/`），也可使用仓库外独立目录。恢复检查绑定根目录、branch、HEAD、暂存区、已跟踪/未跟踪文件内容、执行包及交接产物；即使两个时点都 dirty，内容变化也会拒绝恢复。归档结果或提交本身会改变上下文，此时保留旧记录、核对变化后重新 `check`，不能修改旧 checkpoint 使其通过。FAIL/UNKNOWN 不继承为成功，也不自动重放有副作用的命令。

这是本地命令入口：不能拦截操作者绕过入口直接使用其他工具，不能判断任意子命令的业务语义，不能证明远端来源或最小权限。PREPARE 仅用于授权的调查命令。LIVE_CALL/CERTIFY 的资料条件仍由既有校验器检查；实际付费/认证 dispatch 在受保护授权接入前保持拒绝。
