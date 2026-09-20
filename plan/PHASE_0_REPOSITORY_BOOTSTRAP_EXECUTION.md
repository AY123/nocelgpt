# P0 Repository Bootstrap 执行方案

范围：仅 V2-001～004。状态：READY_TO_START，尚未实施/验收。现行规范入口：[README](README.md)。

## 1. 目标与排除项

交付可重复构建的 V2 仓库、唯一规范入口、架构适应性检查、安全/依赖 CI、PostgreSQL 测试环境及当前提交绿色证据。

不实现 Narrative 实体、Canon 事务业务、Genesis Bootstrap 业务、Provider UNKNOWN 运行逻辑、Writer、Q0–Q3 或认证 runner。允许为架构检查建立无业务副作用的测试夹具。

## 2. V2-001 Repository bootstrap

输入：本包架构、平台规范；当前仓库已有文档/Git，不重新初始化或删除历史。

工作：选定并记录实际 Python 补丁、PostgreSQL 镜像版本/摘要、uv 与工具版本；建立 `src/anovel` 可安装骨架、pyproject、唯一锁文件、最小测试、compose 测试 DB、操作 README 和本地配置示例。保留现有资料。

验收：干净环境锁定安装成功；最小包/测试启动；隔离 PostgreSQL 可启动、连接和清理；缺配置有明确失败；不得包含真实凭证。运行环境决定写 ADR-001。

产物目标：`pyproject.toml`、`uv.lock`、`.python-version`、`src/anovel/__init__.py`、`compose.yaml`、`README.md`、`tests/integration/test_postgres_environment.py`。

## 3. V2-002 Normative documentation index

输入：本包及来源登记。工作：接入资料验证器、确定现行 specs 注册机制、补充实际负责人、把任务关闭/阶段 Gate 检查接入工程命令；根 README 明确指向 plan。

验收：任务/阶段/里程碑唯一；archive 不作为自动实现输入；再生成视图无差异；错阶段/缺引用/无证据 CLOSED 被拒绝；P0 未验证时 P1 无法被正式放行。仅本包的存在不自动关闭该任务。

## 4. V2-003 Architecture fitness harness

工作：把合法/非法模块依赖夹具纳入真实测试。至少验证领域层不依赖 Provider/数据库实现、非授权模块不导入 Canon 写入口、生产开关不能禁用适用硬门禁、归档不被导入。规则记录启用阶段；Canon 运行写权限随 P2 落地。

验收：合法骨架通过；故意错误导入/旁路能力的负例失败；新增模块被扫描；检查命令在 CI 执行。空目录扫描零结果不能单独作为边界验证成功。

## 5. V2-004 Secret/dependency CI

工作：编写实际 `.gitlab-ci.yml`；接入静态、单元、资料/结构、架构、安全、依赖及 PostgreSQL 基础检查。锁文件/扫描配置进入版本管理；依赖漏洞例外遵守具体、限时、可追踪规则。

验收：适用 job 硬失败不能被吞掉；无害模拟 Secret/非法依赖/坏 Schema 负例能够阻断；DB job 真正连接 PostgreSQL；当前提交可追溯的 CI 结果与 artifact 可读取。远端凭证/runner 不可用则保持 IMPLEMENTED 或 BLOCKED 验证状态，不写 CI green。

## 6. 执行顺序与协作

先完成环境与结构，再接入资料/架构/安全测试，最后验证 CI 和 Gate。四任务允许按依赖准备并行工作，不改变最终全部通过要求。本方案不要求新建线程或 Agent。

## 7. P0 退出清单

- 四任务均有代码/配置、测试、CI、验收引用，状态经核验后 CLOSED。
- 当前使用的规范没有未裁决冲突；已知未来缺陷有正确任务和最晚时点。
- 安装/检查/DB 命令可由干净环境复现，依赖已锁定。
- 适用硬门禁能通过，也能阻断人工注入的失败。
- G-P0 和 M0 证据绑定当前提交；只有此后才允许 V2-005。

验收记录使用 [模板](templates/TASK_ACCEPTANCE_RECORD.yaml)。本资料整理阶段没有运行这些工程任务，所有勾选项保持未完成。
