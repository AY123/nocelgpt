# V2-005 实施交接（整改后）

日期：2026-10-18。任务：核心实体 ID 与别名解析。

本轮已修复实际行为缺陷并完成本地验证。正式任务仍为 `IN_PROGRESS`；没有将本地测试等同于远程 CI、任务关闭或产品完成。

## 实际能力

- `src/anovel/domain/identity.py` 提供不可变的 `EntityId`、`Entity` 和内存 `EntityRegistry`。
- 每次查找必须明确项目。名字和别名不是主键；不同 ID 的同名实体不会被合并。
- 解析真实返回唯一匹配、未找到、歧义三种结果。共享名字或别名会实际触发 `AMBIGUOUS`。
- 改名保持 ID，按参数保留或移除旧名称；修复了旧名称已在 aliases 中时索引丢失的问题。
- 外部不能通过返回的实体或 aliases 改写注册表身份、项目或索引。
- `from_dict` / `to_dict` 与 `specs/schemas/entity.schema.json` 对照验证：非法类型、额外字段、重复别名、无项目作用域等被拒绝；输出顺序确定。

运行真实演示：

```bash
.venv/bin/python -B demo_v2_005.py
```

演示包含项目隔离、稳定 ID 改名、多别名、真实歧义、未找到和 JSON 往返；没有模型或数据库调用。

## 本地验证

| 验证 | 结果 | 边界 |
| --- | --- | --- |
| contract + architecture | 851 PASS，0 failure/error/skip | 工作树实现，不是精确代码提交的远程结果 |
| V2-005 领域测试 | 97 PASS | 上述 851 的子集 |
| 任务/交付门禁测试 | 256 PASS | 上述 851 的子集 |
| 历史 enrollment 测试 | 73 PASS，0 skip | 上述 851 的子集 |
| 架构测试 | 212 PASS | 上述 851 的子集，真实架构门禁又执行一次 |
| 正式本地 ARCH_FITNESS | PASS | 实际 V2-005 IMPLEMENT 入口 + 生产树扫描 + 212 架构测试 |
| STATIC | PASS | 配置、格式、lint、strict mypy、语法 |
| 规划结构 / 自测 | PASS / 32 PASS | 本地规划校验 |
| 治理回归 | 39 PASS | 修复隔离夹具后重新执行；生产验证规则不变 |
| 执行包回归 | 36 PASS | 本地执行包规则；不是远程权限证明 |
| 离线 secret scan | 54 detected / 54 consumed，0 unmatched / unused | 真实扫描，使用已有精确批准，没有新增例外 |
| 必要历史引用 | 330 required / 0 missing | 从已存在且核验过的本地交付库恢复历史对象与本地 tag |

子集数字不能相加为额外测试。原始日志、JUnit 和失败尝试保留在：

`dist/validation/v2005-remediation-20261017/`

最终门禁文件：`final-arch-gate/receipt.json`、`final-arch-gate/action-entry.json`。

## 工程修复与证据边界

1. 删除此前加上的 skip。未修改历史 guard 或嵌入 manifest；正向夹具从固定历史 Git tree 构造，另测工作区脏改不影响夹具，以及篡改、缺失、额外源文件均被拒绝。
2. 原生架构入口改为核验唯一活动任务的执行包及差异，不再对新任务继续使用旧 V2-004 绑定。多活动任务、缺包、错误绑定仍失败；三个架构命令和六个 mandatory gate 保留。
3. 两处治理测试夹具隔离真实 P1 进展，保留原断言与正负控制；没有修改生产 validator。
4. 创建真实 V2-005 执行包并记录整改授权，不追认此前无执行包的开发为已验收。
5. 范围基线仅冻结无关用户改动与工具缓存；任务代码参与真实差异审核。旧失败记录保留，没有以扩大 ignore 或降低门槛换取 PASS。
6. 将本地 origin 规范为不带用户信息的 GitHub URL；未修改远程仓库设置。

执行包：`plan/validation/execution/V2-005/execution-packet.yaml`。

本地 scope/review pin 是执行元数据提交，不是业务交付 SHA。2026-10-18 Owner 已明确授权将全部现有项目改动统一到 main 并提交推送；交付提交及远程读回以 Git 历史和 dist/validation/main-delivery-20261018/ 的实际结果为准。上表是本地测试，不能将旧 CI 视为新提交的远程验证。

本轮由同一 Codex 操作者实施和验证，子代理作技术交叉检查；不声称独立人员验收。此前交接中“skip 即修复”、仅检查 enum 即证明歧义、代码行数代表产品完成度等说法已撤回。原交接副本保留在本地 opening-files 中。

## 保留与未执行

- 用户原有的文档修订及两份文件删除纳入本次授权提交；已在 AGENTS.md 和 README 中补充 main 开发入口、同步当前任务状态。原字节和差异已另存本地，未丢弃用户修改。
- 整改验证阶段未 push；本次另获 Owner 授权提交推送。没有远程 CI、runner 启动、远程设置修改或付费 Provider 调用。
- 本轮没有重放真实 PostgreSQL，也没有重跑在线依赖漏洞审计；不声称六门远程验收完成。
- 没有持久化、Canon 写入、小说生成或真实读者验证。当前交付是内存实体能力，不能推导为完整产品闭环。

## 下一步

将本轮领域实现、工程修复及 Owner 指定的既有项目改动统一交付到 GitHub main。工作区应清洁且本地/远程 main 一致；本次不触发 CI。下一关键验收点再执行远程 CI，绑定同一实际提交，满足任务证据要求后关闭 V2-005。之后进入 V2-006；本轮未提前开发其能力。
