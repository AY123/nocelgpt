# V2-003 架构检查分工复核

日期：2026-09-24（Asia/Shanghai）。范围：`plan/scripts/architecture_checks.py`、`scripts/check_architecture.py`、`tests/architecture/test_dependency_boundaries.py` 与 AT-V2-003-01～03；另外核对现行 `machine/ci-gates.yaml` 的六个 P0 门禁。未修改被审代码或机器门禁。

复核角色是 V2-003 架构子代理，亦为该架构检查器的实施者；主代理负责整体验证与汇总。本记录属于同一 AI 协作、同一工作区和共享权限下的实施者自查与分工复核，不是独立审核、独立权限验证或可信 CI 认证。

## 结论和真实运行

在明确的 P0 静态检查范围内，前三项场景具备真实生产发现与隔离正反夹具证据，本次未发现阻断性不符合项。不是空扫描证据，也没有创建 P1/P2 业务实现。真实 CI、P2 Canon 运行写权限和任务最终验收仍未验证；本结论不能据此关闭 V2-003 或 P0。

- `.venv/bin/python -B -m pytest -q tests/architecture/test_dependency_boundaries.py --junitxml=dist/validation/v2003-architecture-review-20260924/pytest.xml`：退出码 0，**71 passed in 1.02s**，没有 72 项。JUnit 保存在上述独立输出目录。
- `.venv/bin/python -B scripts/check_architecture.py --output dist/validation/v2003-architecture-review-20260924/architecture.json`：退出码 0，PASS，真实生产文件数 1、模块数 1、findings 数 0，`bootstrap_only: true`。这个结果仅覆盖现有 `src/anovel/__init__.py`。
- Python 夹具由 pytest 在临时目录生成，仅供 AST 解析；测试 `test_synthetic_source_is_parsed_without_execution` 用带写入语句和异常的源码确认不会执行候选模块。生产报告和 synthetic 夹具各自标明用途。

## 场景与测试映射

| 场景 | 正例 | 反例与附加覆盖 | 适用边界 |
|---|---|---|---|
| AT-V2-003-01：合法依赖图通过且领域导入 Provider 的负例失败 | `test_legal_domain_ports_and_workflow_public_service`；`test_literal_relative_dynamic_import_is_resolved` | `test_domain_implementation_dependencies_fail`；`test_unknown_domain_third_party_needs_review`；`test_indirect_provider_and_internal_workflow_dependency_fail`；`test_literal_dynamic_import_and_aliases_follow_same_policy`；`test_package_initializers_are_edges_even_for_dotted_import` | 检查直接与内部传递 import，覆盖 Provider、数据库、Web、workflow 类实现；相对导入、别名、包初始化与已识别字面量动态导入进入同一图。领域层仅允许标准库、领域内部及已选择的 Pydantic 边界依赖；未知第三方不默认放行。 |
| AT-V2-003-02：非授权模块访问 Canon 写入口的夹具失败 | 合法例中 Workflow 经 `canon.commit_service` 使用公开提交服务，服务内部依赖 `canon.repository`；不会把合法服务封装误判为 Workflow 直接仓储访问 | `test_unauthorized_canon_imports_fail`；`test_workflow_may_not_access_internal_repository`；`test_package_reexport_and_intermediate_alias_do_not_hide_canon`；`test_literal_dynamic_fromlist_cannot_hide_canon_repository` | 对 repository 内部路径与 commit_service 公开入口分别授权；Writer/quality/repair/context/reference 夹具不得获取写入口。这里只证明静态 import 策略，不证明注入对象、运行授权、SQL 或 DB 角色权限。 |
| AT-V2-003-03：新增模块纳入扫描而非空扫描报成功 | `test_real_production_tree_is_discovered_separately_from_synthetic_fixtures` 对照真实 `src/anovel/**/*.py` 文件集合；`test_new_nested_namespace_module_is_always_scanned` 在无子目录 `__init__.py` 的嵌套模块上先合法通过、再加入违规导入并失败 | `test_empty_discovery_and_scan_narrowing_fail`；`test_syntax_and_relative_root_escape_fail`；`test_symlink_sources_and_directories_fail`；`test_ambiguous_module_file_and_package_fail` | 递归发现不按业务模块白名单缩窄；固定完整 `src/anovel`，拒绝空扫描、非法语法、路径/符号链接别名及歧义模块。实际业务模块缺失如实记为骨架，而不提前创建空业务目录。 |

