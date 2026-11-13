# V2-013 本地交付

实现只读两Anchor目录加载、精确PackRef、同版Profile及hash、完整原始/规范manifest和目录来源、不可变项目binding。可选策略只在绑定Pack中精确匹配，未提供或无命中返回NO_MATCH，不跨Pack/相近子流派fallback。生产仅标准库及既有CJSON1，无新依赖、Canon写入、动态插件或语义判定。

实际本地：1187 UNIT（含新63）、244 ARCH、157 PostgreSQL = 1588项，0失败/error/skip；static与5项规划检查通过；54/54精确安全消费、0未匹配/未使用、51依赖0漏洞。初次专属None语义及mypy循环变量错误保留原日志，修复后专属63和静态复测通过，不将原失败改写为PASS。原始命令/日志/JUnit和收据在dist/validation/v2013-local-20261113；机器摘要LOCAL_RESULTS.json。本地记录不是远程验收。

使用入口：`GenreRegistry.from_directory(Path("specs/genres"))`，`load(PackRef(id,version,content_hash))`，`bind(project,ref)`，`binding.select_strategy(exact_id)`。调用方必须显式指定完整ref，不从packs[0]选择默认题材。`to_dict()`提供独立导出副本与可追溯bytes/hash；本轮不声称项目绑定已写入数据库。

ADR-007先于接口接受。同操作者实施、验证及技术交叉检查，不冒称独立人员审计。extensions当前为空、所有未实现扩展拒绝；V2-014～016实际policy/类型扩展、模型写作、阅读质量及外部备份均未完成。下一步只在精确差异通过后进行一次关键同SHA六门CI。
