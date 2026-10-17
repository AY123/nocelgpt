**当前：P0 工程验收 VERIFIED；V2-001～004 CLOSED；M0 VERIFIED。** 证据与限制见 [P0验收](docs/P0_ACCEPTANCE.md)。工程CI基线611d777，后续文档/夹具维护未新增远程CI。P1尚未开始。

# ANovelOS

Current delivery target: [AY123/nocelgpt](https://github.com/AY123/nocelgpt) (private). V2-004 is CLOSED under the Owner-directed single-operator profile. Engineering revision `611d777`, [Actions run38917341667](https://github.com/AY123/nocelgpt/actions/runs/38917341667): six mandatory gates PASS,714 tests,0 skips. CI is manual at key deliveries. Adversarial permission isolation is not claimed; P0 aggregate is VERIFIED at that engineering baseline; later local fixture maintenance is recorded separately.

面向中文网文的自动创作与可靠生产项目。最终目标是提升作品的阅读竞争力；工程通过、真人阅读结果与市场成绩分别验证，不承诺爆款。

当前为 **Plan v1.3.0 / V2-001～V2-004 CLOSED / G-P0 VERIFIED**。GitHub 工程提交611d777六门全绿、714测试通过。52项历史安全发现保持OPEN，按有限期精确批准消费；没有全局忽略。单人Owner模式与权限限制按用户要求明确登记。其余56任务仍OPEN，P0整体已完成工程验收，章节生产未开始。见[V2-004实施记录](docs/V2-004_IMPLEMENTATION_REPORT.md)与[收口决定](plan/changes/2026-10-16_V2-004_SINGLE_OPERATOR_CLOSURE.md)。

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

V2-003 已完成本地实施与验证，复用 V2-001 的锁定环境和 V2-002 的动作入口。`scripts/check_architecture.py` 扫描完整 `src/anovel` Python 源码，检查导入边界和当前 P0 硬门禁政策；`scripts/check_changes.py` 比较固定 Git 基线与实际 index/worktree，审查任务范围和可识别的验收弱化。代码存在与验证完成分别记录。V2-004已完成真实GitHub六门CI及单人模式验收，证据绑定611d777；本次后续文档登记不冒称其新SHA已运行CI。

G-P0 未验证前不开始 Narrative Kernel。优先保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。

V2-004当前流水线为 `.github/workflows/v2-004.yml`，六门均mandatory，仅关键交付手动触发。`.gitlab-ci.yml`及旧protected runner记录保留历史，不用它们冒充GitHub权限验证。本地命令仍可复用 `uv run --locked python -B scripts/ci/run_gate.py static --output-dir dist/validation/static-run-1`；真实结果见实施记录。

## 资料治理与本地任务入口

现行规范索引直接来自任务表的 `normative_specs`，检查器解析真实路径后拒绝 archive 别名与符号链接。`design_references` 继续作为历史参考。以下工程命令复用全部既有校验器和回归，输出规范—任务索引、实际仓库上下文配置清单及原始结果；输出目录每次使用新名称，不覆盖旧记录：

```bash
python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-1
python3 -B -m pytest -q tests/contract
```

正式动作前使用已绑定的任务专属执行包。`check` 实际读取仓库和输入；`run` 在检查通过后才启动 `--` 后的命令，保留子命令退出码；`resume` 重新核对上一份 PASS 的实际结束状态和当前输入。下面展示已绑定当前执行包的 V2-003 命令，不创建或推进其他任务；旧 V2-001/002 历史包若缺 change_review，仅保留其历史证据，新受限动作必须重新准备绑定：

```bash
python3 -B scripts/task_execution.py check --task V2-003 --action IMPLEMENT --output dist/validation/start-1.json
python3 -B scripts/task_execution.py run --task V2-003 --action IMPLEMENT --output dist/validation/run-1.json -- python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-2
python3 -B scripts/task_execution.py resume --task V2-003 --action IMPLEMENT --checkpoint dist/validation/run-1.json --output dist/validation/resume-1.json
```

报告须输出至 plan 外：仓库内使用 Git 已忽略且未跟踪的目录（如 `dist/`），也可使用仓库外独立目录。恢复检查绑定根目录、branch、HEAD、暂存区、已跟踪/未跟踪文件内容、执行包及交接产物；即使两个时点都 dirty，内容变化也会拒绝恢复。归档结果或提交本身会改变上下文，此时保留旧记录、核对变化后重新 `check`，不能修改旧 checkpoint 使其通过。FAIL/UNKNOWN 不继承为成功，也不自动重放有副作用的命令。

这是本地命令入口：不能拦截操作者绕过入口直接使用其他工具，不能判断任意子命令的业务语义，不能证明远端来源或最小权限。PREPARE 仅用于授权的调查命令。LIVE_CALL/CERTIFY 的资料条件仍由既有校验器检查；实际付费/认证 dispatch 在受保护授权接入前保持拒绝。

## V2-003 本地架构与差异检查

在仓库根目录使用锁定环境，每次选择新的报告文件：

```bash
.venv/bin/python -B scripts/check_architecture.py --output dist/validation/architecture-run-1.json
V2003_SCOPE_REVISION=$(.venv/bin/python -B -c 'import json; print(json.load(open("plan/validation/execution/V2-003/followup/pinned-baseline.json"))["scope_revision"])')
V2003_SCOPE_REF=$(.venv/bin/python -B -c 'import json; print(json.load(open("plan/validation/execution/V2-003/followup/pinned-baseline.json"))["scope_ref"])')
.venv/bin/python -B scripts/check_changes.py --task V2-003 \
  --scope-revision "$V2003_SCOPE_REVISION" --scope-ref "$V2003_SCOPE_REF" \
  --output dist/validation/changes-run-1.json
.venv/bin/python -B -m pytest -q tests/architecture tests/contract
```

架构检查静态读取源码，不运行候选模块。它区分 Workflow 可请求的 `anovel.canon.commit_service` 公共提交服务与 `anovel.canon.repository` 内部写能力；这些规则通过测试夹具验证，未创建 Canon 业务实现，也不证明 P2 运行时写权限。空扫描、不能解析的加载行为和关闭适用硬门禁的请求会失败。

差异检查中的 scope commit 固定开工范围、用户既有改动身份和授权来源。运行前将 `pinned-baseline.json` 中的最新 pin 与当前有效交接核对；该文件提供定位信息，授权内容从明确的 Git commit 读取。开工清单的补正原因和原 pin 保留在准备记录中。尚未处置的 finding 返回失败并保留报告；有依据的技术处置需再提供 `--review-revision` 与 `--review-ref`，二者从当前有效交接取值，绑定准确内容和验证产物。改变被审内容后须重新核对，不能把旧 review 用于新改动。命令和处置方法见[任务执行指南](plan/09_TASK_EXECUTION_GUIDE.md)。

`task_execution.py` 对 IMPLEMENT/LIVE_CALL/CERTIFY 自动读取执行包 `change_review` 的 scope/review pin，在命令前后强制核对差异；缺少绑定会阻断，CLI 只能重述同值、不能覆盖绑定。PREPARE 允许先调查再冻结范围；付费/认证 dispatch 仍被拒绝。架构检查作为明确的子命令执行。所有本地工具均不能抵抗同一写入者修改或绕过检查器；V2-004已交付真实GitHub来源核对；单人模式不声称对抗性权限隔离。
