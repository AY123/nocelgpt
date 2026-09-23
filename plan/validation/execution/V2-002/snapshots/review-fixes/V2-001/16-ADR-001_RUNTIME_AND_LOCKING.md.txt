# ADR-001 — 精确运行环境与锁定工具

状态：ACCEPTED。关联任务：V2-001。责任角色：repository-maintainer。决定人：Codex 主实施 AI，依据用户明确的 V2-001 实施授权。日期：2026-09-22。首次适用：Plan v1.3.0。没有独立人类审核或远端 CI 认证。

## 问题与依据

初始 checkout 的系统 Python 为 3.9.6，没有 uv 或 Python 3.12；Docker 客户端存在但 daemon 未启动。不能把该环境当作已满足工程要求。PREPARE 已真实启动 Docker、安装固定 uv/Python，并拉取和检查 PostgreSQL 镜像。原始记录在 `validation/execution/V2-001/raw/`；正式 decision record 在同一执行目录中引用本决定的不可变源码 revision 与 artifact hash。

## 决定

| 项目 | 唯一基线 |
|---|---|
| Python | CPython **3.12.14**；`.python-version` 写精确补丁；项目 `requires-python = "==3.12.14"`，升级必须明确改动、重新锁定和验证 |
| uv | **0.12.17**；`tool.uv.required-version = "==0.12.17"`，不得由任意最新版隐式代替 |
| 构建 | `uv_build==0.12.17`，`src/anovel` 包；没有其他运行时包或业务模块 |
| PostgreSQL | `postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652` |
| 依赖 | 唯一 `uv.lock`，PyPI 官方索引；运行/开发环境使用 `uv sync --locked`。本任务运行包无依赖；pytest、PyYAML、jsonschema、SQLAlchemy 2.x、psycopg 3 binary 是当前测试和规划脚本的真实消费者 |
| 测试配置 | 必要测试数据库配置显式提供；缺失、空值或非 PostgreSQL 驱动明确失败，无自动 SQLite 回退 |

镜像 digest 是拉取返回的仓库内容身份，不使用浮动 `latest` 或仅主版本 tag。当前实测平台是 macOS arm64 / Docker Linux arm64；其他 runner 平台的实际运行仍须 V2-004 验证，不能从本地成功推定 Linux amd64 已通过。Docker Engine 29.4.0、Compose 5.1.2 为本轮实测工具；本地及未来 CI 使用支持 `up --wait` 的 Compose v2+，记录各自工具版本并运行同一验收。宿主 Docker 版本不是虚构的跨平台字节相同保证。

本地与 CI 必须使用相同 Python 补丁、uv、锁文件和 PostgreSQL image identity。CI 不在本任务实现。锁文件必须提交，不接受普通 sync 自动改锁后宣称重复安装成立；测试同时验证 lock 未变化。首次明确 `uv lock` 可解析兼容依赖，之后以锁文件精确版本和分发 hash 为准。升级时同时审查 pyproject、lock 和环境决定，并重复真实集成测试。构建 backend 单独精确钉住；uv 的匹配内置 backend 不额外引入未锁定构建依赖。

Pydantic v2 / Alembic 在出现实际 Schema / migration 消费者时再加入；此决定不否定现行技术方向。本轮不加入 Web、任务队列、缓存、Agent、模型或向量库框架。

## PostgreSQL 隔离与清理

每次自动测试创建随机且可追溯的 Compose project name；只操作该 project 的容器、网络和卷。端口绑定 `127.0.0.1`，由 Docker 分配空闲端口，不占用固定 5432；PGDATA 使用容器 tmpfs。数据库、用户名和密码均为测试专用的显式一次性配置，不读取生产 DSN 或项目 `.env`。官方镜像初始化账户的 superuser 权限仅用于这个短生命周期测试容器，不是未来生产权限设计。

启动、健康检查、SQLAlchemy `postgresql+psycopg` 连接及 `SELECT`、释放连接池、`down --volumes`、残留资源核对组成一个生命周期。清理在启动操作之前即纳入 try/finally；启动失败也必须尝试清理并显式报告清理失败。Docker 不可用使测试失败，不 skip 或 Mock 代替。SIGKILL/宿主掉电无法保证 finally，报告和 README 保留 project name 供精确恢复清理，不运行全局 prune。

本轮不建业务表。未来事务/CAS/fencing/concurrency 测试仍使用真实 PostgreSQL、独立连接和真实提交，不把整个测试套件包进共享外层 rollback，也不用 SQLite 验证关键语义。认证语义测试属后续任务。

## 取舍与验证

不选系统 Python 3.9、浮动版本、未钉住镜像、固定共享测试库或 SQLite：它们不能满足当前约束。精确补丁锁定会要求显式安全更新，接受这一维护成本。容器使用临时数据，不能当作持久化/备份能力。本决定仅证明选择已作出，工程能力须由随后锁定安装、包导入、干净环境与真实 PostgreSQL 测试证明。

正式实施前登记 ACCEPTED 并通过现有 packet/ADR 校验。V2-001 最终仍须真实 CI 与验收才能关闭；本地结果不足以 VERIFIED/CLOSED。未替代其他 ADR。

## 官方依据（2026-09-22 查询）

- [Python 3.12.14 发布](https://www.python.org/downloads/release/python-31214/)。
- [uv 0.12.17 分发](https://pypi.org/project/uv/0.12.17/) 与 [uv_build 0.12.17](https://pypi.org/project/uv-build/0.12.17/)。
- [uv Python 版本选择](https://docs.astral.sh/uv/concepts/python-versions/)、[required-version](https://docs.astral.sh/uv/reference/settings/#required-version)、[锁定与同步](https://docs.astral.sh/uv/concepts/projects/sync/)。
- [PostgreSQL 支持周期](https://www.postgresql.org/support/versioning/)、[官方容器](https://hub.docker.com/_/postgres)、[Compose 镜像语法](https://docs.docker.com/reference/compose-file/services/#image)。
- [SQLAlchemy psycopg 方言](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)、[pytest 安全清理](https://docs.pytest.org/en/stable/how-to/fixtures.html#safe-teardowns)。
