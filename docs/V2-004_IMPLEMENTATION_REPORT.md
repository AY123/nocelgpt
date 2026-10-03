# V2-004 实施与恢复记录

记录日期：2026-10-03（Asia/Shanghai）；分支：`dev_gpt`；Plan：1.3.0。**V2-004 仍为 IN_PROGRESS，P0 仍为 NOT_VERIFIED。** 本文记录当前实现、本地真实运行、失败及恢复条件，不作为任务验收或远端 CI 绿色证据。最终任务、阶段及证据状态以 `plan/machine/` 为准。

实施和验证由同一操作者及共享工作区的协作 Agent 承担，未建立独立人员审核或独立权限保障。`dev_cc` 仅用于比较方案，其历史 PASS、保护配置和完成状态未继承到 `dev_gpt`。

## 交付范围与六个门禁

新增 `.gitlab-ci.yml`、`security-policy.yaml`、`scripts/ci/`、`tests/contract/test_delivery_gates.py` 和 `tests/integration/test_postgres_ci_service.py`；工具加入 `pyproject.toml` 并由 `uv.lock` 固定实际解析结果。运行环境沿用 ADR-001：Python 3.12.14、uv/uv_build 0.12.17、PostgreSQL 17.11-bookworm 及其既定镜像 SHA。新增工具固定为 ruff 0.16.9、mypy 1.20.2、pip-audit 2.10.1、Gitleaks 8.21.2；PyYAML 类型存根的实际版本由锁文件绑定。

六个适用 job 均显式 `allow_failure: false`，执行 `uv run --locked python -B scripts/ci/run_gate.py <job>`。MR、普通分支和 tag 的 workflow 明确登记；有 MR 的 push 抑制重复分支流水线。未来阶段门禁未由本次工作提前启用。

| Job / 门禁 | 实际命令及覆盖 |
|---|---|
| `static` / STATIC | 检查当前 CI 配置；对 `src/anovel`、新 CI 脚本执行 ruff 格式/lint 与严格 mypy；对两个新测试文件执行格式/lint；对现行 `src`、`scripts`、`plan/scripts`、`tests` 的 Python 在内存中编译。现有历史治理代码未被声称已整体迁移到严格类型和统一格式。 |
| `unit` / UNIT | 固定 scanner bootstrap 后执行现行 `tests/contract` 和仓库 bootstrap 集成测试；缺工具或测试错误仍为失败。 |
| `schema_contract` / SCHEMA_CONTRACT | 实际执行 `scripts/check_governance.py`，聚合现行资料、结构、治理、AI 执行与历史探针回归。 |
| `arch_fitness` / ARCH_FITNESS | 实际执行 V2-004 IMPLEMENT 入口、生产架构扫描和全部 `tests/architecture`；任务入口从执行包读取固定 scope/review 绑定，触发实际差异检查。夹具不代替生产树扫描。 |
| `secret_dependency` / SECRET_DEPENDENCY | 固定 scanner bootstrap 后执行真实 Gitleaks 工作树/完整 Git 历史扫描，以及锁定依赖和 build backend 的 pip-audit。任一部分失败，整个门禁失败。 |
| `postgres_env` / POSTGRES_ENV | 使用固定 PostgreSQL service，真实连接、精确核对 `170011`、数据库名、两个独立连接和空 public schema；本地可复用原 Docker 隔离生命周期测试。缺 DSN 不 skip。 |

`run_gate.py` 用无 shell 的真实子进程运行逐条命令，保留 argv、退出码、stdout/stderr 原始字节及 hash；非零、无法启动和超时停止后续命令。receipt 同时记录 checkout、driver hash、锁文件 hash 和运行身份，输出到新 `dist/` 目录，不覆盖前次产物。GitLab 环境变量仅登记为未核验来源；receipt 自己不能证明远端执行。

