# ANovelOS

面向中文网文的自动创作与可靠生产项目。最终目标是提升作品的阅读竞争力；工程通过、真人阅读结果与市场成绩分别验证，不承诺爆款。

**阶段摘要（2026-11-13）：Plan v1.3.0；V2-001～013 CLOSED；P0/G-P0、P1/G-P1、P2/G-P2及M0/M1/M2 VERIFIED。** 日常开发使用 `main`，远程为 [AY123/nocelgpt](https://github.com/AY123/nocelgpt)。任务状态以[机器任务表](plan/machine/implementation-backlog.yaml)及其实际证据为准，本文只提供导航。

当前业务能力包括内存中的项目隔离实体、稳定 ID、改名、别名歧义解析，以及人物、关系、显式观察取得知识、误信与目标/计划分离；现已增加事件双顺序与有依据的Promise生命周期。**V2-008 NarrativeDelta 已完成工程验收，P1内存Narrative Kernel退出条件已通过**；V2-009已完成持久化和人工/测试根提交的工程验收，V2-010已完成有限事实章节Commit/Permit协议的工程验收（生产默认拒绝TEST Permit）；V2-011/012已验证章节安全重试、并发、断线恢复和有限事实历史重建；尚无正式生产issuer、模型调用或章节生产闭环。

- P0 工程验收绑定 `611d777` / [run38917341667](https://github.com/AY123/nocelgpt/actions/runs/38917341667)，六门通过、714 项测试、0 skip；见[P0 汇总验收](plan/validation/execution/P0/closure-20261017/ACCEPTANCE_SUMMARY.md)。
- V2-005 工程验收绑定 `72219b4` / [run39088653270](https://github.com/AY123/nocelgpt/actions/runs/39088653270)，六门通过、889 项测试、0 skip，其中领域测试97项；见[V2-005 验收记录](plan/validation/execution/V2-005/closure-20261018/ACCEPTANCE_SUMMARY.md)。后续文档提交不冒称已重新运行 CI。

- V2-006 工程验收绑定 `e210078` / [run39106725089](https://github.com/AY123/nocelgpt/actions/runs/39106725089)，六门通过、990项测试、0skip，领域测试101项；见[验收记录](plan/validation/execution/V2-006/closure-20261018/ACCEPTANCE_SUMMARY.md)。

- V2-007 工程验收绑定 `a0ea8df` / [run39119023861](https://github.com/AY123/nocelgpt/actions/runs/39119023861)，六门通过、1071项测试0skip，含81项专项；见[验收记录](plan/validation/execution/V2-007/closure-20261018/ACCEPTANCE_SUMMARY.md)。

- V2-008及P1汇总绑定`f611ba3` / [run39128464248](https://github.com/AY123/nocelgpt/actions/runs/39128464248)，六门通过、1173项测试0skip；含102项V2-008、381项P1领域测试。见[P1汇总](plan/validation/execution/P1/closure-20261018/ACCEPTANCE_SUMMARY.md)。不代表持久Canon或章节生产。

- V2-009工程验收绑定`3d12f20` / [run39256589017](https://github.com/AY123/nocelgpt/actions/runs/39256589017)，六门通过、1318项测试0skip；见[验收记录](plan/validation/execution/V2-009/closure-20261019/ACCEPTANCE_SUMMARY.md)。该次范围为根提交持久化；P2最新工程汇总见下文。

54 项安全发现保持 OPEN，按有限期精确批准消费，没有全局忽略。采用用户确认的单人 Owner 模式，不声称具备对抗性权限隔离；见[收口决定](plan/changes/2026-10-16_V2-004_SINGLE_OPERATOR_CLOSURE.md)。CI 仅在关键交付时手动触发。

## 从这里开始

1. [AGENTS.md](AGENTS.md) → [plan/README.md](plan/README.md)：确认目录、目标和有效资料入口。
2. 从[任务清单](plan/machine/implementation-backlog.yaml)读取本次任务，再核对[阶段门禁](plan/machine/phase-gates.yaml)、[验收场景](plan/machine/test-catalog.yaml)和[ADR 登记](plan/machine/decision-register.yaml)。V2-009已完成工程验收；V2-010已完成工程验收；下一任务V2-014仍OPEN，须建立其专属执行包，已完成的任务不重新走IMPLEMENT。
3. 按任务的 `normative_specs` 阅读适用规范，遵守[AI 开发执行协议](plan/AI_EXECUTION_PROTOCOL.md)，建立并核对本任务执行包后实施。
4. 需要追溯时再读对应验收、历史报告和 archive；不要求每次开发重新遍历已完成的 P0 工作。历史报告中的“当前”仅指其记录时点，不能覆盖机器源。

`plan/machine/` 是现行机器资料，`plan/generated/` 是生成视图。原 `gptdoc/`、`ccdoc/`、历史审核与矩阵已统一保留在 `plan/archive/`，根目录重复副本已清除；历史内容不是平行执行规范。

此前资料迁移的逐文件去向、hash 和恢复依据见[资料迁移清单](docs/repository-layout-migration.md)，不是当前清理授权。独有原始文档和日志已补充归档，工具配置保留。`dist/planning/` 是可再生成的分发目录，旧版本包不覆盖当前 `plan/`；`dist/validation/` 中的历史证据和嵌套 checkout 不作日常开发入口。运行环境选择见 [ADR-001](plan/decisions/ADR-001_RUNTIME_AND_LOCKING.md)。

## 安装和测试

基线是 Python **3.12.14**、uv **0.12.17**、PostgreSQL **17.11** 的 digest 固定镜像。测试需要运行中的 Docker 和支持 `up --wait` 的 Compose v2+；V2-001 本地验收记录使用 Docker 29.4.0 / Compose 5.1.2，不代表后来宿主版本已重新核验。初次安装需要访问 PyPI 和 Python 分发源，数据库镜像首次拉取需要网络。

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

G-P0 已 VERIFIED，P1/G-P1及M1已VERIFIED，下一阶段为P2 Canon Kernel；后续动作仍须满足各自任务与 ADR 前提。保留模块化单体、唯一 Canon 写路径、两个 Anchor Genre、有限修复和分阶段认证，复杂参考智能、学习和市场反馈仍按后期路线实施。

当前六门流水线为 `.github/workflows/v2-004.yml`，V2-005 也复用该入口；文件名不表示只验证 V2-004。六门均 mandatory，仅关键交付手动触发。`.gitlab-ci.yml`、旧验证器及 protected runner 记录仍供历史与回归使用，不用它们冒充 GitHub 权限验证。本地命令可复用 `uv run --locked python -B scripts/ci/run_gate.py static --output-dir dist/validation/static-run-1`；输出目录须使用新名称。

## 资料治理与本地任务入口

现行规范索引直接来自任务表的 `normative_specs`，检查器解析真实路径后拒绝 archive 别名与符号链接。`design_references` 继续作为历史参考。以下工程命令复用全部既有校验器和回归，输出规范—任务索引、实际仓库上下文配置清单及原始结果；输出目录每次使用新名称，不覆盖旧记录：

```bash
python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-1
python3 -B -m pytest -q tests/contract
```

正式动作前使用本任务专属执行包。`check` 实际读取仓库和输入；`run` 在检查通过后才启动 `--` 后的命令，保留子命令退出码；`resume` 重新核对上一份 PASS 的实际结束状态和当前输入。**下面是 V2-003 的历史命令示例，不是当前开工命令**：完成任务的 IMPLEMENT 应被拒绝；新受限动作必须准备本任务的有效绑定，不能复用旧包重新实施已关闭任务。

```bash
python3 -B scripts/task_execution.py check --task V2-003 --action IMPLEMENT --output dist/validation/start-1.json
python3 -B scripts/task_execution.py run --task V2-003 --action IMPLEMENT --output dist/validation/run-1.json -- python3 -B scripts/check_governance.py --output-dir dist/validation/governance-run-2
python3 -B scripts/task_execution.py resume --task V2-003 --action IMPLEMENT --checkpoint dist/validation/run-1.json --output dist/validation/resume-1.json
```

报告须输出至 plan 外：仓库内使用 Git 已忽略且未跟踪的目录（如 `dist/`），也可使用仓库外独立目录。恢复检查绑定根目录、branch、HEAD、暂存区、已跟踪/未跟踪文件内容、执行包及交接产物；即使两个时点都 dirty，内容变化也会拒绝恢复。归档结果或提交本身会改变上下文，此时保留旧记录、核对变化后重新 `check`，不能修改旧 checkpoint 使其通过。FAIL/UNKNOWN 不继承为成功，也不自动重放有副作用的命令。

这是本地命令入口：不能拦截操作者绕过入口直接使用其他工具，不能判断任意子命令的业务语义，不能证明远端来源或最小权限。PREPARE 仅用于授权的调查命令。LIVE_CALL/CERTIFY 的资料条件仍由既有校验器检查；实际付费/认证 dispatch 在受保护授权接入前保持拒绝。

## 本地架构与差异检查（含 V2-003 历史示例）

在仓库根目录使用锁定环境，每次选择新的报告文件。下面的 V2-003 固定 pin 只用于追溯该历史任务；当前任务的 pin 必须来自它自己的执行包：

```bash
.venv/bin/python -B scripts/check_architecture.py --output dist/validation/architecture-run-1.json
V2003_SCOPE_REVISION=$(.venv/bin/python -B -c 'import json; print(json.load(open("plan/validation/execution/V2-003/followup/pinned-baseline.json"))["scope_revision"])')
V2003_SCOPE_REF=$(.venv/bin/python -B -c 'import json; print(json.load(open("plan/validation/execution/V2-003/followup/pinned-baseline.json"))["scope_ref"])')
.venv/bin/python -B scripts/check_changes.py --task V2-003 \
  --scope-revision "$V2003_SCOPE_REVISION" --scope-ref "$V2003_SCOPE_REF" \
  --output dist/validation/changes-run-1.json
.venv/bin/python -B -m pytest -q tests/architecture tests/contract
```

架构检查静态读取源码，不运行候选模块。它区分 Workflow 可请求的 `anovel.canon.commit_service` 公共提交服务与 `anovel.canon.repository` 内部写能力；这些静态规则通过测试夹具验证；当前 Canon 运行证据见下方 P2 验收，静态检查本身不证明运行时写权限。空扫描、不能解析的加载行为和关闭适用硬门禁的请求会失败。

差异检查中的 scope commit 固定开工范围、用户既有改动身份和授权来源。运行前将 `pinned-baseline.json` 中的最新 pin 与当前有效交接核对；该文件提供定位信息，授权内容从明确的 Git commit 读取。开工清单的补正原因和原 pin 保留在准备记录中。尚未处置的 finding 返回失败并保留报告；有依据的技术处置需再提供 `--review-revision` 与 `--review-ref`，二者从当前有效交接取值，绑定准确内容和验证产物。改变被审内容后须重新核对，不能把旧 review 用于新改动。命令和处置方法见[任务执行指南](plan/09_TASK_EXECUTION_GUIDE.md)。

`task_execution.py` 对 IMPLEMENT/LIVE_CALL/CERTIFY 自动读取执行包 `change_review` 的 scope/review pin，在命令前后强制核对差异；缺少绑定会阻断，CLI 只能重述同值、不能覆盖绑定。PREPARE 允许先调查再冻结范围；付费/认证 dispatch 仍被拒绝。架构检查作为明确的子命令执行。所有本地工具均不能抵抗同一写入者修改或绕过检查器；V2-004已交付真实GitHub来源核对；单人模式不声称对抗性权限隔离。

## 历史维护记录（非当前任务入口）

2026-10-17精确处置补记：Owner已批准报告公开哈希的两个精确例外及52→54账本重绑定，仍到期于2027-01-06T06:07:49Z；当前54项OPEN（45精确例外、9历史风险接纳），本地完整扫描54/54消费、0未匹配、0未使用批准。工作区来源基线推进至9d71f91且原16项内容逐一不变，历史身份不变；旧52项GitHub扫描结果仍仅属于611d777。原暂停记录保留在CURRENT_HEAD_BLOCKER.json，由CURRENT_HEAD_RESOLUTION.json及authority-54/OWNER_DECISION_RECEIPT.json补充解除，不改写历史。

结项兼容修正：ARCH_FITNESS对VERIFIED/CLOSED任务执行固定scope/review的实际差异审计；进行中任务仍走原IMPLEMENT动作入口，架构检查及全部架构测试保留。原动作入口继续拒绝对完成任务重新实施。227项本地回归通过；后续完整本地结果保存在dist。六门配置与手动触发方式不变，本维护提交未触发远程CI。

V2-006 本地示例：运行 `.venv/bin/python -B demo_v2_006.py`，可以看到“东库客观事实 / 西库误信 / 观察后才知情 / 计划不改变事实”的完整 JSON 往返。范围与复现见[V2-006本地交付](plan/validation/execution/V2-006/LOCAL_IMPLEMENTATION.md)。

V2-007 本地示例：`.venv/bin/python -B demo_v2_007.py`；插叙、发生状态和读者承诺窗口见[V2-007本地实现](plan/validation/execution/V2-007/LOCAL_IMPLEMENTATION.md)。这是领域内存能力，尚非正文生产或Canon提交。

V2-008本地示例：`.venv/bin/python -B demo_v2_008.py`；四类事实变化、严格前提及纯预演见[本地实现](plan/validation/execution/V2-008/LOCAL_IMPLEMENTATION.md)。不包含Canon提交或正文生产。

V2-009：ADR-005/006及root-only持久化已完成[工程验收](plan/validation/execution/V2-009/closure-20261019/ACCEPTANCE_SUMMARY.md)，绑定3d12f20/run39256589017；P2最新工程汇总见下文，V2-010已按16259d1/run42632232950完成工程验收。

V2-010本地交付：[授权章节提交协议](plan/validation/execution/V2-010/LOCAL_IMPLEMENTATION.md)。隔离测试Permit与正式生产放行分离；未据此关闭V2-011/012或P2。

V2-010已完成[工程验收](plan/validation/execution/V2-010/closure-20261109/ACCEPTANCE_SUMMARY.md)，绑定16259d1/run42632232950，1460项0skip；V2-012及P2结项见下方最新验收。

V2-011已完成[工程验收](plan/validation/execution/V2-011/closure-20261110/ACCEPTANCE_SUMMARY.md)，绑定b716e7c/run42734728628，1474项0skip；现有提交服务复用不变，新增14项真实PG竞争/恢复控制。V2-012/P2结项见下方最新验收；小说生成产品闭环仍未完成。

V2-012已完成[工程验收](plan/validation/execution/V2-012/closure-20261110/ACCEPTANCE_SUMMARY.md)，绑定416c451/run42774996789，1525项0skip；[P2/M2汇总](plan/validation/execution/P2/closure-20261110/ACCEPTANCE_SUMMARY.md)VERIFIED。当前仅有限事实Canon和隔离TEST Permit，不代表生产备份或小说生成/阅读质量已完成。V2-013验收见下方最新记录，P3仍未完成。

V2-013已完成[工程验收](plan/validation/execution/V2-013/closure-20261113/ACCEPTANCE_SUMMARY.md)，绑定b9cb604/run43424270308，1588项0skip（新63项题材契约属于UNIT子集）。ADR007已接受，两Anchor精确加载/项目快照/无匹配不改题材已验证；下一任务V2-014，P3及自动写作/阅读质量/外部备份仍未完成。
