# 开工前资料清理记录

日期：2026-09-21。授权：用户要求“删除过时无用文件，为马上搭建项目做准备”。范围为工作区资料整理，未创建业务骨架、修改工具权限、提交 Git 或关闭 P0 任务。

逐文件源路径、字节数、SHA-256、保留位置及恢复依据见 [repository-layout-migration.json](repository-layout-migration.json)。清理前核对来源和保留副本，全部一致后才删除根副本。

## 处理结果

- 224 份重复资料删除根副本，原始字节仍保留在 `plan/archive/`：包含 gptdoc、ccdoc、历史审核/提取、五份矩阵、最新评估输入以及 `.claude/convergence/`。
- 21 份独有资料先补充归档再移除根副本：11 份前期原件（10 个 Word 文件与清单）、3 份历史脚本/清单、7 份运行日志。日志保存为 `.log.txt`，内容不变；全部进入来源登记。
- 7 个根目录过时 ZIP/校验文件与当前 Git HEAD 逐字节核对后删除，可以从记录的 Git revision/path 恢复。
- 删除根 `.DS_Store`；清除旧 v1.2.1 分发产物，只保留当前规划分发包。
- `.git/`、`.gitignore`、本地工具权限配置、现行 plan 及用户已有规划改动保留。没有执行旧生成脚本，也没有删除唯一原件。

## 当前目录职责

| 位置 | 职责 |
|---|---|
| README.md / AGENTS.md | 正式入口及执行规则 |
| plan/ | 当前规划、机器清单、验证器及历史 archive |
| docs/ | 实际资料迁移与后续工程说明 |
| .claude/ | 保留本地工具配置；旧 convergence 根副本已删除 |
| dist/planning/ | 可再生成的当前下载包，不作为源码或完成证据 |

历史档案中的旧路径和绝对路径按原文保留，不能直接运行。当前规范引用 archive；`source-register.origin` 是迁移前位置，`archive_path` 才是现存副本。

## 恢复与后续

重复/迁移文件按 JSON 的 `retained_path` 查找。旧根 ZIP 可用 Git 导出：`git show <recovery_git_revision>:<recovery_git_path> > <目标文件>`，字段取自该条记录；恢复后核对 SHA-256。不要用整个工作区 reset 来恢复一个文件，避免覆盖尚未提交的规划改动。

此清单仅证明资料整理完成。V2-001 仍缺实际仓库骨架、依赖锁定、干净环境安装和 PostgreSQL 测试；V2-002～004 仍需真实工程接入和 CI。后续代码出现后，还须在架构检查中验证 archive 不被构建/导入，不能由本次目录整理推定已通过。

以上是 2026-09-21 清理时点的状态；后续实施更新见下节，不改写历史清理证据。

## 清理后验证

256 个原路径已确认移除；247 份登记快照的大小与 SHA-256 全部匹配，新归档文件不会被 Git ignore 漏掉。资料校验、32 项自测、39 项治理回归和 13 项旧探针/对照全部通过。工具配置仍保留，任务状态未改变。

## V2-001 工程复核（2026-09-23）

新增 `src/anovel`、pyproject / uv.lock / .python-version、Compose、测试与只读数据库探针。未新增空业务目录、migrations、Provider 或 CI 文件；没有删除/重命名原资料。目录职责新增：`src/` 是唯一可安装包入口，`tests/` 是当前真实验收，`scripts/check_postgres.py` 是无迁移探针；`dist/tools`、`dist/cache` 与 `.venv` 为忽略的本地环境产物。

`test_historical_materials_preserved` 实际核对清单中的 245 份保留文件及来源登记全部 247 份快照的 bytes/hash，包含隐藏 `.claude/convergence` 历史与独有原件。原 `.claude/settings.local.json` 保持原地，本轮没有编辑或分发其内容；现场存在性/hash 记在 V2-001 `raw/resume-state.json`，不会要求其他干净 checkout 带上个人配置。根 README / AGENTS 指向现行 plan。

真实构建的 wheel 与 sdist 已检查清单：只包含声明的 `anovel` 包及必要元数据，不包含 plan/archive、工具配置、测试或运行证据。wheel 在独立虚拟环境和源码目录之外成功导入。完整架构适应性扫描仍属于 V2-003，不能以包清单检查替代。

初次工程结果见 [仓库测试原始输出](../plan/validation/execution/V2-001/raw/020_bootstrap_pytest.json) 和 [数据库测试原始输出](../plan/validation/execution/V2-001/raw/021_postgres_pytest.json)。最终 revision 与后续运行从 [正式执行包](../plan/validation/execution/V2-001/execution-packet.yaml) 追踪。V2-001 只能处于 IMPLEMENTED；本地结果不关闭 P0。
