# Canon PostgreSQL migrations

SQL 的唯一源为 `src/anovel/canon/sql/`，随 wheel/sdist 发布。0001保持原始root Schema；0002增量添加章节授权/Permit和有限Delta证据，不改旧root内容。调用 `anovel.canon.migrations.migrate(engine)`：仅 PostgreSQL、事务级迁移锁、已知完整前缀及checksum核对，顺序安装缺失版本并返回最新checksum。不写初始 Canon，不自动选数据库。不能编辑已部署迁移来修改故事历史。

测试创建独立临时数据库，初始事实和章节都通过同一个CanonCommitService写入。生产不得向Worker暴露管理连接；V2-010的P2测试issuer仅用于显式隔离数据库，默认生产服务拒绝该来源。完整生产Q0–Q3签发、一般CAS专项和投影恢复仍由后续任务验收。早期恢复责任见ADR-006，不据此声称生产备份或数据库丢失恢复已验收。
