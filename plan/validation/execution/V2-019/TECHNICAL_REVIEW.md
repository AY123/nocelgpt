# V2-019 技术交叉检查

实施与验证为同一操作者，子Agent交叉检查不构成人员独立审核。原五项AT和六门mandatory保留；没有Writer、Workflow、Canon写路径或secret例外扩张。

| 真实问题 | 决策 | 最小修正及验证 |
|---|---|---|
| x-request-id可以反射凭据并进入SQLite | ACCEPT | 与body一致过滤当前凭据/sk形式，异常头省略；count/generation/both3种回归不保存反射值，实际body hash保留 |
| urllib的socket空闲timeout不能约束慢滴流总等待 | ACCEPT | 每次POST隔离单个daemon exchange并有界等待；超时UNKNOWN保留责任，迟到worker不得持久化或发送下一POST；真实loopback滴流回归 |
| token count结束后可能已过价格有效期 | ACCEPT | 两次POST前均按run deadline/价格期限较早者计算剩余时间；到期禁止generation |
| Provider实际service tier可能不同于请求 | ACCEPT | 冻结请求default；明确非default响应不套用标准价，保留PENDING并冻结run |
| 为恶意自定义adapter另造认证框架 | REJECT | ProviderAdapter为受信应用组合边界，使用冻结Reply契约；当前无插件/不可信代码执行需求 |

预算BEGIN IMMEDIATE、attempt唯一约束、first-success重放、UNKNOWN责任保留、显式retry、fallback共享原额度与迟到真实回复替换纯恢复UNKNOWN均已检查。无须添加工作流/Agent编排、第二Canon或SDK自动重试。

jsonschema从既有锁定dev包移至runtime用于生产响应验证；51个锁定包均保留原版本，无新SDK。CI driver只向原POSTGRES_ENV命令追加V019集成文件；该文件包含SQLite/本地HTTP测试，不冒称所有新增测试都是PostgreSQL或真实OpenAI。

外部Provider、账户模型权限、实际usage/费用和文学质量尚未验证；本地HTTP不能替代这些证据。