原子进程使用 `os.environ.copy()`，仓库 bootstrap 测试的 fixture 又复制该环境；pytest 失败时的 fixture repr 可能把父进程中的 Provider 密钥或 CI token 写入原始日志。已改为固定最小 allowlist：保留 PATH/HOME/临时目录/locale、必要 uv 路径配置、本地 Docker 连接元数据、明确列出的非秘密 GitLab 项目/提交/job/pipeline/branch 元数据，以及专用于隔离测试库的 `ANOVELOS_TEST_DSN`；固定 Python 不写 bytecode 和 ruff/mypy 的 `dist/cache` 路径。Provider/API token、`CI_JOB_TOKEN`、`ANOVELOS_GITLAB_*`、PIP/uv 凭证配置、Docker registry auth 和其他未登记变量均不进入门禁子进程；含 userinfo、query、fragment 或格式异常的 `DOCKER_HOST` 也不透传。代理 URL 常含认证信息，HTTP/HTTPS/ALL/NO_PROXY 及小写形式均不自动继承，下载因此需要直接公共网络。此修复只防止父环境经测试 fixture 进入日志，不保证测试自身读取或输出的任何内容都无秘密；旧失败记录不因修复而被重写。

配置检查拒绝必需 job 删除、允许失败、命令替换、触发排除、错误镜像和浅历史；未使用的 include/template/inheritance 及 job 覆盖进入拒绝范围，避免只检查未展开 YAML 而漏掉继承的 `when: never`。同仓库实现者仍能修改此检查器，远端反删除保障尚未建立。

## Scanner 来源修正与安全运行

初版缓存复用错误地信任本地 sidecar 的 `binary_sha256`：任意伪 scanner 与 sidecar 一起改写，保留已知 archive 摘要和版本字符串，就可能通过复用检查。该旁路已经修复，`bootstrap_scanners.py` 和 `check_security.py` 共用验证过程：从当前平台固定常量选择官方 archive，重新计算完整 archive SHA，只读唯一普通文件 `gitleaks`，再与当前 binary 逐字比较。sidecar 提供定位和版本信息，不授予 binary 信任。