补充规范覆盖：`test_historical_and_nonproduction_imports_fail` 拒绝 archive/plan/tests/scripts 生产导入；`test_unresolved_dynamic_loading_fails_explicitly` 对已识别但不可静态判定的加载器、通配导入和 importer 状态修改失败。CLI 的成功、失败退出码、独立输出、拒绝覆盖 plan 或已有报告由两个 CLI 测试覆盖。

以上映射对应 `02_ARCHITECTURE_BASELINE.md` 的领域与模块边界、`03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md` 的唯一提交路径、`07_PLATFORM_SECURITY_AND_DELIVERY.md` 的生产/归档隔离和硬门禁，以及 `PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md` 对合法/非法夹具及非空发现的要求。这里没有实现 Narrative、Canon 事务、Provider 或质量业务。

## 六个 P0 门禁核对

`plan/machine/ci-gates.yaml` 当前字节与开工提交 `c6f26c6188f0b6ad82ce73bf04024d1eab96e1cf`、冻结范围提交 `518c8a6646acbd236a38436388d05da06ac19abd` 及复核时 HEAD 中的该文件完全一致。三方和工作树 SHA-256 均为 `5a51a70c8f1a746cbbd14a925f92ebc15c24089455552a292a0e057688378210`，未发生删改或推迟。

六项为 STATIC、UNIT、SCHEMA_CONTRACT、ARCH_FITNESS、SECRET_DEPENDENCY、POSTGRES_ENV；各项均保持 `activation_phase: P0`、`mode: every_change`、`allow_failure: false`，checks 集合保持原样。机器记录仍为 `NOT_IMPLEMENTED`、空 `evidence_refs`，没有伪装成远端 CI 已通过。

检查器要求这六个 gate 存在，拒绝重复/非法阶段、后移 P0 gate、`allow_failure` 放宽以及禁用适用 gate 的参数；阶段参数固定 P0，不接受通过后移阶段绕过扫描。未来 gate 返回 NOT_APPLICABLE 并说明理由。对应测试为 `test_required_p0_gates_cannot_be_disabled_or_deferred`、`test_weakened_or_malformed_gate_policy_fails`、`test_future_gates_are_reported_as_not_applicable` 和 `test_cli_failed_hard_gate_returns_nonzero`。

检查器的门禁检查不执行六项 CI 工作，也不独自验证所有机器政策字段的含义；检查命令/触发模式的实际删改仍由既有计划验证器与 V2-003 差异防弱化检查共同处理。本次核对的六个 gate 没有变化。

## 实现选择与局限

- Canon Python 路径取自 V2-009 的 `canon/repository.py` 和 V2-010 的 `canon/commit_service.py` 目标产物。当前调用者允许集合是 P0 静态规则选择，不声称现行规范已经冻结未来所有具体 Python import；P2/P10 接口落地时须经适用决策和差异审查更新，不能用现有静态规则阻止 Genesis 最终走同一服务。
- 标准库/Pydantic 允许集合、领域只向领域端口依赖及已知外部实现分类是有意保守的静态约束。别名按跨作用域集合合并，可能需要对未来合格代码做有依据的规则修订。
- 支持普通/相对导入、别名、内部 re-export、包初始化、已识别的字面量动态导入与 `__import__` fromlist。已识别但目标未知的 loader 失败；不承诺证明任意 Python 反射、外部进程、能力注入或生成代码安全。
- 扫描 Python 源码且不导入候选模块；不替代安装包分发核验、真实运行集成测试或数据库权限检查。真实生产当前只有骨架，能力边界的负例来自明确的临时 synthetic 源码。
- CLI 可被 V2-004 消费，但当前没有通过本记录证明“检查命令已在真实 CI 执行”。共享写权限操作者仍可能修改工具或来源；可信远端来源和受保护权限继续由 V2-004 核验。

复核时实现文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `plan/scripts/architecture_checks.py` | `8d58f25c207f7e09873a567c90cd2e7d392cb475ece2727dda52bfb3ec9d3960` |
| `scripts/check_architecture.py` | `c4cb7cfbc1f108244f5cf33a0dcf0ca806a70d5edda1e150a77bb4a47b5aaffb` |
| `tests/architecture/test_dependency_boundaries.py` | `80803970e90601cc64db3259014a0f22761b0450d196468518dca9de87cc84e0` |