新 bootstrap 保留完整 archive。旧缓存缺 archive 时，`scanner_binary` 默认拒绝；显式 `--reuse-verified` 可从固定官方 URL 补取 archive，先核对固定摘要及原 binary，再只创建缺失 archive，保留原 binary 和 receipt，不覆盖未知内容。固定摘要来自 [Gitleaks v8.21.2 官方发布](https://github.com/gitleaks/gitleaks/releases/tag/v8.21.2)。

七项隔离控制已通过：合法 archive/binary、伪 binary 与伪 sidecar、伪 archive、缺 archive 拒绝、显式迁移通过、迁移不能替换伪 binary、新安装保留 archive。控制使用合成 archive pin，证明比较逻辑，不声称合成内容是官方 scanner。原始结果为 `/tmp/anovel-scanner-final-review.xml`；对应修复代码的严格 mypy 和 ruff 检查通过。

Secret 扫描使用真实固定 Gitleaks，对 Git 跟踪文件的实际工作树副本和完整 `--all --full-history --root` 历史分别扫描；浅 clone、partial clone、缺对象和空扫描拒绝。候选 `.gitleaks.toml`、`.gitleaksignore`、inline allow 注释和 Gitleaks 环境配置不能扩大忽略范围。报告只保留规则、文件/行/commit、数量及 hash，不复制密钥值、Match 或 scanner 原始日志。实际扫描方式遵循 [Gitleaks 官方使用说明](https://github.com/gitleaks/gitleaks)。

依赖检查遍历全部锁定 registry 包及精确固定的 PEP 517 build backend，不只扫描当下平台安装的子集。非支持来源、非精确 build pin、缺 hash、跳过包、缺覆盖和扫描异常均失败；例外须明确包、版本、漏洞、责任、理由及有效期。实际审计曾覆盖 **51 个包，0 漏洞，退出 0**；对应原始报告在 `dist/validation/v2004-security-online/`。单独的 `flask==0.5` 隔离负例通过真实在线 pip-audit 得到非零退出和漏洞结果，没有安装该易受攻击依赖或加入项目锁文件。

## 已运行结果与尚未解决的失败

下表均为本地真实运行，结果只适用于各自记录的源码/锁文件及运行上下文。`/tmp` 和忽略的 `dist` 是运行产物，后续正式证据需绑定准确提交和 hash；它们不是当前提交可信 CI。

| 运行 | 实际结果与证据 |
|---|---|
| PostgreSQL lifecycle 和新增 service 测试 | **11 passed，0 skipped**，实际 Docker 启动、连接及清理；`/tmp/anovel-v2004-postgres.xml`。 |
| 第一轮合入 delivery 控制 | **60 passed，0 skipped**；`/tmp/anovel-v2004-delivery-merged.xml`。后续 scanner 七控制及配置补充需保留新的完整复测记录，不把这一轮数字当最终总数。 |
| 远端来源核验控制 | **33 passed**；`/tmp/anovel-source-unit-3.xml`。使用合成 API 和临时本地 Git checkout，覆盖来源逻辑及固定 pin，未调用真实远端流水线。 |
| Scanner 来源修复控制 | **7 passed**；`/tmp/anovel-scanner-final-review.xml`。合成 pin 不替代真实官方 archive 或远端权限证据。 |
| 子进程环境控制 | **10 passed**；`/tmp/anovel-delivery-environment-final.xml`。真实子进程检查密钥及代理变量拒绝、实际 uv 可执行、CI 元数据/临时 PostgreSQL DSN 传递、本地 Docker 元数据保留及危险 endpoint 拒绝；严格 mypy/ruff 通过。仅检查 DSN 传递的控制不声称连接了 PostgreSQL，真实数据库仍由上面的 service/lifecycle 测试证明。 |
| UNIT 命令入口首次运行 | **115 passed，3 errors，退出 1 / receipt FAIL**。三个 bootstrap 测试因本地 PATH 缺 uv 未完成；原始失败在 `dist/validation/v2004-unit-final/`，receipt 绑定当次 `f4838f0f2ec7b20d016fce9fb28632321a8c022e`。补齐 PATH 后重跑待主操作者更新，不把错误解释为跳过或 PASS。 |
| 项目 Secret/依赖实际扫描 | 依赖 51 包通过；Secret 存在未处置发现，**整体仍 FAIL**。报告中的安全失败不被成功测试覆盖。 |

当前静态分类为 **36 项 FALSE_POSITIVE、6 项 POSSIBLE_EXPOSURE、1 项 TRUNCATED_CREDENTIAL_REFERENCE**。六处可能暴露对应三个不同完整形态值，另有一个截断引用；有效性、撤销/轮换和仍可使用情况均未知。本次没有试用凭证、撤销凭证、改写 Git 历史或加入忽略规则，原 Secret FAIL 保留。脱敏分类原始记录在 `/tmp/anovel-secret-triage.json`，分类只帮助后续处置，不自动解除门禁。疑似暴露需按现行事故规则核实及记录；删除文本本身不证明已撤销。

## 真实来源与权限验收边界

准备期只读远端观察记录在 `plan/validation/execution/V2-004/preparation/remote-observation.json`：项目 `86656946 / ayitnovel/ainovelos` 的 `dev_gpt` 当时为 `882d0cdf833464dd6a5ebfac3a542204c32cd325`，**pipeline 数为 0、branch 未受保护**；项目启用了 `only_allow_merge_if_pipeline_succeeds`。这是观察时点事实，不证明之后的提交运行过，也不证明普通实施身份的越权请求已被拒绝。当前策略 `trusted_execution.status=NOT_ENROLLED`，runner/config/ref 尚未登记。

`verify_remote.py` 的 CLI 只接受环境中的 `ANOVELOS_GITLAB_TOKEN`，使用固定 GitLab HTTPS GET；不接受本地 CI JSON 放行输入，不把 token 写入输出，不跟随 redirect。它以完整固定 Git policy pin读取策略，核对固定项目、准确 SHA/ref/pipeline、全部六个 job、最新 retry 和原失败历史、runner、实际 trace、精确 job ID 下载的 receipt/log/artifact 字节及 hash。下载后再查 pipeline/job/branch；中途状态变化或 HEAD 漂移保持未核验。按 job ID 查询避免把“分支最近成功产物”误绑定到本次提交；API 依据见 [GitLab Jobs API](https://docs.gitlab.com/api/jobs/) 与 [Job Artifacts API](https://docs.gitlab.com/api/job_artifacts/)。

核验分为三个层次：`source_status` 说明在线来源和执行记录是否匹配；`trust_status` 仅说明固定配置与实际保护元数据是否匹配；`permission_status=UNKNOWN` 保留尚未执行的真实权限正反例。即使来源通过和保护元数据匹配，整体仍 `UNVERIFIED / exit 2`，`acceptance_eligible=false`。失败、取消、漏 job、旧 SHA、伪 receipt、错误 hash 拒绝；无权限、缺 artifact 或被拒绝的重定向保持未核验。合成 API 正例永不升级为真实 CI 或 AT-V2-004-07/08 验收。

根 `.gitlab-ci.yml` 和 driver 位于候选同一仓库，实施身份可同时修改 pipeline、测试和检查器。真实 GitLab job/receipt 只能核对执行来源，不能自己证明必需检查不可删、例外得到适用批准或实施者无权修改保护。受保护分支和受保护 runner 需要实际设置及有效权限核验，并保留普通凭证被拒绝与授权操作可用的正反例；多个共享凭证的 Agent 不提供此边界。[GitLab 受保护分支](https://docs.gitlab.com/user/project/repository/branches/protected/) 和 [runner 保护说明](https://docs.gitlab.com/ci/runners/configure_runners/#prevent-runners-from-revealing-sensitive-information)描述的是平台能力，不是本项目已生效证明。

## Scope、复现与恢复条件

固定 scope 提交为 `4f813a219254f24be851419a172bc60d74f255a1`，分别保存 `scope-baseline-local-final.json` 与 `scope-baseline-ci-final.json`。local scope 保留用户已有 `审核报告.txt`、本地工具配置和缓存归属；报告未被删除或归为 AI 完成。缓存漂移的原因在 `preparation/tool-cache-attribution.json`，后续工具使用 `dist/cache` 或 `--no-cache`，没有删用户文件制造干净工作区。

CI scope 专供已提交的干净 checkout，`pre_existing` 为空；它不要求远端伪造本地用户脏文件，也不能用于删除或恢复本地文件。计划切换到单独的 clean active packet 时，须先保留 local packet 和恢复上下文，再绑定固定 CI scope 与相应精确 review pin；写本文时该切换仍待主操作者完成。两个固定 scope 均不构成远端受信来源。

从仓库根执行；输出路径必须是新目录，下面示例目录不可覆盖旧运行：

```sh
export PATH="$PWD/dist/tools/uv-bootstrap/bin:$PATH"
export UV_CACHE_DIR="$PWD/dist/cache/uv"
uv --version
uv sync --locked
uv run --locked python -B scripts/ci/bootstrap_scanners.py --output-dir dist/tools/gitleaks-8.21.2 --reuse-verified
uv run --locked python -B scripts/ci/run_gate.py static --output-dir dist/validation/v2004-static-recovery
uv run --locked python -B scripts/ci/run_gate.py unit --output-dir dist/validation/v2004-unit-recovery
uv run --locked python -B scripts/ci/run_gate.py schema_contract --output-dir dist/validation/v2004-schema-recovery
uv run --locked python -B scripts/ci/run_gate.py arch_fitness --output-dir dist/validation/v2004-arch-recovery
uv run --locked python -B scripts/ci/run_gate.py secret_dependency --output-dir dist/validation/v2004-security-recovery
uv run --locked python -B scripts/ci/run_gate.py postgres_env --output-dir dist/validation/v2004-postgres-recovery
```

arch_fitness 在实际差异未复核或 packet 输入失效时应失败；Secret 在当前发现未处置时应失败。运行失败即保存对应记录和恢复条件，不能使用旧 PASS、改 action 名称或换空 scope 放行。

真实 pipeline 存在后，来源命令形式如下；完整 SHA、pipeline ID 和 policy pin 需来自当次已核对记录，token 由受控环境注入：

```sh
uv run --locked python -B scripts/ci/verify_remote.py \
  --revision <完整被测提交SHA> --pipeline-id <真实pipeline_ID> --ref dev_gpt \
  --policy-revision <已核对的完整policy_Git_pin> \
  --output dist/validation/v2004-online-source-recovery.json
```

恢复顺序：核对 checkout、用户文件身份、输入 hash、local/CI packet 消费条件和精确 scope/review；补齐 uv PATH 并记录 UNIT 真正重跑；保留并处置 Secret 发现；在干净提交运行真实 CI并读取当次原始产物；最后核验保护配置及 AT-07/08 的真实权限和反删除正反例。当前缺少真实 CI、已生效受信执行和最终验收，不能转 VERIFIED/CLOSED，不能据本文开启 P1。
